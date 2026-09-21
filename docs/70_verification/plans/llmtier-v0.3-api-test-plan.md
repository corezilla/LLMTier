<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 API Test Plan

> STD 使用入口：[项目采用说明与标准导航](docs/00_management/standards/README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-v0.3-api-test-plan` |
| Document Version | `0.3.0-draft.3` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-21` |
| Last Modified Date | `2026-09-21` |
| Template ID | `assurance.test-plan` |
| Template Version | `0.1.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | `llmtier-v0.3-test-plan`, `llmtier-v0.3-vv-plan` |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/plans/llmtier-v0.3-api-test-plan.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. 目标、范围与定位

本文件是 LLMTier V0.3 API 的专项测试计划，聚焦 **HTTP 端点的行为验证**，区别于：

- `llmtier-v0.3-test-plan.md`：ST-01~ST-26 系统测试（部分覆盖 API）
- `llmtier-v0.3-vv-plan.md`：高层 V&V 方法论
- `llmtier-api-reference.md`：API 契约的人类可读说明

**被测范围**：所有 Data Plane、Observation、Admin Management HTTP 端点（见 §3）。

**不在本计划范围**：Web UI、FD 资源、SQLite 持久化、auth mock 单元测试、静态契约验证。

**Case 总数**：68 个（拆分后；详见 §4）。

---

## 2. 测试环境约束

### 2.0 测试执行机 + A/B 类 case 分流

**测试执行机 = m5air (`192.168.1.9:8181`)**。理由：

- 9-20 / 9-21 两轮测试和整个 `api-testing-handoff.md` 都是在 m5air 上做的
- m5air 当前已部署完成，3 provider / 4 deployment / 7 tier 状态完整可用
- m5air OMLX (`192.168.1.9:9000`) 也在本机，无网络依赖

> 注：`llmtier-v0.3-test-plan.md` §2.2 提到 "m5air 不是测试环境"，但那是针对 **ST-18 FD 泄漏 / ST-19 30min 长期 / ST-21 性能压测**这类**会污染服务状态**的 case。HTTP 端点的读 / 一次性写测试不污染 SQLite，且每个写 case 后做 teardown，对 m5air 状态无可观察影响。

68 case 按是否写 m5air 状态分两类：

| 类 | 范围 | 执行方式 | case 数 |
|---|---|---|---|
| **A 类 — 读 / 观察** | OBS-01~02、DP-MODELS-* (6)、DP-RESP-* (9)、DP-EMB-* (4)、DP-USAGE-* (4)、AUTH-* (6)、ADM 类的 GET (providers list/get、deployments list/get、service-levels list/get、audit、logs、runtime、stats)、ADM-PROBE-* (2)、ADM-PROV-USAGE-* (3)、ADM-ADMIN-USAGE-* (2)、ADM-AUDIT-* (2)、ADM-LOGS-* (2)、ADM-RUNTIME-01、ADM-STATS-* (3)、ADM-SL-01/03 (2) | 直接打 m5air 现有实例 | 53 |
| **B 类 — 写操作** | ADM-PROV-* POST/PATCH/DELETE 全集 (6)、ADM-DEPL-* POST/PATCH/DELETE 全集 (3)、ADM-SL-* POST/PATCH/DELETE (5：02/02b/04/04b/05)、OBS-03 (1) | 用**临时 SQLite + 临时端口**启新实例（同一台机器 m5air 上，第二个进程）；teardown 清理 | 15 |

**B 类为什么用临时实例**：B 类 case 会创建/删除/修改 provider/deployment/service-level，如果直接在 m5air 上跑：
- 多次跑可能因为 ID 冲突 / state 累积 导致测试不稳定
- 9-20 报告 ST-13 DELETE 后未清理就影响后续 ST-14
- 临时实例 = 干净起点，跑完即销毁

**A 类为什么直接用 m5air**：所有读操作对状态无影响；用 m5air 真实 state（已包含完整 provider/deployment）省去 fixture 注入；§2.1 检查清单保证可用。

### 2.1 环境就绪检查清单（执行前必过）

每一项必须为 `[OK]`，否则整个 suite skip。

```
[OK] m5air LLMTier /healthz 200
     ssh m5air 'curl -sf http://localhost:8181/healthz'  →  {"status":"ok"}

[OK] m5air LLMTier /readyz 200 + tiers 非空
     ssh m5air 'curl -sf http://localhost:8181/readyz'  →  含 7 个 tier (Senior/Junior/Worker/Associate/Engineer/Executor/Embedding-v1)

[OK] m5air OMLX 端口 9000 健康
     curl -sf http://192.168.1.9:9000/v1/models -H 'Authorization: Bearer 9832'  →  200
     期望至少含 bge-m3, gemma-4-e2b-it-4bit

[OK] m5mac OMLX 端口 9000 健康（如 DP-RESP 走 provider_omlx_m5mac 路径则需要）
     curl -sf http://192.168.1.8:9000/v1/models -H 'Authorization: Bearer 9832'  →  200

[OK] provider_omlx_m5mac.secret_ref 不是 env:OMLX_API_KEY（2026-09-21 上午修复）
     ssh m5air 'curl -sf http://localhost:8181/tier/admin/v1/providers/provider_omlx_m5mac -H "Authorization: Bearer dev-admin" | python3 -c "import json,sys;print(json.load(sys.stdin)[\"has_secret\"])"'  →  True
```

> 注：Python 3.14、LAN trust、TS-003 等约束已经在 m5air 当前部署上成立，不需要每次检查。

### 2.2 Provider / Deployment 路由矩阵

| 逻辑 Tier | 路由 | 上游 Provider | 上游 Endpoint | 上游模型 | 上游 Auth |
|---|---|---|---|---|---|
| Worker / Senior / Junior / Associate / Engineer / Executor | 三选一调度（provider_minimax / provider_local / provider_omlx_m5mac） | 见表 | 见表 | 见 api-testing-handoff.md §3 | Bearer 9832 (omlx) / MiniMax API key |
| Embedding-v1 | 固定 provider_local | provider_local | `http://192.168.1.9:9000/v1` | bge-m3（**1024 维硬断言**） | Bearer 9832 |

**约束**

- `DP-RESP-*` 不指定路由，断言"最终 200 + SSE/JSON 合法"即可。路由由调度器决定。
- `DP-EMB-*` 严格绑定 Embedding-v1 → bge-m3 1024 维。
- 云端 provider_minimax 调用有外部费用；A 类 case 不验其返回值内容，只验 HTTP 200。
- B 类临时实例用 §2.3 fixture 注入。

### 2.3 B 类临时实例的 fixture 注入

每个 B 类 case 在临时实例启动后，按以下最小集注入（用 admin API 而非 SQL）：

```
3 providers: provider_local, provider_omlx_m5mac, provider_minimax
4 deployments: dep_local_gemma, dep_local_bge_m3, dep_omlx_qwen36, dep_minimax_m27
7 service-levels: Senior, Junior, Worker, Associate, Engineer, Executor, Embedding-v1
  （注意：service-levels 只接受 7 个固定 ID 中之一，见 registry.py:292）
```

**secret_ref**：复用 m5air 上已存在的 secret 文件路径。临时实例的 `LLMTIER_DATA_TOKEN`/`LLMTIER_ADMIN_TOKEN` 用 `dev-data`/`dev-admin`（与 m5air 一致）。

---

## 3. API Surface — 完整端点清单

### 3.1 Data Plane

| Method | Path | 说明 | Auth |
|--------|------|------|------|
| `GET` | `/v1/models` | 列出所有可见逻辑模型 | Data Bearer Token |
| `GET` | `/v1/models/{model}` | 获取指定模型（精确大小写） | Data Bearer Token |
| `POST` | `/v1/responses` | 创建模型响应（SSE 流式） | Data Bearer Token |
| `POST` | `/v1/embeddings` | 创建 embedding 向量 | Data Bearer Token |
| `GET` | `/tier/v1/usage` | 当前用户的 token 使用量（分页） | Data Bearer Token |

### 3.2 Observation

| Method | Path | 说明 | Auth |
|--------|------|------|------|
| `GET` | `/healthz` | 健康检查（始终 200） | 无 |
| `GET` | `/readyz` | 就绪检查（依赖部署状态） | 无 |
| `GET` | `/ui/*` | Web UI 静态文件 | 无 |

### 3.3 Admin Management

| Method | Path | 说明 | Auth |
|--------|------|------|------|
| `GET` | `/tier/admin/v1/providers` | 列出所有 provider（分页） | Admin Bearer Token |
| `POST` | `/tier/admin/v1/providers` | 创建 provider | Admin Bearer Token |
| `GET` | `/tier/admin/v1/providers/{id}` | 获取 provider 详情 | Admin Bearer Token |
| `PATCH` | `/tier/admin/v1/providers/{id}` | 更新 provider（**If-Match 必需**） | Admin Bearer Token |
| `DELETE` | `/tier/admin/v1/providers/{id}` | 删除 provider（**If-Match 必需**） | Admin Bearer Token |
| `GET` | `/tier/admin/v1/providers/{id}/usage` | 获取 provider 使用量快照 | Admin Bearer Token |
| `POST` | `/tier/admin/v1/providers/{id}/usage` | 刷新 provider 使用量（**confirm_external_call:true 必需**） | Admin Bearer Token |
| `GET` | `/tier/admin/v1/deployments` | 列出所有 deployment（分页） | Admin Bearer Token |
| `POST` | `/tier/admin/v1/deployments` | 创建 deployment | Admin Bearer Token |
| `GET` | `/tier/admin/v1/deployments/{id}` | 获取 deployment 详情 | Admin Bearer Token |
| `PATCH` | `/tier/admin/v1/deployments/{id}` | 更新 deployment（**If-Match 必需**） | Admin Bearer Token |
| `DELETE` | `/tier/admin/v1/deployments/{id}` | 删除 deployment（**If-Match 必需**） | Admin Bearer Token |
| `GET` | `/tier/admin/v1/service-levels` | 列出所有服务等级（分页） | Admin Bearer Token |
| `POST` | `/tier/admin/v1/service-levels` | 创建 service level（**id 必须在 FIXED_TIERS 内**） | Admin Bearer Token |
| `GET` | `/tier/admin/v1/service-levels/{id}` | 获取 service level 详情 | Admin Bearer Token |
| `PATCH` | `/tier/admin/v1/service-levels/{id}` | 更新 service level（**If-Match 必需**；仅 `deployment_ids`/`enabled` 可改） | Admin Bearer Token |
| `DELETE` | `/tier/admin/v1/service-levels/{id}` | 删除 service level（**If-Match 必需**；7 个固定 tier 拒绝 → 409） | Admin Bearer Token |
| `POST` | `/tier/admin/v1/probes` | 探测 deployment 健康状态（**confirm_external_call:true 必需**） | Admin Bearer Token |
| `GET` | `/tier/admin/v1/usage` | 管理面使用量统计（**需 from/to**） | Admin Bearer Token |
| `GET` | `/tier/admin/v1/audit` | 审计事件列表（分页） | Admin Bearer Token |
| `GET` | `/tier/admin/v1/logs` | 脱敏日志列表（**需 from/to**） | Admin Bearer Token |
| `GET` | `/tier/admin/v1/runtime` | 运行时状态快照 | Admin Bearer Token |
| `GET` | `/tier/admin/v1/stats` | 统计聚合（**需 from/to**；支持 group_by=tier|deployment） | Admin Bearer Token |

#### 3.3.1 If-Match 头格式（必读，9-20 [P7]）

ETag 格式由 `src/llmtier_v03/registry.py:25` 定义：

```python
def _etag(resource_id: str, version: int) -> str:
    return f'"{resource_id}.v{version}"'
```

**注意带双引号** —— PATCH/DELETE 请求必须严格匹配：

```bash
# 1. GET 拿到当前 ETag（响应头 ETag 字段）
ETAG=$(curl -sI http://192.168.1.9:8181/tier/admin/v1/providers/provider_local \
  -H 'Authorization: Bearer dev-admin' | awk -F': ' 'tolower($1)=="etag"{gsub(/\r/,"");print $2}')

# 2. PATCH 带上 If-Match（**值带双引号**）
curl -X PATCH http://192.168.1.9:8181/tier/admin/v1/providers/provider_local \
  -H 'Authorization: Bearer dev-admin' \
  -H "If-Match: $ETAG" \
  -H 'Content-Type: application/json' \
  -d '{"name":"new name"}'
```

期望值示例：`"provider_local.v1"`（双引号 + `.v<N>` 后缀）。

**If-Match 不匹配** → 412 `version_conflict`，**响应 body 必含 `current_version` 字段**（registry.py:156 / 9-20 API-001 已修）：

```json
{"error": {"code": "version_conflict", "message": "Provider version changed", "current_version": 2}}
```

#### 3.3.2 confirm_external_call 必读（9-21 [P4]）

`/tier/admin/v1/providers/{id}/usage` POST 和 `/tier/admin/v1/probes` POST 要求 body 为：

```json
{"confirm_external_call": true, "<其他字段>"}
```

- `Usage refresh`：`confirm_external_call` 必须为 `True`（account_usage.py:151），否则 400 `confirmation_required`
- `Probes`：`confirm_external_call=True` 且 body 仅含 `deployment_id` + `confirm_external_call`（admin.py:106），否则 400 `confirmation_required`
- 注：`/tier/admin/v1/usage` POST 的 body 限制更严（app.py:136）：只接受 `{confirm_external_call}` 单字段

---

## 4. Test Case 矩阵

### 4.1 Observation — 公共端点

| ID | Case | 方法 | 路径 | 预期 | Fixture / 依赖 | 类 |
|----|------|------|------|------|----------------|----|
| OBS-01 | 健康检查始终200 | GET | `/healthz` | 200，body 含 `status: ok` | 无 | A |
| OBS-02 | 就绪检查-正常 | GET | `/readyz` | 200，body 含 `tiers` 列表（7 个固定 tier） | 7 tier = Senior/Junior/Worker/Associate/Engineer/Executor/Embedding-v1 | A |
| OBS-03 | 就绪检查-无部署 | GET | `/readyz` | 200，`tiers` 为空数组 | **B 类临时实例**：启动后不注入 §2.3 fixture；teardown 时 kill 整个临时实例 | B |

### 4.2 Data Plane — Models

| ID | Case | 方法 | 路径 | 预期 | Fixture / 依赖 | 类 |
|----|------|------|------|------|----------------|----|
| DP-MODELS-01 | 列出所有模型 | GET | `/v1/models` | 200，`data[]` 含 7 个 tier | m5air 现有 state；含 `Embedding-v1` | A |
| DP-MODELS-02 | 获取存在的模型 | GET | `/v1/models/Worker` | 200，含 `id="Worker"`、`object="model"`、`created`（unix 秒） | m5air 现有 state | A |
| DP-MODELS-03 | 大小写不匹配拒绝 | GET | `/v1/models/worker` | 404，error `code="model_not_found"` | 大小写敏感 | A |
| DP-MODELS-04 | 全大写拒绝 | GET | `/v1/models/WORKER` | 404，error `code="model_not_found"` | 大小写敏感 | A |
| DP-MODELS-05 | URL编码空格拒绝 | GET | `/v1/models/Senior%20` | 404，error `code="model_not_found"` | URL 解码后为 "Senior "，无此 tier | A |
| DP-MODELS-06 | 不存在的模型 | GET | `/v1/models/NonExistent` | 404，error `code="model_not_found"` |  | A |

### 4.3 Data Plane — Responses

> 实现约束（registry.py / responses.py / sse.py）：
>
> - POST body 必填 `model`, `input`, `stream`, `store`（responses.py:49）
> - `stream` 必须为 `True`，`store` 必须为 `False`（responses.py:50）→ 不满足 400 `unsupported_request`
> - 拒 `previous_response_id`/`conversation`/`truncation` 等 cache/continuation 字段 → 400 `unsupported_field`（responses.py:52）
> - 路由找不到 model → 404 `model_not_found`（responses.py:58 / routing.py:74）

| ID | Case | 方法 | 路径 | 预期 | Fixture / 依赖 | 类 |
|----|------|------|------|------|----------------|----|
| DP-RESP-01 | 流式响应成功 | POST | `/v1/responses` | 200，SSE 完整 | model=Worker，input="Hello"，stream=true，store=false；SSE 序列（**sse.py 真相**）：`response.created` → `response.output_item.added` → `response.output_text.delta` ×N → `response.output_text.done` → `response.output_item.done` → `response.completed`（status=completed） → `data: [DONE]`；`usage.input_tokens/output_tokens/total_tokens` 全部非 null；每帧含 `sequence_number` 单调递增 | A |
| DP-RESP-02 | 非流式响应 | POST | `/v1/responses` | 200，JSON body | 同 DP-RESP-01 但 stream=false；body 含 `output[].content[].text` 与 `usage`；**注意**：当前实现强制 `stream=true`（responses.py:50），传 `stream=false` 会被拒（见 DP-RESP-06）。本 case 预期是**当前实际行为**：stream=false → 400 `unsupported_request`。若实现日后放宽，case 期望需调整 | A |
| DP-RESP-03 | 推理任务 | POST | `/v1/responses` | 200，output_text 含结果与输入数字 | model=Worker，input="Calculate 15 * 23 + 45 step by step"；断言：output_text 含 "390"（**最终结果**，gemma 可能写 "390" 或 "three hundred ninety"——后者会导致 false FAIL，**所以断言用数字串 "390"**）；同时断言含 "15" 和 "23"（输入数字，证明模型看到了输入） | A |
| DP-RESP-04 | tools 参数合法性 | POST | `/v1/responses` | 200，SSE 完整 | **目标：测 LLMTier 透传 tools 给上游，不测上游是否调用工具**。model=Worker，body 含合法 `tools=[{type:function, name:get_weather, parameters:{...}}]`；断言 HTTP 200，SSE 完整，**不**断言是否出现 `function_call_arguments.delta` 事件——这是上游行为 | A |
| DP-RESP-05 | unknown model | POST | `/v1/responses` | 404，error `code="model_not_found"` | model="NonExistentModel" | A |
| DP-RESP-06 | 强制 stream=true | POST | `/v1/responses` | 200 | body `stream=true`（这是 LLMTier **唯一接受**的 stream 取值）；DP-RESP-02 是 `stream=false` 失败的对应 case | A |
| DP-RESP-07 | store:true 被拒绝 | POST | `/v1/responses` | 400，error `code="unsupported_request"` | body `store=true`；store 必须 false | A |
| DP-RESP-08 | 缺少 model 字段 | POST | `/v1/responses` | 400，error `code="invalid_request"` | body 不含 model | A |
| DP-RESP-09 | previous_response_id 被拒绝 | POST | `/v1/responses` | 400，error `code="unsupported_field"` | body 含 `previous_response_id="resp_xxx"`（任意非空字符串） | A |

> **注意**：DP-RESP-01/03/04 依赖上游 Provider 健康（§2.1 检查），不健康 → 对应 case SKIP。

### 4.4 Data Plane — Embeddings

| ID | Case | 方法 | 路径 | 预期 | Fixture / 依赖 | 类 |
|----|------|------|------|------|----------------|----|
| DP-EMB-01 | 基本 embedding | POST | `/v1/embeddings` | 200，`data[0].embedding` 长度=1024，无 NaN/Inf | model=Embedding-v1，input="Hello world"；上游=provider_local bge-m3；维度 1024 硬断言 | A |
| DP-EMB-02 | base64 编码 | POST | `/v1/embeddings` | 200，base64 解码后 1024 个 little-endian float32，全部 finite | 同 DP-EMB-01 + encoding_format="base64" | A |
| DP-EMB-03 | 不变量验证 | POST | `/v1/embeddings` ×5 | 5 次请求维度均为 1024 | 同输入 "Hello world" 连发 5 次；断言：dim 全 1024、两两 cosine similarity > 0.99、`embedding_space_id` 字段一致 | A |
| DP-EMB-04 | unknown model | POST | `/v1/embeddings` | 404，error `code="model_not_found"` | model="NonExistentModel" | A |

### 4.5 Data Plane — Usage

| ID | Case | 方法 | 路径 | 预期 | Fixture / 依赖 | 类 |
|----|------|------|------|------|----------------|----|
| DP-USAGE-01 | usage 可查询 | GET | `/tier/v1/usage` | 200，body 含 `data` 数组与 `page` 元数据；data 可能为空（m5air 历史清空时）或非空 | 时间窗 `from=now-1h&to=now+1h`（UTC RFC3339）；**断言 data 是数组**（不强求空——m5air 上可能有历史 usage） | A |
| DP-USAGE-02 | 有 usage 数据 | GET | `/tier/v1/usage` | 200，`data.length ≥ 1` | m5air 上跑过 DP-RESP-01 后查；时间窗 `from=now-5m&to=now+5m` 紧贴响应时间 | A |
| DP-USAGE-03 | 分页游标 | GET | `/tier/v1/usage?limit=1` | 200，`data.length ≤ 1`，`page.has_more` 为 boolean，`page.next_cursor` 与 `has_more` 同步：has_more=true 时非空 | 时间窗同上 | A |
| DP-USAGE-04 | 过期 cursor | GET | `/tier/v1/usage?cursor=<expired>` | 400，error `code="cursor_expired"` | **fixture**：跑 DP-RESP-01 拿到 cursor=`"sid:offset"`，再 sqlite3 直连 m5air `/Users/mlp/LLMTier-dev/state.sqlite3` 执行 `UPDATE query_snapshots SET expires_at='2020-01-01T00:00:00Z' WHERE snapshot_id='<sid>'`，然后用原 cursor 请求；cursor 格式必须严格是 `"<sid>:<offset>"`（usage.py:62） | A（需要 sqlite3 直连权限） |

### 4.6 Admin — Providers CRUD

| ID | Case | 方法 | 路径 | 预期 | Fixture / 依赖 | 类 |
|----|------|------|------|------|----------------|----|
| ADM-PROV-01 | 列出 providers | GET | `/tier/admin/v1/providers` | 200，`data[]` 含 m5air 现有 3 个 provider，`page.has_more=false` | m5air 现有 state | A |
| ADM-PROV-02 | 创建 provider | POST | `/tier/admin/v1/providers` | 201，`id` 自动生成（hex 16 位），`has_secret=true` | body: `{name, kind, endpoint, secret_ref, enabled}`；**禁止传 `id`**（ProviderWrite schema `additionalProperties:false` 验证）；**禁止传 usage 子对象**（ProviderWrite 仅在 base + usage 嵌套允许；为简化，case 用最小集）；teardown DELETE | B |
| ADM-PROV-03 | 获取存在的 provider | GET | `/tier/admin/v1/providers/{id}` | 200，含 `name`、`kind`、`endpoint`、`enabled`、`has_secret`、`usage.*`、`request_usage.*`、`version` | 用 m5air 现有 `provider_local` | A |
| ADM-PROV-04 | 获取不存在的 provider | GET | `/tier/admin/v1/providers/{id}` | 404，error `code="not_found"` | id="provider_does_not_exist_xyz" | A |
| ADM-PROV-05 | 更新 provider | PATCH | `/tier/admin/v1/providers/{id}` | 200，新 ETag `"<id>.v<N+1>"`，version+1 | **If-Match: `"<id>.v<N>"`**（带双引号，registry.py:25）；body `{"name":"at-updated"}`；teardown 恢复原名 | B |
| ADM-PROV-06 | 更新缺 If-Match | PATCH | `/tier/admin/v1/providers/{id}` | 412，error `code="version_conflict"`，**body 含 `current_version` 字段** | **9-20 API-001 修复点**：若 current_version 缺失 → FAIL（不应再退化） | B |
| ADM-PROV-07 | 更新过期 ETag | PATCH | `/tier/admin/v1/providers/{id}` | 412，error `code="version_conflict"` | If-Match: `"<id>.v999"`（明显过期） | B |
| ADM-PROV-08 | 删除 provider | DELETE | `/tier/admin/v1/providers/{id}` | 204，无 body | If-Match 必需；teardown 必做 | B |
| ADM-PROV-09 | 删除缺 If-Match | DELETE | `/tier/admin/v1/providers/{id}` | 412，error `code="version_conflict"` | 不带 If-Match | B |

### 4.7 Admin — Deployments CRUD

| ID | Case | 方法 | 路径 | 预期 | Fixture / 依赖 | 类 |
|----|------|------|------|------|----------------|----|
| ADM-DEPL-01 | 列出 deployments | GET | `/tier/admin/v1/deployments` | 200，`data[]` 含 m5air 现有 4 个 deployment | m5air 现有 state | A |
| ADM-DEPL-02 | 创建 deployment | POST | `/tier/admin/v1/deployments` | 201，`id` 自动生成，含完整 `capabilities` | body: `{name, provider_id, backend_model, capabilities, enabled}`；**capabilities 必填全集**（registry.py:16 `CAPABILITY_KEYS`，12 个字段）：`{responses, embeddings, tools, structured_outputs, input_modalities, output_modalities, context_window, max_output_tokens, embedding_space_id, embedding_dimensions, embedding_max_batch_inputs, embedding_max_input_tokens}`；缺一个即 400 | B |
| ADM-DEPL-03 | 获取 deployment | GET | `/tier/admin/v1/deployments/{id}` | 200 | 用 m5air 现有 `dep_local_gemma` | A |
| ADM-DEPL-04 | 更新 deployment | PATCH | `/tier/admin/v1/deployments/{id}` | 200，新 ETag | **If-Match: `"<id>.v<N>"`**（带双引号）；body 只含 allowed 字段（`name`/`enabled`/`backend_model`/`capabilities`），其他如 `provider_id` 不在 patch allowed 集合（registry.py:243） | B |
| ADM-DEPL-05 | 删除 deployment | DELETE | `/tier/admin/v1/deployments/{id}` | 204 | If-Match 必需；teardown | B |

### 4.8 Admin — Service Levels CRUD

> 实现约束（registry.py）：
> - service-level id **必须在 FIXED_TIERS 内**（Senior/Junior/Worker/Associate/Engineer/Executor/Embedding-v1）—— 不在则 400 `invalid_request`（registry.py:292）
> - 7 个 FIXED_TIERS **不可删除**——DELETE → 409 `fixed_service_level`（registry.py:334）
> - PATCH 仅 `deployment_ids` / `enabled` 可改（registry.py:316）

| ID | Case | 方法 | 路径 | 预期 | Fixture / 依赖 | 类 |
|----|------|------|------|------|----------------|----|
| ADM-SL-01 | 列出 service-levels | GET | `/tier/admin/v1/service-levels` | 200，`data.length=7`，含全部 7 个 FIXED_TIERS | m5air 现有 state | A |
| ADM-SL-02 | 创建非固定 tier | POST | `/tier/admin/v1/service-levels` | 400，error `code="invalid_request"` | body `{"id":"at-test-tier", "deployment_ids":["dep_local_gemma"], "enabled":true}`；非 FIXED_TIERS 一律拒；**9-21 [P4] 覆盖** | B |
| ADM-SL-02b | 创建 FIXED_TIERS 已存在 | POST | `/tier/admin/v1/service-levels` | 409，error `code="resource_conflict"` | body `{"id":"Worker", ...}`；Worker 已存在 | B |
| ADM-SL-03 | 获取 service-level | GET | `/tier/admin/v1/service-levels/{id}` | 200 | id="Worker" | A |
| ADM-SL-04 | 更新 service-level | PATCH | `/tier/admin/v1/service-levels/{id}` | 200，新 ETag | If-Match 必需；body `{"enabled":false}`（allowed 字段）；teardown 恢复 true | B |
| ADM-SL-04b | 更新非法字段 | PATCH | `/tier/admin/v1/service-levels/{id}` | 400，error `code="invalid_request"` | body `{"name":"x"}`；`name` 不在 allowed patch 字段 | B |
| ADM-SL-05 | 删除 FIXED_TIER | DELETE | `/tier/admin/v1/service-levels/{id}` | 409，error `code="fixed_service_level"` | 不带 If-Match 也行（直接被 FIXED_TIER 逻辑拦）；带 If-Match 同样 409 | B |

> 注：ADM-SL-02 → ADM-SL-02b，ADM-SL-04 → ADM-SL-04b，原 5 个 case 拆成 7 个，最终 case 总数从 57 → 68（详见 §1）；§5.1 顺序表相应调整。

### 4.9 Admin — Probes and Usage

| ID | Case | 方法 | 路径 | 预期 | Fixture / 依赖 | 类 |
|----|------|------|------|------|----------------|----|
| ADM-PROBE-01 | 探测无 confirm | POST | `/tier/admin/v1/probes` | 400，error `code="confirmation_required"` | body `{}` 或 body 含 `deployment_id` 但缺 `confirm_external_call`（admin.py:106） | A |
| ADM-PROBE-02 | 探测带 confirm | POST | `/tier/admin/v1/probes` | 200，含 `status` ∈ {healthy, unhealthy} | body `{"deployment_id":"dep_local_gemma","confirm_external_call":true}`（**仅这两字段**，body 必须 `set() == {"deployment_id","confirm_external_call"}`，admin.py:106） | A |
| ADM-PROV-USAGE-01 | 获取 provider usage | GET | `/tier/admin/v1/providers/{id}/usage` | 200，body 含 snapshot | id="provider_local" | A |
| ADM-PROV-USAGE-02 | 刷新 provider usage 缺 confirm | POST | `/tier/admin/v1/providers/{id}/usage` | 400，error `code="confirmation_required"` | body `{}`；account_usage.py:151 强制 `confirm_external_call=True` | A |
| ADM-PROV-USAGE-03 | 刷新带 confirm | POST | `/tier/admin/v1/providers/{id}/usage` | 200，snapshot 更新 | body `{"confirm_external_call":true}` | A |
| ADM-ADMIN-USAGE-01 | 管理面 usage | GET | `/tier/admin/v1/usage` | 200，`data.length ≥ 0`，含聚合 | 时间窗 `from=now-1h&to=now+1h`（UTC RFC3339） | A |
| ADM-ADMIN-USAGE-02 | 管理面 usage 分页 | GET | `/tier/admin/v1/usage?limit=1` | 200，`data.length ≤ 1`，`page.has_more` 为 boolean | 同上 | A |

### 4.10 Admin — Audit, Logs, Runtime, Stats

| ID | Case | 方法 | 路径 | 预期 | Fixture / 依赖 | 类 |
|----|------|------|------|------|----------------|----|
| ADM-AUDIT-01 | 列出 audit 事件 | GET | `/tier/admin/v1/audit` | 200，字段齐全，**无敏感信息泄露** | m5air 上跑过若干 admin 操作（PATCH provider、POST deployment、刷新 usage）会留下 audit；**断言响应 body 不含 secret 字面值 "9832"、不含 .mnm_api_key 文件内容、不含 omlx-secret-key.txt 字面值**（**9-21 [P1]** 思路） | A |
| ADM-AUDIT-02 | audit 分页 | GET | `/tier/admin/v1/audit?limit=1` | 200，`data.length=1`，`page.has_more=true` | m5air 上有 audit 历史 | A |
| ADM-LOGS-01 | 列出 logs | GET | `/tier/admin/v1/logs?from=...&to=...` | 200，**无敏感信息泄露** | 时间窗 `from=now-1h&to=now+1h`；断言不含 secret 字面值 | A |
| ADM-LOGS-02 | logs 缺时间范围 | GET | `/tier/admin/v1/logs` | 400，error `code="invalid_request"` | 不带 from/to query（app.py:127） | A |
| ADM-RUNTIME-01 | 运行时状态 | GET | `/tier/admin/v1/runtime` | 200，body 含 runtime 快照 | 无 | A |
| ADM-STATS-01 | 统计数据 | GET | `/tier/admin/v1/stats?from=...&to=...` | 200，含聚合 | 时间窗 `from=now-1h&to=now+1h`（RFC3339） | A |
| ADM-STATS-02 | stats 分组 | GET | `/tier/admin/v1/stats?group_by=tier` | 200，按 tier 聚合 | 同 ADM-STATS-01 + group_by=tier（admin.py:37 允许 `tier`/`deployment`） | A |
| ADM-STATS-03 | stats 缺时间范围 | GET | `/tier/admin/v1/stats` | 400，error `code="invalid_request"` | 不带 from/to query | A |

### 4.11 Auth — 认证与授权

> 实现约束（auth.py:51-57）：未配 auth → 503 `auth_not_configured`；无 bearer → 401 `authentication_required`；principal 无权 → 403 `permission_denied`。LAN trust 模式下 RFC1918 客户端 IP 可无 token。

| ID | Case | 方法 | 路径 | 预期 | Fixture / 依赖 | 类 |
|----|------|------|------|------|----------------|----|
| AUTH-01 | Data 端点无 token（LAN trust） | GET | `/v1/models` | 200 | m5air 当前 `LLMTIER_TRUSTED_LAN_MODE=1`；客户端在 192.168.x | A |
| AUTH-02 | Data 端点错误 token | GET | `/v1/models` | 401，error `code="authentication_required"` | Authorization: Bearer "bogus-token-xxx"（LAN trust 模式下错误 token 仍 401，因为有 Authorization header 就要验证） | A |
| AUTH-03 | Admin 端点用 Data token | GET | `/tier/admin/v1/providers` | 403，error `code="permission_denied"` | Authorization: Bearer "dev-data"（data token 不是 admin principal） | A |
| AUTH-04 | Admin 端点无 token（LAN trust） | GET | `/tier/admin/v1/providers` | 200 | 客户端在 192.168.x；无 Authorization header | A |
| AUTH-05 | 公共端点无需 token | GET | `/healthz` | 200 | 无 Authorization header | A |
| AUTH-06 | 伪造 Authorization header | GET | `/v1/models` | 401 | Authorization: Bearer ""（空字符串） | A |

---

## 5. 测试执行策略

### 5.1 执行顺序

按 A/B 类区分执行策略；A 类可并发，B 类串行（共享临时实例）：

**A 类（53 个，m5air 现有 state，可并发）**：

```
OBS-01~03 → DP-MODELS-01~06 → DP-EMB-01~04
→ DP-RESP-{01,03,04}（流式/推理/tools）
→ DP-RESP-{02,05,06,07,08,09}（错误目录）
→ DP-USAGE-01~04
→ ADM-PROV-{01,03,04}（GET 集合）
→ ADM-DEPL-{01,03}
→ ADM-SL-{01,03}
→ ADM-PROBE-01~02
→ ADM-PROV-USAGE-01~03
→ ADM-ADMIN-USAGE-01~02
→ ADM-AUDIT-01~02
→ ADM-LOGS-01~02
→ ADM-RUNTIME-01
→ ADM-STATS-01~03
→ AUTH-01~06
```

**B 类（15 个，临时实例，必须串行）**：

```
1. 启临时实例（§2.3 fixture 注入：3 provider + 4 deployment；service-levels 7 个已在 bootstrap 中，跳过）
2. 顺序：ADM-PROV-{02,05,06,07,08,09} → ADM-DEPL-{02,04,05} → ADM-SL-{02,02b,04,04b,05} → OBS-03（无部署状态）
3. teardown：kill 临时实例，rm SQLite
```

> 注：ADM-SL-03（GET service-level）和 §4 表中标记 A 类的所有 GET 都在 m5air 实例上跑（不依赖 B 类临时实例）。

### 5.2 每个 Case 的结构

每个 case 输出：
- 命令（curl 或 python httpx）
- 预期 HTTP status
- 预期 response body 关键字段
- 实际结果
- PASS / FAIL

### 5.3 通过标准

- 全部 68 个 case PASS → API 端点测试通过
- 任何 FAIL → 记录 `failure_reason`，阻塞 release

### 5.4 Case 状态判定规则

> 9-20 报告中 10/26 case 被打 BLOCKED，其中部分是环境限制，部分是测试本身缺陷，混在一起导致 50% BLOCKED 的争议。本节明确四种状态的判定边界。

| 状态 | 何时打 | 是否阻塞 release | 报告必含字段 |
|---|---|---|---|
| **PASS** | 所有断言通过，HTTP status + body 关键字段 + error code 全部 match | 否 | — |
| **FAIL** | 断言失败：HTTP status 不符、body 字段缺失、error code 不符、SSE 事件序列断裂、SSE timeout、流式不完整 | **是** | `failure_reason`（预期 vs 实际）、`reproduction_cmd`、`failure_step` |
| **SKIP** | **环境限制**导致无法执行：上游 Provider 不健康（§2.1 检查失败）、网络不可达、临时 SQLite 权限不足 | **不阻塞** | `skip_reason`（必须引用 §2.1 检查项编号）、`fix_owner`、`eta` |
| **BLOCKED** | **测试代码或 API 契约本身有问题**：fixture 缺失、断言逻辑错、API 字段语义不清、OpenAPI 与实现不一致 | **是** | `block_reason`、`required_resolution`、`reproduction_cmd` |

**关键区分**：

- 上游 Provider 离线 → **SKIP**（不是 BLOCKED，环境问题不是测试代码的锅）
- 测试 fixture 写不出来 → **BLOCKED**（是测试代码需要修）
- API 返回 status 对但 body 字段缺失 → **FAIL**（实现不符合契约）

**本轮 SKIP 上限**：≤ 5 个（10%）。超出则视为测试覆盖不足，需补 mock 或 fixture 后重跑。

**禁止状态**：不允许出现"未跑"（unexecuted）——runner 必须每个 case 都跑出来一个明确结果。

---

## 6. 缺口与待补充

> v0.3.0-draft.3 之前的缺口已通过本轮修订解决：SSE 完整事件序列在 §4.3 fixture 列明；If-Match 格式在 §3.3.1 给完整示例 + 9-20 [P7]；DP-USAGE-04 cursor expired 通过 sqlite3 UPDATE 解决；API-001 current_version 字段已直接进入 §4.6 断言；capabilities 12 字段全集来自 registry.py:16。下表为**本轮仍未覆盖的**缺口。

| 缺口 | 说明 | 优先级 | 关联 case |
|------|------|--------|----------|
| 并发请求归属验证 | 多并发请求 → 验证每个 provider 的 calls 计数（不属于本 plan 单 case 范围） | 低 | — |
| Admin DELETE 后列表清理验证 | 当前 case 只验 204；补一条"DELETE 后 GET → 404" | 中 | ADM-PROV-08, ADM-DEPL-05 |
| Provider `secret_ref` 三种格式子 case | `file:`/`env:`/`raw:` 各一条；目前只测 `file:`（9-21 [P4]） | 中 | ADM-PROV-02 |
| 多 principal 环境 | ST-25/25A 缺口，本 plan 不重复；引用 `llmtier-v0.3-test-plan.md` §11 | — | — |
| `usage` 时间窗默认值 | 当前所有 usage case 显式带 from/to；缺省行为未测（9-20 [P8]） | 低 | — |

---

## 7. 与现有测试的关系

| 现有测试 | 覆盖的 Case | 备注 |
|----------|-------------|------|
| `tests/system/st_03a.py` | DP-MODELS-03, DP-MODELS-04, DP-MODELS-05 | exact-case 大小写 |
| `tests/system/st_09.py` | DP-RESP-05, DP-RESP-06, DP-RESP-07, DP-RESP-08 | 错误目录 |
| `tests/system/st_09a.py` | DP-RESP-09 | previous_response_id |
| `tests/system/st_10.py` | DP-EMB-01 | bge-m3 1024 维 |
| `tests/system/st_11.py` | DP-EMB-02 | base64 编码 |
| `tests/system/st_12.py` | DP-EMB-03 | 不变量（×5 次同输入） |
| `tests/system/st_12a.py` | DP-USAGE-04 | cursor expired（**注意**：本 plan 改用 sqlite3 UPDATE expires_at 方式，ST-12a 若仍用字面值 → 评审对齐） |
| `tests/system/st_13a.py` | ADM-PROV-06, ADM-PROV-07 | If-Match 412 + current_version |
| `tests/system/st_15a.py` | ADM-AUDIT-01, ADM-LOGS-01 | 敏感信息不泄露（fixture 简单版） |
| `tests/system/st_25.py` | AUTH-01, AUTH-04 | Trusted LAN routing |
| `tools/api_smoke_test.py` | 全部 21 endpoint smoke（手动工具） | **不替代** 68 case 断言；smoke 只验 status code，不验 body 关键字段 |
| 单元测试 `tests/unit/` | Auth mock、admin logic、usage 计算、capability keys | |

**本计划新增**（即 ST-* 未覆盖、smoke 未细化的部分）：

- DP-MODELS-01, DP-MODELS-02, DP-MODELS-06（list / get exact case）
- DP-RESP-01, DP-RESP-02, DP-RESP-03, DP-RESP-04（SSE 完整序列 + 推理 + tools fixture）
- DP-USAGE-01, DP-USAGE-02, DP-USAGE-03（数据存在性 + 分页）
- ADM-PROV-01~05, ADM-PROV-08, ADM-PROV-09（CRUD 完整流 + ETag 重试）
- ADM-DEPL-01~05（CRUD 完整流）
- ADM-SL-01~05（拆分后 7 个 case）
- ADM-PROBE-01, ADM-PROBE-02（confirm 语义）
- ADM-PROV-USAGE-01, ADM-PROV-USAGE-03（snapshot 行为）
- ADM-ADMIN-USAGE-01, ADM-ADMIN-USAGE-02
- ADM-AUDIT-02（分页）
- ADM-LOGS-02（缺时间范围 → 400）
- ADM-RUNTIME-01
- ADM-STATS-01, ADM-STATS-02, ADM-STATS-03
- AUTH-02, AUTH-03, AUTH-05, AUTH-06

---

## 8. 历史问题清单（9-20 / 9-21 踩坑回归检查）

> 本节列出此前报告 `2026-09-20-test-report.md` 与 `2026-09-21-test-report.md` 中已经踩过的坑，本轮执行前必须在 §2.1 检查清单里"主动验证已修复"，避免重蹈覆辙。每个问题给出 ID 和对应的 case。

| ID | 问题 | 来源 | 关联 case | 验证方式 |
|----|------|------|-----------|----------|
| **P1** | 测试用 `127.0.0.1`（违反 TS-003） | 9-20 ST-12 | 所有 DP-RESP / DP-EMB | §2.1 检查清单强制 LAN IP；TS-002 测试头部注释 |
| **P2** | Provider endpoint 未明确指向 m5mac/m5air | 9-20, 9-21 | 所有 DP-RESP / DP-EMB | §2.2 路由矩阵 |
| **P3** | 上游 Provider 健康不可知 → 跑一半 500 | 9-20 ST-12, 9-21 provider_omlx_m5mac | DP-RESP-01~04, ADM-PROBE-02 | §2.1 检查清单 OMLX 双机 curl |
| **P4** | `secret_ref` 三种格式（`file:`/`env:`/`raw:`）行为差异未测 | 9-21 smoke 部分覆盖 | ADM-PROV-02 | §6 缺口保留 |
| **P5** | `capabilities` 必填字段缺失导致 400 | 9-20 ST-14 PARTIAL, 9-21 smoke | ADM-DEPL-02 | §4.7 fixture 模板列 12 字段全集 |
| **P6 / API-001** | PATCH 412 响应缺 `current_version` 字段 | 9-20 ST-13A | ADM-PROV-06 | §4.6 断言 body 含 `current_version`；registry.py:156 已实现 |
| **P7** | If-Match ETag 格式 `id.vN` 未文档化 | 9-20 ST-13A | 所有 PATCH/DELETE 9 个 case | §3.3.1 给完整 curl 示例 + 测试头部注释 |
| **P8** | `/tier/v1/usage` 缺 RFC3339 时间参数 | 9-20 smoke, 9-21 smoke | DP-USAGE-*, ADM-ADMIN-USAGE-* | §4.5/§4.9 fixture 列时间窗 RFC3339 字符串 |
| **P9** | Provider create 多传 `id` 字段（auto-generated） | 9-21 smoke | ADM-PROV-02 | §4.6 fixture 模板明确禁止传 id（schema `additionalProperties:false` 也会拦） |
| **P10** | 并发测试 `grep "error"` 误匹配 `"error":null` | 9-20 ST-22/23 | ADM-PROBE-02（并发场景） | 用 JSON 解析而非字符串 grep |
| **P11 / FD-001** | FD 泄漏（50 req 后 FD=89） | 9-20 ST-18 | 不在本 plan 范围 | 引用 `llmtier-v0.3-test-plan.md` ST-18/ST-19 |
| **P12** | 50% BLOCKED（环境缺）当成"失败" | 9-20 争议 | 全局 | §5.4 PASS/FAIL/SKIP/BLOCKED 四状态判定；SKIP ≤ 5 个 |
| **P13** | 之前没在测试代码头部写明依赖（TS-002） | 9-21 隐含 | 所有 case | 测试文件头部按 TS-002 写明 endpoint / provider / 模型 / auth |
| **P14** | 测试期望错：DP-RESP-02 期望 200，实际 stream=false 必拒 | 本轮 review | DP-RESP-02 / DP-RESP-06 | §4.3 已修正预期 |

**执行前必读**：`docs/70_verification/reports/2026-09-20-summary.md`、`docs/70_verification/reports/2026-09-21-summary.md`。
