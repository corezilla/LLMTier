# `src/llm_tier/tier_core.py` ISD

Version: v1.8
Last Updated: 2026-09-08 12:18:44
Status: Implemented / Source-Verified

target_file: `src/llm_tier/tier_core.py`
target_state: `existing`

所属边界：Tier / Tier Client Module。
上游：`docs/40_module_design/tier/tier_client_module.md`。
接口追踪：provided_interfaces=`TIR-HTTP-001`；consumed_interfaces=`TIR-HTTP-002`。

## 1. 文件职责

本ISD以当前`src/llm_tier/tier_core.py`为行为baseline，目标文件保留其单文件责任；除上游Module Design明确的Approved Delta外，不改变算法、selector、配置路径、重试或fallback。

## 2. 源码结构

- 当前行数：112
- Imports：`__future__:annotations`, `typing:Any`, `llm_tier.client:TierClient`, `llm_tier.tier_model:TierCallRequest,TierCallResult,TierStatsQuery,TierStatsRow`
- Module constants：`_TIER_INSTANCE`

### 2.1 Classes / Functions / Methods

| Symbol | Line | Signature | Direct calls（最多10个） | Raises |
|---|---:|---|---|---|
| `get_tier` | 15 | `def get_tier() -> TierCore` | `TierCore` | none |
| `TierCore` | 25 | `class TierCore` | none | none |
| `TierCore.__init__` | 29 | `def __init__(self, client: TierClient \| None = None) -> None` | `TierClient` | none |
| `TierCore.is_client_mode` | 36 | `def is_client_mode(self) -> bool` | none | none |
| `TierCore.call` | 42 | `def call(self, req: TierCallRequest) -> TierCallResult` | `self._client.call` | none |
| `TierCore.call_async` | 48 | `def call_async(self, req: TierCallRequest) -> str` | `self._client.call_async` | none |
| `TierCore.get_result` | 54 | `def get_result(self, job_id: str) -> TierCallResult \| None` | `self._client.get_result` | none |
| `TierCore.reload_config` | 60 | `def reload_config(self) -> bool` | `self._client.reload_config`, `bool`, `response.get` | none |
| `TierCore.get_tier_info` | 67 | `def get_tier_info(self, tier_name: str) -> dict[str, Any]` | `self._client.get_stats` | none |
| `TierCore.reset_exhausted` | 73 | `def reset_exhausted(self, tier_name: str = '') -> None` | `self._client.reset_exhausted` | none |
| `TierCore.get_stats` | 79 | `def get_stats(self, query: TierStatsQuery \| None = None) -> list[TierStatsRow]` | `TierStatsQuery`, `self._client.get_stats`, `TierStatsRow` | none |
| `TierCore.get_summary` | 98 | `def get_summary(self) -> dict[str, Any]` | `self._client.get_stats`, `dict` | none |
| `TierCore.is_enabled` | 107 | `def is_enabled(self) -> bool` | `self._client.get_health`, `bool`, `health.get` | none |

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
- LLM/Tier
- Logging/Stats
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

文件已位于目标路径并完成HTTP client-only facade迁移。`_TierEmbedded`、Router、Backend registry、local stats/job和`settings_path`分支均已删除；后续变更只能扩展现有Tier HTTP Contract，不得恢复embedded或引入第二transport。

## 8. 已实现机制：HTTP Client-only Facade

`TierCore`仅作为现有调用方的HTTP client facade，封装`TierClient`和file-mode result materialization。完整删除`_TierEmbedded`、Backend registry、Router、QuotaManager、StatsCollector和本地call/job/stats实现；删除`settings_path`与`is_client_mode`分支，不保留embedded fallback。

`get_tier()`返回无参client facade；`call/call_async/get_result/reload_config/get_stats/get_summary/reset_exhausted`委托Tier Service。`is_enabled`读取Service health/config结果，Service不可达不得解释为embedded enabled。

Tier HTTP不可达时必须返回或抛明确transport error；file-mode error sidecar保留现有Contract，但不得创建成功response、本地job、本地stats或调用Backend。测试必须证明HTTP不可达时Backend registry调用数为0、stats文件不创建，并通过源码审计确认`_TierEmbedded`不存在。
