<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-LOG-001 — OperationalLog 组装后脱敏与查询

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-LOG-001` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-LOG-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-LOG-001`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-LOG-001.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-LOG-001` / M008 log §9 · `OperationalLog.record/page`（组装） v0.1.0-draft.1 / VRC-LOG-001（log-design §14 / log.isd §9.1，log 0.1.0-draft.1） / VRC-LOG-001 / security / P0（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：鉴权/脱敏/注入边界冒烟 + 契约 + 分支×端点配对（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：无（层① 接口行为分母行）
- 要测什么（责任展开）：组装后脱敏与查询：Bearer/api_key/token 落库 `[REDACTED]`、长度 ≤512、倒序、过滤、`limit` 夹到 200、缺 `since`/`until`→400（本 Case 责任：record→落库脱敏、长度上限、page 倒序/过滤/limit 夹取、缺参 400）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝log 组装后脱敏与查询面组装行为与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/log/logs.py::OperationalLog.record`/`page`

```text
log.record(level, module, event, message, request_id=None); log.page(limit, level, module, request_id, since, until)
```

- 初态构造（经公开入口）：`AppFixture` 真实组装（ENV-1），经 M008 公开入口 `record`/`page` 播种与查询
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 组装隔离库
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture`（`FakeAdapter`/`AppFixture` 组装契约，见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：`record` 5 次（不同 level/module/request_id）；`page` 用 `limit=999/0/2` 与 `level`/`request_id` 过滤
- 边界/非法取值及理由：消息长度 `[:512]`；`limit` 夹取 `[1,200]`；换行折平；倒序 `created_at DESC, id DESC`
- 规模 / 时间域（数量、分页、复杂度、观测开销）：5 行；单连接；O(n log n) 排序

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `record` 含 `authorization: Bearer sk-123` | 读回消息含 `[REDACTED]`、不含 `sk-123` |
| 2 | `record` 2000 字消息 | 读回长度 512 |
| 3 | `record` 含换行 | 读回无换行（折平为单行） |
| 4 | `page` 按 level/request_id 过滤 | 命中子集正确 |
| 5 | `page(limit=999)` / `page(limit=0)` | ≤200 行 / ≥1 行（夹取） |
| 6 | `page()` 缺参 | 400 `invalid_request` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：log 模块设计 §14.1 + 错误码契约；按 `_SENSITIVE` 正则与 `[:512]` 截断语义人工推导
- 互斥预期（成功 / 各错误分支）：敏感串一律 `[REDACTED]`；长度 ≤512；倒序稳定；`limit` 夹取；缺 `since/until`→400

## 6. 错误路径、副作用与清理

- 错误出口与表现：缺 `since`/`until`→400 `invalid_request`
- 副作用断言与清理：写失败 fail-open（`record` 内吞异常）；本 Case 只读回已写行

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-LOG-001.py`（6 个）：`test_record_then_page_roundtrip_redacts`、`test_message_truncated_to_512`、`test_desc_order_and_filters`、`test_limit_clamped_to_200`、`test_page_requires_since_and_until`、`test_newlines_flattened`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-LOG-001.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
