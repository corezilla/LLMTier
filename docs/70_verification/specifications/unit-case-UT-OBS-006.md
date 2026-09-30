<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-OBS-006 — 快照 URL 脱敏与存储不可读 503

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-OBS-006` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-09-30` |
| Template ID | `tests.unit-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/unit-case-UT-OBS-006.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-OBS-006`）；责任摘要、分类与优先级以 [单元测试方案 §3](../schemes/llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [observability](../../40_module_design/observability-design.md) §14 / ISD [observability.isd.md](../../50_implementation_design/observability.isd.md) §9.1，设计验证项 `VRC-OBS-002`（固定版本 `observability 0.1.0-draft.6`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `observability`；裁剪依据见 [STD 裁剪清单](../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-OBS-006` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-OBS-006` / M005 observability §14.2 · 快照 URL 脱敏 v0.1.0-draft.6 / `VRC-OBS-002` / security / P1（[方案清单 §3](../schemes/llmtier-unit-test-scheme.md)）。
- 要测什么（责任展开）：被测：快照/轨迹端到端 URL 去 query（`?token=` 不落库）；查询存储不可读 → 503 `usage_store_unavailable`，不伪装空页。
- 明确不测什么 / 失败含义：不测：统计口径/百分位（UT-DIAG-002/005）；不测浏览器呈现（G-UT-4）。失败含义＝URL 脱敏或存储失败显式化实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/libdiag/snapshots.py`（`upstream_url` 去 query）与 `src/http_api/app.py::Handler._store_read`（`sqlite3.Error`→503 `usage_store_unavailable`）

```text
DiagnosticsService.capture_snapshot(...); Handler._store_read(fn, ...) -> 200 | 503
```

- 初态构造（经公开入口）：`AppFixture().seed()`；带 `?token=` 的上游调用；patch 查询存储抛 `sqlite3.OperationalError`（ENV-1+ENV-2）
- Fixture / 向量及版本：`tests/unit/v03/test_observability_gaps.py::SnapshotRedactionTests`/`DiagnosticsAvailabilityTests`；`fakes.py::AppFixture`（ENV-1）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../plans/llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库 / ENV-2 loopback 测试 HTTP 实例
- 依赖的测试资产（tests.asset-design 文档）：无（真实实现）

## 3. 输入构造

- 逐参数输入构造：上游 URL 含 `?token=…`；patch 使查询存储不可读
- 边界/非法取值及理由：去 query 后不含 secret；503 而非空页
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单请求，O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 上游调用带 `?token=` | 落库 URL 无 query、无 token |
| 2 | trace stage URL | 同样去 query |
| 3 | 存储不可读查快照 | 503 `usage_store_unavailable`（非空页） |
| 4 | 存储正常读开关 | 200 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`RULE-OBS-REDACT` + `T-API-03` 503 语义 + 人工推导；不调用被测复算。**判据语义以设计验证项 `VRC-OBS-002` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：URL 去 query（token 不落库）；存储不可读 503 不空页；开关读 200；互斥

## 6. 错误路径、副作用与清理

- 错误出口与表现：503 `usage_store_unavailable`；无第三态
- 副作用断言与清理：脱敏后的 URL 落库（隔离库）；loopback 实例清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/v03/test_observability_gaps.py::SnapshotRedactionTests::test_query_secret_is_not_stored_in_snapshot` / `test_trace_stage_url_also_stripped` / `DiagnosticsAvailabilityTests::test_snapshots_store_failure_is_503_not_empty_page` / `test_switches_read_still_200`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/v03/test_observability_gaps.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/v03/test_observability_gaps.py`）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。
