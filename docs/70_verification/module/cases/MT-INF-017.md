<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-INF-017 — 畸形帧与非 SS 帧

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-INF-017` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-INF-017.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-INF-017`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-INF-017.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-INF-017` / M003 畸形帧分支：非 JSON `data:` 行 / 坏 SSE 块（组装，ENV-3） v0.1.0-draft.1 / VRC-INF-003（inference-design §14 / inference.isd §9.1，inference 0.1.0-draft.1） / VRC-INF-003 / negative / P0（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（非法字段/凭据/引用/类型/顺序）+ 判定表组合（主要手段：边界外协作者用 loopback `FakeUpstream`（真实 `ThreadingHTTPServer` 上的 OpenAI 兼容假上游，经公开 Registry 入口接线，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M003-畸形帧（§1.5.1 c7）
- 要测什么（责任展开）：`data: {not json}` 或坏块→502 `provider_contract_error`；不伪装成功（§1.5.1 c7）（本 Case 责任：非 SSE→502；非 JSON 帧/非 JSON 体→503（`src/` 实测）；两类均不伪装成功）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝inference 组装后畸形帧与非 SS 响应的映射与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`providers/openai.py::complete`（Content-Type 校验、JSON 解析异常归类）、`embed`（非 JSON body）

```text
create(...) / create(...embeddings)  # 上游返回非 SSE / 非 JSON 帧 / 非 JSON 体
```

- 初态构造（经公开入口）：真实 cloud provider → loopback `FakeUpstream(mode=non_sse / badframe / nonjson)`
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-3（loopback 假上游）
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：`non_sse`（`text/plain` 体）；`badframe`（`data: {not json}`）；`nonjson`（embeddings 返 `<html>`）
- 边界/非法取值及理由：非 SSE Content-Type→**502** `provider_contract_error`；非 JSON 帧/非 JSON 体→**503** `provider_unavailable`（retryable，`src/` 实测；与方案 §1.5.1 a25/b4/c7 的 502 预期存在偏差，已按 §4 `G-INF-NONJSON-MAPPING-1` 具名）；两类均不伪装成功、账本 unknown
- 规模 / 时间域（数量、分页、复杂度、观测开销）：4 次调用；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `non_sse` | 502 `provider_contract_error` |
| 2 | `badframe` | 503 `provider_unavailable`（retryable） |
| 3 | embeddings `nonjson` | 503 `provider_unavailable` |
| 4 | 畸形流后查账本 | `unknown` 且 `total_tokens=NULL`（无伪 terminal） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：方案 §1.5.1 b4/b5/c7（Oracle ＝ `src/`，偏差见 §4 `G-INF-NONJSON-MAPPING-1`）；按 `complete` 的 Content-Type 显式 raise 与 `JSONDecodeError` 归类人工推导
- 互斥预期（成功 / 各错误分支）：非 SSE→502；非 JSON→503（以实现为准，偏差已具名）；不伪装成功

## 6. 错误路径、副作用与清理

- 错误出口与表现：502 `provider_contract_error` / 503 `provider_unavailable`
- 副作用断言与清理：账本收敛 unknown

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-INF-017.py`（4 个）：`test_non_sse_content_type_is_502`、`test_non_json_data_frame_maps_503_per_src`、`test_non_json_embeddings_body_maps_503_per_src`、`test_malformed_stream_never_fakes_success`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-INF-017.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
