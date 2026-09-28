# ADM-USAGE-03 — 清空 usage（admin + 审计）

- **Case ID**：`ADM-USAGE-03`（与 §3.2 权威清单一致；本文件名 `adm-admin-usage-03.md`，对应 §3.4 索引 `cases/adm-admin-usage-03.md`）。
- **标题**：`DELETE /v1/usage` 清空用量记录：仅 admin 受理（data→403），返回 `{"deleted":N}` 并写审计。
- **目的（被测契约）**：验证用量**重置契约、角色门与审计副作用**。被测端点/规则：`DELETE /v1/usage`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `deleteUsage`，query `model`/`deployment_id` 可选，`security=AdminBearerAuth`）；[`app.py`](../../../../src/http_api/app.py) 以 `_auth_either()` 取主体，`if not is_admin: raise ApiError(403, "permission_denied", …)`；admin 路径经 [`AdminService.mutate`](../../../../src/management/admin.py) 调 [`UsageRecorder.reset_usage`](../../../../src/inference/usage.py) 按 scope 删记录并返回 `{"deleted":<int>}`，同一事务写审计 `action="usage.reset"`、`target="all"`、`result="success"`。设计验证项 `VRC-MGMT-006`；机制 `T-MET-RESET`；需求/机制链 `LT-FUN-004`、`LT-INT-004`、`R-MET-01`、`CT-USAGE-001`。**不证明什么**：不证明查询/分页（ADM-USAGE-01/02、DP-USAGE-*）、不证明重置后新请求重新计账（temporal 时序，未单独构 case）、不证明 provider 的 usage 快照刷新（ADM-PROV-USAGE-02/03）。本 case 锁定"admin 清空 + `deleted` 计数 + 审计 + data 拒绝"。
  > **A/B 归属不一致（登记）**：§3.2 将本 Case 登记为**环境 A**；但全量/部分重置为**破坏性写**（§4.3 将"删除/修改"归 B 类），实现 [`at_adm_admin_usage_03.py`](../../../../tests/system/api_test_v03/at_adm_admin_usage_03.py) 标记 `@pytest.mark.api_b` 并在 `llmtier_b` 上执行。为避免污染 m5air 用户在途账本，本设计以**环境 B** 为准执行，并把"§3.2 A vs 实现/安全 B"登记为规格/实现不一致。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）。执行前须满足[测试设计 §2.1](../llmtier-api-test-specification.md) **附加（B 类）**（`/healthz` 200；`_BASELINE_SETTINGS` = `prov_b`+`depl_b`+7 tier）。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`admin_client_b`（`Bearer dev-admin`）、`api_client_b`（`Bearer dev-data`）、`llmtier_b`（暴露 `_db_path` 供直接 SQL 造种子）。初始状态：`usage_*` 表由本 case 直接 SQL 造种子后非空。
- **输入与构造**：本 case 用直接 SQL 造可计数的种子（`usage_obligations`/`usage_record_versions`/`usage_heads`/`provider_request_bindings`），再 `DELETE`。核心请求：
  ```http
  DELETE /v1/usage HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  ```
  变体（scope）：`DELETE /v1/usage?model=Worker`、`?deployment_id=<id>`、`?model=Worker&deployment_id=<id>`；角色负向：`DELETE /v1/usage` 带 `Bearer dev-data` → 403。不注入故障。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. （种子）直接连 `llmtier_b._db_path`，插入已知条数的 usage 记录（`model∈{Worker,Senior}`、绑定 `prov_b`/`depl_b`），`commit`；记 `inserted`/`before = COUNT(usage_record_versions)`。
  3. `resp = admin_client_b.delete("/v1/usage")`；断言 `200`；`body["deleted"] == inserted`；直连 SQL 断言 `usage_record_versions` 计数为 0。
  4. （scope 变体）重新造种子，`DELETE ?model=Worker` 断言 `deleted == Worker 条数` 且 `Senior` 仍存；`DELETE ?deployment_id=…` 同理。
  5. （审计）`admin_client_b.get("/v1/audit?limit=20")` 断言出现 `action=="usage.reset"`、`result=="success"` 的审计行（`mutate` 写）。
  6. （角色负向）`api_client_b.delete("/v1/usage")` 断言 `403` + `error.code=="permission_denied"` + `type=="request_error"`。
- **重点关注步骤**：① **角色门**——`_auth_either()` 后 `is_admin` 检查；data 凭据必须 403 `permission_denied`（不是 401/400），且**不得**删除任何记录（零副作用）；② **`deleted` 计数**——返回值须等于该 scope 实际删除的行数（`reset_usage` 的 `deleted`）；全量 scope 与 model/deployment scope 计数不同，测试须分别构造；③ **审计同事务**——`AdminService.mutate` 以 `atomic=True` 在同一事务写 `usage.reset` success；**必须**断言审计行存在（本 case 的"审计"契约）；④ **STORE 错误语义**——store 故障应 503 `usage_store_unavailable`（`app.py` 捕获 `sqlite3.Error`），不得返回 200 空 `deleted`；⑤ **破坏性**——全量重置不可在 A 类 m5air 上执行；⑥ **幂等性**——重置后可再次造种子/重置（本 case 每个断言自造种子）。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `deleteUsage` 200 schema `{deleted:integer}` + 角色规则 + 审计要求（[测试设计 §11](../llmtier-api-test-specification.md)）。
  - `DELETE`（admin）：`200`；body `{"deleted":<int == 该 scope 删除行数>}`。
  - 清空核验：直连 SQL `COUNT == 0`（全量）或仅 scope 内记录被删。
  - 审计：出现 `usage.reset`/`success` 行。
  - 角色负向：`403` + `error.code=="permission_denied"`，记录未被删除。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：admin `200` 且 `deleted` 计数正确、scope 语义正确、审计行存在；data 负向 `403 permission_denied` 且零副作用。
  - **FAIL**：status/计数/scope 错、审计缺失、data 得 200、或 store 故障未 503。
  - **BLOCKED**：fixture/断言逻辑问题（种子写不出、直连 SQL 失败）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充被测服务、或在 A 类 m5air 上执行破坏性全量重置——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存种子 SQL/计数、`DELETE` 请求与原始 200 响应（含 `deleted`）、直连 SQL 复核、审计查询响应、角色负向 403（脱敏后）、发出命令、exit code、`elapsed`、环境快照。`manifest.json` 必含 `{…,environment:"b",inputs(scope/种子),oracle,actual,verdict,evidence_files,redactions,reproduction_cmd}`。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`；失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**隔离由 B 类承担**——重置即本 case 的目的状态；退出前确认 `usage_record_versions` 计数为 0（或本次断言终态）、无本次新建 deployment 残留（部署 scope 变体若新建 deployment 须删除）。B 类整班结束 `stop()`（`terminate`→等待 5s→`kill`）+ `rm -rf` 临时目录（[测试设计 §4.7](../llmtier-api-test-specification.md)）。**不得**在 A 类执行。
- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b` / `api_client_b`（[§4.4](../llmtier-api-test-specification.md)）；`deleteUsage` 机器契约；`UsageRecorder.reset_usage`；`AdminService.mutate` 审计；机制 `T-MET-RESET`。自动化入口 [`at_adm_admin_usage_03.py`](../../../../tests/system/api_test_v03/at_adm_admin_usage_03.py)。**不依赖**其它 Case；与 ADM-USAGE-01/02 读路径互补。
