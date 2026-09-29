# LLMTier V0.3 API Test Suite — A/B Class

> 配套：[`llmtier-system-test-plan.md`](../../../../docs/70_verification/plans/llmtier-system-test-plan.md) §4

已实现（RUN）**88** 个 `at_*.py`（权威设计清单共 **140** 个 Case，其余 52 项为 MISSING 缺口；见测试设计 §3.2），按 pytest marker 分流：

| 类 | marker | 数量 | 执行环境 |
|---|---|---|---|
| A | `@pytest.mark.api_a` | 60 | 直接打 m5air (`192.168.1.9:8181`) 现有实例（读 / 无状态写） |
| B | `@pytest.mark.api_b` | 28 | 临时 SQLite + 临时端口 LLMTier 实例（CRUD / 注入），teardown 清理 |

B 类 fixtures 与 A 类共用同一个 `conftest.py`（`_b` suffix fixtures）；没有独立的
`conftest_b.py`，也没有 `at_b_*.py`——B 类与 A 类用同一套 `at_*.py` 命名 + marker 区分。

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

TS-003：provider **endpoint** 必须是 LAN IP（`192.168.1.x`），禁止 `127.0.0.1` /
`localhost`。B 类 conftest 在机器 LAN IP 上起 fake provider
（`tests/fixtures/v03_fake_provider.py`），provider endpoint 取自该 LAN URL；可用
`LLMTIER_TEST_PROVIDER_URL` 覆盖为其它 LAN URL。

---

## 跑法

```bash
# A 类全量（只跑 api_a marker）
bash tests/system/api_test_v03/runner_a.sh

# B 类全量（只跑 api_b marker，文件集合由 marker 生成）
bash tests/system/api_test_v03/runner_b.sh

# 直接跑（整个目录，不做 marker 过滤）
PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/ -q

# 单个 case
PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_obs_01.py -v

# 强制跑（即使 §2.1 检查失败）
PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/ -q --override-ini="addopts="
```

可调环境变量：`LLMTIER_TEST_TIMEOUT`（httpx 超时秒数，默认 30）、
`LLMTIER_TEST_RETRIES`（瞬时超时重试，0–3，默认 2）、
`LLMTIER_TEST_LAN_IP` / `LLMTIER_TEST_PROVIDER_URL`（B 类 LAN upstream）、
`LLMTIER_TEST_PYTHON`（B 类实例解释器，默认 `sys.executable`）。

---

## 环境就绪检查（§2.1）

`pytest_configure` 阶段跑 6 项检查，全部通过才往下走：

1. m5air `/healthz` 200
2. m5air `/readyz` 200 + 含 7 个 tier
3. m5air OMLX 9000 健康
4. m5mac OMLX 9000 健康
5. provider_omlx_m5mac.secret_ref = file: 路径（非 env:）
6. A 类依赖的 provider / deployment 已注册（`provider_local`、`provider_minimax`、
   `provider_omlx_m5mac`；`dep_local_gemma`、`dep_local_bge_m3`、`dep_omlx_qwen36`、
   `dep_minimax_m27`）

任一失败 → 整个 session skip。

---

## Fixture

- `m5air_base_url` = `http://192.168.1.9:8181`
- `api_client(session)` = httpx.Client，Bearer dev-data
- `admin_client(session)` = httpx.Client，Bearer dev-admin
- `parse_sse()` / `parse_sse_raw()` = helper，解析 SSE 事件流
- B 类：`llmtier_b` / `llmtier_b_empty` / `llmtier_b_no_auth` +
  `admin_client_b` / `api_client_b` / `client_b_empty` 等 `_b` fixture

B 类子进程环境会清空继承的 `LLMTIER_*` 变量，再显式设置
`LLMTIER_TRUSTED_LAN_MODE=1`（dev 实例另设 `LLMTIER_DEV_MODE=1` 与
`dev-admin`/`dev-data` token），保证 auth 行为与设计一致。

---

## Case 命名

`at_<类别>_<编号>.py`，如 `at_obs_01.py`、`at_dp_resp_01.py`、`at_adm_prov_05.py`。

例外：`at_adm_admin_usage_01..03.py` 对应 Case ID `ADM-USAGE-01..03`，文件名由
[`llmtier-system-test-scheme.md`](../../../../docs/70_verification/schemes/llmtier-system-test-scheme.md)
§3 Case 清单显式声明。
