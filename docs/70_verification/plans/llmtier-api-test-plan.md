<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 API Test Plan

> STD 使用入口：[项目采用说明与标准导航](../../00_management/standards/README.md)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-api-test-plan` |
| Document Version | `0.3.0-draft.11` |
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
| Gate Owner | 待填（执行负责人） |
| Gate Approver | 待填（见证/裁决） |
| Gate Approval Date | 待填（ISO-8601） |

> Reviewer、Approver、Approval Date、Gate Owner/Approver/Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. 目标、范围与测试层级

本文件是 LLMTier V0.3 **HTTP API 专项测试计划的执行层**：只规定 **Case 如何被执行**——执行顺序、批次分组、执行流程、进入/退出与判定门、证据采集、复位、缺陷与回归。**它不承载逐 Case 的输入/预期/Oracle/证据/清理**；那些在 case 详细设计文档。

**测试层级**：系统级 / 接口级（system / interface contract of a running LAN service）。不使用单元测试或静态契约验证冒充本层结论；反之，本层 PASS 也不证明静态契约或单元逻辑正确。

**文档链与职责（测试设计 → case 设计 → case 脚本；本计划 = 执行）**

| 层 | 文档 / 产物 | 职责 |
|---|---|---|
| 测试设计 | [`llmtier-api-test-specification.md`](../specifications/llmtier-api-test-specification.md) | Case 清单/命名/分类（§3.2）、每 case 设计契约（§3.3）、共同机制（§4）、环境与前置（§2） |
| case 设计 | [`cases/<lowercased-case-id>.md`](../specifications/cases/README.md)（一 Case 一文件） | 逐 Case 12 字段详细设计：输入/执行/Oracle/判定/证据/清理 |
| case 脚本 | `tests/system/api_test_v03/at_*.py`、`tools/inference_smoke.py` | 可执行断言 |
| **执行（本文件）** | `llmtier-api-test-plan.md` | 顺序/批次/流程/门禁/证据/复位/回归 |
| 相邻层 | `llmtier-test-plan.md`、`llmtier-contract-test-specification.md`、`llmtier-vv-plan.md`、[`llmtier-api-test-execution.md`](./llmtier-api-test-execution.md) | 系统测试、静态契约、V&V、阶段/工时/产出物 |

> **父文档说明（`parent_document_id`）**：文档链上的**功能父对象**是测试设计 `llmtier-api-test-specification`（§3.2 权威 Case 清单、§2 环境、§4 共同机制）。但 STD `parent_document_id` 只接受**设计文档**（`design.*`）为父，指向 `assurance.test-specification` 会触发 `hierarchy.parent-type`，故本计划 `parent_document_id` 保持 `llmtier-system-design`（与同链的 spec/execution 元数据一致），功能父关系以本节表格与正文引用表达。

**被测范围**：全部对外路由——Data Plane（`POST /v1/responses`(SSE)、`POST /v1/embeddings`、`GET /v1/models`、`GET /v1/models/{model}`）、Usage（`GET /v1/usage`、`DELETE /v1/usage`）、Management（`/v1/providers(/{id})`、`/v1/providers/{id}/usage`、`/v1/providers/{id}/models`、`/v1/deployments(/{id})`、`/v1/service-levels(/{id})`、`POST /v1/probes`、`/v1/runtime`、`/v1/stats`、`/v1/audit`、`/v1/logs`）、Observability（`/v1/diagnostics(+/snapshots|/stats|/traces)`、`/v1/deployments/{id}/diagnostics`、`/v1/trace/{request_id}`）、No-auth（`/healthz`、`/readyz`）、Alias（`/tier/admin/v1/*`）。

**不在本计划范围**：Web UI、FD 资源泄漏、SQLite 持久化文件格式、auth mock 单元测试、静态契约验证、性能 SLO 校准（分别由 `llmtier-test-plan.md` ST-18/19/21、contract specification、unit 承接）。

**Case 总数**：140（RUN 88 / MISSING 52；A 89 / B 51；P0 45 / P1 72 / P2 23）。执行通过标准：**适用 Case**（§7.2）全 PASS；MISSING 记为 NOT_RUN 缺口而非跳过，**P0 MISSING 阻断**（§7.2/§10）。**权威清单**见测试设计 §3.2（计数以该处为准，测试设计升版时本节随之回填）；**每个 Case 的预期/Oracle**见 `cases/<lowercased-case-id>.md`（§3.3 契约）。

## 2. 被测基线、排除项与依赖

**固定基线（可复查来源与版本）**

| 类别 | 基线 | 变化时的重跑范围 |
|---|---|---|
| 机器契约 | `interfaces/openapi/llmtier.openapi.json`（OpenAPI 3.1.0；`BearerAuth`/`AdminBearerAuth`；`x-llmtier-contract-aliases`） | 全部路由/schema 相关 Case |
| 错误目录 | 系统设计 §7.8（`<!-- STD_PUBLIC_ERROR_CATALOG_BEGIN -->`，`ERR-*` 八字段） | 全部负向 Case |
| 数据/行为 | `llmtier-system-design.md` §5–§7、§11 | 对应机制 Case |
| 接口控制（ISD） | `piko-data-plane-control.md`、`slinky-capacity-observation-control.md`、`llmtier-management-control.md` | 对应接口成员 Case |
| 机制 | `mechanisms/{inference-stream,access-trust,usage-metering,observability,config-lifecycle}.md` | `T-*`/`VRC-*` 映射 Case |
| case 设计 | `docs/70_verification/specifications/cases/<lowercased-case-id>.md`（per §3.3） | 该 Case 的输入/Oracle 变更时只重跑该 Case |
| 测试规范 | `testing-standard.md`（TS-002 依赖头部、TS-003 LAN IP） | 全部 Case |
| 项目标准 | `docs/std.lock.json`（STD `0.1.0-draft.41`） | 文档质量门 |
| 代码 | 当前 `main` 工作树（m5air 部署版本） | 全量 |

**排除项与依据**：FD/耐久/性能压测排除（`llmtier-test-plan.md` §2.2 已定 m5air 不适合污染性 Case）；外部 MiniMax 返回内容排除（费用与不确定性，A 类只验 HTTP 200）；Web UI 认证（无浏览器 SSO，由 `llmtier-test-plan.md` 独立承接）。

**依赖**：m5air OMLX `192.168.1.9:9000`、m5mac OMLX `192.168.1.8:9000`（Bearer `9832`）；B 类临时实例依赖 Python 3.14 + 可用临时端口 + 临时 SQLite 权限。**依赖不可用 → BLOCKED/SKIP**（见 §7）。

## 3. Test Strategy 与执行模型

**本节定位**：只描述**如何执行**（执行分层、批次、顺序、流程）；Case 的契约与预期见测试设计 §3 与 `cases/<id>.md`，本节不复制断言内容。

**导出方式**：从机器契约（openapi 路由/方法/securitySchemes）+ 错误目录（§7.8）+ 机制可验证断言（`T-*`/`INV-*`）导出 Case；再用**状态与风险**补负向、边界、并发、恢复路径。覆盖模型必须能发现**孤儿需求**（有 Rule 无 Case）与**未测失败路径**（有 error code 无 Case）。覆盖证据 = 测试设计 §3.2 的 `设计 V` 列。

### 3.1 三层职责边界

- **测试设计**定义"有哪些 Case、共同机制、环境"——唯一 Case 清单与命名分类。
- **case 设计**定义"每个 Case 的输入/执行/Oracle/判定/证据/清理"——一 Case 一文件。
- **case 脚本**实现断言；**本计划**只安排它们的**运行顺序与批次**，不复制断言内容，也不内联 per-case 预期。

### 3.2 A/B 两类执行模型

| 类 | 范围 | 执行方式 | case 数 |
|---|---|---|---|
| **A — 读/观察/无状态写** | HEALTH、DP-MODELS/RESP/EMB/USAGE 的读、全部 GET、PROBE-01/02、PROV-USAGE、审计/日志/运行态/统计、AUTH | 直接打 m5air 现有实例 | 88 中的 A 子集 |
| **B — 写/空库/无鉴权/注入** | provider/deployment/service-level POST/PATCH/DELETE、`_EMPTY_SETTINGS`、`_NO_AUTH_SETTINGS`、OBS-DEPL 注入、并发/故障注入 | 临时 SQLite + 临时端口启新实例（同机第二进程），teardown 销毁 | 88 中的 B 子集 |

**B 类为何用临时实例**：写操作若直接在 m5air 跑会因 ID 冲突/状态累积而不稳定（9-20 ST-13 DELETE 未清理污染 ST-14）；临时实例 = 干净起点。**A 类为何直连 m5air**：读操作无状态影响，且 m5air 已有完整 provider/deployment 现成 state。**A 与 B 不共享 SQLite/进程，且不并行。**

### 3.3 批次分组（按环境类与端点族）

批次是**执行分组**，不是 Case 定义；每个 Case 的精确 A/B 归属以测试设计 §3.2 的 `A/B` 列为准。

| 批次 | 环境 | 选择规则（端点族 + 类） | 执行入口 |
|---|---|---|---|
| `A-gate` | A | 无认证健康/就绪（`/healthz`、`/readyz`） | `pytest_configure`（整班门） |
| `A-data` | A | Data Plane 读/无状态写：`/v1/models`、`/v1/responses`、`/v1/embeddings`、`/v1/usage` 的 A 类 Case | `runner_a.sh` |
| `A-mgmt` | A | Management/观测读 + 无状态写：providers/deployments/service-levels/probes/runtime/stats/audit/logs、OBS 读、AUTH 的 A 类 Case | `runner_a.sh`（写后即 teardown） |
| `A-alias` | A | `/tier/admin/v1/*` 读别名（OBS-ALIAS-01..03） | `runner_a.sh` |
| `B-empty-noauth` | B | 空库/无鉴权：`/readyz` 无 deployment、未配置鉴权 | `runner_b.sh`（串行） |
| `B-crud` | B | 管理 CRUD + Data Plane 负向：providers/deployments/service-levels、probe/inject 写 | `runner_b.sh`（串行） |
| `B-inject` | B | 故障注入/并发/恢复：`/v1/deployments/{id}/diagnostics` + `/v1/responses` 异常 | `runner_b.sh`（注入链配对） |
| `B-alias` | B | `/tier/admin/v1/deployments/{id}/diagnostics` 写别名 | `runner_b.sh`（串行） |

### 3.4 执行顺序（依赖驱动）

1. **门禁**：先跑 §2.1 就绪检查（`pytest_configure` 5 项）。不通过 → 整班 BLOCKED/SKIP，**停止**后续批次，不得改用模拟路径。
2. **先 A 后 B**：A 类（只读/无状态写）先跑；同一实例上 A、B 互斥且不并行；A 类每个写 Case 立即 teardown。B 类每班启临时实例、串行执行、跑完销毁。
3. **A 内部顺序**：`A-gate` → `A-data`（models → responses → embeddings → usage 读）→ `A-mgmt`（读 → 无状态写）→ `A-alias`。
4. **B 内部顺序**（串行）：启动临时实例 → `B-empty-noauth` → `B-crud`（CRUD 链：create → read → patch/delete，按资源依赖）→ `B-inject`（写注入 → 命中 → 清空）→ `B-alias` → `stop()` + 清理临时目录。
5. **依赖边**：每个 Case 的前置、跨 Case 依赖（如"先注入/先建资源/先有 usage 记录"）与清理复位**只在其 `cases/<lowercased-case-id>.md` 的"依赖"与"清理与复位"字段维护**，本计划不复制。执行前按该字段排程；依赖链前置未满足 → 该 Case 标 `SKIP`（§7.2）并在续跑时按依赖顺序补跑（§7.1）。
6. **禁止**：A/B 并行、并发写与 A 类并行、未复位就进入下一 Case。

### 3.5 执行流程（环境就绪 → 部署/启动 → 跑批次 → 收证据 → 复位）

1. **环境就绪**：开发机执行 §2.1 的 5 项检查（`/healthz`、`/readyz` 7 tier、m5air OMLX、m5mac OMLX、`provider_omlx_m5mac` secret）；由 `pytest_configure` 自动执行。任一失败 → 整班 SKIP/BLOCKED。
2. **部署 / 启动待测版本**：A 类 m5air 已部署，如需更新按测试设计 §2.5（`rsync` → 查旧进程/端口 → `kill -TERM` → Python 3.14 重启 → `/healthz` 验证 → 确认无残留）；B 类由 `LLMTierInstance` fixture 起临时实例（临时端口 + 临时 SQLite + 每 run settings，`start()` 轮询 `/healthz`）。
3. **跑批次**：按 §3.3/§3.4 顺序执行——全量 `PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/ -q`；A/B 分跑 `bash tests/system/api_test_v03/runner_a.sh` / `runner_b.sh`；Data Plane smoke `python3 tools/inference_smoke.py --base http://192.168.1.9:8181`（smoke 只验建连/骨架，不替代逐 Case 断言）。
4. **收证据**：记录命令、exit code、HTTP status/headers/body、SSE 逐帧、注入命中证据（trace `source=injected`）、环境快照；Run ID `<date>/<class>-<phase>`；落 §10 位置，失败现场不截断。
5. **复位**：A 类每个写 Case teardown、注入 `items:[]` 清空、`DP-USAGE-04` 复位 `query_snapshots.expires_at`；B 类整班 `stop()` 终止进程并 `rm -rf` 临时目录。核验 `/readyz` 与 provider/deployment 列表回到基线、无遗留端口监听、无未清空注入。
6. **判定与登记**：按 §7 为每个执行项给出 PASS/FAIL/BLOCKED/SKIP/INVALID/NOT_RUN；FAIL/BLOCKED/INVALID 登记缺陷并保留现场，不得把未运行项补造为成功。

### 3.6 断言策略与定量覆盖模型

**断言策略（引用，不展开）**：先建连/状态码 → 再验 body 关键字段与 error `code` → SSE 另验事件序列/唯一 terminal/`[DONE]`；禁止"HTTP 200 即 PASS"。拒绝用例交叉核对**零副作用**（usage/runtime/trace）；注入用例必须**证明命中**。逐 Case 断言见 `cases/<lowercased-case-id>.md`；共同机制常量见测试设计 §4（错误信封 §4.6、SSE §4.5、管理/配置常量 §4.10）与 §5/§6。

**定量覆盖模型（四维，非"有 Case 即覆盖"）**：对 `路由 × 方法 × 角色 × 错误码` 四维各自设下限并计数；覆盖证据 = 测试设计 §3.2 `设计 V` 列 + 下列矩阵 + §3.6.2 的 `ERR-*` 表。任一下限不满足即记覆盖缺口（非静默）。

1. **路由 × 方法**：每条 openapi 路由的每个对外方法 ≥1 正常 Case + ≥1 负向 Case。
2. **角色**：`none`（公共）/`data`/`admin` 三类各 ≥1 AUTH Case，含 LAN trust 无 token 与未配置鉴权。
3. **错误码**：系统设计 §7.8 每个 `ERR-*` ≥1 映射 Case，或登记**具名缺口**（缺口=有目录无 Case，需 owner/ETA，不自动阻断但计入 Gate 报告）。
4. **状态码**：每个出现的 4xx/5xx 状态（400/401/403/404/409/412/413/429/502/503）≥1 Case。

#### 3.6.1 路由 × 方法 × 角色覆盖矩阵

| 路由 | 方法 | 角色 | 正常 Case | 负向 / 错误 Case | 覆盖 |
|---|---|---|---|---|---|
| `/healthz` | GET | none | HEALTH-01 | AUTH-05 | ✅ |
| `/readyz` | GET | none | HEALTH-02 | HEALTH-03/04/05/06 | ✅ |
| `/v1/models` | GET | data | DP-MODELS-01/07 | DP-MODELS-03/04/05/06 | ✅ |
| `/v1/models/{model}` | GET | data | DP-MODELS-02 | DP-MODELS-03/04/05/06 | ✅ |
| `/v1/responses` | POST | data | DP-RESP-01/03/06/10/12/13/14/15 | DP-RESP-02/05/07/08/09/11/16/17/18/19/20/21 | ✅ |
| `/v1/embeddings` | POST | data | DP-EMB-01/02/03/05 | DP-EMB-04/06/07 | ✅ |
| `/v1/usage` | GET | data/admin | DP-USAGE-01/02/03、ADM-USAGE-01/02 | DP-USAGE-04/05/06 | ✅ |
| `/v1/usage` | DELETE | admin | ADM-USAGE-03 | ADM-USAGE-03（角色边界） | ✅ |
| `/v1/providers` | GET/POST | admin | ADM-PROV-01/02 | ADM-PROV-11/12、AUTH-03/09 | ✅ |
| `/v1/providers/{id}` | GET/PATCH/DELETE | admin | ADM-PROV-03/05/08/13 | ADM-PROV-04/06/07/09/10 | ✅ |
| `/v1/providers/{id}/usage` | GET/POST | admin | ADM-PROV-USAGE-01/03 | ADM-PROV-USAGE-02 | ✅ |
| `/v1/providers/{id}/models` | GET | admin | ADM-PROV-MODELS-01 | ADM-PROV-MODELS-02 | ✅ |
| `/v1/deployments` | GET/POST | admin | ADM-DEPL-01/02 | ADM-DEPL-06/07/08 | ✅ |
| `/v1/deployments/{id}` | GET/PATCH/DELETE | admin | ADM-DEPL-03/04/05 | ADM-DEPL-09 | ✅ |
| `/v1/service-levels` | GET/POST | admin | ADM-SL-01（bootstrap） | ADM-SL-02/02b | ✅ |
| `/v1/service-levels/{id}` | GET/PATCH/DELETE | admin | ADM-SL-03/04 | ADM-SL-04b/05/06/07 | ✅ |
| `/v1/probes` | POST | admin | ADM-PROBE-02 | ADM-PROBE-01/03 | ✅ |
| `/v1/runtime` | GET | admin | ADM-RUNTIME-01 | — | ⚠️ 无负向（只读快照） |
| `/v1/stats` | GET | admin | ADM-STATS-01/02 | ADM-STATS-03 | ✅ |
| `/v1/audit` | GET | admin | ADM-AUDIT-01/02 | — | ⚠️ 分页边界即负向（cursor） |
| `/v1/logs` | GET | admin | ADM-LOGS-01 | ADM-LOGS-02 | ✅ |
| `/v1/diagnostics` | GET/PATCH | admin | OBS-DIAG-01/02 | OBS-DIAG-03 | ✅ |
| `/v1/diagnostics/snapshots` | GET | admin | OBS-SNAP-01 | OBS-SNAP-02 | ✅ |
| `/v1/diagnostics/stats` | GET | admin | OBS-STATS-01 | OBS-STATS-02 | ✅ |
| `/v1/diagnostics/traces` | GET | admin | OBS-TRACE-01 | OBS-TRACE-02 | ✅ |
| `/v1/deployments/{id}/diagnostics` | GET/PATCH | admin | OBS-DEPL-01/02 | OBS-DEPL-03/04 | ✅ |
| `/v1/trace/{request_id}` | GET | admin | OBS-REQTRACE-01 | OBS-REQTRACE-02 | ✅ |
| `/tier/admin/v1/*`（6 条别名） | GET/PATCH | admin | OBS-ALIAS-01/02/03/04 | AUTH-08 | ✅ |

**计数口径**：路由=28 条（含别名族）；`⚠️` 行为已知覆盖缺口，须在 §10 报告具名登记（`/v1/runtime` 纯只读、`/v1/audit` 负向由分页 cursor 承接）。

#### 3.6.2 `ERR-*` → Case / 具名缺口

`ERR-*` 取自系统设计 §7.8（八字段目录）；`具名缺口` = 目录有码、当前 Case 清单无映射，须在 §10 报告登记 owner/ETA。

| Error ID | 映射 Case | 状态 |
|---|---|---|
| ERR-REQ-VALIDATION | DP-RESP-08、DP-EMB-07、DP-USAGE-05、ADM-PROV-11、ADM-DEPL-06/07/08、ADM-SL-02/04b、ADM-STATS-03、ADM-LOGS-02、OBS-DIAG-03、OBS-STATS-02 | ✅ |
| ERR-REQ-UNSUPPORTED | DP-RESP-02、DP-RESP-07 | ✅ |
| ERR-REQ-FIELD | DP-RESP-09 | ✅ |
| ERR-REQ-MODEL | DP-RESP-17 | ✅ |
| ERR-REQ-JSON | DP-RESP-16 | ✅ |
| ERR-REQ-TOO-LARGE | DP-RESP-18 | ✅ |
| ERR-REQ-DIM | DP-EMB-06 | ✅ |
| ERR-AUTH-REQUIRED | 缺凭据 401 未被 AUTH-02/06（403）覆盖 | ⚠️ 具名缺口 |
| ERR-AUTH-DENIED | AUTH-02/03/06/08/09 | ✅ |
| ERR-AUTH-NOCFG | AUTH-07 | ✅ |
| ERR-MODEL-NOTFOUND | DP-MODELS-03/04/05/06、DP-RESP-05 | ✅ |
| ERR-NOTFOUND | DP-EMB-04、ADM-PROV-04、ADM-PROV-MODELS-02、ADM-PROBE-03、OBS-DEPL-03、OBS-REQTRACE-02、ADM-DEPL/SL 相应 404 | ✅ |
| ERR-CONFLICT | ADM-SL-02b | ✅ |
| ERR-CAPABILITY | ADM-SL-06 | ✅ |
| ERR-EMBEDDING-SPACE | ADM-SL-07 | ✅ |
| ERR-FIXED-LEVEL | ADM-SL-05 | ✅ |
| ERR-INUSE | ADM-PROV-10 | ✅ |
| ERR-STALE | ADM-PROV-06/07/09、ADM-DEPL-04/09、ADM-SL-04 | ✅ |
| ERR-CURSOR | DP-USAGE-04、OBS-SNAP-02、OBS-TRACE-02 | ✅ |
| ERR-RATE-LIMIT | DP-RESP-20 | ✅ |
| ERR-PROVIDER-UNAVAIL | `fault_503` 扩展（测试设计 §6）未落 Case | ⚠️ 具名缺口 |
| ERR-PROVIDER-FAIL | `fault_503`/上游 error（测试设计 §6）未落 Case | ⚠️ 具名缺口 |
| ERR-PROVIDER-INJECTED | DP-RESP-11 | ✅ |
| ERR-PROVIDER-SECRET | `secret_ref` 不可用路径未落 Case | ⚠️ 具名缺口 |
| ERR-PROVIDER-CONTRACT | 上游契约错误路径未落 Case | ⚠️ 具名缺口 |
| ERR-MODEL-UNAVAIL | DP-RESP-19 | ✅ |
| ERR-STORE | store 不可用路径未落 Case | ⚠️ 具名缺口 |
| ERR-INTERNAL | 入口兜底；无故障注入路径 | ⚠️ 具名缺口 |
| ERR-BOOT | HEALTH-05 | ✅ |
| ERR-SCHEMA | 由 §7.1.2 恢复手册覆盖（非运行 Case） | ✅（执行层） |
| ERR-PATH-UNSAFE | 启动路径不安全未落 Case | ⚠️ 具名缺口 |
| ERR-UTIL-TXN | 嵌套事务路径未落 Case | ⚠️ 具名缺口 |
| ERR-INJECTION | OBS-DEPL-04 | ✅ |
| ERR-CONFIRM | ADM-PROBE-01、ADM-PROV-USAGE-02 | ✅ |

**覆盖门（定量）**：§3.6.1 每行"覆盖=✅"；§3.6.2 非具名缺口项均有映射；具名缺口逐条进 §10 报告（owner/ETA），其中 `ERR-AUTH-REQUIRED` 与 `ERR-PROVIDER-UNAVAIL/FAIL` 若升为 P0 则按 §10 Gate 阻断。覆盖证据 = 测试设计 §3.2 `设计 V` 列 + 本矩阵。**测试设计升版新增 `ERR-*`/Case 时以 §3.2 为准并回填本节。**

## 4. Test Item、Feature 与 Requirement Matrix

本矩阵只**索引**，不替代逐 Case 设计与判据；逐 Case 输入/Expected/Oracle 见 `cases/<lowercased-case-id>.md`。

| Feature / 子系统 | Requirement / 设计 V | 层级 | 责任模块 | 验证方法 | Case 家族（测试设计 §3.2） |
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

**执行机 = 开发机**（与测试设计 §2.7/§8 一致）：在项目根目录运行 `pytest` 与 `tools/inference_smoke.py`；`cwd = "$(git rev-parse --show-toplevel)"`，`PYTHONPATH=src`。

- **A 类**：执行机经 LAN 连**被测目标机 m5air**（`192.168.1.9:8181`）现有实例；m5air 不是执行机。
- **B 类**：执行机本机起临时实例（临时端口 + 临时 SQLite，`127.0.0.1:<port>`；loopback 仅客户端→LLMTier，见测试设计 §2.7）。
- 上游：m5air OMLX `192.168.1.9:9000`、m5mac OMLX `192.168.1.8:9000`。
- **TS-003：被测服务内部的上游 provider endpoint 必须使用 LAN IP（`192.168.x.x`），禁止 `127.0.0.1`。**

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
| Embedding-v1 | 固定 `provider_local` | `http://192.168.1.9:9000/v1` | bge-m3 | Bearer 9832 |

**本矩阵只固定上游路由与 TS-003 LAN IP 约束，不承载断言。** 逐 Case 的输入/预期/Oracle（含维度、SSE 序列、内容策略、费用确认）见测试设计 §3.2/§4.10 与对应 `cases/<lowercased-case-id>.md`；`provider_minimax` 等外部费用调用按 §11.2 与测试设计 §11 处理。

### 5.4 fixture 与基线状态

- **A 类基线（m5air 现有 state）**：3 provider / 4 deployment / 7 fixed tier（§5.2）。
- **B 类 fixture（`tests/system/api_test_v03/conftest.py` 的 `LLMTierInstance`，session-scope）**：`_BASELINE_SETTINGS`（`prov_b` + `depl_b` + 7 tier，用于 CRUD/注入）、`_EMPTY_SETTINGS`（空库）、`_NO_AUTH_SETTINGS`（无鉴权）；每 run 写临时 `settings.json` 并置 `LLMTIER_SETTINGS`。
- **凭据**：`LLMTIER_DEV_MODE=1` → `dev-data`/`dev-admin`；上游 OMLX Bearer `9832`。

fixture 语义、字段与常量见测试设计 §4.4/§4.10；逐 Case 的种子/输入/预期见 `cases/<lowercased-case-id>.md`。本计划不复制断言。

### 5.5 数据与工具

| 工具 | 用途 | 备注 |
|---|---|---|
| `tests/system/api_test_v03/at_*.py` | Case 实现（`at_<family>_<seq>.py`） | `HEALTH-*` 由 `at_obs_01..03.py` 承接 |
| `tests/system/api_test_v03/{runner_a.sh,runner_b.sh}` | A/B 类批量执行 | B 类串行 |
| [`tools/inference_smoke.py`](../../../tools/inference_smoke.py) | Data Plane 端到端 smoke：`/healthz` + `POST /v1/responses`(SSE 骨架) + `POST /v1/embeddings`(float/base64) | **不替代** 逐 Case 断言；默认 `--base http://192.168.1.9:8181` |
| `tools/api_smoke_test.py` | 全端点 status-only smoke | 只验建连，不验 body 字段 |
| `tests/fixtures/v03_fake_provider.py` | 本地假上游（无外部依赖） | provider endpoint 用 LAN IP |
| `tests/integration/v03_smoke.py` | 集成冒烟 | |
| `docs/70_verification/specifications/cases/*.md` | 逐 Case 详细设计（输入/Oracle/判定） | 设计层，不是脚本 |
| `sqlite3` 直连状态库 | 仅用于需直接构造 DB 状态的 Case（具体见该 Case 的 `cases/<lowercased-case-id>.md`） | 需权限；A 类需记录原值并复位（§7.1.7、§11.3） |

## 6. Test Types 与 Case Families

覆盖类型：**normal、boundary、negative、concurrency、recovery、security、performance、endurance**（endurance 引用 `llmtier-test-plan.md` ST-19，不重复）。下表只把类型**映射到执行批次**（覆盖分配），**不承载任何断言/预期**。

逐 Case 的输入、预期与 Oracle 见对应 `cases/<lowercased-case-id>.md`；共同断言与机制基线见测试设计 §4.5（SSE）、§4.6（错误信封）、§4.10（配置常量）与 §5/§6（正常/边界/负向/并发/恢复）。本计划不复制。

| 类型 | 覆盖分配（Case 家族） | 执行批次 |
|---|---|---|
| normal | DP-RESP、DP-EMB、ADM-* CRUD、HEALTH、OBS-DEPL 正常流 | A-data / A-mgmt / B-crud |
| boundary | DP-MODELS、DP-RESP、DP-EMB、DP-USAGE、ADM-AUDIT/USAGE、OBS-DEPL | A-data / A-mgmt / B-inject |
| negative | DP-RESP、DP-EMB、ADM-* 4xx、AUTH | A-data / B-crud / B-empty-noauth |
| concurrency | DP-RESP、ADM-PROV、ADM-PROBE | B-inject / A-mgmt |
| recovery | DP-RESP、OBS-DEPL、流终止/畸形事件 | B-inject |
| security | ADM-AUDIT/LOGS、AUTH、OBS-ALIAS | A-mgmt / A-alias / B-alias |
| performance | DP-RESP 时序/准入 | A-data / B-inject |
| endurance | —（引用 ST-19） | 不在本计划 |

## 7. Entry、Exit、Pass、Fail、Blocked 和 Invalid Criteria

### 7.1 执行韧性与恢复手册（阻塞 → 恢复 → 续跑）

本节是整轮执行的**权威恢复手册**（continue-on-error），是 §9 续跑/回归与 §11 清理恢复在执行层的统一语义；测试设计只定义判定状态（测试设计 §9），执行编排以本节为准。每项恢复动作给出**可运行命令**或**可定位的配置旋钮**；不得只写"重试/修复"。

#### 7.1.0 前置就绪检测（命令 + 失败动作）

在**开发机**（执行机，§5.1）执行；前 5 项由 `tests/system/api_test_v03/conftest.py::pytest_configure` 自动执行。任一失败 → 整班 BLOCKED/SKIP，**不得**改跑模拟路径。

| 检查 | 命令（开发机） | 期望 | 失败动作 |
|---|---|---|---|
| healthz | `curl -fsS http://192.168.1.9:8181/healthz` | 200，`{"status":"ok",...}` | A 类按 §7.1.2 重启；仍失败 → 整班 BLOCKED |
| readyz | `curl -fsS http://192.168.1.9:8181/readyz` | 200，含 7 fixed tier | 无/非 healthy tier → 查 bootstrap；A 类 BLOCKED |
| m5air OMLX | `curl -fsS -H 'Authorization: Bearer 9832' http://192.168.1.9:9000/v1/models` | 200 | 受影响 DP 批次 SKIP（§7.1.5 上游超时） |
| m5mac OMLX | `curl -fsS -H 'Authorization: Bearer 9832' http://192.168.1.8:9000/v1/models` | 200 | 同上 |
| secret | `curl -fsS -H 'Authorization: Bearer dev-admin' http://192.168.1.9:8181/v1/providers/provider_omlx_m5mac` | `has_secret=true`，`secret_ref` 为 `file:` | 修 `secret_ref` 为 `file:` + `chmod 600` 后重启（§7.1.2） |
| schema_version | `ssh m5air "sqlite3 /Users/mlp/LLMTier-dev/state.sqlite3 'SELECT schema_version FROM schema_meta WHERE singleton=1'"` | `2`（`src/util/store.py` `EXPECTED_SCHEMA_VERSION`） | 不匹配 → §7.1.2 **显式二选一**（重建 / 离线迁移） |
| tokens | `curl -fsS -o /dev/null -w '%{http_code}' -H 'Authorization: Bearer dev-admin' http://192.168.1.9:8181/v1/providers` | `200` | 非 200 → 核对服务端 `LLMTIER_ADMIN_TOKEN=dev-admin`/`LLMTIER_DATA_TOKEN=dev-data`（LAN trust 对 RFC1918 来源自动生效，无需 `LLMTIER_TRUSTED_LAN_MODE`），按 §7.1.2 重启 |

#### 7.1.1 单 case 受阻 → 就地恢复后继续

1. **不中断整轮**：任何 case 无法执行（前置不满足、超时、阻塞）时，将该 case 标为 `BLOCKED`（可重试）或 `SKIP`（明确不适用/依赖失败），登记**检测事实 + 原因 + 对应恢复动作**；执行 §7.1.5 的**就地恢复动作**后，**直接继续下一个 case**（同类/同批其余 case 继续跑），不回退、不整体中断。
2. **一路执行到底**：整轮 continue-on-error；批次之间、case 之间只要前置满足就继续，直到跑完全部 case。
3. **依赖感知跳过**：若某 case 的前置（各 `cases/<lowercased-case-id>.md` 的"依赖"字段）未 PASS，该 case 标 `SKIP`（非 FAIL/BLOCKED），并在续跑时按依赖顺序补跑。

#### 7.1.2 A 类恢复（m5air 已部署实例）

**重启（kill → Python 3.14 → 验证）**：

```bash
ssh m5air 'pid=$(cat /Users/mlp/LLMTier-dev/llmtier.pid); kill -TERM "$pid"'
ssh m5air "/usr/sbin/lsof -nP -iTCP:8181 -sTCP:LISTEN"   # 端口应无监听
ssh m5air "cd /Users/mlp/LLMTier-dev && \
  LLMTIER_ADMIN_TOKEN=dev-admin LLMTIER_DATA_TOKEN=dev-data \
  PYTHONPATH=src /usr/local/bin/python3 -m http_api --host 0.0.0.0 --port 8181 \
  --database /Users/mlp/LLMTier-dev/state.sqlite3 >> /Users/mlp/LLMTier-dev/llmtier.log 2>&1 &"
curl -fsS http://192.168.1.9:8181/healthz && curl -fsS http://192.168.1.9:8181/readyz
```

> 启动命令/解释器/环境变量以 `m5air-deploy-guide.md` 与 `m5air-operations-manual.md` 为权威（测试设计 §2.5 镜像）；**`LLMTIER_TRUSTED_LAN_MODE` 不在源码读取范围**，不要传入。

**schema/版本不匹配（`schema_version_mismatch` / `schema_unknown` / 启动 503）→ 显式二选一**（`src/util/store.py` 为 init-only，无在线 upgrade/downgrade/auto-repair）：

- **A) Fresh-DB rebuild（丢弃重建）**：冷停 → 备份并移走旧 DB → 空库首启用一次性 `--settings` 重建 → 验证。
  ```bash
  ssh m5air 'pid=$(cat /Users/mlp/LLMTier-dev/llmtier.pid); kill -TERM "$pid"'
  ssh m5air "cp /Users/mlp/LLMTier-dev/state.sqlite3 /Users/mlp/LLMTier-dev/state.sqlite3.\$(date +%s).bak"
  ssh m5air "mv /Users/mlp/LLMTier-dev/state.sqlite3 /Users/mlp/LLMTier-dev/state.sqlite3.rebuild"
  # 按 §7.1.2 重启命令追加 --settings config/settings.json（仅空库首启有效）
  ```
- **B) Offline migration（离线迁移，保留数据）**：冷停 → 保全日志+DB → 用迁移 SQL 将 `schema_version` 带到 `EXPECTED_SCHEMA_VERSION=2`，或恢复**同版本冷备份** → 按上重启 → 验证 `SELECT schema_version ...` 与 `/readyz`。

**authority 后果（无死区）**：初始化后 **SQLite 是唯一运行 authority**，`--settings` 仅空库首启有效；因此重建**必须**在空库上进行，迁移**必须**离线完成并保持 DB authority。**禁止**在版本不匹配时删除 `schema_meta` 行当"未知库"（会触发 `schema_unknown`，且让 authority 在 settings 与 SQLite 间悬空）。重建会丢账本/使用历史，执行前先导出/备份。

#### 7.1.3 B 类恢复（临时实例）

- **执行机 = 开发机**；**可移植 `cwd`** = 仓库根：`cd "$(git rev-parse --show-toplevel)"`，`export PYTHONPATH=src`。`conftest.py` 的 `LLMTierInstance` 以该根为子进程 cwd 启动（当前硬编码 `/Users/ben/work/LLMTier`；换 checkout 路径时须同步该 cwd）。
- **实例启动失败（`LLMTier did not become healthy`）逐项检查后重启**：
  - 端口：`lsof -nP -iTCP:<port> -sTCP:LISTEN`；占用则让 fixture 重选空闲端口（`_find_free_port`）后重试。
  - DB：`ls -l "$LLMTIER_DATABASE"`；报 `schema_version_mismatch`/`schema_unknown` → 删除临时 DB 后空库重建（本类 DB 可丢弃）。
  - 临时目录：`ls -ld "${TMPDIR:-/tmp}"/llmtier_b_*`；不可写或残留 → `rm -rf` 后重起；确认 `/tmp` 可写、端口可 bind。
  - 重启：`stop()`（`terminate`→等 5 s→`kill`）→ `start()`（轮询 `/healthz` 最多 40×0.25 s）。

#### 7.1.4 多阻塞诊断阈值（机器可读）

达阈值即**暂停批次**、判根因（环境 vs 测试设计/脚本），修后**断点续跑**（§7.1.6）。阈值与 owner/tool/artifact：

| 指标 | 阈值 | 动作 | Owner | Tool | Artifact |
|---|---|---|---|---|---|
| 同批次 BLOCKED 比例 | > 50% | 暂停批次、诊断单一根因 | 执行者 + 环境 owner | pytest 摘要 / runner 日志 | `<date>/diagnosis.md` |
| 同根因连续 BLOCKED | ≥ 3 case | 暂停、定位该端点/构造 | 执行者 | `case-status.json` 分组 | `<date>/diagnosis.md` |
| 同根因累计 BLOCKED | ≥ 5 case | 判系统性、修环境或改 case | 测试设计 owner | ledger 聚合 | `<date>/diagnosis.md` |
| flaky 重试仍失败 | > 3 次 | 转 BLOCKED，记录并发度/时间窗 | 执行者 | 重试记录 | §10 报告 |
| SKIP 超上限 | A > 5 / B > 3 | 覆盖不足，补 fixture/注入后重跑 | 测试设计 owner | runner exit code 2 | §10 报告 |

#### 7.1.5 恢复目录（阻塞源 → 检测事实 → 可运行恢复动作 → 复位）

| 阻塞源 | 检测事实 | 恢复动作（可运行） | 复位 |
|---|---|---|---|
| 环境不就绪 | §7.1.0 任一失败 | A 类按 §7.1.2 重启 / 修 `secret_ref` / 重建 bootstrap；B 类按 §7.1.3 | 重新执行 §7.1.0 |
| 上游超时 | 建连/首字节/流空闲超时（`delay` 可复现） | 调大 deployment runtime profile（`deployment_runtime_profiles.connect_timeout_ms`/`stream_idle_timeout_ms`，默认 30000/60000；B：`sqlite3 "$LLMTIER_DATABASE" "UPDATE deployment_runtime_profiles SET connect_timeout_ms=60000, stream_idle_timeout_ms=120000 WHERE deployment_id='depl_b'"`）；有界重试 ≤ 3；换候选 provider | 恢复 profile 原值；补跑 |
| 鉴权/配置 | 401/403/503 `auth_not_configured` | **`unset` 环境中的 `LLMTIER_ADMIN_TOKEN`/`LLMTIER_DATA_TOKEN`（LAN trust 场景不要追加 token）**；仅当目标实例确实未配置时，才对 B 类用 `LLMTIER_DEV_MODE=1`、对 A 类在服务端 env 设置 | unset 临时变量；复位基线 settings |
| store 忙/锁 | SQLite `database is locked` | 退避重试（`sleep 1`→`2`→`4`，≤ 3 次；连接超时 10 s） | 无残留 |
| provider endpoint 被改 | `PATCH` 后 endpoint 非基线 | **恢复原值**：`PATCH /v1/providers/{id}`（带正确 `If-Match`）写回 §5.3 矩阵中的基线 endpoint | `GET` 核验回基线 |
| 注入未清 | diagnostics `items` 非空 | `curl -X PATCH -H 'Authorization: Bearer dev-admin' -H 'Content-Type: application/json' -d '{"items":[]}' http://…/v1/deployments/{id}/diagnostics`（或同 `type` `enabled=false`） | `GET` 确认空 |
| 账本污染 | usage 记录影响断言 | A：`curl -X DELETE -H 'Authorization: Bearer dev-admin' http://192.168.1.9:8181/v1/usage`；B：丢弃临时 DB 重起 | 重建/核验记录基线 |
| cursor/快照过期 | 400 `cursor_expired` | 重开查询：去掉 `cursor`，重设 `from`/`to`（`/v1/diagnostics/stats` 用 `since`/`until`）时间窗 | 无状态残留 |
| flaky（并发/上游非确定） | 同输入结果不稳定 | 有限重试 ≤ 3（记录并发度与时间窗）；超阈值转 BLOCKED | 该 case；无残留 |
| schema/版本不匹配 | 启动 503 `schema_version_mismatch`/`schema_unknown` | A：§7.1.2 显式二选一；B：删除临时 DB 后空库重建 | 重验 `schema_version` 与 `/readyz` |

#### 7.1.6 续跑语义

**续跑 = 只执行未 PASS 的 case（按依赖顺序）**，已 PASS 的不重跑；依赖链上被跳过的 case 若前置恢复后满足则补跑，否则保持 `SKIP`；一轮结束产出汇总（每 case 终态 + 原因）。

```bash
# 只跑 A 类 / B 类（marker 注册于 pyproject.toml）
PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/ -m api_a -q
PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/ -m api_b -q
# 只跑上次失败的（--lf = last-failed）
PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/ --lf -q
# 按批次/表达式选 case
PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/ -k "adm_prov_05 or adm_prov_06" -q
# 单批 runner（均为 marker 选择）：runner_a.sh = -m api_a，runner_b.sh = -m api_b
bash tests/system/api_test_v03/runner_a.sh
bash tests/system/api_test_v03/runner_b.sh
```

- **Case 状态账本（定义文件）**：`tests/system/reports/<date>/case-status.json`，逐 Case 记录终态，供续跑筛选与回归 diff：
  ```json
  {"run_id":"<date>/<class>-<phase>",
   "cases":{"<CASE-ID>":{"status":"PASS|FAIL|BLOCKED|SKIP|INVALID|NOT_RUN",
                          "reason":"","owner":"","eta":"","artifact":""}}}
  ```
- **续跑选择**：读取账本，取 `status != PASS` 的 Case，按各 `cases/<lowercased-case-id>.md` 的"依赖"字段拓扑排序后执行；或用 `-m api_a`/`-m api_b` + `--lf`/`-k` 选批。
- **禁止**重跑已 PASS 的 case（除非其基线/契约变更，§9 Regression）。

#### 7.1.7 复位约束

每个恢复动作后**必做状态复位**（清注入 / 重置账本 / 复位被改字段与 version / 换独立 DB），确保后续批次从干净状态开始；核验 `/readyz` 7 tier、provider/deployment 列表回基线、无遗留端口、无未清空注入（§11.3）。**A 类对 m5air 现有 state 的副作用须可复位**且不得删除既有资源或用户 usage。

### 7.2 Entry、Exit 与状态判定

**Entry（开始门）**：基线可解析（openapi + §7.8）；§5.2 就绪检查全过；B 类临时实例可启动；测试代码头部满足 TS-002。

**适用（applicable）定义**：一个 Case 在本轮**适用**，当且仅当 (a) 其前置/环境（A 类 m5air 或 B 类临时实例）可用，(b) 其 `cases/<lowercased-case-id>.md` 的 Oracle 可独立判定，且 (c) 该平台确有该行为（例如功耗/FPGA 时序不适用）。不适用须给**裁剪依据**（如功耗 N/A）并具名批准，不得用 `SKIP` 掩盖。**Gate 口径只统计适用 Case。**

**Exit（结束门）**：**本轮跑完 = 所有 case 有终态（PASS/FAIL/BLOCKED/SKIP）且无未诊断的系统性阻塞**（而非"全 PASS 才结束"）；FAIL/BLOCKED/INVALID 均已登记并给出根因/恢复动作；结果落 §10 报告；teardown/复位完成且初态可核验。

| 状态 | 判定 | 阻塞 release | 报告必含 |
|---|---|---|---|
| **PASS** | status + body 关键字段 + error `code`（+ SSE 序列/terminal/`[DONE]`）全 match | 否 | — |
| **FAIL** | 断言不符（含注入命中后行为不符） | **是** | 预期 vs 实际、`reproduction_cmd`、`failure_step` |
| **BLOCKED** | 无法执行/无法判定且**可重试**（测试代码/契约问题且恢复动作未解除：fixture 写不出、断言逻辑错、ISD/OpenAPI 语义不清、注入无法命中） | **是** | `block_reason`、`required_resolution`、**已执行/待执行的恢复动作**、`reproduction_cmd` |
| **SKIP** | 明确不适用或依赖失败（§5.2 环境限制、上游离线、临时实例不可用、依赖链前置未满足） | 否（有上限） | `skip_reason`（引用 §5.2 项/依赖）、`fix_owner`、`eta` |
| **INVALID** | 注入未命中却按行为判定；或用 `127.0.0.1`/mock 冒充真实路径 | **是** | `invalid_reason`、证据缺口 |
| **NOT_RUN** | Case 已定义但本轮未执行，含 MISSING 实现（52 个） | **P0 MISSING 阻断；非 P0 MISSING 具名批准** | 缺口引用（测试设计 §3）、owner、ETA |

**P0 MISSING 规则**：MISSING 是**缺口**不是 SKIP。**P0 且 MISSING** 的 Case 阻断 release（不得以 NOT_RUN 放行）；非 P0 MISSING 记缺口并具名批准（owner/ETA）。

**关键区分**：上游离线/前置不满足 → SKIP（本轮不重跑，恢复后按 §7.1 补跑前置）；fixture 写不出且恢复动作未解除 → BLOCKED（可重试）；status 对但字段缺 → FAIL。**单 case 的 BLOCKED/SKIP 不终止整轮**（§7.1）；**本轮 Exit ≠ 全 PASS**，以"所有 case 有终态且无未诊断系统性阻塞"为准。**禁止"未跑"无状态**：runner 必须每项给明确结果。**跨 backend 隔离**：A 类 PASS 不关闭 B 类；静态 contract PASS 不关闭本计划。

**Flake / SKIP 上限与 runner 退出码**：**SKIP 上限** A 类 ≤ 5、B 类 ≤ 3；超出视为覆盖不足，须补 fixture/注入后重跑。Runner 退出码契约：`0` = 全部适用 Case PASS 且 SKIP 在上限内；`1` = 存在 FAIL/BLOCKED/INVALID；`2` = SKIP 超上限（覆盖不足门）。可对非确定性 Case 设 quarantine/isolate（`-m "not quarantine"` 排除出 Gate，具名批准），quarantine 计入 §10 报告但不静默豁免。

## 8. 组织、职责、排期和资源

| 角色 | 职责 | 产物 |
|---|---|---|
| 测试设计（Case 作者） | 维护测试设计 §3、逐 Case 设计文档与 `at_*.py` 断言 | Case、case 设计、fixture |
| 环境提供（m5air owner） | 部署、secret、OMLX、就绪检查 | §5.2 全绿 |
| 执行者 | 按 §3.4 顺序跑 A/B 批次、teardown、记录 Run | Run 报告 |
| 见证/裁决 | BLOCKED/INVALID 裁决、回归门 | Gate 结论 |

排期沿用执行层计划阶段：P0 基线+conftest/runner → P1 A 类批次 → P2 B 类批次（临时实例）→ P3 首跑+报告 → P4（可选）CI。**冲突处理**：A/B 互斥同一实例；并发写测试独占 B 类，不与 A 类并行；MISSING 52 项的补实现优先于新增范围。

## 9. Defect、Deviation、Rerun 与 Regression

- **缺陷登记**：每个 FAIL/BLOCKED/INVALID 记 ID、Case、预期/实际、`reproduction_cmd`、根因、owner、状态。
- **偏差批准**：任何跳过/裁剪（如功耗 N/A、endurance 引用他文）须具名理由与批准，不得静默。
- **修复基线**：修复后必须回到同一基线重跑，并保留首轮失败与重测的关联（不覆盖旧失败）。
- **Rerun / 续跑**：生成新 Run ID；**续跑按 §7.1 只执行未 PASS 的 case（依赖顺序）**，已 PASS 不重跑；依赖链上被跳过者其前置恢复后满足则补跑，否则标 SKIP；非确定性 Case（并发/上游）重跑须记录并发度与时间窗；重跑只重跑受影响批次（§3.3）。
- **Regression 邻域**：契约/错误码/路由变更 → 全量；单模块修复 → 本 family + 共享 `T-*`/`VRC-*` 的家族（如 Registry 改 → ADM-PROV/DEPL/SL + DP-MODELS/RESP/EMB 路由）；错误信封改 → 全部负向 Case；case 设计变更 → 该 Case 及其依赖边下游（§3.4）。
- **Golden / baseline 回归产物（机制）**：在同一基线上把一份**全 PASS 的 Run** 固化为 golden：`tests/system/reports/<date>/baseline/expected.json`（Case ID → 归一化期望：HTTP status、body 关键字段集、error `code`/`param`、SSE 事件序列骨架），与 `baseline/run_id` 指向的原始证据并存。回归执行时用 **case-status 账本 + diff**：`case-status.json`（§7.1.6）与 `expected.json` 逐 Case 比对，产出 `reports/<date>/regression-diff.md`（新增/消失/翻转的 Case 与字段）；差异即回归缺陷。**基线随契约变更显式升版**（不静默覆盖旧 golden），首轮失败与重测关联保留。

## 10. Evidence、Traceability、Reporting 与 Gate

- **Run ID**：`<date>/<class>-<phase>`（如 `2026-09-28/A-api`、`2026-09-28/B-api`）。
- **原始证据**：命令、HTTP status/headers/body、SSE 逐帧、exit code、耗时、环境快照（`/healthz`/`/readyz` + provider/deployment 列表 + `api_smoke_test.py` 输出）。失败现场保留不截断。
- **保存位置**：`tests/system/reports/<date>/`；本计划的 Case ↔ Run 对应表随报告维护。
- **Traceability**：Case → 测试设计 §3.2 `设计 V`（`VRC-*`/`T-*`）→ openapi/§7.8/ISD；每 Case 的详细追踪见 `cases/<id>.md`；`ERR-*` 目录逐条映射 Case 或缺口。
- **Reporting/Gate**：报告须给出覆盖数（应跑/已跑/PASS/FAIL/SKIP/BLOCKED/INVALID/NOT_RUN）、未关闭缺陷、MISSING 缺口、具名缺口清单（§3.6.2）。**Gate 判定**：**适用 Case**（§7.2）全 PASS 且 FAIL/BLOCKED/INVALID=0、SKIP 在上限内（§7.2）；**P0 MISSING 阻断**；非 P0 MISSING 与具名缺口需具名批准（owner/ETA）。**注意：本 Gate 是 release 放行门槛，不等于"本轮跑完"**——"本轮跑完"见 §7.2 Exit（所有 case 有终态且无未诊断的系统性阻塞）。
- **Gate owner / 审批元数据（进入 Gate 状态时填写，不伪造）**：

| 字段 | 值 |
|---|---|
| Gate Owner | 待填（执行负责人） |
| Gate Approver | 待填（见证/裁决） |
| Gate Approval Date | 待填（ISO-8601） |
| Gate Result | 待填（PASS / CONDITIONAL / REJECT） |
| Approved Gaps | 待填（具名缺口 ID + owner + ETA） |
| Baseline Run ID | 待填（golden Run，§9） |

## 11. 风险、安全与清理恢复

### 11.1 风险与停止阈值

| 风险 | 触发 | 停止/恢复 |
|---|---|---|
| 上游 provider 离线 | §5.2 检查失败 | 停止受影响 DP-RESP/EMB 批次（**不终止整轮**），标 SKIP；按 §7.1 恢复后补跑/续跑 |
| 写测试污染 m5air | teardown 失败或残留 | 停止 B 类；隔离实例；不得删除 m5air 既有资源 |
| 注入未清除 | 离开时 `GET /deployments/{id}/diagnostics` 非空 | 阻止下一轮；手动清空 `items:[]` |
| 临时实例不可终止 | 进程/端口未释放 | BLOCKED，保留证据，不做无边界清理 |
| 费用型外部调用 | 未确认即调 MiniMax/probe/usage-refresh | 立即停止；必须显式 `confirm_external_call` |

**恢复策略**：单 case/单批受阻按 §7.1 **就地恢复后继续**（不终止整轮）；触及 §7.1 阈值时暂停 → 诊断根因（环境 vs 测试设计）→ 修环境/改 case → **断点续跑**（不回跑已 PASS）。恢复目录与续跑语义见 §7.1；清理与复位见 §11.3。

### 11.2 安全

- 真实 Secret 绝不出现在日志/审计/证据；脱敏断言显式检查不含 `9832` 与 key 文件内容。
- `dev-data`/`dev-admin`/`9832` 为本地开发凭据，不作为"秘密"证据对象。
- 管理面未授权不得泄露资源存在性。

### 11.3 清理与可重复性

- A 类每个写 Case teardown（恢复原名/删除创建物）；B 类整班销毁临时实例与临时 SQLite；注入 Case 清空 items。
- 清理后下一轮可核验初态（§5.2 + `/readyz`）；不得删除用户 usage 或其他任务数据。
- 测试进程退出 ≠ 设备停止：B 类须显式 `terminate` 并等待。
- **恢复后复位（§7.1.7）**：每个就地恢复动作执行后必做状态复位（清注入 / 重置账本 `DELETE /v1/usage` / 换独立 DB），确保后续批次从干净状态开始；A 类对 m5air 现有 state 的副作用须可复位（§2.8）。

### 11.4 历史踩坑回归检查（执行前逐项确认已修复）

| ID | 问题 | 关联 Case | 验证方式 |
|---|---|---|---|
| P1 | 用 `127.0.0.1`（违反 TS-003） | 全部 DP | §5.2/§5.3 强制 LAN IP；TS-002 头部 |
| P2 | provider endpoint 未指向 m5mac/m5air | DP-RESP/EMB | §5.3 路由矩阵 |
| P3 | 上游健康不可知 → 跑一半 500 | DP-RESP-01~04、ADM-PROBE-02 | §5.2 OMLX 双机检查 |
| P4 | `secret_ref` 三格式（`file:`/`env:`/`raw:`）差异未测 | ADM-PROV-02/12 | 保留缺口（现只测 `file:`） |
| P5 | `capabilities` 缺字段 → 400 | ADM-DEPL-02/06/07 | 测试设计 §4.10 12 键全集 |
| P6/API-001 | 412 缺 `current_version` | ADM-PROV-06 | 测试设计 §4.10 If-Match 段 |
| P7 | If-Match ETag 格式未文档化 | 所有 PATCH/DELETE | 测试设计 §4.10 If-Match 段 |
| P8 | 时间参数 RFC3339 缺失 | DP-USAGE-*、ADM-USAGE-* | 测试设计 §4.10 时间参数段 |
| P9 | create 多传 `id` | ADM-PROV-02 | schema `additionalProperties:false` |
| P10 | grep `"error"` 误匹配 `"error":null` | ADM-PROBE-02、并发 | 测试设计 §4.6（JSON 解析） |
| P11/FD-001 | FD 泄漏 | 不在本计划 | 引用 `llmtier-test-plan.md` ST-18/19 |
| P12 | 50% BLOCKED 当失败（本轮中断） | 全局 | §7.1 阈值触发「暂停+诊断+续跑」而非失败；§7.2 六状态判定；SKIP 上限 |
| P13 | 测试头部未写依赖（TS-002） | 全部 Case | §5.5/测试设计 §2 |
| P14 | DP-RESP-02 期望错（`stream=false` 必拒） | DP-RESP-02/06 | `cases/dp-resp-02.md` |
| P15 | 诊断面误用 `from`/`to` | OBS-STATS-02 | 测试设计 §4.10 时间参数段（`since`/`until`） |
| P16 | 别名与扁平路径不等价 | OBS-ALIAS-01..04 | 测试设计 §4.10 别名段 |
| P17 | provider-models 触上游未记录 | ADM-PROV-MODELS-01/02 | 测试设计 §4.10 confirm 段 |
