# LLMTier Interface Specifications

机器可读的接口与数据模型规范索引。

---

## HTTP API（OpenAPI）

| 文件 | 说明 | 适用场景 |
|------|------|----------|
| `openapi/llmtier-v0.3.openapi.json` | Admin + Data Plane REST API 完整定义 | Agent 解析 API 端点、请求/响应结构、错误码 |

---

## JSON Schema

| 文件 | 说明 | 对应版本 |
|------|------|----------|
| `schemas/llmtier-settings-v0.3.schema.json` | `settings.json` 配置文件结构 | v0.3 |
| `schemas/llmtier-contracts-v0.2.schema.json` | 内部数据模型（历史遗留） | v0.2 |

### settings.json Schema 用途

`llmtier-settings-v0.3.schema.json` 是 LLMTier 启动配置文件的机器可读规范。
Agent 读取后可理解：

- Provider / Deployment / ServiceLevel 三类资源的字段定义、类型、约束
- `capabilities` 12 个标准 key 的名称和含义
- `secret_ref` / `usage_*_ref` 引用路径的格式要求（`env:` / `file:` 前缀）
- 7 个固定 Tier ID（Senior / Junior / Worker / Associate / Engineer / Executor / Embedding-v1）

使用示例：

```bash
# 用 jsonschema 验证配置文件
pip install jsonschema
jsonschema -i config/settings.json interfaces/schemas/llmtier-settings-v0.3.schema.json
```
