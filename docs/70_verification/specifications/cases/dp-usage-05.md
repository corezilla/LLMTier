# DP-USAGE-05 — 缺 `from`/`to`

- **Case ID**：`DP-USAGE-05`（与 §3.2 权威清单一致；本文件名 `dp-usage-05.md`，唯一对应）。
- **标题**：`GET /v1/usage` 缺 `from` 或 `to`（或二者）→ `400 invalid_request`；非法 `date-time` 或 `from >= to` 同样 400，且在**建 snapshot / 读账本之前**被拒（零副作用）。
- **目的（被测契约）**：验证 **Usage 查询的请求校验契约**。被测端点/规则：`GET /v1/usage`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listUsage`，`from`/`to` **required** `date-time`）。实现：handler `src/http_api/app.py` 在 `not since or not until` 时直接 `ApiError(400,"invalid_request","from and to are required")`（在建快照前）；`src/inference/usage.py::_page` 在做 `from`/`to` 解析失败或 `start >= end` 时 `ApiError(400,"invalid_request",...)`（仍在 `query_snapshots` 写入前）。设计验证项 `VRC-MGMT-006`；机制需求 `R-MET-04`（HTTP 适配层错误映射）；错误目录 `ERR-REQ-VALIDATION` → `invalid_request`（[系统设计 §7.8](../../../20_system_design/llmtier-system-design.md)）；需求链 `LT-FUN-004`、`LT-INT-004/005/007`、`CT-USAGE-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明正常查询（DP-USAGE-01/03）、过期 cursor 的 `cursor_expired`（DP-USAGE-04）、filter/cursor 不匹配的 `invalid_request`（属 DP-USAGE-07 的 cursor 组件）、主体隔离（DP-USAGE-06）、store 不可用 → 503（DP-USAGE-08）；也不证明 `limit` 范围校验（实现只做整数转换，见 DP-USAGE-03 备注）。
- **前置与环境**：**环境 A**（m5air，角色 `data`，纯读/无副作用；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 6 项就绪检查；任一失败 → 整班 BLOCKED/SKIP。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`api_client`（`Bearer dev-data`）。**本 Case 自动化入口当前 `MISSING`**（[测试设计 §3.2/§3.4/§8.5](../llmtier-api-test-specification.md)），尚无 `at_dp_usage_05.py`；实现时须按 §4.9/§8.5 命名 `at_<family>_<seq>.py`。
- **输入与构造**：对 `GET /v1/usage` 逐项构造非法/缺失查询（同一 `api_client`，不注入故障）：
  1. 无任何查询参数：`GET /v1/usage`
  2. 仅 `from`：`GET /v1/usage?from=<now-30d>`
  3. 仅 `to`：`GET /v1/usage?to=<now>`
  4. 空串：`GET /v1/usage?from=&to=`
  5. 非法日期：`GET /v1/usage?from=not-a-date&to=<now>`
  6. 非法日期：`GET /v1/usage?from=<now-30d>&to=2026-13-45`
  7. 逆序/等值：`GET /v1/usage?from=<now>&to=<now-30d>` 与 `from=<now>&to=<now>`
  构造点：`from`/`to` 用动态值（`constants.recent_window()` 或 `now()`），**禁止硬编码日期**；合法值仅用于构造对照（变体 5/7）。
- **执行过程（逐步调用）**：
  1. `GET /healthz`/`GET /readyz`（`pytest_configure` 完成，不重复）。
  2. 逐个变体发 `GET /v1/usage`；断言 `status_code == 400`。
  3. 对每个响应断言 `err = body["error"]`：`err["code"] == "invalid_request"`、`err["type"] == "request_error"`、信封键集恰 `{message,type,code,param,retryable}`；`param` 为 `null`（实现未设 param，不强制其它值）。
  4. （零副作用交叉核对，可选）若具备 `ssh m5air sqlite3`（同 DP-USAGE-04 渠道），在变体前后 `SELECT COUNT(*) FROM query_snapshots;` 断言计数**不变**（校验"校验先于建 snapshot"）；无 SSH 权限时跳过该子检查，**不**因此判变体失败（子检查不计入 PASS 充分条件，仅作加强证据）。
  5. （对照，不改变本 case 判定）对同一 `api_client` 发一次**合法**查询 `?from&to`，确认返回 200——佐证拒绝来自参数而非端点/存储不可用。
- **重点关注步骤**：① **缺参 vs 坏日期都要 400 `invalid_request`**——`not since or not until` 在 handler 层、日期解析/`from>=to` 在 `_page` 层，两处都要覆盖；② **空串视同缺失**——`query.get("from",[None])[0]` 得到 `""` 为假值，应走 `invalid_request`；③ **零副作用**——拒绝必须发生在 `query_snapshots` INSERT 之前（handler 的缺参检查确实先于 `_page`；`_page` 的日期/区间检查也在建快照块之前），不得留下过期/孤儿快照；④ **错误信封 identity**——恰 5 键、无 `category`，`type` 由 `<500` 导出为 `request_error`；⑤ **不夸大**——`param` 实现为 `null`，不断言具体字段名；⑥ **MISSING 语义**——无实现是缺口（NOT_RUN），不是跳过（[测试设计 §9](../llmtier-api-test-specification.md)）；实现时须补脚本，本设计即为其 Oracle。
- **期望结果与独立 Oracle**：独立 Oracle = [`openapi`](../../../../interfaces/openapi/llmtier.openapi.json) `from`/`to` `required:true` + `ERR-REQ-VALIDATION` 目录（不依赖实现消息文本）。
  - 变体 1–7：HTTP `400`；`error.code=="invalid_request"`；`error.type=="request_error"`；信封恰 5 键。
  - 对照合法查询：`200`。
  - 可选：`query_snapshots` 计数不变。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：变体 1–7 均 `400 + invalid_request + request_error`，合法对照 `200`（可选的计数不变不改变结论）。
  - **FAIL**：任一变体返回非 400，或 `code`/`type` 不符，或返回错误信封以外形态（如 200 空页）。
  - **BLOCKED**：断言逻辑/契约问题（如 `param` 语义不清）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 mock/替代路径冒充真实路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9（MISSING ≠ NOT_RUN：无实现是缺口，不是跳过）。
- **证据与 Run**：保存 7 个变体的完整请求（含 query 实际值）与原始 status/headers/body、对照合法查询响应、可选 `ssh sqlite3` 的 `COUNT(*)` 前后值、命令/exit code、环境快照。`manifest.json` 含 `target_artifact`（三 pin）与 `redactions`（`Authorization` 脱敏）。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/dp-usage-05/`。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——全部请求在 dispatch/建快照前被拒，不产生状态变更；不创建/修改 provider/deployment/service-level、不写注入、不删除用户 usage。退出前 `/readyz` 仍 7 tier；若误跑 B 类则按[测试设计 §4.7](../llmtier-api-test-specification.md) 销毁。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client`（[§4.4](../llmtier-api-test-specification.md)）；`constants.recent_window()` 动态值；`listUsage` 机器契约与 `ERR-REQ-VALIDATION`；可选 `ssh m5air sqlite3`（仅加强证据，非 PASS 必要条件）。自动化入口 `at_dp_usage_05.py`（**当前 `MISSING`**）。**不依赖**其它 Case；与 DP-USAGE-01（正常查询）、DP-USAGE-04（过期 cursor）区分参数缺失/坏值与 cursor 过期两类 400。
