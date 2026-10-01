<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-resp-021 — 客户端中途断开

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-resp-021` |
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
| Canonical Path | `docs/70_verification/system/cases/st-resp-021.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-resp-021` / 系统设计 §8 Responses 接口 / `VRC-INF-001` / recovery / P1（[方案清单 `ST-resp-021`](../llmtier-system-test-scheme.md)）；机制 `T-DISCONNECT`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）。
- **测试方法（§1.5 方法表行）**：故障注入（客户端中途断开）+ 有界重试 + 复位阶梯
- 要测什么（责任展开）：`POST /v1/responses` 客户端在 SSE 发送阶段断开：出口记 `aborted`、无成功终态、许可释放（自动化入口 `at_dp_resp_21.py`）。SSE 发送阶段 `BrokenPipeError`/`ConnectionResetError` 被 M001 捕获，记录 trace `aborted`（reason `client disconnected`），不产生"半个成功"，且准入许可被释放。实现 `src/http_api/app.py`（`except (BrokenPipeError, ConnectionResetError): diagnostics.record_trace(request_id, "aborted", {"reason":"client disconnected"}); return`）。
- 明确不测什么 / 失败含义：不测 `stream_terminate`/`malformed_event` 注入路径；不测账本在 `create()` 返回前已收敛的细节（本 case 只要求无"半个成功"）；不测答案。失败含义＝客户端断开契约破坏。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `POST /v1/responses`（流式，`data`）与 `GET /v1/trace/{request_id}`（`admin`）。

```text
POST /v1/responses                 Authorization: Bearer dev-data
GET  /v1/trace/{request_id}        Authorization: Bearer dev-admin
```

- 初态构造（经公开入口）：**环境 B**（临时 LLMTier 实例，fixture `llmtier_b_diag`）。专属实例避免与其它 case 抢占许可。`_baseline_settings`：`prov_b` + `depl_b` + 7 tier；`depl_b` 已 probe `healthy`；随后经 `PATCH /v1/deployments/depl_b` 把 `backend_model` 改为 `force-huge-stream`（teardown 恢复 `test-model`）。
- Fixture / 向量及版本：`LLMTierInstance`、`api_client_b`；`force-huge-stream`（输出远超 socket 缓冲）请求向量，随 Run manifest 存档。
- 依赖的测试资产（tests.asset-design 文档）：B 类 fixture `LLMTierInstance` / `api_client_b`。

## 3. 输入构造

- 逐参数输入构造：被测请求（`stream=true`），`depl_b.backend_model="force-huge-stream"` 使上游 SSE 帧数远超 socket 缓冲（约 20000 帧）：

```json
{"model": "Senior", "input": [{"role": "user", "content": "Count from 1 to 1000."}], "stream": true, "store": false, "max_output_tokens": 2000}
```

- 边界/非法取值及理由：断开构造——以 `httpx` 流式读取，读满 **>=1** 个事件（至少 `response.created`）后立即关闭响应/连接（退出 `with` 前 break），不读完整流。
- 规模 / 时间域：一次巨量输出流；断开后服务端必有一次写入失败（超出 socket 缓冲），故 `aborted` 确定出现。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | （fixture 前置）启动实例并 probe `depl_b` → `healthy` | 实例就绪 |
| 2 | `with api_client_b.stream("POST", "/v1/responses", json=...) as resp:` | `status_code == 200` 与 `text/event-stream` |
| 3 | 读取至少一个事件后**主动关闭连接**（不读到 terminal） | 客户端截断位置 |
| 4 | 记录本次 `X-Request-ID` | 响应头 `X-Request-ID` |
| 5 | 以 `admin` 调 `GET /v1/trace/{request_id}` | trace 含 `aborted` 阶段且 `reason=="client disconnected"`（服务端观测；字段名以实现为准） |
| 6 | 校验无"半个成功" | 本次流中**不出现** terminal（`response.completed`/`response.incomplete`/`response.failed`）与 `[DONE]` |
| 7 | 紧随其后发一个正常 `POST /v1/responses` | 可正常准入（许可已释放）并返回 `200` + terminal |

- 重点关注步骤：① **服务端捕获断开**——必须记录 trace `aborted`（`reason=client disconnected`），而非静默或崩溃；② **无半个成功**——断开后不得把已发事件当完成成功；③ **许可释放**——后续请求可准入（验证 `finally` 释放）；④ **账本已在 `create()` 返回前收敛**——`usage.finish` 早于流发送；⑤ **确定性构造**——上游 `force-huge-stream` 输出远超 socket 缓冲，断开后服务端写入必然失败 ⇒ `aborted` 确定出现；测试用硬断言轮询 trace，**不使用非 strict `pytest.xfail`**（不得掩盖真实缺陷）；⑥ **自动化入口**——`at_dp_resp_21.py` 已实现。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：机制 `T-DISCONNECT`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）+ 系统设计 §6（`aborted`、无 terminal、许可释放）。**判据语义以设计验证项 `VRC-INF-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：首响 `200` + `text/event-stream`（在断开前）；断开后客户端未收到 terminal/`[DONE]`，服务端 `GET /v1/trace/{request_id}` 记 `aborted`（reason `client disconnected`）；后续请求 `200` + 唯一 terminal + `[DONE]`（许可未泄漏）。

## 6. 错误路径、副作用与清理

- 错误出口与表现：客户端断开 → 服务端 trace `aborted`，无 terminal；不得当成功。
- 副作用断言与清理：无注入/无持久写；断开只影响本连接。专属实例按计划整班销毁。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：[`tests/system/api_test_v03/at_dp_resp_21.py`](../../../../tests/system/api_test_v03/at_dp_resp_21.py)（已实现）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_resp_21.py -q`。
- 实现状态：Implemented；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：首响 200 SSE；断开被服务端记为 `aborted`；无半个成功；后续请求正常准入。
- FAIL：服务端未记 `aborted`（静默/崩溃）、把断开当成功、许可未释放致后续请求阻塞/失败。
- BLOCKED：trace 视图不可读（`GET /v1/trace/{request_id}` 不可用）。断开路径已确定性构造（`force-huge-stream` + 硬断言），不再以 xfail 兜底。
- SKIP：B 类临时实例不可用。
- INVALID：以 mock/替代路径冒充真实路径。
- NOT_RUN：本 Case 有实现（`at_dp_resp_21.py`），未执行记 `NOT_RUN`。

**证据与 Run**：保存请求、首响 status/headers（含 `X-Request-ID`）、已读事件与断开位置、`GET /v1/trace/{request_id}` 的 `aborted`、后续请求响应、发出命令、exit code、环境快照（本 case `environment:"b"`）。

**依赖**：B 类 fixture `LLMTierInstance` / `api_client_b`；`GET /v1/trace/{request_id}`（ST-obsreqtrace-001）；实现 `src/http_api/app.py`；机制 `T-DISCONNECT`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）。**不依赖**其它 Case。
