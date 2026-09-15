<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Requirements Specification

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-v0.3-requirements` |
| Document Version | `0.3.1-draft.1` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | LLMTier |
| Approver | LLMTier |
| Approval Date | `2026-09-07` |
| Created Date | `2026-09-07` |
| Last Modified Date | `2026-09-15` |
| Template Version | `0.1.0` |
| Template ID | `requirements.specification` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/10_requirements/llmtier-v0.3-requirements.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. 目的、范围与来源

本文从 LLMTier V0.3 原设计、三份接口说明、OpenAPI、compatibility manifest、fixtures 与 QA ledger
提取本服务自身必须满足的需求。Slinky 的 Project/Plan/IR 和 Piko 的 Agent Runtime/adapter 需求仅作为
外部约束输入；本文不取得或复制其 authority。

范围包含 Responses/Embeddings non-stream、Models/recovery、Observation、Management/Admin UI、Registry、
admission/capacity、idempotency/retention、安全、可观测性与 activation gate。V0.4 Chat/SSE/streaming、
未批准的 persistence/HA/topology 选择不在 V0.3 requirement baseline。

## 2. 系统/产品上下文

LLMTier 是单一独立模型服务。Piko 是 Agent Runtime consumer，Slinky 是只读 Observation consumer，
Memory/Knowledge Client 是 Embeddings consumer，管理员使用 Management API/UI。唯一 IR-backed inference
链路是 `Runtime -> Piko -> LLMTier -> Provider/Local Deployment`。LLMTier 不执行 Agent tool loop，
不组合 Project/Plan/IR，也不向 consumer 暴露 Provider credential 或 physical routing。

生命周期覆盖配置、Registry publish、启动、admission/dispatch、recovery、Observation、管理、升级、回滚
与退役。当前仅冻结 contract/design candidate；production implementation 和 Runtime Activation 尚未完成。

服务源码、安装制品、配置、Secret、状态与运维入口全部属于 LLMTier。当前 repo 路径分别为 `src/`、
`config/settings.json`、`config/secrets/`、`state/` 和 `interfaces/`；外部 consumer 不直接 import 本仓库源码，
不读写这些目录，也不控制服务进程。

## 3. 假设、约束与术语

- 已确认：V0.3 Scope B、exact-case Service Level、唯一 OpenAPI、M2-C `W=168h`/`M=24h`、
  `concurrent_invocation` 与 activation=false。
- 外部约束：Piko 负责 pinned adapter 与 recovery obligation；Slinky 负责 Seat projection；consumer 的内部
  路由策略不改变 LLMTier API boundary。
- 待验证：durable store、production routes、provider SLO、Admin UI、isolation/fairness、HA/RPO/RTO。
- Service Level ID 是 catalog ID，不是 Role；fallback 仅可在 LLMTier 内同一 Service Level 的 approved
  backend set 内发生，禁止跨等级替换。
- `PASS` 只表示指定 evidence 层；static PASS 不等于 runtime 或 acceptance PASS。

## 4. 功能需求

| Requirement ID | Shall statement | 来源 | Priority | Verification | Status |
|---|---|---|---|---|---|
| LT-FUN-001 | LLMTier shall 仅提供 V0.3 Scope B 的 Responses/Embeddings non-stream、Models 与 recovery surface，并对 Chat/SSE/streaming fail closed | design §1/3；Piko control | P0 | CT-DP-001 | Candidate/static PASS；runtime BLOCKED |
| LT-FUN-002 | LLMTier shall 使用单一 Service Level Registry 驱动 Models、Observation、admission、capacity membership 与 manifest | design §5 | P0 | CT-REG-001 | Candidate/static PASS；runtime BLOCKED |
| LT-FUN-003 | LLMTier shall 先持久化 idempotency decision；仅 admission 成功才原子授予 Seat 并创建 Invocation/dispatch intent，且在 backend dispatch 前形成 recovery obligation | design §6/10；Piko control | P0 | CT-ADM-001/CT-REC-001/002 | Candidate/static PASS；runtime BLOCKED |
| LT-FUN-004 | LLMTier shall 提供 Client-scoped、只读 Observation，并表达 readiness、capacity、Invocation、usage 与 compatibility | Slinky control | P0 | CT-OBS-001 | Static PASS；Slinky E2E BLOCKED |
| LT-FUN-005 | LLMTier shall 通过 `/tier/admin/v1` 与最小 Admin UI 管理 Registry、Provider、Client/Source、capacity、Job、audit 与 recovery | Management control | P0 | CT-MGT-001 | Static PASS；implementation BLOCKED |
| LT-FUN-006 | LLMTier shall 对 UnknownOutcome 只允许 manual reconcile，不自动 redispatch | Piko/Management controls | P0 | CT-REC-002 | Fixture PASS；runtime BLOCKED |
| LT-FUN-007 | LLMTier shall 作为独立 Python 服务提供唯一 service/operator entry point，并将现有 legacy API 与未激活 V0.3 API 明确区分 | system design §5/7；operations | P1 | CT-PKG-001/CT-OPS-001 | Current CLI PASS；V0.3 runtime BLOCKED |
| LT-FUN-008 | V0.3 Responses non-stream shall 接受多轮 message、声明 function tools、返回 function_call，并接受相同 call_id 的 function_call_output；LLMTier shall 不执行工具 | Slinky L3；Piko control；design §11.2 | P0 | CT-DP-001/Piko capture | Schema candidate PASS；consumer/runtime BLOCKED |

## 5. 接口需求

| Requirement ID | Shall statement | Authority | Verification | Status |
|---|---|---|---|---|
| LT-INT-001 | 所有 `service_level_id` shall exact、大小写敏感；禁止 lowercase、alias、Role selector 与 cross-level fallback | OpenAPI + manifest | CT-ID-001 | Static PASS |
| LT-INT-002 | Management prefix shall 仅为 `/tier/admin/v1`；canonical headers shall 为 `X-Tier-Client-Request-ID` 与 `X-Tier-Invocation-ID` | OpenAPI | CT-MGT-001/authority scan | Static PASS |
| LT-INT-003 | OpenAPI v0.3 shall 是字段级唯一机器接口 authority；Markdown 不得形成第二 Schema | OpenAPI + contract spec | CT-MIG-001 | Static PASS |
| LT-INT-004 | active `202`、terminal response/error、Location、Invocation ID 与 Retry-After shall 符合 recovery contract | OpenAPI | CT-REC-001 | Fixture PASS；runtime BLOCKED |
| LT-INT-005 | Observation list/detail shall 支持冻结的 filter、pagination、ETag/304 与 typed errors | OpenAPI | CT-OBS-001 | Static PASS；runtime BLOCKED |

## 6. 性能与容量需求

| Requirement ID | Shall statement | Verification | Status |
|---|---|---|---|
| LT-CAP-001 | committed capacity shall 以 `concurrent_invocation` 计量，并同时满足 direct、全部 shared/overlapping group、Client quota、readiness 与 `valid_until` | CT-OBS-001/CT-PERF-001 | Fixture PASS；production BLOCKED |
| LT-CAP-002 | unknown quota、过期 snapshot 或不一致 membership shall 阻止新增 committed Seat，不得折算为零或可用 | CT-OBS-001 | Fixture PASS；runtime BLOCKED |
| LT-CAP-003 | pre-admission 不满足 shall 返回 429 typed rejection，Seat/Invocation/dispatch 均为零；同 key/digest 只可按 decision expiry 重新 admission | CT-ADM-001 | Candidate amendment；runtime BLOCKED |
| LT-PERF-001 | production SLO shall 固定 provider/model/config、拓扑、工作负载、样本和统计口径后测量 | CT-PERF-001 | BLOCKED：baseline 未批准 |

## 7. 安全、可靠性与合规需求

| Requirement ID | Shall statement | Verification | Status |
|---|---|---|---|
| LT-SEC-001 | authenticated Client 与 canonical Source shall 构成授权/恢复隔离边界，禁止跨 Client/Source 数据泄露 | CT-AUTH-001/CT-SEC-001 | Static PASS；runtime BLOCKED |
| LT-SEC-002 | Provider credential shall 只写不读，且不得进入 consumer DTO、日志或 evidence | CT-MGT-001/CT-SEC-001 | Static shape PASS；runtime BLOCKED |
| LT-REL-001 | terminal digest/tombstone、Invocation view 与 canonical Response shall 在 terminal 后至少保留 168h；自动恢复 deadline 为 24h | CT-REC-002 | Fixture PASS；durability BLOCKED |
| LT-REL-002 | 不支持、未知、未授权、过期或未激活的输入 shall fail closed，不得 silent compatibility expansion | negative cases | Static PASS；runtime BLOCKED |

## 8. 运维、诊断与可观测性需求

| Requirement ID | Shall statement | Verification | Status |
|---|---|---|---|
| LT-OPS-001 | readiness、usage、Invocation、audit 和 recovery evidence shall 可关联 Client/Source/Service Level 且不泄露 secret | CT-OBS-001/CT-SEC-001 | Static PASS；runtime BLOCKED |
| LT-OPS-002 | compatibility manifest shall 区分 policy selection 与 Runtime Activation，production Gate 未齐时保持 false | activation tests | Static PASS |
| LT-OPS-003 | Registry/contract/config 变化 shall 有 version、ETag、effective time、审计与回滚 evidence | CT-REG-001 | Design fixed；runtime BLOCKED |

## 9. 制造、部署、维护与退役需求

- 硬件制造不适用。
- LT-DEP-001：部署 shall 保持 LLMTier 独立配置 authority，不回读 Slinky config，也不创建 Provider-direct、
  Role routing、跨等级 fallback 或第二 API path。
- LT-DEP-003：默认配置 shall 为 `config/settings.json`，默认运行状态 shall 位于 `state/`；只允许现有
  `LLMTIER_CONFIG`、`--settings` 和 `LLMTIER_STATE_DIR` 覆盖机制，不得为旧 workspace 建兼容副本。
- LT-DEP-004：安装后的 entry points shall 为 `llm-tier` 与 `llm-tier-cli`；源码 checkout 的等价入口 shall
  为 `PYTHONPATH=src python3 -m tier_service` 与 `PYTHONPATH=src python3 -m cli`。
- LT-DEP-002：production release/rollback/backup/recovery/retirement shall 在 C4 operations 文档中引用真实
  topology、artifact、migration 与 evidence；未决定项保持 Open Gate。
- 当前两项均为 design constraint；production procedure/evidence 为 BLOCKED。

## 10. 验收与 traceability

每条 requirement 必须映射到设计/接口、实现位置、case ID 和实际 evidence；详见
`docs/10_requirements/llmtier-v0.3-traceability.md`。Migration Review 只验结构与来源。Runtime Activation
要求全部 P0 production-required case PASS、manifest/route 一致、consumer evidence 完整，并由独立 authority
批准。Document Review、Document Status、canonical promotion、RAG publication 与 Runtime Activation 不互相推导。

## 11. 未决问题与变更历史

未决：production persistence/HA/RPO/RTO、Admin UI 技术栈、provider measured SLO、真实多 Client 隔离、
Piko/Slinky/Embeddings consumer evidence。它们不阻止 requirements migration candidate，但阻止相关
Document Status/operations conclusion 或 Runtime Activation。

- 2026-09-07：C3 首版从现有 V0.3 design/contract/QA authority 提取；未新增业务语义。
- 2026-09-09：按独立项目现状补齐 repo path、配置/状态 authority 与 CLI 使用约束；机器契约不变。
