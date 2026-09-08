# Tier Client Module Design

Version: v1.2
Last Updated: 2026-09-04 08:12:20
Status: Draft

code_directory: `src/llm_tier/client/`
current_source_files: `src/llm_tier/client.py`, `src/llm_tier/tier_core.py`
provided_interfaces: `TIR-HTTP-001`
consumed_interfaces: `TIR-HTTP-002`

## 1. Ownership与职责

所属Subsystem：Tier。

本Module拥有Slinky内部调用Tier的唯一 client-side 入口，负责把 Stage Process、Memory、WebUI server-side proxy 等上游请求转换为标准 Tier HTTP request，并处理 submit、poll、bounded retry、transport error normalization 和结果投影。

本Module不拥有 Router、Backend selection、quota、provider usage、runtime writer、stats writer 和 management authority；这些都属于Tier Server Module。Client 侧在 Service 不可达时必须显式失败，不得退回 embedded Router、本地 provider call 或第二套 fallback。

## 2. Source Boundary

| 文件 | 当前职责 |
|---|---|
| `src/llm_tier/client.py` | HTTP 请求发送、busy retry、job poll、结果归一化 |
| `src/llm_tier/tier_core.py` | public facade；只负责把调用转交给 `TierClient` |

### 2.1 Current Implementation Baseline

当前源码仍位于 `src/llm_tier/` 下，尚未按目标 Module 目录拆分；但职责边界已经可以按文件区分为 client facade 和 server authority。后续代码实施时，必须按本设计迁入 `src/llm_tier/client/`，并删除旧的平铺实现入口，不保留双路径。

## 3. Module Overview

### 3.1 模块定位

Tier Client Module 是所有非浏览器调用者进入 Tier 的唯一 client-side transport 入口。

### 3.2 基本流程

1. 接收上游 `role_name + prompt/prompt_path/user_prompt` 调用。
2. 补齐 execution identity、metadata 和 timeout 约束。
3. 向trusted-network Tier HTTP Service发起submit或read请求。
4. 对 busy / transport / protocol error 做有界处理。
5. 把结果转换为调用方可消费的标准返回结构。

### 3.3 核心设计思路

- 唯一 transport：只允许 HTTP Client → Tier Server。
- authority 下沉：所有业务判断都在 Server 侧，不在 Client 侧复制。
- 错误显式化：transport、busy、protocol、business error 分型返回。

## 4. Public Interfaces

### 4.1 `TIR-HTTP-001` Invoke Role 与 Job Client Contract

| 接口 | 输入 | 输出 | 错误 |
|---|---|---|---|
| `TierClient.invoke_role(payload)` | 必填 `role_name` 与 `prompt/user_prompt/prompt_path` 之一；可选 scope、metadata、timeout、response paths | `ok/content/model_name/tier/backend/execution_level/role_profile/latency_ms/token_usage/...` | `parameter_error`、`transport_error`、`busy_timeout`、`protocol_error`、`business_error` |
| `TierClient.call_async(req)` | 标准 Tier request | job id 与 submit receipt | submit / transport / validation error |
| `TierClient.get_result(job_id)` | 非空 job id | pending / terminal result / not_found | transport / decode / protocol error |
| `TierCore.call(req)` | `TierCallRequest` | `TierCallResult` | 同上 |

### 4.2 调用约束

- Tier URL 只允许来自现有 `TierClient.server_url` / `TIER_SERVER_URL` 机制。
- Tier URL必须是无credential、无额外path的HTTP(S) origin，host仅允许`localhost`、loopback或明确private IP；禁止wildcard和public IP。
- 不允许从 SSH host、浏览器端口、workspace 配置或模型配置推导新的 Tier 地址。
- `call` / `invoke_role` 为非幂等提交，不得因未知 outcome 自动重提。
- poll/read 为幂等读取，可重试，但必须受正 timeout 约束。

## 5. Failure、可观测性与测试性

### 5.1 Failure 语义

| 场景 | 行为 |
|---|---|
| Tier Service unavailable | 立即返回 transport error，不执行任何本地调用 |
| busy 耗尽 | 按 bounded retry 后失败 |
| malformed response | 返回 protocol error，不伪造成功结果 |
| poll timeout | 返回明确 pending/timeout 语义，不切换 transport |

### 5.2 可测试性设计

- 必须支持 fake Tier Server / fixture response 进行独立 unit test。
- 必须能注入超时、空 body、malformed JSON、busy、terminal error 等负向输入。
- 必须记录 request id、job id、tier/account/model、latency 和 error class，便于 system test 审计。
- 必须支持调试开关输出 submit/poll/retry 明细，但不泄露 credential。

## 6. Current Gap

当前缺口不是再引入新 client 机制，而是把现有 `client.py` / `tier_core.py` 的权责按本设计固定下来，并在后续实施中迁入独立 Module 目录。

## 7. Business Branch / Condition Design

| Branch ID | Decision owner / public entry | Exact predicate | True / selected path | False / else path | State / side effect | Failure / recovery | Required evidence |
|---|---|---|---|---|---|---|---|
| `TCL-BR-001` | Tier Client request builder | endpoint、tier、account、model、request ID 和 payload schema 全部合法 | 构造唯一 HTTP request并提交 | 返回 typed client validation error，不发网络请求 | 不修改 job/runtime state | 修正输入后重试 | normalized request、validation result、network absence |
| `TCL-BR-002` | Submit response parser | HTTP success 且 response schema 含唯一 `job_id` 与 accepted status | 返回 typed job handle | HTTP/schema/error envelope 转为 typed failure | 只在 accepted 后记录 job identity | transport retry 受 budget 限制；schema error不重试 | status、response body hash、job identity |
| `TCL-BR-003` | Poll controller | job status 属于 `queued/running` 且 elapsed 小于 timeout | 按 backoff 继续 poll | terminal 时解析 result；超时时 cancel或返回 timeout | poll 不改变服务端 truth | timeout/cancel 结果显式记录，不伪造 terminal | status sequence、timings、cancel response |
| `TCL-BR-004` | Terminal result parser | status 为 declared terminal，result/error envelope 与 status一致，artifact refs 可解析 | 返回成功或 typed terminal failure | 返回 protocol mismatch | 不改写服务端 result | 重新 query 同一 job；不得重新 submit掩盖错误 | terminal envelope、artifact refs、error class |
| `TCL-BR-005` | Backend identity mapper | tier、account、model 三字段均存在且与 request一致 | 输出 `tier:account:model` identity | 返回 identity mismatch | stats/log保留 account，不从文本猜测 | 修复上游 response 后重放 | request/response identity、display label |
