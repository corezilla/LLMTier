<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-RESP-005 — unknown model 路由失败

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-RESP-005` |
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
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-RESP-005.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。方案清单行见[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-RESP-005` / 系统设计 §8 Responses 接口（POST /v1/responses） / `VRC-INF-001/004` / `negative` / `P0`。本文件名 `st-resp-005.md`，与 Case ID 唯一对应。
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（ERR-*）
- 要测什么（责任展开）：`POST /v1/responses` 使用未知 `model`：`404 model_not_found`，无上游调用。
- 明确不测什么 / 失败含义：**不证明什么**——不证明大小写/URL 编码的模型清单语义（ST-MODEL-003/04/05）；不证明合法模型的流式成功（ST-RESP-001/03/06）；不证明 `model` 字段缺失的校验（ST-RESP-008，属 `invalid_request`）；不证明上游答案。**失败含义＝模型解析失败契约破坏**。

**目的（被测契约）**：验证 Data Plane `POST /v1/responses` 的**模型解析失败契约**：请求的 `model` 不在可见 tier 集合内时，M003 在 dispatch 前以 `404 model_not_found` 拒绝。被测端点/规则：`POST /v1/responses`；设计验证项 `VRC-INF-001/004`；错误目录 `ERR-MODEL-NOTFOUND` → wire `code=model_not_found`（系统设计 §7.8）；实现 `src/inference/responses.py`（捕获 `registry.get_service_level` 的 404 后 `raise ApiError(404, "model_not_found", "Model not found")`；`Router.admit` 在无候选时也抛 `404 model_not_found`）（[系统测试方案 §3](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明大小写/URL 编码的模型清单语义（ST-MODEL-003/04/05）；不证明合法模型的流式成功（ST-RESP-001/03/06）；不证明 `model` 字段缺失的校验（ST-RESP-008，属 `invalid_request`）；不证明上游答案。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 现有实例，角色 `data`，无状态；见[系统测试方案 §1 测试边界](../llmtier-system-test-scheme.md)）。前置 = 就绪检查（由 `conftest.py::pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP）。fixture `api_client`（Data 角色客户端）。初始状态 = 3 provider / 4 deployment / 7 fixed tier；`model="NonExistentModel"` 不属于其中任一。
- **被测入口**：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Content-Type: application/json
  ```

- **初态构造与客户端**：只读无状态；凭据固定 `data`（经 `api_client` 注入）。
- **依赖的测试资产（tests.asset-design 文档）**：本阶段 `tests.asset-design` 文档尚未建立；`api_client` 等夹具契约见方案 §4。

## 3. 输入构造

- **输入与构造**：固定请求（未知 model；其余字段合法齐备）：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Content-Type: application/json
  ```

  ```json
  {
    "model": "NonExistentModel",
    "input": [{"role": "user", "content": "hi"}],
    "stream": true,
    "store": false
  }
  ```

  构造点：`model` 语法合法（非空字符串）但不在 7 fixed tier；保持 `stream=true`/`store=false` 通过跨字段校验，使失败唯一归因于模型解析；不注入故障。
- **规模 / 时间域**：单次 POST；无分页/并发；记录 `elapsed` 供报告。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认基线（由 `pytest_configure` 自动执行）。
  2. `POST /v1/responses`（上表 body）。
  3. 断言 `resp.status_code == 404`，响应为 JSON 错误信封（非 SSE）。
  4. 解析 `resp.json()["error"]`，断言 `code=="model_not_found"`、`type=="request_error"`、`param is None`、`retryable is False`，键集恰 5 键。
  5. 交叉核对零副作用：无上游调用、无账本义务（可选 `GET /v1/usage`）。

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 确认基线（`pytest_configure` 自动执行） | 就绪检查通过 |
| 2 | `POST /v1/responses`（未知 model） | status / headers / body |
| 3 | 断言 404 且为 JSON 错误信封（非 SSE） | 响应头/体 |
| 4 | `code=="model_not_found"`、`type=="request_error"`、`param None`、`retryable False`、5 键 | 响应体 |
| 5 | 交叉核对零副作用（可选 `GET /v1/usage`） | 上游/账本 |

**重点关注步骤**：① **`model_not_found` 而非 `not_found`**——m5air 上 7 tier 由 bootstrap 建立，未知 tier 的 `get_service_level` 抛 `404 not_found` 后被 M003 统一改写为 `model_not_found`；无候选的 tier 亦走 `model_not_found`；② **拒绝在 dispatch 前**；③ **信封 identity**（5 键、无 `category`）；④ **非 SSE**。脚本 [`at_dp_resp_05.py`](../../../../tests/system/api_test_v03/at_dp_resp_05.py) 第 36 行已断言 `code=="model_not_found"`，与当前实现及方案清单一致。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `ErrorEnvelope`/`ErrorDetail` + 系统设计 §7.8 `ERR-MODEL-NOTFOUND`（不依赖实现答案）。**判据语义以设计验证项 `VRC-INF-001/004` 为唯一权威**。
  - HTTP：`404`；`Content-Type: application/json`。
  - body：`{"error":{"message":"Model not found","type":"request_error","code":"model_not_found","param":null,"retryable":false}}`；无 SSE 帧/`[DONE]`。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：status 404 + `code=model_not_found` + `type=request_error` + `param=null` + `retryable=false` + 非 SSE。
  - **FAIL**：status/code 不符（含返回 `not_found` 或 200）、信封键集错、被当 SSE 吞掉。
  - **BLOCKED**：测试代码/契约问题——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：就绪前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：以 mock/替代路径冒充真实路径——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（方案清单 `RUN`），未执行时记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：本 case 的"错误出口"即被拒绝的 404 `model_not_found`（期望路径）；若返回 `not_found` 或 200 则按 §5 判 FAIL 并保留原始错误信封与失败现场。
- **副作用断言与清理**：**无需 teardown**——环境 A 无状态，未创建/修改资源；退出前确认 `/readyz` 仍 7 tier。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-system-test-scheme.md)：保存请求 body、HTTP status/headers、原始错误信封、发出命令、exit code、环境快照；manifest 与报告落位见 §4.8/§10（本 case `environment:"a"`）；失败现场不截断。
- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`api_client`（[系统测试方案 §4 共同机制](../llmtier-system-test-scheme.md)）；自动化入口 [`at_dp_resp_05.py`](../../../../tests/system/api_test_v03/at_dp_resp_05.py)（已断言 `model_not_found`）；错误目录 `ERR-MODEL-NOTFOUND`（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md) §7.8）。**不依赖**其它 Case；与 ST-RESP-008（缺 `model`）区分：本 case 有 `model` 但未知。

> 实现状态：Implemented（`at_dp_resp_05.py` 已断言本 case 契约）；执行状态与 Verdict 只在 Run 报告。
