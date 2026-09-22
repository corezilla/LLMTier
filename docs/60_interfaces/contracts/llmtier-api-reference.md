<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier API Reference

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-api-reference` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-21` |
| Last Modified Date | `2026-09-22` |
| Template ID | `contracts.specification` |
| Template Version | `0.3.1` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/60_interfaces/contracts/llmtier-api-reference.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Contract scope 与 authority

**API 版本**: `0.3-simplified-candidate.8`

**机器契约权威源**: `interfaces/openapi/llmtier.openapi.json`

LLMTier 提供 OpenAI-compatible HTTP API，供局域网上的 consumer（如 Piko）调用。

### 1.1 接口分类

| 分类 | 说明 | Auth |
|------|------|------|
| **Data Plane** | `/v1/responses`, `/v1/embeddings`, `/v1/models` | Data Bearer Token |
| **Observation** | `/healthz`, `/readyz`, `/v1/usage` | Data Bearer Token |
| **Management** | `/v1/*` | Admin Bearer Token |

### 1.2 服务器信息

```
Base URL: http://<host>:<port>
示例: http://192.168.1.9:8765
```

生产环境应使用 HTTPS。

---

## 2. Operation Catalog

### 2.1 Data Plane

| Method | Path | Summary |
|--------|------|---------|
| `POST` | `/v1/responses` | 创建模型响应，使用 SSE 流式返回 |
| `POST` | `/v1/embeddings` | 创建文本 embedding 向量 |
| `GET` | `/v1/models` | 列出所有可用模型 |
| `GET` | `/v1/models/{model}` | 获取指定模型的详细信息 |

### 2.2 Observation

| Method | Path | Summary |
|--------|------|---------|
| `GET` | `/healthz` | 服务健康检查（总是 200） |
| `GET` | `/readyz` | 服务就绪状态（依赖部署健康） |
| `GET` | `/v1/usage` | 当前用户的 token 使用量 |

### 2.3 Management (Admin)

| Method | Path | Summary |
|--------|------|---------|
| `GET` | `/v1/providers` | 列出所有 provider |
| `POST` | `/v1/providers` | 创建 provider |
| `GET` | `/v1/providers/{provider_id}` | 获取 provider 详情 |
| `PATCH` | `/v1/providers/{provider_id}` | 更新 provider |
| `DELETE` | `/v1/providers/{provider_id}` | 删除 provider |
| `GET` | `/v1/providers/{provider_id}/usage` | 获取 provider 使用量 |
| `POST` | `/v1/providers/{provider_id}/usage` | 刷新 provider 使用量 |
| `GET` | `/v1/deployments` | 列出所有 deployment |
| `POST` | `/v1/deployments` | 创建 deployment |
| `GET` | `/v1/deployments/{deployment_id}` | 获取 deployment 详情 |
| `PATCH` | `/v1/deployments/{deployment_id}` | 更新 deployment |
| `DELETE` | `/v1/deployments/{deployment_id}` | 删除 deployment |
| `GET` | `/v1/service-levels` | 列出所有服务等级 |
| `POST` | `/v1/service-levels` | 创建服务等级 |
| `GET` | `/v1/service-levels/{service_level_id}` | 获取服务等级详情 |
| `PATCH` | `/v1/service-levels/{service_level_id}` | 更新服务等级 |
| `DELETE` | `/v1/service-levels/{service_level_id}` | 删除服务等级 |
| `POST` | `/v1/probes` | 执行 provider 探测 |
| `GET` | `/v1/usage` | 管理面使用量统计 |
| `GET` | `/v1/audit` | 审计事件列表 |
| `GET` | `/v1/logs` | 脱敏日志列表 |

---

## 3. Authentication

### 3.1 Data Plane Auth

使用 `Authorization: Bearer <token>` header。

- `LLMTIER_DATA_TOKEN` 环境变量配置

### 3.2 Admin Auth

使用 `Authorization: Bearer <token>` header。

- `LLMTIER_ADMIN_TOKEN` 环境变量配置

### 3.3 Trusted LAN Mode

当 `LLMTIER_TRUSTED_LAN_MODE=1` 且客户端 IP 在 `192.168.1.0/24` 时：
- 可使用 `trusted-lan-consumer` / `trusted-lan-operator` 角色
- 不需要 Bearer Token

---

## 4. Data Objects

### 4.1 Model

```json
{
  "id": "Worker",
  "object": "model",
  "created": 1234567890,
  "owned_by": "llmtier"
}
```

### 4.2 Response (SSE)

```json
{
  "id": "resp_xxx",
  "object": "response",
  "status": "completed",
  "model": "Worker",
  "output": [
    {
      "type": "message",
      "id": "msg_xxx",
      "role": "assistant",
      "content": [{"type": "output_text", "text": "Hello"}]
    }
  ],
  "usage": {
    "input_tokens": 10,
    "output_tokens": 5,
    "total_tokens": 15
  }
}
```

### 4.3 Embedding

```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "embedding": [0.123, -0.456, ...],
      "index": 0
    }
  ],
  "model": "Embedding-v1",
  "usage": {
    "prompt_tokens": 5,
    "total_tokens": 5
  }
}
```

### 4.4 Provider

```json
{
  "id": "provider_xxx",
  "name": "My Provider",
  "kind": "local",
  "endpoint": "http://192.168.1.8:9000/v1",
  "has_secret": true,
  "enabled": true,
  "usage": { ... },
  "version": 1
}
```

### 4.5 Deployment

```json
{
  "id": "deployment_xxx",
  "name": "My Deployment",
  "provider_id": "provider_xxx",
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
  "enabled": true,
  "health": "healthy"
}
```

### 4.6 Service Level

```json
{
  "id": "Worker",
  "deployment_ids": ["deployment_xxx"],
  "enabled": true
}
```

---

## 5. Error Responses

| HTTP Status | Code | 说明 |
|-------------|------|------|
| `400` | `invalid_request` | 请求参数错误 |
| `401` | `authentication_error` | 认证失败 |
| `403` | `permission_denied` | 权限不足 |
| `404` | `not_found` | 资源不存在 |
| `409` | `resource_conflict` | 资源冲突（如名称重复） |
| `412` | `version_conflict` | ETag 版本不匹配 |
| `429` | `rate_limit_exceeded` | 请求过于频繁 |
| `502` | `provider_error` | 上游 provider 返回错误 |
| `503` | `provider_unavailable` | provider 不可用 |

错误响应格式：

```json
{
  "error": {
    "message": "Human-readable error message",
    "type": "request_error",
    "code": "invalid_request",
    "param": null,
    "retryable": false
  }
}
```

---

## 6. ETag / Concurrency Control

可变更资源（Provider、Deployment、Service Level）使用 ETag 进行并发控制：

- GET 返回 `ETag` header
- PATCH/DELETE 必须发送 `If-Match: <etag>` header
- 版本不匹配返回 `412`

---

## 7. Pagination

列表接口使用游标分页：

```
GET /v1/providers?limit=10&cursor=xxx
```

响应：

```json
{
  "data": [...],
  "page": {
    "has_more": true,
    "next_cursor": "cursor_value"
  }
}
```

---

## 8. Common Headers

| Header | 说明 |
|--------|------|
| `Authorization` | `Bearer <token>` |
| `Content-Type` | `application/json` |
| `If-Match` | ETag for concurrency control |
| `X-Request-ID` | 请求追踪 ID |

---

## 9. Service Tiers (Service Levels)

LLMTier 预定义了以下服务等级：

| Tier ID | 说明 |
|---------|------|
| `Senior` | 最高优先级 |
| `Junior` | 高优先级 |
| `Worker` | 标准优先级 |
| `Associate` | 中优先级 |
| `Engineer` | 工程优先级 |
| `Executor` | 执行优先级 |
| `Embedding-v1` | Embedding 专用 |

---

## 10. Environment Variables

| Variable | 说明 |
|----------|------|
| `LLMTIER_ADMIN_TOKEN` | Admin API 认证 token |
| `LLMTIER_DATA_TOKEN` | Data API 认证 token |
| `LLMTIER_TRUSTED_LAN_MODE` | 启用信任局域网模式（1=on） |
| `LLMTIER_DEV_MODE` | 开发模式（1=on） |
