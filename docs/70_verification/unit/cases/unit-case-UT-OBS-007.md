<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-OBS-007 — 关联标识回显与 traceparent trace-id 提取

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-OBS-007` |
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
| Canonical Path | `docs/70_verification/unit/cases/unit-case-UT-OBS-007.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-OBS-007`）；责任摘要、分类与优先级以 [单元测试方案 §3](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [observability](../../../40_module_design/observability-design.md) §14 / ISD [observability.isd.md](../../../50_implementation_design/observability.isd.md) §9.1，设计验证项 `VRC-OBS-004`（固定版本 `observability 0.1.0-draft.6`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `observability`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-OBS-007` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-OBS-007` / M005 observability §14.4 · `_correlation` traceparent v0.1.0-draft.6 / `VRC-OBS-004` / normal / P1（[方案清单 §3](../llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：等价类划分（关联标识回显/提取）
- 要测什么（责任展开）：被测：`X-Correlation-ID` 有则回显；缺省时 `traceparent`→提取 trace-id；无头时缺省无该响应头。
- 明确不测什么 / 失败含义：不测：trace 落库查询（UT-OBS-004）；不测 API 层参数（UT-API-007 与之共担）。失败含义＝关联标识提取/回显实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/http_api/app.py::Handler._correlation`（observability 侧经入口透传/回显）

```text
Handler._correlation() -> str | None
```

- 初态构造（经公开入口）：`AppFixture().seed()` + loopback `handler_factory(app)`（ENV-2）
- Fixture / 向量及版本：`tests/unit/v03/test_observability_gaps.py::CorrelationObservabilityTests`；`fakes.py::AppFixture`（ENV-1）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-2 loopback 测试 HTTP 实例
- 依赖的测试资产（tests.asset-design 文档）：无（真实实现）

## 3. 输入构造

- 逐参数输入构造：带 `X-Correlation-ID`；带 `traceparent: 00-<32hex>-<16hex>-01`；两者皆缺
- 边界/非法取值及理由：有头→回显；仅 traceparent→提取；皆缺→无头（三态互斥）
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单请求，O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 传 `X-Correlation-ID` | 响应头回显 |
| 2 | 传 `traceparent` | 提取 32-hex trace-id |
| 3 | 无头 | 无 `X-Correlation-ID` 响应头 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`RULE-OBS-CORR` + W3C traceparent 正则 + 人工推导；不调用被测复算。**判据语义以设计验证项 `VRC-OBS-004` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：显式回显、traceparent 提取、无头缺省；三态互斥

## 6. 错误路径、副作用与清理

- 错误出口与表现：无（缺省即 None）
- 副作用断言与清理：correlation 落 trace（诊断开时）；loopback 实例清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/v03/test_observability_gaps.py::CorrelationObservabilityTests::test_explicit_correlation_id_is_echoed` / `test_traceparent_trace_id_is_extracted` / `test_no_correlation_header_is_absent`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/v03/test_observability_gaps.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/v03/test_observability_gaps.py`）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。
