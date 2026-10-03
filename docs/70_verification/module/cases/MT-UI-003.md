<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-UI-003 — `dispatchUiError` 五分支契约

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-UI-003` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-UI-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-UI-003`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-UI-003.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-UI-003` / M002 `dispatchUiError` 分支：401/403、409、412、429、503/default（组装契约） v0.1.0-draft.2 / VRC-UI-002（web-ui-design §14 / web-ui.isd §9.1，web-ui 0.1.0-draft.2） / VRC-UI-002 / negative / P0（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：错误猜测 + 反例驱动（非法字段/凭据/引用/类型/顺序）+ 判定表组合（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现与真实静态产物））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M002-dispatchUiError 五分支
- 要测什么（责任展开）：五分支：401/403 呈现；409 引用保留输入；412 stale 保留输入；429 `Retry-After`；503/default stale（本 Case 责任：401/403/409/412/429/503 分派互斥且文案固定；403 不泄露存在性；`Retry-After` 取自响应头）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝web-ui 组装后UI 错误分派五分支与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/web_ui/app.js::dispatchUiError`（401/403/409/412/429/503）

```text
dispatchUiError(error) —— 状态码 → 呈现行为
```

- 初态构造（经公开入口）：真实静态产物 + ENV-2（真实 401/403/503 状态与 `Retry-After` 头核对）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2
- 依赖的测试资产（tests.asset-design 文档）：无（真实静态产物 `src/web_ui/*` + ENV-1/ENV-2 真实端点；不经替身）

## 3. 输入构造

- 逐参数输入构造：401/403/409/412/429/503 六态；未知状态；真实 401/403 信封；未配置凭据 503；`Retry-After` 位置
- 边界/非法取值及理由：401 加 stale 并跳 `LOGIN_URL`；403 固定文案（不泄露存在性）；409 追加冲突前缀并标 `referenceConflict`；412 标 `staleEdit` 并提示输入保留；429 读 `Retry-After` 拼文案；503 `markStale`；未知状态不改视图
- 规模 / 时间域（数量、分页、复杂度、观测开销）：11 个测试方法；静态 + 3 次 loopback；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 六态分支逐条断言 | 各自分派到跳转/横幅/保留输入/stale |
| 2 | 409 文案与标记 | 含「still in use」前缀且 `referenceConflict=true` |
| 3 | 412 文案与标记 | 含「Your input was kept」且 `staleEdit=true` |
| 4 | 429 文案 | 含 `Retry-After` 秒数（缺失时回落 `a moment`） |
| 5 | 真实 401/403 | 信封形状一致（支撑 403 固定文案不猜存在性） |
| 6 | 未配置凭据 503 | 落 503 分支（`auth_not_configured`） |
| 7 | `Retry-After` 来源 | 取自响应头而非信封（信封无此字段） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：web-ui 模块设计 §14.2 + 错误信封契约；按 `dispatchUiError` 的 `if` 链与服务端真实状态码人工推导（`/login` 路由缺失见 §7 `G-UI-LOGIN-ROUTE-1`）
- 互斥预期（成功 / 各错误分支）：五分支互斥且文案固定；`Retry-After` 取值路径正确；403 不泄露存在性。逐分支出口码：401 `authentication_required`、403 `permission_denied`、409 `resource_conflict`/`resource_in_use`、412 `version_conflict`、429 `rate_limit_exceeded`；信封形状对照含 `not_found`/`usage_store_unavailable`/`internal_error`；真实 401/403 共用同一信封形状；`Retry-After` 只取自响应头

## 6. 错误路径、副作用与清理

- 错误出口与表现：无 UI 自有错误码（消费服务端状态）
- 副作用断言与清理：错误分派只改视图/横幅，不改数据

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-UI-003.py`（11 个）：`test_dispatch_covers_exactly_the_designated_statuses`、`test_401_clears_the_session_and_redirects_without_echoing_credentials`、`test_403_presents_a_fixed_banner_without_leaking_existence`、`test_409_flags_reference_conflict_and_keeps_the_server_message`、`test_412_marks_a_stale_edit_and_keeps_the_draft`、`test_429_surfaces_retry_after_and_marks_the_view_stale`、`test_503_marks_stale_and_leaves_unlisted_statuses_to_report_load_failure`、`test_error_object_fields_match_the_m001_error_envelope`、`test_real_401_and_403_share_the_same_envelope_shape`、`test_unconfigured_auth_is_503_and_lands_in_the_same_503_branch`、`test_retry_after_comes_from_the_header_not_the_envelope`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-UI-003.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
