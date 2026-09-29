# ADM-PROBE-02 — 探测带确认

- **Case ID**：`ADM-PROBE-02`（与 §3.2 权威清单一致；本文件名 `adm-probe-02.md`，唯一对应）。
- **标题**：`POST /v1/probes` 带 `confirm_external_call=true`：HTTP 200 + `ProbeResult`（`deployment_id`/`status`/`checked_at`/`may_have_incurred_cost`）。
- **目的（被测契约）**：验证**已确认探测**的成功契约与 health 落地。被测端点/规则：`POST /v1/probes`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `probeDeployment`，body `ProbeRequest`，`security=AdminBearerAuth`）；[`AdminService.probe`](../../../../src/management/admin.py) 通过确认门后 `get_deployment`→`get_provider`→构造 `LocalProvider`/`OpenAIProvider`→`adapter.probe()`→`apply_probe_result(...)`（写 `deployments.health` 与 `probe_results`）→`audit.record("deployment.probe")`→返回 `{deployment_id,status,checked_at,may_have_incurred_cost}`。设计验证项 `VRC-DIAG-004`；需求/机制链 `LT-FUN-005`、`LT-OPS-002`、`R-OBS-01`、`CT-ADMIN-001`、`CT-OPS-001`。**不证明什么**：不证明缺确认的 400（ADM-PROBE-01）、不证明未知 deployment 的 404（ADM-PROBE-03）、不证明 provider 目录（ADM-PROV-MODELS-*）、不发布上游时延 SLO（本 case 只记录 `elapsed`）。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[测试设计 §2.3](../llmtier-api-test-specification.md)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[测试设计 §4.4](../llmtier-api-test-specification.md)）；初始状态=`dep_local_gemma`（local provider）`health` 为 `healthy`（ready 基线）。本 case **会调上游探测**（[测试设计 §11](../llmtier-api-test-specification.md)：探测/费用须显式确认，执行者需授权）。
- **输入与构造**：
  ```http
  POST /v1/probes HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```
  ```json
  {"deployment_id": "dep_local_gemma", "confirm_external_call": true}
  ```
  构造点：body 键集**恰为** `{deployment_id, confirm_external_call}`（`admin.probe` 要求精确相等，多/少键→400）；`confirm_external_call is true`；选 local deployment `dep_local_gemma`（TS-003：其 provider endpoint 为 LAN/本机 local adapter，不引入 `127.0.0.1` 上游）。不注入故障。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. （前置快照）`GET /v1/deployments/dep_local_gemma`；记 `health_before`、`version_before`。
  3. `resp = admin_client.post("/v1/probes", json={"deployment_id":"dep_local_gemma","confirm_external_call":True})`。
  4. 断言 `resp.status_code == 200`；`body = resp.json()`：断言键集**恰为** `{deployment_id,status,checked_at,may_have_incurred_cost}`（`ProbeResult.additionalProperties:false`）；`deployment_id=="dep_local_gemma"`、`status in {"healthy","degraded","unhealthy"}`、`checked_at` 为 RFC3339 字符串、`may_have_incurred_cost` 为 bool。
  5. （health 落地核验）`GET /v1/deployments/dep_local_gemma` 断言 `health == body["status"]`（`apply_probe_result` 已写入）。
  6. （可选）`GET /v1/audit?limit=5` 断言出现 `action=="deployment.probe"`、`target=="dep_local_gemma"`、`result=="success"` 的审计行。
- **重点关注步骤**：① **精确键集**——`admin.probe` 要求 `set(body)=={deployment_id,confirm_external_call}`；多余键（如加 `"foo"`）须 400 `confirmation_required`，不得误当成功；② **真实上游调用与命中**——本 case 是真探测（非注入），`status` 来自 `adapter.probe()`，不能以 mock 替代；③ **health 落地**——响应 `status` 必须等于 `GET deployment` 的 `health`（证明探测结果写库），这是与"仅返回 status"的关键区别；④ **副作用范围**——探测写 `deployments.health` 与 `probe_results`（按 deployment upsert）、写审计与 operational log；**不改 `version`**（`apply_probe_result` 不更新 version）；⑤ **`may_have_incurred_cost`**——OpenAPI 仅为 bool；当前实现硬编码 `False`（即使真实探测可能计费），断言 bool 存在，**不断言其业务真值**，并在报告中记录该实现事实；⑥ **teardown 自恢复性**——探测是幂等观测，重跑得同一 health，无需资源删除。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ProbeResult` + 确认规则 + health 落地一致性。
  - HTTP：`200`；body 键集恰 `{deployment_id,status,checked_at,may_have_incurred_cost}`。
  - 一致性：`GET deployment.health == body.status`。
  - 审计：出现 `deployment.probe` success 行（可选交叉核对）。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + `ProbeResult` 键集/类型正确 + `deployment_id` 匹配 + `status∈{healthy,degraded,unhealthy}` + `GET deployment.health` 与之一致。
  - **FAIL**：status 非 200、键集不符、`status` 非法、或 health 与响应不一致。
  - **BLOCKED**：上游不可达导致 `adapter.probe()` 抛错且无法判定（若属 §2.1 就绪则 SKIP）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（OMLX 离线、m5air 不可达）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实探测，或未真正调用上游却按行为判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存POST 请求与原始 200 响应（脱敏后）、探测前后 `GET deployment`（`health`/`version`）、审计交叉核对、发出命令、exit code、`elapsed`、环境快照；落位与契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。
- **清理与复位**：**观测型，无破坏性 teardown**——本 case 不创建/删除 provider/deployment/service-level；探测把 `dep_local_gemma.health` 置为其真实状态、写一条 `probe_results`（按 deployment upsert，无累积）与审计/日志（append-only）。退出前确认 `GET /v1/deployments/dep_local_gemma.health` 与初态一致、`/readyz` 仍 7 tier。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`ProbeRequest`/`ProbeResult` 机器契约；`AdminService.probe`/`apply_probe_result`；`dep_local_gemma` + 其 local provider；机制 `T-OBS`/`R-OBS-01`。自动化入口 [`at_adm_probe_02.py`](../../../../tests/system/api_test_v03/at_adm_probe_02.py)。**不依赖**其它 Case；与 ADM-PROBE-01/03 互补但各自独立执行。
