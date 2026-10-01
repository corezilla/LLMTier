<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-MGMT-010 — 探测不可达落 unhealthy 与成本标记

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-MGMT-010` |
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
| Canonical Path | `docs/70_verification/unit/cases/UT-MGMT-010.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-MGMT-010`）；责任摘要、分类与优先级以 [单元测试方案 §3](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [management](../../../40_module_design/management-design.md) §14 / ISD [management.isd.md](../../../50_implementation_design/management.isd.md) §9.1，设计验证项 `VRC-MGMT-005`（固定版本 `management 0.1.0-draft.3`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `management`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-MGMT-010` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-MGMT-010` / M004 management §14.5 · `probe` 不可达 v0.1.0-draft.2 / `VRC-MGMT-005` / recovery / P1（[方案清单 §3](../llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：故障注入 + 异常路径恢复（上游不可达→unhealthy 落库）（主要手段：直接调用 + 替身注入）
- 要测什么（责任展开）：被测：上游不可达 → `unhealthy` 落库；`probe` 返回含 `may_have_incurred_cost`。
- 明确不测什么 / 失败含义：不测：未确认 400（UT-MGMT-005）；不测真实上游协议。失败含义＝探测失败落库或成本标记实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/management/admin.py::AdminService.probe`（上游不可达分支 + `may_have_incurred_cost`）

```text
AdminService.probe(principal_id, body, request_id) -> dict
```

- 初态构造（经公开入口）：`AppFixture().seed()`；provider 指向不可达端点（`FakeResponse` 本地 stub / patch `urlopen`）（ENV-1+ENV-3）
- Fixture / 向量及版本：`tests/unit/cases/UT-MGMT-010.py::ProbeUnreachableTests`；`fakes.py::AppFixture`（ENV-1）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库 / ENV-3 provider 进程内 fake
- 依赖的测试资产（tests.asset-design 文档）：`FakeAdapter`/本地 `FakeResponse`（`llmtier-unit-fakes`，资产文档已建）

## 3. 输入构造

- 逐参数输入构造：不可达上游的探测请求（含确认）
- 边界/非法取值及理由：不可达→`unhealthy`；响应含成本标记
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单次探测，O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 对不可达上游发起探测 | 结果 `unhealthy` 且落库 |
| 2 | 检查响应字段 | 含 `may_have_incurred_cost` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`RULE-MGMT-PROBE`/`T-INF-*` + 人工推导；不调用被测复算。**判据语义以设计验证项 `VRC-MGMT-005` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：不可达→`unhealthy` 持久化；响应含 `may_have_incurred_cost`；互斥

## 6. 错误路径、副作用与清理

- 错误出口与表现：上游不可达不抛错，映射为 `unhealthy` 结果（fail-observed）
- 副作用断言与清理：探测结果落库（隔离库）；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/cases/UT-MGMT-010.py::ProbeUnreachableTests::test_unreachable_probe_is_unhealthy_persisted`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/cases/UT-MGMT-010.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/cases/UT-MGMT-010.py`）；执行状态与 Verdict 见 Run 报告 `run-20261001-04`。
