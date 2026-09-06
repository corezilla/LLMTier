from __future__ import annotations

import hashlib
import hmac
import json
import re
import ssl
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from llm_tier.tier_model import TierModel


VOLC_SERVICE = "ark"
VOLC_REGION = "cn-beijing"
VOLC_USAGE_HOST = "ark.cn-beijing.volcengineapi.com"
VOLC_USAGE_VERSION = "2024-01-01"
MINIMAX_USAGE_URL = "https://api.minimaxi.com/v1/coding_plan/remains"
MINIMAX_CONSOLE_USAGE_URL = "https://www.minimaxi.com/v1/api/openplatform/coding_plan/remains"
XFYUN_CODING_PLAN_LIST_URL = "https://maas.xfyun.cn/api/v1/gpt-finetune/coding-plan/list"
DEFAULT_USAGE_CACHE_SECONDS = 300


# 用途：
# - 保存单个 backend 对应的 provider 用量快照
# 输入：
# - 由 ProviderUsageManager 根据 backend/provider/quota/credentials 构造
# 输出：
# - 可直接放入 /runtime backend row 的字典
@dataclass
class ProviderUsageSnapshot:
    provider: str
    source: str
    status: str
    usage_key: str
    used: float | None = None
    quota: float | None = None
    remaining: float | None = None
    percent: float | None = None
    reset_at: str = ""
    window: str = ""
    windows: list[dict[str, Any]] | None = None
    checked_at: str = ""
    error: str = ""

    # 用途：
    # - 转成 JSON 友好的字典
    # 输入：
    # - 无；读取当前 snapshot 字段
    # 输出：
    # - Dashboard 和 API 可消费的 provider usage payload
    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "source": self.source,
            "status": self.status,
            "usage_key": self.usage_key,
            "account_key": self.usage_key.rsplit(":", 1)[-1] if ":" in self.usage_key else self.usage_key,
            "used": self.used,
            "quota": self.quota,
            "remaining": self.remaining,
            "percent": self.percent,
            "reset_at": self.reset_at,
            "window": self.window,
            "windows": self.windows or [],
            "checked_at": self.checked_at,
            "error": self.error,
        }


# 用途：
# - 为 Tier runtime 查询并缓存云模型 provider 用量，避免 dashboard 高频刷新压 provider API
# 输入：
# - cache_ttl_seconds: provider usage 查询缓存周期
# 输出：
# - `usage_for_model()` 可按 backend 返回用量快照
class ProviderUsageManager:
    # 用途：
    # - 初始化 provider usage 缓存
    # 输入：
    # - cache_ttl_seconds: 同一 usage key 的最小刷新间隔
    # 输出：
    # - 可复用的 ProviderUsageManager 实例
    def __init__(self, cache_ttl_seconds: int = DEFAULT_USAGE_CACHE_SECONDS) -> None:
        self._cache_ttl_seconds = max(60, int(cache_ttl_seconds or DEFAULT_USAGE_CACHE_SECONDS))
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = threading.RLock()

    # 用途：
    # - 清空 provider usage 缓存，让下一次强制刷新重新读取 cookie/key 文件
    # 输入：
    # - 无
    # 输出：
    # - 无
    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()

    # 用途：
    # - 返回一个 backend 的 provider usage 快照；普通读取只使用缓存，强制刷新才访问外部 provider
    # 输入：
    # - model: 当前 TierModel backend 配置
    # - force_refresh: True 时忽略缓存并立即重新查询 provider usage
    # 输出：
    # - provider usage 字典；未刷新过时返回 not_refreshed，避免 dashboard 自动刷新触网阻塞
    def usage_for_model(self, model: TierModel, *, force_refresh: bool = False) -> dict[str, Any]:
        usage_key = provider_usage_key(model)
        now = time.time()
        with self._lock:
            cached = self._cache.get(usage_key)
        if not force_refresh and cached and now - cached[0] < self._cache_ttl_seconds:
            return dict(cached[1])
        if not force_refresh:
            return ProviderUsageSnapshot(
                provider=resolved_quota_provider(model),
                source="cache",
                status="not_refreshed",
                usage_key=usage_key,
                checked_at=now_iso(),
            ).to_dict()

        snapshot = self._load_usage(model, usage_key).to_dict()
        with self._lock:
            self._cache[usage_key] = (now, snapshot)
        return dict(snapshot)

    # 用途：
    # - 强制刷新一个 backend 的 provider usage，并写入共享 cache
    # 输入：
    # - model: 当前 TierModel backend 配置
    # 输出：
    # - 最新 provider usage 字典；调用方可直接写入 runtime 状态
    def refresh_for_model(self, model: TierModel) -> dict[str, Any]:
        return self.usage_for_model(model, force_refresh=True)

    # 用途：
    # - 按 provider 分发实际 usage 查询或配置推导
    # 输入：
    # - model/usage_key: backend 配置和去敏后的缓存 key
    # 输出：
    # - ProviderUsageSnapshot
    def _load_usage(self, model: TierModel, usage_key: str) -> ProviderUsageSnapshot:
        provider = resolved_quota_provider(model)
        if _is_unlimited_quota(model.quota):
            return _unlimited_usage_snapshot(provider=provider, usage_key=usage_key)
        if provider == "volc":
            return self._load_volc_usage(model, usage_key)
        if provider == "xfyun":
            return self._load_xfyun_usage(model, usage_key)
        if provider == "minimax":
            return self._load_minimax_usage(model, usage_key)
        if provider == "opencode-go":
            return self._load_opencode_go_usage(model, usage_key)
        return ProviderUsageSnapshot(
            provider=provider,
            source="unsupported",
            status="unsupported",
            usage_key=usage_key,
            checked_at=now_iso(),
            error="provider_usage_unsupported",
        )

    # 用途：
    # - 使用 AK/SK 调用火山方舟 Coding Plan OpenAPI 获取真实用量和 ResetTime
    # 输入：
    # - model/usage_key: backend 配置和缓存 key
    # 输出：
    # - 成功时返回真实 usage；缺少查询凭据或调用失败时返回错误快照
    def _load_volc_usage(self, model: TierModel, usage_key: str) -> ProviderUsageSnapshot:
        access_key = str(
            model.credentials.get("usage_access_key_id")
            or model.credentials.get("access_key_id")
            or _read_text_file(str(model.credentials.get("usage_access_key_id_file") or ""))
            or ""
        ).strip()
        secret_key = str(
            model.credentials.get("usage_secret_access_key")
            or model.credentials.get("secret_access_key")
            or _read_text_file(str(model.credentials.get("usage_secret_access_key_file") or ""))
            or ""
        ).strip()
        if not access_key or not secret_key:
            return self._derived_usage(
                model,
                usage_key,
                provider="volc",
                source="credentials_missing",
                error="volc_get_coding_plan_usage_requires_ak_sk",
            )

        try:
            payload = _volc_signed_json_request(
                action="GetCodingPlanUsage",
                access_key=access_key,
                secret_key=secret_key,
            )
        except Exception as exc:  # noqa: BLE001
            return self._derived_usage(
                model,
                usage_key,
                provider="volc",
                source="provider_api_error",
                error=f"{exc.__class__.__name__}:{str(exc)[:160]}",
            )

        result = payload.get("Result") if isinstance(payload.get("Result"), dict) else {}
        snapshot = _snapshot_from_volc_coding_plan_result(usage_key=usage_key, result=result)
        if snapshot:
            return snapshot
        return self._derived_usage(
            model,
            usage_key,
            provider="volc",
            source="provider_api",
            error="volc_get_coding_plan_usage_empty_result",
        )

    # 用途：
    # - 调用 MiniMax Coding Plan usage API 获取当前窗口用量
    # 输入：
    # - model/usage_key: backend 配置和缓存 key
    # 输出：
    # - 成功时返回真实 usage；失败时返回配置推导 snapshot
    def _load_minimax_usage(self, model: TierModel, usage_key: str) -> ProviderUsageSnapshot:
        cookie = str(
            model.credentials.get("usage_cookie")
            or _read_text_file(str(
                model.credentials.get("usage_cookie_file")
                or model.credentials.get("console_cookie_file")
                or ""
            ))
            or ""
        ).strip()
        if cookie:
            return self._load_minimax_console_usage(model, usage_key, cookie)

        api_key = str(
            model.credentials.get("api_key")
            or _read_api_key_file(str(model.credentials.get("api_key_file") or ""))
            or ""
        ).strip()
        if not api_key:
            return self._derived_usage(
                model,
                usage_key,
                provider="minimax",
                source="credentials_missing",
                error="minimax_usage_requires_api_key",
            )
        try:
            request = urllib.request.Request(
                MINIMAX_USAGE_URL,
                method="GET",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            with _urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            return self._derived_usage(
                model,
                usage_key,
                provider="minimax",
                source="provider_api_error",
                error=f"minimax_usage_http_{exc.code}:{text[:120]}",
            )
        except Exception as exc:  # noqa: BLE001
            return self._derived_usage(
                model,
                usage_key,
                provider="minimax",
                source="provider_api_error",
                error=f"{exc.__class__.__name__}:{str(exc)[:160]}",
            )

        base_resp = payload.get("base_resp") if isinstance(payload.get("base_resp"), dict) else {}
        if int(base_resp.get("status_code") or 0) != 0:
            return self._derived_usage(
                model,
                usage_key,
                provider="minimax",
                source="provider_api_error",
                error=str(base_resp.get("status_msg") or "minimax_usage_failed")[:160],
            )
        remains = payload.get("model_remains") if isinstance(payload.get("model_remains"), list) else []
        selected = _select_minimax_remains(model, remains)
        if not selected:
            return self._derived_usage(
                model,
                usage_key,
                provider="minimax",
                source="provider_api",
                error="minimax_usage_empty_result",
            )
        return _snapshot_from_minimax_remains(model=model, usage_key=usage_key, item=selected)

    # 用途：
    # - 调用 MiniMax 平台 `coding_plan/remains` 接口获取 Token Plan 用量窗口
    # 输入：
    # - model/usage_key/cookie: backend 配置、缓存 key 和 MiniMax 平台登录态
    # 输出：
    # - 成功时返回 5hour/weekly 用量窗口；失败时返回配置推导 snapshot
    def _load_minimax_console_usage(
        self,
        model: TierModel,
        usage_key: str,
        cookie: str,
    ) -> ProviderUsageSnapshot:
        group_id = str(
            model.credentials.get("usage_group_id")
            or model.credentials.get("group_id")
            or _cookie_value(cookie, "minimax_group_id_v2")
            or ""
        ).strip()
        usage_url = str(model.credentials.get("usage_url") or MINIMAX_CONSOLE_USAGE_URL).strip()
        try:
            request = urllib.request.Request(
                usage_url,
                method="GET",
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "Cookie": cookie,
                    "Origin": "https://platform.minimaxi.com",
                    "Referer": "https://platform.minimaxi.com/",
                    "X-Group-Id": group_id,
                },
            )
            with _urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            return self._derived_usage(
                model,
                usage_key,
                provider="minimax",
                source="provider_api_error",
                error=f"minimax_console_usage_http_{exc.code}:{text[:120]}",
            )
        except Exception as exc:  # noqa: BLE001
            return self._derived_usage(
                model,
                usage_key,
                provider="minimax",
                source="provider_api_error",
                error=f"{exc.__class__.__name__}:{str(exc)[:160]}",
            )

        base_resp = payload.get("base_resp") if isinstance(payload.get("base_resp"), dict) else {}
        if base_resp and int(base_resp.get("status_code") or 0) != 0:
            return self._derived_usage(
                model,
                usage_key,
                provider="minimax",
                source="provider_api_error",
                error=str(base_resp.get("status_msg") or "minimax_console_usage_failed")[:160],
            )
        remains = payload.get("model_remains") if isinstance(payload.get("model_remains"), list) else []
        selected = _select_minimax_remains(model, remains)
        if not selected:
            usage_summary = _snapshot_from_minimax_usage_summary(model=model, usage_key=usage_key, payload=payload)
            if usage_summary:
                return usage_summary
            return self._derived_usage(
                model,
                usage_key,
                provider="minimax",
                source="provider_api",
                error="minimax_console_usage_empty_result",
            )
        return _snapshot_from_minimax_remains(model=model, usage_key=usage_key, item=selected)

    # 用途：
    # - 调用讯飞 MaaS CodingPlan 页面使用的 list 接口获取真实用量
    # 输入：
    # - model/usage_key: backend 配置和缓存 key
    # 输出：
    # - 成功时返回 CodingPlan 订阅聚合用量；缺少网页登录态或调用失败时返回配置推导 snapshot
    def _load_xfyun_usage(self, model: TierModel, usage_key: str) -> ProviderUsageSnapshot:
        cookie = str(
            model.credentials.get("usage_cookie")
            or _read_text_file(str(
                model.credentials.get("usage_cookie_file")
                or model.credentials.get("console_cookie_file")
                or ""
            ))
            or ""
        ).strip()
        if not cookie:
            return self._derived_usage(
                model,
                usage_key,
                provider="xfyun",
                source="credentials_missing",
                error="xfyun_coding_plan_usage_requires_console_cookie",
            )

        usage_url = str(model.credentials.get("usage_url") or XFYUN_CODING_PLAN_LIST_URL).strip()
        separator = "&" if "?" in usage_url else "?"
        request_url = f"{usage_url}{separator}page=1&size=200"
        try:
            request = urllib.request.Request(
                request_url,
                method="GET",
                headers={
                    "Accept": "application/json",
                    "Cookie": cookie,
                    "X-Requested-With": "XMLHttpRequest",
                },
            )
            with _urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            return self._derived_usage(
                model,
                usage_key,
                provider="xfyun",
                source="provider_api_error",
                error=f"xfyun_usage_http_{exc.code}:{text[:120]}",
            )
        except Exception as exc:  # noqa: BLE001
            return self._derived_usage(
                model,
                usage_key,
                provider="xfyun",
                source="provider_api_error",
                error=f"{exc.__class__.__name__}:{str(exc)[:160]}",
            )

        if int(payload.get("code") or 0) != 0:
            return self._derived_usage(
                model,
                usage_key,
                provider="xfyun",
                source="provider_api_error",
                error=str(payload.get("message") or payload.get("desc") or "xfyun_usage_failed")[:160],
            )
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        rows = data.get("rows") if isinstance(data.get("rows"), list) else []
        snapshot = _snapshot_from_xfyun_coding_plans(model=model, usage_key=usage_key, rows=rows)
        if snapshot:
            return snapshot
        return self._derived_usage(
            model,
            usage_key,
            provider="xfyun",
            source="provider_api",
            error="xfyun_usage_empty_result",
        )

    # 用途：
    # - 从 opencode-go workspace 页面 SSR 数据读取滚动/每周/每月用量
    # 输入：
    # - model/usage_key: backend 配置和缓存 key
    # 输出：
    # - 成功时返回 percent-only usage；缺少网页登录态或解析失败时返回配置推导 snapshot
    def _load_opencode_go_usage(self, model: TierModel, usage_key: str) -> ProviderUsageSnapshot:
        cookie = str(
            model.credentials.get("usage_cookie")
            or _read_text_file(str(
                model.credentials.get("usage_cookie_file")
                or model.credentials.get("console_cookie_file")
                or ""
            ))
            or ""
        ).strip()
        usage_url = str(model.credentials.get("usage_workspace_url") or model.credentials.get("usage_url") or "").strip()
        if not cookie or not usage_url:
            return self._derived_usage(
                model,
                usage_key,
                provider="opencode-go",
                source="credentials_missing",
                error="opencode_go_usage_requires_workspace_url_and_cookie",
            )
        try:
            request = urllib.request.Request(
                usage_url,
                method="GET",
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Cookie": cookie,
                    "User-Agent": "Mozilla/5.0",
                },
            )
            with _urlopen(request, timeout=20) as response:
                html = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            return self._derived_usage(
                model,
                usage_key,
                provider="opencode-go",
                source="provider_api_error",
                error=f"opencode_go_usage_http_{exc.code}:{text[:120]}",
            )
        except Exception as exc:  # noqa: BLE001
            return self._derived_usage(
                model,
                usage_key,
                provider="opencode-go",
                source="provider_api_error",
                error=f"{exc.__class__.__name__}:{str(exc)[:160]}",
            )

        snapshot = _snapshot_from_opencode_go_workspace_html(usage_key=usage_key, html=html)
        if snapshot:
            return snapshot
        return self._derived_usage(
            model,
            usage_key,
            provider="opencode-go",
            source="provider_api",
            error="opencode_go_usage_html_parse_failed",
        )

    # 用途：
    # - 在 provider 没有可调用 usage API 时，根据 backend quota 配置推导下一次 reset 时间
    # 输入：
    # - model/usage_key/provider/source/error: backend 配置、provider 名和状态说明
    # 输出：
    # - 不含 used/quota 的 usage snapshot，但包含 reset_at/window
    def _derived_usage(
        self,
        model: TierModel,
        usage_key: str,
        *,
        provider: str,
        source: str,
        error: str,
    ) -> ProviderUsageSnapshot:
        reset_at, window = derive_reset_at_from_quota(model.quota)
        windows = [_usage_window_entry(window, None, None, reset_at)] if window else []
        return ProviderUsageSnapshot(
            provider=provider,
            source=source,
            status="unavailable",
            usage_key=usage_key,
            reset_at=reset_at,
            window=window,
            windows=windows,
            checked_at=now_iso(),
            error=error,
        )


# 用途：
# - 解析 backend 的真实 quota provider，而不是 CLI adapter 名称
# 输入：
# - model: backend 配置
# 输出：
# - provider usage 归属名
def resolved_quota_provider(model: TierModel) -> str:
    quota_provider = str(
        model.quota.get("usage_provider")
        or model.quota.get("quota_provider")
        or ""
    ).strip().lower()
    if quota_provider:
        return quota_provider.replace("_", "-")
    provider = str(model.provider or "").strip().lower()
    model_key = str(model.model_key or "").strip().lower()
    model_name = str(model.model_name or "").strip().lower()
    normalized_provider = provider.replace("_", "-")
    if provider in {"claude"} and "minimax" in model_name:
        return "minimax"
    if normalized_provider == "opencode-go":
        return "opencode-go"
    if provider == "mlexp":
        usage_account = str(model.usage_account or "").strip().lower()
        if usage_account in {"ollama", "local", "llama", "llamacpp", "llama.cpp"}:
            return usage_account
        if usage_account == "go" or model_key.startswith("go/") or model_name.startswith("go/"):
            return "opencode-go"
    if provider in {"opencode"}:
        if model_key.startswith("xfyun/") or model_name.startswith("xfyun/"):
            return "xfyun"
        if model_key.startswith("opencode-go/") or model_name.startswith("go/"):
            return "opencode-go"
        if "minimax" in model_key or "minimax" in model_name:
            return "minimax"
    return provider


# 用途：
# - 判断 backend/account quota 是否声明为无限额度
# 输入：
# - quota: TierModel 聚合后的 quota 配置
# 输出：
# - True 表示 Dashboard 应按无限额度展示，而不是当作 usage unsupported
def _is_unlimited_quota(quota: dict[str, Any]) -> bool:
    quota_type = str((quota or {}).get("quota_type") or "").strip().lower()
    return quota_type in {"unlimited", "infinite", "none", "no_limit"}


# 用途：
# - 构造无限额度 provider usage snapshot
# 输入：
# - provider/usage_key: provider 名称和稳定 usage key
# 输出：
# - status=unlimited 的 authoritative runtime usage 记录
def _unlimited_usage_snapshot(*, provider: str, usage_key: str) -> ProviderUsageSnapshot:
    return ProviderUsageSnapshot(
        provider=provider,
        source="quota_config",
        status="unlimited",
        usage_key=usage_key,
        checked_at=now_iso(),
    )


# 用途：
# - 构造同一云模型账号共享的 usage cache key，并避免泄露 credential
# 输入：
# - model: backend 配置
# 输出：
# - provider + scope/account + credential hash 组成的稳定 key
def provider_usage_key(model: TierModel) -> str:
    provider = resolved_quota_provider(model)
    scope = str(model.quota.get("quota_scope") or model.quota.get("scope") or "account").strip()
    account_seed = _provider_usage_account_seed(model, provider)
    credential_hash = hashlib.sha256(account_seed.encode("utf-8")).hexdigest()[:12]
    return f"{provider}:{scope}:{credential_hash}"


# 用途：
# - 解析 provider usage 的账号维度，避免同 provider 不同账号共用 usage cache
# 输入：
# - model/provider: backend 配置和已解析的 quota provider
# 输出：
# - 去敏前账号种子；只用于 hash，不直接暴露到 runtime
def _provider_usage_account_seed(model: TierModel, provider: str) -> str:
    explicit_account = str(
        model.credentials.get("usage_account_id")
        or model.credentials.get("account_id")
        or model.quota.get("usage_account_id")
        or model.quota.get("account_id")
        or ""
    ).strip()
    if explicit_account:
        return f"account:{explicit_account}"
    if provider == "xfyun":
        api_key = str(
            model.credentials.get("api_key")
            or _read_api_key_file(str(model.credentials.get("api_key_file") or ""))
            or ""
        ).strip()
        if api_key:
            return f"xfyun_api_key:{api_key}"
    return str(
        model.credentials.get("usage_access_key_id")
        or _read_text_file(str(model.credentials.get("usage_access_key_id_file") or ""))
        or model.credentials.get("access_key_id")
        or model.credentials.get("usage_cookie_file")
        or model.credentials.get("console_cookie_file")
        or model.credentials.get("usage_cookie")
        or model.credentials.get("api_key")
        or model.credentials.get("api_key_file")
        or model.backend
    ).strip()


# 用途：
# - 根据 quota_type/reset_day 推导下一次 reset 时间
# 输入：
# - quota: backend 自身 quota 配置
# 输出：
# - `(reset_at, window)`；无法推导时 reset_at 为空
def derive_reset_at_from_quota(quota: dict[str, Any]) -> tuple[str, str]:
    quota_type = str(quota.get("quota_type") or "").strip().lower()
    reset_day = quota.get("reset_day")
    now = datetime.now(timezone(timedelta(hours=8)))
    if quota_type == "daily":
        reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return format_reset_time(reset), "daily"
    if quota_type == "weekly":
        reset_hour = 8 if str(reset_day or "").strip().lower() in {"monday", "mon"} else 0
        days_ahead = (0 - now.weekday()) % 7
        reset = (now + timedelta(days=days_ahead)).replace(hour=reset_hour, minute=0, second=0, microsecond=0)
        if reset <= now:
            reset += timedelta(days=7)
        return format_reset_time(reset), "weekly"
    if quota_type == "monthly":
        try:
            day = max(1, min(28, int(reset_day or 1)))
        except (TypeError, ValueError):
            day = 1
        year = now.year
        month = now.month
        reset = now.replace(day=day, hour=0, minute=0, second=0, microsecond=0)
        if reset <= now:
            if month == 12:
                year += 1
                month = 1
            else:
                month += 1
            reset = reset.replace(year=year, month=month, day=day)
        return format_reset_time(reset), "monthly"
    return "", ""


# 用途：
# - 返回当前 UTC ISO 时间
# 输入：
# - 无
# 输出：
# - ISO 8601 UTC 时间字符串
def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# 用途：
# - 把 reset datetime 格式化为 Dashboard 使用的本地时间字符串
# 输入：
# - value: 带时区 datetime
# 输出：
# - `YYYY-MM-DD HH:MM` 字符串
def format_reset_time(value: datetime) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M")


# 用途：
# - 读取 MiniMax api_key_file，供 provider usage 查询复用 backend 配置
# 输入：
# - api_key_file: 配置中的 key 文件路径
# 输出：
# - key 文本；读取失败时返回空字符串
def _read_api_key_file(api_key_file: str) -> str:
    return _read_text_file(api_key_file)


# 用途：
# - 读取本地文本文件，供 api key / console cookie 等 provider credential 使用
# 输入：
# - file_path: 配置中的文件路径
# 输出：
# - 文件文本；读取失败时返回空字符串
def _read_text_file(file_path: str) -> str:
    from pathlib import Path

    path_text = str(file_path or "").strip()
    if not path_text:
        return ""
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


# 用途：
# - 从 Cookie header 中提取指定 cookie 值
# 输入：
# - cookie/name: Cookie header 文本和 cookie 名
# 输出：
# - cookie 值；不存在时返回空字符串
def _cookie_value(cookie: str, name: str) -> str:
    target = f"{name}="
    for item in str(cookie or "").split(";"):
        part = item.strip()
        if part.startswith(target):
            return part[len(target):].strip()
    return ""


# 用途：
# - 判断 Cookie header 中某个 JWT cookie 是否已经过期
# 输入：
# - cookie/name: Cookie header 文本和 JWT cookie 名
# 输出：
# - 已过期时返回本地时间字符串；未过期或无法解析时返回空字符串
def _jwt_cookie_expired_at(cookie: str, name: str) -> str:
    token = _cookie_value(cookie, name)
    if token.count(".") < 2:
        return ""
    try:
        payload = token.split(".", 2)[1]
        payload += "=" * ((4 - len(payload) % 4) % 4)
        import base64

        data = json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8"))
        exp = int(data.get("exp") or 0)
    except Exception:
        return ""
    if exp and exp < int(time.time()):
        return datetime.fromtimestamp(exp).strftime("%Y-%m-%d %H:%M:%S")
    return ""


# 用途：
# - 使用可验证的 CA bundle 发起 HTTPS 请求，避免 Mac Python 缺失系统证书链导致 provider usage 查询失败
# 输入：
# - request: urllib Request；timeout: 请求超时时间
# 输出：
# - urllib response；调用方负责读取和关闭
def _urlopen(request: urllib.request.Request, *, timeout: int):
    context = _https_context()
    return urllib.request.urlopen(request, timeout=timeout, context=context)


# 用途：
# - 构造 HTTPS 证书校验 context，优先复用 certifi 的 CA bundle
# 输入：
# - 无
# 输出：
# - ssl.SSLContext
def _https_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore[import-not-found]

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001
        return ssl.create_default_context()


# 用途：
# - 将讯飞 CodingPlan 订阅列表聚合成统一 provider usage snapshot
# 输入：
# - model/usage_key/rows: backend 配置、缓存 key 和讯飞 coding-plan/list rows
# 输出：
# - ProviderUsageSnapshot；没有有效 usage 时返回 None
def _snapshot_from_xfyun_coding_plans(
    *,
    model: TierModel,
    usage_key: str,
    rows: list[Any],
) -> ProviderUsageSnapshot | None:
    valid_rows = [row for row in rows if isinstance(row, dict)]
    if not valid_rows:
        return None

    target_api_key = str(
        model.credentials.get("api_key")
        or _read_api_key_file(str(model.credentials.get("api_key_file") or ""))
        or ""
    ).strip()
    matched = [
        row for row in valid_rows
        if target_api_key
        and str(
            (row.get("codingPlanAppCredentialDTO") or {}).get("apiKey")
            if isinstance(row.get("codingPlanAppCredentialDTO"), dict)
            else ""
        ).strip() == target_api_key
    ]
    selected = matched or valid_rows
    totals = {
        "5hour": {"used": 0.0, "quota": 0.0},
        "weekly": {"used": 0.0, "quota": 0.0},
        "monthly": {"used": 0.0, "quota": 0.0},
    }
    for row in selected:
        usage = row.get("codingPlanUsageDTO") if isinstance(row.get("codingPlanUsageDTO"), dict) else {}
        totals["5hour"]["used"] += _float_value(usage.get("rp5hUsage"))
        totals["5hour"]["quota"] += _float_value(usage.get("rp5hLimit"))
        totals["weekly"]["used"] += _float_value(usage.get("rpwUsage"))
        totals["weekly"]["quota"] += _float_value(usage.get("rpwLimit"))

        package_limit = _float_value(usage.get("packageLimit"))
        package_usage = _float_value(usage.get("packageUsage"))
        if package_usage <= 0 and package_limit > 0:
            package_usage = max(0.0, package_limit - _float_value(usage.get("packageLeft")))
        totals["monthly"]["used"] += package_usage
        totals["monthly"]["quota"] += package_limit

    primary_name = _select_primary_usage_total(totals)
    if not primary_name:
        return None

    used = totals[primary_name]["used"]
    quota = totals[primary_name]["quota"]
    remaining = max(0.0, quota - used)
    percent = round((used / quota) * 100, 1)
    reset_at, window = derive_reset_at_from_quota(model.quota)
    reset_by_window = {
        "5hour": "",
        "weekly": reset_at if (window or "").lower() == "weekly" else "",
        "monthly": reset_at if (window or "").lower() == "monthly" else "",
    }
    return ProviderUsageSnapshot(
        provider="xfyun",
        source="provider_api",
        status="ok",
        usage_key=usage_key,
        used=used,
        quota=quota,
        remaining=remaining,
        percent=percent,
        reset_at=reset_at,
        window=primary_name,
        windows=[
            _usage_window_entry(name, values["used"], values["quota"], reset_by_window.get(name, ""))
            for name, values in totals.items()
            if values["quota"] > 0
        ],
        checked_at=now_iso(),
    )


# 用途：
# - 从多窗口 totals 中选择最适合顶层展示的窗口
# 输入：
# - totals: 5hour/weekly/monthly 的 used/quota 聚合值
# 输出：
# - primary window 名称；没有有效 quota 时返回空字符串
def _select_primary_usage_total(totals: dict[str, dict[str, float]]) -> str:
    for name in ("5hour", "weekly", "monthly"):
        values = totals.get(name) or {}
        quota = _float_value(values.get("quota"))
        used = _float_value(values.get("used"))
        if quota > 0 and used >= quota:
            return name
    for name in ("weekly", "monthly", "5hour"):
        values = totals.get(name) or {}
        if _float_value(values.get("quota")) > 0:
            return name
    return ""


# 用途：
# - 将火山 Coding Plan OpenAPI 返回转换成统一 provider usage snapshot
# 输入：
# - usage_key/result: 缓存 key 和 GetCodingPlanUsage Result 对象
# 输出：
# - ProviderUsageSnapshot；无法识别窗口时返回 None
def _snapshot_from_volc_coding_plan_result(
    *,
    usage_key: str,
    result: dict[str, Any],
) -> ProviderUsageSnapshot | None:
    return _snapshot_from_volc_quota_usage(usage_key=usage_key, result=result)


# 用途：
# - 解析火山 `GetCodingPlanUsage.QuotaUsage` 百分比窗口
# 输入：
# - usage_key/result: 缓存 key 和 OpenAPI Result 对象
# 输出：
# - ProviderUsageSnapshot；没有 QuotaUsage 时返回 None
def _snapshot_from_volc_quota_usage(
    *,
    usage_key: str,
    result: dict[str, Any],
) -> ProviderUsageSnapshot | None:
    quota_usage = result.get("QuotaUsage")
    if not isinstance(quota_usage, list):
        return None
    windows: list[dict[str, Any]] = []
    for item in quota_usage:
        if not isinstance(item, dict):
            continue
        name = _normalize_usage_window_name(str(item.get("Level") or ""))
        percent = _float_value(item.get("Percent"))
        reset_at = _reset_at_from_volc_seconds(item.get("ResetTimestamp"))
        windows.append({
            "name": name,
            "used": None,
            "quota": None,
            "remaining": None,
            "percent": round(percent, 1),
            "reset_at": reset_at,
        })
    windows = [item for item in windows if item["name"]]
    if not windows:
        return None
    primary = _select_primary_percent_window(windows)
    return ProviderUsageSnapshot(
        provider="volc",
        source="provider_api",
        status="ok",
        usage_key=usage_key,
        used=None,
        quota=None,
        remaining=None,
        percent=primary.get("percent"),
        reset_at=str(primary.get("reset_at") or ""),
        window=str(primary.get("name") or ""),
        windows=windows,
        checked_at=now_iso(),
    )


# 用途：
# - 从百分比窗口中选择顶层展示窗口
# 输入：
# - windows: provider usage window 列表
# 输出：
# - 优先返回已满窗口，否则按 weekly/monthly/5hour 选择
def _select_primary_percent_window(windows: list[dict[str, Any]]) -> dict[str, Any]:
    for item in windows:
        if _float_value(item.get("percent")) >= 100:
            return item
    by_name = {str(item.get("name") or ""): item for item in windows}
    for name in ("weekly", "monthly", "5hour"):
        if name in by_name:
            return by_name[name]
    return windows[0]


# 用途：
# - 从 MiniMax remains 列表中选择当前模型对应的用量窗口
# 输入：
# - model/remains: backend 配置和 MiniMax 返回的 model_remains
# 输出：
# - 命中的 remains item；未命中时返回 None
def _select_minimax_remains(model: TierModel, remains: list[Any]) -> dict[str, Any] | None:
    normalized_model = str(model.model_key or model.model_name or "").strip().lower()
    candidates = [item for item in remains if isinstance(item, dict)]
    if not candidates:
        return None
    for item in candidates:
        if str(item.get("model_name") or "").strip().lower() == normalized_model:
            return item
    for item in candidates:
        if str(item.get("model_name") or "").strip().lower() == "general":
            return item
    return candidates[0]


# 用途：
# - 将 MiniMax remains item 转为统一 provider usage snapshot
# 输入：
# - usage_key/item: 缓存 key 和 MiniMax remains item
# 输出：
# - ProviderUsageSnapshot
def _snapshot_from_minimax_remains(
    *,
    model: TierModel,
    usage_key: str,
    item: dict[str, Any],
) -> ProviderUsageSnapshot:
    interval_used = _float_value(item.get("current_interval_usage_count"))
    interval_quota = _float_value(item.get("current_interval_total_count"))
    weekly_used = _float_value(item.get("current_weekly_usage_count"))
    weekly_quota = _float_value(item.get("current_weekly_total_count"))
    interval_percent = _used_percent_from_minimax_remaining(item.get("current_interval_remaining_percent"))
    weekly_percent = _used_percent_from_minimax_remaining(item.get("current_weekly_remaining_percent"))
    interval_reset_at = _reset_at_from_epoch_ms(item.get("end_time"))
    weekly_reset_at = _reset_at_from_epoch_ms(item.get("weekly_end_time"))
    configured_reset_at, _configured_window = derive_reset_at_from_quota(model.quota)
    windows = [
        _usage_window_entry(
            "5hour",
            interval_used if interval_quota > 0 else None,
            interval_quota if interval_quota > 0 else None,
            interval_reset_at,
            percent=interval_percent,
        ),
        _usage_window_entry(
            "weekly",
            weekly_used if weekly_quota > 0 else None,
            weekly_quota if weekly_quota > 0 else None,
            weekly_reset_at,
            percent=weekly_percent,
        ),
    ]
    primary = _select_primary_percent_window(windows)
    window = str(primary.get("name") or item.get("model_name") or "general")
    return ProviderUsageSnapshot(
        provider="minimax",
        source="provider_api",
        status="ok",
        usage_key=usage_key,
        used=primary.get("used"),
        quota=primary.get("quota"),
        remaining=primary.get("remaining"),
        percent=primary.get("percent"),
        reset_at=str(primary.get("reset_at") or configured_reset_at),
        window=window,
        windows=windows,
        checked_at=now_iso(),
    )


# 用途：
# - 将 MiniMax remaining_percent 转成 Dashboard 使用的已用百分比
# 输入：
# - value: provider 返回的 remaining percent
# 输出：
# - 已用百分比；无法识别时返回 None
def _used_percent_from_minimax_remaining(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    remaining_percent = _float_value(value)
    if remaining_percent < 0:
        return None
    return round(max(0.0, min(100.0, 100.0 - remaining_percent)), 1)


# 用途：
# - 将 MiniMax token_plan usage_summary 响应转为统一 provider usage snapshot
# 输入：
# - model/usage_key/payload: backend 配置、缓存 key 和 MiniMax usage_summary JSON
# 输出：
# - 可展示的 usage snapshot；无法识别有效用量时返回 None
def _snapshot_from_minimax_usage_summary(
    *,
    model: TierModel,
    usage_key: str,
    payload: dict[str, Any],
) -> ProviderUsageSnapshot | None:
    total_used = _compact_number_or_none(payload.get("total_token_consumed"))
    date_model_usage = payload.get("date_model_usage") if isinstance(payload.get("date_model_usage"), list) else []
    if total_used is None:
        daily_usage = payload.get("daily_token_usage") if isinstance(payload.get("daily_token_usage"), list) else []
        if daily_usage:
            total_used = sum(_compact_number_value(item) for item in daily_usage)
    latest_daily_used = _latest_minimax_daily_total(date_model_usage)
    if total_used is None and latest_daily_used is None:
        return None

    configured_reset_at, _configured_window = derive_reset_at_from_quota(model.quota)
    windows = [
        _usage_window_entry("monthly", total_used, None, configured_reset_at),
    ]
    if latest_daily_used is not None:
        windows.append(_usage_window_entry("daily", latest_daily_used, None, ""))
    active_days = _compact_number_or_none(payload.get("active_days"))
    if active_days is not None:
        windows.append(_usage_window_entry("active_days", active_days, None, ""))
    return ProviderUsageSnapshot(
        provider="minimax",
        source="provider_api",
        status="ok",
        usage_key=usage_key,
        used=total_used,
        quota=None,
        remaining=None,
        percent=None,
        reset_at=configured_reset_at,
        window="monthly",
        windows=windows,
        checked_at=now_iso(),
    )


# 用途：
# - 从 MiniMax date_model_usage 中读取最近一天 token 总量
# 输入：
# - items: usage_summary.date_model_usage 列表
# 输出：
# - 最近一条可识别 total_token；没有时返回 None
def _latest_minimax_daily_total(items: list[Any]) -> float | None:
    for item in reversed(items):
        if not isinstance(item, dict):
            continue
        value = _compact_number_or_none(item.get("total_token"))
        if value is not None:
            return value
    return None


# 用途：
# - 从 opencode-go workspace HTML 的 SSR hydration 数据解析 provider usage
# 输入：
# - usage_key/html: 缓存 key 和 workspace HTML
# 输出：
# - ProviderUsageSnapshot；无法识别 usage 数据时返回 None
def _snapshot_from_opencode_go_workspace_html(
    *,
    usage_key: str,
    html: str,
) -> ProviderUsageSnapshot | None:
    windows_by_name: dict[str, dict[str, Any]] = {}
    pattern = re.compile(
        r"(?P<field>rollingUsage|weeklyUsage|monthlyUsage):"
        r"(?:\$R\[\d+\]=)?\{status:\"(?P<status>[^\"]+)\","
        r"resetInSec:(?P<reset>-?\d+),usagePercent:(?P<percent>-?\d+(?:\.\d+)?)\}"
    )
    for match in pattern.finditer(html):
        status = match.group("status")
        if status != "ok":
            continue
        field = match.group("field")
        name = {
            "rollingUsage": "5hour",
            "weeklyUsage": "weekly",
            "monthlyUsage": "monthly",
        }.get(field, "")
        if not name:
            continue
        windows_by_name[name] = {
            "name": name,
            "used": None,
            "quota": None,
            "remaining": None,
            "percent": round(float(match.group("percent")), 1),
            "reset_at": _reset_at_from_delta_seconds(match.group("reset")),
        }
    windows = [
        windows_by_name[name]
        for name in ("5hour", "weekly", "monthly")
        if name in windows_by_name
    ]
    if not windows:
        return None
    primary = _select_primary_percent_window(windows)
    return ProviderUsageSnapshot(
        provider="opencode-go",
        source="provider_api",
        status="ok",
        usage_key=usage_key,
        used=None,
        quota=None,
        remaining=None,
        percent=primary.get("percent"),
        reset_at=str(primary.get("reset_at") or ""),
        window=str(primary.get("name") or ""),
        windows=windows,
        checked_at=now_iso(),
    )


# 用途：
# - 解析 provider 返回的紧凑数量字符串，例如 `322.98M`
# 输入：
# - value: 数值或带 K/M/B 后缀的字符串
# 输出：
# - float 数值；无法解析时为 0
def _compact_count_value(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip().replace(",", "")
    if not text:
        return 0.0
    suffix = text[-1].upper()
    multiplier = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(suffix, 1)
    number_text = text[:-1] if suffix in {"K", "M", "B"} else text
    try:
        return float(number_text) * multiplier
    except ValueError:
        return 0.0


# 用途：
# - 将 provider 原始窗口名归一到 dashboard 展示名称
# 输入：
# - name: provider window 名称
# 输出：
# - 5hour/weekly/monthly/daily 等规范名称
def _normalize_usage_window_name(name: str) -> str:
    normalized = str(name or "").strip().lower()
    mapping = {
        "session": "5hour",
        "5h": "5hour",
        "afpfivehour": "5hour",
        "5hour": "5hour",
        "fivehour": "5hour",
        "afpweekly": "weekly",
        "week": "weekly",
        "weekly": "weekly",
        "afpmonthly": "monthly",
        "month": "monthly",
        "monthly": "monthly",
        "afpdaily": "daily",
        "daily": "daily",
    }
    return mapping.get(normalized, normalized)


# 用途：
# - 构造统一 usage window 明细
# 输入：
# - name/used/quota/reset_at/percent: 窗口名、已用额度、总额度、恢复时间、可选 provider 百分比
# 输出：
# - 可 JSON 序列化的 window 明细
def _usage_window_entry(
    name: str,
    used: float | None,
    quota: float | None,
    reset_at: str,
    *,
    percent: float | None = None,
) -> dict[str, Any]:
    normalized_name = _normalize_usage_window_name(name)
    used_value = used if used is not None else None
    quota_value = quota if quota is not None else None
    remaining = None
    percent_value = percent
    if used_value is not None and quota_value is not None and quota_value > 0:
        remaining = max(0.0, quota_value - used_value)
        if percent_value is None:
            percent_value = round((used_value / quota_value) * 100, 1)
    return {
        "name": normalized_name,
        "used": used_value,
        "quota": quota_value,
        "remaining": remaining,
        "percent": percent_value,
        "reset_at": reset_at,
    }


# 用途：
# - 将毫秒 epoch reset time 转换为 dashboard 时间字符串
# 输入：
# - value: provider 返回的毫秒时间戳
# 输出：
# - 本地时间字符串；无效时返回空字符串
def _reset_at_from_epoch_ms(value: Any) -> str:
    reset_ms = _int_value(value)
    if reset_ms <= 0:
        return ""
    return datetime.fromtimestamp(reset_ms / 1000, tz=UTC).astimezone().strftime("%Y-%m-%d %H:%M")


# 用途：
# - 将火山秒级 reset timestamp 转换为 dashboard 时间字符串
# 输入：
# - value: provider 返回的秒级时间戳
# 输出：
# - 本地时间字符串；无效时返回空字符串
def _reset_at_from_volc_seconds(value: Any) -> str:
    reset_seconds = _int_value(value)
    if reset_seconds <= 0:
        return ""
    return datetime.fromtimestamp(reset_seconds, tz=UTC).astimezone().strftime("%Y-%m-%d %H:%M")


# 用途：
# - 将 provider 返回的相对 reset 秒数转换为 dashboard 时间字符串
# 输入：
# - value: 距离 reset 的秒数
# 输出：
# - 本地时间字符串；无效时返回空字符串
def _reset_at_from_delta_seconds(value: Any) -> str:
    seconds = _int_value(value)
    if seconds <= 0:
        return ""
    return (datetime.now(UTC) + timedelta(seconds=seconds)).astimezone().strftime("%Y-%m-%d %H:%M")


# 用途：
# - 调用火山 OpenAPI 并执行 HMAC-SHA256 签名
# 输入：
# - action/access_key/secret_key: OpenAPI Action 与 AK/SK
# 输出：
# - JSON 响应字典
def _volc_signed_json_request(
    *,
    action: str,
    access_key: str,
    secret_key: str,
) -> dict[str, Any]:
    body = b"{}"
    now = datetime.now(UTC)
    x_date = now.strftime("%Y%m%dT%H%M%SZ")
    short_date = now.strftime("%Y%m%d")
    query = f"Action={action}&Version={VOLC_USAGE_VERSION}"
    payload_hash = hashlib.sha256(body).hexdigest()
    signed_headers = "host;x-content-sha256;x-date"
    canonical_headers = (
        f"host:{VOLC_USAGE_HOST}\n"
        f"x-content-sha256:{payload_hash}\n"
        f"x-date:{x_date}\n"
    )
    canonical_request = "\n".join([
        "POST",
        "/",
        query,
        canonical_headers,
        signed_headers,
        payload_hash,
    ])
    credential_scope = f"{short_date}/{VOLC_REGION}/{VOLC_SERVICE}/request"
    string_to_sign = "\n".join([
        "HMAC-SHA256",
        x_date,
        credential_scope,
        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
    ])
    signing_key = _volc_signing_key(secret_key, short_date)
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = (
        f"HMAC-SHA256 Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    request = urllib.request.Request(
        f"https://{VOLC_USAGE_HOST}/?{query}",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=UTF-8",
            "Host": VOLC_USAGE_HOST,
            "X-Date": x_date,
            "X-Content-Sha256": payload_hash,
            "Authorization": authorization,
        },
    )
    try:
        with _urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"volc_usage_http_{exc.code}:{text[:160]}") from exc


# 用途：
# - 生成火山 HMAC 签名 key
# 输入：
# - secret_key/date: 火山 SK 与 YYYYMMDD 日期
# 输出：
# - signing key bytes
def _volc_signing_key(secret_key: str, date: str) -> bytes:
    k_date = hmac.new(secret_key.encode("utf-8"), date.encode("utf-8"), hashlib.sha256).digest()
    k_region = hmac.new(k_date, VOLC_REGION.encode("utf-8"), hashlib.sha256).digest()
    k_service = hmac.new(k_region, VOLC_SERVICE.encode("utf-8"), hashlib.sha256).digest()
    return hmac.new(k_service, b"request", hashlib.sha256).digest()


# 用途：
# - 安全读取 float
# 输入：
# - value: 任意 provider 数字字段
# 输出：
# - float；无法转换时返回 0.0
def _float_value(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


# 用途：
# - 安全读取可选 float，保留缺失和非法字段
# 输入：
# - value: 任意 provider 数字字段
# 输出：
# - float；缺失或无法转换时返回 None
def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# 用途：
# - 安全读取 MiniMax 紧凑数字，缺失或非法时保留 None
# 输入：
# - value: 数字或 `1.26B`、`5.96M`、`120K` 形式的 provider 字段
# 输出：
# - float；缺失或无法转换时返回 None
def _compact_number_or_none(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return _compact_number_value(value)
    except ValueError:
        return None


# 用途：
# - 将 provider 紧凑数字转换为基础数值
# 输入：
# - value: 数字或带 K/M/B/T 后缀的字符串
# 输出：
# - float；无法转换时抛出 ValueError
def _compact_number_value(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    raw = str(value).strip().replace(",", "")
    if not raw:
        raise ValueError("empty compact number")
    multiplier = 1.0
    suffix = raw[-1:].upper()
    if suffix in {"K", "M", "B", "T"}:
        raw = raw[:-1]
        multiplier = {"K": 1_000.0, "M": 1_000_000.0, "B": 1_000_000_000.0, "T": 1_000_000_000_000.0}[suffix]
    return float(raw) * multiplier


# 用途：
# - 安全读取 int
# 输入：
# - value: 任意 provider 数字字段
# 输出：
# - int；无法转换时返回 0
def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
