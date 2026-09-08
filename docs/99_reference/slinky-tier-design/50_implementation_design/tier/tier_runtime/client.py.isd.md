# `src/llm_tier/client.py` ISD

Version: v1.8
Last Updated: 2026-09-08 12:18:44
Status: Draft / Source-Verified Baseline + Approved Delta

target_file: `src/llm_tier/client.py`
target_state: `existing`

所属边界：Tier / Tier Client Module。
上游：`docs/40_module_design/tier/tier_client_module.md`。
接口追踪：provided_interfaces=`TIR-HTTP-001`；consumed_interfaces=`TIR-HTTP-002`。

## 1. 文件职责

本ISD以当前`src/llm_tier/client.py`为行为baseline，目标文件保留其单文件责任；除上游Module Design明确的Approved Delta外，不改变算法、selector、配置路径、重试或fallback。

## 2. 源码结构

- 当前行数：1205
- Imports：`__future__:annotations`, `json`, `os`, `time`, `urllib.error`, `urllib.parse`, `urllib.request`, `uuid`, `datetime:UTC,datetime`, `pathlib:Path`, `typing:Any`, `core.execution_identity:resolve_execution_identity_for_role`, `llm_tier.tier_model:TierCallRequest,TierCallResult`, `utils.response_parser:ParseError,ResponseParser`
- Module constants：`DEFAULT_SERVER_URL`, `POLL_INTERVAL_SECONDS`, `POLL_TIMEOUT_SECONDS`, `POLL_TIMEOUT_BUFFER_SECONDS`, `DEFAULT_BACKEND_TIMEOUT_SECONDS`, `CONNECT_TIMEOUT_SECONDS`, `BUSY_RETRY_INTERVAL_SECONDS`, `BUSY_MAX_RETRY_INTERVAL_SECONDS`, `TRACE_LEVELS`, `DEFAULT_TRACE_STATE_PATH`, `DEFAULT_TRACE_PATH`, `REPLAY_RESPONSE_PATH_ENV`, `REPLAY_MAP_PATH_ENV`, `REPLAY_ROLE_ENV`, `REPLAY_PROMPT_NAME_ENV`, `REPLAY_TASK_ID_ENV`, `_RESPONSE_PARSER`

### 2.1 Classes / Functions / Methods

| Symbol | Line | Signature | Direct calls（最多10个） | Raises |
|---|---:|---|---|---|
| `TierClient` | 50 | `class TierClient` | none | none |
| `TierClient.__init__` | 57 | `def __init__(self, server_url: str = '') -> None` | `rstrip`, `_env_float`, `os.environ.get.strip`, `os.environ.get` | none |
| `TierClient.invoke_role` | 77 | `def invoke_role(self, payload: dict[str, Any]) -> dict[str, Any]` | `str.strip`, `dict`, `resolve_execution_identity_for_role`, `self._maybe_replay_role_response`, `TierCallRequest`, `self.call`, `str.strip.lower`, `_attach_parsed_json_response`, `str`, `payload.get` | none |
| `TierClient._maybe_replay_role_response` | 148 | `def _maybe_replay_role_response(self, *, payload: dict[str, Any], metadata: dict[str, Any], role_name: str) -> dict[str, Any] \| None` | `_resolve_replay_source_path`, `replay_source.read_text`, `_write_replay_response_file`, `_write_replay_raw_response_file`, `str.strip`, `str`, `len`, `metadata.get`, `payload.get` | none |
| `TierClient.is_reachable` | 204 | `def is_reachable(self, timeout: float = CONNECT_TIMEOUT_SECONDS) -> bool` | `self._http_get` | none |
| `TierClient.get_health` | 217 | `def get_health(self) -> dict[str, Any]` | `self._http_get` | none |
| `TierClient.call` | 230 | `def call(self, req: TierCallRequest) -> TierCallResult` | `self._call_with_busy_retry`, `_request_dict` | none |
| `TierClient.call_async` | 242 | `def call_async(self, req: TierCallRequest) -> str` | `_request_dict`, `self._http_post`, `str`, `resp.get` | none |
| `TierClient.get_result` | 253 | `def get_result(self, job_id: str) -> TierCallResult \| None` | `resp.get`, `_result_from_dict`, `self._http_get` | none |
| `TierClient.escalate` | 273 | `def escalate(self, req: TierEscalationRequest) -> TierCallResult` | `self._call_with_busy_retry`, `_escalation_request_dict` | none |
| `TierClient.escalate_async` | 285 | `def escalate_async(self, req: TierEscalationRequest) -> str` | `_escalation_request_dict`, `self._http_post`, `str`, `resp.get` | none |
| `TierClient.get_stats` | 300 | `def get_stats(self, project: str = '', *, stage: str = '', phase: str = '', task_id: str = '', task_key: str = '', tier: str = '', backend: str = '', role: str = '') -> dict[str, Any]` | `urllib.parse.urlencode`, `self._http_get`, `params.items` | none |
| `TierClient.reset_exhausted` | 326 | `def reset_exhausted(self, tier_name: str = '') -> dict[str, Any]` | `self._http_post` | none |
| `TierClient.reload_config` | 329 | `def reload_config(self) -> dict[str, Any]` | `self._http_post` | none |
| `TierClient.get_runtime` | 338 | `def get_runtime(self) -> dict[str, Any]` | `self._http_get` | none |
| `TierClient.probe_backend` | 347 | `def probe_backend(self, *, tier_name: str, account: str, backend: str, model_name: str) -> dict[str, Any]` | `self._http_post`, `str.strip`, `str` | none |
| `TierClient.get_backend_status` | 364 | `def get_backend_status(self, *, tier_name: str, account: str, backend: str, model_name: str) -> dict[str, Any]` | `self.get_runtime`, `list`, `isinstance`, `runtime.get`, `tiers.get`, `dict`, `str.strip`, `str`, `row.get` | none |
| `TierClient.wait_backend_probe_status` | 387 | `def wait_backend_probe_status(self, *, tier_name: str, account: str, backend: str, model_name: str, expected_status: str = 'running', timeout_seconds: int = 600, poll_interval_seconds: float = 2.0) -> dict[str, Any]` | `time.time`, `self.get_backend_status`, `str.strip.lower`, `time.sleep`, `RuntimeError`, `int`, `float`, `str.strip`, `str`, `status_row.get` | `RuntimeError` |
| `TierClient._call_with_busy_retry` | 427 | `def _call_with_busy_retry(self, *, submit_path: str, request_data: dict[str, Any]) -> TierCallResult` | `time.time`, `self._submit_and_wait`, `time.sleep`, `self._is_busy_result`, `self._busy_retry_delay_seconds` | none |
| `TierClient._submit_and_wait` | 458 | `def _submit_and_wait(self, *, submit_path: str, request_data: dict[str, Any]) -> TierCallResult` | `dict`, `time.time`, `self._trace`, `self._http_post`, `str.strip`, `self._poll_result`, `isinstance`, `str`, `TierCallResult`, `request_data.get` | none |
| `TierClient._is_busy_result` | 513 | `def _is_busy_result(self, result: TierCallResult) -> bool` | `str.strip.lower`, `error_text.startswith`, `str.strip`, `str` | none |
| `TierClient._busy_retry_delay_seconds` | 525 | `def _busy_retry_delay_seconds(self, result: TierCallResult, *, elapsed_seconds: float = 0.0, retry_count: int = 0) -> float` | `_busy_retry_schedule_seconds`, `isinstance`, `float`, `min`, `max`, `result.raw_response.get` | none |
| `TierClient._poll_result` | 552 | `def _poll_result(self, job_id: str, *, timeout_seconds: float, request_data: dict[str, Any] \| None = None) -> TierCallResult` | `time.time`, `_request_trace_fields`, `resp.get`, `time.sleep`, `self._trace`, `self._http_get`, `_result_from_dict`, `_busy_retry_schedule_seconds`, `str` | none |
| `TierClient._client_trace_state` | 634 | `def _client_trace_state(self) -> dict[str, Any]` | `Path`, `state_path.exists`, `json.loads`, `isinstance`, `dict`, `state_path.read_text` | none |
| `TierClient._trace` | 650 | `def _trace(self, event_type: str, level: str, event: str, fields: dict[str, Any] \| None = None) -> None` | `self._client_trace_state`, `str.strip.lower`, `_normalize_trace_types`, `bool`, `TRACE_LEVELS.get`, `state.get`, `datetime.now.strftime`, `str`, `dict`, `Path` | none |
| `TierClient._http_get` | 685 | `def _http_get(self, path: str, timeout: float = CONNECT_TIMEOUT_SECONDS) -> dict[str, Any]` | `urllib.request.Request`, `urllib.request.urlopen`, `json.loads`, `resp.read.decode`, `resp.read` | none |
| `TierClient._http_post` | 692 | `def _http_post(self, path: str, data: dict[str, Any], timeout: float = POLL_TIMEOUT_SECONDS) -> dict[str, Any]` | `json.dumps.encode`, `urllib.request.Request`, `req.add_header`, `urllib.request.urlopen`, `json.loads`, `json.dumps`, `resp.read.decode`, `resp.read` | none |
| `TierEscalationRequest` | 712 | `class TierEscalationRequest` | none | none |
| `TierEscalationRequest.__init__` | 713 | `def __init__(self, prompt: str, project_name: str, tier_priority: list[str] \| None = None, stage_name: str = '', phase_name: str = '', task_id: str = '', task_key: str = '', temperature: float = 0.1) -> None` | none | none |
| `_request_dict` | 738 | `def _request_dict(req: TierCallRequest) -> dict[str, Any]` | `str.strip`, `_resolve_error_response_path`, `dict`, `str` | none |
| `_resolve_error_response_path` | 774 | `def _resolve_error_response_path(*, response_path: str, requested_path: str = '') -> str` | `str.strip`, `Path`, `str`, `path.with_suffix` | none |
| `_resolve_replay_source_path` | 793 | `def _resolve_replay_source_path(*, payload: dict[str, Any], metadata: dict[str, Any], role_name: str) -> Path \| None` | `_matching_replay_map_entry`, `str.strip`, `_resolve_existing_replay_path`, `_replay_env_filters_match`, `str`, `os.environ.get` | none |
| `_matching_replay_map_entry` | 816 | `def _matching_replay_map_entry(*, payload: dict[str, Any], metadata: dict[str, Any], role_name: str) -> str` | `str.strip`, `_resolve_existing_replay_path`, `isinstance`, `json.loads`, `raw_map.get`, `str`, `resolved_map_path.read_text`, `_replay_entry_matches`, `entries.items`, `os.environ.get` | none |
| `_replay_entry_matches` | 864 | `def _replay_entry_matches(*, entry: dict[str, Any], payload: dict[str, Any], metadata: dict[str, Any], role_name: str) -> bool` | `str.strip`, `checks.items`, `str`, `entry.get`, `metadata.get`, `payload.get` | none |
| `_replay_env_filters_match` | 905 | `def _replay_env_filters_match(*, payload: dict[str, Any], metadata: dict[str, Any], role_name: str) -> bool` | `filters.items`, `str.strip`, `str`, `metadata.get`, `payload.get`, `os.environ.get` | none |
| `_resolve_existing_replay_path` | 930 | `def _resolve_existing_replay_path(raw_path: str, metadata: dict[str, Any]) -> Path \| None` | `str.strip`, `Path.expanduser`, `candidate.is_absolute`, `candidate.resolve`, `str`, `Path`, `Path.cwd`, `resolved.exists`, `resolved.is_file`, `metadata.get` | none |
| `_write_replay_response_file` | 954 | `def _write_replay_response_file(*, requested_path: str, content: str, metadata: dict[str, Any]) -> str` | `_resolve_output_path`, `target.parent.mkdir`, `target.write_text`, `str` | none |
| `_write_replay_raw_response_file` | 974 | `def _write_replay_raw_response_file(*, requested_path: str, replay_source: Path, content: str, metadata: dict[str, Any], role_name: str, prompt_name: str) -> str` | `_resolve_output_path`, `target.parent.mkdir`, `target.write_text`, `str`, `str.strip`, `len`, `json.dumps`, `metadata.get` | none |
| `_resolve_output_path` | 1007 | `def _resolve_output_path(requested_path: str, metadata: dict[str, Any]) -> Path \| None` | `str.strip`, `Path.expanduser`, `target.is_absolute`, `Path.cwd`, `str`, `Path`, `metadata.get` | none |
| `_normalize_trace_types` | 1025 | `def _normalize_trace_types(raw_types: Any) -> set[str]` | `isinstance`, `raw_types.split`, `str.strip.lower`, `list`, `str.strip`, `str` | none |
| `_request_trace_fields` | 1041 | `def _request_trace_fields(request_data: dict[str, Any]) -> dict[str, Any]` | `str`, `isinstance`, `request_data.get`, `len`, `metadata.get` | none |
| `_poll_timeout_for_request` | 1066 | `def _poll_timeout_for_request(request_data: dict[str, Any]) -> float` | `max`, `isinstance`, `request_data.get`, `metadata.get`, `float` | none |
| `_busy_retry_schedule_seconds` | 1082 | `def _busy_retry_schedule_seconds(*, elapsed_seconds: float, retry_count: int, initial_seconds: float) -> float` | `int`, `min`, `max`, `float` | none |
| `_escalation_request_dict` | 1105 | `def _escalation_request_dict(req: TierEscalationRequest) -> dict[str, Any]` | none | none |
| `_result_from_dict` | 1118 | `def _result_from_dict(r: dict[str, Any]) -> TierCallResult` | `TierCallResult`, `bool`, `str`, `int`, `float`, `dict`, `r.get`, `isinstance` | none |
| `_attach_parsed_json_response` | 1144 | `def _attach_parsed_json_response(response_payload: dict[str, Any]) -> None` | `_tier_response_text`, `bool`, `_RESPONSE_PARSER.parse_json`, `isinstance`, `parsed.get`, `nested_result.strip.startswith`, `response_payload.get`, `nested_result.strip` | none |
| `_tier_response_text` | 1174 | `def _tier_response_text(response_payload: dict[str, Any]) -> str` | `str`, `response_payload.get`, `str.strip`, `isinstance`, `Path.read_text`, `Path`, `artifact_paths.get` | none |
| `_env_float` | 1197 | `def _env_float(env_name: str, default: float) -> float` | `str.strip`, `float`, `str`, `os.environ.get` | none |

### 2.2 逐Callable Contract

第2.1节每个callable的参数名、顺序、positional/keyword规则、default和annotation均为迁移Contract；不得增加吞错kwargs、隐式类型转换或兼容alias。返回值保持当前源码annotation及所有分支的可观察类型；表中Raises和源码显式传播的dependency exception必须保留，不能转换为空成功。跨文件调用只能使用所属Module登记的public symbol，underscore symbol只允许本文件内部使用。各callable的IO、state mutation、network/process、logging和并发side effect按第4节及其Direct calls执行，Test Design必须为每个public callable至少建立正常、边界、错误和side-effect evidence。

## 3. 输入、输出与不变量

- 输入类型、默认值和返回annotation以第2节源码签名为准；无annotation的现有参数不得在实现阶段擅自收窄。
- `None`、空集合和异常语义保持当前调用方可观察行为，除非上游Approved Delta明确要求改变。
- public symbol名称和调用方向必须保持唯一；迁移不得保留旧路径re-export或兼容wrapper。
- 本文件不得获得所属Module之外的authority，也不得从日志、目录或display text推断业务真值。

## 4. State、IO与Side Effects

- Workspace/File IO
- JSON/SQLite state
- Network/HTTP
- LLM/Tier
- Logging/Stats
- 非幂等写操作必须由所属Module现有single-writer/lock/attempt机制约束；unknown outcome不得盲目重试。
- timeout、retry、redaction和日志字段沿用当前owner Contract，不在本文件建立第二套policy。

## 5. Error、Recovery与禁止路径

- 保留第2节列出的typed exception和调用方错误映射；不得把malformed、missing、timeout或runner error转换为空成功。
- 不自动跨Stage rollback，不新增config、selector、routing、fallback或兼容分支。
- 迁移失败必须回滚整个文件/import变更，不允许新旧文件同时成为authority。

## 6. Tests

- 现有相关测试：`test/unit/stage_process/framework/behavior_cases/test_execution_identity.py`, `test/unit/stage_process/stages/system_testing_stage/behavior_cases/test_execution_step_normalization.py`, `test/unit/stage_process/stages/system_testing_stage/behavior_cases/test_case_data_raw_text_validation.py`, `test/unit/tier/tier_runtime/behavior_cases/test_client_replay.py`, `test/unit/tier/tier_runtime/behavior_cases/test_provider_usage.py`, `test/unit/tier/tier_runtime/behavior_cases/test_mlexp_backend.py`, `test/unit/tier/tier_runtime/behavior_cases/test_server_jobs.py`, `test/unit/memory/retrieval_context/behavior_cases/test_judge_validator.py`, `test/unit/webui/dashboard/behavior_cases/test_dashboard_fast_paths.py`, `test/unit/common/stats/behavior_cases/test_llm_stats.py`, `test/subsystem/tier/case/tier-BASIS-001/run.py`, `test/subsystem/tier/case/tier-ENV-001/run.py`；其余由Module测试索引覆盖。
- Contract Test覆盖public signature、authority、错误传播和禁止fallback。
- 迁移文件增加import graph检查，证明旧source path无production/test caller。

## 7. Current Difference

文件已位于目标路径。本ISD不批准额外行为变化；已知缺陷只能按Module Design和bug记录另行进入Test Design。

## 8. Approved Delta：唯一HTTP Transport

`TierClient`保留`invoke_role/call/call_async/get_result/escalate/stats/runtime/probe/management`公共能力，全部请求只通过现有`server_url`/`TIER_SERVER_URL`进入Tier HTTP Service；默认仍为`http://127.0.0.1:8765`。URL必须为loopback HTTP(S)，不得允许Browser输入覆盖，也不得import Router或Backend、保留embedded/direct-provider fallback。

Role请求包含role、prompt source、scope identity、metadata、timeout和可选file paths。Client补齐execution identity但不覆盖调用方显式字段，不传credential或Backend selector。busy retry仅处理Service明确返回的busy结果，并受bounded schedule和总timeout约束；submit成功后只能poll同一job id，poll timeout或HTTP unknown outcome不得重新提交非幂等请求。

URL invalid、connection refused、connect/read timeout、HTTP status、malformed JSON、busy exhausted、poll timeout和Service business error必须分别映射，不能转为空content成功。read operation幂等；call/async submit/escalate/management write非幂等。HTTP connect/read/poll均要求positive timeout，日志和error必须redact credential。

新增测试必须覆盖真实HTTP Tier process、断连/malformed body/未知submit结果、poll timeout不重提、显式replay证据，以及源码/import graph中不存在Router/Backend访问或embedded fallback。
