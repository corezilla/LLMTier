<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier 可观测性机制（LT-OBS）

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-observability-mechanism` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-22` |
| Last Modified Date | `2026-09-22` |
| Template ID | `design.system-mechanism` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/20_system_design/mechanisms/observability.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 机制摘要：解决什么问题

跨服务失败时无法定位"哪一层、哪个请求、哪个上游调用"。本机制提供上游环回快照、数据面统计、故障注入、单请求 trace 与关联标识透传，使定位链路产品化。

## 2. 使用场景与功能

- 上游快照：记录一次上游调用的 URL/status/时延/错误摘要；
- 数据面统计：请求数、错误数、P50/P95；
- 故障注入：运行时可切换地制造故障/时延/限流/流异常；
- 单请求 trace：按 request_id 一次查全生命周期；
- 关联标识：可选接收 consumer 的 `X-Correlation-ID`/`traceparent` 并回显。

## 3. 参与方、责任和 authority

### 3.1 系统约束与参与方承接

本机制为顶层机制（上级 Mechanism ID = none），约束继承自系统设计 §3。

参与方：Inference（事件产生）、Observability（查询/呈现/切换开关）、`libdiag`（底层能力）。Authority 为 LLMTier。

### 3.2 运行时统筹与确认责任

`libdiag` 提供能力（开关/注入配置/记录读写）；Observability 调用并呈现；Inference 在请求路径按配置注入并写入事实。

### 3.3 拓扑、目标身份与共享故障域

单节点；观测为尽力而为，fail-open，其故障不得使推理失败。

## 4. 数据结构设计

### 4.1 类型目录与完整字段

`diagnostic_snapshots`（request_id、upstream_url、backend_model、http_status、latency_ms、error_summary）；`data_plane_stats`（按 deployment/model/hour 的计数与 P50/P95）；`diagnostic_injections`（按 deployment 的注入配置）；`trace_events`（stage、timestamp、detail、correlation_id）。

### 4.2 编码、布局与共享类型映射

字段见实现设计 `llmtier-diagnostics.isd.md`。

### 4.3 一致性、可见性与数据寿命

保留 7 天；关默认关闭、关闭零开销。

## 5. 接口设计

### 5.1 逐操作签名、错误与调用演练

- `GET/PATCH /v1/diagnostics`（全局开关）；
- `GET /v1/diagnostics/snapshots`、`GET /v1/diagnostics/stats`；
- `GET/PATCH /v1/deployments/{id}/diagnostics`（注入）；
- `GET /v1/trace/{request_id}`。

## 6. 正常端到端流程

请求进入（received）→ 校验（validated）→ 路由（routed，读注入配置）→ 上游开始/结束（写快照）→ 终态（completed/error/aborted）→ 统计累积。

### 6.1 生命周期过程与交叠操作

逐阶段记录；同一 request_id 事件有序。

## 7. 分支和替代流程

- 开关关闭 → 不写入、零开销；
- 注入命中 → 按类型延迟/报错/限流；
- 观测写入失败 → 记 warning，不阻塞。

## 8. 状态机与不变量

不变量：不记录 Secret/credential/完整正文；注入调用账本 source 标注 `injected`。

### 8.1 资源预留、交付、释放与复位

无预留；过期记录由清理任务删除。

## 9. 失败传播、重试与恢复

fail-open：任何观测失败不得改变推理结果。

## 10. 并发、排序与容量

统计内存缓存带上限与淘汰；写入为尽力而为。

## 11. 安全、权限与信任边界

需 operator 凭据；`error_summary` UTF-8 安全截断。

## 12. 可观测性与证据

### 12.1 统计、日志、时间与关联

本机制即证据来源；与 logs/audit 分离。

### 12.2 维护命令、自检与调试路径

`LLMTier joint-diagnose.sh` 通过 `x-request-id` 调 trace/snapshots。

## 13. 配置、兼容与部署

开关与注入配置存于存储；默认关闭。

## 14. 各参与方实现清单

| 参与方 | 义务 |
|---|---|
| `libdiag` | 开关/注入/记录能力 |
| Observability | 查询与呈现、开关切换 |
| Inference | 按配置注入、写事件 |

## 15. 验证、上线与回滚

### 15.1 输入构造、故障控制与独立判据

用例覆盖开关生效、快照/统计/trace 查询、注入四类、关闭后恢复。

### 15.2 环境部署、复位、并发隔离与自动化

测试实例独立库；注入在测试关。

### 15.3 组合验收、启用与旧机制退出

随 Phase 化实现启用；流注入见 `LT-OPEN-05`。

## 16. 风险、未决问题与决定

- `LT-OPEN-04`：四类数据各归 1 张表，保留 7 天；
- `LT-OPEN-05`：流注入需改造流式输出。

## A. 输入基线、适用性与图文规则

输入：系统设计 §11.3、`HANDOFF-Piko-Joint-OBS`（Piko 联调输入）。

## B. 文档控制与修订记录

初版 `0.1.0-draft.1`；修订见 Git。
