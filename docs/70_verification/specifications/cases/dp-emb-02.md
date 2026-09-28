# DP-EMB-02 — base64 编码

- **Case ID**：`DP-EMB-02`（与 §3.2 权威清单一致；本文件名 `dp-emb-02.md`，唯一对应）。
- **标题**：`POST /v1/embeddings` `encoding_format=base64`：`data[0].embedding` 为 RFC 4648 base64 字符串，独立解码得 1024 个 little-endian IEEE-754 float32，全部 finite。
- **目的（被测契约）**：验证 Data Plane `POST /v1/embeddings` 的 **base64 表示契约**。被测端点/规则：请求 `encoding_format="base64"` 时，成功响应的 `data[0].embedding` 必须是**字符串**，且为 **RFC 4648 base64**，其解码字节为**连续的 little-endian IEEE-754 float32**，数量恰为 1024（与 `Embedding-v1` 冻结空间 `bge-m3-dense-1024-v1` 一致）。设计验证项 `VRC-INF-001`；需求 `LT-FUN-003`/`LT-OPEN-02`（[requirements](../../../10_requirements/llmtier-requirements.md)）；机制需求 `R-INF-04`/`R-INF-07`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；契约 `CT-EMB-001`；[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `EmbeddingRequest.encoding_format`（`enum:[float,base64]`）与 `EmbeddingItem.embedding`（`contentEncoding:"base64"`，描述明确 little-endian float32）。**不证明什么**：不证明 `float`（默认）表示的形状/有限性（DP-EMB-01），不证明重复不变量（DP-EMB-03），不证明未知 model（DP-EMB-04）、batch>1（DP-EMB-05）、`dimensions` 不符（DP-EMB-06）、非法 `encoding_format`（DP-EMB-07）；不对向量语义/L2 归一化数值做门限。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，角色 `data`，只读/无状态；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 6 项就绪检查；任一失败 → 整班 BLOCKED/SKIP，不得改用模拟路径。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`api_client`（`httpx.Client`，`Authorization: Bearer dev-data`）。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier；`Embedding-v1` 已启用（上游本地 bge-m3，LAN，TS-003）。本 case 为纯读。
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
    "input": "Hello world",
    "encoding_format": "base64"
  }
  ```

  边界/构造点：`encoding_format` 取合法枚举值 `base64`（非 `float`、非非法值——后者属 DP-EMB-07）；`input` 取字符串；`model="Embedding-v1"`；不注入故障。独立解码所需的 `base64`/`struct` 标准库由测试侧使用，不依赖被测实现。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（`pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = api_client.post("/v1/embeddings", json={"model": "Embedding-v1", "input": "Hello world", "encoding_format": "base64"})`；记录 status、`Content-Type`、body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`；确认非错误信封。
  4. 断言顶层键集恰为 `{object,data,model,usage}` 且 `object=="list"`、`model=="Embedding-v1"`；`data` 非空。
  5. 取 `emb = data[0]["embedding"]`，断言 `isinstance(emb, str)`（base64 形态**必须是字符串**，不得是 JSON 数组）。
  6. 独立解码：`raw = base64.b64decode(emb, validate=True)`；断言 `len(raw) == 4096`；`arr = struct.unpack("<" + "f" * (len(raw)//4), raw)`；断言 `len(arr) == 1024` 且 `all(math.isfinite(v) for v in arr)`。
  7. （可选、非门限）比较同输入下 `encoding_format` 缺省（float）与 `base64` 的向量关系（同源应一致），仅作旁证，不作为本 case PASS 条件。
- **重点关注步骤**：① **类型区分**——base64 路径返回**字符串**；若返回 JSON 数组说明忽略/未实现 `encoding_format`，判 FAIL；② **严格解码**——用 `validate=True`（实现 [`embeddings.py`](../../../../src/inference/embeddings.py) 第 55 行亦以 `validate=True` 校验）确保无非法字符/填充；③ **字节数 = 4096**——1024×4 字节，是维度契约的强证据，避免只解出任意长度；④ **little-endian float32**——`struct.unpack("<f")`，字节序错会得到不同数值但不报错，需以 `<` 明确；⑤ **finite 检查**——解码后仍须 `isfinite`（base64 可承载 `NaN`/`Inf` 位模式）；⑥ **独立 Oracle**——测试侧自行 base64 解码，不能只依赖实现"返回 200 即视为合法"（200 只说明实现内部 round-trip 通过）。
- **期望结果与独立 Oracle**：独立 Oracle = [openapi](../../../../interfaces/openapi/llmtier.openapi.json) `EmbeddingItem.embedding`（`contentEncoding:"base64"` + "contiguous little-endian IEEE-754 float32"）与 `bge-m3-dense-1024-v1` 的 1024 维契约。
  - HTTP：`200`；`Content-Type: application/json`；`X-Request-ID` 存在。
  - 顶层 body 键集恰为 `{object,data,model,usage}`；`object=="list"`；`model=="Embedding-v1"`。
  - `data[0]`：`object=="embedding"`、`index==0`；`embedding` 为 `str`。
  - 解码：`len(base64.b64decode(embedding, validate=True)) == 4096`；`struct.unpack("<1024f", raw)` 得 1024 个 float32，全部 finite。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200`，键集/Oracle 一致，`embedding` 为合法 base64 字符串，独立解码后恰 1024 个 little-endian float32 且全部 finite。
  - **FAIL**：status 非 200、`embedding` 非字符串、base64 非法/长度非 4096/解码非 1024/含非有限值，或以错误信封冒充成功。
  - **BLOCKED**：测试代码/契约本身问题（解码器/断言逻辑错等）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实实例，或用 B 类结果冒充 A 类——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：有实现（§3.2 `RUN`）但本轮未执行——按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存原始 HTTP status/headers/body（脱敏后）、测试侧解码脚本与 `raw` 字节数/`arr` 摘要、发出命令、exit code、`elapsed`、环境快照。`manifest.json` 含 `{run_id, case_id, target_artifact{git_commit, db_schema_version, openapi_version}, environment:"a", inputs, oracle, actual, verdict, evidence_files, redactions, reproduction_cmd}`（[测试设计 §4.8](../llmtier-api-test-specification.md)）。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/dp-emb-02/`，失败现场不截断（[测试设计 §10](../llmtier-api-test-specification.md)）。
- **清理与复位**：**无需 teardown**——只读 embedding 调用，不改配置/不写注入项；不删除既有资源或用户 usage。退出前确认 `/readyz` 7 tier、无未清空注入项；若误跑于 B 类实例，按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班销毁。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client` fixture（[测试设计 §4.4](../llmtier-api-test-specification.md)）；`Embedding-v1` 上游 tier；`EmbeddingItem.embedding` 机器契约（[openapi](../../../../interfaces/openapi/llmtier.openapi.json)）；实现 [`src/inference/embeddings.py`](../../../../src/inference/embeddings.py)（第 53–58 行解码分支）；自动化入口 [`at_dp_emb_02.py`](../../../../tests/system/api_test_v03/at_dp_emb_02.py)。**不依赖**其它 Case；与 DP-EMB-01（float 形态）互补、各自独立执行。
