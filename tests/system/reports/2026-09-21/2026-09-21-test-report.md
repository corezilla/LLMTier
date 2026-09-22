# LLMTier v0.3 Test Report

**Date**: 2026-09-21
**Branch**: `docs/std-draft21-upgrade`
**Commits**: 21dbd27, c42dcee, 24643f4

---

## Test Summary

| Suite | Tests | Passed | Skipped | Failed |
|-------|-------|--------|---------|--------|
| Unit | 191 | 191 | 0 | 0 |
| System | 30 | 30 | 0 | 0 |
| **Total** | **221** | **221** | **0** | **0** |

---

## System Tests Detail

| ID | Name | Tests | Status | Notes |
|----|------|-------|--------|-------|
| ST-01 | Boot baseline | 3 | PASS | FD ≤ 80, /healthz 200, /readyz 200 |
| ST-02 | Contract validator | 1 | PASS | OpenAPI spec validation |
| ST-03 | Models exact case | 5 | PASS | Correct case required |
| ST-04 | Forbidden path scan | 4 | PASS | No legacy paths |
| ST-09 | Error directory | 5 | PASS | stream/store/error handling |
| ST-12 | Embedding invariant | 1 | PASS | 1024-dim bge-m3 embedding |
| ST-15A | Audit log filter | 4 | PASS | Log level filtering |
| ST-22 | Rate limit queue | 1 | PASS | 6 concurrent queued |
| ST-23 | Queue full | 1 | PASS | 33rd request gets 429 |
| ST-25 | Trusted LAN routing | 3 | PASS | No bearer auth in LAN mode |
| ST-26 | Provider attribution | 2 | PASS | Request attribution |

---

## API Smoke Test

`tools/api_smoke_test.py` — covers all external endpoints:

| Category | Endpoint | Status |
|----------|----------|--------|
| Public | GET /healthz | 200 |
| Public | GET /readyz | 503 (no healthy deployments) |
| Public | GET /v1/models | 200 |
| Public | GET /v1/models/Worker | 200 |
| Data | POST /v1/responses | 400 (no healthy deployment) |
| Data | GET /tier/v1/usage | 200 |
| Admin | GET /tier/admin/v1/providers | 200 |
| Admin | POST /tier/admin/v1/providers | 201 |
| Admin | GET /tier/admin/v1/providers/{id} | 200 |
| Admin | PATCH /tier/admin/v1/providers/{id} | 200 |
| Admin | GET /tier/admin/v1/deployments | 200 |
| Admin | POST /tier/admin/v1/deployments | 201 |
| Admin | GET /tier/admin/v1/deployments/{id} | 200 |
| Admin | PATCH /tier/admin/v1/deployments/{id} | 200 |
| Admin | GET /tier/admin/v1/service-levels | 200 |
| Admin | GET /tier/admin/v1/runtime | 200 |
| Admin | POST /tier/admin/v1/probes | 400 (confirm_external_call=false) |
| Admin | GET /tier/admin/v1/usage | 200 |
| Admin | GET /tier/admin/v1/audit | 200 |
| Admin | GET /tier/admin/v1/logs | 200 |
| Cleanup | DELETE /tier/admin/v1/deployments/{id} | 204 |
| Cleanup | DELETE /tier/admin/v1/providers/{id} | 204 |

**ALL PASSED**

---

## Bugs Found & Fixed

### API Smoke Test
1. f-string 嵌套引号语法错误
2. subprocess 缺少 LLMTIER_DATA_TOKEN 环境变量
3. /tier/v1/usage 缺少 RFC3339 时间参数
4. Provider create 传了 id 字段（auto-generated）
5. Deployment capabilities 缺少 embedding 字段

### ST-12 Embedding
1. 硬编码 127.0.0.1:9100 — 应该用 LAN IP（LLMTier 是 LAN 服务）
2. Provider 配置有多余的 usage 字段
3. _omlx_key() operator precedence bug

---

## Environment

- **m5mac** (dev machine): `192.168.1.8`
- **m5air** (ops environment): `192.168.1.9`
- **OMLX** on m5air: `http://192.168.1.9:9000/v1`, model `bge-m3`
- **OMLX** on m5mac: `http://192.168.1.8:9000`, model `Qwen3-Embedding-0.6B-4bit-DWQ`
