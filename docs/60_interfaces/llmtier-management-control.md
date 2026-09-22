<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier Management Interface Control

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-management-control` |
| Document Version | `0.3.3-draft.5` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | LLMTier |
| Approver | 待定 |
| Approval Date | 待定 |
| Created Date | `2026-09-07` |
| Last Modified Date | `2026-09-22` |
| Template Version | `0.1.0` |
| Template ID | `interfaces.control` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/60_interfaces/llmtier-management-control.md` |
| Supersedes | `docs/99_reference/contracts/llmtier-management-contract-v0.3.md` |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 接口目的、范围与双方 authority

Management是LLMTier自己的operator面，不是Slinky/Piko控制面。只管理云/本地模型、deployment、逻辑等级、健康探测、token Usage和审计，并提供只读的脱敏运行日志查询。

## 2. 接口注册表

`/v1/providers*`、`/v1/deployments*`、`/v1/service-levels*`提供list/get/create/update/delete；`POST /v1/probes`执行获授权探测；`GET /v1/usage`（data credential仅见自身，admin credential见全部）、`DELETE /v1/usage`（仅admin，清空用量）、`GET /v1/runtime`、`GET /v1/audit`和`GET /v1/logs`只读。Logs仅返回服务端脱敏的level/module/event/message/request ID/time。无clients/sources/SourceInstance/entitlements/capacity-groups/recovery-items/Cost。

## 3. 传输与物理边界

Admin Bearer auth与Data Plane credential分离；生产使用TLS。中文Web UI同源调用Admin API，不直接读配置文件或Secret。

## 4. 数据、命令与 Schema

Provider区分cloud/local，保存OpenAI-compatible API root endpoint（适配器在其后使用`/models`、`/responses`、`/embeddings`）和Secret引用；view只返回`has_secret`。Deployment绑定backend model和能力。ServiceLevel用exact ID绑定一个或多个同等级deployment。删除有引用的资源返回409。

## 5. 状态机、顺序和时序

创建/更新先校验，再在单个SQLite事务中持久化资源版本与Audit；对模型可用性的影响由readyz反映。UI不得把配置保存成功显示成probe成功。PATCH是局部更新：省略字段保持原值，显式null只在Schema允许时清空；不得把未提交的partial write暴露为成功。

## 6. 错误、timeout、重试、幂等和恢复

使用400/401/403/404/409/412/502。每个可变资源的GET/创建/修改成功返回ETag；PATCH/DELETE必须带 `If-Match`。版本不匹配返回412且不写入；引用冲突返回409；权限不足返回403。管理mutation不提供custom idempotency状态机；UI在结果不明时先GET核对，不盲目重复Secret或删除操作。备份/restore和restart由运维runbook管理。

## 7. 并发、流控、容量与性能

使用ETag/If-Match/412防止覆盖并发编辑；列表统一使用 `limit`、opaque `cursor`、稳定snapshot和 `has_more/next_cursor`，cursor绑定principal及原filter。日志支持level/module/request ID过滤，store不可读返回503。不得创建外部capacity product。

## 8. 安全、身份、权限和隔离

Secret值只写不读、不回显、不进日志/audit/backup report。运行日志还禁止prompt、模型输出、reasoning、向量、Authorization和原始headers，message最长512字符。probe可能产生费用，必须`confirm_external_call=true`且由operator授权。reload/restart/delete属于状态变更操作。

## 9. 版本协商、兼容矩阵与弃用

Admin API随OpenAPI显式版本变更；无运行时兼容协商。旧访问控制、容量、恢复和调用方管理页面全部退出current authority。

## 10. Contract fixture、验证与证据

验证CRUD、If-Match缺失/过期、partial PATCH原子性、401/403/409/412、稳定分页、引用冲突、Secret不回显、cloud/local字段、exact model、probe确认、Usage store 503、Usage无Cost、审计脱敏、LogPage/禁入内容/日志store 503和旧path absence。

## 11. 未决项与双方批准

SQLite Operational Store已经选定为初始化后的唯一运行配置authority；JSON只允许空库首次bootstrap，之后不得覆盖Store。auth/TLS和backup的具体部署仍是LLMTier下游设计，不需要Slinky/Piko批准。
