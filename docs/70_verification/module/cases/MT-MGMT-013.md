<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-MGMT-013 — provider 模型目录组装链

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-MGMT-013` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-MGMT-013.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-MGMT-013`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-MGMT-013.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-MGMT-013` / M004 management §9 · provider 模型目录（组装） v0.1.0-draft.3 / VRC-MGMT-002 / VRC-MGMT-005（management-design §14 / management.isd §9.1，management 0.1.0-draft.3） / VRC-MGMT-002 / VRC-MGMT-005 / negative / P1（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：错误猜测 + 反例驱动（非法字段/凭据/引用/类型/顺序）+ 判定表组合（主要手段：边界外协作者用 loopback `FakeUpstream`（真实 `ThreadingHTTPServer` 上的 OpenAI 兼容假上游，经公开 Registry 入口接线，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：无（层① 接口行为分母行）
- 要测什么（责任展开）：组装后 `/v1/providers/{id}/models`：上游目录 `data` 逐项过滤（非 dict / 缺 id / id 非 str 剔除）、坏元素不致命（不得 500）、上游 5xx→503 `provider_unavailable`、未知 provider→404（本 Case 责任：`/v1/providers/{id}/models` 组装链：目录逐项过滤（非 dict/缺 id/id 非 str 剔除，不得 500）、上游 5xx→503、未知 provider→404）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝management 组装后provider 模型目录的路由→服务→适配链与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/http_api/app.py` 路由（`/v1/providers/{id}/models`）、`src/management/admin.py::list_provider_models`、`src/inference/providers/openai.py::list_models`

```text
GET /v1/providers/{id}/models -> {"data": [id, ...]}
```

- 初态构造（经公开入口）：`AppFixture` + `seed()`（ENV-1）+ ENV-2；provider endpoint 指向 loopback `FakeUpstream`（可配置 `/models` 返回）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2 + ENV-3（loopback 假上游 `/models`）
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：合法目录；`data` 含缺 id / id 非 str 的 dict（应被过滤）；`data` 含非 dict 元素（应被过滤，不得 500）；上游 503；未知 provider
- 边界/非法取值及理由：合法→id 列表；坏 dict 元素过滤、非 dict 元素过滤（不 500）；上游 5xx→503 `provider_unavailable`；未知→404
- 规模 / 时间域（数量、分页、复杂度、观测开销）：5 请求；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 合法目录 | 200，`data` 为 id 列表 |
| 2 | `data` 含缺 id/id 非 str 的 dict | 仅保留合法 id |
| 3 | `data` 含非 dict 元素（字符串/数字） | 该元素被过滤，返回 200 而非 500（E-PROVIDER-CATALOG） |
| 4 | 上游 503 | 503 `provider_unavailable`（retryable） |
| 5 | 未知 provider | 404 `not_found` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：management 设计 §14.5 + M003 适配器契约；按 `list_models` 的逐项过滤与 HTTPError 映射人工推导（非 dict 过滤为 `0.1.0-draft.11` 修复的健壮性行为）
- 互斥预期（成功 / 各错误分支）：目录过滤到位、坏元素不致命；上游 5xx/未知 provider 码精确

## 6. 错误路径、副作用与清理

- 错误出口与表现：503 `provider_unavailable` / 404 `not_found`
- 副作用断言与清理：查询不改库；上游 5xx 不落业务副作用

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-MGMT-013.py`（5 个）：`test_valid_catalog_returns_id_list`、`test_bad_entries_are_filtered_to_valid_ids`、`test_non_object_entry_is_filtered_not_500`、`test_upstream_5xx_is_503_provider_unavailable`、`test_unknown_provider_is_404`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-MGMT-013.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
