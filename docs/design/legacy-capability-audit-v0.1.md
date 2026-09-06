# LLMTier 旧实现能力与耦合审计 v0.1

Last Updated: 2026-09-06 13:40:00 +08:00

Status: 设计输入；不是新契约冻结或实现验收

## 1. 审计结论

复制基线提供了可复用的 Python 服务生命周期、路由、并发、配额、统计和 Provider adapter，但对外接口仍是 Slinky 内嵌时期的私有 Tier API。当前代码没有实现 Piko 所需的 `/v1/responses`、`/v1/chat/completions`、`/v1/models`，也没有实现新版 `/tier/v1/*` scoped observation contract。

因此后续工作是在现有单一服务机制内替换边界，不把旧接口包装成永久兼容旁路。

## 2. 现有能力证据

| 能力 | 当前实现位置 | 当前证据 | 处置 |
| --- | --- | --- | --- |
| 服务启动/停止 | `src/llm_tier/__main__.py`, `server.py` | `python -m llm_tier --help` 可运行 | 保留并独立化配置/状态路径 |
| HTTP listener | `server.py:TierServer` | loopback/private host 校验；旧 GET/POST dispatch | 保留 listener 与唯一业务 authority，替换外部 route contract |
| 模型路由 | `router_core.py` | Tier 到 backend/account/model 选择 | 保留 routing core，改为 exact `service_level_id` admission |
| 并发控制 | `concurrency.py` | backend/account active limit | 保留基础原语，补 Client/Source entitlement 与 capacity group |
| quota | `quota_manager.py` | backend quota/state | 保留基础原语，明确 authoritative persistence 与 snapshot version |
| usage/statistics | `provider_usage.py`, `stats_collector.py`, `stats/llm_stats.py` | Provider usage、SQLite invocation statistics | 保留采集能力，修正 unknown usage 不补零并加入 scoped identity |
| credential redaction | `redaction.py` | credential-like key/value 脱敏 | 保留并加入错误、stream、audit fixture |
| API Provider adapter | `backends/api_backend.py`, `deepseek.py`, `minimax.py`, `volc.py`, `xfyun.py`, `opencode_go.py` | 多种 HTTP Provider 调用 | 保留候选 adapter；需验证 tool/stream/structured-output/usage/error 语义 |
| 旧异步 Job | `server.py`, `client.py` | `/call`、`/result/{job_id}`、cancel/poll | 作为 Invocation lifecycle 实现参考，不保留为 Piko 第二协议 |
| 旧运营接口 | `server.py` | `/health`、`/runtime`、`/stats`、config/backend mutation | 按 Data/Observation/Management 三分面重新授权和命名 |

## 3. 必须替换或删除的耦合

| 旧机制 | 冲突 | 目标处置 |
| --- | --- | --- |
| `role_name` 与 `execution_identity.py` | Role/IR/Agent authority 属于 Slinky/Piko | 从 Piko Data Plane 删除；只接受 exact `model=service_level_id` 与 canonical Client/Source identity |
| `/call`、`/escalate` | 不是 OpenAI-compatible surface；`escalate` 允许 Tier 决定跨等级 | 由 `/v1/responses` 主路径取代；不保留 fallback endpoint |
| `agent_backend.py` | Tier 内执行 Agent/Tool loop | 从新 authoritative registry 删除 |
| `mlexp.py`, `mlexp_contract.py` | 旧 mlexp Agent/runtime 旁路 | 从新运行时删除，不提供兼容路径 |
| `claude.py`, `codex.py`, `opencode.py` | CLI Agent runner，不是纯模型 Data Plane | 从新 authoritative registry 删除或隔离为历史代码，不能进入生产路由 |
| `SLINKY_*` 环境变量 | 独立服务仍依赖旧项目命名与路径 | 迁移为单一 LLMTIER 配置机制；不并存两套永久配置路径 |
| `workspaces/settings.json` 与 `workspaces/tier_state` | 依赖 Slinky repository layout | 改为 LLMTier 自有 config/state root，默认路径不越出本项目 |
| 旧 Dashboard 直接集成 | 管理 UI 属 LLMTier，不能依赖 Slinky Dashboard | 后续建立独立 Admin UI 或先仅保留 Management API；不复制旧页面作为运行依赖 |

## 4. Piko Data Plane 差距

| 契约项 | 当前状态 |
| --- | --- |
| `POST /v1/responses` | 未实现 |
| `POST /v1/chat/completions` | 未实现；是否进入最低范围取决于 pinned Pi SDK 证据 |
| `GET /v1/models` 与 exact `service_level_id` | 未实现 |
| Function Tool / tool choice / tool result | 未实现 OpenAI inbound contract；Provider adapter 能力未形成统一证据 |
| Structured output / JSON Schema strictness | 未实现统一 contract |
| SSE streaming 与 terminal event | 未实现统一 inbound stream |
| Bearer auth 与 canonical Client/Source headers | 未实现新版 contract |
| `x-tier-invocation-id` | 未实现 |
| Data Plane outcome query | 未冻结、未实现 |
| Idempotency digest/retention | 旧 Job 机制不足以证明新版 contract |
| Compatibility manifest | 未实现 machine-readable artifact |

## 5. Slinky capacity/observation 差距

当前 `/health`、`/runtime`、`/stats` 提供旧全局/运营视图，但尚未形成 Client-scoped、versioned、带 `valid_until`/ETag 的 readiness、service-level、capacity、invocation、usage 和 compatibility API。旧字段不能直接被 Slinky 当作 Tier Service Seat 的权威投影。

## 6. 实施顺序

1. 冻结单一独立配置与状态根，清除运行时对 Slinky 路径的依赖。
2. 将 authoritative backend registry 限制为纯模型 adapter，移除 Agent/mlexp/CLI runner 路径。
3. 在现有 `TierServer`/Router/Concurrency/Stats authority 上实现 exact service-level admission 与 Invocation ledger。
4. 先实现 `/v1/responses`、`/v1/models`、认证、identity、error、usage 和 non-stream fixture。
5. 依据 pinned Pi SDK 实测决定是否加入 `/v1/chat/completions`，随后实现 Tool、structured output、stream/cancel/recovery。
6. 实现 Slinky scoped capacity/observation contract，最后处理 Management/Admin UI。

