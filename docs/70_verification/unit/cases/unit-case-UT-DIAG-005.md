<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-DIAG-005 — 快照截断/类型与统计百分位分桶

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-DIAG-005` |
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
| Canonical Path | `docs/70_verification/unit/cases/unit-case-UT-DIAG-005.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-DIAG-005`）；责任摘要、分类与优先级以 [单元测试方案 §3](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [libdiag](../../../40_module_design/libdiag-design.md) §14 / ISD [libdiag.isd.md](../../../50_implementation_design/libdiag.isd.md) §9.1，设计验证项 `VRC-DIAG-002`（固定版本 `libdiag 0.1.0-draft.6`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `libdiag`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-DIAG-005` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-DIAG-005` / M006 libdiag §14.2 · `snapshots`/`stats` 分支 v0.1.0-draft.6 / `VRC-DIAG-002` / boundary / P1（[方案清单 §3](../llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：边界值（256B 字节截断/百分位/分桶）
- 要测什么（责任展开）：被测：快照 `error_summary` 256B UTF-8 字节截断；`snapshot_type` 由 status 判定（有 status→upstream、无→error）；开关关→无行；stats 百分位 P50/P95 与 `windows=[]`、`error_4xx/5xx` 分桶。
- 明确不测什么 / 失败含义：不测：HTTP 契约（UT-DIAG-002）；不测 fail-open（UT-DIAG-003/007）。失败含义＝截断/类型判定/百分位与分桶实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/libdiag/snapshots.py`（`error_summary` 截断、`snapshot_type`）与 `src/libdiag/stats.py`（百分位、分桶、空窗）

```text
DiagnosticsService.capture_snapshot(...); DiagnosticsService.stats(since, until, ...)
```

- 初态构造（经公开入口）：`AppFixture` 建 `DiagnosticsService`；写入 200/None 状态快照与多延迟样本（ENV-1）
- Fixture / 向量及版本：`tests/unit/v03/test_diagnostics_gaps.py::SnapshotBranchTests`/`StatsBranchTests`；`fakes.py::AppFixture`（ENV-1）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库
- 依赖的测试资产（tests.asset-design 文档）：无（真实实现）

## 3. 输入构造

- 逐参数输入构造：超 256B 的 `error_summary`；status 200 / `None`；开关关；多延迟样本；空窗
- 边界/非法取值及理由：256B UTF-8 字节边界；百分位；空窗与分桶
- 规模 / 时间域（数量、分页、复杂度、观测开销）：O(样本数)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 超长 `error_summary` | 截断至 ≤256 UTF-8 字节 |
| 2 | status 200 / None | `snapshot_type=upstream` / `error` |
| 3 | 开关关 | 无行 |
| 4 | 多样本 stats | P50/P95 正确、`error_4xx/5xx` 分桶；空窗 `windows=[]` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`RULE-DIAG-*`/截断与百分位算法（人工手算）+ 人工推导；不调用被测复算。**判据语义以设计验证项 `VRC-DIAG-002` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：256B 截断；类型判定正确；开关关无行；P50/P95 与分桶正确、空窗 `windows=[]`；互斥

## 6. 错误路径、副作用与清理

- 错误出口与表现：无错误出口（边界与分桶断言）
- 副作用断言与清理：仅开关开时落库（隔离库）；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/v03/test_diagnostics_gaps.py::SnapshotBranchTests::test_error_summary_truncated_to_256_utf8_bytes` / `test_snapshot_type_upstream_when_status_present` / `test_snapshot_type_error_when_status_absent` / `test_switch_off_captures_nothing` / `StatsBranchTests::test_stats_empty_windows_when_no_samples` / `test_percentiles_and_error_buckets` / `test_stats_switch_off_writes_nothing`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/v03/test_diagnostics_gaps.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/v03/test_diagnostics_gaps.py`）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。
