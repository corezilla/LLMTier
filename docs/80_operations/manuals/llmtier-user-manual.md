<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier User Manual

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-user-manual` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-21` |
| Last Modified Date | `2026-09-21` |
| Template ID | `operations.user-manual` |
| Template Version | `0.1.1` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/80_operations/manuals/llmtier-user-manual.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. 产品简介、目标读者与适用版本

**产品**: LLMTier 是一个独立的 Python 服务，提供 OpenAI-compatible HTTP API，供局域网上的 consumer（如 Piko）调用。

**目标读者**: 需要在局域网内部署 AI 模型网关的运维人员和开发者。

**核心功能**:
- OpenAI-compatible Responses API（流式 SSE）
- OpenAI-compatible Embeddings API
- OpenAI-compatible Models API
- Token Usage 统计
- Provider/Deployment/Service Level 管理
- 健康检查与监控

**适用版本**: V0.3 (当前为候选版本)

---

## 2. Safety、Security 与使用限制

### 2.1 安全限制

- LLMTier 设计运行在可信局域网环境（`192.168.1.0/24`）
- 生产环境应使用 HTTPS
- Admin API 和 Data API 使用不同的认证 token
- Secret 值只写不读，不回显

### 2.2 使用限制

- 单进程 SQLite 存储
- 不支持分布式部署
- 不支持跨网络调用上游 provider

---

## 3. 系统要求、包装内容与准备工作

### 3.1 系统要求

- Python 3.11+
- 独立虚拟环境（推荐）

### 3.2 安装

```bash
# 从源码安装
python3 -m pip install -e .

# 或直接运行
PYTHONPATH=src python3 -m llmtier_v03 --help
```

### 3.3 配置文件

LLMTier 通过 `--settings <path>` 或环境变量 `LLMTIER_SETTINGS` 指定 JSON 配置文件。
启动时系统将配置内容导入 SQLite 数据库，此后数据库独立运行，修改 settings.json 不会自动同步。

**三个数组均可为空**，用于空集群启动后再通过 Admin API 逐步添加资源。

```json
{
  "providers": [
    {
      "name": "My OMLX",
      "kind": "local",
      "endpoint": "http://192.168.1.8:9000/v1",
      "secret_ref": null,
      "enabled": true
    }
  ],
  "deployments": [
    {
      "name": "Qwen3.6",
      "provider_id": "provider_xxx",
      "backend_model": "Qwen3.6",
      "capabilities": { ... },
      "enabled": true
    }
  ],
  "service_levels": [
    {
      "id": "Senior",
      "deployment_ids": ["deployment_yyy"],
      "enabled": true
    }
  ]
}
```

> **注**：`provider_id` 和 `deployment_ids` 在 JSON 中使用系统生成的 ID（格式 `provider_<hex>` / `deployment_<hex>`）。
> 建议通过 Admin API 依次创建 provider → deployment → service-level，由系统自动分配 ID。

---

## 4. 安装、连接、登录与首次配置

### 4.1 启动服务

```bash
PYTHONPATH=src python3 -m llmtier_v03 \
  --host 0.0.0.0 \
  --port 8180 \
  --database var/llmtier-v03.sqlite3 \
  --settings config/settings.json
```

### 4.2 环境变量

| Variable | 说明 | 默认值 |
|----------|------|--------|
| `LLMTIER_ADMIN_TOKEN` | Admin API token | - |
| `LLMTIER_DATA_TOKEN` | Data API token | - |
| `LLMTIER_TRUSTED_LAN_MODE` | 信任局域网模式 | 1 |
| `LLMTIER_DEV_MODE` | 开发模式 | - |

### 4.3 首次配置流程

1. 启动服务
2. 创建 Provider（指向 OMLX 或其他上游）
3. 创建 Deployment（绑定 Provider 和模型）
4. 创建 Service Level（绑定 Deployment）
5. 验证 `/readyz` 返回 200

---

## 5. Quick Start

### 5.1 健康检查

```bash
curl http://localhost:8180/healthz
```

### 5.2 调用 Responses API

```bash
curl -X POST http://localhost:8180/v1/responses \
  -H "Authorization: Bearer <data_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Worker",
    "input": [{"role": "user", "content": "Hello"}],
    "stream": true,
    "max_output_tokens": 100
  }'
```

### 5.3 调用 Embeddings API

```bash
curl -X POST http://localhost:8180/v1/embeddings \
  -H "Authorization: Bearer <data_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Embedding-v1",
    "input": "Hello world"
  }'
```

### 5.4 列出可用模型

```bash
curl http://localhost:8180/v1/models \
  -H "Authorization: Bearer <data_token>"
```

---

## 6. 主要任务与工作流

### 6.1 添加新的 Provider

```bash
curl -X POST http://localhost:8180/tier/admin/v1/providers \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Local OMLX",
    "kind": "local",
    "endpoint": "http://192.168.1.8:9000/v1",
    "secret_ref": "file:/path/to/key.txt",
    "enabled": true
  }'
```

### 6.2 添加新的 Deployment

```bash
curl -X POST http://localhost:8180/tier/admin/v1/deployments \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Gemma Deployment",
    "provider_id": "<provider_id>",
    "backend_model": "gemma-4-12b-it",
    "capabilities": {
      "responses": true,
      "embeddings": false,
      "tools": false,
      "structured_outputs": false,
      "input_modalities": ["text"],
      "output_modalities": ["text"],
      "context_window": 128000,
      "max_output_tokens": 16384
    },
    "enabled": true
  }'
```

### 6.3 创建 Service Level

```bash
curl -X POST http://localhost:8180/tier/admin/v1/service-levels \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "Worker",
    "deployment_ids": ["<deployment_id>"],
    "enabled": true
  }'
```

### 6.4 查看使用量

```bash
# 用户使用量
curl "http://localhost:8180/tier/v1/usage?from=2026-01-01T00:00:00Z&to=2026-12-31T23:59:59Z" \
  -H "Authorization: Bearer <data_token>"

# Admin 使用量统计
curl "http://localhost:8180/tier/admin/v1/usage?from=2026-01-01T00:00:00Z&to=2026-12-31T23:59:59Z" \
  -H "Authorization: Bearer <admin_token>"
```

---

## 7. 配置、输入、输出和数据管理

### 7.1 配置文件（settings.json）

启动时通过 `--settings <path>` 或环境变量 `LLMTIER_SETTINGS` 指定 JSON 配置文件，
系统启动时将其中定义的 providers、deployments、service_levels 导入 SQLite 数据库。
文件路径无默认值，必须显式指定。

```json
{
  "providers": [ ... ],
  "deployments": [ ... ],
  "service_levels": [ ... ]
}
```

所有三个数组均可为空。已导入的数据在数据库中独立存在，修改 settings.json 不会自动同步到数据库（需通过 Admin API 管理和查询）。

---

### 7.2 Provider 配置

Provider 代表一个上游推理服务端点（本地 OMLX 部署或云端 API）。

#### 7.2.1 Provider 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 否 | 系统自动生成，格式 `provider_<hex>`，如 `provider_abc123`。创建后不可更改 |
| `name` | string | **是** | 显示名称，同一实例内唯一；冲突返回 409 `resource_conflict` |
| `kind` | string | **是** | 上游类型。取值：`local`（本地 OMLX 部署）或 `cloud`（云端 API） |
| `endpoint` | string | **是** | 上游 API 基础 URL，如 `http://192.168.1.8:9000/v1` |
| `secret_ref` | string \| null | **是** | API key 引用路径。格式：`env:VARIABLE_NAME`（从环境变量读取）或 `file:/absolute/path/to/key.txt`（从文件读取）；创建后为 `null` 表示无 key |
| `enabled` | boolean | **是** | 是否启用。禁用后该 Provider 下的所有 Deployment 不会被调度 |
| `usage` | object | 否 | 用量限制配置，见 §7.2.2 |

#### 7.2.2 Provider.usage 子对象

通过 Admin API 的 PATCH `/tier/admin/v1/providers/{id}` 更新（不支持 POST 时传入）。

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `usage_provider` | string | `local`（kind=local）或 `none`（kind=cloud） | 用量记录来源。取值：`none`/`local`/`minimax`/`volc` |
| `usage_api_key_ref` | string \| null | `null` | API key 引用，格式同 `secret_ref`（`env:`/`file:` 前缀） |
| `usage_access_key_ref` | string \| null | `null` | Access key 引用，格式同上 |
| `usage_secret_key_ref` | string \| null | `null` | Secret key 引用，格式同上 |
| `max_concurrent_requests` | integer | `1` | 该 Provider 同时处理的的最大请求数（≥ 1） |
| `min_request_interval_ms` | integer | `0` | 两次请求之间的最小间隔（毫秒，≥ 0） |
| `requests_per_minute` | integer | `0` | 每分钟请求数上限（0 = 不限） |

> **注**：`usage_api_key_ref`/`usage_access_key_ref`/`usage_secret_key_ref` 必须使用 `env:` 或 `file:` 前缀，否则返回 400 `invalid_request`。

#### 7.2.3 Provider API 行为

- **POST**（创建）：必填字段不完整 → 400；`kind` 不是 `local`/`cloud` → 400；`name` 重复 → 409
- **PATCH**（更新）：不允许字段 → 400；更新 `usage` 时会清除所有用量快照（强制重新统计）
- **DELETE**（删除）：有 active deployment 引用 → 409 `resource_in_use`

---

### 7.3 Deployment 配置

Deployment 表示一个具体的模型实例，绑定到一个 Provider。

#### 7.3.1 Deployment 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 否 | 系统自动生成，格式 `deployment_<hex>`；创建后不可更改 |
| `name` | string | **是** | 显示名称，同一实例内唯一；冲突返回 409 `resource_conflict` |
| `provider_id` | string | **是** | 绑定的 Provider ID，该 Provider 必须存在且已启用 |
| `backend_model` | string | **是** | 上游模型名称（如 `Qwen3.6`、`gemma-4-2b-it`），LLMTier 将此字段透传给上游 |
| `capabilities` | object | **是** | 模型能力声明，必须包含全部 12 个标准 key；见 §7.3.2 |
| `enabled` | boolean | **是** | 是否启用。禁用后不会被任何 Service Level 调度 |
| `health` | string | 否 | 健康状态，枚举值：`unknown`/`healthy`/`degraded`/`unhealthy`；由系统探测写入，管理员不可直接修改 |

#### 7.3.2 Deployment.capabilities（12 个标准字段）

`capabilities` 是 **12 个固定 key 的 object**，每个字段必须显式声明，缺一不可。
系统以此判断模型是否满足某 Service Level 的要求。

| 字段 | 类型 | 说明 |
|------|------|------|
| `responses` | boolean | 是否支持 `/v1/responses` 推理接口 |
| `embeddings` | boolean | 是否支持 `/v1/embeddings` 接口 |
| `tools` | boolean | 是否支持 Tools（函数调用）功能 |
| `structured_outputs` | boolean | 是否支持结构化输出（JSON mode） |
| `input_modalities` | string[] | 支持的输入模态，如 `["text"]`、`["text", "image"]` |
| `output_modalities` | string[] | 支持的输出模态，如 `["text"]`、`["text", "image"]` |
| `context_window` | integer \| null | 模型上下文窗口最大 token 数（null 表示无限制或未知）；用于判断单请求上限 |
| `max_output_tokens` | integer \| null | 单次输出最大 token 数上限（null 表示无限制）；与 `context_window` 分别控制输入/输出 |
| `embedding_space_id` | string \| null | Embedding 向量空间标识符；`Embedding-v1` Tier 要求固定值 `"bge-m3-dense-1024-v1"` |
| `embedding_dimensions` | integer[] \| null | Embedding 向量维度，如 `[1024]`；`Embedding-v1` Tier 要求 `[1024]` |
| `embedding_max_batch_inputs` | integer \| null | 每次 Embedding 请求最大输入文本条数；`Embedding-v1` Tier 要求 `32` |
| `embedding_max_input_tokens` | integer \| null | 每次 Embedding 请求单条最大输入 token 数；`Embedding-v1` Tier 要求 `8192` |

**必填规则**：所有 12 个 key 必须存在，类型必须匹配，少一个或多一个均返回 400 `invalid_request`。

**字段类型规则**：
- `responses`/`embeddings`/`tools`/`structured_outputs`：必须是 `true`/`false`（boolean）
- `input_modalities`/`output_modalities`：必须是 string 数组
- `context_window`/`max_output_tokens`/`embedding_max_batch_inputs`/`embedding_max_input_tokens`：必须是 integer 或 `null`
- `embedding_space_id`：`null` 或 string
- `embedding_dimensions`：`null` 或 integer 数组

#### 7.3.3 Deployment API 行为

- **POST**（创建）：`provider_id` 对应的 Provider 不存在 → 400；`capabilities` 缺少/多出 key → 400；字段类型错误 → 400
- **PATCH**（更新）：`provider_id` 不可通过 PATCH 修改（会返回 400）；`capabilities` 可以整体替换（会重新校验全部 12 个 key）
- **DELETE**（删除）：被任何 Service Level 引用 → 409 `resource_in_use`

---

### 7.4 Service Level 配置

Service Level（服务层级）是 LLMTier 的核心抽象，每个 Tier ID 精确对应一个逻辑模型名称（如 `Worker`、`Senior`），客户端请求时按 `model` 字段精确路由。

> **固定 Tier**：系统内置 7 个固定 Tier：`Senior`、`Junior`、`Worker`、`Associate`、`Engineer`、`Executor`、`Embedding-v1`。这些 Tier 的 ID 不可更改，不可新增，不可删除（DELETE 返回 409 `fixed_service_level`）。

#### 7.4.1 Service Level 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | **是** | Tier 标识符。必须是 7 个固定值之一（见上）；其他值 → 400 `invalid_request` |
| `deployment_ids` | string[] | **是** | 该 Tier 的候选 deployment 列表（按优先级排序）；**必须非空**，空数组 → 400 `invalid_request` |
| `enabled` | boolean | **是** | 是否启用。禁用后该 Tier 不会被路由匹配 |
| `capabilities` | object | 否 | 系统自动计算（所有 `deployment_ids` 的 capabilities 交集）；通过 GET 返回，**创建/更新时不可传入** |

#### 7.4.2 capabilities 交集计算规则

系统自动计算 `deployment_ids` 内所有 deployment 的 capabilities 交集：

- 对 **boolean 类型字段**（`responses`/`embeddings`/`tools`/`structured_outputs`）：取 `all(values)`，即所有 deployment 都声明 `true` 时结果才为 `true`
- 对 **non-boolean 字段**（如 `context_window`、`input_modalities`）：所有 deployment 值必须完全一致，不一致时该字段被丢弃
- 交集结果必须恰好包含 **全部 12 个 key**，否则该 Tier 无法使用（`capability_conflict` 错误）

这意味着：同一个 Tier 下的所有 deployment 必须在非 bool 能力上保持完全一致，否则该 Tier 不可用。

#### 7.4.3 Embedding-v1 特殊约束

`Embedding-v1` Tier 有额外的 embedding 向量空间锁定：

| 字段 | 要求的值 |
|------|---------|
| `embeddings` | `true` |
| `responses` | `false` |
| `embedding_space_id` | `"bge-m3-dense-1024-v1"`（固定值，不可更改） |
| `embedding_dimensions` | `[1024]` |
| `embedding_max_batch_inputs` | `32` |
| `embedding_max_input_tokens` | `8192` |

违反上述任一条件 → 409 `embedding_space_conflict`。

#### 7.4.4 Service Level API 行为

- **POST**（创建）：`id` 不是 7 个固定值之一 → 400；`deployment_ids` 为空 → 400；capabilities 交集缺失 key → 409 `capability_conflict`；`Embedding-v1` 向量空间不符 → 409 `embedding_space_conflict`
- **PATCH**（更新）：只允许更新 `deployment_ids` 和 `enabled`（其他字段 → 400）；更新 `deployment_ids` 时重新触发 capabilities 校验，冲突 → 409
- **DELETE**（删除）：固定 Tier → 409 `fixed_service_level`（"Fixed Tier service levels cannot be deleted"）

---

### 7.5 配置校验规则汇总

| 操作 | 校验 | 错误码 |
|------|------|--------|
| POST Provider | `kind` 不是 `local`/`cloud` | `invalid_request` |
| POST Provider | `secret_ref` 不以 `env:`/`file:` 开头（非 null） | `invalid_request` |
| PATCH Provider | 传入不允许字段 | `invalid_request` |
| PATCH Provider | `usage.*_ref` 格式不以 `env:`/`file:` 开头 | `invalid_request` |
| DELETE Provider | 有 deployment 引用该 Provider | `resource_in_use` |
| POST Deployment | `provider_id` 不存在 | `invalid_request` |
| POST Deployment | `capabilities` key 数量不是 12 | `invalid_request` |
| POST Deployment | `capabilities` 含未知 key | `invalid_request` |
| PATCH Deployment | `provider_id` 传入新值 | `invalid_request` |
| PATCH Deployment | 新 `provider_id` 不存在 | `invalid_request` |
| DELETE Deployment | 有 Service Level 引用该 Deployment | `resource_in_use` |
| POST Service Level | `id` 不是 7 个固定 Tier 之一 | `invalid_request` |
| POST Service Level | `deployment_ids` 为空 | `invalid_request` |
| PATCH Service Level | 传入 `capabilities` 字段 | `invalid_request` |
| PATCH Service Level | 新 `deployment_ids` 组合导致 capability 交集缺失 key | `capability_conflict` |
| PATCH Service Level | `Embedding-v1` 新 `deployment_ids` 向量空间不符 | `embedding_space_conflict` |
| DELETE Service Level | 目标 Tier 是固定 Tier | `fixed_service_level` |

---

## 8. 状态、通知、错误和恢复

### 8.1 健康状态

- `/healthz`: 总是返回 200（服务进程存活）
- `/readyz`: 返回 200 或 503（依赖所有 Provider/Deployment 健康状态）

### 8.2 常见错误

| 错误 | 原因 | 解决方法 |
|------|------|----------|
| `401` | Token 错误或缺失 | 检查 `LLMTIER_ADMIN_TOKEN` / `LLMTIER_DATA_TOKEN` |
| `404` | 资源不存在 | 检查 ID 是否正确 |
| `412` | ETag 版本冲突 | 重新 GET 获取最新 ETag |
| `503` | Provider 不可用 | 检查 Provider endpoint 和网络连通性 |

### 8.3 恢复

- 服务重启后自动恢复
- 状态存储在 SQLite 数据库
- 日志路径可在启动时配置

---

## 9. 日常维护、升级和备份

### 9.1 备份

定期备份 SQLite 数据库文件：
```bash
cp state.sqlite3 state.sqlite3.backup
```

### 9.2 升级

```bash
# 停止服务
# 备份数据库
# 安装新版本
python3 -m pip install -e .

# 重启服务
```

### 9.3 日志

日志级别可通过环境变量控制。查看日志获取运行时信息。

---

## 10. Troubleshooting 与 Support

### 10.1 服务无法启动

- 检查端口是否被占用
- 检查配置文件格式是否正确
- 检查数据库文件权限

### 10.2 Provider 不可用

- 确认 Provider endpoint 网络可达
- 确认 API key 正确
- 使用 Admin API 的 `/probes` 端点探测

### 10.3 认证失败

- 确认环境变量 `LLMTIER_ADMIN_TOKEN` / `LLMTIER_DATA_TOKEN` 设置正确
- 确认请求 Header 使用正确的 `Authorization: Bearer <token>` 格式

---

## 11. 权限、隐私、合规和注意事项

### 11.1 权限

- Admin API 需要 `LLMTIER_ADMIN_TOKEN`
- Data API 需要 `LLMTIER_DATA_TOKEN`
- 信任局域网模式（`LLMTIER_TRUSTED_LAN_MODE=1`）下，局域网 IP 不需要 token

### 11.2 隐私

- Secret 值只写不读
- 日志不记录 token、prompt、模型输出
- 请求 ID 用于追踪

### 11.3 注意事项

- 生产环境使用 HTTPS
- 妥善保管 token
- 定期备份数据库

---

## 12. Glossary、FAQ 与 Reference

### 12.1 Glossary

| Term | 说明 |
|------|------|
| Provider | 上游模型服务（OMLX、云端 API） |
| Deployment | Deployment 是 Provider 的具体实例 |
| Service Level | 逻辑模型层级，绑定一个或多个 Deployment |
| ETag | 资源版本标识，用于并发控制 |
| Tier | Service Level 的另一种称呼 |

### 12.2 FAQ

**Q: 如何添加新的模型？**
A: 在 Admin API 创建一个新的 Deployment，指定模型名称和 Provider。

**Q: 如何支持多个模型？**
A: 创建多个 Deployment，分别绑定不同的模型，然后用 Service Level 进行分层。

**Q: Provider 不可用时会发生什么？**
A: `/readyz` 返回 503，调用该模型的 API 返回 503。

### 12.3 Reference

- API Reference: `docs/60_interfaces/contracts/llmtier-api-reference.md`
- OpenAPI Spec: `interfaces/openapi/llmtier-v0.3.openapi.json`
- Test Plan: `docs/70_verification/plans/llmtier-v0.3-test-plan.md`
