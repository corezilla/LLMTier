<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-INF-005 — 观测 fail-open 与不二次鉴权

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-INF-005` |
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
| Canonical Path | `docs/70_verification/unit/cases/UT-INF-005.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-INF-005`）；责任摘要、分类与优先级以 [单元测试方案 §6](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [inference-design.md](../../../40_module_design/inference-design.md) §14 / ISD [inference.isd.md](../../../50_implementation_design/inference.isd.md) §9.1，设计验证项 `VRC-INF-005`（固定版本 `inference 0.1.0-draft.1`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `INF`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-INF-005` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-INF-005` / `VRC-INF-005`（inference 模块设计 §14 / inference-isd §9.1，inference 0.1.0-draft.1） / `VRC-INF-005` / recovery / P1（[方案清单 §6](../llmtier-unit-test-scheme.md)）。
- **测试方法（§2.1 方法表行）**：故障注入 + 异常路径恢复（观测 fail-open/不二次鉴权）（主要手段：直接调用 + 替身注入）
- 要测什么（责任展开）：被测：观测（diagnostics）不可用时推理结果不变（fail-open），推理路径不做二次鉴权。
- 明确不测什么 / 失败含义：不测：真观测库故障注入完整性（归 M005/M006）；不测 M001 鉴权。失败含义＝观测故障导致推理失败（不 fail-open）。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/inference/responses.py`（diagnostics 调用点）；`src/libdiag` 不可用桩

```text
ResponsesService.create(..., diagnostics=...)
```

- 初态构造（经公开入口）：`AppFixture`；`app.diagnostics` 替换为 `_UnavailableDiagnostics` 或抛错桩
- Fixture / 向量及版本：`tests/common/fakes.py::AppFixture`/`FakeAdapter`（ENV-3）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库 / ENV-2 loopback 测试 HTTP 实例 / ENV-3 provider 进程内 fake（按 Case 需要，见 §4）
- 依赖的测试资产（tests.asset-design 文档）：`FakeAdapter`（`llmtier-unit-fakes`，资产文档已建）

## 3. 输入构造

- 逐参数输入构造：正常请求 + 注入 diagnostics 故障
- 边界/非法取值及理由：正常 vs 故障注入
- 规模 / 时间域（数量、分页、复杂度、观测开销）：O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 正常请求 | 成功结果 |
| 2 | diagnostics 抛错 | 结果不变、无二次鉴权 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`CON-INFER-005`/`R-OBS-03`；人工推导（对照正常路径结果）。**判据语义以设计验证项 `VRC-INF-005` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：注入观测故障后 Responses 返回与正常路径一致；推理路径无鉴权调用点（`http_api.auth` 的三个入口被 patch 为抛错后推理仍完成；`inference.routing`/`responses` 导入不拉入 `http_api.auth`）

## 6. 错误路径、副作用与清理

- 错误出口与表现：无（fail-open 为成功预期）
- 副作用断言与清理：无（观测副作用不改变推理）；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/cases/UT-INF-005.py::InferenceFailOpenTests::test_inference_result_unchanged_when_diagnostic_writes_fail` / `test_usage_ledger_still_measured_when_diagnostic_writes_fail` / `test_upstream_fault_still_surfaces_when_diagnostic_writes_fail`（观测 fail-open）+ `InferenceNoSecondAuthTests::test_inference_path_does_not_call_authenticate` / `test_inference_modules_do_not_import_auth`（推理路径无二次鉴权调用点）；
  `_UnavailableDiagnostics` 降级行为另由 `UT-INF-005.py::UnavailableDiagnosticsUnitTests`、`UT-INF-005.py::UnavailableDiagnosticsTests` 覆盖。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/cases/UT-INF-005.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit`）；执行状态与 Verdict 见 Run 报告 `run-20261001-04`。

