<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-OBS-004 — 诊断注入与观测 fail-open

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-OBS-004` |
| Document Version | `0.1.0-draft.6` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-OBS-004.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-OBS-004`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-OBS-004.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-OBS-004` / M005 注入分支：合法/非法 400/未知 deployment 404 + 观测写失败推理不变（组装） v0.1.0-draft.6 / VRC-OBS-003（observability-design §14 / observability.isd §9.1，observability 0.1.0-draft.6） / VRC-OBS-003 / recovery / P1（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：故障注入 + 异常路径回滚 + 状态迁移断言（主要手段：边界外协作者用进程内 `FakeAdapter`（`ResponsesService._test_adapter` seam，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M005-注入三分支
- 要测什么（责任展开）：合法注入命中；非法类型 400；未知 deployment 404；观测库写失败推理不变（fail-open）（本 Case 责任：注入四态（合法命中/非法 400/缺 items 400/未知 deployment 404）互斥；观测写失败推理不变）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝observability 组装后注入配置面与观测 fail-open与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`app.py`（`/v1/deployments/{id}/diagnostics` GET/PATCH）、`libdiag/injections.py`、推理路径的观测写入

```text
GET/PATCH /v1/deployments/{id}/diagnostics; POST /v1/responses
```

- 初态构造（经公开入口）：`AppFixture` 真实组装（ENV-1）+ ENV-2；注入配置经公开 PATCH；观测写失败经存储面注入
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2 + ENV-3 + ENV-4
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：合法注入（`fault_502`）；非法类型；缺 config 字段；未知 deployment（GET/PATCH 双动词）；缺 `items`；`items:[]` 撤销；DROP 诊断表后推理
- 边界/非法取值及理由：合法注入持久且推理命中（502 `provider_failure`）；非法→400 `invalid_injection`；缺 `items`→400 `invalid_request`；未知 deployment→404；`items:[]` 撤销全部；观测全失败时推理 200 且输出不变
- 规模 / 时间域（数量、分页、复杂度、观测开销）：7 个测试方法；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | PATCH 合法 `fault_502` 注入 | 200；`GET` 读回一致；推理得 502 `provider_failure`（注入命中） |
| 2 | PATCH 非法类型 | 400 `invalid_injection`（`param=type`） |
| 3 | PATCH 缺 config 字段 | 400 `invalid_injection`（`param=error_body`） |
| 4 | 未知 deployment（GET 与 PATCH） | 均 404 `not_found` |
| 5 | PATCH 无 `items` 键 | 400 `invalid_request` |
| 6 | PATCH `items:[]` | 200 且读回 0 条（撤销全部） |
| 7 | DROP 诊断表后推理 | 200，输出/usage 与基线一致（fail-open） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：observability 模块设计 §14.3 + inference 模块设计 §14.5；按注入校验与 fail-open 契约人工推导
- 互斥预期（成功 / 各错误分支）：注入四态互斥且命中可观测——`GET` 读回 `config` 逐字段一致、推理错误 message 回显注入 body、账本 `source=injected` 且 `measurement_status=unknown`；非法注入与未知 deployment 各落审计 `result=failed`；观测写失败时推理仍 200、账本 `measurement_status=measured`，诊断查询面 503 `usage_store_unavailable`

## 6. 错误路径、副作用与清理

- 错误出口与表现：400 `invalid_injection` / 400 `invalid_request` / 404 `not_found` / 注入态 502
- 副作用断言与清理：注入写入经审计（`diagnostics.injection.update`）；撤销为 DELETE

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-OBS-004.py`（7 个）：`test_legal_injection_is_persisted_and_hits_inference`、`test_unknown_injection_type_is_400_invalid_injection`、`test_missing_injection_config_field_is_400_invalid_injection`、`test_unknown_deployment_is_404_on_both_verbs`、`test_patch_without_items_is_400`、`test_empty_items_revokes_every_injection`、`test_inference_is_unchanged_when_every_observability_write_fails`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-OBS-004.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
