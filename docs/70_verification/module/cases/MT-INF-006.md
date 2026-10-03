<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-INF-006 — 能力档 × 请求形态

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-INF-006` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-10-02` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.module-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/module/cases/MT-INF-006.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-INF-006`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-INF-006.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-INF-006` / M003 能力分支：responses=false / tools 无能力 / max_output_tokens 越界（组装） v0.1.0-draft.1 / VRC-INF-001（inference-design §14 / inference.isd §9.1，inference 0.1.0-draft.1） / VRC-INF-001 / negative / P0（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：错误猜测 + 反例驱动（非法字段/凭据/引用/类型/顺序）+ 判定表组合（主要手段：边界外协作者用进程内 `FakeAdapter`（`ResponsesService._test_adapter`/`EmbeddingsService._test_adapter` seam，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M003-能力三分支；组合：K5
- 要测什么（责任展开）：`unsupported_model` / `unsupported_request`(tools) / `invalid_request`(max 范围/布尔) 三分支（本 Case 责任：K5 四行组合命中：能力拒绝与数值边界；类型守卫（布尔被排除））
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝inference 组装后能力档与请求形态组合与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`responses.py::create` 能力校验段（responses/tools/max_output_tokens）

```text
create(principal, request_id, body)  # capabilities 取自 service_levels
```

- 初态构造（经公开入口）：`AppFixture` + 真实 `Registry`（各 tier 能力经公开入口绑定）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-3
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：空 tier（`responses=false`）；`tools` 能力关的 tier；`max_output_tokens` 上限 100 的 tier（值 0/-1/101/"50"/`True`）
- 边界/非法取值及理由：空 tier→400 `unsupported_model`（先于准入）；tools 不支持→400 `unsupported_request`（`param=tools`）；越界/非整数→400 `invalid_request`（`param=max_output_tokens`）
- 规模 / 时间域（数量、分页、复杂度、观测开销）：8 次调用；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 空 tier `Junior` | 400 `unsupported_model`，`param=model` |
| 2 | `tools` 关的 tier 带 tools | 400 `unsupported_request`，`param=tools` |
| 3 | 上限 100 的 tier 传 0/-1/101 | 均 400 `invalid_request`（`param=max_output_tokens`） |
| 4 | 传字符串 `"50"` / 布尔 `True` | 均 400 `invalid_request`（布尔被显式排除） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：方案 §6.3 K5 + inference 模块设计 §14.1；按能力键判定与类型守卫人工推导
- 互斥预期（成功 / 各错误分支）：K5 四行全部命中；类型与范围判据互斥

## 6. 错误路径、副作用与清理

- 错误出口与表现：400 `unsupported_model` / `unsupported_request` / `invalid_request`
- 副作用断言与清理：能力拒绝不写账本

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-INF-006.py`（4 个）：`test_responses_false_is_unsupported_model`、`test_tools_without_capability_is_unsupported_request`、`test_max_output_tokens_out_of_range`、`test_max_output_tokens_non_integer_rejected`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-INF-006.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
