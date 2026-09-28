# ADM-LOGS-02 — 缺时间窗

- **Case ID**：`ADM-LOGS-02`（与 §3.2 权威清单一致；本文件名 `adm-logs-02.md`，唯一对应）。
- **标题**：`GET /v1/logs` 缺 `from`/`to`：HTTP 400 `invalid_request`。
- **目的（被测契约）**：验证运行日志查询的**必填时间窗校验**。被测端点/规则：`GET /v1/logs`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listLogs`，`from`/`to` 均 `required:true`）；[`app.py`](../../../../src/http_api/app.py) `since, until = query.get("from"), query.get("to"); if not since or not until: raise ApiError(400, "invalid_request", "from and to are required")`（admin 鉴权后、`app.logs.page` 前）；[`OperationalLog.page`](../../../../src/log/logs.py) 自身也有 `if not since or not until: raise` 双重校验。设计验证项 `VRC-LOG-001`；错误目录 `ERR-REQ-VALIDATION` → wire `code=invalid_request`；机制 `R-OBS-01`；需求/机制链 `LT-FUN-006`、`LT-SEC-004`、`CT-LOG-001`。**不证明什么**：不证明成功日志读与脱敏（ADM-LOGS-01）、不证明 stats 的同类缺窗（ADM-STATS-03）、不证明非法 `limit`（logs 的 `limit` 由 `_int_param` 校验，未单独构 case）、不证明角色负向（AUTH 家族）。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。就绪检查同[测试设计 §2.1](../llmtier-api-test-specification.md)（**6** 项，`pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP）。fixture：`admin_client`（[§4.4](../llmtier-api-test-specification.md)）。初始状态 = m5air 基线；拒绝路径无副作用。
- **输入与构造**：
  ```http
  GET /v1/logs HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：**不带 `from`/`to`**（可另构造只带其一的两个变体，均期望 400）；不注入故障。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/logs")`。
  3. 断言 `resp.status_code == 400`；`err = resp.json()["error"]`：断言 `err["code"]=="invalid_request"`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  4. （边界变体，可选）`GET /v1/logs?from=<since>`（缺 `to`）与 `GET /v1/logs?to=<until>`（缺 `from`）各断言 400 `invalid_request`。
- **重点关注步骤**：① **必填两参数**——`from`/`to` 缺任一必须 400，不得返回 200 空 `data`；② **校验位置**——`app.py` 在 admin 鉴权后、`logs.page` 前抛错，不触库、无副作用（`OperationalLog.page` 的同类 `raise` 为第二道防线）；③ **错误信封 identity**——恰 5 键、`type=request_error`、`code=invalid_request`；④ **param 语义**——该 `raise` 未传 `param`，故 `param==null`；⑤ **不把 400 当 200 空页**——`usage_store_unavailable`/空 `data` 不属本 case（`/v1/logs` 无 store 不可用分支）。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + `from`/`to` required 规则。
  - HTTP：`400`；body `{"error":{"message":"from and to are required","type":"request_error","code":"invalid_request","param":null,"retryable":false}}`。
  - 无日志/配置副作用。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`400` + `code=="invalid_request"` + `type=="request_error"`（三种缺参变体均如此）。
  - **FAIL**：status 非 400（含 200）、`code` 错、或返回日志数据。
  - **BLOCKED**：fixture/断言逻辑问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存请求 URL/headers、原始 400 响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照。`manifest.json` 必含 `{…,environment:"a",inputs,oracle,actual,verdict,evidence_files,redactions,reproduction_cmd}`。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`；失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——拒绝路径无状态变更。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`app.py`/`OperationalLog.page` 的 `from`/`to` 必填校验；错误目录 `ERR-REQ-VALIDATION`。自动化入口 [`at_adm_logs_02.py`](../../../../tests/system/api_test_v03/at_adm_logs_02.py)。**不依赖**其它 Case；与 ADM-LOGS-01 的成功路径互补。
