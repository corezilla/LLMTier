from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from tier_config import TierConfig

_QUOTA_ERROR_MARKERS = (
    "accountquotaexceeded", "quota", "rate limit", "rate_limit",
    "too many requests", "http error: 429", " 429 ", "reset at ",
    "notenoughcv", "notenoughcverror",
    "限额已用尽", "配额不足", "额度不足", "配额已耗尽",
    "insufficient_quota", "exceeded your quota", "usage limit",
)

_QUOTA_STATE_FILE = "quota_state.json"


# 用途：
# - 返回默认 quota state 目录，避免运行态文件落到 repo 根目录或调用者当前目录
# 输入：
# - 无
# 输出：
# - LLMTier 项目 state/quota 路径
def _default_quota_state_dir() -> Path:
    repo_root = Path(__file__).resolve().parent.parent
    configured_path = os.environ.get("LLMTIER_STATE_DIR", "").strip()
    state_root = Path(configured_path).expanduser() if configured_path else repo_root / "state"
    return state_root / "quota"


# 用途：
# - 管理 LLM backend 的 quota exhausted 状态和可选 reset_at 展示值
# 输入：
# - TierConfig 和可选 state_dir
# 输出：
# - 可持久化、可查询、可自动重置的 quota 状态管理器
class QuotaManager:
    # 用途：
    # - 初始化配额管理器并加载持久化 exhausted 状态
    # 输入：
    # - tier_config: backend quota/reset 配置
    # - state_dir: quota_state.json 所在目录
    # 输出：
    # - 可供 router/server 查询和更新的 QuotaManager 实例
    def __init__(self, tier_config: TierConfig, state_dir: str | Path = "") -> None:
        self._tier_config = tier_config
        self._exhausted: dict[str, bool] = {}
        self._mark_time: dict[str, float] = {}
        self._reset_time: dict[str, str] = {}
        self._state_dir = Path(state_dir) if str(state_dir or "").strip() else _default_quota_state_dir()
        self._load_state()

    # =========================================================================
    # 持久化
    # =========================================================================

    # 用途：
    # - 解析当前 quota state 文件路径
    # 输入：
    # - 无；读取初始化时的 state_dir
    # 输出：
    # - quota_state.json 的文件路径
    def _state_path(self) -> str:
        return str(self._state_dir / _QUOTA_STATE_FILE)

    # 用途：
    # - 从 quota_state.json 恢复 exhausted 和 reset_at 状态
    # 输入：
    # - 无；读取 `_state_path()`
    # 输出：
    # - 更新内存中的 exhausted/mark_time/reset_time
    def _load_state(self) -> None:
        path = self._state_path()
        try:
            if os.path.isfile(path):
                with open(path) as f:
                    data = json.load(f)
                for entry in data.get("exhausted", []):
                    key = entry.get("key", "")
                    ts = entry.get("exhausted_ts", 0)
                    if key:
                        self._exhausted[key] = True
                        self._mark_time[key] = ts
                        reset_at = self._normalize_reset_at(entry.get("reset_at", ""))
                        if reset_at:
                            self._reset_time[key] = reset_at
        except (OSError, json.JSONDecodeError):
            return

    # 用途：
    # - 将当前 exhausted 状态持久化到 quota_state.json
    # 输入：
    # - 无；读取内存状态
    # 输出：
    # - 写入 quota_state.json
    def _save_state(self) -> None:
        path = self._state_path()
        try:
            data = {
                "exhausted": [
                    {"key": k, "exhausted_ts": self._mark_time.get(k, 0),
                     "reset_at": self._reset_time.get(k, "")}
                    for k, v in self._exhausted.items() if v
                ],
            }
            dirname = os.path.dirname(path)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except OSError:
            return

    # 用途：
    # - 将 backend/model 定位到 account 级 quota key
    # 输入：
    # - backend/model_name: backend 标识和展示模型名
    # 输出：
    # - `account:<account>`；缺失 account 时退回 backend:model 以暴露配置问题
    def _quota_key(self, backend: str, model_name: str) -> str:
        model = self._tier_config.find_backend_model(backend, model_name=model_name)
        account = str(getattr(model, "account", "") or "").strip() if model is not None else ""
        if account:
            return f"account:{account}"
        return f"{backend}:{model_name}"

    # 用途：
    # - 判断指定 backend/model 是否已被标记为配额耗尽
    # 输入：
    # - backend/model_name: backend 标识和展示模型名
    # 输出：
    # - True 表示当前不可选
    def is_exhausted(self, backend: str, model_name: str) -> bool:
        self._check_auto_reset(backend, model_name)
        key = self._quota_key(backend, model_name)
        return self._exhausted.get(key, False)

    # 用途：
    # - 将指定 backend/model 标记为配额耗尽，并记录可解析的 reset_at
    # 输入：
    # - backend/model_name: backend 标识和展示模型名
    # - error_message: 后端错误文本，仅用于提取明确 reset 时间
    # 输出：
    # - 更新内存和持久化状态
    def mark_exhausted(self, backend: str, model_name: str, error_message: str = "") -> None:
        key = self._quota_key(backend, model_name)
        self._exhausted[key] = True
        self._mark_time[key] = time.time()
        reset_at = self._parse_reset_at(error_message)
        if reset_at:
            self._reset_time[key] = reset_at
        else:
            self._reset_time.pop(key, None)
        self._save_state()

    @staticmethod
    # 用途：
    # - 从配额错误消息中提取明确的 reset 时间
    # 输入：
    # - msg: backend 错误文本
    # 输出：
    # - `YYYY-MM-DD HH:MM` 或空字符串；绝不返回任意原始错误文本
    def _parse_reset_at(msg: str) -> str:
        import re
        from datetime import datetime

        raw = ""
        # "try again at May 31st, 2026 9:05 AM"
        m = re.search(r'(?:try again at|reset at|retry at)\s+(.+?)(?:\.|$)', msg, re.IGNORECASE)
        if m:
            raw = m.group(1).strip()
        else:
            # "It will reset at 2026-06-13 23:59:59 +0800 CST"
            m = re.search(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', msg)
            if m:
                raw = m.group(0)

        if not raw:
            # 可能是纯时间字符串直接传入
            raw = msg.strip()

        raw = QuotaManager._normalize_reset_at(raw)
        if not raw:
            return ""

        # 统一转 YYYY-MM-DD HH:MM
        # 格式1: "May 31st, 2026 9:05 AM" → 去掉序数后缀
        m = re.match(r'([A-Za-z]+)\s+(\d+)(?:st|nd|rd|th)?,\s+(\d{4})\s+(\d+):(\d+)\s*(AM|PM)', raw)
        if m:
            try:
                dt = datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)} {m.group(4)}:{m.group(5)} {m.group(6)}",
                                       "%B %d %Y %I:%M %p")
            except ValueError:
                dt = None
            if dt is not None:
                return dt.strftime("%Y-%m-%d %H:%M")
        # 格式2: "2026-06-13 23:59:59" → 截取到分钟
        m = re.match(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', raw)
        if m:
            return m.group(1)

        return ""

    @staticmethod
    # 用途：
    # - 过滤持久化 state 中的 reset_at，防止旧错误文本污染 dashboard
    # 输入：
    # - reset_at: quota_state 中保存的 reset_at 值
    # 输出：
    # - 合法时间字符串或空字符串
    def _normalize_reset_at(reset_at: Any) -> str:
        import re

        value = str(reset_at or "").strip()
        if not value:
            return ""
        datetime_match = re.search(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?", value)
        if datetime_match:
            return datetime_match.group(0)[:16]
        if re.fullmatch(r"\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)", value):
            return value
        return ""

    # 用途：
    # - 清空全部 quota exhausted 状态
    # 输入：
    # - 无
    # 输出：
    # - 内存和持久化 quota state 均被重置
    def reset_all(self) -> None:
        self._exhausted.clear()
        self._mark_time.clear()
        self._reset_time.clear()
        self._save_state()

    # 用途：
    # - 清空指定 Tier 下模型的 quota exhausted 状态
    # 输入：
    # - tier_name: 要重置的 Tier 名称
    # 输出：
    # - 对应 backend/model 的内存和持久化 state 被移除
    def reset_tier(self, tier_name: str) -> None:
        models = self._tier_config.get_tier_models(tier_name)
        for m in models:
            key = self._quota_key(m.backend, m.model_name)
            self._exhausted.pop(key, None)
            self._mark_time.pop(key, None)
            self._reset_time.pop(key, None)
        self._save_state()

    # 用途：
    # - 清空指定 backend/model 的 quota exhausted 状态
    # 输入：
    # - backend/model_name: 要清理的 backend 标识和展示模型名
    # 输出：
    # - 对应 backend/model 的内存和持久化 state 被移除
    def reset_backend(self, backend: str, model_name: str) -> None:
        key = self._quota_key(backend, model_name)
        self._exhausted.pop(key, None)
        self._mark_time.pop(key, None)
        self._reset_time.pop(key, None)
        self._save_state()

    # 用途：
    # - 返回指定 backend/model 当前 quota exhausted 记录，供 tier 调度恢复 probe
    # 输入：
    # - backend/model_name: backend 标识和展示模型名
    # 输出：
    # - 包含 key/exhausted_ts/exhausted_at/reset_at 的字典；未 exhausted 时返回空字典
    def get_exhausted_info(self, backend: str, model_name: str) -> dict[str, Any]:
        self._check_auto_reset(backend, model_name)
        key = self._quota_key(backend, model_name)
        if not self._exhausted.get(key, False):
            return {}
        mark_ts = self._mark_time.get(key, 0.0)
        return {
            "key": key,
            "exhausted_ts": mark_ts,
            "exhausted_at": datetime.fromtimestamp(mark_ts).isoformat() if mark_ts else "",
            "reset_at": self._reset_time.get(key, ""),
        }

    # 用途：
    # - 将 provider usage 刷新的 reset_at 回写到当前 exhausted 记录
    # 输入：
    # - backend/model_name/reset_at: backend 标识和 provider 推导出的恢复时间
    # 输出：
    # - True 表示已更新持久化 reset_at；False 表示无有效 exhausted 记录或 reset_at
    def update_exhausted_reset_at(self, backend: str, model_name: str, reset_at: Any) -> bool:
        key = self._quota_key(backend, model_name)
        if not self._exhausted.get(key, False):
            return False
        normalized = self._normalize_reset_at(reset_at)
        if not normalized:
            return False
        self._reset_time[key] = normalized
        self._save_state()
        return True

    # 用途：
    # - 返回全部 exhausted backend 的展示状态
    # 输入：
    # - 无
    # 输出：
    # - 包含 key/exhausted_at/reset_at 的列表
    def get_all_exhausted(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for key, exhausted in self._exhausted.items():
            if not exhausted:
                continue
            mark_ts = self._mark_time.get(key, 0.0)
            result.append({
                "key": key,
                "exhausted_at": datetime.fromtimestamp(mark_ts).isoformat() if mark_ts else "",
                "reset_at": self._reset_time.get(key, ""),
            })
        return result

    @staticmethod
    # 用途：
    # - 判断错误文本是否代表 quota/rate-limit 类错误
    # 输入：
    # - error_message: backend 错误文本
    # 输出：
    # - True 表示 router 可进入 quota exhausted fallback 逻辑
    def is_quota_error(error_message: str) -> bool:
        msg_lower = error_message.lower()
        return any(marker in msg_lower for marker in _QUOTA_ERROR_MARKERS)

    # 用途：
    # - 根据 quota 配置自动解除已过周期的 exhausted 状态
    # 输入：
    # - backend/model_name: backend 标识和展示模型名
    # 输出：
    # - 必要时更新内存 exhausted 状态
    def _check_auto_reset(self, backend: str, model_name: str) -> None:
        quota_cfg = self._tier_config.get_quota_config(backend)
        if not quota_cfg:
            return
        reset_day = quota_cfg.get("reset_day", "")
        if not reset_day:
            return
        key = self._quota_key(backend, model_name)
        last_mark_ts = self._mark_time.get(key, 0.0)
        if last_mark_ts == 0.0:
            return
        last_mark = datetime.fromtimestamp(last_mark_ts)
        now = datetime.now()
        if isinstance(reset_day, str):
            if now.weekday() != last_mark.weekday() or (now.weekday() == last_mark.weekday() and now > last_mark and last_mark.weekday() != now.weekday()):
                self._exhausted.pop(key, None)
                self._mark_time.pop(key, None)
                self._reset_time.pop(key, None)
        elif isinstance(reset_day, int):
            if now.day >= reset_day and last_mark.day < reset_day:
                self._exhausted.pop(key, None)
                self._mark_time.pop(key, None)
                self._reset_time.pop(key, None)
