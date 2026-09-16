<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Operational Store 与事务边界

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-v0.3-operational-store` |
| Document Version | `0.1.0-draft.2` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-16` |
| Last Modified Date | `2026-09-16` |
| Template ID | `decisions.adr` |
| Template Version | `0.1.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/90_decisions/llmtier-v0.3-operational-store.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

- Status: proposed
- Date: `2026-09-16`
- Decision owners: LLMTier
- Supersedes: none

## Context

LLMTier V0.3 要求在首次 backend dispatch 前持久化同一 logical invocation 的幂等决定、Seat、
Invocation、DispatchIntent 和 RecoveryObligation，并在结果返回调用方前原子提交 terminal fact、
canonical response、usage、Seat release evidence 和 audit。任何部分写入、跨文件重命名或进程重启都不能
产生第二个 Invocation、重复 dispatch、提前释放 Seat，或把 UnknownOutcome 误写为已停止。

当前实现是单 Python 服务进程，已有 `LLMTIER_STATE_DIR`、SQLite/WAL 统计库和 JSON quota state，
但这些现状不提供 V0.3 所需的跨记录事务。V0.3 尚未批准多实例、HA、共享文件系统或外部数据库；
M2-C 要求 active obligation 保留至可证明 resolved terminal，terminal view、canonical result 和
content-free digest/tombstone 从 resolved terminal 起至少保留 168 小时。生产 TLS、at-rest encryption、
backup/RPO/RTO 和容量实测仍是独立 activation gate。

本 ADR 只决定 V0.3 单节点 Operational Store 与事务边界。它不决定 Provider 选择、跨 Service Level
routing、Piko task 状态，也不把逻辑构件拆成独立 subsystem 或服务。

## Decision Drivers

1. admission 成功必须把 Seat、Invocation、dispatch intent 和 recovery obligation 作为一个原子事实提交；
2. backend 调用是不可纳入本地数据库事务的外部副作用，必须用 durable intent 和单调状态隔离；
3. 同一 Client/Source/endpoint/key/digest 在并发、重启和丢响应下最多绑定一个 Invocation；
4. Observation、Management 和 Data Plane 必须读取同一 Registry/Ledger authority；
5. active/Unknown/Held obligation 不得因超时、清理或 Slinky/Piko 生命周期而被删除或释放；
6. 选择应复用现有单服务/state-root 机制，并允许以后在显式 ADR 下迁移到多实例事务数据库；
7. 存储不可用、事务不可提交或 schema 不兼容时必须停止新 admission 和 dispatch。

## Considered Options

| 选项 | 优点 | 主要问题 | 结论 |
|---|---|---|---|
| A. 单一 SQLite Operational Store，WAL + FULL durability | 复用 Python/现有 SQLite 基线；单文件事务覆盖 admission、ledger、capacity、usage、audit、job；部署最小 | 仅适合单节点 writer；需要控制大 response、WAL、backup 和写争用 | 推荐用于 V0.3 单节点基线 |
| B. 立即使用 PostgreSQL 等外部事务数据库 | 支持多实例、行锁和成熟 HA | 当前 topology/Operator/RPO/RTO 未定；引入新部署依赖而没有已批准多实例需求 | V0.3 不选；满足重开条件时评估 |
| C. SQLite、quota JSON、response 文件和 audit 文件并行作为 authority | 改动当前代码较少 | 无法跨介质原子提交；崩溃后会出现 Seat、Invocation、result 和 audit 分裂 | 拒绝 |
| D. 自研 append-only event log | 可保留完整事件历史 | 需要自研 commit、索引、compaction、恢复和一致性协议，风险高且无现成证据 | 拒绝 |

## Decision

### 1. V0.3 存储形态

采用一个由 LLMTier 独占的 SQLite Operational Store，位于既有 `LLMTIER_STATE_DIR` 下的固定
`operational/llmtier.sqlite3`。V0.3 只允许一个服务实例打开该 store 进行 admission/dispatch；不得放在
NFS/共享文件系统上，也不得由多个进程以“共享单文件”方式实现 HA。数据库启用：

- `journal_mode=WAL`；
- `synchronous=FULL`，用于所有会授权 dispatch、改变 Seat/terminal/release、写 management configuration
  或 recovery action 的事务；
- `foreign_keys=ON`、有限 `busy_timeout` 和显式 schema version；
- 写事务使用 repository transaction coordinator 和 `BEGIN IMMEDIATE`，避免各模块自行提交；
- 连接、transaction 和 migration 失败进入 store NotReady，禁止新 admission/dispatch。

`NORMAL` durability 只允许派生缓存或可重建统计，不能用于上述 authoritative transaction。

### 2. 单一 authority 与数据归属

以下 V0.3 authoritative facts 必须位于同一 Operational Store，并通过同一 repository layer 访问：

- authenticated Client/Source projection、Entitlement 和有效 Registry snapshot；
- IdempotencyDecisionRecord、Invocation、DispatchIntent、RecoveryObligation；
- direct/group Capacity fact、Seat grant/hold/release、quota decision；
- canonical Response/Embedding result、terminal error、digest/tombstone 和 retention boundary；
- Usage/CostEvidence、AuditEvent、RecoveryItem 和 AdminJob；
- Management mutation 的版本、ETag source version 和发布状态。

Provider Secret 明文不进入 SQLite；store 只保存受控 secret reference、版本和非敏感 metadata。
Secret material 沿用 `config/secrets/` 的受控入口，生产 at-rest encryption 与 backup key 管理未关闭前
不得激活。OpenAPI、schema、compatibility manifest 等受控发布 artifact 仍在 `interfaces/`；启动时验证后，
把实际生效版本作为 immutable Registry/config snapshot 记录，而不是建立第二份可独立漂移的目录。

现有 `llm_stats.sqlite3` 和 `quota_state.json` 属于 legacy baseline。V0.3 激活前，权威 usage/quota 必须
一次性迁入 Operational Store；不得 dual-write 后让两个存储都声称 current authority。旧文件可在迁移
验证后只读保留或归档，但不能参与 V0.3 admission、Observation 或恢复决定。

### 3. 原子事务边界

| 事务 | 必须同一提交的事实 | 提交后允许的外部动作 |
|---|---|---|
| Rejection decision | namespace/key/digest、typed reason、decision version/expiry、deadline fact、audit | 返回 429/408/409；不授予 Seat、不 dispatch |
| Admission | decision CAS、所有 direct/group/quota 检查版本、Seat grant、Invocation、DispatchIntent=`Prepared`、RecoveryObligation、audit | 仅在 COMMIT 成功后由 dispatcher claim |
| Dispatch claim | DispatchIntent `Prepared→Dispatching` CAS、attempt token、started_at、record version | claim COMMIT 后最多执行一次 backend request |
| Terminal success | provider outcome、Invocation `Succeeded`、canonical result、usage/cost evidence、Seat release evidence、audit | COMMIT 后返回/恢复 200 |
| Terminal failure/cancel | terminal error、backend execution fact、合法 release evidence（若具备）、usage、audit | COMMIT 后返回 typed terminal；无停止证据则 Seat 仍 Held |
| Unknown/reconcile | UnknownOutcome/backend fact、Held/Released 证据、RecoveryItem/action、audit | 只允许授权 reconcile；`redispatch=false` |
| Management mutation | expected version/If-Match、new immutable version、secret ref、audit/job | COMMIT 后发布对应新 snapshot |

数据库 COMMIT 与 backend HTTP 调用之间不存在分布式原子性，因此规则是保守不重复：dispatcher 必须先
持久化唯一 `Dispatching` claim，再调用 backend。进程在 claim 后、确定 outcome 前崩溃时，恢复不得重放
backend request；该 Invocation 转入 UnknownOutcome/RecoveryRequired 并保持 Seat Held，直到取得
`backend_terminal`、`execution_stopped_ack` 或 `authorized_reconcile` 证据。`Failed`、`Cancelled`、本地
timeout 或“取消已受理”标签本身不是 release evidence。

### 4. 并发、时间与清理

- namespace/key 和 Invocation/Seat/dispatch token 使用数据库唯一约束；CAS 以 record version 和期望状态
  作为 WHERE 条件，影响行数不是 1 即失败并重读 authoritative record；
- 同一 rejection expiry 后的并发重评只有一个 admission transaction 可获胜；digest binding 不随 decision
  expiry 清除；request deadline 到达且无 Invocation 时 408 先于缓存 429；已有 Invocation 始终恢复原义务；
- UTC contract time 与 `deadline_exceeded_at` 持久化；进程内 monotonic clock 只用于等待预算，重启后依据
  persisted UTC、可信时钟状态和原 deadline 恢复，绝不推进 deadline；
- retention worker 只能删除已 resolved terminal 且保证窗口已结束、无 legal/recovery hold 的内容；清理
  与 tombstone 更新在同一事务完成。active、UnknownOutcome、Held 或未决 RecoveryItem 不按年龄删除；
- canonical result 在冻结 168h 下限内必须可恢复。任何更短的 content/privacy 配置在发布时无效并阻断
  readiness，而不是运行时悄悄降级。

### 5. Schema migration、backup 与 restore

Schema migration 在服务开放 admission 前、独占 store 时执行；每步记录 from/to version、artifact hash、
started/completed/failed fact。破坏现有 obligation、缩短 retention 或丢失 release evidence 的 downgrade
禁止执行。迁移失败保持 NotReady，不能回到会读取错误 schema 的旧 binary。

备份使用 SQLite online backup API 或等价一致性 snapshot，不能只复制主数据库文件而遗漏 WAL。备份结果
记录 schema/config/catalog version、coverage boundary、hash 和未决 obligation 数。Restore 只在服务停止
admission/dispatch且目标 store 隔离时进行，必须通过 `integrity_check`、foreign key、schema compatibility、
retention/obligation 和 artifact provenance 校验后才可重新 Ready。具体频率、RPO/RTO、加密和演练证据仍为
production gate，本 ADR 不伪造其数值。

## Consequences

收益：

- admission、Seat、Invocation、dispatch 和 recovery 具备一个可验证的事务边界；
- Data Plane、Observation 和 Management 读取同一事实来源；
- 利用现有 Python/SQLite 能力，V0.3 不增加数据库服务或第二配置路径；
- crash 后优先暴露 Unknown/Held，而不是重复调用或错误释放。

代价与风险：

- V0.3 被明确限制为单节点/单 writer；SQLite 写锁、WAL 增长、canonical response 大小和 168h 容量需要
  实测及运维门禁；
- 外部 backend 无法参与本地事务，claim 后失联会保守形成 UnknownOutcome，并可能长期占用 Seat；
- legacy stats/quota 必须迁移，不能长期 dual-write；
- production at-rest encryption、backup/RPO/RTO、磁盘耗尽策略和 restore 演练仍未关闭，故 runtime
  activation 继续为 false。

不可逆边界：一旦生产 store 含有未决 obligation，不能回滚到不理解当前 schema/状态的版本，也不能
通过删除数据库或旧 key 来“恢复服务”。

## Verification and Evidence

ADR 接受前需要文档/设计检查；实现阶段至少提供以下不可变 evidence：

1. 并发同 key/digest、同 key/异 digest、rejection expiry 重评的唯一性测试；
2. 在 admission transaction 各写点注入 crash，证明 COMMIT 前 backend call=0；
3. 在 dispatch claim 后、socket write/response/terminal commit 各点注入 crash，证明 additional dispatch=0，
   未知事实为 UnknownOutcome/Held；
4. terminal success、failure、cancel、Unknown/reconcile 的 Seat release 证据正负测试；
5. store busy/corrupt/full、migration failure、audit failure 时 NotReady/fail-closed 测试；
6. online backup + isolated restore + integrity/schema/retention 校验，以及 WAL 未遗漏测试；
7. active/Unknown/Held 不清理、resolved terminal 168h 下限和 tombstone 原子替换测试；
8. legacy `quota_state.json`/`llm_stats.sqlite3` 不再参与 V0.3 authority 的扫描和迁移测试；
9. 负载下 write latency、WAL/checkpoint、database size 和 disk headroom 测量。

上述测试通过前只能称设计候选或实现证据，不能称 production activation。

## Rollback / Revisit Conditions

以下任一条件出现时必须重开本 ADR，而不是在代码中增加隐藏 fallback：

- 需要两个及以上 LLMTier 实例同时 admission/dispatch，或明确 HA/failover；
- Operational Store 需要跨主机共享，或部署环境不能提供可靠本地持久磁盘与文件锁；
- 实测写争用、WAL/backup 窗口、database size 或 canonical result 体量不能满足冻结 SLO/retention；
- 批准的 RPO/RTO、加密、审计或监管要求无法由单节点 SQLite 达成；
- 需要把 content blob 移出数据库，且无法维持 result metadata/content 的原子可恢复边界；
- Provider 出现可验证的幂等 dispatch token，可安全改变 UnknownOutcome 的 reconcile 策略。

激活前回滚可恢复到备份并停留 NotReady；激活后只能迁移到能够完整承接现有 schema、obligation、
retention 和 audit 的版本/数据库。禁止以清空 state、生成新 key 或启用 legacy path 作为回滚。

## Traceability

- System design：`docs/20_system_design/llmtier-system-design.md` §6、§10、§13、§17、§18；
- Requirements：`LT-FUN-003`、`LT-FUN-006`、`LT-CAP-003`、`LT-CAP-004`、`LT-REL-001`、
  `LT-REL-003`、`LT-REL-004`、`LT-OPS-001`、`LT-OPS-003`；
- Machine authority：`interfaces/openapi/llmtier-v0.3.openapi.json`、
  `interfaces/compatibility/compatibility-manifest-v0.3.json`；
- Verification：`docs/70_verification/plans/llmtier-v0.3-vv-plan.md`、
  `docs/70_verification/specifications/llmtier-v0.3-contract-test-specification.md`；
- Tailoring：`docs/00_management/std-tailoring.md` LT-TL-002、LT-TL-010、LT-TL-016；
- Open risk：`LT-RISK-003`；本 ADR 只关闭 V0.3 persistence choice，HA/RPO/RTO 和 production evidence
  继续保持 Open Gate。
