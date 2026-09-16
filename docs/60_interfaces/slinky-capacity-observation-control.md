<!-- STD_DOCUMENT_COVER_BEGIN -->
# Slinky ↔ LLMTier Usage and Embeddings Interface Control

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-slinky-capacity-observation-control` |
| Document Version | `0.3.2-draft.1` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | Slinky |
| Approver | 待定 |
| Approval Date | 待定 |
| Created Date | `2026-09-07` |
| Last Modified Date | `2026-09-17` |
| Template Version | `0.3.0` |
| Template ID | `interfaces.control` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/60_interfaces/slinky-capacity-observation-control.md` |
| Supersedes | `docs/99_reference/contracts/slinky-capacity-observation-contract-v0.3.md` |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 接口目的、范围与双方 authority

Slinky Memory只消费标准Embeddings与token Usage。Slinky拥有材料分块、向量库、索引、检索、正式记忆和业务验收；LLMTier只做向量化和模型服务。文件名保留以维持文档引用，但“capacity observation”旧范围已经退出current authority。

## 2. 接口注册表

- `POST /v1/embeddings`
- `GET /v1/models` / detail：选择 `capabilities.embeddings=true` 的 exact model
- `GET /tier/v1/usage`：只读token事实
- `GET /healthz` / `/readyz`：环境检查

没有capacity snapshot、Seat、Invocation、recovery、Cost或compatibility endpoint。

## 3. 传输与物理边界

HTTPS/JSON/Bearer auth。Memory调用不进入Piko的模型调用控制面，也不传Project/Memory对象给LLMTier；只发送标准embedding request内容。

## 4. 数据、命令与 Schema

`EmbeddingRequest`含exact `model`、`input`、可选`encoding_format/dimensions/user`。`EmbeddingResponse`含vectors、model和可空usage。UsageRecord含request/model/endpoint/time、measurement status/source以及可空token字段；unknown不得补零。Cost不在Schema中。

## 5. 状态机、顺序和时序

每个embedding POST独立。Slinky在本地把有效结果原子关联到自己的index generation；LLMTier不持有Memory generation或索引状态。

## 6. 错误、timeout、重试、幂等和恢复

使用标准400/401/404/429/502/503。重试由Slinky Memory按标准HTTP/client policy决定；无custom Idempotency、Invocation、202 active、410 tombstone或Responses GET recovery。

## 7. 并发、流控、容量与性能

内部保护可返回429/Retry-After。Slinky不读取或计算Tier Seat/capacity；向量维数、batch限制和输入上限由Models能力与请求校验表达。

## 8. 安全、身份、权限和隔离

credential只标识获授权调用主体；不引入SourceInstance。Memory内容不得进入普通日志；向量输出的存储权限由Slinky管理。

## 9. 版本协商、兼容矩阵与弃用

无专用协商endpoint。旧Observation/Capacity/Cost contract与fixtures退出current authority；不作为fallback。

## 10. Contract fixture、验证与证据

正例覆盖float/base64、batch index、usage measured/estimated/unknown；负例覆盖非embedding model、维数不支持、unknown field、旧path不存在。production embedding deployment/capture尚未完成。

## 11. 未决项与双方批准

LLMTier内部待选择并配置dedicated embedding deployment；Slinky需在实现阶段验证实际维数、输入上限和结果入库。没有新的跨系统协议待定。
