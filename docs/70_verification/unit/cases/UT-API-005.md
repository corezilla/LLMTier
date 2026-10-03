<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-API-005 — 分发错误出口与统一错误信封

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-API-005` |
| Document Version | `0.1.0-draft.3` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.unit-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/unit/cases/UT-API-005.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-API-005`）；责任摘要、分类与优先级以 [单元测试方案 §6](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [http-api](../../../40_module_design/http-api-design.md) §14 / ISD [http-api.isd.md](../../../50_implementation_design/http-api.isd.md) §9.1，设计验证项 `VRC-API-001`（固定版本 `http-api 0.1.0-draft.2`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `http_api`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-API-005` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-API-005` / M001 http-api §14.1 · `_dispatch`/`_run` 错误出口 v0.1.0-draft.2 / `VRC-API-001` / negative / P0（[方案清单 §6](../llmtier-unit-test-scheme.md)）。
- **测试方法（§2.1 方法表行）**：错误猜测 + 反例驱动（未知路由/异常/读路径 sqlite3.Error）（主要手段：直接调用 + 冻结向量 + 替身注入）
- 要测什么（责任展开）：被测：`Handler._dispatch`/`_run` 的未知路由 404（`not_found`）、未知异常 500（`internal_error` + `unhandled_error` 落运行日志）、读路径 `sqlite3.Error` → 503 `usage_store_unavailable`；错误响应对应统一信封且带 `X-Request-ID`。
- 明确不测什么 / 失败含义：不测：成功路径（UT-API-001）；不测 wire 互操作（契约/系统层）。失败含义＝错误出口映射或统一信封实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/http_api/app.py::Handler._dispatch`（路由表尾 `raise ApiError(404, ...)`）与 `Handler._run`（`except sqlite3.Error` / `except Exception` 两个出口）

```text
Handler._run() -> None  # 捕获 ApiError / sqlite3.Error / Exception 并写出错误信封
```

- 初态构造（经公开入口）：`AppFixture()` + `AppFixture.seed()`（1 tier/1 deployment）挂到真实 `ThreadingHTTPServer((127.0.0.1,0), handler_factory(app))`（ENV-2）
- Fixture / 向量及版本：`tests/common/fakes.py::AppFixture`（ENV-1）+ `UT-API-005.py::LoopbackApp`（ENV-2）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-2 loopback 测试 HTTP 实例（真实 `Application` + 真实 socket）
- 依赖的测试资产（tests.asset-design 文档）：`FakeAdapter`（`llmtier-unit-fakes`）；本 Case 用不到

## 3. 输入构造

- 逐参数输入构造：未知路径 `GET /v1/nope`；`app.models.list` 被 patch 抛 `RuntimeError` 的 `GET /v1/models`；`app.usage.page` 被 patch 抛 `RuntimeError` 的 `GET /v1/usage?from=…&to=…`
- 边界/非法取值及理由：未知路由无匹配；异常为运行时类型（非 ApiError）；三类出口互斥
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单请求，O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /v1/nope` | 404 + `error.code=not_found` + 非空 `X-Request-ID` |
| 2 | patch `models.list` 抛异常后 `GET /v1/models` | 500 + `error.code=internal_error` |
| 3 | 查运行日志含 `event=unhandled_error` | 存在该审计/运行日志行 |
| 4 | patch `usage.page` 抛异常后 `GET /v1/usage` | 503 + `error.code=usage_store_unavailable` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：T-API-03 错误出口规则 + 人工推导状态码/错误码；不调用被测复算。**判据语义以设计验证项 `VRC-API-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：未知路由 404 `not_found`；未知异常 500 `internal_error` 且落 `unhandled_error`；读路径 `sqlite3.Error`/等价异常 503 `usage_store_unavailable`；三分支互斥

## 6. 错误路径、副作用与清理

- 错误出口与表现：本 Case 即三错误出口本身；每出口独立 Step 与断言，无第三态
- 副作用断言与清理：`unhandled_error` 落运行日志（隔离库）；loopback 实例由 `tearDownClass` shutdown + server_close 清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/cases/UT-API-005.py::DispatchErrorTests::test_unknown_route_is_404_not_found` / `test_unhandled_error_is_500_and_logged` / `test_read_path_store_failure_is_503_usage_store_unavailable`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/cases/UT-API-005.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/cases/UT-API-005.py`）；执行状态与 Verdict 见 Run 报告 `run-20261001-04`。
