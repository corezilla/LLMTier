<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-DIAG-006 — 游标格式与 correlation 取自 stage detail 的失败路径

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-DIAG-006` |
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
| Canonical Path | `docs/70_verification/unit/cases/UT-DIAG-006.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-DIAG-006`）；责任摘要、分类与优先级以 [单元测试方案 §6](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [libdiag](../../../40_module_design/libdiag-design.md) §14 / ISD [libdiag.isd.md](../../../50_implementation_design/libdiag.isd.md) §9.1，设计验证项 `VRC-DIAG-002`（固定版本 `libdiag 0.1.0-draft.6`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `libdiag`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-DIAG-006` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-DIAG-006` / M006 libdiag §14.2/§14.3 · 游标与失败 v0.1.0-draft.6 / `VRC-DIAG-002` / recovery / P1（[方案清单 §6](../llmtier-unit-test-scheme.md)）。
- **测试方法（§2.1 方法表行）**：错误猜测 + 反例驱动（非法 cursor）+ 异常路径恢复（主要手段：直接调用 + 冻结向量 + 替身注入）
- 要测什么（责任展开）：被测：snapshots/traces 非法 cursor → 400 `cursor_expired`；trace cursor 格式 `first_ts|request_id`；correlation 取自 stage detail。
- 明确不测什么 / 失败含义：不测：游标正常分页（UT-DIAG-002/004）；不测写入失败（UT-DIAG-007）。失败含义＝游标格式/校验或 correlation 提取实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/libdiag/traces.py`（cursor 编解码、stage detail correlation）与 `src/libdiag/snapshots.py`（cursor）；入口 `DiagnosticsService.traces`/`snapshots_page`

```text
DiagnosticsService.traces(..., cursor); DiagnosticsService.snapshots_page(..., cursor)
```

- 初态构造（经公开入口）：`AppFixture` 建 `DiagnosticsService`；写入 trace 与 snapshots（ENV-1）
- Fixture / 向量及版本：`tests/unit/cases/UT-DIAG-006.py::CursorContractGapTests`；`fakes.py::AppFixture`（ENV-1）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库
- 依赖的测试资产（tests.asset-design 文档）：无（真实实现）

## 3. 输入构造

- 逐参数输入构造：非法 cursor 字符串；正常 trace 记录；带 stage detail 的 record_trace
- 边界/非法取值及理由：非法 cursor→400；cursor 格式固定
- 规模 / 时间域（数量、分页、复杂度、观测开销）：O(记录数)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | trace cursor 格式 | `first_ts|request_id` |
| 2 | correlation 取自 stage detail | 与 detail 中 `x_correlation_id` 一致 |
| 3 | snapshots cursor | `snapshot_id` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`RULE-DIAG-CURSOR`/`T-DIAG-*` + 人工推导；不调用被测复算。**判据语义以设计验证项 `VRC-DIAG-002` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：cursor 格式正确；correlation 取自 stage detail；非法 cursor 400 `cursor_expired`；互斥

## 6. 错误路径、副作用与清理

- 错误出口与表现：400 `cursor_expired`（非法 cursor）；无第三态
- 副作用断言与清理：读取不写库；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/cases/UT-DIAG-006.py::CursorContractGapTests::test_trace_cursor_is_first_ts_pipe_request_id` / `test_correlation_id_taken_from_stage_detail` / `test_snapshots_cursor_is_snapshot_id`；非法 cursor 400 另由 `UT-DIAG-006.py::DiagnosticsHttpContractTests::test_traces_invalid_cursor_is_400_expired` 覆盖
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/cases/UT-DIAG-006.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/cases/UT-DIAG-006.py`）；执行状态与 Verdict 见 Run 报告 `run-20261001-04`。
