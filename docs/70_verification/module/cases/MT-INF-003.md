<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-INF-003 — UsageRecorder 账本组装后失败与用量

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-INF-003` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-10-02` |
| Last Modified Date | `2026-10-02` |
| Template ID | `tests.module-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/module/cases/MT-INF-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-INF-003`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-INF-003.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-INF-003` / M003 inference §9 · `UsageRecorder` 账本（组装） v0.1.0-draft.1 / VRC-INF-003（inference-design §14 / inference.isd §9.1，inference 0.1.0-draft.1） / VRC-INF-003 / recovery / P0（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：故障注入 + 异常路径回滚 + 状态迁移断言（主要手段：边界外协作者用进程内 `FakeAdapter`（`ResponsesService._test_adapter`/`EmbeddingsService._test_adapter` seam，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：迁移：T1、T2、T3
- 要测什么（责任展开）：组装后失败与用量：上游 5xx/超时、usage 缺失→unknown 不补零、账本终态单调推进（本 Case 责任：measured/unknown 两终态互斥；usage 缺失不补零；上游 5xx/超时后义务收敛 final（T1/T2/T3））
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝inference 组装后账本终态与未知不补零与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`usage.py::UsageRecorder.authorize_dispatch`/`bind_backend`/`finish`、`responses.py::create` 异常路径

```text
authorize_dispatch(...); bind_backend(...); finish(principal, request_id, usage, source_override=None)
```

- 初态构造（经公开入口）：`AppFixture` + 真实 `Store`（ENV-1）；上游＝`FakeAdapter`（正常/无 usage/5xx/超时）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-3
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：`FakeAdapter(usage=True)`、`(usage=False)`、`(fail=ApiError(503,...))`、`(fail=TimeoutError)`
- 边界/非法取值及理由：measured 终态 `(measured, provider)`；无 usage→`(unknown, unavailable)` 且 tokens 全 NULL；上游 5xx/超时→unknown 收敛为 final
- 规模 / 时间域（数量、分页、复杂度、观测开销）：4 次请求；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 正常（usage=True） | 账本 final + measured + provider |
| 2 | usage=False | 账本 final + unknown + unavailable，tokens 三项均 `None` |
| 3 | 上游 503 | 抛 503 `provider_unavailable`（retryable），账本 final unknown |
| 4 | 上游 TimeoutError | 异常原样传播（503 映射归 transport，MT-INF-013），账本 final unknown |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：inference 模块设计 §14.3 + 账本契约；按 `finish` 的 `measured` 判定与 NULL 不补零规则人工推导
- 互斥预期（成功 / 各错误分支）：终态三态互斥；未知绝不补零；失败后义务必收敛为 final

## 6. 错误路径、副作用与清理

- 错误出口与表现：上游错误→unknown 收敛（不落半成品）
- 副作用断言与清理：每请求写 obligation + 版本行；head 指向最新版本

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-INF-003.py`（5 个）：`test_measured_finish_is_final`、`test_missing_usage_is_unknown_not_zero`、`test_upstream_5xx_maps_503_and_ledger_unknown`、`test_upstream_timeout_leaves_ledger_unknown`、`test_ledger_advances_across_requests`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-INF-003.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
