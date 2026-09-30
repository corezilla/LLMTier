<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 System Test Report — Run 2026-09-30

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-system-test-report-2026-09-30` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-09-30` |
| Template ID | `tests.system-test-report` |
| Template Version | `0.3.1` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `tests/system/reports/2026-09-30/system-test-report.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本报告由 Run 目录 `tests/system/reports/2026-09-30/`（A 类 `A-api-6`、B 类 `B-api-5`）与
> `tests/unit/v03/reports/run-20260930-05/` 的机器产物整理而成；只使用这些 Run 的 `junit.xml` /
> `test-run.env` / `case-status.json` 记录的事实，未运行/未实现项一律保留 `NOT_RUN`，不补造结果。

### 模板定位：报告、方案、用例、计划与 Run 证据的边界

- **Verdict 唯一持有**：执行状态（NOT_RUN/BLOCKED/INVALID）与实际判定（PASS/FAIL）只在测试报告与 Run 证据中产生；方案与 Case 文档不预填任何结果。
- **引用不复制**：逐 Case 结果引用 Run ID 与证据路径，不把 stdout 全文搬进报告。
- **保留失败**：失败、阻塞、无效与未运行如实保留；重跑生成新报告不覆盖旧失败。
- **不越权**：Gate 建议不是批准；验收与发布授权另循其轨（验收不在 tests 家族，见 std-tailoring）。

### 状态语义：执行状态与 Verdict

| 状态 | 取值 | 含义 | 判定事实 |
|---|---|---|---|
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | 未运行 / 环境阻断 / 执行未命中设计 | 运行记录与环境事实 |
| 实际判定 Verdict | `PASS` / `FAIL` | 断言与独立 Oracle 一致 / 不一致 | 有效 Run 的断言结果 |

## 1. 执行摘要与结论

- 报告范围（计划/方案版本）：
  - 方案：`llmtier-system-test-scheme`（`docs/70_verification/schemes/llmtier-system-test-scheme.md`，Case 清单 **163 条**：A 102 / B 61，设计数）。
  - 计划：`llmtier-system-test-plan`（`docs/70_verification/plans/llmtier-system-test-plan.md`，v0.1.0-draft.9，Template `tests.system-test-plan` v0.9.2）。
  - 机器契约：`interfaces/openapi/llmtier.openapi.json`（OpenAPI 3.1.0，`info.version=0.3-simplified-candidate.8`）。
- 执行范围：本 Run 执行系统层 A 类（`-m api_a`）、系统层 B 类（`-m api_b`）与单元层全量（`tests/unit/v03`）三批。
- 结果分布与总结论：
  - **A 类**（Run `2026-09-30/A-api-6`）：collected=105、`PASS=105`、`FAIL=0`、`BLOCKED=0`、`SKIP=0`、`INVALID=0`、`XPASS=0`、`NOT_RUN=0`；exit code=**0**。
  - **B 类**（Run `2026-09-30/B-api-5`）：collected=71、`PASS=71`、`FAIL=0`、`BLOCKED=0`、`SKIP=0`、`INVALID=0`、`XPASS=0`、`NOT_RUN=0`；exit code=**0**。
  - **单元层**（Run `run-20260930-05`）：`PASS=425`、`FAIL=0`、`BLOCKED=0`、`SKIP=0`、`INVALID=0`、`XPASS=0`、`NOT_RUN=0`；exit code=**0**（绿色）。
  - **汇总（按设计 Case ID 去重）**：方案 §3 设计 **163/163** 个 Case 全部有有效 Run、全部 **PASS**；`FAIL/BLOCKED/INVALID/NOT_RUN = 0`；`SKIP=0`（A 上限 ≤5、B 上限 ≤3 均满足）。
- Gate 达成情况：**按计划 §8 口径 = ACCEPT 建议（Gate 建议，非批准）**——全部适用 163 Case PASS，FAIL/BLOCKED/INVALID=0，SKIP 在上限内，无 MISSING（`NOT_RUN`=0），单元结果绿色。方案 §4 的裁决按本版审计重分类：**(a) COVERED 16 项**模块级 VRC 由真实单元行为测试覆盖；**(b) OUT-OF-SCOPE**（验收/生产环境/容量耐久/运维恢复等）不在 tests 家族，引用 `std-tailoring`/设计权威；**(c) REAL HOLE 1 项具名开放 RISK `RISK-UI-EXEC-1`**（M002 `VRC-UI-001..006`＋M005 视觉子项仅有字符串契约、无 JS 宿主，见 §6）。报告只给 Gate 建议，不等同验收或上线授权。

## 2. 被测基线与实际环境

- 实际基线（与计划对照）——**制品 pin（计划 §2/§7 `{git_commit, db_schema_version, openapi_version}`）**，取自各 Run 的 `test-run.env`：
  - `git_commit`：`b86be7ba4f4d2dee9ecd578a5a73745d71f4d3be`（三批一致；`test-run.env` 记录）。
  - `db_schema_version`：`2`（`src/util/store.py::EXPECTED_SCHEMA_VERSION=2`；`test-run.env` 记录 `schema_version=2`）。
  - `openapi_version`：`0.3-simplified-candidate.8`（`test-run.env` 记录）。
  - 与计划 §2 基线一致：m5air 生产部署 `192.168.1.9:8181`；Python `3.14.3 (arm64)`。
- 环境偏差及影响：
  - **无功能性偏差**。环境实测与计划 §6 一致：`/healthz`=`{"status":"ok","version":"0.3.0-dev"}`、`/readyz`=200 `status=ready` 7 个 fixed tier 全 `available`。
  - Go/No-Go 前检 `tools/check_env.py --class all` = **8/8 passed，exit 0**（A1–A6 六项 + B1–B2 两项）。
  - B 类夹具的假上游绑定 LAN IP（`192.168.1.8:<临时端口>`，TS-003），无 `pytest.skip`（`SKIP=0`），故不触发计划 §6-B 的“无 LAN IP 静默 skip”。
  - `case-status.json` 中 `schema_version: 1` 是**报告文件自身 schema 版本**（`tools/test_report.py` 产物格式版本），`schema_version_db: "2"` 才是被测 DB schema 版本；二者不同名同义，非偏差。
- 证据版本绑定与待重验：
  - 源码/契约/环境/checker 版本均绑定上述 pin；本报告结论仅对该 commit 有效，相关源码或契约修改后须重跑并标“待重验”。
  - 环境快照：`/healthz`、`/readyz` 于 Run 后复核（见上），m5air 3 providers / 4 deployments 保持基线。

## 3. 逐 Case 执行记录

本 Run 执行了系统层全部 163 个设计 Case（A 类 + B 类）与单元层全量。下表按方案 §3 家族汇总；每个家族内全部 Case 均为有效 Run 且 PASS。逐 Case 级证据见各 Run 的 `cases/<case-id>/manifest.json`。

| Case 家族 / 方案 Case ID | 执行状态 | Verdict | Run ID / 证据 | 缺陷 / 备注 |
|---|---|---|---|---|
| HEALTH-01..06 | 有效 Run | PASS | 2026-09-30/A-api-6（01/02）、B-api-5（03/04/05/06） | 6/6 PASS |
| DP-MODELS-01..07 | 有效 Run | PASS | 2026-09-30/A-api-6 | 7/7 PASS |
| DP-RESP-01..27 | 有效 Run | PASS | 2026-09-30/A-api-6 | 27/27 PASS |
| DP-EMB-01..10 | 有效 Run | PASS | 2026-09-30/A-api-6 | 10/10 PASS |
| DP-USAGE-01..09 | 有效 Run | PASS | 2026-09-30/A-api-6 | 9/9 PASS |
| ADM-PROV-01..17 | 有效 Run | PASS | 2026-09-30/A-api-6（01/03/04/14）、B-api-5（其余） | 17/17 PASS |
| ADM-PROV-MODELS-01/02 | 有效 Run | PASS | 2026-09-30/A-api-6 | 2/2 PASS |
| ADM-PROV-USAGE-01..04 | 有效 Run | PASS | 2026-09-30/A-api-6 | 4/4 PASS |
| ADM-DEPL-01..12 | 有效 Run | PASS | 2026-09-30/A-api-6（01/03）、B-api-5（其余） | 12/12 PASS |
| ADM-SL-01..11（含 02b/04b） | 有效 Run | PASS | 2026-09-30/A-api-6（01/03）、B-api-5（其余） | 13/13 PASS |
| ADM-PROBE-01..03 | 有效 Run | PASS | 2026-09-30/A-api-6 | 3/3 PASS |
| ADM-RUNTIME-01..03 | 有效 Run | PASS | 2026-09-30/A-api-6 | 3/3 PASS |
| ADM-STATS-01..04 | 有效 Run | PASS | 2026-09-30/A-api-6 | 4/4 PASS |
| ADM-AUDIT-01..04 | 有效 Run | PASS | 2026-09-30/A-api-6 | 4/4 PASS |
| ADM-LOGS-01..03 | 有效 Run | PASS | 2026-09-30/A-api-6 | 3/3 PASS |
| ADM-USAGE-01..03 | 有效 Run | PASS | 2026-09-30/A-api-6（01/02）、B-api-5（03） | 3/3 PASS |
| OBS-DIAG-01..03 | 有效 Run | PASS | 2026-09-30/A-api-6 | 3/3 PASS |
| OBS-SNAP-01..03 | 有效 Run | PASS | 2026-09-30/A-api-6 | 3/3 PASS |
| OBS-STATS-01..03 | 有效 Run | PASS | 2026-09-30/A-api-6 | 3/3 PASS |
| OBS-TRACE-01..03 | 有效 Run | PASS | 2026-09-30/A-api-6 | 3/3 PASS |
| OBS-DEPL-01..05 | 有效 Run | PASS | 2026-09-30/A-api-6 | 5/5 PASS |
| OBS-REQTRACE-01..03 | 有效 Run | PASS | 2026-09-30/A-api-6 | 3/3 PASS |
| OBS-ALIAS-01..06 | 有效 Run | PASS | 2026-09-30/A-api-6 | 6/6 PASS |
| AUTH-01..10 | 有效 Run | PASS | 2026-09-30/A-api-6 | 10/10 PASS |
| 单元层 `tests/unit/v03`（全量） | 有效 Run | PASS | run-20260930-05 | 425/425 PASS，非系统层 Case，佐证不阻断 |

> **Case ID 归一对齐（本 Run 修复）**：`test-report` 从测试源头部 `Case ID:` 提取 Case ID。`at_obs_01..04.py` / `at_adm_admin_usage_0{1,2,3}.py` 原头部写有历史别名（`OBS-01/02/03/04`、`ADM-ADMIN-USAGE-01/02/03`），与方案 §3 权威 ID（`HEALTH-01/02/03/04`、`ADM-USAGE-01/02/03`）不一致，导致前序 Run 的 `case-status.json` 出现 ID 漂移。本 Run 前已将上述 7 个文件头部改为权威 Case ID，Run 后按设计 ID 去重复算 **163/163 全部命中，无漂移、无别名残留**。该修复属测试报告缺陷（非产品缺陷）。

## 4. 偏差、无效执行与重跑

| 偏差 / 无效项 | 原因 | 影响 Case | 处置与重跑 Run |
|---|---|---|---|
| Case ID 漂移（历史别名） | 7 个 `at_*.py` 头部 `Case ID:` 使用旧别名（`OBS-01..04`、`ADM-ADMIN-USAGE-01..03`），与方案 §3 权威 ID 不符 | HEALTH-01..04、ADM-USAGE-01..03 | 已改 7 个文件头部为权威 ID；重跑生成 A-api-6 / B-api-5，复算 163/163 命中（见 §3 注） |
| 无无效执行（INVALID） | — | — | — |
| 无 SKIP / BLOCKED | B 类夹具 LAN IP 可用、假上游健康 | — | — |

- 重跑不覆盖历史：本日更早的 Run（`A-api`..`A-api-5`、`B-api`..`B-api-4`、`run-20260930-01..04`）全部保留，未删除；本报告只引用最终三批。

## 5. 覆盖复算（对照方案分母）

对照 `llmtier-system-test-scheme` §3 的每个来源 ID 与设计验证项（VRC）逐条复算。除 Verdict 外记录三列——结果已知性、副作用、清理状态。

| 方案来源 ID | 设计验证项 ID | Case ID | 报告状态 | 结果已知性 | 副作用 | 清理状态 | 剩余缺口 |
|---|---|---|---|---|---|---|---|
| §8 健康/就绪接口 | VRC-API-002、VRC-MGMT-003、VRC-UTIL-001 | HEALTH-01..06 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| §8 逻辑模型清单接口 | VRC-INF-001/002 | DP-MODELS-01..07 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| §8 Responses 接口 | VRC-INF-001/003/004、VRC-DIAG-004 | DP-RESP-01..27 | PASS | 可独立判定（事件序列/注入命中） | 只读 + 一次性状态写（注入已 teardown） | 已回基线 | — |
| §8 Embeddings 接口 | VRC-INF-001/002/004 | DP-EMB-01..10 | PASS | 可独立判定 | 只读 + 一次性写 | 已回基线 | — |
| §8 Usage 查询接口 | VRC-MGMT-006、VRC-INF-004 | DP-USAGE-01..09 | PASS | 可独立判定（崩溃恢复不变量） | 只读 + 账本写（已复位） | 已回基线 | — |
| §8 Provider CRUD 接口 | VRC-MGMT-001/002 | ADM-PROV-01..17 | PASS | 可独立判定 | 空库 CRUD 写（B 类临时实例） | 实例销毁 | — |
| §8 provider 上游模型目录接口 | VRC-MGMT-001 | ADM-PROV-MODELS-01/02 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| §8 provider usage 快照接口 | VRC-MGMT-006、VRC-DIAG-004 | ADM-PROV-USAGE-01..04 | PASS | 可独立判定 | 只读 + 一次性写 | 已回基线 | — |
| §8 Deployment CRUD 接口 | VRC-MGMT-001/002 | ADM-DEPL-01..12 | PASS | 可独立判定 | 空库 CRUD 写 | 实例销毁 | — |
| §8 Service Level CRUD 接口 | VRC-MGMT-002 | ADM-SL-01..11（含 02b/04b） | PASS | 可独立判定 | 空库 CRUD 写 | 实例销毁 | — |
| §8 探测接口 | VRC-DIAG-004 | ADM-PROBE-01..03 | PASS | 可独立判定 | 只读 + 一次性写 | 已回基线 | — |
| §8 运行态接口 | VRC-INF-004、VRC-API-002 | ADM-RUNTIME-01..03 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| §8 统计接口 | VRC-MGMT-006 | ADM-STATS-01..04 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| §8 审计接口 | VRC-MGMT-003/006 | ADM-AUDIT-01..04 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| §8 日志接口 | VRC-LOG-001 | ADM-LOGS-01..03 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| §8 管理 usage 接口 | VRC-MGMT-006 | ADM-USAGE-01..03 | PASS | 可独立判定 | 账本复位写（已 teardown） | 已回基线 | — |
| §8 诊断开关接口 | VRC-DIAG-001 | OBS-DIAG-01..03 | PASS | 可独立判定 | 开关一次性写 | 已回基线 | — |
| §8 诊断快照接口 | VRC-DIAG-002 | OBS-SNAP-01..03 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| §8 诊断统计接口 | VRC-DIAG-002 | OBS-STATS-01..03 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| §8 诊断 trace 接口 | VRC-DIAG-002 | OBS-TRACE-01..03 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| §8 注入配置接口 | VRC-DIAG-004 | OBS-DEPL-01..05 | PASS | 可独立判定 | 注入写（已清空 teardown） | 已回基线 | — |
| §8 请求追踪接口 | VRC-DIAG-002、VRC-API-002 | OBS-REQTRACE-01..03 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| §8 契约别名命名空间 | VRC-DIAG-001/002/004 | OBS-ALIAS-01..06 | PASS | 可独立判定 | 只读/一次性写 | 已回基线 | — |
| §8 认证与授权跨切面 | VRC-API-002、VRC-MGMT-003 | AUTH-01..10 | PASS | 可独立判定 | 只读 | 无需清理 | — |

**覆盖复算小结**：
- **设计数 vs 已跑数**：方案 §3 设计 **163**；本 Run 按设计 Case ID 去重命中 **163/163 已跑**（`NOT_RUN=0`）；**PASS 163/163**。原始 collect 计数 A=105 / B=71（同一 Case 的多臂/参数化条目在 `case-status.json` 中按 Case ID 收敛为 A 102 / B 62 条记录，去重后与设计 163 一一对应）。
- **逐来源 ID**：25 个来源 ID 组，每组 `已跑=设计`、`PASS=已跑`（例：Responses 27/27、Provider CRUD 17/17、Service Level 13/13、Auth 10/10）。
- **逐 VRC（本层 14 项有 Case 的）**：`VRC-INF-001` 31/31、`VRC-MGMT-006` 21/21、`VRC-MGMT-001` 22/22、`VRC-MGMT-002` 22/22、`VRC-API-002` 13/13、`VRC-DIAG-002` 15/15、`VRC-DIAG-004` 15/15、`VRC-MGMT-003` 9/9、`VRC-INF-002` 5/5、`VRC-INF-004` 7/7、`VRC-DIAG-001` 4/4、`VRC-LOG-001` 3/3、`VRC-UTIL-001` 2/2、`VRC-INF-003` 1/1 —— **全部已跑且 PASS，覆盖计数与方案 §3 声明完全一致**。
- **其余 19 个 VRC 按方案 §4 本版审计重分类**：`VRC-INF-005`、`VRC-UTIL-002`、`VRC-API-001/003/004`、`VRC-MGMT-004/005`、`VRC-DIAG-003`、`VRC-OBS-001..005`（行为级）= **(a) COVERED**，由**真实单元行为测试**（`test_*` 断言被测返回/落库）覆盖，见方案 §4 逐项证据；`VRC-UI-001..006`＋`VRC-OBS-*` 视觉子项 = **(c) REAL HOLE → 开放 RISK `RISK-UI-EXEC-1`**（字符串契约≠JS 执行验证，无宿主）。本 Run 系统层 `NOT_RUN=0`、无 MISSING；`RISK-UI-EXEC-1` 为**已登记的独立残留风险**（不阻断本层运行结论，但阻断 Web UI 行为级断言的可信度），见 §6。

## 6. 缺陷与残余风险

- 缺陷清单（关联 Case 与 Run）：
  - **测试报告缺陷（已修）**：7 个 `at_*.py` 的 `Case ID:` 头部使用历史别名，致 `case-status.json` ID 漂移（影响 HEALTH-01..04、ADM-USAGE-01..03 的归集）。已改头部为方案 §3 权威 ID 并重跑验证（§3 注 / §4）。**非产品缺陷**。
  - **产品缺陷**：本 Run **无 FAIL**，未发现产品缺陷。
- 残余风险：
  - **内容与容量不在本层**：不证明上游模型输出质量、不证明 FD 泄漏/30min 耐久/性能 SLO（方案 §1 已声明不证明；方案 §4 **(b) OUT-OF-SCOPE**，权威＝系统设计 §11.1「V0.3 不承诺未测量 SLO」＋`std-tailoring` `LT-TL-020`/`LT-TL-024`）。
  - **`RISK-UI-EXEC-1`（本版新增，开放）**：M002 `VRC-UI-001..006` 与 M005 诊断页视觉子项的**行为级从未被真实执行验证**——`UT-UI-001..010` 仅对 `app.js`/`index.html` 源码做字符串契约断言（`assertIn`），不执行 JS；本项目无浏览器/JS 宿主（零 node/jsdom/playwright/selenium），无法升级。**影响**：Web UI 行为回归（分支顺序、DOM 渲染、事件绑定）可在本报告 163/163 PASS 与单元 425/425 PASS 下漏检。**Owner**：M002（共同 M005）。**关闭条件**：引入浏览器/JS 宿主 → 将 `UT-UI-*` 升级为真实执行断言 → RISK 关闭。权威登记：scheme §4、unit scheme §4、plan §10-O6。
  - **真实 consumer 未联调**：Piko / Slinky 真实集成未验证；本层 PASS 只证明 LLMTier 自身运行行为。
  - **生产部署面未验证**：TLS/SSO/CSRF、`runtime_activation=true` 不在本层（方案 §4 Tailored-N/A，运维/验收承接）。

## 7. Gate 结论与建议

- Gate 结论（接受/条件接受/拒绝）：**ACCEPT 建议**（按计划 §8 口径给出，**非批准**）。
  - 适用 Case（方案 §3 全部 163，无裁剪）**全 PASS**：163/163。
  - `FAIL=0`、`BLOCKED=0`、`INVALID=0`。
  - `SKIP=0`，在计划 §8 上限内（A ≤5 / B ≤3）。
  - 无 P0 MISSING（`NOT_RUN=0`）；无具名缺口新增。
  - 覆盖复算：25 来源 ID 与 14 个本层 VRC 全部命中，计数与方案 §3 一致。
  - 单元层结果**绿色**（425/425 PASS），不阻断。
- 开放问题与责任方：
  - Piko / Slinky 真实 consumer 联调（consumer owner）——属验收/相邻方，不在本层分母。
  - 生产部署面（TLS/SSO/runtime activation）由运维/验收承接（`std-tailoring` `LT-TL-022`）。
  - 本报告不授权 release；`runtime_activation=true` 需独立决定。

## 8. 未决项

| 未决项 / 关联 | Owner / 最晚 Gate | 关闭所需事实或决定 |
|---|---|---|
| 真实 consumer（Piko / Slinky）联调 | consumer owner / 验收前 | 真实端到端联调结果 |
| 生产部署面（TLS/SSO/CSRF、runtime activation） | 运维/安全 / 验收 Gate | 按 `std-tailoring` `LT-TL-022` 由验收活动承接 |
| 容量/耐久（FD/30min/SLO） | 性能/运维 / 另立专项 | 方案 §4 Tailored-N/A，需独立专项 |

<!-- 交付自查：任一 Verdict 能否定位唯一 Run 与原始证据；失败与 NOT_RUN 是否如实保留；报告是否越权写成批准。 -->
