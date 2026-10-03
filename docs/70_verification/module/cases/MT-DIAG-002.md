<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-DIAG-002 — 注入配置与命中优先级

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-DIAG-002` |
| Document Version | `0.1.0-draft.3` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-DIAG-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-DIAG-002`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-DIAG-002.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-DIAG-002` / M006 libdiag §9 · 注入配置（组装） v0.1.0-draft.6 / VRC-DIAG-004（libdiag-design §14 / libdiag.isd §9.1，libdiag 0.1.0-draft.6） / VRC-DIAG-004 / negative / P0（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：错误猜测 + 反例驱动（非法字段/凭据/引用/类型/顺序）+ 判定表组合（主要手段：边界外协作者用进程内 `FakeAdapter`（`ResponsesService._test_adapter` seam，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：无（层① 接口行为分母行）
- 要测什么（责任展开）：组装后注入：六类注入、非法类型 400、命中确定、优先级、traces 时间窗分页（本 Case 责任：六类注入读回保真；前置优先级确定且与流阶段互不干扰；命中可观测；traces 时间窗分页）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝libdiag 组装后注入配置面与优先级与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`libdiag/injections.py::InjectionDiagnostics.set_injections`/`injections`/`enabled_injection`/`enabled_stream_injection`、`traces.py::traces`

```text
set_injections(deployment_id, items, conn=None) -> list; enabled_injection/enabled_stream_injection(deployment_id)
```

- 初态构造（经公开入口）：`AppFixture` 真实组装（ENV-1）；注入经公开 `set_injections`；推理上游＝`FakeAdapter`
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-3 + ENV-4
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：六类注入一次全配（冻结参数：`error_body="boom"/"down"`、`delay_ms=5`、`retry_after_sec=1`、`stream_terminate_after_events=1`、`malformed_after_events=1` 且 `malformed_event_type="invalid_json"`）；四个前置注入并存（查优先级）；`enabled=false`；`enabled=true` 命中推理；未知类型；3 条 trace 分页（limit=2）与时间窗外查询
- 边界/非法取值及理由：六类读回一致（含 `deployment_id`/`enabled`/`updated_at`）；前置优先级 `fault_502` > `fault_503` > `rate_limit` > `delay`；流阶段注入与前置阶段互不干扰；`enabled=false` 不命中；命中可观测（502 `provider_failure`）；分页 2+1 且不重叠；时间窗外为空
- 规模 / 时间域（数量、分页、复杂度、观测开销）：5 次配置/注入 + 3 条 trace；O(6)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 一次配置六类注入 | 读回 6 条，类型集合与输入一致，字段完整 |
| 2 | 四个前置注入并存 | `enabled_injection()` 返回 `fault_502`；`enabled_stream_injection()` 为 None |
| 3 | `enabled=false` 的 `fault_502` | `enabled_injection()` 为 None；推理 completed |
| 4 | `enabled=true` 的 `fault_502` | 推理抛 502 `provider_failure`（注入命中） |
| 5 | 未知类型 | 400 `invalid_injection`（`param=type`） |
| 6 | 3 条 trace 分页 | 2 条 + `has_more`，第二页 1 条且不重叠 |
| 7 | 时间窗外查 traces | 空列表 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：libdiag 模块设计 §14.4 + 方案 §6.3 K4；按 `_PRE_CALL`/`_STREAM` 优先级序与分页窗口语义人工推导
- 互斥预期（成功 / 各错误分支）：六类配置保真；优先级确定；命中可观测；分页与时间窗正确

## 6. 错误路径、副作用与清理

- 错误出口与表现：400 `invalid_injection`（唯一）
- 副作用断言与清理：注入配置为 deployment 级，不影响其它 deployment

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-DIAG-002.py`（6 个）：`test_all_six_injection_types_configure_and_read_back`、`test_pre_call_priority_fault_502_first`、`test_disabled_injection_does_not_hit`、`test_enabled_injection_hits_in_assembled_inference`、`test_unknown_injection_type_is_400`、`test_traces_time_window_and_paging`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-DIAG-002.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
