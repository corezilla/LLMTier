# ADM-RUNTIME-01 — 运行时快照

- **Case ID**：`ADM-RUNTIME-01`（与 §3.2 权威清单一致；本文件名 `adm-runtime-01.md`，唯一对应）。
- **标题**：`GET /v1/runtime` 返回运行时并发/队列快照：HTTP 200 + `{deployments,providers,queues}`。
- **目的（被测契约）**：验证**运行时快照读契约**。被测端点/规则：`GET /v1/runtime`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getRuntimeSnapshot`，`security=AdminBearerAuth`，响应 schema `type: object`）；[`Router.snapshot`](../../../../src/inference/routing.py) 在条件锁内读 `deployment_runtime_profiles`/`provider_usage_profiles` 并返回 `deployments{id:{running,max_concurrent}}`、`providers{id:{running,max_concurrent,min_request_interval_ms,requests_per_minute}}`、`queues{tier:len}`（只含非空队列）。设计验证项 `VRC-INF-004`；需求/机制链 `LT-FUN-005`、`LT-OPS-002`、`R-INF-03`、`CT-OPS-001`。**不证明什么**：不证明 data 角色的 403 负向（ADM-RUNTIME-02）、不证明具体并发数值（运行时动态，不设门限）、不证明队列上限/429（DP-RESP-20 的领域）。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[测试设计 §2.3](../llmtier-api-test-specification.md)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[测试设计 §4.4](../llmtier-api-test-specification.md)）；初始状态=§2.3 A 类基线（3 provider / 4 deployment / 7 fixed tier）。快照只读。
- **输入与构造**：
  ```http
  GET /v1/runtime HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：无 body、无 query；凭据固定 `admin`；不注入故障；不构造非法输入。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/runtime")`；记录 status、headers、body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 body：断言为对象且含 `deployments`、`providers`、`queues` 三键；断言 `deployments` 与 `providers` 均为对象（dict），`queues` 为对象。
  5. 抽查 `providers` 元素键集含 `{running,max_concurrent,min_request_interval_ms,requests_per_minute}`（`Router.snapshot` 契约，`routing.py:59-67`）；`deployments` 元素键集含 `{running,max_concurrent}`。
  6. （可选）抽查 `deployments` 的键 ⊆ `GET /v1/deployments` 的 id 集合（快照与注册表一致，不出现未知 deployment）。
- **重点关注步骤**：① **三键齐全**——OpenAPI 仅声明 `type: object`，但实现契约固定 `{deployments,providers,queues}`；缺键即 FAIL；② **类型正确**——`providers`/`deployments` 必须是 id→对象 的映射，不是数组；③ **不设数值门限**——`running`/`max_concurrent` 为运行时动态值，只断言存在与类型，不硬编码具体数；④ **`queues` 可空**——只含非空队列，空实例可为 `{}`，不得因空 FAIL；⑤ **纯读**——`GET` 不写库（不创建 `query_snapshots`），不改 version；⑥ **一致性**——`deployments` 键应来自 `deployment_runtime_profiles`，与注册表一致。
- **期望结果与独立 Oracle**：独立 Oracle = `Router.snapshot` 的字段契约 + `openapi` `/v1/runtime` 200。
  - HTTP：`200`；`Content-Type: application/json`。
  - body：`{"deployments":{...},"providers":{...},"queues":{...}}`；`providers` 元素含 `running`/`max_concurrent`/`min_request_interval_ms`/`requests_per_minute`；`deployments` 元素含 `running`/`max_concurrent`。
  - 无错误信封。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + 三键齐全 + `providers`/`deployments` 为 dict 且元素含规定键、`queues` 为 dict。
  - **FAIL**：status 非 200、缺键、类型错（如数组）、或出现错误信封。
  - **BLOCKED**：fixture/断言逻辑问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存原始 HTTP status/headers/body、发出命令、exit code、`elapsed`、环境快照；落位与契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。
- **清理与复位**：**无需 teardown**——纯读，不改并发/队列/配置。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`Router.snapshot`；机制 `R-INF-03`。自动化入口 [`at_adm_runtime_01.py`](../../../../tests/system/api_test_v03/at_adm_runtime_01.py)。**不依赖**其它 Case；与 ADM-RUNTIME-02（data 角色负向）互补。
