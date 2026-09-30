<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-MGMT-001 — 引导与 Secret 引用

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-MGMT-001` |
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
| Canonical Path | `docs/70_verification/specifications/unit-case-UT-MGMT-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-MGMT-001`）；责任摘要、分类与优先级以 [单元测试方案 §3](../schemes/llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [management-design.md](../../40_module_design/management-design.md) §14 / ISD [management.isd.md](../../50_implementation_design/management.isd.md) §9.1，设计验证项 `VRC-MGMT-001`（固定版本 `management 0.1.0-draft.2`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `MGMT`；裁剪依据见 [STD 裁剪清单](../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-MGMT-001` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-MGMT-001` / `VRC-MGMT-001`（management 模块设计 §14 / management-isd §9.1，management 0.1.0-draft.2） / `VRC-MGMT-001` / normal / P0（[方案清单 §3](../schemes/llmtier-unit-test-scheme.md)）。
- 要测什么（责任展开）：被测：`Registry.bootstrap_settings` 合法 settings、重复启动忽略、缺节、`env:` 空/`file:` 不存在 → 503 + 回滚 + not_ready；`ensure_fixed_tiers`。
- 明确不测什么 / 失败含义：不测：真实 secret 管理系统；不测进程启动（系统层）。失败含义＝引导/secret 引用实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/management/registry.py::bootstrap_settings`/`ensure_fixed_tiers`；`src/http_api/app.py` 启动错误捕获

```text
bootstrap_settings(settings) ; ensure_fixed_tiers()
```

- 初态构造（经公开入口）：空库 `AppFixture`；`test_app_startup` 用 `Application` + 临时 settings
- Fixture / 向量及版本：`tests/unit/v03/fakes.py::AppFixture`（ENV-1）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../plans/llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库 / ENV-2 loopback 测试 HTTP 实例 / ENV-3 provider 进程内 fake（按 Case 需要，见 §4）
- 依赖的测试资产（tests.asset-design 文档）：无（真实实现）

## 3. 输入构造

- 逐参数输入构造：合法 settings；重复启动；缺节；`env:` 空；`file:` 不存在
- 边界/非法取值及理由：空库/缺节边界
- 规模 / 时间域（数量、分页、复杂度、观测开销）：O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 合法 bootstrap | Registry 与 hash 一致 |
| 2 | 重复启动 / 忽略外部 settings | 不重复写 |
| 3 | 缺节 / env 空 / file 不存在 | 503 + 回滚 + not_ready |
| 4 | 固定 tier | 7 个 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：系统设计 §3.2/§11 + `CON-CFG-001/2`；人工推导。**判据语义以设计验证项 `VRC-MGMT-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：合法 settings 引导成功且 7 tier 存在；坏 settings → `bootstrap_error`、无 provider、not_ready 503

## 6. 错误路径、副作用与清理

- 错误出口与表现：无（分支互斥）
- 副作用断言与清理：隔离库回滚；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/v03/test_app_startup.py`（7 个）+ `tests/unit/v03/test_registry.py::test_fixed_tiers_exist`（注意：本 Case 的测试函数当前按子句（test case method）映射；若与设计 VRC 不一致，以设计修订回溯后重裁）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/v03/test_app_startup.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/v03`）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。

