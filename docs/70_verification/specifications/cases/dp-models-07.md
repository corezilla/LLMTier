# DP-MODELS-07 — capabilities 固定 12 键

- **Case ID**：`DP-MODELS-07`（与 §3.2 权威清单一致；本文件名 `dp-models-07.md`，唯一对应）。
- **标题**：`GET /v1/models` 返回的每个 tier 的 `capabilities` 键集恰为固定的 **12 个** key。
- **目的（被测契约）**：验证 Data Plane `GET /v1/models` 中每个 `Model.capabilities` 对象满足 `ModelCapabilities` 契约（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `ModelCapabilities`：`additionalProperties:false` + `required` 恰 12 项，故键集**恰等于** 12 键）。12 键固定为：`responses`、`embeddings`、`tools`、`structured_outputs`、`input_modalities`、`output_modalities`、`context_window`、`max_output_tokens`、`embedding_space_id`、`embedding_dimensions`、`embedding_max_batch_inputs`、`embedding_max_input_tokens`（与 [`registry.CAPABILITY_KEYS`](../../../../src/management/registry.py) 完全一致）；`capabilities` 由 tier 绑定的 deployment 能力交集得出并透传（[`ModelCatalog._view`](../../../../src/inference/models.py)），该端点**只读 Registry、不 dispatch 上游**。设计验证项 `VRC-INF-002`；机制 `R-INF-04`/`R-INF-07`、`T-TRUST-ENDPOINTS`、契约 `CT-MODEL-001`（见[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明清单元素数/顺序（DP-MODELS-01）、单模型精确返回（DP-MODELS-02）、负向（DP-MODELS-03/04/05/06）；不证明各键**取值**的业务正确性（本 case 只锁键集；`responses`/`embeddings`/`tools`/`structured_outputs` 的布尔约束在 deployment/service-level 写入面校验，见 ADM-DEPL-06/07）；不证明 `availability`；不证明凭据与 LAN trust（AUTH-01/02/06）。
- **前置与环境**：**环境 A**（m5air 现有实例，角色 `data`，只读/无副作用；见[测试设计 §2.3](../llmtier-api-test-specification.md)）；前置 = §2.1 就绪检查（由 `conftest.py::pytest_configure` 自动执行，任一失败 → 整班 BLOCKED/SKIP）。fixture = `api_client`（Data 角色客户端，见[测试设计 §4.4](../llmtier-api-test-specification.md)）。初始状态 = 3 provider / 4 deployment / 7 fixed tier；7 个 tier 的 `capabilities` 均由 bootstrap 建立（`config/settings.json` 一次性 bootstrap 的 deployment 能力交集），此后 SQLite 为唯一 authority。
- **输入与构造**：固定请求（无 body、无 query）：

  ```http
  GET /v1/models HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Accept: application/json
  ```

  边界/构造点：与 DP-MODELS-01 同端点、同凭据（经 `api_client` 注入，见 §4.4）；本 case 的断言维度是**每个 `data[]` 元素的 `capabilities` 键集**（而非清单结构）；期望键集**硬编码为 12 键**（与 openapi `required` 与 `CAPABILITY_KEYS` 同源），不从被测响应反推；不注入故障；不构造非法输入。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（`pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = api_client.get("/v1/models")`；记录 status、`Content-Type`、`X-Request-ID`、原始 body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`，且存在 `X-Request-ID` 响应头。
  4. 解析 JSON：断言 `body["object"] == "list"` 且 `data` 为非空数组。
  5. 定义期望键集 `EXPECTED = {12 个 key}`（**恰 12 个**，见"目的"）；逐元素断言 `set(element["capabilities"].keys()) == EXPECTED`（`==` 而非 `⊇`，从而同时排除缺键与多键）。
  6. 断言 `len(EXPECTED) == 12` 且每个 `capabilities` 对象的键数为 `12`；记录每个 tier 的缺失/多余键明细（如有）。
- **重点关注步骤**：① **精确键集而非仅"包含"**——`ModelCapabilities.additionalProperties:false` + `required` 12 项意味着键集**恰为** 12；只查"缺不缺"会漏掉**多余键**，本 case 必须用 `==`，多一键即 FAIL；② **精确计数 12**——显式断言 `len(keys)==12`，便于报告直接给出"12 键"结论；③ **逐 tier 覆盖**——不是只抽查一个 tier，7 个 tier 全部要过；④ **键名逐字匹配**——含 `structured_outputs`、`embedding_max_batch_inputs`、`embedding_max_input_tokens` 等下划线命名，不得近似；⑤ **不以"清单看起来对"代替**——键集来自固定常量/openapi，不从响应自身推导；⑥ **只读**——本 case 不写库。
- **期望结果与独立 Oracle**：独立 Oracle = [openapi](../../../../interfaces/openapi/llmtier.openapi.json) `ModelCapabilities`（`additionalProperties:false`，`required` 12 项）+ [`registry.CAPABILITY_KEYS`](../../../../src/management/registry.py)（不依赖"清单看起来有这些字段"）。
  - HTTP：`200`；`Content-Type: application/json`；`X-Request-ID` 存在。
  - `data` 非空，每个元素含 `capabilities` 对象。
  - 每个 `capabilities` 的键集**恰为** 12 键：`{responses, embeddings, tools, structured_outputs, input_modalities, output_modalities, context_window, max_output_tokens, embedding_space_id, embedding_dimensions, embedding_max_batch_inputs, embedding_max_input_tokens}`；键数为 12，无缺失、无多余。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` 且 `data` 非空，且每个元素的 `capabilities` 键集恰为上述 12 键（集合相等 + 计数 12）。
  - **FAIL**：status 非 200、`data` 为空、任一元素缺键**或多键**、键数非 12、键名不符——按[测试设计 §9](../llmtier-api-test-specification.md) 记 FAIL 并给预期 vs 实际、`reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（fixture 写不出、断言逻辑错、`openapi` 键集语义不清）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（m5air 不可达、`/readyz` 非 7 tier、双 OMLX 离线等）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或不触真实 Registry 却按行为判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 case 有实现（§3.2 `RUN`），未执行时按 §9 记 `NOT_RUN`；不得以未跑冒充 PASS。
- **证据与 Run**：保存原始 HTTP status/headers/body、发出命令、exit code、`elapsed`、环境快照（`/healthz`/`/readyz`），以及每个 tier 的 `capabilities` 键集/键数摘要；manifest 与报告落位见 §4.8/§10（本 case `environment:"a"`）。
- **清理与复位**：**无需 teardown**——纯读 `GET`，不创建/修改 provider/deployment/service-level、不写注入项、不写 usage/账本。退出前确认 `/readyz` 仍显示 7 tier 且无未清空注入项（本 case 不注入）；若被误跑于 B 类临时实例，则按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf` 临时目录。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`ModelCapabilities` 机器契约（`interfaces/openapi/llmtier.openapi.json`）与 [`registry.CAPABILITY_KEYS`](../../../../src/management/registry.py)；实现 [`src/inference/models.py`](../../../../src/inference/models.py)；自动化入口 [`at_dp_models_07.py`](../../../../tests/system/api_test_v03/at_dp_models_07.py)。**不依赖**其它 Case；与 DP-MODELS-01 共享同一 `GET /v1/models` 响应但断言维度不同，各自独立执行、互不关闭。
