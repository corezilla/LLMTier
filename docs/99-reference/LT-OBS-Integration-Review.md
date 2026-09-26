# LT-OBS 集成与模块设计总评（consolidated review）

- 日期：2026-09-23
- 适用范围：Piko ↔ LLMTier 联调侧（joint commissioning），含 LLMTier 模块设计、契约对齐、实现契合度、缺口。
- 文档定位：非 STD（reference 类）。

## 0. 现状速览（commit 锚点）

| 仓库 | 节点 | 关键 commit |
|---|---|---|
| LLMTier | `/tier/admin/v1/*` 与 `/v1/*` 命名空间 + observability 设计 + 实现 | `29efe80`（诊断契约路由 alias 恢复）、`555e084`（/v1/* 扁平化诊断路由）、`c433258`（LT-OBS 实现）、`bf0d5a1`（/v1/* 扁平化，破坏契约路由） |
| piko | 联合调试方案 + 诊断消费工具 | `85b6355`（契约路径回滚）、`4434671`（/v1/* 跟随实现）、`4bf66a8`（集成 review + F-7 修复） |

## 1. 模块设计 review（基于已发布实现 + 设计文档）

### 1.1 契合项（无需改）

| 模块/能力 | 设计文档 | 实现/契约契合 |
|---|---|---|
| 节点划分 | `observability-design.md` M005 + `libdiag-design.md` M006 + `core-design §3` | diagnostics.py 与 libdiag 拆分清晰；app.py 仅作 M001 入口 |
| 接口契约 §9 IF-OBS-01..03 | observability-design §9.1-9.5 | app.py → DiagnosticsService 方法签名与设计一致（switch/set_switches/snapshots_page/stats/trace/set_injections/injections） |
| 流注入包装（Phase 5b） | `libdiag-design §2.6 F-DIAG-STREAM` | response_stream 包装在 app.py（不动 sse.py），符合"流注入落 M001 不动 M004 SSE 内部"的设计 |
| Retention 清理（7 天） | `observability-design §2.7 F-DIAG-CLEANUP` + `libdiag-design §2.7` | diagnostics.cleanup(7) 在 Application.__init__ 启动时执行，fail-open |
| fail-open 原则 | `observability-design §5.4`、`core-design §10`（失败与恢复） | DiagnosticsService 所有写入路径包 try/except；需求 §8.3 一致 |
| 注入 `source=injected` 账本标注 | 契约 §5.1、design §4.1 capture_snapshot 注入入账本语义 | `usage.finish(...,source_override="injected")` 仅对 raise-with-injection 的请求调用，常规请求走默认 `provider/unavailable` |

### 1.2 设计 ↔ 实现偏差（已实现，文档待对齐 — 不阻塞，仅文档修订）

| ID | 偏差 | 建议 |
|---|---|---|
| D-3 | `observability-design §2.4 F-OBS-INJECTIONS` 缺"多 enabled 时确定性优先级"（contract §5.1 要求 fault_502→fault_503→rate_limit→delay；流阶段同理） | observability-design §2.4 / §4.1 `get_enabled_injections` 补单次优先级规则 |
| D-4 | `observability-design §4.1 get_enabled_injections` 返回 list；contract §5.1 要求"首个命中即触发一种"，**单条** | 改返回单条，或追加 `get_enabled_injection` 单条 API |
| D-5 | `observability-design §2.6 F-OBS-CORRELATION` 缺"consumer 提供时响应头 `X-Correlation-ID` 回显"契约 | §9 接口契约补：`X-Correlation-ID` 仅 consumer 提供时回显 |
| D-6 | `observability-design §4.1` 列为 `snapshots_enabled()` / `stats_enabled()` 单独方法；实现用 `switches()` 合并 | 实现保留 `switches()`/`set_switches()`；设计可补两个独立方法为 alias |

### 1.3 契约 ↔ 实现冲突（**实现修正，契约待跟进**）

| ID | 冲突 | 状态 |
|---|---|---|
| **F-7** | `bf0d5a1` 把已发布契约（`llmtier-management-contract v0.3` `/tier/admin/v1/*`）静默改名 `/v1/*` 且未保留 alias，破坏既有 management/usage/audit/logs 路径；observability-design §9 同时用 `/v1/diagnostics*` 与契约冲突 | **已修复**：`29efe80` 在 app.py 加 `/tier/admin/v1/diagnostics*` + `/tier/admin/v1/trace/{id}` alias 共存 `/v1/*`；contract v0.3 与 design §9 共存 |
| F-7 衍生 | `joint-diagnose.sh` 与 spec §7.0 原引用 `/tier/v1/usage` / `/tier/admin/v1/audit` / `/tier/admin/v1/logs` | **已修复**：`85b6355` 跟随契约路径回滚到 `/tier/admin/v1/*`、`/tier/v1/usage`；后续直接对接契约即可工作 |

### 1.4 observability-design.md §2.3 stats 口径与契约 §5.3 偏离

| 设计文档 | 契约（需求文档 §5.3） |
|---|---|
| `get_stats` 返回 `request_count, error_4xx_count, error_5xx_count, P50/P95/min/max/avg` | `request_count, error_count, status_breakdown{status:count}, P50/P95/min/max/sum`（**按 HTTP status 分列 + 每 status 计数**） |

**LLMTier agent 需更新 §2.3 与 §4.1**：在 stats 响应中加 `status_breakdown`（per-status 计数对象）；保留 4xx/5xx 总数作兼容（可选）。

## 2. 缺口：需 LLMTier agent 实现

| ID | 缺口 | 接口 | 落地 |
|---|---|---|---|
| **G-1** | trace 按时间窗查询 | `GET /tier/admin/v1/diagnostics/traces?since=&until=&deployment_id=&model=&limit=&cursor=` 返回 `{items:[{request_id,stages[],correlation_id?,usage?}], next_cursor, has_more}` | 与 snapshots 对称；联调场景"过去 10 分钟所有失败请求"的关键 API |
| **G-2** | `get_stats` 口径补 `status_breakdown`（per-HTTP-status 计数对象） | 修改 observability-design §2.3 + §4.1 + libdiag-design §2.4 F-DIAG-STATS | 与契约 §5.3 对齐；Piko 联调 JT-13 已按契约验证 |
| **G-3** | observability-design.md 文档对齐 | 补 §2.4 优先级规则 / §4.1 单条 enabled API / §2.6 回显契约 / §2.3 stats 口径 / §4.1 单方法 alias | 一次性同步 |

## 3. 缺口：Piko consumer 侧（非 LLMTier）

| ID | 项 | 落地 |
|---|---|---|
| **G-4** | Piko consumer 当前不在每请求发送 `X-Correlation-ID` / `traceparent` 头 | Piko 在每条出站模型请求加 `X-Correlation-ID: <run_id>`（或 `traceparent`），与 Piko 自身 `provider_calls.request_id` 对齐；**这要求 Piko product 改动，不在 LLMTier 侧** |

## 4. 决策点（建议与理由）

### 4.1 契约路由：保留 `/tier/admin/v1/*` 还是升级 contract 到 `/v1/*`

**建议保留 `/tier/admin/v1/*` 契约路径**（当前已用 alias 实现 `29efe80`），保留原因：

- `llmtier-management-contract v0.3` 是 frozen 契约；任何包含外部消费者的产品（Piko、运维工具、Prometheus 抓取、第三方 ops 平台）都已按 v0.3 写死。
- 升级契约到 v0.4（`/v1/*`）需要走 contract 升级流程（STD 评估 + Owner sign-off + consumer 同步迁移），不是 LLMTier 一个 commit 可完成。
- `/v1/*` 与 `/tier/admin/v1/*` 共存零成本（同一 handler 派发），保留 alias 与扁平内部命名空间不冲突。

### 4.2 注入 enabled_injection 单条 vs list

**建议单条返回**（与契约 §5.1 一致）：多 enabled 注入同时发生语义模糊（Piko 联调 JT-17 要求确定性优先级）。内部数据仍存多行（可启用多项），但暴露的查询 API 返回"下一步要触发的一条"。

### 4.3 stats status_breakdown

**实现应同时提供**：
- `status_breakdown:{"200":n, "429":m, "502":k, ...}` per-status 计数对象（Piko 联调 JT-13 契约 §5.3 验证）
- `error_count` 总数（与 status_breakdown 中 status≥400 + upstream_error 之和一致）

实现侧 cost 极低：在 `record_latency` 内同步 UPSERT 一行 per (hour, deployment, model, status)。

## 5. Piko 联调侧的「未通过点」现状与下一步

按 §1.4 review 与之前联调报告（Juno 16 PASS + JT-17 BLOCKED）：

| case | 状态 | 阻塞 |
|---|---|---|
| JT-01..JT-13 | ✅ PASS | — |
| JT-14 | ✅ PASS | — |
| JT-15 | ✅ PASS | — |
| JT-16 | ✅ PASS（embedding 实测） | — |
| **JT-17** | ⚠️ **BLOCKED（待 R-T-5/LT-OBS-5 实现完成后补执行）** | G-1 trace 时间窗查询（非必需）；**当前 JT-17 ①②③ 已可执行**（代码已实现且 320 测试绿） |

**实际可立即执行**：JT-17 ②③ 部分（fault_502 通过 Piko → ModelUnavailable；delay 5s；rate_limit 429+Retry-After）。仅需运行 + 在 joint-diagnose.sh 启用 diagnostics（designed from /tier/admin/v1/diagnostics PATCH），开关当前默认 off → 联调开始前 PATCH 开启 → 跑 JT-17 ②③ → 关闭。

## 6. 总结：review vs 实施 vs 未来

| 维度 | 状态 |
|---|---|
| 模块设计（observability-design + libdiag-design + core-design） | 设计完整，已实现，**仅文档对齐偏差待修订** |
| 契约 ↔ 设计 ↔ 实现 | `bf0d5a1` 破坏契约路由 → 已加 alias 修复 → 现契约契约路由 + 实现 + 设计三方一致 |
| 缺口 | G-1（trace 时间窗）、G-2（stats status_breakdown）、G-3（observability-design 文档同步）、G-4（Piko consumer 发 `X-Correlation-ID`，非 LLMTier 范围） |
| 联调 Gate 状态 | 16 PASS + 1 BLOCKED（JT-17 待 G-1/G-3 收敛后补执行；②③ 现在可立即跑） |

## 7. 行动表（按优先级排序）

| 序 | 行动 | 归 | 完成判据 |
|---|---|---|---|
| 1 | LLMTier 路由契约兼容性已修（`29efe80`）→ Piko 联调立即可执行 JT-17 ②③ | 完成 |  |
| 2 | LLMTier 设计/代码补 `GET /tier/admin/v1/diagnostics/traces` 时间窗查询（G-1） | LLMTier agent | 接口契约 §10 增加条目；新增单元测试；diagnostics.py 实现；pytest 绿 |
| 3 | observability-design.md 文档一次性同步（D-3/D-4/D-5/D-6 + stats 口径 G-2） | LLMTier agent | 与契约 §5.3、§5.1 对齐；新增 VRC-OBS-* 单元 |
| 4 | Piko product 在每条出站模型请求加 `X-Correlation-ID` 头（G-4） | Piko 联调方 | 双向定位贯通；JT-17 ④⑤ 联动验证 |
| 5 | JT-17 完整执行（①②③ 立即；④⑤ 待 Phase 5b/audit 文档验证后） | Piko 联调方 | 联调 Gate 收口 |