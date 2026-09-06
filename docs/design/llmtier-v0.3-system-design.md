# LLMTier V0.3 系统设计（STD 迁移候选）

> STD template: `design.system` 0.1.0；迁移来源为
> `docs/design/llmtier-v0.3-design-review.md`。本文件是结构迁移候选，不改变既有 authority、
> Scope B、接口 ID、评审结论或 activation gate。

| 属性 | 值 |
|---|---|
| 文档 ID | `llmtier-v0.3-system-design` |
| 状态 | Review；不得解释为 accepted/released 或 runtime activation |
| 当前迁移基线 | `7607f55f249a2b63d2495566895fb598a5b4eaaa` |
| 项目 authority | LLMTier |
| 外部 reviewers | Slinky、Piko |
| 当前评审事实 | Slinky 已接受 `4ddfe73` 的 V0.3 design/contract candidate；Piko machine-contract review 尚待闭环 |
| 机器契约 authority | `docs/contracts/openapi/llmtier-v0.3.openapi.json` |

## 1. 引言与目标

LLMTier 从 Slinky 的旧 embedded Tier 拆分为独立模型服务。V0.3 的目标是形成一个可管理、
可观测、可由 Piko 调用的完整系统边界，同时不取得 Agent、Project、Plan 或 IR authority。

V0.3 成功标准：

1. Piko 通过唯一 `Runtime -> Piko -> LLMTier` 路径使用 Responses non-stream；
2. Memory/Knowledge Client 可使用 Embeddings non-stream；
3. Slinky 只读、Client-scoped 地观察 readiness、Service Level、capacity、invocation 和 usage；
4. LLMTier 管理员可通过 `/tier/admin/v1` 与最小 Admin Web UI 管理 Registry、Provider、
   capacity、Client/Source、审计和恢复；
5. 同一 authoritative Service Level Registry 驱动 Models、Observation、admission、capacity
   membership 和 Compatibility Manifest；
6. idempotency、lost response、UnknownOutcome 和 M2-C retention 有可执行契约与验证证据；
7. 所有 production gate 关闭前，manifest 的 runtime activation 保持 false。

Stakeholder：LLMTier 管理员与实现者、Piko Agent Runtime、Slinky Project/Plan/IR 管理、
Memory/Knowledge Client，以及负责 Contract Test 和上线批准的 reviewers。

## 2. 架构约束

### 2.1 已冻结约束

- `service_level_id` 是 exact、大小写敏感的 catalog ID；例如 `Worker` 与 `Junior`。禁止
  lowercase 转换、alias、Role selector 和跨 Service Level fallback。
- 唯一 IR-backed inference 路径是 `Runtime -> Piko -> LLMTier -> Provider/Local Deployment`。
- V0.3 Scope B 只包含 Responses non-stream、Embeddings non-stream、Models list/detail、
  Invocation GET 与 Response GET。Chat Completions 和所有 SSE/streaming contract 属于 V0.4。
- Management prefix 唯一为 `/tier/admin/v1`；canonical headers 使用
  `X-Tier-Client-Request-ID` 与 `X-Tier-Invocation-ID`，不保留 alias。
- 唯一容量单位是 `concurrent_invocation`；committed capacity、全部 shared/overlapping
  Capacity Group、Client quota、readiness 和 `valid_until` 必须同时满足。
- Secret 只写不读。Provider credential、physical routing 和内部 error evidence 不进入
  Piko/Slinky DTO。
- V0.3 唯一机器接口 authority 是 OpenAPI 3.1 文件；历史 v0.1/v0.2 文档只作 provenance。

### 2.2 当前实现基线与批准增量

当前仓库保留从 Slinky 复制的 Python Tier 基线，可复用服务生命周期、路由、并发、配额、
统计和 Provider adapter；它尚未证明 V0.3 Data Plane、Management、Observation、Registry、
durable ledger 或 Admin UI 已生产接线。旧私有 Tier API、Role routing、Agent backend、mlexp、
CLI runner 和 fallback 语义不是新架构的兼容承诺。

批准的设计增量由当前 V0.3 Contract、OpenAPI、fixtures 和 manifest 表达。模板迁移本身不新增
runtime mechanism、配置路径、selector、fallback 或并行实现。

## 3. 系统范围与上下文

| 参与方 | 权威职责 | 禁止越界 |
|---|---|---|
| Slinky | Project、Plan、IR、Forecast/Risk/Action；读取 Observation 并投影 Seat | 不持有 Provider credential，不做最终 admission，不直接执行 IR-backed inference |
| Piko | Agent Runtime；使用 assigned exact `service_level_id`；SDK/recovery adapter | 不理解 Provider/account/pool/Capacity Group，不调用 Management/Observation |
| LLMTier | 模型服务、admission/routing、Invocation/idempotency ledger、Registry、Management、Client-scoped Observation | 不执行 Agent Tool Loop，不组合 Plan/IR，不持有 Knowledge/Artifact/Acceptance authority |
| Admin | 配置 Provider、Registry、Client/Source、capacity、recovery | 不获得 Piko/Slinky 业务 authority，不读取 Secret |
| Memory/Knowledge Client | 调用 Embeddings non-stream | 不形成 Piko Agent Runtime 的旁路 generation path |

系统边界：

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
          -> exact Service Level admission
          -> backend routing
          -> canonical result + usage/recovery

Slinky -> /tier/v1 readiness | service-levels | capacity | invocations | usage | compatibility
          -> version/ETag/valid_until validation
          -> all-constraints committed Seat projection
```

## 4. 解决方案策略

1. **单一事实来源**：Registry 统一 catalog、Models、Observation、admission、capacity membership
   与 manifest，Invocation ledger 统一 Data Plane recovery 与 Observation projection。
2. **分面而不复制状态机**：Data Plane、Observation、Management 使用不同权限和 DTO，但共享
   Registry/ledger 的事实，不建立第二 Registry、第二 inference path 或第二 recovery state machine。
3. **先持久化再 dispatch**：Backend 调用前持久化 idempotency record、Invocation 和 dispatch
   intent，以同一 key/digest 处理 transport retry、agent retry 和 restart recovery。
4. **fail closed**：未知或未激活 surface、streaming、hidden model、权限不匹配和 quota unknown
   都以 typed error 拒绝；不得静默降级或切换 Service Level。
5. **有限且明确的恢复保证**：采用 M2-C `W=168h`、`M=24h`、产品 deadline `D=24h`，不宣称
   无限期 exactly-once。
6. **契约先行、证据激活**：OpenAPI/manifest/fixtures 先成为一致候选；只有实现、capture、隔离、
   retention、UI 和 legacy-removal evidence 全部满足后才激活。

## 5. 构建块视图

| 构建块 | Owner | 职责 | 禁止项/接口 |
|---|---|---|---|
| Data Plane | LLMTier | Responses、Embeddings、Models、recovery GET；校验身份与 strict payload | 不接受 Role/IR selector；不暴露 Provider；不提供 Chat/SSE V0.3 路径 |
| Identity/Entitlement | LLMTier | credential→client、canonical source 授权、quota/entitlement | `source_instance_id` 不作为重启恢复 namespace |
| Admission/Capacity | LLMTier | exact Service Level admission、Capacity Group 与 quota 联合约束 | burst 不计 committed Seat；unknown quota 不视为零或可用 |
| Service Level Registry | LLMTier | catalog/version/ETag/effective/valid、compatibility、physical mapping | 不建立 alias；破坏兼容性必须新 ID 或新 API major |
| Invocation Ledger | LLMTier | idempotency、dispatch intent、状态、canonical response、tombstone、usage | UnknownOutcome 不盲目重派；不得用第二 ledger 投影 Observation |
| Backend Router | LLMTier | 在同一 Service Level 内选择 Provider/Account/Pool/Deployment | 禁止跨 Service Level fallback 和 Provider-direct Client path |
| Observation | LLMTier | Client-scoped readiness、catalog、capacity、invocation、usage、compatibility | 不泄露跨 Client 或 physical credential/routing |
| Management API/UI | LLMTier | inventory、Secret write/rotate、probe、publish、capacity/usage/audit/recovery | mutation 必须鉴权、授权、审计和并发检查；Secret 不回显 |
| Piko adapter | Piko | non-stream POST、202/terminal/lost-response recovery、`maxRetries:0` | 不退回 Pi 内建 streaming adapter；不生成新 key 盲重派 |
| Seat projection | Slinky | 将有效 Capacity Snapshot 投影为 TierServiceSeat/IRBackingSeat | 不绕过 LLMTier admission，不撤销已 admission in-flight Invocation |

## 6. 运行时视图

### 6.1 首次 Responses 调用

1. Piko 使用 Bearer credential、canonical Source headers、`Idempotency-Key`、
   `X-Tier-Client-Request-ID` 和 exact `model=service_level_id` 发起 non-stream POST。
2. LLMTier 认证 client、授权 source、规范化请求并计算 canonical digest。
3. 在任何 Backend 调用前，事务性持久化 idempotency record、Invocation 和 dispatch intent。
4. admission 同时检查 Registry、entitlement、direct committed capacity、所有 overlapping groups、
   Client quota、readiness 与有效期。
5. Router 只在同一 Service Level 内选择 Backend，完成一次 dispatch。
6. terminal 成功写入 canonical Response/usage，返回标准 `200 ResponsesResponse`。

### 6.2 并发重复与 recovery

| 状态 | POST replay | 后续动作 |
|---|---|---|
| Pending/Queued/Running | `202 InvocationAccepted` + `Location` + `X-Tier-Invocation-ID` + `Retry-After` | Piko 按 Invocation GET readiness 等待 |
| Succeeded | 原 endpoint canonical `200` body | 零次 dispatch；必要时 Response GET |
| Failed | `502 invocation_failed` | typed `retryable=false`，不得重派 |
| Cancelled | `409 invocation_cancelled` | typed `retryable=false`，不得重派 |
| UnknownOutcome | `503 invocation_outcome_unknown` | manual reconcile；不得重派 |

lost response 后，Piko 复用同一 key/digest/Invocation obligation，查询
`GET /v1/invocations/{id}`。`recovery_ready`、`retry_after_ms` 和
`recovery_disposition=wait|retrieve_response|raise_terminal_error|manual_reconcile` 是唯一恢复判定，
不能从 HTTP 200 猜测状态。

### 6.3 Capacity Snapshot 失效

1. `TierServiceSeat`/`IRBackingSeat` 立即 Invalidated，禁止新 dispatch；
2. Slinky IR Management 通知 Plan 更新 Forecast/Risk/Action；
3. 已由 LLMTier admission 的 in-flight Invocation 不撤销、不跨 Stage rollback；
4. 当前 Attempt 只在该 Invocation 的安全边界内收敛；
5. 后续 Work 重新获取 snapshot、投影并 admission。

### 6.4 启动、关闭与升级

- 启动必须验证配置来源、Registry/manifest 版本、ledger readiness、所需 Service Level 与
  Observation readiness；缺字段或不兼容返回 SourceError/ContractMismatch。
- 优雅关闭停止新 admission，允许已 admission Invocation 在受控边界内收敛，并保持 recovery
  record 可查询。非优雅退出由 durable dispatch intent 与 ledger 恢复，不默认重新 dispatch。
- Registry 更新以 version、ETag、`effective_at`、`valid_until` 和原子 publish 生效；破坏兼容性的
  语义变化使用新 ID/API major。升级不得同时保留旧新 current path。

## 7. 部署与物理视图

V0.3 逻辑部署至少包含 LLMTier API process、Admin Web UI、durable Registry/ledger/result store、
Provider/Local Deployment connectors，以及面向日志、metrics、audit 的观测后端。Data Plane、
Observation 和 Management 可以由同一服务进程暴露，但 credential、authorization policy 和 DTO
必须分离。

具体 production 主机、容器编排、数据库产品、HA 拓扑、备份 RPO/RTO 和故障域尚未冻结，属于
实现前 Open Gate，不得从当前 Python 开发基线推断。部署选择必须证明：ledger 在进程重启后仍可
恢复、M2-C retention 不因滚动升级降级、Secret 不进入镜像/日志/备份导出、多个实例共享一致
Registry 和 idempotency namespace。

## 8. 横切概念

### 8.1 身份与权限

- Authorization 绑定 canonical `client_id`。
- `X-Tier-Source-ID` 是该 client 下经授权的 canonical `source_id`。
- `X-Tier-Source-Instance-ID` 仅用于 observation、correlation 和 audit。
- `Idempotency-Key` 是逻辑 Invocation 的 durable 去重/恢复 identity；
  `X-Tier-Client-Request-ID` 只是调用相关性 ID，不能替代前者。

### 8.2 配置、时间与错误

LLMTier 独立配置是唯一运行时覆盖入口，不回读 Slinky 配置。跨接口时间使用契约冻结格式，
ETag/304 和 `valid_until` 必须由 Client 显式处理。所有错误使用机器可判定的 typed envelope；
unknown/partial usage 保持 unknown/partial，不能折算为零。

### 8.3 幂等、retention 与隐私

namespace 至少覆盖 canonical client/source、endpoint/version 与 Idempotency-Key；digest 覆盖 exact
Service Level、规范化 body 和影响语义的 headers。同 namespace/key 不同 digest 是不可重试 conflict。
active record 保留到 terminal；terminal 后 digest/tombstone、Invocation terminal view 和 canonical
Response 至少保留 168h。Prompt/output privacy retention 可独立配置，但不得提前删除 content-free
digest/tombstone。

### 8.4 容量与公平性

`concurrent_invocation` 是唯一 Seat 单位。Semantic validator 检查 ID 唯一、exact-case membership、
双向 group membership、`available <= committed`、时间顺序、unknown quota 和 blocking reason。
Schema 校验不能替代运行时语义校验；multi-client/source isolation 与公平性必须有生产证据。

### 8.5 兼容性

V0.3 manifest 必须分别给出 overall/per-capability activation，并保持 candidate/not_active，直到全部
gate 关闭。Responses `stream=true` 返回 `unsupported_feature`；Chat/SSE path 返回统一
`unsupported_endpoint`。不提供 alias、passthrough、转换入口或 runtime fallback。

## 9. 架构决策

当前决定来自三方已记录的 Review ID；本次迁移不重写或重新批准：

| Decision | 状态 | 来源 |
|---|---|---|
| Authority 分离与唯一 inference path | Candidate accepted by Slinky | `S-20260906-59891d73fa13` |
| M2-C：`W=168h`、`M=24h`、`D=24h` | Candidate frozen | `L-20260906-12940a96e148`、`P-20260906-c14b4af35ac3` |
| Scope B：V0.3 non-stream；Chat/SSE 延至 V0.4 | Authoritative scope decision | `S-20260906-2f9539048493` |
| Amendment 4 design/contract candidate | Slinky ACCEPTED | `S-20260906-1e12f5e61d73` |
| Piko machine-contract field review | Open | `P-20260906-6084db30d431` |

新重大设计选择必须单独建立 `decisions.adr`；不得藏在本迁移 diff 中。

## 10. 质量要求

| ID | 场景 | 可测判定 |
|---|---|---|
| LT-QR-001 | 相同 key/digest 并发或重启重试 | Backend dispatch 总数为 1；active 返回 202，terminal 重放 canonical 结果/错误 |
| LT-QR-002 | lost response 或 UnknownOutcome | adapter 先查询 recovery；UnknownOutcome 不自动重派 |
| LT-QR-003 | Capacity Snapshot 失效 | 新 dispatch 被阻断；已 admission Invocation 仅安全收敛；后续 Work 重新投影 |
| LT-QR-004 | exact-case 与 Registry 一致性 | Models、Observation、admission、manifest 对同一 ID/version/ETag 一致；错误大小写 fail closed |
| LT-QR-005 | Client/Source 隔离 | 跨 client/source 的 invocation、usage、capacity 和 recovery 不可见，返回 typed error |
| LT-QR-006 | Management Secret | create/rotate 只一次性返回允许的信息；list/detail/UI/log/audit 不含 secret 明文或可逆值 |
| LT-QR-007 | M2-C retention | terminal 后连续 168h 识别重复 key，并在 24h recovery deadline 内恢复 canonical outcome |
| LT-QR-008 | unsupported surface | Chat/SSE/streaming 无 route、alias 或 fallback，稳定返回规定 typed error |
| LT-QR-009 | 管理与观察一致性 | API/UI、aggregate DTO、ETag/304、pagination、unknown/partial 通过正负 Contract Test |

## 11. 风险与技术债

| ID | 风险/债务 | 影响 | Gate/缓解 |
|---|---|---|---|
| LT-RISK-001 | 当前代码仍是旧 embedded Tier 复制基线 | 文档可能领先实现 | production wiring 和 legacy-removal scan 未通过前 activation=false |
| LT-RISK-002 | Piko machine-contract review 未闭环 | SDK/adapter 字段级不兼容 | 使用已发送 bundle 完成 exact fixture capture |
| LT-RISK-003 | durable store/HA/RPO/RTO 未选型 | 无法证明 crash recovery 与 168h retention | 实现前 ADR 与故障注入证据 |
| LT-RISK-004 | Admin Web UI 尚无实现证据 | V0.3 required management 不完整 | UI/API 正负、权限和 secret tests |
| LT-RISK-005 | 公共 STD 仍是 draft、无 immutable revision | 无法冻结模板来源 commit | `docs/std.lock.json.source_revision=null`；STD 首次 tag 后升级 review |
| LT-RISK-006 | 旧 v0.1/v0.2 文档仍在仓库 | 检索/实现可能误取历史语义 | inventory 明确 superseded；迁移 review 前不删除，后续归档并按 authority 过滤 |

## 12. 术语表

| 术语 | 定义 |
|---|---|
| Service Level | LLMTier catalog 中 exact-case、Client-visible 的模型服务能力与 SLO identity |
| Registry | Service Level、版本、兼容性和 capacity membership 的唯一事实来源 |
| Invocation | 一次逻辑模型调用及其 durable admission/dispatch/recovery 状态 |
| Seat | Slinky 投影的 `concurrent_invocation` committed capacity 单位 |
| Capacity Group | shared/overlapping capacity 约束集合，全部相关 group 必须同时满足 |
| M2-C | 有限窗口的 idempotency/recovery 保证：terminal 后 `W=168h`，margin `M=24h` |
| canonical Response | create、completed replay 与 Response GET 复用的同一标准 Response body |
| Scope B | Slinky 冻结的 V0.3 non-stream surface；Chat/SSE 延至 V0.4 |

## A. 数据模型与状态机

核心实体：Client、Source、SourceInstance、Entitlement、ServiceLevel、Pool、CapacityGroup、
Provider、Account、Deployment、Invocation、CanonicalResponse、Usage、RecoveryItem、AdminJob。

Invocation active 状态仅为 Pending、Queued、Running；terminal 为 Succeeded、Failed、Cancelled、
UnknownOutcome。`InvocationAccepted` 不得包含 UnknownOutcome。完整字段、oneOf 和错误状态以当前
OpenAPI 为准。

## B. API、Schema、Event 与错误契约

- Data Plane：`docs/contracts/piko-data-plane-contract-v0.3.md`
- Slinky Observation：`docs/contracts/slinky-capacity-observation-contract-v0.3.md`
- Management/UI：`docs/contracts/llmtier-management-contract-v0.3.md`
- 唯一 machine authority：`docs/contracts/openapi/llmtier-v0.3.openapi.json`
- compatibility authority：`docs/contracts/compatibility-manifest-v0.3.json`
- fixtures：`docs/contracts/fixtures/v0.3/`

Markdown 负责范围、rationale 与 authority；OpenAPI/manifest/fixtures 负责可生成、可验证的字段级
契约。发生冲突时必须通过 review 修正两者，不允许 Consumer 自选一套解释。

## C. 持久化、一致性、幂等与恢复

Backend dispatch 前必须持久化 request digest、Invocation reference 和 recovery obligation。
active/replay/terminal 行为、headers、recovery disposition、retention 与完全删除后的边界见第 6、8 节
及 recovery fixtures。完全删除后不保证识别历史 key，不宣称无限 exactly-once。

## D. 安全、隐私、Secret 与审计

三分面 credential 与 scope 分离；least privilege；Management mutation 全审计并带 concurrency check；
Secret create/rotate 只写不读；metadata key/value 按 64/512 UTF-8 encoded bytes fail closed，不静默截断。
Prompt/output retention 与 content-free tombstone retention 分离。

## E. 可观测性、容量、性能、资源与 SLO

Readiness 必须暴露 Ready/Degraded/NotReady、实例/版本、Observation readiness、visible Service Levels、
snapshot version 和 next refresh。Usage 支持按 Source/Instance/Service Level/endpoint/status 分组；
unknown/partial 不折算为零。当前没有 throughput/latency 的 production measured baseline；性能目标在
Provider/Deployment 与 Service Level SLO 冻结后补齐，不得把开发环境或模拟结果写成实测。

## F. 测试设计与需求 traceability

`docs/qa/llm-tier-contract-qa-v0.3.md` 与 `tests/test_contract_semantics_v03.py` 覆盖当前静态 candidate。
需求/Review → Contract → fixture/test → execution evidence 的映射必须保留原 Review ID。当前 33 项本地
测试通过只证明文档与 Schema 自洽，不证明 production implementation。

## G. 集成、部署、迁移、回滚与发布 Gate

实现顺序：Registry/ledger → Scope B Data Plane/recovery → Management API/UI → Observation/capacity →
三方 conformance → legacy/direct-path removal → manifest activation。回滚不能恢复旧 embedded Tier、
Provider-direct、Role selector 或跨等级 fallback；若新实现无法激活，应保持 candidate 关闭而非启用旁路。

Activation gates：

1. production implementation commit 与完整正负 Contract Test；
2. Management API/UI 权限、并发、Secret non-disclosure；
3. Registry 多分面一致性与 Capacity semantic validator 生产接线；
4. multi-client/source isolation、entitlement、公平性；
5. Piko pinned SDK/adapter capture 与 Memory/Knowledge Embeddings Consumer Contract Test；
6. M2-C retention、privacy policy 和 crash/lost-response 零重复 dispatch；
7. legacy/parallel/direct path 删除扫描；
8. 文档、机器契约、fixtures、manifest 与 route 行为一致。

## H. 未决问题、外部依赖和后续版本

- Piko 对当前 machine-contract bundle 的最终 ACCEPTED/AMENDMENT；
- production persistence/HA/backup/RPO/RTO 选型及 ADR；
- Provider/Deployment 的 measured SLO 与公平性验证环境；
- Admin Web UI 的具体技术栈与部署方式；
- STD 首个 immutable revision/tag 及项目 lock 升级；
- V0.4 Chat Completions、Responses/Chat SSE 和 streaming recovery 的独立设计与 review。
