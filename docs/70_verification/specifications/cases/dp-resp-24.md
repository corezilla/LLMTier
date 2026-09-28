# DP-RESP-24 — provider 凭据缺失

- **Case ID**：`DP-RESP-24`
- **标题**：`POST /v1/responses` provider `secret_ref` 不可解析：`503 provider_secret_unavailable`（**MISSING** 自动化）。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses` 的**provider 凭据可用性契约**：所选 provider 的 `secret_ref` 指向缺失/不可读的凭据时，适配层在建立上游请求前抛 `503 provider_secret_unavailable`。被测端点/规则：`POST /v1/responses`；需求 `R-INF-05`；设计验证项 `VRC-INF-001`；错误目录 `ERR-PROVIDER-SECRET` → wire `code=provider_secret_unavailable`；实现 `src/inference/providers/openai.py`（`_secret()`：`file:` 读取 `OSError` → `ApiError(503, "provider_secret_unavailable", "Provider secret file is unreadable")`；非 `env:`/`file:` → "Unsupported provider secret reference"）。**不证明什么**：不证明 `secret_ref` 格式校验的 400 `invalid_request`（`registry._validate_secret_ref`，属写侧管理契约，见 ADM-PROV-12）；不证明 401/403 上游鉴权失败；不证明上游不可达（`provider_unavailable`）；不证明答案。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 `127.0.0.1:<随机空闲端口>` + 临时 SQLite；见[测试设计 §2.3](../llmtier-api-test-specification.md) / §2.4 B 类）。建议专属实例以免改动共享 `prov_b`。`_baseline_settings`：`prov_b` + `depl_b` + 7 tier；`depl_b` 已 probe `healthy`（此时 `secret_ref=None`）。fixture `LLMTierInstance`、`admin_client_b`、`api_client_b`（[§4.4](../llmtier-api-test-specification.md)）。初始状态无注入项。
- **输入与构造**：先以 admin PATCH 把 `prov_b.secret_ref` 改为一个**语法合法但文件不存在**的 `file:` 引用（通过 `_validate_secret_ref`，但读取时失败），再发被测请求。

  改 `secret_ref`（需 `If-Match`，先 `GET /v1/providers/prov_b` 取 `ETag`）：

  ```http
  PATCH /v1/providers/prov_b HTTP/1.1
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```

  ```json
  {"secret_ref": "file:/nonexistent/llmtier-test/secret.txt"}
  ```

  > **`If-Match` 取值**：必须在发送 `PATCH` 前先 `GET /v1/providers/prov_b`，取响应头返回的**当前** `ETag`（形如 `"prov_b.v<N>"`，含双引号）作为 `If-Match` 值，**不得硬编码**；teardown 恢复时同样须重新 `GET` 取新 `ETag`（[§4.10](../llmtier-api-test-specification.md)）。

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

  边界/构造点：`file:` 前缀必须保留（否则 PATCH 先被 `_validate_secret_ref` 拒为 `400 invalid_request,param=secret_ref`，观测不到 503）；`ETag` 格式 `"<id>.v<N>"`（含双引号，[§4.10](../llmtier-api-test-specification.md)）；只改 `secret_ref` 一个字段。
- **执行过程（逐步调用）**：
  1. （fixture 前置）启动实例并 probe `depl_b` → `healthy`；确认无启用注入。
  2. `GET /v1/providers/prov_b`（`admin`）→ 记录当前 `ETag` 与原始 `secret_ref`（用于 teardown）。
  3. `PATCH /v1/providers/prov_b`（`If-Match`，body 改 `secret_ref` 为不存在的 `file:`）→ 断言 200，且响应 `has_secret` 为真（引用非空）。
  4. `POST /v1/responses`（上表 body）→ 断言响应为**普通 JSON 错误信封**（非 SSE）。
  5. 断言 `status_code == 503`；解析 `error`：`code=="provider_secret_unavailable"`、`type=="server_error"`、`retryable is False`、`param is None`，键集恰 5 键。
  6. （teardown，`finally`）`PATCH /v1/providers/prov_b` 用新 `ETag` 将 `secret_ref` 恢复为原始值 → 断言 200；`GET` 校验 `has_secret` 与原始一致。
- **重点关注步骤**：① **格式校验 vs 读取失败**——`file:` 通过写侧格式校验，失败发生在适配层读取凭据；② **拒绝位置**——在 `urlopen` 上游请求前抛错；③ **`retryable=false`**——凭据缺失不可重试（与 `provider_unavailable` 的 `true` 区分）；④ **信封 identity**（5 键、`type=server_error`）；⑤ **teardown 必恢复 `secret_ref`**，且必须重新 `GET` 取新 `ETag` 再 PATCH（412 后不覆盖，[§4.10](../llmtier-api-test-specification.md)）；⑥ **MISSING**——§3.2 自动化入口为 `MISSING`，须先实现 `at_dp_resp_24.py`。
- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `ErrorEnvelope`/`ErrorDetail` + 系统设计 §7.8 `ERR-PROVIDER-SECRET`（不依赖实现答案）。
  - PATCH：`200`，`has_secret=true`；非 `file:`/`env:` 的引用才会 400（本 case 不用）。
  - 被测：HTTP `503`；`Content-Type: application/json`；`{"error":{"message":"Provider secret file is unreadable","type":"server_error","code":"provider_secret_unavailable","param":null,"retryable":false}}`；无 SSE。
  - teardown：`secret_ref` 恢复原值；`GET` 校验。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：PATCH 200 且引用改成功；被测 `503` + `provider_secret_unavailable` + `type=server_error` + `retryable=false` + 非 SSE；teardown 恢复成功。
  - **FAIL**：status/code/retryable 错、PATCH 被拒（构造错）、teardown 未恢复。
  - **BLOCKED**：PATCH/If-Match 流程不可用、无法构造不可读 secret——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 mock/替代路径冒充真实路径、或凭据未真正缺失却按行为判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case **无自动化实现**（§3.2 `MISSING`）；未执行按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存原始/新 `secret_ref` 与 `ETag`、PATCH 请求响应、被测请求与原始 503 信封、teardown 恢复请求与 `GET` 校验、发出命令、exit code、环境快照。**脱敏**：不得记录任何真实 secret 值（[§10](../llmtier-api-test-specification.md)）。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`，含 `manifest.json`（[§4.8](../llmtier-api-test-specification.md)）；失败现场不截断。**当前无脚本/artifact**。
- **清理与复位**：**必须 teardown（`finally`）**——将 `prov_b.secret_ref` 恢复为原值（新 `ETag` + PATCH），`GET` 校验；不删除 `prov_b`/`depl_b`；无注入。专属实例由 fixture `stop()` + `rm -rf` 销毁（[测试设计 §2.8/§4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `LLMTierInstance` / `admin_client_b` / `api_client_b`（[§4.4](../llmtier-api-test-specification.md)）；`PATCH /v1/providers/{id}`（ADM-PROV-05/06，[§4.10](../llmtier-api-test-specification.md)）；实现 `src/inference/providers/openai.py`（`_secret`）、`src/management/registry.py`（`_validate_secret_ref`）；错误目录 `ERR-PROVIDER-SECRET`（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md) §7.8）。**自动化入口 `at_dp_resp_24.py` MISSING（§3.2）**；与 ADM-PROV-12（`secret_ref` 格式）区分。
