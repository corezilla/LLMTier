# `src/llm_tier/backends/opencode.py` ISD

Version: v1.6
Last Updated: 2026-09-08 12:18:44
Status: Draft / Source-Verified Baseline

target_file: `src/llm_tier/backends/opencode.py`
target_state: `existing`

所属边界：Tier / Tier Server Module。
上游：`docs/40_module_design/tier/tier_server_module.md`。
接口追踪：provided_interfaces=`TIR-HTTP-001`, `TIR-HTTP-002`, `TIR-PROC-001`, `TIR-DATA-001`；consumed_interfaces=`MLX-HTTP-001`, `MLX-HTTP-002`, `MLX-HTTP-003`, `MLX-HTTP-004`, `MLX-HTTP-005`, `MLX-HTTP-006`。

## 1. 文件职责

本ISD以当前`src/llm_tier/backends/opencode.py`为行为baseline，目标文件保留其单文件责任；除上游Module Design明确的Approved Delta外，不改变算法、selector、配置路径、重试或fallback。

## 2. 源码结构

- 当前行数：547
- Imports：`__future__:annotations`, `json`, `os`, `shutil`, `time`, `dataclasses:dataclass,field`, `pathlib:Path`, `typing:Any`, `llm_tier.backends:register_backend`, `llm_tier.backends.agent_backend:AgentBackendMixin`, `llm_tier.backends.base:BaseBackendClient`, `llm_tier.backends.cli_io:build_cli_log_paths,run_cli_with_live_logs`, `llm_tier.exceptions:BackendCallError,QuotaExhaustedError`, `llm_tier.quota_manager:QuotaManager`
- Module constants：`DEFAULT_OPENCODE_CLI_PATH`, `DEFAULT_OPENCODE_CLI_MODEL`, `DEFAULT_OPENCODE_CLI_TIMEOUT_SECONDS`, `_ANSI_ESCAPE_RE`

### 2.1 Classes / Functions / Methods

| Symbol | Line | Signature | Direct calls（最多10个） | Raises |
|---|---:|---|---|---|
| `_resolve_default_opencode_cli_path` | 25 | `def _resolve_default_opencode_cli_path() -> str` | `str.strip`, `shutil.which`, `repo_tool_path.exists`, `os.path.expanduser`, `str`, `os.environ.get`, `Path.resolve`, `Path` | none |
| `OpenCodeCliResult` | 50 | `class OpenCodeCliResult` | none | none |
| `OpenCodeCliResult.to_serializable` | 70 | `def to_serializable(self) -> dict[str, Any]` | `list`, `_parse_opencode_cli_usage` | none |
| `_invoke_opencode_cli` | 93 | `def _invoke_opencode_cli(*, prompt_text: str, workspace_root: str \| Path, opencode_path: str = DEFAULT_OPENCODE_CLI_PATH, model_name: str = DEFAULT_OPENCODE_CLI_MODEL, timeout_seconds: int = DEFAULT_OPENCODE_CLI_TIMEOUT_SECONDS, dangerously_skip_permissions: bool = True, metadata: dict[str, Any] \| None = None) -> OpenCodeCliResult` | `Path.resolve`, `time.monotonic`, `_build_isolated_env`, `_build_opencode_run_command`, `_run_opencode_subprocess`, `Path`, `str` | none |
| `_build_isolated_env` | 133 | `def _build_isolated_env() -> dict[str, str]` | `os.environ.copy`, `list`, `json.dumps`, `env.keys`, `k.startswith` | none |
| `_build_opencode_run_command` | 153 | `def _build_opencode_run_command(*, opencode_path: str, model_name: str, workspace_root: str \| Path, dangerously_skip_permissions: bool, prompt_text: str) -> list[str]` | `Path.resolve`, `str.strip`, `command.append`, `str`, `command.extend` | none |
| `_run_opencode_subprocess` | 181 | `def _run_opencode_subprocess(*, command: list[str], cwd: str, timeout_seconds: int, env: dict[str, str], started_at: float, model_name: str, metadata: dict[str, Any] \| None = None) -> OpenCodeCliResult` | `build_cli_log_paths`, `run_cli_with_live_logs`, `_extract_opencode_content`, `OpenCodeCliResult`, `int`, `str`, `max`, `time.monotonic` | none |
| `_decode_timeout_output` | 236 | `def _decode_timeout_output(output: str \| bytes \| None) -> str` | `isinstance`, `str`, `output.decode` | none |
| `_extract_opencode_content` | 244 | `def _extract_opencode_content(stdout: str) -> str` | `str.splitlines`, `stdout.strip`, `raw_line.strip`, `str.strip`, `str`, `json.loads`, `isinstance`, `part.get`, `event.get`, `data.get` | none |
| `_extract_opencode_model_name` | 287 | `def _extract_opencode_model_name(stdout: str, stderr: str = '') -> str` | `str.splitlines`, `raw_line.strip`, `_strip_ansi`, `part.get`, `str`, `stripped.split`, `json.loads`, `isinstance`, `event.get`, `len` | none |
| `_strip_ansi` | 327 | `def _strip_ansi(text: str) -> str` | `_ANSI_ESCAPE_RE.sub`, `re.compile` | none |
| `_parse_opencode_cli_usage` | 350 | `def _parse_opencode_cli_usage(stderr: str, stdout: str = '') -> dict[str, Any]` | `str.splitlines`, `_to_int`, `raw_line.strip`, `event.get`, `isinstance`, `str.strip`, `_aggregate_opencode_step_usages`, `dict`, `str`, `json.loads` | none |
| `_aggregate_opencode_step_usages` | 398 | `def _aggregate_opencode_step_usages(step_usages: list[dict[str, Any]]) -> dict[str, Any]` | `_opencode_usage_int`, `isinstance`, `usage.get`, `_to_int`, `len`, `cache.get`, `dict` | none |
| `_opencode_usage_int` | 444 | `def _opencode_usage_int(usage: dict[str, Any], key: str) -> int` | `_to_int`, `usage.get` | none |
| `_to_int` | 448 | `def _to_int(value: Any) -> int` | `int` | none |
| `OpenCodeClient` | 461 | `class OpenCodeClient(BaseBackendClient, AgentBackendMixin)` | none | none |
| `OpenCodeClient.__init__` | 462 | `def __init__(self, cli_path: str = '', model_name: str = '', timeout_seconds: int = 180, **kwargs: Any) -> None` | none | none |
| `OpenCodeClient.backend` | 468 | `def backend(self) -> str` | none | none |
| `OpenCodeClient.backend_type` | 472 | `def backend_type(self) -> str` | none | none |
| `OpenCodeClient.supported_models` | 475 | `def supported_models(self) -> list[str]` | none | none |
| `OpenCodeClient.call` | 484 | `def call(self, model_name: str = '', prompt: str = '', system_prompt: str = '', temperature: float = 0.0, timeout_seconds: int = 180, metadata: dict[str, str] \| None = None, **kwargs: Any) -> dict[str, Any]` | `time.time`, `str`, `_invoke_opencode_cli`, `QuotaManager.is_quota_error`, `_parse_opencode_cli_usage`, `BackendCallError`, `_extract_opencode_content`, `QuotaExhaustedError`, `_extract_opencode_model_name`, `get` | `BackendCallError`, `QuotaExhaustedError` |

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
- OpenCode Agent必须同时以subprocess `cwd`和CLI `--dir`绑定到调用方提供的project workspace；workspace位于外层Git repository内时，不得回溯并改用repository root。
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

文件已位于目标路径。System Round 5确认OpenCode仅设置subprocess `cwd`仍可能回溯到外层Git root；现有调用路径必须显式传入同一workspace的`--dir`，不新增配置、selector、routing或fallback。
