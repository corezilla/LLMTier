<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-INF-007 — Embeddings 失败分支与维度错误码

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-INF-007` |
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
| Canonical Path | `docs/70_verification/unit/cases/UT-INF-007.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-INF-007`）；责任摘要、分类与优先级以 [单元测试方案 §6](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [inference](../../../40_module_design/inference-design.md) §14 / ISD [inference.isd.md](../../../50_implementation_design/inference.isd.md) §9.1，设计验证项 `VRC-INF-002`（固定版本 `inference 0.1.0-draft.1`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `inference`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-INF-007` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-INF-007` / M003 inference §14.2 · `EmbeddingsService.create` 分支 v0.1.0-draft.1 / `VRC-INF-002` / negative / P1（[方案清单 §6](../llmtier-unit-test-scheme.md)）。
- **测试方法（§2.1 方法表行）**：错误猜测 + 反例驱动（非法 base64/维数/空向量）（主要手段：直接调用 + 冻结向量 + 替身注入）
- 要测什么（责任展开）：被测：`EmbeddingsService.create` 对非法 base64 → 502 `provider_contract_error`；空向量 → 502 `provider_contract_error`；`unsupported_dimensions` 码与 param 断言。
- 明确不测什么 / 失败含义：不测：正常/base64 成功路径（UT-INF-002）；不改写 provider 协议。失败含义＝向量失败分支或错误码实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/inference/embeddings.py::EmbeddingsService.create`（对 provider 返回的解码/维度校验）

```text
EmbeddingsService.create(principal_id, request_id, body) -> dict
```

- 初态构造（经公开入口）：`AppFixture().seed()`；`service` 注入本地 `Base64Adapter`/`BadAdapter`（ENV-3）
- Fixture / 向量及版本：`tests/unit/cases/UT-INF-007.py::EmbeddingsFailureGapTests`；`fakes.py::AppFixture`（ENV-1）/`FakeAdapter`（ENV-3）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库 / ENV-3 provider 进程内 fake
- 依赖的测试资产（tests.asset-design 文档）：`FakeAdapter`（`llmtier-unit-fakes`，资产文档已建）

## 3. 输入构造

- 逐参数输入构造：返回非法 base64 的 adapter；返回空向量的 adapter；维度与请求不符的 adapter
- 边界/非法取值及理由：非法解码/空向量/维度不符各分支互斥
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单请求，O(向量数)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 非法 base64 | 502 `provider_contract_error` |
| 2 | 空向量 | 502 `provider_contract_error` |
| 3 | 维度不符 | 断言 `unsupported_dimensions` 码与 `param` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`RULE-INF-EMBED` + OpenAPI 错误码 + 人工推导；不调用被测复算。**判据语义以设计验证项 `VRC-INF-002` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：非法 base64/空向量 502 `provider_contract_error`；维度不符 `unsupported_dimensions`；互斥

## 6. 错误路径、副作用与清理

- 错误出口与表现：502 `provider_contract_error` / `unsupported_dimensions`；无第三态
- 副作用断言与清理：失败路径无有效向量落库；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/cases/UT-INF-007.py::EmbeddingsFailureGapTests::test_invalid_base64_is_502_provider_contract_error` / `test_empty_vector_is_502_provider_contract_error` / `test_unsupported_dimensions_code_and_param` / `test_unknown_model_is_404_model_not_found`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/cases/UT-INF-007.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/cases/UT-INF-007.py`）；执行状态与 Verdict 见 Run 报告 `run-20261001-04`。
