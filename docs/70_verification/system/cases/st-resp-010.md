<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-resp-010 — max_output_tokens 截断

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-resp-010` |
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
| Canonical Path | `docs/70_verification/system/cases/st-resp-010.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。方案清单行见[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-resp-010` / 系统设计 §8 Responses 接口（POST /v1/responses） / `VRC-INF-001` / `boundary` / `P1`。本文件名 `st-resp-010.md`，与 Case ID 唯一对应。
- **测试方法（§1.5 方法表行）**：边界值抽样 + 契约字段比对
- 要测什么（责任展开）：`POST /v1/responses` 传 `max_output_tokens=10`：SSE 以 `response.incomplete` 终止，`incomplete_details.reason=="max_output_tokens"`。
- 明确不测什么 / 失败含义：**不证明什么**——不证明 `context_window` 硬上限边界（本 case 只覆盖可测的 `max_output_tokens` 截断）；不证明超时/断开异常（ST-resp-011/21）；不证明模型内容。**失败含义＝截断终止契约破坏**。

**目的（被测契约）**：验证 Data Plane `POST /v1/responses` 的**截断终止契约**：当输出达到 `max_output_tokens` 上限时，终态为 `incomplete`（非 `completed`）且 `incomplete_details.reason=="max_output_tokens"`，SSE 仍以唯一 terminal + `[DONE]` 收尾。被测端点/规则：`POST /v1/responses`；设计验证项 `VRC-INF-001`；机制 `T-STREAM`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；实现 `src/http_api/sse.py`（terminal 类型 `f"response.{response['status']}"`）与 provider 归一（`src/inference/providers/openai.py` 透传 upstream `status`/`incomplete_details`）（[系统测试方案 §3](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明 `context_window` 硬上限边界（Qwen 实测 API 层未触发，本 case 只覆盖可测的 `max_output_tokens` 截断）；不证明超时/断开异常（ST-resp-011/21）；不证明模型内容。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 现有实例，角色 `data`，无状态；见[系统测试方案 §1 测试边界](../llmtier-system-test-scheme.md)）。前置 = 就绪检查（由 `conftest.py::pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP）。fixture `api_client`（Data 角色客户端）。初始状态 = 3 provider / 4 deployment / 7 fixed tier；所选 tier `Worker` 的 `capabilities.max_output_tokens` 必须 `>=10`，否则请求会先被字段范围校验拒为 `400 invalid_request`（`param="max_output_tokens"`）。
- **被测入口**：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Content-Type: application/json
  Accept: text/event-stream
  ```

- **初态构造与客户端**：只读无状态；凭据固定 `data`（经 `api_client` 注入）；能力门上界经公开 `GET /v1/models` 确认。
- **依赖的测试资产（tests.asset-design 文档）**：本阶段 `tests.asset-design` 文档尚未建立；`api_client` 等夹具契约见方案 §4。

## 3. 输入构造

- **输入与构造**：固定请求（长输出 prompt 迫使达到 10 token 上限）：

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
    "input": [{"role": "user", "content": "Count from 1 to 1000. Output only numbers separated by commas."}],
    "stream": true,
    "store": false,
    "max_output_tokens": 10
  }
  ```

  构造点：`max_output_tokens=10` 必须在能力上界内（`responses.py` 校验 `1 <= max_output_tokens <= caps.max_output_tokens`，否则 `400 invalid_request`）；固定长输出 prompt 保证触发截断；`store=false` 无副作用。
- **规模 / 时间域**：单个 SSE 流（`max_output_tokens=10`）；无分页/并发；记录 `elapsed` 供报告，不发布 SLO。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认基线（由 `pytest_configure` 自动执行）。
  2. `POST /v1/responses` 以流式读取；断言 `status_code == 200` 且 `Content-Type` 含 `text/event-stream`。
  3. 逐帧解析 `text/event-stream`。
  4. 断言事件序列含 `response.created`；断言**恰好一个** terminal，且为 `response.incomplete`（不是 `response.completed`）。
  5. 断言 `response.incomplete.response.status == "incomplete"`，且 `response.incomplete_details.reason == "max_output_tokens"`。
  6. 断言 `sequence_number` 自 0 严格递增；`data: [DONE]` 收尾。

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 确认基线（`pytest_configure` 自动执行） | 就绪检查通过 |
| 2 | 流式 `POST /v1/responses`（`max_output_tokens=10`） | 200 + `text/event-stream` |
| 3 | 逐帧解析 SSE | 事件名 / `data` JSON |
| 4 | 断言唯一 terminal 为 `response.incomplete` | 事件序列 |
| 5 | 断言 `status=="incomplete"`、`incomplete_details.reason=="max_output_tokens"` | 响应字段 |
| 6 | 断言 `sequence_number` 递增、`[DONE]` 收尾 | 帧内/流尾 |

**重点关注步骤**：① **terminal identity**——必须是 `response.incomplete`，出现 `response.completed` 即 FAIL（截断被误报为成功）；② **唯一 terminal**——`response.completed` 与 `response.incomplete` 不得并存；③ **reason 精确匹配** `"max_output_tokens"`；④ **`[DONE]` 仍收尾**——截断不是异常，仍是正常流终止；⑤ **字段范围前置校验**——若 `max_output_tokens` 超过能力上界，先被 `400 invalid_request` 拒绝，本 case 不得把该路径当截断。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = 标准 Responses terminal 形态 + OpenAPI `ResponsesResponse.incomplete_details`（[`interfaces/openapi/llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)）。**判据语义以设计验证项 `VRC-INF-001` 为唯一权威**。
  - HTTP：`200`；`Content-Type: text/event-stream`。
  - 事件：`response.created` 首帧；唯一 terminal `response.incomplete`，`response.status=="incomplete"`，`response.incomplete_details.reason=="max_output_tokens"`；`data: [DONE]` 收尾；`sequence_number` 自 0 递增。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：status 200 + 唯一 terminal `response.incomplete` + `status=incomplete` + `reason=max_output_tokens` + `[DONE]` + 递增 match。
  - **FAIL**：terminal 为 `completed`、terminal 缺失/重复、`reason` 错、`[DONE]` 缺失。
  - **BLOCKED**：测试代码/断言不可实现——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：就绪前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：以 mock/替代路径冒充真实路径——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（方案清单 `RUN`），未执行时记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：terminal 为 `completed`/缺失/重复、`reason` 错、`[DONE]` 缺失按 §5 判 FAIL 并保留逐帧现场。字段范围越界路径（`400 invalid_request`）不属本 case。
- **副作用断言与清理**：**无需 teardown**——`store=false`、环境 A 无状态；退出前确认 `/readyz` 仍 7 tier。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-system-test-scheme.md)：保存请求 body、HTTP status/headers、原始 SSE 逐帧（含 terminal 与 `incomplete_details`）、发出命令、exit code、`elapsed`、环境快照；manifest 与报告落位见 §4.8/§10（本 case `environment:"a"`）；失败现场不截断。
- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`api_client`（[系统测试方案 §4 共同机制](../llmtier-system-test-scheme.md)）；上游 tier `Worker`（`capabilities.max_output_tokens >= 10`）；自动化入口 [`at_dp_resp_10.py`](../../../../tests/system/api_test_v03/at_dp_resp_10.py)。**不依赖**其它 Case；与 ST-resp-001（`completed`）互为 terminal 类型对照。

> 实现状态：Implemented（`at_dp_resp_10.py` 已断言本 case 契约）；执行状态与 Verdict 只在 Run 报告。
