# ADM-STATS-03 — 缺时间窗

- **Case ID**：`ADM-STATS-03`（与 §3.2 权威清单一致；本文件名 `adm-stats-03.md`，唯一对应）。
- **标题**：`GET /v1/stats` 缺 `from`/`to`：HTTP 400 `invalid_request`。
- **目的（被测契约）**：验证统计查询的**必填时间窗校验**。被测端点/规则：`GET /v1/stats`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getStats`，`from`/`to` 均 `required:true`）；[`app.py`](../../../../src/http_api/app.py) `since, until = query.get("from"), query.get("to"); if not since or not until: raise ApiError(400, "invalid_request", "from and to are required")`（在鉴权后、handler 前）。设计验证项 `VRC-MGMT-006`；错误目录 `ERR-REQ-VALIDATION` → wire `code=invalid_request`；需求/机制链 `LT-FUN-006`、`R-MET-03`、`CT-USAGE-001`。**不证明什么**：不证明缺窗时的 usage/logs 同类校验（ADM-USAGE-* 无缺窗 case、ADM-LOGS-02）、不证明非法 `group_by` 400（未单独构 case）、不证明成功聚合（ADM-STATS-01/02）、不证明认证负向（AUTH-03/09）。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。就绪检查同[测试设计 §2.1](../llmtier-api-test-specification.md)（**6** 项，`pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP）。fixture：`admin_client`（[§4.4](../llmtier-api-test-specification.md)）。初始状态 = m5air 基线；拒绝路径无副作用。
- **输入与构造**：
  ```http
  GET /v1/stats HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：**不带 `from`/`to`**（也可构造只带其一的两种变体，均期望同一 400）；不注入故障。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/stats")`。
  3. 断言 `resp.status_code == 400`；`err = resp.json()["error"]`：断言 `err["code"]=="invalid_request"`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  4. （边界变体，可选）`GET /v1/stats?from=<since>`（缺 `to`）与 `GET /v1/stats?to=<until>`（缺 `from`）各断言 400 `invalid_request`。
- **重点关注步骤**：① **必填两参数**——`from`/`to` 缺任一都必须 400，不是空窗聚合（不得返回 200 `{data:[]}` 冒充）；② **校验位置**——`app.py` 在带 admin 凭据分派后、调用 `AdminService.stats` 前抛错，不触库、无副作用；③ **错误信封 identity**——恰 5 键、`type=request_error`、`code=invalid_request`；④ **param 语义**——该 `raise` 未传 `param`，故 `param==null`；⑤ **不把 400 当 200 空页**——`usage_store_unavailable`/空 `data` 不属本 case。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + `from`/`to` required 规则。
  - HTTP：`400`；body `{"error":{"message":"from and to are required","type":"request_error","code":"invalid_request","param":null,"retryable":false}}`。
  - 无账本/配置副作用。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`400` + `code=="invalid_request"` + `type=="request_error"`（三种缺参变体均如此）。
  - **FAIL**：status 非 400（含 200）、`code` 错、或返回空聚合。
  - **BLOCKED**：fixture/断言逻辑问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存请求 URL/headers、原始 400 响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照。`manifest.json` 必含 `{…,environment:"a",inputs,oracle,actual,verdict,evidence_files,redactions,reproduction_cmd}`。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`；失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——拒绝路径无状态变更。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`app.py` 的 `from`/`to` 必填校验；错误目录 `ERR-REQ-VALIDATION`。自动化入口 [`at_adm_stats_03.py`](../../../../tests/system/api_test_v03/at_adm_stats_03.py)。**不依赖**其它 Case；与 ADM-STATS-01/02 的成功路径互补。
