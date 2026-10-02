<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-DIAG-005 — stream_wrapper 三态

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-DIAG-005` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-DIAG-005.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-DIAG-005`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-DIAG-005.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-DIAG-005` / M006 `stream_wrapper` 三态：透传/早停/畸形帧（组装） v0.1.0-draft.6 / VRC-DIAG-004（libdiag-design §14 / libdiag.isd §9.1，libdiag 0.1.0-draft.6） / VRC-DIAG-004 / boundary / P1（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：边界值（上限/零/空/刚好满、长度、分页越界）+ 条件边界（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M006-stream_wrapper 三态；组合：K4、K4
- 要测什么（责任展开）：无注入→透传；`stream_terminate`→到点 return；`malformed_event`→到点发畸形帧并 return（本 Case 责任：无注入透传；`stream_terminate` 到点 return；`malformed_event` 到点发畸形帧后 return；阈值精确到帧）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝libdiag 组装后流阶段注入三态与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`libdiag/stream.py::stream_wrapper`、`injections.py::enabled_stream_injection`

```text
stream_wrapper(deployment_id, base_stream) -> Iterable[bytes]
```

- 初态构造（经公开入口）：`AppFixture` 真实组装（ENV-1）；流阶段注入经公开 `set_injections`
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-4
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：基准流 `[a,b,c,[DONE]]` 四帧；`stream_terminate_after_events=2/1`；`malformed_event{malformed_after_events:2, invalid_json}`；`enabled=false`；注入配置在另一 deployment
- 边界/非法取值及理由：无注入逐帧原样透传；`stream_terminate=2` 恰出前 2 帧且无 `[DONE]`；阈值 1 恰出 1 帧；`malformed_event=2` 在第 2 帧后追加畸形帧（`response.malformed`）并停止、无 `[DONE]`；`enabled=false` 与他 deployment 注入均不生效
- 规模 / 时间域（数量、分页、复杂度、观测开销）：6 个测试方法；4 帧基准；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 无注入 | 输出与输入逐帧相等 |
| 2 | `stream_terminate=2` | 恰前 2 帧，拼接后无 `[DONE]` |
| 3 | `stream_terminate=1` | 恰 1 帧 |
| 4 | `malformed_event`（2 帧后） | 前 2 帧 + 1 畸形帧（`response.malformed`），无 `[DONE]` |
| 5 | `stream_terminate` 但 `enabled=false` | 全帧透传 |
| 6 | 注入配在 Embedding-v1，查 Senior | 全帧透传 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：libdiag 模块设计 §14.4 + 方案 §3.3 K4 流阶段行；按 `stream_wrapper` 的两个提前 `return` 位置人工推导
- 互斥预期（成功 / 各错误分支）：三态互斥；阈值精确到帧；畸形帧内容可辨

## 6. 错误路径、副作用与清理

- 错误出口与表现：无错误出口（提前 return 不抛错）
- 副作用断言与清理：包装器不消费/改写上游帧（除注入的畸形帧）

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-DIAG-005.py`（6 个）：`test_no_injection_passes_through_unchanged`、`test_stream_terminate_stops_at_configured_event`、`test_stream_terminate_default_threshold_is_one`、`test_malformed_event_appends_broken_frame_and_stops`、`test_disabled_stream_injection_passes_through`、`test_other_deployment_injection_does_not_affect`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-DIAG-005.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
