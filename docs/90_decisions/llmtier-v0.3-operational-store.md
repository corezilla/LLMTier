<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Operational Store 边界

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-v0.3-operational-store` |
| Document Version | `0.2.0-draft.2` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-16` |
| Last Modified Date | `2026-09-17` |
| Template ID | `decisions.adr` |
| Template Version | `0.1.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/90_decisions/llmtier-v0.3-operational-store.md` |
| Supersedes | `0.1.0-draft.2` |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

- Status: proposed
- Date: `2026-09-17`
- Decision owners: LLMTier
- Supersedes: `0.1.0-draft.2`

## Context

LLMTier V0.3 已收缩为无 Agent 会话状态的 OpenAI-compatible 模型网关。外部调用方提交每次调用所需的完整输入；LLMTier 不保存 Agent Session/Conversation，不执行工具，不压缩上下文，也不管理或匹配后端 KV cache。

因此，旧版 ADR 围绕跨系统 Invocation、Seat、RecoveryObligation、M2-C 与 CostEvidence 构建的事务模型不再是当前外部契约依据。本 ADR 只决定单服务内部配置、Token Usage 和审计事实的存储边界，不建立自定义调用恢复协议。

## Decision Drivers

1. 云端 Provider、本地部署与逻辑等级映射需要一个可审计的配置事实来源；
2. Token Usage 需要保留来源、统计范围和 measured/estimated/unknown 质量；
3. Provider Secret 不得进入普通查询、日志或 UI 回显；
4. 单服务 V0.3 不应为了未确认的多实例需求引入外部数据库或事件平台；
5. 标准模型调用的请求正文和 Agent 历史不应复制到管理存储。

## Considered Options

| 选项 | 优点 | 主要问题 | 结论 |
|---|---|---|---|
| A. 单一 SQLite Operational Store | 复用现有 Python/SQLite；配置、Usage 与审计可事务提交 | 当前仅适合单节点 writer | V0.3 采用 |
| B. 立即引入外部事务数据库 | 支持多实例与 HA | 没有已批准需求，增加部署和运维复杂度 | 不采用 |
| C. JSON、日志和多个数据库并列为权威 | 改动小 | 版本、审计和 Usage 会漂移 | 拒绝 |

## Decision

### 1. 存储内容

Operational Store 保存：

- 云 Provider、本地模型部署和 exact `service_level_id` 映射的版本化配置；
- Provider 健康探测的非敏感结果与最后更新时间；
- Token Usage 记录及其 `measured|estimated|unknown` 质量、统计范围和关联 ID；
- 管理变更、探测、启动/重启/恢复操作的审计事实；
- Schema 与配置版本。

它不保存或承担：

- Agent Session、Conversation、历史、压缩摘要或工具循环；
- 项目、IR、STD、Matrix Session/Topic；
- 后端 KV cache identity；
- 跨系统 SourceInstance、Seat、execution claim 或 Session close/drain/release；
- 自定义 Idempotency/Invocation/结果恢复 ledger；
- 外部 Cost、币种或计价版本。

### 2. 单节点事务边界

V0.3 使用 `LLMTIER_STATE_DIR` 下的 SQLite 数据库，启用 WAL、foreign keys 和显式 schema version。空库可从一个经过校验的settings文件一次性bootstrap；bootstrap提交成功后SQLite成为唯一运行配置authority，后续启动不得自动重导、覆盖或双写JSON。配置变更、Usage 写入和审计记录分别在单库事务内提交。数据库提交不与 Provider HTTP 调用构成分布式事务，也不对外承诺 exactly-once。

Provider Secret 明文不进入数据库；只保存受控 Secret reference、版本和非敏感 metadata。对 Secret 的新增或替换是只写操作，查询和 UI 仅显示是否配置以及引用版本。

### 3. Usage 与请求关联

Usage 只保存标准响应或 Provider 可验证事实中的 token 计数：`input_tokens`、`output_tokens`、`total_tokens` 和可获得的 cached/cache-write/reasoning tokens。关联使用认证principal与服务端request ID；不引入 SourceInstance、Agent Session 或业务项目字段。每个request至多有一个逻辑记录，迟到事实以单调`record_version`替换旧版本而不累计；内部provider attempts的实际总量先归并到该request事实。未知值保持null并标记unknown，不写成零；存储不可用不得以空查询结果掩盖。

### 4. 健康、恢复与授权

健康检查可读且无副作用。启动、重启、配置发布、凭据变更、主动探测以及可能产生费用或改变状态的恢复动作只能由获授权 Operator 发起，并写审计。LLMTier 的环境恢复不创建跨系统恢复状态机，也不宣称 Piko 任务已成功。

### 5. 备份与迁移

备份必须形成 SQLite 一致性快照并记录 schema/config version 与 hash。恢复只在服务停止写入、目标存储隔离且 Operator 明确授权时执行；恢复后必须完成 integrity、schema、配置引用和健康检查。RPO/RTO、加密和演练仍是生产实现 Gate，不在本设计候选中伪造完成。

## Consequences

- 外部接口回到主流无状态模型调用边界，内部存储不再驱动跨系统调用恢复。
- 管理配置、Token Usage 与审计保持可追溯；Secret 和模型内容不进入普通存储。
- 多实例/HA 若成为明确需求，必须另立 ADR 评估共享事务数据库。
- runtime activation 继续为 false；本 ADR 是设计决定，不是实现或运行证据。

## Verification and Evidence

1. Schema migration 与事务失败不会产生半发布配置；
2. Secret 不出现在查询、日志、UI、备份清单或测试 fixture；
3. measured/estimated/unknown Usage 正负例通过，unknown 不填零；
4. Agent Session、SourceInstance、Seat、Invocation recovery、Cost 等退出概念不出现在当前数据库 Schema；
5. 健康检查无副作用；状态变更操作要求 Operator 授权并有审计；
6. backup/restore 的 integrity 与 schema 校验在实现阶段提供证据。

## Rollback / Revisit Conditions

出现多实例写入、HA、共享存储、监管保留或单节点 SQLite 无法满足已批准 SLO 时重开本 ADR。不得以隐藏 fallback、第二数据库 authority 或恢复旧跨系统协议规避评审。

## Traceability

- System design：`docs/20_system_design/llmtier-system-design.md`；
- Requirements：`LT-FUN-001..004`、`LT-OPS-001..003`；
- Machine authority：`interfaces/openapi/llmtier-v0.3.openapi.json`、`interfaces/compatibility/compatibility-manifest-v0.3.json`；
- Verification：`docs/70_verification/plans/llmtier-v0.3-vv-plan.md`；
- Tailoring：`docs/00_management/std-tailoring.md`。
