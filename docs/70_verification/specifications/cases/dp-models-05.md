# DP-MODELS-05 — URL 编码尾空格不匹配

- **Case ID**：`DP-MODELS-05`（与 §3.2 权威清单一致；本文件名 `dp-models-05.md`，唯一对应）。
- **标题**：`GET /v1/models/Senior%20`（URL 编码尾空格）不匹配任何 tier → HTTP 404 + `error.code=="model_not_found"`。
- **目的（被测契约）**：验证 Data Plane `GET /v1/models/{model}` 对**带编码尾空格的路径段**的负向契约。被测端点/规则：`model` 是**精确标识符**，"`Senior `（带尾空格）"不是任何 tier，必须**不命中**并返回 `404 model_not_found`，信封 `{error:{message,type,code,param,retryable}}`（5 键，`type=="request_error"`、`param==null`、`retryable==false`）。实现侧路径来自 `urlparse(self.path).path` 的 `[^/]+` 捕获（[`app.py`](../../../../src/http_api/app.py) 正则 `/v1/models/([^/]+)`），随后交 [`Registry.get_service_level()`](../../../../src/management/registry.py) 的 SQL `WHERE id=?` 精确等值匹配；[`ModelCatalog.get()`](../../../../src/inference/models.py) 将 404 `not_found` 转译为 `model_not_found`。设计验证项 `VRC-INF-001`；机制 `R-INF-04`（§3.2 行）；家族需求链 `LT-FUN-002`、`R-INF-04`/`R-INF-07`、`T-TRUST-ENDPOINTS`、契约 `CT-MODEL-001`（见[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明正向精确返回（DP-MODELS-02）、小写/全大写负向（DP-MODELS-03/04）、其它不存在 id（DP-MODELS-06）；不证明服务端对**合法**含空格模型 id 的支持（无此 tier，本 case 只证明其被拒）；不证明凭据与 LAN trust（AUTH-01/02/06）；**不锁定"404 的具体成因是解码后带空格还是字面 `%20`"**——两者都落在"未命中"这一可观察契约上（见重点关注 ①）。
- **前置与环境**：**环境 A**（m5air 现有实例，角色 `data`，无副作用；见[测试设计 §2.3](../llmtier-api-test-specification.md)）；前置 = §2.1 就绪检查（由 `conftest.py::pytest_configure` 自动执行，任一失败 → 整班 BLOCKED/SKIP）。fixture = `api_client`（Data 角色客户端，见[测试设计 §4.4](../llmtier-api-test-specification.md)）。初始状态 = 3 provider / 4 deployment / 7 fixed tier；被拒绝的目标是 `Senior`（存在 tier）加尾空格后的形态，**不在** `FIXED_TIERS`（[`constants.py`](../../../../tests/system/api_test_v03/constants.py)）中。
- **输入与构造**：固定请求（无 body、无 query）：

  ```http
  GET /v1/models/Senior%20 HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Accept: application/json
  ```

  边界/构造点：`model` 路径段固定为 `Senior%20`（`%20` 为空格编码；被拒目标 = `Senior` + 尾空格）；**必须**以已编码形式发送，不得让客户端把 `%20` 误还原成裸空格后由 httpx 再编码成同一字节序列（本 case 关注的是该编码路径段不命中）；凭据固定 `data`（经 `api_client` 注入，见 §4.4）；不注入故障；不构造非法 JSON/其它错误输入。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（`pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = api_client.get("/v1/models/Senior%20")`；记录 status、`Content-Type`、`X-Request-ID`、原始 body，以及实际发送的请求目标（含 `%20`）。
  3. 断言 `resp.status_code == 404`（精确 404，非 200/400/500）。
  4. 断言 `content-type` 含 `application/json`，且存在 `X-Request-ID` 响应头。
  5. 解析 JSON：断言顶层键集恰为 `{error}`，`err = body["error"]` 的键集恰为 `{message,type,code,param,retryable}`（5 键，无 `category`）。
  6. 断言 `err["code"] == "model_not_found"`、`err["type"] == "request_error"`、`err["param"] is None`、`err["retryable"] is False`；`err["message"]` 为非空字符串。
- **重点关注步骤**：① **"未命中"是唯一被锁定的可观察契约**——`Senior `（带尾空格）不是 tier，故 404；实现当前**不做** percent-decode（`app.py` 直接取 `urlparse(...).path` 的 `[^/]+`），因此传入 Registry 的是字面 `Senior%20`，与"解码后 `Senior `"同样都**未命中**。本 case 的 Oracle 只管 `status==404 + code==model_not_found`，**不**断言具体成因；若未来实现改为先 `unquote` 再匹配，本 case 仍应 PASS（不能因成因变化而 FAIL）。② **状态精确 404**——不是 400/500/其它；③ **错误信封 identity**——恰 5 键（无 `category`），`type=="request_error"`、`retryable=false`、`param=null`；④ **零副作用**——404 必须在 dispatch 前完成，不触上游、不写账本；⑤ **编码保持**——必须确认发送的是 `%20` 形态（请求行/httpx URL 快照），避免把"裸空格被 httpx 重编码"与"字面 `%20`"混为一谈；⑥ **码值精确**——`model_not_found` 而非泛化 `not_found`。
- **期望结果与独立 Oracle**：独立 Oracle = [openapi](../../../../interfaces/openapi/llmtier.openapi.json) `ModelNotFound`（引用 `ErrorEnvelope`/`ErrorDetail`）+ 系统设计 §7.8 `ERR-MODEL-NOTFOUND`（不依赖"清单看起来没有 `Senior `"）。
  - HTTP：`404`；`Content-Type: application/json`；`X-Request-ID` 存在。
  - body：`{"error":{"message":<非空字符串>,"type":"request_error","code":"model_not_found","param":null,"retryable":false}}`；`error` 恰 5 键。
  - 无 `Model`/`ModelList` 形态的 200 body。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==404` 且 body 满足上述 `model_not_found` 信封（键集 + `code` + `type` + `param` + `retryable` + message 非空）。
  - **FAIL**：status 非 404（尤其 200）、`code` 非 `model_not_found`、信封键数不符、`type`/`param`/`retryable` 不符——按[测试设计 §9](../llmtier-api-test-specification.md) 记 FAIL 并给预期 vs 实际、`reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（fixture 写不出、断言逻辑错、编码构造/`openapi` 语义不清）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（m5air 不可达、`/readyz` 非 7 tier、双 OMLX 离线等）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或不触真实 Registry 却按行为判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 case 有实现（§3.2 `RUN`），未执行时按 §9 记 `NOT_RUN`；不得以未跑冒充 PASS。
- **证据与 Run**：保存原始 HTTP status/headers/body、**含 `%20` 的请求目标快照**、发出命令、exit code、`elapsed`、环境快照（`/healthz`/`/readyz`）；manifest 与报告落位见 §4.8/§10（本 case `environment:"a"`）。
- **清理与复位**：**无需 teardown**——本 case 为被拒绝的只读请求，未产生副作用（无上游调用、无账本义务、无注入）。退出前确认 `/readyz` 仍显示 7 tier 且无未清空注入项（本 case 不注入）；若被误跑于 B 类临时实例，则按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf` 临时目录。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；实现 [`src/inference/models.py`](../../../../src/inference/models.py) `ModelCatalog.get()`、[`Registry.get_service_level()`](../../../../src/management/registry.py) 与路径捕获 [`app.py`](../../../../src/http_api/app.py)；`ModelNotFound`/`ErrorDetail` 机器契约（`interfaces/openapi/llmtier.openapi.json`）；自动化入口 [`at_dp_models_05.py`](../../../../tests/system/api_test_v03/at_dp_models_05.py)。**不依赖**其它 Case；与 DP-MODELS-03/04/06 都以同一个 404 `model_not_found` 收口，但输入维度不同，各自独立执行、互不关闭。
