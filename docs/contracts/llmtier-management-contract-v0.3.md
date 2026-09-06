# LLMTier Management API 与 Admin Web UI 契约提案 v0.3

Last Updated: 2026-09-06

Status: Candidate Required Scope；V0.3 必须交付，当前尚未实现

## 1. Authority 与访问边界

LLMTier 是独立模型服务系统，V0.3 必须提供 Management API 和最小可用 Admin Web UI。该分面只供 LLMTier 管理员使用，与 Piko Data Plane credential、Slinky Observation credential 和普通 Client scope 分离。

所有 mutation 必须鉴权、授权、审计并支持并发版本检查。Secret 只写不读：API/UI 只能显示是否已配置、版本/轮换时间和健康状态，绝不回显 secret 明文、密文或可逆导出。

## 2. Management API surface

统一前缀为 `/tier/admin/v1`，唯一机器权威为 `openapi/llmtier-v0.3.openapi.json`：

- Provider、Account、Local Deployment：list/get/create/update/disable、credential write/rotate、discovery/probe。
- Model discovery：触发/读取 discovery result，并将 physical capability 映射到 Service Level candidate。
- Service Level Registry 与 Pool：exact-case ID、Contract/SLO、同等级 Backend override、capacity membership、版本发布。
- Client、Source、SourceInstance、Entitlement：注册、scope、多 Slinky/Piko Host/test lane identity、Service Level grant、committed/burst/quota policy。
- Probe/readiness：执行 probe、查看 readiness evidence、隔离或恢复 backend eligibility。
- Capacity Group、Capacity、Usage、Audit、Job、Recovery Item：查看 shared/overlapping membership、scoped/aggregate 状态、backlog 和历史 disposition，执行明确授权的 reconcile/cancel 操作。

Management operation 不得创建跨 Service Level fallback、Role selector 或 Provider-direct Data Plane。破坏兼容性的 Service Level 修改必须创建新 ID 或 API major。

### 2.1 逐 endpoint 契约

| 资源 | Collection | Detail / action |
| --- | --- | --- |
| Provider | `GET/POST /tier/admin/v1/providers` | `GET/PATCH /tier/admin/v1/providers/{provider_id}` |
| Account | `GET/POST /tier/admin/v1/accounts` | `GET/PATCH /tier/admin/v1/accounts/{account_id}`；`POST .../secret` 写入或轮换 secret |
| Local Deployment | `GET/POST /tier/admin/v1/deployments` | `GET/PATCH /tier/admin/v1/deployments/{deployment_id}` |
| Service Level | `GET/POST /tier/admin/v1/service-levels` | `GET/PATCH /tier/admin/v1/service-levels/{service_level_id}`；`POST /registry/publish` 发布 Registry |
| Pool | `GET/POST /tier/admin/v1/pools` | `GET/PATCH /tier/admin/v1/pools/{pool_id}` |
| Client | `GET/POST /tier/admin/v1/clients` | `GET/PATCH /tier/admin/v1/clients/{client_id}`；`POST .../credentials` 创建一次性 credential |
| Source | `GET/POST /tier/admin/v1/sources` | `GET/PATCH /tier/admin/v1/sources/{source_id}` |
| SourceInstance | `GET/POST /tier/admin/v1/source-instances` | `GET/PATCH /tier/admin/v1/source-instances/{source_instance_id}` |
| Capacity Group | `GET /tier/admin/v1/capacity-groups` | `GET /tier/admin/v1/capacity-groups/{capacity_group_id}` |
| Entitlement | `GET/POST /tier/admin/v1/entitlements` | `GET/PATCH /tier/admin/v1/entitlements/{entitlement_id}` |
| Discovery / Probe / Job | `POST /tier/admin/v1/discovery/jobs`；`POST /tier/admin/v1/probe/jobs`；`GET /tier/admin/v1/jobs` | `GET /tier/admin/v1/jobs/{job_id}` |
| Operations | `GET /tier/admin/v1/capacity`、`/usage`、`/audit`、`/recovery-items` | `GET /tier/admin/v1/recovery-items/{id}`；`POST .../{id}/actions` |

OpenAPI 为每个 operation 固定 request/response DTO、typed default error 和资源 ID parameter。所有 list 使用 `limit`、`cursor` 与 `PageMeta.next_cursor`。ETag 支持必须逐 endpoint 显式出现：声明 `If-None-Match` 的 GET 同时声明强 `ETag` 和 `304`，未声明的 GET 不声称缓存验证能力。所有 create/action `POST` 要求 `Idempotency-Key`；所有资源 `PATCH` 同时要求 `If-Match` 和 body `expected_version`，不匹配返回 `409/412 version_conflict`。Discovery、probe、Registry publish 和 recovery action 返回 `202 AdminJob` 与 `/tier/admin/v1/jobs/{job_id}` Location。

无 `client_id/source_id` filter 的 `/capacity` 使用 `AdminCapacityPage`，维度可为 null 表示 aggregate；无 `client_id` filter 的 `/usage` 使用 grouped `AdminUsagePage`。Unknown/Partial usage 的 count/token 保持 null，绝不能补零。

Account secret 写入/轮换的 response 只返回状态、secret version 和 rotated timestamp；Client credential 只在创建 response 返回一次 plaintext credential，之后所有 GET/list/audit 都只能返回 fingerprint/status。Recovery action 必须显式提交 `redispatch=false`，只允许 `reconcile` 或 `cancel`，不得绕过 Invocation ledger。

## 3. 最小 Admin Web UI

UI 必须覆盖上述资源的 list/detail/edit/disable/rotate/probe/publish/recovery 操作，并具备：

- destructive/secret mutation 的明确确认和 typed result；
- pending/active/failed 状态与最近审计事件；
- Registry draft 与 published version diff；
- readiness/capacity/usage 的 freshness、版本和 blocking reason；
- secret 字段始终 write-only，浏览器响应和日志不得含 secret value。

## 4. 一致性与激活

Management 发布的同一 authoritative Registry 必须驱动 Data Plane Models、Observation service levels、admission 和 Compatibility Manifest。V0.3 激活前必须具备：

1. API/UI 正向、权限拒绝、输入负例、并发冲突和 secret non-disclosure 测试；
2. Registry draft/publish/rollback-policy 与 exact-case 唯一性测试；
3. Provider/Account/Deployment discovery/probe 到 readiness 的 trace；
4. Client/Source isolation、entitlement、公平性和审计证据；
5. Recovery 管理操作不绕过 Invocation ledger/idempotency safety 的测试。

本文件定义 required V0.3 scope，不声称当前旧 `/health`、`/runtime`、`/stats` 或 CLI 已满足该范围。
