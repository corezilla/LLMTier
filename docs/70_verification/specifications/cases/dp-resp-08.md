<!-- STD_DOCUMENT_COVER_BEGIN -->
# DP-RESP-08 — 缺 model

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `DP-RESP-08` |
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
| Canonical Path | `docs/70_verification/specifications/cases/dp-resp-08.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。方案清单行见[系统测试方案 §3 覆盖分母与 Case 清单](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`DP-RESP-08` / 系统设计 §8 Responses 接口（POST /v1/responses） / `VRC-INF-001` / `negative` / `P0`。本文件名 `dp-resp-08.md`，与 Case ID 唯一对应。
- 要测什么（责任展开）：`POST /v1/responses` 缺 `model`：字段齐备性校验失败，`400 invalid_request`（清单记 `param=model`）。
- 明确不测什么 / 失败含义：**不证明什么**——不证明未知 model 的解析失败（DP-RESP-05，属 `model_not_found`）；不证明 `stream=false`/`store=true` 的跨字段拒绝（DP-RESP-02/07）；不证明上游调用或答案。**失败含义＝必填字段齐备性契约破坏**。

**目的（被测契约）**：验证 Data Plane `POST /v1/responses` 的**必填字段齐备性**：`model`/`input`/`stream`/`store` 四者缺一即在 dispatch 前拒绝。被测端点/规则：`POST /v1/responses`；需求 `LT-FUN-001`；设计验证项 `VRC-INF-001`；错误目录 `ERR-REQ-VALIDATION` → wire `code=invalid_request`；实现 `src/inference/responses.py`（`require({"model","input","stream","store"} <= set(body), 400, "invalid_request", "model, input, stream, and store are required")`）（[系统测试方案 §3](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明未知 model 的解析失败（DP-RESP-05，属 `model_not_found`）；不证明 `stream=false`/`store=true` 的跨字段拒绝（DP-RESP-02/07）；不证明上游调用或答案。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 现有实例，角色 `data`，无状态；见[系统测试方案 §1 测试边界](../../schemes/llmtier-system-test-scheme.md)）。前置 = 就绪检查（由 `conftest.py::pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP）。fixture `api_client`（Data 角色客户端）。初始状态 = 3 provider / 4 deployment / 7 fixed tier。**不需要上游可用**（校验在 dispatch 之前）。
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

- **输入与构造**：固定请求（省略 `model`，其余三字段齐备）：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Content-Type: application/json
  ```

  ```json
  {
    "input": [{"role": "user", "content": "hi"}],
    "stream": true,
    "store": false
  }
  ```

  构造点：仅缺 `model`；`input`/`stream`/`store` 齐备，使失败唯一归因于缺失的 `model`；不注入故障。
- **规模 / 时间域**：单次 POST；无分页/并发；记录 `elapsed` 供报告。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认基线（由 `pytest_configure` 自动执行）。
  2. `POST /v1/responses`（上表 body）。
  3. 断言 `resp.status_code == 400`，响应为 JSON 错误信封（非 SSE）。
  4. 解析 `resp.json()["error"]`，断言 `code=="invalid_request"`、`type=="request_error"`、`retryable is False`；键集恰 5 键。
  5. 断言 `error.param == "model"`（清单 / OpenAPI `ResponsesRequest.required` 契约；实现 `responses.py:72-73` 已把缺失字段名作为 `param` 传入），并记录实测值。
  6. 交叉核对零副作用：无上游调用、无账本义务（可选）。

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 确认基线（`pytest_configure` 自动执行） | 就绪检查通过 |
| 2 | `POST /v1/responses`（缺 `model`） | status / headers / body |
| 3 | 断言 400 且为 JSON 错误信封（非 SSE） | 响应头/体 |
| 4 | `code=="invalid_request"`、`type=="request_error"`、`retryable False`、5 键 | 响应体 |
| 5 | 断言 `param=="model"` 并记录实测值 | 响应体 |
| 6 | 交叉核对零副作用（可选） | 上游/账本 |

**重点关注步骤**：① **拒绝先于模型解析**——齐备性检查在 `get_service_level`/`admit` 之前，缺 `model` 不得报 `model_not_found`；② **信封 identity**（5 键、`type=request_error`、无 `category`）；③ **非 SSE**；④ **`param` 归因**——契约值 `param=="model"`（实现已传入）；⑤ **零副作用**。
> **实现说明（登记）**：本 case 的契约值 `error.param == "model"`（方案清单与 OpenAPI `ResponsesRequest.required` 均如此），当前实现 [`responses.py`](../../../../src/inference/responses.py) 第 72-73 行已把缺失字段名作为 `param` 传给 `require(...)`（`require(missing is None, 400, "invalid_request", "model, input, stream, and store are required", missing)`），故 wire 上 `param` 即缺失字段名（`"model"`）。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `ResponsesRequest.required`（`model` 必填）+ `ErrorEnvelope`/`ErrorDetail` + 系统设计 §7.8 `ERR-REQ-VALIDATION`。**判据语义以设计验证项 `VRC-INF-001` 为唯一权威**。
  - HTTP：`400`；`Content-Type: application/json`。
  - body：`error.code=="invalid_request"`、`type=="request_error"`、`retryable==false`；`message` 含 `"required"` 语义（实现为 `"model, input, stream, and store are required"`）。
  - `error.param == "model"`（方案清单 / OpenAPI；实现 `responses.py:72-73` 已传入该字段名）。
  - 无 SSE 帧/`[DONE]`。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：status 400 + `code=invalid_request` + `type=request_error` + `retryable=false` + `param=="model"` + 非 SSE + 零副作用。
  - **FAIL**：status/code 错、`param` 非 `"model"`、报 `model_not_found`、返回 200/SSE、信封键集错。
  - **BLOCKED**：测试代码/契约问题——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：就绪前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：以 mock/替代路径冒充真实路径——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（方案清单 `RUN`），未执行时记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：本 case 的"错误出口"即被拒绝的 400 `invalid_request`（期望路径）；若报 `model_not_found` 或返回 200/SSE 则按 §5 判 FAIL 并保留原始错误信封与失败现场。
- **副作用断言与清理**：**无需 teardown**——环境 A 无状态；退出前确认 `/readyz` 仍 7 tier。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../../schemes/llmtier-system-test-scheme.md)：保存请求 body、HTTP status/headers、原始错误信封（含 `param` 实测）、发出命令、exit code、环境快照；manifest 与报告落位见 §4.8/§10（本 case `environment:"a"`）；失败现场不截断。
- **依赖**：[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`api_client`（[系统测试方案 §4 共同机制](../../schemes/llmtier-system-test-scheme.md)）；需求 `LT-FUN-001`；自动化入口 [`at_dp_resp_08.py`](../../../../tests/system/api_test_v03/at_dp_resp_08.py)（只断 status+code，未断 `param`）。**不依赖**其它 Case；与 DP-RESP-05 区分：本 case 无 `model` 字段，非未知值。

> 实现状态：Implemented（`at_dp_resp_08.py` 已断言 status+code；`param` 断言待补）；执行状态与 Verdict 只在 Run 报告。
