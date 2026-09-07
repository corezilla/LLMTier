<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier Management Interface Control（V0.3 候选）

| 文档字段 | 值 |
|---|---|
| Document ID | llmtier-management-control |
| Document Version | 0.3.0-draft.1 |
| Status | Draft |
| Project | LLMTier |
| Authority | LLMTier |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | 2026-09-06 |
| Last Modified Date | 2026-09-07 |
| STD Version | 0.1.0-draft.17 |
| Template ID | interfaces.control |
| Template Conformance | tailored |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | corezilla/LLMTier |
| Canonical Path | docs/60_interfaces/llmtier-management-control.md |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本文是非破坏迁移候选。原 docs/contracts/llmtier-management-contract-v0.3.md 在 canonical
> promotion 前继续承担说明 authority；v0.3 OpenAPI 保持字段级机器 authority。

## 1. 接口目的、范围与双方 authority

Management API 与最小 Admin Web UI 由 LLMTier 提供并只供 LLMTier 管理员使用。它与 Piko Data
Plane credential、Slinky Observation credential 和普通 Client scope 分离。

LLMTier 拥有 Provider/Account/Deployment、Registry/Pool、Client/Source/Entitlement、capacity、
usage/audit/job/recovery 管理事实。该接口不取得 Piko/Slinky 业务 authority，也不能创建
Provider-direct Data Plane、Role selector 或跨 Service Level fallback。

## 2. 接口注册表

| Interface ID | Provider | Consumer | 类型 | Version | Status |
|---|---|---|---|---|---|
| LT-ADM-INVENTORY | LLMTier | LLMTier Admin | /tier/admin/v1 Provider/Account/Deployment CRUD | v0.3 | Candidate / not implemented |
| LT-ADM-REGISTRY | LLMTier | LLMTier Admin | Service Level/Pool/registry publish | v0.3 | Candidate / not implemented |
| LT-ADM-IDENTITY | LLMTier | LLMTier Admin | Client/Source/SourceInstance/Entitlement | v0.3 | Candidate / not implemented |
| LT-ADM-OPERATIONS | LLMTier | LLMTier Admin | capacity/usage/audit/jobs/recovery items | v0.3 | Candidate / not implemented |
| LT-ADM-UI | LLMTier | LLMTier Admin | Admin Web UI | v0.3 | Required candidate / not implemented |

完整 method/path catalog 只由 OpenAPI 定义；本文不复制 operation schema。

## 3. 传输与物理边界

统一 HTTP prefix 是 /tier/admin/v1。API 和 UI 必须独立鉴权、授权、审计；普通 Client、Piko 和
Slinky credential 不得访问 Management。所有 mutation 需要显式确认/typed result，不能绕过
concurrency 或 audit。

physical Provider credential 只在 LLMTier 管理边界内 write-only 保存；API、UI、浏览器响应、日志和
audit 均不得含 secret value。

## 4. 数据、命令与 Schema

request/response DTO、resource ID、typed default error、pagination 和 operation path 以 v0.3 OpenAPI
为唯一字段 authority。list 使用 limit/cursor/PageMeta.next_cursor。声明 If-None-Match 的 GET 同时
声明强 ETag 与 304；未声明的 GET 不声称缓存验证。

所有 create/action POST 要求 Idempotency-Key；资源 PATCH 同时要求 If-Match 和 body
expected_version。Account secret response 只返回状态、secret version 和 rotated timestamp；Client
credential 只在 create response 返回一次 plaintext，此后只返回 fingerprint/status。

## 5. 状态机、顺序和时序

discovery、probe、Registry publish 和 recovery action 返回 202 AdminJob，并以
/tier/admin/v1/jobs/{job_id} 跟踪。UI 呈现 pending/active/failed 与最近 audit event，不自行推导成功。

Registry draft、published version 和 diff 必须可见；publish 后同一 Registry 驱动 Data Plane Models、
Observation、admission 和 compatibility manifest。版本冲突返回 409/412 version_conflict。

## 6. 错误、timeout、重试、幂等和恢复

typed error、retryability 和 operation status 由 OpenAPI 定义。POST idempotency 防止重复 mutation；
PATCH optimistic concurrency 防止 lost update。客户端不得把 timeout 当作 mutation 未发生，必须查询
job/resource/audit 结果。

Recovery action 明确提交 redispatch=false，只允许 reconcile 或 cancel；不得绕过 Invocation ledger、
idempotency safety 或 UnknownOutcome manual reconcile。

## 7. 并发、流控、容量与性能

所有 mutation 串接 resource version/ETag。capacity/usage 支持 scoped 与 aggregate view；aggregate
dimension 可为 null，Unknown/Partial usage 的 count/token 保持 null，不能补零。

当前没有 production Admin API/UI latency、throughput 或 operator-load evidence；这些不由文档迁移
推导。

## 8. 安全、身份、权限和隔离

每项 mutation 必须有 authenticated admin、authorization decision、audit record 和 concurrency check。
secret create/rotate 只写不读；list/detail/UI/log/audit 不返回明文、密文或可逆导出。

Client/Source/SourceInstance/Entitlement 管理不能扩大 Data Plane recovery namespace。跨 Client 数据、
Provider secret 和 physical mapping 不能出现在 Observation/Data Plane。

## 9. 版本协商、兼容矩阵与弃用

Service Level ID exact、大小写敏感。Contract/SLO 不变时可替换同等级 backend；破坏兼容性的变化使用
新 ID 或 API major。旧 /health、/runtime、/stats 和 CLI 不构成 v0.3 Management compatibility
承诺，也不能作为 fallback。

v0.3 compatibility manifest 当前 contract_status=candidate、runtime_activation=false。

## 10. Contract fixture、验证与证据

- 字段 authority：docs/contracts/openapi/llmtier-v0.3.openapi.json。
- fixtures：observation-management-openapi-fixtures、authorization-scope-fixtures、
  capacity-semantic-negative-fixtures 和 metadata-utf8-byte-fixtures。
- 静态/语义验证：tests/test_contract_semantics_v03.py、tests/test_contract_consistency.py。
- production evidence：API/UI positive/deny/secret/concurrency、Registry publish、provider probe、
  fairness/audit 和 recovery safety 尚未完成，状态为 BLOCKED/NOT_RUN。

## 11. 未决项与双方批准

LLMTier owner 必须审查全部 Management 和安全事实。persistence/HA、Admin UI 技术栈、deployment、
backup/RPO/RTO 仍是 Open Gate，应以独立 ADR/operations cohort 处理。进入 promotion 前需要 immutable
project commit 和终局 decision；本文不请求状态升级或 Runtime Activation。
