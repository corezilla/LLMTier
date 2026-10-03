<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-INF-015 — 超大 response 边界内归一

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-INF-015` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-INF-015.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-INF-015`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-INF-015.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-INF-015` / M003 超大 response 分支：超长/超大上游响应体归一（组装，ENV-3） v0.1.0-draft.1 / VRC-INF-003（inference-design §14 / inference.isd §9.1，inference 0.1.0-draft.1） / VRC-INF-003 / boundary / P1（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：边界值（上限/零/空/刚好满、长度、分页越界）+ 条件边界（主要手段：边界外协作者用 loopback `FakeUpstream`（真实 `ThreadingHTTPServer` 上的 OpenAI 兼容假上游，经公开 Registry 入口接线，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M003-超大 response 归一（§2.3 c3）
- 要测什么（责任展开）：超大 body / 极长 SSE 单帧 / 超多事件在模块边界内完整归一、不越界崩溃；超 2 MB 下游响应归系统层（§2.3 c3）（本 Case 责任：2 MiB 输出与 3000 事件在模块边界内完整归一、不越界崩溃；下游预算归系统层）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝inference 组装后超大响应的边界内归一与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`providers/openai.py::complete`（整流读取）、`sse.py::response_stream` 产帧

```text
create(...)  # 上游 2 MiB 输出 / 3000 事件
```

- 初态构造（经公开入口）：真实 cloud provider → loopback `FakeUpstream(mode=oversize / many_events)`
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-3（loopback 假上游）
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：`oversize`：单条 2 MiB `output_text`；`many_events`：3000 个事件；随后 `ok` 作对照
- 边界/非法取值及理由：2 MiB 输出完整返回（长度精确 2 MiB）；3000 事件全部归一（不截断、不崩溃）；对照请求正常；账本 measured
- 规模 / 时间域（数量、分页、复杂度、观测开销）：3 次请求；2 MiB + 3000 事件；O(n) 帧/字节

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `oversize` | `status=completed`，`output[0].content[0].text` 长度 2 MiB，账本 measured |
| 2 | `many_events`（3000） | `status=completed`，账本 measured |
| 3 | 切回 `ok` | 正常完成（服务未受污染） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：方案 §2.3 c3 + inference 模块设计 §14.3；按「模块边界内完整归一」与下游预算归系统层的分工人工推导
- 互斥预期（成功 / 各错误分支）：超大输入在模块内被完整归一，不越界崩溃；恰好一个 terminal

## 6. 错误路径、副作用与清理

- 错误出口与表现：无（不得因体积报错）
- 副作用断言与清理：内存占用随输入线性，无资源泄漏

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-INF-015.py`（3 个）：`test_two_megabyte_output_normalized`、`test_many_events_normalized`、`test_service_remains_healthy_after_oversize`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-INF-015.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
