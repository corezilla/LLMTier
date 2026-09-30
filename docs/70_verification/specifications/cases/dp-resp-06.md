<!-- STD_DOCUMENT_COVER_BEGIN -->
# DP-RESP-06 — stream=true 唯一受理形态

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `DP-RESP-06` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-09-30` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/cases/dp-resp-06.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。方案清单行见[系统测试方案 §3 覆盖分母与 Case 清单](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`DP-RESP-06` / 系统设计 §8 Responses 接口（POST /v1/responses） / `VRC-INF-001` / `normal` / `P0`。本文件名 `dp-resp-06.md`，与 Case ID 唯一对应。
- 要测什么（责任展开）：`POST /v1/responses` 显式 `stream=true`：受理并返回合法 SSE（唯一受理形态的正向基线）。
- 明确不测什么 / 失败含义：**不证明什么**——不证明事件序列的完整逐帧 identity（DP-RESP-01 承担）、不证明 `stream=false`/`store=true` 被拒（DP-RESP-02/07）、不证明截断（DP-RESP-10）或异常路径；不证明模型答案。**失败含义＝受理形态契约破坏**。

**目的（被测契约）**：验证 Data Plane `POST /v1/responses` 的**唯一受理形态**：`stream=true` + `store=false` 被接受并返回标准 SSE。被测端点/规则：`POST /v1/responses`；设计验证项 `VRC-INF-001`；机制 `T-STREAM`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；OpenAPI `ResponsesRequest.stream.const=true`（[系统测试方案 §3](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明事件序列的完整逐帧 identity（DP-RESP-01 承担）、不证明 `stream=false`/`store=true` 被拒（DP-RESP-02/07）、不证明截断（DP-RESP-10）或异常路径；不证明模型答案。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 现有实例，角色 `data`，无状态；见[系统测试方案 §1 测试边界](../../schemes/llmtier-system-test-scheme.md)）。前置 = 就绪检查（由 `conftest.py::pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP）。fixture `api_client`（Data 角色客户端）。初始状态 = 3 provider / 4 deployment / 7 fixed tier；`model="Worker"` 由三选一调度。
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

- **输入与构造**：固定请求（最小受理形态）：

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
    "input": [{"role": "user", "content": "Hello"}],
    "stream": true,
    "store": false,
    "max_output_tokens": 30
  }
  ```

  构造点：显式 `stream=true`；`store=false`；`max_output_tokens=30` 限制流长；不注入故障；其余字段构造与 DP-RESP-01 一致，本 case 只保留 `stream=true` 受理这一 delta。
- **规模 / 时间域**：单个 SSE 流（`max_output_tokens=30`）；无分页/并发；记录 `elapsed` 供报告。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认基线（由 `pytest_configure` 自动执行）。
  2. `POST /v1/responses`（上表 body）。
  3. 断言 `status_code == 200` 且 `content-type` 含 `text/event-stream`（受理形态 delta；事件序列完整断言见 DP-RESP-01）。
  4. 同步读取 body，断言含 `event: response.completed`（terminal 存在性）。
  5. 断言出现 `data: [DONE]`。

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 确认基线（`pytest_configure` 自动执行） | 就绪检查通过 |
| 2 | `POST /v1/responses`（`stream=true`） | status / headers / body |
| 3 | 断言 200 + `text/event-stream` | 响应头 |
| 4 | 断言含 `event: response.completed` | terminal 存在性 |
| 5 | 断言出现 `data: [DONE]` | 流收尾 |

**重点关注步骤**：① **正向与负向配对**——本 case 与 DP-RESP-02（`stream=false`）/DP-RESP-07（`store=true`）构成受理边界的三联，各自独立执行；② **受理即返回 SSE**——`Content-Type: text/event-stream` 而非错误信封；③ **terminal 存在**——本 case 只断 `response.completed` 存在，逐帧 identity/唯一性/顺序由 DP-RESP-01 承担（不重复其断言）；④ **不把答案文本当 Oracle**。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `stream.const=true` 受理，不依赖实现答案。事件序列/唯一 terminal/`[DONE]`/usage 的完整判定见 DP-RESP-01；本 case 只断"受理形态"这一前沿。**判据语义以设计验证项 `VRC-INF-001` 为唯一权威**。
  - HTTP：`200`；`Content-Type: text/event-stream`。
  - 事件：含 `response.created` 与 terminal `response.completed`；`data: [DONE]` 收尾。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：status 200 + `text/event-stream` + `response.completed` + `[DONE]` match。
  - **FAIL**：status 非 200、无 SSE、`response.completed` 缺失、`[DONE]` 缺失。
  - **BLOCKED**：测试代码/断言不可实现——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：就绪前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：以 mock/替代路径冒充真实路径——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（方案清单 `RUN`），未执行时记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：无 SSE / `response.completed` 缺失 / `[DONE]` 缺失按 §5 判 FAIL 并保留逐帧现场。被拒形态见 DP-RESP-02/07。
- **副作用断言与清理**：**无需 teardown**——`store=false`、环境 A 无状态；退出前确认 `/readyz` 仍 7 tier；若被误跑于 B 类临时实例，则按[系统测试方案 §4 共同机制](../../schemes/llmtier-system-test-scheme.md) 整班销毁。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../../schemes/llmtier-system-test-scheme.md)：保存请求 body、HTTP status/headers、原始 SSE、发出命令、exit code、环境快照；manifest 与报告落位见 §4.8/§10（本 case `environment:"a"`）；失败现场不截断。
- **依赖**：[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`api_client`（[系统测试方案 §4 共同机制](../../schemes/llmtier-system-test-scheme.md)）；上游 tier `Worker`；自动化入口 [`at_dp_resp_06.py`](../../../../tests/system/api_test_v03/at_dp_resp_06.py)。**不依赖**其它 Case；与 DP-RESP-01 共享 SSE 机制但断言范围更窄（受理 + terminal 存在）。

> 实现状态：Implemented（`at_dp_resp_06.py` 已断言本 case 契约）；执行状态与 Verdict 只在 Run 报告。
