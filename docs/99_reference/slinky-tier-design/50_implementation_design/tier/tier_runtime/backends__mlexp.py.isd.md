# `src/llm_tier/backends/mlexp.py` ISD

Version: v1.7
Last Updated: 2026-09-08 12:18:44
Status: Draft / Source-Verified Baseline + Approved Delta

target_file: `src/llm_tier/backends/mlexp.py`
target_state: `existing`

所属边界：Tier / Tier Server Module。
上游：`docs/40_module_design/tier/tier_server_module.md`。
接口追踪：provided_interfaces=`TIR-HTTP-001`, `TIR-HTTP-002`, `TIR-PROC-001`, `TIR-DATA-001`；consumed_interfaces=`MLX-HTTP-001`, `MLX-HTTP-002`, `MLX-HTTP-003`, `MLX-HTTP-004`, `MLX-HTTP-005`, `MLX-HTTP-006`。

## 1. 文件职责

本ISD以当前`src/llm_tier/backends/mlexp.py`为行为baseline，目标文件保留其单文件责任；除上游Module Design明确的Approved Delta外，不改变算法、selector、配置路径、重试或fallback。

## 2. 源码结构

- 当前行数：1002
- Imports：`__future__:annotations`, `hashlib`, `json`, `time`, `urllib.error`, `urllib.parse`, `urllib.request`, `dataclasses:dataclass,field`, `pathlib:Path`, `typing:Any`, `llm_tier.backends:register_backend`, `llm_tier.backends.base:BaseBackendClient`, `llm_tier.exceptions:BackendCallError`
- Module constants：`DEFAULT_MLEXP_BASE_URL`, `DEFAULT_MLEXP_HTTP_PORT`, `DEFAULT_MLEXP_TIMEOUT_SECONDS`, `DEFAULT_MLEXP_AI_BACKEND`, `DEFAULT_MLEXP_AI_MODEL_NAME`, `DEFAULT_MLEXP_MODEL_NAME`, `DEFAULT_MLEXP_REMOTE_WORKSPACE_ROOT`

### 2.1 Classes / Functions / Methods

| Symbol | Line | Signature | Direct calls（最多10个） | Raises |
|---|---:|---|---|---|
| `MlexpBackendError` | 33 | `class MlexpBackendError(RuntimeError)` | none | none |
| `MlexpSystemTestJob` | 44 | `class MlexpSystemTestJob` | none | none |
| `MlexpProjectCaseReportLocation` | 60 | `class MlexpProjectCaseReportLocation` | none | none |
| `MlexpProjectCaseReportLocation.report_path` | 72 | `def report_path(self, *, workspace_root: str \| Path) -> Path` | `Path` | none |
| `_mlexp_base_url_from_ssh` | 89 | `def _mlexp_base_url_from_ssh(ssh: Any) -> str` | `str.strip`, `isinstance`, `str`, `ssh.get` | none |
| `MlexpClient` | 104 | `class MlexpClient(BaseBackendClient)` | none | none |
| `MlexpClient.__init__` | 112 | `def __init__(self, base_url: str = '', timeout_seconds: int = DEFAULT_MLEXP_TIMEOUT_SECONDS, **kwargs: Any) -> None` | `str.rstrip`, `int`, `float`, `str.strip`, `_mlexp_base_url_from_ssh`, `kwargs.get`, `str` | none |
| `MlexpClient.backend` | 131 | `def backend(self) -> str` | none | none |
| `MlexpClient.backend_type` | 141 | `def backend_type(self) -> str` | none | none |
| `MlexpClient.supported_models` | 150 | `def supported_models(self) -> list[str]` | none | none |
| `MlexpClient.call` | 159 | `def call(self, model_name: str, prompt: str, system_prompt: str = '', temperature: float = 0.0, timeout_seconds: int = DEFAULT_MLEXP_TIMEOUT_SECONDS, metadata: dict[str, str] \| None = None, **kwargs: Any) -> dict[str, Any]` | `str.strip`, `time.time`, `self.health`, `self.runtime`, `bool`, `isinstance`, `self._call_system_test_job`, `health.get`, `BackendCallError`, `runtime.get` | `BackendCallError` |
| `MlexpClient._call_system_test_job` | 220 | `def _call_system_test_job(self, *, model_name: str, prompt: str, role_name: str, timeout_seconds: int, metadata: dict[str, str], started_at: float) -> dict[str, Any]` | `_parse_mlexp_model_selector`, `str.strip`, `_resolve_mlexp_case_id`, `str.rstrip`, `build_description_only_system_test_payload`, `str.strip.lower`, `_usage_from_mlexp_terminal`, `self._read_job_output_json`, `_is_preflight_call`, `self.submit_system_test` | `BackendCallError` |
| `MlexpClient.health` | 305 | `def health(self, *, timeout_seconds: int \| None = None) -> dict[str, Any]` | `self._request_json` | none |
| `MlexpClient.runtime` | 314 | `def runtime(self, *, timeout_seconds: int \| None = None) -> dict[str, Any]` | `self._request_json` | none |
| `MlexpClient.submit_description_only_case` | 324 | `def submit_description_only_case(self, *, project_name: str, case_id: str, name: str, description: str, expected: str, remote_workspace_root: str = DEFAULT_MLEXP_REMOTE_WORKSPACE_ROOT, ai_backend: str = DEFAULT_MLEXP_AI_BACKEND, model_name: str = DEFAULT_MLEXP_AI_MODEL_NAME, phase_name: str = 'manual', task_id: str = '', timeout_seconds: int \| None = None) -> MlexpSystemTestJob` | `build_description_only_system_test_payload`, `self._request_json`, `self._parse_submit_response` | none |
| `MlexpClient.submit_case_payload` | 366 | `def submit_case_payload(self, *, project_name: str, case_payload: dict[str, Any], case_id: str = '', remote_workspace_root: str = DEFAULT_MLEXP_REMOTE_WORKSPACE_ROOT, report_root: str = 'test/system', report_subdir: str = 'mlexp', details_dir: str = 'details', ai_backend: str = DEFAULT_MLEXP_AI_BACKEND, model_name: str = DEFAULT_MLEXP_AI_MODEL_NAME, ai_mode: str = 'full', app_files: dict[str, str] \| None = None, environment_setup: dict[str, Any] \| None = None, phase_name: str = 'execution', task_id: str = '', task_key: str = '', timeout_seconds: int \| None = None) -> MlexpSystemTestJob` | `build_system_test_payload_from_case`, `self._request_json`, `self._parse_submit_response` | none |
| `MlexpClient.submit_system_test` | 417 | `def submit_system_test(self, payload: dict[str, Any], *, timeout_seconds: int \| None = None) -> MlexpSystemTestJob` | `self._request_json`, `self._parse_submit_response` | none |
| `MlexpClient.get_job` | 437 | `def get_job(self, job_id: str, *, timeout_seconds: int \| None = None) -> dict[str, Any]` | `self._require_job_id`, `self._request_json` | none |
| `MlexpClient.cancel_job` | 447 | `def cancel_job(self, job_id: str, *, timeout_seconds: int \| None = None) -> dict[str, Any]` | `self._require_job_id`, `self._request_json` | none |
| `MlexpClient.get_artifacts` | 462 | `def get_artifacts(self, job_id: str, *, timeout_seconds: int \| None = None) -> dict[str, Any]` | `self._require_job_id`, `self._request_json` | none |
| `MlexpClient.get_workspace_file` | 476 | `def get_workspace_file(self, job_id: str, path: str, *, timeout_seconds: int \| None = None) -> dict[str, Any]` | `self._require_job_id`, `urllib.parse.quote`, `self._request_json`, `str.strip`, `str` | none |
| `MlexpClient._read_job_output_json` | 491 | `def _read_job_output_json(self, job_id: str, path: str, *, timeout_seconds: int \| None = None) -> dict[str, Any]` | `payload.get`, `self.get_workspace_file`, `json.loads`, `isinstance`, `content.strip` | none |
| `MlexpClient.wait_for_job` | 513 | `def wait_for_job(self, job_id: str, *, timeout_seconds: int = 600, poll_interval_seconds: float = 5.0) -> dict[str, Any]` | `MlexpBackendError`, `time.monotonic`, `max`, `self.get_job`, `str.strip.lower`, `time.sleep`, `int`, `min`, `str.strip`, `float` | `MlexpBackendError` |
| `MlexpClient._parse_submit_response` | 542 | `def _parse_submit_response(self, response: dict[str, Any]) -> MlexpSystemTestJob` | `str.strip`, `MlexpSystemTestJob`, `bool`, `MlexpBackendError`, `response.get`, `str` | `MlexpBackendError` |
| `MlexpClient._require_job_id` | 563 | `def _require_job_id(self, job_id: str) -> str` | `str.strip`, `urllib.parse.quote`, `MlexpBackendError`, `str` | `MlexpBackendError` |
| `MlexpClient._request_json` | 575 | `def _request_json(self, method: str, path: str, *, payload: dict[str, Any] \| None = None, timeout_seconds: int \| None = None) -> dict[str, Any]` | `urllib.request.Request`, `json.dumps.encode`, `json.loads`, `isinstance`, `MlexpBackendError`, `urllib.request.urlopen`, `response.read.decode`, `exc.read.decode`, `json.dumps`, `response.read` | `MlexpBackendError` |
| `build_description_only_system_test_payload` | 621 | `def build_description_only_system_test_payload(*, project_name: str, case_id: str, name: str, description: str, expected: str, remote_workspace_root: str = DEFAULT_MLEXP_REMOTE_WORKSPACE_ROOT, app_workdir: str = '.', report_root: str = 'test/system', report_subdir: str = 'mlexp', details_dir: str = 'details', ai_backend: str = DEFAULT_MLEXP_AI_BACKEND, model_name: str = DEFAULT_MLEXP_AI_MODEL_NAME, stage_name: str = 'system_testing', phase_name: str = 'manual', task_id: str = '', task_key: str = '', external_id: str = '', agent_kind: str = '') -> dict[str, Any]` | `_require_text`, `str.strip`, `str.strip.rstrip`, `str` | none |
| `build_system_test_payload_from_case` | 705 | `def build_system_test_payload_from_case(*, project_name: str, case_payload: dict[str, Any], case_id: str = '', remote_workspace_root: str = DEFAULT_MLEXP_REMOTE_WORKSPACE_ROOT, app_workdir: str = '.', report_root: str = 'test/system', report_subdir: str = 'mlexp', details_dir: str = 'details', ai_backend: str = DEFAULT_MLEXP_AI_BACKEND, model_name: str = DEFAULT_MLEXP_AI_MODEL_NAME, ai_mode: str = 'full', app_files: dict[str, str] \| None = None, environment_setup: dict[str, Any] \| None = None, stage_name: str = 'system_testing', phase_name: str = 'execution', task_id: str = '', task_key: str = '', external_id: str = '') -> dict[str, Any]` | `_require_text`, `str.strip.rstrip`, `isinstance`, `MlexpBackendError`, `str`, `dict`, `str.strip`, `case_payload.get` | `MlexpBackendError` |
| `read_project_case_report` | 793 | `def read_project_case_report(*, workspace_root: str \| Path, project_name: str, case_id: str, root: str = 'test/system', subdir: str = 'mlexp') -> dict[str, Any]` | `MlexpProjectCaseReportLocation`, `location.report_path`, `json.loads`, `isinstance`, `MlexpBackendError`, `report_path.read_text` | `MlexpBackendError` |
| `extract_llm_usage_from_report` | 825 | `def extract_llm_usage_from_report(report: dict[str, Any]) -> dict[str, Any]` | `report.get`, `isinstance`, `dict` | none |
| `_usage_from_mlexp_terminal` | 855 | `def _usage_from_mlexp_terminal(terminal: dict[str, Any]) -> dict[str, Any]` | `terminal.get`, `isinstance`, `usage_sources.extend`, `report.get`, `int`, `_failed_mlexp_llm_call_count`, `max`, `_mlexp_usage_latency_ms`, `bool`, `str` | none |
| `_failed_mlexp_llm_call_count` | 909 | `def _failed_mlexp_llm_call_count(*, usage: dict[str, Any], llm_calls: list[dict[str, Any]]) -> int` | `usage.get`, `int`, `str.strip`, `str.strip.lower`, `str`, `item.get` | none |
| `_mlexp_usage_latency_ms` | 928 | `def _mlexp_usage_latency_ms(*, usage: dict[str, Any], llm_calls: list[dict[str, Any]], call_count: int) -> float` | `float`, `usage.get`, `sum`, `len`, `item.get` | none |
| `_parse_mlexp_model_selector` | 950 | `def _parse_mlexp_model_selector(model_name: str) -> tuple[str, str]` | `str.strip`, `normalized.split`, `str`, `backend.strip`, `model.strip` | none |
| `_resolve_mlexp_case_id` | 969 | `def _resolve_mlexp_case_id(*, task_id: str, task_key: str, prompt: str) -> str` | `hashlib.sha1.hexdigest`, `task_id.rsplit`, `hashlib.sha1`, `str.encode`, `str` | none |
| `_is_preflight_call` | 984 | `def _is_preflight_call(role_name: str, phase_name: str) -> bool` | `lower` | none |
| `_require_text` | 995 | `def _require_text(value: str, name: str) -> str` | `str.strip`, `MlexpBackendError`, `str` | `MlexpBackendError` |

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
- 非幂等写操作必须由所属Module现有single-writer/lock/attempt机制约束；unknown outcome不得盲目重试。
- timeout、retry、redaction和日志字段沿用当前owner Contract，不在本文件建立第二套policy。

## 5. Error、Recovery与禁止路径

- 保留第2节列出的typed exception和调用方错误映射；不得把malformed、missing、timeout或runner error转换为空成功。
- 不自动跨Stage rollback，不新增config、selector、routing、fallback或兼容分支。
- 迁移失败必须回滚整个文件/import变更，不允许新旧文件同时成为authority。

## 6. Tests

- 现有相关测试：`test/unit/stage_process/stages/system_testing_stage/behavior_cases/test_execution_step_normalization.py`, `test/unit/stage_process/stages/system_testing_stage/behavior_cases/test_environment_report_validation.py`, `test/unit/stage_process/stages/system_testing_stage/behavior_cases/test_cross_phase_success_gate_removed.py`, `test/unit/tier/tier_runtime/behavior_cases/test_client_replay.py`, `test/unit/tier/tier_runtime/behavior_cases/test_mlexp_backend.py`, `test/unit/tier/tier_runtime/behavior_cases/test_server_jobs.py`, `test/unit/memory/retrieval_context/behavior_cases/test_context_provider.py`, `test/unit/webui/dashboard/behavior_cases/test_dashboard_fast_paths.py`, `test/unit/common/stats/behavior_cases/test_llm_stats.py`, `test/subsystem/tier/case/tier-BASIS-001/run.py`, `test/subsystem/tier/case/tier-ENV-001/run.py`。
- Contract Test覆盖public signature、authority、错误传播和禁止fallback。
- 迁移文件增加import graph检查，证明旧source path无production/test caller。

## 7. Current Difference

文件已位于目标路径。`build_system_test_payload_from_case()`必须根据输入实体选择唯一部署模式：非空`app_files`表示文件尚需由MLEXP materialize，必须使用现有`inline` deploy并完整携带文件；仅当`app_files`为空且`remote_workspace_root`非空时，才使用已预部署的`mlexp_workspace`。禁止因为配置了remote root而丢弃待部署文件，也禁止同时声明两种deploy模式。

## 8. Approved Delta：显式MLEXP Endpoint

删除`DEFAULT_MLEXP_BASE_URL`中的LAN地址默认值及`_mlexp_base_url_from_ssh()`。`MlexpClient.__init__()`要求显式提供非空且scheme为HTTP(S)的`base_url`；缺失或非法值抛`MlexpBackendError(code="config_missing", ...)`或对应config error。SSH配置不得参与URL推导，System Testing不得import被删除的private helper。

URL仅通过`base_url.rstrip('/') + path`构造。submit属于非幂等操作，请求结果未知时不得自动resubmit；poll只读取原job。job id和workspace path先做本地基本validation，服务端仍是authoritative validator。HTTP 4xx、5xx、timeout、decode error与domain terminal failure必须分类。

payload保留project/stage/phase/task/task_key/case_id/external_id。terminal Report中的LLM calls/tokens/latency映射到Tier stats，不得把一次MLEXP job自动计为一次LLM call。测试必须覆盖缺失endpoint、非法scheme、SSH-only config、旧LAN地址不存在、submit unknown outcome、poll、cancel、Artifact/file读取和usage identity。
