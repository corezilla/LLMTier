<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-INF-009 — admitted 真/假副作用分支

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-INF-009` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-INF-009.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-INF-009`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-INF-009.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-INF-009` / M003 admitted 真/假副作用分支（组装） v0.1.0-draft.1 / VRC-INF-003（inference-design §14 / inference.isd §9.1，inference 0.1.0-draft.1） / VRC-INF-003 / recovery / P0（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：故障注入 + 异常路径回滚 + 状态迁移断言（主要手段：边界外协作者用进程内 `FakeAdapter`（`ResponsesService._test_adapter`/`EmbeddingsService._test_adapter` seam，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M003-admitted 真/假副作用；迁移：T1
- 要测什么（责任展开）：admitted=True 失败→`usage.finish(source=injected/none)`；admitted=False→无 usage 副作用（E-INF-ADMIT）（本 Case 责任：admitted=True 失败→finish 收敛 final；admitted=False→无 finish 副作用（E-INF-ADMIT，T1））
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝inference 组装后准入结果对账本副作用的分支与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`responses.py::create` 异常处理（E-INF-ADMIT）、`usage.py::finish`

```text
create(...)  # admitted 由 with router.admit 上下文决定
```

- 初态构造（经公开入口）：`AppFixture` + 真实 `Router`（ENV-1）；上游＝`FakeAdapter`
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-3
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：① 准入成功（admitted=True）后适配器 503；② 全部 unhealthy（admitted=False，准入在 yield 前抛）
- 边界/非法取值及理由：True 分支：head 变 final（unknown）；False 分支：head 停留 version 1、`is_final=0`、`source=unavailable`、tokens NULL
- 规模 / 时间域（数量、分页、复杂度、观测开销）：2 次请求；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 准入成功后上游 503 | 账本 `is_final=1`、`unknown` |
| 2 | 全不健康致准入拒绝 | 账本 `is_final=0`、`unknown`、tokens NULL（无 finish 副作用） |
| 3 | 对照：再跑一次 admitted=True 失败 | 终态收敛为 final（与上一条停留态不同） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：inference 模块设计 §14.3 + E-INF-ADMIT；按 `except` 中 `if admitted` 分支人工推导
- 互斥预期（成功 / 各错误分支）：True/False 两分支的账本终态严格不同；无义务泄漏

## 6. 错误路径、副作用与清理

- 错误出口与表现：无新增错误码（复用准入/上游码）
- 副作用断言与清理：False 分支不得写入 final 行

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-INF-009.py`（2 个）：`test_admitted_true_failure_converges_final`、`test_admitted_false_rejection_has_no_finish_side_effect`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-INF-009.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
