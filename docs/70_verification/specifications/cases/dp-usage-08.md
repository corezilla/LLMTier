# DP-USAGE-08 — store 不可用不返回空页

- **Case ID**：`DP-USAGE-08`（与 §3.2 权威清单一致；本文件名 `dp-usage-08.md`，唯一对应；**新增 Case**）。
- **标题**：Usage store 不可用时 `GET /v1/usage` 返回 `503 usage_store_unavailable`（typed server error），**不得**以 `200 + 空 data` 冒充"无记录"；恢复存储后查询回到 200。
- **目的（被测契约）**：验证 **Usage 读取的存储不可用显式化契约**。被测端点/规则：`GET /v1/usage`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listUsage`，503 响应 `UsageStoreUnavailable`）。实现三处收敛为同一 wire 码：`src/inference/usage.py::page` 的 `except Exception → ApiError(503,"usage_store_unavailable")`、`src/http_api/app.py::_store_read` 同映射、`_run` 的 `except sqlite3.Error` 兜底到 `usage_store_unavailable`（另有 500 `internal_error` 仅用于非 sqlite 的未知异常）。因此存储层故障**必须**表现为 503 而非空 `UsagePage`。设计验证项 `VRC-MGMT-006`；机制需求 `R-MET-04`（HTTP 适配层 503 显式化 / CON-METER-005）；机制 `T-MET-PAGE`（见 [usage-metering 机制](../../../20_system_design/mechanisms/usage-metering.md) §4.7「存储不可用返回 typed 503，不用空页冒充无记录」/§7）；错误目录 `ERR-STORE` → `usage_store_unavailable`（[系统设计 §7.8](../../../20_system_design/llmtier-system-design.md)）；需求链 `LT-FUN-004`、`LT-INT-004/005/007`、`CT-STORE-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明正常查询内容（DP-USAGE-01/02/03）、过期 cursor（DP-USAGE-04）、主体隔离（DP-USAGE-06）、重放幂等（DP-USAGE-07）；不证明**启动期** schema/引导错误（`ERR-SCHEMA`/`ERR-BOOT`，见[测试设计 §2.9/§11.1](../llmtier-api-test-specification.md)）与 symlink 路径拒绝（`ERR-PATH-UNSAFE`）；不证明 `DELETE /v1/usage` 的 503 分支（由同机制的 ADM-USAGE-03 邻近，不在本 case 断言）。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 `127.0.0.1:<port>` + 临时 SQLite，同机第二个进程；见[§2.3](../llmtier-api-test-specification.md)/§2.4）。执行前满足[§2.1](../llmtier-api-test-specification.md) **附加（B 类）**：临时实例可启动且 `GET /healthz` 200；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。fixture（[§4.4](../llmtier-api-test-specification.md)）：本 case **必须使用一个专用的 `LLMTierInstance`**（session/module-scope，独立临时 SQLite 与端口），**不得**复用或就地改动 session-scope 的 `llmtier_b`（其 `_db_path` 被其它 B 类 case 共享，就地移库会污染它们）；该专用实例同样由 `_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier，并以 `dev-data` 客户端访问。**当前 `conftest.py` 尚未提供此专用 fixture**（需新增，如 `llmtier_b_usage_store`/等价），并应暴露其临时库路径的**只读访问器**（避免依赖私有 `_db_path`）；fixture 落地前本 case 为 **BLOCKED**。**TS-003**：本 case 不触上游 provider，但仍不得把 `127.0.0.1` 写进被测服务上游 endpoint（§2.7；`_baseline_settings` 已用 LAN fake provider）。**注意（隔离）**：专用实例的 SQLite 仅由本 case 操作，`finally` 仍须原子恢复并验证，但不会波及其它 B 类 case。
- **输入与构造**：
  1. 正常基线（data）：`GET /v1/usage?from=<now-30d>&to=<now>`（动态窗口，禁止硬编码）→ 期望 200 `UsagePage`，记录 `data` 长度与 `snapshot_id`。
  2. **制造存储不可用**（专用实例自有临时库，可安全操作）：把被测实例的 SQLite 三件套移开，并在原路径放置一个**目录**，使 `sqlite3.connect(<db_path>)` 失败：
     ```python
     db = inst.db_path            # 专用实例的只读访问器（非 llmtier_b._db_path）
     for suffix in ("", "-wal", "-shm"):
         src = Path(str(db) + suffix)
         if src.exists(): os.replace(src, str(src) + ".disabled")
     os.mkdir(db)          # 原路径变成目录 → 连接失败（不新建空库）
     ```
     备用触发（记录其一即可）：`os.chmod(db, 0o000)`（注意以 root 运行时无效，故以"目录占位"为主）。
  3. 同一查询重发：`GET /v1/usage?from=<w>&to=<w>`（`api_client_b`）。
  4. 恢复：删除占位目录/新文件，把 `.disabled` 原子移回原位，再发同一查询验证恢复。
  构造点：窗口由 `now()` 生成；两次查询的 `from`/`to` 完全一致；触发只针对**专用实例进程实际使用的库路径**，不 mock 任何 HTTP 行为。
- **执行过程（逐步调用）**：
  1. `GET /healthz`/`GET /readyz`（`pytest_configure` 完成，B 类附加检查同节）。
  2. `baseline = inst_client.get("/v1/usage", params={"from": w0, "to": w1})`；断言 200，记录 `baseline.json()["data"]` 长度与 `snapshot_id`。
  3. **try**：按上述构造把库移开并 `mkdir` 占位；`resp = inst_client.get("/v1/usage", params={"from": w0, "to": w1})`。
  4. 断言 `resp.status_code == 503`。
  5. `err = resp.json()["error"]`：断言 `err["code"] == "usage_store_unavailable"`、`err["type"] == "server_error"`、信封恰 5 键 `{message,type,code,param,retryable}`（`retryable` 观测并记录，openapi 未对每个 code 固定该值）。
  6. 断言响应**不是** `UsagePage`：body 顶层**无** `data`/`has_more`/`snapshot_id`，且**有** `error`；即"非空页冒充"的显式反证（避免 `200 + data:[]`）。
  7. **finally**：删除占位目录/占位空库，将 `.disabled` 文件原子移回原路径（含 `-wal`/`-shm`），随后再次 `GET` 同一查询；断言 `200` 且 `data` 长度/`snapshot_id` 与基线可复现（至少 200 且为 `UsagePage`），证明恢复。本 case 的库是**专用实例**独有，恢复失败只影响本 case，不波及其它 B 类 case。
- **重点关注步骤**：① **503 而非空页**——核心断言是 `status==503` 且 body 为 `error` 信封；若返回 `200 + {"data":[],...}` 即 FAIL（把"读不到"冒充"没有"）；② **typed 码**——必须 `usage_store_unavailable`（`ERR-STORE`），不是 `internal_error`/`not_found`；③ **触发命中真实进程**——实现每请求新建 per-thread SQLite 连接（`ThreadingHTTPServer` 每请求新线程、`_run` 末尾 `store.close()`），故"路径 → 目录"会使下一次连接失败；**若未来实现改为持久连接池，路径法可能失效**——此时本 case 判 BLOCKED 并登记（不得改判 PASS）；④ **专用实例隔离**——必须使用本 case 专属 `LLMTierInstance`（独立临时库/端口），**不得**碰 session-scope `llmtier_b` 的库；`finally` 仍须移回并二次查询 200；⑤ **不 mock**——不得 monkeypatch handler/`page` 直接抛错来伪造 503（INVALID）；触发只能发生在真实存储路径层；⑥ **信封 identity**——恰 5 键、`type` 由 503≥500 导出 `server_error`；⑦ **MISSING 语义**——无实现是缺口（NOT_RUN），不是跳过。
- **期望结果与独立 Oracle**：独立 Oracle = 机制"存储不可用 ⇒ typed 503，不用空页冒充无记录" + [`openapi` `UsageStoreUnavailable`/`ErrorEnvelope`](../../../../interfaces/openapi/llmtier.openapi.json) + `ERR-STORE`。
  - 基线：`200`，合法 `UsagePage`。
  - 存储不可用：HTTP `503`；body `{"error":{"message":<str>,"type":"server_error","code":"usage_store_unavailable","param":null,"retryable":<bool>}}`；**无** `data`/`has_more`/`snapshot_id` 顶层键。
  - 恢复：`200`，`UsagePage`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：存储不可用时 `503 + usage_store_unavailable + type=server_error` 且响应形态为错误信封（非 `UsagePage`）；`finally` 恢复后查询回到 `200`。
  - **FAIL**：返回 `200`（尤以 `data:[]` 空页冒充）、或码非 `usage_store_unavailable`、或信封不合规；或恢复后无法回到 200（残留破坏）。
  - **BLOCKED（当前判定）**：**尚未提供所需的专用 `LLMTierInstance` fixture**（需新增并暴露临时库只读访问器），或无法使真实运行进程失去存储（如改为连接池、权限/chmod 限制导致触发不生效）、或无法安全恢复 / 无法取得专用实例的临时库路径——**可重试**，须写 `required_resolution` 与 `reproduction_cmd`（[测试设计 §9](../llmtier-api-test-specification.md)）。
  - **SKIP**：B 类临时实例不可用、§2.1 附加前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：mock/替代路径伪造 503（未真正使存储不可用）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9。
- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-api-test-specification.md)：Run ID=`<date>/B-api`；保存原始 status/headers/body（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：基线查询、触发动作（移动的文件清单与 `os.mkdir` 结果、`db_path`）、故障查询的原始 status/headers/body、恢复动作与恢复后查询、动态窗口值、环境快照（`/healthz`/`/readyz`）；`target_artifact` 三 pin 中 B 类 `db_schema_version` 取临时库 `schema_meta.version`。
- **清理与复位**：**强制 teardown（`finally`）**——把 `.disabled` 文件（含 `-wal`/`-shm`）原子移回原路径、删除占位目录/占位空库，并二次查询验证 200；库属本 case **专用实例**，不得留其在存储不可用状态。专用实例整班结束由 fixture `stop()`（`terminate`→等待 5 s→`kill`）+ `rm -rf` 临时目录销毁（[§2.8](../llmtier-api-test-specification.md)/[§4.7](../llmtier-api-test-specification.md)）。无法安全恢复时保留证据并按 §9/§11 报 BLOCKED，不做无边界清理。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 附加（B 类）与 [§4.7](../llmtier-api-test-specification.md)；**本 case 专用 `LLMTierInstance` fixture**（独立临时库/端口，**当前缺失、需新增**，并暴露临时库只读访问器；**不得**复用 session-scope `llmtier_b`）（[§4.4](../llmtier-api-test-specification.md)）；机制 [`usage-metering` §4.7/§7](../../../20_system_design/mechanisms/usage-metering.md)；`UsageStoreUnavailable`/`ErrorEnvelope` 机器契约；`ERR-STORE`。自动化入口 `at_dp_usage_08.py`（**当前 `MISSING`，新增 Case**）。**不依赖**其它 Case；与 OBS-DIAG-01 的 `ERR-STORE` 503 语义相邻（同一 `_store_read` 映射），但各自独立执行；与 DP-USAGE-04（TTL 过期，非存储故障）严格区分。
