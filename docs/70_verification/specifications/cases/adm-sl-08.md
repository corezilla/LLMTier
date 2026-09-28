# ADM-SL-08 — 内部错误信封（非数组输入）

- **Case ID**：`ADM-SL-08`（与 §3.2 权威清单一致；本文件名 `adm-sl-08.md`，唯一对应）。
- **标题**：`PATCH /v1/service-levels/{id}` 用非数组 `deployment_ids`：HTTP 500 `internal_error` 信封（无栈/无 secret）；同时登记"非法类型未预校验"缺陷。
- **目的（被测契约）**：验证统一**服务器错误信封**在兜底 500 路径上的契约，并**登记**输入类型校验缺陷。被测端点/规则：`PATCH /v1/service-levels/{service_level_id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `updateServiceLevel`，`ServiceLevelPatch.deployment_ids` 类型应为 `array`）；[`registry.update_service_level`](../../../../src/management/registry.py) 只做键集校验（`set(body) <= {"deployment_ids","enabled"}`）**不做类型校验**，把 `deployment_ids` 直接交给 `_capability_intersection` 迭代；当其为非可迭代 JSON 类型（如整数）时抛 `TypeError`，被 [`app.py`](../../../../src/http_api/app.py) 的兜底 `except Exception` 转为 `ApiError(500, "internal_error", "Internal server error")`（`errors.py::ApiError.envelope` 5 键）。设计验证项 `VRC-MGMT-002`；错误目录 `ERR-INTERNAL` → wire `code=internal_error`；机制 `R-CFG-01`；需求/机制链 `LT-FUN-005`、`CT-ADMIN-001`。**不证明什么**：不证明合法 PATCH（ADM-SL-04）、不证明键白名单 400（ADM-SL-04b）、不证明能力/向量空间冲突 409（ADM-SL-06/07）、不证明审计/日志（ADM-AUDIT-01/ADM-LOGS-01）。本 case **不把 500 当正确行为**——它验证信封契约并登记缺陷。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）。执行前须满足[测试设计 §2.1](../llmtier-api-test-specification.md) **附加（B 类）**（`/healthz` 200；`_BASELINE_SETTINGS`）。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`admin_client_b`。本 case 为 **MISSING**（§3.2 无 `at_adm_sl_08.py`），设计已写、实现待补。初始状态：`Worker` 存在。
- **输入与构造**：
  ```http
  PATCH /v1/service-levels/Worker HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  If-Match: "<从 GET 读取的真实 ETag>"
  Content-Type: application/json
  ```
  ```json
  {"deployment_ids": 1}
  ```
  构造点：`deployment_ids` 为 JSON **number**（非 array；非可迭代 → 触发 `TypeError`）；`If-Match` 取真实 ETag（使失败点落在类型处理而非 412）；body 键集仍 ⊆ 白名单（否则被 400 拦，无法到达 500 路径）。
  > **类型选择**：须用**非可迭代** JSON 类型（整数/布尔/null）才能命中 500。字符串会逐字符迭代并被当作未知 deployment 引用而返回 400 `invalid_request`、对象会迭代键同理——均**不**满足本 case 的 500 断言。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `get = admin_client_b.get("/v1/service-levels/Worker")`；断言 200；记 `etag`、`version_before`。
  3. `resp = admin_client_b.patch("/v1/service-levels/Worker", json={"deployment_ids": 1}, headers={"If-Match": etag})`。
  4. 断言 `resp.status_code == 500`；`err = resp.json()["error"]`：断言键集**恰为** `{message,type,code,param,retryable}`（无 `category`）、`err["code"]=="internal_error"`、`err["type"]=="server_error"`、`err["retryable"] is False`。
  5. 断言响应体**不含** Python traceback（`Traceback`/`File "`）、`TypeError`、`'int' object`、secret 字面 `9832`、`omlx-secret-key.txt`（脱敏校验）。
  6. （零副作用核验）`GET /v1/service-levels/Worker` 断言 `version==version_before`（异常在 `txn` 内抛出、事务回滚）。
  7. （缺陷登记）在 Run 报告写出缺陷记录：`deployment_ids` 缺失 JSON 类型预校验，非法类型未返回 400 `invalid_request` 而泄漏为 500 `internal_error`；`reproduction_cmd` 指向本 case 步骤 3。
- **重点关注步骤**：① **命中真实 500 路径**——非数组、非可迭代输入导致 `_capability_intersection` 迭代 `TypeError`；字符串/对象会得 400，不能冒充本 case；② **信封 identity**——恰 5 键、`type` 由 500 导出为 `server_error`、`code=internal_error`；③ **不泄露**——body 不得含 traceback/内部类型信息/secret；④ **零副作用**——500 前事务必须回滚，`Worker.version` 不变；⑤ **现状与期望的区分**——500 是**已登记缺陷**的现状表现，PASS 判定的是"信封契约成立 + 缺陷被登记"，不是"500 是期望行为"；⑥ **审计**——失败经 `mutate` 记 `result="failed"`，属允许的审计记录。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail`（5 键）+ `ApiError.envelope` 的 `type` 由状态导出规则。
  - HTTP：`500`；`Content-Type: application/json`；body `{"error":{"message":"Internal server error","type":"server_error","code":"internal_error","param":null,"retryable":false}}`。
  - 脱敏：body 不含 traceback / `TypeError` / 内部类型字符串 / secret 字面。
  - 资源：`Worker.version` 不变。
  - 缺陷：Run 报告登记"非数组 `deployment_ids` 缺失类型预校验（应 400 `invalid_request`）"。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`500` + 恰 5 键信封 + `code=="internal_error"` + `type=="server_error"` + 无栈/无 secret；`Worker.version` 不变；缺陷已具名登记。
  - **FAIL**：status 非 500（如实现修复后返回 400——则须更新本 case 与 §3.2/§11.1 后再判）、信封键集不符、`code`/`type` 错、泄露内部信息、或 `Worker` 被改。
  - **BLOCKED**：无法执行/无法判定且可重试（实现尚未暴露该路径、断言不可实现）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 自动化入口 **`MISSING`**（§3.2），本轮未执行；缺口引用 §3.2/§9（MISSING ≠ NOT_RUN：无实现是缺口，不是跳过）。
  - **INVALID**：用 `127.0.0.1`/mock 冒充，或用字符串/对象等会得 400 的输入冒充 500 路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
- **证据与 Run**：保存 GET/PATCH 的请求与原始 500 响应（脱敏后）、`Worker` 前后 `version`、缺陷登记条目（含 `reproduction_cmd`）、发出命令、exit code、`elapsed`、环境快照。`manifest.json` 必含 `{…,environment:"b",inputs,oracle,actual,verdict,evidence_files,redactions,reproduction_cmd}`。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`；失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需业务 teardown**——500 前回滚，无资源改动。退出前确认 7 tier 齐全、`Worker.version` 未变、无注入残留。B 类整班结束 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；`registry.update_service_level`/`_capability_intersection`（缺类型校验）；[`app.py`](../../../../src/http_api/app.py) 兜底 500；错误目录 `ERR-INTERNAL`；机制 `R-CFG-01`。自动化入口 **`MISSING`**（待补 `at_adm_sl_08.py`，落位按 §4.9/§8.5）。**不依赖**其它 Case；与 ADM-SL-04b（键白名单 400）互为"输入校验"的正/反例。
