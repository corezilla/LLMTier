<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Release and Operations

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-v0.3-release-and-operations` |
| Document Version | `0.3.0` |
| Status | `Approved` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | LLMTier |
| Approver | LLMTier |
| Approval Date | `2026-09-07` |
| Created Date | `2026-09-07` |
| Last Modified Date | `2026-09-08` |
| STD Version | `0.1.0-draft.18` |
| Template ID | `operations.release` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/80_operations/llmtier-v0.3-release-and-operations.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Release scope、版本与兼容性

本文迁移当前仓库可确认的 build/start/stop/health、配置、安全、回滚和 acceptance 边界，并显式列出
V0.3 production Open Gate。它是 operations candidate，不是 release approval 或 runtime runbook。

- 当前 Python package 版本是 `pyproject.toml` 的 `0.1.0`；不能把它称为 V0.3 production release。
- V0.3 contract/design 仍为 candidate，`overall.runtime_activation=false`。
- 兼容性唯一机器 authority 是 `interfaces/compatibility/compatibility-manifest-v0.3.json`；接口字段 authority 是
  OpenAPI v0.3。本文不新增 compatibility path。
- V0.3 Scope B、exact Service Level、canonical headers/path、M2-C 与 no cross-level fallback 均不可由
  release 操作放宽。

## 2. 构建、制品、SBOM/BOM 与来源证明

当前 build source 是 Git commit、`pyproject.toml`、`src/llm_tier/` 和 Python `>=3.11`；test extra 为
`jsonschema>=4.23,<5`。项目使用 setuptools build backend，console scripts 为 `llm-tier` 与
`llm-tier-cli`。

每个可发布 artifact 必须记录 commit、Python/build backend 版本、dependency lock/SBOM、构建命令、
artifact SHA-256 与签署结果。当前仓库没有已批准的 V0.3 wheel/container/SBOM 或 production provenance，
因此 production artifact 状态为 NOT_AVAILABLE/BLOCKED。软件项目 BOM 只指依赖/SBOM；硬件 BOM 不适用。

## 3. 部署/安装/烧录/装配步骤

当前可验证的开发入口：

1. 在固定 commit 的隔离 Python 环境安装本项目及需要的 test extra；
2. 运行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m llm_tier --help`；
3. 运行全部 tests 与 contract/STD validators；
4. 仅在独立环境授权后，使用明确 `--host`、`--port`、`--settings` 启动 `python3 -m llm_tier`；
5. SIGINT/SIGTERM 触发当前进程的 bounded graceful shutdown。

上述入口只证明当前 baseline CLI 形状。旧 `settings.json`、`/health`、`/runtime`、`/stats` 等实现不得被
误称为 V0.3 Data Plane/Observation/Management 已接线。production service manager、container image、
network/TLS、filesystem owner、resource limit 和 multi-instance topology 均是 Open Gate。无烧录/装配步骤。

## 4. 配置、Secret、校准数据与环境

- 配置必须属于 LLMTier，不回读 Slinky config；每个环境记录配置 version/digest 和 non-secret diff。
- Provider credential 只写不读，不进入日志、DTO、backup 明文、CLI output 或 evidence。
- 环境至少区分 development/test/staging/production；禁止用未激活 endpoint 或旧 alias 代替目标 surface。
- `TIER_SERVER_URL` 只是当前 client 连接位置，不是 authority、routing policy 或 compatibility selector。
- production config schema、secret store、rotation、encryption、retention 和 migration 尚未批准，状态 BLOCKED。

## 5. Preflight、Bring-up 与健康检查

Preflight 必须固定 commit/artifact/config digest，验证 Python/dependencies、port/filesystem 权限、secret
availability、Registry/manifest version、durable store、required Service Levels、consumer identity 和
`runtime_activation`。Bring-up 先阻断流量，完成 schema/config check、store recovery、Registry/admission
consistency、Management/Observation/Data Plane probes 后才可进入独立 activation Gate。

当前 `/health`、`/runtime`、`/stats` 可用于 legacy baseline 诊断，但不是 V0.3 readiness contract。
V0.3 health/readiness 的 machine authority 是 OpenAPI；production route evidence 未提供，故 bring-up 为
NOT_RUN/BLOCKED。

## 6. 升级、迁移、回滚和恢复

- upgrade input：immutable artifact、config/schema migration、compatibility assessment、backup/restore test、
  consumer matrix 和 rollback trigger。
- rollout 必须保持单一 Registry/ledger 与唯一 `Runtime -> Piko -> LLMTier` path；不运行旧/新并行
  inference 或 recovery path。
- rollback 只能回到明确兼容的 artifact/config/data state；不能通过 alias、Role selector、跨等级 fallback
  或缩短 retention 绕过问题。
- in-flight Invocation、idempotency/dispatch intent、canonical response 与 tombstone 必须按 M2-C 恢复。
- 当前没有已批准的 database schema、backup format、HA、RPO/RTO、blue-green/canary 或 disaster recovery
  procedure，相关步骤保持 Open Gate，不能执行 production migration。

## 7. 操作、监控、告警与 SLO

运行时应监控 readiness、request/error、queue/admission、capacity/quota、provider health、Invocation state、
recovery、usage、audit、store health 与 secret access denial，并按 Client/Source/Service Level 隔离。告警不得
泄露 prompt/output/credential。

当前没有 production latency/throughput/error budget 或 provider measured SLO。开发日志和 mock/static
fixture 不能作为 SLO evidence。SLO、告警阈值、on-call owner、dashboard 和 escalation 在 production
baseline 冻结前为 BLOCKED。

## 8. 故障诊断、维护与更换

诊断顺序：固定 incident/commit/config；检查 readiness/store/Registry；按 Invocation ID 与 canonical
Client/Source 查询；区分 validation、auth、capacity、provider、store、UnknownOutcome；保留脱敏 evidence。
UnknownOutcome 只允许 manual reconcile，不盲重派。维护不得直接编辑持久化状态或跨 Client 查看数据。

当前可替换对象仅是同一 Service Level 的 approved backend/deployment；不得换为其他 Service Level。
正式 maintenance window、data repair、provider replacement 和 operator authorization 尚未定义。

## 9. 数据保留、备份、审计与安全

- active record 保留至 terminal；terminal digest/tombstone、Invocation view 与 canonical Response 至少 168h；
  自动恢复 deadline 24h，clock skew 上限 5m。
- prompt/output privacy retention 可独立配置，但不得破坏上述 recovery 下限。
- backup 必须加密、最小权限、可审计，并验证 restore 后 idempotency/Invocation/Registry 一致性。
- Secret 不得可读或出现在 backup report；audit 必须记录管理 mutation、publish/rollback 和 recovery action。
- 当前 backup/restore、key management、retention enforcement 与 security run evidence 均为 BLOCKED。

## 10. Acceptance、交接与退役

production acceptance 至少要求：immutable artifact/provenance、全部 P0 contract/runtime/security/recovery/
capacity cases PASS、consumer captures、operations owner、backup/restore、rollback rehearsal、SLO/alert、
single-authority scan、manifest 与 routes 一致，以及独立 Runtime Activation approval。

交接包包含 runbook、artifact/config/schema、contacts、dashboard/alert、known issues、backup/restore、rollback、
evidence 与 decision。退役必须先停止新 admission，收敛 in-flight，满足 retention/export/delete policy，撤销
credential，移除 route/consumer config，并验证不存在旧 embedded/Provider-direct path。当前 acceptance、
handoff 与 retirement 均 NOT_RUN/BLOCKED；本文不授权执行。
