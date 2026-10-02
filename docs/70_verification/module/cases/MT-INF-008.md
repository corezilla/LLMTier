<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-INF-008 — 产品注入四态（前置阶段）

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-INF-008` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-INF-008.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-INF-008`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-INF-008.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-INF-008` / M003 注入四态：fault_502/fault_503/rate_limit/delay/none（组装） v0.1.0-draft.1 / VRC-INF-003（inference-design §14 / inference.isd §9.1，inference 0.1.0-draft.1） / VRC-INF-003 / recovery / P0（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：故障注入 + 异常路径回滚 + 状态迁移断言（主要手段：边界外协作者用进程内 `FakeAdapter`（`ResponsesService._test_adapter`/`EmbeddingsService._test_adapter` seam，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M003-注入四态；组合：K4
- 要测什么（责任展开）：502→`provider_failure`；503→`provider_unavailable`；rate_limit→429+`Retry-After`；delay→延迟；none→正常；均标 `piko_injected`（本 Case 责任：K4 前置四行注入全部命中且映射正确；命中可由 `piko_injected` 与账本 `source=injected` 观测）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝inference 组装后前置阶段注入四态与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`responses.py::create` 注入分支（fault_502/fault_503/rate_limit/delay/disabled）、`libdiag/injections.py::enabled_injection`

```text
create(...)  # 注入经 diagnostics.set_injections 配置
```

- 初态构造（经公开入口）：`AppFixture` + 真实 `DiagnosticsService`（ENV-1）；注入配置经公开入口 `set_injections`；上游＝`FakeAdapter`
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-3 + ENV-4 确定性注入
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：`fault_502{error_body}`、`fault_503{error_body}`、`rate_limit{retry_after_sec:7}`、`delay{delay_ms:300}`、`enabled=false`
- 边界/非法取值及理由：502→`provider_failure`；503→`provider_unavailable`；rate_limit→429+`Retry-After:7`；delay→耗时 ≥0.25s 且成功；disabled→正常 measured
- 规模 / 时间域（数量、分页、复杂度、观测开销）：5 次请求；delay 注入 300ms；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `fault_502` 启用 | 抛 502 `provider_failure`，`piko_injected.type=fault_502`；账本 `source=injected` |
| 2 | `fault_503` 启用 | 抛 503 `provider_unavailable`（retryable） |
| 3 | `rate_limit` 启用（7s） | 429 `rate_limit_exceeded`，`Retry-After: 7`，账本 `injected` |
| 4 | `delay` 启用（300ms） | 成功返回，耗时 ≥0.25s，账本 measured |
| 5 | `fault_502` 但 `enabled=false` | 正常 completed，账本 measured |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：方案 §3.3 K4 + inference 模块设计 §14.3；按注入优先级与错误码契约人工推导
- 互斥预期（成功 / 各错误分支）：五个注入态全部命中且映射正确；注入命中可观测

## 6. 错误路径、副作用与清理

- 错误出口与表现：502/503/429 注入码精确
- 副作用断言与清理：注入态下账本仍收敛（unknown 或 measured）

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-INF-008.py`（5 个）：`test_fault_502_is_provider_failure_and_injected_source`、`test_fault_503_is_provider_unavailable`、`test_rate_limit_injection_is_429_with_retry_after`、`test_delay_injection_delays_but_succeeds`、`test_none_injection_is_normal`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-INF-008.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
