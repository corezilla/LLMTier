<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Release and Operations

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-v0.3-release-and-operations` |
| Document Version | `0.3.1-draft.3` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | LLMTier |
| Approver | LLMTier |
| Approval Date | `2026-09-07` |
| Created Date | `2026-09-07` |
| Last Modified Date | `2026-09-17` |
| Template Version | `0.1.0` |
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

本文定义独立 LLMTier 仓库当前可确认的 build/start/stop/health、配置、安全、回滚和 acceptance 边界，
并显式列出 V0.3 production Open Gate。它包含目标单节点runbook，但不是release approval、已执行证据或
production部署授权。

- 当前 Python package 版本是 `pyproject.toml` 的 `0.1.0`；不能把它称为 V0.3 production release。
- V0.3 contract/design 仍为 candidate，`overall.runtime_activation=false`。
- 兼容性唯一机器 authority 是 `interfaces/compatibility/compatibility-manifest-v0.3.json`；接口字段 authority 是
  OpenAPI v0.3。本文不新增 compatibility path。
- V0.3 simplified candidate 保留 exact Service Level 与 no cross-level fallback；不再对外承诺 M2-C、
  custom Invocation/idempotency recovery、capacity/Seat、Cost 或专用 compatibility negotiation。

## 2. 构建、制品、SBOM/BOM 与来源证明

当前 build source 是 Git commit、`pyproject.toml`、`src/` 和 Python `>=3.11`；test extra 为
`jsonschema>=4.23,<5`。项目使用 setuptools build backend，console scripts 为 `llm-tier` 与
`llm-tier-cli`。

每个可发布 artifact 必须记录 commit、Python/build backend 版本、dependency lock/SBOM、构建命令、
artifact SHA-256 与签署结果。当前仓库没有已批准的 V0.3 wheel/container/SBOM 或 production provenance，
因此 production artifact 状态为 NOT_AVAILABLE/BLOCKED。软件项目 BOM 只指依赖/SBOM；硬件 BOM 不适用。

## 3. 部署/安装/烧录/装配步骤

当前可验证的开发/本地运行入口：

1. 在固定 commit 的隔离 Python 3.11+ 环境运行 `python3 -m pip install -e .`；
2. 安装后以 `llm-tier --host 127.0.0.1 --port 8765 --settings config/settings.json` 启动；
3. 以 `llm-tier-cli --server-url http://127.0.0.1:8765 health` 执行 operator health 检查；
4. 未安装 package 时使用 `PYTHONPATH=src python3 -m tier_service` 和 `PYTHONPATH=src python3 -m cli`；
5. 运行全部 tests 与 contract/STD validators；SIGINT/SIGTERM 触发 bounded graceful shutdown。

上述入口只证明当前 baseline CLI 形状。现有 `/health`、`/runtime`、`/stats` 等实现不得被
误称为 V0.3 Data Plane/Observation/Management 已接线。V0.3 production参考拓扑固定为单节点Linux：
TLS/SSO反向代理监听外部地址，LLMTier systemd service只绑定loopback，独立非登录用户运行，SQLite/日志/备份
目录分别最小授权；不设计多实例或共享SQLite。container image仍不是首版必要条件。无烧录/装配步骤。

## 4. 配置、Secret、校准数据与环境

- `config/settings.json`、显式 `--settings` 或 `LLMTIER_CONFIG` 只允许在空SQLite首次启动时提供一次性bootstrap输入；初始化成功后SQLite Operational Store是唯一运行配置authority，后续启动不得自动重导、覆盖或双写JSON。配置属于 LLMTier，不回读 Slinky config。
- 文件型 Secret 位于 Git-ignored 的 `config/secrets/`，相对路径从 repo root 解析；目录和文件使用
  owner-only 权限，验证只记录存在性/摘要，不读取或输出内容。
- 默认运行状态、统计和 trace 位于 Git-ignored 的 `state/`；`LLMTIER_STATE_DIR` 可为部署选择唯一替代目录，
  server/client 同步解析该目录；既有 `TIER_TRACE_STATE_PATH` 只用于显式选择单个 debug-state 文件。
- Provider credential 只写不读，不进入日志、DTO、backup 明文、CLI output 或 evidence。
- 环境至少区分 development/test/staging/production；禁止用未激活 endpoint 或旧 alias 代替目标 surface。
- `TIER_SERVER_URL` 只是当前 client 连接位置，不是 authority、routing policy 或 compatibility selector。
- 当前 server 只接受 localhost、loopback、RFC1918 或 IPv6 ULA bind/origin；credential 不得嵌入 URL。
- production Secret backend、credential rotation、磁盘/备份加密和migration必须按下述单节点基线实现并留证；
  在证据完成前状态仍为BLOCKED，而不是设计未定义。

## 5. Preflight、Bring-up 与健康检查

Preflight 必须固定 commit/artifact/config digest，验证 Python/dependencies、port/filesystem 权限、secret
availability、model registry、Usage/Audit store、required logical models、credential 和 `runtime_activation`。
Bring-up 先阻断流量，完成 schema/config check、store recovery、model availability、Admin/Data Plane checks
后才可进入独立 activation Gate。

当前 `/health`、`/runtime`、`/stats` 可用于 legacy baseline 诊断，但不是 V0.3 readiness contract。
V0.3 health/readiness 的 machine authority 是 OpenAPI；production route evidence 未提供，故 bring-up 为
NOT_RUN/BLOCKED。

当前 operator CLI 还提供 `debug`、`invoke`、`reset`、`reload` 和 `probe`。这些命令只覆盖现有实现；
不得把它们当成 `/tier/admin/v1`、`/tier/v1` 或 `/v1` V0.3 surface 的替代入口。

## 6. 升级、迁移、回滚和恢复

- upgrade input：immutable artifact、config/schema migration、compatibility assessment、backup/restore test、
  consumer matrix 和 rollback trigger。
- rollout 必须保持单一 model registry 与唯一 `Runtime -> Piko -> LLMTier` inference path；不运行 legacy
  `/call` 与目标 `/v1` 的consumer fallback。
- rollback 只能回到明确兼容的 artifact/config/data state；不能通过 alias、Role selector、跨等级 fallback
  或缩短 retention 绕过问题。
- Piko Agent session/任务恢复不属于 LLMTier；LLMTier只恢复自身配置、Usage/Audit store和服务进程。
- SQLite schema与迁移边界由Runtime ISD定义；backup format、HA、RPO/RTO、blue-green/canary 或 disaster recovery
  procedure仍是 Open Gate，不能执行 production migration。

## 7. 操作、监控、告警与 SLO

运行时应监控 health/readiness、request/error、内部 queue/concurrency、provider health、token usage、audit、
store health 与 secret access denial。内部资源指标不形成外部 Seat/capacity contract；告警不得泄露
prompt/output/credential。

当前没有 production latency/throughput/error budget 或 provider measured SLO。开发日志和 mock/static
fixture 不能作为 SLO evidence。首版内部保护固定为每deployment并发1、每level FIFO 32、排队30秒、连接/首字节
30秒、SSE空闲60秒；这些是安全上限而非SLO。on-call owner、测量后的告警阈值和dashboard在activation前仍为BLOCKED。

## 8. 故障诊断、维护与更换

诊断顺序：固定 incident/commit/config；检查 health/readiness/store/model registry；按 request ID 与标准 trace
查询；区分 validation、auth、rate-limit、provider、store；保留脱敏 evidence。网络结果不明由调用方按其任务
策略处理，LLMTier不提供custom Invocation reconcile。维护不得直接编辑持久化状态。

当前可替换对象仅是同一 Service Level 的 approved backend/deployment；不得换为其他 Service Level。
正式 maintenance window、data repair、provider replacement 和 operator authorization 尚未定义。

## 9. 数据保留、备份、审计与安全

- QuerySnapshot TTL固定15分钟；后台每小时清理过期snapshot，清理前不得删除其引用的Usage版本。
- Usage head及其版本保留30天，Audit保留90天；unknown token不能在过期或聚合时变成0。到期删除按UTC日界执行并写Audit。
- prompt/output默认不持久化；若因明确诊断需求保存，必须有独立批准和retention。
- backup 必须加密、最小权限、可审计，并验证restore后配置、model registry和Usage/Audit一致性。
- Secret 不得可读或出现在 backup report；audit 必须记录管理 mutation、publish/rollback 和 recovery action。
- SQLite使用在线backup API每日生成一次加密备份，保留7份每日和4份每周副本；备份落到与活动state不同的受控卷，
  Secret值不进入SQLite或备份。首版目标RPO 24小时、RTO 4小时；每次release前必须在隔离目录恢复最近备份，
  执行integrity check、schema version、Registry/Usage/Audit抽样和readyz检查。key management、retention enforcement、
  restore rehearsal与security run evidence完成前仍为BLOCKED。

## 10. 单节点启动、重启与恢复Runbook

1. operator固定artifact SHA、bootstrap/store路径、代理配置和Secret reference；先验证磁盘权限与最近备份。
2. systemd以专用用户启动LLMTier，`Restart=on-failure`且限制重启速率；进程只监听loopback，外部TLS由反向代理终止。
3. `/healthz`仅证明进程和事件循环；`/readyz`必须同时通过SQLite integrity、Registry、所需deployment配置与adapter检查。
4. 普通重启先在代理摘流，等待最多60秒完成已dispatch请求；超时终止后由调用方处理连接结果，LLMTier不恢复调用。
5. 恢复顺序为停止服务→保全故障state→在新目录恢复加密备份→离线integrity/migration检查→只读启动→
   Registry/Usage/Audit抽样→受授权smoke probe→代理重新加流。环境恢复不等于Piko任务成功。
6. 任何真实provider probe、credential rotation、restore、migration和重新加流都需operator显式批准并写Audit；
   无副作用health/readiness读取可自动执行。

上述为目标runbook；真实systemd unit、代理/SSO配置、备份密钥和restore rehearsal尚未交付，因此activation仍BLOCKED。

## 11. Acceptance、交接与退役

production acceptance 至少要求：immutable artifact/provenance、全部 P0 contract/runtime/security/operations
cases PASS、Piko/Embedding consumer captures、operations owner、backup/restore、rollback rehearsal、SLO/alert、
single-authority scan、manifest 与 routes 一致，以及独立 Runtime Activation approval。

交接包包含 runbook、artifact/config/schema、contacts、dashboard/alert、known issues、backup/restore、rollback、
evidence 与 decision。退役必须先停止新 admission，收敛 in-flight，满足 retention/export/delete policy，撤销
credential，移除 route/consumer config，并验证不存在旧 embedded/Provider-direct path。当前 acceptance、
handoff 与 retirement 均 NOT_RUN/BLOCKED；本文不授权执行。
