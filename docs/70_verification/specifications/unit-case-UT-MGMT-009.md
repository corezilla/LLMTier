<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-MGMT-009 — admin cursor 过期与 reset_usage 范围矩阵

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-MGMT-009` |
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
| Canonical Path | `docs/70_verification/specifications/unit-case-UT-MGMT-009.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-MGMT-009`）；责任摘要、分类与优先级以 [单元测试方案 §3](../schemes/llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [management](../../40_module_design/management-design.md) §14 / ISD [management.isd.md](../../50_implementation_design/management.isd.md) §9.1，设计验证项 `VRC-MGMT-004`（固定版本 `management 0.1.0-draft.3`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `management`；裁剪依据见 [STD 裁剪清单](../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-MGMT-009` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-MGMT-009` / M004 management §14.4 · `admin.page`/`reset_usage` v0.1.0-draft.2 / `VRC-MGMT-004` / boundary / P1（[方案清单 §3](../schemes/llmtier-unit-test-scheme.md)）。
- 要测什么（责任展开）：被测：admin cursor `expires_at` 过期 → 400 `cursor_expired`；**畸形 cursor（`<sid>:<非整数>`/非整数 offset）→ 400 `cursor_expired` 而非未捕获 `ValueError`→500（CR-ADMIN-CURSOR）**；**cursor 绑定 `authorization_digest`/`filter_digest` 与 `snapshot_kind` 重校验（CR-ADMIN-CURSOR-GUARD）**；usage 快照冻结；`reset_usage` 范围矩阵（model/deployment/both/neither）。
- 明确不测什么 / 失败含义：不测：首屏分页主路径（UT-MGMT-004）；不测跨 principal 身份（由 UT-MGMT-004 覆盖）。失败含义＝cursor TTL/解析/摘要绑定检查或清空范围实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/management/admin.py::AdminService.page`（`query_snapshots.expires_at`/`authorization_digest`/`filter_digest` 与 cursor offset 解析）与 `src/inference/usage.py::UsageRecorder.reset_usage`（范围过滤）

```text
AdminService.page(...); UsageRecorder.reset_usage(...)  # 范围：model/deployment/both/neither
```

- 初态构造（经公开入口）：`AppFixture().seed()` + 写入用量行与查询快照；构造过期 cursor（ENV-1）
- Fixture / 向量及版本：`tests/unit/v03/test_management_gaps.py::AdminCursorExpiryTests`/`ResetUsageScopeTests`；`fakes.py::AppFixture`（ENV-1）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../plans/llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库
- 依赖的测试资产（tests.asset-design 文档）：无（真实实现）

## 3. 输入构造

- 逐参数输入构造：手动过期 `query_snapshots.expires_at` 后的续页 cursor；`<sid>:abc` 畸形 offset cursor；非整数 offset 的「合法样式」cursor；篡改 `authorization_digest`/`filter_digest` 的快照行；不同 `kind` 续页；`reset_usage` 分别按 model/deployment/both/neither
- 边界/非法取值及理由：过期/畸形→400；摘要或 filter 不符→400；清空范围四态互斥、计数一致
- 规模 / 时间域（数量、分页、复杂度、观测开销）：O(用量行数)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 过期 cursor 续页 | 400 `cursor_expired` |
| 2 | 畸形 offset cursor 续页 | 400 `cursor_expired`（非 `ValueError`） |
| 3 | 篡改 `authorization_digest`/`filter_digest` 后续页 | 400 `cursor_expired` |
| 4 | 不同 kind 续页 | 400 `cursor_expired`（`filter_digest`/`snapshot_kind` 绑定） |
| 5 | 范围 model | 仅该 model 清除 |
| 6 | 范围 deployment | 仅该 deployment 清除 |
| 7 | 范围 both / neither | 交集清除 / 全清 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`RULE-MGMT-SNAPSHOT`/`CON-METER-004` + T-MGMT-08 + 系统 §7.10 cursor 摘要绑定 + 人工推导；不调用被测复算。**判据语义以设计验证项 `VRC-MGMT-004` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：过期/畸形/摘要或 filter 不符 cursor → 400 `cursor_expired`（畸形不得泄漏 `ValueError`）；快照冻结（旧页稳定）；reset 范围计数一致；互斥

## 6. 错误路径、副作用与清理

- 错误出口与表现：400 `cursor_expired`；无第三态
- 副作用断言与清理：reset 落库计数与查询一致；隔离库由 fixture 清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/v03/test_management_gaps.py::AdminCursorExpiryTests::test_expired_admin_cursor_is_400` / `test_malformed_offset_cursor_is_400_not_500` / `test_non_integer_offset_cursor_is_400_not_valueerror` + `AdminCursorGuardTests::test_cursor_filter_digest_is_checked` / `test_cursor_authorization_digest_is_checked` / `test_cursor_filter_kind_mismatch_is_400` + `ResetUsageScopeTests::test_reset_by_model_only` / `test_reset_by_deployment_only` / `test_reset_by_model_and_deployment` / `test_reset_all`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/v03/test_management_gaps.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/v03/test_management_gaps.py`）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。
