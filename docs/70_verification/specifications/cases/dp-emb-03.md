# DP-EMB-03 — 不变量（同输入 ×5）

- **Case ID**：`DP-EMB-03`（与 §3.2 权威清单一致；本文件名 `dp-emb-03.md`，唯一对应）。
- **标题**：`POST /v1/embeddings` 同一输入连续 5 次：每次 200、维度均 1024，且 5 个向量两两 cosine 相似度 `> 0.99`。
- **目的（被测契约）**：验证 `Embedding-v1` 对**同一逻辑 model + 同一输入**的可复现性/稳定性契约。被测端点/规则：`model="Embedding-v1"`、`input` 固定为同一字符串，连续发起 5 次 `POST /v1/embeddings`（`encoding_format` 缺省 `float`）；期望 5 次均 `200`，每个向量维度 `1024`，且任意两向量的 `cosine similarity > 0.99`。设计验证项 `VRC-INF-002`（模型确定性/空间稳定）；需求 `LT-FUN-003`/`LT-OPEN-02`（[requirements](../../../10_requirements/llmtier-requirements.md)）；机制需求 `R-INF-04`/`R-INF-07`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；契约 `CT-EMB-001`；[测试设计 §5](../llmtier-api-test-specification.md) 正常场景明确"DP-EMB-01/02/03：维度 1024、base64 严格解码、同输入不变量（cosine > 0.99）"。**不证明什么**：不证明"逐位相等"（本 case 接受高相似而非 bitwise 相同），不证明不同输入间的区分度，不证明 base64 形态（DP-EMB-02），不证明未知 model（DP-EMB-04）、batch>1（DP-EMB-05）、`dimensions`（DP-EMB-06）、非法 `encoding_format`（DP-EMB-07）；不对向量语义/答案做断言。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，角色 `data`，只读/无状态；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 6 项就绪检查；任一失败 → 整班 BLOCKED/SKIP，不得改用模拟路径。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`api_client`（`httpx.Client`，`Authorization: Bearer dev-data`）。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier；`Embedding-v1` 已启用（上游本地 bge-m3，LAN，TS-003）。本 case 为纯读，5 次调用无状态。
- **输入与构造**：固定请求（连续 5 次，body 完全相同）：

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

  边界/构造点：`input` 在 5 次间**逐字符相同**（同 prompt，随 [测试设计 §10](../llmtier-api-test-specification.md) 固定输入存档）；`encoding_format` 缺省 `float`；`model` 固定；不注入故障；不并发（串行 5 次，避免把并发/准入影响混入不变量判定）。相似度阈值取自[测试设计 §5](../llmtier-api-test-specification.md)（`> 0.99`）。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（`pytest_configure` 自动执行，本 case 不重复）。
  2. 循环 5 次：`resp = api_client.post("/v1/embeddings", json={"model": "Embedding-v1", "input": "Hello world"})`；每次断言 `status_code == 200`、`data[0].object == "embedding"`、`embedding` 为非空数值数组且 `len == 1024`，收集向量到 `vectors`。
  3. 对每一对 `(i,j)`（`0<=i<j<5`）计算 `cosine(vectors[i], vectors[j])`；断言 `> 0.99`。
  4. 记录 5 次 `X-Request-ID` 与 `elapsed`（仅供证据，不参与 PASS/FAIL）。
- **重点关注步骤**：① **同输入一致性**——5 次必须使用**完全相同的 body**（尤其 `input` 与省略字段一致），任一字段漂移会使比较失去意义；② **相似度而非相等**——Oracle 是 `cosine > 0.99`（软阈值，容忍上游推理的浮点/批次差异），**不是**逐位相等；不要因为向量不完全相同而误判 FAIL，也不要因"同输入必相同"的假设而过严；③ **维度一致性**——5 个向量都须 1024，长度不一致须先判 FAIL；④ **cosine 实现独立**——测试侧自行计算点积/范数（见 [`at_dp_emb_03.py`](../../../../tests/system/api_test_v03/at_dp_emb_03.py) 的 `_cosine`），不调用被测实现的归一化；⑤ **零向量保护**——范数为 0 时 cosine 未定义，测试实现返回 0（判 FAIL），须显式处理；⑥ **串行执行**——避免并发导致的不相关差异；本 case 不承担并发/准入判定。
- **期望结果与独立 Oracle**：独立 Oracle = "同逻辑 model + 同输入 ⇒ 高相似（cosine > 0.99）"的稳定性规则，与具体向量值无关。
  - 5 次 HTTP 均 `200`；`Content-Type: application/json`。
  - 每次 `data[0].object=="embedding"`、`len(embedding)==1024`、元素为有限数值。
  - 任意两向量 `cosine > 0.99`（测试侧独立计算）。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：5 次均 200 且维度 1024，且 10 个两两组合的 cosine 全部 `> 0.99`。
  - **FAIL**：任一次非 200、维度非 1024、或某对 cosine `<= 0.99`（不满足不变量契约）。
  - **BLOCKED**：测试代码/契约本身问题（cosine 实现错、断言不可实现）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实实例，或对每次输入做了不同构造却声称"同输入"——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：有实现（§3.2 `RUN`）但本轮未执行——按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存 5 次请求/响应的 status/headers/body（或各自向量摘要）、测试侧 cosine 矩阵、发出命令、exit code、`elapsed`、环境快照。`manifest.json` 含 `{run_id, case_id, target_artifact{git_commit, db_schema_version, openapi_version}, environment:"a", inputs, oracle, actual, verdict, evidence_files, redactions, reproduction_cmd}`（[测试设计 §4.8](../llmtier-api-test-specification.md)）。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/dp-emb-03/`，失败现场不截断（[测试设计 §10](../llmtier-api-test-specification.md)）。
- **清理与复位**：**无需 teardown**——5 次只读调用，不改配置/不写注入项；不删除既有资源或用户 usage。退出前确认 `/readyz` 7 tier、无未清空注入项；若误跑于 B 类实例，按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班销毁。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client` fixture（[测试设计 §4.4](../llmtier-api-test-specification.md)）；`Embedding-v1` 上游 tier；[测试设计 §5](../llmtier-api-test-specification.md) 的不变量阈值；实现 [`src/inference/embeddings.py`](../../../../src/inference/embeddings.py)；自动化入口 [`at_dp_emb_03.py`](../../../../tests/system/api_test_v03/at_dp_emb_03.py)。**不依赖**其它 Case；与 DP-EMB-01/02 共享成功路径但独立执行。
