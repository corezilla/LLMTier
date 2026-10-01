<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-INF-006 — Responses 校验顺序与错误码

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-INF-006` |
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
| Canonical Path | `docs/70_verification/unit/cases/UT-INF-006.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-INF-006`）；责任摘要、分类与优先级以 [单元测试方案 §3](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [inference](../../../40_module_design/inference-design.md) §14 / ISD [inference.isd.md](../../../50_implementation_design/inference.isd.md) §9.1，设计验证项 `VRC-INF-001`（固定版本 `inference 0.1.0-draft.1`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `inference`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-INF-006` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-INF-006` / M003 inference §14.1 · `ResponsesService._validate` v0.1.0-draft.1 / `VRC-INF-001` / negative / P0（[方案清单 §3](../llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（校验顺序与码）（主要手段：直接调用 + 冻结向量 + 替身注入）
- 要测什么（责任展开）：被测：`ResponsesService._validate` 的校验顺序与错误码——未知字段/禁字段→`unsupported_field`（`param`=首个违规字段名，系统 §7.8 ERR-REQ-FIELD）；`tools` 无能力→`unsupported_request`；`max_output_tokens` 范围/布尔→`invalid_request`；responses 能力 false→`unsupported_model`。
- 明确不测什么 / 失败含义：不测：成功归一（UT-INF-001）；不测 provider 协议 wire。失败含义＝校验顺序或错误码实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/inference/responses.py::ResponsesService._validate`（`ALLOWED_FIELDS` 白名单、能力检查、`max_output_tokens` 范围）

```text
_validate(body, caps)  # 顺序：required/stream-store → unknown fields → responses cap → tools → max_output_tokens
```

- 初态构造（经公开入口）：`AppFixture().seed()`；`service._adapter = lambda _: FakeAdapter(...)`（ENV-3）
- Fixture / 向量及版本：`tests/unit/cases/UT-INF-006.py::ResponsesValidationGapTests`；`fakes.py::AppFixture`（ENV-1）/`FakeAdapter`（ENV-3）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库 / ENV-3 provider 进程内 fake
- 依赖的测试资产（tests.asset-design 文档）：`FakeAdapter`（`llmtier-unit-fakes`，资产文档已建）

## 3. 输入构造

- 逐参数输入构造：未知字段 body（如 `bogus`）；禁字段 body（`previous_response_id`）；`tools`+无 tools 能力；`max_output_tokens=0`/超能力上限/布尔；无 responses 能力 model
- 边界/非法取值及理由：各错误类互斥；`max_output_tokens` 合法区间接受
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单请求，O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 未知字段 / 禁字段 | 400 `unsupported_field` + `param`=违规字段名 |
| 2 | `tools` 无能力 | 400 `unsupported_request` |
| 3 | `max_output_tokens` 越界/布尔 | 400 `invalid_request` |
| 4 | responses 能力 false | 400 `unsupported_model` |
| 5 | 合法区间 | 接受 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`RULE-INF-VALIDATE` 校验顺序 + OpenAPI 错误码 + 人工推导；不调用被测复算。**判据语义以设计验证项 `VRC-INF-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：未知字段/禁字段`unsupported_field`（`param`=违规字段名）；tools 无能力`unsupported_request`；max tokens 非法`invalid_request`；无 responses 能力`unsupported_model`；合法接受；互斥

## 6. 错误路径、副作用与清理

- 错误出口与表现：400 各错误码独立；无第三态
- 副作用断言与清理：拒绝路径不产生 usage/落库；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/cases/UT-INF-006.py::ResponsesValidationGapTests::test_unknown_field_is_400_unsupported_field`（`param="bogus"`）/ `test_forbidden_field_carries_param`（`param="previous_response_id"`）/ `test_tools_without_capability_is_400_unsupported_request` / `test_max_output_tokens_zero_is_400` / `test_max_output_tokens_non_integer_bool_is_400` / `test_max_output_tokens_over_capability_is_400` / `test_max_output_tokens_within_range_accepted` / `test_unsupported_responses_capability_is_400_unsupported_model`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/cases/UT-INF-006.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/cases/UT-INF-006.py`）；执行状态与 Verdict 见 Run 报告 `run-20261001-04`。
