<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier API 测试交接

> STD 使用入口：[项目采用说明与标准导航](../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `api-testing-handoff` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-22` |
| Last Modified Date | `2026-09-22` |
| Template ID | `operations.maintenance` |
| Template Version | `0.1.1` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/80_operations/manuals/api-testing-handoff.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

> 创建日期：2026-09-21。下一次进行 LLMTier API 测试时的交接记录。

## 1. 快速启动

### m5air 当前部署状态

| 项 | 值 |
|---|---|
| 主机 | `192.168.1.9` (m5air) |
| 端口 | `8181`（监听 `0.0.0.0`） |
| 进程 PID | 启动时查询 `ps aux \| grep llmtier_v03.*8181` |
| 代码目录 | `/Users/mlp/LLMTier-dev`（非 git repo） |
| 数据库 | `/Users/mlp/LLMTier-dev/state.sqlite3` |
| Python | `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3` |
| 启动方式 | `PYTHONPATH=src` + `--database` + token env vars |

### 启动命令

```bash
ssh m5air "ps aux | grep 'llmtier_v03.*8181' | grep -v grep | awk '{print \$2}'"  # 查 PID

# Kill 旧进程，重启
ssh m5air "P=\$(ps aux | grep 'llmtier_v03.*8181' | grep -v grep | awk '{print \$2}'); \
  kill \$P 2>/dev/null; sleep 1; \
  cd /Users/mlp/LLMTier-dev && \
  LLMTIER_ADMIN_TOKEN=dev-admin \
  LLMTIER_DATA_TOKEN=dev-data \
  PYTHONPATH=src \
  /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 \
  -m llmtier_v03 \
  --host 0.0.0.0 --port 8181 \
  --database /Users/mlp/LLMTier-dev/state.sqlite3 \
  >> /Users/mlp/LLMTier-dev/llmtier.log 2>&1 &"

# 验证
ssh m5air "curl http://localhost:8181/healthz"
```

**重要**: 必须用 Python 3.14（不是系统 Python 3.9）。`@dataclass(slots=True)` 在 3.9 下报错。

---

## 2. 认证

LLMTier 信任局域网（`192.168.0.0/16`、`10.0.0.0/8`、`172.16.0.0/12`），所以**局域网请求不需要 Bearer token**。

测试 token：
- Admin: `dev-admin`
- Data: `dev-data`

```bash
# 无 token（LAN 信任）
curl http://192.168.1.9:8181/v1/models

# 带 token
curl http://192.168.1.9:8181/v1/providers \
  -H 'Authorization: Bearer dev-admin'
```

---

## 3. 当前 m5air 配置

### 3 Providers

| ID | Name | Kind | Endpoint | Secret |
|---|---|---|---|---|
| `provider_minimax` | MiniMax | cloud | `https://api.minimaxi.com/v1` | `file:/Users/mlp/LLMTier-dev/.mnm_api_key` |
| `provider_local` | m5air oMLX | local | `http://192.168.1.9:9000/v1` | `file:/Users/mlp/LLMTier-dev/secrets/omlx-secret-key.txt` |
| `provider_omlx_m5mac` | m5mac oMLX | local | `http://192.168.1.8:9000/v1` | `env:OMLX_API_KEY` (**未设置**, 会 500) |

### 4 Deployments

| ID | Name | Provider | Backend Model |
|---|---|---|---|
| `dep_minimax_m27` | MiniMax M3 | provider_minimax | MiniMax-M3 |
| `dep_omlx_qwen36` | m5mac Qwen3.6 | provider_omlx_m5mac | Qwen3.6-35B-A3B-4bit-MTPLX-Optimized-Speed |
| `dep_local_gemma` | Gemma 4 E2B | provider_local | gemma-4-e2b-it-4bit |
| `dep_local_bge_m3` | BGE-M3 Embedding | provider_local | bge-m3 |

### 7 Tiers

Senior, Junior, Worker, Associate, Engineer, Executor, Embedding-v1

Senior/Junior/Worker/Associate/Engineer/Executor 都包含 dep_minimax_m27, dep_omlx_qwen36, dep_local_gemma。
Embedding-v1 只包含 dep_local_bge_m3。

### Provider Models（实际返回）

| Provider | 可用模型 |
|---|---|
| provider_minimax | MiniMax-M3, MiniMax-M2.7, MiniMax-M2.7-highspeed, MiniMax-M2.5, MiniMax-M2.5-highspeed, MiniMax-M2.1, MiniMax-M2.1-highspeed, MiniMax-M2 |
| provider_local | bge-m3, gemma-4-e2b-it-4bit |
| provider_omlx_m5mac | **500 错误**（OMLX_API_KEY 未设置） |

---

## 4. API 端点清单（截至 V0.3）

### Data Plane
| Method | Path |
|---|---|
| GET | `/v1/models` |
| GET | `/v1/models/{model}` |
| POST | `/v1/responses` |
| POST | `/v1/embeddings` |
| GET | `/v1/usage` |

### Observation
| Method | Path |
|---|---|
| GET | `/healthz` |
| GET | `/readyz` |

### Admin Management
| Method | Path |
|---|---|
| GET | `/v1/providers` |
| POST | `/v1/providers` |
| GET | `/v1/providers/{id}` |
| PATCH | `/v1/providers/{id}` |
| DELETE | `/v1/providers/{id}` |
| GET | `/v1/providers/{id}/usage` |
| POST | `/v1/providers/{id}/usage` |
| GET | `/v1/providers/{id}/models` |
| GET | `/v1/deployments` |
| POST | `/v1/deployments` |
| GET | `/v1/deployments/{id}` |
| PATCH | `/v1/deployments/{id}` |
| DELETE | `/v1/deployments/{id}` |
| GET | `/v1/service-levels` |
| POST | `/v1/service-levels` |
| GET | `/v1/service-levels/{id}` |
| PATCH | `/v1/service-levels/{id}` |
| DELETE | `/v1/service-levels/{id}` |
| POST | `/v1/probes` |
| GET | `/v1/usage` |
| GET | `/v1/audit` |
| GET | `/v1/logs` |
| GET | `/v1/runtime` |
| GET | `/v1/stats` |

---

## 5. 测试用例清单（57 个，来自 `docs/70_verification/plans/llmtier-api-test-plan.md`）

| 分组 | Case IDs | 数量 |
|---|---|---|
| Observation | OBS-01~03 | 3 |
| Data Plane Models | DP-MODELS-01~06 | 6 |
| Data Plane Responses | DP-RESP-01~09 | 9 |
| Data Plane Embeddings | DP-EMB-01~04 | 4 |
| Data Plane Usage | DP-USAGE-01~04 | 4 |
| Admin Providers CRUD | ADM-PROV-01~09 | 9 |
| Admin Deployments CRUD | ADM-DEPL-01~05 | 5 |
| Admin Service Levels CRUD | ADM-SL-01~05 | 5 |
| Admin Probes & Usage | ADM-PROBE, ADM-PROV-USAGE, ADM-ADMIN-USAGE | 6 |
| Admin Audit/Logs/Runtime/Stats | ADM-AUDIT-01~02, ADM-LOGS-01~02, ADM-RUNTIME-01, ADM-STATS-01~03 | 7 |
| Auth | AUTH-01~06 | 6 |

详细测试计划：`docs/70_verification/plans/llmtier-api-test-plan.md`

---

## 6. 测试脚本

### 现有工具

- `tools/api_smoke_test.py` — 21 个 endpoint smoke 测试，手动运行
- `tests/system/st_*.py` — ST-01~ST-26 系统测试（部分覆盖 API）
- `tools/contract_semantic_validator_v03.py` — OpenAPI 静态校验

### 测试脚本模式

```bash
# 系统测试
PYTHONPATH=src python3 -m pytest tests/system/st_*.py -v

# 单元测试
PYTHONPATH=src python3 -m pytest tests/ -q

# 全部
PYTHONPATH=src python3 -m pytest tests/ tests/system/st_*.py -q
```

### 当前状态
- 单元测试：191/191 PASS
- 系统测试 ST：30/30 已实现（含部分 BLOCKED）

---

## 7. 关键 curl 模板

### 基础请求

```bash
# Health check
curl -s http://192.168.1.9:8181/healthz

# Ready check
curl -s http://192.168.1.9:8181/readyz | python3 -m json.tool

# 列出模型
curl -s http://192.168.1.9:8181/v1/models | python3 -m json.tool

# 获取特定模型
curl -s http://192.168.1.9:8181/v1/models/Worker | python3 -m json.tool
```

### Data Plane — Responses（SSE 流式）

```bash
curl -X POST http://192.168.1.9:8181/v1/responses \
  -H 'Authorization: Bearer dev-data' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Worker",
    "input": [{"role": "user", "content": "Hello"}],
    "stream": true,
    "max_output_tokens": 100
  }'

# 非流式
curl -X POST http://192.168.1.9:8181/v1/responses \
  -H 'Authorization: Bearer dev-data' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Worker",
    "input": [{"role": "user", "content": "Hello"}],
    "stream": false
  }' | python3 -m json.tool
```

### Data Plane — Embeddings

```bash
curl -X POST http://192.168.1.9:8181/v1/embeddings \
  -H 'Authorization: Bearer dev-data' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Embedding-v1",
    "input": "Hello world"
  }' | python3 -m json.tool
```

### Admin — Providers CRUD

```bash
# 列出
curl -s http://192.168.1.9:8181/v1/providers | python3 -m json.tool

# 创建（带 secret_ref）
curl -X POST http://192.168.1.9:8181/v1/providers \
  -H 'Authorization: Bearer dev-admin' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Test Provider",
    "kind": "local",
    "endpoint": "http://192.168.1.9:9000/v1",
    "secret_ref": "file:/Users/mlp/LLMTier-dev/secrets/omlx-secret-key.txt",
    "enabled": true
  }'

# 获取特定 provider 的模型列表（需要 admin auth）
curl -s http://192.168.1.9:8181/v1/providers/provider_minimax/models \
  -H 'Authorization: Bearer dev-admin' | python3 -m json.tool

# 更新（需要 If-Match ETag）
ETAG=$(curl -sI http://192.168.1.9:8181/v1/providers/provider_minimax | grep -i etag | awk '{print \$2}' | tr -d '\r')
curl -X PATCH http://192.168.1.9:8181/v1/providers/provider_minimax \
  -H 'Authorization: Bearer dev-admin' \
  -H "If-Match: $ETAG" \
  -H 'Content-Type: application/json' \
  -d '{"name": "MiniMax (renamed)"}'
```

### Admin — Deployments

```bash
# 列出
curl -s http://192.168.1.9:8181/v1/deployments | python3 -m json.tool

# 创建
curl -X POST http://192.168.1.9:8181/v1/deployments \
  -H 'Authorization: Bearer dev-admin' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "MiniMax-M2.7",
    "provider_id": "provider_minimax",
    "backend_model": "MiniMax-M2.7",
    "capabilities": {
      "responses": true, "embeddings": false, "tools": false,
      "structured_outputs": false,
      "input_modalities": ["text"],
      "output_modalities": ["text"],
      "context_window": 128000,
      "max_output_tokens": 16384
    },
    "enabled": true
  }'
```

### Admin — Service Levels

```bash
curl -s http://192.168.1.9:8181/v1/service-levels | python3 -m json.tool
```

### Admin — Stats

```bash
# Stats 需要 from/to 参数
curl -s "http://192.168.1.9:8181/v1/stats?from=2026-01-01T00:00:00Z&to=2026-12-31T23:59:59Z&group_by=tier" \
  -H 'Authorization: Bearer dev-admin' | python3 -m json.tool
```

### Admin — Audit / Logs / Runtime

```bash
# Audit
curl -s http://192.168.1.9:8181/v1/audit \
  -H 'Authorization: Bearer dev-admin' | python3 -m json.tool

# Logs（需要 from/to）
curl -s "http://192.168.1.9:8181/v1/logs?from=2026-01-01T00:00:00Z&to=2026-12-31T23:59:59Z" \
  -H 'Authorization: Bearer dev-admin' | python3 -m json.tool

# Runtime
curl -s http://192.168.1.9:8181/v1/runtime \
  -H 'Authorization: Bearer dev-admin' | python3 -m json.tool
```

---

## 8. 已知问题

1. **provider_omlx_m5mac 返回 500**: `env:OMLX_API_KEY` 在 m5air 上未设置。修复：在 m5air 启动时设 `OMLX_API_KEY=<value>` env，或改用 `file:` ref。

2. **Models 维度硬编码**: OMLX bge-m3 必须返回 1024 维向量，否则 embedding 接口失败。

3. **WebUI 是早期版本**: Web UI 不是 API 测试范围，但 UI 改动可能影响 API 行为（比如 `available_for_routing` checkbox）。

---

## 9. 同步代码到 m5air

修改代码后（**不是 git push**，因为 m5air 不是 git repo）：

```bash
# rsync 修改的文件
rsync -avz /Users/ben/work/LLMTier/src/llmtier_v03/webui/app.js \
  m5air:/Users/mlp/LLMTier-dev/src/llmtier_v03/webui/app.js

# 重启服务（用上面"启动命令"部分的命令）
```

详细指南：`docs/80_operations/manuals/m5air-deploy-guide.md`

---

## 10. 验证脚本（用于 API 测试自动化）

放在 `/tmp/api_test.py`，跑：

```bash
python3 /tmp/api_test.py
```

基本结构：

```python
import urllib.request, json
BASE = "http://192.168.1.9:8181"
HEADERS = {"Authorization": "Bearer dev-admin"}

def get(path):
    req = urllib.request.Request(f"{BASE}{path}", headers=HEADERS)
    return json.loads(urllib.request.urlopen(req).read())

def post(path, body):
    req = urllib.request.Request(f"{BASE}{path}", method="POST",
        headers={**HEADERS, "Content-Type": "application/json"},
        data=json.dumps(body).encode())
    return json.loads(urllib.request.urlopen(req).read())

# Test 1: Models
print("Models:", get("/v1/models"))

# Test 2: Responses
print("Response:", post("/v1/responses", {"model": "Worker", "input": [{"role":"user","content":"hi"}], "stream": False, "max_output_tokens": 10}))

# Test 3: Embeddings
print("Embedding:", post("/v1/embeddings", {"model": "Embedding-v1", "input": "hello"}))
```

---

## 11. 注意事项

- 所有 POST 请求必须用 `Content-Type: application/json`
- Admin PATCH/DELETE 需要 `If-Match: <ETag>` header（并发控制）
- Admin usage refresh 需要 `confirm_external_call: true` body 字段
- Admin probes 需要 `confirm_external_call: true` body 字段
- Stats 必须有 `from` + `to` query 参数
- Logs 必须有 `from` + `to` query 参数
- LAN 内请求不需要 Bearer token；外部请求需要

---

## 12. 文档索引

- API 测试计划：`docs/70_verification/plans/llmtier-api-test-plan.md`（57 个测试用例）
- API Reference：`docs/60_interfaces/contracts/llmtier-api-reference.md`
- OpenAPI 机器契约：`interfaces/openapi/llmtier.openapi.json`
- m5air 部署指南：`docs/80_operations/manuals/m5air-deploy-guide.md`
- 系统测试 ST：`tests/system/st_*.py`
- smoke test：`tools/api_smoke_test.py`