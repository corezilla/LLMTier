<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-API-008 — SSE terminal 三态

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-API-008` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-API-008.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-API-008`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-API-008.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-API-008` / M001 SSE terminal 三态：completed/client-abort/error-abort（组装） v0.1.0-draft.2 / VRC-API-003（http-api-design §14 / http-api.isd §9.1，http-api 0.1.0-draft.2） / VRC-API-003 / recovery / P0（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：故障注入 + 异常路径回滚 + 状态迁移断言（主要手段：边界外协作者用进程内 `FakeAdapter`（`ResponsesService._test_adapter` seam，资产 `llmtier-unit-fakes`）；`LargeFakeAdapter` 为其长流子类）
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M001-SSE completed/client-abort/error-abort；组合：K2
- 要测什么（责任展开）：正常流→`completed` trace；客户端断开→`aborted(client disconnected)`；流异常→`aborted(stream_error)` 且落日志；created 首、terminal 唯一、`[DONE]`（本 Case 责任：completed / client-abort / error-abort 三态互斥且可区分；事件子集不越界、terminal 唯一）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝http-api 组装后SSE 终态三态与事件子集与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/http_api/app.py`（SSE 写循环）、`src/http_api/sse.py::response_stream`

```text
POST /v1/responses -> text/event-stream; GET /v1/trace/{request_id}
```

- 初态构造（经公开入口）：同 MT-API-001（ENV-1 + ENV-2）；上游＝`FakeAdapter`（正常/长流/毒载荷）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2 + ENV-3 provider 进程内 fake
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture`（`FakeAdapter`/`AppFixture` 组装契约，见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：① 正常（`FakeAdapter(usage=True)`）；② 客户端读完 `response.created` 后排空在途字节并 `close()`；③ 边界替身返回非对象 `output`（毒载荷）
- 边界/非法取值及理由：`response.created` 首帧；`[DONE]` 末帧；terminal 恰 1 个；断开→`aborted(client disconnected)`；毒载荷→`aborted(stream_error)` + `stream_error` 日志
- 规模 / 时间域（数量、分页、复杂度、观测开销）：①5 帧；②800 output item（长流，保证写侧报错）；③1 帧后异常；O(n) 帧

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 正常流读全量 | 首帧 `response.created`、末帧 `[DONE]`、`response.completed` 恰 1 个；trace 末 stage=`completed` |
| 2 | 长流客户端 `close()` | trace 出现 `aborted` 且 `detail.reason=client disconnected` |
| 3 | 毒载荷流 | trace 出现 `aborted` 且 `reason=stream_error`；`stream_error` 落日志 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：http-api 模块设计 §14.4 + OpenAPI 事件子集；按 SSE 循环三个 `except` 子句与 trace stage 字面量人工推导
- 互斥预期（成功 / 各错误分支）：三态互斥且可区分；事件子集不越界；terminal 唯一

## 6. 错误路径、副作用与清理

- 错误出口与表现：断开与流异常均落 `aborted`，不产生 500
- 副作用断言与清理：异常后连接被 finally 关闭；账本由推理阶段记账（abort 不改记账）

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-API-008.py`（3 个）：`test_completed_terminal_state`、`test_client_abort_is_aborted_client_disconnected`、`test_stream_poison_is_aborted_stream_error_and_logged`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-API-008.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
