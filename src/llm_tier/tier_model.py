from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# 用途：
# - 描述一个 provider account，作为额度、凭证、账号级并发和调用间隔的配置主体
# 输入：
# - account_id/provider/max_concurrent_requests/min_request_interval_ms/requests_per_minute/quota/credentials
# 输出：
# - Router、Dashboard 和 usage 查询可共享的账号对象
@dataclass
class TierAccount:
    account_id: str
    provider: str
    max_concurrent_requests: int = 1
    min_request_interval_ms: int = 0
    requests_per_minute: int = 0
    quota: dict[str, Any] = field(default_factory=dict)
    credentials: dict[str, Any] = field(default_factory=dict)


# 用途：
# - 描述一个完整 backend 路由入口，引用 account 并保存 provider、agent、模型、权重和运行能力配置
# 输入：
# - backend/account/usage_account/provider/model/context/enabled/weight 等配置字段
# 输出：
# - Router、Dashboard 和执行阶段可直接消费的 backend model 对象
@dataclass
class TierModel:
    backend: str              # 用户自定义的 backend 名，如 "xfyun-primary"
    provider: str             # LLM 能力提供商，如 "minimax"、"volc"、"xfyun"
    model_name: str           # 真实模型名，用于显示/统计，如 "Qwen3.5-397B-A17B"
    account: str = ""         # 账号配置引用，指向 llm_accounts 中的 account id
    usage_account: str = ""   # 额度/usage 查询账号；为空时等于 account
    model_key: str = ""       # API 调用用的 model ID，为空时等于 model_name
    backend_type: str = "API"
    weight: int = 1
    priority: int = 0
    enabled: bool = True
    exhausted: bool = False
    timeout_seconds: int = 600
    max_context_tokens: int = 0
    reserved_completion_tokens: int = 0
    max_output_tokens: int = 0
    quota: dict[str, Any] = field(default_factory=dict)
    credentials: dict[str, Any] = field(default_factory=dict)


# 用途：
# - 解析 TierModel 应实例化的 backend client 名称
# 输入：
# - model: Tier backend 配置对象
# 输出：
# - backend client registry key；CLI/MLP 走 backend identity 中的 agent，API 走 provider client
def backend_client_name(model: TierModel) -> str:
    backend_type = str(model.backend_type or "").strip().upper()
    backend_name = str(model.backend or "").strip()
    agent_name = backend_agent_name(model)
    if backend_type in {"CLI", "MLP"} and agent_name:
        return agent_name
    return str(model.provider or backend_name).strip()


# 用途：
# - 从 backend identity 中解析 agent 名称
# 输入：
# - model: Tier backend 配置对象；CLI/MLP backend 可为 `agent:account/model`
# 输出：
# - agent 名称；非 agent identity 时返回空字符串
def backend_agent_name(model: TierModel) -> str:
    backend_name = str(model.backend or "").strip()
    if ":" in backend_name:
        agent, _selector = backend_name.split(":", 1)
        return agent.strip()
    return ""


# 用途：
# - 从 backend identity 中解析 account/model selector
# 输入：
# - model: Tier backend 配置对象；CLI/MLP 可为 `agent:account/model`，API 可为 `account/model`
# 输出：
# - `account/model` selector；backend 不含 selector 时返回空字符串
def backend_identity_selector(model: TierModel) -> str:
    backend_name = str(model.backend or "").strip()
    if ":" in backend_name:
        _agent, selector = backend_name.split(":", 1)
        return selector.strip()
    if "/" in backend_name:
        return backend_name
    return ""


# 用途：
# - 解析传给 backend client 的模型选择字符串
# 输入：
# - model: Tier backend 配置对象
# 输出：
# - API backend 返回 model_key/model_name；CLI/MLP agent 返回 account/model selector
def backend_call_model_name(model: TierModel) -> str:
    identity_selector = backend_identity_selector(model)
    if str(model.backend_type or "").strip().upper() in {"CLI", "MLP"} and identity_selector:
        return identity_selector
    selector = str(model.model_key or model.model_name or "").strip()
    if backend_client_name(model) == "mlexp" and selector and "/" not in selector:
        account = str(model.account or model.usage_account or "").strip()
        if account:
            return f"{account}/{selector}"
    return selector


# 用途：
# - 生成用户可读的 backend label，避免把内部 `tier:account:model` 状态 key 暴露到诊断信息
# 输入：
# - model: Tier backend 配置对象
# 输出：
# - API 返回 `account/model`；CLI/MLP 返回 `agent:account/model`
def backend_readable_label(model: TierModel) -> str:
    backend_type = str(model.backend_type or "").strip().upper()
    backend_name = str(model.backend or "").strip()
    account = str(model.account or model.usage_account or "").strip()
    model_name = str(model.model_name or model.model_key or "").strip()
    if account and model_name.startswith(f"{account}/"):
        model_name = model_name[len(account) + 1:]

    if backend_type in {"CLI", "MLP"}:
        identity_selector = backend_identity_selector(model)
        agent = backend_agent_name(model) or backend_name
        if identity_selector and agent:
            return f"{agent}:{identity_selector}"
        if agent and account and model_name:
            return f"{agent}:{account}/{model_name}"
    if account and model_name:
        return f"{account}/{model_name}"
    return backend_name or model_name


# 用途：
# - 描述一次 llm_tier 调用请求，支持 HTTP content mode 与 Task-local file mode
# 输入：
# - role/prompt/project/stage/phase/task/metadata 以及可选 prompt/response 文件路径
# 输出：
# - 可序列化给 client/server/router 的调用请求对象
@dataclass
class TierCallRequest:
    role_name: str
    prompt: str
    project_name: str
    stage_name: str = ""
    phase_name: str = ""
    task_id: str = ""
    task_key: str = ""
    temperature: float = 0.0
    timeout_seconds: int | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    prompt_path: str = ""
    response_path: str = ""
    raw_response_path: str = ""
    error_response_path: str = ""


# Purpose: Carry one completed Tier call result with authoritative Backend identity and usage.
# Inputs: Outcome, content, tier/account/backend/model identity, latency, usage, artifacts, and error fields.
# Outputs: Serializable result shared by Router, HTTP Server, Client, stats, and Stage consumers.
@dataclass
class TierCallResult:
    ok: bool
    content: str
    backend: str
    model_name: str
    backend_type: str
    tier: str
    tier_priority: int
    latency_ms: float
    token_usage: dict[str, int]
    account: str = ""
    is_fallback: bool = False
    fallback_count: int = 0
    raw_response: dict[str, Any] = field(default_factory=dict)
    artifact_paths: dict[str, str] = field(default_factory=dict)
    error_code: int = 0
    error_message: str = ""


# 用途：
# - 描述 llm_tier runtime stats 查询条件，供 /stats 和 dashboard 按层级读取统计
# 输入：
# - project/stage/phase/task/tier/backend/role/time/group/limit: 可选过滤字段
# 输出：
# - StatsCollector 可消费的查询对象
@dataclass
class TierStatsQuery:
    project_name: str = ""
    stage_name: str = ""
    phase_name: str = ""
    task_id: str = ""
    task_id_prefix: str = ""
    task_key: str = ""
    tier: str = ""
    backend: str = ""
    role_name: str = ""
    time_range_hours: int = 0
    started_at_epoch: float = 0.0
    started_at_text: str = ""
    task_started_at_epochs: dict[str, float] = field(default_factory=dict)
    task_started_at_texts: dict[str, str] = field(default_factory=dict)
    group_by: str = ""
    include_events: bool = True
    limit: int = 100


@dataclass
class TierStatsRow:
    project_name: str
    tier: str
    backend: str
    backend_type: str
    model_name: str
    role_name: str
    account: str = ""
    calls: int = 0
    success_count: int = 0
    fail_count: int = 0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    prompt_tokens_avg: float = 0.0
    prompt_tokens_p50: float = 0.0
    prompt_tokens_p70: float = 0.0
    prompt_tokens_p95: float = 0.0
    prompt_tokens_p99: float = 0.0
    completion_tokens_avg: float = 0.0
    completion_tokens_p50: float = 0.0
    completion_tokens_p70: float = 0.0
    completion_tokens_p95: float = 0.0
    completion_tokens_p99: float = 0.0
    prompt_chars: int = 0
    prompt_chars_avg: float = 0.0
    prompt_chars_p50: float = 0.0
    prompt_chars_p70: float = 0.0
    prompt_chars_p95: float = 0.0
    prompt_chars_p99: float = 0.0
    completion_chars: int = 0
    completion_chars_avg: float = 0.0
    completion_chars_p50: float = 0.0
    completion_chars_p70: float = 0.0
    completion_chars_p95: float = 0.0
    completion_chars_p99: float = 0.0
    latency_avg_ms: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p70_ms: float = 0.0
    latency_p90_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    fallback_count: int = 0
    exhausted_count: int = 0
