# LLM Tier 子系统设计

Version: v1.92
Last Updated: 2026-09-08 18:32:24
Status: Draft

---

## 概述

LLM Tier 是 Slinky 的统一 LLM 接入层，采用**两层架构**：

MLEXP现已作为Slinky第五个Subsystem独立设计。`src/llm_tier/backends/mlexp.py`是Tier消费MLEXP HTTP job API的adapter；本文中的`MLP backend`、`MLEXP backend`均仅指Tier配置/adapter identity，不表示MLEXP服务、worker、Report或Artifact归Tier所有。系统级边界以`docs/30_subsystem_design/mlexp_subsystem.md`为准。

```
┌───────────────────────────────────────────────────────────┐
│ llm_tier（外层 — 项目级入口 + 统一统计）                     │
│                                                           │
│  职责：                                                    │
│  · 项目级配置管理（settings.json → Tier 模型池、角色映射）    │
│  · 对外统一调用接口（.call()）                              │
│  · 全局统计聚合（按 backend / tier / role / project / time） │
│  · 统计查询接口                                            │
│                                                           │
│  ┌───────────────────────────────────────────────────┐    │
│  │ llm_router（内层 — backend 级路由 + Fallback）       │    │
│  │                                                    │    │
│  │  职责：                                             │    │
│  │  · role → Tier → Backend 选择                      │    │
│  │  · 额度检测 + Tier 内自动 fallback                  │    │
│  │  · Account 级并发控制 + Backend 级运行计数           │    │
│  │  · 通用错误 → QuotaExhaustedError 转换              │    │
│  └───────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────┘
```

- **llm_tier** 面向项目，管配置和统计
- **llm_router** 面向 backend，管路由和容错

## 目录结构

```
src/llm_tier/
├── __init__.py              # 导出 get_tier(), TierCallRequest, TierCallResult
├── tier_core.py             # 外层入口：.call() 流程编排 + 调试开关
├── router_core.py           # 内层路由：Backend 选择、Fallback 循环
├── quota_manager.py         # 额度管理：检测、标记、自动重置
├── concurrency.py           # 并发管理：Account 级 semaphore + Backend 运行计数
├── tier_config.py           # 配置加载器：纯读取 settings.json
├── tier_model.py            # 数据模型定义
├── exceptions.py            # 异常定义
├── stats_collector.py       # 统计收集与查询（写 meta/llm_tier/llm_stats.sqlite3）
├── backends/
│   ├── __init__.py          # Backend 注册表
│   ├── base.py              # BaseBackendClient 统一接口
│   ├── api_backend.py       # api 公共逻辑：HTTP POST + retry + 错误转换
│   ├── agent_backend.py     # agent 公共逻辑：subprocess + 文件锁 + stdout 捕获
│   ├── xfyun.py             # 讯飞 (api)，封装 model_client.XfyunModelClient
│   ├── volc.py              # 火山 (api)，封装 model_client.VolcModelClient
│   ├── deepseek.py          # DeepSeek (api)，新写 OpenAI-compatible
│   ├── minimax.py           # MiniMax Token Plan (api)，Anthropic-compatible
│   ├── local.py             # 本地模型 (api)
│   ├── codex.py             # Codex CLI (agent)，内联 CLI 调用逻辑
│   └── claude.py            # Claude CLI (agent)，内联 CLI 调用逻辑
```

## 模块与接口总览

| 文件 | 导出的公共符号 | 类型 | 对外接口 |
|------|--------------|------|---------|
| `tier_model.py` | `TierAccount`, `TierModel`, `TierCallRequest`, `TierCallResult`, `TierStatsQuery`, `TierStatsRow` | @dataclass | 无方法，纯数据结构 |
| `exceptions.py` | `TierRouterError`, `QuotaExhaustedError`, `AllModelsExhaustedError`, `BackendCallError`, `ConcurrencyTimeoutError` | Exception | `.backend`, `.model_name`, `.tier_name` 等属性 |
| `tier_config.py` | `TierConfig` | class | `.get_accounts()`, `.get_account()`, `.get_account_concurrency()`, `.get_tier_models()`, `.get_tier_for_role()`, `.get_quota_config()`, `.reload()`, `.is_enabled()` |
| `quota_manager.py` | `QuotaManager` | class | `.is_exhausted(backend, model)`, `.mark_exhausted(backend, model)`, `.reset_tier(name)`, `.reset_all()` |
| `concurrency.py` | `BackendConcurrencyManager` | class | `.acquire(backend_key, account_key)`, `.release(backend_key, account_key)`, `.get_load(backend_key)`, `.get_account_load(account_key)` |
| `router_core.py` | `LLMRouter` | class | `.call(role, prompt, ...) → (TierCallResult, stats_event)` |
| `tier_core.py` | `TierCore`, `get_tier()` | class + 函数 | `.call(req)`, `.call_async(req)`, `.reload_config()`, `.get_tier_info(name)`, `.reset_exhausted(name)`, `.get_stats(query)`, `.get_summary()` |
| `stats_collector.py` | `StatsCollector` | class | `.write(stats_event)`, `.get_stats(query) → list[TierStatsRow]`, `.get_summary() → dict` |
| `backends/__init__.py` | `register_backend`, `get_backend_client`, `list_backends` | 函数 | 注册/获取/列举 Backend |
| `backends/base.py` | `BaseBackendClient` | ABC | `.backend`, `.backend_type`, `.supported_models()`, `.call(model, prompt, ...)` |
| `backends/api_backend.py` | `ApiBackendMixin` | mixin | `._post(payload) → dict`, `._handle_http_error(exc)` — api Backend 公共逻辑 |
| `backends/agent_backend.py` | `AgentBackendMixin` | mixin | `._run_cli(command) → dict`, `._capture_stdout(path)`, `._acquire_file_lock(path)` — agent Backend 公共逻辑 |
| `backends/xfyun.py` | `XfyunClient` | class | 继承 BaseBackendClient + ApiBackendMixin，`.call()` |
| `backends/volc.py` | `VolcClient` | class | 同上 |
| `backends/deepseek.py` | `DeepSeekClient` | class | 同上 |
| `backends/minimax.py` | `MiniMaxClient` | class | Anthropic-compatible Token Plan API，`.call()` |
| `backends/local.py` | `LocalClient` | class | 同上 |
| `backends/codex.py` | `CodexClient` | class | 继承 BaseBackendClient + AgentBackendMixin，`.call()` |
| `backends/claude.py` | `ClaudeClient` | class | 同上 |
| `__init__.py` | `get_tier`, `TierCallRequest`, `TierCallResult` | 函数 + 类 | 对外统一入口 |

## Backend 类型

| 类型 | 说明 | 调用方式 | 并发模式 | 示例 |
|------|------|---------|---------|------|
| **API** | 云端 API | HTTP POST `/chat/completions` 或兼容协议 endpoint | 多路（semaphore） | xfyun, volc, deepseek, minimax, local |
| **CLI** | 本地 CLI | subprocess.run | 单路（semaphore=1 + 文件锁） | codex, claude, opencode |
| **agent** | 自主 Agent | Agent runtime / OpenClaw 类执行器 | 由 Agent runtime 管理 | openclaw（未来） |

两类 Backend 必须实现同一 `BaseBackendClient` 接口，对上层透明。

## Tier 等级定义

| Tier | 适用角色 | 模型池（按优先级） | 说明 |
|------|---------|-------------------|------|
| **Senior** | execution fixer, escalator, unit/system test fixer | 1. `opencode:volc/glm-5.2` (CLI agent) | 高能力 rescue / override 层，质量优先；Claude/Codex CLI 未安装或未验证时不得配置为可路由 Backend |
| **Junior** | author, classifier, risk manager, scoped design / research task | 1. `opencode:mnm/MiniMax-M3` (CLI agent) 2. `opencode:volc/kimi-k2.6` (CLI agent，可按验证状态启用) | 受控 agent 层，负责较复杂的 Artifact 生成、局部调查和设计文档任务 |
| **Worker** | reviewer, reviser, review arbiter, drift controller, low-cost author fallback | 1. MiniMax M2.x (API) 2. xfyun Qwen Coder (API) 3. local / OMLX API（按服务可用性启用） | 低成本 API / 本地 worker 层，负责高频审查、定向修订和可边界化生成 |
| **Associate** | RAG Provider / Judge / 低成本辅助判断 | 1. local / OMLX / xfyun lightweight API（按项目配置启用） | 位于 Worker 与 Executor 之间，承接高频、结构化、低成本判断任务，例如 `rag_judger` |
| **Foreman** | Environment Provisioner | 1. opencode CLI | 负责通过 SSH / CLI agent 部署和启动 MLEXP、NFS、依赖与测试环境；当前主链未启用时可以为空 |
| **Engineer** | System Testing Preflight Engineer | 1. MLEXP / MLP backend | 位于 Foreman 与 Executor 之间，供 system_testing preflight / execution 调试调用；Engineer backend 必须是 MLEXP 节点，MLEXP 自己持有 API key 并调用内部云模型，不通过回调 Tier 调用 Engineer |
| **Executor** | System Testing 本地执行 | 1. `mlexp:omlx9/gemma-4-e2b-it-4bit` (MLP) | 通过 m5air 本地 OMLX 模型执行，不占用云模型额度 |

---

### 当前 m5air 测试配置基线

当前测试环境按以下原则配置 Tier，不再保留已废弃账号或未安装 CLI 的可路由 Backend：

- `Senior` 使用高能力 agent Backend：`opencode:volc/glm-5.2`。若 GLM-5.2 在目标机器未验证成功，该 Backend 必须保持 disabled 或从配置中移除；不得用未安装成功的 `claude:*` 作为可路由 Senior。
- `Junior` 使用 agent Backend：`opencode:mnm/MiniMax-M3`；`opencode:volc/kimi-k2.6` 可作为 Junior 备选，但必须按真实可用性启用。
- `Worker` 保留 API / 本地 worker Backend，用于原有 author/reviewer/reviser 等可边界化任务；废弃账号（例如已确认无效的 xfyun 套餐账号）不得继续出现在可路由配置中。
- `role_name -> Tier` 仍是当前唯一运行时路由入口；`execution_level / role_profile` 是审计身份字段，不新增第二套路由 selector。
- 所有 Backend identity 必须使用 `tier:account:model_name`；Dashboard 显示必须使用 `account/model`、`cli: account/model` 或 `agent:account/model`。

### Engineer / MLEXP Subsystem Adapter 封装边界

Engineer 对上层 client 必须保持普通 Tier call 语义：调用方只传 `role_name/prompt/project_name/stage_name/phase_name/task_id/task_key/metadata`，不得直接拼 MLEXP `/api/system-test/run` 请求体，也不得传递云模型 API key。

`mlexp` adapter负责把普通Tier call封装为MLEXP system-test job；job lifecycle、capacity、Report和Artifact由MLEXP Subsystem拥有：

- 按 backend `model_key/model_name` 解析 MLEXP 内部模型选择，例如 `mlexp:mnm/MiniMax-M2.5` 对应 MLEXP `options.backend = "mnm/MiniMax-M2.5"`。
- MLP backend 的执行节点和模型供应账号必须分开：`base_url` / `ssh` 表示 m5air 的连接信息；`account` 表示内部模型供应账号，例如 `mnm/MiniMax-M2.5` 的 `mnm`、`omlx9/gemma-4-e2b-it-4bit` 的 `omlx9`。
- 未显式配置 `usage_account` 时，`mlexp` backend 必须从 `model_key/model_name` 的 `/` 前缀自动推导；如果该前缀存在于 `llm_accounts`，则复用该账号的 provider usage 凭证与 quota 配置；如果前缀是 `ollama/local/llama` 等本地供应商，则按本地无限额度展示。
- 用 `project_name/task_id/task_key/phase_name` 构造 `external_id`、`report_output` 和 description-only `test_case`。
- 通过 MLEXP `/api/system-test/run` 提交 job，并轮询 `/api/jobs/{job_id}` 到终态。
- 将 MLEXP job 终态、report 摘要和 usage 封装回 `TierCallResult.content/raw_response/token_usage`。
- MLEXP 终态中的 `llm_usage` / `usage` 必须进入 Tier 统一 stats event：`calls` 映射为 `call_count`，失败的内部 `llm_calls` 映射为 `failed_call_count`，`prompt_tokens`、`completion_tokens`、`total_tokens`、`cached_tokens`、`prompt_chars`、`completion_chars`、`latency_ms`、`provider_usage_available`、`usage_source` 必须保留；如果 `llm_usage.calls = 0`，Tier 必须保留 0，不得把一次 MLEXP job 误计为一次内部 LLM call。
- MLEXP 连接失败、提交失败、轮询超时属于 backend 调用失败；测试用例自身 failed / blocked 属于业务报告内容，不应被 Tier 误判为模型 backend 不可用。

Rule:

Engineer 的 MLEXP 协议必须封装在 Tier backend 内；client 侧不能因为目标是 MLEXP 就走另一套调用方式。

---

## 零、核心数据模型

### TierModel

```python
@dataclass
class TierModel:
    """Tier 内单个模型配置"""
    backend: str              # backend 标识，如 "xfyun"、"codex"
    model_name: str           # 模型名
    account: str              # 连接、并发和调用间隔账号
    usage_account: str        # provider usage / quota 查询账号；为空时等于 account
    backend_type: str         # "API" | "CLI" | "agent"
    weight: int = 1           # 负载权重（整数；按配置顺序展开）
    enabled: bool = True      # 人工启用开关；false 时不能参与路由
    exhausted: bool = False   # 运行时额度耗尽标记，不持久化
```

### TierCallRequest — 对外调用请求

```python
@dataclass
class TierCallRequest:
    """llm_tier.call() 的请求参数"""
    role_name: str                       # 必填：角色名
    prompt: str                          # 必填：prompt 文本
    project_name: str                    # 必填：项目名
    stage_name: str = ""                 # 可选：当前 Stage
    phase_name: str = ""                 # 可选：当前 Phase
    task_id: str = ""                    # 可选：当前 Task ID
    task_key: str = ""                   # 可选：当前 Task Key
    temperature: float = 0.0             # 可选：温度
    timeout_seconds: int | None = None   # 可选：None 则用 Backend 默认
    metadata: dict[str, str] = field(default_factory=dict)
    prompt_path: str = ""                # file mode: client 已写好的 prompt 文件
    response_path: str = ""              # file mode: server 成功时写入的业务 response 文件
    raw_response_path: str = ""          # file mode: server 成功时写入的审计 raw response 文件
    error_response_path: str = ""        # file mode: server 失败时写入的错误 sidecar 文件
```

**参数说明：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `role_name` | str | 是 | 角色标识，用于 Tier 路由 |
| `prompt` | str | 是 | 完整 prompt 文本，直接传给 Backend |
| `project_name` | str | 是 | 项目名，用于统计聚合和配置隔离 |
| `stage_name` | str | 否 | 当前 Stage，用于统计和日志 |
| `phase_name` | str | 否 | 当前 Phase，用于统计和日志 |
| `task_id` | str | 否 | 当前 Task ID，用于统计和 trace |
| `task_key` | str | 否 | 当前 Task Key，用于统计 |
| `temperature` | float | 否 | 采样温度，默认 0.0 |
| `timeout_seconds` | int | 否 | 单次调用超时，None 则用 Backend 默认 |
| `metadata` | dict | 否 | 透传给 Backend 的额外元数据 |
| `prompt_path` | str | 否 | file mode 输入 prompt 文件；存在时 `prompt` 可以为空 |
| `response_path` | str | 否 | file mode 成功业务 response 文件，由 server 写入原始模型输出 |
| `raw_response_path` | str | 否 | file mode 成功审计文件，由 server 写入 backend raw response / usage |
| `error_response_path` | str | 否 | file mode 失败 sidecar 文件，由 server 写入 transport/backend/tier 错误 |

### TierCallResult — 对外调用返回

```python
@dataclass
class TierCallResult:
    """llm_tier.call() 的返回结果"""
    ok: bool                            # 调用是否成功
    content: str                        # LLM 响应文本
    backend: str                        # 实际使用的 Backend
    model_name: str                     # 实际使用的模型名
    backend_type: str                   # "API" | "CLI" | "agent"
    tier: str                           # 命中的 Tier 名
    tier_priority: int                  # Tier 内的优先级序号（1-based）
    latency_ms: float                   # 端到端延迟
    token_usage: dict[str, int]         # {"prompt_tokens": N, "completion_tokens": N, "total_tokens": N}
    is_fallback: bool                   # 是否触发了 fallback 切换
    fallback_count: int                 # fallback 切换次数
    raw_response: dict[str, Any]        # Backend 原始响应（审计用）
    error_code: int = 0                 # 错误码，0=成功
    error_message: str = ""             # 错误信息
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `ok` | bool | True 表示拿到有效响应 |
| `content` | str | LLM 返回的文本内容 |
| `backend` | str | 实际响应的 Backend 名，如 `"xfyun"` |
| `model_name` | str | 实际使用的模型名 |
| `backend_type` | str | `"API"`、`"CLI"` 或未来 `"agent"`；dashboard 原样显示该值 |
| `tier` | str | 命中的 Tier 名 |
| `tier_priority` | int | 命中模型在 Tier 内的优先级序号 |
| `latency_ms` | float | 端到端延迟，含路由、排队、网络、推理 |
| `token_usage` | dict | token 用量。agent Backend 无法获取时填 0 |
| `is_fallback` | bool | 是否因额度耗尽触发过切换 |
| `fallback_count` | int | 累计 fallback 次数 |
| `raw_response` | dict | Backend 原始返回（审计用） |

### Tier 与 Client 的 LLM IO 职责边界

为避免同一次调用出现两套目录规则，LLM IO 的职责边界必须固定如下：

- client 侧负责：
  - 生成标准 task-local `prompt/response/raw_response/error_response` 文件路径
  - 写入 `prompt` 文件
  - 记录对应 intermediate artifact
- server/router 侧负责：
  - Backend 选择
  - backend 调用
  - fallback / busy / exhausted / unhealthy-disable 决策
  - 返回 `content/raw_response/token_usage/error`
  - 在 file mode 中，按 client 提供的路径写入 `response_path`、`raw_response_path` 或 `error_response_path`
  - 写入 Tier 统计

禁止事项：

- server/router 不得根据 `workspace_root/stage_name/phase_name/task_id` 再次推导 task-local response 目录。
- server/router 不得维护第二套 `response_path/raw_response_path/error_response_path` 文件名规则；未显式传入 `error_response_path` 时，只能由 `response_path` 机械推导同目录同 stem 的 `.error.json` sidecar。
- client 在收到 Tier 返回后，不得以 Tier 返回的 response 路径覆盖本地标准 LLM IO 路径。

### File Mode Response / Error Sidecar 协议

file mode 必须保持业务 response 原文通道和 transport/backend/tier 错误通道分离。

状态判定：

| 文件状态 | 语义 | client 行为 |
|----------|------|-------------|
| `response.txt` 存在，`response.error.json` 不存在 | Backend 成功返回业务原文 | 读取 `response.txt`，交给 task parser |
| `response.error.json` 存在，`response.txt` 不存在 | transport/backend/tier 失败 | 不调用 task parser，当前 attempt failed / retry |
| 两者都不存在 | job 仍在运行或等待 | 继续 poll，直到 job timeout |
| 两者同时存在 | 协议错误 | 当前 attempt failed，并记录 `protocol_error` |

写入规则：

- 成功时 server 必须只写 `response_path` 和可选 `raw_response_path`，不得写 `error_response_path`。
- 失败时 server 必须只写 `error_response_path`，不得写 `response_path`；可把 backend raw response / stdout / stderr / trace 路径写入 error sidecar。
- `response_path` 是业务数据通道，内容必须是模型原始输出，不得包外层 JSON、状态 envelope 或错误 payload。
- `error_response_path` 是错误 sidecar，默认命名为 `response_path` 去掉 `.txt` 后追加 `.error.json`，例如 `d1.generation.response.error.json`。
- 合法空业务数据不得通过空 `response.txt` 表达。需要生成 0-byte / empty / whitespace-only test data 时，业务 response 必须包含该 task 定义的合法 envelope 或其它业务层协议；transport/backend/tier 空返回必须写入 `response.error.json`。

`response.error.json` 结构：

```json
{
  "success": false,
  "error_type": "empty_response",
  "error_code": 1005,
  "message": "backend returned no usable response",
  "backend": "xf2/Qwen3-Coder-Next-FP8",
  "model_name": "Qwen3-Coder-Next-FP8",
  "tier": "Associate",
  "started_at": "2026-06-16T01:15:59Z",
  "finished_at": "2026-06-16T01:16:04Z",
  "raw_response": {},
  "debug_paths": {
    "raw_response_path": "",
    "stdout_path": "",
    "stderr_path": ""
  }
}
```

### 错误码

| 错误码 | 错误名 | 说明 | 触发条件 |
|--------|--------|------|---------|
| `0` | success | 成功 | — |
| `1001` | tier_config_missing | 未找到 Tier 配置 | settings.json 缺失或格式错误 |
| `1002` | role_not_mapped | role 未映射到任何 Tier | role_tier_map 中无此 role |
| `1003` | all_backends_exhausted | Tier 内所有 Backend 额度耗尽 | 全部 Backend 抛 QuotaExhaustedError |
| `1004` | backend_not_found | Backend 标识未注册 | Registry 中无此 Backend |
| `1005` | backend_call_failed | Backend 调用返回错误 | HTTP 5xx / returncode != 0 / 其他异常 |
| `1006` | backend_timeout | Backend 调用超时 | 超过 timeout_seconds |
| `1007` | concurrency_exhausted | 并发数已满 | semaphore 已满 + 队列已满 |
| `1008` | invalid_request | 请求参数不合法 | role_name/prompt/project_name 为空 |

### 错误码映射（Backend Error → Tier Error）

| Backend 错误场景 | 是否触发 Fallback | 最终 error_code |
|---|---|---|
| HTTP 429 / `quota_exhausted` / `NotEnoughCv` / `rate_limit` | **是**（标记 exhausted，不直接返回） | 全部 Backend 都耗尽后 → `1003` |
| HTTP 5xx（非额度） | 否，重试 3 次后 | `1005` |
| subprocess returncode != 0 | 否 | `1005` |
| subprocess / HTTP 超时 | 否 | `1006` |
| 并发满 | 否 | `1007` |
| role 无匹配 Tier | 否 | `1002` |
| Backend 未注册 | 否 | `1004` |

### 统计数据结构

```python
@dataclass
class TierStatsQuery:
    """统计查询条件"""
    project_name: str = ""              # 按项目筛选，空=全部
    tier: str = ""                      # 按 Tier 筛选，空=全部
    backend: str = ""                   # 按 Backend 筛选，空=全部
    role_name: str = ""                 # 按角色筛选，空=全部
    time_range_hours: int = 0           # 时间范围，0=全部
    limit: int = 100                    # 返回上限

@dataclass
class TierStatsRow:
    """单条统计记录（按 backend+model+role 聚合）"""
    project_name: str
    tier: str
    backend: str
    backend_type: str
    model_name: str
    role_name: str
    calls: int                          # 总调用次数
    success_count: int                  # 成功次数
    fail_count: int                    # 失败次数
    total_tokens: int                   # 总 token
    prompt_tokens: int                  # prompt token
    completion_tokens: int             # completion token
    cached_tokens: int                  # cached token
    prompt_chars: int                   # prompt 字符数
    completion_chars: int              # completion 字符数
    latency_avg_ms: float               # 平均延迟
    latency_p50_ms: float               # p50
    latency_p90_ms: float               # p90
    latency_p99_ms: float               # p99
    fallback_count: int                 # fallback 次数
    exhausted_count: int                # 额度耗尽次数
```

---

## 一、对外接口（llm_tier 对外暴露）

### 1. 调用接口

#### `tier.call(req: TierCallRequest) -> TierCallResult`

同步调用 LLM，自动路由和 fallback。

```
流程：
  1. 校验参数（role_name / project_name / prompt 非空）
  2. 查 role → Tier 映射（TierConfig）
  3. 委托 llm_router 执行 "选择 Backend → 调用 → fallback 循环"
  4. llm_router 返回 (result, stats_event)
  5. 外层调用 stats_collector.write(stats_event) 写入统计
  6. 返回 TierCallResult
```

LLM IO 边界约束：

- task-local `prompt/response/raw_response/error_response` 文件路径必须由 client 侧标准 LLM IO 流统一生成。
- `llm_tier server` / `router` 只负责路由、调用、返回内容与统计；在 file mode 中可以按请求传入的路径写入 `response_path`、`raw_response_path` 或 `error_response_path`，但不得自行发明第二套 task-local 目录或文件名规则。
- `TierCallResult.artifact_paths` 可以回传实际写入的 `response_path`、`raw_response_path` 或 `error_response_path`，供 client / Dashboard 登记；调用方不得用它覆盖本地已生成的标准路径。

#### `tier.call_async(req: TierCallRequest) -> TierCallResult`

同 `call()` 的异步版本，内部 Routing 和 Backend 调用使用 async。

### 2. 配置接口

#### `tier.reload_config() -> bool`

重新加载 settings.json 中的 Tier 配置，返回是否成功。运行时切换 Backend 后调用。

约束：

- `reload_config()` 表示回到配置文件定义的路由状态。
- `reload_config()` 不得清除 quota state 和 stats 数据。

#### Backend 启用与权重接口

`llm_tier server` 只保留一套 Backend 可调度控制机制：`enabled`。用户不希望某个 Backend 参与调度时，必须禁用该 Backend；不得再维护独立选择池。

禁用 / 启用接口：

```http
POST /backend/disable
POST /backend/enable
```

请求：

```json
{
  "tier_name": "Worker",
  "account": "xf2",
  "backend": "xf2/Qwen3-Coder-Next-FP8",
  "model_name": "Qwen3-Coder-Next-FP8"
}
```

权重接口：

```http
POST /backend/weight
```

请求：

```json
{
  "tier_name": "Worker",
  "account": "xf2",
  "backend": "xf2/Qwen3-Coder-Next-FP8",
  "model_name": "Qwen3-Coder-Next-FP8",
  "weight": 3
}
```

语义：

- `enabled=false` 的 Backend 不参与 Router 选择，也不计入 Dashboard 的 Tier `running/max`。
- `enabled=true` 且健康状态允许调度的 Backend 参与 Router 选择。
- 多个 enabled Backend 使用唯一的 ordered weighted ring：按配置文件顺序展开 `weight` 后循环选择。
- 示例：`b1.weight=1, b2.weight=1, b3.weight=2` 的选择序列必须是 `b1, b2, b3, b3` 循环。
- Router 必须在同一个临界区内完成“从 weighted ring 找到可用 backend slot”和“占用对应 account 并发槽”，不得先选 backend 再在另一个步骤 acquire account 槽。
- 如果 cursor 命中的 slot 对应 account 已满载、调用间隔未到或每分钟请求数已满，Router 必须继续扫描 ring 中的后续 slot；只有全部候选都暂时 busy 时才返回 `all_backends_busy`。
- 配置文件中 Backend 的位置就是路由顺序；不再维护独立 `priority` 路由机制。
- `weight`、`enabled`、`model_name`、`model_key`、`max_context_tokens` 属于 Backend 自身配置，保存时必须写回同一个 Backend 对象。
- `max_concurrent_requests` 和 `min_request_interval_ms` 属于 Account 配置，Backend 只能通过 `account` 字段引用 Account，不得复制账号级并发配置。

返回：

```json
{
  "ok": true,
  "tier_name": "Worker",
  "account": "xf2",
  "backend": "xf2/Qwen3-Coder-Next-FP8",
  "model_name": "Qwen3-Coder-Next-FP8",
  "weight": 3
}
```

Account 最大并发接口：

```http
POST /account/concurrency
```

请求：

```json
{
  "account": "xf2",
  "max_concurrent_requests": 5
}
```

语义：

- `max_concurrent_requests` 属于 Account 配置，保存时必须写回 `llm_accounts[account]`。
- 修改成功后，当前 tier server 内存中的 account identity 并发上限必须立即更新，后续 `acquire()` 使用新上限。
- 当前正在运行的请求不被取消；若新的最大并发数低于当前运行数，新的请求必须等到运行数降到新上限以下才可获取槽位。

返回：

```json
{
  "ok": true,
  "tier_name": "Worker",
  "account": "xf2",
  "backend": "xf2/Qwen3-Coder-Next-FP8",
  "model_name": "Qwen3-Coder-Next-FP8",
  "max_concurrent_requests": 5
}
```

Dashboard 展示约束：

- `/runtime` 与 `/health` 必须返回 `enabled`、`active`、`weight`、`state` 字段。
- Dashboard 不得显示 `Select/Remove`；用户不使用某个 Backend 时必须点击 `Disable`。
- 用户必须可以在线调整 Backend 的 `weight`；权重修改直接写入 Backend 对象。
- Tier `running/max` 只统计 `active=true` 的 Backend。

HTTP 服务约束：

- Tier server 的 HTTP 接入层必须支持并发请求处理，不能使用单线程 HTTP 处理模型阻塞 `/runtime`、`/result/{job_id}`、`/stats` 或 Dashboard 刷新。
- Backend 调用仍由异步 job 线程执行；HTTP handler 只负责提交 job、读取 job 状态、返回 runtime / stats / debug 数据。
- 当多个 client 同时轮询 `/result/{job_id}` 时，一个慢请求不得阻塞其他 job 的结果查询，也不得导致 Dashboard 看起来没有活跃 LLM jobs。
- `/runtime` 必须能在 backend 长耗时调用期间快速返回当前 job running/done 计数和 backend `running/max`，用于判断是真无活跃 job 还是 client / retrieval / dashboard 侧卡住。
- `/runtime` 中的 stats 摘要允许由 Tier server 使用短 TTL authoritative cache 和 single-flight 查询保护，避免 Dashboard 并发刷新重复扫描 SQLite；缓存必须在 server 端完成，Dashboard 不得自行补算或推断。

### 2.1 Backend 主状态模型

每个 `tier:account:model_name` 对外只允许暴露一套主状态。本文将 Tier 内一个 Account 的一个 Model 组合称为一个 Backend；因此相同 `account:model_name` 出现在不同 Tier 时，是不同 Backend：

1. `disabled`
2. `probing`
3. `running`
4. `exhausted`
5. `unreachable`

其中：

- `enabled=false` 对外状态必须显示为 `disabled`，优先级高于所有健康状态。
- `enabled=true` 后必须进入 `probing`，不得直接显示为 `running`。
- `running` 表示 Backend 已通过 probe，当前可运行；它不是“正在执行请求数”。真实并发必须使用独立 `running/max` 数字展示。
- `probing` 是正在探测状态；当前实现中 probe 并发立即执行，不需要等待队列，因此不再保留 `available` 状态。
- `exhausted` 表示额度 / 流控耗尽。
- `unreachable` 表示 Backend 不可达、CLI/API 错误、probe 超时，或真实 LLM 请求失败 / 超时达到阈值。
- `ok` 已废弃，禁止作为 Backend runtime 主状态或内部健康稳定态。
- `available` 和 `selected` 均已废弃，禁止作为 runtime / dashboard 状态。
- `active = enabled && state == running`。
- `cooldown` 机制已废弃；主状态机中不再存在 `cooldown`，也不再维护 `cooldown_until`

### 2.1.1 Backend 展示命名规则

Tier 内部 Backend identity 使用 `tier:account:model_name`；Dashboard 和 tier.html 面向用户显示时必须使用可读的 `agent:account/model` 口径。

规则如下：

- 本文称 Tier 内一个 Account 的一个 Model 组合为一个 Backend；`tier` 是 Backend identity 的命名空间，不是显示名前缀。
- API Backend 显示为 `account/model`，例如 `xf2/Qwen3-Coder-Next-FP8`、`mnm/MiniMax-M2.7`。
- CLI Backend 显示为 `cli: account/model`，其中 `cli` 是实际 CLI backend 名，例如 `opencode: mnm/MiniMax-M3`、`opencode: volc/glm-5.2`。
- MLP / MLEXP Backend 显示为 `agent:account/model`，其中 `agent` 是 MLEXP 节点名，`account` 是 MLEXP 内部模型供应账号，例如 `m5air:mnm/MiniMax-M2.5`、`m5air:omlx9/gemma-4-e2b-it-4bit`。
- `backend/model` 或 `agent/model` 是旧口径，禁止继续出现在 runtime snapshot、stats API、Dashboard 展开行、tier.html 主表或项目摘要中。
- LLM stats event、SQLite 聚合、`/runtime` backend stats、Dashboard `LLM Stats By Tier` backend 展开行必须携带并使用 `account` 字段；不得只用 `tier/backend/model` 聚合或展示，否则会把不同 Tier 中同账号同模型的 Backend 混淆。
- dashboard 主表只能显示 `disabled / probing / running / exhausted / unreachable`
- `exhausted` 行仍然属于可操作态；单 Backend `Probe` 必须允许点击，用于恢复该 Backend
- 这套主状态机的唯一当前态必须保存在 `llm_tier server` 进程内存中；Dashboard 只能读取这份当前态，不能自行推导或拼装状态。
- Dashboard 中单 Backend `Probe` 按钮是否可点击，只能由 `runtime.state` 这一处决定；点击处理函数不得再维护第二套临时禁用/恢复逻辑。

路由是否允许选择 Backend，必须满足：

```text
routable = enabled && state == running
```

约束：

- 不允许同时维护一套“主状态优先级”和另一套独立 `exhausted` 展示优先级，再在 `/runtime` 时二次拼装。
- 不允许把 quota store、router meta、probe 临时字段分别当成多套“当前状态”，再由 Dashboard 或 `/runtime` 临时拼装。
- 一次 Probe 开始后，主状态必须先切到 `probing`；随后只能根据 Probe 结果落到 `running / exhausted / unreachable` 之一。
- Probe 的 timeout 属于 server 自己的状态机约束；server 必须记录本次 probing 的开始时间和 timeout，并在超时后主动把主状态切到 `unreachable`，不得无限保持 `probing`。
- 一次 probing 被 server 判定超时后，旧 probe 晚到的结果不得再覆盖当前主状态。
- `Enable` 必须自动触发 Probe；不得因为旧健康记录为内部 `ok` 而跳过 Probe。
- `context_length_exceeded` 不进入主状态机，它只属于单次请求语义，不得把 Backend 主状态改成 `unreachable` 或 `exhausted`。

### 2.2 Backend 状态迁移

#### 手工按钮触发

- `Disable`
  - `* -> disabled`
  - 立即生效，不需要 Probe。
- `Enable`
  - `disabled -> probing`
  - 必须自动触发一次单 Backend Probe。
  - Probe 成功后进入 `running`；Probe 返回 quota exhausted 后进入 `exhausted`；Probe 超时/连接失败/CLI 失败后进入 `unreachable`。
- `Probe`
  - 对单个 Backend 触发一次手工 Probe。
  - Probe 开始前状态切到 `probing`。
  - Dashboard 在 `state in {disabled, probing}` 时必须禁用单 Backend `Probe` 按钮；其它主状态下允许点击。
  - Probe 成功：清空连续 unhealthy failure 计数、清除 exhausted 标记，主状态切到 `running`。
  - Probe 返回 quota exhausted：主状态切到 `exhausted`。
  - Probe 超时/连接失败/CLI 失败：主状态切到 `unreachable`。

#### 系统自动触发

- `QuotaExhaustedError`
  - 进入 `exhausted`
  - 不计入连续 unhealthy failure。
- `BackendCallError` / transport error / timeout / poll timeout / empty response / completion_truncated
  - 计入连续 unhealthy failure。
  - 连续失败阈值默认 `3` 次；达到阈值后进入 `unreachable`。
  - 普通失败不得自动进入 `disabled`；`disabled` 只由用户开关或配置 `enabled=false` 产生。
  - 用户手工 `Probe` 或 `Enable` 成功时必须清零该 Backend 的 `failure_count`。
- `all_backends_busy`
  - 视为临时资源不足，不得直接视为最终失败。
  - `llm_tier client` 必须按固定间隔重提请求，默认 `retry_interval=10s`，默认最多等待 `600s`。
  - 只有超过 busy wait timeout 后，才允许将 busy 结果返回给上层。
  - 默认不得写入 LLM stats，也不得出现在 `/runtime.recent_errors`；需要排查 backend 全忙时，必须通过 runtime debug trace 开关记录。
- `context_length_exceeded`
  - 视为当前请求不适配，不计入 unhealthy，也不得把 Backend 记为 `unreachable` 或 `disabled`。

### 2.3 Backend Enabled 与 Runtime State 关系

- `enabled=false` 的 Backend 不参与路由，不计入 Tier `running/max`。
- `Enable` 后必须先通过 Probe 确认可用，才能重新参与路由。
- `Disable` 是用户表达“不使用该 Backend”的唯一操作；系统不得再维护独立选择池。

### 2.4 Dashboard 按钮

Tier dashboard 每行 Backend 必须提供以下按钮：

- `Disable` / `Enable`
  - 二选一显示。
- `Probe`
  - 对单个 Backend 手工 Probe。
状态列显示优先级必须为：

```text
disabled > probing > exhausted > unreachable > running
```

并且每行必须额外展示：

- 连续 unhealthy failure 次数，例如 `fail 2/3`
- `last_error`
- `last_error_at`

### 2.5 整体配置按钮

Tier dashboard 页头必须提供：

- `Refresh`
- `Load Config`
- `Save Config`

语义约束：

- `Load Config`
  - 从当前 `settings.json` 重新读取配置，覆盖 runtime 内存态。
  - 会丢弃未保存的 runtime 配置改动。
  - 不得清除 quota exhausted 状态和 stats 数据。
- `Save Config`
  - 将当前 runtime 的可持久化配置写回 `settings.json`。
  - 持久化内容至少包括：
    - `llm_tiers[*].model_name`
    - `llm_tiers[*].model_key`
    - `llm_tiers[*].max_context_tokens`
    - `llm_tiers[*].enabled`
    - `llm_tiers[*].weight`
- `Reload Runtime`
  - 不单独暴露成按钮；`Load Config` 已经承担回到文件定义状态的职责。

### 2.6 Provider Profile 与模型选择

`settings.json` 可以提供 `provider_profiles`，用于描述某个 provider 可选模型及其能力边界。Tier dashboard 必须优先从当前 backend 的 `provider` 查找 profile，并把 profile 中的模型渲染为可选列表。

当用户在 dashboard 中切换模型时，Tier Server 必须在同一个 backend 配置对象内同步更新：

- `model_name`
- `model_key`
- `max_context_tokens`

上述字段必须一起持久化回 `settings.json`。不得只修改展示名，也不得把同一 backend 的模型能力拆到其它 runtime override 结构中。

示例：

```json
{
  "provider_profiles": {
    "xfyun": {
      "models": [
        {
          "model_name": "DeepSeek-V3.2",
          "model_key": "xopdeepseekv32",
          "max_context_tokens": 128000
        }
      ]
    }
  }
}
```

不得再新增独立选择配置。Backend 是否参与调度只由其自身对象内的 `enabled`、`weight` 和 runtime health 决定。

以及每个 Tier model entry 支持：

```json
{
  "backend": "xf2/Qwen3-Coder-Next-FP8",
  "provider": "xfyun",
  "account": "xf2",
  "model_name": "Qwen3-Coder-Next-FP8",
  "enabled": true
}
```

### 2.7 Provider Usage 展示

Tier dashboard 必须在 `/runtime.accounts[*]` 展示云 provider 用量摘要。该摘要属于 provider/account 级别，不属于单次 LLM 调用统计，不能写入 `llm_stats`。Backend 行可以复用同一账号的 snapshot 做辅助展示，但不得把 provider usage 当成 Backend 独有数据。

`/runtime.accounts[*].provider_usage` 和 `/runtime.tiers[*][*].provider_usage` 字段格式一致：

```json
{
  "provider": "xfyun",
  "source": "provider_api",
  "status": "ok",
  "usage_key": "xfyun:account:xxxx",
  "account_key": "xxxx",
  "used": 12000,
  "quota": 100000,
  "remaining": 88000,
  "percent": 12.0,
  "reset_at": "2026-06-15 08:00",
  "window": "weekly",
  "windows": [
    {
      "name": "5hour",
      "used": 1200,
      "quota": 10000,
      "remaining": 8800,
      "percent": 12.0,
      "reset_at": "2026-06-11 10:00"
    }
  ],
  "checked_at": "2026-06-11T00:42:12Z",
  "error": ""
}
```

字段约束：

- `usage_key` 必须由 provider、scope 和 credential hash 构造，不能暴露 API Key、AK/SK、cookie。
- `provider` 和 `account` 是两个独立概念；同一 provider 可配置多个账号，每个账号必须有独立 usage cache key。
- provider usage 识别必须先归一化 provider 名；例如 `opencode_go`、`opencode-go` 都必须识别为 `opencode-go`，不能因为 backend adapter 名使用下划线而跳过真实 usage 查询。
- `account_key` 是账号维度的非敏感 hash，仅用于 Dashboard/API 区分同 provider 下的多个账号，不得暴露原始 API Key、AK/SK、cookie。
- `/runtime.accounts[*]` 表示 provider usage account，不表示 MLEXP 执行节点；例如 `mlexp:mnm/MiniMax-M2.5` 必须归入 `mnm`，`mlexp:omlx9/gemma-4-e2b-it-4bit` 必须归入 `omlx9`，不得把 `m5air` 或 MLEXP endpoint 作为额度账号行展示。
- backend 可显式配置 `usage_account_id/account_id` 作为 provider usage 账号维度；未配置时由 provider-specific credential 推导。
- 同一云账号下的多个 backend 必须尽量共享同一个 `usage_key` 和缓存结果，避免 dashboard 高频刷新压 provider。
- `source=provider_api` 表示真实 provider 接口返回。
- `source=config_schedule` 表示只能根据 `quota_type/reset_day` 推导 reset 时间，不能显示 used/quota。
- `source=credentials_missing` 表示 provider 有查询接口，但当前 backend 没有配置查询凭据。
- `source=provider_api_error` 表示接口调用失败，`error` 只能保存截断后的非敏感错误摘要。
- dashboard 只能展示 `/runtime` 返回的数据，不能在前端自行推导 provider usage。
- provider usage 默认必须使用 server 端缓存，避免 dashboard 自动刷新频繁打 provider 接口。
- 普通 `/runtime` 在 provider usage cache miss 时也不得同步访问外部 provider，必须返回 `status=not_refreshed` 或等价的未刷新状态。
- dashboard 自动刷新只能调用普通 `/runtime`，不得强制刷新 provider usage。
- 用户点击 dashboard 的 `Refresh` 按钮时，必须调用 `/runtime?refresh_usage=1`，由 server 忽略 provider usage cache 并重新查询一次。
- 用户点击 tier dashboard 的 `Reload Usage Credentials` 按钮时，必须调用 `/usage/reload`，只清空 provider usage cache 并重新读取 usage credential 文件，不得重建 router、不得触发 Backend Probe。
- Backend Probe 必须在状态收口前强制刷新当前 backend 对应账号的 provider usage cache；Probe 完成后普通 `/runtime` 必须能直接返回本次 Probe 写入的 `provider_usage` snapshot，不能因为普通自动刷新不触网而重新显示 `not_refreshed`。
- Backend Probe 的 provider usage 刷新失败时，不得由 Dashboard 推断为无限额度；Tier Server 必须返回 `source=provider_usage_error` 或 provider-specific error source、`status=unavailable` 和截断后的 `error` 摘要。
- tier dashboard 主表不得再显示独立 `Supplement` 列；quota reset 信息必须显示在 `Usage` 单元格内。
- Account 表的 `Usage` 单元格必须使用三层同心环展示 `5hour / weekly / monthly` 三个窗口：外层表示 `5hour`，中层表示 `weekly`，内层表示 `monthly`。
- 同心环中心默认不显示百分比；窗口百分比和 reset 时间必须放在 tooltip 或等价详情中展示。
- 本地模型或无额度上限窗口可以显示 `∞`；provider usage 缺失或查询失败必须显示未刷新/不可用状态，不得由前端推断为无限额度。

当前 provider usage 接入策略：

| Provider | 查询方式 | 凭据要求 | Reset 来源 |
|----------|----------|----------|------------|
| `volc` | 使用火山方舟 OpenAPI 域名 `ark.cn-beijing.volcengineapi.com`，通过 HMAC-SHA256 签名调用 `GetCodingPlanUsage` | `usage_access_key_id` 与 `usage_secret_access_key`，或 file-backed `usage_access_key_id_file` 与 `usage_secret_access_key_file`；允许复用账号级 `access_key_id/secret_access_key` | `QuotaUsage[].ResetTimestamp` |
| `minimax` | 优先使用 MiniMax 平台接口 `https://www.minimaxi.com/v1/api/openplatform/coding_plan/remains`；无平台登录态时可使用 `https://api.minimaxi.com/v1/coding_plan/remains`；`https://www.minimaxi.com/backend/account/token_plan/usage_summary` 只作为用量明细补充来源 | 平台路径需要 `usage_cookie` 或 `usage_cookie_file/console_cookie_file`，并可配置 `usage_group_id/group_id`；API 路径需要 `api_key` 或 `api_key_file` | provider 返回的 `end_time/weekly_end_time`；usage_summary 不作为 quota ring reset 权威来源 |
| `xfyun` | 讯飞 MaaS `CodingPlan` 页面同源接口 `/api/v1/gpt-finetune/coding-plan/list` | account 或 backend 内配置 `usage_cookie` 或 `usage_cookie_file/console_cookie_file` | backend/account `quota_type/reset_day` 推导 |
| `opencode-go` | opencode workspace 页面 SSR 数据，读取 `rollingUsage/weeklyUsage/monthlyUsage` | account 或 backend 内配置 `usage_workspace_url` 与 `usage_cookie` 或 `usage_cookie_file/console_cookie_file` | SSR 数据中的 `resetInSec` |

火山注意事项：

- 火山 Coding Plan 用量只允许使用 AK/SK 签名的 `GetCodingPlanUsage` 路径；不得保留 Console cookie、CSRF、web-id、`/api/coding/v1/quotas` 或 `GetAFPUsage` fallback。
- `GetCodingPlanUsage` 返回 `QuotaUsage[]`，字段包括 `Level`、`Percent`、`ResetTimestamp`；该接口可能只返回百分比，不返回 `used/quota` 绝对值，Dashboard 必须允许 `used/quota=null` 且 `percent` 有值的窗口，并直接用 `percent` 渲染圆环。
- `Level=session/weekly/monthly` 在 Dashboard 中归一为 `5hour/weekly/monthly`。
- 模型调用使用的 API Key 不是 usage credential，不得替代 AK/SK；缺少任一 AK/SK 文件时必须返回 `credentials_missing`。
- `GetAFPUsage` 返回 Agent Plan 用量，不是 Coding Plan authority；即使调用成功且数值为零，也不得覆盖 Coding Plan 用量。

MiniMax 注意事项：

- MiniMax 平台 `/v1/api/openplatform/coding_plan/remains` 当前返回 `model_remains[]`，字段包括 `current_interval_remaining_percent`、`current_weekly_remaining_percent`、`end_time`、`weekly_end_time`。
- MiniMax 返回的是剩余额度百分比，Tier 必须转换为 Dashboard 使用的已用百分比：`used_percent = 100 - remaining_percent`。
- MiniMax 的 `current_interval_*` 在 Dashboard 中归一为 `5hour`，`current_weekly_*` 归一为 `weekly`。
- MiniMax `usage_summary` 只对应页面下方“订阅套餐用量详情/调用趋势”，可用于展示近 7 天 / 近 30 天调用量明细，但不得用于 `5hour/weekly/monthly` quota 圆环。
- `X-Group-Id` 可由 backend `usage_group_id/group_id` 配置；未配置时可从 cookie `minimax_group_id_v2` 推导。

opencode-go 注意事项：

- opencode-go 当前页面 `https://opencode.ai/workspace/<workspace_id>/go` 的 HTML 中包含 SSR hydration 数据，例如 `rollingUsage`、`weeklyUsage`、`monthlyUsage`。
- 每个窗口包含 `usagePercent` 和 `resetInSec`，不包含 `used/quota` 绝对值；Dashboard 必须按 percent-only 窗口渲染。
- `rollingUsage` 在 Dashboard 中归一为 `5hour`，`weeklyUsage/monthlyUsage` 分别归一为 `weekly/monthly`。

讯飞注意事项：

- `https://maas.xfyun.cn/packageSubscription` 是前端页面；真实 CodingPlan 用量由同源接口 `/api/v1/gpt-finetune/coding-plan/list` 返回。
- Chrome Network 中调试 CodingPlan 用量时应过滤 `coding-plan/list`；`token-plan/seats` 只对应 Token Plan 页面，不对应 CodingPlan 页面。
- 该接口依赖网页登录态，未登录时返回 `用户未登录`，因此 Tier 不能只靠 OpenAI-compatible API Key 查询。
- 讯飞同一个 Console 登录态可返回多个 CodingPlan 套餐；Tier 必须按 backend API key 匹配 `codingPlanAppCredentialDTO.apiKey`，并以 API key hash 作为账号维度，避免 `xf2` 等不同账号共用同一个 usage cache。
- 如果某个 xfyun 兼容 backend 没有直接配置 API key，但需要绑定某个套餐账号，必须显式配置 `usage_account_id/account_id`。
- 若需要真实显示讯飞用量，必须在 backend 对象内配置 console cookie 文件，例如：

```json
{
  "backend": "xf2/Qwen3-Coder-Next-FP8",
  "provider": "xfyun",
  "account": "xf2",
  "model_name": "Qwen3-Coder-Next-FP8",
  "model_key": "xop3qwencodernext",
  "quota_type": "weekly",
  "reset_day": "Monday",
  "usage_cookie_file": "workspaces/secrets/xfyun_console.cookie"
}
```

#### `tier.get_tier_info(tier_name: str) -> dict`

返回指定 Tier 的配置和当前状态：
```python
{
    "tier": "Worker",
    "models": [
        {"backend": "xf2/Qwen3-Coder-Next-FP8", "account": "xf2", "model_name": "Qwen3-Coder-Next-FP8", "backend_type": "API", "exhausted": False},
        {"backend": "minimax", "account": "mnm", "model_name": "MiniMax-M2.7", "backend_type": "API", "exhausted": False},
    ]
}
```

#### `tier.reset_exhausted(tier_name: str = "") -> None`

重置额度耗尽标记，并同步清理对应 Backend 的 router runtime failure 状态。

- `tier_name` 为空时重置全部 Tier。
- `tier_name` 非空时只重置该 Tier 下的 Backend。
- Reset 必须同时清理 quota store、router runtime status、最近错误和连续失败计数。
- Reset 不得恢复人工 disabled 的 Backend；人工 disabled 只能通过 enable/probe 流程恢复。
- Reset 后 `/runtime` 展示状态与 router 实际可路由状态必须一致，不能出现 Dashboard 显示 `running` 但 router 仍排除为 `runtime_exhausted` 的状态。
- Reset 不负责复活已经完成失败的 job；如果某次调用已经以 `runtime_exhausted` / `all_backends_unavailable` 结束，Reset 后只能保证后续新调用重新按清理后的 runtime state 路由。

### 3. 统计接口

#### `tier.get_stats(query: TierStatsQuery) -> list[TierStatsRow]`

按条件查询统计，支持按 project / stage / phase / task / task_id_prefix / tier / backend / role / time 维度筛选。

数据源：`workspaces/tier_state/llm_stats.sqlite3`（由 stats_collector 写入）。

统计事件必须保留以下 runtime 关联字段，供 dashboard 和后续报表全链读取：

- `project_name`
- `stage_name`
- `phase_name`
- `task_id`
- `task_key`
- `role`
- `backend`
- `model`
- `backend_type`
- `call_count`
- `failed_call_count`
- `cached_tokens`
- `prompt_chars`
- `completion_chars`
- `provider_usage_available`
- `usage_source`

普通 backend 的 `call_count` 默认为 1；MLEXP backend 的 `call_count` 必须使用 MLEXP report 中的内部 LLM 调用次数。stats_collector 聚合 `calls/success_count/fail_count` 时必须使用 `call_count/failed_call_count`，不得再用 SQLite event 行数代替调用次数。

`task_id` 是全链统计主键，必须使用完整 runtime task id：

```text
{stage}::{phase}::{task_key}
```

`task_key` 只作为 phase-local alias 使用，不得作为全局主键。

dashboard 读取规则：

- `LLM Stats By Stage` 必须从 `/stats` 的 stage 维度统计生成。
- `LLM Stats By Tier` 必须从 `/stats` 的 tier / backend 维度统计生成。
- Phase 展开时，dashboard 必须按当前 Phase 的 `stage`、`phase`、`task_id_prefix={stage}::{phase}::` 读取 task 维度统计，不能逐个 Task 请求，也不能在 JS 中扫描全项目 LLM events 后自行聚合。
- Phase 展开读取 task 维度统计时，dashboard 必须把当前已加载 Task 的 `{task_id: started_at}` 映射作为 `task_started_at_map` 传给 `/stats`；`stats_collector` 必须在 SQLite 查询侧按每个 Task 自己的 `started_at` 过滤，不能用 Phase 的 `started_at` 代替 Task run 边界。
- Task 行必须按完整 `task_id` 匹配实时统计；`task_id_prefix` 只用于批量取出同一 Phase 下的 Task 统计行。
- Phase 展开行必须由当前 Phase 下 task 的 `/stats` 记录聚合得到，且必须使用当前 Phase 的 `started_at` 作为时间过滤边界。
- `task.summary.json`、`phase.summary.json`、`stage.summary.json` 不得保存 LLM 字段或 metrics fallback；dashboard 必须通过 `/stats` 获取 LLM 统计。

`group_by` 查询必须由 stats_collector 在 SQLite 侧读取并聚合，dashboard 只负责选择查询 scope 和展示结果。stats_collector 可以维护聚合 cache，但 cache 命中必须绑定 query key、匹配事件数量和最大 event id；只要新的 `llm_call` 写入，旧 cache 必须自动失效。

#### `tier.get_summary() -> dict`

获取全局概览：
```python
{
    "total_calls": 12345,
    "total_tokens": 98765432,
    "total_fallback_count": 23,
    "exhausted_backends": ["xfyun"],
    "active_backends": ["xfyun", "volc", "codex"]
}
```

---

## 二、内层路由（llm_router）

### Router Core

```python
class LLMRouter:
    """内层路由 — Backend 选择 + Fallback"""

    def call(
        self,
        role_name: str,
        prompt: str,
        temperature: float,
        timeout_seconds: int | None,
        metadata: dict[str, str],
    ) -> tuple[TierCallResult, dict[str, Any]]:
        """
        返回：(result, stats_event)
        - result: 最终结果（可能成功也可能全部耗尽失败）
        - stats_event: 给 stats_collector 的结构化事件（含 tier/account/model/latency/tokens/fallback）

        流程：
          1. role → Tier 映射
          2. 循环（最多 Tier 内 Backend 数量次）：
             a. 按策略选择最优 Backend
             b. 获取并发许可
             c. 调用 Backend
             d. 成功 → 构建 stats_event → return (result, stats_event)
             e. QuotaExhaustedError → 标记 exhausted → fallback_count++ → 继续
             f. 其他异常 → 记录 error → 继续（可选，取决于是否 retry 其他 backend）
          3. 全部耗尽 → return (error_result, stats_event)
        """
```

Router 只返回 `(result, stats_event)`，**不写入**统计。stats_event 由外层 `tier_core` 统一写入 `stats_collector`。

### 路由策略

Router 只保留 ordered weighted ring 这一种路由机制：

1. 按 Tier 配置文件中的 Backend 顺序读取候选。
2. 过滤 `disabled / probing / exhausted / unreachable / account_missing / request_failed / request_busy`。
3. 按剩余候选的配置顺序展开 `weight`。
4. 使用每个 Tier 独立 cursor 在展开后的列表中轮询。
5. Router 必须在同一临界区内扫描 ring、跳过 account 并发满或调用间隔未到的 backend、占用第一个可用 backend 对应 account 的并发槽，并把 cursor 移到被占用 slot 的下一个位置。
6. 如果 ring 中全部候选都因为 `account_concurrency_full / account_interval_wait / account_rate_limit_wait / runtime_probing / request_busy` 暂时不可用，返回 `all_backends_busy`，由 client 轮询重试；server 不维护 backend queue。

示例：

```text
配置：b1.weight=1, b2.weight=1, b3.weight=2
展开：b1, b2, b3, b3
选择：b1 -> b2 -> b3 -> b3 -> b1 ...
```

### Account 与并发管理（concurrency.py）

Account 是凭证、额度、账号级并发和调用间隔的主体；Backend 是 Tier 内可调度的模型入口。一个 Account 可以被多个 Backend 引用，Backend 可以是 API、CLI 或 MLP 形式，也可以使用同一 Account 下的不同模型。

配置结构：

```json
{
  "llm_accounts": {
    "xf2": {
      "provider": "xfyun",
      "max_concurrent_requests": 5,
      "min_request_interval_ms": 500,
      "requests_per_minute": 120,
      "api_key": "...",
      "base_url": "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2",
      "usage_cookie_file": "workspaces/secrets/xfyun_console.cookie",
      "quota_type": "weekly",
      "reset_day": "Monday"
    }
  },
  "llm_tiers": {
    "Worker": [
      {
        "backend": "xf2/Qwen3-Coder-Next-FP8",
        "provider": "xfyun",
        "account": "xf2",
        "model_name": "Qwen3-Coder-Next-FP8",
        "model_key": "xop3qwencodernext",
        "weight": 1,
        "enabled": true
      }
    ]
  }
}
```

规则：

- Account 的 `max_concurrent_requests` 是同一账号跨 Tier、跨 Backend、跨模型的全局硬上限。
- Account 的 `min_request_interval_ms` 表示同一账号两次请求启动之间的最小间隔；未到时间时视为 `account_interval_wait`，不是失败。
- Account 的 `requests_per_minute` 表示同一账号 60 秒滑动窗口内允许启动的最大请求数；超过时视为 `account_rate_limit_wait`，不是失败。
- Backend 不再配置最大并发；Backend 行只展示当前运行数。
- Tier 汇总只展示当前运行数，不展示 Backend 最大并发之和。
- Tier Dashboard 必须提供 Account 配置表，展示并允许修改 Account 的 `running/max`。

```python
class BackendConcurrencyManager:
    """Account identity 级 semaphore 控制，同时记录 Backend identity 当前运行数"""
    def __init__(self, account_config: dict[str, dict]): ...
    def acquire(self, backend_key: str, account_key: str) -> tuple[bool, str]:
        """获取账号并发许可。账号槽满或调用间隔未到返回 False 和 busy reason"""
        ...
    def release(self, backend_key: str, account_key: str) -> None: ...
    def get_load(self, backend_key: str) -> int:
        """返回当前 Backend 运行数"""
        ...
    def get_account_load(self, account_key: str) -> int:
        """返回当前 Account 运行数"""
        ...
```

```
Account identity 级 semaphore:
  mnm                  max 5 并发
  volc                 max 10 并发
  xf2                  max 5 并发
  omlx8                max 4 并发
  omlx9                max 4 并发

Tier 路由:
  请求到达 → ordered weighted ring 原子选择 backend 并占用其 account semaphore → 执行
  若全部 backend 引用的 account 槽满、间隔未到或每分钟请求数已满，返回 all_backends_busy，由 client 按固定间隔轮询重试；server 不维护 backend queue。
```

Backend running、ordered weighted ring cursor、请求内 `busy / failed` 排除集合、`/runtime` 的 `load / running` 展示必须使用 runtime identity：`tier:account:model_name`。Account 并发、调用间隔和 usage 必须使用 account identity：`account`。同一个 Account 下配置多个 Backend 时必须共享 Account 并发池；同一个 `account:model_name` 出现在不同 Tier 时必须分别维护 Backend 状态，不得因为 Worker 中的 `omlx8/Qwen3.6-35B-A3B` disabled 而同时 disabled Associate 中的 `omlx8/gemma-4-e2b-it-4bit`。

### 额度管理（quota_manager.py）

```python
class QuotaManager:
    """
    运行时内存状态，不持久化。

    自动重置：每次 is_exhausted() 调用时检查 llm_quota_config.reset_day，
    如果当前时间已过重置点，自动清除该 Backend 的 exhausted 标记。
    """
    def __init__(self, tier_config: TierConfig): ...
    def is_exhausted(self, backend: str, model_name: str) -> bool: ...
    def mark_exhausted(self, backend: str, model_name: str) -> None: ...
    def reset_all(self) -> None: ...
    def reset_tier(self, tier_name: str) -> None: ...

    @staticmethod
    def is_quota_error(error_message: str) -> bool:
        """判断错误文本是否表示额度耗尽（从 backend_fallback.py 移入）"""
        ...
```

触发标记：`QuotaExhaustedError`（由 Backend 客户端抛出）。

---

## 三、配置管理（tier_config.py）

```python
class TierConfig:
    """纯配置加载器，从 settings.json 读取，不做业务逻辑"""

    def __init__(self, settings_path: str | None = None):
        """不传路径则自动查找 workspaces/<project>/settings.json"""
        ...

    # 模型池
    def get_tier_models(self, tier_name: str) -> list[TierModel]:
        """返回指定 Tier 的模型列表，保持配置文件顺序"""
        ...

    # Account 并发
    def get_account_concurrency(self, account: str) -> dict[str, Any]:
        """返回 {"max_concurrent_requests": N, "min_request_interval_ms": N, "requests_per_minute": N}，未配置用默认值"""
        ...

    # 额度重置
    def get_quota_config(self, backend: str) -> dict[str, Any] | None:
        """返回 {"quota_type": "weekly", "reset_day": "Monday"} 或 None"""
        ...

    # 热重载
    def reload(self) -> bool:
        """重新读取 settings.json。失败返回 False，已有配置不变"""
        ...

    # 是否启用
    def is_enabled(self) -> bool:
        """默认 True。设为 False 时 tier.call() 直接走兜底"""
        ...
```

---

## 四、Backend 统一接口

### BaseBackendClient

```python
class BaseBackendClient(ABC):
    @property
    @abstractmethod
    def backend(self) -> str:
        """Backend 标识，如 "xfyun"、"codex" """
        ...
    @property
    @abstractmethod
    def backend_type(self) -> str:
        """"API" | "CLI" | "agent" """
        ...
    @abstractmethod
    def supported_models(self) -> list[str]: ...
    @abstractmethod
    def call(
        self,
        model_name: str,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.0,
        timeout_seconds: int = 600,
        metadata: dict[str, str] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        返回：
        {
            "ok": bool,
            "content": str,
            "model_name": str,
            "latency_ms": float,
            "token_usage": {"prompt_tokens": N, "completion_tokens": N, "total_tokens": N},
            "raw_response": dict,
            "error_code": int,
            "error_message": str,
        }
        异常：
        · QuotaExhaustedError  — 额度耗尽
        · BackendCallError     — 其他调用错误
        """
        ...
```

### api 类型 — 公共逻辑（api_backend.py）

```python
class ApiBackendMixin:
    """api Backend 公共逻辑：HTTP POST + 重试 + 错误转换"""

    def _post_json(self, url: str, payload: dict, timeout: int) -> dict:
        """发送 POST 请求，返回解析后的 JSON dict"""
        ...

    def _handle_http_error(self, status_code: int, body: str, retry_count: int, max_retry: int) -> None:
        """
        错误处理：
          · 429 / quota / NotEnoughCv → QuotaExhaustedError
          · 5xx + retry_count < max_retry → 不抛异常，调用方重试
          · 5xx + retry_count >= max_retry → BackendCallError
          · 其他 → BackendCallError
        """
        ...
```

### agent 类型 — 公共逻辑（agent_backend.py）

```python
class AgentBackendMixin:
    """agent Backend 公共逻辑：subprocess + 文件锁 + stdout 捕获"""

    def _run_cli(self, command: list[str], cwd: str, timeout: int, input_text: str) -> dict:
        """
        执行 CLI 命令，返回 {"returncode": int, "stdout": str, "stderr": str, "timed_out": bool}
        """
        ...

    def _write_result_message(self, stdout: str, output_path: str) -> None:
        """将 stdout 写入 --output-last-message 等价文件"""
        ...

    def _acquire_file_lock(self, lock_path: str) -> bool:
        """获取文件锁，已存在且进程存活则阻塞等待"""
        ...
```

### api 类型

```
通讯：HTTP POST /chat/completions（OpenAI 兼容格式）
并发：多路（semaphore 控制上限）
错误：
  · HTTP 429 / quota 字样 → QuotaExhaustedError
  · NotEnoughCv → QuotaExhaustedError
  · HTTP 5xx → 重试 3 次 → BackendCallError
  · 超时 → BackendCallError
```

### agent 类型

```
通讯：subprocess.run
并发：单路（semaphore=1 + 文件锁），通过 Python 层补齐 CLI 不支持的能力：
  · --cd <path>          → subprocess.run(cwd=...)
  · --output-last-message → 捕获 stdout 写入文件
  · --skip-git-repo-check → Python 层静默跳过
token_usage：agent 通常不返回 token 数 → 填 {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
错误：
  · returncode != 0 / quota_exceeded 字样 → QuotaExhaustedError
  · 超时 → BackendCallError
```

### Backend 注册

```python
# src/llm_tier/backends/__init__.py

_registry: dict[str, type[BaseBackendClient]] = {}

def register_backend(name: str, cls: type[BaseBackendClient]) -> None:
    _registry[name] = cls

def get_backend_client(name: str, **init_kwargs) -> BaseBackendClient | None:
    cls = _registry.get(name)
    return cls(**init_kwargs) if cls else None

def list_backends() -> list[str]:
    return list(_registry.keys())
```

每个 `backends/*.py` 在模块底部调用 `register_backend("xfyun", XfyunClient)` 完成注册。

---

## 五、统计（stats_collector.py）

```python
class StatsCollector:
    """统计收集器：每调用一次写一行到 llm_stats.sqlite3"""

    def __init__(self, stats_dir: str):
        """stats_dir = workspaces/tier_state/"""
        ...

    def write(self, event: dict[str, Any]) -> None:
        """
        写入一条 SQLite llm_call。event 字段：
          ts, project, tier, backend, backend_type, model, role,
          ok, latency_ms, prompt_tokens, completion_tokens, total_tokens,
          is_fallback, fallback_count, error_code, error_message
        写失败只打 WARN 日志，不抛异常。
        """
        ...

    def get_stats(self, query: TierStatsQuery) -> list[TierStatsRow]:
        """读取 SQLite，按 query 条件过滤，聚合计数 + 分位延迟，返回"""
        ...

    def get_grouped_stats(self, query: TierStatsQuery, group_by: str) -> list[dict[str, Any]]:
        """按 stage / phase / task / tier / backend 返回 SQLite 聚合行，并允许复用有效聚合 cache"""
        ...

    def get_summary(self) -> dict[str, Any]:
        """
        返回 {"total_calls": N, "total_tokens": N, "total_fallback_count": N,
               "exhausted_backends": [...], "active_backends": [...]}
        """
        ...
```

写入格式（SQLite `llm_call.raw_json` 示例）：
```json
{"ts":"2026-05-29T08:00:00Z","project":"llm_json_interpreter","tier":"Worker",
 "backend":"volc","backend_type":"API","model":"deepseek-v3-2-251201",
 "role":"unit_test_case_group_reviewer","ok":true,"latency_ms":1234,
 "prompt_tokens":500,"completion_tokens":200,"total_tokens":700,
 "is_fallback":false,"fallback_count":0}
```

---

## 六、settings.json 配置

```json
{
  "llm_tier": {
    "enabled": true
  },
  "llm_tiers": {
    "Senior": [
      { "backend": "opencode:volc/glm-5.2", "provider": "opencode", "account": "volc", "model_name": "volc/glm-5.2", "model_key": "volc/glm-5.2", "backend_type": "CLI", "enabled": true, "weight": 2, "timeout_seconds": 600, "max_context_tokens": 200000 }
    ],
    "Junior": [
      { "backend": "opencode:mnm/MiniMax-M3", "provider": "opencode", "account": "mnm", "model_name": "mnm/MiniMax-M3", "model_key": "mnm/MiniMax-M3", "backend_type": "CLI", "enabled": true, "weight": 1, "timeout_seconds": 600, "max_context_tokens": 1000000 },
      { "backend": "opencode:volc/kimi-k2.6", "provider": "opencode", "account": "volc", "model_name": "volc/kimi-k2.6", "model_key": "volc/kimi-k2.6", "backend_type": "CLI", "enabled": false, "weight": 1, "timeout_seconds": 600, "max_context_tokens": 1000000 }
    ],
    "Worker": [
      { "backend": "minimax", "provider": "minimax", "account": "mnm", "model_name": "MiniMax-M2.7", "model_key": "MiniMax-M2.7", "backend_type": "API", "enabled": true, "weight": 1, "max_context_tokens": 1000000 },
      { "backend": "xf2/Qwen3-Coder-Next-FP8", "provider": "xfyun", "account": "xf2", "model_name": "Qwen3-Coder-Next-FP8", "model_key": "xop3qwencodernext", "backend_type": "API", "enabled": true, "weight": 1 },
      { "backend": "omlx8/Qwen3.6-35B-A3B", "provider": "omlx", "account": "omlx8", "model_name": "Qwen3.6-35B-A3B", "model_key": "Qwen3.6-35B-A3B-4bit-MTPLX-Optimized-Speed", "backend_type": "API", "enabled": false, "weight": 1 }
    ],
    "Associate": [
      { "backend": "omlx", "provider": "omlx", "account": "omlx8", "model_name": "gemma-4-e2b-it-4bit", "model_key": "gemma-4-e2b-it-4bit", "backend_type": "API", "enabled": true, "weight": 1 },
      { "backend": "omlx", "provider": "omlx", "account": "omlx9", "model_name": "gemma-4-e2b-it-4bit", "model_key": "gemma-4-e2b-it-4bit", "backend_type": "API", "enabled": true, "weight": 1 }
    ],
    "Foreman": [
    ],
    "Engineer": [
      { "backend": "mlexp:mnm/MiniMax-M2.5", "provider": "minimax", "account": "mnm", "model_name": "MiniMax-M2.5", "model_key": "MiniMax-M2.5", "backend_type": "MLP", "enabled": true, "weight": 1, "timeout_seconds": 600, "max_context_tokens": 1000000, "base_url": "http://192.168.1.9:8001", "remote_workspace_root": "/Users/mlp/workspaces" }
    ],
    "Executor": [
      { "backend": "mlexp:omlx9/gemma-4-e2b-it-4bit", "provider": "omlx", "account": "omlx9", "model_name": "gemma-4-e2b-it-4bit", "model_key": "gemma-4-e2b-it-4bit", "backend_type": "MLP", "enabled": true, "weight": 1, "timeout_seconds": 600, "max_context_tokens": 65536, "ssh": { "host": "192.168.1.9", "user": "mlp", "port": 22 } }
    ]
  },
  "role_tier_map": {
    "review_arbiter": "Worker",
    "drift_controller": "Worker",
    "execution_fixer": "Senior",
    "escalator": "Senior",
    "unit_test_fixer": "Senior",
    "system_test_fixer": "Senior",
    "preflight_engineer": "Executor",
    "system_testing_engineer": "Executor",
    "drift_risk_manager": "Junior",
    "drift_classifier": "Junior",
    "requirement_author": "Junior",
    "system_design_author": "Junior",
    "module_design_author": "Junior",
    "subsystem_design_author": "Junior",
    "unit_test_case_author": "Junior",
    "unit_test_case_group_author": "Junior",
    "unit_test_case_catalog_author": "Junior",
    "coding_reviewer": "Worker",
    "unit_test_case_reviewer": "Worker",
    "unit_test_case_group_reviewer": "Worker",
    "unit_test_case_catalog_reviewer": "Worker",
    "unit_test_case_reviser": "Worker",
    "unit_test_case_group_reviser": "Worker",
    "rag_judger": "Associate"
  },
  "llm_accounts": {
    "mnm": { "provider": "minimax", "max_concurrent_requests": 5, "min_request_interval_ms": 500, "requests_per_minute": 120 },
    "volc": { "provider": "volc", "max_concurrent_requests": 10, "min_request_interval_ms": 500, "requests_per_minute": 120 },
    "xf2": { "provider": "xfyun", "max_concurrent_requests": 5, "min_request_interval_ms": 500, "requests_per_minute": 120 },
    "omlx8": { "provider": "omlx", "max_concurrent_requests": 4, "min_request_interval_ms": 500, "requests_per_minute": 120 },
    "omlx9": { "provider": "omlx", "max_concurrent_requests": 4, "min_request_interval_ms": 500, "requests_per_minute": 120 }
  },
  "llm_backend_capabilities": {
    "opencode:volc/glm-5.2": { "max_context_tokens": 1000000 },
    "opencode:mnm/MiniMax-M3": { "max_context_tokens": 1000000 },
    "opencode:volc/kimi-k2.6": { "max_context_tokens": 1000000 },
    "minimax:MiniMax-M2.7": { "max_context_tokens": 200000 },
    "xf2/Qwen3-Coder-Next-FP8": { "max_context_tokens": 262144 },
    "omlx": { "max_context_tokens": 128000 }
  },
  "llm_quota_config": {
    "xf2":  { "quota_type": "weekly",  "reset_day": "Monday" },
    "volc": { "quota_type": "monthly", "reset_day": 1 },
    "mnm":  { "quota_type": "monthly", "reset_day": 1 }
  }
}
```

`model_name` 是 dashboard 和统计展示名；`model_key` 是传给 backend 的真实 runtime model id。MiniMax Token Plan API Backend 使用 Anthropic-compatible endpoint；opencode agent Backend 的 `model_key` 使用 `account/model` 形式，例如 `mnm/MiniMax-M3`、`volc/glm-5.2`。

`llm_backend_capabilities` 描述 backend 或 backend:model 的能力边界。查找顺序为 `backend:model_key`、`backend:model_name`、`backend`。当前支持：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `max_context_tokens` | int | backend 或模型最大上下文 token 数；未配置或为 0 时不做 context 预检 |
| `reserved_completion_tokens` | int | 为 completion 预留的 token 数；未配置时使用 backend credentials 的 `max_tokens`，再退回默认 `4096` |

Router 在进入 backend 选择前先执行 Upshift 判断，然后在选中 backend 并取得并发槽位后、真正调用 backend 前执行 context 预检：

1. 用轻量估算函数计算 `estimated_prompt_tokens`。
2. 对当前 Tier 的每个 backend 计算 `prompt_capacity_tokens = max_context_tokens - reserved_completion_tokens`；其中 `reserved_completion_tokens` 优先使用 `max_output_tokens`，再使用 `reserved_completion_tokens`，最后退回 `DEFAULT_MAX_OUTPUT_TOKENS`。
3. 当前 Tier 只要存在一个已配置上下文上限的 backend 可以容纳 `estimated_prompt_tokens`，本次请求就留在当前 Tier；如果 backend 未配置 `max_context_tokens` 或配置为 0，则视为不触发 Upshift，由后续标准 context 预检负责。
4. 当原始 Tier 是 `Associate` 且当前 prompt 超过 Associate backend prompt 容量时，本次请求执行 Upshift 到 `Worker`；当原始或中间 Tier 是 `Worker` 且当前 prompt 超过 Worker backend prompt 容量时，本次请求执行 Upshift 到 `Junior`。
5. Upshift 可以逐级执行，例如 Associate backend 容量不足且 Worker backend 容量也不足时，实际路由可从 `Associate` 继续提升到 `Junior`。
6. Upshift 只改变本次请求的实际 Tier，不修改 role 配置，不新增独立配置路径，也不改变原始 backend 状态。
7. 若目标 Tier 不存在或没有 backend，Router 记录 `router.upshift.target_missing`，并按当前 Tier 继续走标准 context 预检和错误返回。
8. 标准 context 预检仍以最终选中的 backend 为准；若 `estimated_total_tokens > max_context_tokens`，直接返回 `error_code=1006`，`error_message=context_length_exceeded: ...`。
9. context 超限不触发同 Tier fallback，避免把同一个超大 prompt 继续发送给同一能力边界内的其他 backend；Upshift 是进入 backend 选择前的跨 Tier 路由提升。
10. Router 必须在内存 runtime state 中记录实际执行的 Upshift 次数，并通过 `/runtime.summary.upshift_count` 返回；只有成功切换到目标 Tier 的请求才计数，`router.upshift.target_missing` 不计数。
9. `/runtime` 和 `/health` 输出每个 backend 的 `max_context_tokens`，并在 `accounts` 列表输出每个 account 的 `running/max`。
10. Tier dashboard 在 `Context` 列展示最大上下文，在 Backend 主表展示当前 running，在 Account 配置表展示并允许修改 `R/M`，在顶部摘要展示 `Upshift` 计数。
11. `/runtime` 必须额外返回 `recent_errors`，包含最近失败请求的 `error_code`、`error_message`、tier/backend/model、stage/phase/task 与 prompt 长度；Tier dashboard 必须在底部展示最近错误日志窗口，便于定位 `context_length_exceeded`、`completion_truncated`、timeout 与 transport error。

---

## 七、接口集成：现有代码改造

### 调用链路对比

```
旧：
   Stage Process
     → role_proxy.invoke_role()
       → llm_proxy.invoke()                    ← _invoke_with_retry
         → _invoke_single_backend()            ← 硬编码 backend:model

新：
   Stage Process
     → TierClient.invoke_role()                ← 统一入口，外部只知 Role
       → TierCore.call(req=TierCallRequest)    ← Role → Tier 路由
         → llm_router.call()                   ← 路由+fallback
           → BaseBackendClient.call()           ← 具体 Backend
```

### 需修改的模块

| 模块 | 改动 | 说明 |
|------|------|------|
| `src/llm_tier/tier_model.py` | **新建** | 数据模型 |
| `src/llm_tier/exceptions.py` | **新建** | QuotaExhaustedError 等 |
| `src/llm_tier/tier_config.py` | **新建** | 纯配置加载器 |
| `src/llm_tier/backends/base.py` | **新建** | Backend 统一接口 |
| `src/llm_tier/backends/__init__.py` | **新建** | Backend 注册表 |
| `src/llm_tier/backends/{api_backend,minimax,xfyun,volc}.py` | **新建** | API Backend 封装 |
| `src/llm_tier/backends/{agent_backend,opencode,mlexp}.py` | **新建** | CLI agent封装与MLEXP Subsystem HTTP adapter |
| `src/llm_tier/router_core.py` | **新建** | 路由 + Fallback 循环 |
| `src/llm_tier/tier_core.py` | **新建** | 外层入口 + 统计写入 |
| `src/llm_tier/stats_collector.py` | **新建** | 统计持久化与查询 |
| `src/core/roles.py` | **改** | `_build_role_prompt_metadata` 补 `project_name` / `task_key` |
| `src/llm_tier/client.py` | **新建** | TierClient — 对外统一入口，invoke_role() |

### 单机制约束

- **统一入口**：所有 Role 调用只走 `TierClient.invoke_role()`；Tier disabled、Role 未映射或目标 Tier 未配置可路由 Backend 时必须显式失败，不得回退旧 selector、旧配置或第二套直连机制
- **Backend 封装**：API、CLI agent 与 MLP 的差异只允许存在于 `src/llm_tier/backends/` 内；外部调用统一走 `TierClient.invoke_role()`
- **Dashboard LLM Stats**：Tier 统计通过 SQLite-backed stats API 提供，可合并到现有 Dashboard 的 "LLM Stats By Backend" 表格
- **回归保证**：迁移后的调用点必须保持统一 Tier 语义；不得以兼容名义恢复旧 Role selector 或直接 Backend 路由

---

## 八、测试方案

当前权威测试设计见 `test/subsystem/tier/SUBSYSTEM_TEST_DESIGN.md`。系统测试 case 必须按“每个 case 一个目录、每个 case 一个脚本、每个 case 一个 report”的方式组织：

```text
test/subsystem/tier/case/tier-<GROUP>-<NNN>/
├── case.md
├── data/functional.json
├── data/mock_valid.json
├── data/mock_mutation.json
├── oracle/expected.json
├── run.py
├── debug/report.json
└── report.json
```

当前权威基线共196个case，稳定编号与分组由`test/subsystem/tier/case_pack.md`定义：

| 维度 | Case 数 | 重点 |
|------|---------|------|
| Runtime / HTTP / Management | 53 | Service lifecycle、HTTP boundary、配置、probe、管理操作 |
| Routing / Quota / Conflict | 46 | upshift、quota/exhaustion、并发与运行时冲突 |
| Invoke / Usage / MLEXP / Stats | 38 | 真实Backend输出、usage window、MLEXP Agent、identity统计 |
| Dashboard / Migration | 32 | 统一Dashboard、same-origin、无Tier HTTP listener和旧入口 |
| Failure / Pipeline / Performance / Security / Report | 27 | 失败传播、Stage集成、负载、安全与报告gate |
| **Total** | **196** | 每case独立脚本、data、oracle和双向mock debug |

新增或高风险维度的强制语义：

- `ROUTING_EDGE_QUOTA_CONCURRENCY` 必须真实触发 quota fallback、全 exhausted、reset 恢复、context upshift、account 并发串行化、调用间隔、RPM、跨 account 并行、disabled backend 副作用隔离。
- `RUNTIME_CONFLICTS` 必须真实触发运行时冲突，不能只检查静态配置；包括 startup probe 中调用、双 probe 竞态、load/save config 中 running call、reset exhausted 后续恢复、disable/enable probe 中调用、动态并发更新、model-name 切换和 usage reload。
- 每个 case 的 `reports/` 必须保存至少一份带环境标识的可审计 JSON 报告，例如 `reports/m5air.json`；允许本地隔离调试使用 `reports/latest.json`，但它不能替代目标环境报告。未生成目标环境 report、report 失败、或只跑静态 smoke 都不能算上机测试通过。

### 执行

```bash
python3 test/subsystem/tier/case/tier-<GROUP>-<NNN>/run.py
```

必要的回归验证还包括：

```bash
python3 -m py_compile $(find src test/system/support test/subsystem/tier/case -name "*.py" -not -name '._*')
python3 -m pytest test/unit/tier/tier_runtime/behavior_cases/test_server_jobs.py test/unit/tier/tier_runtime/behavior_cases/test_provider_usage.py -q
```

---

## 九、实现基线与剩余收口

当前实现基线：

- `tier_model.py`、`tier_config.py`、`router_core.py`、`quota_manager.py`、`concurrency.py`、`tier_core.py`、`stats_collector.py` 已形成单一 Tier runtime。
- API、CLI agent通过`src/llm_tier/backends/`封装；MLEXP也通过同目录adapter进入Tier调用链，但服务本体仍是独立Subsystem。对Tier调用方统一由`TierClient.invoke_role()`进入。
- settings、runtime、stats 与 Dashboard 使用同一 Backend identity：`tier:account:model_name`。
- `role_name -> Tier` 是唯一 selector；context Upshift 只改变单次请求的实际 Tier，不创建第二套路由配置。

剩余收口必须以 `test/unit/tier/tier_runtime/behavior_cases/TIER_SUBSYSTEM_TEST_DESIGN.md` 的系统测试为准：

- m5air 上逐 Backend 验证 CLI/API/MLP 的真实可用性，未验证 Backend 保持 disabled。
- 运行并保留全部 175 个 case 的独立报告，失败 case 修复后必须重跑对应 case 与关联回归。
- UI 必须在浏览器通过 m5air LAN 地址验证 API same-origin、状态展示、操作结果与 patch-only 自动刷新。
- push 前生成测试报告；存在未通过项时不得把当前版本声明为系统测试通过。


---

## 附录 A：Backend 凭证配置

settings.json 中新增 `llm_backend_credentials` 段，Backend 初始化时的参数优先级：

```
settings.json → 环境变量 → config.py 默认值
```

```json
{
  "llm_backend_credentials": {
    "xfyun": {
      "api_key": "",
      "base_url": "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2",
      "timeout_seconds": 600
    },
    "volc": {
      "api_key": "",
      "base_url": "https://ark.cn-beijing.volces.com/api/coding/v3",
      "timeout_seconds": 600
    },
    "deepseek": {
      "api_key": "",
      "base_url": "https://api.deepseek.com/v1",
      "timeout_seconds": 300
    },
    "minimax": {
      "api_key_file": "minimax.txt",
      "base_url": "https://api.minimaxi.com/anthropic",
      "timeout_seconds": 600,
      "max_tokens": 4096
    },
    "local": {
      "base_url": "http://127.0.0.1:11434/v1",
      "timeout_seconds": 120
    },
    "codex": {
      "cli_path": "",
      "model_name": "gpt-5.4",
      "sandbox": "danger-full-access",
      "timeout_seconds": 180
    },
    "claude": {
      "cli_path": "",
      "model_name": "",
      "sandbox": "danger-full-access",
      "timeout_seconds": 180
    },
    "debug": {
      "scenario_file": "notes/llm_tier_debug_success.scenario.json",
      "default_content": "DEBUG OK",
      "latency_ms": 0
    }
  }
}
```

api_key 为空时从环境变量读取：`SLINKY_XFYUN_API_KEY`, `SLINKY_VOLC_API_KEY` 等。
MiniMax Token Plan 的 API key 不写入 settings.json；`api_key_file` 指向本地 `minimax.txt`，或通过 `SLINKY_MINIMAX_API_KEY` / `ANTHROPIC_API_KEY` 注入。
cli_path 为空时从 PATH 或默认路径查找。
`debug` backend 不真实调用 LLM，而是读取 `scenario_file` 指定的 JSON 场景文件；场景文件可以声明 `content`、`content_file`、`token_usage`、`latency_ms`，也可以声明 `error_type=backend/quota/exception` 和 `error_message` 来模拟失败。运行时还可以通过请求 metadata 里的 `debug_scenario_file`、`debug_content_file`、`debug_error_type`、`debug_error_message` 临时覆盖默认场景，用于调试 fallback、dashboard、错误面板和 escalation 链路。

---

## 附录 B：project_name 推导

`TierCallRequest.project_name` 由调用方填入。现有代码中 project_name 不在 prompt context 中，从 `workspace_root` 推导：

```python
def _resolve_project_name(workspace_root: str) -> str:
    """从 workspace_root 路径的最后一个目录名推导项目名"""
    return Path(workspace_root).name
```

调用位置：`src/llm_tier/client.py` 的 `invoke_role()` 中构造 `TierCallRequest` 时。
调用方同时从 metadata 中取 `stage_name`、`phase_name`、`task_id`、`task_key`，
这些已由 `_build_role_prompt_metadata` 注入。

metadata 字段映射：

| metadata key | TierCallRequest 字段 | 来源 |
|-------------|---------------------|------|
| `project_name` | `project_name` | workspace_root 推导 |
| `stage_name` | `stage_name` | prompt context |
| `phase_name` | `phase_name` | prompt context |
| `task_id` | `task_id` | prompt context |
| `task_key` | `task_key` | prompt context |

---

## 附录 C：TierCallResult → 旧调用格式转换

旧 `_invoke_single_backend` 返回：
```python
{
    "ok": True,
    "content": str,
    "model_name": str,
    "usage": {"prompt_tokens": N, "completion_tokens": N, "total_tokens": N},
    "raw_response": dict,
    "error": str,       # 空=成功
    "artifact_paths": {},   # 兼容字段；不承载 task-local prompt/response 路径
}
```

转换函数：
```python
def _tier_result_to_proxy_response(result: TierCallResult) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "content": result.content,
        "model_name": result.model_name,
        "usage": result.token_usage,
        "raw_response": result.raw_response,
        "error": result.error_message,
        "artifact_paths": {},
    }
```

说明：

- `artifact_paths` 只保留兼容字段，不再承载 Tier 特有调试信息。
- Tier 特有信息（`backend`, `tier`, `is_fallback`）应通过独立返回字段和 SQL 统计读取，不得再伪装成文件路径信息。

---

## 附录 D：一次性全改的依赖与顺序

不改外部 API，只改内部实现。以下顺序保证每步之间代码可编译、旧功能可用。

### 块 1：新建模块（零依赖）

```
src/llm_tier/tier_model.py        # @dataclass 定义
src/llm_tier/exceptions.py        # 异常类
src/llm_tier/tier_config.py       # 配置加载（依赖 tier_model）
```

**验证**：`python3 -m py_compile src/llm_tier/tier_model.py src/llm_tier/exceptions.py src/llm_tier/tier_config.py`

### 块 2：Backend 接口与实现（依赖块 1 + 现有旧文件）

```
src/llm_tier/backends/__init__.py
src/llm_tier/backends/base.py
src/llm_tier/backends/api_backend.py      # api 公共逻辑
src/llm_tier/backends/agent_backend.py    # agent 公共逻辑
src/llm_tier/backends/xfyun.py            # 封装 model_client.XfyunModelClient
src/llm_tier/backends/volc.py             # 封装 model_client.VolcModelClient
src/llm_tier/backends/deepseek.py         # 新写
src/llm_tier/backends/local.py            # 封装 model_client.LocalModelClient
src/llm_tier/backends/codex.py            # 内联 Codex CLI 调用逻辑
src/llm_tier/backends/claude.py           # 内联 Claude CLI 调用逻辑
```

**验证**：`python3 -m py_compile src/llm_tier/backends/*.py`

### 块 3：路由 + 入口（依赖块 1 + 块 2）

```
src/llm_tier/router_core.py       # LLMRouter, QuotaManager, 并发
src/llm_tier/stats_collector.py   # 统计
src/llm_tier/tier_core.py         # TierCore 入口 + get_tier()
src/llm_tier/__init__.py          # 导出
```

**验证**：`python3 -c "from llm_tier import get_tier, TierCallRequest, TierCallResult"`

### 块 4：切链路（依赖块 3）

```
src/llm_tier/client.py   # TierClient.invoke_role() 统一入口
src/utils/config.py    # 加 get_model_for_role()，改 get_llm_proxy_role_configs
```

**验证**：`python3 -m py_compile src/llm_tier/client.py src/utils/config.py`

### 块 5：部署 settings.json

```
workspaces/<project>/settings.json   # 写入 Tier 配置
```

**验证**：`python3 -c "from llm_tier.tier_config import TierConfig; c=TierConfig(); assert c.is_enabled()"`

### 块 6：删除旧代码

| 删除 | 原因 |
|------|------|
| `src/llm/backend_fallback.py` | `is_quota_or_rate_limit_error` 逻辑已移入 router_core |
| `src/core/llm_proxy.py` | 外部调用统一走 TierClient.invoke_role() |
| `src/core/llm_codex_cli.py` / `src/core/llm_claude_cli.py` | CLI 逻辑内联到 backends/codex.py 和 backends/claude.py |
| 旧 Role selector / 直连 Backend 配置 | 全部从 settings.json 的 `role_tier_map` 与 `llm_tiers` 读取 |

以下保留不动：
- `src/llm/openai_compatible.py` / `model_client.py` 仅作为 Backend 内部协议实现，不得成为 Role 的并行路由入口

以下已删除：
- `src/core/llm_proxy.py` — 外部调用统一走 TierClient.invoke_role()
- `src/core/llm_codex_cli.py` / `src/core/llm_claude_cli.py` — CLI 逻辑内联到 backends/codex.py 和 backends/claude.py

### 块 7：端到端验证

```bash
python3 -m py_compile $(find src -name '*.py' -not -name '._*')
./tools/run.sh --project-name llm_json_interpreter --start unit_testing::fix
grep 'tier.call' workspaces/llm_json_interpreter/meta/*/*/*/task.log.jsonl
sqlite3 workspaces/llm_json_interpreter/meta/llm_tier/llm_stats.sqlite3 '.tables'
```

---

## 附录 E：一次性改完的风险与回退方案

| 风险 | 缓解 |
|------|------|
| 块 1-3 引入编译错误 | 块之间用 `py_compile` 验证 |
| 块 4 切链路后旧行为异常 | settings.json 中 `llm_tier.enabled=false` 即可回退到旧路径 |
| Backend 实现 bug 导致调用失败 | 同 Tier 配多个 Backend，一个挂了自动 fallback |
| 新 Backend（deepseek）不可用 | 不配入 settings.json 就不会被选中 |
| 删除旧配置后需要回退 | 删除前 git commit，回退时 git revert |

---

## 附录 F：HTTP API 摘要

server固定只监听loopback，默认`127.0.0.1:8765`；Client可通过`TIER_SERVER_URL`覆盖为另一loopback HTTP origin。m5air或其它远程测试机上的浏览器只访问统一Dashboard的LAN地址，Dashboard再通过本机`TierClient`连接Tier；禁止将Tier server绑定`0.0.0.0`或直接暴露给浏览器。页面same-origin规则见`docs/30_subsystem_design/legacy_root_migration/65_tier_dashboard_design.md`。

### `GET /health`

返回 Tier server 基本在线状态，例如：

```json
{
  "ok": true,
  "running": true,
  "tier_enabled": true,
  "jobs": {
    "running": 1,
    "done": 12,
    "total": 13
  }
}
```

### `POST /call`

提交一次 role 驱动的异步调用，请求体使用 `TierCallRequest` 字段：

```json
{
  "role_name": "system_testing_author",
  "prompt": "...",
  "project_name": "llm_json_interpreter",
  "stage_name": "system_testing",
  "phase_name": "family",
  "task_id": "system_testing::family::S1.F1",
  "task_key": "S1.F1",
  "temperature": 0.0
}
```

返回：

```json
{
  "ok": true,
  "job_id": "a1b2c3d4e5f6"
}
```

### `POST /escalate`

提交一次跨 Tier 扫描调用。它不依赖 `role_name`，而是显式提供 `tier_priority`：

```json
{
  "prompt": "...",
  "project_name": "llm_json_interpreter",
  "tier_priority": ["Senior", "Junior", "Worker", "Associate"],
  "stage_name": "system_testing",
  "phase_name": "family",
  "task_id": "system_testing::family::S1.F1",
  "task_key": "S1.F1",
  "temperature": 0.0
}
```

### `GET /result/{job_id}`

轮询异步任务结果：

```json
{"ok": true, "status": "running"}
```

或：

```json
{
  "ok": true,
  "status": "done",
  "result": {
    "ok": true,
    "content": "...",
    "backend": "minimax",
    "account": "mnm",
    "model_name": "MiniMax-M2.7",
    "tier": "Worker"
  }
}
```

### `GET /stats`

用于 Dashboard 和调试读取统计。支持按 `project`、`tier`、`backend`、`role`、`limit` 过滤。

### 管理接口

- `POST /reload`
  - 重载配置文件
- `POST /reset`
  - 重置 exhausted 状态；可全局或按 Tier
  - 必须同步清理 quota exhausted、router runtime status、server runtime snapshot 中的 exhausted/unreachable/last_error/failure_count
  - 不得恢复人工 disabled Backend
- `POST /backend/probe`
  - 对单个 Backend 发起 Probe
- `POST /backend/enable`
  - 手工启用 Backend，并按主状态机规则决定是否自动 Probe
- `POST /backend/disable`
  - 手工禁用 Backend
- `POST /backend/weight`
  - 更新 Backend 自身的调度权重
- `POST /account/concurrency`
  - 更新 Account 自身的最大并发数，并立即同步 runtime 并发上限

---

## 附录 G：调试开关与启动参数

### 调试开关

`settings.json` 可包含：

```json
{
  "llm_tier": {
    "debug": {
      "router": false,
      "backend": false,
      "concurrency": false,
      "stats_verbose": false
    }
  }
}
```

字段含义：

- `router`
  - 打印路由决策日志
- `backend`
  - 打印 backend 调用细节
- `concurrency`
  - 打印并发池变化
- `stats_verbose`
  - 每次写统计时额外打印

### 环境变量

- `TIER_SERVER_URL`
  - 指定 Tier server 地址，默认 `http://127.0.0.1:8765`
- `SLINKY_TIER_CONFIG`
  - 指定 `settings.json` 路径

### Server 启动参数

```bash
PYTHONPATH=src python3 -m llm_tier --host 127.0.0.1 --port 8765 --settings workspaces/<project>/settings.json
```

参数：

- `--host`
  - 监听地址，只允许loopback，默认 `127.0.0.1`
- `--port`
  - 监听端口，默认 `8765`
- `--settings`
  - `settings.json` 路径
