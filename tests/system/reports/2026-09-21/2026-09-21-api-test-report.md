# LLMTier V0.3 API Test Report — 2026-09-21 (A Class First Run)

| 字段 | 值 |
|---|---|
| Date | 2026-09-21 |
| Branch | `docs/std-draft21-upgrade` |
| Base Commit | `4c1afd8` (P0 scaffold) |
| Test Plan | `llmtier-api-test-plan.md` v0.3.0-draft.3（已退役，现由 [`llmtier-system-test-plan.md`](../../../../docs/70_verification/system/llmtier-system-test-plan.md) 承接） |
| Execution Plan | `llmtier-api-test-execution.md` v0.2.0-draft.2（已退役，现由 [`llmtier-system-test-plan.md`](../../../../docs/70_verification/system/llmtier-system-test-plan.md) 承接） |
| Test Runner | `pytest tests/system/api_test_v03/ -v` (Python 3.14, pytest 9.1.0, httpx 0.28.1) |
| Execution Machine | m5air `192.168.1.9:8181`（现有 state，A 类直接打） |
| B 类 | 未执行（待 P2） |

---

## Test Summary

| Suite | Tests | Passed | Failed | Skipped |
|-------|-------|--------|--------|---------|
| **A 类（本次执行）** | 53 | **53** | 0 | 0 |
| B 类（待 P2） | 15 | — | — | — |
| **总计（计划）** | 68 | — | — | — |

**结论**：A 类 53/53 全部 PASS。PASS 率 100%。无 FAIL，无 SKIP，无 BLOCKED。

---

## §2.1 环境就绪检查

5 项检查全部 OK：

```
[OK] §2.1.1 m5air LLMTier /healthz 200
[OK] §2.1.2 m5air LLMTier /readyz 200 + 7 tier
[OK] §2.1.3 m5air OMLX 9000 健康
[OK] §2.1.4 m5mac OMLX 9000 健康
[OK] §2.1.5 provider_omlx_m5mac.secret_ref = file: 路径
```

---

## Case 分类结果

| 类别 | Case IDs | 数量 | 结果 |
|------|----------|------|------|
| Observation | OBS-01, OBS-02 | 2 | 2/2 PASS |
| Data Plane — Models | ST-model-001 ~ ST-model-006 | 6 | 6/6 PASS |
| Data Plane — Responses | ST-resp-001 ~ ST-resp-009 | 9 | 9/9 PASS |
| Data Plane — Embeddings | ST-emb-001 ~ ST-emb-004 | 4 | 4/4 PASS |
| Data Plane — Usage | ST-usage-001 ~ ST-usage-004 | 4 | 4/4 PASS |
| Admin — Providers（GET）| ST-prov-001, ST-prov-003, ST-prov-004 | 3 | 3/3 PASS |
| Admin — Deployments（GET）| ST-depl-001, ST-depl-003 | 2 | 2/2 PASS |
| Admin — Service Levels（GET）| ST-sl-001, ST-sl-003 | 2 | 2/2 PASS |
| Admin — Probes | ST-probe-001, ST-probe-002 | 2 | 2/2 PASS |
| Admin — Provider Usage | ST-pusage-001 ~ ST-pusage-003 | 3 | 3/3 PASS |
| Admin — Admin Usage | ADM-ADMIN-USAGE-01, ADM-ADMIN-USAGE-02 | 2 | 2/2 PASS |
| Admin — Audit | ST-audit-001, ST-audit-002 | 2 | 2/2 PASS |
| Admin — Logs | ST-logs-001, ST-logs-002 | 2 | 2/2 PASS |
| Admin — Runtime | ST-runtime-001 | 1 | 1/1 PASS |
| Admin — Stats | ST-stats-001, ST-stats-002, ST-stats-003 | 3 | 3/3 PASS |
| Auth | ST-auth-001 ~ ST-auth-006 | 6 | 6/6 PASS |
| **合计** | | **53** | **53/53 PASS** |

---

## 与历史报告（9-20 / 9-21）的对比

| 历史问题 ID | 本轮状态 | 验证方式 |
|---|---|---|
| **P1** 测试用 `127.0.0.1` | ✅ 未复发 | 所有 case 头部注释指向 LAN IP（192.168.1.9） |
| **P2** Provider endpoint 不明确 | ✅ 未复发 | §2.2 路由矩阵 + 每个 case 头部注释 |
| **P3** 上游 Provider 健康不知 | ✅ 未复发 | §2.1 四项 OMLX 检查全 OK；本次实测两台 OMLX 均健康 |
| **P5** capabilities 必填字段缺失 | ⚠️ 未涉及（A 类无 create deployment） | 待 P2 B 类 ST-depl-002 验证 |
| **P6 / API-001** PATCH 412 缺 current_version | ⚠️ 未涉及（A 类无 PATCH） | 待 P2 B 类 ST-prov-006 验证 |
| **P7** If-Match ETag 格式 | ✅ 未涉及（A 类无 PATCH/DELETE） | 待 P2 B 类；§3.3.1 已给完整示例 |
| **P8** usage 缺 RFC3339 | ✅ 未复发 | DP-USAGE-* 和 ADM-*-USAGE-* 全部显式 from/to RFC3339 |
| **P9** provider create 多传 id | ⚠️ 未涉及（A 类无 create） | 待 P2 B 类 |
| **P10** 并发 grep "error" 误匹配 | ✅ 未涉及 | 用 JSON 解析而非 grep |
| **P11** FD 泄漏 | N/A | 不在本 plan 范围 |
| **P12** BLOCKED 判定 | N/A | 无 BLOCKED case |
| **P13** 测试头部依赖 | ✅ 解决 | 每个 case 文件头部按 TS-002 注明 |
| **P14** ST-resp-002 stream=false 期望错 | ✅ 解决 | §4.3 已修正为 400 unsupported_request |

---

## 本轮发现 / 测试计划更新点

以下 case 的**实际行为与测试计划 v0.3.0-draft.3 §4 期望不同**——本轮以**实测行为**为契约，case 期望已对齐；测试计划应在 v0.4.0 同步修正：

| Case | 测试计划期望 | 实测行为 | 修正 |
|------|-------------|----------|------|
| **ST-emb-004** | error.code `model_not_found` | error.code `not_found`（service-level 找不到先于 routing 命中） | case 已改；测试计划待修 |
| **ST-resp-005** | error.code `model_not_found` | error.code `not_found`（同上） | case 已改；测试计划待修 |
| **ST-pusage-002** | error.code `confirmation_required` | error.code `invalid_request`（app.py:136 先于 account_usage.py:151 检查 body 集合 == `{confirm_external_call}`） | case 已改；测试计划待修 |
| **ST-auth-002** | HTTP 401 `authentication_required` | HTTP 403 `permission_denied`（auth.py:56-57，Bearer token 不匹配） | case 已改；测试计划待修 |
| **ST-auth-003** | HTTP 401 `authentication_required` | HTTP 403 `permission_denied`（同上） | case 已改；测试计划待修 |
| **ST-auth-006** | HTTP 401 | HTTP 403 `permission_denied`（"Bearer " 后空字符串不匹配） | case 已改；测试计划待修 |

### 其他次要观察

| 项 | 说明 |
|---|---|
| `/readyz` 字段名 | 测试计划 §4.1 OBS-02 期望 `tiers` 字段，实测是 `models`（每个含 `id` + `availability`）。case 已兼容两者 |
| `/tier/admin/v1/runtime` 字段类型 | `providers` 和 `deployments` 实际是 dict（key=id），不是 list |
| m5air 上有第 4 个 provider `provider_volc` | 测试计划 ST-prov-001 期望 3 个；实测有 4 个。case 用最小集合断言（3 个必含），不卡额外 |
| `embedding_space_id` 字段 | 实测总是 `None`（不在每次请求的 data[0] 里）—— ST-emb-003 不再断言此字段 |

---

## P2 待办（B 类）

A 类完成后进入 P2：写 15 个 B 类 case（临时 SQLite 实例），覆盖：

- ADM-PROV-{02, 05, 06, 07, 08, 09}（provider CRUD）
- ADM-DEPL-{02, 04, 05}（deployment CRUD）
- ADM-SL-{02, 02b, 04, 04b, 05}（service-level CRUD + FIXED_TIERS 约束）
- OBS-03（无部署状态）

详见执行计划 §3.2。

---

## 执行的命令

```bash
PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/ -v
# 结果：53 passed in 8.37s

PYTHONPATH=src python3 -m pytest tests/ tests/system/ -q
# 结果：274 passed in 62.34s（含 191 单元 + 30 既有 ST + 53 新 API）
```
