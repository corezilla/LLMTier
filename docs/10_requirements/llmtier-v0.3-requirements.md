<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Requirements Specification

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-v0.3-requirements` |
| Document Version | `0.3.2-draft.7` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | Piko、Slinky、LLMTier |
| Approver | LLMTier |
| Approval Date | 待定 |
| Created Date | `2026-09-07` |
| Last Modified Date | `2026-09-18` |
| Template Version | `0.1.0` |
| Template ID | `requirements.specification` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/10_requirements/llmtier-v0.3-requirements.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 目的、范围与来源

本文把用户于 2026-09-17 确认的简化边界写成 LLMTier V0.3 当前需求：LLMTier 是标准 OpenAI-compatible、无 Agent 会话状态的模型网关。Piko 管 Agent 上下文、工具循环和执行内重试；Slinky 管业务流程与记忆。

V0.3 外部范围：Responses、Embeddings、Models、token Usage、health/readiness，以及仅供 operator 使用的模型/等级管理、探测、Usage 与审计。runtime activation 仍为 false。

## 2. 系统/产品上下文

- Piko 是 Responses consumer，并对每次调用提供完整当前输入。
- Slinky Memory 是 Embeddings consumer；分块、索引、向量库和检索不属于 LLMTier。
- Operator 使用英文 Web UI/Admin API 管理云模型、本地模型和逻辑等级。
- Provider/local inference server 是 LLMTier 的外部依赖。

## 3. 假设、约束与术语

- `model` 是 exact、大小写敏感的逻辑等级 ID；禁止 alias 或跨等级 silent fallback。
- “无状态”指不持有 Agent conversation；不否定单次请求处理、内部队列、Usage/Audit 和服务配置。
- LLMTier 不理解 Agent/Run/Project/IR/STD/Matrix Session，不管理后端 KV identity。
- 偏离标准前必须记录已确认需求、标准不足、最小扩展及成本；未确认不增加协议。

## 4. 功能需求

| ID | 需求 | 优先级 | 验证 |
|---|---|---|---|
| LT-FUN-001 | shall 提供 OpenAI-compatible `POST /v1/responses`，接受固定 Pi 0.85.1 实际发送的 `stream=true`、`store=false`、easy message、assistant/function/reasoning历史、function result及所选reasoning字段；支持标准 SSE text/function/reasoning/refusal/terminal Usage，refusal最终content保持标准`type=refusal`；首阶段不增加未消费的JSON并行模式 | P0 | CT-DP-001 |
| LT-FUN-002 | shall 提供 `GET /v1/models` 与 exact-case detail，返回真实逻辑等级、能力、上下文/输出限制和 availability | P0 | CT-MODEL-001 |
| LT-FUN-003 | shall 提供标准 `POST /v1/embeddings` 字符串输入子集；首版`Embedding-v1`固定为本地`BAAI/bge-m3` dense、space `bge-m3-dense-1024-v1`、1024维、单项8192 tokens、batch 32和L2 normalization；支持与请求一致的float数组或RFC4648 little-endian float32 base64表示并验证有限值/维数；同一逻辑model只能绑定同一向量空间，非兼容模型/版本/预处理变更必须使用新逻辑model ID | P0 | CT-EMB-001 |
| LT-FUN-004 | shall 在模型响应保留标准token Usage结构，并提供统一只读token Usage查询；measured、estimated、unknown及原始字段存在性必须可区分 | P0 | CT-USAGE-001 |
| LT-FUN-005 | shall 通过 Admin API/英文 Web UI 在主页一屏展示全部逻辑Tier、模型映射和状态；每个固定Tier可编辑成员，新增成员只能选择供应商管理页已有Provider；Provider可独立添加、修改和在无引用时删除；并提供Usage、审计与脱敏运行日志 | P1 | CT-ADMIN-001/CT-UI-001/CT-LOG-001 |
| LT-FUN-006 | shall 提供无副作用 health/readiness；真实 provider probe、reload、restart 等潜在费用/状态变更操作必须要求 operator 授权 | P0 | CT-OPS-001 |
| LT-FUN-007 | shall 不保存/压缩 Agent 历史、不执行工具、不创建 Agent Session/Conversation、不管理或匹配 backend KV | P0 | CT-BOUNDARY-001 |
| LT-FUN-008 | function call 仅由模型输出；Piko 执行工具并在后续完整请求中提交结果 | P0 | CT-DP-001 |

## 5. 接口需求

| ID | 需求 |
|---|---|
| LT-INT-001 | Data Plane shall 使用 Bearer auth、JSON 和标准 OpenAI error shape；响应生成 `X-Request-ID` 仅作关联 |
| LT-INT-002 | V0.3 current paths 仅包括 `/v1/responses`、`/v1/embeddings`、`/v1/models`、`/v1/models/{model}`、`/tier/v1/usage`、`/healthz`、`/readyz` 及精简 Admin paths；日志仅通过只读`GET /tier/admin/v1/logs`提供 |
| LT-INT-003 | shall 不定义 SourceInstance、custom Idempotency-Key、Invocation、response recovery、Seat/claim/capacity snapshot、Cost 或 compatibility negotiation path/header/schema |
| LT-INT-004 | `/tier/v1/usage` 是唯一 consumer extension；原因是 OpenAI API 没有统一跨请求 token 查询。它不得承载任务、项目、会话、费用或执行状态 |
| LT-INT-005 | unknown token数不得填零；usage缺失不得把成功模型结果改为失败，但Piko必须能识别任务Usage unknown；UsageRecord数值字段在unknown时为null |
| LT-INT-006 | 首阶段固定`stream:true/store:false`并使用标准 Responses SSE；`stream:false`不在当前契约。不得增加自定义 streaming/recovery endpoint、JSON并行模式或legacy fallback |
| LT-INT-007 | 每个鉴权主体+server request ID最多一个逻辑UsageRecord；dispatch前持久unknown义务，更高record_version以不可变版本追加并替换旧事实而不累计；分页snapshot固定精确版本/view且每页复核权限，过期/冲突返回400，store不可用返回typed 503 |
| LT-INT-008 | Admin item更新/删除shall使用强ETag/If-Match；stale version返回412，引用冲突返回409；PATCH只修改出现字段 |

## 6. 性能与容量需求

| ID | 需求 |
|---|---|
| LT-PERF-001 | 首版内部guard shall按deployment限制并发1、按exact level FIFO排队最多32项/30秒；queue full/等待到期返回429，全部候选不可用返回503；连接/首字节和SSE空闲timeout分别为30/60秒 |
| LT-PERF-002 | 同一逻辑等级内可选择已配置 deployment；不得因容量不足跨等级替换 |
| LT-PERF-003 | 未测量前不得宣称 production latency、throughput 或 availability SLO |

容量、Seat、shared pool、quota composition 和 execution claim 是内部实现或历史候选，不是 Slinky/Piko 外部契约。

## 7. 安全、可靠性与合规需求

| ID | 需求 |
|---|---|
| LT-SEC-001 | Data Plane 和 Admin credential shall 分权；Provider Secret 只写/引用，不回显、不记录 |
| LT-SEC-002 | prompt/output 默认不进入普通日志、Usage 或 Audit；诊断使用脱敏 request ID/trace |
| LT-SEC-003 | production Web UI shall 由同源TLS反向代理完成operator SSO/MFA、短期HttpOnly会话、CSRF和Admin bearer注入；浏览器不得保存或读取bearer，且不得新增账号/访问控制页面或LLMTier登录API |
| LT-SEC-004 | operational log shall 在写入前脱敏且消息有长度上限；不得包含prompt、模型输出、reasoning正文、Embedding向量、Authorization、Secret或原始请求头 |
| LT-REL-001 | LLMTier shall 返回真实 HTTP/typed error；调用方按其任务策略重试，LLMTier不承诺跨系统 exactly-once |
| LT-REL-002 | 内部可靠性、provider retry 或防重不得创建对外 Invocation/recovery/session contract |
| LT-REL-003 | 未知 Usage、健康或 provider fact shall 显式 unknown/unavailable，不得伪造零或成功 |
| LT-REL-004 | 初始化后SQLite Operational Store shall 是唯一配置authority；settings文件只允许空库首次bootstrap，不得监听、双写或在重启时覆盖Admin变更 |

## 8. 运维、诊断与可观测性需求

| ID | 需求 |
|---|---|
| LT-OPS-001 | healthz shall 表示进程存活；readyz shall 表示配置和至少所需模型可接受请求；二者不触发 provider 计费调用 |
| LT-OPS-002 | provider probe 应显示可能费用/副作用并要求明确 operator 授权；结果进入 Audit |
| LT-OPS-003 | restart/reload/restore shall 使用 LLMTier 自有 runbook，不建立统一跨系统恢复状态机 |
| LT-OPS-004 | 恢复确认 shall 分层检查 process、config、model availability、Usage store，并仅在授权后运行 smoke request |
| LT-OPS-005 | 单节点基线 shall 由systemd管理loopback服务，优雅摘流最长60秒；QuerySnapshot TTL为15分钟，Usage/Audit分别保留30/90天；每日加密SQLite备份保留7日+4周，目标RPO 24小时、RTO 4小时，并在release前执行隔离restore rehearsal |
| LT-OPS-006 | 脱敏Operational Log保留7天并以稳定快照分页；存储不可读返回503，不得用空页表示无日志；日志查询只读且不得提供全量浏览器导出 |

## 9. 制造、部署、维护与退役需求

硬件制造不适用。部署需要固定 artifact/config、owner-only Secret、TLS/auth、service manager、resource limit、backup/restore 和 rollback。legacy `/call`、Role selector 和旧 custom contract 必须一次性退出 consumer authority，不作为 fallback；源码可在迁移期间保留但要标明非 current contract。

## 10. 验收与 traceability

验收至少包括：OpenAPI ref resolution；Responses/tool loop；Models exact ID；Embeddings model capability；Usage measured/estimated/unknown；Admin CRUD 与 Secret 不回显；health/probe 授权；旧 path/header/schema absence；runtime activation false。静态 PASS 不证明实现上线。

## 11. 未决问题与变更历史

| ID | Owner | 问题 | 最晚阶段 |
|---|---|---|---|
| LT-OPEN-02 | LLMTier | **设计已关闭，实施待证据**：`Embedding-v1`=`BAAI/bge-m3` dense、space `bge-m3-dense-1024-v1`、1024维、batch 32、单项8192 tokens；部署需固定权重/tokenizer/runtime digest | Embeddings activation 前 |
| LT-OPEN-03 | LLMTier | **设计已关闭，实施待证据**：单节点Linux、TLS反向代理operator SSO/MFA、systemd、加密SQLite备份与Operations runbook | runtime activation 前 |

2026-09-17：以主流标准接口替代旧复杂 candidate；删除 SourceInstance、外部容量/Seat、custom idempotency/Invocation recovery、Cost、compatibility negotiation 和跨系统 release 要求；保留 exact model、内部保护、token Usage、模型管理与运维。candidate.6在既有标准调用语义上增加主页全量状态视图与只读脱敏日志查询。2026-09-18按用户决定将整个Web UI可见文本统一为英文。
