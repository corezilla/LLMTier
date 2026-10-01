<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-API-003 — 请求体上限与 SSE 单帧/事件序列

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-API-003` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-10-01` |
| Template ID | `tests.unit-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/unit/cases/UT-API-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-API-003`）；责任摘要、分类与优先级以 [单元测试方案 §3](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [http-api-design.md](../../../40_module_design/http-api-design.md) §14 / ISD [http-api.isd.md](../../../50_implementation_design/http-api.isd.md) §9.1，设计验证项 `VRC-API-003`（固定版本 `http-api 0.1.0-draft.2`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `API`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-API-003` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-API-003` / `VRC-API-003`（http-api 模块设计 §14 / http-api-isd §9.1，http-api 0.1.0-draft.2） / `VRC-API-003` / boundary / P0（[方案清单 §3](../llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：边界值（单帧/事件序列/terminal 唯一）（主要手段：直接调用 + 冻结向量）
- 要测什么（责任展开）：被测：body 上限检查（`Content-Length > 2*1024*1024` → 413 `request_too_large`）与非法 JSON 400；`src/http_api/sse.py::frame` 合法帧、事件序列单调、`[DONE]` 终止、terminal 唯一。
- 明确不测什么 / 失败含义：不测：真实网络断开恢复（系统层）；不测上游事件内容正确性。失败含义＝body 上限/SSE 帧契约实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/http_api/sse.py::frame`/`response_stream`/`events`；`app.py::_body`

```text
frame(event, data) -> bytes; response_stream(response) -> iterable[bytes]; events(response) -> list[dict]
```

- 初态构造（经公开入口）：`AppFixture`；SSE 用 `events(FakeAdapter.complete(...))` 构造响应
- Fixture / 向量及版本：`tests/common/fakes.py::FakeAdapter`（ENV-3）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库 / ENV-2 loopback 测试 HTTP 实例 / ENV-3 provider 进程内 fake（按 Case 需要，见 §4）
- 依赖的测试资产（tests.asset-design 文档）：无（真实实现）

## 3. 输入构造

- 逐参数输入构造：合法/非法 frame；标准 response；incomplete 终态；refusal/function_arguments
- 边界/非法取值及理由：`Content-Length == 2097152` 与 `2097153` 边界；sequence_number 从 0 单调
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单响应 ≤ 数帧，O(帧数)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `frame("x",{"a":1})` | `event: x` 前缀与 data |
| 2 | `events(response())` | 序号 0..n、created 首、completed 末 |
| 3 | refusal / function_arguments 事件 | delta 字段 |
| 4 | `response_stream` 末帧 | `[DONE]` 标记 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：OpenAPI 事件子集 + `RULE-API-SSE`；人工推导，不调用被测复算。**判据语义以设计验证项 `VRC-API-003` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：帧以 `event: <name>\n` 起、`data:` JSON、`\n\n` 止；sequence_number 单调 0..4；`[DONE]` 为最后字节；恰好一个 terminal

## 6. 错误路径、副作用与清理

- 错误出口与表现：非法 JSON → 400（由 body 解析路径，属本 VRC 范围）
- 副作用断言与清理：无副作用；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/cases/UT-API-003.py`（全部 9 个测试）+ HTTP 层 413 断言由系统 case 覆盖（本层贡献 SSE 帧/序列）（注意：本 Case 的测试函数当前按子句（test case method）映射；若与设计 VRC 不一致，以设计修订回溯后重裁）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/cases/UT-API-003.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit`）；执行状态与 Verdict 见 Run 报告 `run-20261001-04`。

