# DP-EMB-07 — 非法 encoding_format

- **Case ID**：`DP-EMB-07`（与 §3.2 权威清单一致；本文件名 `dp-emb-07.md`，唯一对应）。
- **标题**：`POST /v1/embeddings` `encoding_format=hex`（非 `float|base64`）：返回 `400 invalid_request`（`ERR-REQ-VALIDATION`），不触上游。
- **目的（被测契约）**：验证 `POST /v1/embeddings` 对**非法 `encoding_format` 枚举值**的拒绝语义。被测端点/规则：`encoding_format` 仅允许 `float|base64`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `EmbeddingRequest.encoding_format.enum`）；取非法值 `"hex"` 时应在 dispatch 之前被拒，返回 `ErrorEnvelope`，HTTP `400` 且 `error.code=="invalid_request"`（`ERR-REQ-VALIDATION`，系统设计 §7.8，见[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md)），`type=="request_error"`、`retryable==false`。设计验证项 `VRC-INF-001`；需求 `LT-FUN-003`（[requirements](../../../10_requirements/llmtier-requirements.md)）；机制需求 `R-INF-04`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；契约 `CT-EMB-001`；错误映射见[测试设计 §11.1](../llmtier-api-test-specification.md)（`ERR-REQ-VALIDATION` → `DP-EMB-07`）。**同一校验分支的相邻负向（"缺/多字段"）**：`EmbeddingRequest` 顶层 `additionalProperties:false` 且 `required:[model,input]`；缺 `model`/`input` 或带未知顶层键时，[`src/inference/embeddings.py`](../../../../src/inference/embeddings.py) 第 32 行 `require(set(body) <= {model,input,encoding_format,dimensions,user} and {model,input} <= set(body), 400, "invalid_request", ...)` 亦返回 `400 invalid_request`（该 `require` 未传 `param`，故 `param==null`）。本 case 的可选加强项即覆盖该类"invalid input"。**不证明什么**：不证明合法 `float`/`base64` 的成功（DP-EMB-01/02），不证明未知 model（DP-EMB-04）、`dimensions` 不符（DP-EMB-06）、batch（DP-EMB-05）；**不声称**本 case 已实现（§3.2 `MISSING`，无 `at_dp_emb_07.py`）。
> **已知实现偏差（执行前必读）**：当前源码**只校验请求键集、model 存在性与 `embeddings` 能力、`dimensions` 成员，未对 `encoding_format` 的**枚举值**做校验**——`create()` 中 `encoding = body.get("encoding_format","float")`（第 33 行）后仅判断 `if encoding == "base64": ... else: values = vector`（第 52–57 行），即 `"hex"` 会被当作非 base64（float）路径处理。因此设计期望的 `400 invalid_request` **在现存实现中不可达**：在 B 类基线 `_BASELINE_SETTINGS` 下，`depl_b.capabilities.embeddings==false`（[`conftest.py`](../../../../tests/system/api_test_v03/conftest.py)），请求会先命中第 40 行 `unsupported_model`（`param="model"`）而非编码校验；在 A 类 m5air（`Embedding-v1` embeddings-capable）下则可能被上游忽略 `hex` 而返回 200。**结论**：本 case 是一处**设计↔实现缺口**，执行时若实测非 `400 invalid_request`，按 FAIL 登记并写明实现未做 `encoding_format` 值校验（不得回写设计迁就实现）。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 `127.0.0.1:<随机空闲端口>` + 临时 SQLite，同机第二个进程；见[测试设计 §2.3](../llmtier-api-test-specification.md) / §2.4 B 类）。执行前必须满足[测试设计 §2.1](../llmtier-api-test-specification.md) 的**附加（B 类）**：临时实例可启动且 `GET /healthz` 200；`_BASELINE_SETTINGS` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier；否则整班 BLOCKED/SKIP。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`llmtier_b`（session-scope 临时实例，提供 `base_url`）、`api_client_b`（`httpx.Client`，`Authorization: Bearer dev-data`）。**fixture 局限（须登记）**：基线 `depl_b` 的 `capabilities.embeddings=false`，没有 embeddings-capable 部署；若要在 B 类隔离"`encoding_format` 值校验"，需要一个 `embeddings:true` 且 `embedding_dimensions` 就绪的部署（可经 admin API 在临时实例内创建，或改在 A 类 `Embedding-v1` 上执行），否则 B 类基线会以 `unsupported_model` 抢先，令本 case 无法判定编码校验。TS-003：B 类内部上游 provider endpoint 必须是 LAN IP（本 case 若被 capability/编码校验前置拒绝，不会触上游）。
- **输入与构造**：固定请求：

  ```http
  POST /v1/embeddings HTTP/1.1
  Host: 127.0.0.1:<port>
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

  边界/构造点：`encoding_format="hex"` 为**非空字符串**但**不在** `enum:[float,base64]` 内；`input`/`model` 取合法值，使（若实现有值校验）失败点唯一落在编码格式。**可选加强负向**（同一校验分支）：分别构造缺 `input`、缺 `model`、带未知顶层键（如 `"foo":1`）的 body，期望均为 `400 invalid_request`（`param==null`）。非法值 `"hex"` 及缺字段构造随 Run manifest 固定。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` 启动并轮询 `/healthz` 200；确认基线 provider/deployment/tier。
  2. （推荐前置，若在 B 类执行）经 `admin_client_b` 在临时实例创建/启用一个 embeddings-capable 部署并让 `Embedding-v1` 指向它（或直接将本 case 置于 A 类 `Embedding-v1`），以隔离编码校验、避免 `unsupported_model` 抢先。
  3. （可选）记录 `GET /v1/usage` 基线，用于证明零副作用。
  4. `resp = api_client_b.post("/v1/embeddings", json={"model": "Embedding-v1", "input": "Hello world", "encoding_format": "hex"})`；记录 status、headers、body。
  5. 断言 `resp.status_code == 400`；body 为错误信封。
  6. 解析 `err = resp.json()["error"]`：断言键集恰为 `{message,type,code,param,retryable}`，`err["code"]=="invalid_request"`、`err["type"]=="request_error"`、`err["retryable"] is False`；`param` 期望为 `"encoding_format"`（值级枚举校验的语义自然 param；**当前实现无值级校验**，见偏差段，若实测走键集 `require` 则 `param==null`，须在报告中如实记录）。断言前**先接受 `param ∈ {"encoding_format", null}` 并记录实测值**，不因 `param` 形态掩盖核心 `code` 判定。
  7. （可选加强）对缺 `input`/缺 `model`/未知顶层键各发一次，断言均 `400 invalid_request`（`param==null`），覆盖"invalid input"路径。
  8. （可选）核对 usage 基线未新增 dispatch。
- **重点关注步骤**：① **错误码 `invalid_request` 与 `param`**——核心 Oracle 是 `400 + invalid_request`；`param` 的自然期望为 `"encoding_format"`，但当前 `require`（键集）不传 param，实测须如实记录两者差异；② **实现未做值校验的缺口**——`encoding_format` 值未进入任何 `require`，`"hex"` 在 B 类基线会先触发 `unsupported_model`（第 40 行）、在 A 类可能 200；这是本 case 可能 FAIL 的根因，必须在报告中登记为"实现缺口/设计未落地"，而非把结果读成"契约成立"；③ **capability 抢先**——确保 `model` 指向 embeddings-capable 部署，否则观测到的 400 不是编码校验；④ **零副作用**——校验失败须在 dispatch 前完成（第 43 行 `authorize_dispatch` 之前），无上游调用/无账本义务，以 usage 交叉核对；⑤ **MISSING 事实**——本 case 当前 `MISSING`（§3.2），**尚无** `at_dp_emb_07.py`；判定按 NOT_RUN，不得以其它 emb case 的通过冒充（[测试设计 §4.9](../llmtier-api-test-specification.md)）；⑥ **B 类基线不含 embeddings**——计划以 B 类承接本 case，但 `_BASELINE_SETTINGS` 的 `depl_b` 为 `embeddings:false`，须补 fixture 或改 A 类，见"前置与环境"。
- **期望结果与独立 Oracle**：独立 Oracle = [openapi](../../../../interfaces/openapi/llmtier.openapi.json) `EmbeddingRequest.encoding_format.enum`（+ `additionalProperties:false`/`required`）+ `ErrorEnvelope`（`code=="invalid_request"`）+ [测试设计 §3.2/§11.1](../llmtier-api-test-specification.md)。
  - HTTP：`400`；`Content-Type: application/json`。
  - body：`{"error":{"message":<str>,"type":"request_error","code":"invalid_request","param":<"encoding_format"|null>,"retryable":false}}`。
  - 可选加强（缺字段/未知键）：同形 `400 invalid_request`，`param==null`。
  - 无成功字段；无上游 dispatch、无账本新增义务（可选交叉核对）。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==400` 且 `error.code=="invalid_request"`、`type=="request_error"`、`retryable is False`，键集恰 5（`param` 记录实测，不因形态另判）；且（若核对）无新账本义务。
  - **FAIL**：status 非 400、`code` 非 `invalid_request`（如 `unsupported_model`、`provider_error`）、`type`/`retryable` 不符、键集多/缺，或产生上游调用/账本义务——尤其当 `"hex"` 被当作合法值时，登记**实现未校验 `encoding_format` 值**的缺口。
  - **BLOCKED**：测试代码/契约/fixture 问题（B 类基线无 embeddings-capable 部署、断言不可执行）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 附加（B 类）前置不满足（临时实例不可启动、上游不可达等）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：注入/替代路径冒充真实路径，或以 A 类结果冒充 B 类（或反之）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 case 自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见[测试设计 §9](../llmtier-api-test-specification.md)（MISSING ≠ NOT_RUN）。
- **证据与 Run**：保存临时实例 fixture settings/初态、请求/响应（status/headers/body，脱敏后）、可选 usage 前后快照、若做了 fixture 补强则保存 admin 建部署/改指向的请求响应、发出命令、exit code、`elapsed`、环境快照（`/healthz` + provider/deployment 列表）。`manifest.json` 含 `{run_id, case_id, target_artifact{git_commit, db_schema_version, openapi_version}, environment:"b", inputs, oracle, actual, verdict, evidence_files, redactions, reproduction_cmd}`（[测试设计 §4.8](../llmtier-api-test-specification.md)）。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/dp-emb-07/`，失败现场不截断（[测试设计 §10](../llmtier-api-test-specification.md)）。
- **清理与复位**：若在 B 类执行，**整班结束由 fixture `stop()`（`terminate`→等待 5s→`kill`）+ `rm -rf` 临时目录销毁**（[测试设计 §2.8/§4.7](../llmtier-api-test-specification.md)）；若在临时实例内经 admin 补建了 embeddings-capable 部署/改了 `Embedding-v1` 指向，应在离开前 `DELETE`/复原（B 类一次性，但保持 fixture 语义）。本 case 被拒请求无账本/注入副作用。若在 A 类执行，则**无需 teardown**，退出前确认 `/readyz` 7 tier、无未清空注入项。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 附加（B 类）前置；B 类 fixture `llmtier_b` / `api_client_b`（[测试设计 §4.4](../llmtier-api-test-specification.md)）；`EmbeddingRequest.encoding_format` 机器契约（[openapi](../../../../interfaces/openapi/llmtier.openapi.json)）；实现 [`src/inference/embeddings.py`](../../../../src/inference/embeddings.py) 第 32/33/52–57 行与 [`src/inference/routing.py`](../../../../src/inference/routing.py)；`ErrorDetail.code` 机器契约；**依赖一个 embeddings-capable 部署**（B 基线 `depl_b` 不满足，须补 fixture 或改 A 类）。自动化入口 `at_dp_emb_07.py`（**当前 `MISSING`，尚未实现**，落位按[测试设计 §4.9/§8.5](../llmtier-api-test-specification.md)）。**不依赖**其它 Case；与 DP-EMB-06（`dimensions` 不符）同属 embeddings 本地校验负向，各自独立执行。
