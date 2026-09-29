# OBS-STATS-02 — 统计缺 since/until

- **Case ID**：`OBS-STATS-02`
- **标题**：`GET /v1/diagnostics/stats` 缺少必填 `since`/`until`：HTTP 400 `invalid_request`，且不落到空窗口的 `200`。
- **目的（被测契约）**：验证 `GET /v1/diagnostics/stats` 的**必填时间窗校验**。被测端点/规则：`since`/`until` 在 openapi 中 `required:true`（[`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json) `/v1/diagnostics/stats` parameters）；handler 在读取存储前校验 `if not since or not until: raise ApiError(400, "invalid_request", "since and until are required")`（[`src/http_api/app.py`](../../../../src/http_api/app.py)）；错误信封恰 5 键（`type="request_error"`，`retryable=false`，`param=null`）；校验先于 `_store_read`，**零副作用**。设计验证项 `VRC-DIAG-002`；机制/错误 `ERR-REQ-VALIDATION` → `invalid_request`（[系统设计 §7.8](../../../20_system_design/llmtier-system-design.md)）；分页时间参数约定 `since`/`until`（[测试设计 §4.10](../llmtier-api-test-specification.md)：`/v1/diagnostics/stats` 用 `since`/`until`，缺 → 400 `invalid_request`）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明正向聚合窗口（OBS-STATS-01）、不证明 `from`/`to`（那是 `/v1/usage`、`/v1/stats` 的约定，本端点**不是** `from`/`to`）、不证明 `limit`/cursor（本端点无分页）、不证明别名等价（OBS-ALIAS-05）。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`；见[测试设计 §2.3](../llmtier-api-test-specification.md)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[测试设计 §4.4](../llmtier-api-test-specification.md)）；本 case 纯 GET、期望零写入，初态即终态。
- **输入与构造**：三种缺参构造（逐项独立发起，均无 body）：
  - 两者都缺：`GET /v1/diagnostics/stats`
  - 缺 `until`：`GET /v1/diagnostics/stats?since=2000-01-01T00:00:00Z`
  - 缺 `since`：`GET /v1/diagnostics/stats?until=2100-01-01T00:00:00Z`

  以及对照（应 200）：`GET /v1/diagnostics/stats?since=2000-01-01T00:00:00Z&until=2100-01-01T00:00:00Z`。  边界点：空串 `since=`/`until=` 在实现中因 [`parse_qs(parsed.query)`](../../../../src/http_api/app.py)（`app.py:185`）默认 `keep_blank_values=False` 而**被丢弃**，`query.get(...)` 得 `None`（等价于缺参）→ 同样 400（作为边界等价样例，机制与 `not ""` 不同）；本 case 不用 `from`/`to`（那是别的端点约定）。
- **执行过程（逐步调用）**：
  1. 对三种缺参构造逐个 `GET`，断言 `resp.status_code == 400`。
  2. 每次取 `err = resp.json()["error"]`：断言键集恰 `{message,type,code,param,retryable}`、`err["code"]=="invalid_request"`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  3. （边界）`?since=`（空值）→ 断言 400：因 `parse_qs`（`app.py:185`，`keep_blank_values` 默认 False）丢弃空白值，`since` 得 `None`（等价缺失），非"空串被 `not ""` 判真"。
  4. （对照）完整 `since`+`until` → 断言 `200` 且顶层键集 `{windows}`（证明端点本体可用，排除"端点坏"被误判为缺参拒绝）。
  5. 断言缺参 400 **不是** `200 {"windows":[]}`（不得用"空窗口"冒充参数校验）。
- **重点关注步骤**：① **必填校验先于存储读取**——缺参必须在 `_store_read` 之前 400，不得尝试读库（否则存储故障会被误报为 500/503 而非 400）。② **`since`/`until` 而非 `from`/`to`**——本端点唯一正确参数名是 `since`/`until`；用错参数名等价于缺参 → 400。③ **错误信封 identity**——恰 5 键、`type` 由 400 导出为 `request_error`、`retryable=false`。④ **不得空页冒充**——缺参返回 `200 + {"windows":[]}` 即 FAIL。⑤ **空串边界**——`since=` 之所以视为缺失，是依赖解析层 [`parse_qs(parsed.query)`](../../../../src/http_api/app.py)（`app.py:185`）默认 `keep_blank_values=False` **丢弃空白值**（`query.get("since")` 得 `None`），而非 `not ""` 为真（若改用保留空白的解析，`not ""` 同样为真，但当前实现的实际机制是丢弃；400 结论不变）；作为边界证据记录。⑥ **零副作用**——400 不写库、不新增 trace。⑦ **降级/存储**——本校验在 HTTP 层，降级实例仍应 400（与 diagnostics 降级无关）；`503 usage_store_unavailable` 仅可能出现在正相对照，判 BLOCKED/SKIP。注意：本 case 当前 `MISSING`（§3.2），无 `at_obs_stats_02.py`。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `BadRequest`（`ErrorEnvelope`）+ `/v1/diagnostics/stats` 参数 `required:true` + 测试设计 §4.10 时间参数约定。
  - 每个缺参/空参：HTTP `400`；`Content-Type: application/json`；body `{"error":{"message":"since and until are required","type":"request_error","code":"invalid_request","param":null,"retryable":false}}`（恰 5 键；openapi 未为响应声明头）。
  - 对照：完整参数 → `200` + `{windows}`。
  - **fail-open 不适用**：本校验是 HTTP 层必填，与观测子系统降级无关；若一个健康实例对缺参返回 200 空窗口 → **FAIL**。存储不可达仅影响正相对照，判 **BLOCKED/SKIP**。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：三种缺参（及空串）均 `400 + invalid_request + type=request_error + retryable=false`，且对照 200 正确；无空页冒充。
  - **FAIL**：任一缺参返回 200（含空 `windows`）或其他状态/code。
  - **BLOCKED**：测试代码/契约问题或正相对照遇存储不可达 `503 usage_store_unavailable`——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air，或未真正提交缺参却按行为判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
- **证据与 Run**：保存三种缺参请求与原始 400 信封、空串边界、正相对照 200、命令/exit code/`elapsed`、环境快照；落位与契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。
- **清理与复位**：**无需 teardown**——纯 GET，零副作用；不写库、不改开关、不注入。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[测试设计 §4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 6 项就绪检查；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`since`/`until` required 机器契约；实现 [`src/http_api/app.py`](../../../../src/http_api/app.py)（行 306–308 校验）。自动化入口 `at_obs_stats_02.py`（**当前 `MISSING`，尚未实现**）。**不依赖**其它 Case；与 OBS-STATS-01（正向窗口）互为正向/负向，各自独立执行。
