<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-API-012 — 诊断初始化失败 fail-open 与 bootstrap_error 可达性

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-API-012` |
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
| Canonical Path | `docs/70_verification/specifications/unit-case-UT-API-012.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-API-012`）；责任摘要、分类与优先级以 [单元测试方案 §3](../schemes/llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [http-api](../../40_module_design/http-api-design.md) §14 / ISD [http-api.isd.md](../../50_implementation_design/http-api.isd.md) §9.1，设计验证项 `VRC-API-001`（固定版本 `http-api 0.1.0-draft.2`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `http_api`；裁剪依据见 [STD 裁剪清单](../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-API-012` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-API-012` / M001 http-api §14.1 · `_UnavailableDiagnostics`/引导 v0.1.0-draft.2 / `VRC-API-001` / recovery / P1（[方案清单 §3](../schemes/llmtier-unit-test-scheme.md)）。
- 要测什么（责任展开）：被测：`DiagnosticsService` 初始化失败时降级为 `_UnavailableDiagnostics`（全方法 no-op、开关默认关），推理仍成功；`bootstrap_error` 置位时 `/healthz`+`/ui/*` 仍可达、`/readyz` →503、数据面 503；**`Application` 对非 `ApiError` 引导异常兜底为 `bootstrap_error`(503 `bootstrap_invalid`) 而非崩溃（CR-BOOTSTRAP-CATCH）**。
- 明确不测什么 / 失败含义：不测：诊断正常路径（UT-DIAG-*）；不测 systemd 启动。失败含义＝fail-open 降级或引导错误面实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/http_api/app.py::_UnavailableDiagnostics` + `Application.__init__` 的 try/except 降级 + `Handler._dispatch` 中 `app.bootstrap_error` 分支

```text
Application(database, settings)  # DiagnosticsService 失败时 self.diagnostics = _UnavailableDiagnostics()
```

- 初态构造（经公开入口）：构造 `Application` 使诊断初始化失败（禁用/坏路径）或显式注入 `bootstrap_error`，起 loopback 实例（ENV-2）
- Fixture / 向量及版本：`tests/unit/v03/fakes.py::AppFixture`（ENV-1）+ `test_app_dispatch.py::UnavailableDiagnosticsTests`/`BootstrapErrorTests`（ENV-2）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../plans/llmtier-unit-test-plan.md) 分配）：ENV-2 loopback 测试 HTTP 实例 + ENV-3 `FakeAdapter`（推理仍成功断言）
- 依赖的测试资产（tests.asset-design 文档）：`FakeAdapter`（G-UT-2）

## 3. 输入构造

- 逐参数输入构造：诊断初始化失败的 `Application`；`bootstrap_error` 置位的 `Application`；关闭开关的 `_UnavailableDiagnostics`
- 边界/非法取值及理由：降级为 no-op（零副作用）；bootstrap_error 下就绪面/数据面 503、健康/静态面 200
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单请求，O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 诊断降级对象调各方法 | 返回降级值、无异常 |
| 2 | 开关默认 | `{False,False}` |
| 3 | 降级下发起推理 | 推理仍成功 |
| 4 | `bootstrap_error` 下 `GET /healthz`/`/ui/` | 200 |
| 5 | `bootstrap_error` 下 `GET /readyz` / 数据面 | 503 not_ready / 503 |
| 6 | 非 `ApiError` 引导异常（patch `bootstrap_settings` 抛 `OSError`） | `bootstrap_error`=(503,`bootstrap_invalid`)、进程不崩 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`CON-INFER-005` fail-open + `T-MGMT-02` not_ready 语义 + 人工推导；不调用被测复算。**判据语义以设计验证项 `VRC-API-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：降级为 no-op 且开关默认关；推理成功；bootstrap_error 下 `/healthz`+`/ui/*` 200、`/readyz` 503、数据面 503；非 `ApiError` 引导异常 → 503 `bootstrap_invalid` 且不崩溃；互斥

## 6. 错误路径、副作用与清理

- 错误出口与表现：无降级自身错误出口；bootstrap_error 触发就绪/数据面 503
- 副作用断言与清理：降级不写观测库；loopback 实例清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/v03/test_app_dispatch.py::UnavailableDiagnosticsTests::test_degrades_to_unavailable_observer` / `test_switches_default_off` / `test_void_methods_are_noops` / `test_inference_still_succeeds_when_diagnostics_unavailable` + `BootstrapErrorTests::test_healthz_still_reachable` / `test_ui_still_reachable` / `test_readyz_is_503_not_ready` / `test_data_plane_returns_bootstrap_error` + `tests/unit/v03/test_app_startup.py::StartupTests::test_non_apierror_bootstrap_does_not_crash`（CR-BOOTSTRAP-CATCH）
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/v03/test_app_dispatch.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/v03/test_app_dispatch.py`）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。
