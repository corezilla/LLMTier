<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-API-010 — 静态资源目录穿越与 readyz 映射

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-API-010` |
| Document Version | `0.1.0-draft.4` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.unit-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/unit/cases/UT-API-010.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-API-010`）；责任摘要、分类与优先级以 [单元测试方案 §6](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [http-api](../../../40_module_design/http-api-design.md) §14 / ISD [http-api.isd.md](../../../50_implementation_design/http-api.isd.md) §9.1，设计验证项 `VRC-API-004`（固定版本 `http-api 0.1.0-draft.2`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `http_api`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-API-010` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-API-010` / M001 http-api §14.1 · `Handler._static` v0.1.0-draft.2 / `VRC-API-004` / security / P1（[方案清单 §6](../llmtier-unit-test-scheme.md)）。
- **测试方法（§2.1 方法表行）**：鉴权/脱敏/注入边界冒烟（目录穿越/静态/readyz）（主要手段：直接调用 + 冻结向量 + 替身注入）
- 要测什么（责任展开）：被测：`Handler._static` 对 `../` 目录穿越 → 404；`/ui/` 命中 `index.html`；`/readyz` 空库 not_ready → 503。
- 明确不测什么 / 失败含义：不测：mime/`Cache-Control` exact 字节（方案 §7 Tailored-N/A，归系统/契约层）。失败含义＝静态交付安全或就绪映射实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/http_api/app.py::Handler._static` 与 `_dispatch` 中 `/readyz` 分支；`src/http_api/health.py::readiness_view`

```text
Handler._static(path: str) -> None; readiness_view(registry) -> (dict, int)
```

- 初态构造（经公开入口）：`AppFixture`（空库未 seed 与已 seed 两态）+ loopback 实例（ENV-2）
- Fixture / 向量及版本：`tests/common/fakes.py::AppFixture`（ENV-1）+ `UT-API-010.py::StaticAndReadinessTests`/`ReadinessStatusTests`（ENV-2）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-2 loopback 测试 HTTP 实例
- 依赖的测试资产（tests.asset-design 文档）：无（真实静态产物）

## 3. 输入构造

- 逐参数输入构造：`GET /ui/../app.py`（穿越）；`GET /ui/`；空库 `GET /readyz`
- 边界/非法取值及理由：穿越拒绝 404 / 正常命中 200；空库 not_ready 503
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单请求，O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /ui/../app.py` | 404 + `error.code=not_found` |
| 2 | `GET /ui/` | 200 命中 `index.html` |
| 3 | 空库 `GET /readyz` | 503 + `status=not_ready` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`IF-API-STATIC`/`IF-API-HEALTH` 规则 + 人工推导；不调用被测复算。**判据语义以设计验证项 `VRC-API-004` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：穿越 404；`/ui/` 200 index；空库 readyz 503 not_ready；互斥。存在候选但全不健康时就绪视图为 `degraded`（与空库 `not_ready` 区分）

## 6. 错误路径、副作用与清理

- 错误出口与表现：404 穿越；503 未就绪；无第三态
- 副作用断言与清理：无写库；loopback 实例清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/cases/UT-API-010.py::StaticAndReadinessTests::test_directory_traversal_is_404` / `test_ui_root_serves_index` / `test_readyz_seeded_is_degraded_503` / `ReadinessStatusTests::test_empty_is_not_ready_503`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/cases/UT-API-010.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/cases/UT-API-010.py`）；执行状态与 Verdict 见 Run 报告 `run-20261001-04`。
