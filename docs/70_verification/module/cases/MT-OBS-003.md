<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-OBS-003 — 诊断查询面字段与存储不可读

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-OBS-003` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-OBS-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-OBS-003`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-OBS-003.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-OBS-003` / M005 查询分支：快照/统计字段 + 去 query + 存储不可读 503（组装） v0.1.0-draft.6 / VRC-OBS-002（observability-design §14 / observability.isd §9.1，observability 0.1.0-draft.6） / VRC-OBS-002 / boundary / P1（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：边界值（上限/零/空/刚好满、长度、分页越界）+ 条件边界（主要手段：边界外协作者用进程内 `FakeAdapter`（`ResponsesService._test_adapter` seam，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M005-查询三分支
- 要测什么（责任展开）：字段完整、URL 去 query（`?token=` 不落库）、存储不可读→503 不伪装空页（本 Case 责任：三面字段完整；窗口/limit 校验一致；query 脱敏到位；存储不可读→503 不伪装空页）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝observability 组装后查询面字段、脱敏与存储故障与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`app.py::_store_read`（诊断查询面的存储读保护）、`libdiag` 快照/统计/trace 视图

```text
GET /v1/diagnostics/{snapshots,stats,traces}; 存储不可读注入
```

- 初态构造（经公开入口）：`AppFixture` 真实组装（ENV-1）+ ENV-2；坏状态经存储面注入（DROP 诊断表 / 文件权限）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2 + ENV-3
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：快照/统计/trace 三页字段；`limit` 夹取与非整数；stats 缺 `since/until`；endpoint 带 `?token=`；DROP 诊断表；`chmod 000` 库文件
- 边界/非法取值及理由：三页字段集完整；`limit` 夹取 [1,500]；非整数→400 `invalid_request`；缺窗→400；`upstream_url` 不含 query、`token=` 不出现在任何诊断页；存储不可读→503 `usage_store_unavailable`（非空页，见 §7 `O-OBS-STORECODE-1`）
- 规模 / 时间域（数量、分页、复杂度、观测开销）：10 个测试方法；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 快照/统计/trace 三页逐字段断言 | 字段集与契约一致 |
| 2 | `limit` 取 0/99999/非整数 | 夹取到 [1,500] / 400 `invalid_request` |
| 3 | stats 缺 `since` 或 `until` | 400 `invalid_request` |
| 4 | endpoint 带 `?token=secret` 后推理 | 快照 `upstream_url` 无 query；两页与单 trace 均不含 `secret` |
| 5 | DROP 诊断表后查查询面 | 503 `usage_store_unavailable`（非空页） |
| 6 | `chmod 000` 库文件后查开关面 | 503（库整体不可用） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：observability 模块设计 §14.2 + 方案 §2.3 a27；按 `_store_read` 的异常映射与三视图字段契约人工推导
- 互斥预期（成功 / 各错误分支）：字段完整；窗口/limit 校验一致；query 脱敏到位；存储故障显式 503 不静默

## 6. 错误路径、副作用与清理

- 错误出口与表现：400 `invalid_request` / 503 `usage_store_unavailable`
- 副作用断言与清理：查询不改库；故障注入在 finally 还原

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-OBS-003.py`（10 个）：`test_snapshot_item_carries_every_documented_field`、`test_stats_window_carries_every_documented_field`、`test_trace_view_carries_every_documented_field`、`test_limit_is_clamped_to_the_documented_range`、`test_non_integer_limit_is_400`、`test_stats_without_since_or_until_is_400`、`test_snapshot_upstream_url_drops_the_query_string`、`test_token_never_reaches_the_diagnostics_pages`、`test_dropped_diagnostics_tables_are_503_not_an_empty_page`、`test_unreadable_database_file_is_503_not_an_empty_page`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-OBS-003.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
