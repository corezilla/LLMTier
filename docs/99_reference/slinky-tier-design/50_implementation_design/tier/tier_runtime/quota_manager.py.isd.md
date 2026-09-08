# `src/llm_tier/quota_manager.py` ISD

Version: v1.5
Last Updated: 2026-09-08 12:18:44
Status: Draft / Source-Verified Baseline

target_file: `src/llm_tier/quota_manager.py`
target_state: `existing`

所属边界：Tier / Tier Server Module。
上游：`docs/40_module_design/tier/tier_server_module.md`。
接口追踪：provided_interfaces=`TIR-PROC-001`, `TIR-DATA-001`；consumed_interfaces=`MLX-HTTP-001`, `MLX-HTTP-002`, `MLX-HTTP-003`, `MLX-HTTP-004`, `MLX-HTTP-005`, `MLX-HTTP-006`。

## 1. 文件职责

本ISD以当前`src/llm_tier/quota_manager.py`为行为baseline，目标文件保留其单文件责任；除上游Module Design明确的Approved Delta外，不改变算法、selector、配置路径、重试或fallback。

## 2. 源码结构

- 当前行数：360
- Imports：`__future__:annotations`, `json`, `os`, `time`, `datetime:datetime`, `pathlib:Path`, `typing:Any`, `llm_tier.tier_config:TierConfig`
- Module constants：`_QUOTA_ERROR_MARKERS`, `_QUOTA_STATE_FILE`

### 2.1 Classes / Functions / Methods

| Symbol | Line | Signature | Direct calls（最多10个） | Raises |
|---|---:|---|---|---|
| `_default_quota_state_dir` | 29 | `def _default_quota_state_dir() -> Path` | `Path.resolve`, `Path` | none |
| `QuotaManager` | 40 | `class QuotaManager` | none | none |
| `QuotaManager.__init__` | 48 | `def __init__(self, tier_config: TierConfig, state_dir: str \| Path = '') -> None` | `self._load_state`, `str.strip`, `Path`, `_default_quota_state_dir`, `str` | none |
| `QuotaManager._state_path` | 66 | `def _state_path(self) -> str` | `str` | none |
| `QuotaManager._load_state` | 75 | `def _load_state(self) -> None` | `self._state_path`, `os.path.isfile`, `data.get`, `open`, `json.load`, `entry.get`, `self._normalize_reset_at` | none |
| `QuotaManager._save_state` | 99 | `def _save_state(self) -> None` | `self._state_path`, `os.path.dirname`, `os.makedirs`, `open`, `json.dump`, `self._mark_time.get`, `self._reset_time.get`, `self._exhausted.items` | none |
| `QuotaManager._quota_key` | 123 | `def _quota_key(self, backend: str, model_name: str) -> str` | `self._tier_config.find_backend_model`, `str.strip`, `str`, `getattr` | none |
| `QuotaManager.is_exhausted` | 136 | `def is_exhausted(self, backend: str, model_name: str) -> bool` | `self._check_auto_reset`, `self._quota_key`, `self._exhausted.get` | none |
| `QuotaManager.mark_exhausted` | 148 | `def mark_exhausted(self, backend: str, model_name: str, error_message: str = '') -> None` | `self._quota_key`, `time.time`, `self._parse_reset_at`, `self._save_state`, `self._reset_time.pop` | none |
| `QuotaManager._parse_reset_at` | 166 | `def _parse_reset_at(msg: str) -> str` | `re.search`, `QuotaManager._normalize_reset_at`, `re.match`, `m.group.strip`, `msg.strip`, `m.group`, `datetime.strptime`, `dt.strftime` | none |
| `QuotaManager._normalize_reset_at` | 213 | `def _normalize_reset_at(reset_at: Any) -> str` | `str.strip`, `re.search`, `re.fullmatch`, `str`, `datetime_match.group` | none |
| `QuotaManager.reset_all` | 232 | `def reset_all(self) -> None` | `self._exhausted.clear`, `self._mark_time.clear`, `self._reset_time.clear`, `self._save_state` | none |
| `QuotaManager.reset_tier` | 244 | `def reset_tier(self, tier_name: str) -> None` | `self._tier_config.get_tier_models`, `self._save_state`, `self._quota_key`, `self._exhausted.pop`, `self._mark_time.pop`, `self._reset_time.pop` | none |
| `QuotaManager.reset_backend` | 259 | `def reset_backend(self, backend: str, model_name: str) -> None` | `self._quota_key`, `self._exhausted.pop`, `self._mark_time.pop`, `self._reset_time.pop`, `self._save_state` | none |
| `QuotaManager.get_exhausted_info` | 272 | `def get_exhausted_info(self, backend: str, model_name: str) -> dict[str, Any]` | `self._check_auto_reset`, `self._quota_key`, `self._mark_time.get`, `self._exhausted.get`, `self._reset_time.get`, `datetime.fromtimestamp.isoformat`, `datetime.fromtimestamp` | none |
| `QuotaManager.update_exhausted_reset_at` | 291 | `def update_exhausted_reset_at(self, backend: str, model_name: str, reset_at: Any) -> bool` | `self._quota_key`, `self._normalize_reset_at`, `self._save_state`, `self._exhausted.get` | none |
| `QuotaManager.get_all_exhausted` | 308 | `def get_all_exhausted(self) -> list[dict[str, Any]]` | `self._exhausted.items`, `self._mark_time.get`, `result.append`, `self._reset_time.get`, `datetime.fromtimestamp.isoformat`, `datetime.fromtimestamp` | none |
| `QuotaManager.is_quota_error` | 328 | `def is_quota_error(error_message: str) -> bool` | `error_message.lower`, `any` | none |
| `QuotaManager._check_auto_reset` | 338 | `def _check_auto_reset(self, backend: str, model_name: str) -> None` | `self._tier_config.get_quota_config`, `quota_cfg.get`, `self._quota_key`, `self._mark_time.get`, `datetime.fromtimestamp`, `datetime.now`, `isinstance`, `self._exhausted.pop`, `self._mark_time.pop`, `self._reset_time.pop` | none |

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

- 现有相关测试：`test/unit/stage_process/framework/behavior_cases/test_execution_identity.py`, `test/unit/stage_process/stages/system_testing_stage/behavior_cases/test_case_data_raw_text_validation.py`, `test/unit/tier/tier_runtime/behavior_cases/test_client_replay.py`, `test/unit/tier/tier_runtime/behavior_cases/test_provider_usage.py`, `test/unit/tier/tier_runtime/behavior_cases/test_mlexp_backend.py`, `test/unit/tier/tier_runtime/behavior_cases/test_server_jobs.py`, `test/unit/memory/retrieval_context/behavior_cases/test_judge_validator.py`, `test/unit/webui/dashboard/behavior_cases/test_dashboard_fast_paths.py`, `test/unit/common/stats/behavior_cases/test_llm_stats.py`, `test/subsystem/tier/case/tier-BASIS-001/run.py`, `test/subsystem/tier/case/tier-ENV-001/run.py`, `test/subsystem/tier/case/tier-CONFIG-001/run.py`；其余由Module测试索引覆盖。
- Contract Test覆盖public signature、authority、错误传播和禁止fallback。
- 迁移文件增加import graph检查，证明旧source path无production/test caller。

## 7. Current Difference

文件已位于目标路径。本ISD不批准额外行为变化；已知缺陷只能按Module Design和bug记录另行进入Test Design。
