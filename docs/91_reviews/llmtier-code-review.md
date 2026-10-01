<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 src/ 代码审查报告（tests.code-review-checklist）

> STD 使用入口：[STD 主说明与执行流程](../../README.md)。这是工程文档标准模板；作者先读入口，再按项目已采用版本读取适用规范和专项指南。

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-code-review` |
| Document Version | `0.1.0-draft.1` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-09-30` |
| Template ID | `review.tests-code-review-checklist` |
| Template Version | `0.1.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/91_reviews/llmtier-code-review.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Review scope、Revision、Inputs 与 Reviewers

### 1.1 审查范围与基线

| 项 | 值 |
|---|---|
| 被审对象 | `src/`（38 个 Python 文件，25 个受控生产单元 + 调试工具/支撑，约 2 844 行） |
| 被审 revision | Git commit `1cc30d9665e7a137fe4f41e35dba7110784dc2ee`（HEAD，提交信息 "fix(test): iteration fix->review->fix loop on all cases"） |
| `openapi` 版本 | `openapi: 3.1.0`；`info.version = 0.3-simplified-candidate.8`（`interfaces/openapi/llmtier.openapi.json`） |
| `schema_version` | `EXPECTED_SCHEMA_VERSION = 2`（`src/util/store.py:14`；DDL 见 `src/util/migrations/001_initial.sql:88`） |
| 工作区状态 | 审查时工作区有 4 个**未提交**的文档/metadata 变更（`docs/std.lock.json`、`docs/std-source-manifest.json`、`docs/70_verification/plans/*.metadata.json`），均**不涉及 `src/`**；本报告结论只绑定上述 commit 的 `src/` 内容。 |
| 被审模块 | M001 `http_api`、M002 `web_ui`（静态位）、M003 `inference`、M004 `management`、M005 `observability`（空占位）、M006 `libdiag`、M007 `util`、M008 `log` |

### 1.2 输入证据（authority 顺序）

1. STD 模板与目录：`/Users/ben/work/STD/templates/review/tests.code-review-checklist.md`，catalog `templates/catalog.json`（`template_versions["review.tests-code-review-checklist"] = "0.1.0"`，catalog_version `0.1.0-draft.72`，模板 SHA-256 `c83bde9fddd55c0f66b2f32df86fedcf10b5fd650cb5111f7698d4951ef1dc6f`）；路径策略 `templates/path-policy.json`、`docs/repository-layout.md`（`91_reviews` = 正式评审包/发现/决定/关闭记录）。
2. 系统设计：`docs/20_system_design/llmtier-system-design.md`（尤其 §7.7 数据库表、§7.8 错误码目录、§7.9/§7.10 账本一致性与 cursor 绑定、§8.1 API）。
3. 模块设计：`docs/40_module_design/{http-api,inference,management,libdiag,log,observability,util,web-ui}-design.md`（§9 接口、§11 安全、§14 测试、§6.8 错误表）。
4. 实现规格（ISD）：`docs/50_implementation_design/*.isd.md`（§4 数据结构、§5 接口、§7 生命周期、§9 VRC）。
5. 机器契约：`interfaces/openapi/llmtier.openapi.json`（`ErrorEnvelope`/`ErrorDetail.code` 枚举、各端点 `security` 与状态码）。
6. 需求与规范：`docs/10_requirements/llmtier-requirements.md`、`docs/10_requirements/llmtier-observability-debug-requirements.md`、`docs/00_management/standards/testing-standard.md`（TS-003）、`docs/00_management/llmtier-implementation-plan.md`（§8 Gate）。
7. 验证方案：`docs/70_verification/unit/llmtier-unit-test-scheme.md`（§3 33 个 VRC → Case 登记）。
8. 测试基线：本机 `PYTHONPATH=src python3 -m pytest tests/ -q` → **584 passed**（审查时，Python 3.14.3）。修复复核后同一命令为 **596 passed**（见 §7/§8）。

### 1.3 审查者

| 角色 | 人员 | 说明 |
|---|---|---|
| Code Reviewer | LLMTier | 逐条对照 §2–§6 检查项 |
| Reviewer（Agent 作者） | opencode/deepseek-v4.1-flash | 本报告生成 |
| Approver | 待指派 | 进入 Approved 时填写 |

## 2. Naming、Public Contract 与上游契约一致性

逐项核对被审源码的公开 API 与设计 §9 / 契约条目。已发现的问题集中登记于 §7；本节给出对账事实。

- [x] **公开函数/方法名与设计 §9 一致**：`Registry`（`bootstrap_settings`/`ensure_fixed_tiers`/`create/get/update/delete_provider|deployment|service_level`/`candidates`）、`AdminService.page/mutate/probe/stats/list_provider_models`、`UsageRecorder.authorize_dispatch/bind_backend/record_provider_request_id/finish/page/reset_usage`、`ResponsesService.create`、`EmbeddingsService.create`、`Router.admit/snapshot`、`DiagnosticsService.*`、`OperationalLog.record/page`、`Store.migrate/transaction/one/all/close` 均可与 ISD §5 逐一对上。证据：`src/management/registry.py:122-388`、`src/management/admin.py:21-128`、`src/inference/usage.py:20-168`、`src/libdiag/diagnostics.py:31-106`。
- [x] **错误码 ∈ openapi `ErrorDetail.code` 枚举**：源码抛出的码（`invalid_request`/`invalid_json`/`request_too_large`/`authentication_required`/`permission_denied`/`auth_not_configured`/`model_not_found`/`not_found`/`resource_conflict`/`resource_in_use`/`version_conflict`/`cursor_expired`/`rate_limit_exceeded`/`provider_unavailable`/`provider_error`/`provider_failure`/`provider_contract_error`/`provider_secret_unavailable`/`model_unavailable`/`usage_store_unavailable`/`internal_error`/`bootstrap_required`/`bootstrap_invalid`/`schema_version_mismatch`/`schema_unknown`/`schema_integrity_failed`/`store_path_unsafe`/`E-UTIL-NESTED-TXN`/`invalid_injection`/`confirmation_required`/`fixed_service_level`/`capability_conflict`/`embedding_space_conflict`）均在 `openapi` 枚举内（`interfaces/openapi/llmtier.openapi.json` `ErrorDetail.code`）。**未发现擅自新建的系统外码。**
- [x] **参数顺序/类型/可空性**：`UsageRecorder.page(principal, cursor, limit=50, admin=False, since, until, model, request_id)` 与 `management.isd.md:671` 一致；路由层 GET `/v1/usage` 显式传 `limit` 缺省 100（`src/http_api/app.py:238`）与 ISD 注记一致。
- [~] **`param` 指向"首个非法字段"**：多数路径满足（`src/http_api/app.py:42,170`、`src/libdiag/injections.py:33-55`、`src/libdiag/settings.py:21`、`src/management/registry.py:126,183,200-207,300,306`）。**但存在未设 `param` 的 `unsupported_field`/`invalid_request`**（`src/inference/responses.py:75,76`、`src/inference/embeddings.py:32`），违反系统 §7.8 `param` 约束 → 见 §7 `CR-PARAM-SPECIFIC`。
- [x] **私有实现细节未暴露**：`_SENSITIVE`、`_usage_values`、`_capability_intersection`、`_provider_ready_in`、`_UnavailableDiagnostics`、`_adapter`、`_secret` 均以下划线私有，未出现在公开契约；`interfaces/openapi` 无内部结构泄漏。
- [x] **公开方法可重入/线程安全**：`Router` 用 `threading.Condition` 保护全部可变共享状态（`src/inference/routing.py:17,76,113`）；`Store` 用 `threading.local()` 每线程一个连接（`src/util/store.py:45,61`）；`Registry`/`AdminService`/`UsageRecorder` 无可变全局状态。无文档声明非并发。
- [x] **过期/替代签名**：无残留旧名；`/tier/admin/v1/*` 与 `/v1/*` 为**并存**契约别名（非旧名），parity 由 `UT-API-011` 覆盖（`src/http_api/app.py:347-376`）。
- [x] **资源所有权/调用顺序与设计 §8 一致**：`authorize_dispatch`→`admit`→`bind_backend`→dispatch→`finish` 顺序与系统 §7.9 / inference.isd 一致（`src/inference/responses.py:95-142`）。
- [~] **单元 Case 与方案 §3 VRC 对账**：33 个 VRC 在 `docs/70_verification/unit/llmtier-unit-test-scheme.md:139-` 均有 Case 登记；本机实跑 584 通过。**但方案 §3 的 VRC 清单仍有一处与本审查相关的覆盖缺口**（admin cursor 非法格式、`param` 具体性）→ 见 §6/§7。

结论：公开契约整体与上游一致；§7 登记的 `param` 具体性与未知字段码位问题是本节的未关闭项。

## 3. Error handling、错误路径与边界

- [x] **每个公开错误路径返回契约错误码**：`Handler._run` 统一信封（`src/http_api/app.py:379-390`），`ApiError`→精确码，`sqlite3.Error`→503 `usage_store_unavailable`，未知异常→500 `internal_error`；`_store_read` 将读路径异常映射为 503（`src/http_api/app.py:134-140`）。
- [x] **无 catch-all + log + 假装成功**：观测写入的 `except Exception`（`src/libdiag/snapshots.py:37`、`stats.py:35`、`traces.py:33`、`retention.py:27`）均为**设计明示的 fail-open 观测路径**（系统 §10.3、`libdiag` 设计），不吞业务错误；`OperationalLog.record` 的 `except Exception: pass`（`src/log/logs.py:25-26`）是日志自身失败兜底，不改变控制流。未发现把失败伪装为成功返回的分支。
- [x] **空/超长/类型/注入输入各有 Case**：空 body→`invalid_json`（`app.py:159-162`）、>2 MB→413（`app.py:157`）、`_int_param` 非整数→400（`app.py:35-42`）、`_optional_boolean` 非 bool→400（`app.py:165-171`）、URL 注入由 `_static` 的 `resolve()` 边界拒绝（`app.py:176-178`）与 SQL 参数化（全程 `?` 占位）覆盖。
- [~] **资源获取失败不部分初始化**：`Application.__init__`（`src/http_api/app.py:94-116`）在 `DiagnosticsService` 构造失败时降级为 `_UnavailableDiagnostics`（F-OBS-4，符合设计 §9 降级语义）；`bootstrap_settings` 失败置 `bootstrap_error` 并阻断业务路由（`app.py:98-101,201`）。**但 `admin.py:23-33` 的 cursor 解析在进入快照校验前即可能抛未捕获 `ValueError`**，绕过了"显式返回契约错误"的兜底 → 见 §7 `CR-ADMIN-CURSOR`。
- [x] **错误返回不改变已提交副作用（roll-forward）**：管理写操作在 `Store.transaction` 内执行、异常回滚（`src/util/store.py:115-132`）；`AdminService.mutate` 原子路径审计与写入同事务（`src/management/admin.py:98-102`）。
- [x] **assertion 失败不调用外部 API**：`AdminService.probe` 先校验 `confirm_external_call is True` 且 body 恰为 `{deployment_id, confirm_external_call}`（`admin.py:114`）后才构造适配器触网；`AccountUsageService.refresh` 同样先 `require(confirm_external_call is True)`（`account_usage.py:158`）。`probe()` 的 `except Exception: return False`（`openai.py:145`）不向上抛，属探活语义。

## 4. Resource、Concurrency 与副作用清理

- [x] **锁/资源获取与释放配对**：`Router.admit` 在 `with self._condition:` 内入队/出队，`except` 移除 ticket 并 `notify_all`（`src/inference/routing.py:107-109`），正常 `finally` 递减 inflight 计数（`routing.py:110-116`）。
- [x] **异常路径也释放**：`Store.transaction` 异常 `rollback`、正常 `commit`（`src/util/store.py:126-132`）；`Handler._run` 的 `finally` 关闭本线程 Store 连接，覆盖正常/异常/断开（`src/http_api/app.py:391-400`，对应设计 `CF-API-FD`）。
- [x] **锁粒度与设计 §10/§5.1 匹配**：单锁 `Condition` + 有界 FIFO 队列（上限 32，`routing.py:77`），等待上限 30 s（`routing.py:75,105`），无多锁嵌套 → 无死锁/锁顺序问题。
- [x] **跨接口副作用异常回滚**：账本追加式模型保证终态失败保留 unknown（`src/inference/usage.py:52-58`、`responses.py:154-158`）；`account_usage.refresh` 用 `atomic=False` 以避免外部调用持写事务（`admin.py:96-104`），外部失败写 `unavailable` 快照（`account_usage.py:169-174`）。
- [~] **并发场景可复现**：`Router` 的队列满/等待超时由 `UT-INF-004/009` 覆盖；**但 `admin.page` cursor 的非法输入未在测试中覆盖**（见 §6）。
- [x] **全局/单例可重入性**：`Store._local` 线程隔离；`Router` 单实例被多请求线程共享但全部状态在锁内；`DiagnosticsService` 单例，`record_*` 均各自开启短事务，无跨请求可变状态。
- [x] **资源泄漏 finally**：Store 连接 `finally close`；SSE 流断开 `BrokenPipeError/ConnectionResetError` 记录 `aborted` 并返回（`app.py:222-224`）。

## 5. Security 与敏感路径

- [x] **鉴权边界显式且不可旁路**：所有受保护端点在路由分派最前调用 `_auth`/`_auth_either`（`src/http_api/app.py:202-248`），无端点绕过；`_auth` 先 `unauthenticated_principal` 再 `authenticate`，`authenticate` 用 `hmac.compare_digest`（`auth.py:56`）。角色映射与契约 `security` 一致（`/v1/stats`、`/v1/runtime`、`/v1/providers/{id}/models|usage` 均需 admin，代码落在 `_auth("admin")` 之后）。
- [x] **权限来源绑定身份而非 URL/参数**：`Principal` 由 `authenticate`/`unauthenticated_principal` 从凭据与 client 地址派生（`auth.py:23-88`），管理操作使用 `principal.principal_id` 作为审计 actor 与 cursor 归属（`admin.py:25,31`），不信任请求参数中的身份。
- [~] **敏感数据不进 stdout/日志/trace**：设计 §9.2 要求"secret 值写日志前脱敏，错误消息不含 secret"。当前 `_SENSITIVE` 仅替换**键名**（`authorization`/`api_key`/`secret` 等），**不替换键名后的值**，导致 `apikey=sk-...`、`api_key: sk-...`、`X-Api-Key: sk-...` 的值仍落库 → 见 §7 `RISK-LOG-1`（既有台账项，本次复核仍复现）。证据 `src/log/logs.py:11`。
- [x] **注入隔离**：LLM 请求 body 经 `ALLOWED_FIELDS` 白名单校验（`responses.py:16-19,76`），禁字段 `FORBIDDEN_FIELDS` 显式拒绝（`:20,75`）；上游 URL 只取 provider `endpoint` 且剥查询串（`responses.py:122-123`）；SQL 全参数化；静态资源 `resolve()` 目录穿越拒绝（`app.py:176-178`）。
- [x] **跨接口不暴露内部权限范围**：401/403 不泄露存在性（`auth.py:48-59`）；管理读接口只返回 `has_secret`/`has_usage_api_key` 布尔（`registry.py:152,222`），不回显引用或明文。
- [x] **失败路径不留下可被重试绕过的半资源**：cursor 失效/跨主体/授权摘要不符分别 400/403（`usage.py:90-95`）；`auth_not_configured` 503 阻止"关闭校验"式绕过（`auth.py:50-51,82-83`）。

## 6. Testability、可观察性与下游测试钩子

- [~] **公开契约可注入替身**：`ResponsesService._test_adapter`（`src/inference/responses.py:26-30`）与 `LLMTIER_SLOW_ADAPTER_DELAY`（`:31-49`）提供替身/时延钩子，无需改业务代码；但 `EmbeddingsService._adapter`（`src/inference/embeddings.py:20-29`）与 `AdminService.probe/list_provider_models` 的适配器构造**无对应注入点**（`admin.py:118,127`），只能经真实网络或 monkeypatch 替换，可测性弱于 Responses 路径。
- [~] **关键路径有 VRC↔Case 登记**：33 个 VRC 在方案 §3 均登记；**但本审查新发现的两个缺口未在方案 §3 覆盖**：① `admin.page` cursor `:<非整数>` 未捕获异常（`UT-MGMT-004/009` 只覆盖"过期/跨 principal"）；② `unsupported_field`/`invalid_request` 的 `param` 具体性与未知字段码位（`UT-INF-001/006` 只断言码值，未断言 `param` 与未知字段归 `unsupported_field`）。
- [x] **运行期/失败期可观测、可断言**：`record_trace`/`capture_snapshot`/`record_latency` 在正常与失败路径均落库（`responses.py:92,102,124,131-139`），`GET /v1/trace/{id}`、`/v1/diagnostics/*` 可断言；观测 fail-open 不吞推理错误（`libdiag/diagnostics.py:46-51`）。
- [x] **单元层可重入**：无全局可变状态；`Store` 线程局部连接使并发测试隔离。
- [~] **测试 Case 与同一基线 commit**：Case 绑定 `0.1.0-draft.2`/`draft.1` 模块设计版本（方案 §3），本报告绑定 commit `1cc30d9`；工作区文档有 4 处未提交变更，需在补 Case 后重新对齐。
- [x] **并发竞态可主动重放**：`Router` 可通过占满队列/制造等待重放 429（`UT-INF-004/009`）。

## 7. Issue Log

| ID | Severity | Finding | Contract Source | Owner | 关闭条件 | Disposition |
|---|---|---|---|---|---|---|
| `RISK-LOG-1` | Medium | `_SENSITIVE` 正则（`src/log/logs.py:11`）只匹配键名，不消费键名后的值；实测 `apikey=sk-abc123secretvalue` → `[REDACTED]=sk-abc123[REDACTED]value`（值 `secretvalue` 泄漏）、`api_key: sk-abc123` → `[REDACTED]: sk-abc123`、`X-Api-Key: sk-live-1234567890` → `X-[REDACTED]: sk-live-1234567890`；`access_key=AKIA123456` 完全不匹配。复现：`OperationalLog.record("info","m","e","apikey=sk-...")` 后查 `operational_logs`。 | 系统 §9.2「Authorization 与 secret 值在写日志前脱敏」；`log-design.md:450` §8.1；`log.isd.md:167-187`；`RISK-LOG-1`（`log-design.md:620`、`log.isd.md:592`，状态 Open） | LLMTier | 扩展 `_SENSITIVE` 使键名后值被吞（如 `(?i)(authorization\|bearer\s+\S+\|(api[_-]?key\|apikey\|secret\|access_key\|access_key_id\|token)\s*[:=]\s*\S+)`→`[REDACTED]`），并新增一组"键名+值"脱敏 Case；`VRC-LOG-001` 通过。 | **Closed**：`_SENSITIVE`（`logs.py:11`）改为 `(?i)(authorization\|bearer\s+\S+\|(?:api[_-]?key\|apikey\|secret\|access[_-]?key(?:_id)?\|token)\s*[:=]\s*\S+)`，键名+值整体替换；回归 `test_api_key_value_redaction`/`test_access_key_value_redacted`/`test_x_api_key_header_value_redacted` 通过；`log-design §8.1/§15.1`、`log.isd §4.3.1/§10.3.1` 已同步为 Closed。 |
| `CR-ADMIN-CURSOR` | High | `AdminService.page` 在 `src/management/admin.py:24` 于进入快照校验**之前**执行 `offset = int(raw_offset or "0")`，且不在 try/except 内。任何形如 `任意前缀:<非整数>` 的 cursor 触发未捕获 `ValueError`，经 `Handler._run`（`src/http_api/app.py:388`）落为 **500 `internal_error`**，而契约要求 400 `cursor_expired`/`invalid_request`。实测：`admin.page(..., cursor="validstyle:abc")` → `ValueError: invalid literal for int()`（未捕获）；`cursor="nonsense"` → 400 `cursor_expired`（正常）。复现：`GET /v1/providers?cursor=x:abc`（需 admin）→ 500。 | `openapi /v1/providers\|deployments\|service-levels` 400 `cursor_expired`；系统 §7.8 `ERR-CURSOR`；`management.isd.md:445,467 T-MGMT-07/08`；系统 §7.10「cursor 绑定 principal、当前授权和原 filter」 | LLMTier | `admin.page` 将 cursor 解析包进 try/except，非法 offset → 400 `cursor_expired`（或 `invalid_request`）；新增 `UT-MGMT-004/009` 负例 `cursor=<sid>:abc`；`VRC-MGMT-004` 通过。 | **Closed**：`admin.py:24-29` 用 `try: offset=int(raw_offset) except ValueError: raise ApiError(400,"cursor_expired",...)`；m5air 实测 `GET /v1/providers?cursor=x:abc` → 400 `cursor_expired`（原 500）；回归 `test_malformed_offset_cursor_is_400_not_500`/`test_non_integer_offset_cursor_is_400_not_valueerror` 通过。 |
| `CR-ADMIN-CURSOR-GUARD` | Medium | `admin.page` 续页 guard（`src/management/admin.py:25-26`）只比较 `snapshot_kind`、`principal_id`、`expires_at`，**不复核** `query_snapshots.authorization_digest` 与 `filter_digest`；`filter_digest` 恒写死 `"all"`（`:31`），使"cursor 绑定原 filter/授权"在管理面分页上失效（用量分页 `usage.py:93-95` 有复核，管理面没有）。复现：篡改/替换为同 principal 的其它筛选 cursor 仍可续页。 | 系统 §7.10「首个页面持久冻结精确 record version，cursor 绑定 principal、当前授权和原 filter」；系统 §7.7.14 `query_snapshots`（`filter_digest`/`authorization_digest` 非空摘要）；`management.isd.md:445,468` | LLMTier | 管理面续页补齐 `authorization_digest`/`filter_digest` 复核，或由 §7.7.14 authority 显式降级管理面语义并同步 `management-design` §6.2.5/T-MGMT-08；新增跨 filter cursor 负例。 | **Closed**：按系统 §7.10（authority）在 `admin.page` 补齐复核——`filter_digest=sha256(kind)`、`authorization_digest=sha256(actor)` 写入首屏并在续页比较；`management-design §6.2.5/§8.5/§7.7` 与 `management.isd §4.6.2/T-MGMT-07/08` 由"仅存储"更正为"复核"；跨 kind/篡改摘要负例 `test_cursor_filter_kind_mismatch_is_400`/`test_cursor_authorization_digest_is_checked` 通过。 |
| `CR-PARAM-SPECIFIC` | Medium | 多个 400 错误未按规定给出指向首个非法字段的 `param`：`src/inference/responses.py:75`（`unsupported_field`，无 `param`）、`:76`（未知字段用 `invalid_request`，无 `param`；按系统 §7.8 `ERR-REQ-FIELD` 应为 `unsupported_field` 且 `param`=未知字段名）、`src/inference/embeddings.py:32`（非法 embedding 请求用 `invalid_request`，无 `param`）。实测 `responses.py:75/76` 生成的 envelope `param:null`。复现：POST `/v1/responses` body 含 `{"unknown_field":1,...}` → 400 `invalid_request` `param:null`。 | 系统 §7.8 `ERR-REQ-VALIDATION`「`param` 指向首个非法字段」、`ERR-REQ-FIELD`「`param`=未知字段名、`additionalProperties:false`」；`openapi` `ResponsesRequest`/`EmbeddingRequest` additionalProperties:false | LLMTier | 未知字段改判 `unsupported_field` 并带 `param=<字段名>`；`FORBIDDEN_FIELDS` 命中同样带 `param`；嵌入非法请求细分到首个非法字段；同步系统 §7.8↔`inference.isd.md:564` 的码位分歧；新增 `param` 断言 Case。 | **Closed**：`responses.py` 未知字段→`unsupported_field`+`param`、禁字段带 `param`；`embeddings.py` 缺字段→`invalid_request`+`param`、未知字段→`unsupported_field`+`param`；单元与 system 用例（`at_dp_resp_09/12/13/14/15`、`at_dp_emb_07`）更新并通过。 |
| `CR-UNKNOWN-FIELD-CODE` | Medium | 系统 §7.8 与 ISD 对"未知字段"的错误码自相矛盾：系统 `ERR-REQ-FIELD` 规定未知字段→`unsupported_field`（`llmtier-system-design.md:2480-2488`），而 `inference.isd.md:564` 步骤④把 `set(body) ⊆ ALLOWED_FIELDS` 失败定义为 `invalid_request`，代码（`responses.py:76`）按 ISD 实现。上层契约（authority）与 ISD 快照不一致，调用方按系统目录处理会判错。 | 系统 §7.8 `ERR-REQ-FIELD`（authority） vs `inference.isd.md:564`、`inference-design.md:935-937` | LLMTier | 二选一并同步：建议向系统 §7.8 语义收敛（未知字段=`unsupported_field`+`param`），更新 ISD/模块设计错误表；`VRC-INF-001` 增加未知字段码断言。 | **Closed**：代码向系统 §7.8 收敛（见 `CR-PARAM-SPECIFIC`）；`inference.isd.md` 步骤④、`inference-design.md` §6.8 错误表已更新为未知字段=`unsupported_field`+`param`。 |
| `CR-BOOTSTRAP-CATCH` | Medium | `Application.__init__`（`src/http_api/app.py:98-101`）只捕获 `ApiError`；若 `bootstrap_settings` 抛**非 ApiError**（如未包裹的 `sqlite3.Error`/`OSError`），进程直接崩溃而非进入 `bootstrap_error`→`not_ready` 路径（设计 §6.1 要求空库/非法 bootstrap 以 `not_ready` 表达并可观测）。当前 `registry.bootstrap_settings` 内部把通用异常包成 `ApiError`（`registry.py:100-101`），故现网路径未触发；但该边界缺少 Case 且在将来引入非 ApiError 异常时会回归。 | 系统 §7.8 `ERR-BOOT`「回滚并保持 not_ready」；§6.1 启动与就绪；`http-api.isd.md:7.1.3 CF-API-LIFECYCLE` | LLMTier | 将 bootstrap 段改为 `except Exception as exc: self.bootstrap_error = exc if isinstance(exc, ApiError) else ApiError(503,"bootstrap_invalid",...)`，或文档明确"bootstrap 只允许抛 ApiError"；新增非 ApiError 注入 Case。 | **Closed**：`app.py:98-104` 增加 `except Exception as exc: self.bootstrap_error = ApiError(503,"bootstrap_invalid",...)`；回归 `test_non_apierror_bootstrap_does_not_crash`（注入 `OSError`）通过。 |
| `CR-EMBEDDINGS-ADAPTER-HOOK` | Low | `EmbeddingsService` 与 `AdminService`（probe/list_models）适配器无注入点（`src/inference/embeddings.py:20-29`、`src/management/admin.py:118,127`），相较 `ResponsesService._test_adapter`（`responses.py:26-30`）可测性不一致，单元测试只能 monkeypatch 类。 | 模板 §6「公开契约可注入替身，无需改业务代码」；`libdiag/observability` 设计 §14 VRC；方案 §3 | LLMTier | 为 embeddings/admin 增加与 Responses 一致的适配器工厂注入点，或文档显式声明"仅 Responses 支持替身"并说明替代测试手段。 | **Closed（部分）**：`EmbeddingsService` 增加 `_test_adapter` 注入点（`embeddings.py:20-23`），回归 `test_test_adapter_hook_bypasses_construction` 通过；`inference.isd` 已同步。`AdminService.probe/list_provider_models` 维持现状（其探活语义按设计已由 `monkeypatch` Provider 类覆盖，见 `test_management_gaps.py`），保留记录：**Open（低）**——如需统一，另开低优先项。 |
| `CR-PROGRESS-COUNT-DRIFT` | Low | `AGENTS.md` 声明测试基线"当前 566 pass"，实际本机为 **584 passed**；文档/规范数字过期，易误导门禁判断。 | `AGENTS.md`（项目规范）；方案 §3 就绪度 | LLMTier | 更新 `AGENTS.md` 测试计数为实测值（584），并在方案 §3 记录基线。 | **Closed**：`AGENTS.md:63` 更新为 **596 pass**（本次修复后实测全基线）。 |

> 未在 §7 登记"已检查/通过"项；§2–§6 的 `[x]` 为通过事实，开放项全部上表。

## 8. Review Decision 与 Test Gate

| 项 | 结论 |
|---|---|
| Review Verdict | `PASS`（修复复核通过；全部 High/Medium 已关闭） |
| 未关闭 BLOCKED 项数 | `0`（无 BLOCKED 级；原 1 项 High `CR-ADMIN-CURSOR` 已 Closed） |
| 是否允许进入测试（plan §3「代码 review 通过」） | `通过`：允许继续执行/回归测试与用例补齐 |
| Reviewer | LLMTier |
| Approver | 待指派 |
| Approval Date | 待填写 |

**结论说明**：

1. 公开契约（命名/签名/错误码集合/鉴权映射）与系统 §7.8、`openapi`、各 ISD 整体一致，未发现擅自新建错误码、私有泄漏或鉴权旁路；错误路径统一信封、异常回滚、资源 finally 释放、fail-open 观测边界均成立。基于此，plan §3「代码 review 通过」**成立**，可进入测试阶段。
2. **原 Top blocker 的处置（均已关闭）**：
   - `CR-ADMIN-CURSOR`（High）：`admin.page` cursor 解析已包 try/except，非法格式返回契约 400 `cursor_expired`；m5air 实测 `GET /v1/providers?cursor=x:abc` → 400（原 500）。
   - `CR-PARAM-SPECIFIC` / `CR-UNKNOWN-FIELD-CODE`（Medium）：`param` 已指向首个非法字段；未知字段统一 `unsupported_field`；系统 §7.8（authority）与 ISD/模块设计错误表已同步。
   - `RISK-LOG-1`（Medium）：`_SENSITIVE` 已键名+值整体脱敏，回归 Case 通过；`log-design §15.1`/`log.isd §10.3.1` 状态 Closed。
3. **其余项**：`CR-ADMIN-CURSOR-GUARD`、`CR-BOOTSTRAP-CATCH`、`CR-PROGRESS-COUNT-DRIFT` 已 Closed；`CR-EMBEDDINGS-ADAPTER-HOOK` 部分关闭（Embeddings 注入点已补；`AdminService` 维持现状，保留低优先 Open 记录）。
4. **回归证据**：`PYTHONPATH=src python3 -m pytest tests/ -q` → **596 passed**（0 fail / 0 error，含 m5air A 类实测用例）；`tests/unit tests/contract` → **390 passed**；`bash -n` 各 runner 干净。
5. **再审查入口**：修复后以 `detect_changes()` 复核影响面；`validate-design --project-root .` → 0 errors。
