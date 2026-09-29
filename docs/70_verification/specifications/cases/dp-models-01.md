# DP-MODELS-01 — 列出全部可见 tier

- **Case ID**：`DP-MODELS-01`（与 §3.2 权威清单一致；本文件名 `dp-models-01.md`，唯一对应）。
- **标题**：`GET /v1/models` 返回全部可见逻辑模型（fixed tier）清单：HTTP 200 + `object=="list"` + `data` 恰含 7 个 tier、id 互不重复。
- **目的（被测契约）**：验证 Data Plane `GET /v1/models`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listModels`，全局 `security=BearerAuth`，role=`data`）的**模型清单读契约**。被测端点/规则：成功返回 `ModelList`（`{object:"list", data:[Model...]}`，`additionalProperties:false`）；`data` 元素为 `Model`（`{id,object,created,owned_by,availability,capabilities}`，`additionalProperties:false`），`object=="model"`、`owned_by=="llmtier"`、`availability∈{available,degraded,unavailable}`；`data` 恰含 7 个 fixed tier（`FIXED_TIERS`）。实现见 [`ModelCatalog.list()`](../../../../src/inference/models.py) 与 [`Registry.list_service_levels()`](../../../../src/management/registry.py)；该端点**只读 Registry、不 dispatch 上游**。设计验证项 `VRC-INF-002`（§3.2 行另记 `R-CFG-01`）；家族需求链 `LT-FUN-002`、机制 `R-INF-04`/`R-INF-07`、`T-TRUST-ENDPOINTS`、契约 `CT-MODEL-001`（见[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明单模型精确返回（DP-MODELS-02）、大小写/URL 编码/不存在负向（DP-MODELS-03/04/05/06）、`capabilities` 键集完整性（DP-MODELS-07）；不证明凭据负向与 LAN trust（AUTH-01/02/06）；不证明 `availability` 与上游健康一致（本 case 只断言枚举合法，不断言具体值）；不触上游，故不证明任何 provider/模型可用性。
- **前置与环境**：**环境 A**（m5air 现有实例，角色 `data`，只读/无副作用；见[测试设计 §2.3](../llmtier-api-test-specification.md)）；前置 = §2.1 就绪检查（由 `conftest.py::pytest_configure` 自动执行，任一失败 → 整班 BLOCKED/SKIP）。fixture = `api_client`（Data 角色客户端，见[测试设计 §4.4](../llmtier-api-test-specification.md)）。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier；基线 tier 集合见 [`constants.FIXED_TIERS`](../../../../tests/system/api_test_v03/constants.py)。
- **输入与构造**：固定请求（无请求体、无查询参数）：

  ```http
  GET /v1/models HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Accept: application/json
  ```

  边界/构造点：**无 body**（GET 不携带）；**无 query**（清单端点不接受参数）；凭据固定 `data`（经 `api_client` 注入，见 §4.4）；不注入故障；不构造非法输入（错误/空/缺凭据属 AUTH-01/02/06）。基线期望由 `FIXED_TIERS` 常量决定（**集合/数量**；不依赖实现返回顺序）。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = api_client.get("/v1/models")`；记录 status、`Content-Type`、`X-Request-ID`、原始 body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`，且存在 `X-Request-ID` 响应头。
  4. 解析 JSON：断言顶层为对象且键集**恰为** `{object, data}`（`additionalProperties:false`），`body["object"] == "list"`，`body["data"]` 为数组。
  5. 断言 `len(data) == 7`；`[m["id"] for m in data]` 无重复；`set(ids) == set(FIXED_TIERS)`（**只断言集合/数量，不断言顺序**——openapi `ModelList.data` 是无序数组，§3.2 只固定 7 个 tier 的集合/数量）。
  6. 抽每个元素：键集**恰为** `{id,object,created,owned_by,availability,capabilities}`；`object=="model"`、`owned_by=="llmtier"`、`created` 为正整数、`availability` 在枚举内、`capabilities` 为对象。
- **重点关注步骤**：① **精确元素数**——不是"至少含 7 个"，而是 `len(data)==7` 且 id 集合恰等于 7 个 fixed tier（多/少/重复即 FAIL）；② **键集精确性**——顶层 `ModelList` 与每个 `Model` 均为 `additionalProperties:false`，多一个键即违约；③ **不得以错误信封冒充**——非 200 时须确认是 `ERR-AUTH-*`/其它可解释错误，而非把 `{error:...}` 当 `ModelList` 读；④ **不触上游**——本端点不应产生上游调用或账本义务，区别于 `/v1/responses`；⑤ **`availability` 只验枚举**——m5air 各 tier 的实际可用性随上游状态变化，不写死具体值；⑥ **`created` 是响应时刻**——实现为 `int(time.time())`（[`models.py`](../../../../src/inference/models.py) `_view`），**不是**持久化创建时间，故只断言"正整数"，不得断言跨请求稳定。
- **期望结果与独立 Oracle**：独立 Oracle = [openapi](../../../../interfaces/openapi/llmtier.openapi.json) `ModelList`/`Model` 的 wire 形态 + 固定 tier 基线（**集合/数量**，不依赖"清单看起来对"，也不依赖实现顺序）。
  - HTTP：`200`；`Content-Type: application/json`；`X-Request-ID` 存在。
  - 顶层键集恰 `{object, data}`；`object=="list"`；`data` 长度 7。
  - `data` 的 id **集合恰为** `set(FIXED_TIERS)` = `{Senior, Junior, Worker, Associate, Engineer, Executor, Embedding-v1}`；**不断言数组顺序**（`ModelList.data` 为无序数组，§3.2 只固定集合/数量）。
  - 每个元素键集恰 `{id,object,created,owned_by,availability,capabilities}`，`object=="model"`、`owned_by=="llmtier"`、`created` 为正整数、`availability∈{available,degraded,unavailable}`。
  - 无 `{"error":{...}}` 信封。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：上述期望结果与独立 Oracle 全部 match（status + content-type + 顶层键集 + `object=="list"` + `len(data)==7` + id 集合 + 每元素 `Model` 键集与字段值）。
  - **FAIL**：任一断言不符（status 非 200、`object` 错、元素数/id 集合不符、键集多/缺、字段类型或枚举错）——按[测试设计 §9](../llmtier-api-test-specification.md) 记 FAIL 并给预期 vs 实际、`reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（fixture 写不出、断言逻辑错、`openapi` 语义不清）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（m5air 不可达、`/readyz` 非 7 tier、双 OMLX 离线等）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或不触真实 Registry 却按行为判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 case 有实现（§3.2 `RUN`），未执行时按 §9 记 `NOT_RUN`；不得以未跑冒充 PASS。
- **证据与 Run**：保存原始 HTTP status/headers/body、发出命令（httpx/`curl`）、exit code、`elapsed`、环境快照（`/healthz`/`/readyz` + provider/deployment 列表）；manifest 与报告落位见 §4.8/§10（本 case `environment:"a"`）。
- **清理与复位**：**无需 teardown**——本 case 为只读 `GET`，不创建/修改 provider/deployment/service-level、不写注入项、不写 usage/账本。退出前确认 `/readyz` 仍显示 7 tier 且无未清空注入项（本 case 不注入）；若被误跑于 B 类临时实例，则按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf` 临时目录。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`FIXED_TIERS` 基线（[`constants.py`](../../../../tests/system/api_test_v03/constants.py) / [`registry.py`](../../../../src/management/registry.py)）；实现 [`src/inference/models.py`](../../../../src/inference/models.py)；`ModelList`/`Model` 机器契约（`interfaces/openapi/llmtier.openapi.json`）；自动化入口 [`at_dp_models_01.py`](../../../../tests/system/api_test_v03/at_dp_models_01.py)。**不依赖**其它 Case；与 DP-MODELS-07（同一清单上的 capabilities 键集断言）共享响应但各自独立执行、互不关闭。
