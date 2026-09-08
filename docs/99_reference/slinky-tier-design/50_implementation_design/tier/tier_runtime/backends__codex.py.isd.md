# `src/llm_tier/backends/codex.py` ISD

Version: v1.5
Last Updated: 2026-09-08 12:18:44
Status: Draft / Source-Verified Baseline

target_file: `src/llm_tier/backends/codex.py`
target_state: `existing`

所属边界：Tier / Tier Server Module。
上游：`docs/40_module_design/tier/tier_server_module.md`。
接口追踪：provided_interfaces=`TIR-HTTP-001`, `TIR-HTTP-002`, `TIR-PROC-001`, `TIR-DATA-001`；consumed_interfaces=`MLX-HTTP-001`, `MLX-HTTP-002`, `MLX-HTTP-003`, `MLX-HTTP-004`, `MLX-HTTP-005`, `MLX-HTTP-006`。

## 1. 文件职责

本ISD以当前`src/llm_tier/backends/codex.py`为行为baseline，目标文件保留其单文件责任；除上游Module Design明确的Approved Delta外，不改变算法、selector、配置路径、重试或fallback。

## 2. 源码结构

- 当前行数：312
- Imports：`__future__:annotations`, `json`, `os`, `re`, `shutil`, `subprocess`, `time`, `dataclasses:dataclass,field`, `pathlib:Path`, `typing:Any`, `llm_tier.backends:register_backend`, `llm_tier.backends.agent_backend:AgentBackendMixin`, `llm_tier.backends.base:BaseBackendClient`, `llm_tier.exceptions:BackendCallError,QuotaExhaustedError`, `llm_tier.quota_manager:QuotaManager`
- Module constants：`DEFAULT_CODEX_CLI_PATH`, `DEFAULT_CODEX_CLI_MODEL`, `DEFAULT_CODEX_CLI_SANDBOX`, `DEFAULT_CODEX_CLI_TIMEOUT_SECONDS`

### 2.1 Classes / Functions / Methods

| Symbol | Line | Signature | Direct calls（最多10个） | Raises |
|---|---:|---|---|---|
| `_resolve_default_codex_cli_path` | 20 | `def _resolve_default_codex_cli_path() -> str` | `str.strip`, `tools_codex.is_file`, `shutil.which`, `Path`, `vscode_bin_root.exists`, `os.path.expanduser`, `Path.resolve`, `str`, `sorted`, `reversed` | none |
| `CodexCliResult` | 48 | `class CodexCliResult` | none | none |
| `CodexCliResult.to_serializable` | 61 | `def to_serializable(self) -> dict[str, Any]` | `list`, `_parse_codex_cli_usage` | none |
| `_invoke_codex_cli` | 78 | `def _invoke_codex_cli(*, prompt_text: str, workspace_root: str \| Path, output_message_path: str \| Path, codex_path: str = DEFAULT_CODEX_CLI_PATH, model_name: str = DEFAULT_CODEX_CLI_MODEL, sandbox_mode: str = DEFAULT_CODEX_CLI_SANDBOX, timeout_seconds: int = DEFAULT_CODEX_CLI_TIMEOUT_SECONDS) -> CodexCliResult` | `Path.resolve`, `output_message_abs.parent.mkdir`, `time.monotonic`, `str.strip`, `command.extend`, `CodexCliResult`, `str`, `subprocess.run`, `output_message_abs.exists`, `output_message_abs.read_text` | none |
| `_decode_timeout_output` | 165 | `def _decode_timeout_output(output: str \| bytes \| None) -> str` | `isinstance`, `str`, `output.decode` | none |
| `_parse_codex_cli_usage` | 173 | `def _parse_codex_cli_usage(stderr: str, stdout: str = '') -> dict[str, Any]` | `_parse_codex_cli_json_usage`, `str`, `re.search`, `int`, `match.group.replace`, `match.group` | none |
| `_parse_codex_cli_json_usage` | 195 | `def _parse_codex_cli_json_usage(stdout: str) -> dict[str, Any]` | `str.splitlines`, `_to_int`, `raw_line.strip`, `event.get`, `isinstance`, `latest_usage.get`, `dict`, `str`, `json.loads`, `str.strip` | none |
| `_to_int` | 230 | `def _to_int(value: Any) -> int` | `int` | none |
| `CodexClient` | 237 | `class CodexClient(BaseBackendClient, AgentBackendMixin)` | none | none |
| `CodexClient.__init__` | 238 | `def __init__(self, cli_path: str = '', model_name: str = '', sandbox: str = 'danger-full-access', timeout_seconds: int = 180, **kwargs: Any) -> None` | none | none |
| `CodexClient.backend` | 245 | `def backend(self) -> str` | none | none |
| `CodexClient.backend_type` | 249 | `def backend_type(self) -> str` | none | none |
| `CodexClient.supported_models` | 252 | `def supported_models(self) -> list[str]` | none | none |
| `CodexClient.call` | 255 | `def call(self, model_name: str = '', prompt: str = '', system_prompt: str = '', temperature: float = 0.0, timeout_seconds: int = 180, metadata: dict[str, str] \| None = None, **kwargs: Any) -> dict[str, Any]` | `time.time`, `str`, `tempfile.NamedTemporaryFile`, `_invoke_codex_cli`, `os.path.exists`, `QuotaManager.is_quota_error`, `get`, `os.getcwd`, `BackendCallError`, `open.read` | `BackendCallError`, `QuotaExhaustedError` |

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
- Process/Command
- 非幂等写操作必须由所属Module现有single-writer/lock/attempt机制约束；unknown outcome不得盲目重试。
- timeout、retry、redaction和日志字段沿用当前owner Contract，不在本文件建立第二套policy。

## 5. Error、Recovery与禁止路径

- 保留第2节列出的typed exception和调用方错误映射；不得把malformed、missing、timeout或runner error转换为空成功。
- 不自动跨Stage rollback，不新增config、selector、routing、fallback或兼容分支。
- 迁移失败必须回滚整个文件/import变更，不允许新旧文件同时成为authority。

## 6. Tests

- 现有相关测试：`test/unit/stage_process/stages/system_testing_stage/behavior_cases/test_cross_phase_success_gate_removed.py`, `test/unit/tier/tier_runtime/behavior_cases/test_client_replay.py`, `test/unit/tier/tier_runtime/behavior_cases/test_mlexp_backend.py`, `test/unit/tier/tier_runtime/behavior_cases/test_server_jobs.py`, `test/unit/webui/dashboard/behavior_cases/test_dashboard_fast_paths.py`, `test/subsystem/tier/case/tier-BASIS-001/run.py`, `test/subsystem/tier/case/tier-ENV-001/run.py`。
- Contract Test覆盖public signature、authority、错误传播和禁止fallback。
- 迁移文件增加import graph检查，证明旧source path无production/test caller。

## 7. Current Difference

文件已位于目标路径。本ISD不批准额外行为变化；已知缺陷只能按Module Design和bug记录另行进入Test Design。
