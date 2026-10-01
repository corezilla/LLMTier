<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-resp-026 — 流截断注入 stream_terminate

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-resp-026` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-10-01` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/st-resp-026.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-resp-026` / 系统设计 §8 Responses 接口（POST /v1/responses） / `VRC-DIAG-004` / recovery / P1（[方案清单 `ST-resp-026`](../llmtier-system-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：故障注入（stream_terminate 流截断）+ 复位阶梯

- 要测什么（责任展开）：注入 `stream_terminate` 后，`POST /v1/responses`（stream=true）的 SSE 流在达到 `stream_terminate_after_events` 个事件后**提前结束**（不再有 terminal 事件与 `[DONE]`），客户端可观察到截断。需求 `R-OBS-01`；机制 `T-OBS-INJECT`（[observability §14.4](../../../20_system_design/mechanisms/observability.md)）；实现 `src/libdiag/stream.py::stream_wrapper`（`count >= stream_terminate_after_events → return`）。

- 明确不测什么 / 失败含义：不测 `malformed_event`（ST-resp-027）；不测前置阶段注入 `fault_502/503/rate_limit/delay`（ST-resp-011/22/20）；不测正常流事件序列（ST-resp-001）；不测注入配置读写校验（ST-obsdepl-001..04）。失败含义＝流截断注入未生效或事件计数语义错误。

**目的（被测契约）**：验证 **SSE 流阶段的故障注入**（`stream_terminate`）行为。被测端点/规则：先 `PATCH /v1/deployments/{deployment_id}/diagnostics` 写入 `stream_terminate`；随后 `POST /v1/responses`（stream=true）的响应经 [`app.py`](../../../../src/http_api/app.py) 的 `app.diagnostics.stream_wrapper(...)` 包裹，[`stream.py`](../../../../src/libdiag/stream.py) 在第 N 个事件后 `return`，流提前结束。设计验证项 `VRC-DIAG-004`；机制 `T-OBS-INJECT`。**不证明什么**：不测 `malformed_event`/前置注入/正常序列/配置校验。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例）。前置 = 方案 §5 附加（B 类）就绪检查；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier，`llmtier_b` probe `depl_b` 为 `healthy`。`prov_b.endpoint` 必须是 LAN IP 上的 fake provider（TS-003）。fixture = `llmtier_b`、`admin_client_b`（注入写/读）、`api_client_b`（Data Plane）。初始状态 = `diagnostic_injections` 为空。
- **被测入口**：

  ```http
  PATCH /v1/deployments/depl_b/diagnostics HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```

  ```http
  POST /v1/responses HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-data
  Content-Type: application/json
  Accept: text/event-stream
  ```

## 3. 输入构造

- **输入与构造**：先写注入（admin 面），再发被测请求（data 面）。
  注入写：
  ```json
  {"items": [{"type": "stream_terminate", "config": {"stream_terminate_after_events": 2}, "enabled": true}]}
  ```
  被测请求：
  ```json
  {"model": "Senior", "input": [{"role": "user", "content": "Hello"}], "stream": true, "store": false}
  ```
- **边界/非法取值及理由**：`stream_terminate_after_events` 取小正整数（如 2，范围 `[1,10000]`）；`enabled=true` 才生效；注入按 `(deployment_id, injection_type)` upsert，仅作用于 `depl_b`。`stream=true`/`store=false` 是唯一受理形态。
- **规模 / 时间域**：单次注入写 + 单次被测请求；记录 `elapsed`。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | （fixture 前置）启动 `llmtier_b`、probe `depl_b=healthy`、确认注入为空 | 实例就绪 |
| 2 | `PATCH .../diagnostics` 写入 `stream_terminate` | 200 + `stream_terminate enabled=true`（因） |
| 3 | `POST /v1/responses`（`model=Senior`，stream=true） | SSE 流 |
| 4 | 解析 SSE 事件 | 事件数在截断点附近终止；**无** terminal（`response.completed`/`response.failed`）且**无** `[DONE]` |
| 5 | （teardown，`finally`）`PATCH .../diagnostics` body `{"items": []}` 并二次 `GET` | 清空校验 |

- **重点关注步骤**：① **注入命中证明**——步骤 2 的 200+enabled 是因，步骤 4 的截断是果，同 deployment 闭环；② **截断语义**——`stream_wrapper` 在 yield 第 N 个 chunk 后 `return`，客户端连接结束；**不**追加 terminal/`[DONE]`；③ **不是错误信封**——流已以 200 `text/event-stream` 开始，截断表现为连接提前结束，而非 JSON 错误；④ **与 `malformed_event` 区分**（ST-resp-027）；⑤ **teardown 完整性**——`finally` 清空并二次 `GET` 校验为空，绝不残留注入。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **独立 Oracle 来源与推导**：OpenAPI Responses SSE 事件契约 + 机制 `observability` §14.4（`stream_terminate`）+ [`stream.py`](../../../../src/libdiag/stream.py) 的计数语义。
  - 注入写：`PATCH` → `200`，`InjectionView[]` 含 `{type:"stream_terminate", enabled:true}`。
  - 被测流：`200` + `Content-Type: text/event-stream`；在 `stream_terminate_after_events` 个事件后流终止；**无** terminal 事件、**无** `[DONE]`。
  - teardown：`PATCH {"items":[]}` → `200`；`GET` 校验为空。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：注入写 200 且生效；流在截断点后终止且无 terminal/`[DONE]`；teardown 生效。
  - **FAIL**：流未截断、截断点错误、或出现 terminal/`[DONE]`（截断未生效）；或 teardown 未清空。
  - **BLOCKED**：注入写 API 不可用或注入无法命中。
  - **SKIP**：B 类临时实例不可用、附加前置不满足。
  - **INVALID**：注入未命中却按行为判定，或以 mock/替代路径冒充。
  - **NOT_RUN**：有实现但本轮未执行。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：流未截断/截断点错/出现 terminal → FAIL；注入写失败 → BLOCKED。保留原始 SSE 字节流与失败现场。
- **副作用断言与清理**：**必须 teardown（`finally` 强制）**——`PATCH /v1/deployments/depl_b/diagnostics` body `{"items":[]}` 清空，随后 `GET` 校验无启用项；不修改 `prov_b`/`depl_b` 配置。B 类实例按方案 §4 整班销毁。清空失败必须报错，不得把启用注入留给后续 Case。

## 7. 自动化位置与状态

- **测试文件 / 测试函数**：[`tests/system/api_test_v03/at_dp_resp_26.py`](../../../../tests/system/api_test_v03/at_dp_resp_26.py)（已实现）。
- **单 Case 执行命令**：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_resp_26.py -q`。
- **实现状态**：Implemented；执行与 Verdict 归 Run 报告。

**证据与 Run**：保存注入写请求/响应、被测 SSE 原始字节流（含事件计数）、teardown 的 `PATCH items:[]` 与随后 `GET`、发出命令、exit code、`elapsed`、环境快照（本 case `environment:"b"`）。

**依赖**：B 类 fixture `llmtier_b` / `admin_client_b` / `api_client_b`；`ST-obsdepl-002`（注入写）；实现 `src/libdiag/stream.py`、`src/http_api/app.py`；机制 `T-OBS-INJECT`。**不依赖**其它 Case；与 ST-resp-027 互补。

