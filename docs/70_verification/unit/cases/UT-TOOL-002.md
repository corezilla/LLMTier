<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-TOOL-002 — 环境工具：readiness 聚合、复位阶梯与部署命令构造

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-TOOL-002` |
| Document Version | `0.1.0-draft.3` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-10-01` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.unit-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/unit/cases/UT-TOOL-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-TOOL-002`）；责任摘要、分类与优先级以 [单元测试方案 §6](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：本项目**验证工具（verification tooling）**，非 8 个软件模块（`M001-M008`）之一：被测为 `tools/check_env.py`（系统计划 §3 Go/No-Go 的可执行实现）、`tools/reset_env.py`（系统计划 §6 复位阶梯可执行实现）、`tools/deploy.py`（`m5air-deploy-guide.md` 部署脚本化）。该 Case 不归属任何模块设计 §14 VRC（工具不实现产品行为），作为方案 §6 的独立「TOOL 家族」登记，**不改变** 33 个模块 VRC 的分母。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的工具切片 `TOOL`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-TOOL-002` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-TOOL-002` / M-TOOL `tools/check_env.py`＋`tools/reset_env.py`＋`tools/deploy.py`（系统计划 §3 Go/No-Go、§6 环境操作）/ none（工具，无模块 VRC）/ normal / P1（[方案清单 §6](../llmtier-unit-test-scheme.md)）。
- **测试方法（§2.1 方法表行）**：等价类划分 + 契约字段比对（工具纯逻辑）（主要手段：直接调用 + 冻结向量 + 替身注入）
- 要测什么（责任展开）：
  - `tools/check_env.py`：A/B 检查聚合（`summarize` 计数与 `all_pass`）、`--class a|b|all` 选择、检查异常不崩溃、exit 码（0 全过 / 2 任一失败）、`detect_lan_ip` override（TS-003）。
  - `tools/reset_env.py`：复位阶梯顺序（backup→restore/rebuild→clear-injections→reset-ledger→kill-leftovers→recheck）、`--dry-run` 不触网/不改、`--yes` 非交互 guard、sqlite backup API 备份、`--restore`/`--rebuild` 互斥与效果、注入清空 `PATCH {"items":[]}`＋断言空、`DELETE /v1/usage`、遗留测试进程解析。
  - `tools/deploy.py`：制品 pin（`git rev-parse HEAD`、openapi version、`schema_version`）、rsync/ssh/lsof/kill/start/rollback 命令构造、start 命令含 Python 3.14＋`PYTHONPATH=src -m http_api` 且**不泄漏 secret 值**、`--dry-run` 不执行远程命令。
- 明确不测什么 / 失败含义：不测：真实 m5air 网络/ssh、真实 OMLX、真实 DB 迁移语义。失败含义＝前检/复位/部署的**纯逻辑**（聚合、顺序、命令构造、退出码）错误，导致 Go/No-Go 误判、复位跳过步骤或部署命令错误。

## 2. 被测入口与前置

- 被测入口声明与位置：

```text
check_env: run_checks(kind, cfg) -> list[CheckResult]; summarize(results) -> dict;
           detect_lan_ip(override) -> str | None; build_config(argparse.Namespace) -> EnvConfig;
           main(argv) -> int
reset_env: reset_plan() -> list[callable]; step_backup/step_restore_or_rebuild/
           step_clear_injections/step_reset_ledger/step_kill_leftovers/step_recheck(cfg) -> StepResult;
           backup_database(db, dest) -> None; default_backup_path(db, now) -> Path;
           find_leftover_pids(ps, markers, self_pid) -> list[int]; summarize(results) -> dict;
           main(argv) -> int
deploy:    artifact_pin(repo_root) -> dict; read_git_commit/read_openapi_version/read_schema_version(root) -> str;
           rsync_command/ssh_command/find_pid_command/kill_command/start_command/rollback_command(cfg) -> list[str];
           run_deploy/run_rollback(cfg) -> list[StepResult]; main(argv) -> int
```

- 初态构造（经公开入口）：`check_env.EnvConfig` / `reset_env.ResetConfig` / `deploy.DeployConfig` 直接构造；`tempfile.TemporaryDirectory` 造临时 sqlite；HTTP 用 `mock.patch.object(module, "_request"|"http_get")`；子进程用 `mock.patch("module.subprocess.run")`。无真实网络/ssh。
- Fixture / 向量及版本：`tests/unit/cases/UT-TOOL-002.py`（内联 mock，无外部资产）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-TOOL 工具进程内（`tempfile.TemporaryDirectory`；无时钟/网络依赖）
- 依赖的测试资产（tests.asset-design 文档）：无（真实工具实现）

## 3. 输入构造

- 逐参数输入构造：固定 `argparse.Namespace`（override base-url/token/lan-ip/repo-root）；固定 `ps` 文本（含临时实例行、m5air 生产行、grep 行）；指定时刻的 `datetime`（备份名稳定）；内联 sqlite 表数据。
- 边界/非法取值及理由：`--restore`＋`--rebuild` 互斥；`--restore` 缺 `--db`；缺失 openapi/schema 文件回退 `"unknown"`；`readyz` 缺 tier / 多 tier 均失败；`ps` 中自身 PID 排除。
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单次调用，O(deployments) / O(ps lines)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `check_env.run_checks('a'/'b'/'all')` | 按 `--class` 返回对应检查；单个检查抛错转 failed 结果不中断 |
| 2 | `check_env.summarize` + `main` | `all_pass`/计数正确；exit 0 全过、2 任一失败 |
| 3 | `check_env.detect_lan_ip` | 显式 override / env override 命中 |
| 4 | `reset_env.reset_plan` | 顺序＝backup→restore/rebuild→clear-injections→reset-ledger→kill-leftovers→recheck |
| 5 | `reset_env.step_backup` / `backup_database` | 备份存在且内容一致；`--no-backup` skip；固定时钟名稳定 |
| 6 | `reset_env.step_restore_or_rebuild` | 互斥拒绝、restore 覆盖、rebuild 产空文件 |
| 7 | `reset_env.step_clear_injections` | 逐 deployment `PATCH {"items":[]}` 且 `GET` 断言空；非空即失败 |
| 8 | `reset_env.step_reset_ledger` | `DELETE /v1/usage`；`--no-ledger` skip |
| 9 | `reset_env.find_leftover_pids` / `step_kill_leftovers` | 只匹配临时实例标记、排除自身；dry-run 打印 PID |
| 10 | `reset_env.main` | 无 `--yes` 拒绝且不执行；失败步退出非零 |
| 11 | `deploy.artifact_pin` / `read_*` | pin 三要素；缺失回退 `"unknown"` |
| 12 | `deploy.*_command` | rsync 目标、lsof 端口、`kill -TERM`、start 含 3.14/PYTHONPATH/-m http_api、**无 token 值**、rollback cp |
| 13 | `deploy.run_deploy`/`run_rollback`/`main` | dry-run 无 ssh/rsync 子进程；`--pin-only` 提前返回；guard 拒绝无 `--yes` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：系统计划 §3（6 项 A 检查）§6（复位阶梯 a–f）＋`m5air-deploy-guide.md` 环境事实＋`testing-standard.md` TS-003；人工推导，不调用被测复算。
- 互斥预期（成功 / 各错误分支）：`--class` 选择正确；exit 0/2 口径正确；plan 顺序固定；dry-run 无副作用；`--yes` guard 生效；备份内容一致；注入清空成功/失败二分；pin 缺失回退；start 命令不含 secret；dry-run 不执行远程命令。

## 6. 错误路径、副作用与清理

- 错误出口与表现：工具返回非零退出码或 `StepResult.ok=False`（不抛未捕获异常）；`run_checks` 捕获检查异常。
- 副作用断言与清理：所有 DB 写入在 `tempfile.TemporaryDirectory`；mock 覆盖 HTTP/subprocess 保证无真实副作用；无持久副作用。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/cases/UT-TOOL-002.py`（`CheckEnvConfigTests` 1 + `CheckEnvAChecksTests` 5 + `CheckEnvAggregationTests` 6 + `ResetPlanTests` 4 + `ResetBackupTests` 4 + `ResetRestoreTests` 4 + `ResetInjectionTests` 2 + `ResetLedgerTests` 2 + `ResetKillTests` 3 + `ResetRecheckTests` 2 + `DeployPinTests` 3 + `DeployCommandTests` 7 + `DeployFlowTests` 5 = 48 个）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/cases/UT-TOOL-002.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/cases/UT-TOOL-002.py`）；执行状态与 Verdict 归 Run 报告。
