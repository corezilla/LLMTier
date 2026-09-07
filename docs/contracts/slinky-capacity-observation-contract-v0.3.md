# LLMTier 面向 Slinky 的 Capacity/Observation 契约提案 v0.3

> **Document Status: Superseded（2026-09-07）** 当前人工可读 consumer-boundary authority 已迁至
> [`llmtier-slinky-capacity-observation-control`](../60_interfaces/slinky-capacity-observation-control.md)，
> 机器字段 authority 仍为 [`llmtier-v0.3.openapi.json`](openapi/llmtier-v0.3.openapi.json)。本文件仅保留
> 历史来源；逐 scope disposition 见
> [`legacy-v03-scope-mapping.md`](../98_migration/legacy-v03-scope-mapping.md)。

Last Updated: 2026-09-07

Status: Superseded；历史契约提案，仍无 production wiring 证据

## 1. Authority 与唯一推理路径

Slinky 负责 Project/Plan/IR 和读取 Client-scoped Observation；Piko 负责 Agent Runtime；LLMTier 负责模型服务、admission、routing、Invocation ledger、Service Level Registry 和 Client-scoped observation。唯一 IR-backed inference 路径是 `Runtime -> Piko -> LLMTier`。

Slinky 不取得 Provider credential、physical routing 或 LLMTier Management authority，也不绕过 Piko 执行 inference。Piko 不消费 Observation 分面。

## 2. Observation surface

- `GET /tier/v1/readiness`
- `GET /tier/v1/service-levels`
- `GET /tier/v1/service-levels/{service_level_id}`
- `GET /tier/v1/capacity/snapshots/current`
- `GET /tier/v1/invocations/{invocation_id}`
- `GET /tier/v1/invocations`
- `GET /tier/v1/usage/summary`
- `GET /tier/v1/compatibility`

所有响应按 credential scope 过滤。`/tier/v1/service-levels` 与 Data Plane Models、admission、capacity membership 和 Compatibility Manifest 必须由 LLMTier 同一 Registry 生成。

同一 authenticated Client 可以在其已授权范围内查询或聚合多个 Source；`source_id` 与
`source_instance_id` query 只是过滤/分组维度，不创建新的鉴权 namespace。跨 Client 或未授权 Source
访问必须拒绝。Data Plane recovery 仍严格使用 authenticated `client_id + canonical source_id`，
Observation 的聚合能力不得扩大该 recovery scope；`source_instance_id` 只用于 correlation、
observation 和 audit。

各 endpoint 的 query/header、cursor pagination、ETag/`If-None-Match`/`304`、response DTO、typed error 与 Schema ref 以 `openapi/llmtier-v0.3.openapi.json` 为唯一机器权威。Invocation list 支持 `limit/cursor/status/service_level_id/source_id/source_instance_id/from/to/client_request_id`；Usage 支持 `interval/group_by/source_id/source_instance_id/service_level_id/endpoint/status/limit/cursor`。字段或 Source identity 无法满足时返回 typed `source_error` 或 `contract_mismatch`，Slinky Adapter 不得猜测。

Readiness 显式给出 Ready/Degraded/NotReady、Tier instance/version、Observation readiness、visible Service Levels、snapshot version 与 refresh window。Service Level DTO 包含 kind、capabilities、context、Structured Output、Tool Calling、modalities/limits 和 Compatibility ref。Compatibility endpoint 按 method/path 返回 supported/unsupported fields、streaming、Schema/error version、SDK matrix 与 effective_at。

## 3. Service Level Registry

LLMTier 是 catalog authority。`service_level_id` 使用 exact、大小写敏感名称，例如 `Worker`、`Junior`；禁止 lowercasing、alias、Role selector 或跨 Service Level fallback。

Provider/account/pool mapping 与同等级 Backend override 属于 LLMTier。只要能力 Contract/SLO 不变，physical mapping 可替换而不改变 ID；破坏兼容性的语义变化必须创建新 ID 或新 API major。Registry 发布 catalog/version/ETag/`effective_at`/`valid_until`，并在唯一 ID、capacity membership 和 manifest 三方 Contract Test 通过后激活。跨分面一致性验证的是 exact ID、catalog version/ref 与兼容语义来自同一 Registry；各 endpoint 的 ETag 只校验自身 representation，capacity/usage 变化不要求 Models 或 Registry ETag 同步变化。

## 4. CapacitySnapshot 与 Seat

唯一容量单位是 `concurrent_invocation`。一个 committed Tier Service Seat 表示一个可同时 admission 的 invocation，不表示 token/s、Agent Slot 或 burst entitlement。

投影必须同时满足 direct committed capacity、全部 shared/overlapping Capacity Group、Client quota、service readiness/blocking reason 和 `valid_until`。同一 shared group 不得跨等级重复相加；同属多个 group 时每个约束都必须满足。burst 不计入 committed Seat；`request_quota_remaining=null` 必须以 `client_quota_unknown` 阻断新增 committed Seat。

JSON Schema 负责结构；authoritative semantic validator 还必须检查：

1. `capacity_group_id` 和 exact-case `service_level_id` 各自在 snapshot 内唯一；
2. `available_committed_concurrency <= committed_concurrency`；
3. group membership 双向完全一致，引用必须存在；
4. 每个 service level ID 存在于同一 Registry，case 完全相同；
5. `observed_at < valid_until`，evaluation time 不晚于 `valid_until`；
6. quota unknown、Unavailable 或 blocking reason 对新投影 fail closed。

## 5. Version、ETag 与精确 invalidation

`configuration_version`、`inventory_version`、`capacity_version` 和单调 `snapshot_version` 分离；完整 response bytes 使用强 ETag。`valid_until` 是新投影/dispatch 的硬截止时间。

Snapshot 失效时：

1. 关联的 `TierServiceSeat` / `IRBackingSeat` 立即进入 `Invalidated`，不得用于新 dispatch；
2. IR Management 通知 Plan 更新 Forecast、Risk 和 Action；
3. 已经被 LLMTier admission 的 in-flight Invocation 不由 Slinky 撤销，也不跨 Stage rollback；
4. 当前 Attempt 只在该已 admission Invocation 的安全边界内收敛；
5. 后续 Work 不得继续使用失效 Seat，必须重新投影并 admission。

因此“不回滚 active IR”不表示失效 Seat 仍可继续派发。

## 6. Retention 与 recovery observation

Observation invocation view 与 Data Plane recovery extension 投影自同一 Invocation ledger，不得出现第二状态机。V0.3 采用 M2-C：最短保证窗口 `W=168h` 从 Invocation terminal 起算；safety margin `M=24h`，其中 clock skew 最多 5 分钟；产品 deadline `D=24h` 满足 `D <= W-M = 144h`。active idempotency record 保留到 terminal；terminal 后 content-free digest/tombstone、Invocation terminal view 与带恢复所需内容的 canonical Response 均至少保留 168h。可独立配置的是原始 Prompt/output 副本的 privacy retention；配置不得提前删除 digest/tombstone，也不得使 canonical Response 在 168h 窗口内不可恢复，否则配置无效并阻断 activation。

## 7. Metadata 与证据状态

Metadata key/value 的权威限制是 64/512 UTF-8 encoded bytes；Schema 的 `maxLength` 不是最终字节检查。多字节和 capacity 负例由 V0.3 fixtures/validator 覆盖。

- Planned：真实 Observation endpoints、Registry、admission 和 invalidation notification wiring。
- Implemented：candidate Schema、manifest、fixtures、semantic validator test harness。
- Verified：本地静态/语义测试；尚无 production endpoint、Registry 一致性、公平性或 Slinky E2E 证据。
