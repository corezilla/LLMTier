<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-DIAG-002 — 记录与查询（trace/快照/统计/清理）

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-DIAG-002` |
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
| Canonical Path | `docs/70_verification/unit/cases/UT-DIAG-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-DIAG-002`）；责任摘要、分类与优先级以 [单元测试方案 §6](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [libdiag-design.md](../../../40_module_design/libdiag-design.md) §14 / ISD [libdiag.isd.md](../../../50_implementation_design/libdiag.isd.md) §9.1，设计验证项 `VRC-DIAG-002`（固定版本 `libdiag 0.1.0-draft.6`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `DIAG`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-DIAG-002` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-DIAG-002` / `VRC-DIAG-002`（libdiag 模块设计 §14 / libdiag-isd §9.1，libdiag 0.1.0-draft.6） / `VRC-DIAG-002` / boundary / P1（[方案清单 §6](../llmtier-unit-test-scheme.md)）。
- **测试方法（§2.1 方法表行）**：边界值（字段/去 query/截断/百分位/清理）（主要手段：直接调用 + 冻结向量 + 替身注入）
- 要测什么（责任展开）：被测：一次调用后 trace/snapshot/stats 字段、URL 去 query、summary 截断 512、百分位、7 天清理计数。
- 明确不测什么 / 失败含义：不测：真实长期保留策略（系统层）；不测 UI。失败含义＝记录/截断/清理实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/libdiag/traces.py`/`snapshots.py`/`stats.py`/`retention.py`；`record_trace`

```text
record_trace(...); cleanup(days) -> int
```

- 初态构造（经公开入口）：`AppFixture`
- Fixture / 向量及版本：`tests/common/fakes.py::AppFixture`（ENV-1）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库 / ENV-2 loopback 测试 HTTP 实例 / ENV-3 provider 进程内 fake（按 Case 需要，见 §4）
- 依赖的测试资产（tests.asset-design 文档）：无（真实实现）

## 3. 输入构造

- 逐参数输入构造：一次调用；URL 带 query；超长 summary；7 天前记录
- 边界/非法取值及理由：截断 512、查询串去除、7 天边界
- 规模 / 时间域（数量、分页、复杂度、观测开销）：O(记录数)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | trace/snapshot/stats 字段 | 字段完整 |
| 2 | URL 去 query | 无 query |
| 3 | summary 截断 512 | ≤512 |
| 4 | 百分位 | 值正确 |
| 5 | 7 天清理 | 返回删除数 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`RULE-DIAG-TRUNC/PCTL`；人工推导。**判据语义以设计验证项 `VRC-DIAG-002` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：字段完整；URL 去 query；summary ≤512；百分位正确；7 天前删除且返回计数

## 6. 错误路径、副作用与清理

- 错误出口与表现：无（分支互斥）
- 副作用断言与清理：留痕落库；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/cases/UT-DIAG-002.py::test_error_body_truncated_to_512_bytes/test_traces_dedups_by_request_and_stable_paging/test_cleanup_removes_expired_and_returns_count`（注意：本 Case 的测试函数当前按子句（test case method）映射；若与设计 VRC 不一致，以设计修订回溯后重裁）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/cases/UT-DIAG-002.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit`）；执行状态与 Verdict 见 Run 报告 `run-20261001-04`。

