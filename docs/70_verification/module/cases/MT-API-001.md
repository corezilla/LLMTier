<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-API-001 — 组装后路由分发、统一错误信封与健康就绪

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-API-001` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-API-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-API-001`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-API-001.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-API-001` / M001 http-api §9 · `Handler._dispatch` 路由分发（组装） v0.1.0-draft.2 / VRC-API-001（http-api-design §14 / http-api.isd §9.1，http-api 0.1.0-draft.2） / VRC-API-001 / normal / P0（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：组装后真实调用 + 等价类划分 + 分支覆盖（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：无（层① 接口行为分母行）
- 要测什么（责任展开）：组装后路由分发端到端：请求经 handler 栈命中端点、统一错误信封（`X-Request-ID`、`error.type`）与健康/就绪视图一致（本 Case 责任：真实 handler 栈（鉴权→路由→服务→存储）命中端点；错误信封键集与请求 ID 全链路一致；健康/就绪视图正确）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝http-api 组装后路由分发与统一信封/就绪语义与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/http_api/app.py::handler_factory`（`Handler._dispatch`/`_json`）、`health.py`、`errors.py`、`inference/models.py::ModelCatalog`

```text
GET /healthz, GET /readyz, GET /v1/models, POST /v1/responses -> (status, body, headers)
```

- 初态构造（经公开入口）：`AppFixture` + `seed()`（真实 `Store`/`Registry`/`Router`/`UsageRecorder`/`DiagnosticsService`），ENV-2 loopback `ThreadingHTTPServer(127.0.0.1:0)`
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 组装隔离库 + ENV-2 loopback 组装 HTTP 实例
- 依赖的测试资产（tests.asset-design 文档）：无（全部真实实现；不经替身）

## 3. 输入构造

- 逐参数输入构造：`/healthz`、`/readyz`、播种后 `/v1/models`、`POST /v1/responses`（缺 `input`）
- 边界/非法取值及理由：只播种 1 个 tier 时 `/readyz` 为 `degraded`/503（其余 tier `unavailable`）；错误信封键集固定 5 键
- 规模 / 时间域（数量、分页、复杂度、观测开销）：4 请求；每请求新线程 + 线程本地连接；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /healthz` | 200 `{status:ok, version}` |
| 2 | `GET /readyz`（仅 Worker 有候选） | 503 `degraded`；Worker `available`、其余 `unavailable` |
| 3 | `GET /v1/models` | 200，Worker 在列表中且 `availability=available`（路由→服务→存储贯通） |
| 4 | `POST /v1/responses` 缺 `input` | 400；信封键集 `{message,type,code,param,retryable}`，`type=request_error`；响应带 `X-Request-ID` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：http-api 模块设计 §14.1/§14.6 + 错误信封契约；按 `health_view`/`readiness_view`/`ApiError.envelope` 人工推导
- 互斥预期（成功 / 各错误分支）：健康 200；就绪语义（degraded/503）正确；模型目录反映播种事实；错误信封与请求 ID 全链路一致

## 6. 错误路径、副作用与清理

- 错误出口与表现：ApiError→既定码（本 Case 取 400 `invalid_request`）；未知异常→500 归 MT-API-005
- 副作用断言与清理：每请求线程本地连接被 finally 关闭；账本未被非法请求写入（校验先于 `authorize_dispatch`）

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-API-001.py`（4 个）：`test_healthz_view`、`test_readyz_after_seed_maps_degraded`、`test_models_route_hits_service_and_store`、`test_error_envelope_is_uniform`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-API-001.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
