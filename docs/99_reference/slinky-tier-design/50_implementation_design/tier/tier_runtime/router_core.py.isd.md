# `src/llm_tier/router_core.py` ISD

Version: v1.8
Last Updated: 2026-09-08 12:18:44
Status: Draft / Source-Verified Baseline

target_file: `src/llm_tier/router_core.py`
target_state: `existing`

所属边界：Tier / Tier Server Module。
上游：`docs/40_module_design/tier/tier_server_module.md`。
接口追踪：provided_interfaces=`TIR-PROC-001`, `TIR-DATA-001`；consumed_interfaces=`MLX-HTTP-001`, `MLX-HTTP-002`, `MLX-HTTP-003`, `MLX-HTTP-004`, `MLX-HTTP-005`, `MLX-HTTP-006`。

## 1. 文件职责

本ISD以当前`src/llm_tier/router_core.py`为行为baseline，目标文件保留其单文件责任；除上游Module Design明确的Approved Delta外，不改变算法、selector、配置路径、重试或fallback。

## 2. 源码结构

- 当前行数：1256
- Imports：`__future__:annotations`, `re`, `time`, `threading`, `datetime:datetime,timezone`, `typing:Any,Callable`, `llm_tier.backends:get_backend_client`, `llm_tier.concurrency:BackendConcurrencyManager`, `llm_tier.exceptions:AllModelsExhaustedError,BackendCallError,QuotaExhaustedError`, `llm_tier.quota_manager:QuotaManager`, `llm_tier.tier_config:TierConfig`, `llm_tier.tier_model:TierCallResult,TierModel,backend_call_model_name,backend_client_name,backend_readable_label`
- Module constants：`DEFAULT_MAX_OUTPUT_TOKENS`, `UPSHIFT_TARGET_BY_TIER`

### 2.1 Classes / Functions / Methods

| Symbol | Line | Signature | Direct calls（最多10个） | Raises |
|---|---:|---|---|---|
| `_safe_path_part` | 36 | `def _safe_path_part(value: str) -> str` | `re.sub`, `normalized.strip`, `str.strip`, `str` | none |
| `_completion_truncation_error` | 47 | `def _completion_truncation_error(*, token_usage: dict[str, Any], max_tokens: int, backend: str, model_name: str) -> str` | `int`, `get` | none |
| `LLMRouter` | 71 | `class LLMRouter` | none | none |
| `LLMRouter.__init__` | 78 | `def __init__(self, tier_config: TierConfig, state_dir: str = '', trace_hook: TraceHook \| None = None) -> None` | `QuotaManager`, `self._build_concurrency`, `self._config.get_breaker_config`, `int`, `threading.Lock`, `breaker_config.get` | none |
| `LLMRouter._trace` | 105 | `def _trace(self, event_type: str, level: str, event: str, fields: dict[str, Any] \| None = None) -> None` | `self._trace_hook`, `dict` | none |
| `LLMRouter._build_concurrency` | 125 | `def _build_concurrency(self) -> BackendConcurrencyManager` | `self._config.get_accounts`, `BackendConcurrencyManager`, `self._config.get_account_concurrency` | none |
| `LLMRouter.call` | 137 | `def call(self, role_name: str, prompt: str, temperature: float = 0.0, timeout_seconds: int \| None = None, metadata: dict[str, str] \| None = None) -> tuple[TierCallResult, dict[str, Any]]` | `dict`, `self._trace`, `self._config.get_tier_for_role`, `self._resolve_upshift_tier`, `self._config.get_tier_models`, `set`, `range`, `self._selection_debug_summary`, `self._selection_has_transient_busy`, `str` | none |
| `LLMRouter._select_and_acquire_backend` | 649 | `def _select_and_acquire_backend(self, models: list[TierModel], failed_backend_keys: set[str] \| None = None, tier_name: str = '', busy_backend_keys: set[str] \| None = None) -> tuple[TierModel \| None, str, str, float]` | `self._select_and_acquire_weighted_backend`, `self.backend_key`, `str.strip`, `self.is_backend_enabled`, `self.backend_routable`, `self._quota.is_exhausted`, `str`, `backend_identity` | none |
| `LLMRouter._backend_exclusion_reason` | 688 | `def _backend_exclusion_reason(self, model: TierModel, *, tier_name: str = '', failed_backend_keys: set[str] \| None = None, busy_backend_keys: set[str] \| None = None) -> str` | `self.backend_key`, `self.backend_runtime_status`, `self._quota.is_exhausted`, `str.strip`, `self.is_backend_enabled`, `self.backend_routable`, `str` | none |
| `LLMRouter._selection_debug_summary` | 718 | `def _selection_debug_summary(self, models: list[TierModel], *, failed_backend_keys: set[str] \| None = None, busy_backend_keys: set[str] \| None = None, tier_name: str = '') -> str` | `join`, `backend_readable_label`, `self._backend_exclusion_reason`, `parts.append` | none |
| `LLMRouter._selection_has_transient_busy` | 745 | `def _selection_has_transient_busy(self, selection_debug: str) -> bool` | `str.strip.lower`, `str.strip`, `str` | none |
| `LLMRouter.backend_key` | 763 | `def backend_key(self, backend: str, model_name: str, *, tier_name: str = '', account: str = '') -> str` | `str.strip`, `str` | none |
| `LLMRouter.is_backend_enabled` | 774 | `def is_backend_enabled(self, backend: str, model_name: str, *, tier_name: str = '', account: str = '') -> bool` | `self.backend_key`, `bool`, `self._admin_state_by_backend.get` | none |
| `LLMRouter.set_backend_enabled` | 785 | `def set_backend_enabled(self, backend: str, model_name: str, enabled: bool, *, tier_name: str = '', account: str = '') -> None` | `self.backend_key`, `bool`, `self._failure_count_by_backend.pop` | none |
| `LLMRouter.backend_runtime_status` | 798 | `def backend_runtime_status(self, backend: str, model_name: str, *, tier_name: str = '', account: str = '') -> str` | `self.backend_key`, `str`, `self._runtime_status_by_backend.get` | none |
| `LLMRouter.set_backend_runtime_status` | 809 | `def set_backend_runtime_status(self, backend: str, model_name: str, status: str, *, tier_name: str = '', account: str = '') -> None` | `self.backend_key`, `str` | none |
| `LLMRouter.reset_runtime_statuses` | 820 | `def reset_runtime_statuses(self, tier_name: str = '') -> list[str]` | `str.strip`, `str`, `self.backend_key`, `self._runtime_error_by_backend.pop`, `self._failure_count_by_backend.pop`, `reset_keys.append`, `self._config.get_tier_models`, `self._config._config.get`, `self._admin_state_by_backend.get` | none |
| `LLMRouter.backend_routable` | 852 | `def backend_routable(self, backend: str, model_name: str, *, tier_name: str = '', account: str = '') -> bool` | `self.backend_runtime_status` | none |
| `LLMRouter.backend_runtime_meta` | 862 | `def backend_runtime_meta(self, backend: str, model_name: str, *, tier_name: str = '', account: str = '') -> dict[str, Any]` | `self.backend_key`, `int`, `dict`, `self._failure_count_by_backend.get`, `self._runtime_error_by_backend.get` | none |
| `LLMRouter._record_backend_success` | 876 | `def _record_backend_success(self, backend: str, model_name: str, *, tier_name: str = '', account: str = '') -> None` | `self.backend_key`, `self._failure_count_by_backend.pop`, `self._runtime_error_by_backend.pop` | none |
| `LLMRouter._record_backend_error` | 889 | `def _record_backend_error(self, backend: str, model_name: str, error_message: str, *, tier_name: str = '', account: str = '', failure_type: str) -> None` | `self.backend_key`, `str`, `time.strftime`, `time.gmtime` | none |
| `LLMRouter._record_unhealthy_failure` | 913 | `def _record_unhealthy_failure(self, backend: str, model_name: str, error_message: str, *, tier_name: str = '', account: str = '', source: str = 'call') -> None` | `self.backend_key`, `str.strip.lower`, `int`, `str`, `time.strftime`, `str.strip`, `time.gmtime`, `self._failure_count_by_backend.get` | none |
| `LLMRouter._select_and_acquire_weighted_backend` | 946 | `def _select_and_acquire_weighted_backend(self, tier_name: str, models: list[TierModel], *, busy_backend_keys: set[str] \| None = None) -> tuple[TierModel \| None, str, str, float]` | `min`, `weighted_models.extend`, `int`, `range`, `len`, `self.backend_key`, `str.strip`, `self._concurrency.acquire`, `retry_after_candidates.append`, `self._trace` | none |
| `LLMRouter._build_stats_event` | 994 | `def _build_stats_event(self, tier_name: str, backend: str, account: str, backend_type: str, model: str, ok: bool, latency_ms: float, token_usage: dict[str, int], is_fallback: bool, fallback_count: int, selection_debug: str = '') -> dict[str, Any]` | `datetime.now.strftime`, `token_usage.get`, `str`, `datetime.now` | none |
| `LLMRouter._resolve_upshift_tier` | 1038 | `def _resolve_upshift_tier(self, *, tier_name: str, prompt: str, trace_base: dict[str, Any]) -> str` | `str.strip`, `self._estimate_prompt_tokens`, `self._config.get_tier_models`, `self._tier_prompt_capacity_tokens`, `self._trace`, `str` | none |
| `LLMRouter._tier_prompt_capacity_tokens` | 1096 | `def _tier_prompt_capacity_tokens(self, models: list[TierModel]) -> int` | `max`, `int`, `capacities.append` | none |
| `LLMRouter.upshift_count` | 1118 | `def upshift_count(self) -> int` | `int` | none |
| `LLMRouter._context_limit_error` | 1128 | `def _context_limit_error(self, model: TierModel, prompt: str, credentials: dict[str, Any]) -> dict[str, Any] \| None` | `self._config.get_backend_capabilities`, `int`, `self._estimate_prompt_tokens`, `max`, `capabilities.get`, `credentials.get` | none |
| `LLMRouter._estimated_prompt_token_usage` | 1172 | `def _estimated_prompt_token_usage(self, prompt: str) -> dict[str, int]` | `self._estimate_prompt_tokens` | none |
| `LLMRouter._client_request_error_message` | 1186 | `def _client_request_error_message(self, error_message: str) -> str` | `str.strip`, `normalized.lower`, `any`, `str` | none |
| `LLMRouter._max_tokens_for_model` | 1217 | `def _max_tokens_for_model(self, model: TierModel, credentials: dict[str, Any]) -> int` | `self._config.get_backend_capabilities`, `int`, `capabilities.get`, `credentials.get` | none |
| `LLMRouter._estimate_prompt_tokens` | 1236 | `def _estimate_prompt_tokens(self, prompt: str) -> int` | `str`, `max`, `len` | none |
| `LLMRouter._get_backend_credentials` | 1242 | `def _get_backend_credentials(self, backend_name: str, provider: str = '', model_name: str = '', model_key: str = '', account: str = '') -> dict[str, Any]` | `self._config.get_backend_credentials` | none |

### 2.2 逐Callable Contract

第2.1节每个callable的参数名、顺序、positional/keyword规则、default和annotation均为迁移Contract；不得增加吞错kwargs、隐式类型转换或兼容alias。返回值保持当前源码annotation及所有分支的可观察类型；表中Raises和源码显式传播的dependency exception必须保留，不能转换为空成功。跨文件调用只能使用所属Module登记的public symbol，underscore symbol只允许本文件内部使用。各callable的IO、state mutation、network/process、logging和并发side effect按第4节及其Direct calls执行，Test Design必须为每个public callable至少建立正常、边界、错误和side-effect evidence。

## 3. 输入、输出与不变量

- 输入类型、默认值和返回annotation以第2节源码签名为准；无annotation的现有参数不得在实现阶段擅自收窄。
- `None`、空集合和异常语义保持当前调用方可观察行为，除非上游Approved Delta明确要求改变。
- public symbol名称和调用方向必须保持唯一；迁移不得保留旧路径re-export或兼容wrapper。
- 本文件不得获得所属Module之外的authority，也不得从日志、目录或display text推断业务真值。

## 4. State、IO与Side Effects

- Logging/Stats
- Concurrency
- 非幂等写操作必须由所属Module现有single-writer/lock/attempt机制约束；unknown outcome不得盲目重试。
- timeout、retry、redaction和日志字段沿用当前owner Contract，不在本文件建立第二套policy。
- Backend连续unhealthy failure达到阈值后，唯一runtime状态为`unreachable`；该状态属于明确不可路由，不得归类为临时`all_backends_busy`。
- MLEXP 已接受并执行的 job 返回 `failed/blocked/error` 业务终态时，Router 必须沿现有 client-request error 分支返回 typed failure，不得把该结果计入 MLEXP backend unhealthy breaker；连接、timeout、malformed protocol 与 health/readiness 失败仍按 backend failure 处理。
- `LLMRouter.call()`一旦选择并调用某个 Backend，quota、`BackendCallError`和unexpected exception分支写入的`last_failure`必须保存该次选择的`backend/model_name/backend_type/account`、从`start_ts`计算的`latency_ms`和`_estimated_prompt_token_usage(prompt)`；最终`TierCallResult`与`_build_stats_event()`必须复用这些字段，禁止以空identity结束失败调用。

## 5. Error、Recovery与禁止路径

- 保留第2节列出的typed exception和调用方错误映射；不得把malformed、missing、timeout或runner error转换为空成功。
- 不自动跨Stage rollback，不新增config、selector、routing、fallback或兼容分支。
- 迁移失败必须回滚整个文件/import变更，不允许新旧文件同时成为authority。

## 6. Tests

- 现有相关测试：`test/unit/stage_process/framework/behavior_cases/test_execution_identity.py`, `test/unit/stage_process/stages/system_testing_stage/behavior_cases/test_case_data_raw_text_validation.py`, `test/unit/tier/tier_runtime/behavior_cases/test_client_replay.py`, `test/unit/tier/tier_runtime/behavior_cases/test_provider_usage.py`, `test/unit/tier/tier_runtime/behavior_cases/test_mlexp_backend.py`, `test/unit/tier/tier_runtime/behavior_cases/test_server_jobs.py`, `test/unit/memory/retrieval_context/behavior_cases/test_judge_validator.py`, `test/unit/webui/dashboard/behavior_cases/test_dashboard_fast_paths.py`, `test/unit/common/stats/behavior_cases/test_llm_stats.py`, `test/subsystem/tier/case/tier-BASIS-001/run.py`, `test/subsystem/tier/case/tier-ENV-001/run.py`, `test/subsystem/tier/case/tier-CONFIG-001/run.py`；其余由Module测试索引覆盖。
- Contract Test覆盖public signature、authority、错误传播和禁止fallback。
- MLEXP terminal business failure 测试必须同时断言 `TierCallResult.ok=false`、错误仍可见、breaker count 不增长且 backend 保持 `running`。
- Router terminal Backend failure 测试必须断言失败`TierCallResult`和raw stats event的`tier/account/backend/model`与实际选择一致，保证项目和账号维度的`fail_count`可聚合。
- 迁移文件增加import graph检查，证明旧source path无production/test caller。

## 7. Current Difference

文件已位于目标路径。本ISD不批准额外行为变化；已知缺陷只能按Module Design和bug记录另行进入Test Design。
