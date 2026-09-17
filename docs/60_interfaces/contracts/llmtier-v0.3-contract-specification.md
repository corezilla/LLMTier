<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Contract Specification

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-v0.3-contract-specification` |
| Document Version | `0.3.2-draft.3` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | Piko, Slinky |
| Approver | 待定 |
| Approval Date | 待定 |
| Created Date | `2026-09-07` |
| Last Modified Date | `2026-09-17` |
| Template Version | `0.1.0` |
| Template ID | `contracts.specification` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/60_interfaces/contracts/llmtier-v0.3-contract-specification.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. Contract scope 与 authority

唯一字段级 authority 是 `interfaces/openapi/llmtier-v0.3.openapi.json` version `0.3-simplified-candidate.5`。Manifest只描述范围和activation，不复制字段。`runtime_activation=false`，本候选不授权runtime。

## 2. Operation / Message / Event Catalog

Current consumer operations：Responses、Embeddings、Models、token Usage、health/readiness。Current operator operations：Provider/Deployment/ServiceLevel CRUD、Probe、Usage、Audit。没有跨系统event或调用恢复operation。

## 3. Request、Response、Event 与数据对象

Responses支持固定Pi实际使用的easy message、assistant历史、opaque reasoning、function tool/call/output和image tool result；每次完整输入，`stream:true/store:false`，使用标准SSE的text/refusal/reasoning/function/terminal事件且保持item identity。最终refusal content固定为标准`{type:"refusal",refusal:string}`，不得改写成`output_text`。Embeddings支持string或string array；`encoding_format`缺省/`float`时返回有限JSON number array，`base64`时返回RFC 4648字符串，其内容固定为连续little-endian IEEE-754 float32。请求与响应表示必须一致，严格核验解码、4字节对齐、有限值和维数；同一逻辑model ID保持同一 `embedding_space_id`。Models发布exact ID和真实能力。Usage使用标准token字段并记录质量、版本、finality、request/model/time；无Cost。

## 4. 状态、错误和 blocker catalog

标准错误：invalid_request、authentication_error、model_not_found、rate_limit_exceeded、provider_error、service_unavailable、conflict。不存在InvocationStatus、Seat状态、RecoveryDisposition或compatibility status。

## 5. 幂等、并发、事务与一致性

外部契约不承诺custom idempotency/exactly-once。内部admission/queue/concurrency不暴露资源状态。管理CRUD须一致地校验引用并审计；PATCH为原子局部更新，PATCH/DELETE使用ETag/If-Match，失败不得留下partial write。实现并发控制不得扩展consumer协议。

## 6. Pagination、filter、ordering 与 retention

Usage按from/to必填，可选model/request_id，按 `(recorded_at,request_id)` 稳定排序；首个页面固定有期限snapshot及每个request的具体record version，cursor绑定principal、当前授权和原filter且不跨filter复用。页间更正/插入只进入新snapshot；snapshot到期、权限缩小、签名或filter不符返回400 `invalid_request`。同一request只选择snapshot冻结版本，绝不重复相加。dispatch前必须已有持久unknown Usage义务；因此terminal后计量写失败或崩溃时，重启后仍能返回unknown而不是空页。store不可读返回typed 503。Admin列表同样冻结序列化view/ETag并逐页复核授权。模型列表不分页。Retention是LLMTier内部政策，未知不得伪造成零；不对消费者承诺旧M2-C窗口。

## 7. 身份、权限、Secret 与调用边界

Bearer credential只用于授权，不形成Client/Source/SourceInstance DTO。Admin credential独立。Secret只写引用、view仅`has_secret`。不传Agent/Run/Project/IR/STD/Session。

## 8. 版本、兼容性与迁移

本候选一次性替代`0.3-finalization-candidate.5`，旧custom endpoints/headers/schemas/fixtures成为历史，无runtime fallback或alias。legacy `/call`不属于current contract。

## 9. Positive/Negative fixture 与 validator

Current fixtures：`openai-surface-fixtures.json`、`usage-fixtures.json`、`admin-model-fixtures.json`、`stateless-gateway-boundary-fixtures.json`。Validator必须解析全部refs，执行SSE sequence/delta/done/terminal identity及refusal形状、Embedding float/base64表示与维数、Usage unknown/source/subset/单调版本、分页snapshot及崩溃顺序、Admin并发条件和旧custom术语/path absence检查；不能用“文件可解析”冒充语义通过。

## 10. Requirement → Contract → Test traceability

CT-DP-001、CT-MODEL-001、CT-EMB-001、CT-USAGE-001、CT-ADMIN-001、CT-OPS-001、CT-BOUNDARY-001、CT-SCOPE-001映射见requirements traceability。

## 11. Activation Gate 与未决项

需要实现、provider capture、Piko对标准SSE事件子集的消费签署、Embedding consumer test、auth/TLS/operations、Admin UI test。streaming设计范围不再待决。
