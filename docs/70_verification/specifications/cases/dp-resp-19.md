# DP-RESP-19 — 全部候选不健康

- **Case ID**：`DP-RESP-19`
- **标题**：`POST /v1/responses` 全部候选不健康：`503 model_unavailable`（`retryable=true`），无上游调用（**MISSING** 自动化）。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses` 的**路由可用性契约**：service-level 存在且有候选 deployment，但没有任何 `health=="healthy"` 候选时，`Router.admit` 在 dispatch 前拒绝。被测端点/规则：`POST /v1/responses`；设计验证项 `VRC-INF-004`；错误目录 `ERR-MODEL-UNAVAIL` → wire `code=model_unavailable`；机制 `T-QUEUE`；实现 `src/inference/routing.py`（`healthy=[c for c in candidates if c.health=="healthy"]; if not healthy: raise ApiError(503, "model_unavailable", "All configured backends are unhealthy", retryable=True)`）。**不证明什么**：不证明"无候选"（`404 model_not_found`，DP-RESP-05）；不证明准入饱和 `429`（DP-RESP-20）；不证明真实上游故障（DP-RESP-22/23）；不证明模型答案。
- **前置与环境**：**环境 B**（临时 LLMTier 实例，见[测试设计 §2.3](../llmtier-api-test-specification.md)/§2.4 B 类）。需一个**专属**实例（不与共享 `llmtier_b` 混用，避免污染其它 case 的健康状态）：以 `_baseline_settings` 变体启动，其 `prov_b.endpoint` 指向一个**语法合法但不可达的 LAN 地址**（如 `http://192.168.1.254:9/v1`；TS-003 要求上游 endpoint 为 LAN IP，见[测试设计 §2.7](../llmtier-api-test-specification.md)）。初始状态 = 1 provider / 1 deployment / 7 tier，且该 deployment 尚未被 probe 为 healthy。fixture = `LLMTierInstance`（[§4.4](../llmtier-api-test-specification.md)）。
- **输入与构造**：两步。

  构造"不健康"：先以 admin 触发探测（`endpoint` 不可达 → `unhealthy`）：

  ```http
  POST /v1/probes HTTP/1.1
  Authorization: Bearer dev-admin
  Content-Type: application/json

  {"deployment_id": "depl_b", "confirm_external_call": true}
  ```

  被测请求：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-data
  Content-Type: application/json
  ```

  ```json
  {"model": "Senior", "input": [{"role": "user", "content": "hi"}], "stream": true, "store": false}
  ```

  边界/构造点：`Senior` 的 `deployment_ids` 指向 `depl_b`，故必然路由到该唯一（不健康）候选；`POST /v1/probes` 的 body 键集必须恰为 `{deployment_id, confirm_external_call}`；探测对不可达 LAN endpoint 返回 `status=="unhealthy"` 并写库。
- **执行过程（逐步调用）**：
  1. （fixture 前置）启动专属 `LLMTierInstance`，轮询 `/healthz` 200；**不**断言 `depl_b` healthy。
  2. `POST /v1/probes`（`admin`）→ 断言 200 且 `status=="unhealthy"`（证明健康状态已被置为不健康）。
  3. `POST /v1/responses`（上表 body，`data`）→ 断言 `status_code == 503`。
  4. 解析 `error`：`code=="model_unavailable"`、`type=="server_error"`、`retryable is True`、`param is None`，键集恰 5 键。
  5. 交叉核对：无上游调用（trace/runtime 无该次 upstream_started），失败在 `admit` 内。
- **重点关注步骤**：① **区分"无候选"与"有不健康候选"**——本 case 必须让 `candidates()` 非空（deployment/provider 均 enabled）但 `health != healthy`，否则会得到 `404 model_not_found`；② **`retryable=true`**——可用性类错误；③ **拒绝在 dispatch 前**（`INV-5`）；④ **专属实例**——避免污染共享实例的健康状态；⑤ **MISSING**——§3.2 自动化入口为 `MISSING`，须先实现 `at_dp_resp_19.py` 与"不可达 LAN endpoint"fixture。
- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `ErrorEnvelope`/`ErrorDetail` + 系统设计 §7.8 `ERR-MODEL-UNAVAIL`（不依赖实现答案）。
  - 探测：`POST /v1/probes` → 200，`status="unhealthy"`。
  - 被测：HTTP `503`；`Content-Type: application/json`；`{"error":{"message":"All configured backends are unhealthy","type":"server_error","code":"model_unavailable","param":null,"retryable":true}}`；无 SSE。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：探测置 `unhealthy` 成功 + 后续 `503` + `model_unavailable` + `type=server_error` + `retryable=true` + 非 SSE。
  - **FAIL**：得到 `404 model_not_found`（候选为空，构造错）或 `200`；code/type/retryable 错。
  - **BLOCKED**：测试代码/fixture 不可实现（无法稳定构造不健康候选）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例不可用、无可用 LAN IP 构造不可达 endpoint（TS-003）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 mock/`127.0.0.1` 上游冒充真实路径，或未真正置不健康却按行为判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case **无自动化实现**（§3.2 `MISSING`）；未执行按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存探测请求/响应（`status=unhealthy`）、被测请求与原始 `503` 信封、健康状态证据、发出命令、exit code、环境快照。manifest 与报告落位见 §4.8/§10（本 case `environment:"b"`）。
- **清理与复位**：结束可由 fixture `stop()` 销毁专属实例（[测试设计 §4.7](../llmtier-api-test-specification.md)）；若复用共享实例则必须 `POST /v1/probes` 使 `depl_b` 恢复 `healthy`（或销毁实例），不得把不健康状态留给其它 case。离开前确认无残留不健康候选/临时进程。
- **依赖**：B 类 fixture `LLMTierInstance`（[§4.4](../llmtier-api-test-specification.md)）；TS-003 LAN endpoint（[§2.7](../llmtier-api-test-specification.md)）；`POST /v1/probes`（ADM-PROBE-01/02）；实现 `src/inference/routing.py`；错误目录 `ERR-MODEL-UNAVAIL`（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md) §7.8）。**自动化入口 `at_dp_resp_19.py` MISSING（§3.2）**；**不依赖**其它 Case。
