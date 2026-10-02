<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-API-005 — `_run` 三错误出口

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-API-005` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-API-005.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-API-005`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-API-005.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-API-005` / M001 `_run` 错误出口：ApiError/sqlite3.Error/未知异常（组装） v0.1.0-draft.2 / VRC-API-001（http-api-design §14 / http-api.isd §9.1，http-api 0.1.0-draft.2） / VRC-API-001 / negative / P0（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（非法字段/凭据/引用/类型/顺序）+ 判定表组合（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M001-ApiError/sqlite/未知异常
- 要测什么（责任展开）：三出口分别断言：ApiError→既定码；`sqlite3.Error`→503 `usage_store_unavailable`；未知异常→500 `internal_error`（均落日志）（本 Case 责任：ApiError 保持既定码；sqlite 读失败→503；未知异常→500 并落日志；三出口互不掩盖）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝http-api 组装后_run 三个错误出口与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/http_api/app.py::Handler._run`（`ApiError`/`sqlite3.Error`/未知异常三出口）

```text
_run -> (status, envelope); 异常出口经 sqlite3.Error / 未捕获异常
```

- 初态构造（经公开入口）：同 MT-API-001（ENV-1 + ENV-2）；坏状态经存储面注入（文件权限 / 毒化 `service_levels.capabilities_json`）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2
- 依赖的测试资产（tests.asset-design 文档）：无（全部真实实现；不经替身）

## 3. 输入构造

- 逐参数输入构造：① 非法 `from=bad-timestamp`；② `chmod 000` 库文件后 `GET /v1/providers`；③ `capabilities_json='{oops'` 后 `GET /v1/models`
- 边界/非法取值及理由：sqlite 出口 message 为 `Store is unavailable`（区别服务层 `Usage store is unavailable`）；未知异常 message 为 `Internal server error`；均带 `X-Request-ID`
- 规模 / 时间域（数量、分页、复杂度、观测开销）：3 请求 + 2 次存储面注入与还原；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /v1/usage?from=bad-timestamp` | 400 `invalid_request`（ApiError 出口） |
| 2 | `chmod 000` 库文件 → `GET /v1/providers` | 503 `usage_store_unavailable`，message=`Store is unavailable`；恢复权限后日志通路恢复（库整体不可用时日志写入亦被 fail-open 吞掉） |
| 3 | 毒化 `service_levels.capabilities_json='{oops'` → `GET /v1/models` | 500 `internal_error`、`type=server_error`；还原后日志出现 `unhandled_error` |
| 4 | `GET /healthz` | 200（进程存活） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：http-api 模块设计 §14.1 + 错误码目录；按 `_run` 三个 `except` 子句与消息字面量人工推导
- 互斥预期（成功 / 各错误分支）：ApiError 保持既定码；sqlite 失败→503 `usage_store_unavailable`；未知异常→500 `internal_error` 并落日志；进程不崩

## 6. 错误路径、副作用与清理

- 错误出口与表现：sqlite3.Error→503；未知异常→500；两者均不得泄漏堆栈
- 副作用断言与清理：失败后连接被 finally 关闭；库状态在 finally 中还原

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-API-005.py`（4 个）：`test_api_error_exit_maps_declared_code`、`test_store_failure_exit_is_503_usage_store_unavailable`、`test_unknown_exception_exit_is_500_internal_error_and_logged`、`test_server_survives_after_error_exits`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-API-005.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
