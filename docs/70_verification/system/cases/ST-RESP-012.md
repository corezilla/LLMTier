<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-RESP-012 — conversation_id 未知字段被拒

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-RESP-012` |
| Document Version | `0.1.0-draft.4` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-RESP-012.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。方案清单行见[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-RESP-012` / 系统设计 §8 Responses 接口（POST /v1/responses） / `VRC-INF-001` / `negative` / `P2`。本文件名 `st-resp-012.md`，与 Case ID 唯一对应。
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（ERR-*）
- 要测什么（责任展开）：`POST /v1/responses` 携带 `conversation_id`（未知顶层字段）：`400 unsupported_field`（"Request body contains unknown fields"，`param="conversation_id"`），dispatch 前拒绝、零副作用。
- 明确不测什么 / 失败含义：**不证明什么**——不证明任何 conversation 持久化/续写（本版本不存在，[piko-data-plane-control.md](../../../60_interfaces/piko-data-plane-control.md)）；不证明禁字段清单路径（ST-RESP-009，`previous_response_id` 命中 `unsupported_field`）；不证明合法流式成功（ST-RESP-001/06）。**失败含义＝未知字段拒绝契约破坏**。

**目的（被测契约）**：验证 Data Plane `POST /v1/responses` 对**非请求字段 `conversation_id`** 的处理契约。契约由 OpenAPI `ResponsesRequest.additionalProperties:false` + 实现 `src/inference/responses.py` 的 `ALLOWED_FIELDS`（不含 `conversation_id`）与 `require(unknown is None, 400, "unsupported_field", "Request body contains unknown fields", unknown)` 共同定义：未知顶层字段在 dispatch 前被拒，`code=unsupported_field`、`param`=首个未知字段名。
设计验证项 `VRC-INF-001`（[系统测试方案 §3](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明任何 conversation 持久化/续写（本版本不存在）；
不证明禁字段清单路径（ST-RESP-009，`previous_response_id` 命中 `unsupported_field`）；不证明合法流式成功（ST-RESP-001/06）。

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

- **输入与构造**：固定请求（合法四字段 + 非请求字段）：

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
    "store": false,
    "conversation_id": "conv_ignored_test"
  }
  ```

  构造点：`stream=true`/`store=false` 先通过跨字段要求；`conversation_id` 不在 `ALLOWED_FIELDS`，触发未知字段拒绝。同 case 可选对照：省略 `conversation_id` 时同一请求应成功（证明失败确由该字段引起）。
- **规模 / 时间域**：单次 POST（可选去字段对照）；无分页/并发；记录 `elapsed` 供报告。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认基线（由 `pytest_configure` 自动执行）。
  2. `POST /v1/responses`（上表 body）。
  3. 断言观测形态，并按**当前机器契约**判定：`status_code == 400`，响应为 JSON 错误信封（非 SSE）。
  4. 解析 `resp.json()["error"]`，断言 `code=="unsupported_field"`、`message` 含 `"unknown fields"`、`type=="request_error"`、`param=="conversation_id"`、`retryable is False`，键集恰 5 键。
  5. 可选对照：以同一 body **去掉 `conversation_id`** 重发，断言 `200` + SSE（隔离归因）。

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 确认基线（`pytest_configure` 自动执行） | 就绪检查通过 |
| 2 | `POST /v1/responses`（携带 `conversation_id`） | status / headers / body |
| 3 | 断言 400 且为 JSON 错误信封（非 SSE） | 响应头/体 |
| 4 | `code=="unsupported_field"`、message 含 `"unknown fields"`、`type=="request_error"`、`param=="conversation_id"`、`retryable False`、5 键 | 响应体 |
| 5 | （可选）去掉字段重发断言 200 + SSE | 隔离归因 |

**重点关注步骤**：① **未知字段路径**——`conversation_id` 不在 OpenAPI `ResponsesRequest` 属性、亦不在 `ALLOWED_FIELDS`，故被 `additionalProperties:false` 等价校验拒绝；
② **错误码归因**——未知字段 → `unsupported_field`（系统 §7.8 `ERR-REQ-FIELD`），`param` 为未知字段名；③ **拒绝在 dispatch 前、零副作用**；④ **方案清单与脚本一致**——清单记 `400 unsupported_field`，[`ST-RESP-012.py`](../../../../tests/system/cases/ST-RESP-012.py) 第 34-38 行亦断言 `400` + `unsupported_field` + `param=="conversation_id"`，契约已收敛于拒绝语义。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `ResponsesRequest.additionalProperties:false` + `ErrorEnvelope`/`ErrorDetail`（[`interfaces/openapi/llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)），**不依赖实现"答案内容"**。**判据语义以设计验证项 `VRC-INF-001` 为唯一权威**。
  - HTTP `400`；`Content-Type: application/json`；`error.code=="unsupported_field"`、`type=="request_error"`、`param=="conversation_id"`、`retryable=false`；无 SSE。
  - "静默忽略"（200 + SSE）不是候选真值：清单与脚本均为拒绝语义。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`400` + `unsupported_field` + `param=="conversation_id"` + 非 SSE + 零副作用。
  - **FAIL**：返回 `200`（未知字段被接受，违反 `additionalProperties:false`）；或 status/code 不符（如 `invalid_request`）、`param` 非 `"conversation_id"`、返回 SSE、信封键集错。
  - **BLOCKED**：测试代码/契约问题（`param`/错误码语义不清、断言不可实现）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：就绪前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：以 mock/替代路径冒充真实路径——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（方案清单 `RUN`），未执行时记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：本 case 的"错误出口"即被拒绝的 400 `unsupported_field`（期望路径）；若返回 200/SSE 或 `invalid_request` 则按 §5 判 FAIL 并保留原始错误信封与失败现场。
- **副作用断言与清理**：**无需 teardown**——环境 A 无状态；退出前确认 `/readyz` 仍 7 tier。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-system-test-scheme.md)：保存请求 body、HTTP status/headers、原始错误信封、可选对照请求响应、发出命令、exit code、环境快照；manifest 与报告落位见 §4.8/§10（本 case `environment:"a"`）；失败现场不截断。
- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`api_client`（[系统测试方案 §4 共同机制](../llmtier-system-test-scheme.md)）；OpenAPI `ResponsesRequest`；实现 `src/inference/responses.py`（`ALLOWED_FIELDS`）；自动化入口 [`ST-RESP-012.py`](../../../../tests/system/cases/ST-RESP-012.py)（已断言 `400 unsupported_field` + `param=="conversation_id"`）。**不依赖**其它 Case；与 ST-RESP-013/14 同类（未知字段），与 ST-RESP-009（显式禁字段）区分。

> 实现状态：Implemented（`ST-RESP-012.py` 已断言本 case 契约）；执行状态与 Verdict 只在 Run 报告。
