# DP-EMB-01 — 基本 embedding（1024 维 finite）

- **Case ID**：`DP-EMB-01`（与 §3.2 权威清单一致；本文件名 `dp-emb-01.md`，唯一对应）。
- **标题**：`POST /v1/embeddings` 基本 embedding：`Embedding-v1`（bge-m3，冻结空间 `bge-m3-dense-1024-v1`）成功返回，`object="list"`、`data[0].object="embedding"`、`embedding` 为 1024 个有限数值。
- **目的（被测契约）**：验证 Data Plane `POST /v1/embeddings` 的**同步 JSON 成功路径契约**。被测端点/规则：`model="Embedding-v1"`、`input` 为字符串、`encoding_format` 缺省（默认 `float`）；成功返回 [openapi](../../../../interfaces/openapi/llmtier.openapi.json) `EmbeddingResponse`（顶层键 `{object,data,model,usage}`），其中 `object=="list"`、`data` 为 `EmbeddingItem[]`、`model` 回显请求逻辑模型、`usage` 为 `EmbeddingUsage|null`；单输入时 `data[0].index==0`、`data[0].object=="embedding"`、`embedding` 为 1024 个 JSON 数值。设计验证项 `VRC-INF-001`/`VRC-INF-002`；需求 `LT-FUN-003`/`LT-OPEN-02`（[requirements](../../../10_requirements/llmtier-requirements.md)）；机制需求 `R-INF-04`/`R-INF-05`/`R-INF-07`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；契约 `CT-EMB-001`（需求→机制→设计→契约映射见[测试设计 §3.6](../llmtier-api-test-specification.md)）；`Embedding-v1` 固定为本地 `BAAI/bge-m3` dense、1024 维、`embedding_dimensions=[1024]`、`embedding_max_batch_inputs=32`（`src/management/registry.py`）。**不证明什么**：不证明 `encoding_format=base64` 表示（DP-EMB-02），不证明多次同输入的不变量/相似度（DP-EMB-03），不证明未知 model 的 404（DP-EMB-04），不证明 batch>1 行为（DP-EMB-05），不证明 `dimensions` 与冻结空间不符的拒绝（DP-EMB-06），不证明非法 `encoding_format` 的拒绝（DP-EMB-07）；不发布时延/吞吐 SLO；不对向量的语义、答案或 L2 归一化数值做门限断言（本 case 只断言结构/键集/长度/数值有限性）。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，角色 `data`，只读/无状态；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 6 项就绪检查（m5air `/healthz`、`/readyz` 含 7 tier、m5air OMLX `192.168.1.9:9000`、m5mac OMLX `192.168.1.8:9000`、`provider_omlx_m5mac.secret_ref` 为 `file:`、§2.1.6 必需 provider/deployment）；任一失败 → 整班 BLOCKED/SKIP，不得改用模拟路径。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`api_client`（`httpx.Client`，`base_url=M5AIR_BASE`，`Authorization: Bearer dev-data`，定义于 [`conftest.py`](../../../../tests/system/api_test_v03/conftest.py)）。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier；`Embedding-v1` 已启用且指向本地 bge-m3 deployment（上游走 LAN，TS-003）。本 case 为纯读，初态即终态。
- **输入与构造**：固定请求：

  ```http
  POST /v1/embeddings HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Content-Type: application/json
  Accept: application/json
  ```

  ```json
  {
    "model": "Embedding-v1",
    "input": "Hello world"
  }
  ```

  边界/构造点：`input` 取**字符串**（`EmbeddingRequest.input` 的 `oneOf` 最小合法形态之一，另一形态为非空字符串数组，见 DP-EMB-05）；`model` 必须为 embeddings-capable fixed tier（此处 `Embedding-v1`）；**省略** `encoding_format`（走 openapi 默认 `float`）、`dimensions`、`user`，以验证缺省路径；不注入故障；不构造非法输入（缺字段/多字段 → 400 `invalid_request` 属 DP-EMB-07 邻域，未知 model → DP-EMB-04）。固定 prompt/输入随 Run manifest 存档（[测试设计 §10](../llmtier-api-test-specification.md)）。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = api_client.post("/v1/embeddings", json={"model": "Embedding-v1", "input": "Hello world"})`；记录 status、`Content-Type`、`X-Request-ID`、body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`；确认 body **不是** `{"error":{...}}` 错误信封。
  4. 断言顶层键集**恰为** `{object, data, model, usage}`（openapi `EmbeddingResponse.additionalProperties:false`）；`object == "list"`；`model == "Embedding-v1"`。
  5. 断言 `data` 为非空 JSON 数组；取 `item = data[0]`，断言其键集**恰为** `{object, index, embedding}`（openapi `EmbeddingItem.additionalProperties:false`），且 `item["object"] == "embedding"`、`item["index"] == 0`（单输入）。
  6. 断言 `item["embedding"]` 为 JSON 数组（`list`），长度 `== 1024`，且每个元素为 `int`/`float`（非 `bool`）且 `math.isfinite(x)` 为真（无 `NaN`/`Infinity`）。
  7. （可选、非门限）读取顶层 `usage`：断言其为 `null` 或 JSON 对象；不把 `usage` 的具体数值当作本 case 的 PASS 条件。
- **重点关注步骤**：① **键集严格性**——不是"含这些键"而是"键集恰等"，`EmbeddingResponse`/`EmbeddingItem` 均 `additionalProperties:false`，多键即契约违反；② **数值有限性**——`isfinite` 覆盖 `NaN`/`±Infinity`；仅"是数字"不够（JSON 允许 `NaN` 字面量时须拒绝）；③ **维数 1024**——bge-m3 冻结空间硬约束，误按 768/1536 断言即错；④ **`model` 回显逻辑模型**——实现把上游结果 `result["model"] = model`（[`src/inference/embeddings.py`](../../../../src/inference/embeddings.py) 第 72 行）覆盖为请求的 `Embedding-v1`，断言应为逻辑模型而非上游 `bge-m3`；⑤ **`usage` 直通风险**——实现只把上游 payload 的 `model` 覆盖后原样返回，**响应 `usage` 来自上游且未经归一**（归一后的 usage 仅写账本 `usage.finish`）；因此只断言"存在且为 `null` 或对象"，若上游返回超出 `EmbeddingUsage` 键集的字段（`additionalProperties:false`）将是契约问题，现有 [`at_dp_emb_01.py`](../../../../tests/system/api_test_v03/at_dp_emb_01.py) 未断言此点，属加强项；⑥ **不依赖向量语义**——不对答案、相似度、L2 范数做门限（后者属 LT-FUN-003 数值性质，但不纳入本 case 独立 Oracle）。
- **期望结果与独立 Oracle**：独立 Oracle = [openapi](../../../../interfaces/openapi/llmtier.openapi.json) `EmbeddingResponse`/`EmbeddingItem` 的 wire 形态（不依赖实现的具体向量值）。
  - HTTP：`200`；响应头 `Content-Type: application/json`；`X-Request-ID` 存在（openapi `createEmbedding` 200 header）。
  - 顶层 body：JSON 对象，键集**恰为** `{object, data, model, usage}`；`object=="list"`；`model=="Embedding-v1"`。
  - `data[0]`：键集**恰为** `{object, index, embedding}`；`object=="embedding"`；`index==0`。
  - `data[0].embedding`：JSON 数组，`len == 1024`，元素均为有限的 `int`/`float`。
  - `usage`：`null` 或 JSON 对象（若为对象，按 openapi `EmbeddingUsage` 应恰含 `{prompt_tokens,total_tokens}` 且为 >=0 整数；本 case 仅作可选交叉核对）。
  - 无错误信封：本 case 不应出现 `{"error":{...}}`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` 且 content-type 为 JSON，且顶层/`data[0]` 键集与 Oracle 一致，`object`/`index`/`embedding` 长度 1024 且全部 finite（`usage` 存在且为 null 或对象）。
  - **FAIL**：任一断言不符（status 非 200、键集不等、`object`/`index` 错、维数非 1024、含非有限值或非数值、以错误信封冒充成功）。
  - **BLOCKED**：测试代码/契约本身问题（如 `api_client` 写不出、断言逻辑错、openapi 语义不清）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（m5air 不可达、`/readyz` 非 7 tier、双 OMLX 离线等）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或以 B 类临时实例结果冒充 A 类——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`；不得以未跑冒充 PASS。
- **证据与 Run**：保存原始 HTTP status/headers/body（脱敏后）、发出命令（`curl`/httpx）、exit code、`elapsed`、环境快照（`/healthz`/`/readyz` + provider/deployment 列表）。每 Case `manifest.json` 含被测版本锁定 `target_artifact`（`git_commit`/`db_schema_version`/`openapi_version`）与 `redactions`（`Authorization` 脱敏）。Run ID = `<date>/A-api`（如 `2026-09-28/A-api`），落位 `tests/system/reports/<date>/A-api/dp-emb-01/`，`manifest.json` 必填字段见[测试设计 §4.8](../llmtier-api-test-specification.md)，失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——本 case 为只读 `POST`（embedding 不落配置、不改 provider/deployment/service-level、不写注入项；账本可能记录一次 dispatch，属正常计量不回收）。不删除任何既有资源或用户 usage。退出前确认无未清空的注入项（本 case 不注入）、`/readyz` 仍显示 7 tier；若被误跑于 B 类临时实例，则按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf` 临时目录。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查（m5air `/healthz`、`/readyz` 7 tier、双 OMLX、`provider_omlx_m5mac` secret）；`api_client` fixture（[测试设计 §4.4](../llmtier-api-test-specification.md)）；embeddings-capable 上游 tier `Embedding-v1`（本地 bge-m3，1024 维）；机器契约 `EmbeddingResponse`/`EmbeddingItem`/`EmbeddingUsage`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json)）；实现 [`src/inference/embeddings.py`](../../../../src/inference/embeddings.py)；自动化入口 [`at_dp_emb_01.py`](../../../../tests/system/api_test_v03/at_dp_emb_01.py)。**不依赖**其它 Case；与 DP-EMB-02/03 共享同一成功路径语义但各自独立执行（02 校验 base64 形态，03 校验重复不变量）。
