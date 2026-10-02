<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-MGMT-009 — usage 分页 cursor 四态

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-MGMT-009` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-MGMT-009.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-MGMT-009`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-MGMT-009.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-MGMT-009` / M004 分页 cursor 四态：none/expired/cross-principal/filter-mismatch（组装） v0.1.0-draft.3 / VRC-MGMT-004（management-design §14 / management.isd §9.1，management 0.1.0-draft.3） / VRC-MGMT-004 / boundary / P0（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：边界值（上限/零/空/刚好满、长度、分页越界）+ 条件边界（主要手段：边界外协作者用进程内 `FakeAdapter`（`ResponsesService._test_adapter` seam，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M004-cursor 四态；组合：K3
- 要测什么（责任展开）：无 cursor 首页；过期→400 `cursor_expired`；跨 principal→403；过滤不符→400；旧页冻结（本 Case 责任：K3 四行全覆盖（首页/下一页/过期/越界）；跨 principal 403、过滤不符 400；旧页冻结）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝management 组装后用量分页游标四态与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`inference/usage.py::UsageRecorder.page`/`_page`（游标快照与授权摘要）

```text
page(principal, cursor, limit, admin, since, until, model, request_id) -> {data, next_cursor, has_more, snapshot_id}
```

- 初态构造（经公开入口）：`AppFixture` + 真实 `Router`/`UsageRecorder`（ENV-1）；记录经公开入口 `responses.create` 造数（上游＝`FakeAdapter`）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-3
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：3 条记录分 2 页；`cursor=snap_missing:0`；跨 principal（alice→mallory）；`model` 过滤不匹配；`offset` 越界；新增记录后重取旧 cursor
- 边界/非法取值及理由：首页 2 条+`has_more`；第二页 1 条不重叠；未知 cursor→400 `cursor_expired`；跨 principal→403 `permission_denied`；过滤不符→400 `invalid_request`；越界→空页且 `next_cursor=None`；旧页对新记录冻结
- 规模 / 时间域（数量、分页、复杂度、观测开销）：6 次 `page` + 3 条记录；O(n log n)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 首页（limit=2） | 2 条 + `has_more` |
| 2 | 第二页 | 1 条，与首页 id 不相交 |
| 3 | 未知 cursor | 400 `cursor_expired` |
| 4 | 跨 principal cursor | 403 `permission_denied` |
| 5 | 过滤（`model`）不匹配 | 400 `invalid_request` |
| 6 | `offset` 越界 | 空页 + `next_cursor=None` |
| 7 | 新增记录后重取首页 cursor | 内容不变（快照冻结） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：方案 §3.3 K3 + 用量分页契约；按 `_page` 的 cursor 校验顺序与授权摘要人工推导
- 互斥预期（成功 / 各错误分支）：K3 四行全覆盖；跨主体隔离生效；快照冻结

## 6. 错误路径、副作用与清理

- 错误出口与表现：400 `cursor_expired` / 403 `permission_denied` / 400 `invalid_request`
- 副作用断言与清理：每次分页建 `query_snapshots`（10 分钟过期）

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-MGMT-009.py`（6 个）：`test_first_page_then_next_page`、`test_expired_cursor_is_400`、`test_cross_principal_cursor_is_403`、`test_filter_mismatch_is_400`、`test_beyond_total_is_empty_page`、`test_old_page_frozen_against_new_records`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-MGMT-009.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
