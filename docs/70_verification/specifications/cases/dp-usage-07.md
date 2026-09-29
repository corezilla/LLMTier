# DP-USAGE-07 — 分页重放幂等

- **Case ID**：`DP-USAGE-07`（与 §3.2 权威清单一致；本文件名 `dp-usage-07.md`，唯一对应；**新增 Case**）。
- **标题**：同一 usage `cursor` **重放**返回同一冻结的 record version 成员：后续页重放逐字段相同，不新建 `snapshot`、不推进 head；首屏冻结后新增记录对旧页不可见。
- **目的（被测契约）**：验证 **Usage cursor 重放幂等与快照冻结契约**。被测端点/规则：`GET /v1/usage`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listUsage`）：首屏在单事务内写 `query_snapshots` 并冻结有序成员 `(principal, request_id, record_version)`；后续页仅按 `<snapshot_id>:<offset>` 读**冻结视图** `query_snapshot_items`（含 `frozen_view_json`）；读操作不写账本。实现 `src/inference/usage.py::UsageRecorder._page`（首屏 `INSERT INTO query_snapshots`/`query_snapshot_items`；后续页 `SELECT frozen_view_json ... WHERE snapshot_id=? AND ordinal>=?`）。设计验证项 `VRC-MGMT-006`；机制需求 `R-MET-02`；机制 `T-MET-PAGE`（见 [usage-metering 机制](../../../20_system_design/mechanisms/usage-metering.md) §4.7/CON-METER-004，INV-6「旧页不受后续更正影响」、Step 5 冻结视图）；需求链 `LT-FUN-004`、`LT-INT-004/005/007`、`CT-USAGE-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明过期 cursor（DP-USAGE-04）、主体绑定/跨主体拒绝（DP-USAGE-06）、分页稳定排序本身（DP-USAGE-03）、store 不可用（DP-USAGE-08）；不证明跨请求的 exactly-once 重试语义（[测试设计 §6](../llmtier-api-test-specification.md) 明确本版本不定义）；不证明 `recorded_at`/版本推进（由 DP-USAGE-02 的 `T-MET-FINAL` 承接）。
- **前置与环境**：**环境 A**（m5air 已部署实例；角色 `data`，只读/无状态；见[§2.3](../llmtier-api-test-specification.md)）。执行前必须通过[§2.1](../llmtier-api-test-specification.md) 的 6 项就绪检查（详见 §2.1）；任一失败 → 整班 BLOCKED/SKIP。fixture（[§4.4](../llmtier-api-test-specification.md)）：api_client（见 §4.4）。初始状态：m5air 现有基线。embeddings tier `Embedding-v1`/`dep_local_bge_m3`（§2.1.6）。**自含前置**：发 3 次 `POST /v1/embeddings`（固定输入）得到 `rid_1..rid_3`；用**紧致动态窗口**（`from=now-5min`、`to=now+1min`，由 `now()` 生成，禁止硬编码）圈定；分页全程 `from`/`to` 逐字节不变（否则 `filter_digest` 不匹配 → 400 `invalid_request`）。
- **输入与构造**：
  ```http
  GET /v1/usage?from=<w>&to=<w>&limit=1                 → page1（无 cursor，创建 snapshot sid）
  GET /v1/usage?from=<w>&to=<w>&limit=1&cursor=<sid>:1  → page2（冻结视图 offset 1）
  GET /v1/usage?from=<w>&to=<w>&limit=1&cursor=<sid>:1  → page2'（重放）
  GET /v1/usage?from=<w>&to=<w>&limit=1&cursor=<sid>:1  → page2''（追加一条记录后再重放）
  ```
  另发第 4 次 embeddings（`rid_4`）在 page1 之后，用于验证"插入对旧页不可见"。
  构造点：cursor 取首屏 `next_cursor` 原样（或 `f"{sid}:1"`）；每次重放带**同一** `from`/`to`/`limit`；`sid` 取自 page1 `snapshot_id`。
- **执行过程（逐步调用）**：
  1. `GET /healthz`/`GET /readyz`（`pytest_configure` 完成，不重复）。
  2. 发 3 次 embeddings，断 200，捕获 `rid_1..rid_3`。
  3. `page1 = GET ?from&to&limit=1`；断言 200，`snapshot_id=sid`，`next_cursor=c`（形如 `<sid>:1`）。
  4. `page2 = GET ?...&cursor=c`；断言 200 且 `snapshot_id==sid`，记录 `page2.data`（含 `request_id`+`record_version`）与 `next_cursor`/`has_more`。
  5. `page2r = GET ?...&cursor=c`（重放）；断言 `page2r.data == page2.data`（逐字段，**含 `record_version`**）、`page2r.snapshot_id == sid`、`page2r.next_cursor == page2.next_cursor`、`page2r.has_more == page2.has_more`。
  6. 发第 4 次 embeddings（`rid_4`，落在同一窗口）。
  7. `page2r2 = GET ?...&cursor=c`（再次重放）；断言 `page2r2.data == page2.data`（旧页**不受**新增 `rid_4` 影响；`rid_4` 不得出现在 page2 的重放结果中）。
  8. （对照，不改变判定）`fresh = GET ?from&to&limit=200`（无 cursor，新快照）；断言 `rid_4` **出现**在新快照中——佐证"新增只对新 snapshot 可见"。
- **重点关注步骤**：① **重放相等必须含 `record_version`**——只比较 `request_id` 不够；冻结的是 `(request_id, record_version)` 成员，版本号必须一致；② **snapshot 不因重放新建**——`snapshot_id` 在三/四次请求间恒为 `sid`（cursor 分支不写 `query_snapshots`）；③ **旧页冻结**——page1 后新增 `rid_4` 对 `cursor=c` 的重放不可见（INV-6）；④ **读不改账本**——重放不推进 `usage_heads.head_record_version`，可用同一 `request_id` 在新快照中的 `record_version` 未因读取而增大间接佐证；⑤ **filter 一致**——重放的 `from`/`to`/`limit` 必须与原 cursor 完全一致，否则 400 `invalid_request`（属误操作，非本 case 期望）；⑥ **cursor 为 null 兜底**——若 `limit=1` 窗口内仅 1 条，`next_cursor=null`，改用 `f"{sid}:1"` 生成第二页 cursor，但需确保窗口内确有 ≥2 条（本 case 已发 3 条）；⑦ **MISSING 语义**——无实现是缺口（NOT_RUN），不是跳过。
- **期望结果与独立 Oracle**：独立 Oracle = 机制 CON-METER-004/Step 5（冻结视图按 `sid:offset` 读）+ INV-6（旧页不受后续更正/插入影响），不依赖实现的返回顺序/内容。
  - page2 与两次重放：`data` 逐字段相等（含 `request_id`、`record_version`）；`snapshot_id` 恒为 `sid`；`next_cursor`/`has_more` 相等。
  - page1 之后新增的 `rid_4` 不出现在 `cursor=c` 的任何重放结果中；新快照（无 cursor）中可见。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：步骤 5 与 7 的重放逐字段相等、`snapshot_id` 稳定、`rid_4` 不进旧页，且步骤 8 新快照可见 `rid_4`。
  - **FAIL**：重放结果不一致（含 `record_version` 漂移）、重放生成新 `snapshot_id`、旧页泄漏新增记录、或 `next_cursor`/`has_more` 漂移。
  - **BLOCKED**：断言逻辑/契约问题、embeddings 前置无法命中——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：mock/替代路径冒充真实路径——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9。
- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-api-test-specification.md)：Run ID=`<date>/A-api`；保存4 次前置 embeddings 的 `X-Request-ID`、page1/page2/各次重放/新快照的完整响应（`request_id`、`record_version`、`snapshot_id`、`next_cursor`、`has_more`）、cursor 实际值、动态窗口值、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。
- **清理与复位**：**无需 teardown**——4 次 embeddings 属被测行为，不删用户 usage（§2.8）；查询只创建 10 分钟 TTL 快照；不改 provider/deployment/service-level、不写注入。退出前 `/readyz` 仍 7 tier；若误跑 B 类则按[测试设计 §4.7](../llmtier-api-test-specification.md) 销毁。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client`（[§4.4](../llmtier-api-test-specification.md)）；embeddings tier `Embedding-v1`；机制 [`usage-metering` §4.7/CON-METER-004/INV-6](../../../20_system_design/mechanisms/usage-metering.md)；[测试设计 §6](../llmtier-api-test-specification.md) 的重放/幂等边界；`UsagePage`/`UsageRecord` 机器契约。自动化入口 `at_dp_usage_07.py`（**当前 `MISSING`，新增 Case**）。**不依赖**其它 Case；与 DP-USAGE-03（游标推进）、DP-USAGE-04（过期）、DP-USAGE-06（主体绑定）共享 cursor 语义但各自独立执行。
