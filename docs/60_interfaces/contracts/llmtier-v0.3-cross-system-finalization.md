<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Cross-system Simplification Candidate

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-v0.3-cross-system-finalization` |
| Document Version | `0.3.1-draft.6` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | Piko, Slinky |
| Approver | 待定 |
| Approval Date | 待定 |
| Created Date | `2026-09-16` |
| Last Modified Date | `2026-09-22` |
| Template Version | `0.1.0` |
| Template ID | `contracts.specification` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/60_interfaces/contracts/llmtier-v0.3-cross-system-finalization.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 定型范围与机器权威

Current candidate是`0.3-simplified-candidate.8`。OpenAPI和manifest是唯一current machine artifacts；旧candidate只作历史审计。

## 2. Operation、鉴权与公共字段

Bearer auth、standard trace context和response `X-Request-ID`。没有SourceInstance、custom deadline/idempotency/invocation headers。Request ID不承担task/session/recovery语义。

## 3. Responses 与 tool loop 逐字段表

| Field | Producer | Consumer/Meaning |
|---|---|---|
| model | Piko | exact logical model ID；LLMTier不alias/fallback |
| input | Piko | 本次调用完整上下文；不由LLMTier补历史 |
| stream/store | Piko | 固定Pi首阶段固定`true/false`；只走标准SSE |
| tools/tool_choice | Piko | 可调用工具描述；LLMTier不执行 |
| assistant/reasoning/function历史 | Piko | 保留标准item ID与opaque reasoning；LLMTier不形成conversation |
| output function_call | Model/LLMTier | 保留item ID/call ID；Piko执行并在新请求提交result |
| SSE terminal | LLMTier | item identity一致，恰有一个completed/incomplete/failed/error终点 |
| usage | LLMTier | 标准token/details；缺失为Unknown，不把成功结果改失败 |

## 4. Registry 与 Models 字段

Model只发布id、availability及responses/embeddings/tools/structured output/modalities/context/output limits。Embedding model还发布稳定space ID、维数、batch和输入上限；不兼容空间必须新model ID。物理provider/account不暴露；compatibility协商不是必需面。

## 5. Usage 与 Slinky/Piko 消费

Piko主要聚合response usage形成任务usage；必要时按request_id查询`/v1/usage`。同request的更高record version替换旧值，response和query不得重复相加；store失败为typed 503。Slinky可为Memory/运维读取相同token事实。没有Cost、capacity或执行状态。

## 6. Embeddings 完整契约

标准POST成功/标准错误；无202 active、Invocation ID、custom replay、410 tombstone或Responses GET。Memory负责自己的输入和索引幂等。

## 7. 旧接口一次性退役版本

退出current authority：SourceInstance；capacity/Seat/claim；custom Idempotency/Invocation/recovery/deadline；cross-system release；compatibility endpoint；clients/sources/entitlements/recovery admin；Cost；Topic/SID/RID等业务字段。没有deprecated acceptance或fallback。

## 8. A/B/C 分栏与剩余项

- A跨系统：标准 Responses SSE 沿用已接受candidate.5语义；candidate.6只增加LLMTier operator主页与只读脱敏日志面，不改变Piko/Slinky模型消费字段。
- B LLMTier内部：provider adapters、embedding deployment、queue/concurrency、Usage store、Admin UI、auth/TLS/runbook。
- C联调：SDK capture、真实token、429/5xx、embedding维数、health/restart、UI安全。

## 9. Validation 与 immutable evidence

静态validator检查refs、fixtures和旧path/schema absence。提交后记录commit/hash；当前文档不宣称实现或activation。
