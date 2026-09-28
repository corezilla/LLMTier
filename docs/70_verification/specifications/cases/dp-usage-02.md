# DP-USAGE-02 — 请求后可见记录

- **Case ID**：`DP-USAGE-02`（与 §3.2 权威清单一致；本文件名 `dp-usage-02.md`，唯一对应）。
- **标题**：一次成功的 `POST /v1/embeddings` 之后，其 `request_id` 在同一动态窗口的 `GET /v1/usage` 中可见，记录为 head 终态（`is_final=true`）、`endpoint`/`model` 与调用一致。
- **目的（被测契约）**：验证 **Usage Recorder 终态账本契约**——调用完成后可查到该主主体的 usage fact。被测端点/规则：前置 `POST /v1/embeddings`（生成一条账本义务并 `finish` 为终态版本），随后 `GET /v1/usage`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listUsage`，支持 `request_id` 过滤）读取。实现为 `src/inference/usage.py`：dispatch 前 `authorize_dispatch` 写 `usage_obligations` v1（`unknown`），成功 `finish` 追加 v2（`measured`，head 单调推进，读取只取 head 单条、不累加）。设计验证项 `VRC-MGMT-006`；机制 `T-MET-FINAL`（见 [usage-metering 机制](../../../20_system_design/mechanisms/usage-metering.md) §4.5/§4.6 CON-METER-001..003，INV-1/2/3）；机制需求 `R-MET-01`/`R-MET-02`；需求链 `LT-FUN-004`、`LT-INT-004/005/007`、`CT-USAGE-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明 token 计量数值的准确性（上游未回 usage 时按 `unknown`+`null` 收敛，属正常；token 语义由 `T-MET-UNKNOWN` 承接，不在本 case 断言）；不证明分页（DP-USAGE-03）、过期 cursor（04）、主体隔离（06）、重放幂等（07）、store 不可用（08）；不证明答案/向量内容正确性。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，角色 `data`，一次性无状态写后立即回收；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 6 项就绪检查；任一失败 → 整班 BLOCKED/SKIP。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`api_client`（`Bearer dev-data`，principal_id=`consumer`）。**关键前置**：m5air 存在可路由的 embeddings-capable deployment（§2.1.6 的 `dep_local_bge_m3`，固定 tier `Embedding-v1`）；若该 deployment 不 healthy，`/readyz` 会暴露，按 §2.1 处理。窗口由 [`constants.recent_window()`](../../../../tests/system/api_test_v03/constants.py) 动态生成（**禁止硬编码日期**）。
- **输入与构造**：先发前置调用（固定 prompt/输入），再查询：
  ```http
  POST /v1/embeddings HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Content-Type: application/json
  ```
  ```json
  {"model": "Embedding-v1", "input": ["llmtier-usage-02-probe"], "encoding_format": "float"}
  ```
  ```http
  GET /v1/usage?from=<now-30d>&to=<now>&request_id=<rid> HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  ```
  构造点：`model="Embedding-v1"` 指 embeddings tier；输入为固定短字符串（确定性、无随机）；`request_id` 取前置响应的 `X-Request-ID` 头（服务端为**本次**请求生成的 `req_<hex>`），用 `request_id` 过滤把窗口噪声排除，使断言确定；窗口 `[from,to)` 覆盖调用时刻。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz`（由 `pytest_configure` 完成，本 case 不重复）。
  2. `emb = api_client.post("/v1/embeddings", json={...})`；断言 `emb.status_code == 200`；`rid = emb.headers["X-Request-ID"]`；断言 `rid` 非空（服务端恒发该头，见 `src/http_api/app.py` `_json`）。
  3. `since, until = recent_window()`；`resp = api_client.get("/v1/usage", params={"from": since, "to": until, "request_id": rid})`；断言 `200`。
  4. `body = resp.json()`；断言 `len(body["data"]) == 1` 且 `body["data"][0]["request_id"] == rid`。
  5. 断言该记录 `endpoint=="/v1/embeddings"`、`model=="Embedding-v1"`、`is_final is True`、`record_version >= 1`（head 终态；不是 v1 obligation）。
  6. 断言 `measurement_status ∈ {measured,estimated,unknown}` 且 `source` 与之一致（`measured⇒provider`、`estimated⇒gateway_estimate`、`unknown⇒unavailable`）；`measurement_status=="unknown"` 时 `input_tokens`/`output_tokens`/`total_tokens` 全为 `null`（**不得为 0**，INV-5）；否则为非负整数。
  7. 断言 `recorded_at`/`updated_at` 为合法 RFC3339 且 `recorded_at ∈ [since,until)`。
- **重点关注步骤**：① **`request_id` 捕获**——必须取前置响应头 `X-Request-ID`（服务端生成），不要自行编造；用 `request_id` 过滤使窗口无关噪声被排除；② **head 单条、不累加**——`data` 中同一 `request_id` 只应出现一条（head 指向的版本），实现 join `usage_heads` 而非叠加版本（INV-3）；若出现同 `request_id` 的多条即 FAIL；③ **终态而非 v1 obligation**——`is_final=true` 且 `record_version>=1`；④ **unknown ⇒ NULL 而非 0**——这是 `T-MET-UNKNOWN`/INV-5 的强断言，不许用 0 冒充未测；⑤ **不夸大计量**——不对 token 数值做业务断言（上游是否回 usage 决定 measured/unknown）；⑥ **窗口动态**——同上，禁止硬编码。注意：现有 [`at_dp_usage_02.py`](../../../../tests/system/api_test_v03/at_dp_usage_02.py) 只断言"窗口内 `data` 非空且首条含 `request_id`/`model`/`endpoint`/`recorded_at`"，**未自建前置调用、未按 `request_id` 过滤、未断言 `is_final`/head 唯一/unknown⇒null**；本设计与脚本存在覆盖缺口，脚本须补齐前置调用与上述断言后方可判本 Case PASS。
- **期望结果与独立 Oracle**：独立 Oracle = 机制 `T-MET-FINAL`（`authorize_dispatch` → `finish` 后 head 指向单一终态版本，`GET /v1/usage` 只暴露该 head）+ [`openapi` `UsageRecord`](../../../../interfaces/openapi/llmtier.openapi.json)。
  - 前置 `POST /v1/embeddings`：`200`，响应头 `X-Request-ID=rid`。
  - `GET /v1/usage?request_id=rid`：`200`，`data` 恰 1 条，`request_id==rid`、`model=="Embedding-v1"`、`endpoint=="/v1/embeddings"`、`is_final=true`、`record_version>=1`。
  - `unknown ⇒ tokens all null`；`recorded_at ∈ [from,to)`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：前置调用 `200` 且查询 `200`，且 `data` 恰 1 条满足 `request_id`/`model`/`endpoint`/`is_final`/`record_version`/`measurement_status-source-token` 一致与 `[from,to)`。
  - **FAIL**：查询 `200` 但 `data` 不含该 `request_id`、或含多条、或 `is_final` 非真、或 `endpoint`/`model` 不符、或 `unknown` 却填 0、或 `recorded_at` 越界。
  - **BLOCKED**：测试代码/契约本身问题，或 embeddings 前置无法命中（如断言不可实现）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（embeddings deployment 不可用、上游离线等）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时记 `NOT_RUN`。
- **证据与 Run**：保存前置 `POST /v1/embeddings` 的请求/响应（含 `X-Request-ID`）、随后的 `GET /v1/usage?request_id=...` 请求/响应、动态窗口实际值、发出命令、exit code、`elapsed`、环境快照。`manifest.json` 含 `target_artifact`（三 pin）与 `redactions`（`Authorization` 脱敏）。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/dp-usage-02/`，失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**A 类一次性无状态写**——前置 embeddings 调用会向账本写一条 usage fact；这是被测行为本身，**不删除用户 usage**（§2.8 明确不得删除 m5air 既有/用户 usage），故**无 teardown**。仅确认不误建 provider/deployment/service-level、不写注入项；退出前 `/readyz` 仍 7 tier。若被误跑于 B 类临时实例，则按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf`。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；embeddings-capable tier `Embedding-v1` / `dep_local_bge_m3`（§2.1.6）；`constants.recent_window()`；`UsageRecord`/`UsagePage` 机器契约；机制 [`usage-metering` §4.5/§4.6](../../../20_system_design/mechanisms/usage-metering.md)；自动化入口 [`at_dp_usage_02.py`](../../../../tests/system/api_test_v03/at_dp_usage_02.py)。**不依赖**其它 Case；与 DP-EMB-01（基本 embedding）共享同一调用形态但各自独立执行；与 DP-USAGE-03（分页）、DP-USAGE-06（隔离）语义相邻。
