<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-MGMT-014 — `/v1/stats` 汇总组装链

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-MGMT-014` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-MGMT-014.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-MGMT-014`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-MGMT-014.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-MGMT-014` / M004 management §9 · `Admin.stats` 汇总（组装） v0.1.0-draft.3 / VRC-MGMT-004（management-design §14 / management.isd §9.1，management 0.1.0-draft.3） / VRC-MGMT-004 / negative / P1（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（非法字段/凭据/引用/类型/顺序）+ 判定表组合（主要手段：边界外协作者用进程内 `FakeAdapter`（`ResponsesService._test_adapter` seam，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：无（层① 接口行为分母行）
- 要测什么（责任展开）：组装后 `/v1/stats`：`from`/`to` 缺失→400（app 层校验）、`group_by` tier/deployment 两分组结构与键、`group_by` 缺省 tier、非法 `group_by`→400（本 Case 责任：`/v1/stats`：`from`/`to` 缺失→400（app 层）、`group_by` tier/deployment 两分组结构与键、缺省 tier、非法 group_by→400）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝management 组装后统计端点的组装层校验与分组结构与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/http_api/app.py` 路由（`/v1/stats`，含 `from`/`to` 必填校验与 `group_by` 缺省）、`src/management/admin.py::stats`

```text
GET /v1/stats?from=&to=&group_by=tier|deployment -> {"data": [...]}
```

- 初态构造（经公开入口）：`AppFixture` + `seed()`（ENV-1）+ ENV-2；用量经公开入口 `responses.create` 造数（上游＝`FakeAdapter`）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2 + ENV-3
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：缺 `from`；缺 `to`；`group_by=tier`；`group_by=deployment`；缺省 group_by；非法 group_by
- 边界/非法取值及理由：缺 from/to→400 `invalid_request`（app 层校验，UT 直接调 admin.stats 不经此）；tier 分组键为 tier；deployment 分组键含 deployment_id；缺省→tier；非法→400（admin 层）
- 规模 / 时间域（数量、分页、复杂度、观测开销）：6 请求 + 2 条用量；O(n)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 缺 `from` 或 `to` | 400 `invalid_request`（app 层） |
| 2 | `group_by=tier` | 200，`data` 含 tier 键的记录 |
| 3 | `group_by=deployment` | 200，`data` 含 deployment 维度 |
| 4 | 缺省 group_by | 等同 tier |
| 5 | 非法 group_by | 400（admin 层 `require`） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：management 设计 §14.4 + http-api 设计 §9；按 `app.py` 的 `from/to` 必填分支与 `admin.stats` 的 `group_by` 校验人工推导
- 互斥预期（成功 / 各错误分支）：组装层必填校验与两分组结构正确；非法 group_by 400

## 6. 错误路径、副作用与清理

- 错误出口与表现：400 `invalid_request`（from/to 缺；非法 group_by）
- 副作用断言与清理：查询不改库

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-MGMT-014.py`（5 个）：`test_missing_from_or_to_is_400`、`test_group_by_tier_structure_and_keys`、`test_group_by_deployment_structure_and_keys`、`test_group_by_defaults_to_tier`、`test_invalid_group_by_is_400`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-MGMT-014.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
