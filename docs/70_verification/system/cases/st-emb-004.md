<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-emb-004 — unknown model

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-emb-004` |
| Document Version | `0.1.0-draft.3` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-10-01` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/st-emb-004.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-emb-004`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Embeddings 接口（parent `llmtier-system-design`），设计验证项 `VRC-INF-001`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-emb-004` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-emb-004` / 系统设计 §8 Embeddings 接口 / `VRC-INF-001` / negative / P0（[方案清单 `ST-emb-004`](../llmtier-system-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（ERR-MODEL）
- 要测什么（责任展开）：`POST /v1/embeddings` 请求未知逻辑 model：返回 `404 model_not_found`（统一错误信封），不触上游。端点在**准入/路由之前**以 OpenAPI `ErrorEnvelope` 返回 HTTP `404` 且 `error.code=="model_not_found"`（`ERR-MODEL-NOTFOUND`，系统设计 §7.8）；`type=="request_error"`（status<500）、`param==null`、`retryable==false`。需求 `LT-FUN-003`；机制需求 `R-INF-04`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；契约 `CT-EMB-001`。**权威码确认**：`src/inference/embeddings.py` 第 36–39 行捕获 `registry.get_service_level()` 的 `ApiError(404,"not_found")` 并**重映射为 `ApiError(404,"model_not_found")`**；`Router.admit` 无候选时亦抛 `model_not_found`。
- 明确不测什么 / 失败含义：不测向量形状/维数（ST-emb-001/02）；不测成功路径（ST-emb-001）；不测其它错误码（缺字段 400 `invalid_request` 属 ST-emb-007 邻域）；不测 `/v1/models/{model}` 的 404（ST-model-006）或 `/v1/responses` 的 404（ST-resp-005）。失败含义＝未知 model 拒绝语义/错误码破坏。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `POST /v1/embeddings`；角色 `data`，只读/无状态。

```text
POST /v1/embeddings
Authorization: Bearer dev-data
Content-Type: application/json
Accept: application/json
```

- 初态构造（经公开入口）：**环境 A**（m5air 已部署实例，只读/无状态）。所选未知 id **不在** 7 个 fixed tier（`Senior/Junior/Worker/Associate/Engineer/Executor/Embedding-v1`）内。本 case 为纯负向读，无副作用。
- Fixture / 向量及版本：固定请求 body（`model="NonExistentModel"`），字面量与 [`at_dp_emb_04.py`](../../../../tests/system/api_test_v03/at_dp_emb_04.py) 一致，随 Run manifest 固定。
- 依赖的测试资产（tests.asset-design 文档）：`api_client`；`conftest.py::pytest_configure` 就绪检查。

## 3. 输入构造

- 逐参数输入构造：固定请求：

```json
{
  "model": "NonExistentModel",
  "input": "hello"
}
```

- 边界/非法取值及理由：`model` 为**语法合法但语义不存在**的字符串（长度 ≥1，满足 `EmbeddingRequest.model.minLength:1`），确保失败点在 model 解析而非请求形态；`input` 提供合法值，避免同时触发 400 校验而掩盖 404；不注入故障。
- 规模 / 时间域：单次请求；在准入/路由前拒绝。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /healthz`、`GET /readyz`（`pytest_configure` 自动执行） | §2.1 基线 |
| 2 | （可选）`GET /v1/usage` 记录 usage 基线 | 用于事后证明无新增账本义务 |
| 3 | `resp = api_client.post("/v1/embeddings", json={"model": "NonExistentModel", "input": "hello"})` | status / headers / body |
| 4 | 断言 `resp.status_code == 404` | `body` 不含成功字段（无顶层 `data`/`object`），是错误信封 |
| 5 | 解析 `err = resp.json()["error"]` | 键集恰为 `{message,type,code,param,retryable}`（5 键，无 `category`），`code=="model_not_found"`、`type=="request_error"`、`param is None`、`retryable is False` |
| 6 | （可选）重发同一请求确认可复现；核对 usage 基线未新增 dispatch | 零副作用交叉核对 |

- 重点关注步骤：① **精确错误码 `model_not_found`**——不是通用 `not_found`（源码 `embeddings.py` 第 39 行 remap）；② **`type` 由状态导出**——404<500 ⇒ `request_error`；③ **信封 identity**——恰 5 键、无 `category`；④ **零副作用**——404 在 dispatch 之前完成：无上游调用、无账本义务；⑤ **非成功体混淆**——404 体不得含 `data`；⑥ **`param`**——本路径 `param==null`，不要臆断为 `"model"`。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：OpenAPI `ErrorEnvelope`/`ErrorDetail`（`code` enum 含 `model_not_found`）+ 方案错误映射（`ERR-MODEL-NOTFOUND` → 本 case）。**判据语义以设计验证项 `VRC-INF-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：HTTP `404`；`Content-Type: application/json`；`{"error":{"message":<str>,"type":"request_error","code":"model_not_found","param":null,"retryable":false}}`；无成功字段（无 `object`/`data`）；无上游 dispatch、无账本新增义务（可选交叉核对）。

## 6. 错误路径、副作用与清理

- 错误出口与表现：未知 model → `404 model_not_found`（`type=request_error`），若实测仍为 `not_found` 说明部署未含重映射（部署漂移），按 FAIL 登记并附 `reproduction_cmd`，不得回写设计迁就脚本。
- 副作用断言与清理：**无需 teardown**——被拒请求，无配置/资源/注入改动，无用户 usage 删除。退出前确认 `/readyz` 7 tier、无未清空注入项；若误跑于 B 类实例，按计划整班销毁。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：[`tests/system/api_test_v03/at_dp_emb_04.py`](../../../../tests/system/api_test_v03/at_dp_emb_04.py)（脚本已断言 `model_not_found`）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_emb_04.py -q`。
- 实现状态：Implemented；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：`status==404` 且 `error.code=="model_not_found"`、`type=="request_error"`、`param is None`、`retryable is False`，键集恰 5；且（若做交叉核对）无新账本义务。
- FAIL：status 非 404、`code` 非 `model_not_found`（含实测 `not_found`）、`type`/`param`/`retryable` 不符、键集多/缺，或产生上游调用/账本义务。
- BLOCKED：测试代码/契约本身问题。
- SKIP：就绪检查不满足。
- INVALID：用 `127.0.0.1`/mock/替代路径冒充真实实例，或用 B 类结果冒充 A 类。
- NOT_RUN：有实现但本轮未执行。

**证据与 Run**：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、请求/响应、可选 usage 前后快照、发出命令、exit code、`elapsed`、环境快照（本 case `environment:"a"`）。

**依赖**：就绪检查；`api_client`；7 个 fixed tier 清单与"未知 id 不在其中"的初态；`ErrorDetail.code` 机器契约；实现 `src/inference/embeddings.py` 第 36–39 行与 `src/inference/routing.py` 的 `admit`；自动化入口 `at_dp_emb_04.py`。**不依赖**其它 Case；与 ST-model-006、ST-resp-005 同属 `model_not_found` 家族但端点不同。
