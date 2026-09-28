# DP-MODELS-04 — 大小写敏感（全大写）

- **Case ID**：`DP-MODELS-04`（与 §3.2 权威清单一致；本文件名 `dp-models-04.md`，唯一对应）。
- **标题**：`GET /v1/models/WORKER`（全大写）不匹配任何 tier → HTTP 404 + `error.code=="model_not_found"`（大小写敏感）。
- **目的（被测契约）**：验证 Data Plane `GET /v1/models/{model}` 的**大小写敏感负向契约**（全大写臂）。被测端点/规则：`model` 是**精确大小写敏感**标识符（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getModel` 参数 "Exact case-sensitive logical model ID"）；存在 tier `Worker` 为 `W` 大写 + 其余小写，请求全大写 `WORKER` 必须**不命中**并返回 `404 model_not_found`，信封 `{error:{message,type,code,param,retryable}}`（5 键，`type=="request_error"`、`param==null`、`retryable==false`）。实现 [`Registry.get_service_level()`](../../../../src/management/registry.py) 用 SQL `WHERE id=?` 精确等值匹配，[`ModelCatalog.get()`](../../../../src/inference/models.py) 将 404 `not_found` 转译为 `model_not_found`。设计验证项 `VRC-INF-001`；机制 `R-INF-04`（§3.2 行）；家族需求链 `LT-FUN-002`、`R-INF-04`/`R-INF-07`、`T-TRUST-ENDPOINTS`、契约 `CT-MODEL-001`（见[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明正向精确返回（DP-MODELS-02）、小写负向（DP-MODELS-03）、URL 编码尾空格（DP-MODELS-05）、其他不存在 id（DP-MODELS-06）；不证明凭据与 LAN trust（AUTH-01/02/06）；不证明"错误码目录全集"，只锁定本路径的 `model_not_found`。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，角色 `data`，无副作用；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的就绪检查（m5air `/healthz`、`/readyz` 含 7 tier、m5air OMLX `192.168.1.9:9000`、m5mac OMLX `192.168.1.8:9000`、`provider_omlx_m5mac.secret_ref` 为 `file:`），由 `pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`api_client`（`Authorization: Bearer dev-data`）。初始状态 = 3 provider / 4 deployment / 7 fixed tier；被拒绝的目标 `WORKER` 是全大写形态，**不在** `FIXED_TIERS`（[`constants.py`](../../../../tests/system/api_test_v03/constants.py)）中。
- **输入与构造**：固定请求（无 body、无 query）：

  ```http
  GET /v1/models/WORKER HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Accept: application/json
  ```

  边界/构造点：`model` 路径段固定为**全大写** `WORKER`（`Worker` 的全大写折叠）；本 case 只否定全大写形态，小写形态归 DP-MODELS-03；凭据固定 `data`（`dev-data`）；不注入故障；不构造非法 JSON/其它错误输入。**关键**：`WORKER` 必须由实现按字面等值匹配而 404，不得被客户端或服务端归一化为 `Worker`。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（`pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = api_client.get("/v1/models/WORKER")`；记录 status、`Content-Type`、`X-Request-ID`、原始 body。
  3. 断言 `resp.status_code == 404`（精确 404，非 200/400/500）。
  4. 断言 `content-type` 含 `application/json`，且存在 `X-Request-ID` 响应头。
  5. 解析 JSON：断言顶层键集恰为 `{error}`，`err = body["error"]` 的键集恰为 `{message,type,code,param,retryable}`（5 键，无 `category`）。
  6. 断言 `err["code"] == "model_not_found"`、`err["type"] == "request_error"`、`err["param"] is None`、`err["retryable"] is False`；`err["message"]` 为非空字符串。
- **重点关注步骤**：① **大小写敏感（全大写）**——必须观测到 404；若返回 200（把 `WORKER` 归一为 `Worker`）即 FAIL；② **状态精确 404**——不是 400/500/其它；③ **错误信封 identity**——恰 5 键 `{message,type,code,param,retryable}`（无 `category`），`type` 由状态导出（404<500 ⇒ `request_error`），`retryable=false`、`param=null`；④ **零副作用**——404 必须在 dispatch 前完成，不触上游、不写账本；⑤ **码值精确**——`model_not_found` 而非泛化 `not_found`；⑥ 不得把 `{"error":...}` 当 `Model` 读。
- **期望结果与独立 Oracle**：独立 Oracle = [openapi](../../../../interfaces/openapi/llmtier.openapi.json) `ModelNotFound`（引用 `ErrorEnvelope`/`ErrorDetail`）+ 系统设计 §7.8 `ERR-MODEL-NOTFOUND`（不依赖"清单看起来没有 WORKER"）。
  - HTTP：`404`；`Content-Type: application/json`；`X-Request-ID` 存在。
  - body：`{"error":{"message":<非空字符串>,"type":"request_error","code":"model_not_found","param":null,"retryable":false}}`；`error` 恰 5 键。
  - 无 `Model`/`ModelList` 形态的 200 body。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==404` 且 body 满足上述 `model_not_found` 信封（键集 + `code` + `type` + `param` + `retryable` + message 非空）。
  - **FAIL**：status 非 404（尤其 200）、`code` 非 `model_not_found`、信封键数不符、`type`/`param`/`retryable` 不符——按[测试设计 §9](../llmtier-api-test-specification.md) 记 FAIL 并给预期 vs 实际、`reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（fixture 写不出、断言逻辑错、`openapi`/错误码语义不清）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（m5air 不可达、`/readyz` 非 7 tier、双 OMLX 离线等）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或不触真实 Registry 却按行为判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 case 有实现（§3.2 `RUN`），未执行时按 §9 记 `NOT_RUN`；不得以未跑冒充 PASS。
- **证据与 Run**：保存原始 HTTP status/headers/body、发出命令、exit code、`elapsed`、环境快照（`/healthz`/`/readyz`），以及**证明输入为全大写**的请求行快照。每 Case `manifest.json` 含 `target_artifact`（`git_commit`/`db_schema_version`/`openapi_version`）与 `redactions`；Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/dp-models-04/`，失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——本 case 为被拒绝的只读请求，未产生副作用（无上游调用、无账本义务、无注入）。退出前确认 `/readyz` 仍显示 7 tier 且无未清空注入项（本 case 不注入）；若被误跑于 B 类临时实例，则按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf` 临时目录。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；实现 [`src/inference/models.py`](../../../../src/inference/models.py) `ModelCatalog.get()` 与 [`Registry.get_service_level()`](../../../../src/management/registry.py)；`ModelNotFound`/`ErrorDetail` 机器契约（`interfaces/openapi/llmtier.openapi.json`）；自动化入口 [`at_dp_models_04.py`](../../../../tests/system/api_test_v03/at_dp_models_04.py)。**不依赖**其它 Case；与 DP-MODELS-03（全小写）、DP-MODELS-05（URL 编码尾空格）、DP-MODELS-06（不存在）都以同一个 404 `model_not_found` 收口，但输入与"敏感维度"不同，各自独立执行、互不关闭。
