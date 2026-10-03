<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-DIAG-003 — 注入校验六分支

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-DIAG-003` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-10-02` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.module-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/module/cases/MT-DIAG-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-DIAG-003`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-DIAG-003.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-DIAG-003` / M006 注入校验分支：未知类型/enabled 非布尔/config 非对象/缺字段/越界/error_body 空或超长（组装） v0.1.0-draft.6 / VRC-DIAG-004（libdiag-design §14 / libdiag.isd §9.1，libdiag 0.1.0-draft.6） / VRC-DIAG-004 / negative / P0（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：错误猜测 + 反例驱动（非法字段/凭据/引用/类型/顺序）+ 判定表组合（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M006-注入校验六分支；组合：K8
- 要测什么（责任展开）：六类判定分支分别断言 400 `invalid_injection`；error_body >512 截断；`malformed_event_type` 非法 400（本 Case 责任：六类校验出口 400 + `param` 精确；`error_body` 超 512 截断；范围边界值被接受；全批原子性）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝libdiag 组装后注入配置校验矩阵与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`libdiag/injections.py::InjectionDiagnostics._validate`（类型/enabled/config/范围/截断）

```text
_validate(item) -> {"type", "config", "enabled"}
```

- 初态构造（经公开入口）：`AppFixture` 真实组装（ENV-1）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-4
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：`enabled` 非布尔（`"true"/1/None/[]`）；`config` 非对象（`"x"/5/[1]`）；五类缺 config 字段；`delay_ms` 越界（`-1/60001/1.5/True/"5"`）；`malformed_event_type` 非法；`error_body` 空/非字符串；900 字 `error_body`；范围边界 0/60000/300；半程失败不落库
- 边界/非法取值及理由：六类出口均 400 `invalid_injection` 且 `param` 指向违规字段；`error_body` 截断为 512 字节；边界值（0/60000/300/1）被接受；`bool` 被显式排除为整数；任一项失败则整批不落库
- 规模 / 时间域（数量、分页、复杂度、观测开销）：9 个测试方法；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `enabled` 四种非布尔 | 均 400（`param=enabled`） |
| 2 | `config` 三种非对象 | 均 400（`param=config`） |
| 3 | 五类缺 config 字段 | 均 400（`param` 为缺失字段名） |
| 4 | `delay_ms` 五种越界/错类型 | 均 400（`param=delay_ms`） |
| 5 | `malformed_event_type` 三种非法 | 均 400（`param=malformed_event_type`） |
| 6 | `error_body` 空与非字符串 | 均 400（`param=error_body`） |
| 7 | 900 字 `error_body` | 读回 512 字节且仍为 `z` 前缀 |
| 8 | 范围边界 0/60000/0/300 + `stream_terminate_after_events=1` | 均被接受且读回一致（按类型取行，不依赖行序） |
| 9 | 合法项 + 非法项同批 | 整批不落库（`injections()` 为空） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：libdiag 模块设计 §14.4 + 方案 §6.3 K8；按 `_validate` 的六个 `require` 顺序与 `_RANGES` 上下界人工推导
- 互斥预期（成功 / 各错误分支）：六类校验出口全覆盖；截断与边界值处理正确；原子性（全批成功或全批不写）

## 6. 错误路径、副作用与清理

- 错误出口与表现：400 `invalid_injection`（全部出口）
- 副作用断言与清理：校验失败零写入

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-DIAG-003.py`（9 个）：`test_enabled_non_boolean_is_400`、`test_config_non_object_is_400`、`test_missing_config_field_is_400`、`test_delay_out_of_range_is_400`、`test_malformed_event_type_invalid_is_400`、`test_error_body_empty_or_non_string_is_400`、`test_error_body_over_512_is_truncated`、`test_range_boundaries_accepted`、`test_validation_failure_writes_nothing`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-DIAG-003.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
