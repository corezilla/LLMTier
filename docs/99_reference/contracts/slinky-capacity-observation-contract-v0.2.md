# llmtier 面向 Slinky 的 Capacity/Observation 契约提案 v0.2

Last Updated: 2026-09-06 15:03:00 +08:00

Status: Candidate；回应 Slinky C1–C7 review，不是冻结契约或实现证据

## 1. Authority（C1 ACCEPT）

Slinky 读取 Client-scoped Logical Service Level、readiness、committed capacity、usage 和 dependency outcome，用于投影 Tier Service Seat。Slinky 不取得 Provider credential、physical routing 或 llmtier Management authority，也不能绕过 Piko 直接执行 IR-backed Agent inference。Piko 不消费此分面。

## 2. API surface

- `GET /tier/v1/readiness`
- `GET /tier/v1/service-levels`
- `GET /tier/v1/service-levels/{service_level_id}`
- `GET /tier/v1/capacity/snapshots/current`
- `GET /tier/v1/invocations/{invocation_id}`
- `GET /tier/v1/usage/summary`
- `GET /tier/v1/compatibility`

所有响应按 credential scope 过滤；普通 Slinky Client 看不到其他 Client 或 physical Provider/Account/Backend/Pool。

## 3. Capacity DTO 与单位（C2）

Machine-readable Schema：`schemas/llmtier-contracts-v0.2.schema.json#/$defs/CapacitySnapshot`；完整 DTO 示例为 `fixtures/v0.2/capacity-snapshot-example.json`。

唯一计量单位是 `concurrent_invocation`。一个 committed Tier Service Seat 表示一个可同时 admission 的 invocation，不表示 token/s、Agent Slot 或 burst entitlement。

Snapshot 同时提供：

- `service_levels[]`：每个 exact service level 的 direct committed 上限/可用量、burst、in-flight、queue、Client quota 和所属 group。
- `capacity_groups[]`：每个 group 的 Client committed 上限、当前 committed in-flight、剩余 committed capacity、service-level membership。
- `membership_mode=all_constraints`：某 service level 属于多个 group 时，一个新增 Seat 同时消耗每个所属 group 的一个单位。

令 `x_l` 为准备给 service level `l` 新增投影的 committed Seat 数。投影必须同时满足：

1. `x_l >= 0` 且为整数。
2. `x_l <= direct_available_committed_l`。
3. 对每个 group `g`：`sum(x_l for l in members(g)) <= available_committed_concurrency_g`。
4. service level 同属多个 group 时，第 3 条每个约束都必须满足；不能选择一个 group，也不能把 group capacity 相加。
5. `request_quota_remaining` 已知时，`x_l` 不得超过它；未知不等于无限，需按 blocking policy 处理。
6. `burst_concurrency` 不进入 committed Seat 投影，只能作为 admission 时的临时非承诺能力。
7. `status=Unavailable`、存在 blocking reason 或 snapshot 过期时，不得新增 Seat。

这允许共享 group 中的多个等级按组合分配，而不是简单丢弃某个等级。正反 fixture：`fixtures/v0.2/capacity-projection-fixtures.json`，覆盖共享组、重叠组、burst、Client quota 和 snapshot expiry。

## 4. Version、ETag 与 invalidation（C3）

- `configuration_version`：影响 service-level contract、entitlement、routing policy 或 retention 的配置内容 digest；只有这些配置事实改变才变化。
- `inventory_version`：Provider/Account/Backend/Pool inventory 及其可用能力集合的 digest；inventory/probe eligibility 改变时变化。
- `capacity_version`：决定 committed constraint graph 的 entitlement、group membership、group/direct committed limit 的 digest；live request counter 变化不改变它。
- `snapshot_version`：每次发布新的 immutable observation 单调递增；in-flight/available/queue 变化会产生新 snapshot。
- `ETag`：完整 response bytes 的强 ETag；任一返回字段变化都会变化，支持 `If-None-Match`/`304`。
- `valid_until`：该 observation 可用于新投影的截止时间；时间到即失效，即使版本字段未变。

Slinky 通过 readiness/capacity 的条件 GET 发现新 `inventory_version`/`capacity_version` 或到期。`snapshot_version`/ETag 因 live counter 刷新本身不触发整体重规划；它只更新当前 admission 观察。

Invalidation 仅阻止未 dispatch 或新增 Seat 分配。它不自动回滚 Stage、不取消已被 llmtier 接收的 Invocation，也不释放 active IR。运行中绑定沿已有 invocation reconcile/recovery obligation 收敛。

## 5. Invocation 与 usage

Observation invocation view 与 Data Plane recovery extension 投影自同一 Invocation ledger；前者可提供授权的运营字段，后者只提供 Piko 恢复所需最小字段。两者不得拥有不同状态机或 state store。

Usage 缺失为 unknown/absent，不补零；Client invocation 与内部 Backend attempt 分开计数。

## 6. 设计、实现、验证状态

- Planned：本 v0.2 DTO、约束算法、version/invalidation 语义。
- Implemented：当前代码已完成独立 config/state 和纯模型 authoritative registry 第一阶段。
- Verified：独立 package/runtime boundary tests 与契约静态/fixture 结构检查；本契约 endpoint 和真实 admission runner 尚未实现。
