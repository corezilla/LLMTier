# DP-USAGE-04 — 过期 cursor

- **Case ID**：`DP-USAGE-04`（与 §3.2 权威清单一致；本文件名 `dp-usage-04.md`，唯一对应）。
- **标题**：**真实过期**的 usage cursor → `400 cursor_expired`：先查首屏取 `snapshot_id`，经 `ssh m5air sqlite3` 把该行 `query_snapshots.expires_at` 改到过去后重放同一 cursor，`finally` 复位原值。
- **目的（被测契约）**：验证 **Usage cursor 的 TTL 过期拒绝契约**。被测端点/规则：`GET /v1/usage`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listUsage`，`cursor` 可选；过期/非法/不匹配 cursor 的 wire 码见错误目录 `ERR-CURSOR` → `cursor_expired`）。实现 `src/inference/usage.py::UsageRecorder._page`：`snapshot is None or expires_at <= now` → `ApiError(400,"cursor_expired",...)`，且该检查在 `filter_digest`/`authorization_digest` 复核**之前**。设计验证项 `VRC-MGMT-006`；机制需求 `R-MET-02`；机制 `T-MET-PAGE`（见 [usage-metering 机制](../../../20_system_design/mechanisms/usage-metering.md) §4.7「TTL 10 分钟」/CON-METER-004）；需求链 `LT-FUN-004`、`LT-OPS-005`、`CT-USAGE-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明 cursor 属于他人或 filter 不匹配时的 403/400（`authorization_digest`/`filter_digest` 分支，属 DP-USAGE-06/07）、不证明分页内容（DP-USAGE-03）、不证明重放幂等（DP-USAGE-07）、不证明 store 不可用（DP-USAGE-08）；**不**用字面量 `cursor="expired"` 之类的伪触发（那会命中"snapshot 不存在"分支而非真实 TTL 分支）。
- **前置与环境**：**环境 A**（m5air 已部署实例；角色 `data`；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 6 项就绪检查；任一失败 → 整班 BLOCKED/SKIP。**关键额外权限**：[测试设计 §2.8](../llmtier-api-test-specification.md) 明确允许 DP-USAGE-04 直接读取/改写 m5air `state.sqlite3` 的 `query_snapshots.expires_at`（执行前记录原值，执行后复位）——需要 `ssh m5air` 免交互（BatchMode）与非交互 `sqlite3`。DB 路径与 SSH 主机可由环境变量覆盖（现有脚本 [`at_dp_usage_04.py`](../../../../tests/system/api_test_v03/at_dp_usage_04.py) 用 `LLMTIER_M5AIR_SSH` 默认 `m5air`、`LLMTIER_M5AIR_DB` 默认 `/Users/mlp/LLMTier-dev/state.sqlite3`）。fixture：`api_client`（`Bearer dev-data`，principal_id=`consumer`）。窗口由 `constants.recent_window()` **动态**生成（禁止硬编码日期）。
- **输入与构造**：两步（生成快照 → 过期后续页）：
  ```http
  GET /v1/usage?from=<now-30d>&to=<now> HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  ```
  ```bash
  ssh -o BatchMode=yes m5air "sqlite3 /Users/mlp/LLMTier-dev/state.sqlite3 \
    \"SELECT expires_at FROM query_snapshots WHERE snapshot_id='<sid>';\""
  ssh -o BatchMode=yes m5air "sqlite3 /Users/mlp/LLMTier-dev/state.sqlite3 \
    \"UPDATE query_snapshots SET expires_at='2000-01-01T00:00:00.000Z' WHERE snapshot_id='<sid>';\""
  ```
  ```http
  GET /v1/usage?from=<now-30d>&to=<now>&cursor=<sid>:0 HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  ```
  构造点：`<sid>` 取自首屏响应的 `snapshot_id`；cursor 用 `<sid>:0`（或原样 `next_cursor`）；改写的行必须**确实存在**（先 `SELECT` 校验非空）；`from`/`to` 与首屏保持逐字节相同（虽然过期检查先于 filter 校验，保持一致以排除歧义）；改写的过期值用明确的过去时间且格式与库内一致（`...Z`，含毫秒）。
- **执行过程（逐步调用）**：
  1. `GET /healthz`/`GET /readyz`（`pytest_configure` 完成，不重复）。
  2. 首屏 `GET /v1/usage?from&to`；断言 200 且 `snapshot_id` 非空，记为 `sid`。
  3. 探测 SSH/sqlite3 可用：`_ssh_sqlite("SELECT 1;")`；不可用 → **BLOCKED**（判 BLOCKED 而非 SKIP；见判定，不得退回用伪 cursor）。
  4. `original = _ssh_sqlite("SELECT expires_at FROM query_snapshots WHERE snapshot_id='<sid>';")`；断言非空（快照确在服务端库内）。
  5. **try**：`UPDATE query_snapshots SET expires_at='2000-01-01T00:00:00.000Z' WHERE snapshot_id='<sid>'`；重放 `GET /v1/usage?...&cursor=<sid>:0`；断言 `status_code == 400`；`err = resp.json()["error"]`：`err["code"]=="cursor_expired"`、`err["type"]=="request_error"`、信封恰 5 键。
  6. **finally**：`UPDATE query_snapshots SET expires_at='<original>' WHERE snapshot_id='<sid>'`（恢复**原值**，含原始毫秒/时区文本）；随后 `SELECT` 回读并断言与 `original` 逐字节相等，证明复位成功。
- **重点关注步骤**：① **真实 TTL 分支**——必须走"快照存在但 `expires_at` 已过"的分支，不得用不存在的 `snapshot_id`/字面量 "expired"（那会命中"snapshot is None"同一 400 码但**不是** TTL 语义）；② **改写命中确认**——UPDATE 后应 `SELECT` 回读确认值为过去（或至少确认 UPDATE 的 `changes()`/rowcount），证明改写生效；③ **复位完整性**——`finally` 必须恢复**原字符串**（不要用 `now()+10min` 重算），并回读校验；复位失败须保留证据并按 §9 报 BLOCKED，**不得**把 m5air 快照留在过期状态；④ **principal/filter 一致**——用同一 `api_client`（consumer）与同一 `from`/`to`，避免把 403/400 混入；⑤ **无 SSH/DB 权限**——按本设计判 **BLOCKED**（可重试，需补 `ssh`/`sqlite3` 权限），并写 `required_resolution`；**不得**记为 SKIP（`ssh`/`sqlite3` 不可用属可重试工具缺失，不是 §2 前置不满足）；现有 [`at_dp_usage_04.py`](../../../../tests/system/api_test_v03/at_dp_usage_04.py) 在无权限时调用 `pytest.xfail` 记为 BLOCKED（可重试），与本设计要求一致；⑥ **纯 A 类**——不改 provider/deployment/service-level，只改一行 `expires_at` 并复位。
- **期望结果与独立 Oracle**：独立 Oracle = 机制 TTL 规则（`expires_at <= now` ⇒ cursor 不可用）+ [`openapi` `ErrorEnvelope`/`ErrorDetail`](../../../../interfaces/openapi/llmtier.openapi.json) + `ERR-CURSOR`（[系统设计 §7.8](../../../20_system_design/llmtier-system-design.md)）。
  - 首屏：`200`，`snapshot_id` 非空。
  - 过期重放：HTTP `400`；body `{"error":{"message":<str>,"type":"request_error","code":"cursor_expired","param":null,"retryable":false}}`（恰 5 键）。
  - 复位：`finally` 回读 `expires_at == original`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：能成功改写为过期并观测 `400 + cursor_expired + type=request_error`，且 `finally` 复位回读与 `original` 相等。
  - **FAIL**：过期重放未返回 400、或 `code != cursor_expired`、或信封不合规；或复位未完成（即使行为正确，残留过期快照也判 FAIL 并保留证据）。
  - **BLOCKED**：无 `ssh`/`sqlite3` 权限、SSH 不可达、快照行不可定位等**可重试**环境/工具缺失（须写 `required_resolution` 与 `reproduction_cmd`；**判 BLOCKED，不得降级为 SKIP**）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（m5air 不可达等）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用伪 cursor/mock 冒充真实过期分支，或用替代路径冒充真实 m5air 路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时记 `NOT_RUN`。
- **证据与 Run**：保存首屏响应（`snapshot_id`）、SSH 命令与输出（`SELECT` 原值、`UPDATE`、回读校验）、过期重放的原始 HTTP status/headers/body、动态窗口值、命令/exit code、环境快照。**证据脱敏**：SSH/DB 命令不含 Secret；`Authorization` 脱敏。`manifest.json` 含 `target_artifact`（三 pin，`git_commit` 为 m5air 同步来源 commit SHA）、`redactions`、FAIL/BLOCKED 时 `reproduction_cmd`。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/dp-usage-04/`，失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**强制 teardown（`finally`）**——恢复该 `snapshot_id` 行的 `expires_at` 原值并回读校验；不改 provider/deployment/service-level，不写注入项，不删除用户 usage。若复位失败：保留现场、报 BLOCKED/FAIL，不做无边界清理（[测试设计 §11](../llmtier-api-test-specification.md)）。B 类不适用本 case；若误跑 B 类，按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班销毁。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查与 [§2.8](../llmtier-api-test-specification.md) 的 DP-USAGE-04 直改 `expires_at` 授权；`ssh m5air` 非交互与非交互 `sqlite3`；`api_client`（[§4.4](../llmtier-api-test-specification.md)）；机制 [`usage-metering` §4.7 TTL](../../../20_system_design/mechanisms/usage-metering.md)；自动化入口 [`at_dp_usage_04.py`](../../../../tests/system/api_test_v03/at_dp_usage_04.py)。**不依赖**其它 Case；与 DP-USAGE-03（正常分页）、DP-USAGE-07（同 cursor 重放）共享 cursor 语义但各自独立执行。
