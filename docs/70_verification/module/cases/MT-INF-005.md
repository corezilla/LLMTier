<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-INF-005 — 校验顺序四出口

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-INF-005` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-INF-005.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-INF-005`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-INF-005.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-INF-005` / M003 校验顺序四出口：缺字段/unsupported_request/禁字段/未知字段（组装） v0.1.0-draft.1 / VRC-INF-001（inference-design §14 / inference.isd §9.1，inference 0.1.0-draft.1） / VRC-INF-001 / negative / P0（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：错误猜测 + 反例驱动（非法字段/凭据/引用/类型/顺序）+ 判定表组合（主要手段：边界外协作者用进程内 `FakeAdapter`（`ResponsesService._test_adapter`/`EmbeddingsService._test_adapter` seam，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M003-校验四出口
- 要测什么（责任展开）：按顺序分别断言 `invalid_request`/`unsupported_request`/`unsupported_field`(禁)/`unsupported_field`(未知)，`param` 指向违规字段（本 Case 责任：缺字段/形态/禁字段/未知字段四出口按实现顺序命中，`param` 指向违规字段）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝inference 组装后请求校验顺序与四出口与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`responses.py::ResponsesService.create` 前置校验链

```text
create(principal, request_id, body)
```

- 初态构造（经公开入口）：`AppFixture`（ENV-1）；上游＝`FakeAdapter`（校验先于路由，不应被触达）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-3
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：依次去掉 `model`/`input`/`stream`/`store`；`stream:false`/`store:true`；`prompt_cache_key`＋未知字段；仅未知字段
- 边界/非法取值及理由：`param` 指向首个违规字段；禁字段优先于未知字段；形态校验先于字段白名单
- 规模 / 时间域（数量、分页、复杂度、观测开销）：9 次调用；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 分别缺 4 个必填字段 | 均 400 `invalid_request`，`param` 为该字段名 |
| 2 | `stream:false` / `store:true` | 400 `unsupported_request` |
| 3 | 禁字段 + 未知字段同现 | 400 `unsupported_field`，`param=prompt_cache_key`（禁字段优先） |
| 4 | 仅未知字段 | 400 `unsupported_field`，`param=mystery` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：inference 模块设计 §14.1 + 校验顺序契约；按 `create` 中四个 `require` 的先后顺序人工推导
- 互斥预期（成功 / 各错误分支）：四出口码与 `param` 精确；顺序语义可验证

## 6. 错误路径、副作用与清理

- 错误出口与表现：400 `invalid_request` / `unsupported_request` / `unsupported_field`（禁/未知各一次）
- 副作用断言与清理：校验失败不写账本（`authorize_dispatch` 在校验之后）

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-INF-005.py`（4 个）：`test_missing_field_is_invalid_request_with_param`、`test_wrong_stream_store_shape_is_unsupported_request`、`test_forbidden_field_beats_unknown_field`、`test_unknown_field_is_unsupported_field`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-INF-005.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
