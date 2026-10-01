<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-INF-008 — 上游失败映射、usage 部分未知与 provider_request_id no-op

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-INF-008` |
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
| Canonical Path | `docs/70_verification/unit/cases/unit-case-UT-INF-008.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-INF-008`）；责任摘要、分类与优先级以 [单元测试方案 §3](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [inference](../../../40_module_design/inference-design.md) §14 / ISD [inference.isd.md](../../../50_implementation_design/inference.isd.md) §9.1，设计验证项 `VRC-INF-003`（固定版本 `inference 0.1.0-draft.1`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `inference`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-INF-008` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-INF-008` / M003 inference §14.3 · `_adapter`/`record_provider_request_id` v0.1.0-draft.1 / `VRC-INF-003` / recovery / P1（[方案清单 §3](../llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：故障注入 + 异常路径恢复（URL/超时错误→503/usage 非整数→unknown）
- 要测什么（责任展开）：被测：上游 URL/超时错误 → 503 `provider_unavailable`；usage 非整数部分→ unknown + NULL；空 `provider_request_id` → 经服务路径 no-op；注入源记录 `source='injected'`。
- 明确不测什么 / 失败含义：不测：真实 provider 协议（契约/系统层）；不测终态唯一（UT-INF-003）。失败含义＝上游失败映射/用量未知处理/绑定 no-op 实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/inference/providers/openai.py::_request`/`complete`（`urllib.error.URLError`/`TimeoutError`→503）与 `src/inference/responses.py::ResponsesService._adapter`；`src/inference/usage.py::record_provider_request_id`

```text
ProviderAdapter._request(...) -> (dict, headers); UsageRecorder.record_provider_request_id(principal, request_id, provider_request_id)
```

- 初态构造（经公开入口）：`AppFixture().seed()`；`service._adapter` 注入失败 `FakeAdapter` 或 patch `urllib.request.urlopen` 抛 `URLError`（ENV-3）
- Fixture / 向量及版本：`tests/unit/v03/test_responses.py::ResponsesValidationGapTests` / `test_provider_openai.py` / `test_inference_failopen.py`；`fakes.py::AppFixture`（ENV-1）/`FakeAdapter`（ENV-3）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库 / ENV-3 provider 进程内 fake
- 依赖的测试资产（tests.asset-design 文档）：`FakeAdapter`（`llmtier-unit-fakes`，资产文档已建）

## 3. 输入构造

- 逐参数输入构造：抛 `URLError`/`TimeoutError` 的 `urlopen`；usage 含非整数部分的 provider 结果；空 `provider_request_id`；注入故障命中
- 边界/非法取值及理由：503 映射；usage 部分非整数→NULL/unknown；空 id→no-op
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单请求，O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `urlopen` 抛 `URLError` | 503 `provider_unavailable` |
| 2 | usage 非整数部分 | unknown + NULL，不补零 |
| 3 | 空 `provider_request_id` 经服务路径 | 绑定 no-op |
| 4 | 注入故障命中 | usage `source='injected'` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`E-INF-UPSTREAM`/`RULE-INF-TERMINAL` + T-INF-08 + 人工推导；不调用被测复算。**判据语义以设计验证项 `VRC-INF-003` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：上游 URL/超时 503 `provider_unavailable`；usage 部分非整数 unknown+NULL（不补零）；空 provider_request_id no-op；注入源 `injected`；互斥

## 6. 错误路径、副作用与清理

- 错误出口与表现：503 `provider_unavailable`（上游）；未知量不补零；无第三态
- 副作用断言与清理：usage 义务/账本按 unknown 落库（隔离库）；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/v03/test_provider_openai.py::test_probe_uses_authenticated_models_endpoint`（URL/auth）+ `test_url_error_maps_to_provider_unavailable` / `test_timeout_maps_to_provider_unavailable` / `test_remote_disconnect_maps_to_provider_unavailable`（URL/超时/断开 → 503 `provider_unavailable`）+ `test_responses.py::ResponsesValidationGapTests::test_usage_non_integer_partial_is_unknown_with_nulls` / `test_empty_provider_request_id_is_noop_via_service` / `test_injected_source_recorded_on_injected_fault` + `test_inference_failopen.py::test_upstream_fault_still_surfaces_when_diagnostic_writes_fail`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/v03/test_responses.py tests/unit/v03/test_provider_openai.py tests/unit/v03/test_inference_failopen.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/v03`；上游 503 映射另由 `test_provider_openai.py`/`test_inference_failopen.py` 覆盖）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。
