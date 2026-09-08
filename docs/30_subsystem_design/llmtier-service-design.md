<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 单服务设计

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-service-design` |
| Document Version | `0.3.0` |
| Status | `Approved` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | LLMTier |
| Approver | LLMTier |
| Approval Date | `2026-09-07` |
| Created Date | `2026-09-06` |
| Last Modified Date | `2026-09-08` |
| STD Version | `0.1.0-draft.18` |
| Template ID | `design.definition` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/30_subsystem_design/llmtier-service-design.md` |
| Supersedes | `docs/99_reference/design/llmtier-v0.3-design-review.md` |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本文按 STD 的“单应用、单服务或单库”软件项目模型，将 LLMTier 定义为一个独立部署的
> 模型服务；`design_level=subsystem` 表示它在 Slinky/Piko/LLMTier 协作链路中的层级，不表示
> 本仓库拥有该跨项目系统。迁移来源为 `docs/99_reference/design/llmtier-v0.3-design-review.md`。本次只修正
> 文档分类与结构，不改变既有 authority、Scope B、接口 ID、评审结论或 activation gate。本文已通过
> Owner review 进入 Approved promotion candidate；原设计全部 current scope 已映射并标为 Superseded。

## 1. 目的、范围与上位输入

LLMTier 从 Slinky 的旧 embedded Tier 拆分为单一、独立部署的模型服务。V0.3 目标是提供可管理、
可观测、可由 Piko 调用的模型服务边界，同时不取得 Agent、Project、Plan 或 IR authority。

本服务的 V0.3 范围是：

1. Piko 通过唯一 `Runtime -> Piko -> LLMTier` 路径使用 Responses non-stream；
2. Memory/Knowledge Client 使用 Embeddings non-stream；
3. Slinky 只读、Client-scoped 地观察 readiness、Service Level、capacity、invocation 和 usage；
4. LLMTier 管理员通过 `/tier/admin/v1` 与最小 Admin Web UI 管理 Registry、Provider、capacity、
   Client/Source、审计和恢复；
5. 同一 authoritative Service Level Registry 驱动 Models、Observation、admission、capacity
   membership 和 Compatibility Manifest；
6. idempotency、lost response、UnknownOutcome 和 M2-C retention 有可执行契约；
7. production gate 全部关闭前，manifest 的 runtime activation 保持 false。

上位输入包括 Slinky 冻结的跨项目 Scope B 与消费需求、Piko 的 pinned SDK/adapter capture 约束、
既有 Matrix Review ID，以及本仓库的 V0.3 OpenAPI、manifest、fixtures 和原始设计。外部输入不会
转移 LLMTier 对本服务设计、管理、安全、部署和实现事实的 authority。

## 2. Ownership 与边界

| 参与方 | 权威职责 | 禁止越界 |
|---|---|---|
| Slinky | Project、Plan、IR、Forecast/Risk/Action；读取 Observation 并投影 Seat | 不持有 Provider credential，不做最终 admission，不直接执行 IR-backed inference |
| Piko | Agent Runtime；执行 assigned exact `service_level_id`；SDK/recovery adapter | 不理解 Provider/account/pool/Capacity Group，不调用 Management/Observation |
| LLMTier | 本单服务的模型服务、admission/routing、Invocation ledger、Registry、Management、Client-scoped Observation | 不执行 Agent Tool Loop，不组合 Plan/IR，不持有 Knowledge/Artifact/Acceptance authority |
| Admin | 配置 Provider、Registry、Client/Source、capacity、recovery | 不获得 Piko/Slinky 业务 authority，不读取 Secret |
| Memory/Knowledge Client | 调用 Embeddings non-stream | 不形成 Piko Agent Runtime 的旁路 generation path |

- 负责：Data Plane、Observation、Management/Admin UI、Registry、admission、routing、capacity、
  Invocation/idempotency ledger、usage、audit 与 recovery。
- 不负责：Slinky 的 Project/Plan/IR 与 Piko 的 Agent Runtime/tool loop。
- authority：LLMTier 是本仓库设计、契约实现和服务事实的唯一 owner；外部 reviewer 只对其拥有的
  消费边界、互操作契约和冻结范围作出结论。
- 上级设计与需求：跨项目协作边界和 Scope B 是本服务的约束输入，不是由本仓库维护的 system design。

## 3. Current Baseline 与 Approved Delta

### 3.1 Current Baseline

仓库当前保留从 Slinky 复制的 Python Tier 基线，可复用服务生命周期、路由、并发、配额、统计和
Provider adapter。它尚未证明 V0.3 Data Plane、Management、Observation、Registry、durable ledger
或 Admin UI 已生产接线。旧私有 Tier API、Role routing、Agent backend、mlexp、CLI runner 和
fallback 语义不是新服务的兼容承诺。

### 3.2 Approved Delta

当前 V0.3 Contract、OpenAPI、fixtures 和 manifest 表达已批准的设计增量：

- exact、大小写敏感的 Service Level ID，例如 `Worker`、`Junior`；禁止 lowercase 转换、alias、
  Role selector 与跨 Service Level fallback；
- V0.3 Scope B 仅含 Responses non-stream、Embeddings non-stream、Models list/detail、Invocation GET
  和 Response GET；Chat Completions 与 SSE/streaming 属于 V0.4；
- Management prefix 唯一为 `/tier/admin/v1`；canonical headers 是
  `X-Tier-Client-Request-ID` 与 `X-Tier-Invocation-ID`；
- 唯一容量单位为 `concurrent_invocation`，所有 direct/shared/overlapping group、quota、readiness、
  `valid_until` 约束必须同时满足；
- M2-C 固定为 `W=168h`、`M=24h`、产品自动恢复 deadline `D=24h`；
- V0.3 的唯一机器接口 authority 是 OpenAPI 3.1；v0.1/v0.2 仅作 provenance。

### 3.3 Future / Unapproved

production persistence/HA/backup/RPO/RTO、Admin UI 技术栈、Provider measured SLO、V0.4 Chat/SSE
和 streaming recovery 都是 Open Gate。不得因本文迁移而把它们提升为 Implemented、Verified 或 active。

## 4. 设计概览与主流程

```text
Admin -> /tier/admin/v1 + Admin Web UI
          -> inventory / secret-write / probe / registry publish / entitlement
          -> authoritative Service Level Registry
             |-> /v1/models
             |-> /tier/v1/service-levels
             |-> admission + capacity membership
             `-> compatibility manifest

Piko -> /v1/responses non-stream | /v1/models | recovery GET
Memory/Knowledge Client -> /v1/embeddings non-stream
          -> auth + canonical Client/Source
          -> validation + durable idempotency/Invocation ledger
          -> exact Service Level admission -> backend routing
          -> canonical result + usage/recovery

Slinky -> /tier/v1 readiness | service-levels | capacity | invocations | usage | compatibility
          -> version/ETag/valid_until validation
          -> all-constraints committed Seat projection
```

策略是单一事实来源、分面但不复制状态机、先持久化再 dispatch、fail closed、有限恢复保证与
契约先行。Data Plane、Observation、Management 使用不同权限和 DTO，但共享 Registry/ledger；
不得建立第二 Registry、第二 inference path 或第二 recovery state machine。

## 5. 内部分解与依赖

| 构件 | 职责 | 允许依赖 | 禁止项 |
|---|---|---|---|
| Data Plane | Responses、Embeddings、Models、recovery GET 与 strict validation | Identity、Registry、Ledger、Admission、Router | Role/IR selector、Chat/SSE V0.3、Provider passthrough |
| Identity/Entitlement | credential→client、canonical source 授权与 quota | 管理配置 | `source_instance_id` 作为恢复 namespace |
| Service Level Registry | catalog/version/ETag/compatibility/capacity membership | 管理发布 | alias、非 exact-case ID |
| Admission/Capacity | 联合校验 Service Level、groups、quota、readiness、有效期 | Registry、Entitlement | unknown quota 当作零或可用 |
| Invocation Ledger | idempotency、dispatch intent、状态、canonical response、tombstone、usage | durable store | UnknownOutcome 自动重派、第二 ledger |
| Backend Router | 同一 Service Level 内选择 Provider/Account/Pool/Deployment | Registry、Admission | 跨等级 fallback、Client provider-direct |
| Observation | readiness、catalog、capacity、invocation、usage、compatibility | Registry、Ledger | 跨 Client 数据或 physical credential 泄露 |
| Management API/UI | inventory、Secret、probe、publish、capacity、audit、recovery | 全部管理资源 | 未鉴权 mutation、Secret 回显 |

依赖方向由入口分面指向共享的 Registry/Ledger/Admission，再指向 Backend connectors；共享核心不反向
依赖 Piko 或 Slinky 的业务模型。

## 6. 接口与契约

| 分面 | Provided interface | Authority |
|---|---|---|
| Data Plane | `POST /v1/responses`、`POST /v1/embeddings`、Models list/detail、Invocation/Response GET | `interfaces/openapi/llmtier-v0.3.openapi.json` |
| Observation | `/tier/v1` readiness、service-levels、capacity、invocations、usage、compatibility | 同一 V0.3 OpenAPI；说明见 Slinky contract |
| Management | `/tier/admin/v1` 与最小 Admin Web UI | 同一 V0.3 OpenAPI；说明见 Management contract |
| Compatibility | overall/per-capability candidate 与 activation | `interfaces/compatibility/compatibility-manifest-v0.3.json` |

说明文档为 `docs/99_reference/contracts/piko-data-plane-contract-v0.3.md`、
`docs/99_reference/contracts/slinky-capacity-observation-contract-v0.3.md` 和
`docs/99_reference/contracts/llmtier-management-contract-v0.3.md`；正负样例在 `interfaces/vectors/v0.3/`。
Markdown 负责范围、rationale 与 authority；OpenAPI/manifest/fixtures 负责字段级机器契约。发生冲突
必须通过 review 修正，Consumer 不得自选解释。

Registry provenance 一致不要求不同 DTO 的 ETag 字面相同。Models、Observation、admission、manifest
必须引用同一 exact ID/catalog version 与兼容语义；各 endpoint 的 ETag 各自校验本 resource
representation。live capacity/usage 变化不要求 Models 或 Registry ETag 同步变化。

## 7. 数据、状态与生命周期

核心实体为 Client、Source、SourceInstance、Entitlement、ServiceLevel、Pool、CapacityGroup、Provider、
Account、Deployment、Invocation、CanonicalResponse、Usage、RecoveryItem 与 AdminJob。

Invocation active 状态仅为 Pending、Queued、Running；terminal 为 Succeeded、Failed、Cancelled、
UnknownOutcome。`InvocationAccepted` 不得包含 UnknownOutcome。成功 create、Succeeded replay 与 Response
GET 使用同一 canonical `ResponsesResponse` body；Failed、Cancelled、UnknownOutcome 使用冻结的 typed
non-2xx envelope。

namespace 至少覆盖 authenticated client、canonical source、endpoint/version 与 `Idempotency-Key`；digest
覆盖 exact Service Level、规范化 body 和影响语义的 headers。同 namespace/key 不同 digest 是不可重试
conflict。Backend dispatch 前必须持久化 request digest、Invocation reference、dispatch intent 和
recovery obligation。

active record 保留到 terminal；terminal 后 content-free digest/tombstone 与 Invocation terminal view
至少保留 168h，canonical Response 在冻结的
168h recovery window 内仍可恢复。原始 prompt/output 副本可有独立 privacy retention，但配置必须
同时满足这两个冻结下限；短于任一下限的配置无效并阻断 activation，且不允许运行时降级。

## 8. 控制流、并发与时序

### 8.1 首次 Responses 调用

1. Piko 使用 credential、canonical Source headers、`Idempotency-Key`、
   `X-Tier-Client-Request-ID` 与 exact `model=service_level_id` 发起 non-stream POST；
2. LLMTier 认证 client、授权 source、规范化请求并计算 digest；
3. 在 Backend 调用前事务性持久化 record、Invocation 与 dispatch intent；
4. admission 同时检查 Registry、entitlement、direct committed capacity、全部 overlapping groups、
   quota、readiness 与有效期；
5. Router 只在同一 Service Level 内选择 Backend 并完成一次 dispatch；
6. terminal 成功写入 canonical Response/usage，返回标准 `200 ResponsesResponse`。

### 8.2 replay 状态

| Invocation 状态 | 同一 POST replay | 后续动作 |
|---|---|---|
| Pending/Queued/Running | `202 InvocationAccepted` + `Location` + `X-Tier-Invocation-ID` + `Retry-After` | 按 Invocation GET readiness 等待 |
| Succeeded | 原 endpoint canonical `200` body | 零次 dispatch；必要时 Response GET |
| Failed | `502 invocation_failed` | `retryable=false`，不得重派 |
| Cancelled | `409 invocation_cancelled` | `retryable=false`，不得重派 |
| UnknownOutcome | `503 invocation_outcome_unknown` | manual reconcile；不得重派 |

### 8.3 Capacity Snapshot 失效

Snapshot 失效后，`TierServiceSeat`/`IRBackingSeat` 立即 Invalidated，禁止新 dispatch；Slinky 通知 Plan
更新 Forecast/Risk/Action。已经 LLMTier admission 的 in-flight Invocation 不撤销、不跨 Stage rollback，
当前 Attempt 只在该 Invocation 安全边界内收敛；后续 Work 必须重新获取 snapshot、投影并 admission。

启动验证配置来源、Registry/manifest 版本、ledger readiness、required Service Level 与 Observation
readiness。优雅关闭停止新 admission，并允许 in-flight Invocation 受控收敛；非优雅退出依赖 durable
intent/ledger 恢复，不默认重新 dispatch。Registry publish 以 version、ETag、`effective_at`、
`valid_until` 原子生效；破坏兼容性的变化使用新 ID/API major。

## 9. 失败、恢复与可观测性

lost response 保留两条由同一 idempotency contract 定义的分支：

1. 已获得 Invocation ID 时，查询 `GET /v1/invocations/{id}`，只按 `recovery_ready`、
   `retry_after_ms` 与 `recovery_disposition=wait|retrieve_response|raise_terminal_error|manual_reconcile`
   判定；
2. 响应头也丢失、没有 Invocation ID 时，在 `D=24h` 内以原 authenticated client、canonical source、
   request body、digest、`Idempotency-Key` 和 `X-Tier-Client-Request-ID` 重放同一
   `POST /v1/responses`，取得首次、active、Succeeded 或 terminal outcome/recovery reference。

第二条是 transport recovery，不是新查询入口、新 recovery path、新 Attempt、换 endpoint、换 key 或
Backend 重新 dispatch 授权。若既存 record 已建立，additional dispatch 为零；UnknownOutcome 仍不得
盲重派。SDK 固定 `maxRetries:0`，由 Piko durable obligation 层执行恢复。

错误采用机器可判定的 typed envelope；unsupported surface、权限不匹配、hidden model、quota unknown
均 fail closed。Readiness 暴露 Ready/Degraded/NotReady、实例/版本、Observation readiness、visible
Service Levels、snapshot version 与 next refresh；Usage 支持按 Source/Instance/Service Level/endpoint/
status 分组，unknown/partial 不折算为零。日志、metrics、audit 不得泄露 Secret 或跨 Client 内容。

## 10. 资源、容量、性能与限制

`concurrent_invocation` 是唯一 Seat 单位。committed capacity、全部 shared/overlapping Capacity Group、
Client quota、readiness 与 `valid_until` 必须同时满足。burst 不计入 committed Seat；
`request_quota_remaining=null` 阻断新增 committed Seat。

Semantic validator 检查 ID 唯一、exact-case membership、双向 group membership、
`available <= committed`、时间顺序、unknown quota 和 blocking reason。Schema validation 不能替代
运行时语义验证；multi-client/source isolation 与公平性需要 production evidence。

当前没有 throughput/latency 的 production measured baseline。性能目标必须在 Provider/Deployment 与
Service Level SLO 冻结后补齐，开发环境或 mock capture 不得写成实测。逻辑部署至少包含 API process、
Admin Web UI、durable Registry/ledger/result store、Provider/Local Deployment connectors 与 observability
backend；数据库、HA、RPO/RTO 和故障域仍是 Open Gate。

## 11. 安全与隔离

- Authorization 绑定 canonical `client_id`；`X-Tier-Source-ID` 是该 client 下获授权的 canonical
  `source_id`。
- Data Plane recovery namespace 固定为 authenticated client + canonical source；Observation 的
  source filter 只是授权范围内查询维度，不创建鉴权或恢复 namespace。
- `X-Tier-Source-Instance-ID` 仅用于 observation、correlation、audit。
- `Idempotency-Key` 是逻辑 Invocation 的 durable identity；`X-Tier-Client-Request-ID` 只是 correlation。
- 禁止跨 Client 和未授权 Source；同 Client 已授权多 Source 的 Observation/Management 聚合按各自
  授权和过滤契约执行。
- Secret create/rotate 只写不读；list/detail/UI/log/audit 不返回明文或可逆值。
- Management mutation 必须认证、授权、审计并执行 concurrency check；三分面 credential、policy 与
  DTO 分离。

## 12. 实现映射与变更范围

LLMTier 是单服务软件仓库，采用 STD 单应用/单服务布局：

| 位置 | 作用 |
|---|---|
| `src/` | 单服务 Python 当前实现基线 |
| `tests/` | 单元、contract semantic 与迁移一致性测试 |
| `docs/` | 设计、接口、QA、迁移和 provenance |
| `docs/30_subsystem_design/` | `design.definition` 的 canonical service/subsystem design |
| `docs/00_management/` | tailoring 与 adoption 管理文档 |
| `docs/98_migration/` | 迁移 inventory 与映射证据 |
| `docs/std-source-manifest.json` | 锁定 STD draft.18 的 71 个来源 artifact；不是项目 RAG ingestion |
| `rag/` | legacy draft.12 STD source list；本轮不修改、不执行项目文档 ingestion |

本次不新建 `software/llmtier/`、`services/llmtier/` 或多应用 workspace，因为仓库当前只有一个服务
ownership 和一个部署边界。未来若出现两个以上可独立部署、独立发布、独立 owner 的产品单元，必须
重新 tailoring 并经用户批准，不能提前铺设目录或并行实现路径。

允许的实现变更仅限扩展本服务现有机制以满足批准契约；不得未经批准引入新 config path、selector、
fallback、兼容 alias、第二 inference/recovery path 或新旧并行 implementation。具体 production
deploy/config/schema/migration/ops 文件在实现需要与 ADR/评审关闭后添加。

## 13. Verification、测试义务与证据

| Requirement | Design element | Verification method | Evidence | Status |
|---|---|---|---|---|
| LT-QR-001：同 key/digest 零重复 dispatch | §7-9 Ledger/recovery | active/terminal/lost-response fixture + crash test | v0.3 recovery fixtures；production crash evidence 待补 | Candidate |
| LT-QR-002：UnknownOutcome 不盲重派 | §8-9 | typed terminal Contract Test | OpenAPI + semantic tests | Candidate |
| LT-QR-003：Seat invalidation | §8.3 | capacity semantic + Slinky projection test | v0.3 capacity fixtures | Candidate |
| LT-QR-004：Registry 一致性 | §5-6 | exact ID/catalog ref；各资源 ETag/304 test | OpenAPI/manifest tests | Candidate |
| LT-QR-005：Client/Source 隔离 | §11 | 多 Source 正例、未授权 Source/跨 Client 负例 | authorization fixtures；production evidence 待补 | Candidate |
| LT-QR-006：Secret 只写不读 | §11 | Management API/UI/log/audit negative tests | machine contract 已定义；实现证据待补 | Open Gate |
| LT-QR-007：M2-C retention | §7、§9 | 24h recovery + terminal 后 168h retention/fault test | policy frozen；长时运行证据待补 | Open Gate |
| LT-QR-008：unsupported surface | §3、§6 | Chat/SSE/stream request negative tests | fail-closed fixtures | Candidate |
| LT-QR-009：管理与观察一致性 | §5-6、§9 | pagination、aggregate、ETag、unknown/partial tests | OpenAPI semantic tests；UI evidence 待补 | Candidate |
| STD-LT-001：单服务分类 | §1、§12 | metadata/path/tailoring/inventory consistency test | `tests/test_std_migration.py` | Candidate |

`docs/99_reference/verification/llm-tier-contract-qa-v0.3.md` 和 tests 只证明文档、Schema、fixture 的静态一致性，不证明
production implementation、runtime activation 或 SLO。Review→Contract→fixture/test→execution evidence
必须保留原 Review ID。

## 14. Review Checklist、未决项与 Gate

### 14.1 已保留的冻结决定

| Decision | 状态 | 来源 |
|---|---|---|
| Authority 分离与唯一 inference path | Candidate accepted by Slinky | `S-20260906-59891d73fa13` |
| M2-C：`W=168h`、`M=24h`、`D=24h` | Candidate frozen | `L-20260906-12940a96e148`、`P-20260906-c14b4af35ac3` |
| Scope B：V0.3 non-stream；Chat/SSE 延至 V0.4 | Authoritative scope decision | `S-20260906-2f9539048493` |
| Amendment 4 design/contract candidate | Slinky ACCEPTED | `S-20260906-1e12f5e61d73` |
| STD 分类修正为单服务 `design.definition` | 本轮 review candidate | 用户 2026-09-07 指示 |

### 14.2 Activation gates

1. production implementation commit 与完整正负 Contract Test；
2. Management API/UI 权限、并发、Secret non-disclosure；
3. Registry 多分面一致性与 Capacity semantic validator 生产接线；
4. multi-client/source isolation、entitlement、公平性；
5. Piko pinned SDK/adapter capture 与 Memory/Knowledge Embeddings Consumer Contract Test；
6. M2-C retention、privacy policy 和 crash/lost-response 零重复 dispatch；
7. legacy/parallel/direct path 删除扫描；
8. 文档、机器契约、fixtures、manifest 与 route 行为一致。

### 14.3 Open items

- 项目授权 reviewer 对 immutable LLMTier candidate commit 的终局 Migration Review；
- Piko 对 V0.3 machine-contract bundle 的最终结论；
- production persistence/HA/backup/RPO/RTO 选型及 ADR；
- Provider/Deployment measured SLO 与公平性验证环境；
- Admin Web UI 技术栈、部署和端到端证据；
- canonical promotion、项目 RAG publication 与 runtime activation 的独立后置决定；
- V0.4 Chat Completions、Responses/Chat SSE 和 streaming recovery 的独立设计。

### 14.4 Review checklist

- [x] `design.definition`、`design_level=subsystem` 与单服务 repo layout 一致；
- [x] Current Baseline、Approved Delta、Future/Open Gate 分离；
- [x] authority、接口、状态、recovery、capacity、安全、verification 与 traceability 未裁掉；
- [x] 原始设计保留，未伪造 production implementation 或 activation；
- [x] STD draft.16 与本项目迁移结构已获 READY 协调共识；draft.17/draft.18 只升级 validator discovery/read/source robustness，未改变本文业务内容；
- [ ] LLMTier owner 批准 canonical 替换；
- [ ] production activation gates 全部关闭。
