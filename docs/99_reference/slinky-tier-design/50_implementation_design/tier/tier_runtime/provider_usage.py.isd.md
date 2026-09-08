# `src/llm_tier/provider_usage.py` ISD

Version: v1.6
Last Updated: 2026-09-08 12:18:44
Status: Draft / Source-Verified Baseline

target_file: `src/llm_tier/provider_usage.py`
target_state: `existing`

所属边界：Tier / Tier Server Module。
上游：`docs/40_module_design/tier/tier_server_module.md`。
接口追踪：provided_interfaces=`TIR-PROC-001`, `TIR-DATA-001`；consumed_interfaces=`MLX-HTTP-001`, `MLX-HTTP-002`, `MLX-HTTP-003`, `MLX-HTTP-004`, `MLX-HTTP-005`, `MLX-HTTP-006`。

## 1. 文件职责

本ISD以当前`src/llm_tier/provider_usage.py`为行为baseline，目标文件保留其单文件责任；除上游Module Design明确的Approved Delta外，不改变算法、selector、配置路径、重试或fallback。

## 2. 源码结构

- 当前行数：2032
- Imports：`__future__:annotations`, `hashlib`, `hmac`, `json`, `re`, `ssl`, `threading`, `time`, `urllib.error`, `urllib.request`, `dataclasses:dataclass`, `datetime:UTC,datetime,timedelta,timezone`, `typing:Any`, `llm_tier.tier_model:TierModel`
- Module constants：`VOLC_SERVICE`, `VOLC_REGION`, `VOLC_USAGE_HOST`, `VOLC_USAGE_VERSION`, `MINIMAX_USAGE_URL`, `MINIMAX_CONSOLE_USAGE_URL`, `XFYUN_CODING_PLAN_LIST_URL`, `DEFAULT_USAGE_CACHE_SECONDS`

### 2.1 Classes / Functions / Methods

| Symbol | Line | Signature | Direct calls（最多10个） | Raises |
|---|---:|---|---|---|
| `ProviderUsageSnapshot` | 39 | `class ProviderUsageSnapshot` | none | none |
| `ProviderUsageSnapshot.to_dict` | 60 | `def to_dict(self) -> dict[str, Any]` | `self.usage_key.rsplit` | none |
| `ProviderUsageManager` | 85 | `class ProviderUsageManager` | none | none |
| `ProviderUsageManager.__init__` | 92 | `def __init__(self, cache_ttl_seconds: int = DEFAULT_USAGE_CACHE_SECONDS) -> None` | `max`, `threading.RLock`, `int` | none |
| `ProviderUsageManager.clear_cache` | 103 | `def clear_cache(self) -> None` | `self._cache.clear` | none |
| `ProviderUsageManager.usage_for_model` | 114 | `def usage_for_model(self, model: TierModel, *, force_refresh: bool = False) -> dict[str, Any]` | `provider_usage_key`, `time.time`, `self._load_usage.to_dict`, `dict`, `self._cache.get`, `ProviderUsageSnapshot.to_dict`, `self._load_usage`, `ProviderUsageSnapshot`, `resolved_quota_provider`, `now_iso` | none |
| `ProviderUsageManager.refresh_for_model` | 141 | `def refresh_for_model(self, model: TierModel) -> dict[str, Any]` | `self.usage_for_model` | none |
| `ProviderUsageManager._load_usage` | 150 | `def _load_usage(self, model: TierModel, usage_key: str) -> ProviderUsageSnapshot` | `resolved_quota_provider`, `_is_unlimited_quota`, `ProviderUsageSnapshot`, `_unlimited_usage_snapshot`, `self._load_volc_usage`, `self._load_xfyun_usage`, `self._load_minimax_usage`, `self._load_opencode_go_usage`, `now_iso` | none |
| `ProviderUsageManager._load_volc_usage` | 177 | `def _load_volc_usage(self, model: TierModel, usage_key: str) -> ProviderUsageSnapshot` | `_read_text_file`, `_volc_signed_json_request`, `_snapshot_from_volc_coding_plan_result`, `self._derived_usage`, `str.strip`, `isinstance`, `payload.get` | none |
| `ProviderUsageManager._load_minimax_usage` | 408 | `def _load_minimax_usage(self, model: TierModel, usage_key: str) -> ProviderUsageSnapshot` | `str.strip`, `_select_minimax_remains`, `_snapshot_from_minimax_remains`, `self._load_minimax_console_usage`, `self._derived_usage`, `urllib.request.Request`, `isinstance`, `payload.get`, `int`, `str` | none |
| `ProviderUsageManager._load_minimax_console_usage` | 487 | `def _load_minimax_console_usage(self, model: TierModel, usage_key: str, cookie: str) -> ProviderUsageSnapshot` | `str.strip`, `_select_minimax_remains`, `_snapshot_from_minimax_remains`, `urllib.request.Request`, `isinstance`, `payload.get`, `self._derived_usage`, `_snapshot_from_minimax_usage_summary`, `str`, `_urlopen` | none |
| `ProviderUsageManager._load_xfyun_usage` | 562 | `def _load_xfyun_usage(self, model: TierModel, usage_key: str) -> ProviderUsageSnapshot` | `str.strip`, `_snapshot_from_xfyun_coding_plans`, `self._derived_usage`, `urllib.request.Request`, `int`, `isinstance`, `payload.get`, `data.get`, `str`, `_urlopen` | none |
| `ProviderUsageManager._load_opencode_go_usage` | 641 | `def _load_opencode_go_usage(self, model: TierModel, usage_key: str) -> ProviderUsageSnapshot` | `str.strip`, `_snapshot_from_opencode_go_workspace_html`, `self._derived_usage`, `urllib.request.Request`, `str`, `_urlopen`, `response.read.decode`, `exc.read.decode`, `model.credentials.get`, `_read_text_file` | none |
| `ProviderUsageManager._derived_usage` | 707 | `def _derived_usage(self, model: TierModel, usage_key: str, *, provider: str, source: str, error: str) -> ProviderUsageSnapshot` | `derive_reset_at_from_quota`, `ProviderUsageSnapshot`, `_usage_window_entry`, `now_iso` | none |
| `resolved_quota_provider` | 737 | `def resolved_quota_provider(model: TierModel) -> str` | `str.strip.lower`, `provider.replace`, `quota_provider.replace`, `str.strip`, `model_key.startswith`, `model_name.startswith`, `str`, `model.quota.get` | none |
| `_is_unlimited_quota` | 775 | `def _is_unlimited_quota(quota: dict[str, Any]) -> bool` | `str.strip.lower`, `str.strip`, `str`, `get` | none |
| `_unlimited_usage_snapshot` | 786 | `def _unlimited_usage_snapshot(*, provider: str, usage_key: str) -> ProviderUsageSnapshot` | `ProviderUsageSnapshot`, `now_iso` | none |
| `provider_usage_key` | 802 | `def provider_usage_key(model: TierModel) -> str` | `resolved_quota_provider`, `str.strip`, `_provider_usage_account_seed`, `hashlib.sha256.hexdigest`, `str`, `hashlib.sha256`, `model.quota.get`, `account_seed.encode` | none |
| `_provider_usage_account_seed` | 816 | `def _provider_usage_account_seed(model: TierModel, provider: str) -> str` | `str.strip`, `str`, `model.credentials.get`, `model.quota.get`, `_read_api_key_file` | none |
| `derive_reset_at_from_quota` | 852 | `def derive_reset_at_from_quota(quota: dict[str, Any]) -> tuple[str, str]` | `str.strip.lower`, `quota.get`, `datetime.now`, `timezone`, `replace`, `now.replace`, `str.strip`, `timedelta`, `format_reset_time`, `max` | none |
| `now_iso` | 891 | `def now_iso() -> str` | `datetime.now.strftime`, `datetime.now` | none |
| `format_reset_time` | 901 | `def format_reset_time(value: datetime) -> str` | `value.astimezone.strftime`, `value.astimezone` | none |
| `_read_api_key_file` | 911 | `def _read_api_key_file(api_key_file: str) -> str` | `_read_text_file` | none |
| `_read_text_file` | 921 | `def _read_text_file(file_path: str) -> str` | `str.strip`, `Path.expanduser`, `path.is_absolute`, `path.read_text.strip`, `str`, `Path`, `Path.cwd`, `path.read_text` | none |
| `_cookie_value` | 942 | `def _cookie_value(cookie: str, name: str) -> str` | `str.split`, `item.strip`, `part.startswith`, `str`, `part.strip`, `len` | none |
| `_jwt_cookie_expired_at` | 957 | `def _jwt_cookie_expired_at(cookie: str, name: str) -> str` | `_cookie_value`, `token.count`, `json.loads`, `int`, `datetime.fromtimestamp.strftime`, `token.split`, `base64.urlsafe_b64decode.decode`, `data.get`, `time.time`, `datetime.fromtimestamp` | none |
| `_urlopen` | 981 | `def _urlopen(request: urllib.request.Request, *, timeout: int)` | `_https_context`, `urllib.request.urlopen` | none |
| `_https_context` | 992 | `def _https_context() -> ssl.SSLContext` | `ssl.create_default_context`, `certifi.where` | none |
| `_snapshot_from_xfyun_coding_plans` | 1007 | `def _snapshot_from_xfyun_coding_plans(*, model: TierModel, usage_key: str, rows: list[Any]) -> ProviderUsageSnapshot \| None` | `str.strip`, `_select_primary_usage_total`, `max`, `round`, `derive_reset_at_from_quota`, `ProviderUsageSnapshot`, `_float_value`, `isinstance`, `str`, `row.get` | none |
| `_select_primary_usage_total` | 1091 | `def _select_primary_usage_total(totals: dict[str, dict[str, float]]) -> str` | `_float_value`, `totals.get`, `values.get` | none |
| `_snapshot_from_volc_coding_plan_result` | 986 | `def _snapshot_from_volc_coding_plan_result(*, usage_key: str, result: dict[str, Any]) -> ProviderUsageSnapshot \| None` | `_snapshot_from_volc_quota_usage` | none |
| `_snapshot_from_volc_quota_usage` | 1265 | `def _snapshot_from_volc_quota_usage(*, usage_key: str, result: dict[str, Any]) -> ProviderUsageSnapshot \| None` | `result.get`, `_select_primary_percent_window`, `ProviderUsageSnapshot`, `isinstance`, `_normalize_usage_window_name`, `_float_value`, `_reset_at_from_volc_seconds`, `windows.append`, `str`, `item.get` | none |
| `_select_primary_percent_window` | 1314 | `def _select_primary_percent_window(windows: list[dict[str, Any]]) -> dict[str, Any]` | `str`, `_float_value`, `item.get` | none |
| `_select_minimax_remains` | 1456 | `def _select_minimax_remains(model: TierModel, remains: list[Any]) -> dict[str, Any] \| None` | `str.strip.lower`, `str.strip`, `isinstance`, `str`, `item.get` | none |
| `_snapshot_from_minimax_remains` | 1476 | `def _snapshot_from_minimax_remains(*, model: TierModel, usage_key: str, item: dict[str, Any]) -> ProviderUsageSnapshot` | `_float_value`, `_used_percent_from_minimax_remaining`, `_reset_at_from_epoch_ms`, `derive_reset_at_from_quota`, `_select_primary_percent_window`, `str`, `ProviderUsageSnapshot`, `item.get`, `_usage_window_entry`, `primary.get` | none |
| `_used_percent_from_minimax_remaining` | 1531 | `def _used_percent_from_minimax_remaining(value: Any) -> float \| None` | `_float_value`, `round`, `max`, `str.strip`, `min`, `str` | none |
| `_snapshot_from_minimax_usage_summary` | 1546 | `def _snapshot_from_minimax_usage_summary(*, model: TierModel, usage_key: str, payload: dict[str, Any]) -> ProviderUsageSnapshot \| None` | `_compact_number_or_none`, `_latest_minimax_daily_total`, `derive_reset_at_from_quota`, `ProviderUsageSnapshot`, `payload.get`, `isinstance`, `_usage_window_entry`, `windows.append`, `sum`, `now_iso` | none |
| `_latest_minimax_daily_total` | 1593 | `def _latest_minimax_daily_total(items: list[Any]) -> float \| None` | `reversed`, `_compact_number_or_none`, `isinstance`, `item.get` | none |
| `_snapshot_from_opencode_go_workspace_html` | 1609 | `def _snapshot_from_opencode_go_workspace_html(*, usage_key: str, html: str) -> ProviderUsageSnapshot \| None` | `re.compile`, `pattern.finditer`, `_select_primary_percent_window`, `ProviderUsageSnapshot`, `match.group`, `get`, `round`, `_reset_at_from_delta_seconds`, `primary.get`, `str` | none |
| `_compact_count_value` | 1670 | `def _compact_count_value(value: Any) -> float` | `isinstance`, `str.strip.replace`, `text.upper`, `get`, `float`, `str.strip`, `str` | none |
| `_normalize_usage_window_name` | 1789 | `def _normalize_usage_window_name(name: str) -> str` | `str.strip.lower`, `mapping.get`, `str.strip`, `str` | none |
| `_usage_window_entry` | 1815 | `def _usage_window_entry(name: str, used: float \| None, quota: float \| None, reset_at: str, *, percent: float \| None = None) -> dict[str, Any]` | `_normalize_usage_window_name`, `max`, `round` | none |
| `_reset_at_from_epoch_ms` | 1848 | `def _reset_at_from_epoch_ms(value: Any) -> str` | `_int_value`, `datetime.fromtimestamp.astimezone.strftime`, `datetime.fromtimestamp.astimezone`, `datetime.fromtimestamp` | none |
| `_reset_at_from_volc_seconds` | 1861 | `def _reset_at_from_volc_seconds(value: Any) -> str` | `_int_value`, `datetime.fromtimestamp.astimezone.strftime`, `datetime.fromtimestamp.astimezone`, `datetime.fromtimestamp` | none |
| `_reset_at_from_delta_seconds` | 1874 | `def _reset_at_from_delta_seconds(value: Any) -> str` | `_int_value`, `astimezone.strftime`, `astimezone`, `datetime.now`, `timedelta` | none |
| `_volc_signed_json_request` | 1887 | `def _volc_signed_json_request(*, action: str, access_key: str, secret_key: str) -> dict[str, Any]` | `datetime.now`, `now.strftime`, `hashlib.sha256.hexdigest`, `join`, `_volc_signing_key`, `hmac.new.hexdigest`, `urllib.request.Request`, `hashlib.sha256`, `hmac.new`, `_urlopen` | `RuntimeError` |
| `_volc_signing_key` | 1952 | `def _volc_signing_key(secret_key: str, date: str) -> bytes` | `hmac.new.digest`, `hmac.new`, `secret_key.encode`, `date.encode`, `VOLC_REGION.encode`, `VOLC_SERVICE.encode` | none |
| `_float_value` | 1965 | `def _float_value(value: Any) -> float` | `float` | none |
| `_float_or_none` | 1978 | `def _float_or_none(value: Any) -> float \| None` | `float` | none |
| `_compact_number_or_none` | 1993 | `def _compact_number_or_none(value: Any) -> float \| None` | `_compact_number_value`, `str.strip`, `str` | none |
| `_compact_number_value` | 2008 | `def _compact_number_value(value: Any) -> float` | `isinstance`, `str.strip.replace`, `raw.upper`, `float`, `ValueError`, `str.strip`, `str` | `ValueError` |
| `_int_value` | 2028 | `def _int_value(value: Any) -> int` | `int` | none |

### 2.2 逐Callable Contract

第2.1节每个callable的参数名、顺序、positional/keyword规则、default和annotation均为迁移Contract；不得增加吞错kwargs、隐式类型转换或兼容alias。返回值保持当前源码annotation及所有分支的可观察类型；表中Raises和源码显式传播的dependency exception必须保留，不能转换为空成功。跨文件调用只能使用所属Module登记的public symbol，underscore symbol只允许本文件内部使用。各callable的IO、state mutation、network/process、logging和并发side effect按第4节及其Direct calls执行，Test Design必须为每个public callable至少建立正常、边界、错误和side-effect evidence。

## 3. 输入、输出与不变量

- 输入类型、默认值和返回annotation以第2节源码签名为准；无annotation的现有参数不得在实现阶段擅自收窄。
- `None`、空集合和异常语义保持当前调用方可观察行为，除非上游Approved Delta明确要求改变。
- public symbol名称和调用方向必须保持唯一；迁移不得保留旧路径re-export或兼容wrapper。
- 本文件不得获得所属Module之外的authority，也不得从日志、目录或display text推断业务真值。
- 火山 Coding Plan 用量只接受 `usage_access_key_id/usage_secret_access_key` 或对应 file-backed 配置；模型调用 API Key、Console cookie、CSRF token 和 web-id 均不得作为该接口凭据。
- 火山请求必须签名调用 `https://ark.cn-beijing.volcengineapi.com/?Action=GetCodingPlanUsage&Version=2024-01-01`；不得 fallback 到 Console route、`/api/coding/v1/quotas` 或 Agent Plan `GetAFPUsage`。
- `QuotaUsage[].Level=session/weekly/monthly` 必须归一为 `5hour/weekly/monthly`，`Percent` 与 `ResetTimestamp` 分别作为 percent-only window 和 reset authority。

## 4. State、IO与Side Effects

- Workspace/File IO
- JSON/SQLite state
- Network/HTTP
- Concurrency
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

文件已位于目标路径。Approved Delta 是将火山用量查询从易过期的 Console cookie 多路径收口为唯一 AK/SK 签名 `GetCodingPlanUsage` 路径；其他 provider、缓存、Dashboard runtime Contract 和错误传播保持不变。
