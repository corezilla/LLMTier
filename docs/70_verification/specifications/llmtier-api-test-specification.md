<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 API Test Specification

> STD 使用入口：[项目采用说明与标准导航](../../00_management/standards/README.md)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-api-test-specification` |
| Document Version | `0.3.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-28` |
| Last Modified Date | `2026-09-28` |
| Template ID | `assurance.test-specification` |
| Template Version | `0.2.1` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/llmtier-api-test-specification.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. 目标、范围与被测对象

**本节目的**：固定本规格验证哪一组外部 HTTP 行为的设计保证，以及结论边界。

**被测保证**：LLMTier V0.3 对外的 **HTTP API 契约**——路径、方法、认证角色（`data` / `admin` / 无认证）、正常载荷、边界与负向行为、统一错误信封 `{error:{message,type,category,code,param,retryable}}` 与稳定错误码、SSE 事件序列、分页 cursor 语义。被测对象是**运行中的 LAN 服务**（A 类 = m5air `192.168.1.9:8181`；B 类 = 临时实例），不是静态 OpenAPI 文本，也不是 Web UI / SQLite 文件格式。

**不证明什么**：本规格不证明 Web UI 行为、FD 泄漏、30min 耐久、性能 SLO 校准、上游模型答案质量、上游 provider 的实际推理正确性；这些分别由 `llmtier-test-plan.md` / `llmtier-contract-test-specification.md` / 运维手册承接。**静态契约一致（contract specification STATIC PASS）不等于运行行为 PASS**，反之亦然。

**范围**：全部对外路由（见 §3 Case Matrix）：

- **Data Plane**（`data` token，LAN trust 下可匿名）：`POST /v1/responses`（SSE）、`POST /v1/embeddings`、`GET /v1/models`、`GET /v1/models/{model}`。
- **Usage**（`data` 或 `admin`）：`GET /v1/usage`（`from`/`to` 必填 + cursor 分页）；`DELETE /v1/usage`（仅 `admin`）。
- **Management**（`admin`）：`/v1/providers`（+`{id}`、`{id}/usage`、`{id}/models`）、`/v1/deployments`（+`{id}`）、`/v1/service-levels`（+`{id}`）、`POST /v1/probes`、`/v1/runtime`、`/v1/stats`、`/v1/audit`、`/v1/logs`。
- **Observability**（`admin`）：`/v1/diagnostics`（+`snapshots`/`stats`/`traces`）、`/v1/deployments/{id}/diagnostics`、`/v1/trace/{request_id}`。
- **No-auth**：`GET /healthz`、`GET /readyz`。
- **Alias namespace**：`/tier/admin/v1/*`（Management/Observability 的 6 条诊断/追踪子集，与 `/v1/*` 为同一 handler 的精确别名）。

**接口责任方**：M001（HTTP 入口/鉴权/序列化）、M003（推理编排/适配）、M004（Registry）、M005（观测读）、M006（观测写/注入）、M007（Store）。**设计验证项** `VRC-*`（系统设计）+ 机制 `T-*`（详见 §3）。

## 2. 引用基线、环境与前置条件

**固定基线（可复查来源）**

| 类别 | 基线 | 说明 |
|---|---|---|
| 机器契约 | `interfaces/openapi/llmtier.openapi.json`（OpenAPI 3.1.0） | 路由/方法/请求响应 schema/securitySchemes（`BearerAuth`、`AdminBearerAuth`）的**机器权威** |
| 错误目录 | 系统设计 §7.8（`ERR-*` 八字段 + `<!-- STD_PUBLIC_ERROR_CATALOG_BEGIN -->` 区块） | 错误**类别与调用方行为**权威；wire 信封为 `openapi` `ErrorEnvelope`/`ErrorDetail` |
| 数据/行为 | `docs/20_system_design/llmtier-system-design.md` §5–§7、§11 | 预算、超时、准入、账本、保留 |
| 接口控制 | `docs/60_interfaces/piko-data-plane-control.md`、`slinky-capacity-observation-control.md`、`llmtier-management-control.md` | 各成员的成功/失败条件、错误引用 |
| 机制 | `docs/20_system_design/mechanisms/{inference-stream,access-trust,usage-metering,observability,config-lifecycle}.md` | INC/INV/T-* 可验证断言 |
| 测试规范 | `testing-standard.md`（TS-002 依赖头部、TS-003 LAN IP） | 强制约束 |
| 项目标准 | `docs/std.lock.json`（STD `0.1.0-draft.41`） | 文档/流程基线 |

**环境拓扑（A/B 两班）**

| 环境 ID | 组成 | 用途 |
|---|---|---|
| **A** | m5air `192.168.1.9:8181`（已部署：3 provider / 4 deployment / 7 fixed tier）+ m5air OMLX `192.168.1.9:9000` + m5mac OMLX `192.168.1.8:9000` | 只读/观察/一次性无状态写；不污染 SQLite |
| **B** | 临时 LLMTier 实例：临时端口 + 临时 SQLite（`tests/system/api_test_v03/conftest.py` 的 `llmtier_b` / `llmtier_b_empty` / `llmtier_b_no_auth`），**同机第二个进程** | 创建/修改/删除 provider/deployment/service-level；空库；无鉴权场景；跑完销毁 |

**前置条件（执行前必过，任一不满足 → 整班 BLOCKED/SKIP）**

1. A 类：m5air `/healthz` 200 且 `status="ok"`；`/readyz` 200 且含 7 个 fixed tier（`Senior/Junior/Worker/Associate/Engineer/Executor/Embedding-v1`）。
2. A 类：m5air/m5mac OMLX `GET /models` 200（`Bearer 9832`）；`provider_omlx_m5mac.has_secret=true` 且 `secret_ref` 为 `file:`（非 `env:`）。
3. B 类：临时实例可启动并 `GET /healthz` 200；fixture 注入 3 provider + 4 deployment（service-levels 由 bootstrap 建立）。
4. TS-003：**所有 provider endpoint 必须使用 LAN IP（`192.168.x.x`）**，禁止 `127.0.0.1` 出现在被测服务的上游 endpoint 配置中（B 类临时实例内部 provider endpoint 亦按可解析的 LAN 地址给出）。
5. TS-002：每个 `at_*.py` 文件头部写明 Endpoint / Upstream Provider / Model / Auth。

**复位**：A 类每个写 case 之后必须 teardown（PATCH 恢复原名、DELETE 删除本次创建物）；B 类整班结束 `terminate` 进程并 `rm -rf` 临时目录。执行者必须能核验"无前次残留"（见 §10）。

## 3. Case Matrix

**ID 家族**：`HEALTH-*`（无认证健康/就绪）、`DP-MODELS-*`、`DP-RESP-*`、`DP-EMB-*`、`DP-USAGE-*`（Data Plane）、`ADM-*`（Management）、`OBS-*`（Observability/诊断/追踪/别名）、`AUTH-*`（认证与授权）。**同一 Case 可承接多个规则**，`设计 V` 列给出 `VRC-*`/`T-*`。

列含义：`环境` A/B；`实现/状态` 指仓库现有 `tests/system/api_test_v03/at_*.py` 与执行状态（RUN 已执行 / NOT_RUN 尚未执行 / MISSING 无实现）；`证据/缺口` 指向 Run 记录或缺口的具名承接。Run 结果不在本规格维护。

### 3.1 HEALTH — 无认证公共端点

| Case ID | Requirement / 成员或规则 | 设计 V | 场景 / 输入（前置） | 独立 Oracle（Expected） | 环境 | 实现 / 状态 | 证据 / 缺口 | Priority |
|---|---|---|---|---|---|---|---|---|
| HEALTH-01 | `GET /healthz` 始终存活 | `VRC-API-002`,`T-TRUST-ENDPOINTS` | 无 auth header | 200；`{status:"ok",version:str}` | A | `at_obs_01.py`（旧名 OBS-01）/ RUN | Run | P0 |
| HEALTH-02 | `GET /readyz` 就绪=全部 tier 可用 | `VRC-MGMT-003`,`T-OBS` | 7 tier 均有 ≥1 healthy candidate | 200；`{status:"ready",models[7]}`，`availability=available` | A | `at_obs_02.py`（旧名 OBS-02）/ RUN | Run | P0 |
| HEALTH-03 | `/readyz` degraded | `VRC-MGMT-003`,`T-OBS` | 某 tier 有 candidate 但 `health≠healthy` | 503；`status="degraded"`；该 tier `availability="degraded"` | B | **MISSING**（新增） | fixture：`_BASELINE_SETTINGS` + health=unknown | P1 |
| HEALTH-04 | `/readyz` not_ready（无 deployment） | `VRC-MGMT-003`,`VRC-UTIL-001/002` | `_EMPTY_SETTINGS`，无 provider/deployment | 503；`status="not_ready"`；7 tier `availability="unavailable"` | B | `at_obs_03.py`（旧名 OBS-03）/ RUN | Run | P0 |
| HEALTH-05 | `/readyz` bootstrap 失败 | `VRC-MGMT-003`,`VRC-UTIL-001/002` | 非法 settings（`app.bootstrap_error` 非空） | 503；`{status:"not_ready",models:[]}` | B | **MISSING** | `ERR-BOOT`/`ERR-SCHEMA` 路径 | P1 |
| HEALTH-06 | 健康端点无需鉴权 | `T-TRUST-NOCFG`,`T-AUTH-ANY` | `_NO_AUTH_SETTINGS` 实例，无 token | `/healthz`、`/readyz` 不返回 401/403/`auth_not_configured` | B | **MISSING** | 与 AUTH-07 对照 | P1 |

### 3.2 DP-MODELS — 逻辑模型清单

| Case ID | Requirement / 成员或规则 | 设计 V | 场景 / 输入（前置） | 独立 Oracle（Expected） | 环境 | 实现 / 状态 | 证据 / 缺口 | Priority |
|---|---|---|---|---|---|---|---|---|
| DP-MODELS-01 | `GET /v1/models` 列出全部可见 tier | `VRC-INF-002`,`T-LEVEL` | m5air 现有 state | 200；`object="list"`；`data[7]`，含 `Embedding-v1` | A | `at_dp_models_01.py` / RUN | Run | P0 |
| DP-MODELS-02 | `GET /v1/models/{model}` 精确返回 | `VRC-INF-001/002`,`T-NAME` | `Worker` | 200；`id="Worker"`,`object="model"`,`created`（int unix 秒） | A | `at_dp_models_02.py` / RUN | Run | P0 |
| DP-MODELS-03 | 大小写敏感（小写） | `VRC-INF-001`,`T-NAME` | `worker` | 404；`code="model_not_found"` | A | `at_dp_models_03.py` / RUN | Run | P0 |
| DP-MODELS-04 | 大小写敏感（全大写） | `VRC-INF-001`,`T-NAME` | `WORKER` | 404；`code="model_not_found"` | A | `at_dp_models_04.py` / RUN | Run | P1 |
| DP-MODELS-05 | URL 编码尾空格不匹配 | `VRC-INF-001`,`T-NAME` | `Senior%20` | 404；`code="model_not_found"` | A | `at_dp_models_05.py` / RUN | Run | P1 |
| DP-MODELS-06 | 不存在模型 | `VRC-INF-001`,`T-NAME` | `NonExistent` | 404；`code="model_not_found"` | A | `at_dp_models_06.py` / RUN | Run | P0 |
| DP-MODELS-07 | capabilities 固定 12 键 | `VRC-INF-002` | `GET /v1/models` | 每项 `capabilities` 键集 = `CAPABILITY_KEYS`（12，缺/多即 FAIL） | A | `at_dp_models_07.py` / RUN | Run | P1 |

### 3.3 DP-RESP — Responses（SSE）

实现约束：body 必填 `model`/`input`/`stream`/`store`；`stream` 必须 `true`、`store` 必须 `false`；`previous_response_id`/`conversation`/`prompt_cache_*` 等为禁字段（系统 `ERR-REQ-UNSUPPORTED`/`ERR-REQ-FIELD`）。

| Case ID | Requirement / 成员或规则 | 设计 V | 场景 / 输入（前置） | 独立 Oracle（Expected） | 环境 | 实现 / 状态 | 证据 / 缺口 | Priority |
|---|---|---|---|---|---|---|---|---|
| DP-RESP-01 | 流式成功 + 事件序列 | `VRC-INF-001`,`T-STREAM` | `model=Worker,input="Hello",stream=true,store=false` | 200 `text/event-stream`；`response.created→output_item.added→output_text.delta×N→output_text.done→output_item.done→response.completed(status=completed)→[DONE]`；`usage.{input,output,total}_tokens` 非 null；`sequence_number` 自 0 严格递增 | A | `at_dp_resp_01.py` / RUN | Run | P0 |
| DP-RESP-02 | `stream=false` 被拒 | `VRC-INF-001`,`ERR-REQ-UNSUPPORTED` | 同 01 但 `stream=false` | 400；`code="unsupported_request"` | A | `at_dp_resp_02.py` / RUN | Run | P0 |
| DP-RESP-03 | 推理任务结果（数字串） | `VRC-INF-001`,`T-STREAM` | `input="Calculate 15 * 23 + 45 step by step"` | 200；`output_text` 含 `"390"`（不依赖文字写法）且含 `"15"`/`"23"` | A | `at_dp_resp_03.py` / RUN | Run | P1 |
| DP-RESP-04 | tools 透传 | `VRC-INF-001`,`T-TOOLS` | 合法 `tools=[{type:function,name:get_weather,parameters:{…}}]` | 200；SSE 完整；**不**断言上游是否调用工具 | A | `at_dp_resp_04.py` / RUN | Run | P1 |
| DP-RESP-05 | unknown model 路由失败 | `VRC-INF-004`,`T-ERROR-MAP` | `model="NonExistentModel"` | 404；`code="not_found"`（service-level 查不到先于 model 路由） | A | `at_dp_resp_05.py` / RUN | Run | P0 |
| DP-RESP-06 | `stream=true` 唯一受理形态 | `VRC-INF-001`,`T-STREAM` | `stream=true` | 200；SSE | A | `at_dp_resp_06.py` / RUN | Run | P0 |
| DP-RESP-07 | `store=true` 被拒 | `ERR-REQ-UNSUPPORTED`,`T-OPEN-05` | `store=true` | 400；`code="unsupported_request"` | A | `at_dp_resp_07.py` / RUN | Run | P0 |
| DP-RESP-08 | 缺 `model` | `ERR-REQ-VALIDATION`,`T-OPEN-03` | 无 `model` | 400；`code="invalid_request"`，`param="model"` | A | `at_dp_resp_08.py` / RUN | Run | P0 |
| DP-RESP-09 | 禁字段 `previous_response_id` | `ERR-REQ-FIELD`,`T-OPEN-03` | `previous_response_id="resp_x"` | 400；`code="unsupported_field"` | A | `at_dp_resp_09.py` / RUN | Run | P0 |
| DP-RESP-10 | `max_output_tokens` 截断 | `VRC-INF-001`,`T-STREAM` | `max_output_tokens=10` | 200；以 `response.incomplete` 终止；`incomplete_details.reason="max_output_tokens"` | A | `at_dp_resp_10.py` / RUN | Run | P1 |
| DP-RESP-11 | 注入上游 502 → `provider_failure` | `VRC-DIAG-004`,`T-OBS-INJECT`,`ERR-PROVIDER-INJECTED` | 先 PATCH 该 deployment 注入 `fault_502`，再请求；结束清理注入 | 502/503；信封 `code="provider_failure"`,`retryable=true`；trace 记 `source=injected` | B | `at_dp_resp_11.py` / 由 SKIP 转 RUN（需注入，见 §5） | Run | P0 |
| DP-RESP-12 | `conversation_id` 静默忽略 | `VRC-INF-001` | `conversation_id="conv_x"` | 200；SSE 完整（未知非禁字段忽略） | A | `at_dp_resp_12.py` / RUN | Run | P2 |
| DP-RESP-13 | `truncation` 静默忽略 | `VRC-INF-001` | `truncation="auto"` | 200 | A | `at_dp_resp_13.py` / RUN | Run | P2 |
| DP-RESP-14 | `max_tokens` 别名 | `VRC-INF-001` | `max_tokens=50` | 200；按 `max_output_tokens` 处理 | A | `at_dp_resp_14.py` / RUN | Run | P2 |
| DP-RESP-15 | `temperature`/`top_p` | `VRC-INF-001` | `temperature=0.7` | 200（忽略或透传） | A | `at_dp_resp_15.py` / RUN | Run | P2 |
| DP-RESP-16 | 非法 JSON body | `ERR-REQ-JSON`,`T-OPEN-03` | 原始非 JSON 字节 | 400；`code="invalid_json"` | B | **MISSING** | | P1 |
| DP-RESP-17 | embedding-only 等级发 Responses | `ERR-REQ-MODEL` | `model=Embedding-v1` | 400；`code="unsupported_model"`,`param="model"` | A | **MISSING** | | P1 |
| DP-RESP-18 | body 超 2 MB | `ERR-REQ-TOO-LARGE`,`VRC-INF-001` | `input` > 2 MB | 413；`code="request_too_large"` | B | **MISSING** | 预算见系统设计 §11.1 | P2 |
| DP-RESP-19 | 全部候选不健康 | `ERR-MODEL-UNAVAIL`,`VRC-INF-004` | 目标 tier 全部成员 `enabled=false` 或 `health≠healthy` | 503；`code="model_unavailable"` | B | **MISSING** | 需 fixture 改 deployment enabled | P1 |
| DP-RESP-20 | 准入饱和 → 429 | `ERR-RATE-LIMIT`,`T-QUEUE`,`VRC-INF-004` | 并发压满并发许可 + 队列 | 429；`code="rate_limit_exceeded"`；`Retry-After` 存在；零上游副作用 | B | **MISSING** | 并发配额由部署配置决定 | P1 |
| DP-RESP-21 | 客户端中途断开 | `T-DISCONNECT`,`VRC-INF-001` | SSE 发送阶段断开连接 | 出口记 `aborted`；无 terminal；许可释放；账本已在 `create()` 返回前收敛；后续请求可准入 | B | **MISSING** | 见 §5 | P1 |

### 3.4 DP-EMB — Embeddings

| Case ID | Requirement / 成员或规则 | 设计 V | 场景 / 输入（前置） | 独立 Oracle（Expected） | 环境 | 实现 / 状态 | 证据 / 缺口 | Priority |
|---|---|---|---|---|---|---|---|---|
| DP-EMB-01 | 基本 embedding | `VRC-INF-001`,`T-OPEN-04` | `model=Embedding-v1,input="Hello world"`；上游 bge-m3 | 200；`data[0].embedding` 长度 **1024**，全 finite（无 NaN/Inf） | A | `at_dp_emb_01.py` / RUN | Run | P0 |
| DP-EMB-02 | base64 编码 | `VRC-INF-001`,`T-OPEN-04` | + `encoding_format="base64"` | 200；解码为 1024 × little-endian float32 且全 finite | A | `at_dp_emb_02.py` / RUN | Run | P0 |
| DP-EMB-03 | 不变量（同输入 ×5） | `VRC-INF-002`,`T-OPEN-04` | `"Hello world"` 连发 5 次 | 维度全 1024；两两 cosine > 0.99；`embedding_space_id` 一致 | A | `at_dp_emb_03.py` / RUN | Run | P1 |
| DP-EMB-04 | unknown model | `ERR-NOTFOUND`,`T-ERROR-MAP` | `model="NonExistentModel"` | 404；`code="not_found"` | A | `at_dp_emb_04.py` / RUN | Run | P0 |
| DP-EMB-05 | batch 33 不强制上限 | `VRC-INF-002` | `input` = 33 字符串 | 200；`data` 33 项（`embedding_max_batch_inputs` 仅 informational） | A | `at_dp_emb_05.py` / RUN | Run | P2 |
| DP-EMB-06 | `dimensions` 与冻结空间不符 | `ERR-REQ-DIM` | `dimensions=768` | 400；`code="unsupported_dimensions"`,`param="dimensions"` | A | **MISSING** | | P1 |
| DP-EMB-07 | 非法 `encoding_format` | `ERR-REQ-VALIDATION` | `encoding_format="hex"` | 400；`code="invalid_request"` | B | **MISSING** | | P2 |

### 3.5 DP-USAGE — Usage 查询

| Case ID | Requirement / 成员或规则 | 设计 V | 场景 / 输入（前置） | 独立 Oracle（Expected） | 环境 | 实现 / 状态 | 证据 / 缺口 | Priority |
|---|---|---|---|---|---|---|---|---|
| DP-USAGE-01 | 时间窗查询 | `VRC-MGMT-006`,`T-USAGE-VIEW` | `from=now-1h&to=now+1h`（UTC RFC3339） | 200；`data` 为数组；`page` 元数据存在 | A | `at_dp_usage_01.py` / RUN | Run | P0 |
| DP-USAGE-02 | 请求后可见记录 | `VRC-MGMT-006`,`T-MET-FINAL` | 先 DP-RESP-01，再 `from=now-5m&to=now+5m` | 200；`data.length ≥ 1` | A | `at_dp_usage_02.py` / RUN | Run | P1 |
| DP-USAGE-03 | cursor 分页 | `VRC-MGMT-006`,`T-PAGE` | `limit=1` | 200；`data.length ≤ 1`；`page.has_more` 为 bool；`has_more=true` ⇒ `next_cursor` 非空 | A | `at_dp_usage_03.py` / RUN | Run | P1 |
| DP-USAGE-04 | 过期 cursor | `ERR-CURSOR`,`T-PAGE` | 取 cursor `<sid>:<offset>`，将 `query_snapshots.expires_at` 置为过去后复用 | 400；`code="cursor_expired"` | A | `at_dp_usage_04.py` / RUN | Run | P2 |
| DP-USAGE-05 | 缺 `from`/`to` | `ERR-REQ-VALIDATION` | `GET /v1/usage` 无时间窗 | 400；`code="invalid_request"` | A | **MISSING** | | P1 |
| DP-USAGE-06 | 主体隔离：data 只见自身，admin 见全局 | `VRC-MGMT-006`,`T-AUTH-ANY`,`T-USAGE-VIEW` | 同时间窗分别用 `dev-data` 与 `dev-admin` | data 结果 ⊆ admin 结果；admin 可跨 principal | A | **MISSING** | | P1 |

> `DELETE /v1/usage`（清空，admin）归 ADM-USAGE-03。

### 3.6 ADM — Management（Providers / Deployments / Service Levels / Probes / 运行态）

| Case ID | Requirement / 成员或规则 | 设计 V | 场景 / 输入（前置） | 独立 Oracle（Expected） | 环境 | 实现 / 状态 | 证据 / 缺口 | Priority |
|---|---|---|---|---|---|---|---|---|
| ADM-PROV-01 | 列出 providers | `VRC-MGMT-001` | m5air 现有 state | 200；`data[]` 含现有 3 provider；`page.has_more=false` | A | `at_adm_prov_01.py` / RUN | Run | P0 |
| ADM-PROV-02 | 创建 provider | `VRC-MGMT-001`,`T-CONFIG` | 最小 `{name,kind,endpoint,secret_ref,enabled}`；**不得带 `id`** | 201；`id` 自动生成；`has_secret=true`；teardown DELETE | B | `at_adm_prov_02.py` / RUN | Run | P0 |
| ADM-PROV-03 | 获取 provider 详情 | `VRC-MGMT-001` | 现有 `provider_local` | 200；含 `name/kind/endpoint/enabled/has_secret/usage/request_usage/version` | A | `at_adm_prov_03.py` / RUN | Run | P0 |
| ADM-PROV-04 | 不存在 provider | `ERR-NOTFOUND`,`VRC-MGMT-001` | `provider_does_not_exist_xyz` | 404；`code="not_found"` | A | `at_adm_prov_04.py` / RUN | Run | P0 |
| ADM-PROV-05 | 更新 provider | `VRC-MGMT-002`,`T-CFG-CAS` | `PATCH` + `If-Match: "<id>.v<N>"`（带双引号） | 200；新 ETag `"<id>.v<N+1>"`；version+1；teardown 恢复 | B | `at_adm_prov_05.py` / RUN | Run | P0 |
| ADM-PROV-06 | 更新缺 If-Match | `ERR-STALE`,`T-CFG-CAS` | `PATCH` 无 `If-Match` | 412；`code="version_conflict"`；**body 含 `current_version`** | B | `at_adm_prov_06.py` / RUN | Run | P0 |
| ADM-PROV-07 | 过期 ETag | `ERR-STALE` | `If-Match: "<id>.v999"` | 412；`code="version_conflict"` | B | `at_adm_prov_07.py` / RUN | Run | P1 |
| ADM-PROV-08 | 删除 provider | `VRC-MGMT-001` | `DELETE` + 正确 `If-Match` | 204；无 body；teardown | B | `at_adm_prov_08.py` / RUN | Run | P0 |
| ADM-PROV-09 | 删除缺 If-Match | `ERR-STALE` | `DELETE` 无 `If-Match` | 412；`code="version_conflict"` | B | `at_adm_prov_09.py` / RUN | Run | P1 |
| ADM-PROV-10 | 删除被引用 provider | `ERR-INUSE`,`T-CFG-DELREF` | provider 有 active deployment | 409；`code="resource_in_use"` | B | `at_adm_prov_10.py` / RUN | Run | P1 |
| ADM-PROV-11 | `kind` 枚举校验 | `VRC-MGMT-001` | `kind="invalid_kind"` | 400；`code="invalid_request"` | B | `at_adm_prov_11.py` / RUN | Run | P1 |
| ADM-PROV-12 | `secret_ref` 格式 | `T-CFG-SECRET` | `secret_ref="not-a-ref-format"` | 记录实际：当前无格式校验 → 201（**预期=当前行为**，未来收紧需改 case） | B | `at_adm_prov_12.py` / RUN | Run | P2 |
| ADM-PROV-13 | usage 子对象更新 | `VRC-MGMT-002` | `PATCH {"usage":{"max_concurrent_requests":5}}` | 200；usage 子字段更新 | B | `at_adm_prov_13.py` / RUN | Run | P2 |
| ADM-PROV-MODELS-01 | provider 上游模型目录 | `VRC-MGMT-001`,`T-CONFIG` | `GET /v1/providers/{id}/models`（可达 provider） | 200；`{"data":[<model-id>…]}` | A | **MISSING** | 可能触上游（读目录）；失败按 ADM-PROV-MODELS-02 | P1 |
| ADM-PROV-MODELS-02 | 不存在 provider | `ERR-NOTFOUND` | 未知 provider id | 404；`code="not_found"` | A | **MISSING** | | P1 |
| ADM-PROV-USAGE-01 | 读取 provider usage 快照 | `VRC-MGMT-006` | `GET /v1/providers/{id}/usage` | 200；含 snapshot 字段 | A | `at_adm_prov_usage_01.py` / RUN | Run | P1 |
| ADM-PROV-USAGE-02 | 刷新缺确认 | `ERR-CONFIRM` | `POST` body `{}` | 400；`code="invalid_request"`（body 键集必须 `{confirm_external_call}`） | A | `at_adm_prov_usage_02.py` / RUN | Run | P1 |
| ADM-PROV-USAGE-03 | 刷新带确认 | `T-CFG-SECRET` | `{"confirm_external_call":true}` | 200；snapshot 更新 | A | `at_adm_prov_usage_03.py` / RUN | Run | P1 |
| ADM-DEPL-01 | 列出 deployments | `VRC-MGMT-001` | m5air state | 200；`data[]` 含现有 4 deployment | A | `at_adm_depl_01.py` / RUN | Run | P0 |
| ADM-DEPL-02 | 创建 deployment | `VRC-MGMT-001` | body 含 `capabilities` 12 键全集 | 201；`id` 自动生成；teardown | B | `at_adm_depl_02.py` / RUN | Run | P0 |
| ADM-DEPL-03 | 获取 deployment | `VRC-MGMT-001` | `dep_local_gemma` | 200 | A | `at_adm_depl_03.py` / RUN | Run | P0 |
| ADM-DEPL-04 | 更新 deployment | `VRC-MGMT-002` | `If-Match` 正确；allowed 字段 | 200；新 ETag；`provider_id` 不可改 | B | `at_adm_depl_04.py` / RUN | Run | P1 |
| ADM-DEPL-05 | 删除 deployment | `VRC-MGMT-001` | 正确 `If-Match` | 204；teardown | B | `at_adm_depl_05.py` / RUN | Run | P0 |
| ADM-DEPL-06 | capabilities 缺字段 | `VRC-MGMT-001` | 缺任一必填键 | 400；`code="invalid_request"` | B | `at_adm_depl_06.py` / RUN | Run | P1 |
| ADM-DEPL-07 | capabilities 未知字段 | `VRC-MGMT-001` | 含 `unknown_field` | 400；`code="invalid_request"` | B | `at_adm_depl_07.py` / RUN | Run | P1 |
| ADM-DEPL-08 | 引用不存在 provider | `ERR-REQ-VALIDATION` | `provider_id="nonexistent_provider"` | 400；`code="invalid_request"` | B | `at_adm_depl_08.py` / RUN | Run | P1 |
| ADM-DEPL-09 | `provider_id` 不可 PATCH | `VRC-MGMT-002` | `PATCH {"provider_id":…}` | 400；`code="invalid_request"` | B | `at_adm_depl_09.py` / RUN | Run | P1 |
| ADM-SL-01 | 列出 service-levels | `VRC-MGMT-002` | m5air state | 200；`data.length=7`，全 fixed tier | A | `at_adm_sl_01.py` / RUN | Run | P0 |
| ADM-SL-02 | 创建非 fixed tier | `VRC-MGMT-002` | `{"id":"at-test-tier",…}` | 400；`code="invalid_request"` | B | `at_adm_sl_02.py` / RUN | Run | P1 |
| ADM-SL-02b | 创建已存在 fixed tier | `ERR-CONFLICT` | `{"id":"Worker",…}` | 409；`code="resource_conflict"` | B | `at_adm_sl_02b.py` / RUN | Run | P1 |
| ADM-SL-03 | 获取 service-level | `VRC-MGMT-002` | `Worker` | 200 | A | `at_adm_sl_03.py` / RUN | Run | P0 |
| ADM-SL-04 | 更新 service-level | `VRC-MGMT-002` | `If-Match`；`{"enabled":false}` | 200；新 ETag；teardown | B | `at_adm_sl_04.py` / RUN | Run | P1 |
| ADM-SL-04b | 更新非法字段 | `VRC-MGMT-002` | `{"name":"x"}` | 400；`code="invalid_request"` | B | `at_adm_sl_04b.py` / RUN | Run | P1 |
| ADM-SL-05 | 删除 fixed tier | `ERR-FIXED-LEVEL` | `DELETE /v1/service-levels/Worker` | 409；`code="fixed_service_level"` | B | `at_adm_sl_05.py` / RUN | Run | P0 |
| ADM-SL-06 | 成员能力不一致 | `ERR-CAPABILITY`,`T-LEVEL` | PATCH `Senior.deployment_ids` 为能力不同成员 | 409；`code="capability_conflict"` | B | `at_adm_sl_06.py` / RUN | Run | P2 |
| ADM-SL-07 | 冻结向量空间冲突 | `ERR-EMBEDDING-SPACE` | PATCH `Embedding-v1.deployment_ids` 为错误 `embedding_space_id` | 409；`code="embedding_space_conflict"` | B | `at_adm_sl_07.py` / RUN | Run | P2 |
| ADM-PROBE-01 | 探测缺确认 | `ERR-CONFIRM`,`VRC-DIAG-004` | `POST /v1/probes` body `{}` | 400；`code="confirmation_required"` | A | `at_adm_probe_01.py` / RUN | Run | P0 |
| ADM-PROBE-02 | 探测带确认 | `VRC-DIAG-004` | `{"deployment_id":"dep_local_gemma","confirm_external_call":true}`（仅这两键） | 200；`status ∈ {healthy,unhealthy}` | A | `at_adm_probe_02.py` / RUN | Run | P1 |
| ADM-PROBE-03 | 探测未知 deployment | `ERR-NOTFOUND` | 合法 body 但 deployment 不存在 | 404；`code="not_found"` | B | **MISSING** | | P1 |
| ADM-RUNTIME-01 | 运行时快照 | `VRC-INF-004` | `GET /v1/runtime` | 200；含 runtime 快照（准入/健康等） | A | `at_adm_runtime_01.py` / RUN | Run | P1 |
| ADM-STATS-01 | 统计聚合 | `VRC-MGMT-006` | `from`/`to` 时间窗 | 200；含聚合 | A | `at_adm_stats_01.py` / RUN | Run | P1 |
| ADM-STATS-02 | 分组 | `VRC-MGMT-006` | `group_by=tier` | 200；按 tier 聚合 | A | `at_adm_stats_02.py` / RUN | Run | P2 |
| ADM-STATS-03 | 缺时间窗 | `ERR-REQ-VALIDATION` | 无 `from`/`to` | 400；`code="invalid_request"` | A | `at_adm_stats_03.py` / RUN | Run | P1 |
| ADM-AUDIT-01 | 审计事件 + 脱敏 | `VRC-MGMT-003`,`T-EVENT`,`T-TRUST-LEAK` | `GET /v1/audit` | 200；字段齐全；body 不含 secret 字面值（`9832`/key 文件内容） | A | `at_adm_audit_01.py` / RUN | Run | P0 |
| ADM-AUDIT-02 | 审计分页 | `VRC-MGMT-006`,`T-PAGE` | `limit=1` | 200；`data.length=1`；`has_more` bool | A | `at_adm_audit_02.py` / RUN | Run | P1 |
| ADM-LOGS-01 | 脱敏日志 | `VRC-LOG-001`,`T-TRUST-LEAK` | `from`/`to` 时间窗 | 200；不含 secret 字面值 | A | `at_adm_logs_01.py` / RUN | Run | P0 |
| ADM-LOGS-02 | 缺时间窗 | `ERR-REQ-VALIDATION` | 无 `from`/`to` | 400；`code="invalid_request"` | A | `at_adm_logs_02.py` / RUN | Run | P1 |
| ADM-USAGE-01 | 管理面 usage | `VRC-MGMT-006` | `from`/`to` | 200；`data.length ≥ 0`；含聚合 | A | `at_adm_admin_usage_01.py` / RUN | Run | P1 |
| ADM-USAGE-02 | 管理面分页 | `VRC-MGMT-006`,`T-PAGE` | `limit=1` | 200；`data.length ≤ 1`；`has_more` bool | A | `at_adm_admin_usage_02.py` / RUN | Run | P1 |
| ADM-USAGE-03 | 清空 usage（admin + 审计） | `T-MET-RESET`,`T-RESET` | `DELETE /v1/usage`；可选 `?model=`/`?deployment_id=` | 200；`{"deleted":N}`；产生审计事件；data token 调用 → 403 `permission_denied` | A | `at_adm_admin_usage_03.py` / RUN | Run | P1 |

### 3.7 OBS — Observability（诊断/追踪/别名）

| Case ID | Requirement / 成员或规则 | 设计 V | 场景 / 输入（前置） | 独立 Oracle（Expected） | 环境 | 实现 / 状态 | 证据 / 缺口 | Priority |
|---|---|---|---|---|---|---|---|---|
| OBS-DIAG-01 | 读取诊断开关 | `VRC-DIAG-001`,`T-OBS-SWITCH` | `GET /v1/diagnostics` | 200；`SwitchState`（`snapshots_enabled`,`stats_enabled` 为 bool） | A | **MISSING** | | P1 |
| OBS-DIAG-02 | 更新诊断开关 | `VRC-DIAG-001`,`T-OBS-SWITCH` | `PATCH {"snapshots_enabled":true,"stats_enabled":true}` | 200；返回更新后开关；留下审计事件；teardown 恢复 | B | **MISSING** | | P1 |
| OBS-DIAG-03 | 开关更新非法值 | `ERR-REQ-VALIDATION` | `PATCH {"snapshots_enabled":"yes"}` | 400；`code="invalid_request"` | B | **MISSING** | | P2 |
| OBS-SNAP-01 | 快照页（脱敏） | `VRC-DIAG-002`,`T-OBS-SNAP` | `GET /v1/diagnostics/snapshots?since&until` | 200；`SnapshotPage`；不含 secret/正文 | A | **MISSING** | 需先使能 snapshots | P1 |
| OBS-SNAP-02 | 快照无效 cursor | `ERR-CURSOR`,`T-PAGE` | 复用/invalid cursor | 400；`code="cursor_expired"` | B | **MISSING** | | P2 |
| OBS-STATS-01 | 诊断统计窗口 | `VRC-DIAG-002`,`T-OBS-STATS` | `GET /v1/diagnostics/stats?since&until` | 200；聚合窗口 | A | **MISSING** | | P1 |
| OBS-STATS-02 | 统计缺 `since`/`until` | `ERR-REQ-VALIDATION` | 无 `since`/`until` | 400；`code="invalid_request"`（**注意**：诊断面用 `since`/`until`，非 `from`/`to`） | A | **MISSING** | | P1 |
| OBS-TRACE-01 | trace 列表去重 | `VRC-DIAG-002`,`T-OBS-TRACE` | `GET /v1/diagnostics/traces` | 200；按 `request_id` 去重稳定分页 | A | **MISSING** | | P1 |
| OBS-TRACE-02 | trace 列表分页/游标 | `ERR-CURSOR`,`T-PAGE` | `limit=1` + next cursor | 稳定不重不漏；非法 cursor → 400 `cursor_expired` | B | **MISSING** | | P2 |
| OBS-DEPL-01 | 读取 deployment 注入配置 | `VRC-DIAG-004`,`T-OBS-INJECT` | `GET /v1/deployments/{id}/diagnostics` | 200；`InjectionView[]`（`type` 属于 6 类，`enabled` bool） | A | **MISSING** | | P0 |
| OBS-DEPL-02 | 写入故障注入 | `VRC-DIAG-004`,`T-OBS-INJECT` | `PATCH body {"items":[{"type":"fault_502","config":{"error_body":"x"},"enabled":true}]}` | 200；返回注入列表；DP-RESP-11 可命中；teardown `items:[]` 清空 | B | **MISSING** | 与 DP-RESP-11 配套 | P0 |
| OBS-DEPL-03 | 注入未知 deployment | `ERR-NOTFOUND` | 未知 id | 404；`code="not_found"` | B | **MISSING** | | P1 |
| OBS-DEPL-04 | 非法注入项 | `ERR-INJECTION`,`T-OBS-INJECT` | `type="bogus"` 或 `delay.config.delay_ms=999999` | 400；`code="invalid_injection"`，`param` 指向首因 | B | **MISSING** | 取值范围见 `libdiag/injections.py` | P1 |
| OBS-REQTRACE-01 | 请求全生命周期 trace | `VRC-DIAG-002`,`T-OBS-TRACE` | 先 DP-RESP-01，取 `X-Request-ID`，`GET /v1/trace/{request_id}` | 200；`TraceView` 含 `received`…`completed` 阶段 | A | **MISSING** | | P1 |
| OBS-REQTRACE-02 | 未知 request_id | `ERR-NOTFOUND` | 未知 `req_*` | 404；`code="not_found"` | A | **MISSING** | | P1 |
| OBS-ALIAS-01 | 别名 `GET /tier/admin/v1/diagnostics` | `VRC-DIAG-001`,`T-AUTH-ANY` | admin token | 200；body 与 `/v1/diagnostics` **逐字节等价** | A | **MISSING** | | P1 |
| OBS-ALIAS-02 | 别名 `GET /tier/admin/v1/diagnostics/snapshots` | `VRC-DIAG-002` | admin token + 时间窗 | 200；与 `/v1/diagnostics/snapshots` 等价 | A | **MISSING** | | P2 |
| OBS-ALIAS-03 | 别名 `GET /tier/admin/v1/trace/{request_id}` | `VRC-DIAG-002` | admin token，已知 request_id | 200；与 `/v1/trace/{request_id}` 等价 | A | **MISSING** | | P2 |
| OBS-ALIAS-04 | 别名 `PATCH /tier/admin/v1/deployments/{id}/diagnostics` | `VRC-DIAG-004` | admin token，body `{"items":[…]}` | 200；与扁平路径同 handler；teardown 清空 | B | **MISSING** | 别名集共 6 条，见 openapi `x-llmtier-contract-aliases` | P2 |

### 3.8 AUTH — 认证与授权

实现约束：未配置鉴权 → 503 `auth_not_configured`；缺凭据 → 401 `authentication_required`；凭据无权 → 403 `permission_denied`；LAN trust 下 RFC1918 客户端可无 token。

| Case ID | Requirement / 成员或规则 | 设计 V | 场景 / 输入（前置） | 独立 Oracle（Expected） | 环境 | 实现 / 状态 | 证据 / 缺口 | Priority |
|---|---|---|---|---|---|---|---|---|
| AUTH-01 | Data 端点 LAN trust 无 token | `T-TRUST-LAN`,`VRC-API-002` | `GET /v1/models`，`LLMTIER_TRUSTED_LAN_MODE=1`，来源 192.168.x | 200 | A | `at_auth_01.py` / RUN | Run | P0 |
| AUTH-02 | 错误 bearer | `ERR-AUTH-DENIED` | `Authorization: Bearer bogus-token-xxx` | 403；`code="permission_denied"` | A | `at_auth_02.py` / RUN | Run | P0 |
| AUTH-03 | Data token 访问 admin 面 | `ERR-AUTH-DENIED`,`T-ROLE` | `Bearer dev-data` + `GET /v1/providers` | 403；`code="permission_denied"` | A | `at_auth_03.py` / RUN | Run | P0 |
| AUTH-04 | Admin 端点 LAN trust 无 token | `T-TRUST-LAN` | `GET /v1/providers` 无 header，来源 192.168.x | 200 | A | `at_auth_04.py` / RUN | Run | P0 |
| AUTH-05 | 公共端点无需 token | `T-TRUST-NOCFG` | `GET /healthz` 无 header | 200 | A | `at_auth_05.py` / RUN | Run | P0 |
| AUTH-06 | 空 bearer | `ERR-AUTH-DENIED` | `Authorization: Bearer ""`（urllib 直发） | 403；`code="permission_denied"` | A | `at_auth_06.py` / RUN | Run | P2 |
| AUTH-07 | 未配置鉴权 | `ERR-AUTH-NOCFG`,`VRC-MGMT-003`,`T-TRUST-NOCFG` | `_NO_AUTH_SETTINGS`，`DEV_MODE=0`，无 token | 503；`code="auth_not_configured"` | B | `at_auth_07.py` / RUN | Run | P0 |
| AUTH-08 | 别名命名空间需 admin | `T-ROLE`,`T-AUTH-ANY` | data token → `/tier/admin/v1/diagnostics` | 403；`code="permission_denied"` | A | **MISSING** | | P1 |
| AUTH-09 | 管理面未授权优先于资源存在性 | `ERR-AUTH-DENIED`,`T-TRUST-LEAK` | data token → 不存在的 provider id | 403（**不**泄露 `not_found`） | A | **MISSING** | | P1 |

**Case 计数**：HEALTH 6 + DP-MODELS 7 + DP-RESP 21 + DP-EMB 7 + DP-USAGE 6 + ADM 50 + OBS 19 + AUTH 9 = **125 个 Case**（RUN 88 / MISSING 37，见 §7/§8）。

## 4. 正常、边界、负向与并发场景

**正常（happy path，独立 Oracle）**

- DP-RESP-01：SSE 事件**顺序与 identity**（INV-1）+ 恰好一个 terminal + `[DONE]`（INV-2）+ `sequence_number` 严格递增；不是"HTTP 200 即通过"。
- DP-EMB-01/02/03：维度 1024、base64 严格解码、同输入不变量（cosine > 0.99）。
- ADM CRUD 正常流（ADM-PROV-02/05/08、ADM-DEPL-02/04/05、ADM-SL-04）：201/200/204 + ETag `"<id>.v<N>"` 推进 + teardown。
- HEALTH-02：`ready` 判定。
- OBS-DEPL-02 → DP-RESP-11 → OBS-DEPL-02 清空：注入命中并回收。

**边界**

- 大小写与 URL 编码（DP-MODELS-03/04/05）；`limit` 取 1（DP-USAGE-03、ADM-AUDIT-02、ADM-USAGE-02）；`max_output_tokens=10`（DP-RESP-10）；batch 33（DP-EMB-05）；`context_window` 极大不可用普通 input 触发（DP-RESP-10 注）。
- 数值范围：注入 `delay_ms∈[0,60000]`、`retry_after_sec∈[0,300]`、`stream_terminate_after_events∈[1,10000]`（OBS-DEPL-04）。
- body 上限 2 MB（DP-RESP-18，系统设计 §11.1）。

**负向（拒绝位置 + 零副作用）**

- 校验失败集中在 dispatch 之前（INV-5）：400 `invalid_request`/`unsupported_request`/`unsupported_field`/`invalid_json`/`unsupported_model`/`unsupported_dimensions`；413 `request_too_large`。
- 认证失败 `authentication_required`/`permission_denied`/`auth_not_configured`（AUTH-*）。
- 资源与并发：404 `not_found`/`model_not_found`、409 `resource_conflict`/`capability_conflict`/`embedding_space_conflict`/`fixed_service_level`/`resource_in_use`、412 `version_conflict`、400 `cursor_expired`/`invalid_injection`/`confirmation_required`。
- 上游：502/503 `provider_unavailable`/`provider_error`/`provider_failure`/`provider_secret_unavailable`/`provider_contract_error`；504 超时；`model_unavailable`；429 `rate_limit_exceeded` + `Retry-After`。
- **拒绝即无副作用**：无上游 dispatch、无账本义务；需以 usage/runtime/trace 交叉核对（例如 DP-RESP-20 后 `GET /v1/usage` 无新增 obligation）。

**并发**

- DP-RESP-20：并发请求共享同一 tier 的**准入许可与队列**（非独立资源），断言 429 只发生在饱和时、`Retry-After` 存在、前序成功请求账本各归各 principal。禁止用不同 Case ID 假定隔离。
- ADM-PROV-05/06/07：并发编辑以 `If-Match` / 412 串行化；两写者同 version 只能一个成功。
- OBS-DEPL-02 + 并发推理：注入配置变更与在途流的关系按 §5 定义，不假设原子。

**LLM 判据**：所有 Responses 断言基于**结构/事件序列/可复现字符串**（如数字 `"390"`），不写"答案正确"；temperature/top_p 不参与断言。

## 5. Recovery、重放、幂等与故障注入

**故障注入入口**：`PATCH /v1/deployments/{id}/diagnostics`（M006），`items[].type ∈ {fault_502, fault_503, delay, rate_limit, stream_terminate, malformed_event}`；前置阶段优先级 `fault_502→fault_503→rate_limit→delay`，流阶段 `stream_terminate→malformed_event`；撤销 = PATCH 同 `type` `enabled=false` 或 `items:[]`。每个注入 Case 必须**证明命中**（响应状态/错误码/trace `source=injected`），否则判 INVALID。

| 场景 | Case | 注入/触发 | 期望终态 | 撤销/证据 |
|---|---|---|---|---|
| 上游 502 | DP-RESP-11 | `fault_502` | `provider_failure`，`retryable=true`，trace `injected`；账本按 measured/unknown 收敛，不写成 0 | 清空 items；trace + usage 交叉核对 |
| 上游 503 | （扩展 `fault_503`） | `fault_503` | `provider_unavailable`/`provider_error` | 同上 |
| 上游延迟/首字节超时 | `delay` + 超时预算 | `delay` | 适配层超时 → `provider_unavailable`；不在本规格强制时点（§6） | 清除 delay |
| 流中途终止 | `stream_terminate` | 达到 `stream_terminate_after_events` | 无终端 `response.completed`，consumer 可判失败；不产生半个成功 | 清空；对照 INV-2 |
| 畸形事件 | `malformed_event` | `invalid_json`/`unknown_event_type` | 流被终止，记为失败而非成功 | 清空 |
| 客户端断开 | DP-RESP-21 | 客户端在 SSE 发送阶段断开 | 出口记 `aborted`；无 terminal；许可释放；账本已在 `create()` 返回前收敛 | 服务端 trace；后续请求可正常准入 |

**重放/幂等**

- 本版本**不定义**自定义 model-call recovery/exactly-once。测试标准 client 在 429/502/503 下的 retry（尊重 `Retry-After`），**不声称 exactly-once**；同一 `request_id` 的 usage **版本不累计**（追加式，head 单调）。
- 分页重放：同一 cursor 重放返回同一冻结的 record version 成员（`query_snapshots`），cursor 绑定 principal + 授权 + 原 filter（`T-QUERY-SNAPSHOT`）。
- 配置重放：`If-Match` 412 后重新 GET 取新 ETag 再 PATCH（不覆盖）。
- 进程 crash/restart 后：已登记 unknown 义务仍可查，不回填为 0（`T-MET-CRASH`）——归运维/系统测试，引用 `llmtier-test-plan.md`。

## 6. 性能、容量、功耗或时序测试

**适用性**：功耗/FPGA 硬件时序**不适用**（纯软件）。本规格只定义**时序/预算类可观察断言**，不发布 SLO 结论：

- SSE 首字节与流完成：inference smoke 记录 `elapsed`；DP-RESP-01 不设固定 ms 门限。
- 准入：队列上限 32、排队上限 30 s、并发许可按部署配置；DP-RESP-20 观测 429 + `Retry-After`（`ERR-RATE-LIMIT` 预算）。
- 超时：上游建连/首字节/流空闲超时按系统设计 §5.3；`delay` 注入用于命中超时路径。
- 账本/分页：`limit` 与 cursor 稳定排序 `(recorded_at, request_id)`（`VRC-MGMT-006`）。
- 采样方法：同一 A 环境下固定 prompt/model/时间窗；记录并发度与输入规模；**Modeled/Simulated ≠ Measured**，本规格不将 smoke 计时当容量结论。
- 容量压测（FD 泄漏、30min 耐久、50 并发）在 `llmtier-test-plan.md` ST-18/ST-19/ST-21，本规格只引用不重复。

## 7. 执行步骤与自动化入口

**运行位置**：执行机 = m5air（A 类直连本机实例；B 类同机第二个进程）。**TS-003：禁止 `127.0.0.1` 作为被测服务上游 endpoint。**

**准备 / 就绪检查（§2 前置）**：`pytest_configure` 执行 5 项（`conftest.py`）；任一失败 → 整班 skip（BLOCKED/SKIP）。

**入口（命令）**

```bash
# 全量（A 类 + B 类同目录）
PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/ -q

# 单个 Case（文件名对应 Case ID）
PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_resp_01.py -v

# A 类 runner / B 类 runner
bash tests/system/api_test_v03/runner_a.sh
bash tests/system/api_test_v03/runner_b.sh

# Data Plane 端到端 smoke（非替代断言，只验建连与骨架）
python3 tools/inference_smoke.py --base http://192.168.1.9:8181

# 全 21 端点 status-only smoke（手动）
python3 tools/api_smoke_test.py

# 本地假上游（TS-003：provider endpoint 用 LAN IP，见下）
PYTHONPATH=src python3 tests/fixtures/v03_fake_provider.py --port 9191
PYTHONPATH=src python3 tests/integration/v03_smoke.py
```

**步骤模板**：① 就绪检查 → ② 发送请求（curl/httpx）→ ③ 校验 HTTP status → ④ 校验 body 关键字段与 error `code` → ⑤ SSE 需校验事件序列与 terminal → ⑥ teardown → ⑦ 记录 Run（命令、exit code、stdout/stderr、产物路径）。**自动化必须检查动作命中**；环境缺失应 BLOCKED，不得静默改用模拟路径声称真实通过。

**Case ↔ 文件映射**：`at_<family>_<seq>.py`；`HEALTH-*` 由 `at_obs_01..03.py` 承接（旧 ID OBS-01..03）。`OBS-ALIAS-*`/`ADM-PROV-MODELS-*`/`DP-RESP-16..20`/`DP-EMB-06..07`/`DP-USAGE-05..06`/`ADM-PROBE-03` 为 MISSING，见 §3 与 §8。

## 8. Pass/Fail/Blocked/Invalid 判定

| 状态 | 判定 | 阻塞 release | 报告必含 |
|---|---|---|---|
| **PASS** | HTTP status + body 关键字段 + error `code`（+ SSE 事件序列无误、terminal 唯一、`[DONE]`）全部 match | 否 | — |
| **FAIL** | 断言不符：status/字段错、error code 不符、SSE 序列断裂、terminal 缺失或重复、注入已命中但行为不符 | 是 | 预期 vs 实际、`reproduction_cmd`、`failure_step` |
| **BLOCKED** | 测试代码/契约本身问题（fixture 写不出、断言逻辑错、ISD/OpenAPI 语义不清、注入无法命中） | 是 | `block_reason`、`required_resolution`、`reproduction_cmd` |
| **SKIP** | 环境限制（§2 前置不满足、上游 provider 离线、B 类临时实例不可用） | 否（有上限） | `skip_reason`（引用 §2 检查项）、`fix_owner`、`eta` |
| **INVALID** | 注入未命中却按行为判定、或替代路径冒充真实路径（如错误地用 `127.0.0.1` 或 mock 结果当实测） | 是 | `invalid_reason`、证据缺口 |
| **NOT_RUN** | Case 已定义但本轮未执行（含 MISSING 实现） | 不适用 | 缺口引用（§3） |

**规则**：MISSING ≠ NOT_RUN；无实现是缺口，不是跳过。N/A 需裁剪依据（如功耗）。**SKIP 上限**：A 类 ≤ 5、B 类 ≤ 3；超出视为覆盖不足，须补 fixture/注入后重跑。**禁止**"未跑"无状态：runner 必须为每个执行项给出明确状态。**跨 backend 隔离**：A 类 PASS 不关闭 B 类；静态 contract PASS 不关闭运行保证。

## 9. Artifact、日志、测量与证据保存

- **Run ID**：`<date>/<class>-<phase>`（如 `2026-09-28/A-api`、`2026-09-28/B-api`）。
- **固定输入**：prompt、model、时间窗、注入项、If-Match ETag 字面值、fixture settings；随 Run 存档。
- **原始输出**：命令、HTTP status/headers、body、SSE 逐帧、exit code、耗时；失败现场保留不截断。
- **环境快照**：m5air 部署版本、`/healthz`/`/readyz` 响应、provider/deployment 列表、`tools/api_smoke_test.py` 输出。
- **保存位置**：`tests/system/reports/<date>/`（沿用现有约定）；本规格的 Case ↔ Run 对应表在 Run 报告中维护。
- **重跑**：生成新 Run，不覆盖旧失败，不把未运行项目补造为成功。
- **保密**：不保存 Secret/凭据/完整 provider payload；脱敏规则见 §10。

## 10. 安全、清理与可重复性

- **凭据**：测试用 `dev-data`/`dev-admin`/`9832` 为本地开发凭据，不出现在证据中作为"秘密"；真实 Secret 绝不出现在日志/审计/证据（ADM-AUDIT-01、ADM-LOGS-01 显式断言不含 `9832` 与 key 文件内容）。
- **探针/费用**：`POST /v1/probes`、`POST /v1/providers/{id}/usage`、`GET /v1/providers/{id}/models` 可能触上游或产生费用——必须显式 `confirm_external_call`（provider-models 按只读目录处理并记录）；执行者需授权。
- **清理**：A 类每个写 Case teardown（恢复字段/删除本次创建物）；B 类整班销毁临时实例与临时 SQLite；注入配置 `items:[]` 清空后才离开。
- **复用性**：清理后下一轮可核验初态（§2 前置 + `/readyz`）；不得删除 m5air 既有 provider/deployment/service-level 或用户 usage。
- **隔离**：B 类不与 A 类共享 SQLite/端口；测试进程退出 ≠ 设备停止（B 类须显式 `terminate` 并等待）。
- **不可安全释放时**：保留证据并报告 BLOCKED（例如 B 类进程无法终止），不做无边界清理。
