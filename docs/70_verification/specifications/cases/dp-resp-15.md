<!-- STD_DOCUMENT_COVER_BEGIN -->
# DP-RESP-15 — temperature 受理 / top_p 未知字段被拒

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `DP-RESP-15` |
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
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/cases/dp-resp-15.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`DP-RESP-15` / 系统设计 §8 Responses 接口 / `VRC-INF-001` / negative / P2（[方案清单 `DP-RESP-15`](../../schemes/llmtier-system-test-scheme.md)）；机制 `T-STREAM`。
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（ERR-*）
- 要测什么（责任展开）：`POST /v1/responses` 携带 `temperature` 与 `top_p`：`temperature` 为合法字段被受理，`top_p` 不属请求字段、组合命中 `400 unsupported_field`（`param="top_p"`）。OpenAPI `ResponsesRequest` 声明 `temperature`（`number`，`[0,2]`）为合法可选字段，但**未声明 `top_p`**；实现 `src/inference/responses.py` 的 `ALLOWED_FIELDS` 同样只含 `temperature`。
- 明确不测什么 / 失败含义：不测 `temperature` 对生成结果的数值影响（temperature/top_p 不参与断言）；不测任何别名；不测合法流式成功（DP-RESP-01/06）。失败含义＝字段白名单语义被破坏。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `POST /v1/responses`；角色 `data`。

```text
POST /v1/responses
Authorization: Bearer dev-data
Content-Type: application/json
```

- 初态构造（经公开入口）：**环境 A**（m5air 现有实例，无状态）。初始状态 = 3 provider / 4 deployment / 7 fixed tier。`temperature` 路径需要上游可用；`top_p` 拒绝路径不需要。
- Fixture / 向量及版本：两个子请求（a：仅 `temperature`；b：`temperature` + `top_p`），随 Run manifest 存档。
- 依赖的测试资产（tests.asset-design 文档）：`api_client`；`conftest.py::pytest_configure` 就绪检查。

## 3. 输入构造

- 逐参数输入构造：两个子请求。

（a）`temperature` 单独（期望受理）：

```json
{
  "model": "Worker",
  "input": [{"role": "user", "content": "say hello"}],
  "stream": true,
  "store": false,
  "temperature": 0.7
}
```

（b）`temperature` + `top_p`（期望拒绝）：

```json
{
  "model": "Worker",
  "input": [{"role": "user", "content": "say hello"}],
  "stream": true,
  "store": false,
  "temperature": 0.7,
  "top_p": 0.9
}
```

- 边界/非法取值及理由：`temperature ∈ [0,2]`；`top_p` 不在 `ALLOWED_FIELDS`；`stream=true`/`store=false` 先通过跨字段要求，使 (b) 的失败唯一归因于 `top_p`。
- 规模 / 时间域：两个子请求；`temperature` 走一次成功流，`top_p` 在 dispatch 前拒绝。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /healthz`、`GET /readyz`（由 `pytest_configure` 自动执行） | §2.1 基线 |
| 2 | `POST /v1/responses`（子请求 a，仅 `temperature`） | `status_code == 200`、`Content-Type` 含 `text/event-stream`、含 `response.completed` |
| 3 | `POST /v1/responses`（子请求 b，含 `top_p`） | `status_code == 400`，JSON 错误信封（非 SSE） |
| 4 | 解析 (b) 的 `error` | `code=="unsupported_field"`、`message` 含 `"unknown fields"`、`type=="request_error"`、`param=="top_p"`、`retryable is False`，键集恰 5 键 |

- 重点关注步骤：① **字段白名单**——只有 `temperature` 合法，`top_p` 是未知字段；② **错误码归因**——`unsupported_field`（系统 §7.8 `ERR-REQ-FIELD`），`param` 为未知字段名；③ **temperature 不参与数值断言**；④ **方案与脚本一致**——[`at_dp_resp_15.py`](../../../../tests/system/api_test_v03/at_dp_resp_15.py) 第 37-49 行亦断言 `temperature` 200 + `top_p` 400 `unsupported_field` + `param=="top_p"`。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：OpenAPI `ResponsesRequest`（含 `temperature`、不含 `top_p`）+ `ErrorEnvelope`/`ErrorDetail`（[`interfaces/openapi/llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)）。**判据语义以设计验证项 `VRC-INF-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：(a) HTTP `200` + `text/event-stream` + `response.completed`；(b) HTTP `400`；`Content-Type: application/json`；`error.code=="unsupported_field"`、`type=="request_error"`、`param=="top_p"`、`retryable=false`；无 SSE。

## 6. 错误路径、副作用与清理

- 错误出口与表现：`top_p` 未知字段 → `400 unsupported_field`（`param="top_p"`），可观察且非 SSE。
- 副作用断言与清理：**无需 teardown**——`store=false`、环境 A 无状态；拒绝在 dispatch 前。退出前确认 `/readyz` 仍 7 tier。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：[`tests/system/api_test_v03/at_dp_resp_15.py`](../../../../tests/system/api_test_v03/at_dp_resp_15.py)（已断言 `temperature` 200 + `top_p` 400 `unsupported_field` + `param=="top_p"`）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_resp_15.py -q`。
- 实现状态：Implemented；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：(a) 200 + SSE；(b) `400` + `unsupported_field` + `param=="top_p"` + 非 SSE。
- FAIL：(a) 非 200；或 (b) 被接受（200）/返回非 `unsupported_field`/`param` 非 `"top_p"`。
- BLOCKED：测试代码/契约问题。
- SKIP：就绪检查不满足。
- INVALID：以 mock/替代路径冒充真实路径。
- NOT_RUN：本 Case 有实现，未执行时记 `NOT_RUN`。

**证据与 Run**：保存 (a)/(b) 请求 body、HTTP status/headers、原始响应（SSE 与错误信封）、发出命令、exit code、环境快照（本 case `environment:"a"`）。

**依赖**：就绪检查；`api_client`；OpenAPI `ResponsesRequest`；实现 `src/inference/responses.py`（`ALLOWED_FIELDS`）；自动化入口 `at_dp_resp_15.py`。**不依赖**其它 Case。
