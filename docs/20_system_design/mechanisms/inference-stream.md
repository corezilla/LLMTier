<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier 推理与流式返回机制

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-inference-stream-mechanism` |
| Document Version | `0.1.0-draft.5` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-22` |
| Last Modified Date | `2026-09-22` |
| Template ID | `design.system-mechanism` |
| Template Version | `2.4.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/20_system_design/mechanisms/inference-stream.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 机制摘要：解决什么问题

Consumer（Piko）提交一次模型推理请求后，需要拿到**标准 Responses 流式结果**与 **token 用量**，而 LLMTier 必须把这次调用**可靠地**落到一个已配置的后端，并在失败/中断时给出**可判定**的结局。

**为什么不能由一个单元独立完成**：Consumer 不懂后端拓扑（provider/deployment/等级），后端不懂 Piko 的协议与用量账本；本机制横跨入口（HTTP/SSE）、推理编排、准入与路由、外部后端，是数据面主路径。

**输入 → 处理 → 输出**：
- 输入：`POST /v1/responses`（完整 input、exact `model`、`stream:true`、`store:false`）
- 处理：校验 → 记 unknown 义务 → 准入 → 选后端 → 调用 → 归一为 SSE → 记终态用量
- 输出：标准 SSE 事件流 + 一个 terminal 事件；terminal response 内含 token Usage

**本版本范围与取舍**：只支持 `stream:true/store:false`（固定 Pi 实际消费路径）；不提供 JSON 非流式并行模式；不做跨等级 fallback；不承诺跨系统 exactly-once。最坏情形下准入会排队并可能返回 429——用**保守资源保护**换**可预测的失败**。

## 2. 使用场景与功能

| Capability ID | 业务任务与触发 | 输入与可观察结果 | 提供方 / 消费者 | 实现状态 | 验证判据 |
|---|---|---|---|---|---|
| CAP-RESP | Consumer 单轮推理（固定 Pi） | 完整 input → 标准 SSE + terminal usage | Inference / Consumer | Implemented | 契约 + 系统用例 DP-RESP-* |
| CAP-RESP-STREAM | 以 SSE 增量消费输出 | 事件序 + 稳定 item id | Inference / Consumer | Implemented | 事件子集与终态断言 |
| CAP-TOOLS | 模型返回 function call，Consumer 执行后以新请求回传 | `response.function_call_arguments.*` 事件 | Inference / Consumer | Implemented | DP-RESP-04 透传 |
| CAP-WAIT-FAIL | 队列满 / 等待超时 | 429 + `Retry-After` | Inference / Consumer | Implemented | 并发用例 |
| CAP-CANCEL | Consumer 断开连接 | 结束本次调用，不产生可恢复 Invocation | Inference | Implemented | 断开用例 |

**不提供**：非流式 JSON 模式；会话/历史；跨等级 fallback；Invocation 查询/结果恢复；prompt cache 协议。

## 3. 参与方、责任和 authority

### 3.1 系统约束与参与方承接

本机制为顶层机制（上级 Mechanism ID = none），约束继承自系统设计 §3。

| Constraint ID | 约束 | 参与方保证 | 自由度 | 本文落实位置 |
|---|---|---|---|---|
| C-INFER-1 | 只提供标准 Responses SSE，不增 JSON 并行模式 | 入口只发标准事件 | 内部编排方式 | §5.1、§6 |
| C-INFER-2 | 每请求恰好一个 terminal 事件 | 出口保证 | 事件名由 status 决定 | §6、§8 |
| C-INFER-3 | 结果未知不补零；账本只追加 | Inference 写 unknown 义务 | 归一实现 | §9、M-METER |
| C-INFER-4 | 不做跨等级/跨空间 fallback | Router 只在同等级选 | 选择排序 | §10 |
| C-INFER-5 | 观测 fail-open，不改推理结果 | Inference 不因观测失败而失败 | 捕获实现 | §12、M-OBS |

### 3.2 运行时统筹与确认责任

入口（HTTP API）统筹请求生命周期与 `request_id`；Inference 决定校验与归一；Router 决定准入与候选；后端决定生成内容；出口统一确认 terminal。

### 3.3 拓扑、目标身份与共享故障域

单进程单节点。后端为**外部依赖**，其故障域独立于 LLMTier；本机制不拥有后端内部。请求级身份为 `request_id`（+ 可选关联标识，见 M-OBS）。无跨节点协调。

## 4. 数据结构设计

### 4.1 类型目录与完整字段

> 数据定义分支：**已有机器源**（见下表“机器源”列）；正文只给阅读视图与差异，不另抄完整规范。

| 类型成员 ID | 用途与生产/消费 | 机器源 | 身份/可见性/寿命 |
|---|---|---|---|
| `ResponsesRequest` | Consumer → Inference | OpenAPI `/v1/responses` requestBody | 请求级；不含 Secret |
| `ResponsesResponse` | Inference → 出口（终态） | OpenAPI Response | 请求级 |
| `OutputItem` | 归一后的输出项 | OpenAPI（message/reasoning/function_call） | 请求级 |
| `SSEEvent` | 出口 → Consumer | §6 事件子集 | 顺序流；逐事件 |
| `ProviderResult` | 后端 → Inference | 内部（`providers/base.py`） | 请求级；含 usage/status/error |

`ResponsesRequest` 关键字段（完整以 OpenAPI 为准）：`model`(string,逻辑等级)、`input`(array)、`stream`(必为 true)、`store`(必为 false)、`tools`(可选)、`max_output_tokens`(可选)。**禁字段**：`prompt_cache_key`、`prompt_cache_retention`、`previous_response_id`。

`ProviderResult`（实现契约）：`output: list[OutputItem]`、`usage: {input_tokens,output_tokens,total_tokens,*_details} | null`、`status: completed|incomplete|failed`、`error`、`incomplete_details`。

### 4.2 编码、布局与共享类型映射

不适用二进制 ABI：本机制为 HTTP + UTF-8 JSON（`Content-Type: application/json`）与 `text/event-stream`，无端序/对齐/padding/wire offset。SSE 帧格式固定为 `event: <name>\ndata: <json>\n\n`，以空行分隔事件。

### 4.3 一致性、可见性与数据寿命

请求级一致：同一 `request_id` 内事件**有序**（`sequence_number` 单调递增）；不同请求各自独立。流式"已发送"不等于"已完成"——只有 terminal 事件表示本次调用结束。终态 Usage 一经写入即为账本事实（M-METER），本机制不保留历史。

## 5. 接口设计

### 5.1 逐操作签名、错误与调用演练

**操作**：`POST /v1/responses`（consumer 凭据 `Bearer`）

| 项 | 内容 |
|---|---|
| 请求 | `ResponsesRequest`（§4.1）|
| 成功 | `200 text/event-stream`；§6 事件子集 + 一个 terminal |
| 校验顺序 | 必填字段 → `stream/store` 约束 → 禁字段 → 模型存在 → 能力 `responses=true` → 准入 |
| 幂等/重复 | **非幂等**：同 input 重复调用 = 两次独立模型调用；不提供幂等键 |
| 取消 | Consumer 断开连接即结束本次调用（§7）|
| 期限 | 准入等待 ≤ 30s；后端建连/首字节 30s；SSE 空闲 60s |

**错误（错误码 / 含义 / 合法下一步）**：

| HTTP | code | 触发 | 副作用 | 结果已知性 | 合法下一步 |
|---|---|---|---|---|---|
| 400 | `invalid_request` | 缺必填字段 | 无 | 已知失败 | 修请求重试 |
| 400 | `unsupported_request` | `stream!=true` 或 `store!=false` | 无 | 已知失败 | 改用流式 |
| 400 | `unsupported_field` | 含禁字段 | 无 | 已知失败 | 移除该字段 |
| 400 | `unsupported_model` | 等级不支持 responses | 无 | 已知失败 | 换模型 |
| 404 | `model_not_found` | 等级不存在 | 无 | 已知失败 | 换模型 |
| 429 | `rate_limit_exceeded` | 队列满 / 等待超 30s | 无 | 已知失败；**未调用后端** | 按 `Retry-After` 重试 |
| 5xx | `provider_unavailable` / `internal_error` | 后端失败 / 内部错误 | 可能已调用后端 | 见 §9 | 见 §9 |

**调用演练（一份具体输入）**：`{"model":"Worker","input":[{"role":"user","content":"hi"}],"stream":true,"store":false,"max_output_tokens":20}` → 校验通过 → 记义务 → 准入得候选 → 调用 `dep_local_gemma` → 归一 → SSE：`response.created` → `output_item.added` → `output_text.delta` → `output_text.done` → `output_item.done` → `response.completed` → `data: [DONE]`。

## 6. 正常端到端流程

![推理与流式返回时序](../../assets/diagrams/diagram-mech-infer-sequence.png)

[可编辑 SVG 源](../../assets/diagrams/diagram-mech-infer-sequence.svg)

图 M · 推理与流式返回时序（实线=请求，虚线=响应；先后关系非时间比例）。

编号步骤：

1. **入口** 信任判定（见 M-INFER §3.1；凭据在入口单点校验，Principal 下传）→ 生成 `request_id`。
2. **校验** 必填/`stream·store`/禁字段/模型存在/能力（§5.1 顺序）；失败即错误出口。
3. **记义务** `usage.authorize_dispatch` 写 unknown Usage 义务（M-METER）。
4. **准入** `router.admit(level)` 取许可并选候选；超限 → 429。
5. **绑定** `usage.bind_backend` 记最终 provider/deployment（M-METER）。
6. **调用** `adapter.complete(backend_model, body)` → `ProviderResult`。
7. **归一** 构造终态 `ResponsesResponse`（status/output/usage）。
8. **流式** `response_stream` 逐事件发送（§4.2 帧格式），终止于一个 terminal + `[DONE]`。
9. **终态** `usage.finish(usage)`；异常路径 `finish(None)`（unknown）。

### 6.1 交叠请求、跨轮次与生命周期边界

一次调用 = 一个生命周期（校验→准入→调用→流式→终态）。**交叠**：多个请求共享同一 LLMTier，各自独立；准入通过许可/队列串行化对同一 deployment 的并发。同一 `request_id` 内事件有序；跨请求无顺序保证。

## 7. 分支和替代流程

| 分支 | 触发 | 处理 |
|---|---|---|
| 队列满 | 同等级等待 > 32 | 立即 429 + `Retry-After: 30`；未调用后端 |
| 等待超时 | 排队 > 30s | 429 + `Retry-After: 1` |
| 后端不可用 | 建连/首字节失败 | `provider_unavailable`；记 unknown usage |
| 后端超时 | 超过 30s / 空闲 60s | 结束本次调用；**不重放**（避免重复输出）|
| 客户端断开 | Consumer 关闭连接 | 结束本次调用；`finish(None)`；不创建可恢复 Invocation |
| 工具调用 | 后端返回 function_call | 发送 `function_call_arguments.*`；由 Consumer 执行并新请求回传 |
| refusal | 后端返回 refusal | 发 `response.refusal.*`，不伪装为 output_text |

## 8. 状态机与不变量

| INV-ID | 可验证断言（量词、条件和预期必须明确） | Enforcement / 事实来源 | 反例输入/违反后的结果 | 验证项 |
|---|---|---|---|---|
| INV-1 | ∀ output item：`added`/`delta`/`done`/terminal 中 `id` 完全一致 | 出口序列化（§14.4 HTTP/SSE Adapter）| 同 item 出现两个 id → Consumer 无法拼接，输出错乱 | T-STREAM |
| INV-2 | ∀ 请求：恰好一个 terminal 事件，且 `sequence_number` 自 0 严格递增 | `response_stream` 单次出口 + `admit` | 0 或 2 个 terminal → Consumer 无法判定结束 | T-STREAM |
| INV-3 | ∀ 请求：仅 terminal 表示完成；`response.created.status=in_progress` ≠ 成功 | 出口状态机（§6）| 以 `in_progress` 判成功 → 误判成功 | T-STREAM |
| INV-4 | ∀ 记录：`usage=null` 或 `measurement_status=unknown` 时 token 字段为 NULL（**≠ 0**）| UsageRecorder（M-METER）| 未测写成 0 → 被误读为"没有调用" | T-MET-UNKNOWN |
| INV-5 | ∀ 校验失败/429：未调用后端（零副作用）| 校验在 dispatch 前（§5.1、§14.4）| 校验后仍发出后端调用 → 无谓消耗与计费 | T-QUEUE |

### 8.1 资源预留、交付、释放与复位

准入许可是**临时资源**：`admit` 获取，请求结束（成功/失败/断开）在 `finally` 中释放并 `notify_all`。无租约、无持久预留。释放后无残留状态（观测数据独立，见 M-OBS）。

## 9. 失败传播、重试与恢复

| Failure ID / 检测方 | 失败点与传播 | 结果已知性 | 已发生/可能副作用 | 访问安全/证据 | 操作终态 | 资源释放 | 重新准入/重试条件 |
|---|---|---|---|---|---|---|---|
| F-IN-1 / 入口 | 校验失败 | 已知失败 | 无 | 无敏感访问 | 未准入 | 未获许可 | 修请求后重试 |
| F-IN-2 / Router | 队列满/超时 | 已知失败 | 无 | 无 | 429；无调用 | 未分配许可 | 按 `Retry-After` 重试 |
| F-IN-3 / Adapter | 后端 5xx/超时 | **可能未知** | 可能已调用后端 | 后端侧可能已发生 | 记 unknown usage | `finally` 释放许可 | Consumer 按标准 client retry policy；本系统**不自动重放** |
| F-IN-4 / 出口 | 流中途断开（Consumer）| 未知 | 输出已部分送达 | 部分输出已出站 | 结束调用；`finish(None)` | 释放许可 | Consumer 决定；新请求为新调用 |

**边界**：网络结果不明时，Consumer 按标准 client retry policy 处理；本系统不承诺 exactly-once，也不提供结果查询。重放风险由 Consumer 承担（本系统无幂等键）。

## 10. 并发、排序与容量

| 作用域 | 约束来源 | 上限 | 超限行为 |
|---|---|---|---|
| 每 deployment | `deployment_runtime_profiles` | 1 许可 | 排队（同等级）|
| 每 exact 等级 | 内部 admission | FIFO 队列 32 项 | 满 → 429 |
| 准入等待 | 内部 | 30s | 超时 → 429 |
| 每 provider | `provider_usage_profiles` | max_concurrent / RPM / min_interval | 排队/限流 |
| 入口请求体 | HTTP 层 | 2 MB | 413 |

**排序**：同等级内按 `ordinal` 选择 in-flight 最少者；队列 FIFO。**饱和度**：队列满即拒绝（不无限缓冲）。以上为**首版 Specified 保护值，尚未实测**。

## 11. 安全、权限与信任边界

| 入口/资产 | 身份来源 | 授权强制点 | 拒绝 | 审计/观测 |
|---|---|---|---|---|
| `POST /v1/responses` | Bearer（或内网免登录）| 入口 `_auth()` | 401/403 | request_id 日志 |
| Provider Secret | `secret_ref`（env/file）| 适配器调用时解析 | `provider_secret_unavailable` | 不落日志 |
| 上游 token | 后端 | 不进入响应 | — | 仅在 Usage |

信任边界：Consumer 只见自己的用量与模型能力；不得经本机制读取后端内部或他人数据。Secret 只经引用解析（§10.2 系统设计）。本机制无强制点旁路。

## 12. 可观测性与证据

### 12.1 统计、日志、时间与关联

- 响应头 `X-Request-ID` = `request_id`；可透传关联标识（M-OBS）。
- 入口/适配器失败写脱敏日志（module=http/provider）；不含 prompt/output/Secret。
- M-OBS 在 `received/validated/routed/upstream_started/upstream_ended/completed|error` 各阶段写 trace 与快照（fail-open）。

### 12.2 维护命令、自检与调试路径

| Maintenance API / Command / Diagnostic ID | 执行位置、入口、目标、权限 | 完整请求/语法与结果/错误契约 | 施加/回读点及覆盖 | 依赖/占用/恢复退出 | 验证 |
|---|---|---|---|---|---|
| 探测后端 `POST /v1/probes` | LLMTier → 目标后端；operator | 请求 = deployment；结果 = 探活结果；错误 401/403/404 | 施加=目标后端探测；回读=探测结果 | 需 operator；不占数据面许可 | T-OBS 探针用例 |
| 运行时快照 `GET /v1/runtime` | LLMTier 管理面；operator | 无参数；结果 = 并发/队列现状 | 只读 | 无 | 并发用例 |
| 单请求 trace `GET /v1/trace/{request_id}` | LLMTier 管理面；operator | 路径 = `request_id`；结果 = 有序 stages + usage | 只读 | 依赖 M-OBS | T-OBS-TRACE |
| `LLMTIER_SLOW_ADAPTER_DELAY` | 进程环境变量（**仅测试**）| 数值 = 秒；无 HTTP 契约 | 仅测试注入 | 仅测试；非生产协议 | T-TIMEOUT |

## 13. 配置、兼容与部署

- 后端与等级来自 Registry（SQLite authority）；本机制不热载。
- 超时（30s/60s）、队列（32）、等待（30s）、请求体（2MB）为部署/内部配置；变更需审计并复测。
- 兼容：只认标准 Responses shape；`stream`/`store` 固定；版本变化走显式契约变更。
- 部署：随单一实例启动；无独立进程。

## 14. 跨责任单元分解与接口分配（下级设计输入）

本章是**要求侧**：把本机制分解到各责任单元（LLMTier 为纯软件，责任单元 = 软件模块），说明每个对象必须负责什么、向其他对象提供什么接口。下级模块设计在附录"机制承接表"逐条记录**落实侧**，确保无遗漏。软件模块取自系统设计 §3.2 的架构模块，模块内组件取自 `llmtier-core-design.md`。

### 14.1 参与方到架构对象映射

| 机制参与方（§3） | 责任单元/Owner | 架构对象 ID / 类型 / 层或领域 | 下级设计文档 | 在本机制中的主责与非职责 |
|---|---|---|---|---|
| 入口/出口 | HTTP API / LLMTier | HTTP/SSE Adapter（入口层模块）| `llmtier-core-design.md` | 终止 HTTP/SSE、路由、信任判定、SSE 帧序与 terminal；不承载业务规则 |
| 推理编排 | Inference / LLMTier | Inference 编排（业务层）| `llmtier-core-design.md` | 校验、编排、归一；不管理配置 |
| 准入与选择 | Inference / LLMTier | Internal Admission、Exact Model Router（业务层）| `llmtier-core-design.md` | 许可/队列、同等级候选；不做跨等级 fallback |
| 后端调用 | Inference / LLMTier | Provider Adapter（业务层）| `llmtier-core-design.md` | 协议映射、usage 归一；不对外暴露 provider KV |
| 记账 | Inference / LLMTier | Usage Recorder（业务层，M-METER）| `llmtier-core-design.md` | 义务/绑定/终态 record version；不含 Cost |
| 配置读取 | Management / LLMTier | Registry/Config（业务层）| `llmtier-core-design.md` | 等级/能力/provider（只读）；不发起推理 |
| 观测 | Observability / LLMTier | 诊断写入（业务层）→ `libdiag`（基础层）| `llmtier-diagnostics-design.md` | trace/快照，fail-open；不改推理契约 |
| 存储/日志 | LLMTier | Store / 脱敏日志（基础层）| `llmtier-core-design.md` | 唯一持久化、运行日志 |

### 14.2 功能和步骤到责任单元分配

| Capability / Process Step / Constraint | 主责架构对象 | 协作对象 | 必须产生或消费的结果 | 固定行为 / 本地自由度 | 组合验证责任 |
|---|---|---|---|---|---|
| Step 1 信任判定、生成 `request_id` | HTTP/SSE Adapter + Auth/Validation | Store（信任原语）| `Principal`、`request_id` | 凭据解析可自定；`Principal` 语义固定 | 契约 + 组合 |
| Step 2 请求校验（字段/能力）| Auth/Validation | Registry/Config | 通过或 typed error | 实现可自定；**校验顺序固定**（§5.1）| 契约 |
| Step 3 记 unknown 义务（C-INFER-3）| Usage Recorder | — | 义务行（unknown）| 存储布局可自定；未测不补零固定 | 系统用例 |
| Step 4 准入 + 选后端（C-INFER-4）| Internal Admission + Exact Model Router | Registry/Config | permit（许可）+ candidate | 排序实现可自定；仅同等级固定 | 并发用例 |
| Step 5 绑定后端 | Usage Recorder | — | provider/deployment 绑定 | — | 系统用例 |
| Step 6 调用后端 | Provider Adapter | — | `ProviderResult`（usage/status/error）| 各后端映射可自定；typed error 固定 | 契约 |
| Step 7 归一响应 | Inference 编排 | — | `ResponsesResponse` | 实现可自定；shape 固定 | 契约 |
| Step 8 流式发送（C-INFER-1/2）| HTTP/SSE Adapter | — | SSE 事件序 + 一个 terminal | 缓冲可自定；事件子集与终态固定 | 组合（Piko 联调）|
| Step 9 终态记账 | Usage Recorder | — | 最新 record version（或 unknown）| 版本实现可自定；head 单调固定 | 系统用例 |
| 全程观测（C-INFER-5）| Observability → `libdiag` | — | trace/快照（fail-open）| 存储/聚合可自定；fail-open 固定 | 观测用例 |

### 14.3 责任单元间接口契约

| 接口成员 ID / 固定 baseline | 提供对象 | 全部消费对象 | 调用/事件形态 | 本机制固定的语义与错误 | 期限/取消/重复及边界 |
|---|---|---|---|---|---|
| `_auth()` / `authenticate_any()` | Auth/Validation | HTTP/SSE Adapter | 函数 | 由凭据得 `Principal` | 401/403 |
| `ResponsesService.create(principal, request_id, body)` | Inference 编排 | HTTP/SSE Adapter | 函数 | 编排单次调用并返回终态 `ResponsesResponse` | `ApiError`（§5.1）|
| `response_stream(response)` | HTTP/SSE Adapter | HTTP/SSE Adapter | 生成器 | 终态响应 → SSE 帧序 + terminal | 顺序由 §8 INV-2 约束 |
| `Router.admit(level)` | Internal Admission | Inference 编排 | 上下文管理器 | 获取许可 + 候选，退出即释放 | 429 |
| `Router.snapshot()` | Internal Admission | Observability | 只读查询 | 并发/队列现状 | — |
| `Registry.get_service_level(model)` | Registry/Config | Inference 编排 | 只读查询 | 等级 + `capabilities` | 404 |
| `ProviderAdapter.complete(model, body)` | Provider Adapter | Inference 编排 | Protocol | `ProviderResult` | typed error（F-IN-3）|
| `UsageRecorder.authorize_dispatch / bind_backend / finish` | Usage Recorder | Inference 编排 | 函数 | 义务 → 绑定 → 终态 | unknown 语义（§9）|

**共同输入固定**：§6 事件子集（对照 OpenAPI）为出口与 Consumer 的固定共同输入；等级/候选取自 Registry（唯一配置 authority，M-CONFIG）。

### 14.4 下级设计输入清单

| 下级要求 ID | 承接对象 ID / 下级设计文档 | 来源 Capability / Step / Constraint / 接口成员 | 必须负责的行为与保证 | 必须提供/消费的接口 | 下级必须展开的问题 | 允许自行决定的范围 | 本地验证 / 组合验证交接 |
|---|---|---|---|---|---|---|---|
| R-INF-01 | HTTP/SSE Adapter · `llmtier-core-design.md` | C-INFER-1/2、Step 8、interface `response_stream` | SSE 帧序、terminal 唯一、`request_id` 透传、请求体上限 | `response_stream`、`POST /v1/responses` 路由 | 帧缓冲/背压、断开检测与清理、413 | 缓冲与传输实现 | 契约；组合（Piko 联调）|
| R-INF-02 | Auth/Validation · `llmtier-core-design.md` | Step 1–2、interface `authenticate*` | 校验顺序（§5.1）、`Principal` 产生与下传 | `_auth()`/`authenticate_any()` | 凭据解析、错误映射 | 解析实现 | 契约 |
| R-INF-03 | Internal Admission · `llmtier-core-design.md` | C-INFER-4、Step 4、interface `admit` | 并发/队列/等待/429、许可释放 | `admit()`、`snapshot()` | 队列结构、公平性、`Retry-After` | 队列/排序实现 | 并发用例 |
| R-INF-04 | Exact Model Router · `llmtier-core-design.md` | C-INFER-4、Step 4 | 大小写精确选择、同等级候选 | 候选（经 `admit()`）| 选择排序、健康/版本核验 | 排序实现 | 并发用例 |
| R-INF-05 | Provider Adapter · `llmtier-core-design.md` | Step 6、interface `complete` | 协议映射、usage 归一、typed error | `complete()` | 各后端映射、超时、错误分类 | 映射实现 | 契约 |
| R-INF-06 | Usage Recorder · `llmtier-core-design.md` | C-INFER-3、Step 3/5/9 | 义务/绑定/终态、unknown 不补零 | `authorize_dispatch`/`bind_backend`/`finish` | 版本替换、并发写、归一（M-METER）| 存储实现 | 系统用例 |
| R-INF-07 | Registry/Config · `llmtier-core-design.md` | Step 2、interface `get_service_level` | 等级/能力只读查询 | `get_service_level()` | 快照读一致性（M-CONFIG）| 查询实现 | 契约 |
| R-INF-08 | 诊断写入 · `llmtier-diagnostics-design.md` | C-INFER-5 | trace/快照、fail-open | 观测写入 | 默认关闭零开销、脱敏（M-OBS）| 存储/聚合实现 | 观测用例 |

**约束**：下游模块设计不得改变本机制已固定的对外事件子集与错误语义；跨模块新增接口须回写本节并关联模块设计。

## 15. 验证、上线与回滚

### 15.1 输入构造、故障控制与独立判据

| Test / Constraint | 输入与预置事实 | arm/hit/release | 独立 Oracle |
|---|---|---|---|
| T-STREAM / C-INFER-1..2 | 固定 request（Worker）| — | 事件序 + 恰好一个 terminal（对照 OpenAPI 子集）|
| T-TOOLS / CAP-TOOLS | 带 `tools` | — | `function_call_arguments.*` 出现或 200 完整（上游行为不作断言）|
| T-QUEUE / C-INFER-4 | 预置占满队列 | 并发请求 | 429 + `Retry-After` |
| T-TIMEOUT / §7 | `LLMTIER_SLOW_ADAPTER_DELAY` | 设置/清除 | 超时错误 + 许可释放 |
| T-DISCONNECT / §7 | 主动断开 | — | 结束调用；`finish(None)` |

### 15.2 环境部署、复位、并发隔离与自动化

本机实例 + 隔离数据库；复位 = 重建库 + 重启；并发用例验证队列上限与 429。

### 15.3 组合验收、启用与旧机制退出

组合验收 = Consumer（Piko）真实调用 + 联调；`runtime_activation` 由独立门禁批准（LT-OPEN-03）。legacy `/call` 退出 consumer authority。

## 16. 风险、未决问题与决定

| ID | 类别 | 影响 | 下一步 | 状态 |
|---|---|---|---|---|
| LT-OPEN-05 | 设计闭合/实现门禁 | 流注入需改造流式输出 | 确认实现方案 | 未决 |
| RISK-INFER-1 | 风险 | 后端长尾延迟导致超时/429 | 由超时与 429 约束；实测后调参 | 观察 |

## A. 输入基线、适用性与图文规则

- 输入：系统设计 §3/§7.2/§9.1；`LT-ADR-01/04`；`interfaces/openapi/llmtier.openapi.json`。
- 适用性：纯软件、单进程、HTTP API 机制。§4.2（二进制 ABI）不适用；§8.1（租约/持久预留）不适用（仅临时许可）。
- 图：时序图（§6）表达请求/响应与等待；已有系统设计 §7.2 同源。

## B. 文档控制与修订记录

初版见 Git 历史；本版（`0.1.0-draft.3`）补实全部章节并加入时序图。
