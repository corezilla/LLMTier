<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-UI-006 — `reportLoadFailure` 抑制与 stale 分支

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-UI-006` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-UI-006.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-UI-006`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-UI-006.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-UI-006` / M002 `reportLoadFailure` 分支：已列举状态抑制 vs 未知状态 stale（组装契约） v0.1.0-draft.2 / VRC-UI-002（web-ui-design §14 / web-ui.isd §9.1，web-ui 0.1.0-draft.2） / VRC-UI-002 / negative / P1（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：错误猜测 + 反例驱动（非法字段/凭据/引用/类型/顺序）+ 判定表组合（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现与真实静态产物））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M002-reportLoadFailure 抑制/未知
- 要测什么（责任展开）：非列举状态（网络/500）经 `reportLoadFailure` 保留上一屏并标 stale；与 `dispatchUiError` 分工（本 Case 责任：已列举状态抑制（分工无重复横幅）与未知状态标 stale 保留上一屏互斥；失败时不清空业务容器）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝web-ui 组装后装载失败兜底的抑制与 stale与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/web_ui/app.js::reportLoadFailure`、`dispatchUiError` 的状态集合

```text
reportLoadFailure(error) —— 抑制集判定 + markStale
```

- 初态构造（经公开入口）：真实静态产物 + ENV-2（真实 400/404/409/412/500/503 状态核对）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2
- 依赖的测试资产（tests.asset-design 文档）：无（真实静态产物 `src/web_ui/*` + ENV-1/ENV-2 真实端点；不经替身）

## 3. 输入构造

- 逐参数输入构造：抑制集 `{401,403,409,412,429,503}`；未列举状态（网络/500）；无 `status` 的错误；4 个「保留上一屏」装载器的 catch/成功路径；真实状态码归属
- 边界/非法取值及理由：抑制集恰等于 `dispatchUiError` 已呈现集（分工无重复）；抑制分支只 `return`；未列举→`markStale` 只写 body class + `#ui-banner`（不清空业务容器）；无 `status` 不抑制；真实 400/404 在抑制集外、409/412 在集内；M001 存在 500/503 出口锚点
- 规模 / 时间域（数量、分页、复杂度、观测开销）：10 个测试方法；静态 + 约 6 次 loopback；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 抑制集一致性 | 抑制集恰为 `dispatchUiError` 已呈现集 |
| 2 | 抑制分支 | 只 `return`，不动视图 |
| 3 | 未列举失败 | `markStale` 只加 body class + banner，不清空任何业务容器 |
| 4 | 无 `status` 的错误 | 不抑制（`api()` 仅在 `!response.ok` 赋 `error.status`） |
| 5 | 保留上一屏装载器 | 4 个装载器 catch→`reportLoadFailure`、成功→`clearStale` |
| 6 | 真实状态归属 | 400/404 在抑制集外；409/412 在集内；M001 存在 500/503 出口 |
| 7 | UI 调用满足窗口前置 | 每次调用都带 `from/to`（无窗口→400） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：web-ui 模块设计 §14.2 + ISD 失败呈现契约；按 `reportLoadFailure` 的状态判定与 `markStale`/`clearStale` 语义人工推导
- 互斥预期（成功 / 各错误分支）：抑制与 stale 两分支互斥且分工清晰；失败时保留上一屏数据

## 6. 错误路径、副作用与清理

- 错误出口与表现：无 UI 自有错误码（消费服务端状态）
- 副作用断言与清理：stale 标记可由成功装载清除（视图可恢复）

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-UI-006.py`（10 个）：`test_suppressed_set_is_exactly_the_set_dispatch_ui_error_already_presented`、`test_listed_statuses_return_without_touching_the_view`、`test_unlisted_failure_marks_stale_and_keeps_the_last_screen`、`test_failure_without_a_status_is_not_suppressed`、`test_last_screen_loaders_route_failures_here_and_clear_stale_on_success`、`test_the_banner_never_shows_server_text_for_a_stale_refresh`、`test_real_400_and_404_are_outside_the_suppressed_set`、`test_real_409_and_412_are_inside_the_suppressed_set`、`test_the_ui_page_load_calls_satisfy_the_window_precondition`、`test_real_500_and_503_exits_exist_in_m001`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-UI-006.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
