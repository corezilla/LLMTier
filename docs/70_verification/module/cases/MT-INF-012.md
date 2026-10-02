<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-INF-012 — 上游配额/额度耗尽映射

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-INF-012` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-INF-012.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-INF-012`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-INF-012.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-INF-012` / M003 上游非 5xx 错误分支：配额/额度耗尽（429/402/403）→ 沿用上游码 + `provider_error`（组装） v0.1.0-draft.1 / VRC-INF-003（inference-design §14 / inference.isd §9.1，inference 0.1.0-draft.1） / VRC-INF-003 / recovery / P1（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：故障注入 + 异常路径回滚 + 状态迁移断言（主要手段：边界外协作者用 loopback `FakeUpstream`（真实 `ThreadingHTTPServer` 上的 OpenAI 兼容假上游，经公开 Registry 入口接线，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M003-上游非 5xx 错误（配额/额度耗尽 429/402/403）
- 要测什么（责任展开）：边界替身（`FakeAdapter`/本地 `FakeResponse`）返回上游 **配额/额度耗尽** 4xx 错误体；断言模块按 `openai.py` 映射为**沿用上游码 + `code=provider_error`**（429→`retryable=true`，402/403→`retryable=false`），义务收敛 unknown 不补零，不跨等级 fallback（本 Case 责任：上游 4xx 沿用状态码 + `provider_error`；`retryable` 口径正确；义务收敛 unknown；不跨 tier fallback）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝inference 组装后上游 4xx/配额耗尽的错误映射与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`providers/openai.py::OpenAIProvider._request`/`complete` 的 HTTPError 分支、`responses.py::create` 异常路径

```text
OpenAIProvider._request/_complete -> 映射 ApiError(status=上游码, code=provider_error)
```

- 初态构造（经公开入口）：真实 `Registry` 绑定 cloud provider → loopback `FakeUpstream`（真实 transport）；ENV-1
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-3（loopback 假上游，真实 `urllib` 传输）
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：上游 429/402/403/422 配额与业务错误体；命中计数断言
- 边界/非法取值及理由：沿用上游 status + `code=provider_error`；`retryable`：429/408 真、402/403/422 假；义务收敛 unknown；不跨 tier fallback（上游命中恰 1 次）
- 规模 / 时间域（数量、分页、复杂度、观测开销）：5 次请求；每次 1 次上游命中；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 上游 429 | (429, provider_error, retryable=True) |
| 2 | 上游 402 | (402, provider_error, False) |
| 3 | 上游 403 | (403, provider_error, False) |
| 4 | 上游 422（非配额 4xx） | (422, provider_error, False) |
| 5 | 配额耗尽后查账本与上游命中数 | 账本 final unknown、`input_tokens=NULL`；上游恰 +1 次（无二次尝试） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：方案 §1.5.1 b1/b3 + a22 + inference 模块设计 §14.3；按 `complete/_request` 的 HTTPError 映射人工推导
- 互斥预期（成功 / 各错误分支）：上游 4xx 沿用状态码 + `provider_error`；`retryable` 口径正确；无跨级 fallback；unknown 不补零

## 6. 错误路径、副作用与清理

- 错误出口与表现：402/403/408/422/429 各自 `provider_error`
- 副作用断言与清理：账本义务必收敛（不悬空）

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-INF-012.py`（5 个）：`test_upstream_429_is_provider_error_retryable`、`test_upstream_402_is_provider_error_not_retryable`、`test_upstream_403_is_provider_error_not_retryable`、`test_non_quota_4xx_is_provider_error`、`test_no_cross_tier_fallback`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-INF-012.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
