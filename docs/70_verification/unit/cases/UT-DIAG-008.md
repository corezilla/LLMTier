<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-DIAG-008 — stream_wrapper 透传/早停/优先级与 revoke

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-DIAG-008` |
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
| Canonical Path | `docs/70_verification/unit/cases/UT-DIAG-008.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-DIAG-008`）；责任摘要、分类与优先级以 [单元测试方案 §6](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [libdiag](../../../40_module_design/libdiag-design.md) §14 / ISD [libdiag.isd.md](../../../50_implementation_design/libdiag.isd.md) §9.1，设计验证项 `VRC-DIAG-004`（固定版本 `libdiag 0.1.0-draft.6`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `libdiag`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-DIAG-008` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-DIAG-008` / M006 libdiag §14.4 · `stream_wrapper`/优先级 v0.1.0-draft.6 / `VRC-DIAG-004` / boundary / P1（[方案清单 §6](../llmtier-unit-test-scheme.md)）。
- **测试方法（§2.1 方法表行）**：边界值（透传/早停/畸形帧/优先级/revoke）（主要手段：直接调用 + 冻结向量）
- 要测什么（责任展开）：被测：`stream_wrapper` 透传 vs 早停 vs 畸形帧；`enabled_stream_injection` 优先级；空 `items` revoke（DELETE）。
- 明确不测什么 / 失败含义：不测：四类注入校验（UT-DIAG-004）；不测真实 SSE wire。失败含义＝流包装/注入优先级/revoke 实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/libdiag/stream.py::stream_wrapper` / `DiagnosticsService.enabled_stream_injection` / `src/libdiag/injections.py::set_injections(items=[])`

```text
DiagnosticsService.stream_wrapper(deployment_id, base_stream); enabled_stream_injection(deployment_id); set_injections(deployment_id, items)
```

- 初态构造（经公开入口）：`AppFixture` 建 `DiagnosticsService`；配置 stream 注入与 pre-call 注入（ENV-1）
- Fixture / 向量及版本：`tests/unit/cases/UT-DIAG-008.py::StreamWrapperTests`；`fakes.py::AppFixture`（ENV-1）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库 / ENV-3 provider 进程内 fake
- 依赖的测试资产（tests.asset-design 文档）：`FakeAdapter`（`llmtier-unit-fakes`，资产文档已建）

## 3. 输入构造

- 逐参数输入构造：无注入的 base_stream；`stream_terminate`；`malformed_event`；同时配 terminate+malformed；同时配 fault_502+delay；`items=[]`
- 边界/非法取值及理由：透传/早停/畸形三分支；流注入优先级 terminate 优先；pre-call 优先级 fault_502 优先；revoke 删全部行
- 规模 / 时间域（数量、分页、复杂度、观测开销）：O(事件数)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 无注入 | 透传 |
| 2 | `stream_terminate` | 早停 |
| 3 | `malformed_event` | 追加畸形帧 |
| 4 | terminate+malformed | terminate 优先 |
| 5 | fault_502+delay | fault_502 优先 |
| 6 | `items=[]` | DELETE 全部注入行 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`T-DIAG-06/07`/`RULE-*` 优先级 + 人工推导；不调用被测复算。**判据语义以设计验证项 `VRC-DIAG-004` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：透传/早停/畸形正确；流注入 terminate 优先、pre-call fault_502 优先；空 items revoke；互斥

## 6. 错误路径、副作用与清理

- 错误出口与表现：无错误出口（边界/优先级断言）
- 副作用断言与清理：注入行 upsert/DELETE（隔离库）；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/cases/UT-DIAG-008.py::StreamWrapperTests::test_passthrough_without_injection` / `test_stream_terminate_early_end` / `test_malformed_event_appends_broken_frame` / `test_stream_injection_priority_is_terminate_first` / `test_pre_call_injection_priority_is_fault_502_first` / `test_empty_items_revokes_all`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/cases/UT-DIAG-008.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/cases/UT-DIAG-008.py`）；执行状态与 Verdict 见 Run 报告 `run-20261001-04`。
