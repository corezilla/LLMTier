<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-RATELIMIT-001 — provider 并发许可=1 队列排空

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-RATELIMIT-001` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-10-01` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-RATELIMIT-001.md` |
| Supersedes | `ST-22` |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-RATELIMIT-001`）；责任摘要、分类与优先级以 [系统测试方案 §6](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Responses 接口（`POST /v1/responses`）准入队列；机制 `inference-stream` 准入；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为临时替身实例）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-RATELIMIT-001` / 系统设计 §8 Responses 接口（`POST /v1/responses`）准入队列 / `VRC-INF-004` / `concurrency` / `P1`
- **测试方法（§2.2 方法表行）**：状态机驱动 + 固定并发度/种子（准入许可=1 的单槽排队排空）
- 方案清单登记：`ST-RATELIMIT-001`（与 §3 权威清单一致；本文件名 `st-ratelimit-001.md`，唯一对应）。
- 要测什么（责任展开）：provider `max_concurrent_requests=1` 时，6 个并发 Responses 请求被准入队列**吸收**——全部最终 200、无 429；总耗时随许可数串行化（证明经过队列而非并发直通）。
- 明确不测什么 / 失败含义：不测队列满→429（ST-RESP-020）、不测 embeddings 准入饱和（ST-EMB-008）、不测 `Retry-After` 值。失败含义＝单槽排队语义破坏（spurious 429 或并发直通绕过许可）。

**目的（被测契约）**：验证准入层的**正向排队语义**。被测端点/规则：`POST /v1/responses`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `createResponse`）；
[`Router.admit`](../../../../src/inference/routing.py) 以 provider `max_concurrent_requests`（单槽=1）与部署 `max_in_flight` 为并发许可，超限请求进入 32 深队列等待而非立即 429。
设计验证项 `VRC-INF-004`（准入饱和/候选健康）；机制 `T-QUEUE`（[系统测试方案 §6.6](../llmtier-system-test-scheme.md#36-需求lt--到-case-的可追溯映射3-的-36-等价节)）、`CT-DP-001`。
**不证明什么**：不证明队列满→429（ST-RESP-020）、不证明 embeddings 饱和（ST-EMB-008）、不发布任何吞吐/延迟 SLO（方案 §4 容量/耐久裁决）。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例，`llmtier_b_ratelimit` fixture）；`LLMTIER_SLOW_ADAPTER_DELAY=1.0` 使 [`ResponsesService._adapter`](../../../../src/inference/responses.py) 使用进程内 `SlowAdapter`（无网络调用），`depl_b` health 直接置 `healthy`，`provider_usage_profiles.max_concurrent_requests=1`；fixture `llmtier_b_ratelimit`（[系统测试计划 §5](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。TS-002：临时实例 + 进程内替身，无 LAN 上游依赖。

## 3. 输入构造

- **输入与构造**：6 个并发 `POST /v1/responses`，body `{"model":"Senior","input":[{"role":"user","content":"hi"}],"stream":true,"store":false,"max_output_tokens":16}`；固定并发度 6（`concurrency` 家族固定并发度/种子）；单槽=1、每次 complete 阻塞 1s。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. fixture 启动实例并配置单槽 + SlowAdapter（1s）。
  2. 并发发起 6 个请求，记录每个 HTTP status 与总耗时。
  3. 断 6 个请求全部 200；断总耗时 > 4s。

**重点关注步骤**：① **全部 200**——单槽+队列（32）足以吸收 6 个，不得出现 spurious 429；② **耗时下界**——许可=1、每次 1s ⇒ 串行 ≥6s 名义、断言 >4s 容忍调度抖动，证明确实排队。

## 5. 独立 Oracle 与预期结果

- **期望结果与独立 Oracle**：独立 Oracle = 准入许可（1）× 上游时延（1s）× 请求数（6）的串行下界 + `Router.admit` 队列容量（32）> 6。
  - 6 个响应全部 `200`。
  - `elapsed > 4.0s`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：全部 200 且耗时 > 4s。
  - **FAIL**：任一非 200（含 429）或耗时 ≤ 4s（并发直通/许可未生效）。
  - **BLOCKED**：fixture/断言逻辑问题——见[系统测试计划 §7](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：计划 §3 前置不满足——见[系统测试计划 §7](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用真实网络抖动冒充排队（须以 SlowAdapter 确定性时延构造）——见[系统测试计划 §7](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：function-scoped 临时实例，teardown `stop()` + 临时目录删除；SlowAdapter 无外部副作用，无残留长睡眠（每次请求 ≤1s）。

## 7. 自动化位置与状态

- **证据与 Run**：保存每请求 status、总耗时、fixture 配置快照；落位与契约见[系统测试计划 §6](../llmtier-system-test-plan.md#6-证据与-run-记录规则)。
- **依赖**：`llmtier_b_ratelimit` fixture；[`Router.admit`](../../../../src/inference/routing.py)；[`ResponsesService._adapter`](../../../../src/inference/responses.py)。自动化入口 [`ST-RATELIMIT-001.py`](../../../../tests/system/cases/ST-RATELIMIT-001.py)（**Implemented**）。**不依赖**其它 Case；与 ST-RESP-020（队列满→429）互补。

> 实现状态：见上文「依赖」的自动化入口（Implemented）；执行状态与 Verdict 只在 Run 报告。
