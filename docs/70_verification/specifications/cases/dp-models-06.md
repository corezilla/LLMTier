# DP-MODELS-06 — 不存在模型

- **Case ID**：`DP-MODELS-06`（与 §3.2 权威清单一致；本文件名 `dp-models-06.md`，唯一对应）。
- **标题**：`GET /v1/models/NonExistent`（不存在的 id）→ HTTP 404 + `error.code=="model_not_found"`。
- **目的（被测契约）**：验证 Data Plane `GET /v1/models/{model}` 对**完全不存在模型 id** 的负向契约。被测端点/规则：任何不在 7 个 fixed tier 中的精确 id 必须返回 `404 model_not_found`，信封 `{error:{message,type,code,param,retryable}}`（5 键，`type=="request_error"`、`param==null`、`retryable==false`）。实现 [`Registry.get_service_level()`](../../../../src/management/registry.py) 用 SQL `WHERE id=?` 精确等值匹配，未命中抛 `ApiError(404,"not_found")`；[`ModelCatalog.get()`](../../../../src/inference/models.py) 将 404 `not_found` 转译为 `model_not_found`。设计验证项 `VRC-INF-001`；机制 `R-INF-04`（§3.2 行）；家族需求链 `LT-FUN-002`、`R-INF-04`/`R-INF-07`、`T-TRUST-ENDPOINTS`、契约 `CT-MODEL-001`（见[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明正向精确返回（DP-MODELS-02）、大小写/URL 编码边界（DP-MODELS-03/04/05，虽同以 404 收口但输入不同）；不证明清单聚合（DP-MODELS-01）或 capabilities（DP-MODELS-07）；不证明凭据与 LAN trust（AUTH-01/02/06）；不证明路由到 Responses 的 unknown model（DP-RESP-05，端点不同）。
- **前置与环境**：**环境 A**（m5air 现有实例，角色 `data`，无副作用；见[测试设计 §2.3](../llmtier-api-test-specification.md)）；前置 = §2.1 就绪检查（由 `conftest.py::pytest_configure` 自动执行，任一失败 → 整班 BLOCKED/SKIP）。fixture = `api_client`（Data 角色客户端，见[测试设计 §4.4](../llmtier-api-test-specification.md)）。初始状态 = 3 provider / 4 deployment / 7 fixed tier；被请求的 `NonExistent` 不在 `FIXED_TIERS`（[`constants.py`](../../../../tests/system/api_test_v03/constants.py)）中，也非任何合法大小写变体。
- **输入与构造**：固定请求（无 body、无 query）：

  ```http
  GET /v1/models/NonExistent HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Accept: application/json
  ```

  边界/构造点：`model` 路径段固定为 `NonExistent`（一个明确不存在的字面 id）；本 case 的"负向维度"是**存在性**（与 DP-MODELS-03/04 的**大小写**维度、DP-MODELS-05 的**编码/空格**维度相区别）；凭据固定 `data`（经 `api_client` 注入，见 §4.4）；不注入故障；不构造非法 JSON/其它错误输入。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（`pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = api_client.get("/v1/models/NonExistent")`；记录 status、`Content-Type`、`X-Request-ID`、原始 body。
  3. 断言 `resp.status_code == 404`（精确 404，非 200/400/500）。
  4. 断言 `content-type` 含 `application/json`，且存在 `X-Request-ID` 响应头。
  5. 解析 JSON：断言顶层键集恰为 `{error}`，`err = body["error"]` 的键集恰为 `{message,type,code,param,retryable}`（5 键，无 `category`）。
  6. 断言 `err["code"] == "model_not_found"`、`err["type"] == "request_error"`、`err["param"] is None`、`err["retryable"] is False`；`err["message"]` 为非空字符串。
- **重点关注步骤**：① **存在性否定**——必须观测到 404；若 200 或 400 即 FAIL；② **状态精确 404**；③ **错误信封 identity**——恰 5 键（无 `category`），`type=="request_error"`、`retryable=false`、`param=null`；④ **零副作用**——404 必须在 dispatch 前完成，不触上游、不写账本；⑤ **码值精确**——`model_not_found`，**不是**资源子路径用的泛化 `not_found`；⑥ **与路由外层区分**——本端点不进入推理调度，不应出现 `model_unavailable`/`rate_limit_exceeded` 等调度侧码。
- **期望结果与独立 Oracle**：独立 Oracle = [openapi](../../../../interfaces/openapi/llmtier.openapi.json) `ModelNotFound`（引用 `ErrorEnvelope`/`ErrorDetail`）+ 系统设计 §7.8 `ERR-MODEL-NOTFOUND`（不依赖"清单看起来没有 NonExistent"）。
  - HTTP：`404`；`Content-Type: application/json`；`X-Request-ID` 存在。
  - body：`{"error":{"message":<非空字符串>,"type":"request_error","code":"model_not_found","param":null,"retryable":false}}`；`error` 恰 5 键。
  - 无 `Model`/`ModelList` 形态的 200 body。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==404` 且 body 满足上述 `model_not_found` 信封（键集 + `code` + `type` + `param` + `retryable` + message 非空）。
  - **FAIL**：status 非 404（尤其 200/400）、`code` 非 `model_not_found`、信封键数不符、`type`/`param`/`retryable` 不符——按[测试设计 §9](../llmtier-api-test-specification.md) 记 FAIL 并给预期 vs 实际、`reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（fixture 写不出、断言逻辑错、`openapi`/错误码语义不清）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（m5air 不可达、`/readyz` 非 7 tier、双 OMLX 离线等）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或不触真实 Registry 却按行为判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 case 有实现（§3.2 `RUN`），未执行时按 §9 记 `NOT_RUN`；不得以未跑冒充 PASS。
- **证据与 Run**：保存原始 HTTP status/headers/body、发出命令、exit code、`elapsed`、环境快照（`/healthz`/`/readyz`），以及**证明 `NonExistent` 不在清单**的交叉核对证据（可选：`GET /v1/models` 的 id 集合与请求 id 的差集）；manifest 与报告落位见 §4.8/§10（本 case `environment:"a"`）。
- **清理与复位**：**无需 teardown**——本 case 为被拒绝的只读请求，未产生副作用（无上游调用、无账本义务、无注入）。退出前确认 `/readyz` 仍显示 7 tier 且无未清空注入项（本 case 不注入）；若被误跑于 B 类临时实例，则按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf` 临时目录。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；实现 [`src/inference/models.py`](../../../../src/inference/models.py) `ModelCatalog.get()` 与 [`Registry.get_service_level()`](../../../../src/management/registry.py)；`ModelNotFound`/`ErrorDetail` 机器契约（`interfaces/openapi/llmtier.openapi.json`）；自动化入口 [`at_dp_models_06.py`](../../../../tests/system/api_test_v03/at_dp_models_06.py)。**不依赖**其它 Case；与 DP-MODELS-03/04/05 都以同一个 404 `model_not_found` 收口，但输入维度不同，各自独立执行、互不关闭。
