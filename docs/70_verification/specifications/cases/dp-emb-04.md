# DP-EMB-04 — unknown model

- **Case ID**：`DP-EMB-04`（与 §3.2 权威清单一致；本文件名 `dp-emb-04.md`，唯一对应）。
- **标题**：`POST /v1/embeddings` 请求未知逻辑 model：返回 `404 model_not_found`（统一错误信封），不触上游。
- **目的（被测契约）**：验证 `POST /v1/embeddings` 对**未知逻辑 model** 的拒绝语义。被测端点/规则：`model` 取一个不存在于 `service_levels` 的固定 tier id（如 `"NonExistentModel"`），端点在**准入/路由之前**以 [openapi](../../../../interfaces/openapi/llmtier.openapi.json) `ErrorEnvelope` 返回 HTTP `404` 且 `error.code=="model_not_found"`（`ERR-MODEL-NOTFOUND`，系统设计 §7.8，见[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md)）；`type=="request_error"`（status<500）、`param==null`、`retryable==false`。设计验证项 `VRC-INF-001`；需求 `LT-FUN-003`（[requirements](../../../10_requirements/llmtier-requirements.md)）；机制需求 `R-INF-04`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；契约 `CT-EMB-001`；错误映射见[测试设计 §11.1](../llmtier-api-test-specification.md)（`ERR-MODEL-NOTFOUND` → `DP-EMB-04`）。**权威码确认（关键）**：`§3.2` 与 `§11.1` 均记 `model_not_found`，与当前实现一致——[`src/inference/embeddings.py`](../../../../src/inference/embeddings.py) 第 36–39 行捕获 `registry.get_service_level()` 的 `ApiError(404,"not_found")` 并**重映射为 `ApiError(404,"model_not_found")`**；`Router.admit` 无候选时亦抛 `model_not_found`。**不证明什么**：不证明向量形状/维数（DP-EMB-01/02），不证明成功路径（DP-EMB-01），不证明其它错误码（如缺字段 400 `invalid_request` 属 DP-EMB-07 邻域），不证明 `/v1/models/{model}` 的 404（DP-MODELS-06）或 `/v1/responses` 的 404（DP-RESP-05）——虽同族但端不同。
- **前置与环境**：**环境 A**（m5air 已部署实例；角色 `data`，只读/无状态；见[§2.3](../llmtier-api-test-specification.md)）。执行前必须通过[§2.1](../llmtier-api-test-specification.md) 的 6 项就绪检查（详见 §2.1）；任一失败 → 整班 BLOCKED/SKIP。fixture（[§4.4](../llmtier-api-test-specification.md)）：`api_client`。初始状态：所选未知 id **不在** 7 个 fixed tier（`Senior/Junior/Worker/Associate/Engineer/Executor/Embedding-v1`）内。本 case 为纯负向读，无副作用。
- **输入与构造**：固定请求：

  ```http
  POST /v1/embeddings HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Content-Type: application/json
  Accept: application/json
  ```

  ```json
  {
    "model": "NonExistentModel",
    "input": "hello"
  }
  ```

  边界/构造点：`model` 为**语法合法但语义不存在**的字符串（长度 ≥1，满足 `EmbeddingRequest.model.minLength:1`），确保失败点在 model 解析而非请求形态；`input` 提供合法值，避免同时触发 400 校验而掩盖 404；不注入故障。`NonExistentModel` 字面量与 [`at_dp_emb_04.py`](../../../../tests/system/api_test_v03/at_dp_emb_04.py) 一致，随 Run manifest 固定。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（`pytest_configure` 自动执行，本 case 不重复）。
  2. （可选前置交叉核对）`GET /v1/usage` 记录当前 principal 的 usage head / 计数基线，用于事后证明**无新增账本义务**（[测试设计 §4.6](../llmtier-api-test-specification.md) "拒绝即零副作用"）。
  3. `resp = api_client.post("/v1/embeddings", json={"model": "NonExistentModel", "input": "hello"})`；记录 status、headers、body。
  4. 断言 `resp.status_code == 404`；`body` 不含成功字段（无顶层 `data`/`object`），是错误信封。
  5. 解析 `err = resp.json()["error"]`：断言键集恰为 `{message,type,code,param,retryable}`（5 键，无 `category`），`err["code"]=="model_not_found"`、`err["type"]=="request_error"`、`err["param"] is None`、`err["retryable"] is False`。
  6. （可选）重发同一请求确认可复现；并核对步骤 2 的 usage 基线未因两次拒绝而新增 dispatch。
- **重点关注步骤**：① **精确错误码 `model_not_found`**——不是通用 `not_found`。这是本 case 的核心 Oracle，且现已与源码/脚本一致：仓库源码把 `registry` 的 `not_found` 重映射为 `model_not_found`（`embeddings.py` 第 39 行），[`at_dp_emb_04.py`](../../../../tests/system/api_test_v03/at_dp_emb_04.py) 第 29 行已断言 `err.get("code") == "model_not_found"`（脚本注释说明 `EmbeddingsService.create` 在 `embeddings.py:36-39` 完成 remap），本轮以源码/`§3.2`/`§11.1` 为准；2026-09-21 旧运行报告曾记实测 `not_found`（见下），以当前源码与脚本为准。若新 Run 实测仍为 `not_found`，说明被测 m5air 部署未包含该重映射（部署漂移），按 FAIL 登记并附 `reproduction_cmd`，不得回写设计迁就脚本。② **`type` 由状态导出**——404<500 ⇒ `request_error`；不是 `server_error`。③ **信封 identity**——恰 5 键、无 `category`（[测试设计 §4.6](../llmtier-api-test-specification.md)）。④ **零副作用**——404 必须在 dispatch 之前完成：无上游调用、无账本义务；以 usage 交叉核对（[测试设计 §4.6/§8.2](../llmtier-api-test-specification.md)）。⑤ **非成功体混淆**——404 体不得含 `data`；断言前先确认是 `{"error":...}`。⑥ **`param`**——本路径 `model_not_found` 由重映射构造，`param==null`，不要臆断为 `"model"`。
- **期望结果与独立 Oracle**：独立 Oracle = [openapi](../../../../interfaces/openapi/llmtier.openapi.json) `ErrorEnvelope`/`ErrorDetail`（`code` enum 含 `model_not_found`）+ [测试设计 §3.2/§11.1](../llmtier-api-test-specification.md)（`ERR-MODEL-NOTFOUND` → 本 case）。
  - HTTP：`404`；`Content-Type: application/json`。
  - body：`{"error":{"message":<str>,"type":"request_error","code":"model_not_found","param":null,"retryable":false}}`。
  - 无成功字段（无 `object`/`data`）；无上游 dispatch、无账本新增义务（可选交叉核对）。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==404` 且 `error.code=="model_not_found"`、`type=="request_error"`、`param is None`、`retryable is False`，键集恰 5；且（若做交叉核对）无新账本义务。
  - **FAIL**：status 非 404、`code` 非 `model_not_found`（含实测 `not_found`）、`type`/`param`/`retryable` 不符、键集多/缺，或产生上游调用/账本义务。
  - **BLOCKED**：测试代码/契约本身问题（如断言不可执行、契约语义不清）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实实例，或用 B 类结果冒充 A 类——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：有实现（§3.2 `RUN`）但本轮未执行——按 §9 记 `NOT_RUN`。
- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-api-test-specification.md)：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、请求/响应、可选 usage 前后快照、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。
- **清理与复位**：**无需 teardown**——本 case 为被拒请求，无配置/资源/注入改动，无用户 usage 删除。退出前确认 `/readyz` 7 tier、无未清空注入项；若误跑于 B 类实例，按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班销毁。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client` fixture（[测试设计 §4.4](../llmtier-api-test-specification.md)）；7 个 fixed tier 清单与"未知 id 不在其中"的初态；`ErrorDetail.code` 机器契约（[openapi](../../../../interfaces/openapi/llmtier.openapi.json)）；实现 [`src/inference/embeddings.py`](../../../../src/inference/embeddings.py) 第 36–39 行与 [`src/inference/routing.py`](../../../../src/inference/routing.py) 的 `admit`；自动化入口 [`at_dp_emb_04.py`](../../../../tests/system/api_test_v03/at_dp_emb_04.py)（脚本已断言 `model_not_found`，与本设计一致）。**不依赖**其它 Case；与 DP-MODELS-06、DP-RESP-05 同属 `model_not_found` 家族但端点不同。
