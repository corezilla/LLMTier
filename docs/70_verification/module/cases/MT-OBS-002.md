<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-OBS-002 — 诊断开关分支

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-OBS-002` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-OBS-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-OBS-002`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-OBS-002.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-OBS-002` / M005 开关分支：默认关/开/部分更新保留/关闭零写入（组装） v0.1.0-draft.6 / VRC-OBS-001（observability-design §14 / observability.isd §9.1，observability 0.1.0-draft.6） / VRC-OBS-001 / normal / P1（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：组装后真实调用 + 等价类划分 + 分支覆盖（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M005-开关四分支；迁移：T9、T9
- 要测什么（责任展开）：经 M001 端点切换快照/统计开关，关闭时零写入，部分更新保留另一开关（本 Case 责任：默认关/部分更新保留/空体保持/非法值 400/关闭态零写入五态互斥（T9））
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝observability 组装后开关语义与零写入与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`app.py`（`/v1/diagnostics` GET/PATCH）、`libdiag/settings.py::SettingsDiagnostics.set_switches`

```text
GET/PATCH /v1/diagnostics; libdiag capture_snapshot/record_latency 开关闸门
```

- 初态构造（经公开入口）：`AppFixture` 真实组装（ENV-1）+ ENV-2；每测试方法独立夹具（`PerTestLoopbackEnv`）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2 + ENV-3
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：新建实例默认态；`PATCH` 双开；只 PATCH 一个键；空体 PATCH；非布尔值；未知键；关闭后发请求再查
- 边界/非法取值及理由：默认两开关均 false；部分更新保留另一开关；空体 PATCH 不变；非布尔→400 `invalid_request`（`param=<键>`）；未知键→400 且不改状态；关闭态下快照/统计零写入（trace 无开关闸门，见方案 §4 观察项）
- 规模 / 时间域（数量、分页、复杂度、观测开销）：9 个测试方法 ×（1–2 请求）；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 新实例 `GET /v1/diagnostics` | 两开关均 false |
| 2 | `PATCH` 双开 | 200 且两开关 true；审计出现 `diagnostics.switch.update` 成功行 |
| 3 | 只 PATCH `snapshots_enabled` | `stats_enabled` 保持原值 |
| 4 | 空体 PATCH | 两开关不变 |
| 5 | 非布尔 PATCH | 400 `invalid_request`，无审计成功行 |
| 6 | 未知键 PATCH | 400，状态不变 |
| 7 | 关闭双开关后发请求 | snapshots 与 stats 均 0 行（零写入） |
| 8 | 只关快照（统计开） | 快照 0 行、统计有行 |
| 9 | 只关统计（快照开） | 统计 0 行、快照有行 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：observability 模块设计 §14.1 + 方案 §3.4 T9；按 `set_switches` 的 None 保留语义与两个记录面的开关闸门人工推导
- 互斥预期（成功 / 各错误分支）：默认关/部分更新/空体/非法值/未知键五态互斥；关闭态零写入可验证

## 6. 错误路径、副作用与清理

- 错误出口与表现：400 `invalid_request`（非布尔/未知键）
- 副作用断言与清理：开关更新与审计同事务（`mutate`）

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-OBS-002.py`（9 个）：`test_switches_are_off_by_default_on_a_fresh_store`、`test_patch_enables_both_switches_and_audit_records_success`、`test_partial_patch_preserves_the_other_switch`、`test_empty_patch_keeps_both_switches`、`test_non_boolean_switch_is_400_and_writes_no_audit_row`、`test_unknown_switch_field_is_400_and_leaves_state_untouched`、`test_disabled_switches_write_no_snapshot_and_no_stats_row`、`test_snapshots_off_keeps_stats_on`、`test_stats_off_keeps_snapshots_on`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-OBS-002.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
