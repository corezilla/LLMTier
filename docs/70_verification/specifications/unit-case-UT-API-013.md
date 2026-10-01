<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-API-013 — 诊断开关 PATCH 未知键与非布尔值

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-API-013` |
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
| Canonical Path | `docs/70_verification/specifications/unit-case-UT-API-013.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-API-013`）；责任摘要、分类与优先级以 [单元测试方案 §3](../schemes/llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [http-api](../../40_module_design/http-api-design.md) §14 / ISD [http-api.isd.md](../../50_implementation_design/http-api.isd.md) §9.1，设计验证项 `VRC-API-001`（固定版本 `http-api 0.1.0-draft.2`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `http_api`；裁剪依据见 [STD 裁剪清单](../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-API-013` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-API-013` / M001 http-api §14.1 · `/v1/diagnostics` PATCH v0.1.0-draft.2 / `VRC-API-001` / negative / P2（[方案清单 §3](../schemes/llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（未知键/非布尔开关）
- 要测什么（责任展开）：被测：`/v1/diagnostics`（及别名）PATCH 未知键 → 400 `invalid_request`；非布尔开关值 → 400。
- 明确不测什么 / 失败含义：不测：合法开关切换落库（UT-OBS-001 / UT-DIAG-001）。失败含义＝诊断 PATCH 白名单/类型校验实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/http_api/app.py::Handler._dispatch` 中 `/v1/diagnostics` 与 `/tier/admin/v1/diagnostics` 的 PATCH 分支（白名单 `{snapshots_enabled, stats_enabled}` + `_optional_boolean`）

```text
PATCH body 仅允许 snapshots_enabled/stats_enabled 且值为布尔
```

- 初态构造（经公开入口）：`AppFixture().seed()` + admin 凭据 + loopback `handler_factory(app)`（ENV-2）
- Fixture / 向量及版本：`tests/unit/v03/fakes.py::AppFixture`（ENV-1）+ `test_app_dispatch.py::DiagnosticsPatchContractTests`（ENV-2）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../plans/llmtier-unit-test-plan.md) 分配）：ENV-2 loopback 测试 HTTP 实例
- 依赖的测试资产（tests.asset-design 文档）：无（真实实现）

## 3. 输入构造

- 逐参数输入构造：PATCH body `{"unknown_key": true}`；PATCH body `{"snapshots_enabled":"yes"}`
- 边界/非法取值及理由：未知键 400；非布尔 400（互斥）
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单请求，O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `/v1/diagnostics` PATCH 未知键 | 400 + `error.code=invalid_request` |
| 2 | 别名 PATCH 未知键 | 400 + `error.code=invalid_request` |
| 3 | 非布尔开关值 | 400；且前后 `GET /v1/diagnostics` 一致（未落库） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：诊断 PATCH 白名单 + 布尔类型规则 + 人工推导；不调用被测复算。**判据语义以设计验证项 `VRC-API-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：未知键 400 `invalid_request`；非布尔 400；主/别名一致；互斥

## 6. 错误路径、副作用与清理

- 错误出口与表现：400 `invalid_request`；无第三态
- 副作用断言与清理：非法请求不落库（开关未被修改）；loopback 实例清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/v03/test_app_dispatch.py::DiagnosticsPatchContractTests::test_unknown_key_is_400` / `test_alias_unknown_key_is_400` / `test_non_boolean_switch_is_400_and_not_persisted`（非布尔→400 + 前后开关读取证明未落库）
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/v03/test_app_dispatch.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/v03/test_app_dispatch.py`）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。
