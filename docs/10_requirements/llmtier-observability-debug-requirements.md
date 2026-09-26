<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier 可观测性与调试能力需求（Piko 联调输入）

> STD 使用入口：[项目采用说明与标准导航](../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-observability-debug-requirements` |
| Document Version | `0.1.0-draft.9` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-22` |
| Last Modified Date | `2026-09-22` |
| Template ID | `requirements.specification` |
| Template Version | `0.2.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/10_requirements/llmtier-observability-debug-requirements.md` |
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
| LT-OBS-2（统计） | LLMTier shall 提供数据面统计查询：按 model 与 HTTP status 的请求数、错误数、时延分布（P50/P95），管理面可查、支持时间窗；**响应含 `status_breakdown` 按 HTTP status 分列**（契约 §5.3） | 两次不同结果的请求后，`status_breakdown` 分列可区分并累加；时间窗外不计入 |
| LT-OBS-3（审计语义） | LLMTier shall 在管理控制文档中**明示** audit 覆盖范围：当前仅管理面动作（provider/deployment/service-level/probe），数据面请求不产生 audit 事件 | 文档声明与实现一致；consumer 可据此选择追踪手段 |
| LT-OBS-4（readyz 语义） | LLMTier shall 使 `readyz` 全局状态反映**实际可用能力**：未启用对应部署的占位 service level 不得将全局状态降级为 `degraded`（应在模型级标注 unavailable，全局 status 由已启用能力决定） | 仅启用 chat 部署时，`readyz.status` 为 `ok`（或 `ready`），占位 embedding 模型级仍标 unavailable |
| LT-OBS-5（故障/时延/限流/流注入开关） | LLMTier shall 提供**运行时可切的注入开关**（admin 控制、按 deployment 生效、可随时关闭）：① 上游故障（502/503 带错误体）② 时延（+N ms）③ 限流（429+Retry-After）④ **上游流提前终止**（SSE 已开头发一半即断）⑤ **畸形流事件**（违反 Responses 事件序/非法 JSON 事件），使 consumer 侧的故障、重试、流处理路径可**确定性**触达 | ① consumer 收到 502 及错误体 ② 时延按设定增加 ③ 收到 429+Retry-After ④ consumer 收到不完整流并有明确错误处置（不得悬挂/伪报）⑤ consumer 收到畸形事件并有明确错误处置；关闭后立即恢复；非注入流量不受影响；注入事件在 logs/audit 可见 |
| LT-OBS-8（统计清空） | LLMTier shall 提供管理面接口**清空指定范围的 usage 统计记录**（按 model 和/或 deployment_id 过滤；支持全文清空）；清空时同步清理关联表孤儿记录 | DELETE `/v1/usage?model=Worker&deployment_id=dep_xxx` 返回 `{"deleted": N}`；不带过滤参数清空全部统计；清空后 GET /stats 不再含已删除记录；`usage_obligations` 中无对应 `usage_record_versions` 的孤儿记录同步清理 |

| LT-OBS-6（单请求 trace 查询） | LLMTier shall 支持**按 `request_id` 一次查询该请求的全生命周期记录**（范围：通过鉴权的 `/v1/responses` 请求；embeddings/管理面不 trace），且包含**逐阶段时间戳**（received / validated / routed / upstream_started / upstream_ended / completed|error）：接收时间、校验结果、路由（service level/deployment）、上游调用快照（LT-OBS-1）、SSE 终止原因（completed/error/aborted）、usage 记录（含 record_version）；管理面可查；支持导出 JSON；观测数据保留期 ≥ 7 天（与既有 retention 对齐） | 对任一已发生请求，单次查询返回上述全部字段（或明确的缺失标注）；`request_id` 与 Data Plane 响应头 `x-request-id` 一致；逐阶段时间戳可计算各跳时延；导出为合法 JSON |
| LT-OBS-7（consumer 关联标识透传） | LLMTier shall **可选接收** consumer 侧关联标识（`X-Correlation-ID` 或 `traceparent`，非强制），并在该请求的 **logs 与 trace 查询结果中回显**；缺失时行为不变（自动生成 request_id）。**决策（Piko 联调方确认）**：usage 账本不标注 correlation_id——双向定位以 `request_id` 关联替代 | 带/不带标识的请求行为均符合上述语义 |

## 5. 接口需求（契约级——LLMTier shall 按此实现，consumer 侧 case 按此编写）

> 本节为**接口契约需求**：路由、方法、请求/响应体、状态码与语义均为 shall。
> LLMTier 可扩展字段/端点，不得与本节矛盾；实现完成后冻结并附 curl 级示例。

### 5.1 注入开关（LT-OBS-5）

**PATCH** `/v1/deployments/{deployment_id}/diagnostics`（admin Bearer）

- 请求体：JSON 数组，每项 `{"type": <string>, "config": <object>, "enabled": <boolean>}`
- type 枚举与 config（shall 完全支持）：

| type | config | consumer 可见效果 |
|---|---|---|
| `fault_502` | `{"error_body": string}` | HTTP 502 + 该错误体 |
| `fault_503` | `{"error_body": string}` | HTTP 503 + 该错误体 |
| `delay` | `{"delay_ms": int≥0}` | 上游调用前延迟 N ms |
| `rate_limit` | `{"retry_after_sec": int≥0}` | HTTP 429 + Retry-After 头 |
| `stream_terminate` | `{"stream_terminate_after_events": int≥1}` | SSE 发出 N 个事件后断连 |
| `malformed_event` | `{"malformed_after_events": int≥0, "malformed_event_type": string}` | 第 N 事件后注入畸形事件 |

- 行为（shall）：enabled=true 对路由到该 deployment 的**后续请求**确定性生效；enabled=false/删除项立即恢复；
  PATCH 返回 200 + 该 deployment **全量**注入配置（type/config/enabled）；未知 type/缺必填 config →
  `400 invalid_injection`；未知 deployment → `404`；配置变更写 audit；注入期间请求的 usage 账本标注 injected。

**GET** `/v1/deployments/{deployment_id}/diagnostics`（admin Bearer）
- 200 + 全量注入配置数组；未知 deployment → 404。

### 5.2 快照查询（LT-OBS-1）

**GET** `/v1/diagnostics/snapshots?since=&until=&deployment_id=&model=&limit=&cursor=`（admin Bearer）
- 200 + `{"items":[{id,request_id,captured_at,upstream_url,backend_model,http_status,latency_ms,error_summary,model,deployment_id}], "next_cursor", "has_more"}`；`limit≤500` 默认 50；cursor 为上页末条 id。

### 5.3 统计查询（LT-OBS-2）

**GET** `/v1/diagnostics/stats?since=&until=&deployment_id=&model=`（admin Bearer）
- 200 + `{"windows":[{stat_hour,deployment_id,model,status_breakdown:{"200":n,"503":m,…},request_count,error_count,latency_p50_ms,latency_p95_ms,latency_min_ms,latency_max_ms,latency_sum_ms}]}`
- **status_breakdown（按 HTTP status 分列）为 shall**——仅 error_count 不满足需求。

### 5.4 单请求 trace（LT-OBS-6）

**GET** `/v1/trace/{request_id}`（admin Bearer）
- 200 + `{"request_id","correlation_id","stages":[{stage,timestamp,detail}…],"snapshot":{…},"usage":{…}}`
  （stages 覆盖 received/validated/routed/upstream_started/upstream_ended/completed|error|aborted，含逐阶段时间戳；snapshot 为 LT-OBS-1 快照；usage 含 record_version）
- 404 未知 request_id。

### 5.5 通用约定

- 全部诊断接口：admin Bearer；错误响应沿用既有 error 形状（`{error:{message,type,code,param,retryable}}`）；
### 5.6 字段与语义定稿（凡本节未定义的字段不得自行发明）

**通用**：时间戳一律 ISO 8601 UTC（`Z` 后缀）；鉴权一律 admin Bearer（data token → `403`）；
错误响应沿用既有形状 `{error:{message,type,code,param,retryable}}`；诊断端点**不使用 If-Match**
（最后写入生效）；snapshots/trace_events/stats 保留期均 7 天（cleanup job）；trace 与 correlation
仅覆盖 `/v1/responses`（embeddings 不记录）；`x-request-id` 响应头行为维持现状。

**注入 PATCH（§5.1）字段定稿**：
- `config` 取值范围：`delay_ms` 0–60000；`retry_after_sec` 0–300；`stream_terminate_after_events`
  1–10000；`malformed_after_events` 0–10000；`error_body` ≤512 字节。越界/缺失/未知 type →
  `400 invalid_injection`；未知 deployment → `404`。
- 响应 `200`：`[{"type","config","enabled","updated_at"} …]`（全量）；**不使用 If-Match**；
  配置变更 shall 写 audit（action=`diagnostics.injection.update`）。
- 同 deployment 多开关同时 enabled 的**确定性优先级**：前置阶段按
  `fault_502 → fault_503 → rate_limit → delay` 首个命中即触发（互不叠加）；流阶段按
  `stream_terminate → malformed_event` 首个命中（前置通过后才评估）。
- 注入响应体（normative envelope）：HTTP=`fault_status`，体=
  `{"error":{"message":"<error_body>","type":"server_error","code":"<fault_502→provider_failure｜fault_503→provider_unavailable>","param":null,"retryable":true}}`。
- 注入请求不产生上游调用、不产生正常计量；如记 usage 账本则 `source=injected` 可区分。
- `stream_terminate`：转发 N 个事件后**直接断连**（无 terminal 事件/无 [DONE]）；
  `malformed_event`：转发 N 个事件后注入 1 个畸形事件（`invalid_json`=非 JSON data 行；
  `unknown_event_type`=未定义 event 名）再断连（无 terminal 事件/无 [DONE]）。

**快照 GET（§5.2）字段定稿**：
- 过滤：`since`/`until` 为 `captured_at` 闭区间（UTC）；`deployment_id`/`model` 精确匹配；
  `limit` 1–500（默认 50）；`cursor` = 上页末条 `id`（keyset）。
- 排序：`captured_at DESC, id DESC`。响应：`{"items":[…],"next_cursor":str|null,"has_more":bool}`。
- 字段可空性：`backend_model` NULL=上游未返回；`http_status` NULL=连接/异常失败（此时
  `snapshot_type='error'` 且 `error_summary` 非空）；`snapshot_type ∈ {'upstream','error'}`。

**统计 GET（§5.3）字段定稿**：
- `windows[]` 项：`stat_hour`（UTC，按**请求完成时间**截断到小时）；`deployment_id`/`model`
  为 null 表示全局聚合行；`status_breakdown`：key=HTTP status 十进制字符串，**无 HTTP 状态的
  上游失败 key=`"upstream_error"`**；`error_count` = status≥400 各项之和 + `upstream_error`；
  时延单位 ms（REAL）；百分位 nearest-rank，样本数=1 时取该值。
- 合并：[since,until] 内**已完结小时**读表；当前未落盘小时读内存缓存；空结果 `windows:[]`。

**trace GET（§5.4）字段定稿**：
- 仅记录**通过鉴权**的 `/v1/responses` 请求；鉴权失败不产生 trace。
- `correlation_id`：consumer 提供（`X-Correlation-ID` 优先于 `traceparent`）则记录并经
  `X-Correlation-ID` 响应头回显；未提供 → `null` 且不回显。
- `stages[].detail` 白名单（R-3）：`received` 仅记录 `x-correlation-id`/`traceparent` 的**键值**
  与 `content-type`/`content-length` 的**长度**，其余 header 一律不落。
- `usage` 对象字段：`record_version,is_final,model,input_tokens,output_tokens,total_tokens,
  measurement_status,source`（最新 record）。
- 无 `trace_events` 记录的 `request_id` → `404`。
- 保留期：7 天（cleanup job）。

- 本节契约即联调 case（JT-13/14/15/17）与 consumer 定位工具（`joint-diagnose.sh`）的对接面；
  实现后 LLMTier 提供 curl 级示例，consumer 不因实现重构而改步骤。

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
  Piko 联调报告 `piko-llmtier-joint-report-v0.1` 发现 F-2→LT-OBS-4、F-4→LT-OBS-3、
  F-5→LT-OBS-1/6/7、F-6→LT-OBS-5；统计清空（运维）→LT-OBS-8。
- 接口契约：§5（含 §5.6 字段定稿）为 normative；实现后冻结并附 curl 级示例。
- 实现完成后由 Piko 联调方 review（对应 Piko 规格 `piko-llmtier-joint-test-specification-v0.1`
  §3.1 复核记录）。
