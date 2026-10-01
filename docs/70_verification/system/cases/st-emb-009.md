<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-emb-009 — embeddings 上游契约错误 502

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-emb-009` |
| Document Version | `0.1.0-draft.3` |
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
| Canonical Path | `docs/70_verification/system/cases/st-emb-009.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-emb-009` / 系统设计 §8 Embeddings 接口（POST /v1/embeddings） / `VRC-INF-001` / recovery / P1（[方案清单 `ST-emb-009`](../llmtier-system-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：故障注入（上游契约错误 → 502）+ 复位阶梯

- 要测什么（责任展开）：`POST /v1/embeddings` 上游响应无法归一：`502 provider_contract_error`。上游返回非 `object:list` 或 `data` 非数组时，适配层拒绝。需求 `R-INF-05`；错误目录 `ERR-PROVIDER-CONTRACT` → wire `code=provider_contract_error`；实现 `src/inference/providers/openai.py::embed`（`data.get("object")!="list" or not isinstance(data.get("data"), list)` → `ApiError(502, "provider_contract_error", "Provider returned an invalid Embeddings payload")`）与 `src/inference/embeddings.py:57/60`（非法 base64/向量 → 同码）。

- 明确不测什么 / 失败含义：不测上游 5xx/不可达（`503 provider_unavailable`，ST-emb-010）；不测 Responses 的 `provider_contract_error`（ST-resp-025）；不测真实模型答案或向量语义（ST-emb-003）；不测 Responses 注入的 `provider_failure`（`fault_502`）——**Embeddings 无故障注入路径**（`embeddings.py` 不读 `enabled_injection`），故其上游故障只能由真实/假上游产生，`provider_failure` 码在 Embeddings 不可达。失败含义＝非法上游 Embeddings 载荷被当成功流出。

**目的（被测契约）**：验证 **Embeddings 适配层的上游载荷归一契约**。被测端点/规则：`POST /v1/embeddings`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `createEmbedding`）；入口经 [`EmbeddingsService.create`](../../../../src/inference/embeddings.py) 调用 [`OpenAIProvider.embed`](../../../../src/inference/providers/openai.py)，对非 `list`/非数组载荷抛 `502 provider_contract_error`。设计验证项 `VRC-INF-001`；机制 `E-INF-UPSTREAM`。**不证明什么**：不测上游 5xx/不可达（ST-emb-010）；不测 Responses 契约错误（ST-resp-025）；不测答案/向量语义；**不测 `provider_failure`**（Embeddings 无注入路径，该码不可达）。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例，专属实例）。前置 = 方案 §5 附加（B 类）就绪检查；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。`prov_b.endpoint` 必须是 LAN IP 上的**专属违规 stub**（[`tests/fixtures/v03_fake_provider.py`](../../../../tests/fixtures/v03_fake_provider.py)，**已落地**），对 `POST /v1/embeddings` 返回**违反契约**的载荷；`depl_b` 已 probe `healthy`（probe 打 `/models`，需返回合法目录）。TS-003：endpoint 必须是 LAN IP。
- **被测入口**：

  ```http
  POST /v1/embeddings HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-data
  Content-Type: application/json
  ```

- **初态构造（经公开入口）**：专属 stub 被配置为对 `/v1/embeddings` 返回下述任一种契约违规；`depl_b` probe `healthy`；`diagnostic_injections` 为空（本 case 不用注入）。
- **Fixture / 向量及版本**：专属 `LLMTierInstance`、`api_client_b`；违规 stub 配置，随 Run manifest 存档。
- **依赖的测试资产（tests.asset-design 文档）**：B 类实例与违规 stub 契约见方案 §4；TS-003 LAN endpoint。

## 3. 输入构造

- **逐参数输入构造**：被测请求（stub 需被配置为下述任一种契约违规）：

  ```json
  {"model": "Senior", "input": "hello"}
  ```

- **边界/非法取值及理由**：契约违规构造（各子测，逐一独立）：① 上游 200 但 body 非 JSON 对象（如 `[]`）；② body 为对象但 `object != "list"`；③ body 含 `object=="list"` 但 `data` 非数组；④ `data` 为数组但元素缺 `embedding`（非法向量）。另可测 `encoding_format="base64"` 时上游返回非合法 base64 向量（`embeddings.py:55-57` → 同码）。
- **规模 / 时间域**：各子测一次请求；stub 快速返回。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | （fixture 前置）启动专属 stub 与实例，probe `depl_b` → `healthy`；确认无启用注入 | 实例就绪 |
| 2 | 对每个子测配置 stub 使其返回对应契约违规载荷 | stub 违规形态 |
| 3 | `POST /v1/embeddings`（上表 body） | 普通 JSON 错误信封 |
| 4 | 断言 `status_code == 502`；解析 `error` | `code=="provider_contract_error"`、`type=="server_error"`、`retryable is False`、`param is None`，键集恰 5 键 |
| 5 | 断言 `message` 与子测语义一致 | 非 list / 非数组 / 非法向量 / 非法 base64 |

- **重点关注步骤**：① **契约归一在适配层完成**——不把非法上游载荷当成功流出；② **502 而非 503**——契约错误是 `provider_contract_error`，与 `provider_unavailable`（5xx/不可达）区分；③ **码正确性**——Embeddings 是 `provider_contract_error`，**不是** `provider_failure`（后者仅 Responses 注入可达）；④ **`retryable=false`**（实现默认）；⑤ **信封 identity**（5 键、`type=server_error`）；⑥ **子测各自独立**。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **独立 Oracle 来源与推导**：OpenAPI `ErrorEnvelope`/`ErrorDetail` + `ERR-PROVIDER-CONTRACT`（不依赖实现答案）。
  - HTTP `502`；`Content-Type: application/json`；`error.code=="provider_contract_error"`、`type=="server_error"`、`param=null`、`retryable=false`；无成功 `data` 载荷。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`502` + `code=="provider_contract_error"` + `type=="server_error"` + `retryable is False` + 键集恰 5。
  - **FAIL**：status 非 502、码/类型/键集不符、或把非法载荷当成功流出。
  - **BLOCKED**：专属违规 stub 不可用；stub 已落地，不再构成 BLOCKED。
  - **SKIP**：B 类临时实例不可用、附加前置不满足。
  - **INVALID**：用 mock/替代路径伪造 502。
  - **NOT_RUN**：有实现但本轮未执行。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：status 非 502、码非 `provider_contract_error`、或流出成功载荷 → FAIL。
- **副作用断言与清理**：**无需逐请求 teardown**；专属实例整班销毁。离开前确认无残留注入项（本 case 不写注入）。

## 7. 自动化位置与状态

- **测试文件 / 测试函数**：`tests/system/api_test_v03/at_dp_emb_09.py`（已实现；`v03_fake_provider.py` 提供 `force-bad-object`/`force-non-array-data`/`force-bad-vector`/`force-bad-base64` 四种违规载荷）。
- **单 Case 执行命令**：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_emb_09.py -q`。
- **实现状态**：Implemented；执行与 Verdict 归 Run 报告。

**证据与 Run**：保存 stub 违规配置、被测请求与原始响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照（本 case `environment:"b"`）。

**依赖**：B 类专属 `LLMTierInstance` / `api_client_b`；**违规 stub fixture**（[`v03_fake_provider.py`](../../../../tests/fixtures/v03_fake_provider.py)，**已落地**）；实现 `src/inference/providers/openai.py`、`src/inference/embeddings.py`；错误目录 `ERR-PROVIDER-CONTRACT`。**不依赖**其它 Case；与 ST-resp-025 同属 `provider_contract_error` 家族但端点不同。

