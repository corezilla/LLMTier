<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-OBS-001 — 观测开关与关闭零写入

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-OBS-001` |
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
| Canonical Path | `docs/70_verification/unit/cases/UT-OBS-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-OBS-001`）；责任摘要、分类与优先级以 [单元测试方案 §3](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [observability-design.md](../../../40_module_design/observability-design.md) §14 / ISD [observability.isd.md](../../../50_implementation_design/observability.isd.md) §9.1，设计验证项 `VRC-OBS-001`（固定版本 `observability 0.1.0-draft.6`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `OBS`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-OBS-001` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-OBS-001` / `VRC-OBS-001`（observability 模块设计 §14 / observability-isd §9.1，observability 0.1.0-draft.6） / `VRC-OBS-001` / normal / P1（[方案清单 §3](../llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：等价类划分（开关默认/切换）（主要手段：直接调用 + 替身注入）
- 要测什么（责任展开）：被测：诊断开关默认 `{False,False}`、运行时切换、关闭时零写入。
- 明确不测什么 / 失败含义：不测：真实 HTTP 端点（M001/M006）；不测 UI。失败含义＝开关语义实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/libdiag/diagnostics.py::DiagnosticsService.switches/set_switches`

```text
switches() -> dict; set_switches(snapshots_enabled=..., stats_enabled=...)
```

- 初态构造（经公开入口）：`AppFixture`；`d = app.diagnostics`
- Fixture / 向量及版本：`tests/common/fakes.py::AppFixture`（ENV-1）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库 / ENV-2 loopback 测试 HTTP 实例 / ENV-3 provider 进程内 fake（按 Case 需要，见 §4）
- 依赖的测试资产（tests.asset-design 文档）：无（真实实现）

## 3. 输入构造

- 逐参数输入构造：默认；开/关切换；关闭后记录
- 边界/非法取值及理由：默认 vs 开启边界
- 规模 / 时间域（数量、分页、复杂度、观测开销）：O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 默认 switches | {False,False} |
| 2 | set_switches 开 | 关闭零写入 |
| 3 | 关闭后调用 | 无新行 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`FUNC-OBS-SWITCH`/`CON-OBS-001`；人工推导。**判据语义以设计验证项 `VRC-OBS-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：默认 `{snapshots_enabled:False, stats_enabled:False}`；开启后落记录；关闭时零新行

## 6. 错误路径、副作用与清理

- 错误出口与表现：无（分支互斥）
- 副作用断言与清理：开关落库；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/cases/UT-OBS-001.py::test_switches_default_off_and_runtime_toggle`（注意：本 Case 的测试函数当前按子句（test case method）映射；若与设计 VRC 不一致，以设计修订回溯后重裁）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/cases/UT-OBS-001.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit`）；执行状态与 Verdict 见 Run 报告 `run-20261001-04`。

