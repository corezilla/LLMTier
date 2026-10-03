<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-RESP-013 — truncation 未知字段被拒

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-RESP-013` |
| Document Version | `0.1.0-draft.5` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-RESP-013.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-RESP-013` / 系统设计 §8 Responses 接口 / `VRC-INF-001` / negative / P2（[方案清单 `ST-RESP-013`](../llmtier-system-test-scheme.md)）。
- **测试方法（§2.2 方法表行）**：错误猜测 + 反例驱动（ERR-*）
- 要测什么（责任展开）：`POST /v1/responses` 携带 `truncation`（未知顶层字段）：`400 unsupported_field`（"Request body contains unknown fields"，`param="truncation"`），dispatch 前拒绝、零副作用。契约由 OpenAPI `ResponsesRequest.additionalProperties:false` + 实现 `src/inference/responses.py` 的 `ALLOWED_FIELDS`（不含 `truncation`）与 `require(unknown is None, 400, "unsupported_field", "Request body contains unknown fields", unknown)` 定义。
- 明确不测什么 / 失败含义：不测任何截断策略（`truncation` 不改变输入截断行为，本版本无该参数）；不测 `max_output_tokens` 截断（ST-RESP-010）；不测合法流式成功（ST-RESP-001/06）。失败含义＝未知顶层字段未被拒（违反 `additionalProperties:false`）。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `POST /v1/responses`（`src/http_api/app.py`）；角色 `data`。

```text
POST /v1/responses
Authorization: Bearer dev-data
Content-Type: application/json
```

- 初态构造（经公开入口）：**环境 A**（m5air 现有实例，无状态；见[系统测试计划 §2](../llmtier-system-test-plan.md)）。初始状态 = 3 provider / 4 deployment / 7 fixed tier。**不需要上游可用**（校验在 dispatch 之前）。
- Fixture / 向量及版本：固定请求 body（合法四字段 + 非请求字段），随 Run manifest 存档。
- 依赖的测试资产（tests.asset-design 文档）：`api_client`（Data 角色客户端）；就绪检查由 `conftest.py::pytest_configure` 自动执行（任一失败 → 整班 BLOCKED/SKIP）。

## 3. 输入构造

- 逐参数输入构造：固定请求（合法四字段 + 非请求字段）：

```json
{
  "model": "Worker",
  "input": [{"role": "user", "content": "hi"}],
  "stream": true,
  "store": false,
  "truncation": "auto"
}
```

- 边界/非法取值及理由：`stream=true`/`store=false` 先通过跨字段要求；`truncation` 不在 `ALLOWED_FIELDS`，触发未知字段拒绝。可选对照：去掉 `truncation` 重发应 200。
- 规模 / 时间域：单次请求；校验在 dispatch 前，不涉及上游时延预算。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /healthz`、`GET /readyz`（由 `pytest_configure` 自动执行） | 计划 §2 基线 |
| 2 | `POST /v1/responses`（上表 body） | status / Content-Type / body |
| 3 | 断言观测形态，按当前机器契约判定 | `status_code == 400`，JSON 错误信封（非 SSE） |
| 4 | 解析 `resp.json()["error"]` | `code=="unsupported_field"`、`message` 含 `"unknown fields"`、`type=="request_error"`、`param=="truncation"`、`retryable is False`，键集恰 5 键 |
| 5 | 可选对照：去掉 `truncation` 重发 | `200` + SSE |

- 重点关注步骤：① **未知字段路径**——`truncation` 既不在 OpenAPI `ResponsesRequest`，也不在 `ALLOWED_FIELDS`；② **错误码归因**——未知字段 → `unsupported_field`（系统 §7.8 `ERR-REQ-FIELD`），`param` 为未知字段名；③ **拒绝在 dispatch 前、零副作用**；④ **方案与脚本一致**——该行为 `400 unsupported_field`，[`ST-RESP-013.py`](../../../../tests/system/cases/ST-RESP-013.py) 第 34-38 行亦断言 `400` + `unsupported_field` + `param=="truncation"`。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：OpenAPI `ResponsesRequest.additionalProperties:false` + `ErrorEnvelope`/`ErrorDetail`（[`interfaces/openapi/llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)），不依赖实现答案。**判据语义以设计验证项 `VRC-INF-001` 为唯一权威**；本节细化为可执行断言，仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：HTTP `400`；`Content-Type: application/json`；`error.code=="unsupported_field"`、`type=="request_error"`、`param=="truncation"`、`retryable=false`；无 SSE。"静默忽略"（200 + SSE）不是候选真值。

## 6. 错误路径、副作用与清理

- 错误出口与表现：未知顶层字段 → `400 unsupported_field`（"Request body contains unknown fields"，`param="truncation"`），可观察且非 SSE。
- 副作用断言与清理：**无需 teardown**——环境 A 无状态；拒绝在 dispatch 前，无上游调用、无账本义务。退出前确认 `/readyz` 仍 7 tier。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：[`tests/system/cases/ST-RESP-013.py`](../../../../tests/system/cases/ST-RESP-013.py)（已断言 `400 unsupported_field` + `param=="truncation"`）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/system/cases/ST-RESP-013.py -q`。
- 实现状态：Implemented；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：`400` + `unsupported_field` + `param=="truncation"` + 非 SSE + 零副作用。
- FAIL：返回 `200`（未知字段被接受，违反 `additionalProperties:false`）；或 status/code 不符（如 `invalid_request`）、`param` 非 `"truncation"`、返回 SSE、信封键集错。
- BLOCKED：测试代码/契约问题。
- SKIP：就绪检查不满足。
- INVALID：以 mock/替代路径冒充真实路径。
- NOT_RUN：本 Case 有实现，未执行时记 `NOT_RUN`。

**证据与 Run**：保存请求 body、HTTP status/headers、原始错误信封、可选对照、发出命令、exit code、环境快照（本 case `environment:"a"`）。

**依赖**：就绪检查；`api_client`；OpenAPI `ResponsesRequest`；实现 `src/inference/responses.py`（`ALLOWED_FIELDS`）；自动化入口 `ST-RESP-013.py`。**不依赖**其它 Case；与 ST-RESP-012/14 同类。
