<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-MGMT-007 — bootstrap 事务回滚与幂等补建

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-MGMT-007` |
| Document Version | `0.1.0-draft.3` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.unit-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/unit/cases/UT-MGMT-007.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-MGMT-007`）；责任摘要、分类与优先级以 [单元测试方案 §6](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [management](../../../40_module_design/management-design.md) §14 / ISD [management.isd.md](../../../50_implementation_design/management.isd.md) §9.1，设计验证项 `VRC-MGMT-001`（固定版本 `management 0.1.0-draft.3`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `management`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-MGMT-007` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-MGMT-007` / M004 management §14.1 · `bootstrap_settings`/`ensure_fixed_tiers` v0.1.0-draft.2 / `VRC-MGMT-001` / recovery / P0（[方案清单 §6](../llmtier-unit-test-scheme.md)）。
- **测试方法（§2.1 方法表行）**：故障注入 + 异常路径恢复（bootstrap 事务中途失败回滚）（主要手段：直接调用 + 冻结向量 + 替身注入）
- 要测什么（责任展开）：被测：`Registry.bootstrap_settings` 中途失败→空库回滚 + not_ready；`ensure_fixed_tiers` 幂等二次补建且不与 bootstrap 配置能力冲突。
- 明确不测什么 / 失败含义：不测：合法 bootstrap 主路径（UT-MGMT-001）；不测 systemd 启动流程。失败含义＝引导事务原子性/幂等补建实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/management/registry.py::Registry.bootstrap_settings`/`ensure_fixed_tiers`

```text
Registry.bootstrap_settings(settings) ; Registry.ensure_fixed_tiers(conn=None)
```

- 初态构造（经公开入口）：`AppFixture` / 隔离临时库；构造可致中途失败（缺节/坏 Secret 引用）的 settings（ENV-1）
- Fixture / 向量及版本：`tests/unit/cases/UT-MGMT-007.py::BootstrapTests`；`fakes.py::AppFixture`（ENV-1）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库
- 依赖的测试资产（tests.asset-design 文档）：无（真实实现）

## 3. 输入构造

- 逐参数输入构造：合法 settings；重复启动；缺节；`env:` 空；`file:` 不存在；二次 `ensure_fixed_tiers`
- 边界/非法取值及理由：失败→空库回滚；重复启动 no-op；二次补建幂等
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单次引导，O(配置规模)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 合法 bootstrap | 成功且 hash 一致 |
| 2 | 重复启动 | no-op 指纹匹配 |
| 3 | 缺节/坏 Secret 引用 | 失败并回滚空库 + not_ready |
| 4 | 二次 `ensure_fixed_tiers` | 幂等、不冲突 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`T-MGMT-01/02/04` + `CON-CFG-001/2` + 人工推导；不调用被测复算。**判据语义以设计验证项 `VRC-MGMT-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：合法成功；重复 no-op；失败空库回滚 + not_ready；二次补建幂等；互斥

## 6. 错误路径、副作用与清理

- 错误出口与表现：校验/读取失败→回滚；暴露为 not_ready（503）；无第三态
- 副作用断言与清理：失败事务无半写（空库）；隔离库由 fixture 清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/cases/UT-MGMT-007.py::BootstrapTests::test_valid_bootstrap_succeeds` / `test_repeated_start_is_noop` / `test_missing_section_fails` / `test_env_secret_ref_unavailable_fails` / `test_file_secret_ref_missing_fails` / `test_failed_bootstrap_rolls_back_to_empty_store`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/cases/UT-MGMT-007.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/cases/UT-MGMT-007.py`）；执行状态与 Verdict 见 Run 报告 `run-20261001-04`。
