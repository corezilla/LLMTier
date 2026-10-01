<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-MGMT-006 — 账号用量快照

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-MGMT-006` |
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
| Canonical Path | `docs/70_verification/unit/cases/UT-MGMT-006.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-MGMT-006`）；责任摘要、分类与优先级以 [单元测试方案 §3](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [management-design.md](../../../40_module_design/management-design.md) §14 / ISD [management.isd.md](../../../50_implementation_design/management.isd.md) §9.1，设计验证项 `VRC-MGMT-006`（固定版本 `management 0.1.0-draft.2`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `MGMT`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-MGMT-006` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-MGMT-006` / `VRC-MGMT-006`（management 模块设计 §14 / management-isd §9.1，management 0.1.0-draft.2） / `VRC-MGMT-006` / negative / P1（[方案清单 §3](../llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（账号用量 GET/凭据/上游错误）
- 要测什么（责任展开）：被测：`AccountUsageService` GET 不触网、未确认 POST、凭据缺失、provider 报错 → `not_refreshed`/`unavailable`+`error` 且快照持久、provider usage profile 安全 round-trip、MiniMax 复用 token-plan key。
- 明确不测什么 / 失败含义：不测：真实 MiniMax 接口；不测 UI 呈现（M002）。失败含义＝账号用量刷新/安全实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/management/account_usage.py::AccountUsageService`

```text
AccountUsageService.get()/refresh(...); registry provider usage profile
```

- 初态构造（经公开入口）：`AppFixture`；`patch` provider HTTP（`FakeResponse`）
- Fixture / 向量及版本：`tests/common/fakes.py::AppFixture`；`test_account_usage.FakeResponse`（ENV-3 stub）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库 / ENV-2 loopback 测试 HTTP 实例 / ENV-3 provider 进程内 fake（按 Case 需要，见 §4）
- 依赖的测试资产（tests.asset-design 文档）：`FakeResponse`（`llmtier-unit-fakes`，资产文档已建）

## 3. 输入构造

- 逐参数输入构造：GET；未确认 POST；缺凭据；provider 报错；MiniMax profile
- 边界/非法取值及理由：确认/未确认边界；凭据缺失
- 规模 / 时间域（数量、分页、复杂度、观测开销）：O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | GET 不触网 | 不刷新 |
| 2 | 未确认 POST / 缺凭据 | not_refreshed/unavailable |
| 3 | provider 报错 | unavailable+error |
| 4 | profile round-trip 安全 | 无 secret 泄漏 |
| 5 | request usage 归属所选 provider | attribution |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`RULE-MGMT-USAGE-REFRESH`；人工推导。**判据语义以设计验证项 `VRC-MGMT-006` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：GET 不触网；未确认/缺凭据→`not_refreshed`；provider 报错→`unavailable`+`error` 快照持久；profile 不含 secret

## 6. 错误路径、副作用与清理

- 错误出口与表现：无（分支互斥）
- 副作用断言与清理：快照落库；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/cases/UT-MGMT-006.py`（全部 5 个）（注意：本 Case 的测试函数当前按子句（test case method）映射；若与设计 VRC 不一致，以设计修订回溯后重裁）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/cases/account_usage.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit`）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。

