# `src/llm_tier/__main__.py` ISD

Version: v1.8
Last Updated: 2026-09-08 12:18:44
Status: Draft / HTTP Entry Retained

target_file: `src/llm_tier/__main__.py`
target_state: `existing`

所属边界：Tier / Tier CLI Module。
上游：`docs/40_module_design/tier/tier_cli_module.md`。
接口追踪：provided_interfaces=无独立业务接口；consumed_interfaces=`TIR-HTTP-001`, `TIR-HTTP-002`。

## 1. 文件职责

本ISD以当前`src/llm_tier/__main__.py`为启动参数baseline，保留独立HTTP `TierServer`入口。Tier只允许loopback监听；Browser统一经Dashboard访问。

## 2. 源码结构

- 当前行数：56
- Imports：`__future__:annotations`, `argparse`, `sys`
- Module constants：none

### 2.1 Classes / Functions / Methods

| Symbol | Line | Signature | Direct calls（最多10个） | Raises |
|---|---:|---|---|---|
| `main` | 21 | `def main() -> int` | `argparse.ArgumentParser`, `parser.add_argument`, `parser.parse_args`, `TierServer`, `print`, `server.start`, `server.stop` | none |

### 2.2 逐Callable Contract

第2.1节每个callable的参数名、顺序、positional/keyword规则、default和annotation均为迁移Contract；不得增加吞错kwargs、隐式类型转换或兼容alias。返回值保持当前源码annotation及所有分支的可观察类型；表中Raises和源码显式传播的dependency exception必须保留，不能转换为空成功。跨文件调用只能使用所属Module登记的public symbol，underscore symbol只允许本文件内部使用。各callable的IO、state mutation、network/process、logging和并发side effect按第4节及其Direct calls执行，Test Design必须为每个public callable至少建立正常、边界、错误和side-effect evidence。

## 3. 输入、输出与不变量

- 输入类型、默认值和返回annotation以第2节源码签名为准；无annotation的现有参数不得在实现阶段擅自收窄。
- `None`、空集合和异常语义保持当前调用方可观察行为，除非上游Approved Delta明确要求改变。
- public symbol名称和调用方向必须保持唯一；迁移不得保留旧路径re-export或兼容wrapper。
- 本文件不得获得所属Module之外的authority，也不得从日志、目录或display text推断业务真值。

## 4. State、IO与Side Effects

- 校验loopback host/port，启动/停止唯一`TierServer`进程内实例，向stderr写sanitized启动信息。
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

文件已位于目标路径并使用正确HTTP机制；需要补充非loopback host拒绝和明确shutdown错误处理。

## 8. Approved Delta：唯一Tier HTTP启动入口

目标CLI只接受：

| 参数 | 类型/默认 | 约束 |
|---|---|---|
| `--host` | `str`；默认`127.0.0.1` | 只接受`127.0.0.1`、`localhost`或`::1`；拒绝wildcard/LAN地址 |
| `--port` | `int`；默认`8765` | 必须为1..65535；测试可直接构造`TierServer(port=0)` |
| `--settings` | `str`；可空 | 非空时必须是可读settings JSON；配置校验失败不得监听端口 |

`main()`按以下唯一顺序执行：parse/validate → `TierServer(host, port, settings_path)` → `server.start(blocking=True)`。SIGINT/SIGTERM调用一次`server.stop()`；任一步失败返回非零exit并关闭本次创建的listener。Tier入口不提供Dashboard static page。

Client连接地址继续使用`TIER_SERVER_URL`，不在settings JSON建立第二个server URL字段。Contract Test覆盖CLI参数、非loopback拒绝、端口占用、启动中断、shutdown和Tier page route不存在。
