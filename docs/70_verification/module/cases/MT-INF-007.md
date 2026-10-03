<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-INF-007 — 准入四出口

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-INF-007` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-INF-007.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-INF-007`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-INF-007.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-INF-007` / M003 准入四出口：404/429 队列满/503 全不健康/429 超时（组装） v0.1.0-draft.1 / VRC-INF-004（inference-design §14 / inference.isd §9.1，inference 0.1.0-draft.1） / VRC-INF-004 / concurrency / P0（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：线程对偶 + 确定性交错 + 调用序断言（主要手段：边界外协作者用进程内 `FakeAdapter`（`ResponsesService._test_adapter`/`EmbeddingsService._test_adapter` seam，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M003-准入四出口；迁移：T5
- 要测什么（责任展开）：无候选→404；队列≥32→429 `Retry-After 30`；全不健康→503 `model_unavailable`；等待超时→429 `Retry-After 1`（本 Case 责任：未知 tier→404；空 tier→能力拒绝（先于准入）；队列满 32→429 + `Retry-After:30`；全不健康→503（T5））
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝inference 组装后准入四出口与队列阈值与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`routing.py::Router.admit`（404/429 队列满/503 全不健康/429 等待超时）

```text
with router.admit(level_id) as candidate; create(...)  # 经 service 驱动
```

- 初态构造（经公开入口）：`AppFixture` + 真实 `Router`/`Store`（ENV-1）；并发经 33 线程
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-3
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：未知 tier；空 tier；队列填满 32（经 `Router.snapshot()` 公开 seam 观测）；全不健康（存储面置 health）
- 边界/非法取值及理由：未知 tier→404 `model_not_found`；空 tier→400 `unsupported_model`；队列 ≥32→429 + `Retry-After: 30`；全不健康→503 `model_unavailable`
- 规模 / 时间域（数量、分页、复杂度、观测开销）：34 线程；队列长度断言经 snapshot；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 未知 tier | 404 `model_not_found` |
| 2 | 空 tier | 400 `unsupported_model`（校验先于准入） |
| 3 | 1 持有 + 32 排队 → 第 33 个 | 429 `rate_limit_exceeded`，`Retry-After: 30` |
| 4 | 全部候选 unhealthy | 503 `model_unavailable`（retryable） |
| 5 | 槽位被占时新请求 | 保持排队、无错误（超时口径见 MT-INF-018） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：inference 模块设计 §14.4 + 准入契约；按 `admit` 四个 `raise` 点与队列阈值人工推导
- 互斥预期（成功 / 各错误分支）：四出口互斥；`Retry-After` 值区分队列满(30)/等待超时(1)

## 6. 错误路径、副作用与清理

- 错误出口与表现：404/400/429/503 四码精确
- 副作用断言与清理：被拒请求的 ticket 从队列移除（无泄漏）

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-INF-007.py`（5 个）：`test_no_candidates_is_404_model_not_found`、`test_empty_tier_is_unsupported_model_before_admit`、`test_all_unhealthy_is_503_model_unavailable`、`test_queue_full_is_429_retry_after_30`、`test_queue_wait_keeps_order_until_capacity`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-INF-007.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
