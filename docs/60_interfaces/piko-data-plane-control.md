<!-- STD_DOCUMENT_COVER_BEGIN -->
# Piko ↔ LLMTier Data Plane Interface Control

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-piko-data-plane-control` |
| Document Version | `0.3.2-draft.4` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | Piko |
| Approver | 待定 |
| Approval Date | 待定 |
| Created Date | `2026-09-07` |
| Last Modified Date | `2026-09-22` |
| Template Version | `0.1.0` |
| Template ID | `interfaces.control` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/60_interfaces/piko-data-plane-control.md` |
| Supersedes | `docs/99_reference/contracts/piko-data-plane-contract-v0.3.md` |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 接口目的、范围与双方 authority

Piko 拥有 Agent session、完整输入装配、压缩、tool loop、任务 deadline/budget 和执行内 retry。LLMTier 只提供标准 OpenAI-compatible 模型服务，不读取 Piko Run/Session/IR/STD，也不执行工具或管理 backend KV identity。

## 2. 接口注册表

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/responses` | 完整输入的一次模型调用；首阶段固定 `stream:true/store:false` 标准 SSE |
| GET | `/v1/models` | 逻辑模型列表 |
| GET | `/v1/models/{model}` | exact-case 模型能力 |
| GET | `/v1/usage` | 调用主体自己的 token Usage 查询；Piko可按 request ID 汇总任务用量 |

无 Invocation、response retrieval、custom recovery、capacity、compatibility 或 caller-management endpoint。

## 3. 传输与物理边界

HTTPS + JSON + Bearer auth；production TLS/auth 尚未激活。标准 `traceparent` 可用于诊断。响应 `X-Request-ID` 只作关联，不是 session、task、idempotency 或 recovery identity。

## 4. 数据、命令与 Schema

Piko 每次发送 `ResponsesRequest.model`、`stream:true`、`store:false` 和该轮所需的完整 `input`；`model` 是 exact service-level ID。固定 Pi 0.85.1 的真实请求形状是本契约的兼容证据：首轮 `system|developer|user` easy message 不要求 `type`；历史 assistant message 可带 `id/status/phase` 和 `output_text.annotations`；function call 同时保留 item `id` 与 `call_id`；`function_call_output.output` 可以是 string，或由 `input_text|input_image` 构成的数组；opaque reasoning item 原样进入下一轮历史。模型输出 tool call 后，Piko 自行执行工具，并在新的完整请求中提交相同 `call_id` 的 result。LLMTier只透传/规范化，不保存 Agent conversation。

`ResponsesResponse.usage` 使用标准字段 `input_tokens/output_tokens/total_tokens`，并在存在时保留 `input_tokens_details.cached_tokens/cache_write_tokens` 与 `output_tokens_details.reasoning_tokens`。`input_tokens`包含cached token，`cached_tokens`是其子集；`cache_write_tokens`是额外观测细分，不再加进`input_tokens`或`total_tokens`；`reasoning_tokens`是`output_tokens`子集。缺失 usage 不会把成功模型结果改成失败；Piko将该调用记为 Unknown。`GET /v1/usage` 中同一 `request_id` 的较高 `record_version` 替换较低版本，不能和响应usage重复相加。Piko可按自身 task/run 聚合不同 request 的最新事实，LLMTier不接收 task identity。

## 5. 状态机、顺序和时序

每次 HTTP request 独立：validate → internal admit → provider call → response/error。它不是 Agent conversation 状态机。Piko task 与单次模型 request 的顺序、停止和继续由 Piko 管理。

## 6. 错误、timeout、重试、幂等和恢复

400 validation、401 auth、404 exact model not found、429 rate limited、502 provider failure、503 unavailable。429 可携带 Retry-After。Piko在自己的 deadline/budget 内决定 retry；V0.3 不承诺模型级 exactly-once，不定义 custom Idempotency-Key、Invocation、UnknownOutcome 或结果恢复协议。

网络结果未知时不得由 LLMTier推导 Piko任务成功/失败；Piko按标准 client/provider semantics处理。具有副作用的工具不在 LLMTier 内执行。

## 7. 并发、流控、容量与性能

LLMTier内部 queue/concurrency guard 可返回429/503，但不暴露 Seat、claim、capacity snapshot、shared pool或quota composition。Piko自身执行容量与LLMTier内部模型保护互不替代。

## 8. 安全、身份、权限和隔离

Bearer credential控制Data Plane访问；不定义Client/Source/SourceInstance产品层级。普通响应/日志不回显credential、Provider Secret或prompt/output。模型ID不能用于推导物理provider/account。

## 9. 版本协商、兼容矩阵与弃用

不提供运行时compatibility negotiation endpoint。版本通过发布的OpenAPI/manifest和显式变更review管理。legacy `/call` 与旧custom recovery contract一次性退出consumer authority，无alias或fallback。

## 10. Contract fixture、验证与证据

验证：固定Pi golden request（首轮easy message、assistant历史、function call/output、image tool result、opaque reasoning）、标准SSE item identity与terminal、refusal/reasoning事件、exact model、429/5xx、标准usage存在/缺失及查询替换、旧path/header absence。真实Pi/provider capture属于实现Gate，不阻止设计候选review，但阻止activation。

## 11. 定型候选与双方批准

固定 Pi 0.85.1、commit `9767ba275f3e9a5ee0f5c5342249b629ab1b2282` 的 `openai-responses.ts::buildParams` 固定发送 `stream:true` 与 `store:false`；契约据此只支持这一条标准Responses SSE路径，不建立non-stream fallback。必需事件为 created、output item added/done、text delta、refusal delta/done、reasoning summary/text delta/done、function arguments delta/done、completed/incomplete/failed 与 error；同一 output item 的 `item.id`、`output_index` 必须一致，成功流必须恰有一个terminal，terminal response携带可用Usage。Piko消费签署与真实capture仍是activation gate，runtime activation=false。
