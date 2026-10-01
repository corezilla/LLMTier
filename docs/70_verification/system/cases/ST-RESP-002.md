<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-RESP-002 — stream=false 被拒

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-RESP-002` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-RESP-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。方案清单行见[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-RESP-002` / 系统设计 §8 Responses 接口（POST /v1/responses） / `VRC-INF-001` / `negative` / `P0`。本文件名 `st-resp-002.md`，与 Case ID 唯一对应。
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（ERR-*）
- 要测什么（责任展开）：`POST /v1/responses` 传 `stream=false`：在 dispatch 前返回 `400 unsupported_request`，零副作用。
- 明确不测什么 / 失败含义：**不证明什么**——不证明 `store=true` 被拒（ST-RESP-007，反向约束）；不证明合法流式成功与事件序列（ST-RESP-001/06）；不证明上游调用、模型答案或账本行为（本 case 在 dispatch 前拒绝）。**失败含义＝`stream` 跨字段硬约束破坏**。

**目的（被测契约）**：验证 Data Plane `POST /v1/responses` 的 **`stream` 跨字段硬约束**——本版本仅受理 `stream=true`（OpenAPI `ResponsesRequest.stream` 为 `const:true`；ISD M003 `additionalProperties:false` + 跨字段硬约束）。被测端点/规则：`POST /v1/responses`；设计验证项 `VRC-INF-001`；错误目录 `ERR-REQ-UNSUPPORTED` → wire `code=unsupported_request`（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md) §7.8）；实现 `src/inference/responses.py`（`require(body.get("stream") is True and body.get("store") is False, 400, "unsupported_request", "Only stream=true and store=false are supported")`）（[系统测试方案 §3](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明 `store=true` 被拒（ST-RESP-007，反向约束）；不证明合法流式成功与事件序列（ST-RESP-001/06）；不证明上游调用、模型答案或账本行为（本 case 在 dispatch 前拒绝）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 现有实例，角色 `data`，无状态；见[系统测试方案 §1 测试边界](../llmtier-system-test-scheme.md)）。前置 = 就绪检查（由 `conftest.py::pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP）。fixture = `api_client`（Data 角色客户端）。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier。**不需要上游可用**（校验在路由/dispatch 之前）。
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

- **输入与构造**：固定请求（固定 prompt）：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Content-Type: application/json
  ```

  ```json
  {
    "model": "Worker",
    "input": [{"role": "user", "content": "Hello"}],
    "stream": false,
    "store": false
  }
  ```

  构造点：只翻转 `stream` 为 `false`，保持 `store=false`，以**隔离 stream 约束**（若同时 `store=true` 则先命中其它分支，无法区分违反哪一条）；`model` 取合法 responses-capable tier；其余字段齐备，避免先命中"缺字段"校验。
- **规模 / 时间域**：单次 POST；无分页/并发；记录 `elapsed` 供报告。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `POST /v1/responses`（上表 body）。
  3. 断言 `resp.status_code == 400`；断言响应头 `Content-Type` 含 `application/json`（**不是** `text/event-stream`）。
  4. 解析 `resp.json()["error"]`，断言键集恰为 `{message,type,code,param,retryable}`（无 `category`）。
  5. 断言 `code=="unsupported_request"`、`type=="request_error"`、`param is None`、`retryable is False`。
  6. 交叉核对零副作用：本响应非 SSE；如需强证据，`GET /v1/usage`（同 principal + 当前时间窗）确认**无新增已完成 obligation**（拒绝即无副作用）。

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 确认基线（`pytest_configure` 自动执行） | 就绪检查通过 |
| 2 | `POST /v1/responses`（`stream=false`） | status / headers / body |
| 3 | 断言 400 + `application/json`（非 SSE） | 响应头 |
| 4 | error 键集恰 5 键（无 `category`） | 响应体 |
| 5 | `code=="unsupported_request"`、`type=="request_error"`、`param None`、`retryable False` | 响应体 |
| 6 | 交叉核对零副作用（`GET /v1/usage` 无新增 obligation） | 账本 |

**重点关注步骤**：① **拒绝位置**——必须在 `router.admit`/上游调用**之前**，不得先发上游再报错；② **信封 identity**——恰 5 键、`type` 由状态导出（400 < 500 ⇒ `request_error`）、无 `category`；③ **非 SSE**——错误走 `_json(exc.status, exc.envelope(), ...)`，不得以 `text/event-stream` 返回被当成功流吞掉；④ **只翻转 stream**——`store=false` 保持，保证失败归因唯一；⑤ **零副作用**——不产生账本义务/上游调用。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `ErrorEnvelope`/`ErrorDetail` 契约（[`interfaces/openapi/llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)）+ 系统设计 §7.8 `ERR-REQ-UNSUPPORTED`（不依赖实现答案）。**判据语义以设计验证项 `VRC-INF-001` 为唯一权威**。
  - HTTP：`400`；`Content-Type: application/json`。
  - body：`{"error":{"message":"Only stream=true and store=false are supported","type":"request_error","code":"unsupported_request","param":null,"retryable":false}}`。
  - 无 SSE 帧；无 `[DONE]`。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：status 400 + `code=unsupported_request` + `type=request_error` + `param=null` + `retryable=false` + 非 SSE 全部 match。
  - **FAIL**：任一断言不符（status 非 400、code 错、返回 200/SSE 被吞、信封键集错）。
  - **BLOCKED**：测试代码/契约问题（解析器逻辑错、断言不可实现）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：就绪前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 mock/替代路径冒充真实 m5air 路径——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（方案清单 `RUN`），未执行时记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：本 case 的"错误出口"即被拒绝的 400 `unsupported_request`（期望路径）；若返回 200/SSE 则按 §5 判 FAIL 并保留原始错误信封与失败现场。
- **副作用断言与清理**：**无需 teardown**——环境 A 只读/无状态，未创建/修改/删除任何资源；退出前确认 `/readyz` 仍显示 7 tier（见[系统测试方案 §5](../llmtier-system-test-scheme.md)）。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-system-test-scheme.md)：保存请求 body、HTTP status/headers、原始错误信封（脱敏后）、发出命令、exit code、环境快照（`/healthz`/`/readyz`）；manifest 与报告落位见 §4.8/§10（本 case `environment:"a"`）；失败现场不截断。
- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`api_client` fixture（[系统测试方案 §4 共同机制](../llmtier-system-test-scheme.md)）；responses-capable tier `Worker`；自动化入口 [`at_dp_resp_02.py`](../../../../tests/system/api_test_v03/at_dp_resp_02.py)。**不依赖**其它 Case；与 ST-RESP-007（`store=true`）互补但各自独立执行。

> 实现状态：Implemented（`at_dp_resp_02.py` 已断言本 case 契约）；执行状态与 Verdict 只在 Run 报告。
