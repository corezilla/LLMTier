<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-MGMT-011 — 固定 tier 删除分支

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-MGMT-011` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-MGMT-011.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-MGMT-011`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-MGMT-011.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-MGMT-011` / M004 固定 tier 删除分支：固定 service level→409 `fixed_service_level`（组装） v0.1.0-draft.3 / VRC-MGMT-002（management-design §14 / management.isd §9.1，management 0.1.0-draft.3） / VRC-MGMT-002 / negative / P1（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（非法字段/凭据/引用/类型/顺序）+ 判定表组合（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M004-固定 tier 删除 `fixed_service_level`（§1.5.1 a16）
- 要测什么（责任展开）：删除固定 tier（固定 service level）→409 `fixed_service_level`，资源不变；对照 `src/management/registry.py:379`（§1.5.1 a16）（本 Case 责任：删除固定 service level→409 `fixed_service_level`；资源内容与版本逐字段不变）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝management 组装后固定 tier 不可删与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`registry.py::Registry.delete_service_level`、`app.py` DELETE 资源路由

```text
delete_service_level(rid, if_match) -> 无条件 409
```

- 初态构造（经公开入口）：`AppFixture` + `seed()`（ENV-1）+ ENV-2
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：7 个固定 tier 逐一 `DELETE`（ETag 取自 `GET`）；删除前后资源视图比对
- 边界/非法取值及理由：全部 7 tier 删除均 409 `fixed_service_level`（无视 `If-Match`）；资源内容与版本在拒绝后逐字段不变
- 规模 / 时间域（数量、分页、复杂度、观测开销）：7 次 DELETE + 2 次 GET；O(7)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `DELETE /v1/service-levels/Worker` | 409 `fixed_service_level` |
| 2 | 逐一 DELETE 7 个固定 tier | 均 409 `fixed_service_level` |
| 3 | 拒绝后 `GET /v1/service-levels/Worker` | 与删除前逐字段相等（资源不变） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：方案 §1.5.1 a16 + management 模块设计 §14.2（固定 Tier 不可删）；按 `delete_service_level` 的无条件 `raise` 人工推导
- 互斥预期（成功 / 各错误分支）：固定 tier 恒不可删；拒绝无副作用

## 6. 错误路径、副作用与清理

- 错误出口与表现：409 `fixed_service_level`（唯一）
- 副作用断言与清理：无任何写入

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-MGMT-011.py`（3 个）：`test_delete_fixed_tier_is_409_fixed_service_level`、`test_resource_unchanged_after_rejected_delete`、`test_all_fixed_tiers_reject_delete`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-MGMT-011.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
