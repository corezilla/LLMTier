<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-UI-005 — `usageSummary` 四类呈现

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-UI-005` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-10-02` |
| Last Modified Date | `2026-10-02` |
| Template ID | `tests.module-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/module/cases/MT-UI-005.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-UI-005`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-UI-005.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-UI-005` / M002 `usageSummary` 分支：not_refreshed/unlimited/Unavailable/percent-null（组装契约） v0.1.0-draft.2 / VRC-UI-004（web-ui-design §14 / web-ui.isd §9.1，web-ui 0.1.0-draft.2） / VRC-UI-004 / boundary / P1（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：边界值（上限/零/空/刚好满、长度、分页越界）+ 条件边界（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现与真实静态产物））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M002-usageSummary 四态
- 要测什么（责任展开）：四态渲染；Unknown≠0；版本替换去重；503 显式化不显示空表（本 Case 责任：not_refreshed/unlimited/Unavailable/ok 四类呈现互斥；Unknown≠0；503 显式化不显示空表）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝web-ui 组装后账号用量四类呈现与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/web_ui/app.js::usageSummary`、`account_usage.py` 快照 status 域

```text
usageSummary(snapshot) -> html
```

- 初态构造（经公开入口）：真实静态产物 + ENV-2（经公开入口产出三种真实快照）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2
- 依赖的测试资产（tests.asset-design 文档）：无（真实静态产物 `src/web_ui/*` + ENV-1/ENV-2 真实端点；不经替身）

## 3. 输入构造

- 逐参数输入构造：快照 status ∈ {not_refreshed, unlimited, unavailable, ok}；`windows` 逐项渲染；`percent=null`；`windows=[]`；真实快照三态（未刷新 / minimax 无凭据 / local 已刷新）
- 边界/非法取值及理由：`not_refreshed`→`Not refreshed`；`unlimited`→`Unlimited`；非 `ok` 且非上述两者→`Unavailable`（title 带 `error`）；`ok` 才渲染 window；`percent=null`→`Unknown`（≠0）；`windows=[]` 不产生空表；503 显式化（`#provider-error` 有文案）
- 规模 / 时间域（数量、分页、复杂度、观测开销）：9 个测试方法；静态 + 4 次 loopback；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 四类分支渲染 | 标签逐条断言（`ok` 分支只做静态断言，见 §4 `O-UI-USAGEOK-1`） |
| 2 | `percent=null` | 渲染 `Unknown` |
| 3 | `windows=[]` + `percent=null` | 不渲染空 window |
| 4 | 真实三快照 | 三种 status 落进三个不同渲染分支；仅 `ok` 渲染 window |
| 5 | 无 window 的快照 | 不产生空表 |
| 6 | 503 显式化 | `#provider-error` 有文案而非空表 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：web-ui 模块设计 §14.5 + M004 快照 status 域；按 `usageSummary` 的分支顺序与真实快照产出人工推导
- 互斥预期（成功 / 各错误分支）：四类呈现互斥；Unknown≠0；503 显式化不显示空表

## 6. 错误路径、副作用与清理

- 错误出口与表现：无 UI 自有错误码（消费 503 状态）
- 副作用断言与清理：只读渲染，不改快照

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-UI-005.py`（9 个）：`test_not_refreshed_is_the_first_branch_and_covers_a_missing_snapshot`、`test_unlimited_renders_a_metric_not_a_percentage`、`test_any_non_ok_status_becomes_unavailable_with_the_error_reason`、`test_ok_renders_each_window_name_and_percent`、`test_unknown_percent_is_never_rendered_as_zero`、`test_only_the_head_record_version_is_rendered_so_rows_replace`、`test_store_failure_keeps_the_last_table_and_marks_the_view_stale`、`test_the_three_real_snapshots_hit_three_different_render_branches`、`test_no_window_is_rendered_for_any_snapshot_without_windows`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-UI-005.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
