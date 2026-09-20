<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Test Plan

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-v0.3-test-plan` |
| Document Version | `0.3.2-draft.4` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | LLMTier, Piko, Slinky |
| Approver | 待定 |
| Approval Date | 待定 |
| Created Date | `2026-09-19` |
| Last Modified Date | `2026-09-20` |
| Template Version | `0.1.0` |
| Template ID | `assurance.test-plan` |
| Template Conformance | `native` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | `llmtier-v0.3-vv-plan`, `llmtier-v0.3-contract-test-specification` |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/plans/llmtier-v0.3-test-plan.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 目标、范围与测试层级

本文件按 STD `assurance.test-plan` 模板覆盖 **runtime** 端到端测试。区别于：

- `llmtier-v0.3-contract-test-specification.md`：静态契约 + case matrix（CT-*）；本 plan 是其在 runtime 上的落地与扩展。
- `llmtier-v0.3-vv-plan.md`：高层 V&V 方法论；本 plan 是其 system 层的执行细节。

测试层级：system（HTTP/SSE 真实启服 + 真实或受控 provider + 真实 SQLite）。**不**替代 unit（24 个文件，191 cases）和 contract static 测试。

被测：运行中的 `llmtier_v03` 进程、OpenAI-compatible data plane（`/v1/responses`、`/v1/embeddings`、`/v1/models`、`/tier/v1/usage`）、admin（`/tier/admin/v1/*`）、SQLite 持久化、FD 资源约束、auth 与 TRUSTED_LAN。

不被测（§11 列缺口）：浏览器自动化 E2E、生产 TLS/auth/CSRF、`runtime_activation=true`、多实例 / HA / 跨系统恢复、单元 / 静态契约（既有测试覆盖）。

authority：OpenAPI 是字段层 machine authority；本 plan 是 runtime 行为 authority。

## 2. 被测基线、排除项与依赖

### 2.1 前置（必须全满足才能跑任何 ST-XX）

| 前置 | 期望 |
|---|---|
| 代码 commit | HEAD 在 deploy 节点上；含 `b89ba4d`（FD 泄漏修复）与 `a6f06af`（SSL context + reasoning events）；runner 起跑前 `git rev-parse HEAD` 校验 |
| `tests/` 单元测试 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests` exit 0；baseline ≥191 PASS |
| 进程可启服 | `python3 -m llmtier_v03 --host 127.0.0.1 --port <port> --database <db> --settings <bootstrap>` 60 秒内 listen；`/healthz` 200，`/readyz` 200 且 7 个 tier 全部 `available` |
| TRUSTED_LAN_MODE | 默认 `LLMTIER_TRUSTED_LAN_MODE=1`；ST-24A 单独验 OFF |
| OMLX 必须存活 | `127.0.0.1:9100`；其 `auth.api_key` 与 LLMTier `provider_local.secret_ref` 一致。OMLX down → 全部依赖 ST-05..ST-09、ST-12 的 case BLOCKED，恢复路径见 `docs/80_operations/m5air-operations-manual.md` §15 |
| Provider adapter | 至少一个 `local`（fake 或真 OMLX）+ 一个 `cloud`（Piko 端点或受控云）真实可达；调用超时 ≤ 30s |
| Mock-Piko 接入 | `tests/fixtures/v03_fake_provider.py`（已存在）；ST-22A/ST-23 注入 dispatch delay 用此 fake provider。**当前 fake provider 不支持 SSE streaming 模拟**——ST-07 涉及 stream 时需先扩展 fake provider 或换用真 OMLX + 增加 sleep |
| SQLite | 启动时执行 `001_initial.sql` migration；`PRAGMA integrity_check` 输出 `ok` |
| FD baseline | 进程启服后 60 秒 idle 状态下 `lsof -p $PID | wc -l` ≤ 60 |

### 2.2 测试环境约束

**m5air 不是测试环境**。m5air（`192.168.1.9`）是 LLMTier 运维环境，运行生产级服务（`LLMTIER_TRUSTED_LAN_MODE=1`），供人工验证、调试和 Web UI 确认用。自动化系统测试必须跑在**开发机**（如 m5mac）上的临时 SQLite + 临时端口，避免污染 m5air 的运行状态和干扰其服务。

| 环境 | 用途 | 可跑 ST-XX |
|---|---|---|
| m5air (`192.168.1.9`) | 运维、人工验证、Web UI 确认 | 人工确认、smoke |
| 开发机 (m5mac) | 自动化系统测试 | ST-01..ST-26（全部） |
| CI/CD runner | 单元测试 + contract static | ST-02, ST-03 |

ST-05..ST-09、ST-10..ST-12 需要 OMLX 可达：开发机上跑时用 `provider_local`（`127.0.0.1:9100`，m5air 上的 OMLX）或 `provider_omlx_m5mac`（`192.168.1.8:9000`，m5mac 本地 OMLX）。

### 2.3 排除条件

- 当前 commit 缺 `b89ba4d` 或 `a6f06af` 时，**禁止**执行 ST-19；runner 必须先 `git rev-parse HEAD` 验证。
- 任何带 `confirm_external_call=true` 的真实云端 refresh 必须在 operator 显式授权下执行；测试固件中如使用真实云 key，必须先离线 `confirm_external_call` mock 化（跑 ST-15 / ST-16 时 mock 与真实各跑一遍）。
- 真 Piko / 真 Slinky Memory 联调：本 plan 仅覆盖 Mock 路径；真 consumer 联调是 §11.5 M5/M6 缺口。
- ST-16 依赖云端 quota refresh，m5air 上 `provider_volc` 已删除；应在有云端 provider 的独立测试环境跑，或用 mock 替代。

## 3. Test Strategy 与 Coverage Model

策略：单服务 / 单进程 / 单 SQLite 部署边界内的 runtime 端到端；unit mock 与 fake provider 仅用于无法隔离的子路径（如 SSE stream、限速注入）；浏览器 E2E / 生产 TLS / `runtime_activation=true` / 跨系统恢复按 §5.3 单独规划，本 plan 不替代。

覆盖模型（surface → requirement → contract → case）：

| Surface | Contract ID | Case IDs |
|---|---|---|
| 启服 / health / readiness | CT-OPS-001 | ST-01 |
| 单元测试入口 | CT-BOUNDARY-001 + CT-SCOPE-001 | ST-02 |
| Contract static validator | CT-SCOPE-001 | ST-03 |
| Models 严格匹配 | CT-MODEL-001 | ST-03A |
| Forbidden path/header 扫描 | CT-SCOPE-001 + CT-BOUNDARY-001 | ST-04 |
| Piko 路径 `/v1/responses` | CT-DP-001 | ST-05..ST-09A |
| Slinky 路径 `/v1/embeddings` | CT-EMB-001 | ST-10..ST-12A |
| Admin CRUD/probe/refresh | CT-ADMIN-001 | ST-13..ST-16 |
| Audit / LogPage 过滤与禁入 | CT-LOG-001 | ST-15A |
| Web UI fixture 完整性 | CT-WEBSEC-001 起点 | ST-17 |
| 可靠性（FD / crash / WAL） | §5.3 long-running + recovery | ST-18..ST-20 |
| 性能 / 限速 / 队列 | CT-ADM-001 admission | ST-21..ST-23, ST-26 |
| 安全 / auth / TRUSTED_LAN | CT-WEBSEC-001 | ST-24..ST-25A |

Coverage gaps 显式列在 §11.5。

## 4. Case 矩阵（Test Item / Feature / Requirement）

| ID | Case 名 | 步骤摘要 | 预期 |
|---|---|---|---|
| ST-01 | 启服 baseline | 启服 → 60s idle → `/healthz` `/readyz` 各 5 次；检查 `/v1/models` 返回 7 个逻辑 tier | **已测** - healthz ✓, readyz ✓, 7 tiers ✓, FD=41 ≤ 60 ✓ |
| ST-02 | 单元测试入口 | 跑 `tests/` 全集 | exit 0，全部 ≥191 PASS |
| ST-03 | `tools/contract_semantic_validator_v03.py` | 解析 + Schema 校验 | **已测** - exit 0, stdout 空 ✓ |
| ST-03A | Models exact-case | `GET /v1/models/worker` (小写) / `/v1/models/WORKER` / `/v1/models/Senior%20` | **已测** - worker/WORKER/Senior%20 → 404 ✓；Worker → 200 ✓ |
| ST-04 | Forbidden path/header 扫描 | 跑 `tests.contract.test_contract_semantics_v03.SimplifiedV03ContractTests` 与 `tests/unit/v03/test_webui_contract.WebUIContractTests`；扫响应头与路径 | **已测** - contract 16 PASS + webui 20 PASS ✓ |
| ST-05 | Piko Responses text | **目的**: 验证 SSE 流式响应基本正确。**方法**: POST /v1/responses with hi。**环境**: OMLX 可用。**结果**: 已测 - SSE 事件完整，usage 非 null ✓ | SSE 含完整事件；`usage.input_tokens/output_tokens/total_tokens` 非 null |
| ST-06 | Piko Responses reasoning (OMLX) | **目的**: 验证带推理的请求 SSE 流式输出正确。**方法**: POST /v1/responses，prompt="Calculate 15 * 23 + 45"。**环境**: OMLX/gemma 将 reasoning 内嵌在 output_text 而非独立 reasoning_text 事件。**结果**: 已测 - SSE 完整 ✓；output_text 含推理步骤 ✓；`response.completed` terminal ✓ | SSE 含 `response.created / output_item.added / output_text.delta/done / output_item.done / response.completed`；`usage.reasoning_tokens=0`（因为 reasoning 内嵌）；`response.completed` terminal |
| ST-07 | Piko Responses function tool (OMLX) | **目的**: 验证带 tools 参数时 LLMTier 正确透传到 OMLX 并处理响应。**方法**: POST /v1/responses 带 `tools=[{type:function}] + tool_choice="required"`，验证请求不报错。**环境**: gemma 不调用工具，响应仍为正常 message。**结果**: 已测 - 请求合法，200 ✓，SSE 完整但无非 function_call 事件（gemma 行为） | 请求合法返回 200；SSE 事件完整；无非 function_call 事件（gemma 不支持 tool use）；如返回 400/503 则 FAIL |
| ST-08 | Piko Responses 并发 8 路 | **目的**: 验证 8 路并发请求 FD 不泄漏。**方法**: 8 路并行 POST /v1/responses max_output_tokens=64。**环境**: 当前配置只有 OMLX deployment。**结果**: **已测** - 8/8 成功 ✓；FD=48 ≤ 80 ✓ | ≥ 6 路 200；FD 数 ≤ 80 |
| ST-09 | Piko Responses 错误目录 | **目的**: 验证错误请求返回正确错误码。**方法**: 直接 curl 构造 5 个 400 + 1 个 404。**环境**: 无特殊要求，可直接测。**结果**: **已测 PASS** - 全部 6 个子测试通过；unknown model 返回 404 `model_not_found` ✓ | 全部 400/404；`stream:false`→400 `unsupported_request`；`store:true`→400 `unsupported_request`；缺字段→400 `invalid_request`；`previous_response_id`→400 `unsupported_field`；unknown model→404 `model_not_found` |
| ST-09A | Piko Responses `previous_response_id` rejected | **目的**: 验证 previous_response_id 被正确拒绝。**方法**: curl 带此字段。**环境**: 无特殊要求。**结果**: 已测 - PASS，400 `code=unsupported_field` ✓ | 400 `code=unsupported_field` |
| ST-10 | Slinky embedding | **目的**: 验证 embedding 服务可用且返回正确维数。**方法**: POST /v1/embeddings model=Embedding-v1。**环境**: 当前 bge-m3 deployment 未配置，Embedding-v1 为 `unavailable`。**结果**: BLOCKED - 需配置 bge-m3 embedding deployment | 200；`data[0].embedding` 长度=1024；无 NaN/Inf |
| ST-11 | Slinky embedding base64 | 同 ST-10 + `encoding_format=base64` | BLOCKED - 需 ST-10 先 PASS | 200；base64 解码后 1024 个 little-endian float32；全部 finite |
| ST-12 | Slinky embedding 不变量 | 5 次 ST-10；验证维数和 embedding_space_id 一致性 | BLOCKED - 需 ST-10 先 PASS | 每次维数=1024；`embedding_space_id` 一致 |
| ST-12A | Usage 分页边界 | **目的**: 验证 usage cursor 翻页正确处理。**方法**: 先跑若干 Responses 生成 usage，然后 curl 测试翻页、过期 cursor、错误 cursor。**环境**: 需先生成 usage 数据。**结果**: 已测 - cursor roundtrip ✓，bad cursor → 400 `cursor_expired` ✓ | cursor roundtrip 一致；bad cursor → 400 `cursor_expired`；store 503 模拟（断 DB 文件）→ 503 |
| ST-13 | Operator 创建 Provider | `POST /tier/admin/v1/providers` 含 secret_ref；GET 验证 `has_secret=true`；DELETE 清理 | **已测** - POST 201 ✓；has_secret=true ✓；DELETE 需正确 If-Match 格式才返回 204 ✓ |
| ST-13A | Operator If-Match 412 | PATCH provider 不带 `If-Match`；带过期 etag | **已测 PASS** - 无 If-Match → 412 ✓；过期 etag → 412 ✓；**已修复**: response 现在包含 `current_version` 字段 ✓ |
| ST-14 | Operator 创建 Deployment + bind Tier | POST deployment → POST tier PATCH 加 deployment_ids | **部分测** - Deployment 创建需要完整 capabilities 字段（含所有 CAPABILITY_KEYS）；需先创建 provider 再创建 deployment，再绑定 tier |
| ST-15 | Operator Probe 授权 | `POST /tier/admin/v1/probes` 无 confirm → 400；带 confirm=true → 200，response 含 `status=healthy/unhealthy` | **已测 PASS** - 无 confirm → 400 `confirmation_required` ✓；带 `confirm_external_call=true` → 200 `status=healthy/unhealthy` ✓ |
| ST-15A | Audit 过滤 + LogPage 禁入 | **目的**: 验证 audit/log 不泄露敏感信息。**方法**: 先跑请求生成 audit 数据，然后 GET audit 和 logs 检查响应不含 secret/prompt/embedding。**环境**: 需先生成 audit 数据。**结果**: 已测 - audit 字段齐全，无敏感信息泄露 ✓ | 字段齐全；响应 body 不含 prompt/output/embedding/Authorization/Secret 任何字串 |
| ST-16 | Operator 账号 quota refresh | **目的**: 验证云端 provider quota refresh。**方法**: 调用 confirm probe。**环境**: 当前无 MiniMax 云端 API key。**结果**: BLOCKED - 无云端 provider | 400 / 200；snapshot 持久化；错误路径不污染窗口 |
| ST-17 | Operator 页面（headless fixture 完整性） | **目的**: 验证 Web UI 资源可访问且结构正确。**方法**: curl 各路径检查响应和内容。**环境**: 无特殊要求。**结果**: 已测 - 4 pages ✓, 4 nav buttons ✓, 3 tabs ✓ | 全部 200；HTML 内含 4 个 page 与 4 个 nav 按钮；Logs 页内有 3 个 tab |
| ST-18 | FD 稳定性（短期） | **目的**: 验证短期负载下 FD 不泄漏。**方法**: 跑约 50 个请求后检查 FD 和 lsof。**环境**: 无特殊要求。**结果**: **FAIL** - FD=89 > 80 | FD ≤ 80；进程打开的 sqlite 文件数 ≤ 8 |
| ST-19 | FD 稳定性（长期，30min） | **目的**: 验证长时高并发下 FD 稳定。**方法**: 60 并发 max_output_tokens=32 持续 30 分钟，每 30 秒采样。**环境**: 需长时窗口。**结果**: 待测（耗时 30min） | FD 在 5 分钟内达稳定值（前后两次采样差异 ≤ 5）；不出现 `Too many open files`；终值 ≤ 200 |
| ST-20 | Process crash + restart | **目的**: 验证 crash 后数据完整性。**方法**: kill -9 重启后检查 integrity 和 audit 链。**环境**: 无特殊要求。**结果**: **已测** - restart ✓, integrity=ok ✓ | integrity=ok；Audit 无丢；Usage obligation 在 restart 后仍能 finish unknown |
| ST-21 | End-to-end latency P50/P95 | **目的**: 验证响应延迟 SLA。**方法**: 50 路顺序请求后统计 P50/P95。**环境**: OMLX 可用。**结果**: **已测** - P50=8ms, P95=10ms（阈值待 Piko SLA 联调时锁定） | P50 ≤ Xs，P95 ≤ Ys（阈值待 Piko 联调时校准，当前 placeholder） |
| ST-22 | Provider 限速触发（实际行为） | **目的**: 验证 max_concurrent=1 时 6 并发被队列吸收。**方法**: 改配置 + 6 并发。**环境**: 需动态改 provider max_concurrent 配置（当前不支持动态修改）。**结果**: BLOCKED - 需支持动态配置变更或代码级 mock | 全部 200（队列 32 吸收），无 429 |
| ST-22A | Provider 限速触发（人工制造） | **目的**: 验证 slow provider 触发 429。**方法**: 同 ST-22 + 制造慢响应。**环境**: 需代码级 mock slow provider。**结果**: BLOCKED - 需代码级 mock | 至少 5×429 带 `Retry-After: 30` |
| ST-23 | Tier 队列满 | **目的**: 验证队列满时第 33+ 路立即 429。**方法**: 同 ST-22A + 50 并发。**环境**: 需代码级 mock。**结果**: BLOCKED - 需代码级 mock | 第 33+ 路立即 429；前 32 路入队 |
| ST-24 | Auth bypass 阻击（单元级） | **目的**: 验证无 auth 时返回正确错误码。**方法**: 单元测试 mock bad bearer/缺 auth/未知 principal。**环境**: 单元测试。**结果**: **已测** - test_auth.py 10 PASS ✓ | 三个子 case 全 PASS |
| ST-24A | TRUSTED_LAN 总开关 OFF | **目的**: 验证关掉 TRUSTED_LAN 后无 bearer 请求被拒绝。**方法**: 不设 TRUSTED_LAN_MODE 重启，发无 bearer 请求。**环境**: 需重启服务。**结果**: 已测 - 503 `auth_not_configured` ✓（auth 未配置时返回服务不可用） | 503 `auth_not_configured` |
| ST-25 | TRUSTED_LAN 主子分流 | **目的**: 验证 loopback vs RFC1918 分流正确。**方法**: loopback 发 usage，RFC1918 发 responses。**环境**: 需多 principal（当前单 principal）。**结果**: BLOCKED - 需多 principal 环境 | 数据面走 principal；admin 返聚合 |
| ST-25A | 数据面 vs 管理面 usage 隔离 | **目的**: 验证 /v1/usage 和 /tier/admin/v1/usage 数据隔离。**方法**: 对比两者的记录数。**环境**: 需多 principal。**结果**: BLOCKED - 需多 principal 环境 | 两者差值为其他 principal 的量 |
| ST-26 | Provider request 归属 | **目的**: 验证 request 归属到正确 principal。**方法**: 4 并发 4 不同 principal，检查各 provider 的 calls。**环境**: 需多 principal + 多 provider。**结果**: BLOCKED - 需多 principal 环境 | 各 provider calls=1；request_id 可查 |

每个 case 必须产生：调用前状态、调用、调用后状态、判定。失败 case 必须包含 `failure_reason` 字段，写明预期 vs 实际 + 触发步骤 + 复现命令。

## 5. 环境、设备、拓扑、数据和工具

### 5.1 工具与脚本（**本 commit 时点尚未实现**——以下为实施计划，非已存在文件）

待新增：

- `tools/system_test_runner.py`：编排器（operational tool，跑测试但不属于 `tests/` 的 case），参数 `--port`, `--database`, `--provider`, `--commit`, `--cases ST-01,ST-05,...`，按依赖顺序执行；调 `tests/system/` 下 case 并捕获 stdout/stderr/exitcode，写入 `tests/system/reports/<run-id>/<case>.json`。**落地：M2-milestone；当前 PR 阶段在开发机（m5mac）上用 `bash` 直接跑关键 case，不在 m5air 上跑。**
- `tests/system/st_*.py`：每个 case 一个文件，例如 `st05_responses_text.py`、`st18_fd_short.py`、`st22a_provider_429_inject.py`。**落地：M2。**（case 本身属 `tests/system/`，不是 earlier 版本的 `tools/system_test_cases/` —— 按 STD draft.26 HEAD 布局修正）
- `tests/system/reports/<run-id>/`：系统测试报告，按 Run ID 分开（STD 最新 `tests/{level}/reports/<run-id>/` 规则）；不在 `docs/70_verification/` 集中。
- `tests/system/`：firewall 把系统测试连进 `python3 -m unittest`，路径 `tests.system.test_st_*`；可与现有 191 个单元测试合并跑。**落地：M3。**
- 当前可立刻跑的 baseline（无需新工具）：`/tmp/piko_smoke.sh` 模式（已在 HANDOFF §5.2 验证用过）+ `tests/unit/v03/test_admin_stats.py` 模式 → 拷成 `tests/system/st_*.py` 即可。

### 5.2 执行顺序与依赖

```
ST-01 → ST-02/ST-03/ST-04（可并行） → ST-05/ST-07（共用 Piko fixture）
                                → ST-08（独占临时 deployment 切换）
                                → ST-09（独立错误目录）
                                → ST-10/ST-11/ST-12（共用 Slinky fixture）
                                → ST-13/ST-14/ST-15/ST-16（按 CRUD 顺序）
                                → ST-17（headless 静态）
                                → ST-18（短期 FD，跑完 ST-05..ST-09 后顺跑）
                                → ST-19（30min FD 长期，需独立时间段）
                                → ST-20（crash + restart，独立窗口）
                                → ST-21/ST-22/ST-23（性能与限速，独立）
                                → ST-24/ST-25（安全，独立）
```

ST-19 因持续 30 分钟，**默认不在 PR 阶段跑**；由 operator 在预发环境手动执行，结果写入 `tests/system/reports/<run-id>/long_fd/`。

### 5.3 复跑与并发

- 每个 case 在新临时 SQLite（`/tmp/llmtier_system_<uuid>.sqlite3`）下重新启服，避免污染主 state。
- ST-08/ST-19/ST-22/ST-22A/ST-23/ST-26 在 case 内自动恢复 deployment 状态（enablement、max_concurrent）。
- **teardown 由 runner 负责，不挂在某个 case 上**：runner 维护 PATCH-post 列表，结束时统一撤销；kill 进程；rm 临时 SQLite 与临时 secret 文件。
- case 间共享"上次 PATCH 什么"通过 runner 全局状态传递（不是 case 自维护）；这避免 ST-XX-临时禁-忘-恢复-导致-后续-失败。

## 6. Test Types 与 Case Families

| Test Type | 含义 | Case IDs |
|---|---|---|
| **normal** | 默认成功路径 | ST-01, ST-03A, ST-05, ST-06, ST-07, ST-10, ST-11, ST-13, ST-14, ST-15, ST-17, ST-25, ST-26 |
| **boundary** | 边界条件（空数据、维数、cursor、过期） | ST-12, ST-12A, ST-19, ST-21 |
| **negative** | 错误目录、validation、bad input | ST-03, ST-04, ST-09, ST-09A, ST-13A, ST-15A, ST-24, ST-24A |
| **concurrency** | 并发与限速 | ST-08, ST-22, ST-22A, ST-23, ST-26 |
| **recovery** | crash + restart + WAL 持久化 + Usage obligation 持续 | ST-12A, ST-20 |
| **security** | auth、TRUSTED_LAN、secret 不外泄 | ST-04, ST-13, ST-15A, ST-24, ST-24A, ST-25, ST-25A |
| **performance** | 端到端 latency、限速 | ST-21 |
| **endurance** | 长期 FD / 资源稳定 | ST-18, ST-19 |

每个 family 都映射到 ST-XX case 并落到 §4 的 Requirement Matrix 与 §7 的 Evidence。

## 7. Entry、Exit、Pass、Fail、Blocked 和 Invalid Criteria

| 状态 | 含义 |
|---|---|
| PASS | case 所有预期字段与 oracle 字段一致，exit 0，evidence 完整 |
| FAIL | 实际输出与预期至少一处不一致；记录 `failure_reason` 与重跑命令 |
| BLOCKED | 受真实外部依赖限制无法跑（如云端 API 限流、OMLX 未运行）；记录 blocker 字段与解除条件 |
| INVALID | case 设计错误或预期本身不成立；记录 issue，需重新设计 |

**Entry criteria**（runner 起跑前）：§2.1 前置全满足（commit 校验、单测全绿、OMLX 存活、`b89ba4d`+`a6f06af` 包含）。

**Exit criteria**（runner 结束）：
- 全 PASS 或受限 BLOCKED：可发布。
- 任一 FAIL / INVALID：阻塞 release；issue + waiver 走 §8。

ST-19 与 ST-20 是 §5.3 阻塞项的解封步骤；只有当 ST-19 PASS 才能将 `runtime_activation` 决策前的 `process-restart` 门禁视为 GREEN。

## 8. 组织、职责、排期与资源

| 项 | Owner | 资源 | 排期 |
|---|---|---|---|
| ST-01..ST-04（启服 + 静态 smoke） | LLMTier author | dev 机器 | 每个 PR 必跑，< 30s 完成 |
| ST-05..ST-09A（Piko Responses） | LLMTier author + Mock-Piko | dev + OMLX (m5air:9100 或 m5mac:9000) | 每个 PR 必跑；接入真 Piko 后替换（§11.5 M5） |
| ST-10..ST-12A（Slinky embedding） | LLMTier author + Mock-Slinky | dev + OMLX bge-m3 | 每个 PR 必跑；接入 Slinky Memory 后替换（§11.5 M6） |
| ST-13..ST-17（Admin operator） | LLMTier author | dev 临时 SQLite 即可 | 每个 PR 必跑 |
| ST-15A / ST-04 / ST-13A（负例） | LLMTier author | 同上 | 与所属 family 同步跑 |
| ST-18 / ST-19（FD 稳定性） | LLMTier author + operator | dev；ST-19 需预发独立窗口 | ST-18 每个 PR；ST-19 仅 release 前 + 修复后 |
| ST-20（crash + restart） | LLMTier author + operator | dev；可制造 SIGKILL | 每个 PR 跑短版本；完整 restart 流程仅 release 前 |
| ST-21（latency） | LLMTier author | dev + OMLX | 阈值待 Piko SLA 锁定后纳入 PR gate |
| ST-22 / ST-22A / ST-23（限速） | LLMTier author | dev 临时 SQLite + Mock-Piko 注入 delay | 每个 PR 必跑 |
| ST-24 / ST-24A / ST-25 / ST-25A（安全） | LLMTier author | dev 临时 SQLite + unit-level mock auth | 每个 PR 必跑 |
| ST-26（request 归属） | LLMTier author | dev 临时 SQLite | 每个 PR 必跑 |
| acceptance gate | LLMTier owner + Piko reviewer + Slinky reviewer | dev + 真 Piko + 真 Slinky Memory | release 前完整跑一次 ST-01..ST-26 |

资源依赖：1 台 m5air 测试机 + 1 个 OMLX 进程 + (release 前) 真 Piko 与真 Slinky Memory；不含人员排期细节（按 §11 缺口走）。

## 9. Defect、Deviation、Rerun 与 Regression

- 偏差需关联 `requirement id`、`case id`、`commit`、`env`、`owner`、`due`、`approver`，存于 `tests/system/reports/<run-id>/deviations.json`。
- 不可用 legacy `/call`、旧 `/admin` 路径、ASGI/Tornado 等非 Python stdlib HTTP 路径来绕过失败。
- 重测：每次 commit 含 `b89ba4d` / `a6f06af` 等修复时，重跑 ST-01、ST-02、ST-05、ST-09、ST-18；其它按变更范围。
- Regression：每次 release candidate，重跑完整 ST-01..ST-26；新失败 case 阻塞 release。

## 10. Evidence、Traceability、Reporting 与 Gate

- 落档目录：`tests/system/reports/<run-id>/`，包含（按 STD draft.26+ 布局，reports 随 case 同级）：
  - `summary.json`：所有 case 的 PASS/FAIL/BLOCKED/INVALID 计数
  - 每 case 一份 `<id>.json`：命令、stdout、stderr、exit、Oracle diff、duration_ms、commit SHA
  - `env.json`：OS、Python 版本、ulimit、provider endpoint 摘要（不含 secret）
- traceability：每个 case 在本计划里声明其关联的 requirement/contract：
  - ST-01 → CT-OPS-001（health/readiness/restart）
  - ST-02 → CT-BOUNDARY-001 + CT-SCOPE-001（单元测试全绿是 V&V 静态 PASS 基线）
  - ST-03 → CT-SCOPE-001（contract validator）
  - ST-03A → CT-MODEL-001（exact-case，no alias/fallback）
  - ST-04 → CT-SCOPE-001（forbidden path/header absence）+ CT-BOUNDARY-001（无 legacy 暴露）
  - ST-05/ST-06/ST-07/ST-08/ST-09/ST-09A → CT-DP-001（fixed-Pi Responses SSE）
  - ST-10/ST-11/ST-12/ST-12A → CT-EMB-001（embedding float/base64/space/pagination）
  - ST-13/ST-13A/ST-14/ST-15/ST-15A/ST-16 → CT-ADMIN-001（CRUD/probe/secret/If-Match/audit/logs）
  - ST-17 → CT-WEBSEC-001 起点（非 browser E2E）
  - ST-18/ST-19/ST-20 → §5.3 长期并发/性能 / crash+restart
  - ST-21 → §5.3 性能（与 Piko SLA 联调时锁定阈值）
  - ST-22/ST-22A/ST-23/ST-26 → CT-ADM-001（admission / 并发 / FIFO / 429 / request 归属）
  - ST-24/ST-24A/ST-25/ST-25A → CT-WEBSEC-001（auth + TRUSTED_LAN）
- 不落档：任何 `secrets/` 下的文件、生产 prompt/output、provider payload、真实 credential。FAIL 时也只写差异，不重发受 payload 影响的请求。
- Reporting：`summary.json` 上链到 GitHub Actions / 内部 dashboard；FAIL 需附 issue id。
- 签署：LLMTier author + operator +（若涉及 Piko / Slinky 集成）consumer owner；任何 FAIL 需在 summary 附 issue id。
- Gate：本 plan 不授权 `runtime_activation`；`runtime_activation=true` 独立决策前需 ST-19 + ST-20 全 PASS，且真 Piko / 真 Slinky 联调（M5/M6）完成。

## 11. 风险、安全与清理恢复

### 11.1 测试环境隔离

- 每个 ST-XX 在开发机上用 `/tmp/llmtier_system_<uuid>.sqlite3` 独立启服；**不在 m5air 上跑自动化测试**，避免干扰其运行服务。
- 不在 ST 执行期间手动 PATCH m5air production-like 配置；ST-08/ST-22/ST-22A/ST-23/ST-26 的 PATCH-post 列表由 runner 在 teardown 时统一撤销。
- OMLX 进程（`127.0.0.1:9100` on m5air 或 `192.168.1.8:9000` on m5mac）是共享资源；ST-05..ST-09 等使用只读流量，不改 OMLX 配置；如 OMLX 异常 → 全局 BLOCKED，operator 按 `docs/80_operations/m5air-operations-manual.md` §15 恢复。

### 11.2 真实云端调用风险

- ST-15 / ST-16 用真实云端 quota 接口 → 可能计费、可能改变 quota。
- 缓解：ST-15 / ST-16 显式标 `requires_confirm_external_call=true` 路径；operator 单独授权；用 mock provider 跑一遍负例（confirm 缺失 → 400）后再触发真实 refresh。
- 不保存 quota refresh response body 到 evidence；只保存 `provider_id / status / checked_at`。

### 11.3 Secret 与 credential 保护

- 测试固件 secret 写到 `/tmp/llmtier_system_<uuid>_secrets/`、mode 600；不在 evidence 目录里。
- 不打印、不重发受 payload 影响的请求（§10 evidence 只写 oracle diff）。
- operator secret（如 OMLX api_key、provider_minimax api_key）从 m5air `/Users/mlp/LLMTier-dev/secrets/` 借链，不复制到测试 artifacts。

### 11.4 资源限制与清理

- 每个 ST case 在启服后 60 秒 idle 检查 FD baseline ≤ 60（§2.1）；超过 baseline 视为 BLOCKED。
- ST-18 跑后自动回归 FD ≤ 80；ST-19 跑后自动检查 FD 终值 ≤ 200 + 全程无 `Too many open files` 日志。
- teardown：kill 进程、rm 临时 SQLite 与临时 secret 文件、撤销所有 PATCH-post；runner 全局 try/finally 保证 teardown 即便 case 抛错也跑。
- 异常 case（oracle 报错 / sqlite locked / `b89ba4d`/`a6f06af` 缺失）→ 立即停当前 run、保留 evidence、转人工诊断，不自动续跑避免污染后续 case。

### 11.5 当前缺口（与 §9 偏差、§10 签署共同形成 release gate）

- 真 Piko / 真 Slinky 联调未跑：现 Piko / Slinky 集成是 mock-Piko（`tests/fixtures/v03_fake_provider.py`）+ 直接 curl 模拟 Slinky Memory。ST-05..ST-12 仅在 Mock 路径上 PASS，**不能等同于 Piko / Slinky 真实通过的证据**。M5：真 Piko 接入后用 Pi commit `9767ba2` 真实 buildParams 输出替换 ST-05..ST-09 的手写 body；M6：Slinky Memory 端到端替换 ST-10..ST-12。
- 浏览器自动化 E2E、生产 TLS/auth/CSRF、`runtime_activation=true`、多实例 / HA / 跨系统恢复：按 §5.3 单独规划，不在本 plan 范围。
- ST-21 latency 阈值：占位（`P50 ≤ 1.5s / P95 ≤ 3s`），第一次 Piko 联调窗口由 operator 锁定具体数字。
- 本 plan 不是可跑工具集：§5.1 的 runner 与 per-case 脚本尚未实现；PR 阶段用 `bash` + `ssh m5air` 直接跑。实施计划见 §5.1。