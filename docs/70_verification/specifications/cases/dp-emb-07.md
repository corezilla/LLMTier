# DP-EMB-07 — 非法 encoding_format

- **Case ID**：`DP-EMB-07`（与 §3.2 权威清单一致；本文件名 `dp-emb-07.md`，唯一对应）。
- **标题**：`POST /v1/embeddings` `encoding_format=hex`（非 `float|base64`）：返回 `400 invalid_request`（`param="encoding_format"`），不触上游。
- **目的（被测契约）**：验证 `POST /v1/embeddings` 对**非法 `encoding_format` 枚举值**的拒绝语义。被测端点/规则：`encoding_format` 仅允许 `float|base64`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `EmbeddingRequest.encoding_format.enum`）；取非法值 `"hex"` 时应在 dispatch 之前被拒，返回 `ErrorEnvelope`，HTTP `400` 且 `error.code=="invalid_request"`（`ERR-REQ-VALIDATION`，系统设计 §7.8，见[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md)），`param=="encoding_format"`、`type=="request_error"`、`retryable==false`。实现 [`src/inference/embeddings.py`](../../../../src/inference/embeddings.py) 第 34 行：`require(encoding in {"float","base64"}, 400, "invalid_request", "encoding_format must be one of: float, base64", "encoding_format")`——该值级校验在 model/`embeddings` 能力/`dimensions` 校验与 `authorize_dispatch`（第 44 行）之前，故非法值零副作用被拒。**同一校验分支的相邻负向（"缺/多字段"）**：`EmbeddingRequest` 顶层 `additionalProperties:false` 且 `required:[model,input]`；缺 `model`/`input` 或带未知顶层键时，[`src/inference/embeddings.py`](../../../../src/inference/embeddings.py) 第 32 行 `require(set(body) <= {model,input,encoding_format,dimensions,user} and {model,input} <= set(body), 400, "invalid_request", ...)` 亦返回 `400 invalid_request`（该 `require` 未传 `param`，故 `param==null`）。本 case 的可选加强项即覆盖该类"invalid input"。设计验证项 `VRC-INF-001`；需求 `LT-FUN-003`（[requirements](../../../10_requirements/llmtier-requirements.md)）；机制需求 `R-INF-04`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；契约 `CT-EMB-001`；错误映射见[测试设计 §11.1](../llmtier-api-test-specification.md)（`ERR-REQ-VALIDATION` → `DP-EMB-07`）。**不证明什么**：不证明合法 `float`/`base64` 的成功（DP-EMB-01/02），不证明未知 model（DP-EMB-04）、`dimensions` 不符（DP-EMB-06）、batch（DP-EMB-05）、base64 形态（DP-EMB-02）；**不声称**本 case 已实现（§3.2 `MISSING`，无 `at_dp_emb_07.py`）。
- **前置与环境**：**环境 A**（m5air 已部署实例；角色 `data`，只读/无状态；见[§2.3](../llmtier-api-test-specification.md)）。执行前必须通过[§2.1](../llmtier-api-test-specification.md) 的 6 项就绪检查（详见 §2.1）；任一失败 → 整班 BLOCKED/SKIP。fixture（[§4.4](../llmtier-api-test-specification.md)）：`api_client`。初始状态：m5air 现有 3 provider / 4 deployment / 7 fixed tier。**A 类构造**：A 基线（§2.1.6）的 `dep_local_bge_m3` 为 embeddings-capable，固定 tier `Embedding-v1` 指向它，故 `model="Embedding-v1"` 能通过 model/`embeddings` 能力校验，使失败点唯一落在 `encoding_format` 值校验，不会先命中 `unsupported_model`/404。本 case 为纯负向读，无副作用。
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
    "encoding_format": "hex"
  }
  ```

  边界/构造点：`encoding_format="hex"` 为**非空字符串**但**不在** `enum:[float,base64]` 内；`input`/`model` 取合法值（`Embedding-v1` 指向 embeddings-capable 的 `dep_local_bge_m3`），使失败点唯一落在编码格式值校验。**可选加强负向**（同一校验分支）：分别构造缺 `input`、缺 `model`、带未知顶层键（如 `"foo":1`）的 body，期望均为 `400 invalid_request`（`param==null`）。非法值 `"hex"` 及缺字段构造随 Run manifest 固定。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（`pytest_configure` 自动执行，本 case 不重复）。
  2. （可选）记录 `GET /v1/usage` 基线，用于证明零副作用。
  3. `resp = api_client.post("/v1/embeddings", json={"model": "Embedding-v1", "input": "Hello world", "encoding_format": "hex"})`；记录 status、headers、body。
  4. 断言 `resp.status_code == 400`；body 为错误信封（无顶层 `object`/`data`）。
  5. 解析 `err = resp.json()["error"]`：断言键集恰为 `{message,type,code,param,retryable}`，`err["code"]=="invalid_request"`、`err["param"]=="encoding_format"`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  6. （可选加强）对缺 `input`/缺 `model`/未知顶层键各发一次，断言均 `400 invalid_request`（`param==null`），覆盖"invalid input"路径。
  7. （可选）核对 usage 基线未新增 dispatch。
- **重点关注步骤**：① **错误码 `invalid_request` 与 `param="encoding_format"`**——核心 Oracle 是 `400 + invalid_request`，且因第 34 行 `require(..., "encoding_format")` 显式传参，`param` 必须为 `"encoding_format"`；写成 `null` 即 FAIL；② **值级校验已落地**——`encoding_format` 值进入第 34 行 `require`，非法值在 model/能力/`dimensions` 校验之前被拒，不会再出现"被 `unsupported_model` 抢先"或"上游忽略 `hex` 返回 200"；③ **model 指向 embeddings-capable tier**——`Embedding-v1` 必须指向 `dep_local_bge_m3`（A 基线），否则观测到的 400 不是编码值校验（本 case 应命中第 34 行而非第 41 行 `unsupported_model`）；④ **零副作用**——校验失败须在 dispatch 前完成（第 44 行 `authorize_dispatch` 之前），无上游调用/无账本义务，以 usage 交叉核对；⑤ **MISSING 事实**——本 case 当前 `MISSING`（§3.2），**尚无** `at_dp_emb_07.py`；判定按 NOT_RUN，不得以其它 emb case 的通过冒充（[测试设计 §4.9](../llmtier-api-test-specification.md)）；⑥ **相邻负向边界**——缺字段/未知顶层键走第 32 行键集 `require`，其 `param==null`，与值级校验的 `param=="encoding_format"` 区分记录。
- **期望结果与独立 Oracle**：独立 Oracle = [openapi](../../../../interfaces/openapi/llmtier.openapi.json) `EmbeddingRequest.encoding_format.enum`（+ `additionalProperties:false`/`required`）+ `ErrorEnvelope`（`code=="invalid_request"`）+ [测试设计 §3.2/§11.1](../llmtier-api-test-specification.md)。
  - HTTP：`400`；`Content-Type: application/json`。
  - body：`{"error":{"message":<str>,"type":"request_error","code":"invalid_request","param":"encoding_format","retryable":false}}`。
  - 可选加强（缺字段/未知键）：同形 `400 invalid_request`，`param==null`。
  - 无成功字段；无上游 dispatch、无账本新增义务（可选交叉核对）。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==400` 且 `error.code=="invalid_request"`、`param=="encoding_format"`、`type=="request_error"`、`retryable is False`，键集恰 5；且（若核对）无新账本义务。
  - **FAIL**：status 非 400、`code` 非 `invalid_request`（如 `unsupported_model`、`provider_error`）、`param` 非 `"encoding_format"`、`type`/`retryable` 不符、键集多/缺，或产生上游调用/账本义务——尤其当 `"hex"` 被当作合法值时，登记**实现未校验 `encoding_format` 值**的缺口。
  - **BLOCKED**：测试代码/契约本身问题（`api_client` 写不出、断言逻辑错、`param` 语义不清等）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（m5air 不可达、`/readyz` 非 7 tier、双 OMLX 离线等）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或用 B 类结果冒充 A 类——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 case 自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见[测试设计 §9](../llmtier-api-test-specification.md)（MISSING ≠ NOT_RUN）。
- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-api-test-specification.md)：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：请求/响应（status/headers/body，脱敏后）、可选 usage 前后快照、发出命令、exit code、`elapsed`、环境快照（`/healthz` + provider/deployment 列表；确认 `Embedding-v1`→`dep_local_bge_m3`）。
- **清理与复位**：**无需 teardown**——本 case 为被拒请求，不改 provider/deployment/service-level、不写注入项、不删除用户 usage。退出前确认 `/readyz` 7 tier、无未清空注入项；若误跑于 B 类实例，按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班销毁。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client` fixture（[测试设计 §4.4](../llmtier-api-test-specification.md)）；A 基线 embeddings-capable 部署 `dep_local_bge_m3` / 固定 tier `Embedding-v1`（§2.1.6）；`EmbeddingRequest.encoding_format` 机器契约（[openapi](../../../../interfaces/openapi/llmtier.openapi.json)）；实现 [`src/inference/embeddings.py`](../../../../src/inference/embeddings.py) 第 32/33/34/53–58 行与 [`src/inference/routing.py`](../../../../src/inference/routing.py)；`ErrorDetail.code` 机器契约。自动化入口 `at_dp_emb_07.py`（**当前 `MISSING`，尚未实现**，落位按[测试设计 §4.9/§8.5](../llmtier-api-test-specification.md)）。**不依赖**其它 Case；与 DP-EMB-06（`dimensions` 不符）同属 embeddings 本地校验负向，各自独立执行。
