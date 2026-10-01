<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-resp-003 — 推理任务流式结构

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-resp-003` |
| Document Version | `0.1.0-draft.3` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-10-01` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/st-resp-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。方案清单行见[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-resp-003` / 系统设计 §8 Responses 接口（POST /v1/responses） / `VRC-INF-001` / `normal` / `P1`。本文件名 `st-resp-003.md`，与 Case ID 唯一对应。
- **测试方法（§1.5 方法表行）**：等价类划分 + 契约字段比对 + 状态机驱动（SSE 事件序列/唯一 terminal）
- 要测什么（责任展开）：`POST /v1/responses` 固定推理 prompt：SSE 结构完整（事件序列/唯一 terminal/`[DONE]`），不把模型输出内容当 oracle。
- 明确不测什么 / 失败含义：**不证明什么**——不证明模型答案的语义正确性、不证明 upstream 推理质量、不发布时延 SLO；不证明 `stream=false`/`store=true` 被拒（ST-resp-002/07）、不证明截断（ST-resp-010）或异常路径（ST-resp-011/21）。**失败含义＝固定推理 prompt 下的流式结构契约破坏**。

**目的（被测契约）**：验证 Data Plane `POST /v1/responses`（`stream=true`）在**固定推理 prompt** 下的正常路径：事件序列有序、恰好一个 terminal、`output_text.delta` 累积文本非空。被测端点/规则：`POST /v1/responses`；设计验证项 `VRC-INF-001`；机制 `T-STREAM`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；固定 prompt 见[系统测试方案 §4 LLM 判据](../llmtier-system-test-scheme.md)（结构/事件序列，不写"答案正确"、不把内容当 oracle）。**不证明什么**：不证明模型答案的语义正确性、不证明 upstream 推理质量、不发布时延 SLO；不证明 `stream=false`/`store=true` 被拒（ST-resp-002/07）、不证明截断（ST-resp-010）或异常路径（ST-resp-011/21）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 现有实例，角色 `data`，无状态；见[系统测试方案 §1 测试边界](../llmtier-system-test-scheme.md)）。前置 = 就绪检查（由 `conftest.py::pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP）。fixture `api_client`（Data 角色客户端）。初始状态 = 3 provider / 4 deployment / 7 fixed tier；`model="Worker"` 由三选一调度，只断言最终 200 + SSE 合法。
- **被测入口**：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Content-Type: application/json
  Accept: text/event-stream
  ```

- **初态构造与客户端**：只读无状态；凭据固定 `data`（经 `api_client` 注入）。
- **依赖的测试资产（tests.asset-design 文档）**：本阶段 `tests.asset-design` 文档尚未建立；`api_client` 等夹具契约见方案 §4。

## 3. 输入构造

- **输入与构造**：固定请求（固定推理 prompt `Calculate 15 * 23 + 45 step by step`；**模型输出内容不作为 Oracle**，见下可复现性风险）：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Content-Type: application/json
  Accept: text/event-stream
  ```

  ```json
  {
    "model": "Worker",
    "input": [{"role": "user", "content": "Calculate 15 * 23 + 45 step by step"}],
    "stream": true,
    "store": false,
    "max_output_tokens": 1500
  }
  ```

  构造点：`max_output_tokens=1500`（远大于步进推理输出）保证推理任务不被截断、terminal 为 `completed`（不触发 ST-resp-010；上游 Qwen 推理可能较长，上限过小会误判为 `incomplete`）；`model` 为 responses-capable tier；`store=false` 避免落库副作用；不注入故障。
- **规模 / 时间域**：单个 SSE 流（`max_output_tokens=1500`）；无分页/并发；记录 `elapsed` 供报告，不发布 SLO。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认基线（由 `pytest_configure` 自动执行）。
  2. `POST /v1/responses` 以流式读取；断言 `status_code == 200` 且 `content-type` 含 `text/event-stream`。
  3. 逐帧解析 `text/event-stream`（按空行分帧，取 `event:`/`data:`；`data: [DONE]` 单独识别）。
  4. 断言事件集合/顺序（子序列）：`response.created` 首帧；含 `response.output_item.added`、≥1 个 `response.output_text.delta`、`response.output_item.done`；`response.completed` 为唯一 terminal（本版本无独立的文本完成事件，见 ST-resp-001）。
  5. 断言 `response.completed.response.status == "completed"`；各帧 `sequence_number` 自 0 严格递增。
  6. 累积所有 `delta`，断言累积文本非空（结构断言；**不断言模型内容**，如是否含 `"390"`）。
  7. 断言流末尾出现 `data: [DONE]`。

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 确认基线（`pytest_configure` 自动执行） | 就绪检查通过 |
| 2 | 流式 `POST /v1/responses` | 200 + `text/event-stream` |
| 3 | 逐帧解析 SSE（`[DONE]` 单独识别） | 事件名 / `data` JSON |
| 4 | 校验事件序列 + 唯一 terminal | 事件序列 |
| 5 | 断言 `status=="completed"`；`sequence_number` 严格递增 | 事件/帧内 |
| 6 | 累积 delta 文本非空（不断言内容） | 累积文本 |
| 7 | 流末尾 | `data: [DONE]` |

**重点关注步骤**：① **模型内容不是 Oracle**——`"390"` 仅为示例数字串，上游 LLM 输出格式不稳定，**不作为 PASS/FAIL 条件**；若未观察到该串，只作可复现性风险记录（见下），不得据此判 FAIL、也不得改写成"语义对即可"的反向断言；② **terminal 唯一 + `[DONE]`**；③ **`sequence_number` 严格递增**；④ **`Content-Type` 必须 `text/event-stream`**，防止把错误信封当成功流；⑤ **事件 identity**——`delta` 至少 1 个且累积文本非空。
> **可复现性风险（记录，非判据）**：固定 prompt 期望输出含数字串 `"390"`，但上游 LLM 输出不稳定、该子串可能不出现；本设计据此把 `"390"` 移出 PASS 条件，case 保持结构性。若后续要用它做回归，须先在上游侧锁定确定性（如 greedy / `temperature=0`）并在[系统测试方案 §4](../llmtier-system-test-scheme.md) 另立判据。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = 标准 Responses SSE wire 形态（**不依赖实现的"答案内容"与语义正确性**；固定 prompt 仅用于稳定触发推理输出，其内容不作断言）。**判据语义以设计验证项 `VRC-INF-001` 为唯一权威**。
  - HTTP：`200`；`Content-Type: text/event-stream`。
  - 事件序列：`response.created` 首帧 → `output_item.added` → `output_text.delta`（≥1）→ `output_item.done` → 唯一 terminal `response.completed`（`status="completed"`）→ `data: [DONE]`。
  - 帧内 `sequence_number` 自 0 严格递增；累积 delta 文本非空（**不约束内容**，`"390"` 非判据）。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：status + content-type + 事件序列/唯一 terminal + `[DONE]` + `sequence_number` 递增 + 累积文本非空 全部 match。
  - **FAIL**：任一断言不符（status/序列/terminal/`[DONE]`/递增/累积文本为空）。
  - **BLOCKED**：测试代码/断言不可实现——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：就绪前置不满足（上游 OMLX 离线等）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：以 `127.0.0.1`/mock/替代路径冒充真实 m5air——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（方案清单 `RUN`），未执行时记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：SSE 序列断裂、terminal 缺失/重复、`[DONE]` 缺失、累积文本为空按 §5 判 FAIL 并保留逐帧现场。异常路径见 ST-resp-010/11/21。
- **副作用断言与清理**：**无需 teardown**——`store=false`、环境 A 无状态，不创建/修改资源；退出前确认无注入项、`/readyz` 仍 7 tier；若被误跑于 B 类临时实例，则按[系统测试方案 §4 共同机制](../llmtier-system-test-scheme.md) 整班销毁。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-system-test-scheme.md)：保存原始 SSE 逐帧、HTTP status/headers、累积文本、发出命令、exit code、`elapsed`、环境快照（`/healthz`/`/readyz`）；manifest 与报告落位见 §4.8/§10（本 case `environment:"a"`）；失败现场不截断。
- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`api_client`（[系统测试方案 §4 共同机制](../llmtier-system-test-scheme.md)）；上游 tier `Worker`；自动化入口 [`at_dp_resp_03.py`](../../../../tests/system/api_test_v03/at_dp_resp_03.py)。**不依赖**其它 Case；与 ST-resp-001（通用流式成功）共享 SSE 机制但用固定推理 prompt 区分。

> 实现状态：Implemented（`at_dp_resp_03.py` 已断言本 case 的结构契约）；执行状态与 Verdict 只在 Run 报告。
