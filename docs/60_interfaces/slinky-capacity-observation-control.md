<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier–Slinky Capacity/Observation Interface Control（V0.3 候选）

| 文档字段 | 值 |
|---|---|
| Document ID | llmtier-slinky-capacity-observation-control |
| Document Version | 0.3.0-draft.1 |
| Status | Draft |
| Project | LLMTier |
| Authority | LLMTier |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | 2026-09-07 |
| Last Modified Date | 2026-09-07 |
| STD Version | 0.1.0-draft.18 |
| Template ID | interfaces.control |
| Template Conformance | tailored |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | corezilla/LLMTier |
| Canonical Path | docs/60_interfaces/slinky-capacity-observation-control.md |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本文是非破坏迁移候选。原 docs/contracts/slinky-capacity-observation-contract-v0.3.md 在
> canonical promotion 前继续承担说明 authority；v0.3 OpenAPI 保持字段级机器 authority。

## 1. 接口目的、范围与双方 authority

Slinky 负责 Project、Plan、IR 和把 LLMTier Observation 投影为 Forecast/Risk/Action；LLMTier 负责
模型服务、admission、routing、Invocation ledger、Service Level Registry 和 Client-scoped
Observation。唯一 inference 路径仍是 Runtime → Piko → LLMTier。

Slinky 不取得 Provider credential、physical routing、Management authority，也不绕过 Piko 执行
inference。Piko 不消费 Observation 分面。

## 2. 接口注册表

| Interface ID | Provider | Consumer | 类型 | Version | Status |
|---|---|---|---|---|---|
| LT-SLK-READINESS | LLMTier | Slinky | GET /tier/v1/readiness | v0.3 | Candidate / not active |
| LT-SLK-SERVICE-LEVELS | LLMTier | Slinky | GET /tier/v1/service-levels 与 detail | v0.3 | Candidate / not active |
| LT-SLK-CAPACITY | LLMTier | Slinky | GET /tier/v1/capacity/snapshots/current | v0.3 | Candidate / not active |
| LT-SLK-INVOCATIONS | LLMTier | Slinky | GET /tier/v1/invocations 与 detail | v0.3 | Candidate / not active |
| LT-SLK-USAGE | LLMTier | Slinky | GET /tier/v1/usage/summary | v0.3 | Candidate / not active |
| LT-SLK-COMPATIBILITY | LLMTier | Slinky | GET /tier/v1/compatibility | v0.3 | Candidate / not active |

## 3. 传输与物理边界

接口是 authenticated、Client-scoped 的只读 HTTP Observation boundary。query/header、cursor、
ETag/If-None-Match/304、response DTO 和 typed error 由 v0.3 OpenAPI 定义。

physical Provider、account、pool、deployment 和 Management mutation 不跨该边界。Slinky adapter
不能根据缺失字段猜测，也不能将 Observation filter 变成新的权限或 recovery namespace。

## 4. 数据、命令与 Schema

同一 authenticated Client 可在已授权范围内查询/聚合多个 Source。source_id 和
source_instance_id 只是 filter/grouping dimension；Data Plane recovery 仍严格使用 authenticated
client_id + canonical source_id。source_instance_id 只用于 correlation、observation 和 audit。

Readiness 显示 Ready/Degraded/NotReady、Tier instance/version、Observation readiness、visible
Service Levels、snapshot version 与 refresh window。Service Level DTO 描述 kind、capabilities、
context、Structured Output、Tool Calling、modalities/limits 和 compatibility ref。

## 5. 状态机、顺序和时序

Registry publish 原子更新 catalog/version/ETag/effective_at/valid_until。Models、Observation、
admission、capacity membership 和 compatibility manifest 必须来自同一个 Registry，但每个 endpoint
的 ETag 只校验其自身 representation。

CapacitySnapshot 失效时关联 TierServiceSeat/IRBackingSeat 立即 Invalidated，不得用于新 dispatch；
Slinky 通知 Plan 更新 Forecast/Risk/Action。已被 LLMTier admission 的 in-flight Invocation 不撤销、
不跨 Stage rollback；后续 Work 必须重新投影和 admission。

## 6. 错误、timeout、重试、幂等和恢复

字段或 Source identity 不满足时返回 typed source_error 或 contract_mismatch，adapter 不得猜测。
跨 Client、未授权 Source 或 hidden resource 必须 fail closed。

Observation invocation view 与 Data Plane recovery extension 投影自同一 ledger，不得建立第二状态机。
M2-C 固定 W=168h、M=24h、D=24h；digest/tombstone、terminal view 与可恢复 canonical Response 的
最短窗口均为 168h。短于冻结下限的配置无效并阻断 activation。

## 7. 并发、流控、容量与性能

唯一容量单位是 concurrent_invocation。committed Seat 同时受 direct capacity、全部
shared/overlapping Capacity Group、Client quota、readiness/blocking reason 和 valid_until 约束；
burst 不计入 committed Seat，request_quota_remaining=null 以 client_quota_unknown 阻断新投影。

semantic validator 必须检查 ID 唯一、exact-case Registry membership、双向 group membership、
available <= committed、时间顺序和所有 fail-closed blocking reason。Seat 不等于 token/s、Agent Slot
或性能保证；当前没有 production capacity/fairness evidence。

## 8. 安全、身份、权限和隔离

所有响应按 credential scope 过滤。Observation 的 multi-source aggregate 不能扩大 Data Plane
recovery scope，不能暴露 secret、physical credential、Provider payload 或其他 Client 数据。

Usage 的 unknown/partial count/token 保持 null，不得补零。日志、metrics 和 audit 必须保持
Client/Source 隔离。

## 9. 版本协商、兼容矩阵与弃用

service_level_id exact、大小写敏感；禁止 lowercasing、alias、Role selector 和跨等级 fallback。
physical mapping 在 Contract/SLO 不变时可替换；破坏兼容性的语义变化使用新 ID 或 API major。

compatibility endpoint 按 method/path 暴露 supported/unsupported fields、streaming、Schema/error
version、SDK matrix 和 effective_at。v0.3 当前是 candidate，runtime_activation=false。

## 10. Contract fixture、验证与证据

- 字段 authority：docs/contracts/openapi/llmtier-v0.3.openapi.json。
- activation 状态：docs/contracts/compatibility-manifest-v0.3.json。
- fixtures：capacity-semantic-negative-fixtures、observation-management-openapi-fixtures、
  authorization-scope-fixtures、metadata-utf8-byte-fixtures。
- 静态/语义验证：tests/test_contract_semantics_v03.py、tests/test_contract_consistency.py。
- production evidence：真实 endpoints、Registry/admission wiring、公平性、invalidation notification 和
  Slinky E2E 尚未完成，状态为 BLOCKED/NOT_RUN。

## 11. 未决项与双方批准

本候选需要 LLMTier owner 审核提供方和安全事实；Slinky reviewer 只审核其 Observation consumer
boundary 与 Seat 投影义务。进入 promotion 前需要 immutable project commit 和终局 decision；本文
不请求状态升级或 Runtime Activation，旧 v0.3 文档继续保留 residual authority。
