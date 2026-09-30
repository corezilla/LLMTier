<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-API-009 — 请求体边界与非法 JSON 映射

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-API-009` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-09-30` |
| Template ID | `tests.unit-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/unit-case-UT-API-009.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-API-009`）；责任摘要、分类与优先级以 [单元测试方案 §3](../schemes/llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [http-api](../../40_module_design/http-api-design.md) §14 / ISD [http-api.isd.md](../../50_implementation_design/http-api.isd.md) §9.1，设计验证项 `VRC-API-003`（固定版本 `http-api 0.1.0-draft.2`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `http_api`；裁剪依据见 [STD 裁剪清单](../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-API-009` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-API-009` / M001 http-api §14.1 · `Handler._body` v0.1.0-draft.2 / `VRC-API-003` / boundary / P0（[方案清单 §3](../schemes/llmtier-unit-test-scheme.md)）。
- 要测什么（责任展开）：被测：`Handler._body` 对 body > 2 MB → 413 `request_too_large`；非法 JSON → 400 `invalid_json`；顶层非对象 → 400 `invalid_json`；`Content-Length` 非整数 → 400 `invalid_request`。
- 明确不测什么 / 失败含义：不测：body 校验之后的业务；不测 SSE wire（UT-API-003）。失败含义＝请求体限长/解析实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/http_api/app.py::Handler._body`

```text
Handler._body() -> dict  # 读 Content-Length，限长 2 MB，json.loads，要求顶层为对象
```

- 初态构造（经公开入口）：`AppFixture().seed()` + loopback `handler_factory(app)`（ENV-2）
- Fixture / 向量及版本：`tests/unit/v03/fakes.py::AppFixture`（ENV-1）+ `test_app_dispatch.py::BodyTests`（ENV-2）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../plans/llmtier-unit-test-plan.md) 分配）：ENV-2 loopback 测试 HTTP 实例
- 依赖的测试资产（tests.asset-design 文档）：无（真实实现）

## 3. 输入构造

- 逐参数输入构造：声明 `Content-Length=2*1024*1024+1`（不发送 body）；非法 JSON 字节；顶层为数组/数字的 JSON；非整数 `Content-Length`
- 边界/非法取值及理由：2 MB 边界上/下；四类非法互斥
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单请求，O(body 长度)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 声明超 2 MB `Content-Length` | 413 + `error.code=request_too_large` |
| 2 | 发送非法 JSON | 400 + `error.code=invalid_json` |
| 3 | 顶层非对象 | 400 + `error.code=invalid_json` |
| 4 | 非整数 `Content-Length` | 400 + `error.code=invalid_request` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`IF-API-BODY` 规则 + 人工推导；不调用被测复算。**判据语义以设计验证项 `VRC-API-003` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：>2 MB 413；非法 JSON 400 `invalid_json`；顶层非对象 400 `invalid_json`；非整数长度 400 `invalid_request`；四分支互斥

## 6. 错误路径、副作用与清理

- 错误出口与表现：413/400 各错误码独立；无第三态
- 副作用断言与清理：无写库；loopback 实例清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/v03/test_app_dispatch.py::BodyTests::test_body_over_2mb_is_413` / `test_invalid_json_is_400` / `test_top_level_non_object_is_400` / `test_non_integer_content_length_is_400`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/v03/test_app_dispatch.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/v03/test_app_dispatch.py`）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。
