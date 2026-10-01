<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-EMB-010 — embeddings 上游不可用 503

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-EMB-010` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-10-01` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-EMB-010.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-EMB-010` / 系统设计 §8 Embeddings 接口（POST /v1/embeddings） / `VRC-INF-004` / recovery / P1（[方案清单 `ST-EMB-010`](../llmtier-system-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：故障注入（上游 5xx/不可达 → 503）+ 复位阶梯

- 要测什么（责任展开）：`POST /v1/embeddings` 上游 5xx/不可达：`503 provider_unavailable`。适配层把上游 `HTTPError>=500`、`URLError`、超时、JSON 解码失败统一映射为 `503 provider_unavailable`。需求 `R-INF-05`；错误目录 `ERR-PROVIDER-UNAVAIL` → wire `code=provider_unavailable`；实现 `src/inference/providers/openai.py::_request`（`except HTTPError: exc.code>=500 → ApiError(503, "provider_unavailable", retryable=True)`；`except (URLError, TimeoutError, JSONDecodeError) → 同码`）。

- 明确不测什么 / 失败含义：不测上游非 5xx（`provider_error`，状态码随上游）；不测契约错误（ST-EMB-009）；不测上游凭据文件不可读（`provider_secret_unavailable`）；不测 Responses 的 `provider_unavailable`（ST-RESP-022 注入 / ST-RESP-024 凭据）；不测模型/维度校验。失败含义＝上游不可用被误报为其它码或成功。

**目的（被测契约）**：验证 **Embeddings 上游不可用的归一契约**。被测端点/规则：`POST /v1/embeddings`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `createEmbedding`，声明 `503`）；入口经 [`EmbeddingsService.create`](../../../../src/inference/embeddings.py) 调用 [`OpenAIProvider.embed`](../../../../src/inference/providers/openai.py) → `_request`，上游 5xx 映射为 `503 provider_unavailable`。设计验证项 `VRC-INF-004`；机制 `E-INF-UPSTREAM`。**不证明什么**：不测非 5xx、契约错误（ST-EMB-009）、凭据不可读、Responses 同类码。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例，专属实例）。前置 = 方案 §5 附加（B 类）就绪检查；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。`prov_b.endpoint` 必须是 LAN IP 上的 fake provider（TS-003，`tests/fixtures/v03_fake_provider.py`）。**构造点**：fake provider 对 `model == "force-503"` 的任意 POST 返回 `503`（`v03_fake_provider.py:30`）；故把 `depl_b.backend_model` 设为 `force-503`，使上游收到 `model="force-503"` 并返回 503；同时 fake provider 的 `/models` 仍 200，保证 probe `depl_b=healthy`。
- **被测入口**：

  ```http
  POST /v1/embeddings HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-data
  Content-Type: application/json
  ```

- **初态构造（经公开入口）**：专属实例以 `depl_b.backend_model="force-503"` 启动并 probe `healthy`；`diagnostic_injections` 为空。
- **Fixture / 向量及版本**：专属 `LLMTierInstance`、`api_client_b`；`backend_model="force-503"` 的 `_baseline_settings`，随 Run manifest 存档。
- **依赖的测试资产（tests.asset-design 文档）**：B 类实例与 fake provider 契约见方案 §4；TS-003 LAN endpoint。

## 3. 输入构造

- **逐参数输入构造**：

  ```json
  {"model": "Senior", "input": "hello"}
  ```

- **边界/非法取值及理由**：`depl_b.backend_model="force-503"` 使上游对 Embeddings 请求返回 503；`model="Senior"` 指向唯一 deployment `depl_b`；`input` 提供合法值，避免 400 校验掩盖 503。变体（可选）：把 `prov_b.endpoint` 指向同 LAN 上**未监听**端口并重 probe → 上游不可达，同样应得 `503 provider_unavailable`（`URLError` 分支）；重指 endpoint 须在 teardown 复位。
- **规模 / 时间域**：单次请求；stub 快速返回。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | （fixture 前置）启动专属实例（`backend_model="force-503"`）并 probe `depl_b` → `healthy` | 实例就绪 |
| 2 | `POST /v1/embeddings`（上表 body） | 普通 JSON 错误信封 |
| 3 | 断言 `status_code == 503`；解析 `error` | `code=="provider_unavailable"`、`type=="server_error"`、`retryable is True`、`param is None`，键集恰 5 键 |
| 4 | （可选）endpoint 指向死端口变体 | 同样 503 + `provider_unavailable` |
| 5 | （teardown）若改了 endpoint，复位为 LAN fake provider | `GET /v1/providers/prov_b` 恢复 |

- **重点关注步骤**：① **503 + `provider_unavailable`**——上游 5xx/不可达的统一映射；② **不是 502**——502 属契约错误（ST-EMB-009）；③ **`retryable=true`**（实现默认，上游瞬时故障）；④ **信封 identity**（5 键、`type=server_error`）；⑤ **`message` 反映上游 HTTP 状态/传输失败**；⑥ **不改动 provider 配置**（首选 `force-503` 法，避免 endpoint 重指）。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **独立 Oracle 来源与推导**：OpenAPI `ErrorEnvelope`/`ErrorDetail` + `ERR-PROVIDER-UNAVAIL`（不依赖实现答案）。
  - HTTP `503`；`Content-Type: application/json`；`error.code=="provider_unavailable"`、`type=="server_error"`、`param=null`、`retryable=true`；无成功 `data` 载荷。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`503` + `code=="provider_unavailable"` + `type=="server_error"` + `retryable is True` + 键集恰 5。
  - **FAIL**：status 非 503、码/类型/键集不符、或流出成功载荷。
  - **BLOCKED**：B 类 fake provider / 专属实例不可用。
  - **SKIP**：附加前置不满足。
  - **INVALID**：用 mock/替代路径伪造 503。
  - **NOT_RUN**：有实现但本轮未执行。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：status 非 503、码非 `provider_unavailable` → FAIL。
- **副作用断言与清理**：**若采用死端口变体，`finally` 必须把 `prov_b.endpoint` 复位为 LAN fake provider 并验证**；首选 `force-503` 法不修改任何配置。专属实例整班销毁。离开前确认无残留注入项（本 case 不写注入）。

## 7. 自动化位置与状态

- **测试文件 / 测试函数**：`tests/system/api_test_v03/at_dp_emb_10.py`（已实现；`v03_fake_provider.py` 的 `force-503` 覆盖 HTTP 5xx、`force-drop` 覆盖传输失败/断连分支）。
- **单 Case 执行命令**：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_emb_10.py -q`。
- **实现状态**：Implemented；执行与 Verdict 归 Run 报告。

**证据与 Run**：保存被测请求与原始响应（脱敏后）、上游返回证据、发出命令、exit code、`elapsed`、环境快照（本 case `environment:"b"`）。

**依赖**：B 类专属 `LLMTierInstance` / `api_client_b`；fake provider（`force-503`）；实现 `src/inference/providers/openai.py`；错误目录 `ERR-PROVIDER-UNAVAIL`。**不依赖**其它 Case；与 ST-EMB-009（502 契约错误）互补。

