<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 API Test Plan

> STD 使用入口：[项目采用说明与标准导航](../../00_management/standards/README.md)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-api-test-plan` |
| Document Version | `0.3.0-draft.8` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-21` |
| Last Modified Date | `2026-09-28` |
| Template ID | `assurance.test-plan` |
| Template Version | `0.2.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | `llmtier-test-plan, llmtier-vv-plan` |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/plans/llmtier-api-test-plan.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. 目标、范围与测试层级

本文件是 LLMTier V0.3 **HTTP API 专项测试计划**，聚焦**运行中服务的端到端行为验证**（路径、方法、认证角色、正常/边界/负向、错误信封与稳定错误码、SSE 序列、分页、故障注入、别名命名空间）。

**测试层级**：系统级 / 接口级（system / interface contract of a running LAN service）。不使用单元测试或静态契约验证冒充本层结论；反之，本层 PASS 也不证明静态契约或单元逻辑正确。

**配套文档分工**

| 文档 | 职责 |
|---|---|
| [`llmtier-api-test-specification.md`](../specifications/llmtier-api-test-specification.md) | **Case catalog**：逐 Case 的输入/独立 Oracle/设计 V/环境/证据（125 个 Case） |
| `llmtier-test-plan.md` | ST-01~ST-26 系统测试（含 API 与耐久/性能/安全） |
| `llmtier-contract-test-specification.md` | OpenAPI/manifest 静态契约验证（STATIC PASS） |
| `llmtier-vv-plan.md` | 高层 V&V 方法论 |
| [`llmtier-api-test-execution.md`](./llmtier-api-test-execution.md) | 执行层计划（阶段/工时/产出物） |

**被测范围**：全部对外路由——Data Plane（`POST /v1/responses`(SSE)、`POST /v1/embeddings`、`GET /v1/models`、`GET /v1/models/{model}`）、Usage（`GET /v1/usage`、`DELETE /v1/usage`）、Management（`/v1/providers(/{id})`、`/v1/providers/{id}/usage`、`/v1/providers/{id}/models`、`/v1/deployments(/{id})`、`/v1/service-levels(/{id})`、`POST /v1/probes`、`/v1/runtime`、`/v1/stats`、`/v1/audit`、`/v1/logs`）、Observability（`/v1/diagnostics(+/snapshots|/stats|/traces)`、`/v1/deployments/{id}/diagnostics`、`/v1/trace/{request_id}`）、No-auth（`/healthz`、`/readyz`）、Alias（`/tier/admin/v1/*`）。

**不在本计划范围**：Web UI、FD 资源泄漏、SQLite 持久化文件格式、auth mock 单元测试、静态契约验证、性能 SLO 校准（分别由 `llmtier-test-plan.md` ST-18/19/21、contract specification、unit 承接）。

**Case 总数**：125（RUN 88 / MISSING 37）；执行通过标准：全部适用 Case PASS，MISSING 记为 NOT_RUN 缺口而非跳过。计数与逐 Case 定义见 specification §3。

## 2. 被测基线、排除项与依赖

**固定基线（可复查来源与版本）**

| 类别 | 基线 | 变化时的重跑范围 |
|---|---|---|
| 机器契约 | `interfaces/openapi/llmtier.openapi.json`（OpenAPI 3.1.0；`BearerAuth`/`AdminBearerAuth`；`x-llmtier-contract-aliases`） | 全部路由/schema 相关 Case |
| 错误目录 | 系统设计 §7.8（`<!-- STD_PUBLIC_ERROR_CATALOG_BEGIN -->`，`ERR-*` 八字段） | 全部负向 Case |
| 数据/行为 | `llmtier-system-design.md` §5–§7、§11 | 对应机制 Case |
| 接口控制（ISD） | `piko-data-plane-control.md`、`slinky-capacity-observation-control.md`、`llmtier-management-control.md` | 对应接口成员 Case |
| 机制 | `mechanisms/{inference-stream,access-trust,usage-metering,observability,config-lifecycle}.md` | `T-*`/`VRC-*` 映射 Case |
| 测试规范 | `testing-standard.md`（TS-002 依赖头部、TS-003 LAN IP） | 全部 Case |
| 项目标准 | `docs/std.lock.json`（STD `0.1.0-draft.41`） | 文档质量门 |
| 代码 | 当前 `main` 工作树（m5air 部署版本） | 全量 |

**排除项与依据**：FD/耐久/性能压测排除（`llmtier-test-plan.md` §2.2 已定 m5air 不适合污染性 Case）；外部 MiniMax 返回内容排除（费用与不确定性，A 类只验 HTTP 200）；Web UI 认证（无浏览器 SSO，由 `llmtier-test-plan.md` 独立承接）。

**依赖**：m5air OMLX `192.168.1.9:9000`、m5mac OMLX `192.168.1.8:9000`（Bearer `9832`）；B 类临时实例依赖 Python 3.14 + 可用临时端口 + 临时 SQLite 权限。**依赖不可用 → BLOCKED/SKIP**（见 §7）。

## 3. Test Strategy 与 Coverage Model

**导出方式**：从机器契约（openapi 路由/方法/securitySchemes）+ 错误目录（§7.8）+ 机制可验证断言（`T-*`/`INV-*`）导出 Case；再用**状态与风险**补负向、边界、并发、恢复路径。覆盖模型必须能发现**孤儿需求**（有 Rule 无 Case）与**未测失败路径**（有 error code 无 Case）。

**A/B 两类执行策略（核心约束）**

| 类 | 范围 | 执行方式 | case 数 |
|---|---|---|---|
| **A — 读/观察/无状态写** | HEALTH、DP-MODELS/RESP/EMB/USAGE 的读、全部 GET、PROBE-01/02、PROV-USAGE、审计/日志/运行态/统计、AUTH | 直接打 m5air 现有实例 | 88 中的 A 子集 |
| **B — 写/空库/无鉴权/注入** | provider/deployment/service-level POST/PATCH/DELETE、`_EMPTY_SETTINGS`、`_NO_AUTH_SETTINGS`、OBS-DEPL 注入、并发/故障注入 | 临时 SQLite + 临时端口启新实例（同机第二进程），teardown 销毁 | 88 中的 B 子集 |

**B 类为何用临时实例**：写操作若直接在 m5air 跑会因 ID 冲突/状态累积而不稳定（9-20 ST-13 DELETE 未清理污染 ST-14）；临时实例 = 干净起点。**A 类为何直连 m5air**：读操作无状态影响，且 m5air 已有完整 provider/deployment 现成 state。**A 与 B 不共享 SQLite/进程。**

**断言策略**：先建连/状态码，再验 body 关键字段与 error `code`，SSE 还需验事件序列/terminal/`[DONE]`；禁止"HTTP 200 即 PASS"。拒绝用例同时交叉核对**零副作用**（usage/runtime/trace）。注入用例必须证明命中。

**覆盖模型门**：每条 openapi 路由至少一个正常 Case + 一个负向 Case；每个 §7.8 `ERR-*` 至少映射一个 Case 或在 §11 具名缺口；每个 `BearerAuth`/`AdminBearerAuth`/公开端点各覆盖 AUTH Case。specification §3 的 `设计 V` 列即覆盖证据。

## 4. Test Item、Feature 与 Requirement Matrix

本矩阵只**索引**；逐 Case 输入/Expected/Oracle 见 specification §3。

| Feature / 子系统 | Requirement / 设计 V | 层级 | 责任模块 | 验证方法 | Case 家族（specification §3） |
|---|---|---|---|---|---|
| Liveness / Readiness | `VRC-API-002`,`VRC-MGMT-003`,`VRC-UTIL-001/002` | system/interface | M001/M004/M007 | live HTTP + 状态 fixture | HEALTH-01..06 |
| Models | `VRC-INF-001/002`,`T-NAME` | system/interface | M003/M001 | live HTTP | DP-MODELS-01..07 |
| Responses / SSE | `VRC-INF-001/003/004`,`VRC-DIAG-004`,`T-STREAM/T-QUEUE/T-TOOLS/T-DISCONNECT` | system/interface | M001/M003/M006 | live SSE + 故障注入 | DP-RESP-01..21 |
| Embeddings | `VRC-INF-001/002`,`T-OPEN-04` | system/interface | M003/M001 | live HTTP | DP-EMB-01..07 |
| Usage（数据面） | `VRC-MGMT-006`,`T-PAGE/T-USAGE-VIEW/T-QUERY-SNAPSHOT` | system/interface | M003/M004/M007 | live HTTP + fixture | DP-USAGE-01..06 |
| Providers | `VRC-MGMT-001/002`,`T-CFG-*` | system/interface | M004/M007 | live CRUD | ADM-PROV-01..13、ADM-PROV-MODELS-01..02、ADM-PROV-USAGE-01..03 |
| Deployments | `VRC-MGMT-001/002` | system/interface | M004 | live CRUD | ADM-DEPL-01..09 |
| Service levels | `VRC-MGMT-002`,`T-LEVEL` | system/interface | M004 | live CRUD | ADM-SL-01..07 |
| Probes / Runtime / Stats | `VRC-DIAG-004`,`VRC-INF-004`,`VRC-MGMT-006` | system/interface | M004/M003 | live HTTP | ADM-PROBE-01..03、ADM-RUNTIME-01、ADM-STATS-01..03 |
| Audit / Logs | `VRC-MGMT-003`,`VRC-LOG-001`,`T-EVENT/T-TRUST-LEAK` | system/interface | M004/M008 | live HTTP + 脱敏扫描 | ADM-AUDIT-01..02、ADM-LOGS-01..02 |
| Usage reset | `T-MET-RESET`,`T-RESET` | system/interface | M003/M007 | live HTTP + 审计 | ADM-USAGE-01..03 |
| Diagnostics switches | `VRC-DIAG-001`,`T-OBS-SWITCH` | system/interface | M006 | live HTTP | OBS-DIAG-01..03 |
| Snapshots / Stats / Traces | `VRC-DIAG-002`,`T-OBS-SNAP/T-OBS-STATS/T-OBS-TRACE` | system/interface | M006/M005 | live HTTP | OBS-SNAP-01..02、OBS-STATS-01..02、OBS-TRACE-01..02 |
| Fault injection / Request trace | `VRC-DIAG-004/002`,`T-OBS-INJECT/T-OBS-TRACE` | system/interface | M006 | 注入 + trace 交叉 | OBS-DEPL-01..04、OBS-REQTRACE-01..02 |
| Alias namespace | `x-llmtier-contract-aliases` | system/interface | M001 | 路径等价比对 | OBS-ALIAS-01..04 |
| Auth / Role | `VRC-API-002`,`VRC-MGMT-003`,`T-ROLE/T-TRUST-*` | system/interface | M001 | live HTTP（LAN trust/no-auth） | AUTH-01..09 |

## 5. 环境、设备、拓扑、数据和工具

### 5.1 执行机与拓扑

**执行机 = m5air (`192.168.1.9`)**：A 类直连 `http://192.168.1.9:8181` 现有实例；B 类同机第二进程（临时端口 + 临时 SQLite）。上游 m5air OMLX `192.168.1.9:9000` 与 m5mac OMLX `192.168.1.8:9000`。**TS-003：provider endpoint 必须使用 LAN IP（`192.168.x.x`），禁止 `127.0.0.1`。**

### 5.2 环境就绪检查清单（执行前必过；任一失败 → 整班 skip/BLOCKED）

```
[OK] §2.1.1 m5air /healthz 200 且 {"status":"ok"}
[OK] §2.1.2 m5air /readyz 200 且 models 含 7 个固定 tier
          (Senior/Junior/Worker/Associate/Engineer/Executor/Embedding-v1)
[OK] §2.1.3 m5air OMLX :9000 /models 200（Bearer 9832）
[OK] §2.1.4 m5mac OMLX :9000 /models 200（Bearer 9832）
[OK] §2.1.5 provider_omlx_m5mac.secret_ref 为 file: 路径（has_secret=true；非 env:）
```

由 `tests/system/api_test_v03/conftest.py` 的 `pytest_configure` 自动执行。Python 3.14、LAN trust、TS-003 已在 m5air 部署成立。

### 5.3 Provider / Deployment 路由矩阵

| 逻辑 Tier | 路由 | 上游 | 上游模型 | 上游 Auth |
|---|---|---|---|---|
| Worker/Senior/Junior/Associate/Engineer/Executor | 三选一调度（`provider_minimax`/`provider_local`/`provider_omlx_m5mac`） | 见部署配置 | 见部署配置 | Bearer 9832 / MiniMax API key |
| Embedding-v1 | 固定 `provider_local` | `http://192.168.1.9:9000/v1` | bge-m3（**1024 维硬断言**） | Bearer 9832 |

约束：`DP-RESP-*` 不指定路由，只断言"最终 200 + SSE/JSON 合法"；`DP-EMB-*` 严格绑定 Embedding-v1 → bge-m3 1024 维；`provider_minimax` 有外部费用，A 类只验 HTTP 200，不验内容。

### 5.4 B 类 fixture 注入（用 admin API，不直写 SQL）

```
3 providers: provider_local, provider_omlx_m5mac, provider_minimax
4 deployments: dep_local_gemma, dep_local_bge_m3, dep_omlx_qwen36, dep_minimax_m27
7 service-levels: Senior/Junior/Worker/Associate/Engineer/Executor/Embedding-v1
```

预设 fixture：`_BASELINE_SETTINGS`（prov_b + depl_b，用于 CRUD/注入）、`_EMPTY_SETTINGS`（HEALTH-04）、`_NO_AUTH_SETTINGS`（HEALTH-06/AUTH-07）。`LLMTIER_DATA_TOKEN`/`LLMTIER_ADMIN_TOKEN` = `dev-data`/`dev-admin`。

### 5.5 数据与工具

| 工具 | 用途 | 备注 |
|---|---|---|
| `tests/system/api_test_v03/at_*.py` | Case 实现（`at_<family>_<seq>.py`） | `HEALTH-*` 由 `at_obs_01..03.py` 承接 |
| `tests/system/api_test_v03/{runner_a.sh,runner_b.sh}` | A/B 类批量执行 | B 类串行 |
| [`tools/inference_smoke.py`](../../../tools/inference_smoke.py) | Data Plane 端到端 smoke：`/healthz` + `POST /v1/responses`(SSE 骨架) + `POST /v1/embeddings`(float/base64) | **不替代** 逐 Case 断言；默认 `--base http://192.168.1.9:8181` |
| `tools/api_smoke_test.py` | 全端点 status-only smoke | 只验建连，不验 body 字段 |
| `tests/fixtures/v03_fake_provider.py` | 本地假上游（无外部依赖） | provider endpoint 用 LAN IP |
| `tests/integration/v03_smoke.py` | 集成冒烟 | |
| `sqlite3` 直连 m5air 状态库 | 仅 DP-USAGE-04 改 `expires_at` 造过期 cursor | 需权限；仅 A 类该 Case |

## 6. Test Types 与 Case Families

覆盖类型：**normal、boundary、negative、concurrency、recovery、security、performance、endurance**（endurance 引用 `llmtier-test-plan.md` ST-19，不重复）。

| 类型 | 代表 Case | 关键实现约束（执行前必读） |
|---|---|---|
| normal | DP-RESP-01、DP-EMB-01/02、ADM-* CRUD、HEALTH-02、OBS-DEPL-02→DP-RESP-11 | SSE 序列（`sse.py` 真相）：`response.created→output_item.added→output_text.delta×N→output_text.done→output_item.done→response.completed(status=completed)→data: [DONE]`；每帧 `sequence_number` 单调递增；`usage.*` 非 null |
| boundary | DP-MODELS-03/04/05、DP-RESP-10、DP-EMB-05、DP-USAGE-03、ADM-AUDIT-02、ADM-USAGE-02、OBS-DEPL-04 | `limit=1`；`max_output_tokens=10`；batch 33；注入数值范围 `delay_ms∈[0,60000]`、`retry_after_sec∈[0,300]`、`stream_terminate_after_events∈[1,10000]` |
| negative | DP-RESP-02/07/08/09/16/17/18/19、DP-EMB-04/06/07、ADM-*-400/404/409/412、AUTH-02/03/06/07 | **错误信封** `{"error":{"message":str,"type":"request_error"|"server_error","code":str,"param":str|null,"retryable":bool}}`；`type` 由 status 导出（<500=`request_error`，否则 `server_error`）；`code` 用 §7.8 稳定码值；`param` 指首个非法字段 |
| concurrency | DP-RESP-20、ADM-PROV-05/06/07、ADM-PROBE-02 | 并发写用 `If-Match`/412 串行；准入共享许可/队列；**禁止 grep `"error"`**（会误匹配 `"error":null`），必须 JSON 解析 |
| recovery | DP-RESP-11/21、OBS-DEPL-02/04、`stream_terminate`/`malformed_event` | 注入须命中（trace `source=injected`）；撤销后回到合法终态；不定义 exactly-once |
| security | ADM-AUDIT-01、ADM-LOGS-01、AUTH-01..09、OBS-ALIAS-* | 断言不含 secret 字面值（`9832`、key 文件内容）；管理面未授权不泄露存在性；注入/探测需确认 |
| performance | DP-RESP-01 计时、DP-RESP-20 `Retry-After` | 只记录，不设 SLO 门限 |
| endurance | —（引用 ST-19） | 不在本计划 |

**关键实现约束补充**

- **If-Match ETag 格式**：`src/management/registry.py:25` → `f'"{resource_id}.v{version}"'`（**含双引号**）。PATCH/DELETE 必须严格匹配；不匹配 → 412 `version_conflict`，**body 含 `current_version`**。
- **`confirm_external_call`**：`POST /v1/providers/{id}/usage` 与 `POST /v1/probes` 需 `{"confirm_external_call":true,…}`；`/v1/providers/{id}/usage` body 键集必须等于 `{confirm_external_call}`（否则 400 `invalid_request`）；`/v1/probes` body 键集必须等于 `{deployment_id, confirm_external_call}`（缺 → 400 `confirmation_required`）。`GET /v1/providers/{id}/models` 可能触上游（只读目录）。
- **`capabilities` 12 键全集**（registry `CAPABILITY_KEYS`）：`responses, embeddings, tools, structured_outputs, input_modalities, output_modalities, context_window, max_output_tokens, embedding_space_id, embedding_dimensions, embedding_max_batch_inputs, embedding_max_input_tokens`；缺/多即 400。
- **固定 tier**：service-level `id` 必须在 7 个 FIXED_TIERS 内，否则 400 `invalid_request`；删除固定 tier → 409 `fixed_service_level`；PATCH 仅 `deployment_ids`/`enabled`。
- **`/readyz` 状态**：`ready`（全 available，200）| `degraded`（有候选但非全健康，503）| `not_ready`（无候选/启动失败，503）；body `{status, models[{id,availability}]}`。
- **分页时间参数**：`/v1/usage`、`/v1/stats`、`/v1/logs` 用 **`from`/`to`**；`/v1/diagnostics/stats` 用 **`since`/`until`**（缺 → 400 `invalid_request`）。
- **别名命名空间**：`/tier/admin/v1/*` 的 6 条诊断/追踪路由与 `/v1/*` 为**同一 handler 的精确别名**（openapi `x-llmtier-contract-aliases`），body 应逐字节等价；仍要求 `admin` 角色。

## 7. Entry、Exit、Pass、Fail、Blocked 和 Invalid Criteria

**Entry（开始门）**：基线可解析（openapi + §7.8）；§5.2 就绪检查全过；B 类临时实例可启动；测试代码头部满足 TS-002。

**Exit（结束门）**：每个适用 Case 有明确状态；FAIL/BLOCKED/INVALID 均已登记；结果落 §10 报告；teardown 完成且初态可核验。

| 状态 | 判定 | 阻塞 release | 报告必含 |
|---|---|---|---|
| **PASS** | status + body 关键字段 + error `code`（+ SSE 序列/terminal/`[DONE]`）全 match | 否 | — |
| **FAIL** | 断言不符（含注入命中后行为不符） | **是** | 预期 vs 实际、`reproduction_cmd`、`failure_step` |
| **BLOCKED** | 测试代码/契约本身问题（fixture 写不出、断言逻辑错、ISD/OpenAPI 语义不清、注入无法命中） | **是** | `block_reason`、`required_resolution`、`reproduction_cmd` |
| **SKIP** | 环境限制（§5.2 不满足、上游离线、临时实例不可用） | 否（有上限） | `skip_reason`（引用 §5.2 项）、`fix_owner`、`eta` |
| **INVALID** | 注入未命中却按行为判定；或用 `127.0.0.1`/mock 冒充真实路径 | **是** | `invalid_reason`、证据缺口 |
| **NOT_RUN** | Case 已定义但本轮未执行，含 MISSING 实现（37 个） | 不适用 | 缺口引用（specification §3） |

**关键区分**：上游离线 → SKIP；fixture 写不出 → BLOCKED；status 对但字段缺 → FAIL。**SKIP 上限**：A 类 ≤ 5、B 类 ≤ 3；超出视为覆盖不足，须补 fixture/注入后重跑。**禁止"未跑"无状态**：runner 必须每项给明确结果。**跨 backend 隔离**：A 类 PASS 不关闭 B 类；静态 contract PASS 不关闭本计划。

## 8. 组织、职责、排期和资源

| 角色 | 职责 | 产物 |
|---|---|---|
| 测试设计（Case 作者） | 维护 specification §3 与 `at_*.py` 断言 | Case、fixture |
| 环境提供（m5air owner） | 部署、secret、OMLX、就绪检查 | §5.2 全绿 |
| 执行者 | 跑 A/B 班、teardown、记录 Run | Run 报告 |
| 见证/裁决 | BLOCKED/INVALID 裁决、回归门 | Gate 结论 |

排期沿用执行层计划阶段：P0 基线+conftest/runner → P1 A 类批量 → P2 B 类（临时实例）→ P3 首跑+报告 → P4（可选）CI。**冲突处理**：A/B 互斥同一实例；并发写测试独占 B 类，不与 A 类并行；MISSING 37 项的补实现优先于新增范围。

## 9. Defect、Deviation、Rerun 与 Regression

- **缺陷登记**：每个 FAIL/BLOCKED/INVALID 记 ID、Case、预期/实际、`reproduction_cmd`、根因、owner、状态。
- **偏差批准**：任何跳过/裁剪（如功耗 N/A、endurance 引用他文）须具名理由与批准，不得静默。
- **修复基线**：修复后必须回到同一基线重跑，并保留首轮失败与重测的关联（不覆盖旧失败）。
- **Rerun**：生成新 Run ID；非确定性 Case（并发/上游）重跑须记录并发度与时间窗。
- **Regression 邻域**：契约/错误码/路由变更 → 全量；单模块修复 → 本 family + 共享 `T-*`/`VRC-*` 的家族（如 Registry 改 → ADM-PROV/DEPL/SL + DP-MODELS/RESP/EMB 路由）；错误信封改 → 全部负向 Case。

## 10. Evidence、Traceability、Reporting 与 Gate

- **Run ID**：`<date>/<class>-<phase>`（如 `2026-09-28/A-api`、`2026-09-28/B-api`）。
- **原始证据**：命令、HTTP status/headers/body、SSE 逐帧、exit code、耗时、环境快照（`/healthz`/`/readyz` + provider/deployment 列表 + `api_smoke_test.py` 输出）。失败现场保留不截断。
- **保存位置**：`tests/system/reports/<date>/`；本计划的 Case ↔ Run 对应表随报告维护。
- **Traceability**：Case → spec §3 `设计 V`（`VRC-*`/`T-*`）→ openapi/§7.8/ISD；`ERR-*` 目录逐条映射 Case 或缺口。
- **Reporting/Gate**：报告须给出覆盖数（应跑/已跑/PASS/FAIL/SKIP/BLOCKED/INVALID/NOT_RUN）、未关闭缺陷、MISSING 缺口。**Gate**：适用 Case 全 PASS 且 FAIL/BLOCKED/INVALID=0、SKIP 在上限内方可放行；MISSING 记 NOT_RUN 缺口不自动阻断，但需具名批准。

## 11. 风险、安全与清理恢复

### 11.1 风险与停止阈值

| 风险 | 触发 | 停止/恢复 |
|---|---|---|
| 上游 provider 离线 | §5.2 检查失败 | 停止 DP-RESP/EMB，标 SKIP，待恢复重跑 |
| 写测试污染 m5air | teardown 失败或残留 | 停止 B 类；隔离实例；不得删除 m5air 既有资源 |
| 注入未清除 | 离开时 `GET /deployments/{id}/diagnostics` 非空 | 阻止下一轮；手动清空 `items:[]` |
| 临时实例不可终止 | 进程/端口未释放 | BLOCKED，保留证据，不做无边界清理 |
| 费用型外部调用 | 未确认即调 MiniMax/probe/usage-refresh | 立即停止；必须显式 `confirm_external_call` |

### 11.2 安全

- 真实 Secret 绝不出现在日志/审计/证据；脱敏断言显式检查不含 `9832` 与 key 文件内容。
- `dev-data`/`dev-admin`/`9832` 为本地开发凭据，不作为"秘密"证据对象。
- 管理面未授权不得泄露资源存在性。

### 11.3 清理与可重复性

- A 类每个写 Case teardown（恢复原名/删除创建物）；B 类整班销毁临时实例与临时 SQLite；注入 Case 清空 items。
- 清理后下一轮可核验初态（§5.2 + `/readyz`）；不得删除用户 usage 或其他任务数据。
- 测试进程退出 ≠ 设备停止：B 类须显式 `terminate` 并等待。

### 11.4 历史踩坑回归检查（执行前逐项确认已修复）

| ID | 问题 | 关联 Case | 验证方式 |
|---|---|---|---|
| P1 | 用 `127.0.0.1`（违反 TS-003） | 全部 DP | §5.2/§5.3 强制 LAN IP；TS-002 头部 |
| P2 | provider endpoint 未指向 m5mac/m5air | DP-RESP/EMB | §5.3 路由矩阵 |
| P3 | 上游健康不可知 → 跑一半 500 | DP-RESP-01~04、ADM-PROBE-02 | §5.2 OMLX 双机检查 |
| P4 | `secret_ref` 三格式（`file:`/`env:`/`raw:`）差异未测 | ADM-PROV-02/12 | 保留缺口（现只测 `file:`） |
| P5 | `capabilities` 缺字段 → 400 | ADM-DEPL-02/06/07 | §6 12 键全集 |
| P6/API-001 | 412 缺 `current_version` | ADM-PROV-06 | §6 If-Match 段 |
| P7 | If-Match ETag 格式未文档化 | 所有 PATCH/DELETE | §6 If-Match 段 |
| P8 | 时间参数 RFC3339 缺失 | DP-USAGE-*、ADM-USAGE-* | §6 时间参数段 |
| P9 | create 多传 `id` | ADM-PROV-02 | schema `additionalProperties:false` |
| P10 | grep `"error"` 误匹配 `"error":null` | ADM-PROBE-02、并发 | §6 并发段（JSON 解析） |
| P11/FD-001 | FD 泄漏 | 不在本计划 | 引用 `llmtier-test-plan.md` ST-18/19 |
| P12 | 50% BLOCKED 当失败 | 全局 | §7 六状态判定；SKIP 上限 |
| P13 | 测试头部未写依赖（TS-002） | 全部 Case | §5.5/specification §2 |
| P14 | DP-RESP-02 期望错（`stream=false` 必拒） | DP-RESP-02/06 | specification §3 |
| P15 | 诊断面误用 `from`/`to` | OBS-STATS-02 | §6 时间参数段（`since`/`until`） |
| P16 | 别名与扁平路径不等价 | OBS-ALIAS-01..04 | §6 别名段 |
| P17 | provider-models 触上游未记录 | ADM-PROV-MODELS-01/02 | §6 confirm 段 |
