<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-MGMT-006 — bootstrap 五出口与回滚、固定 tier 幂等

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-MGMT-006` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-10-02` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.module-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/module/cases/MT-MGMT-006.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-MGMT-006`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-MGMT-006.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-MGMT-006` / M004 bootstrap 五出口：no-op/required/invalid/`env:` 空/`file:` 缺失 + 回滚（组装） v0.1.0-draft.3 / VRC-MGMT-001（management-design §14 / management.isd §9.1，management 0.1.0-draft.3） / VRC-MGMT-001 / recovery / P0（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：故障注入 + 异常路径回滚 + 状态迁移断言（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M004-bootstrap 五出口；迁移：T7
- 要测什么（责任展开）：五分支 + 中途失败回滚空库 + `ensure_fixed_tiers` 幂等（本 Case 责任：no-op/required/invalid×3 五出口互斥；中途失败回滚空库且可重启（T7）；`ensure_fixed_tiers` 幂等）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝management 组装后引导五出口与回滚与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`registry.py::Registry.bootstrap_settings`/`ensure_fixed_tiers`

```text
bootstrap_settings(settings_path)  # no-op / required / invalid / env 空 / file 缺失
```

- 初态构造（经公开入口）：临时目录 + 真实 `Application`/`Store`（ENV-1）；坏 settings 经文件内容注入
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1
- 依赖的测试资产（tests.asset-design 文档）：无（全部真实实现；不经替身）

## 3. 输入构造

- 逐参数输入构造：缺 `service_levels` 节；`secret_ref=env:<未设变量>`；`secret_ref=file:/nonexistent`；两 deployment（第二个能力非法）
- 边界/非法取值及理由：五出口互斥（no-op / `bootstrap_required` / `bootstrap_invalid`×3）；中途失败→`providers` 为空（回滚）且换合法 settings 可重新引导；`ensure_fixed_tiers` 连调 2 次仍为 7 tier
- 规模 / 时间域（数量、分页、复杂度、观测开销）：6 次启动 + 1 次重引导；O(7)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 同库二次启动（同 settings） | no-op（provider 仍 1 条） |
| 2 | `settings=None` | `bootstrap_required` |
| 3 | 缺节 settings | `bootstrap_invalid` |
| 4 | `env:` 空变量 | `bootstrap_invalid` |
| 5 | `file:` 缺失 | `bootstrap_invalid` |
| 6 | 中途能力非法 | `bootstrap_invalid` + `providers=[]`；再以合法 settings 启动成功且 1 provider |
| 7 | `ensure_fixed_tiers` ×2 | 仍 7 tier（幂等） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：management 模块设计 §14.1 + ISD 引导事务契约；按 `bootstrap_settings` 的校验顺序与单事务回滚人工推导
- 互斥预期（成功 / 各错误分支）：五出口互斥；回滚无半写且可重启；固定 tier 幂等

## 6. 错误路径、副作用与清理

- 错误出口与表现：503 `bootstrap_invalid`（三形态）/ 503 `bootstrap_required`
- 副作用断言与清理：失败引导不写半行（事务回滚）

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-MGMT-006.py`（7 个）：`test_noop_on_bootstrapped_store`、`test_bootstrap_required_without_settings`、`test_missing_section_is_invalid`、`test_env_empty_secret_is_invalid`、`test_missing_secret_file_is_invalid`、`test_mid_transaction_failure_rolls_back_empty`、`test_ensure_fixed_tiers_idempotent`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-MGMT-006.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
