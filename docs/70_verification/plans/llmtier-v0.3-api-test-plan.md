<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 API Test Plan

> STD 使用入口：[项目采用说明与标准导航](docs/00_management/standards/README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-v0.3-api-test-plan` |
| Document Version | `0.1.0-draft.1` |
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

---

## 2. 测试环境约束

| 环境 | 说明 |
|------|------|
| m5mac (`192.168.1.8`) | API 测试执行机 |
| m5air (`192.168.1.9:9000`) | OMLX 上游 Provider（bge-m3, Qwen3-Embedding） |
| 测试数据库 | 每个 case 独立临时 SQLite（`/tmp/llmtier_api_<uuid>.sqlite3`） |
| 端口 | 每个 case 独立随机端口（`49152~65535`） |

**禁止使用 `127.0.0.1` 作为 Provider endpoint**（TS-003）。

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
| `PATCH` | `/tier/admin/v1/providers/{id}` | 更新 provider（含 If-Match） | Admin Bearer Token |
| `DELETE` | `/tier/admin/v1/providers/{id}` | 删除 provider（含 If-Match） | Admin Bearer Token |
| `GET` | `/tier/admin/v1/providers/{id}/usage` | 获取 provider 使用量快照 | Admin Bearer Token |
| `POST` | `/tier/admin/v1/providers/{id}/usage` | 刷新 provider 使用量 | Admin Bearer Token |
| `GET` | `/tier/admin/v1/deployments` | 列出所有 deployment（分页） | Admin Bearer Token |
| `POST` | `/tier/admin/v1/deployments` | 创建 deployment | Admin Bearer Token |
| `GET` | `/tier/admin/v1/deployments/{id}` | 获取 deployment 详情 | Admin Bearer Token |
| `PATCH` | `/tier/admin/v1/deployments/{id}` | 更新 deployment（含 If-Match） | Admin Bearer Token |
| `DELETE` | `/tier/admin/v1/deployments/{id}` | 删除 deployment（含 If-Match） | Admin Bearer Token |
| `GET` | `/tier/admin/v1/service-levels` | 列出所有服务等级（分页） | Admin Bearer Token |
| `POST` | `/tier/admin/v1/service-levels` | 创建服务等级 | Admin Bearer Token |
| `GET` | `/tier/admin/v1/service-levels/{id}` | 获取服务等级详情 | Admin Bearer Token |
| `PATCH` | `/tier/admin/v1/service-levels/{id}` | 更新服务等级（含 If-Match） | Admin Bearer Token |
| `DELETE` | `/tier/admin/v1/service-levels/{id}` | 删除服务等级（含 If-Match） | Admin Bearer Token |
| `POST` | `/tier/admin/v1/probes` | 探测 deployment 健康状态 | Admin Bearer Token |
| `GET` | `/tier/admin/v1/usage` | 管理面使用量统计（分页） | Admin Bearer Token |
| `GET` | `/tier/admin/v1/audit` | 审计事件列表（分页） | Admin Bearer Token |
| `GET` | `/tier/admin/v1/logs` | 脱敏日志列表（需 from/to） | Admin Bearer Token |
| `GET` | `/tier/admin/v1/runtime` | 运行时状态快照 | Admin Bearer Token |
| `GET` | `/tier/admin/v1/stats` | 统计聚合（支持 group_by） | Admin Bearer Token |

---

## 4. Test Case 矩阵

### 4.1 Observation — 公共端点

| ID | Case | 方法 | 路径 | 预期 |
|----|------|------|------|------|
| OBS-01 | 健康检查始终200 | GET | `/healthz` | 200，body 含 `status: ok` |
| OBS-02 | 就绪检查-正常 | GET | `/readyz` | 200，body 含 `tiers` 列表 |
| OBS-03 | 就绪检查-无部署 | GET | `/readyz` | 200，`tiers` 为空数组 |

### 4.2 Data Plane — Models

| ID | Case | 方法 | 路径 | 预期 |
|----|------|------|------|------|
| DP-MODELS-01 | 列出所有模型 | GET | `/v1/models` | 200，含 7 个逻辑 tier |
| DP-MODELS-02 | 获取存在的模型 | GET | `/v1/models/Worker` | 200，含 `id`、`object`、`created` |
| DP-MODELS-03 | 大小写不匹配拒绝 | GET | `/v1/models/worker` | 404 `model_not_found` |
| DP-MODELS-04 | 全大写拒绝 | GET | `/v1/models/WORKER` | 404 `model_not_found` |
| DP-MODELS-05 | URL编码空格拒绝 | GET | `/v1/models/Senior%20` | 404 `model_not_found` |
| DP-MODELS-06 | 不存在的模型 | GET | `/v1/models/NonExistent` | 404 `model_not_found` |

### 4.3 Data Plane — Responses

| ID | Case | 方法 | 路径 | 预期 |
|----|------|------|------|------|
| DP-RESP-01 | 流式响应成功 | POST | `/v1/responses` | 200，SSE 事件完整，含 `response.completed` |
| DP-RESP-02 | 非流式响应 | POST | `/v1/responses`（stream=false） | 200，JSON body，非 SSE |
| DP-RESP-03 | 推理任务 | POST | `/v1/responses` | 200，output_text 含推理步骤 |
| DP-RESP-04 | 带 tools 参数 | POST | `/v1/responses` | 200，SSE 合法（gemma 不调用工具） |
| DP-RESP-05 | unknown model | POST | `/v1/responses` | 404 `model_not_found` |
| DP-RESP-06 | stream:true 被拒绝 | POST | `/v1/responses` | 400 `unsupported_request` |
| DP-RESP-07 | store:true 被拒绝 | POST | `/v1/responses` | 400 `unsupported_request` |
| DP-RESP-08 | 缺少必填字段 | POST | `/v1/responses` | 400 `invalid_request` |
| DP-RESP-09 | previous_response_id 被拒绝 | POST | `/v1/responses` | 400 `unsupported_field` |

### 4.4 Data Plane — Embeddings

| ID | Case | 方法 | 路径 | 预期 |
|----|------|------|------|------|
| DP-EMB-01 | 基本 embedding | POST | `/v1/embeddings` | 200，维度=1024，无 NaN/Inf |
| DP-EMB-02 | base64 编码 | POST | `/v1/embeddings` | 200，base64 解码后 1024 个 float32 |
| DP-EMB-03 | 不变量验证 | POST | `/v1/embeddings` ×5 | 每次维度=1024，`embedding_space_id` 一致 |
| DP-EMB-04 | unknown model | POST | `/v1/embeddings` | 404 `model_not_found` |

### 4.5 Data Plane — Usage

| ID | Case | 方法 | 路径 | 预期 |
|----|------|------|------|------|
| DP-USAGE-01 | 无 usage 数据 | GET | `/tier/v1/usage` | 200，`data` 为空数组 |
| DP-USAGE-02 | 有 usage 数据 | GET | `/tier/v1/usage` | 200，`data` 含调用记录 |
| DP-USAGE-03 | 分页游标 | GET | `/tier/v1/usage?limit=1` | 200，`page.has_more=true` |
| DP-USAGE-04 | 过期 cursor | GET | `/tier/v1/usage?cursor=expired` | 400 `cursor_expired` |

### 4.6 Admin — Providers CRUD

| ID | Case | 方法 | 路径 | 预期 |
|----|------|------|------|------|
| ADM-PROV-01 | 列出 providers | GET | `/tier/admin/v1/providers` | 200，含分页 `page` |
| ADM-PROV-02 | 创建 provider | POST | `/tier/admin/v1/providers` | 201，含 `id`、`has_secret=true` |
| ADM-PROV-03 | 获取存在的 provider | GET | `/tier/admin/v1/providers/{id}` | 200，含完整字段 |
| ADM-PROV-04 | 获取不存在的 provider | GET | `/tier/admin/v1/providers/{id}` | 404 `not_found` |
| ADM-PROV-05 | 更新 provider | PATCH | `/tier/admin/v1/providers/{id}` | 200，含新 ETag |
| ADM-PROV-06 | 更新缺 If-Match | PATCH | `/tier/admin/v1/providers/{id}` | 412 `version_conflict` |
| ADM-PROV-07 | 更新过期 ETag | PATCH | `/tier/admin/v1/providers/{id}` | 412 `version_conflict` |
| ADM-PROV-08 | 删除 provider | DELETE | `/tier/admin/v1/providers/{id}` | 204，无 body |
| ADM-PROV-09 | 删除缺 If-Match | DELETE | `/tier/admin/v1/providers/{id}` | 412 `version_conflict` |

### 4.7 Admin — Deployments CRUD

| ID | Case | 方法 | 路径 | 预期 |
|----|------|------|------|------|
| ADM-DEPL-01 | 列出 deployments | GET | `/tier/admin/v1/deployments` | 200，含分页 |
| ADM-DEPL-02 | 创建 deployment | POST | `/tier/admin/v1/deployments` | 201，含完整 `capabilities` |
| ADM-DEPL-03 | 获取 deployment | GET | `/tier/admin/v1/deployments/{id}` | 200 |
| ADM-DEPL-04 | 更新 deployment | PATCH | `/tier/admin/v1/deployments/{id}` | 200，含新 ETag |
| ADM-DEPL-05 | 删除 deployment | DELETE | `/tier/admin/v1/deployments/{id}` | 204 |

### 4.8 Admin — Service Levels CRUD

| ID | Case | 方法 | 路径 | 预期 |
|----|------|------|------|------|
| ADM-SL-01 | 列出 service-levels | GET | `/tier/admin/v1/service-levels` | 200，含 7 个固定 tier |
| ADM-SL-02 | 创建 service-level | POST | `/tier/admin/v1/service-levels` | 201 |
| ADM-SL-03 | 获取 service-level | GET | `/tier/admin/v1/service-levels/{id}` | 200 |
| ADM-SL-04 | 更新 service-level | PATCH | `/tier/admin/v1/service-levels/{id}` | 200 |
| ADM-SL-05 | 删除 service-level | DELETE | `/tier/admin/v1/service-levels/{id}` | 204 |

### 4.9 Admin — Probes and Usage

| ID | Case | 方法 | 路径 | 预期 |
|----|------|------|------|------|
| ADM-PROBE-01 | 探测无 confirm | POST | `/tier/admin/v1/probes` | 400 `confirmation_required` |
| ADM-PROBE-02 | 探测带 confirm | POST | `/tier/admin/v1/probes` | 200，含 `status: healthy/unhealthy` |
| ADM-PROV-USAGE-01 | 获取 provider usage | GET | `/tier/admin/v1/providers/{id}/usage` | 200，含 snapshot |
| ADM-PROV-USAGE-02 | 刷新 provider usage | POST | `/tier/admin/v1/providers/{id}/usage` | 400（缺 confirm） |
| ADM-PROV-USAGE-03 | 刷新带 confirm | POST | `/tier/admin/v1/providers/{id}/usage` | 200，snapshot 更新 |
| ADM-ADMIN-USAGE-01 | 管理面 usage | GET | `/tier/admin/v1/usage` | 200，含聚合数据 |
| ADM-ADMIN-USAGE-02 | usage 分页 | GET | `/tier/admin/v1/usage?limit=1` | 200，`page.has_more=true` |

### 4.10 Admin — Audit, Logs, Runtime, Stats

| ID | Case | 方法 | 路径 | 预期 |
|----|------|------|------|------|
| ADM-AUDIT-01 | 列出 audit 事件 | GET | `/tier/admin/v1/audit` | 200，无敏感信息泄露 |
| ADM-AUDIT-02 | audit 分页 | GET | `/tier/admin/v1/audit?limit=1` | 200，`page.has_more=true` |
| ADM-LOGS-01 | 列出 logs | GET | `/tier/admin/v1/logs?from=...&to=...` | 200，无敏感信息泄露 |
| ADM-LOGS-02 | logs 缺时间范围 | GET | `/tier/admin/v1/logs` | 400 `invalid_request` |
| ADM-RUNTIME-01 | 运行时状态 | GET | `/tier/admin/v1/runtime` | 200，含 `pools`、`backends` |
| ADM-STATS-01 | 统计数据 | GET | `/tier/admin/v1/stats?from=...&to=...` | 200，含聚合 |
| ADM-STATS-02 | stats 分组 | GET | `/tier/admin/v1/stats?group_by=tier` | 200，按 tier 聚合 |
| ADM-STATS-03 | stats 缺时间范围 | GET | `/tier/admin/v1/stats` | 400 `invalid_request` |

### 4.11 Auth — 认证与授权

| ID | Case | 方法 | 路径 | 预期 |
|----|------|------|------|------|
| AUTH-01 | Data 端点无 token（Trusted LAN） | GET | `/v1/models` | 200（Trusted LAN 模式） |
| AUTH-02 | Data 端点错误 token | GET | `/v1/models` | 401 `authentication_error` |
| AUTH-03 | Admin 端点用 Data token | GET | `/tier/admin/v1/providers` | 401 `authentication_error` |
| AUTH-04 | Admin 端点无 token（Trusted LAN） | GET | `/tier/admin/v1/providers` | 200（Trusted LAN 模式） |
| AUTH-05 | 公共端点无需 token | GET | `/healthz` | 200 |
| AUTH-06 | 伪造 Authorization header | GET | `/v1/models` | 401 |

---

## 5. 测试执行策略

### 5.1 执行顺序

```
OBS-01~03 → DP-MODELS-01~06 → DP-RESP-01~09 → DP-EMB-01~04 → DP-USAGE-01~04
→ ADM-PROV-01~09 → ADM-DEPL-01~05 → ADM-SL-01~05 → ADM-PROBE-01~02
→ ADM-PROV-USAGE-01~03 → ADM-ADMIN-USAGE-01~02 → ADM-AUDIT-01~02
→ ADM-LOGS-01~02 → ADM-RUNTIME-01 → ADM-STATS-01~03
→ AUTH-01~06
```

### 5.2 每个 Case 的结构

每个 case 输出：
- 命令（curl 或 python httpx）
- 预期 HTTP status
- 预期 response body 关键字段
- 实际结果
- PASS / FAIL

### 5.3 通过标准

- 全部 57 个 case PASS → API 端点测试通过
- 任何 FAIL → 记录 `failure_reason`，阻塞 release

---

## 6. 缺口与待补充

| 缺口 | 说明 | 优先级 |
|------|------|--------|
| SSE 流式响应完整事件序列验证 | 当前只验证有 `response.completed`，未验证每个 SSE 事件类型顺序 | 高 |
| 并发请求归属验证 | 多并发请求 → 验证每个 provider 的 calls 计数 | 中 |
| Admin DELETE 清理验证 | 删除后列表不再包含该资源 | 中 |
| ETag 过期后重试 | 获取新 ETag 后 PATCH 成功 | 中 |

---

## 7. 与现有测试的关系

| 现有测试 | 覆盖的 Case |
|----------|-------------|
| `tests/system/st_*.py` | OBS-01~03, DP-MODELS-03~05, DP-RESP-05~09, DP-EMB-01~03, AUTH 部分 |
| `tools/api_smoke_test.py` | 全部端点 smoke 覆盖（手动工具） |
| 单元测试 `tests/unit/` | Auth mock、admin logic、usage 计算 |

本计划补齐：DP-MODELS-01~02/06、DP-USAGE-01~04、ADM-*-05~09、ADM-LOGS、ADM-RUNTIME、ADM-STATS、并发归属。
