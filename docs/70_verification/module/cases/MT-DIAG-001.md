<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-DIAG-001 — DiagnosticsService 记录与查询

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-DIAG-001` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-DIAG-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-DIAG-001`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-DIAG-001.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-DIAG-001` / M006 libdiag §9 · `DiagnosticsService` 记录与查询（组装） v0.1.0-draft.6 / VRC-DIAG-002（libdiag-design §14 / libdiag.isd §9.1，libdiag 0.1.0-draft.6） / VRC-DIAG-002 / boundary / P1（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：边界值（上限/零/空/刚好满、长度、分页越界）+ 条件边界（主要手段：边界外协作者用进程内 `FakeAdapter`（`ResponsesService._test_adapter` seam，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：迁移：T9
- 要测什么（责任展开）：组装后记录与查询：trace/快照/统计字段、URL 去 query、summary 截断、百分位、7 天清理（本 Case 责任：trace/快照/统计字段完整；summary 截断 256；百分位与错误分类数值精确；7 天清理）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝libdiag 组装后观测记录与查询面数值契约与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`libdiag/traces.py`、`snapshots.py`、`stats.py`、`retention.py`、`common.py::percentile`

```text
record_trace(...); capture_snapshot(...) -> str|None; record_latency(...); stats(since, until, ...); cleanup(days=7) -> int
```

- 初态构造（经公开入口）：`AppFixture` 真实组装（ENV-1）；开关经公开 `set_switches`；旧行经存储面注入（回溯时间戳）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-3
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：trace 视图；未知 request_id；endpoint 带 query；600 字 `error_summary`（`http_status=None`）；5 条延迟样本；404/502/None 三种状态码；回溯 7 天前的快照/统计/样本
- 边界/非法取值及理由：trace 含 stages+snapshot+usage；`error_summary` 截断 256 字节且 `snapshot_type=error`；`percentile`（n=5 → p50 第 3 位、p95 第 5 位）；`None`→`upstream_error` 计入 5xx；`cleanup(7)` 删旧留新
- 规模 / 时间域（数量、分页、复杂度、观测开销）：5 延迟样本 + 1 快照 + 回溯 3 行；O(n)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 跑一次推理后 `trace(request_id)` | stages 非空（首 stage ∈ {received, validated}）、snapshot 非空、usage measured |
| 2 | `trace("req_missing")` | 404 `not_found` |
| 3 | endpoint 带 `?token=secret123` 后推理 | 快照 `upstream_url` 无 query |
| 4 | `capture_snapshot(..., http_status=None, error_summary='e'*600)` | `error_summary` 256 字节、`snapshot_type=error`、`http_status=None` |
| 5 | 5 条延迟 10..50 + 查 stats | `request_count=5`、`error_count=0`、`p50=30`、`p95=50`、`min=10`、`max=50`、`sum=150`、`status_breakdown={'200':5}` |
| 6 | 404/502/None 各一条后查 stats | `error_4xx_count=1`、`error_5xx_count=2` |
| 7 | 回溯旧行后 `cleanup(7)` | 删除 ≥2 行；快照页与 stats 窗口均空 |
| 8 | 新行 `cleanup(7)` | 返回 0 且行仍在 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：libdiag 模块设计 §14.2 + 保留期契约；按 `percentile` 的 rank 计算与 `cleanup` 的 cutoff 比较人工推导
- 互斥预期（成功 / 各错误分支）：记录/查询三面字段完整；截断、百分位、错误分类、保留期四项数值精确

## 6. 错误路径、副作用与清理

- 错误出口与表现：404 `not_found`（未知 trace）
- 副作用断言与清理：写入失败 fail-open（见 MT-DIAG-007）

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-DIAG-001.py`（8 个）：`test_trace_view_carries_stages_snapshot_and_usage`、`test_trace_unknown_request_is_404`、`test_snapshot_fields_complete_and_url_without_query`、`test_error_summary_truncated_to_256_bytes`、`test_stats_percentiles_and_status_breakdown`、`test_stats_error_classification`、`test_cleanup_removes_rows_older_than_window`、`test_cleanup_keeps_recent_rows`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-DIAG-001.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
