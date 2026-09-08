# `src/llm_tier/backends/debug.py` ISD

Version: v1.4
Last Updated: 2026-09-08 12:18:44
Status: Draft / Source-Verified Baseline

target_file: `src/llm_tier/backends/debug.py`
target_state: `existing`

所属边界：Tier / Tier Server Module。
上游：`docs/40_module_design/tier/tier_server_module.md`。
接口追踪：provided_interfaces=`TIR-HTTP-001`, `TIR-HTTP-002`, `TIR-PROC-001`, `TIR-DATA-001`；consumed_interfaces=`MLX-HTTP-001`, `MLX-HTTP-002`, `MLX-HTTP-003`, `MLX-HTTP-004`, `MLX-HTTP-005`, `MLX-HTTP-006`。

## 1. 文件职责

本ISD以当前`src/llm_tier/backends/debug.py`为行为baseline，目标文件保留其单文件责任；除上游Module Design明确的Approved Delta外，不改变算法、selector、配置路径、重试或fallback。

## 2. 源码结构

- 当前行数：252
- Imports：`__future__:annotations`, `json`, `time`, `pathlib:Path`, `typing:Any`, `llm_tier.backends:register_backend`, `llm_tier.backends.base:BaseBackendClient`, `llm_tier.exceptions:BackendCallError,QuotaExhaustedError`
- Module constants：none

### 2.1 Classes / Functions / Methods

| Symbol | Line | Signature | Direct calls（最多10个） | Raises |
|---|---:|---|---|---|
| `_resolve_path` | 20 | `def _resolve_path(path_value: str, *, base_dir: Path) -> Path \| None` | `str.strip`, `Path.expanduser`, `candidate.resolve`, `candidate.is_absolute`, `str`, `Path` | none |
| `_read_content_file` | 37 | `def _read_content_file(path_value: str, *, base_dir: Path) -> str` | `_resolve_path`, `BackendCallError`, `content_path.read_text`, `content_path.suffix.lower`, `json.dumps`, `content_path.is_file`, `json.loads` | `BackendCallError` |
| `DebugBackendClient` | 59 | `class DebugBackendClient(BaseBackendClient)` | none | none |
| `DebugBackendClient.__init__` | 66 | `def __init__(self, scenario_file: str = '', content: str = '', default_content: str = 'DEBUG OK', latency_ms: int = 0, **kwargs: Any) -> None` | `str.strip`, `str`, `int` | none |
| `DebugBackendClient.backend` | 86 | `def backend(self) -> str` | none | none |
| `DebugBackendClient.backend_type` | 96 | `def backend_type(self) -> str` | none | none |
| `DebugBackendClient.supported_models` | 105 | `def supported_models(self) -> list[str]` | none | none |
| `DebugBackendClient.call` | 114 | `def call(self, model_name: str, prompt: str, system_prompt: str = '', temperature: float = 0.0, timeout_seconds: int = 600, metadata: dict[str, str] \| None = None, **kwargs: Any) -> dict[str, Any]` | `dict`, `self._load_scenario`, `int`, `max`, `str.strip.lower`, `str.strip`, `self._resolve_content`, `self._resolve_token_usage`, `BackendCallError`, `time.sleep` | `BackendCallError`, `QuotaExhaustedError`, `RuntimeError` |
| `DebugBackendClient._load_scenario` | 175 | `def _load_scenario(self, metadata: dict[str, str]) -> dict[str, Any]` | `str.strip`, `Path.resolve`, `Path.cwd`, `_resolve_path`, `str`, `BackendCallError`, `json.loads`, `Path`, `scenario_path.is_file`, `scenario_path.read_text` | `BackendCallError` |
| `DebugBackendClient._resolve_content` | 214 | `def _resolve_content(self, scenario: dict[str, Any]) -> str` | `Path`, `str.strip`, `str`, `_read_content_file`, `scenario.get`, `Path.cwd`, `_resolve_path` | none |
| `DebugBackendClient._resolve_token_usage` | 233 | `def _resolve_token_usage(self, scenario: dict[str, Any], content: str) -> dict[str, int]` | `scenario.get`, `isinstance`, `int`, `max`, `usage.get`, `len`, `str` | none |

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
- 非幂等写操作必须由所属Module现有single-writer/lock/attempt机制约束；unknown outcome不得盲目重试。
- timeout、retry、redaction和日志字段沿用当前owner Contract，不在本文件建立第二套policy。

## 5. Error、Recovery与禁止路径

- 保留第2节列出的typed exception和调用方错误映射；不得把malformed、missing、timeout或runner error转换为空成功。
- 不自动跨Stage rollback，不新增config、selector、routing、fallback或兼容分支。
- 迁移失败必须回滚整个文件/import变更，不允许新旧文件同时成为authority。

## 6. Tests

- 现有相关测试：`test/unit/stage_process/framework/behavior_cases/test_execution_identity.py`, `test/unit/stage_process/framework/behavior_cases/test_task_state_summary.py`, `test/unit/stage_process/framework/behavior_cases/test_phase_runtime.py`, `test/unit/stage_process/framework/behavior_cases/test_task_acceptance_artifacts.py`, `test/unit/stage_process/framework/behavior_cases/test_phase_index_selection.py`, `test/unit/stage_process/stages/system_testing_stage/behavior_cases/test_execution_step_normalization.py`, `test/unit/stage_process/stages/system_testing_stage/behavior_cases/test_case_data_raw_text_validation.py`, `test/unit/stage_process/stages/system_testing_stage/behavior_cases/test_cross_phase_success_gate_removed.py`, `test/unit/stage_process/stages/system_testing_stage/behavior_cases/test_case_phase_runtime_policy.py`, `test/unit/tier/tier_runtime/behavior_cases/test_client_replay.py`, `test/unit/tier/tier_runtime/behavior_cases/test_mlexp_backend.py`, `test/unit/tier/tier_runtime/behavior_cases/test_server_jobs.py`；其余由Module测试索引覆盖。
- Contract Test覆盖public signature、authority、错误传播和禁止fallback。
- 迁移文件增加import graph检查，证明旧source path无production/test caller。

## 7. Current Difference

文件已位于目标路径。本ISD不批准额外行为变化；已知缺陷只能按Module Design和bug记录另行进入Test Design。
