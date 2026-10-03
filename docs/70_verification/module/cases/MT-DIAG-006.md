<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-DIAG-006 — 游标与时间窗分支

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-DIAG-006` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-DIAG-006.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-DIAG-006`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-DIAG-006.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-DIAG-006` / M006 游标分支：traces/snapshots 非法 cursor→400（组装） v0.1.0-draft.6 / VRC-DIAG-002（libdiag-design §14 / libdiag.isd §9.1，libdiag 0.1.0-draft.6） / VRC-DIAG-002 / boundary / P1（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：边界值（上限/零/空/刚好满、长度、分页越界）+ 条件边界（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M006-游标分支；组合：K9
- 要测什么（责任展开）：非法 cursor→400 `cursor_expired`；`next_cursor`/`has_more` 稳定；时间窗越界为空（本 Case 责任：K9 四行全覆盖；两查询面游标语义各自正确；窗口/limit/过滤一致；分页稳定）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝libdiag 组装后两查询面的游标与窗口与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`libdiag/traces.py::traces`、`snapshots.py::snapshots_page`（游标与窗口）

```text
traces(since, until, deployment_id, model, limit, cursor); snapshots_page(since, until, deployment_id, model, limit, cursor)
```

- 初态构造（经公开入口）：`AppFixture` 真实组装（ENV-1）；traces/快照经公开 `record_trace`/`capture_snapshot` 播种
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：traces 非法 cursor（无 `|`）；traces 窗外；snapshots 非法 cursor（不存在 id）；snapshots 3 行分页（limit=2）；`limit=0/-3/9999`；`model`/`deployment_id` 过滤
- 边界/非法取值及理由：非法 cursor→400 `cursor_expired`（两查询面各一）；窗外为空；分页 2+1 不重叠且末页 `has_more=false`/`next_cursor=None`；`limit` 夹取 [1,500]；`model` 命中/未命中；`deployment_id` 命中
- 规模 / 时间域（数量、分页、复杂度、观测开销）：6 个测试方法；3 快照 + 2 trace；O(n)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | traces 非法 cursor | 400 `cursor_expired` |
| 2 | traces 窗外 | 空 items |
| 3 | snapshots 非法 cursor | 400 `cursor_expired` |
| 4 | snapshots 分页（limit=2） | 2 条 + `has_more`；第二页 1 条、不重叠、`has_more=false`、`next_cursor=None` |
| 5 | `limit=0/-3/9999` | 两查询面分别夹取到 1/1/全部 |
| 6 | `model=Senior` / `model=Junior` / `deployment_id` | 命中 1 条 / 0 条 / 1 条 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：libdiag 模块设计 §14.2 + 方案 §6.3 K9；按两查询面的游标形态差异（`ts|rid` vs snapshot id）与 `max(1,min(limit,500))` 人工推导
- 互斥预期（成功 / 各错误分支）：K9 四行全覆盖；两查询面游标语义各自正确；窗口/limit/过滤一致

## 6. 错误路径、副作用与清理

- 错误出口与表现：400 `cursor_expired`（两形态）
- 副作用断言与清理：查询不改库

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-DIAG-006.py`（6 个）：`test_traces_invalid_cursor_is_400`、`test_traces_beyond_window_is_empty`、`test_snapshots_invalid_cursor_is_400`、`test_snapshots_paging_is_stable`、`test_limit_clamped_on_both_faces`、`test_traces_filter_by_model_and_deployment`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-DIAG-006.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
