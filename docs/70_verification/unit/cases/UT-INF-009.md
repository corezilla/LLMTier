<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-INF-009 — Router 限流、快照与模型可用性错误码

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-INF-009` |
| Document Version | `0.1.0-draft.3` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.unit-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/unit/cases/UT-INF-009.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-INF-009`）；责任摘要、分类与优先级以 [单元测试方案 §6](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [inference](../../../40_module_design/inference-design.md) §14 / ISD [inference.isd.md](../../../50_implementation_design/inference.isd.md) §9.1，设计验证项 `VRC-INF-004`（固定版本 `inference 0.1.0-draft.1`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `inference`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-INF-009` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-INF-009` / M003 inference §14.4 · `Router` 限流/快照/模型码 v0.1.0-draft.1 / `VRC-INF-004` / boundary / P0（[方案清单 §6](../llmtier-unit-test-scheme.md)）。
- **测试方法（§2.1 方法表行）**：边界值（队列满/超时/节流/快照形状）（主要手段：直接调用 + 替身注入）
- 要测什么（责任展开）：被测：队列满/Wait 超时 → 429 + `Retry-After`；provider RPM/`min_interval` 节流；`snapshot()` 形状；degraded/unknown 健康 → 503 `model_unavailable`。
- 明确不测什么 / 失败含义：不测：准入成功/FIFO 主路径（UT-INF-004）；不测真实计时精度。失败含义＝限流边界、快照形状或模型可用性错误码实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/inference/routing.py::Router.admit`/`snapshot`（队列满、等待超时、RPM/min_interval 节流、健康判定）

```text
Router.admit(level_id); Router.snapshot() -> dict; 429 带 Retry-After；503 model_unavailable
```

- 初态构造（经公开入口）：`AppFixture().seed()` 并构造队列占满/限流配置；`Router` 真实实例（ENV-1）
- Fixture / 向量及版本：`tests/unit/cases/UT-INF-009.py::RoutingAdmissionGapTests`；`fakes.py::AppFixture`（ENV-1）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库
- 依赖的测试资产（tests.asset-design 文档）：无（真实实现）

## 3. 输入构造

- 逐参数输入构造：队列占满；等待超时；provider RPM/min_interval 触发；degraded/unknown 健康；正常快照
- 边界/非法取值及理由：队列满/超时二分支均 429 + `Retry-After`；degraded/unknown 503；快照形状固定
- 规模 / 时间域（数量、分页、复杂度、观测开销）：O(候选数)；等待用受控时序

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 队列满 | 429 `rate_limit_exceeded` + `Retry-After` |
| 2 | 等待超时 | 429 + `Retry-After` |
| 3 | provider RPM/min_interval | 被节流 |
| 4 | `snapshot()` | 形状断言 |
| 5 | degraded/unknown | 503 `model_unavailable` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`RULE-INF-ROUTE`/`T-INF-03` 规则 + `CAP-INF-*` + 人工推导；不调用被测复算。**判据语义以设计验证项 `VRC-INF-004` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：队列满/超时 429+`Retry-After`；RPM/min_interval 节流；快照形状正确；degraded/unknown 503 `model_unavailable`；互斥

## 6. 错误路径、副作用与清理

- 错误出口与表现：429 `rate_limit_exceeded`；503 `model_unavailable`；无第三态
- 副作用断言与清理：未受理请求无副作用；许可随上下文退出释放；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/cases/UT-INF-009.py::RoutingAdmissionGapTests::test_queue_full_is_429_with_retry_after` / `test_wait_timeout_is_429_with_retry_after` / `test_provider_min_interval_throttles` / `test_provider_rpm_throttles` / `test_snapshot_shape` / `test_degraded_health_blocks_admission_503` / `test_unknown_health_blocks_admission_503`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/cases/UT-INF-009.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/cases/UT-INF-009.py`）；执行状态与 Verdict 见 Run 报告 `run-20261001-04`。
