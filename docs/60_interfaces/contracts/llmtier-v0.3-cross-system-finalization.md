<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Cross-system Simplification Candidate

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-v0.3-cross-system-finalization` |
| Document Version | `0.3.1-draft.1` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | Piko, Slinky |
| Approver | 待定 |
| Approval Date | 待定 |
| Created Date | `2026-09-16` |
| Last Modified Date | `2026-09-17` |
| Template Version | `0.3.0` |
| Template ID | `contracts.specification` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/60_interfaces/contracts/llmtier-v0.3-cross-system-finalization.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 定型范围与机器权威

Current candidate是`0.3-simplified-candidate.1`。OpenAPI和manifest是唯一current machine artifacts；旧candidate只作历史审计。

## 2. Operation、鉴权与公共字段

Bearer auth、standard trace context和response `X-Request-ID`。没有SourceInstance、custom deadline/idempotency/invocation headers。Request ID不承担task/session/recovery语义。

## 3. Responses 与 tool loop 逐字段表

| Field | Producer | Consumer/Meaning |
|---|---|---|
| model | Piko | exact logical model ID；LLMTier不alias/fallback |
| input | Piko | 本次调用完整上下文；不由LLMTier补历史 |
| tools/tool_choice | Piko | 可调用工具描述；LLMTier不执行 |
| output function_call | Model/LLMTier | Piko执行并在新请求提交result |
| usage | LLMTier | measured/estimated；unknown为null |

## 4. Registry 与 Models 字段

Model只发布id、availability及responses/embeddings/tools/structured output/modalities/context/output limits。物理provider/account不暴露；ETag/compatibility协商不是必需面。

## 5. Usage 与 Slinky/Piko 消费

Piko主要聚合response usage形成任务usage；必要时按request_id查询`/tier/v1/usage`。Slinky可为Memory/运维读取相同token事实。没有Cost、capacity或执行状态。

## 6. Embeddings 完整契约

标准POST成功/标准错误；无202 active、Invocation ID、custom replay、410 tombstone或Responses GET。Memory负责自己的输入和索引幂等。

## 7. 旧接口一次性退役版本

退出current authority：SourceInstance；capacity/Seat/claim；custom Idempotency/Invocation/recovery/deadline；cross-system release；compatibility endpoint；clients/sources/entitlements/recovery admin；Cost；Topic/SID/RID等业务字段。没有deprecated acceptance或fallback。

## 8. A/B/C 分栏与剩余项

- A跨系统：仅standard streaming是否首版需要，owner Piko+LLMTier。
- B LLMTier内部：provider adapters、embedding deployment、queue/concurrency、Usage store、Admin UI、auth/TLS/runbook。
- C联调：SDK capture、真实token、429/5xx、embedding维数、health/restart、UI安全。

## 9. Validation 与 immutable evidence

静态validator检查refs、fixtures和旧path/schema absence。提交后记录commit/hash；当前文档不宣称实现或activation。
