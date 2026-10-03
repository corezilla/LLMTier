<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-INF-020 — provider adapter 重取（endpoint/secret 变更接线）

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-INF-020` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-INF-020.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-INF-020`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-INF-020.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-INF-020` / M003 provider adapter 重取分支：endpoint/secret_ref 每请求重读（组装，ENV-3） v0.1.0-draft.1 / VRC-INF-001（inference-design §14 / inference.isd §9.1，inference 0.1.0-draft.1） / VRC-INF-001 / normal / P0（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：组装后真实调用 + 等价类划分 + 分支覆盖（主要手段：边界外协作者用 loopback `FakeUpstream`（真实 `ThreadingHTTPServer` 上的 OpenAI 兼容假上游，经公开 Registry 入口接线，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M003-provider adapter 重取（endpoint/secret 每请求重读）
- 要测什么（责任展开）：**配置变更→接线**：provider endpoint 或 secret_ref 经公开入口变更后，下一次请求使用新值（打到新上游且旧上游不再命中）；无 adapter/连接缓存跨请求复用（本 Case 责任：provider endpoint/secret_ref 变更后下一次请求打到新值（新上游命中、旧上游不再命中）；无 adapter/连接跨请求复用）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝inference 组装后配置变更到下一请求的通路接线与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/inference/responses.py::ResponsesService._adapter`（每请求重读 endpoint/secret_ref）、`src/inference/embeddings.py::EmbeddingsService._adapter`、`src/management/registry.py::update_provider`

```text
update_provider(rid, {"endpoint": new}, etag); create(...) -> hits(new_upstream)
```

- 初态构造（经公开入口）：`AppFixture` + ENV-1；两个 loopback `FakeUpstream`（A/B，各自 `hits()` 计数）；provider 经公开入口接线，endpoint 变更经 `update_provider`
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-3（两个 loopback 假上游）
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：endpoint A→B 变更后请求；secret_ref 变更后请求（观察上游收到的 Authorization）
- 边界/非法取值及理由：变更后新请求打到 B（B.hits 增、A.hits 不增）；secret 变更后新请求使用新 secret（旧值不再发送）
- 规模 / 时间域（数量、分页、复杂度、观测开销）：3 次请求；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | endpoint=A 请求 | A 命中 +1 |
| 2 | `update_provider(endpoint=B)` 后请求 | B 命中 +1、A 不再增加（无缓存旧值） |
| 3 | 变更 secret_ref 后请求 | 上游收到新 secret（每请求重读） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：inference 设计 §14.3 + M003 适配器契约；按 `_adapter` 每请求从 store 读 endpoint/secret 并新建实例人工推导
- 互斥预期（成功 / 各错误分支）：配置变更对下一请求即时生效；无 adapter/连接复用旧值

## 6. 错误路径、副作用与清理

- 错误出口与表现：无（接线正常路径）
- 副作用断言与清理：不缓存 adapter；每次请求新建 provider 实例

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-INF-020.py`（2 个）：`test_endpoint_change_routes_next_request_to_new_upstream`、`test_secret_change_is_reread_per_request`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-INF-020.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
