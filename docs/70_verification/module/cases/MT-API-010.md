<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-API-010 — `_correlation` 分支

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-API-010` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-API-010.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-API-010`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-API-010.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-API-010` / M001 `_correlation` 分支：header/traceparent 命中/未命中/缺省（组装） v0.1.0-draft.2 / VRC-OBS-004（http-api-design §14 / http-api.isd §9.1，http-api 0.1.0-draft.2） / VRC-OBS-004 / normal / P1（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：组装后真实调用 + 等价类划分 + 分支覆盖（主要手段：边界外协作者用进程内 `FakeAdapter`（`ResponsesService._test_adapter` seam，资产 `llmtier-unit-fakes`）；`LargeFakeAdapter` 为其长流子类）
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M001-correlation header/traceparent/缺省
- 要测什么（责任展开）：`X-Correlation-ID` 回显；`traceparent` 合法→提取 32-hex；非法→原样；皆缺→缺省（本 Case 责任：`X-Correlation-ID` 回显；traceparent 合法→提取 32-hex、非法→原样；皆缺→缺省）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝http-api 组装后关联标识四分支与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/http_api/app.py::Handler._correlation`

```text
_correlation() -> str | None; 响应头 X-Correlation-ID
```

- 初态构造（经公开入口）：同 MT-API-001；上游＝`FakeAdapter`（成功流）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2 + ENV-3
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture`（`FakeAdapter`/`AppFixture` 组装契约，见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：`X-Correlation-ID: corr-abc-1`；`traceparent: 00-<32hex>-<16hex>-01`（冻结向量）；`traceparent: zz-not-a-traceparent`；两者皆缺
- 边界/非法取值及理由：合法 traceparent 提取 32-hex；非法原样透传；皆缺则无该响应头；错误信封同样回显
- 规模 / 时间域（数量、分页、复杂度、观测开销）：5 请求；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 带 `X-Correlation-ID` 发 SSE | 响应头回显同值 |
| 2 | 带合法 `traceparent` | 响应头为提取出的 32-hex |
| 3 | 带非法 `traceparent` | 响应头原样 |
| 4 | 两者皆缺 | 响应头无 `X-Correlation-ID` |
| 5 | 带 `X-Correlation-ID` 发非法体（400） | 错误响应头同样回显 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：observability 模块设计 §14.4 + ISD 关联标识契约；按 `_correlation` 正则 `fullmatch` 与分支顺序人工推导
- 互斥预期（成功 / 各错误分支）：四个分支互斥；错误与流式响应回显一致

## 6. 错误路径、副作用与清理

- 错误出口与表现：无错误出口（仅取值分支）
- 副作用断言与清理：correlation 随 trace 落库（`correlation_id`）

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-API-010.py`（5 个）：`test_x_correlation_id_echoed`、`test_valid_traceparent_extracts_32hex`、`test_invalid_traceparent_kept_verbatim`、`test_missing_both_means_no_header`、`test_error_envelope_carries_correlation`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-API-010.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
