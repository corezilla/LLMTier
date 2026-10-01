<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-TOOL-001 — 证据链工具：状态映射、SKIP 上限与 manifest

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-TOOL-001` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-10-01` |
| Template ID | `tests.unit-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/unit/cases/UT-TOOL-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-TOOL-001`）；责任摘要、分类与优先级以 [单元测试方案 §3](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：本项目**验证工具（verification tooling）**，非 8 个软件模块（`M001-M008`）之一：被测为 `tools/test_report.py`（证据链工具，见 [单元测试计划](../llmtier-unit-test-plan.md) §7 状态映射规则）。该 Case 不归属任何模块设计 §14 VRC（工具不实现产品行为），作为方案 §3 的独立「TOOL 家族」登记，**不改变** 33 个模块 VRC 的分母。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的工具切片 `TOOL`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-TOOL-001` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-TOOL-001` / M-TOOL `tools/test_report.py`（单元计划 §7 状态映射）/ none（工具，无模块 VRC）/ normal / P1（[方案清单 §3](../llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：等价类划分 + 契约字段比对（工具纯逻辑）
- 要测什么（责任展开）：被测：`tools/test_report.py` 的 JUnit→状态映射（`passed→PASS`、`failed→FAIL`、`xfailed→BLOCKED`（原因取自 `BLOCKED (...)`）、`xpassed→XPASS`（绝不 PASS）、环境 `skipped→SKIP` / 计划 `skipped→NOT_RUN`、`errored→BLOCKED`）、运行级 SKIP 上限（A≤5 / B≤3）、`case_id_from_source`（docstring 头 / 路径回退）、`build_report` 计数与阻塞口径、`emit_manifests` 逐 Case manifest 产出。
- 明确不测什么 / 失败含义：不测：pytest 自身执行语义；不测被测产品行为。失败含义＝状态映射错误导致 Run 证据失真（假 PASS / 漏 BLOCKED）。

## 2. 被测入口与前置

- 被测入口声明与位置：`tools/test_report.py::harvest/build_report/cap_breached/case_id_from_source/emit_manifests`

```text
harvest(junit_path) -> list[dict]; build_report(junit_path, metadata) -> dict;
cap_breached(records, layer) -> bool; case_id_from_source(source, fallback) -> str;
emit_manifests(run_dir, records, metadata) -> int
```

- 初态构造（经公开入口）：内联 JUnit XML fixture（`_xml`/`_case`）写入临时目录；`METADATA` 字典固定 run 元数据
- Fixture / 向量及版本：`tests/unit/v03/test_test_report.py`（内联 XML fixture，无外部资产）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-TOOL 工具进程内（`tempfile.TemporaryDirectory`；无时钟/网络依赖，除自身写出的固定 `run-metadata` 文件）
- 依赖的测试资产（tests.asset-design 文档）：无（真实工具实现）

## 3. 输入构造

- 逐参数输入构造：内联 JUnit XML：`passed`/`failure`/`pytest.xfail`（`BLOCKED (...)`）`/`[XPASS(strict)]`/环境 `skipped`/计划 `skipped`/`error`；5/6 条 skip 用例；manifest 输出目录
- 边界/非法取值及理由：SKIP 上限 A=5/B=3 边界（5 不越限、6 越限；B 对 5 即越限）；XPASS 不得计 PASS
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单 XML，O(用例数)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `harvest` 各类 JUnit 结果 | 映射到 `PASS`/`FAIL`/`BLOCKED`/`XPASS`/`SKIP`/`NOT_RUN` |
| 2 | `xfailed` 带 `BLOCKED (ID): reason` | LLMTier 稳定 BLOCKED 与原因保留 |
| 3 | `cap_breached` A/B | A 5 不越限 / 6 越限；B 5 越限（B≤3） |
| 4 | `build_report` | `counts` 与 `release_blocking` 口径 |
| 5 | `emit_manifests` | 逐 Case `manifest.json`（case_id/git_commit/redactions） |
| 6 | `case_id_from_source` | docstring 头 `Case ID:` 优先，缺失回退路径 |
| 7 | `record_property("case_id", ...)` 优先级 | JUnit `<property>` 中的 `case_id` 优先于源码头/路径回退（供多 Case 参数化的真实浏览器 UI 套件 `tests/ui` 归集） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：单元计划 §7 状态映射规则 + SKIP 上限（A≤5/B≤3）+ manifest 契约；人工推导，不调用被测复算。**判据语义以计划 §7 为唯一权威**；本节仅细化不改写，冲突回溯计划/方案修订。
- 互斥预期（成功 / 各错误分支）：`failed→FAIL`；`xfailed→BLOCKED`（原因保留）；`xpassed→XPASS` 且 ≠PASS；环境 skip→SKIP、计划 skip→NOT_RUN；`error→BLOCKED`；A=5 不越限、A=6 越限、B=5 越限；manifest 字段与记录一致

## 6. 错误路径、副作用与清理

- 错误出口与表现：无（纯函数/临时文件；映射为工具输出而非异常）
- 副作用断言与清理：每次 `tempfile.TemporaryDirectory` 隔离；无持久副作用

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/v03/test_test_report.py`（`StatusMappingTests` 7 + `CaseIdTests` 3（含 `test_record_property_case_id_wins_over_source_header`）+ `ReportTests` 8 = 18 个）（注意：本 Case 的测试函数当前按子句（test case method）映射；若与计划/方案不一致，以修订回溯后重裁）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/v03/test_test_report.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/v03/test_test_report.py`）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。
