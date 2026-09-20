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

创建 `settings.json`：

```json
{
  "providers": [],
  "deployments": [],
  "service_levels": []
}
```

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

### 7.1 Provider 配置

Provider 类型：
- `local`: 本地部署的 OMLX 服务
- `cloud`: 云端 API（如 MiniMax）

Provider 配置项：
- `name`: 显示名称
- `kind`: `local` 或 `cloud`
- `endpoint`: 上游 API 地址
- `secret_ref`: API key 文件路径（`file:/path/to/key.txt`）
- `enabled`: 是否启用

### 7.2 Deployment 配置

Deployment 配置项：
- `name`: 显示名称
- `provider_id`: 绑定的 Provider
- `backend_model`: 上游模型名称
- `capabilities`: 模型能力（responses、embeddings 等）
- `enabled`: 是否启用

### 7.3 Service Level 配置

Service Level 定义逻辑模型层级：
- `id`: 精确匹配的模型 ID（如 `Worker`、`Senior`）
- `deployment_ids`: 该层级的候选 deployment 列表
- `enabled`: 是否启用

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
