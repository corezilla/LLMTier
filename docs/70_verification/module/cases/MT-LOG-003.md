<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-LOG-003 — page 分支与日志追加顺序

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-LOG-003` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-LOG-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-LOG-003`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-LOG-003.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-LOG-003` / M008 `page` 分支：缺 since/until→400 + limit 夹取 + 过滤（组装） v0.1.0-draft.1 / VRC-LOG-001（log-design §14 / log.isd §9.1，log 0.1.0-draft.1） / VRC-LOG-001 / negative / P1（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（非法字段/凭据/引用/类型/顺序）+ 判定表组合（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M008-page 三分支；迁移：T14、T14
- 要测什么（责任展开）：缺参→400；`limit` 夹到 [1,200]；level/module/request_id 过滤；DESC 顺序（本 Case 责任：缺参 400、limit 夹取、三类过滤、DESC 顺序稳定（T14））
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝log 组装后查询分支与顺序稳定性与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/log/logs.py::OperationalLog.page`

```text
page(limit, level, module, request_id, since, until) -> {"data", "page"}
```

- 初态构造（经公开入口）：`AppFixture` 真实组装（ENV-1），`setUp` 经 `record` 写 6 行（3 info/3 warning、2 module、2 request_id）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 组装隔离库
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture`（`FakeAdapter`/`AppFixture` 组装契约，见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：`limit` 取 0/-5/2/999；过滤 `level`/`module`/`request_id` 及组合；重复查询两次比对顺序
- 边界/非法取值及理由：`limit` 夹取 `[1,200]`（0/-5→1）；缺 `since`/`until`→400；组合过滤求交
- 规模 / 时间域（数量、分页、复杂度、观测开销）：6 行；单连接；O(n)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 缺 `since` 或 `until`（三种组合） | 均 400 `invalid_request` |
| 2 | `limit=0/-5/2/999` | 1/1/2/6 行 |
| 3 | `level`/`module`/`request_id` 过滤与组合 | 命中集合正确（组合求交） |
| 4 | 连查两次比对 message 序列 | 均为 `message-5…message-0`（倒序稳定，T14） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：log 模块设计 §14.1 + 方案 §3.4 T14；按 `ORDER BY created_at DESC, id DESC` 与 `max(1, min(limit, 200))` 人工推导
- 互斥预期（成功 / 各错误分支）：三处缺参→400；`limit` 夹取；三种过滤与组合正确；倒序稳定可复现

## 6. 错误路径、副作用与清理

- 错误出口与表现：缺参→400 `invalid_request`
- 副作用断言与清理：查询不写库；顺序可复现

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-LOG-003.py`（4 个）：`test_missing_since_or_until_is_400`、`test_limit_clamped_low_and_high`、`test_filter_by_level_module_request_id`、`test_append_order_is_stable_desc`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-LOG-003.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
