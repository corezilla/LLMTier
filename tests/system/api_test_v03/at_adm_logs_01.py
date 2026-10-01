"""Case ID: ST-LOGS-001

Endpoint: GET /v1/logs?from=...&to=...
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言（doc §4/§5）：
- HTTP 200，Content-Type 含 application/json
- data 非空数组；page 键集恰 {has_more,next_cursor}
- 每条 LogEntry 键集恰 {id,created_at,level,module,event,message,request_id}
- level ∈ {info,warning,error}；len(message) ≤ 512
- **全 resp.text 扫描**：不含上游 secret 字面 "9832"、key 文件名
  "omlx-secret-key.txt"、"mnm_api_key"

脱敏（RISK-LOG-1 已关闭）：`_SENSITIVE` 现在同时消费键名后的值
（`api_key=`/`apikey=`/`secret`/`access_key[_id]`/`token` + `[:=]`），故 `api_key=x`
整段 → `[REDACTED]`；log-design §15.1 / log.isd §10.3.1 状态已更新为 Closed。
"""
from __future__ import annotations

import re

import pytest

from tests.system.api_test_v03.constants import recent_window

LOG_ENTRY_KEYS = {"id", "created_at", "level", "module", "event", "message", "request_id"}
LEVEL_ENUM = {"info", "warning", "error"}
FORBIDDEN = ("omlx-secret-key.txt", "mnm_api_key")


@pytest.mark.api_a
def test_adm_logs_01_list_no_secret_leak(admin_client):
    since, until = recent_window()
    resp = admin_client.get("/v1/logs", params={"from": since, "to": until})
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    assert "application/json" in resp.headers.get("Content-Type", ""), (
        f"Content-Type 非 JSON: {resp.headers.get('Content-Type')!r}")

    body = resp.json()
    data = body.get("data")
    assert isinstance(data, list), f"data 非数组: {type(data)}"
    assert data, f"时间窗内无任何日志记录（脱敏无内容可审，构造失败）: {body}"

    page = body.get("page")
    assert isinstance(page, dict), f"缺 page 对象: {list(body.keys())}"
    assert set(page) == {"has_more", "next_cursor"}, f"page 键集不符: {set(page)}"

    for entry in data:
        assert set(entry) == LOG_ENTRY_KEYS, (
            f"LogEntry 键集不符: {set(entry)} != {LOG_ENTRY_KEYS}")
        assert entry["level"] in LEVEL_ENUM, f"level 非白名单: {entry['level']!r}"
        assert isinstance(entry["message"], str), f"message 非字符串: {entry['message']!r}"
        assert len(entry["message"]) <= 512, (
            f"message 超长 {len(entry['message'])} > 512")

    # 强制脱敏断言：扫描整段 resp.text（不止 message/module，覆盖 event/未来字段）。
    # "9832" 为 4 位 token，可能偶然出现在随机 request-id 的十六进制串 / RFC3339 时间戳
    # / 计数器数值中，故要求其为独立的字母数字 token（前后不邻接 [0-9A-Za-z]）——既可
    # 捕获 `Bearer 9832` / `"api_key":"9832"` 式真实泄露，又不被含字母的十六进制 ID 或
    # 数值（如 9832.5）误报。仅用数字边界不够：hex id `ab9832cd` 的下一字符是字母。
    assert not re.search(r"(?<![0-9A-Za-z])9832(?![0-9A-Za-z])", resp.text), (
        "logs 响应整体含敏感 token 字面 '9832'（敏感信息泄露）"
    )
    for s in FORBIDDEN:
        assert s not in resp.text, f"logs 响应整体含敏感字面 '{s}'（敏感信息泄露）"
