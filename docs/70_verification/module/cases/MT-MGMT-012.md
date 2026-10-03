<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-MGMT-012 — 资源启用态 × 请求准入（禁用三态）

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-MGMT-012` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-MGMT-012.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-MGMT-012`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-MGMT-012.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-MGMT-012` / M004 management §9 · 资源启用态 × 请求准入（组装） v0.1.0-draft.3 / VRC-MGMT-002 / VRC-INF-004（management-design §14 / management.isd §9.1，management 0.1.0-draft.3） / VRC-MGMT-002 / VRC-INF-004 / negative / P0（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：错误猜测 + 反例驱动（非法字段/凭据/引用/类型/顺序）+ 判定表组合（主要手段：边界外协作者用进程内 `FakeAdapter`（`ResponsesService._test_adapter` seam，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：无（层① 接口行为分母行）
- 要测什么（责任展开）：**配置变更→运行态**：禁用 provider/deployment/service_level（三态，经公开入口）后请求被拒 404 `model_not_found`（非 503/429），恢复后放行；禁用后 `/v1/models` 对应 tier `availability=unavailable`（`Registry.candidates()` 的 `enabled` 过滤 × 请求路径组装接线）（本 Case 责任：禁用 provider/deployment/service_level 后请求被拒 404 model_not_found（非 503/429），恢复后放行；禁用后模型目录 availability 联动）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝management 组装后配置禁用态到请求路径的组装接线与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/management/registry.py::candidates`（`enabled` 过滤）、`update_provider`/`update_deployment`/`update_service_level`、`src/inference/routing.py::Router.admit`、`src/inference/models.py::ModelCatalog`

```text
update_provider/deployment/service_level(..., enabled=False); create(...) -> 404 model_not_found; GET /v1/models
```

- 初态构造（经公开入口）：`AppFixture` + `seed()`（ENV-1）+ ENV-2；禁用态经公开入口 `update_*` 构造，恢复态同法
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2 + ENV-3
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：三态各一：provider `enabled=False`、deployment `enabled=False`、service_level `enabled=False`；各自恢复 `enabled=True` 作对照；`GET /v1/models`
- 边界/非法取值及理由：禁用后候选为空→404 `model_not_found`（不是 503 `model_unavailable`，后者仅有候选但全不健康）；恢复后放行；禁用后对应 tier `availability=unavailable`
- 规模 / 时间域（数量、分页、复杂度、观测开销）：3 次禁用/恢复 + 3 次请求 + 3 次目录查询；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | provider `enabled=False` → 请求 | 404 `model_not_found`；恢复后成功（因果对照） |
| 2 | deployment `enabled=False` → 请求 | 404 `model_not_found`；恢复后成功 |
| 3 | service_level `enabled=False` → 请求 | 404 `model_not_found`；恢复后成功 |
| 4 | 禁用态下 `GET /v1/models` | 对应 tier `availability=unavailable` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：management 设计 §14.2 + inference 设计 §14.4；按 `candidates()` 的 `sl.enabled=1 AND d.enabled=1 AND p.enabled=1` 过滤与 `admit` 空候选分支（404 而非 503）人工推导
- 互斥预期（成功 / 各错误分支）：三态禁用均致 404 `model_not_found`；恢复后放行；目录 availability 联动

## 6. 错误路径、副作用与清理

- 错误出口与表现：404 `model_not_found`（唯一；与全不健康的 503 区分）
- 副作用断言与清理：禁用只改 `enabled`，不改候选其它属性；恢复后行为复原

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-MGMT-012.py`（3 个）：`test_disabled_deployment_rejects_request_404_then_restores`、`test_disabled_provider_rejects_request_404_then_restores`、`test_disabled_service_level_rejects_request_404_then_restores`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-MGMT-012.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
