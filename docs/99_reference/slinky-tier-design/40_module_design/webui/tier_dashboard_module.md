# Tier Dashboard Module Design

Version: v1.4
Last Updated: 2026-09-08 13:21:23
Status: Draft

code_directory: `dashboard/tier_dashboard/`
current_source_files: `src/dashboard/tier.html`
provided_interfaces: `WEB-UI-003`, `WEB-UI-004`, `WEB-UI-005`
consumed_interfaces: `TIR-HTTP-002`

## 1. Ownership与职责

所属Subsystem：WebUI。

本Module拥有 Tier Dashboard 页面，以及浏览器侧针对 Tier runtime、stats、usage 和 management 的 UI 交互。

本Module不拥有 Tier Router、Backend、quota、config、stats writer 或任何 Tier authority。所有 Tier 数据都必须经 Dashboard server-side proxy 调用 Tier HTTP Service 获得；浏览器不得直连 Tier 端口。

## 2. Source Boundary

| 文件 | 当前职责 |
|---|---|
| `src/dashboard/tier.html` | Tier 页面结构 |

### 2.1 Current Implementation Baseline

当前 Tier 页面已迁入统一 `dashboard/`，并通过 same-origin `/api/...` 路由访问。server-side proxy 装配属于 WebUI Shared Internal Component `Unified HTTP Service`，不属于本Module的独立 ownership。后续实施时需要把 Tier 页面资源与 Project 页面资源按模块收敛，但仍保留统一 listener，不新增第二浏览器入口。

## 3. Module Overview

### 3.1 模块定位

Tier Dashboard Module 是用户观察 Tier runtime 并执行显式 management 的唯一浏览器入口。

### 3.2 基本流程

1. 浏览器访问 `tier.html`，统一listener注入当前完整Slinky版本。
2. 页面通过当前 origin 调用 Dashboard API。
3. Dashboard server-side proxy 调用 loopback Tier HTTP Service。
4. 页面渲染 Tier/account/backend/runtime/usage/stats。
5. 自动刷新只 patch 已有字段；management 结果局部回写。

### 3.3 核心设计思路

- same-origin：浏览器只知道 Dashboard origin。
- proxy-only：浏览器侧不感知 Tier 独立端口。
- authority-transparent：Tier 失败、missing account、冲突都必须显式展示。

## 4. Public Interfaces

### 4.1 `WEB-UI-003` Load Tier Structure

| 输入 | 输出 | 错误 |
|---|---|---|
| 当前页面 scope、可选 tier/account filter | Tier runtime、usage、stats 和 Backend 结构 | Tier 不可达、missing account、HTTP/protocol error |

约束：

- 浏览器只使用 `window.location.origin`。
- 禁止浏览器构造第二端口、固定 8765 或自定义 Tier base URL。

### 4.2 `WEB-UI-004` Auto Patch Runtime / Stats

自动刷新只能 patch：

- runtime summary
- account/backend 状态
- usage/probe/running-job 字段
- 更新时间与 stale/error 指示

自动刷新不得调用 structure renderer 重建整页。

### 4.3 `WEB-UI-005` Tier Management

| 输入 | 输出 | 错误 |
|---|---|---|
| 完整 `tier/account/model` identity 与操作参数 | operation result、局部状态变化 | validation、conflict、unavailable、timeout |

约束：

- management 写操作必须保留完整 identity。
- probe、config reload、enable/disable、weight/concurrency 修改都必须通过 Dashboard proxy → Tier HTTP。
- UI 不得隐藏 race 或把失败展示成伪成功。

## 5. 可测试性设计

- 必须能独立验证浏览器只访问 Dashboard origin，不直连 Tier 端口。
- 必须覆盖 Tier 不可达、missing account、management conflict、reload race、stale runtime。
- 必须对真实 DOM 状态断言 patch-only refresh，不允许源码字符串级替代测试。
- 必须保留 action log、请求耗时、proxy route 和返回状态，便于 system test 审计。
- Tier Dashboard必须显示与CLI一致的完整版本，不得在inline JavaScript中拼接或缓存版本。

## 6. Current Gap

当前主要缺口是把 Tier 页面与 Project 页面彻底分离成独立模块权威文档，并把 same-origin proxy、patch-only refresh 和 management 错误语义落实到后续实现与测试中。

## 7. Business Branch / Condition Design

| Branch ID | Decision owner / public entry | Exact predicate | True / selected path | False / else path | State / side effect | Failure / recovery | Required evidence |
|---|---|---|---|---|---|---|---|
| `TDB-BR-001` | Tier authority loader | runtime/stats response均为compatible schema且backend identity唯一 | 初次render backend/account tables | 显示malformed/missing/duplicate错误 | 不合成backend row或统计 | 用户Refresh在authority恢复后重建 | responses、schema result、visible DOM/error |
| `TDB-BR-002` | Backend label mapper | tier、account、model均存在 | 展示API `account/model`、CLI `cli: account/model`、MLEXP `agent:account/model` | 标记identity invalid，不猜account | grouping key保留account | 修复source stats后刷新 | source fields、group key、rendered label |
| `TDB-BR-003` | Auto-refresh controller | existing DOM node identity匹配poll result | patch usage、latency、state、timestamp | group变化时移动现有node；未知node报告drift | 禁止调用table/LLM panel structure renderer | 显式Refresh才重建 | render spies、node identity、before/after DOM |
| `TDB-BR-004` | Management action handler | action获确认、scope唯一且same-origin endpoint可用 | 发送一次control request并patch结果 | 4xx/5xx/timeout显示typed error | 非幂等action不得自动重发 | 用户可在恢复后显式重试 | request count、status、action log、DOM state |
| `TDB-BR-005` | Error/security boundary | response超时、server unavailable、credential/XSS/path输入任一发生 | 显示安全错误并保留已有truth | 正常数据路径更新字段 | 不泄露secret、不执行payload、不清空旧authority | 恢复后poll仅patch错误状态 | console/network、redaction、DOM persistence |
