# ADM-LOGS-01 — 脱敏日志

- **Case ID**：`ADM-LOGS-01`（与 §3.2 权威清单一致；本文件名 `adm-logs-01.md`，唯一对应）。
- **标题**：`GET /v1/logs?from&to` 返回脱敏的运行日志：HTTP 200 + `LogPage`，且上游 secret `9832` 不出现。
- **目的（被测契约）**：验证运行日志读取的**脱敏契约**（`T-TRUST-LEAK`）。被测端点/规则：`GET /v1/logs`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listLogs`，query `from`/`to` **必填**、`level`/`module`/`request_id` 可选，`security=AdminBearerAuth`）；[`OperationalLog.page`](../../../../src/log/logs.py) 以 `created_at>=? AND created_at<?`（**半开**）返回 `{data:[LogEntry],page}`；写入侧 [`OperationalLog.record`](../../../../src/log/logs.py) 用 `_SENSITIVE` 正则把 `authorization`/`bearer …`/`secret`/`api_key`/`token=…` 替换为 `[REDACTED]` 并截断 512。设计验证项 `VRC-LOG-001`；机制 `T-TRUST-LEAK`；需求/机制链 `LT-FUN-006`、`LT-SEC-004`、`R-OBS-01`、`CT-LOG-001`。**不证明什么**：不证明缺时间窗 400（ADM-LOGS-02）、不证明审计脱敏（ADM-AUDIT-01）、不证明 `level`/`module` 过滤（未单独构 case）、不证明日志完整性/保留策略。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 **6** 项就绪检查，由 [`conftest.py`](../../../../tests/system/api_test_v03/conftest.py) `pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`admin_client`。时间窗用动态 [`recent_window()`](../../../../tests/system/api_test_v03/constants.py)；初始状态：m5air `operational_logs` 非空（HTTP/管理请求已写日志）。只读。
- **输入与构造**：
  ```http
  GET /v1/logs?from=<recent_window.from>&to=<recent_window.to> HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`from`/`to` 取动态近窗（保证非空）；不传 `level`/`module`/`request_id`；不注入故障。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `since, until = recent_window()`；`resp = admin_client.get("/v1/logs", params={"from": since, "to": until})`；记录 status、body 原文。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 body：断言含 `data`（数组，且**非空**——窗内应至少有本 suite 产生的日志）与 `page`；`page` 键集恰 `{has_more,next_cursor}`。
  5. 抽查每条 `LogEntry` 键集恰 `{id,created_at,level,module,event,message,request_id}`；`level∈{info,warning,error}`；`len(message)≤512`。
  6. **脱敏断言（强制）**：对整段 `resp.text` 及每条 `message`/`module`，断言 **不含上游 secret 字面 `"9832"`**、key 文件名 `"omlx-secret-key.txt"`、`"mnm_api_key"`。
- **重点关注步骤**：① **`9832` 必须缺失**（规格明示）——`GET /v1/logs` 响应整体与 `message` 字段都不得出现 `9832`；`_SENSITIVE` 正则并不覆盖裸数字 secret，故这是**实质性**断言而非形式；② **窗内非空**——空 `data` 不能证明脱敏（无内容可审）；须至少有一条日志（本 suite 的 HTTP 请求即产生），否则构造失败（BLOCKED/复核窗口）；③ **半开窗**——`>=from AND <to`；④ **字段完整**——`LogEntry` 7 键、`message≤512`、`level` enum；⑤ **纯读**——`GET /v1/logs` 不写日志；⑥ **与 ADM-AUDIT-01 区分**——本 case 面向 `operational_logs`，非 `audit_events`。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `LogPage`/`LogEntry` + `T-TRUST-LEAK` 脱敏规则。
  - HTTP：`200`；body `{"data":[...非空...],"page":{...}}`。
  - `LogEntry` 7 键齐全；`message≤512`；`level∈{info,warning,error}`。
  - 响应文本与 `message`/`module` 不含 `9832`/`omlx-secret-key.txt`/`mnm_api_key`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + `data` 非空数组 + `LogEntry` 键集正确 + **不含 `9832`** 及其它敏感字面。
  - **FAIL**：status 非 200、`data` 空/非数组、字段缺失、或出现 `9832`/敏感字面。
  - **BLOCKED**：fixture/断言逻辑问题、或窗内确无日志且无法构造（记录并复核窗口）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存请求 URL（含 from/to）、原始 HTTP status/body（**入库前脱敏 Authorization、`9832`、key 文件内容**）、发出命令、exit code、`elapsed`、环境快照。`manifest.json` 必含 `{…,environment:"a",inputs(时间窗),oracle,actual,verdict,evidence_files,redactions,reproduction_cmd}`，`redactions` 明列 `Authorization`/`9832`/key 文件。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`；失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——纯读，不改日志/配置/注入。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`constants.recent_window`；`LogPage`/`LogEntry` 机器契约；`OperationalLog.page`/`_SENSITIVE`；机制 `T-TRUST-LEAK`。自动化入口 [`at_adm_logs_01.py`](../../../../tests/system/api_test_v03/at_adm_logs_01.py)。**不依赖**其它 Case；与 ADM-LOGS-02、ADM-AUDIT-01 互补。
