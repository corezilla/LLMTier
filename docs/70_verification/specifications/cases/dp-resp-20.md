# DP-RESP-20 — 准入饱和 → 429

- **Case ID**：`DP-RESP-20`
- **标题**：`POST /v1/responses` 准入饱和：`429 rate_limit_exceeded` 且带 `Retry-After`（**MISSING** 自动化）。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses` 的**准入/排队契约**：并发超过 `depl_b` 的运行时并发许可与队列上限（队列 32）时，`Router.admit` 拒绝并返回稳定 `429` 与 `Retry-After`。被测端点/规则：`POST /v1/responses`；设计验证项 `VRC-INF-004`；需求 `R-INF-05`；错误目录 `ERR-RATE-LIMIT` → wire `code=rate_limit_exceeded`；机制 `T-QUEUE`；实现 `src/inference/routing.py`（队列满 `len(self._queues[level_id]) >= 32` → `ApiError(429, "rate_limit_exceeded", "Service-level queue is full", retryable=True, headers={"Retry-After":"30"})`；等待超时 → `Retry-After:"1"`）。**不证明什么**：不证明 `model_unavailable`（DP-RESP-19）；不证明超时预算的 ms 级时点（§7 不设 SLO）；不证明 exactly-once/重试语义（§6）。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 `127.0.0.1:<随机空闲端口>` + 临时 SQLite；见[测试设计 §2.3](../llmtier-api-test-specification.md) / §2.4 B 类）。建议使用专属实例，避免与其它 case 的并发/注入互相干扰。`_baseline_settings`：`prov_b` + `depl_b` + 7 tier；`depl_b` 的运行时 `max_in_flight` 默认 1，provider 并发默认 1。fixture `LLMTierInstance`、`admin_client_b`、`api_client_b`（[§4.4](../llmtier-api-test-specification.md)）。初始状态无菌注入项。
- **输入与构造**：以 `delay` 注入占用许可（`delay` 前置阶段在 `admit` 上下文内 sleep，占住唯一并发槽），再并发灌入请求。

  占槽注入（`PATCH /v1/deployments/depl_b/diagnostics`，`admin`）：

  ```json
  {"items": [{"type": "delay", "config": {"delay_ms": 60000}, "enabled": true}]}
  ```

  被测并发：以同一 `data` token 同时发起 `N`（建议 `N >= 34`）个相同请求：

  ```json
  {"model": "Senior", "input": [{"role": "user", "content": "hi"}], "stream": true, "store": false}
  ```

  边界/构造点：`delay_ms` 取上限 `60000`（`_RANGES.delay_ms ∈ [0,60000]`）使槽位长时间占用；`N` 需超过 1（占槽）+ 32（队列上限）；`delay` 属前置阶段注入，命中后 `time.sleep` 发生在 `with router.admit(model)` 内（`responses.py`），故确实持槽。
- **执行过程（逐步调用）**：
  1. （fixture 前置）启动专属实例并 probe `depl_b` → `healthy`；确认无启用注入。
  2. `PATCH /v1/deployments/depl_b/diagnostics`（上表注入）→ 断言 200 且 `delay` 生效。
  3. 以线程/异步并发发起 `N` 个 `POST /v1/responses`。
  4. 收集响应：断言**至少一个**为 `429`；对首个 429 解析 `error`：`code=="rate_limit_exceeded"`、`type=="request_error"`（429<500）、`retryable is True`、`param is None`。
  5. 断言 429 响应含 `Retry-After` 头，值为正整数秒（队列满为 `"30"`，等待超时为 `"1"`）。
  6. （teardown，`finally`）`PATCH .../diagnostics` body `{"items": []}` 清空注入，`GET` 校验为空。
  7. 交叉核对拒绝零副作用：429 无上游调用；账本按 §6/ISD 处理（准入失败可能保留 orphan，不作为"零义务"硬断言，只断言无上游调用）。
- **重点关注步骤**：① **饱和才 429**——只有超过许可+队列上限时拒绝，非首个请求；② **`Retry-After` 存在且为正整数**——本 case 的关键头；③ **区分两条 429 分支**——队列满（`Retry-After:30`）vs 等待超时（`Retry-After:1`），只断"存在+正整数"以免耦合内部时点；④ **并发共享同一 tier 的许可/队列**（§5 并发注），不得假设各请求独立资源；⑤ **注入必须清空**，不得残留 `delay`；⑥ **MISSING**——§3.2 自动化入口为 `MISSING`，须先实现 `at_dp_resp_20.py`。
- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `ErrorEnvelope`/`ErrorDetail` + HTTP `Retry-After` 语义 + 系统设计 §7.8 `ERR-RATE-LIMIT`（不依赖实现答案）。
  - 至少一个请求：HTTP `429`；`Content-Type: application/json`；`Retry-After` 头存在且为正整数。
  - body：`error.code=="rate_limit_exceeded"`、`type=="request_error"`、`retryable==true`、`param==null`。
  - teardown：`PATCH {"items":[]}` → 200，`GET` 无 `enabled` 项。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：饱和时至少一个 `429 rate_limit_exceeded` + `Retry-After` 正整数 + `retryable=true`；teardown 清空。
  - **FAIL**：从未 429（饱和构造失败）、`Retry-After` 缺失/非正整数、code/type 错、注入残留。
  - **BLOCKED**：并发/注入 fixture 不可实现——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 mock/替代路径冒充真实路径，或注入未命中却按 429 判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case **无自动化实现**（§3.2 `MISSING`）；未执行按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存注入写/清空、并发请求清单与各响应（含 429 与 `Retry-After`）、上游调用计数/runtime 快照、发出命令、exit code、环境快照。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`，含 `manifest.json`（[§4.8](../llmtier-api-test-specification.md)）；失败现场不截断。**当前无脚本/artifact**。
- **清理与复位**：**必须 teardown**——`PATCH /v1/deployments/depl_b/diagnostics {"items":[]}` 清空 `delay` 后 `GET` 校验；不修改 `prov_b`/`depl_b`。专属实例由 fixture `stop()` + `rm -rf` 销毁（[测试设计 §2.8/§4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `LLMTierInstance` / `admin_client_b` / `api_client_b`（[§4.4](../llmtier-api-test-specification.md)）；`OBS-DEPL-02`（`PATCH .../diagnostics` 注入，[§3.2](../llmtier-api-test-specification.md)）；实现 `src/inference/routing.py`；错误目录 `ERR-RATE-LIMIT`（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md) §7.8）。**自动化入口 `at_dp_resp_20.py` MISSING（§3.2）**；**不依赖**其它 Case。
