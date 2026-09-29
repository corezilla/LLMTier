# DP-EMB-05 — batch 33 不强制上限

- **Case ID**：`DP-EMB-05`（与 §3.2 权威清单一致；本文件名 `dp-emb-05.md`，唯一对应）。
- **标题**：`POST /v1/embeddings` 输入数组长度 33（超过 `embedding_max_batch_inputs=32`）：LLMTier 层不强制该上限，返回 200 且 `data` 含 33 个 embedding 对象。
- **目的（被测契约）**：验证 `POST /v1/embeddings` 对**多输入 batch** 的处理契约，并固定"LLMTier 不在本地强制 batch 上限"这一（当前实现的）行为。被测端点/规则：`model="Embedding-v1"`、`input` 为 33 个字符串的数组（`EmbeddingRequest.input` 的数组形态，`minItems:1` 无 `maxItems`）；期望 `200`，`object=="list"`，`data` 长度恰为 33，每个元素 `object=="embedding"` 且 `index` 为 `0..32`、`embedding` 为有限的 1024 维数组。设计验证项 `VRC-INF-002`；需求 `LT-FUN-003`/`LT-OPEN-02`（[requirements](../../../10_requirements/llmtier-requirements.md)，`Embedding-v1` 声明 `batch 32`）；机制需求 `R-INF-04`/`R-INF-07`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；契约 `CT-EMB-001`。**当前实现的边界事实**：`capabilities.embedding_max_batch_inputs=32` 在 [`src/management/registry.py`](../../../../src/management/registry.py) 中为 **informational**（用于 `/v1/models` 元数据），[`src/inference/embeddings.py`](../../../../src/inference/embeddings.py) 的 `create()` 校验逻辑**不含** batch 上限检查（只校验请求键集、model、`embeddings` 能力、`dimensions`），故 33 项被原样转发上游；实际 batch 限制由上游 bge-m3 处理。参见 [`at_dp_emb_05.py`](../../../../tests/system/api_test_v03/at_dp_emb_05.py) 文件头注释。**不证明什么**：不证明 batch **上限**（本 case 恰证明"超声明值不被本地拒绝"），不证明超大 batch（如数百项）或上游真实 batch 上限，不证明 base64 形态下的 batch 编码（DP-EMB-02），不证明未知 model（DP-EMB-04）、`dimensions`（DP-EMB-06）、非法 `encoding_format`（DP-EMB-07）；不对向量语义做断言。
- **前置与环境**：**环境 A**（m5air 已部署实例；角色 `data`，只读/无状态；见[§2.3](../llmtier-api-test-specification.md)）。执行前必须通过[§2.1](../llmtier-api-test-specification.md) 的 6 项就绪检查（详见 §2.1）；任一失败 → 整班 BLOCKED/SKIP。fixture（[§4.4](../llmtier-api-test-specification.md)）：`api_client`。初始状态：`Embedding-v1` 已启用（上游本地 bge-m3，LAN，TS-003），其声明 `embedding_max_batch_inputs=32`。**上游依赖**：本 case 期望上游接受 33 项；若上游拒绝，结果将非 200（属上游限制，按判定处理）。
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
    "input": ["hello", "hello", "... (共 33 项)"]
  }
  ```

  边界/构造点：`input` 为 33 个**相同**字符串 `"hello"`（构造简单、可复现；`embedding_max_batch_inputs` 声明为 32，故意 +1 越界以证明"本地不强制"）；`encoding_format` 缺省 `float`；`model="Embedding-v1"`；不注入故障；不与其它写操作并发。33 项固定输入随 Run manifest 存档（[测试设计 §10](../llmtier-api-test-specification.md)）。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（`pytest_configure` 自动执行，本 case 不重复）。
  2. （可选前置）`GET /v1/models/Embedding-v1` 读取 `capabilities.embedding_max_batch_inputs==32`，作为"本地声明上限 32 但不强制"的证据锚点。
  3. `resp = api_client.post("/v1/embeddings", json={"model": "Embedding-v1", "input": ["hello"] * 33})`；记录 status、`Content-Type`、body。
  4. 断言 `resp.status_code == 200`（若拒绝则记录实际 status + 错误信封，按判定 FAIL/BLOCKED）。
  5. 断言 `object=="list"`、`data` 为数组且 `len(data) == 33`。
  6. 断言每个 `item` 的 `object=="embedding"`、`index` 覆盖 `0..32`（顺序稳定）、`embedding` 为有限的 1024 维数值数组。
- **重点关注步骤**：① **长度恰 33**——不是"≥1"也不是"≥33"；本地不得因声明上限 32 而截断/拒绝；② **`index` 与输入顺序对应**——`data[i].index==i`（或按实现稳定排序），是 batch 对齐的强证据；③ **每个向量的维度/有限性**——33 项都须 1024 维 finite，避免只抽查第一项；④ **上游行为风险**——本 case 的 200 依赖上游 bge-m3 接受 33 项；若上游返回非 2xx（经适配层归一为 `provider_error`/`provider_contract_error` 等），应判 **FAIL**（行为与设计期望不符）还是 **BLOCKED**（上游能力限制）需按[测试设计 §9](../llmtier-api-test-specification.md) 记录：设计将其列为正常/边界成功场景，故上游拒绝应按 FAIL 登记；若因上游离线等环境问题则 SKIP；⑤ **"informational" 事实**——`embedding_max_batch_inputs` 不参与 `create()` 校验，不要用"声明 32"反推"33 必被拒"；⑥ **非性能判定**——33 项属功能边界，不发布时延 SLO。
- **期望结果与独立 Oracle**：独立 Oracle = [openapi](../../../../interfaces/openapi/llmtier.openapi.json) `EmbeddingRequest.input`（数组形态无 `maxItems`）+ `EmbeddingResponse.data`（`EmbeddingItem[]`，长度与输入项数一致）+ 实现边界（`embedding_max_batch_inputs` 为 informational）。
  - HTTP：`200`；`Content-Type: application/json`；`X-Request-ID` 存在。
  - body：`object=="list"`、`model=="Embedding-v1"`、`data` 长度 `== 33`。
  - `data[i]`：`object=="embedding"`、`index==i`、`embedding` 为 1024 个有限数值。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` 且 `data` 长度 33 且每项 `object`/`index`/`embedding` 形状与有限性成立。
  - **FAIL**：本地以 400/其它码拒绝 33 项（与"不强制上限"不符），或返回数量非 33、`index` 不对齐、维度/有限性不符、上游因可解释原因拒绝。
  - **BLOCKED**：测试代码/契约本身问题（fixture/断言不可实现）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（上游 OMLX 离线、m5air 不可达等）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实实例，或用 B 类结果冒充 A 类——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：有实现（§3.2 `RUN`）但本轮未执行——按 §9 记 `NOT_RUN`。
- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-api-test-specification.md)：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、请求/响应（或 33 项 `index`/维度摘要）、可选的 `/v1/models/Embedding-v1` capabilities 快照、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。
- **清理与复位**：**无需 teardown**——只读 embedding 调用，不改配置/不写注入项；不删除既有资源或用户 usage。退出前确认 `/readyz` 7 tier、无未清空注入项；若误跑于 B 类实例，按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班销毁。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client` fixture（[测试设计 §4.4](../llmtier-api-test-specification.md)）；`Embedding-v1` 上游 tier（bge-m3）；`EmbeddingRequest.input`/`EmbeddingResponse.data` 机器契约（[openapi](../../../../interfaces/openapi/llmtier.openapi.json)）；实现 [`src/inference/embeddings.py`](../../../../src/inference/embeddings.py) 与 [`src/management/registry.py`](../../../../src/management/registry.py)（`embedding_max_batch_inputs` 仅元数据）；自动化入口 [`at_dp_emb_05.py`](../../../../tests/system/api_test_v03/at_dp_emb_05.py)。**不依赖**其它 Case；与 DP-EMB-01（单输入）互补、各自独立执行。
