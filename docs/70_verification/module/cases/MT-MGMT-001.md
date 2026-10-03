<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-MGMT-001 — Registry.bootstrap_settings 组装后引导

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-MGMT-001` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-MGMT-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-MGMT-001`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-MGMT-001.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-MGMT-001` / M004 management §9 · `Registry.bootstrap_settings`（组装） v0.1.0-draft.3 / VRC-MGMT-001（management-design §14 / management.isd §9.1，management 0.1.0-draft.3） / VRC-MGMT-001 / normal / P0（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：组装后真实调用 + 等价类划分 + 分支覆盖（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：迁移：T6
- 要测什么（责任展开）：组装后引导：合法 settings、重复启动 no-op、空库无 settings→503 `bootstrap_required`、缺节/`env:` 空/`file:` 不存在→503 `bootstrap_invalid` 回滚 + not_ready（本 Case 责任：合法 settings→ready；空库无 settings→503 `bootstrap_required`；重复启动 no-op（审计恰 1 条）（T6））
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝management 组装后引导四态与幂等与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/management/registry.py::Registry.bootstrap_settings`/`ensure_fixed_tiers`、`app.py::Application.__init__`

```text
bootstrap_settings(settings_path | None); ensure_fixed_tiers()
```

- 初态构造（经公开入口）：临时目录 + 真实 `Application`（ENV-1）；空库无 settings 与重复启动两种初态
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1（真实 `Store`+`Registry` 引导）；空库就绪视图经 ENV-2
- 依赖的测试资产（tests.asset-design 文档）：无（全部真实实现；不经替身）

## 3. 输入构造

- 逐参数输入构造：合法空 sections settings；`settings=None`；同库两次 `Application`；`GET /readyz`
- 边界/非法取值及理由：引导成功→7 个固定 tier 且 `bootstrap_error=None`；无 settings→503 `bootstrap_required`；重复启动 no-op（`registry.bootstrap` 审计恰 1 条）；引导失败→`/readyz` 503 `not_ready`
- 规模 / 时间域（数量、分页、复杂度、观测开销）：4 次构建/请求；O(7) tier 登记

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 合法 settings 首次启动 | `bootstrap_error=None`；7 tier 就位 |
| 2 | `settings=None` 启动 | `bootstrap_error=(503, bootstrap_required)` |
| 3 | 同库第二次启动（同 settings） | 引导 no-op；`registry.bootstrap` 审计仍 1 条 |
| 4 | 引导失败实例的 `GET /readyz` | 503 `not_ready` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：management 模块设计 §14.1 + ISD 引导契约；按 `bootstrap_settings` 的 sha256 短路与 tier 兜底登记人工推导
- 互斥预期（成功 / 各错误分支）：引导四态互斥；重复启动幂等；就绪视图与 `bootstrap_error` 一致

## 6. 错误路径、副作用与清理

- 错误出口与表现：503 `bootstrap_required`（无 settings）
- 副作用断言与清理：引导事务一次提交；审计留痕

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-MGMT-001.py`（4 个）：`test_valid_settings_bootstraps_ready`、`test_empty_store_without_settings_is_bootstrap_required`、`test_second_startup_is_noop_single_bootstrap_audit`、`test_readyz_reflects_bootstrap_state`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-MGMT-001.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
