<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 API Test Execution Plan

> 配套文档：[`llmtier-api-test-plan.md`](./llmtier-api-test-plan.md)（执行层：顺序/批次/门禁/恢复/回归）与 [`llmtier-api-test-specification.md`](../specifications/llmtier-api-test-specification.md)（测试设计 + 权威 Case 清单）。本文件是**项目管理层**计划：分阶段、产出物、依赖、人/工时估算、风险与回滚。
>
> **测试环境设计**（环境拓扑与隔离决策、被测版本锚定、启动/重启、复位、结果回收、与运维文档分工）见 [`llmtier-api-test-plan.md`](./llmtier-api-test-plan.md) **§2-E1–§2-E6**；本文件**不重复**该设计，只引用。执行 A/B 类、更新 m5air、重启或复位前，先按 §2-E2–§2-E4 操作。

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-api-test-execution` |
| Document Version | `0.2.0-draft.7` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-21` |
| Last Modified Date | `2026-09-29` |
| Template ID | `assurance.test-plan` |
| Template Version | `0.2.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | `llmtier-api-test-plan` |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/plans/llmtier-api-test-execution.md` |
| Supersedes | none |
| Gate Owner | 待填（执行负责人） |
| Gate Approver | 待填（见证/裁决） |
| Gate Approval Date | 待填（ISO-8601） |

> Reviewer、Approver、Approval Date、Gate Owner/Approver/Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. 目标与定位

把 [`llmtier-api-test-specification.md`](../specifications/llmtier-api-test-specification.md) 的**权威 140 个 Case**（A 89 / B 51；P0 45 / P1 72 / P2 23）从"设计"落到"可执行 + 可回归"，并把执行编排、恢复、门禁落地。

**当前实现状态**：**88 RUN / 52 MISSING**（按环境：RUN = A 60 + B 28；MISSING = A 29 + B 23）。计数以测试设计 §3.2 权威清单为准，测试设计升版时本节随之回填。

- 一 Case 一入口（`tests/system/api_test_v03/at_*.py`；`HEALTH-*` 由 `at_obs_01..03.py` 承接）
- 每个 case 跑前自动做环境就绪检查（测试设计 §2.1 / 执行层计划 §7.1.0），失败 → SKIP/BLOCKED
- 每个 case 跑后产出 PASS/FAIL/SKIP/BLOCKED/INVALID/NOT_RUN + 必要字段
- 全量结果落 `tests/system/reports/<date>/`（Run ID `<date>/<class>-<phase>`）；case 状态账本 `case-status.json`（执行层计划 §7.1.6）

**不在本执行计划范围**：单元测试、contract static、UI E2E、performance SLA 校准。

**父文档说明**：功能父对象是测试设计 `llmtier-api-test-specification`；STD `parent_document_id` 只接受设计文档，故元数据保持 `llmtier-system-design`（同 `llmtier-api-test-plan`），功能父关系以本文件引用表达。

---

## 2. 阶段划分（按 A/B 类）

### 2.1 A 类 vs B 类回顾

| 类 | 含义 | 设计数 | 已实现 (RUN) | 执行方式 |
|---|---|---|---|---|
| **A** | 读 / 观察 / 无状态写 | 89 | 60 | **开发机**经 LAN 打 m5air (`192.168.1.9:8181`) 现有实例 |
| **B** | 创建/修改/删除 / 空库 / 无鉴权 / 注入/并发 | 51 | 28 | **开发机**本机第二进程：临时 SQLite + 临时端口，teardown 清理 |

A 类与 B 类不能共享同一进程的 SQLite（写干扰），所以分两阶段跑；A/B 不并行（执行层计划 §3.2）。**A 类沿用 m5air 现有实例**（隔离决策与"专用测试部署"的级联后果见执行层计划 §2-E1）；**启停与复位按执行层计划 §2-E3/§2-E4**，部署/备份/回滚的权威仍是 `m5air-deploy-guide.md` 与 `m5air-operations-manual.md`（分工见 §2-E6）。

### 2.2 阶段表

| 阶段 | 名称 | 产出物 | 依赖 | 工时 |
|---|---|---|---|---|
| **P0** | 测试基线 + `conftest.py`（就绪检查 + 客户端 + `LLMTierInstance`）+ A/B runner | `tests/system/api_test_v03/` 骨架、`conftest.py`、`runner_a.sh`、`runner_b.sh` | 无 | 3h |
| **P1** | A 类 case | A 类 `at_*.py`（已实现 60；MISSING 20 待补） | P0 | 11h |
| **P2** | B 类 case（临时实例 lifecycle） | B 类 `at_*.py`（已实现 28；MISSING 17 待补），复用 `conftest.py` 的 `LLMTierInstance` | P1（验证 A 类不污染 m5air） | 7h |
| **P3** | 首跑 + 报告 | `tests/system/reports/<date>/<date>-api-test-report.md` + `case-status.json` | P1 + P2 | 2h |
| **P4** | CI 接入（可选） | self-hosted workflow | P3 | 4h |
| **总计** | | | | **~27 人·小时** |

---

## 3. 每阶段详细计划

### P0 — 测试基线 + conftest + runner（3h）

**目标**：搭好目录、写好 `conftest.py`、确认 §2.1 五项检查能跑通。

**任务**：

1. 建目录 `tests/system/api_test_v03/`
2. 写 `tests/system/api_test_v03/conftest.py`（**单文件**，A/B 共用；不存在独立的 `conftest_b.py`）：
   - `pytest_configure(session)` + `pytest_report_header`：跑 §2.1 五项检查；不通过 → 整个 suite skip（`pytest_collection_modifyitems` 统一加 skip marker）
   - `fixture(scope="session") api_client`：httpx.Client，base_url=`http://192.168.1.9:8181`，`Authorization: Bearer dev-data`
   - `fixture(scope="session") admin_client`：同上 + `Authorization: Bearer dev-admin`
   - `parse_sse` / `parse_sse_raw`：SSE 逐帧解析 helper
   - `LLMTierInstance` + B fixtures：`llmtier_b`（`_baseline_settings`：`prov_b` + `depl_b` + 7 tier）、`llmtier_b_empty`（`_EMPTY_SETTINGS`）、`llmtier_b_no_auth`（`_NO_AUTH_SETTINGS`，`dev_mode=False`）；session-scope，临时端口 + 临时 SQLite，`stop()` `terminate`→5 s→`kill` + `rm -rf`
3. 写 `runner_a.sh`（`pytest -m api_a`）与 `runner_b.sh`（`pytest -m api_b`）；markers 注册于 `pyproject.toml`，runner 不再手工维护文件清单
4. **首次跑验证**：故意把 m5air 关掉 → 确认 suite skip + 输出"§2.1 第 1 项 /healthz 不通"；随后按执行层计划 §2-E3（Python 3.14 重启 → `/healthz` 验证）恢复，并重跑 §2.1 就绪检查（§2-E4）

**验收**：
- `PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/ -q` 跑起来不报错
- m5air 正常时无 skip；m5air 挂时整 suite skip
- `LLMTierInstance` 能在本机起临时实例并通过 `/healthz`

### P1 — A 类 case（11h）

**目标**：A 类 case 全部 PASS（已实现 60；设计 80，MISSING 20 待补）。

**任务**：按测试设计 §3.2 权威清单与各 `cases/<lowercased-case-id>.md` 契约补齐/校准 A 类 `at_*.py`。

**关键点（易踩坑）**：

- SSE 完整序列：`httpx.stream` + 手工解析 `event:` / `data:` 行；断言事件序列 + 唯一 terminal + `data: [DONE]`
- 断言策略与 Oracle 见测试设计 §4.5/§4.6/§4.10 与 `cases/<id>.md`（本文件不复制断言）
- `DP-USAGE-04`（cursor expired）：`sqlite3` 直连 m5air 数据库改 `expires_at` 造过期 cursor（需权限，执行前记录原值、执行后复位）
- `ADM-AUDIT-01` / `ADM-LOGS-01`（敏感信息扫描）：断言响应 body 不含 `9832`、不含 key 文件内容
- AUTH-02/AUTH-03/AUTH-06：LAN trust 模式下的 401/403 语义见 `cases/auth-*.md`

**验收**：
- A 类已实现 case 全部 PASS 或 SKIP（上游挂 → SKIP，不超过 5 个）
- 测试文件头部按 TS-002 写明依赖

### P2 — B 类 case（临时实例，7h）

**目标**：B 类 case 全部 PASS；teardown 干净不污染 m5air（已实现 28；设计 45，MISSING 17 待补）。

**任务**：

1. 复用 `conftest.py` 的 `LLMTierInstance`（**不是** `conftest_b.py`）：
   - 端口：`_find_free_port()`（OS 分配空闲端口）
   - 数据库：`tempfile.mkdtemp(prefix="llmtier_b_")/test.sqlite3`（`LLMTIER_DATABASE`）
   - settings：每 run 写 `settings.json` 并置 `LLMTIER_SETTINGS`；`LLMTIER_DEV_MODE=1`
   - Python：执行机 `sys.executable`（开发机 3.14）
   - 启动：`python3 -m http_api --host 127.0.0.1 --port <port>`；`start()` 轮询 `/healthz`（40×0.25 s）
   - teardown：`stop()` → `terminate`→等 5 s→`kill` + `rm -rf` 临时目录
2. 按测试设计 §3.2/§3.3 与各 `cases/<id>.md` 补齐/校准 B 类 `at_*.py`
3. 运行：`bash tests/system/api_test_v03/runner_b.sh`（= `pytest -m api_b`，按 marker 选择 B 类实现）

**关键点**：

- fixture 模板**禁止传 `id`**；`secret_ref` 用 `file:`（`chmod 600`）
- `If-Match` 格式 `"<id>.v<N>"`（**带双引号**）；缺/过期 → 412 `version_conflict` + body `current_version`
- `capabilities` **12 键全集**（见测试设计 §4.10）
- `provider_id` 不可 PATCH；FIXED_TIER 删除 → 409 `fixed_service_level`
- **teardown 必须做**：每 case 删除自己创建的资源；runner 跑完 kill 临时实例 + rm tmpdir

**验收**：
- B 类已实现 case 全部 PASS
- m5air 现有 state 完全未变（curl 对比前后 provider/deployment/service-level 列表）

### P3 — 首跑 + 报告（2h）

**任务**：

1. `bash tests/system/api_test_v03/runner_a.sh && bash tests/system/api_test_v03/runner_b.sh`（或全量 `pytest tests/system/api_test_v03/ -q`），捕获所有 case 结果与 `case-status.json`
2. 按执行层计划 §7.2 判定 PASS/FAIL/SKIP/BLOCKED/INVALID/NOT_RUN；跑 `-m api_a` / `-m api_b` 分开汇总
3. 写 `tests/system/reports/<date>/<date>-api-test-report.md`：
   - 总览（140 设计 case 状态分布；A 89 / B 51；RUN 88 / MISSING 52）
   - 失败 case 详情（`failure_reason` + `reproduction_cmd`）
   - 跳过 case 列表（`skip_reason` + `fix_owner` + `eta`）
   - 阻塞 case 列表（`block_reason` + `required_resolution`）
   - 具名缺口（执行层计划 §3.6.2）与回归 diff（§9）
4. 评审：FAIL + BLOCKED + INVALID = 0；**P0 MISSING 阻断**；SKIP ≤ 上限（A 5 / B 3）

### P4 — CI 接入（可选，4h）

**前提**：CI runner 能访问 m5air（`192.168.1.9`）和 m5mac OMLX——**目前云端 GitHub Actions 不可行**。可选项：
- 本地 self-hosted runner（装在开发机或 m5air 上）
- 仅本地 pre-push hook，不上 CI

**任务**（如选 self-hosted）：

1. `.github/workflows/api-test.yml`：触发 `pull_request` + `push to main`
2. runner step：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/ -q`（或 `-m api_a` / `-m api_b` 分开）
3. 上传报告与 `case-status.json` 到 artifacts

---

## 4. 依赖与前置条件

| 依赖 | 详情 | 状态 |
|---|---|---|
| m5air LLMTier 服务运行 | `192.168.1.9:8181`（**现有实例**，隔离决策见执行层计划 §2-E1） | ✅ 已知运行 |
| m5air OMLX 9000 | 上游 `provider_local` | ✅ 已知健康 |
| m5mac OMLX 9000 | 上游 `provider_omlx_m5mac` | ⚠️ 修复后需实测 |
| `provider_omlx_m5mac.secret_ref` | `file:` 路径 + `chmod 600` | ✅ 已修 |
| schema_version | m5air `state.sqlite3` `schema_meta.schema_version` = `EXPECTED_SCHEMA_VERSION`（2） | ✅（不匹配见 §7.1.2 恢复） |
| m5air sqlite3 直连权限 | 需直接构造 DB 状态的 case（见该 case 文档） | ⚠️ 待验证 |
| Python 3.14 | 开发机 / m5air 启动实例 | ✅ 已确认 |
| 140 case 在测试设计中明确 | `llmtier-api-test-specification.md` §3.2（140；RUN 88 / MISSING 52） | ✅ |
| 测试机在 192.168.x LAN 内 | TS-003（被测服务上游 endpoint 必须 LAN IP） | ✅ |
| 临时实例启停权限 | `/tmp` 写、端口 bind | ✅ |

---

## 5. 风险与缓解

| 风险 | 影响 | 概率 | 缓解 |
|---|---|---|---|
| m5mac OMLX 挂掉 | DP-RESP fallback case SKIP | 中 | §2.1 检查第 4 项；P1 跑完后看 SKIP 列表 |
| OMLX 临时挂 | 多 case SKIP | 中 | `conftest.py` 输出原因 + §2.1 检查项编号 |
| B 类 teardown 不彻底 | m5air 残留 provider/deployment | 中 | runner kill 临时实例 + 校验 m5air 状态对比 |
| schema_version 不匹配 | 启动 503、整班 BLOCKED | 低 | §7.1.0 schema_version 检查；§7.1.2 显式二选一恢复；复位前先冷备份（§2-E4） |
| 误把 A 类测试打到 m5air 生产 state | 既有资源/usage 被误删或被污染 | 低 | A 类只做只读/无状态写且写后 teardown；残留核验按 §2-E4；隔离决策与专用测试部署触发条件见 §2-E1 |
| BLOCKED vs FAIL 判定分歧 | 报告不统一 | 中 | runner 强制六态判定；FAIL/BLOCKED/INVALID 都阻塞 release |
| If-Match / capabilities 断言脆弱 | 412/400 假阴性 | 低 | 测试设计 §4.10 常量 + `cases/<id>.md` Oracle |
| SSE 解析器随 httpx 版本漂移 | false PASS | 低 | 锁定 httpx 版本；纯字节解析（不用 httpx SSE helper） |
| SKIP 超上限 | 覆盖不足放行 | 中 | runner exit code 2 + §7.2 上限（A 5 / B 3） |

---

## 6. 决策记录

| 决策 | 理由 |
|---|---|
| 执行机 = 开发机；m5air 是被测目标机 | 与测试设计 §2.7/§8、执行层计划 §5.1 一致 |
| A 类 / B 类分流 | B 类写/空库/无鉴权/注入用临时实例；A 类读/无状态写用 m5air 现有 state |
| B fixtures 收敛进单文件 `conftest.py` | 避免 `conftest_b.py` 与 A fixture 冲突；session-scope `LLMTierInstance` |
| 全量入口用 `-m api_a` / `-m api_b` | markers 注册于 `pyproject.toml`；取代早期四散 runner |
| 移除 `runner_all.sh` | 该脚本从未存在；全量用 `pytest tests/system/api_test_v03/ -q`，A/B 用 `-m` 或 `runner_a.sh`/`runner_b.sh` |
| case 总数 89 → **140** | 测试设计升版后的权威清单（A 89 / B 51；P0 45 / P1 72 / P2 23） |
| 设计状态与实现分离 | `RUN 88 / MISSING 52` 如实登记；MISSING 是缺口不是 SKIP，P0 MISSING 阻断 |
| `DP-USAGE-04` 用 sqlite3 UPDATE | 真造过期 cursor，而非 `cursor="expired"` 字面值 |
| 执行韧性 + 恢复手册 | 单 case 受阻就地恢复继续；系统性受阻诊断后断点续跑（执行层计划 §7.1） |
| A 类沿用 m5air 现有实例（不引入专用测试部署） | 与测试设计 §2.3/§2.4、`M5AIR_BASE`、§2.1 就绪检查一致；A 类定义为只读/无状态写且可 teardown。专用测试部署属拓扑变更，其级联后果与触发条件已登记在执行层计划 §2-E1 |
| 证据回收 + `xfailed → BLOCKED` 映射 | 报告工具强制把 `xfailed` 映射为 BLOCKED、`xpassed` 告警、`skipped` 为 SKIP（执行层计划 §2-E5），防 xfail 静默豁免 |

---

## 7. 执行节奏

**单人 ~24h（3 个完整工作日）**：

```
Day 1：P0（3h） + P1 前半（5h）
Day 2：P1 后半（3h） + P2 前半（4h）
Day 3：P2 收尾（3h） + P3（2h） + 评审（1h）
Day 4（可选）：P4
```

**双人 ~14h（1.5 天）**：

- A：P0 + P1（A 类量大）
- B：P2（临时实例 + B 类 case）
- 共同：P3 + P4 评审

---

## 8. 验收标准（P3 阶段交付）

报告 `tests/system/reports/<date>/<date>-api-test-report.md` 必须满足：

- [ ] 140 个设计 case 每个都有明确状态（PASS/FAIL/SKIP/BLOCKED/INVALID/NOT_RUN），或明确记为 MISSING 缺口
- [ ] 0 个"未跑"无状态
- [ ] FAIL + BLOCKED + INVALID 总数 = 0
- [ ] **P0 MISSING = 0**（P0 缺口阻断 release）；非 P0 MISSING 每条有 owner + ETA + 具名批准
- [ ] SKIP ≤ 上限（A 5 / B 3），每个 SKIP 都有 §2.1 检查项/依赖引用 + `fix_owner` + `eta`；runner exit code ≠ 2
- [ ] 覆盖模型（执行层计划 §3.6）四维下限满足；具名缺口清单已登记
- [ ] 回归 golden/diff（执行层计划 §9）产出 `regression-diff.md`
- [ ] B 类跑完后 m5air 现有 state 未变（curl 比对前后 providers/deployments/service-levels 列表）
- [ ] Gate Owner / Gate Approver / Baseline Run ID 已填写（执行层计划 §10）

---

## 9. 文档索引

- 测试设计（权威 Case 清单）：[`llmtier-api-test-specification.md`](../specifications/llmtier-api-test-specification.md)（v0.4.0-draft.3）
- 执行层计划（顺序/批次/门禁/恢复/回归 + 测试环境设计 §2-E1–§2-E6）：[`llmtier-api-test-plan.md`](./llmtier-api-test-plan.md)（v0.3.0-draft.12）
- 逐 Case 设计：`docs/70_verification/specifications/cases/<lowercased-case-id>.md`
- 高层 V&V：[`llmtier-vv-plan.md`](./llmtier-vv-plan.md)
- 系统测试：[`llmtier-test-plan.md`](./llmtier-test-plan.md)（ST-01~ST-26）
- 历史报告：`tests/system/reports/2026-09-21/`
- 测试套件：`tests/system/api_test_v03/`（`conftest.py`、`at_*.py`、`runner_a.sh`、`runner_b.sh`）
- m5air 部署：`docs/80_operations/manuals/m5air-deploy-guide.md`
- m5air 操作：`docs/80_operations/m5air-operations-manual.md`
- 测试规范：`docs/00_management/standards/testing-standard.md`（TS-001~TS-005）
