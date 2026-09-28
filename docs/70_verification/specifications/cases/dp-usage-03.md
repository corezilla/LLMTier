# DP-USAGE-03 — cursor 分页（limit=1）

- **Case ID**：`DP-USAGE-03`（与 §3.2 权威清单一致；本文件名 `dp-usage-03.md`，唯一对应）。
- **标题**：`GET /v1/usage?limit=1` 每页至多 1 条并给出 `next_cursor`；沿 cursor 取后续页，同 `snapshot_id`/`snapshot_at`、按 `(recorded_at,request_id)` 稳定推进、无重复无遗漏，`has_more=false` 时 `next_cursor=null`。
- **目的（被测契约）**：验证 **Usage 分页游标契约**。被测端点/规则：`GET /v1/usage`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listUsage`，`limit` `1..200` 默认 100，`cursor` 可选）——首屏创建 `query_snapshots` 并冻结有序成员，返回 `next_cursor = "<snapshot_id>:<offset>"`；后续页按冻结视图读，`snapshot` 跨页不变。实现 `src/inference/usage.py::UsageRecorder._page`（`ORDER BY v.recorded_at,v.request_id`，`limit+1` 探测 `has_more`）。设计验证项 `VRC-MGMT-006`；机制需求 `R-MET-02`；机制 `T-MET-PAGE`（见 [usage-metering 机制](../../../20_system_design/mechanisms/usage-metering.md) §4.5/§4.7 CON-METER-004）；需求链 `LT-FUN-004`、`LT-INT-004/005/007`、`CT-USAGE-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明过期 cursor 拒绝（DP-USAGE-04）、主体隔离（DP-USAGE-06）、同 cursor 重放的逐字节幂等/冻结不变（DP-USAGE-07）、store 不可用（DP-USAGE-08）；不证明时间窗元数据完整性（DP-USAGE-01）；不证明 `limit` 取值范围校验（实现仅做整数转换，见下"缺陷/注意"）。
- **前置与环境**：**环境 A**（m5air，角色 `data`；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 6 项就绪检查；任一失败 → 整班 BLOCKED/SKIP。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`api_client`（`Bearer dev-data`，principal_id=`consumer`）。**自含前置**：为得到 ≥2 条记录，先发 2 次 `POST /v1/embeddings`（`model="Embedding-v1"`，固定输入）并捕获各自 `X-Request-ID`；窗口使用**紧致动态窗口**（如 `from=now-5min`、`to=now+1min`，由 `now()` 生成，禁止硬编码日期），把分页范围限制在本次记录附近。embeddings deployment 见 §2.1.6 `dep_local_bge_m3`。
- **输入与构造**：两次前置 embeddings（同 DP-USAGE-02 形态），随后：
  ```http
  GET /v1/usage?from=<tight-from>&to=<tight-to>&limit=1 HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  ```
  再以首屏返回的 `next_cursor`：
  ```http
  GET /v1/usage?from=<tight-from>&to=<tight-to>&limit=1&cursor=<sid>:1 HTTP/1.1
  ```
  构造点：`limit=1` 为边界（§5 边界清单）；同一 `from`/`to` 必须在所有页保持**逐字节相同**，否则 `filter_digest` 不匹配会返回 400 `invalid_request`（`_page` 的 cursor 复核）；`cursor` 由首屏 `next_cursor` 原样带入。
- **执行过程（逐步调用）**：
  1. `GET /healthz`/`GET /readyz`（`pytest_configure` 完成，不重复）。
  2. 发 2 次 `POST /v1/embeddings`，各断言 200，捕获 `rid_a`、`rid_b`（若两次恰好同 `recorded_at` 秒，排序仍由 `request_id` 决胜，稳定）。
  3. `page1 = GET /v1/usage?from&to&limit=1`；断言 200；`len(data) == 1`；`has_more` 为 bool；`snapshot_id` 非空；若 `has_more=true` 则 `next_cursor` 匹配 `^<snapshot_id>:\d+$` 且非空，否则为 `null`。
  4. `c1 = page1.next_cursor`；`page2 = GET /v1/usage?from&to&limit=1&cursor=c1`；断言 200 且 `page2.snapshot_id == page1.snapshot_id`、`page2.snapshot_at == page1.snapshot_at`。
  5. 断言 `page1.data[0].request_id != page2.data[0].request_id`（不重复）；沿 `next_cursor` 继续（≤ 若干页上限）直到 `has_more=false`，累积所有 `request_id`，断言 `rid_a`、`rid_b` 各恰出现 1 次（无遗漏/无重复）。
  6. 末页断言 `has_more=false ⇒ next_cursor is null`。
- **重点关注步骤**：① **cursor 形态与解析**——`<snapshot_id>:<offset>`；服务端按 `cursor.split(":",1)[0]` 取 snapshot、`[1]` 取 offset；把 `cursor` 当不透明字符串带回，不要自行拼错；② **跨页 snapshot 不变**——`snapshot_id`/`snapshot_at` 在 page1 与 page2 必须一致（首屏冻结、后续页读冻结视图）；若第二页出现**新** `snapshot_id` 即 FAIL；③ **稳定排序 `(recorded_at,request_id)`**——紧致窗口下两页顺序应与该排序一致；④ **`has_more`/`next_cursor` 同步**——openapi `if/then`：`has_more=false ⇒ next_cursor=null`；⑤ **同 filter**——所有页 `from`/`to`（及 `model`/`request_id` 若带）必须一致，否则 400 `invalid_request` 是**预期外**的（本 case 应避免）；⑥ **缺陷/注意（实现与 openapi 不符）**：handler 用 `_int_param`（`src/http_api/app.py`）只做 `int()` 转换，**不校验** openapi 的 `minimum:1`/`maximum:200`；即 `limit=0`/`limit=500` 不会被拒。本 case 不据此判 FAIL（只测合法 `limit=1`），但应在运行报告登记该"范围未校验"偏差。另：现有 [`at_dp_usage_03.py`](../../../../tests/system/api_test_v03/at_dp_usage_03.py) 只断言单页 `≤1` 与 `next_cursor` 非空，**未跟随 cursor 取第二页、未验证跨页同 snapshot/无重复无遗漏**；设计完整断言须补齐。
- **期望结果与独立 Oracle**：独立 Oracle = 机制 CON-METER-004/Step 4–5（首屏冻结 + 后续页读冻结视图 + 稳定排序）+ [`openapi` `UsagePage`](../../../../interfaces/openapi/llmtier.openapi.json)。
  - page1：`200`，`data` 长 1，`has_more` bool；`has_more=true ⇒ next_cursor=="<snapshot_id>:1"`（非空），`false ⇒ null`。
  - page2：`200`，`data` 长 ≤1，`snapshot_id`/`snapshot_at` 与 page1 相同，`request_id` 与 page1 不同。
  - 沿页累积：`rid_a`、`rid_b` 各出现恰 1 次；末页 `has_more=false` 且 `next_cursor=null`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：上述 page1/page2/累积/末页断言全部 match。
  - **FAIL**：`data` 超 `limit`、跨页 `snapshot_id` 变化、重复/遗漏本次 `request_id`、`has_more`/`next_cursor` 不变式破裂、排序不稳。
  - **BLOCKED**：断言逻辑/契约问题、embeddings 前置无法命中——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 mock/替代路径冒充真实路径，或未命中真实分页而按行为判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时记 `NOT_RUN`。
- **证据与 Run**：保存两次前置 embeddings 的 `X-Request-ID`、所有分页请求（含 `cursor` 实际值）与响应（`data[].request_id`、`record_version`、`snapshot_id`、`snapshot_at`、`next_cursor`、`has_more`）、动态窗口值、命令/exit code/`elapsed`、环境快照。`manifest.json` 含 `target_artifact`（三 pin）与 `redactions`。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/dp-usage-03/`。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——查询为只读，仅创建 10 分钟 TTL 的首屏 `query_snapshots`；两次 embeddings 属被测行为（不删用户 usage，§2.8）。不创建/修改 provider/deployment/service-level、不写注入。退出前 `/readyz` 仍 7 tier；若误跑于 B 类则按[测试设计 §4.7](../llmtier-api-test-specification.md) 销毁临时实例。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client`（[§4.4](../llmtier-api-test-specification.md)）；embeddings tier `Embedding-v1`/`dep_local_bge_m3`；机制 [`usage-metering` CON-METER-004](../../../20_system_design/mechanisms/usage-metering.md)；自动化入口 [`at_dp_usage_03.py`](../../../../tests/system/api_test_v03/at_dp_usage_03.py)。**不依赖**其它 Case；与 DP-USAGE-04（过期 cursor）、DP-USAGE-07（同 cursor 重放）共享 cursor 语义但各自独立执行。
