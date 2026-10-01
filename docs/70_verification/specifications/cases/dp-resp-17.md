<!-- STD_DOCUMENT_COVER_BEGIN -->
# DP-RESP-17 — embedding-only 等级发 Responses

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `DP-RESP-17` |
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
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/cases/dp-resp-17.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`DP-RESP-17` / 系统设计 §8 Responses 接口 / `VRC-INF-001` / recovery / P1（[方案清单 `DP-RESP-17`](../../schemes/llmtier-system-test-scheme.md)）；机制 `T-STREAM`。
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（ERR-MODEL：embedding-only 等级发 Responses）
- 要测什么（责任展开）：`POST /v1/responses` 使用 embedding-only 等级：`400 unsupported_model`（`param=model`）（自动化入口 `at_dp_resp_17.py`）。所选 model 的能力声明必须 `capabilities.responses == true`，否则在 dispatch 前拒绝。错误目录 `ERR-REQ-MODEL` → wire `code=unsupported_model`；实现 `src/inference/responses.py`（`require(caps.get("responses") is True, 400, "unsupported_model", "Selected model does not support Responses", "model")`）；需求链 `LT-FUN-001`/`LT-INT-001`、`R-INF-01`。
- 明确不测什么 / 失败含义：不测缺少 `model`（DP-RESP-08）或未知 model（DP-RESP-05）；不测 `tools`/`max_output_tokens` 的次级能力门；不测上游调用（在能力门拒绝）。失败含义＝能力门契约破坏。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `POST /v1/responses`；角色 `data`。

```text
POST /v1/responses
Authorization: Bearer dev-data
Content-Type: application/json
```

- 初态构造（经公开入口）：**环境 A**（m5air 现有实例，无状态）。`/readyz` 含 7 fixed tier（含 `Embedding-v1`）。初始状态 = 3 provider / 4 deployment / 7 fixed tier；`Embedding-v1` 为 embedding-only（`capabilities.responses == false`）。**不需要上游可用**（能力门在 dispatch 前）。
- Fixture / 向量及版本：固定请求（embedding-only 等级 + responses 形态 body），随 Run manifest 存档。
- 依赖的测试资产（tests.asset-design 文档）：`api_client`；`conftest.py::pytest_configure` 就绪检查。

## 3. 输入构造

- 逐参数输入构造：固定请求（embedding-only 等级 + responses 形态 body）：

```json
{
  "model": "Embedding-v1",
  "input": [{"role": "user", "content": "hi"}],
  "stream": true,
  "store": false
}
```

- 边界/非法取值及理由：`model="Embedding-v1"` 必须是 7 fixed tier 之一（否则先命中 DP-RESP-05 的 `model_not_found`）；`stream=true`/`store=false` 通过跨字段要求，使失败唯一归因于能力门。
- 规模 / 时间域：单次请求；能力门在 dispatch 前，不涉及上游时延预算。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /healthz`、`GET /readyz`（由 `pytest_configure` 自动执行） | §2.1 基线及 `Embedding-v1` 存在 |
| 2 | `POST /v1/responses`（上表 body） | status / Content-Type / body |
| 3 | 断言观测形态 | `status_code == 400`，JSON 错误信封（非 SSE） |
| 4 | 解析 `error` | `code=="unsupported_model"`、`param=="model"`、`type=="request_error"`、`retryable is False`，键集恰 5 键 |

- 重点关注步骤：① **能力门先于路由**——在 `get_service_level` 成功后、`admit` 前拒绝；不得为 embedding-only 等级尝试路由；② **`param="model"`**——本错误码实现显式带 `param`（与 DP-RESP-08 的 `null` 不同）；③ **信封 identity**（5 键、无 `category`）；④ **非 SSE**；⑤ **自动化入口**——`at_dp_resp_17.py` 已实现并覆盖上述断言。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：OpenAPI `ResponsesRequest.model` + 等级能力声明 + `ErrorEnvelope`/`ErrorDetail` + 系统设计 §7.8 `ERR-REQ-MODEL`（不依赖实现答案）。**判据语义以设计验证项 `VRC-INF-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：HTTP `400`；`Content-Type: application/json`；body：`{"error":{"message":"Selected model does not support Responses","type":"request_error","code":"unsupported_model","param":"model","retryable":false}}`；无 SSE 帧/`[DONE]`。

## 6. 错误路径、副作用与清理

- 错误出口与表现：embedding-only 等级发 Responses → `400 unsupported_model`（`param=model`），可观察且非 SSE。
- 副作用断言与清理：**无需 teardown**——环境 A 无状态；拒绝在 dispatch 前。退出前确认 `/readyz` 仍 7 tier。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：[`tests/system/api_test_v03/at_dp_resp_17.py`](../../../../tests/system/api_test_v03/at_dp_resp_17.py)（已实现）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_resp_17.py -q`。
- 实现状态：Implemented；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：status 400 + `code=unsupported_model` + `param="model"` + `type=request_error` + `retryable=false` + 非 SSE。
- FAIL：status/code/param 错、返回 200/SSE、信封键集错。
- BLOCKED：测试代码/契约问题。
- SKIP：就绪检查不满足（`Embedding-v1` 缺失等）。
- INVALID：以 mock/替代路径冒充真实路径。
- NOT_RUN：本 Case 有实现（`at_dp_resp_17.py`），未执行记 `NOT_RUN`。

**证据与 Run**：保存请求 body、HTTP status/headers、原始错误信封、发出命令、exit code、环境快照（`/readyz` 含 `Embedding-v1`；本 case `environment:"a"`）。

**依赖**：就绪检查；`api_client`；fixed tier `Embedding-v1` 的 `capabilities.responses=false`；错误目录 `ERR-REQ-MODEL`（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md) §7.8）。**不依赖**其它 Case。
