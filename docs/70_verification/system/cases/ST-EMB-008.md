<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-EMB-008 — embeddings 准入饱和 429

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-EMB-008` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-EMB-008.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-EMB-008` / 系统设计 §8 Embeddings 接口（POST /v1/embeddings） / `VRC-INF-004` / concurrency / P1（[方案清单 `ST-EMB-008`](../llmtier-system-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：状态机驱动（准入饱和 429 + Retry-After）+ 固定并发度/种子

- 要测什么（责任展开）：`POST /v1/embeddings` 准入饱和：并发超过 `depl_b` 运行时并发许可与队列上限（队列 32）时，`Router.admit` 拒绝并返回 `429 rate_limit_exceeded` 且带 `Retry-After`。需求 `R-INF-04`；机制需求 `R-MET-04`；错误目录 `ERR-RATE-LIMIT` → wire `code=rate_limit_exceeded`；实现 `src/inference/routing.py`（队列满 `len(self._queues[level_id]) >= 32` → `ApiError(429, "rate_limit_exceeded", "Service-level queue is full", retryable=True, headers={"Retry-After":"30"})`；等待超时 → `Retry-After:"1"`）。

- 明确不测什么 / 失败含义：不测 Responses 准入饱和（ST-RESP-020）；不测上游自身返回 429（`openai.py` 非 5xx 分支映射为 `429 provider_error`，非 `rate_limit_exceeded`）；不测模型/维度/编码 400/404（ST-EMB-004/06/07）；不发布时延 SLO。失败含义＝第二条 Data Plane 的准入饱和语义缺失或错误码/`Retry-After` 契约破坏。

**目的（被测契约）**：验证 **Embeddings 数据面** 的准入饱和契约与 `Router.admit` 共享实现。被测端点/规则：`POST /v1/embeddings`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `createEmbedding`，`security=DataBearerAuth`）；入口 [`app.py`](../../../../src/http_api/app.py) 以 data 角色鉴权后调用 [`EmbeddingsService.create`](../../../../src/inference/embeddings.py)，其中 `with self.router.admit(model) as candidate`（`embeddings.py:47`）与 Responses 共用同一 [`Router`](../../../../src/inference/routing.py)。设计验证项 `VRC-INF-004`；机制 `T-MET-PAGE` 无关，本 case 属准入（`E-INF-ADMIT`）。**不证明什么**：不测 Responses 准入饱和（ST-RESP-020）；不测上游自身返回 429；不测模型/维度/编码校验；不发布时延 SLO。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例，专属实例，避免与其它并发/注入 Case 互相干扰）。前置 = 方案 §5 附加（B 类）就绪检查；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier，`llmtier_b` probe `depl_b` 为 `healthy`（否则 BLOCKED/SKIP）。`prov_b.endpoint` 必须是 LAN IP 上的 fake provider（TS-003）。初始状态 = 无启用注入项；`depl_b` 运行时 `max_in_flight` 默认 1、provider 并发默认 1。
- **专用 fixture（已落地）**：本 case 需**占住 `depl_b` 的唯一并发槽**。Embeddings 无 Responses 的 `delay` 注入路径（`embeddings.py` 不读 `enabled_injection`），故假上游 [`tests/fixtures/v03_fake_provider.py`](../../../../tests/fixtures/v03_fake_provider.py) 已扩展：`POST /v1/embeddings` 在 `model == "slow-embeddings"` 时 `time.sleep`（门控释放），`depl_b.backend_model` 设为 `slow-embeddings`（fixture `llmtier_b_emb_slow` + `fake_provider_b.release_slow()`）。**不得**以 Responses 的 `delay` 注入冒充 Embeddings 占槽。
- **被测入口**：

  ```http
  POST /v1/embeddings HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-data
  Content-Type: application/json
  ```

- **Fixture / 向量及版本**：专属 `LLMTierInstance`、`api_client_b`；`backend_model="slow-embeddings"` 的 `_baseline_settings`；`N` 个并发 embeddings 请求向量，随 Run manifest 存档。
- **依赖的测试资产（tests.asset-design 文档）**：本阶段 `tests.asset-design` 文档尚未建立；B 类实例与慢上游夹具契约见方案 §4，引用其版本而不复制字节。

## 3. 输入构造

- **输入与构造**：先以 `backend_model="slow-embeddings"` 启动专属实例并 probe `depl_b=healthy`；随后以同一 data token **并发**发起 `N`（建议 `N >= 34`）个相同请求：

  ```json
  {"model": "Senior", "input": "hello"}
  ```

- **边界/非法取值及理由**：`depl_b.backend_model="slow-embeddings"` 使上游慢响应、占住唯一并发槽；`N` 需超过 1（占槽）+ 32（队列上限）；`model="Senior"` 指向唯一 deployment `depl_b`，7 个 fixed tier 的 `deployment_ids` 均指向 `depl_b`。不注入故障（本 case 用真实慢上游占槽，不用注入）。
- **规模 / 时间域**：`N >= 34` 并发；慢上游保持槽位占用；不发布时延 SLO。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | （fixture 前置）启动专属实例 `llmtier_b_emb_slow`（`backend_model="slow-embeddings"`）并 probe `depl_b` → `healthy` | 实例就绪 |
| 2 | 以线程/异步并发发起 `N` 个 `POST /v1/embeddings` | 各响应 status |
| 3 | 收集状态码分布 | 至少一个 `429`（队列满），其余 200（占槽/在队）或 429 |
| 4 | 断言 429 响应体 | `error.code=="rate_limit_exceeded"`、`type=="request_error"`、`retryable is True`、键集恰 5 键 |
| 5 | 断言 429 响应含 `Retry-After` 头 | 值为正整数秒（队列满为 `"30"`，等待超时为 `"1"`） |
| 6 | （teardown）专属实例整班销毁 | 无残留 |

- **重点关注步骤**：① **饱和才 429**——只有超过许可+队列上限时拒绝，非首个请求；② **`Retry-After` 存在且为正整数**；③ **区分两条 429 分支**——队列满（`Retry-After:30`）vs 等待超时（`Retry-After:1`），只断"存在+正整数"以免耦合内部时点；④ **占槽必须来自真实慢上游**——不得 monkeypatch/注入冒充（INVALID）；⑤ **共享同一 tier 的许可/队列**；⑥ **不触碰 Responses 路径**；⑦ **BLOCKED 语义**——慢上游 fixture 不可用（或并发夹具不可实现）时记 BLOCKED，不得跳过。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `ErrorEnvelope`/`ErrorDetail` + `ERR-RATE-LIMIT`（不依赖实现内部时点）。
  - HTTP `429`；`Content-Type: application/json`；body `{"error":{"message":<str>,"type":"request_error","code":"rate_limit_exceeded","param":null,"retryable":true}}`；响应头含 `Retry-After`（正整数秒）。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：并发请求中至少一个 `429` + `error.code=="rate_limit_exceeded"` + `retryable is True` + `Retry-After` 为正整数。
  - **FAIL**：从未 429（饱和构造失败）、`Retry-After` 缺失/非正整数、code/type 错。
  - **BLOCKED**：慢上游 fixture 不可用或并发夹具不可实现；fixture 已落地，不再构成 BLOCKED。
  - **SKIP**：B 类临时实例不可用、附加前置不满足。
  - **INVALID**：以 mock/注入/替代路径冒充 Embeddings 占槽。
  - **NOT_RUN**：本 Case 有实现但本轮未执行。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：从未 429 → FAIL；`Retry-After` 缺失/非法 → FAIL；慢上游未命中 → BLOCKED。保留原始并发请求/响应与失败现场。
- **副作用断言与清理**：**无需逐请求 teardown**（拒绝/正常读均不改配置）；专属实例整班 `stop()` + `rm -rf` 临时目录。离开前确认无残留注入项（本 case 不写注入）；若误用共享 `llmtier_b` 实例并留下占槽请求，必须销毁并报 FAIL。

## 7. 自动化位置与状态

- **测试文件 / 测试函数**：`tests/system/api_test_v03/at_dp_emb_08.py`（已实现；慢上游 fixture `v03_fake_provider.py` 的 `slow-embeddings` 门控）。
- **单 Case 执行命令**：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_emb_08.py -q`。
- **实现状态**：Implemented；执行与 Verdict 归 Run 报告。

**证据与 Run**：保存并发请求清单与各响应（含 429 与 `Retry-After`）、上游调用计数/runtime 快照、发出命令、exit code、`elapsed`、环境快照（本 case `environment:"b"`）。

**依赖**：B 类专属 `LLMTierInstance` `llmtier_b_emb_slow` / `api_client_b`；**慢上游 fixture**（`v03_fake_provider.py` 的 `slow-embeddings` 门控，**已落地**）；实现 `src/inference/routing.py`、`src/inference/embeddings.py`；错误目录 `ERR-RATE-LIMIT`。**不依赖**其它 Case；与 ST-RESP-020 共享 `Router.admit` 但端点不同，各自独立执行。

