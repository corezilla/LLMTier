from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any, Callable

from stats_collector import StatsCollector
from tier_model import TierStatsQuery


StatsEventFormatter = Callable[[dict[str, Any]], dict[str, Any]]


# 用途：
# - 将 HTTP query params 转换为统一 LLM stats 查询对象
# 输入：
# - params: BaseHTTPRequestHandler 解析出的 query 参数字典
# - default_limit: 未显式传 limit 时使用的最大事件数
# 输出：
# - TierStatsQuery
def llm_stats_query_from_http_params(
    params: dict[str, list[str]] | None,
    *,
    default_limit: int = 9999,
) -> TierStatsQuery:
    query = TierStatsQuery(limit=default_limit)
    if not params:
        return query
    query.limit = _int_param(params=params, name="limit", default=default_limit)
    query.project_name = _text_param(params=params, name="project")
    query.stage_name = _text_param(params=params, name="stage")
    query.phase_name = _text_param(params=params, name="phase")
    query.task_id = _text_param(params=params, name="task_id")
    query.task_id_prefix = _text_param(params=params, name="task_id_prefix")
    query.task_key = _text_param(params=params, name="task_key")
    query.tier = _text_param(params=params, name="tier")
    query.backend = _text_param(params=params, name="backend")
    query.role_name = _text_param(params=params, name="role")
    query.group_by = _text_param(params=params, name="group_by")
    query.include_events = _bool_param(params=params, name="include_events", default=True)
    query.started_at_text = _text_param(params=params, name="started_at")
    query.started_at_epoch = _time_param(params=params, name="started_at")
    query.task_started_at_epochs = _task_started_at_epochs_param(params=params, name="task_started_at_map")
    query.task_started_at_texts = _task_started_at_texts_param(params=params, name="task_started_at_map")
    query.time_range_hours = _int_param(params=params, name="time_range_hours", default=0)
    return query


# 用途：
# - 从统一 LLM stats SQLite store 构造 HTTP 可返回的 stats payload
# 输入：
# - collector/query/event_formatter: stats store、查询条件和可选事件响应格式化函数
# 输出：
# - 包含 summary、rows、events 的 JSON 可序列化字典
def build_llm_stats_payload(
    *,
    collector: StatsCollector,
    query: TierStatsQuery,
    event_formatter: StatsEventFormatter | None = None,
) -> dict[str, Any]:
    formatter = event_formatter or _identity_event_formatter
    normalized_group = str(query.group_by or "").strip().lower()
    if normalized_group and normalized_group != "raw":
        groups = collector.get_grouped_stats(query, group_by=query.group_by)
        return {
            "summary": _summary_from_groups(groups),
            "rows": [],
            "groups": groups,
            "events": [],
        }
    payload = {
        "summary": collector.get_summary(query),
        "rows": [row.__dict__ for row in collector.get_stats(query)],
    }
    payload["events"] = [formatter(event) for event in collector.get_events(query)] if query.include_events else []
    return payload


# 用途：
# - 从后端聚合 groups 构造轻量 summary，避免 group 查询额外扫描 events
# 输入：
# - groups: StatsCollector 已聚合的 group rows
# 输出：
# - total_calls、total_tokens、fallback 与 active_backends 摘要
def _summary_from_groups(groups: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total_calls": sum(int(row.get("calls") or 0) for row in groups),
        "total_tokens": sum(int(row.get("total_tokens") or 0) for row in groups),
        "total_fallback_count": sum(int(row.get("fallback_count") or 0) for row in groups),
        "active_backends": sorted({str(row.get("backend") or "") for row in groups if str(row.get("backend") or "")}),
    }


# 用途：
# - 构造与现有 `/stats` HTTP response 兼容的完整响应
# 输入：
# - collector/query/event_formatter: stats store、查询条件和可选事件响应格式化函数
# 输出：
# - `{ok, stats}` 结构的 JSON 可序列化字典
def build_llm_stats_http_response(
    *,
    collector: StatsCollector,
    query: TierStatsQuery,
    event_formatter: StatsEventFormatter | None = None,
) -> dict[str, Any]:
    return {
        "ok": True,
        "stats": build_llm_stats_payload(
            collector=collector,
            query=query,
            event_formatter=event_formatter,
        ),
    }


# 用途：
# - 从 HTTP query params 中读取单个文本参数
# 输入：
# - params/name: 参数字典和字段名
# 输出：
# - 去空白后的参数值；缺失时为空字符串
def _text_param(*, params: dict[str, list[str]], name: str) -> str:
    values = params.get(name) or []
    if not values:
        return ""
    return str(values[0] or "").strip()


# 用途：
# - 从 HTTP query params 中读取单个整数参数
# 输入：
# - params/name/default: 参数字典、字段名和默认值
# 输出：
# - 解析后的整数；解析失败时返回默认值
def _int_param(*, params: dict[str, list[str]], name: str, default: int) -> int:
    text = _text_param(params=params, name=name)
    if not text:
        return default
    try:
        return int(text)
    except ValueError:
        return default


# 用途：
# - 从 HTTP query params 中读取单个布尔参数
# 输入：
# - params/name/default: 参数字典、字段名和默认值
# 输出：
# - 解析后的布尔值
def _bool_param(*, params: dict[str, list[str]], name: str, default: bool) -> bool:
    text = _text_param(params=params, name=name).lower()
    if not text:
        return default
    return text in {"1", "true", "yes", "on"}


# 用途：
# - 从 HTTP query params 中读取 ISO 或 epoch 时间参数
# 输入：
# - params/name: 参数字典和字段名
# 输出：
# - 秒级 epoch；缺失或解析失败时为 0
def _time_param(*, params: dict[str, list[str]], name: str) -> float:
    text = _text_param(params=params, name=name)
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        pass
    normalized = text.replace("Z", "")
    try:
        return float(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp())
    except ValueError:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%y-%m-%d %H:%M:%S"):
        try:
            return float(time.mktime(time.strptime(normalized.split("+")[0], fmt)))
        except ValueError:
            continue
    return 0.0


# 用途：
# - 从 HTTP query params 读取 task_id 到 started_at epoch 的映射
# 输入：
# - params/name: 参数字典和字段名；字段值为 JSON object
# 输出：
# - task_id -> epoch 秒；非法项会被忽略
def _task_started_at_epochs_param(*, params: dict[str, list[str]], name: str) -> dict[str, float]:
    text = _text_param(params=params, name=name)
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    result: dict[str, float] = {}
    for task_id, started_at in payload.items():
        normalized_task_id = str(task_id or "").strip()
        if not normalized_task_id:
            continue
        epoch = _parse_time_value(started_at)
        if epoch > 0:
            result[normalized_task_id] = epoch
    return result


# 用途：
# - 从 HTTP query params 保留 task_id 到 started_at 原始文本的映射
# 输入：
# - params/name: 参数字典和字段名；字段值为 JSON object
# 输出：
# - task_id -> started_at 原始文本；非法项会被忽略
def _task_started_at_texts_param(*, params: dict[str, list[str]], name: str) -> dict[str, str]:
    text = _text_param(params=params, name=name)
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    result: dict[str, str] = {}
    for task_id, started_at in payload.items():
        normalized_task_id = str(task_id or "").strip()
        normalized_started_at = str(started_at or "").strip()
        if normalized_task_id and normalized_started_at:
            result[normalized_task_id] = normalized_started_at
    return result


# 用途：
# - 把任意 started_at 值解析为 epoch 秒
# 输入：
# - value: ISO 字符串、epoch 数字或空值
# 输出：
# - epoch 秒；解析失败返回 0
def _parse_time_value(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        pass
    normalized = str(value or "").strip()
    if not normalized:
        return 0.0
    try:
        return float(datetime.fromisoformat(normalized.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return 0.0


# 用途：
# - 默认保持 stats event 原样返回
# 输入：
# - event: SQLite stats event
# 输出：
# - 原 event 字典副本
def _identity_event_formatter(event: dict[str, Any]) -> dict[str, Any]:
    return dict(event)
