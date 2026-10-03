<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-RESP-007 — store=true 被拒

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-RESP-007` |
| Document Version | `0.1.0-draft.4` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-RESP-007.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。方案清单行见[系统测试方案 §6 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-RESP-007` / 系统设计 §8 Responses 接口（POST /v1/responses） / `VRC-INF-001` / `negative` / `P0`。本文件名 `st-resp-007.md`，与 Case ID 唯一对应。
- **测试方法（§2.2 方法表行）**：错误猜测 + 反例驱动（ERR-*）
- 要测什么（责任展开）：`POST /v1/responses` 传 `store=true`：在 dispatch 前返回 `400 unsupported_request`，零副作用。
- 明确不测什么 / 失败含义：**不证明什么**——不证明 `stream=false` 被拒（ST-RESP-002）；不证明合法流式成功（ST-RESP-001/06）；不证明任何持久化/会话恢复语义（本版本不存在）。**失败含义＝`store` 跨字段硬约束破坏**。

**目的（被测契约）**：验证 Data Plane `POST /v1/responses` 的 **`store` 跨字段硬约束**——本版本不保存 provider conversation 状态，仅受理 `store=false`（OpenAPI `ResponsesRequest.store.const=false`；
[piko-data-plane-control.md](../../../60_interfaces/piko-data-plane-control.md) §"LLMTier 只透传/规范化，不保存 Agent conversation"）。
被测端点/规则：`POST /v1/responses`；需求 `LT-INT-006`；设计验证项 `VRC-INF-001`；错误目录 `ERR-REQ-UNSUPPORTED` → wire `code=unsupported_request`；
实现 `src/inference/responses.py`（同一 `require(stream is True and store is False, 400, "unsupported_request", ...)`）（[系统测试方案 §6](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。
**不证明什么**：不证明 `stream=false` 被拒（ST-RESP-002）；不证明合法流式成功（ST-RESP-001/06）；不证明任何持久化/会话恢复语义（本版本不存在）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 现有实例，角色 `data`，无状态；见[系统测试方案 §1 测试边界](../llmtier-system-test-scheme.md)）。前置 = 就绪检查（由 `conftest.py::pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP）。fixture `api_client`（Data 角色客户端）。初始状态 = 3 provider / 4 deployment / 7 fixed tier。**不需要上游可用**（校验在 dispatch 之前）。
- **被测入口**：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Content-Type: application/json
  ```

- **初态构造与客户端**：只读无状态；凭据固定 `data`（经 `api_client` 注入）。
- **依赖的测试资产（tests.asset-design 文档）**：本阶段 `tests.asset-design` 文档尚未建立；`api_client` 等夹具契约见方案 §4。

## 3. 输入构造

- **输入与构造**：固定请求（只翻转 `store=true`，保持 `stream=true` 以隔离 store 约束）：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Content-Type: application/json
  ```

  ```json
  {
    "model": "Worker",
    "input": [{"role": "user", "content": "hi"}],
    "stream": true,
    "store": true
  }
  ```

  构造点：`stream=true` 通过第一条跨字段要求，使失败唯一归因于 `store`；不注入故障。
- **规模 / 时间域**：单次 POST；无分页/并发；记录 `elapsed` 供报告。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认基线（由 `pytest_configure` 自动执行）。
  2. `POST /v1/responses`（上表 body）。
  3. 断言 `resp.status_code == 400`，响应为 JSON 错误信封（非 SSE）。
  4. 解析 `resp.json()["error"]`，断言键集恰 5 键、`code=="unsupported_request"`、`type=="request_error"`、`param is None`、`retryable is False`。
  5. 交叉核对零副作用：`GET /v1/usage` 无新增 obligation（可选）。

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 确认基线（`pytest_configure` 自动执行） | 就绪检查通过 |
| 2 | `POST /v1/responses`（`store=true`） | status / headers / body |
| 3 | 断言 400 且为 JSON 错误信封（非 SSE） | 响应头/体 |
| 4 | `code=="unsupported_request"`、`type=="request_error"`、`param None`、`retryable False`、5 键 | 响应体 |
| 5 | 交叉核对零副作用（可选 `GET /v1/usage`） | 账本 |

**重点关注步骤**：① **零副作用是重点**——`store=true` 的拒绝必须**不落任何 provider conversation 状态**，且无上游调用；② **信封 identity**（5 键、`type=request_error`、无 `category`）；③ **非 SSE**；④ **只翻转 store**，与 ST-RESP-002 形成配对；⑤ message 与 `stream=false` 共用同一条 `require`，均为 `"Only stream=true and store=false are supported"`。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `store.const=false` + `ErrorEnvelope`（[`interfaces/openapi/llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)）+ 系统设计 §7.8 `ERR-REQ-UNSUPPORTED`。**判据语义以设计验证项 `VRC-INF-001` 为唯一权威**。
  - HTTP：`400`；`Content-Type: application/json`。
  - body：`{"error":{"message":"Only stream=true and store=false are supported","type":"request_error","code":"unsupported_request","param":null,"retryable":false}}`。
  - 无 SSE 帧；无 `[DONE]`；无 provider conversation 持久化副作用。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：status 400 + `code=unsupported_request` + `type=request_error` + `param=null` + `retryable=false` + 非 SSE + 零副作用 match。
  - **FAIL**：任一断言不符（含返回 200/SSE）。
  - **BLOCKED**：测试代码/契约问题——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：就绪前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：以 mock/替代路径冒充真实路径——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（方案清单 `RUN`），未执行时记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：本 case 的"错误出口"即被拒绝的 400 `unsupported_request`（期望路径）；若返回 200/SSE 则按 §5 判 FAIL 并保留原始错误信封与失败现场。
- **副作用断言与清理**：**无需 teardown**——环境 A 无状态；退出前确认 `/readyz` 仍 7 tier。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[计划 §7/§10](../llmtier-system-test-scheme.md)：保存请求 body、HTTP status/headers、原始错误信封、发出命令、exit code、环境快照；manifest 与报告落位见计划 §7/§10（本 case `environment:"a"`）；失败现场不截断。
- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`api_client`（[系统测试方案 §4 测试环境类型](../llmtier-system-test-scheme.md)）；需求 `LT-INT-006`（[llmtier-requirements.md](../../../10_requirements/llmtier-requirements.md)）；自动化入口 [`ST-RESP-007.py`](../../../../tests/system/cases/ST-RESP-007.py)。**不依赖**其它 Case；与 ST-RESP-002 互补。

> 实现状态：Implemented（`ST-RESP-007.py` 已断言本 case 契约）；执行状态与 Verdict 只在 Run 报告。
