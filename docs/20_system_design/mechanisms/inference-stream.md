<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier 推理与流式返回机制

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-inference-stream-mechanism` |
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
| Canonical Path | `docs/20_system_design/mechanisms/inference-stream.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 机制摘要：解决什么问题

一次模型推理请求如何从入口到后端再到流式返回，包含准入、后端选择、SSE 归一以及失败与中断处置。这是数据面主路径。

## 2. 使用场景与功能

Consumer 提交 `POST /v1/responses`（`stream:true/store:false`）或 `POST /v1/embeddings`；系统校验、路由、调用后端并返回标准响应与 token Usage。

## 3. 参与方、责任和 authority

### 3.1 系统约束与参与方承接

参与方：入口层（HTTP/SSE）、Inference（编排）、基础层（信任/供应商适配/计量）。Authority 为 LLMTier。

### 3.2 运行时统筹与确认责任

入口层统筹请求生命周期与 request_id；Inference 负责路由决策；后端负责生成。终态由出口统一确认。

### 3.3 拓扑、目标身份与共享故障域

单节点；后端为外部依赖，其故障域独立；系统不承诺跨系统 exactly-once。

## 4. 数据结构设计

### 4.1 类型目录与完整字段

标准 OpenAI Responses/Embeddings 请求与响应；SSE 事件子集见系统设计 §7.2。内部调用 DTO 含 exact model、候选 deployment、request_id。

### 4.2 编码、布局与共享类型映射

字段级权威为 `interfaces/openapi/llmtier.openapi.json`。

### 4.3 一致性、可见性与数据寿命

请求级寿命；无跨请求状态。

## 5. 接口设计

### 5.1 逐操作签名、错误与调用演练

- `POST /v1/responses` → 200 `text/event-stream`；
- `POST /v1/embeddings` → 200 JSON；
- 错误：validation/auth/model_not_found/rate_limit/provider_unavailable/internal_error。

## 6. 正常端到端流程

信任判定 → schema 校验 → exact model 选择 → 准入排队 → 选择后端 → 调用 → 归一为 SSE/JSON → 终态事件 → 关闭。

### 6.1 生命周期过程与交叠操作

同一 request_id 内事件有序；交叠请求各自独立。

## 7. 分支和替代流程

- 队列满/等待超 30s → 429 + Retry-After；
- 后端不可用 → provider_unavailable；
- 客户端断开 → 结束本次调用，不创建可恢复 Invocation。

## 8. 状态机与不变量

不变量：每个 output item 有稳定 id；delta/added/done/terminal 一致；一个 terminal 事件。

### 8.1 资源预留、交付、释放与复位

准入许可在请求结束（含失败/断开）时释放。

## 9. 失败传播、重试与恢复

超时只结束本次 HTTP 调用；不自动重放（避免重复输出）。调用方按标准 client retry policy 处理网络结果不明。

## 10. 并发、排序与容量

每 deployment 一个许可；每 level 最多 32 项 FIFO 队列；选择 in-flight 最少者。

## 11. 安全、权限与信任边界

需 consumer 凭据；Provider Secret 只经引用解析，不进入响应/日志。

## 12. 可观测性与证据

### 12.1 统计、日志、时间与关联

响应头 `X-Request-ID`；可接收标准 trace context；观测机制记录快照/统计/trace。

### 12.2 维护命令、自检与调试路径

`POST /v1/probes` 探测后端；观测端点见可观测性机制。

## 13. 配置、兼容与部署

后端与等级来自 Registry（SQLite 权威）；timeout 固定 30s/60s。

## 14. 各参与方实现清单

| 参与方 | 义务 |
|---|---|
| 入口层 | SSE 帧、终态、request_id |
| Inference | 校验、路由、归一 |
| 基础层 | 信任、适配器、计量写入 |

## 15. 验证、上线与回滚

### 15.1 输入构造、故障控制与独立判据

用例覆盖成功、拒绝、429、后端失败、流异常；判据为状态码与事件序。

### 15.2 环境部署、复位、并发隔离与自动化

测试实例隔离；并发用例验证队列上限。

### 15.3 组合验收、启用与旧机制退出

legacy `/call` 退出 consumer authority。

## 16. 风险、未决问题与决定

- `LT-OPEN-05`：流注入需改造流式输出；
- 风险：后端长尾延迟；由 timeout 与 429 约束。

## A. 输入基线、适用性与图文规则

输入：系统设计 §7.2、`LT-ADR-01/04`。

## B. 文档控制与修订记录

初版 `0.1.0-draft.1`；修订见 Git。
