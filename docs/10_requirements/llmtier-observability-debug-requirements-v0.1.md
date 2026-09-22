<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier 可观测性与调试能力需求（Piko 联调输入）

> STD 使用入口：[项目采用说明与标准导航](../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-observability-debug-requirements-v0.1` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-22` |
| Last Modified Date | `2026-09-22` |
| Template ID | `requirements.specification` |
| Template Version | `0.1.1` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/10_requirements/llmtier-observability-debug-requirements-v0.1.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. 目的、范围与来源

- **目的**：Piko ↔ LLMTier 首次联合调试（见 Piko 仓库 `piko-llmtier-joint-report-v0.1` §5.2 发现
  F-2/F-4/F-5）暴露出跨服务失败时**层位定位能力不足**。本文将 Piko 侧提出的观测诉求转化为
  LLMTier 的 shall 需求，供 LLMTier 实现与验收。
- **范围**：Data Plane（`/v1/responses`）与相关管理面的可观测性（环回捕获、日志明细、统计、
  readyz 语义）；不改变 Data Plane 功能契约与 Slinky capacity 边界。
- **来源**：Piko 联调报告发现 F-2/F-4/F-5；`llmtier-piko-data-plane-control` §3/§6/§10。

## 2. 系统/产品上下文

LLMTier 位于 consumer（Piko）与模型后端（oMLX，外部系统）之间。oMLX 为外部系统：**只依赖其现有
HTTP 能力**（`/v1/models`、`/v1/responses`、Bearer），后端观测不足由 LLMTier 侧补偿捕获。

## 3. 假设、约束与术语

- 调试捕获必须由**开关控制**，默认关闭；关闭时不得引入可测开销。
- 捕获内容不得包含 Provider Secret、consumer credential 或完整 prompt/输出正文（可含长度、
  哈希与截断摘要）。
- 术语：环回捕获（请求/响应在本节点的收发记录）、数据面（`/v1/responses` 推理请求）。

## 4. 功能需求

| ID | 需求（shall） | 验收标准 |
|---|---|---|
| LT-OBS-1（环回） | 调试开关开启时，LLMTier shall 为每个 Data Plane 请求记录**上游调用快照**：上游 URL、backend_model、HTTP status、时延 ms、错误体摘要（截断）；关闭时不记录 | 开关开启：一次 `/v1/responses` 后可在管理面查到该请求的上游快照（含 status 与时延）；关闭：无新增快照且无开销 |
| LT-OBS-2（统计） | LLMTier shall 提供数据面统计查询：按 model 与 HTTP status 的请求数、错误数、时延分布（P50/P95），管理面可查、支持时间窗 | 两次不同结果的请求后，统计计数可区分并累加；时间窗外不计入 |
| LT-OBS-3（审计语义） | LLMTier shall 在管理控制文档中**明示** audit 覆盖范围：当前仅管理面动作（provider/deployment/service-level/probe），数据面请求不产生 audit 事件 | 文档声明与实现一致；consumer 可据此选择追踪手段 |
| LT-OBS-4（readyz 语义） | LLMTier shall 使 `readyz` 全局状态反映**实际可用能力**：未启用对应部署的占位 service level 不得将全局状态降级为 `degraded`（应在模型级标注 unavailable，全局 status 由已启用能力决定） | 仅启用 chat 部署时，`readyz.status` 为 `ok`（或 `ready`），占位 embedding 模型级仍标 unavailable |
| LT-OBS-5（故障/时延注入开关） | LLMTier shall 提供**运行时可切的注入开关**（admin 控制、按 deployment 生效、可随时关闭）：① 注入上游故障（502/503 带错误体）② 注入时延（+N ms）③ 注入限流（429+Retry-After），使 consumer 侧故障路径可**确定性**触达 | 注入 502 → consumer 收到 502 及错误体；注入时延 → 响应时延按设定增加；注入 429 → consumer 收到 429+Retry-After；关闭后立即恢复且非注入流量不受影响；注入事件在 logs/audit 可见 |
| LT-OBS-6（统计清空） | LLMTier shall 提供管理面接口**清空指定范围的 usage 统计记录**（按 model 和/或 deployment_id 过滤；支持全文清空） | DELETE `/tier/admin/v1/usage?model=Worker&deployment_id=dep_xxx` 返回 `{"deleted": N}`；不带过滤参数清空全部统计；清空后 GET /stats 不再包含已删除记录 |

## 5. 接口需求

- LT-OBS-1/LT-OBS-2 的查询入口扩展管理面（如 `/tier/admin/v1/logs` 增强、或新增
  `/tier/admin/v1/diagnostics/*`），遵循既有 admin Bearer 鉴权与 ETag 约定；具体形状由实现设计定。
- 开关形式：settings 项或 admin API 亦可，但必须**运行时可切换**且默认关闭（LT-OBS-5 同）。
- LT-OBS-5 的注入范围仅限调试用途：注入期间的真实上游调用仍正常计量，注入语义不得写入 usage 账本造成对账歧义（账本可标注 injected）。

## 6. 性能与容量需求

开关关闭时：请求路径不得增加可测开销（无锁、无 IO）；开关开启时：捕获写入不得阻塞推理流
（异步/尽力而为），磁盘用量有上限或轮转。

## 7. 安全、可靠性与合规需求

捕获与统计**不得**记录：Provider Secret、consumer credential、完整 prompt/输出正文（长度、
哈希、截断摘要允许）。观测子系统故障不得影响 Data Plane 可用性（fail-open）。

## 8. 运维、诊断与可观测性需求

观测数据保留期沿用既有 logs/audit 策略；consumer 侧定位流程（Piko `joint-diagnose.sh`）将
消费 LT-OBS-1/LT-OBS-2 的输出，字段命名需稳定并文档化。

## 9. 制造、部署、维护与退役需求

不适用（纯软件服务内能力）；随版本发布说明开关用法。

## 10. 验收与 traceability

- 验收：按 §4 验收标准逐条验证（人工或集成脚本）；来源 traceability：
  Piko `piko-llmtier-joint-report-v0.1` F-2/F-4/F-5 ↔ LT-OBS-1..4；联调补充需求 ↔ LT-OBS-5..6。
- 实现完成后由 Piko 联调方 review（对应 Piko 规格 `piko-llmtier-joint-test-specification-v0.1`
  §3.1 复核记录）。
