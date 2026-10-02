<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-INF-018 — 队列等待超时与许可泄漏

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-INF-018` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-INF-018.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-INF-018`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-INF-018.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-INF-018` / M003 并发超时 + 许可泄漏分支：队列等待超时后许可归零（组装，ENV-1） v0.1.0-draft.1 / VRC-INF-004（inference-design §14 / inference.isd §9.1，inference 0.1.0-draft.1） / VRC-INF-004 / concurrency / P1（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：线程对偶 + 确定性交错 + 调用序断言（主要手段：边界外协作者用进程内 `FakeAdapter`（`ResponsesService._test_adapter` seam，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M003-并发超时 + 许可泄漏（§1.5.1 c8）
- 要测什么（责任展开）：`Router.admit` 等待超 `30 s`→429 `rate_limit_exceeded`+`Retry-After`；`_inflight` 归零、无许可泄漏（§1.5.1 c8）（本 Case 责任：受控时钟下等待超 30s→429 + `Retry-After:1`；`_inflight` 归零、无许可泄漏）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝inference 组装后等待超时出口与许可归还与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`routing.py::Router.admit`（deadline 30s 分支）、`usage.py`（拒绝无 finish）

```text
admit(level_id)  # 受控时钟推进越过 30s deadline
```

- 初态构造（经公开入口）：`AppFixture` 真实组装（ENV-1）；受控时钟（`patch("inference.routing.time", FakeClock)`，方案 §1「受控时钟」资产口径）；provider 节流经公开入口 PATCH `usage.min_request_interval_ms` 制造确定性等待窗
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-3（`BlockingAdapter` 持有槽位）
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：1 持有者占槽 + 1 等待者入队；时钟推进 31s；释放后再 1 请求
- 边界/非法取值及理由：等待超时→429 `rate_limit_exceeded` + `Retry-After: 1`（区别队列满的 30）；`_inflight` 归零；后续请求成功（无许可泄漏）
- 规模 / 时间域（数量、分页、复杂度、观测开销）：2 线程 + 2 次后续请求；等待窗 ≈1s；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 持有者占槽，等待者入队后推进时钟 31s | 等待者抛 429，`Retry-After: 1`，retryable |
| 2 | 释放持有者后轮询 `snapshot()` | `running=0`（许可归零） |
| 3 | 换正常适配器再请求 | completed（无许可泄漏） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：方案 §1.5.1 c8 + a20 + inference 模块设计 §14.4；按 `admit` 的 `remaining <= 0` 分支与 `Retry-After` 字面量人工推导
- 互斥预期（成功 / 各错误分支）：等待超时码与 `Retry-After` 精确；许可归零；后续请求不受影响

## 6. 错误路径、副作用与清理

- 错误出口与表现：429 `rate_limit_exceeded`（`Retry-After: 1`）
- 副作用断言与清理：被拒等待者 ticket 从队列移除；无许可泄漏

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-INF-018.py`（2 个）：`test_queue_wait_timeout_is_429_retry_after_1`、`test_no_permit_leak_after_timeout`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-INF-018.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
