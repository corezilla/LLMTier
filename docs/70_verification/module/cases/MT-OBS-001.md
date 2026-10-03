<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-OBS-001 — 组装后诊断端到端

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-OBS-001` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-OBS-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-OBS-001`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-OBS-001.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-OBS-001` / M005 observability §9 · 诊断端点（组装） v0.1.0-draft.6 / VRC-OBS-001..005（observability-design §14 / observability.isd §9.1，observability 0.1.0-draft.6） / VRC-OBS-001..005 / normal / P1（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：组装后真实调用 + 等价类划分 + 分支覆盖（主要手段：边界外协作者用进程内 `FakeAdapter`（`ResponsesService._test_adapter` seam，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：无（层① 接口行为分母行）
- 要测什么（责任展开）：组装后诊断端到端：经 M001 路由 → M006 `DiagnosticsService`，开关/快照/统计/trace/时间窗全链生效（本 Case 责任：经 M001 路由 → M006 服务，开关/快照/统计/trace/时间窗五面全链生效）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝observability 组装后诊断五面端到端贯通与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`app.py` 诊断路由族、`libdiag/diagnostics.py::DiagnosticsService`

```text
PATCH /v1/diagnostics; POST /v1/responses; GET /v1/diagnostics/{snapshots,stats,traces}, /v1/trace/{id}
```

- 初态构造（经公开入口）：`AppFixture` 真实组装（ENV-1）+ ENV-2；上游＝`FakeAdapter`；开关经公开 `PATCH /v1/diagnostics`
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2 + ENV-3 + ENV-4（注入经公开入口）
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：开两个开关 → 一次推理 → 查 snapshots/stats/traces/单 trace；时间窗内/外各查一次
- 边界/非法取值及理由：开关开启后三面均有行且字段完整；单 trace 的 stages 覆盖 `received`…`completed`；时间窗外为空（stage 位置序不断言，见方案 §7 `G-OBS-STAGE-ORDER-1`）
- 规模 / 时间域（数量、分页、复杂度、观测开销）：1 次推理 + 5 次查询；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `PATCH /v1/diagnostics` 开双开关 | 200 `{snapshots_enabled:true, stats_enabled:true}` |
| 2 | 发一次推理请求 | 200（诊断在观测面记录） |
| 3 | `GET /v1/diagnostics/snapshots` | 1 行且 11 字段完整、`snapshot_type=upstream` |
| 4 | `GET /v1/diagnostics/stats` | 1 个 window，`request_count=1` |
| 5 | `GET /v1/diagnostics/traces` + 单 trace | 1 个 request；stages 含六个阶段；含 snapshot 与 usage 视图（usage `measurement_status=measured`） |
| 6 | 时间窗外查询 | 空（窗口过滤生效） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：observability 模块设计 §14.1–§14.5；按 M001 路由 → M006 服务的字段契约人工推导（stage 位置序见 §4 具名缺口）
- 互斥预期（成功 / 各错误分支）：全链贯通：三面查询均反映同一请求；字段完整；时间窗生效

## 6. 错误路径、副作用与清理

- 错误出口与表现：无（正常路径）
- 副作用断言与清理：观测写入不影响推理返回

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-OBS-001.py`（5 个）：`test_diagnostic_routes_are_served_by_the_m001_handler`、`test_snapshot_row_is_written_by_the_full_chain`、`test_trace_stages_cover_the_chain_and_join_snapshot_and_usage`、`test_time_window_excludes_rows_outside_the_window`、`test_stats_window_records_the_call`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-OBS-001.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
