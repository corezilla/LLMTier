# `src/llm_tier/tier_config.py` ISD

Version: v1.5
Last Updated: 2026-09-08 12:18:44
Status: Draft / Source-Verified Baseline

target_file: `src/llm_tier/tier_config.py`
target_state: `existing`

所属边界：Tier / Tier Server Module。
上游：`docs/40_module_design/tier/tier_server_module.md`。
接口追踪：provided_interfaces=`TIR-DATA-001`；consumed_interfaces=无。

## 1. 文件职责

本ISD以当前`src/llm_tier/tier_config.py`为行为baseline，目标文件保留其单文件责任；除上游Module Design明确的Approved Delta外，不改变算法、selector、配置路径、重试或fallback。

## 2. 源码结构

- 当前行数：515
- Imports：`__future__:annotations`, `json`, `os`, `pathlib:Path`, `typing:Any`, `llm_tier.tier_model:TierAccount,TierModel`
- Module constants：none

### 2.1 Classes / Functions / Methods

| Symbol | Line | Signature | Direct calls（最多10个） | Raises |
|---|---:|---|---|---|
| `TierConfig` | 17 | `class TierConfig` | none | none |
| `TierConfig.__init__` | 24 | `def __init__(self, settings_path: str \| Path \| None = None) -> None` | `Path.resolve`, `os.environ.get.strip`, `self._settings_path.is_file`, `Path.cwd`, `default_path.is_file`, `json.loads`, `Path`, `os.environ.get`, `Path.expanduser`, `candidates.append` | none |
| `TierConfig.get_tier_models` | 65 | `def get_tier_models(self, tier_name: str) -> list[TierModel]` | `self._config.get`, `tiers.get`, `str.strip`, `_backend_identity_account_model`, `backend_name.split.strip`, `credentials.update`, `m.get`, `quota.update`, `models.append`, `int` | none |
| `TierConfig.get_account` | 190 | `def get_account(self, account_id: str) -> TierAccount \| None` | `str.strip`, `self._config.get`, `raw_accounts.get`, `raw.get`, `TierAccount`, `isinstance`, `dict`, `str`, `max`, `int` | none |
| `TierConfig.get_accounts` | 249 | `def get_accounts(self) -> list[TierAccount]` | `self._config.get`, `isinstance`, `self.get_account`, `str` | none |
| `TierConfig.find_backend_model` | 265 | `def find_backend_model(self, backend: str, model_name: str = '', model_key: str = '', provider: str = '', account: str = '') -> TierModel \| None` | `str.strip`, `self._config.get`, `self.get_tier_models`, `str` | none |
| `TierConfig.get_tier_for_role` | 304 | `def get_tier_for_role(self, role_name: str) -> str` | `self._config.get`, `str`, `role_map.get` | none |
| `TierConfig.get_provider_profile_models` | 314 | `def get_provider_profile_models(self, provider: str) -> list[dict[str, Any]]` | `str.strip`, `self._config.get`, `isinstance`, `profiles.get`, `profile.get`, `models.append`, `str`, `int`, `raw_model.get` | none |
| `TierConfig.get_breaker_config` | 346 | `def get_breaker_config(self) -> dict[str, int]` | `self._config.get`, `int`, `isinstance`, `tier_cfg.get`, `max`, `breaker.get` | none |
| `TierConfig.get_account_concurrency` | 362 | `def get_account_concurrency(self, account_id: str) -> dict[str, Any]` | `self.get_account` | none |
| `TierConfig.get_backend_capabilities` | 379 | `def get_backend_capabilities(self, backend: str, model_name: str = '', model_key: str = '', account: str = '') -> dict[str, Any]` | `self.find_backend_model` | none |
| `TierConfig.get_quota_config` | 406 | `def get_quota_config(self, backend: str) -> dict[str, Any] \| None` | `self.find_backend_model`, `dict` | none |
| `TierConfig.get_backend_credentials` | 416 | `def get_backend_credentials(self, backend: str, provider: str = '', model_name: str = '', model_key: str = '', account: str = '') -> dict[str, Any]` | `self.find_backend_model`, `dict` | none |
| `TierConfig.persist` | 439 | `def persist(self) -> bool` | `self._settings_path.parent.mkdir`, `self._settings_path.write_text`, `str`, `json.dumps` | none |
| `TierConfig.reload` | 461 | `def reload(self) -> bool` | `json.loads`, `self._settings_path.is_file`, `self._settings_path.read_text` | none |
| `TierConfig.is_enabled` | 476 | `def is_enabled(self) -> bool` | `self._config.get`, `bool`, `tier_cfg.get` | none |
| `_usage_account_from_model_selector` | 487 | `def _usage_account_from_model_selector(raw_model: dict[str, Any]) -> str` | `str.strip.lower`, `_backend_identity_account_model`, `str.strip.upper`, `str.strip`, `selector.split`, `account.strip`, `str`, `raw_model.get` | none |
| `_backend_identity_account_model` | 508 | `def _backend_identity_account_model(backend: str) -> tuple[str, str]` | `str.strip`, `normalized.split`, `account.strip`, `model.strip`, `str` | none |

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
