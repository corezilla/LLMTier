<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-INF-010 — Embeddings 分支矩阵

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-INF-010` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-INF-010.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-INF-010`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-INF-010.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-INF-010` / M003 `EmbeddingsService.create` 分支：base64/非有限值/非法维数/空（组装） v0.1.0-draft.1 / VRC-INF-002（inference-design §14 / inference.isd §9.1，inference 0.1.0-draft.1） / VRC-INF-002 / boundary / P0（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：边界值（上限/零/空/刚好满、长度、分页越界）+ 条件边界（主要手段：边界外协作者用进程内 `FakeAdapter`（`ResponsesService._test_adapter`/`EmbeddingsService._test_adapter` seam，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M003-embeddings 四分支
- 要测什么（责任展开）：各分支分别断言：非法 base64→502 `provider_contract_error`；非有限值/非法维数/空向量拒绝；usage→`prompt_tokens`（本 Case 责任：非法 base64/空向量/非有限值三类坏向量均 502；usage 缺失→unknown 不补零）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝inference 组装后向量化分支矩阵与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`embeddings.py::create` 向量归一分支（base64 解码/空/非有限值/usage 缺失）

```text
create(principal, request_id, body)
```

- 初态构造（经公开入口）：`AppFixture`（ENV-1）；向量经 `_RawVectorAdapter`（边界替身）与 loopback 假上游
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-3
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：非法 base64 `"!!!not-base64!!!"`（`encoding_format=base64`）；空向量 `[]`；`[inf,0.1]`；`[nan]`；上游合法 float + base64 请求（解码失败）；无 `usage` 键
- 边界/非法取值及理由：非法 base64/空/非有限值→502 `provider_contract_error`；usage 缺失→账本 unknown 且 tokens NULL
- 规模 / 时间域（数量、分页、复杂度、观测开销）：5 次调用；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 非法 base64 | 502 `provider_contract_error` |
| 2 | 空向量 | 502 |
| 3 | `[inf,...]` / `[nan]` | 均 502 |
| 4 | 上游 float 向量 + base64 请求 | 502（解码失败路径） |
| 5 | 上游不带 `usage` | 200 返回向量；账本 final unknown、`input_tokens=NULL` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：inference 模块设计 §14.2 + 方案 §2.3 b6/b7；按 `create` 向量校验顺序人工推导
- 互斥预期（成功 / 各错误分支）：坏向量四类均 502；好向量放行；usage 缺失不补零

## 6. 错误路径、副作用与清理

- 错误出口与表现：502 `provider_contract_error`（唯一新增码）
- 副作用断言与清理：失败路径账本收敛 unknown

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-INF-010.py`（5 个）：`test_invalid_base64_is_502_contract_error`、`test_empty_vector_rejected`、`test_non_finite_values_rejected`、`test_bad_base64_payload_from_transport_is_502`、`test_usage_missing_is_unknown_not_zero`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-INF-010.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
