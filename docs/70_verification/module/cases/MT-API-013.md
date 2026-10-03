<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-API-013 — 连接重置（RST）mid-stream

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-API-013` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-API-013.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-API-013`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-API-013.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-API-013` / M001 连接重置分支：connection reset (RST) mid-stream（组装，ENV-2 真实 socket） v0.1.0-draft.2 / VRC-API-003（http-api-design §14 / http-api.isd §9.1，http-api 0.1.0-draft.2） / VRC-API-003 / recovery / P1（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：故障注入 + 异常路径回滚 + 状态迁移断言（主要手段：边界外协作者用进程内 `FakeAdapter`（`ResponsesService._test_adapter` seam，资产 `llmtier-unit-fakes`）；`LargeFakeAdapter` 为其长流子类）
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M001-连接重置 RST mid-stream（§2.3 c5）
- 要测什么（责任展开）：客户端 `SO_LINGER 0` 关闭触发 RST→`aborted`；进程不崩溃、许可/fd 释放（§2.3 c5）（本 Case 责任：`SO_LINGER 0` 触发的 RST 与 FIN 断开同样落 `aborted`；进程不崩、许可/fd 释放）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝http-api 组装后RST 的终态与资源归还与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`app.py`（SSE 写循环 `ConnectionResetError` 分支）、`Router`

```text
POST /v1/responses（SO_LINGER 0 关闭触发 RST）; GET /v1/trace/{id}, /v1/runtime, /healthz
```

- 初态构造（经公开入口）：同 MT-API-001；上游＝`LargeFakeAdapter`（800 output item 长流）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2（真实 socket，RST）+ ENV-3
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture`（`FakeAdapter`/`AppFixture` 组装契约，见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：排空在途字节后 `setsockopt(SO_LINGER, {1,0})` + `close()`（方案 §2.3 c5）
- 边界/非法取值及理由：`aborted(client disconnected)`；进程存活；许可归零；fd 不增长
- 规模 / 时间域（数量、分页、复杂度、观测开销）：1 次长流 + 3 次观测请求；O(n) 帧

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 长流发起到 `response.created` 后 RST 关闭 | trace 出现 `aborted` |
| 2 | `GET /healthz` | 200（进程不崩） |
| 3 | `GET /v1/runtime` 轮询 | `running` 归 0（许可/fd 释放） |
| 4 | 比对 fd 基线 | ≤ 基线 +2 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：方案 §2.3 c5 + http-api 模块设计 §14.4；按 RST 触发 `ConnectionResetError` 的分支人工推导
- 互斥预期（成功 / 各错误分支）：RST 与 FIN 断开同样落 `aborted`；进程与许可面无副作用

## 6. 错误路径、副作用与清理

- 错误出口与表现：RST 不得升级为 500 或挂起请求线程
- 副作用断言与清理：连接在 finally 关闭；fd 归还

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-API-013.py`（1 个）：`test_rst_mid_stream_aborts_without_crash`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-API-013.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
