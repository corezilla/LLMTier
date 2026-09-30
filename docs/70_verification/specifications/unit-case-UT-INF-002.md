<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-INF-002 — Embeddings 向量化与校验

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-INF-002` |
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
| Canonical Path | `docs/70_verification/specifications/unit-case-UT-INF-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-INF-002`）；责任摘要、分类与优先级以 [单元测试方案 §3](../schemes/llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [inference-design.md](../../40_module_design/inference-design.md) §14 / ISD [inference.isd.md](../../50_implementation_design/inference.isd.md) §9.1，设计验证项 `VRC-INF-002`（固定版本 `inference 0.1.0-draft.1`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `INF`；裁剪依据见 [STD 裁剪清单](../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-INF-002` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-INF-002` / `VRC-INF-002`（inference 模块设计 §14 / inference-isd §9.1，inference 0.1.0-draft.1） / `VRC-INF-002` / boundary / P0（[方案清单 §3](../schemes/llmtier-unit-test-scheme.md)）。
- 要测什么（责任展开）：被测：`EmbeddingsService.create` 正常 float/base64、批数量、逻辑 model、非法维数、未知字段（`unsupported_field`+`param`）、缺字段（`invalid_request`+`param`）、非有限值拒绝、usage→`prompt_tokens`、`_test_adapter` 注入钩子绕过 provider 构造。
- 明确不测什么 / 失败含义：不测：OpenAI 真实 embeddings 协议；不测 M004 能力目录。失败含义＝向量校验/归一实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/inference/embeddings.py::EmbeddingsService.create`

```text
EmbeddingsService.create(principal_id, request_id, body) -> dict
```

- 初态构造（经公开入口）：`AppFixture.seed("Embedding-v1", embedding_capabilities(), "BAAI/bge-m3")`；`_adapter` 替换为 `FakeAdapter`/`Base64Adapter`/`BadAdapter`
- Fixture / 向量及版本：`tests/unit/v03/fakes.py::FakeAdapter`/`embedding_capabilities`（ENV-3）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../plans/llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库 / ENV-2 loopback 测试 HTTP 实例 / ENV-3 provider 进程内 fake（按 Case 需要，见 §4）
- 依赖的测试资产（tests.asset-design 文档）：`FakeAdapter`（`llmtier-unit-fakes`，资产文档已建）

## 3. 输入构造

- 逐参数输入构造：body `{"model":"Embedding-v1","input":"a","dimensions":1024,"encoding_format":"float"}`；批 `[a,b]`；base64；`dimensions=8`；`extra=True`；`{"input":"a"}`（缺 model）；`encoding_format="nope"`；NaN；`_test_adapter` 注入 double
- 边界/非法取值及理由：dimensions 8 vs 1024；float vs base64；batch 1 vs 2
- 规模 / 时间域（数量、分页、复杂度、观测开销）：O(输入数量)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | float 单条/批量 | 长度 1024、条数 |
| 2 | base64 编码 | embedding 为 str |
| 3 | 逻辑 model 返回 | `Embedding-v1` |
| 4 | 非法维数/未知字段/缺字段/非有限值 | ApiError（码与 `param` 分别断言：`unsupported_dimensions`/`unsupported_field`+`param`/`invalid_request`+`param`） |
| 5 | usage 归一 | input_tokens=prompt_tokens |
| 6 | `_test_adapter` 注入 | 真 `_adapter` 返回注入 double、不构造 provider、不触网 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：OpenAPI Embedding 契约 + `RULE-INF-EMBED`；人工推导。**判据语义以设计验证项 `VRC-INF-002` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：维度 1024；base64 为 str；model=`Embedding-v1`；维度错→`unsupported_dimensions`；未知字段→`unsupported_field`+`param`；缺 model→`invalid_request`+`param="model"`；NaN → ApiError；input_tokens 与 usage 一致；`_test_adapter` 注入下不构造真实 provider

## 6. 错误路径、副作用与清理

- 错误出口与表现：无（各分支独立）
- 副作用断言与清理：usage 落库；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/v03/test_embeddings.py::EmbeddingsTests`（全部 16 个；含 `test_test_adapter_hook_bypasses_construction`（CR-EMBEDDINGS-ADAPTER-HOOK）、`test_unknown_field_is_unsupported_field_with_param`、`test_missing_model_is_invalid_request_with_param`、`test_invalid_encoding_format_carries_param`）（注意：本 Case 的测试函数当前按子句（test case method）映射；若与设计 VRC 不一致，以设计修订回溯后重裁）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/v03/test_embeddings.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/v03`）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。

