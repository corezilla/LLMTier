<!-- STD_DOCUMENT_COVER_BEGIN -->
# DP-RESP-04 — tools 透传

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `DP-RESP-04` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-09-29` |
| Template ID | `tests.system-test-design` |
| Template Version | `2.3.0` |
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/cases/dp-resp-04.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。方案清单行见[系统测试方案 §3 覆盖分母与 Case 清单](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`DP-RESP-04` / 系统设计 §8 Responses 接口（POST /v1/responses） / `VRC-INF-001` / `normal` / `P1`。本文件名 `dp-resp-04.md`，与 Case ID 唯一对应。
- 要测什么（责任展开）：`POST /v1/responses` 携带合法 `tools`：被受理并透传，SSE 结构完整。
- 明确不测什么 / 失败含义：**不证明什么**——不证明上游是否真正调用工具（`function_call_arguments.*` 事件属上游行为，非 LLMTier 契约）；不证明工具执行结果；不证明 `tools` 语义正确性；不证明 `stream=false`/`store=true` 被拒（DP-RESP-02/07）。**失败含义＝tools 受理与透传契约破坏**。

**目的（被测契约）**：验证 Data Plane `POST /v1/responses` 对**合法 `tools` 数组**的受理与透传契约：当所选 model 的能力声明 `tools=true` 时，`tools` 作为可选字段被接受并转发给上游，不因出现 `tools` 而拒绝。被测端点/规则：`POST /v1/responses`；设计验证项 `VRC-INF-001`；机制 `T-TOOLS`；字段约束来自 OpenAPI `ResponsesRequest.tools`（`FunctionTool[]`）与实现 `src/inference/responses.py`（`ALLOWED_FIELDS` 含 `tools`；`require(caps.get("tools") ...)` 仅在能力为 `false` 时拒绝）（[系统测试方案 §3](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明上游是否真正调用工具；不证明工具执行结果；不证明 `tools` 语义正确性；不证明 `stream=false`/`store=true` 被拒（DP-RESP-02/07）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 现有实例，角色 `data`，无状态；见[系统测试方案 §1 测试边界](../../schemes/llmtier-system-test-scheme.md)）。前置 = 就绪检查（由 `conftest.py::pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP）。fixture `api_client`（Data 角色客户端）。初始状态 = 3 provider / 4 deployment / 7 fixed tier。**执行门（强制，先于发请求）**：经 `GET /v1/models` 确认所选 responses-capable tier（本例 `Worker`）的 `capabilities.tools == true`；若为 `false`，本 case **BLOCKED**（能力前置不满足），**不得静默 PASS、也不得降级为可选负向观测**。
- **被测入口**：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Content-Type: application/json
  Accept: text/event-stream
  ```

- **初态构造与客户端**：只读无状态；凭据固定 `data`（经 `api_client` 注入）；能力门前置经公开 `GET /v1/models` 构造。
- **依赖的测试资产（tests.asset-design 文档）**：本阶段 `tests.asset-design` 文档尚未建立；`api_client` 等夹具契约见方案 §4。

## 3. 输入构造

- **输入与构造**：固定请求（`tools` 含单个合法 `function` 工具）：

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
    "input": [{"role": "user", "content": "What's the weather in SF?"}],
    "stream": true,
    "store": false,
    "tools": [
      {
        "type": "function",
        "name": "get_weather",
        "description": "Get current weather",
        "parameters": {"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]}
      }
    ],
    "max_output_tokens": 100
  }
  ```

  构造点：`tools[].type` 为 `function`；能力门（`caps.tools`）必须为真；`max_output_tokens=100` 限制流长；`store=false` 无副作用。**不构造** `function_call` 预期——上游是否调用工具不进入 Oracle。
- **规模 / 时间域**：单个 SSE 流（`max_output_tokens=100`）；无分页/并发；记录 `elapsed` 供报告。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认基线（由 `pytest_configure` 自动执行）。
  2. `POST /v1/responses`（上表 body），同步读取完整 SSE（`resp = api_client.post(...)`）。
  3. 断言 `status_code == 200` 且 `Content-Type` 含 `text/event-stream`。
  4. 断言 body 文本含 `event: response.created` 与 `event: response.completed`（终止事件存在）。
  5. 逐帧解析确认恰好一个 terminal（`response.completed`），`sequence_number` 自 0 递增；`data: [DONE]` 出现。
  6. （可选交叉核对）若上游返回 `function_call`，仅记录 `response.output_item.done.item.type=="function_call"`，**不**作为 PASS/FAIL 依据。

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 确认基线（`pytest_configure` 自动执行） | 就绪检查通过 |
| 2 | 同步 `POST /v1/responses`（携带 `tools`） | status / `Content-Type` / body |
| 3 | 断言 200 + `text/event-stream` | 响应头 |
| 4 | 断言含 `response.created` 与 `response.completed` | 事件存在性 |
| 5 | 唯一 terminal、`sequence_number` 递增、`[DONE]` | 事件序列 |
| 6 | （可选）记录上游 `function_call`（不作判据） | 交叉核对 |

**重点关注步骤**：① **受理而非拒绝**——`tools` 出现在 `ALLOWED_FIELDS`，只有 `caps.tools is False` 才 `400 unsupported_request`（`param="tools"`）；本 case 的前提是该 tier 能力为真，为假则 **BLOCKED**，不得把该拒绝当 PASS；② **透传不解释**——LLMTier 只转发 `tools`，不对工具语义/调用结果负责；③ **terminal 唯一 + `[DONE]`**；④ **不把上游工具调用当契约**——禁止以"出现了 `function_call_arguments` 事件"作为 PASS 条件。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = Responses 请求受理 + 标准 SSE 外壳，与上游是否调用工具无关。**判据语义以设计验证项 `VRC-INF-001` 为唯一权威**。
  - HTTP：`200`；`Content-Type: text/event-stream`。
  - 事件序列含 `response.created`、唯一 terminal `response.completed`；`data: [DONE]` 收尾；`sequence_number` 自 0 递增。
  - 本 case **不含负向观测**：`caps.tools is False` 按执行门判 **BLOCKED**（换用 `tools=true` 的 tier，或另立独立负向 case），不计入本 case 的 PASS/FAIL。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：执行门通过（所选 tier `caps.tools==true`）且 status 200 + SSE 外壳（created/completed/唯一 terminal/`[DONE]`/递增）match；不要求出现工具调用事件。
  - **FAIL**：status 非 200（能力为真时应受理）、SSE 序列断裂、terminal 缺失/重复、`[DONE]` 缺失。
  - **BLOCKED**：测试代码/断言不可实现，或所选 tier `capabilities.tools == false`（能力前置不满足，须换 `tools=true` 的 tier）——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：就绪前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：以 mock/替代路径冒充真实路径——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（方案清单 `RUN`），未执行时记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：能力门不满足（`caps.tools==false`）→ BLOCKED（非 FAIL）；SSE 序列断裂/terminal 缺失/`[DONE]` 缺失按 §5 判 FAIL 并保留逐帧现场。
- **副作用断言与清理**：**无需 teardown**——`store=false`、环境 A 无状态，不创建/修改资源；退出前确认 `/readyz` 仍 7 tier。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../../schemes/llmtier-system-test-scheme.md)：保存请求 body（含 `tools`）、HTTP status/headers、原始 SSE 逐帧、发出命令、exit code、环境快照；manifest 与报告落位见 §4.8/§10（本 case `environment:"a"`）；失败现场不截断。
- **依赖**：[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`api_client`（[系统测试方案 §4 共同机制](../../schemes/llmtier-system-test-scheme.md)）；`tools=true` 的 responses-capable tier；自动化入口 [`at_dp_resp_04.py`](../../../../tests/system/api_test_v03/at_dp_resp_04.py)。**不依赖**其它 Case；能力门负向不在本 case 范围（`tools=false` → BLOCKED，不并入 PASS/FAIL）。

> 实现状态：Implemented（`at_dp_resp_04.py` 已断言本 case 契约）；执行状态与 Verdict 只在 Run 报告。
