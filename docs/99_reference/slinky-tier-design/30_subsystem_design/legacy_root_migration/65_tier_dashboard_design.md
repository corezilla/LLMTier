# Tier Dashboard 设计规范

Version: v1.8
Last Updated: 2026-09-08 13:21:23
Status: Draft

---

## 1. 目标

Tier Dashboard 是 `llm_tier` 的运行控制与观测界面，对应实现文件：

```text
src/dashboard/tier.html
```

它用于展示和操作：

- Tier / Backend / Account 配置与状态；
- Backend running 数量；
- Account 并发、调用间隔、额度使用；
- Backend enable / disable；
- Backend probe；
- Recent Errors；
- LLM Stats By Tier / Stage；
- Runtime debug 开关。

Tier Dashboard 不是路由器，也不是额度判断器。所有状态必须来自 Tier Server 的 `/runtime`、`/llm-stats`、`/reload`、`/probe`、`/backend-state` 等接口。

Tier Dashboard 的 API base固定使用当前页面地址栏的`window.location.origin`。例如用户访问`http://192.168.1.9:<dashboard-port>/tier.html`，页面请求只发送到同origin的`/api/tier/*`和`/api/llm-stats`。页面不得提供API base输入框，不得从localStorage读取server URL，也不得硬编码`127.0.0.1:8765`；Dashboard server通过`TierClient`连接loopback Tier HTTP Service。

---

## 2. 核心概念

### 2.1 Tier

Tier 是 role 到 backend 池的路由层，例如：

```text
Senior
Junior
Worker
Associate
Foreman
Engineer
Executor
```

Tier Dashboard 必须按配置顺序展示 Tier。

### 2.2 Account

Account 是 provider 账号级资源，负责：

- 最大并发；
- 调用间隔；
- quota usage；
- reset 时间；
- calls / tokens 统计；
- provider credentials；
- 对 MLP / remote agent backend 的连接参数。

Account 示例：

```text
xf2
mnm
volc
omlx8
omlx9
```

### 2.3 Backend

Backend 是一个 Tier 中的一个 Account + Model 组合。

规范定义：

```text
backend = tier:account:model
```

显示格式：

| Backend type | 显示格式 |
|--------------|----------|
| API | `account/model` |
| CLI | `cli: account/model` |
| MLP | `agent: account/model` |

示例：

```text
xf2/Qwen3-Coder-Next-FP8
opencode: mnm/MiniMax-M3
opencode: volc/glm-5.2
m5air: mnm/MiniMax-M2.5
m5air: omlx9/gemma-4-e2b-it-4bit
```

约束：

- Dashboard 操作 backend 时必须使用完整 backend key；
- enable / disable 一个 backend 只能影响该 Tier 下该 Account + Model；
- 相同 account/model 出现在不同 Tier 时，不能互相联动关闭；
- Account 状态可以被多个 backend 共享，但 Backend enabled 状态不能共享。

---

## 3. Backend 状态模型

稳定状态只允许：

| 状态 | 含义 |
|------|------|
| `disabled` | 用户关闭，不参与 probe 和路由 |
| `probing` | 正在 probe |
| `running` | 可路由 |
| `unreachable` | 网络、认证或服务不可达 |
| `exhausted` | 额度耗尽或 provider 流控 |
| `failed` | 配置错误或不可恢复错误 |

约束：

- 不再使用 `selected`；
- 不再使用 `ok` 作为状态；
- `enabled` 不是稳定状态，只表达用户未禁用；
- Probe 成功后进入 `running`；
- LLM 请求成功后保持 `running`；
- LLM 请求失败或超时达到阈值后进入 `unreachable`；
- LLM 请求返回额度耗尽或流控后进入 `exhausted`；
- `disabled` 必须由用户操作或配置产生。

Dashboard 图标：

- Backend 名称前显示状态图标；
- 状态文字通过 hover tooltip 展示；
- 不单独显示 Status 列；
- `probing` 必须显示动画状态；
- Probe 期间 probe 按钮 disabled。

---

## 4. 路由与 running 展示

Tier Dashboard 展示的 running 是 Backend 当前运行中的请求数。

Account 表展示：

```text
account running / account max concurrency
```

Backend 表展示：

```text
backend running
```

约束：

- Backend 不再展示 max concurrency；
- max concurrency 属于 Account；
- Tier 行可以展示该 Tier 当前 running 总数；
- Tier 的 max 不再由 backend 求和显示为权威值；如需展示，只能按 Account 当前可用并发解释。

---

## 5. Account 表

Account 表必须展示：

| 字段 | 含义 |
|------|------|
| Account | Account key |
| Provider | provider 名称 |
| Backends | 使用该 account 的 backend 数量 |
| Usage | 额度使用 |
| Calls | account 维度 calls |
| Tokens | account 维度 tokens |
| Interval | 调用间隔 |
| Timeout | 请求 timeout |
| R/M | `running / max concurrency` |

可编辑字段：

- max concurrency；
- interval；
- timeout；
- credentials 或 endpoint 只能通过配置文件或明确接口修改，不能由 JS 自行生成。

---

## 6. 顶部摘要

顶部摘要只能展示 `/runtime` 明确返回的字段，不得由 Dashboard 自行扫描 backend 行推断。

必须显示：

- `Jobs`：来自 `/runtime.jobs.running`；
- `Calls`：来自 `/runtime.summary.total_calls`；
- `Tokens`：来自 `/runtime.summary.total_tokens`；
- `Exhausted`：来自 `/runtime.summary.exhausted_count`；
- `Upshift`：来自 `/runtime.summary.upshift_count`；
- `Started`：来自 `/runtime.started_at`；
- `Uptime`：来自 `/runtime.uptime_seconds`。

约束：

- `Upshift` 表示 Router 实际将 Worker / Associate 请求提升到 Junior 的次数；
- Dashboard 不能通过 trace、错误日志或 backend 行状态推断 Upshift 次数；
- 如果 `/runtime.summary.upshift_count` 缺失，按 0 展示；
- 顶部摘要行必须使用稳定 DOM 节点，初始化后只更新每个字段的 textContent 和状态 badge class；
- `Uptime` 每秒变化时，不得重建整行 summary HTML。

---

## 7. Usage 展示

Usage 按窗口显示：

```text
5hour / weekly / monthly
```

每个窗口使用圆环展示百分比。

### 7.1 有 quota limit

显示：

- 圆环中心显示使用百分比；
- 圆环后显示 reset 时间；
- 颜色按使用率分级：
  - 正常：浅蓝；
  - 较高：黄色；
  - 危险：红色。

reset 时间格式：

| 窗口 | 格式 |
|------|------|
| 5hour | `HH:MM` |
| weekly | `DD HH` |
| monthly | `DD HH` |

### 7.2 无 quota limit

显示：

```text
∞
```

约束：

- 本地模型、无限额度账号、provider 未返回 limit 时可显示 `∞`；
- `∞` 必须与圆环中心对齐；
- Dashboard 不得在 provider usage 查询失败时擅自显示 `∞`；
- 查询失败必须显示错误状态，例如 `!`，并通过 tooltip 或 Recent Errors 暴露原因。

### 7.3 provider usage 查询

Usage 查询由 Tier Server 完成，Dashboard 不直接访问 provider 页面或解析 provider HTML。

Dashboard 行为：

- 页面自动刷新不强制刷新 provider usage；
- 用户点击 Refresh 时调用 `/runtime?refresh_usage=1`；
- Probe 完成后应携带最新可用 usage snapshot；
- usage 查询失败时，Tier Server 必须返回错误来源和摘要。

---

## 8. Backend 表

Backend 表按 Tier 分组展示。

建议列：

| 列 | 说明 |
|----|------|
| Tier | Tier 名称和 Tier running |
| Account/Model | Backend 显示名和状态图标 |
| Type | API / CLI / MLP |
| Weight | 路由权重 |
| Context/Out | 最大上下文 / 最大输出 |
| 5hour | usage |
| weekly | usage |
| monthly | usage |
| R | backend running |
| Action | enable/disable、probe |

约束：

- Weight 平时显示数字，点击后才变编辑框；
- Model 平时显示文本，点击后才变选择框；
- Context/Out 显示整数，不显示小数；
- disabled 状态只显示 `disabled`；
- fail 计数不在主表显示，可通过日志或 Recent Errors 查看。

---

## 9. Model profile

Provider profile 用于定义一个 provider 可选模型：

```text
provider
model_key
model_name
max_context_tokens
max_output_tokens
```

约束：

- 用户选择模型后，`model_key`、`model_name`、`max_context_tokens`、`max_output_tokens` 必须同步更新；
- 模型选择框不显示上下文长度；
- 平时显示正常文本，点击后才进入选择状态；
- 选择后必须通过 Tier Server 保存配置，不能只改前端状态。

---

## 10. LLM Stats

Tier Dashboard 的 LLM Stats 只来自 SQLite-backed stats API。

### 10.1 LLM Stats By Tier

字段：

```text
Tier
Calls
Fail
Total
tok/s
Prompt total/avg/p50/p95/p99
Prompt len avg/p50/p95/p99
Completion total/avg/p50/p95/p99
Completion len avg/p50/p95/p99
Latency avg/p50/p95/p99 (s)
```

约束：

- 不从 summary 读取 stats；
- 不从 JSONL 读取 stats；
- `tok/s` 是 decode 速度统计；
- 所有 tokens 文案统一显示为 `toks`；
- 数字自动使用 K / M 单位；
- 表格字体和列宽必须避免 Total 行换行。

### 10.2 LLM Stats By Stage

Project Dashboard 可读取 stage 维度 stats；Tier Dashboard 可按需要展示全局或当前 workspace stats。

约束：

- 按 stats API 查询，不在 JS 中全量拉 events 聚合；
- 已完成 Stage 的 stats 可以来自 materialized summary 表或 stats API 聚合结果；
- 查询必须支持 `started_at` 过滤。

---

## 11. Recent Errors

Recent Errors 由 Tier Server 返回。

字段：

```text
Time
Tier:Backend
Model
Error
Stage / Phase / Task
Prompt len
```

显示规则：

- Time 格式：`YY-MM-DD HH:mm:ss`；
- 标题显示 `Tier:Backend`；
- 内容可显示 `Tier:Backend:Model`；
- Time 列必须足够宽，不能换行；
- 错误不能由 Dashboard 推断；
- `all_backends_busy` 默认不进入 Recent Errors，只有 debug 开关开启时才记录。

---

## 12. Debug 开关

Tier Server 必须提供 runtime debug 开关接口。

建议维度：

```text
routing
backend_call
usage
probe
stats
http
```

等级：

```text
off
error
info
debug
trace
```

Dashboard 只展示和调用这些接口，不自行记录调试事实。

---

## 13. 加载与刷新模型

Tier Dashboard 初始加载：

1. 读取 `/runtime`；
2. 先展示 Backend / Account 基础状态；
3. usage 使用当前 runtime snapshot；
4. 不等待所有 probe 或 usage refresh 完成后才显示页面；
5. LLM stats 异步加载；
6. 页面根节点只初始化固定 section 容器，不得在每次刷新时重建整个页面。

自动刷新：

1. `/runtime`、LLM stats、Recent Errors 可以分别异步完成；
2. 每类数据只能更新自己的固定区域：Summary、Backend table、Account table、LLM Stats、Recent Errors；
3. Summary 必须按字段更新稳定文本节点；Backend table、Account table、LLM Stats、Recent Errors 若某个 section 的 HTML 与上次一致，不得写入 DOM；
4. LLM stats 或 Recent Errors 返回时不得触发 Backend / Account 表重新绘制；
5. 自动刷新不得把已有内容临时改成 `-`、`…` 或 loading 状态再改回真实值；只有首次加载且确实没有数据时才显示 loading / unavailable；
6. 事件监听只能在对应 section 发生 DOM 更新后重新绑定，避免未变化 section 累积重复事件监听。

用户点击 Refresh：

1. 调用 `/runtime?refresh_usage=1`；
2. Tier Server 刷新 provider usage；
3. Dashboard 更新 usage 和状态；
4. 不重置用户正在编辑的字段。

Probe：

1. 点击 probe 后调用 probe 接口；
2. Backend 状态进入 `probing`；
3. Dashboard 轮询 `/runtime`；
4. probe 完成后显示 `running` / `unreachable` / `exhausted` / `failed`；
5. probe 期间按钮 disabled。

---

## 14. 错误显示规则

Tier Dashboard 必须直接暴露：

- 配置加载失败；
- Account credentials missing；
- provider usage 查询失败；
- backend probe 失败；
- backend state update failed；
- stats API 查询失败；
- runtime snapshot malformed。

Dashboard 不得：

- 把 usage 查询失败显示成 `∞`；
- 把 backend 不可达显示成 `running`；
- 把 JS 本地状态当成 backend 状态；
- 因为同 account/model 相同而跨 Tier 联动 enable/disable。

---

## 15. 测试要求

最低测试覆盖：

- Backend key 包含 Tier，关闭 Worker 的 `omlx8/Qwen3.6-35B-A3B` 不影响 Associate 的 `omlx8/gemma-4-e2b-it-4bit`；
- Usage 查询失败显示错误，不显示 `∞`；
- Refresh 调用 `refresh_usage=1`；
- 自动刷新不调用强制 usage refresh；
- Probe 期间状态为 `probing`，按钮 disabled；
- Probe 成功后进入 `running`；
- Account max concurrency 修改后路由使用新值；
- Weight 点击后才进入编辑状态；
- Model 点击后才进入选择状态；
- LLM Stats 不读取 summary / JSONL。

---

## 16. 实现位置

| 文件 | 职责 |
|------|------|
| `src/dashboard/tier.html` | Tier Dashboard 页面、JS、CSS；只调用same-origin API |
| `src/dashboard/server.py` | 静态页面与`/api/tier/*`、`/api/llm-stats` allowlist proxy |
| `src/llm_tier/server.py` | loopback Tier `/runtime`、`/llm-stats`、`/reload`、`/probe`、debug接口 |
| `src/llm_tier/tier_config.py` | Account / Tier / Backend 配置读取 |
| `src/llm_tier/router_core.py` | Backend 选择、Account 并发、错误状态迁移 |
| `src/llm_tier/stats_collector.py` | SQLite stats 写入与查询 |

---

## 17. 设计约束

- Tier Dashboard 只能展示 Tier Server 明确返回的数据；
- Backend 状态必须由 Tier Server 维护；
- Account 状态与 Backend enabled 状态必须分离；
- 任何操作必须以完整 backend key 为目标；
- 不得在 JS 中建立第二套 backend identity；
- 不得为 RAG、usage、mlexp 或 local model 增加特例配置路径；
- 新展示项必须先定义 server payload，再实现 UI。
