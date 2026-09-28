# ADM-AUDIT-03 — 审计非法分页参数

- **Case ID**：`ADM-AUDIT-03`（与 §3.2 权威清单一致；本文件名 `adm-audit-03.md`，唯一对应）。
- **标题**：`GET /v1/audit?limit=abc` 非法分页参数：HTTP 400 `invalid_request`。
- **目的（被测契约）**：验证审计 `limit` 的**整数参数校验**。被测端点/规则：`GET /v1/audit`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listAudit`，query `limit` `type:integer`）；[`app.py`](../../../../src/http_api/app.py) `app.audit.page(_int_param(query, "limit", 50))`，[`_int_param`](../../../../src/http_api/app.py) 对无法 `int()` 的输入 `raise ApiError(400, "invalid_request", "limit must be an integer")`（在 admin 鉴权后、handler 前）。设计验证项 `VRC-MGMT-003`；错误目录 `ERR-REQ-VALIDATION` → wire `code=invalid_request`；机制 `R-OBS-01`；需求/机制链 `LT-FUN-006`、`R-OBS-01`、`CT-ADMIN-001`。**不证明什么**：不证明默认 50/边界 `limit=1`（ADM-AUDIT-01/02）、不证明字段脱敏（ADM-AUDIT-01）、不证明角色负向（`/v1/audit` 为 admin 守门，data 凭据的 403 属 AUTH-03/09 的跨切面角色覆盖，**不是本 case**）、不证明 `cursor`（审计无 cursor）。
  > **规格注记**：§3.2 将 `ADM-AUDIT-03` 登记为"审计非法分页参数 → 400 `invalid_request`"，§11.1 亦将 `ERR-REQ-VALIDATION` 映射到本 Case。`ADM-RUNTIME-02` 才是 `data→403` 的角色负向。运行时若以 data 凭据访问 `/v1/audit`，会在 `_int_param` 之前被 admin 守门以 403 拒绝——本 case 不构造该路径。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。就绪检查同[测试设计 §2.1](../llmtier-api-test-specification.md)（**6** 项，`pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP）。fixture：`admin_client`（[§4.4](../llmtier-api-test-specification.md)）。初始状态 = m5air 基线；本 case 为 **MISSING**（§3.2 无 `at_adm_audit_03.py`），设计已写、实现待补。拒绝路径无副作用。
- **输入与构造**：
  ```http
  GET /v1/audit?limit=abc HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`limit=abc` 为非整数（`int("abc")` 抛 `ValueError`）；凭据为 admin（使失败点确为参数解析而非 403）；不注入故障。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/audit", params={"limit": "abc"})`。
  3. 断言 `resp.status_code == 400`；`err = resp.json()["error"]`：断言 `err["code"]=="invalid_request"`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  4. （边界变体，可选）`limit=`（空串）与 `limit=1.5` 各断言 400 `invalid_request`。
  5. （对照，非本 case 判定）`GET /v1/audit?limit=1` 断言 200（证明 400 来自参数值而非端点/鉴权）。
- **重点关注步骤**：① **非整数必须 400**——不得静默回退默认 50 或返回 200 空页；② **校验位置**——`_int_param` 在 admin 鉴权之后、`app.audit.page` 之前抛错，不触库、无副作用；③ **错误信封 identity**——恰 5 键、`type=request_error`、`code=invalid_request`；④ **param 语义**——`_int_param` 未传 `param`，故 `param==null`；⑤ **区分缺参**——`limit` 缺省是合法默认（50），本 case 锁"有值但非法"，二者不同；⑥ **非角色负向**——本 case 不是 data→403（见目的注记）。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + `limit` integer 类型规则。
  - HTTP：`400`；body `{"error":{"message":"limit must be an integer","type":"request_error","code":"invalid_request","param":null,"retryable":false}}`。
  - 无审计/配置副作用。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`400` + `code=="invalid_request"` + `type=="request_error"`（含可选变体）。
  - **FAIL**：status 非 400（含 200 静默回退）、`code` 错、或返回审计数据。
  - **BLOCKED**：fixture/断言逻辑问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 自动化入口 **`MISSING`**（§3.2），本轮未执行；缺口引用 §3.2/§9（MISSING ≠ NOT_RUN）。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air——见[测试设计 §9](../llmtier-api-test-specification.md)。
- **证据与 Run**：保存请求 URL（含非法 `limit`）、原始 400 响应（脱敏后）、`limit=1` 对照响应、发出命令、exit code、`elapsed`、环境快照。`manifest.json` 必含 `{…,environment:"a",inputs,oracle,actual,verdict,evidence_files,redactions,reproduction_cmd}`。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`；失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——拒绝路径无状态变更。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`app.py::_int_param`；错误目录 `ERR-REQ-VALIDATION`。自动化入口 **`MISSING`**（待补 `at_adm_audit_03.py`，落位按 §4.9/§8.5）。**不依赖**其它 Case；与 ADM-AUDIT-01/02（成功/边界读）互补。
