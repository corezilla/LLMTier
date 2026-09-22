# HANDOFF：LT-OBS 可观测性与调试能力实现（Piko 联调输入）

- 日期：2026-09-22
- 提出方/验收方：Piko 联调方（corezilla/piko，branch `docs/piko-system-design-std26`）
- 实现方：LLMTier
- 需求 authority：`docs/10_requirements/llmtier-observability-debug-requirements-v0.1`（draft.3，LT-OBS-1..6）
- 联调证据：Piko `tests/integration/reports/piko-llmtier-joint-report-v0.1.md`（发现 F-2/F-4/F-5/F-6）

## 0. 一句话任务

按 `llmtier-observability-debug-requirements-v0.1` 实现 **LT-OBS-1..6**（可观测性与调试能力），
实现后由 Piko 联调方 **review 代码 → 联调复核（JT-07/08/13/17、S0-2）→ 双方关闭**。
本文件解释为什么要做、六类白盒手段各自的要求，以及验收与协作方式。

## 1. 背景：联调是白盒测试，观测能力是第一等能力

Piko ↔ LLMTier 联调是**白盒联合调试**：允许通过改变实现与配置来发现和定位问题，目标是
**最快调通功能、发现并消灭所有已知 bug**。联调中暴露的真实问题（Piko 侧已修复 2 个分类缺陷、
实现 1 个恢复语义）都依赖观测手段定位；同时也暴露了 LLMTier 侧的观测缺口——
**"知道有问题，却定位不出是哪一层、哪个请求、哪个上游调用"是不可接受的状态**。

跨服务失败定位的实际案例（已发生）：Piko 收到 `ModelResponseInvalid`，真正的故障是
LLMTier 上游(oMLX)连接被拒（503 provider_unavailable）。当时只能靠 Pi 会话 JSONL + 时间窗
+ 两侧 SQLite 手工拼证据才定位。LT-OBS-1/2/6 就是要把这条定位链产品化。

## 2. 白盒调试六法：介绍与 LLMTier 实现要求

六类手段在跨服务联调中的角色（Piko 侧均已具备或实现，LLMTier 侧按下表补齐）：

| 手段 | 定义 | 在跨服务联调中的用法 |
|---|---|---|
| 探针 | 对节点/路径的快速存活与可用性判定 | 判定故障在哪一层（consumer/tier/backend） |
| 流程改变的调试开关 | 运行时改变处理路径，让故障/慢速/限流路径**确定性**复现 | 注入上游错误、时延、限流、流异常，验证 consumer 处置 |
| 统计 | 计数、分布、增量对账 | 暴露丢失/重复/突增；错误率与时延恶化可见 |
| 日志 | 过程事实与错误现场 | 请求是否到达、返回什么、为什么错 |
| 数据快照 | 任意时刻证据定格，支持事后比对 | 请求级定格（输入/输出/状态/时延），事后定位不依赖进程存活 |
| 环回 | 捕获节点收发的原始数据 | 看到本节点实际发出去什么、收回来什么 |

### 2.1 探针（probe）——现状已满足，要求不回归

- **现状**：`GET /healthz`、`GET /readyz`、`POST /v1/probes`（按 deployment 探活）。
- **实现要求**：
  - LT-OBS 落地过程中**不得回归**：探针保持现有语义与性能；
  - probe 结果继续进入 audit（现状已满足）；
  - readyz 语义按 **LT-OBS-4** 修正（占位 service level 不得降级全局状态）。
- **验收**：现有 probe 行为不变；占位场景下全局 `ready`（见 requirements §4 LT-OBS-4）。

### 2.2 流程改变的调试开关（fault/latency/rate-limit/stream injection）——LT-OBS-5

- **定义**：运行时可切的开关，把处理流程改道到故障/慢速/限流/流异常路径，使 consumer 侧的
  错误处理、重试、预算语义可以**确定性**触达，而不是靠运气复现。
- **实现要求（LT-OBS-5）**：admin 控制、按 deployment 生效、运行时可切、可随时关闭：
  1. 上游故障注入：502/503（带错误体）；
  2. 时延注入：上游响应 +N ms；
  3. 限流注入：429 + Retry-After；
  4. **上游流提前终止**：SSE 已发部分事件即断开（验证 consumer 流中断处置）；
  5. **畸形流事件**：违反 Responses 事件序/非法 JSON 事件（验证 consumer 流解析健壮性）。
- **硬性约束**：默认关闭且关闭时零开销；注入不持久；非注入流量不受影响；注入事件在
  logs/audit 可见；**不污染 usage 账本语义**（注入调用需可标注/区分）。
- **验收**：见 requirements §4 LT-OBS-5 每条验收标准。
- **为什么需要**：联调 case JT-17（502 带体分类、时延可观测、429 处置）与场景回归中的
  流异常路径，当前**无法确定性触达**——这是白盒手段里唯一完全缺失的一类。

### 2.3 统计（statistics）——LT-OBS-2

- **定义**：请求计数、错误计数、时延分布的聚合查询，支持时间窗。
- **实现要求（LT-OBS-2）**：按 model 与 HTTP status 的请求数、错误数、P50/P95 时延；
  管理面可查、时间窗过滤；时间窗外不计入；两次查询计数可区分并累加。
- **用途**：联调中前后增量对比（一个 case 前后统计必须可解释）；错误率突增直接可见。
- **验收**：requirements §4 LT-OBS-2。

### 2.4 日志（logs）——现有 + LT-OBS-1 细化

- **现状**：`/v1/logs`（HTTP 访问行：时间/level/module/message/request_id）+ service stdout。
- **实现要求**：
  - LT-OBS-1 落地时，上游调用失败/异常的**错误体摘要**进入日志或快照查询（截断，见 §3 约束）；
  - `request_id` 保持贯穿（现状已满足）；
  - 日志子系统故障 fail-open，不得影响 Data Plane 可用性。
- **验收**：一次失败请求可在 logs 中找到对应行与状态；上游错误摘要可见（或经 LT-OBS-1 快照查询）。

### 2.5 数据快照（snapshot）——LT-OBS-1 + LT-OBS-6

- **定义**：请求级证据定格，进程死后仍可查。
- **实现要求**：
  - **LT-OBS-1**：每个 Data Plane 请求的上游调用快照——上游 URL、backend_model、HTTP status、
    时延 ms、错误体摘要（截断）；调试开关控制，管理面可查；
  - **LT-OBS-6**：按 `request_id` 的**单请求全生命周期 trace**——接收时间、校验结果、路由
    （service level/deployment）、上游调用快照、SSE 终止原因（completed/error/aborted）、
    usage 记录（含 record_version）一次查全。
- **用途**：consumer 拿到 `x-request-id` 后即可单点定位"哪一层、哪一跳、什么错"。
- **验收**：requirements §4 LT-OBS-1/LT-OBS-6。

### 2.6 环回（loopback）——LT-OBS-1（与数据快照同源）

- **定义**：捕获本节点实际收发的原始数据。
- **实现要求**：LT-OBS-1 的上游调用环回 = 记录 LLMTier 发给 oMLX 的请求事实与收到的响应
  （URL/status/时延/错误体摘要）；**不落完整 prompt/输出正文**（安全约束：长度、哈希、截断
  摘要允许）。
- **用途**：区分"consumer 发错"vs"LLMTier 转发改错"vs"oMLX 返回错"。
- **验收**：同 LT-OBS-1。

## 3. 三个定位/自诊断场景（要求映射）

### 3.1 LLMTier 自身出问题 → 自己快速找出并修复

用途链：**LT-OBS-2 统计**（错误率/时延异常先被发现）→ **LT-OBS-6 trace**（按 request_id 看
单请求全生命周期与逐跳时间戳）→ **LT-OBS-1 上游快照**（上游交互定格）→ **LT-OBS-5 注入开关**
（修复后在同类故障下复现验证）→ logs/audit 佐证。
要求：以上全部**管理面自助可得**，不依赖 consumer 提供信息（见 requirements §4/§5）。

### 3.2 联调失败 → 快速定位是 Piko / LLMTier / oMLX 哪个的问题

三方定位矩阵（Piko 侧 `scripts/joint-diagnose.sh` 按 §7.1 决策树执行；LLMTier 侧按本表配合）：

| 症状（consumer 视角） | LLMTier 侧证据（LT-OBS-1/2/6） | 归属判定 |
|---|---|---|
| `Failed/ModelUnavailable` + B 窗口内有 5xx/上游错误快照 | 上游调用快照可见失败 | **oMLX**（或 B→C 网络） |
| `Failed/ModelUnavailable` + B 窗口内**无任何**该请求记录 | 请求未到 B | **网络 / B 未启动**（B 侧） |
| B logs 出现 400/404 校验拒绝 | 请求被 B 校验拒绝 | 请求形状问题：对照 Piko 会话 JSONL 判 **Piko 装配**；形状合法 → **B 校验过严**（对照 ICD/OpenAPI） |
| B 返回 200 但 consumer 解析 SSE 失败/流异常 | B 侧响应体/流快照异常 | **LLMTier 内部**（序列化/流处理） |
| `Failed/ToolFailure`、`Budget/Deadline`、`UnsafeRetryBlocked` | Piko 自身语义 | **Piko** |

配套要求：**LT-OBS-6 逐阶段时间戳**（received/validated/routed/upstream_started/upstream_ended/
completed）使每跳时延可计算；**LT-OBS-7 consumer 关联标识透传**使 LLMTier 侧可反查"这是哪个
consumer run"（双向定位）。

### 3.3 联调报告的审计证据 → 功能需求

报告每 case 需要引用的请求级证据，映射为 LLMTier 功能：

| 报告证据 | 功能需求 |
|---|---|
| 请求级事实（谁/何时/状态/tokens） | usage 账本（已有）+ **LT-OBS-6 trace** |
| 增量/对账统计 | **LT-OBS-2 统计查询**（支持导出 JSON） |
| 管理动作记录 | audit（已有；LT-OBS-3 明示范围） |
| 证据保留窗口 | 观测数据保留 ≥7 天（LT-OBS-6 已含，与既有 retention 对齐） |

## 3. 实现需求清单（每法 ↔ 需求 ↔ 状态）

| 白盒手段 | 需求 ID | 要点 | 状态 |
|---|---|---|---|
| 探针 | 既有（LT-OBS-4 相关） | healthz/readyz/probes 不回归；占位不降级全局 | 待实现（LT-OBS-4） |
| 流程改变的调试开关 | **LT-OBS-5** | 故障/时延/限流/流终止/畸形流 注入，admin 控制 | 待实现 |
| 统计 | **LT-OBS-2** | 按 model/status 计数 + 时延分布 + 时间窗 | 待实现 |
| 日志 | LT-OBS-1（细化） | 上游错误摘要可见；request_id 贯穿；fail-open | 待实现（随 LT-OBS-1） |
| 数据快照 | **LT-OBS-1 / LT-OBS-6** | 逐请求上游快照 + 单请求全生命周期 trace | 待实现 |
| 环回 | LT-OBS-1 | 上游调用环回（不含正文） | 待实现（随 LT-OBS-1） |
| 审计语义（附带发现） | **LT-OBS-3** | audit 覆盖范围在管理控制文档明示 | 待补充文档 |

## 5. 全局实现约束（所有 LT-OBS 共同）

1. 默认关闭、关闭零开销；开启时异步/尽力而为，**不得阻塞推理流**；
2. 观测子系统自身故障 fail-open；
3. 不记录 Provider Secret、consumer credential、完整 prompt/输出正文（长度/哈希/截断摘要允许）；
4. 注入（LT-OBS-5）不得写坏 usage 账本语义（可标注 injected）；
5. 遵守仓库测试规范：provider endpoint 使用 LAN IP；提交前全量测试通过。

## 6. 验收与 review 流程

1. 实现分支上完成 LT-OBS-1..6 + 全量测试通过（`PYTHONPATH=src python3 -m pytest tests/ tests/system/st_*.py -q`）；
2. **Piko 联调方 review**：逐条对照 requirements §4 验收标准 + 本文件 §2 各条；
3. 联调复核（Piko 侧执行，结果回填联调报告）：
   - S0-2：`readyz=ready`（LT-OBS-4）；
   - JT-07/08 复跑：失败分类不回归；
   - JT-13：统计/审计语义符合 LT-OBS-3；
   - **JT-17**：注入 502 带体 / 时延 / 429（LT-OBS-5）三段全过；
   - LT-OBS-1/6：给定 `x-request-id`，trace 一次查全（对照 Piko `provider_calls`）。
4. 双方关闭：报告更新（发现 F-2/F-4/F-5/F-6 收口）。

## 7. 联调环境参考（复核用）

| 项 | 值 |
|---|---|
| LLMTier joint | `192.168.1.8:8180`（0.0.0.0），`state/llmtier-piko-joint.sqlite3` |
| Piko joint | `127.0.0.1:8788`，`config/runtime.llmtier.json` |
| admin token | `~/piko-secrets/llmtier-joint-admin-token` |
| data token | `~/piko-secrets/llmtier-joint-data-token`（Piko 已持久化出站调用 `provider_calls`，含 x-request-id） |
| consumer 证据 | `x-request-id` == usage 账本 `request_id`（已实测一致） |
| consumer 定位工具 | `piko/scripts/joint-diagnose.sh <run_id>` |
