# LLMTier V0.3 API Test Suite — A Class

> 配套：[`llmtier-v0.3-api-test-plan.md`](../../../../docs/70_verification/plans/llmtier-v0.3-api-test-plan.md) §4

A 类 case（53 个）：直接打 m5air (`192.168.1.9:8181`) 现有实例。读操作 / 无状态写。

B 类 case（15 个）在 `conftest_b.py` + `at_b_*.py`，走临时 SQLite 实例。

---

## 文件头部依赖（TS-002）

每个 `at_*.py` 文件头部按以下格式写明依赖：

```python
"""Case ID: <ID>

Endpoint: <METHOD> <PATH>
Upstream Provider: <id>（如适用）
Model: <backend_model>（如适用）
Auth: Bearer <token> | LAN trust
"""
```

---

## 跑法

```bash
# A 类全量
PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/ -q

# 单个 case
PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_obs_01.py -v

# 强制跑（即使 §2.1 检查失败）
PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/ -q --override-ini="addopts="
```

---

## 环境就绪检查（§2.1）

pytest_configure 阶段跑 5 项检查，全部通过才往下走：

1. m5air `/healthz` 200
2. m5air `/readyz` 200 + 含 7 个 tier
3. m5air OMLX 9000 健康
4. m5mac OMLX 9000 健康
5. provider_omlx_m5mac.secret_ref = file: 路径（非 env:）

任一失败 → 整个 session skip。

---

## Fixture

- `m5air_base_url` = `http://192.168.1.9:8181`
- `api_client(session)` = httpx.Client，Bearer dev-data
- `admin_client(session)` = httpx.Client，Bearer dev-admin
- `sse_events()` = helper，解析 SSE 事件流

---

## Case 命名

`at_<类别>_<编号>.py`，如 `at_obs_01.py`、`at_dp_resp_01.py`、`at_adm_prov_05.py`。
