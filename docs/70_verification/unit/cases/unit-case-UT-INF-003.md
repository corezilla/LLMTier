<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-INF-003 — 失败与用量记账

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-INF-003` |
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
| Canonical Path | `docs/70_verification/unit/cases/unit-case-UT-INF-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-INF-003`）；责任摘要、分类与优先级以 [单元测试方案 §3](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [inference-design.md](../../../40_module_design/inference-design.md) §14 / ISD [inference.isd.md](../../../50_implementation_design/inference.isd.md) §9.1，设计验证项 `VRC-INF-003`（固定版本 `inference 0.1.0-draft.1`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `INF`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-INF-003` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-INF-003` / `VRC-INF-003`（inference 模块设计 §14 / inference-isd §9.1，inference 0.1.0-draft.1） / `VRC-INF-003` / recovery / P0（[方案清单 §3](../llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：故障注入 + 异常路径恢复（上游 5xx/超时/usage 缺失不补零）
- 要测什么（责任展开）：被测：provider 失败/终态不合法时 `UsageRecorder` 的 unknown 不补零、head 单调、只用记录版本、terminal 唯一校验。
- 明确不测什么 / 失败含义：不测：M-METER 跨模块账本一致性（模块层）；不测真实超时墙钟。失败含义＝失败路径记账/终态校验实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/inference/usage.py::UsageRecorder`（`authorize_dispatch`/`finish`/`page`）；`src/inference/providers/openai.py` 终态校验

```text
authorize_dispatch(principal, request_id, model, endpoint); finish(principal, request_id, usage); page(...)
```

- 初态构造（经公开入口）：`AppFixture`；`test_runtime_snapshot`；provider 失败经 `FakeAdapter(fail=ApiError(503,...))`
- Fixture / 向量及版本：`tests/unit/v03/fakes.py::FakeAdapter`（ENV-3）；`usage.py`
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库 / ENV-2 loopback 测试 HTTP 实例 / ENV-3 provider 进程内 fake（按 Case 需要，见 §4）
- 依赖的测试资产（tests.asset-design 文档）：`FakeAdapter`（`llmtier-unit-fakes`，资产文档已建）

## 3. 输入构造

- 逐参数输入构造：usage 可空；provider_request_id 绑定/解绑定；重复 terminal；terminal 状态不一致
- 边界/非法取值及理由：usage 缺失 vs 存在；版本 v1→v2
- 规模 / 时间域（数量、分页、复杂度、观测开销）：O(记录数)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | authorize 后 finish(None) | unknown 且值 null |
| 2 | finish(usage) | 版本推进、head 替换 |
| 3 | provider 失败 | unknown 不补零 |
| 4 | 重复/状态不一致 terminal | 拒绝 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`RULE-INF-TERMINAL` + M-METER 账本语义；人工推导。**判据语义以设计验证项 `VRC-INF-003` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：unknown 时 `total_tokens is None`；measured 时 `record_version=2`；版本不可变（2 行）；重复 terminal 拒绝

## 6. 错误路径、副作用与清理

- 错误出口与表现：provider 失败不产生 PASS 记录（互斥预期）
- 副作用断言与清理：账本追加不可变版本；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/v03/test_usage.py`（全部 11 个）+ `tests/unit/v03/test_provider_openai.py::test_incomplete_terminal_is_preserved/test_duplicate_terminal_is_rejected/test_terminal_event_status_mismatch_is_rejected` + `tests/unit/v03/test_runtime_snapshot.py`（2 个）（注意：本 Case 的测试函数当前按子句（test case method）映射；若与设计 VRC 不一致，以设计修订回溯后重裁）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/v03/test_usage.py tests/unit/v03/test_provider_openai.py tests/unit/v03/test_runtime_snapshot.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/v03`）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。

