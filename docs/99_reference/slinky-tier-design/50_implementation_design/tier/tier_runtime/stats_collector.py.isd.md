# `src/llm_tier/stats_collector.py` ISD

Version: v1.5
Last Updated: 2026-09-08 12:18:44
Status: Draft / Source-Verified Baseline

target_file: `src/llm_tier/stats_collector.py`
target_state: `existing`

所属边界：Tier / Tier Server Module。
上游：`docs/40_module_design/tier/tier_server_module.md`。
接口追踪：provided_interfaces=`TIR-DATA-001`；consumed_interfaces=无。

## 1. 文件职责

本ISD以当前`src/llm_tier/stats_collector.py`为行为baseline，目标文件保留其单文件责任；除上游Module Design明确的Approved Delta外，不改变算法、selector、配置路径、重试或fallback。

## 2. 源码结构

- 当前行数：1249
- Imports：`__future__:annotations`, `calendar`, `json`, `math`, `time`, `contextlib:closing`, `dataclasses:replace`, `pathlib:Path`, `typing:Any`, `llm_tier.tier_model:TierStatsQuery,TierStatsRow`, `utils.sqlite:load_sqlite_module,sqlite_operation_lock`
- Module constants：`LLM_STATS_SQLITE_BUSY_TIMEOUT_MS`

### 2.1 Classes / Functions / Methods

| Symbol | Line | Signature | Direct calls（最多10个） | Raises |
|---|---:|---|---|---|
| `_stats_group_key` | 26 | `def _stats_group_key(*, row: sqlite3.Row, group_by: str) -> tuple[str, ...]` | `str` | none |
| `_ensure_wal_mode` | 48 | `def _ensure_wal_mode(conn: sqlite3.Connection) -> None` | `conn.execute` | none |
| `StatsCollector` | 59 | `class StatsCollector` | none | none |
| `StatsCollector.__init__` | 66 | `def __init__(self, stats_dir: str) -> None` | `Path`, `self._stats_dir.mkdir`, `sqlite_operation_lock`, `self._init_db` | none |
| `StatsCollector.write` | 79 | `def write(self, event: dict[str, Any]) -> None` | `self._normalize_event`, `closing`, `self._insert_event`, `conn.commit`, `self._connect` | none |
| `StatsCollector.get_stats` | 95 | `def get_stats(self, query: TierStatsQuery) -> list[TierStatsRow]` | `self.get_events`, `self._aggregate` | none |
| `StatsCollector.get_grouped_stats` | 107 | `def get_grouped_stats(self, query: TierStatsQuery, *, group_by: str) -> list[dict[str, Any]]` | `str.strip.lower`, `self._load_completed_grouped_summary`, `self._get_grouped_stats_from_events`, `self._merge_task_group_materialized_and_live`, `str.strip`, `str` | none |
| `StatsCollector._get_grouped_stats_from_events` | 127 | `def _get_grouped_stats_from_events(self, query: TierStatsQuery, *, group_by: str) -> list[dict[str, Any]]` | `str.strip.lower`, `self._where_clause`, `clauses.extend`, `str.strip`, `join`, `closing`, `conn.execute.fetchall`, `str`, `self._connect`, `groups.setdefault.append` | none |
| `StatsCollector._load_completed_grouped_summary` | 160 | `def _load_completed_grouped_summary(self, query: TierStatsQuery, *, group_by: str) -> list[dict[str, Any]]` | `self._started_at_text_from_query`, `closing`, `self._connect`, `conn.execute.fetchone`, `self._summary_payload_rows`, `self._load_completed_task_group_summaries`, `conn.execute` | none |
| `StatsCollector._merge_task_group_materialized_and_live` | 197 | `def _merge_task_group_materialized_and_live(self, *, query: TierStatsQuery, materialized: list[dict[str, Any]]) -> list[dict[str, Any]]` | `self._get_grouped_stats_from_events`, `list`, `sorted`, `str.strip`, `merged.append`, `str`, `row.get` | none |
| `StatsCollector.get_events` | 223 | `def get_events(self, query: TierStatsQuery) -> list[dict[str, Any]]` | `self._where_clause`, `values.append`, `int`, `events.append`, `join`, `self._event_from_row`, `closing`, `conn.execute.fetchall`, `self._connect`, `conn.execute` | none |
| `StatsCollector.get_summary` | 253 | `def get_summary(self, query: TierStatsQuery \| None = None) -> dict[str, Any]` | `max`, `self.get_stats`, `sum`, `sorted`, `replace`, `TierStatsQuery`, `int` | none |
| `StatsCollector._connect` | 274 | `def _connect(self) -> sqlite3.Connection` | `sqlite3.connect`, `conn.execute` | none |
| `StatsCollector._init_db` | 286 | `def _init_db(self) -> None` | `closing`, `_ensure_wal_mode`, `conn.execute`, `self._ensure_llm_call_columns`, `conn.executescript`, `conn.commit`, `self._connect` | none |
| `StatsCollector._ensure_llm_call_columns` | 377 | `def _ensure_llm_call_columns(self, conn: sqlite3.Connection) -> None` | `migrations.items`, `str`, `conn.execute.fetchall`, `conn.execute` | none |
| `StatsCollector.sync_completed_summary` | 399 | `def sync_completed_summary(self, *, scope: str, project: str, stage_name: str, phase_name: str = '', task_id: str = '', started_at: str = '') -> None` | `str.strip`, `TierStatsQuery`, `self._get_grouped_stats_from_events`, `str`, `self._parse_time_to_epoch`, `self._empty_group_summary`, `closing`, `conn.commit`, `self._connect`, `conn.execute` | none |
| `StatsCollector.clear_completed_summary` | 488 | `def clear_completed_summary(self, *, scope: str, project: str, stage_name: str, phase_name: str = '', task_id: str = '') -> None` | `str.strip`, `str`, `closing`, `conn.commit`, `self._connect`, `conn.execute` | none |
| `StatsCollector._summary_payload_rows` | 529 | `def _summary_payload_rows(self, rows: list[sqlite3.Row]) -> list[dict[str, Any]]` | `isinstance`, `json.loads`, `payloads.append`, `str` | none |
| `StatsCollector._load_completed_task_group_summaries` | 548 | `def _load_completed_task_group_summaries(self, *, conn: sqlite3.Connection, query: TierStatsQuery) -> list[dict[str, Any]]` | `sorted`, `str`, `self._started_at_text_from_query`, `started_at_map.items`, `conn.execute.fetchone`, `payloads.extend`, `dict.items`, `self._epoch_to_started_at_text`, `self._summary_payload_rows`, `str.strip` | none |
| `StatsCollector._empty_group_summary` | 582 | `def _empty_group_summary(self, *, query: TierStatsQuery, group_by: str) -> dict[str, Any]` | `query.task_id.split` | none |
| `StatsCollector._started_at_text_from_query` | 649 | `def _started_at_text_from_query(self, query: TierStatsQuery) -> str` | `str.strip`, `str`, `getattr` | none |
| `StatsCollector._parse_time_to_epoch` | 658 | `def _parse_time_to_epoch(self, value: Any) -> float` | `str.strip`, `float`, `time.strptime`, `str`, `calendar.timegm`, `text.replace.split`, `text.replace` | none |
| `StatsCollector._epoch_to_started_at_text` | 678 | `def _epoch_to_started_at_text(self, epoch: float) -> str` | `self._iso_timestamp`, `float` | none |
| `StatsCollector._normalize_event` | 687 | `def _normalize_event(self, event: dict[str, Any]) -> dict[str, Any]` | `dict`, `self._int_value`, `self._event_epoch`, `str`, `task_id.split`, `raw_event.get`, `isinstance`, `self._is_aggregate_call_event`, `join`, `bool` | none |
| `StatsCollector._insert_event` | 758 | `def _insert_event(self, conn: sqlite3.Connection, event: dict[str, Any]) -> None` | `conn.execute`, `json.dumps` | none |
| `StatsCollector._where_clause` | 809 | `def _where_clause(self, query: TierStatsQuery) -> tuple[list[str], list[Any]]` | `mapping.items`, `str.strip`, `str`, `clauses.append`, `values.append`, `float`, `sorted`, `dict.items`, `task_started_at_epochs.items`, `task_clauses.append` | none |
| `StatsCollector._escape_like` | 856 | `def _escape_like(self, value: str) -> str` | `str.replace.replace.replace`, `str.replace.replace`, `str.replace`, `str` | none |
| `StatsCollector._aggregate_group_rows` | 865 | `def _aggregate_group_rows(self, *, group_by: str, key: tuple[str, ...], rows: list[sqlite3.Row]) -> dict[str, Any]` | `sum`, `self._int_value`, `self._float_value`, `str`, `self._avg_positive`, `self._percentile_positive`, `len`, `any`, `self._clear_non_group_identity_fields`, `max` | none |
| `StatsCollector._clear_non_group_identity_fields` | 987 | `def _clear_non_group_identity_fields(self, result: dict[str, Any], *, keep: set[str]) -> None` | none | none |
| `StatsCollector._event_from_row` | 1009 | `def _event_from_row(self, row: sqlite3.Row) -> dict[str, Any]` | `event.update`, `json.loads`, `str`, `bool` | none |
| `StatsCollector._aggregate` | 1055 | `def _aggregate(self, events: list[dict[str, Any]]) -> list[TierStatsRow]` | `groups.items`, `groups.setdefault.append`, `str`, `sum`, `rows.append`, `self._is_aggregate_call_event`, `group.get`, `self._int_value`, `self._float_value`, `TierStatsRow` | none |
| `StatsCollector._is_aggregate_call_event` | 1150 | `def _is_aggregate_call_event(self, event: dict[str, Any]) -> bool` | `str.strip`, `self._int_value`, `str`, `event.get`, `error_message.startswith` | none |
| `StatsCollector._event_epoch` | 1172 | `def _event_epoch(self, event: dict[str, Any]) -> float` | `self._float_value`, `str`, `time.time`, `event.get`, `time.strptime`, `float`, `calendar.timegm`, `ts.replace.split`, `ts.replace` | none |
| `StatsCollector._iso_timestamp` | 1191 | `def _iso_timestamp(self, ts_epoch: float) -> str` | `time.strftime`, `time.gmtime` | none |
| `StatsCollector._int_value` | 1200 | `def _int_value(self, value: Any) -> int` | `int` | none |
| `StatsCollector._float_value` | 1212 | `def _float_value(self, value: Any) -> float` | `float` | none |
| `StatsCollector._avg_positive` | 1224 | `def _avg_positive(self, values: list[int] \| list[float]) -> float` | `round`, `float`, `sum`, `len` | none |
| `StatsCollector._percentile_positive` | 1236 | `def _percentile_positive(self, values: list[int] \| list[float], percentile: float) -> float` | `sorted`, `math.floor`, `math.ceil`, `round`, `len`, `float` | none |

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

文件已位于目标路径。本ISD不批准额外行为变化；已知缺陷只能按Module Design和bug记录另行进入Test Design。
