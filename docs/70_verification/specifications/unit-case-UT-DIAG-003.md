<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-DIAG-003 — 诊断 fail-open

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-DIAG-003` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-09-30` |
| Template ID | `tests.unit-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/unit-case-UT-DIAG-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-DIAG-003`）；责任摘要、分类与优先级以 [单元测试方案 §3](../schemes/llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [libdiag-design.md](../../40_module_design/libdiag-design.md) §14 / ISD [libdiag.isd.md](../../50_implementation_design/libdiag.isd.md) §9.1，设计验证项 `VRC-DIAG-003`（固定版本 `libdiag 0.1.0-draft.6`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `DIAG`；裁剪依据见 [STD 裁剪清单](../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-DIAG-003` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-DIAG-003` / `VRC-DIAG-003`（libdiag 模块设计 §14 / libdiag-isd §9.1，libdiag 0.1.0-draft.6） / `VRC-DIAG-003` / recovery / P1（[方案清单 §3](../schemes/llmtier-unit-test-scheme.md)）。
- 要测什么（责任展开）：被测：诊断写入失败/初始化失败时推理结果不变、降级运行（`_UnavailableDiagnostics`）。
- 明确不测什么 / 失败含义：不测：真实磁盘故障（系统层）；不测 M003 推理语义。失败含义＝诊断故障导致推理失败。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/libdiag/diagnostics.py`；`src/http_api/app.py::_UnavailableDiagnostics`

```text
DiagnosticsService(...) 构造异常 / record_trace 抛错
```

- 初态构造（经公开入口）：`AppFixture`；替换 diagnostics 为不可用桩
- Fixture / 向量及版本：`tests/unit/v03/fakes.py::AppFixture`/`FakeAdapter`（ENV-3）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../plans/llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库 / ENV-2 loopback 测试 HTTP 实例 / ENV-3 provider 进程内 fake（按 Case 需要，见 §4）
- 依赖的测试资产（tests.asset-design 文档）：`FakeAdapter`（G-UT-2）

## 3. 输入构造

- 逐参数输入构造：初始化失败；写入失败
- 边界/非法取值及理由：正常 vs 故障
- 规模 / 时间域（数量、分页、复杂度、观测开销）：O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 诊断初始化失败 | 降级运行 |
| 2 | 写入失败 | 推理结果不变 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`RULE-OBS-FAILOPEN`/`CON-OBS-002`；人工推导（对照正常结果）。**判据语义以设计验证项 `VRC-DIAG-003` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：故障时推理返回与正常一致；不抛出宿主不可恢复错误

## 6. 错误路径、副作用与清理

- 错误出口与表现：无（fail-open 为成功预期）
- 副作用断言与清理：无（不改变推理）；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/v03/test_runtime_snapshot.py`（诊断不可用路径）+ `app.py::_UnavailableDiagnostics` 行为（见 `test_app_startup`）（注意：本 Case 的测试函数当前按子句（test case method）映射；若与设计 VRC 不一致，以设计修订回溯后重裁）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/v03 -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/v03`）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。

