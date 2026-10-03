<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-DIAG-007 — fail-open 分支

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-DIAG-007` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-DIAG-007.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-DIAG-007`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-DIAG-007.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-DIAG-007` / M006 fail-open 分支：record_trace/record_latency/capture_snapshot 写失败、cleanup 失败、init 失败（组装） v0.1.0-draft.6 / VRC-DIAG-003（libdiag-design §14 / libdiag.isd §9.1，libdiag 0.1.0-draft.6） / VRC-DIAG-003 / recovery / P1（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：故障注入 + 异常路径回滚 + 状态迁移断言（主要手段：边界外协作者用进程内 `FakeAdapter`（`ResponsesService._test_adapter` seam，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M006-fail-open 分支
- 要测什么（责任展开）：各写入失败不阻断推理；cleanup 失败返回 0；`_UnavailableDiagnostics` 降级（本 Case 责任：四个写入口失败均不抛错并落 warn；`capture_snapshot`→None、`cleanup`→0；推理与开关读不受影响）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝libdiag 组装后观测面写失败的 fail-open与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`libdiag` 各 `record_*`/`cleanup` 的内部 fail-open 与 warn 上报、`app.py::_UnavailableDiagnostics`（已由 UT-API-005 覆盖，本层不重复）

```text
record_trace/capture_snapshot/record_latency/cleanup 写失败时的返回与告警
```

- 初态构造（经公开入口）：`AppFixture` 真实组装（ENV-1）；诊断表经存储面注入 DROP
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-3
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：DROP `trace_events`/`diagnostic_snapshots`/`data_plane_stats`/`data_plane_latency_samples` 后依次调用四个写入口 + `cleanup(7)`；推理对照；`switches()` 读取
- 边界/非法取值及理由：四个写入口均不抛错（`capture_snapshot` 返回 None、`cleanup` 返回 0）；`capture_failed` warn 落日志；推理 200 且输出非空；`switches()` 仍可读
- 规模 / 时间域（数量、分页、复杂度、观测开销）：5 个测试方法；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 丢弃诊断表后写 trace/快照/统计 | 三者均不抛异常 |
| 2 | 查日志 | 存在 `capture_failed` warn |
| 3 | 同条件跑推理 | 200 且 `output` 非空（fail-open） |
| 4 | `cleanup(7)` | 返回 0 且 warn 记录 |
| 5 | `capture_snapshot` 返回值 | None |
| 6 | `switches()` | 仍返回已设置的两开关（读路径独立） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：libdiag 模块设计 §14.3 + 方案 §6.7（`_UnavailableDiagnostics` 降级由 UT-API-005 覆盖，本层不重复登记）；按各写方法的 `try/except + warn` 结构人工推导
- 互斥预期（成功 / 各错误分支）：观测面任何写失败都不外溢；失败可观测（warn）；推理不受影响

## 6. 错误路径、副作用与清理

- 错误出口与表现：无对外错误码（fail-open 不得产生错误）
- 副作用断言与清理：损坏仅限观测表，记账表不受影响

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-DIAG-007.py`（5 个）：`test_write_failures_do_not_raise`、`test_inference_unaffected_by_broken_diagnostics`、`test_cleanup_failure_returns_zero`、`test_capture_snapshot_returns_none_on_write_failure`、`test_switches_still_readable_after_write_failures`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-DIAG-007.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
