<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-UI-002 — UI API 契约与服务端状态码交叉核对

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-UI-002` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-UI-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-UI-002`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-UI-002.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-UI-002` / M002 web-ui §9 · 编辑/暂停/探测/用量/诊断契约（组装） v0.1.0-draft.2 / VRC-UI-002/003/004/005/006（web-ui-design §14 / web-ui.isd §9.1，web-ui 0.1.0-draft.2） / VRC-UI-002/003/004/005/006 / normal / P0（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：组装后真实调用 + 等价类划分 + 分支覆盖（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现与真实静态产物））
- **覆盖的分支 / 组合 / 迁移 ID**：无（层① 接口行为分母行）
- 要测什么（责任展开）：组装后 UI API 契约：编辑 412/409、Pause 确认边界、探测确认、用量 Unknown 呈现、诊断 4 tabs 契约与 `app.js` 接线一致（本 Case 责任：UI 声明的路径/ETag/确认字段与服务端真实行为逐条对齐；412/409 保留输入；诊断 4 tabs 接线一致）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝web-ui 组装后UI 请求契约与服务端行为对齐与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/web_ui/app.js`（`api()`/`saveProvider`/`saveMember`/`toggleDeployment`/`probeDeployment`/`refreshProviderUsage`/诊断 tabs）、`app.py` 资源路由

```text
UI 声明的 /v1 路径、If-Match 头、confirm 字段 与 真实端点行为
```

- 初态构造（经公开入口）：真实静态产物 + ENV-2 loopback（服务端状态码实证）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2
- 依赖的测试资产（tests.asset-design 文档）：无（真实静态产物 `src/web_ui/*` + ENV-1/ENV-2 真实端点；不经替身）

## 3. 输入构造

- 逐参数输入构造：UI 路径集合 × `app.py` 路由；`If-Match` 格式；412/409/400 保留输入；Pause 确认门；`confirm_external_call` 字段；用量 Unknown 呈现；诊断 4 tabs
- 边界/非法取值及理由：UI 声明路径均存在于 `app.py`；三资源旧 ETag PATCH 真得 412 且无副作用；删被引用 provider 真得 409 `resource_in_use`；删固定 tier 得 409（非 412）；未确认探测/刷新被拒（400）；确认探测真 dispatch 并回报 `may_have_incurred_cost`；诊断 4 个 `data-dtab` 与容器一一对应
- 规模 / 时间域（数量、分页、复杂度、观测开销）：12 个测试方法；静态 + 约 10 次 loopback；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 路径↔路由交叉 | UI `api()` 用到的 `/v1/...` 全部在 `app.py` 注册 |
| 2 | `If-Match` 格式 | `etag()` 产 `"<id>.v<n>"` 与服务端 `ETag` 同格式 |
| 3 | 三资源陈旧 `If-Match` PATCH | 均 412 `version_conflict` 且资源未变 |
| 4 | 删除被引用 provider | 409 `resource_in_use`，资源保留 |
| 5 | 删除固定 tier | 409 `fixed_service_level` |
| 6 | 探测/用量刷新未确认（含多余字段） | 均 400（`confirmation_required`） |
| 7 | 确认后探测 | 200 且 `may_have_incurred_cost=false`、health 落库 |
| 8 | UI 错误处理保留输入 | 409/412 分支不改写表单输入（`staleEdit`/`referenceConflict` 标记） |
| 9 | 诊断 4 tabs | 4 个 `data-dtab` ↔ 容器 ↔ loader 对应 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：web-ui 模块设计 §14.2–§14.7 + 契约层；按 `app.js` 请求构造与 `app.py`/服务方法真实返回码人工推导
- 互斥预期（成功 / 各错误分支）：UI 声明的契约与服务端真实行为逐条对齐；确认门与 ETag 语义一致

## 6. 错误路径、副作用与清理

- 错误出口与表现：412/409/400 三类码与 UI 分支对应
- 副作用断言与清理：被拒操作不落库（对照 412 后资源未变）

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-UI-002.py`（12 个）：`test_every_api_path_used_by_app_js_exists_in_the_m001_router`、`test_etag_format_matches_the_registry_writer`、`test_conflict_responses_keep_the_operator_input`、`test_pause_requires_confirmation_only_when_requests_are_running`、`test_probe_and_usage_refresh_require_explicit_confirmation`、`test_usage_view_renders_unknown_instead_of_zero`、`test_diagnostics_tabs_are_wired_to_the_four_backend_faces`、`test_stale_if_match_really_yields_412_for_every_resource_the_ui_edits`、`test_deleting_a_referenced_provider_really_yields_409_resource_in_use`、`test_fixed_service_level_delete_really_yields_409_not_412`、`test_probe_and_usage_refresh_really_reject_unconfirmed_calls`、`test_confirmed_probe_really_dispatch_and_report_cost_flag`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-UI-002.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
