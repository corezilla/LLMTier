<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-MGMT-004 — 分页与范围清空

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-MGMT-004` |
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
| Canonical Path | `docs/70_verification/unit/cases/UT-MGMT-004.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-MGMT-004`）；责任摘要、分类与优先级以 [单元测试方案 §3](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [management-design.md](../../../40_module_design/management-design.md) §14 / ISD [management.isd.md](../../../50_implementation_design/management.isd.md) §9.1，设计验证项 `VRC-MGMT-004`（固定版本 `management 0.1.0-draft.2`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `MGMT`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-MGMT-004` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-MGMT-004` / `VRC-MGMT-004`（management 模块设计 §14 / management-isd §9.1，management 0.1.0-draft.2） / `VRC-MGMT-004` / boundary / P0（[方案清单 §3](../llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：边界值（分页首屏/更正/过期 cursor）
- 要测什么（责任展开）：被测：用量查询分页 cursor 首屏冻结、cursor 过期/跨 principal 400/403、范围清空计数一致；admin cursor 首屏快照与跨 principal 绑定（畸形 cursor 与摘要绑定归 UT-MGMT-009 细化）。
- 明确不测什么 / 失败含义：不测：账本写入（M003）；不测 HTTP 层；不测 cursor TTL 过期/畸形解析/摘要绑定（由 UT-MGMT-009）。失败含义＝分页快照/清空范围实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/management/admin.py::page`；`src/inference/usage.py::page/reset_usage`

```text
page(items, principal, kind, cursor, limit); usage.page(...); usage.reset_usage(...)
```

- 初态构造（经公开入口）：`AppFixture`（隔离库）
- Fixture / 向量及版本：`tests/unit/v03/fakes.py::AppFixture`
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库 / ENV-2 loopback 测试 HTTP 实例 / ENV-3 provider 进程内 fake（按 Case 需要，见 §4）
- 依赖的测试资产（tests.asset-design 文档）：无（真实实现）

## 3. 输入构造

- 逐参数输入构造：首屏后新增记录；cursor 过期/跨 principal；范围清空
- 边界/非法取值及理由：limit 边界；cursor 绑定
- 规模 / 时间域（数量、分页、复杂度、观测开销）：O(记录数)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | page 形状/limit/has_more | 分页字段 |
| 2 | cursor 续页 | 下一条 id |
| 3 | cursor 跨 principal | ApiError |
| 4 | 用量快照冻结 | 旧页稳定 |
| 5 | 范围清空 | 计数一致 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`RULE-MGMT-SNAPSHOT`/`CON-METER-004`；人工推导。**判据语义以设计验证项 `VRC-MGMT-004` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：首屏快照冻结；跨 principal cursor 拒绝（`cursor_expired`）；范围清空后计数与范围一致

## 6. 错误路径、副作用与清理

- 错误出口与表现：无（分支互斥）
- 副作用断言与清理：清空为显式变更（按 VRC 预期）；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/v03/test_admin.py::test_page_shape/test_page_limit/test_page_cursor/test_cursor_principal_bound/test_first_page_snapshot_is_frozen` + `tests/unit/v03/test_usage.py::test_snapshot_is_stable/test_cursor_filter_mismatch/test_invalid_window` + `tests/unit/v03/test_admin_stats.py`（5 个）（注意：本 Case 的测试函数当前按子句（test case method）映射；若与设计 VRC 不一致，以设计修订回溯后重裁）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/v03/test_admin.py tests/unit/v03/test_usage.py tests/unit/v03/test_admin_stats.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/v03`）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。

