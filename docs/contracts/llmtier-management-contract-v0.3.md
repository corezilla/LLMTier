# LLMTier Management API 与 Admin Web UI 契约提案 v0.3

Last Updated: 2026-09-06

Status: Candidate Required Scope；V0.3 必须交付，当前尚未实现

## 1. Authority 与访问边界

LLMTier 是独立模型服务系统，V0.3 必须提供 Management API 和最小可用 Admin Web UI。该分面只供 LLMTier 管理员使用，与 Piko Data Plane credential、Slinky Observation credential 和普通 Client scope 分离。

所有 mutation 必须鉴权、授权、审计并支持并发版本检查。Secret 只写不读：API/UI 只能显示是否已配置、版本/轮换时间和健康状态，绝不回显 secret 明文、密文或可逆导出。

## 2. 最小 Management API surface

统一前缀为 `/admin/v1`：

- Provider、Account、Local Deployment：list/get/create/update/disable、credential write/rotate、discovery/probe。
- Model discovery：触发/读取 discovery result，并将 physical capability 映射到 Service Level candidate。
- Service Level Registry 与 Pool：exact-case ID、Contract/SLO、同等级 Backend override、capacity membership、版本发布。
- Client、Source、Entitlement：注册、scope、Service Level grant、committed/burst/quota policy。
- Probe/readiness：执行 probe、查看 readiness evidence、隔离或恢复 backend eligibility。
- Capacity、Usage、Audit、Recovery：查看 scoped/aggregate 状态，执行明确授权的 reconcile/cancel/retention 管理操作。

Management operation 不得创建跨 Service Level fallback、Role selector 或 Provider-direct Data Plane。破坏兼容性的 Service Level 修改必须创建新 ID 或 API major。

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
