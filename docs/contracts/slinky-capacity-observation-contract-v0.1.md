# llmtier 面向 Slinky 的 Capacity/Observation 契约提案 v0.1

Last Updated: 2026-09-06 14:15:00 +08:00

Status: Candidate；不是冻结契约或实现证据

## 1. Authority

Slinky 使用此分面读取可计划的 Logical Service Level、Client-scoped readiness、committed capacity、usage 和 dependency outcome，用于投影 Tier Service Seat。Slinky 不取得 Provider credential、physical routing 或 llmtier Management authority，也不能绕过 Piko 直接执行 IR-backed Agent inference。

Piko 不消费此分面。

## 2. Candidate surface

- `GET /tier/v1/readiness`
- `GET /tier/v1/service-levels`
- `GET /tier/v1/service-levels/{service_level_id}`
- `GET /tier/v1/capacity/snapshots/current`
- `GET /tier/v1/invocations/{invocation_id}`
- `GET /tier/v1/usage/summary`
- `GET /tier/v1/compatibility`

所有响应按 credential scope 过滤。普通 Slinky Client 看不到其他 Client、physical Provider/Account/Backend/Pool；Admin scope 属独立 Management 分面。

## 3. Seat projection

Capacity snapshot 必须包含 immutable `snapshot_id/version`、`observed_at`、`valid_until`、Client/Source scope，以及每个 exact service level 的 committed/burst/available/in-flight/queued、quota evidence、blocking reason 和 shared capacity group refs。

Slinky 只能按未过期 snapshot 投影 Tier Service Seat；shared capacity group 必须去重，不能把共享同一 physical capacity 的多个 service level 重复相加。Snapshot 不替代最终 admission，也不能推导 Piko Agent Slot capacity。

## 4. Readiness

Global `Degraded` 不自动阻断全部 Client。Slinky 必须同时检查 `data_plane_ready`、当前 Client 可见 service level 状态、committed capacity 和 blocking reason。`valid_until` 到期或 inventory/config version 变化时，旧 Seat projection 失效并触发重新规划。

## 5. Invocation 与 usage

Observation invocation view 可包含 Client/Source/service-level/endpoint/status/usage/error/record version，但 physical routing 默认隐藏。Usage 缺失为 unknown/absent，不补零；Client invocation 与内部 Backend attempt 分开计数。

Piko 的 lost-response recovery 不依赖此 Observation API；其 Data Plane recovery extension 单独 review。

## 6. 当前证据边界

旧实现存在 `/health`、`/runtime`、`/stats` 等运营视图，但缺少新版 Client scope、snapshot version/expiry、ETag、shared capacity group、entitlement 和 authority isolation，因此不能作为本契约已实现证据。

