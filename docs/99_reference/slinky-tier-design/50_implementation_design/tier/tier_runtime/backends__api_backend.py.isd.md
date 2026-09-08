# `src/llm_tier/backends/api_backend.py` ISD

Version: v1.5
Last Updated: 2026-09-08 12:18:44
Status: Draft / Source-Verified Baseline

target_file: `src/llm_tier/backends/api_backend.py`
target_state: `existing`

所属边界：Tier / Tier Server Module。
上游：`docs/40_module_design/tier/tier_server_module.md`。
接口追踪：provided_interfaces=`TIR-HTTP-001`, `TIR-HTTP-002`, `TIR-PROC-001`, `TIR-DATA-001`；consumed_interfaces=`MLX-HTTP-001`, `MLX-HTTP-002`, `MLX-HTTP-003`, `MLX-HTTP-004`, `MLX-HTTP-005`, `MLX-HTTP-006`。

## 1. 文件职责

本ISD以当前`src/llm_tier/backends/api_backend.py`为行为baseline，目标文件保留其单文件责任；除上游Module Design明确的Approved Delta外，不改变算法、selector、配置路径、重试或fallback。

## 2. 源码结构

- 当前行数：90
- Imports：`__future__:annotations`, `json`, `time`, `urllib.error`, `urllib.request`, `typing:Any`, `llm_tier.exceptions:BackendCallError,QuotaExhaustedError`, `llm_tier.quota_manager:QuotaManager`
- Module constants：none

### 2.1 Classes / Functions / Methods

| Symbol | Line | Signature | Direct calls（最多10个） | Raises |
|---|---:|---|---|---|
| `ApiBackendMixin` | 19 | `class ApiBackendMixin` | none | none |
| `ApiBackendMixin._api_retry_deadline` | 26 | `def _api_retry_deadline(self, timeout_seconds: int) -> float` | `time.monotonic`, `max`, `int` | none |
| `ApiBackendMixin._remaining_api_timeout` | 35 | `def _remaining_api_timeout(self, deadline: float, timeout_seconds: int) -> int` | `max`, `time.monotonic`, `BackendCallError`, `int` | `BackendCallError` |
| `ApiBackendMixin._sleep_before_api_retry` | 47 | `def _sleep_before_api_retry(self, retry_count: int, deadline: float, timeout_seconds: int) -> None` | `min`, `time.sleep`, `max`, `BackendCallError`, `int`, `time.monotonic` | `BackendCallError` |
| `ApiBackendMixin._post_json` | 53 | `def _post_json(self, url: str, payload: dict[str, Any], headers: dict[str, str], timeout: int) -> dict[str, Any]` | `json.dumps.encode`, `urllib.request.Request`, `ssl.create_default_context`, `context.load_verify_locations`, `urllib.request.urlopen`, `json.loads`, `json.dumps`, `certifi.where`, `resp.read.decode`, `resp.read` | none |
| `ApiBackendMixin._handle_http_error` | 72 | `def _handle_http_error(self, status_code: int, body: str, retry_count: int, max_retry: int, model_name: str = '', retry_deadline: float \| None = None, timeout_seconds: int = 0) -> None` | `BackendCallError`, `QuotaManager.is_quota_error`, `QuotaExhaustedError`, `self._sleep_before_api_retry`, `time.sleep` | `BackendCallError`, `QuotaExhaustedError` |

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

- 现有相关测试：`test/unit/stage_process/stages/system_testing_stage/behavior_cases/test_cross_phase_success_gate_removed.py`, `test/unit/tier/tier_runtime/behavior_cases/test_client_replay.py`, `test/unit/tier/tier_runtime/behavior_cases/test_mlexp_backend.py`, `test/unit/tier/tier_runtime/behavior_cases/test_server_jobs.py`, `test/unit/webui/dashboard/behavior_cases/test_dashboard_fast_paths.py`, `test/subsystem/tier/case/tier-BASIS-001/run.py`, `test/subsystem/tier/case/tier-ENV-001/run.py`。
- Contract Test覆盖public signature、authority、错误传播和禁止fallback。
- 迁移文件增加import graph检查，证明旧source path无production/test caller。

## 7. Current Difference

文件已位于目标路径。本ISD不批准额外行为变化；已知缺陷只能按Module Design和bug记录另行进入Test Design。
