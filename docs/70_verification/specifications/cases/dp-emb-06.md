# DP-EMB-06 — dimensions 与冻结空间不符

- **Case ID**：`DP-EMB-06`（与 §3.2 权威清单一致；本文件名 `dp-emb-06.md`，唯一对应）。
- **标题**：`POST /v1/embeddings` `dimensions=768`（与 `Embedding-v1` 冻结向量空间不符）：返回 `400 unsupported_dimensions`（`param="dimensions"`），不触上游。
- **目的（被测契约）**：验证 `POST /v1/embeddings` 对**与冻结向量空间不符的 `dimensions`** 的拒绝语义。被测端点/规则：`model="Embedding-v1"`（冻结空间 `bge-m3-dense-1024-v1`，`embedding_dimensions=[1024]`）、`dimensions=768`；请求在 dispatch 之前被拒，返回 [openapi](../../../../interfaces/openapi/llmtier.openapi.json) `ErrorEnvelope`，HTTP `400` 且 `error.code=="unsupported_dimensions"`（`ERR-REQ-DIM`，系统设计 §7.8，见[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md)）、`param=="dimensions"`、`type=="request_error"`、`retryable==false`。设计验证项 `VRC-INF-001`；需求 `LT-FUN-003`/`LT-OPEN-02`（[requirements](../../../10_requirements/llmtier-requirements.md)）；机制需求 `R-INF-04`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；契约 `CT-EMB-001`；错误映射见[测试设计 §11.1](../llmtier-api-test-specification.md)（`ERR-REQ-DIM` → `DP-EMB-06`）。实现见 [`src/inference/embeddings.py`](../../../../src/inference/embeddings.py) 第 42–43 行：`if body.get("dimensions") is not None and caps.get("embedding_dimensions"): require(body["dimensions"] in caps["embedding_dimensions"], 400, "unsupported_dimensions", "Unsupported embedding dimensions", "dimensions")`。**不证明什么**：不证明合法 `dimensions=1024` 的成功（未被 §3.2 单列），不证明未知 model（DP-EMB-04）、非法 `encoding_format`（DP-EMB-07）、batch 上限（DP-EMB-05）、base64 形态（DP-EMB-02）；不证明 `dimensions` 的 `minimum:1` 边界（openapi 层约束）或上游对该参数的实际行为（本 case 在本地即被拒，不上游）。
- **前置与环境**：**环境 A**（m5air 已部署实例；角色 `data`，只读/无状态；见[§2.3](../llmtier-api-test-specification.md)）。执行前必须通过[§2.1](../llmtier-api-test-specification.md) 的 6 项就绪检查（详见 §2.1）；任一失败 → 整班 BLOCKED/SKIP。fixture（[§4.4](../llmtier-api-test-specification.md)）：`api_client`。初始状态：`Embedding-v1` 已启用且 `capabilities.embedding_dimensions==[1024]`（与 `registry.py` 第 320 行冻结校验一致）。本 case 为纯负向读，无副作用。
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
    "dimensions": 768
  }
  ```

  边界/构造点：`dimensions=768` 为**正整数、语法合法**（满足 `EmbeddingRequest.dimensions.minimum:1`）但**不在** `embedding_dimensions=[1024]` 内，确保失败点在冻结空间成员校验而非形态校验；`input`/`model` 均取合法值。若请求同时带非法 `model`，会先命中 404 而掩盖本码——故模型固定为已启用 tier。768 字面量随 Run manifest 固定。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（`pytest_configure` 自动执行，本 case 不重复）。
  2. （前置证据）`GET /v1/models/Embedding-v1` 读取 `capabilities.embedding_dimensions`，断言为 `[1024]`——这是判定"768 不符"的事实依据。
  3. （可选前置）`GET /v1/usage` 记录 usage 基线，用于证明**无新增账本义务**（[测试设计 §4.6](../llmtier-api-test-specification.md)）。
  4. `resp = api_client.post("/v1/embeddings", json={"model": "Embedding-v1", "input": "Hello world", "dimensions": 768})`；记录 status、headers、body。
  5. 断言 `resp.status_code == 400`；`body` 为错误信封（无顶层 `object`/`data`）。
  6. 解析 `err = resp.json()["error"]`：断言键集恰为 `{message,type,code,param,retryable}`，`err["code"]=="unsupported_dimensions"`、`err["param"]=="dimensions"`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  7. （可选）核对 usage 基线未新增 dispatch。
- **重点关注步骤**：① **精确错误码与 `param`**——`unsupported_dimensions` + `param="dimensions"`（见 `require(..., "dimensions")` 第 43 行）；写成 `invalid_request` 或 `param=null` 即 FAIL；② **冻结空间成员语义**——比较对象是 `capabilities.embedding_dimensions` 列表（`[1024]`），不是单值；`dimensions` 必须是该列表成员；③ **不被后置错误掩盖**——必须确保 `model` 已启用且 embeddings-capable，否则会先命中 404/`unsupported_model`；④ **零副作用**——400 在 dispatch 之前（第 44 行 `authorize_dispatch` 之前即已 `require`），无上游调用、无账本义务，以 usage 交叉核对；⑤ **`dimensions` 缺省不受影响**——`body.get("dimensions") is not None and caps.get("embedding_dimensions")` 双重条件：缺省时不进入校验（合法），本 case 仅覆盖"提供且不符"；⑥ **MISSING 事实**——本 case 当前 `MISSING`（§3.2），**尚无** `at_dp_emb_06.py`；判定按 NOT_RUN，不得以邻近 `at_dp_emb_01..05.py` 的通过冒充本 case 通过（[测试设计 §4.9](../llmtier-api-test-specification.md)）。
- **期望结果与独立 Oracle**：独立 Oracle = [openapi](../../../../interfaces/openapi/llmtier.openapi.json) `ErrorEnvelope`/`ErrorDetail`（`code` enum 含 `unsupported_dimensions`）+ `Embedding-v1` 冻结空间 `embedding_dimensions=[1024]` + [测试设计 §3.2/§11.1](../llmtier-api-test-specification.md)。
  - HTTP：`400`；`Content-Type: application/json`。
  - body：`{"error":{"message":<str>,"type":"request_error","code":"unsupported_dimensions","param":"dimensions","retryable":false}}`。
  - 无成功字段；无上游 dispatch、无账本新增义务（可选交叉核对）。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==400` 且 `error.code=="unsupported_dimensions"`、`param=="dimensions"`、`type=="request_error"`、`retryable is False`，键集恰 5；且（若核对）无新账本义务。
  - **FAIL**：status 非 400、`code`/`param`/`type`/`retryable` 不符、键集多/缺，或产生上游调用/账本义务。
  - **BLOCKED**：测试代码/契约本身问题（入口待实现导致断言不可执行等）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实实例，或用 B 类结果冒充 A 类——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 case 自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见[测试设计 §9](../llmtier-api-test-specification.md)（MISSING ≠ NOT_RUN：无实现是缺口，不是跳过）。
- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-api-test-specification.md)：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、`/v1/models/Embedding-v1` 的 `embedding_dimensions` 快照、请求/响应、可选 usage 前后快照、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。
- **清理与复位**：**无需 teardown**——被拒请求，无配置/资源/注入改动，无用户 usage 删除。退出前确认 `/readyz` 7 tier、无未清空注入项；若误跑于 B 类实例，按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班销毁。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client` fixture（[测试设计 §4.4](../llmtier-api-test-specification.md)）；`Embedding-v1` 冻结空间 `embedding_dimensions=[1024]`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) + [`src/management/registry.py`](../../../../src/management/registry.py) 第 320 行）；实现 [`src/inference/embeddings.py`](../../../../src/inference/embeddings.py) 第 42–43 行；`ErrorDetail.code` 机器契约。自动化入口 `at_dp_emb_06.py`（**当前 `MISSING`，尚未实现**，落位按[测试设计 §4.9/§8.5](../llmtier-api-test-specification.md)）。**不依赖**其它 Case；与 DP-EMB-07（非法 `encoding_format`）同属 embeddings 本地校验负向，各自独立执行。
