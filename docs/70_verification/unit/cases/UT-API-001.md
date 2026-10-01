<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-API-001 — 分发、错误信封与健康/就绪

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-API-001` |
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
| Canonical Path | `docs/70_verification/unit/cases/UT-API-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-API-001`）；责任摘要、分类与优先级以 [单元测试方案 §3](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [http-api-design.md](../../../40_module_design/http-api-design.md) §14 / ISD [http-api.isd.md](../../../50_implementation_design/http-api.isd.md) §9.1，设计验证项 `VRC-API-001`（固定版本 `http-api 0.1.0-draft.2`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `API`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-API-001` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-API-001` / `VRC-API-001`（http-api 模块设计 §14 / http-api-isd §9.1，http-api 0.1.0-draft.2） / `VRC-API-001` / normal / P0（[方案清单 §3](../llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：等价类划分（合法分发/健康/空库 not_ready）
- 要测什么（责任展开）：被测：请求分发命中/未命中路由、统一错误信封（`ApiError.envelope()`）与 `X-Request-ID`、`/healthz` 与 `/readyz`（空库 not_ready）。
- 明确不测什么 / 失败含义：不测：真实反向代理/进程启动（模块层与系统层）；不测上游 provider 协议。失败含义＝路由/错误出口/就绪语义实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/http_api/errors.py`、`src/http_api/health.py`、`src/http_api/app.py`（`Handler._dispatch`/`_json`）

```text
ApiError(status, code, message, param=None); health_view(version); readiness_view(registry) -> (payload, status)
```

- 初态构造（经公开入口）：无状态；`AppFixture` 建空 `Application`（空库）
- Fixture / 向量及版本：`tests/unit/v03/fakes.py::AppFixture`
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库 / ENV-2 loopback 测试 HTTP 实例 / ENV-3 provider 进程内 fake（按 Case 需要，见 §4）
- 依赖的测试资产（tests.asset-design 文档）：无（真实实现）

## 3. 输入构造

- 逐参数输入构造：`ApiError` 各状态码；`readiness_view` 空库；`health_view("x")`
- 边界/非法取值及理由：400/500 边界（client_error/server_error 分类）；空库 readiness
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单次调用，O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 构造 `ApiError(400/500,...)` 调 `envelope()` | envelope 键与 type |
| 2 | 空库 `readiness_view(registry)` | payload 与 HTTP status |
| 3 | `health_view("x")` | 固定视图 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：STD 错误信封契约 + 系统设计 §7.8/§11.1，人工推导，不调用被测复算。**判据语义以设计验证项 `VRC-API-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：`ApiError(400).envelope()["error"]["type"]=="request_error"`；`envelope()["error"]["param"]` 透传；空库 readiness 为 `not_ready` 且 status=503

## 6. 错误路径、副作用与清理

- 错误出口与表现：无其他错误出口（非本 VRC 范围内的路由分发错误由 UT-API-002/003 覆盖）
- 副作用断言与清理：无堆外资源、无 I/O；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/v03/test_errors.py`（全部 7 个测试）+ `tests/unit/v03/test_health.py::test_health_ok/test_empty_is_not_ready`+`test_not_ready_http_status`（注意：本 Case 的测试函数当前按子句（test case method）映射；若与设计 VRC 不一致，以设计修订回溯后重裁）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/v03/test_errors.py tests/unit/v03/test_health.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/v03`）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。

