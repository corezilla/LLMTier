# `src/dashboard/tier.html` ISD

Version: v1.8
Last Updated: 2026-09-08 13:21:23
Status: Draft / Approved Unified Dashboard Delta

target_file: `src/dashboard/tier.html`
target_state: `move`
source_file: `src/dashboard/tier.html`

所属边界：WebUI / Tier Dashboard Module。
上游：`docs/40_module_design/webui/tier_dashboard_module.md`。
接口追踪：provided_interfaces=`WEB-UI-001`, `WEB-UI-002`, `WEB-UI-003`, `WEB-UI-004`, `WEB-UI-005`；consumed_interfaces=`STP-DATA-001`, `TIR-HTTP-002`, `TIR-DATA-001`, `MEM-PY-003`。

## 1. 文件职责

本ISD以当前`src/dashboard/tier.html`为行为baseline，文件保留其单文件责任；除上游Module Design明确的Approved Delta外，不改变算法、selector、配置路径、重试或fallback。

## 2. 源码结构

- 当前行数：1804
- Stable DOM ids：`tierAccountsSection`, `tierErrorsSection`, `tierHomeLink`, `tierLoadConfigBtn`, `tierMainSection`, `tierRefreshBtn`, `tierReloadUsageBtn`, `tierRoot`, `tierSaveConfigBtn`, `tierStatsSection`, `tierSummarySection`
- Script dependencies：inline/none

## 3. 输入、输出与不变量

- 输入类型、默认值和返回annotation以第2节源码签名为准；无annotation的现有参数不得在实现阶段擅自收窄。
- `None`、空集合和异常语义保持当前调用方可观察行为，除非上游Approved Delta明确要求改变。
- public symbol名称和调用方向必须保持唯一；迁移不得保留旧路径re-export或兼容wrapper。
- 本文件不得获得所属Module之外的authority，也不得从日志、目录或display text推断业务真值。

## 4. State、IO与Side Effects

- Workspace/File IO
- Logging/Stats
- 非幂等写操作必须由所属Module现有single-writer/lock/attempt机制约束；unknown outcome不得盲目重试。
- timeout、retry、redaction和日志字段沿用当前owner Contract，不在本文件建立第二套policy。

## 5. Error、Recovery与禁止路径

- 保留第2节列出的typed exception和调用方错误映射；不得把malformed、missing、timeout或runner error转换为空成功。
- 不自动跨Stage rollback，不新增config、selector、routing、fallback或兼容分支。
- 迁移失败必须回滚整个文件/import变更，不允许新旧文件同时成为authority。

## 6. Tests

- 现有相关测试：`test/unit/stage_process/framework/behavior_cases/test_execution_identity.py`, `test/unit/stage_process/framework/behavior_cases/test_phase_runtime.py`, `test/unit/stage_process/stages/system_testing_stage/behavior_cases/test_execution_step_normalization.py`, `test/unit/stage_process/stages/system_testing_stage/behavior_cases/test_case_data_raw_text_validation.py`, `test/unit/tier/tier_runtime/behavior_cases/test_client_replay.py`, `test/unit/tier/tier_runtime/behavior_cases/test_provider_usage.py`, `test/unit/tier/tier_runtime/behavior_cases/test_mlexp_backend.py`, `test/unit/tier/tier_runtime/behavior_cases/test_server_jobs.py`, `test/unit/memory/conftest.py`, `test/unit/memory/indexing/behavior_cases/test_embeddings.py`, `test/unit/memory/retrieval_context/behavior_cases/test_judge_validator.py`, `test/unit/webui/dashboard/behavior_cases/test_dashboard_fast_paths.py`；其余由Module测试索引覆盖。
- Contract Test覆盖public signature、authority、错误传播和禁止fallback。
- 迁移文件增加import graph检查，证明旧source path无production/test caller。

## 7. Current Difference

实现已迁入`src/dashboard/tier.html`且旧文件已删除。页面只调用same-origin Dashboard API；8000/8765端口切换、独立Tier base URL和浏览器localhost fallback均不得恢复。

## 8. Approved Delta与Browser Contract

- 所有页面、stats、runtime、probe、config和management请求使用第1节页面所在的`window.location.origin`及Module Design 4.2/4.3登记的`/api/tier/*`、`/api/llm-stats`路径；页面不显示server地址输入框。
- Backend row identity固定为`tier:account:model`。可见label分别为API `account/model`、CLI `cli: account/model`、MLEXP `agent:account/model`；CLI prefix固定为literal `cli:`，不得暴露`opencode`、`codex`等实现Backend名；response缺失account时显示schema error，不自行猜测。
- `renderMainTable`、`renderAccountTable`和`renderLlmStatsPanel`只允许首屏、用户Refresh及明确management action成功后的显式结构刷新调用。
- timer驱动的stats、probe、usage和runtime refresh只能patch既有row的status、usage、counts、latency、running jobs和timestamp；禁止通过`innerHTML`、`updateSection`或上述render函数重建table/panel。
- config load/save、enable/disable、probe及concurrency mutation必须展示Tier返回的409 conflict、503 unavailable和field validation error；不得把失败映射为成功toast或空runtime。
- 标题下方`.tier-label-summary`只保存`{{SLINKY_VERSION}}`并由DashboardServer注入；inline JavaScript不得拼接、缓存或覆盖版本。
- System Test必须真实启动统一Dashboard listener，从另一主机浏览器访问，逐项验证Network/Console、管理操作、Backend identity、自动refresh DOM node稳定性以及不存在8765 listener/request。
