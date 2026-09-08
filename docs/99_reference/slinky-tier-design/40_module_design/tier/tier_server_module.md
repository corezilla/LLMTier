# Tier Server Module Design

Version: v1.3
Last Updated: 2026-09-04 08:12:20
Status: Draft

code_directory: `src/llm_tier/server/`
current_source_files: `src/llm_tier/server.py`, `src/llm_tier/router_core.py`, `src/llm_tier/quota_manager.py`, `src/llm_tier/concurrency.py`, `src/llm_tier/provider_usage.py`, `src/llm_tier/stats_collector.py`, `src/llm_tier/tier_config.py`, `src/llm_tier/tier_model.py`, `src/llm_tier/execution_identity.py`, `src/llm_tier/backends/`
provided_interfaces: `TIR-HTTP-002`, `TIR-PROC-001`, `TIR-DATA-001`
consumed_interfaces: `MLX-HTTP-001`, `MLX-HTTP-002`, `MLX-HTTP-003`, `MLX-HTTP-004`, `MLX-HTTP-005`, `MLX-HTTP-006`

## 1. Ownership与职责

所属Subsystem：Tier。

本Module拥有 Tier 的唯一 server-side authority，包括 trusted-network HTTP Service、job lifecycle、Router、quota/concurrency、provider usage、config/runtime、stats writer、Backend adapters 和 MLEXP adapter。

本Module是唯一允许做 Backend selection、fallback/Upshift、quota 判定和 stats 写入的地方。任何 Stage Process、WebUI 或 Memory 调用都不得绕过本Module直接选择 Backend。

## 2. Source Boundary

| 文件/目录 | 当前职责 |
|---|---|
| `src/llm_tier/server.py` | trusted-network HTTP listener、route dispatch、job/runtime/management |
| `router_core.py` | Backend selection、fallback、Upshift |
| `quota_manager.py` | 配额判定与额度窗口 |
| `concurrency.py` | 并发 slot 与调用期状态 |
| `provider_usage.py` | provider usage 查询与 cache |
| `stats_collector.py` | LLM event append、query、grouping |
| `tier_config.py`、`tier_model.py` | Tier 配置、模型 schema、reload/save |
| `execution_identity.py` | `role_name -> execution_level/role_profile` 解析 |
| `backends/` | API / CLI / Agent / MLEXP adapter |

### 2.1 Current Implementation Baseline

当前源码仍在 `src/llm_tier/` 平铺实现，但在设计上已明确只有 `server.py` 一条 server authority 路径。后续实施时必须迁入 `src/llm_tier/server/`，并按单机制原则删除旧的平铺 authority 入口。

## 3. Module Overview

### 3.1 模块定位

Tier Server Module 是 Slinky 全系统唯一的 LLM routing 与 execution authority。

### 3.2 基本流程

1. 接收来自 Tier Client 或 Dashboard proxy 的 HTTP request。
2. 校验请求、补 execution identity、生成 job/runtime 上下文。
3. 调用 Router 选择 backend/account/model。
4. 执行 quota/concurrency/provider usage 判定。
5. 调用 Backend adapter 或 MLEXP adapter。
6. 写入 result、stats、runtime snapshot 和 recent errors。
7. 对外返回 result、job 状态或 management 结果。

### 3.3 核心设计思路

- 唯一 authority：所有 routing / stats / management 都集中在 server 侧。
- explicit trusted bind：Tier HTTP只监听`localhost`、loopback或明确private IP；禁止wildcard/public bind，不直接暴露给浏览器。
- server-side config：credential、provider usage、backend runtime 均只保留在 server 侧。

## 4. Public Interfaces

### 4.1 `TIR-HTTP-002` Runtime / Stats / Management

| 接口族 | 输入 | 输出 | 错误 |
|---|---|---|---|
| health/runtime/stats/result | scope、time、group、job_id 等 | runtime snapshot、stats aggregates、job result | validation / not_found / transport / protocol |
| management routes | 完整 `tier/account/model` identity 与操作参数 | operation result、conflict、updated runtime | validation / conflict / unavailable / io |

约束：

- 所有 management 写操作必须通过本Module，不允许 Dashboard 本地改 runtime。
- read 路径幂等；write 路径非幂等，必须显式防重和冲突返回。

### 4.2 `TIR-PROC-001` Backend Execution

输入为 resolved backend config、prompt/request、positive timeout、trace context。输出为 normalized provider/CLI/Agent/MLEXP result。

约束：

- API / CLI / Agent / MLEXP adapter 必须共享统一结果 contract。
- credential 不得回传到调用方 payload 或 stats。
- MLEXP adapter 只消费显式 `base_url`，不得从 SSH host 或 LAN IP 猜测地址。

### 4.3 `TIR-DATA-001` Tier Identity / Usage / Stats

运行时记录必须保留：

- `tier`
- `account`
- `backend`
- `model`
- `role_name`
- `execution_level`
- `role_profile`
- `scope`
- `status`
- `timestamp`

缺字段、identity 冲突或 secret 泄露必须视为协议错误，而不是静默容忍。

## 5. Failure、并发与可测试性

### 5.1 Failure 与并发规则

| 场景 | 行为 |
|---|---|
| quota exhausted | 按 Router 现有同 Tier fallback / Upshift 规则处理；全部不可用才失败 |
| provider usage 不可读 | 显式按 unknown/failed 语义返回，不伪造剩余额度 |
| reload/probe/call 并发 | 在途调用持有 snapshot；新调用只看到原子发布后的 snapshot |
| malformed backend result | protocol error，不写成功 sidecar |
| backend unreachable/busy | 返回明确错误并保留 runtime/stat evidence |
| 已选择 Backend 后终止失败 | result 与 raw stats event 保留实际`tier/account/backend/model`、latency 和可确定的 token usage；不得清空 identity |

### 5.2 可测试性设计

- 必须支持用 fixture config 独立验证 Router、quota、concurrency、provider usage。
- 必须能注入 exhausted、auth failure、timeout、nonzero CLI exit、malformed result、MLEXP terminal failure。
- 必须能清零 runtime snapshot、recent errors、stats，支持 system test 前快速恢复。
- 必须保留 account 级 identity 和 action log，供审计和回放。
- 必须对 quota、Backend error 和 unexpected exception 分别注入失败，验证失败 result、raw stats event 与 grouped `fail_count`均归属于实际选择的 Backend 和项目 scope。

## 6. Current Gap

当前主要缺口是把现有 server authority 正式落为单一 Module 并补齐 race、quota、usage 和 management 测试；不是再拆出第二套 routing 或第二个 HTTP 入口。

## 7. Business Branch / Condition Design

| Branch ID | Decision owner / public entry | Exact predicate | True / selected path | False / else path | State / side effect | Failure / recovery | Required evidence |
|---|---|---|---|---|---|---|---|
| `TSV-BR-001` | Tier HTTP admission | route存在，请求schema、tier/account/model和credential policy全部合法 | 进入route/scheduler | 返回对应4xx typed envelope | invalid请求不占capacity、不写usage | 修正请求后新request ID重试 | route、validation、response status、capacity unchanged |
| `TSV-BR-002` | Backend route selector | 显式route可用，probe为ready，quota/capacity均允许且identity唯一 | claim backend并执行 | busy/exhausted/disabled返回typed unavailable与`retry_after` | claim原子写入，防止超卖 | release后重试；不得silent fallback到另一account | route decision、probe、quota、claim ledger |
| `TSV-BR-003` | Probe state reducer | controlled probe evidence满足ready/busy/exhausted/disabled对应规则 | 原子迁移到计算状态 | malformed/stale probe保持旧truth并记录error | state transition含timestamp/source | 后续合法probe恢复，不由UI改状态 | before/after state、probe evidence、error |
| `TSV-BR-004` | Job result handler | backend result identity匹配active job且status合法 | 写terminal result并release capacity | unknown/duplicate/late result拒绝或幂等返回 | terminal write-once；capacity只release一次 | restart从authority恢复未终态job | job/result identity、transition、capacity diff |
| `TSV-BR-005` | Stats/management authority | management action获授权且target scope明确；成功或失败stats event均含实际选择的tier/account/backend/model | 执行reset/control或按scope聚合 | unauthorized/ambiguous action拒绝；malformed或空identity event不聚合并暴露协议错误 | action log与stats authority同步；终止失败不清空identity | reset失败保持旧snapshot并返回typed error | action request/result、成功与失败stats rows、account identity、project fail_count |
