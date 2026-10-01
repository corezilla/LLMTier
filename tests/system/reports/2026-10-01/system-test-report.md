<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 System Test Report — Run 2026-10-01

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-system-test-report-2026-10-01` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-10-01` |
| Last Modified Date | `2026-10-01` |
| Template ID | `tests.system-test-report` |
| Template Version | `0.3.1` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `tests/system/reports/2026-10-01/system-test-report.md` |
| Supersedes | `llmtier-system-test-report-2026-09-30` |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本报告由本轮 Run 目录的机器产物整理而成——系统层 A 类 `tests/system/reports/2026-10-01/A-api/`、
> 系统层 B 类 `tests/system/reports/2026-10-01/B-api/`、真实浏览器 UI Run `tests/ui/reports/2026-10-01/UI-1/`。
> 只使用各 Run 的 `junit.xml` / `test-run.env` / `case-status.json` / 逐 Case `manifest.json` 记录的事实，
> 未运行/未实现项一律保留 `NOT_RUN`，不补造结果。更早的 `tests/system/reports/2026-09-30/*` 是本报告
> 之前的正式记录，按“重跑不覆盖历史”原则原样保留。

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
  - 方案：`llmtier-system-test-scheme`（`docs/70_verification/system/llmtier-system-test-scheme.md`，v0.1.0-draft.12，Template `tests.system-test-scheme` v0.6.1，`template_sha256=dbd507e4…`），Case 清单 **175 条（设计数）**：A 102 / B 63 / UI 10（方案 §2 口径）。
  - 计划：`llmtier-system-test-plan`（`docs/70_verification/system/llmtier-system-test-plan.md`，v0.1.0-draft.10，Template `tests.system-test-plan` v0.9.2）。
  - 机器契约：`interfaces/openapi/llmtier.openapi.json`（`info.version=0.3-simplified-candidate.8`）。
- 执行范围：本 Run 执行系统层 A 类（`-m api_a`）、系统层 B 类（`-m api_b`）与真实浏览器 UI 类（`-m ui`）三批。
- 结果分布与总结论：
  - **A 类**（Run `2026-10-01/A-api`）：collected=105、`PASS=105`、`FAIL=0`、`BLOCKED=0`、`SKIP=0`、`INVALID=0`、`XPASS=0`、`NOT_RUN=0`；exit code=**0**；`case-status.json` 收敛为 102 个设计 Case ID（`ST-EMB-007` 含 4 条参数化 arm）。
  - **B 类**（Run `2026-10-01/B-api`）：collected=76、`PASS=76`、`FAIL=0`、`BLOCKED=0`、`SKIP=0`、`INVALID=0`、`XPASS=0`、`NOT_RUN=0`；exit code=**0**；收敛为 64 个 Case ID（`ST-AUSAGE-003`/`ST-SCAN-001` 等参数化）。
  - **UI 类**（Run `2026-10-01/UI-1`，真实浏览器 headless Chrome over CDP）：`PASS=10`、`FAIL=0`、`BLOCKED=0`、`SKIP=0`、`INVALID=0`、`XPASS=0`、`NOT_RUN=0`；exit code=**0**。
  - **汇总（按设计 Case ID 去重）**：方案 §3 设计 **175/175** 个 Case 全部有有效 Run、全部 **PASS**；`FAIL/BLOCKED/INVALID/NOT_RUN = 0`；`SKIP=0`（A 上限 ≤5、B 上限 ≤3 均满足）。A∪B 去重 = 165（`ST-RESP-004` 同时由 A、B 两类执行），＋ UI 10 = **175**。
- Gate 达成情况：**按计划 §8 口径 = ACCEPT 建议（Gate 建议，非批准）**——全部适用 175 Case（A/B 165 + UI 10）PASS，FAIL/BLOCKED/INVALID=0，SKIP 在上限内，无 MISSING（`NOT_RUN`=0）。方案 §4 的裁决按本版审计重分类：**(a) COVERED** 模块级 VRC 由真实单元行为测试覆盖；**(b) OUT-OF-SCOPE**（验收/生产环境/容量耐久/运维恢复等）不在 tests 家族，引用 `std-tailoring`/设计权威；**(c) REAL HOLE 归零**——唯一具名开放 RISK **`RISK-UI-EXEC-1` 已关闭**（真实浏览器 Run `2026-10-01/UI-1` 执行 `VRC-UI-001..006`＋M005 诊断页视觉子项，见 §3/§5/§6）。报告只给 Gate 建议，不等同验收或上线授权。

## 2. 被测基线与实际环境

- 实际基线（与计划对照）——**制品 pin（计划 §2/§7 `{git_commit, db_schema_version, openapi_version}`）**，取自各 Run 的 `test-run.env`：
  - `git_commit`：`36825b932ec0ecc0757fdde4628973572261a7c8`（三批一致；`test-run.env` 记录）。该 commit 即 `refactor(tests): migrate/retire legacy tests/system/st_*.py to Case-ID naming`，本轮所有 Case ID 均为迁移后的 `ST-*`。
  - `db_schema_version`：`2`（`src/util/store.py::EXPECTED_SCHEMA_VERSION=2`；`test-run.env` 记录 `schema_version=2`）。
  - `openapi_version`：`0.3-simplified-candidate.8`（`test-run.env` 记录）。
  - 与计划 §2 基线一致：m5air 生产部署 `192.168.1.9:8181`；Python `3.14.3 (arm64)`。
- 环境偏差及影响：
  - **无功能性偏差**。Go/No-Go 前检 `tools/check_env.py --class all` = **8/8 passed，exit 0**（A1–A6 六项 + B1–B2 两项）：A1 `/healthz` 200 `version=0.3.0-dev`；A2 `/readyz` 200 全 7 fixed tier；A3/A4 两侧 OMLX `9000` 健康；A5 `provider_omlx_m5mac` `has_secret=true`；A6 3 providers / 4 deployments 已注册；B1 临时实例 `/healthz` 200；B2 假上游绑 LAN IP `192.168.1.8` 可探活（TS-003）。
  - B 类夹具的假上游绑定 LAN IP（`192.168.1.8:<临时端口>`，TS-003），无 `pytest.skip`（`SKIP=0`），故不触发计划 §6-B 的“无 LAN IP 静默 skip”。
  - `case-status.json` 中 `schema_version: 1` 是**报告文件自身 schema 版本**（`tools/test_report.py` 产物格式版本），`schema_version_db: "2"` 才是被测 DB schema 版本；二者不同名同义，非偏差。
- 证据版本绑定与待重验：
  - 源码/契约/环境/checker 版本均绑定上述 pin；本报告结论仅对该 commit 有效，相关源码或契约修改后须重跑并标“待重验”。
  - 环境快照：`/healthz`、`/readyz` 于 Run 后复核（见上），m5air 3 providers / 4 deployments 保持基线。

## 3. 逐 Case 执行记录

本 Run 执行了系统层全部 175 个设计 Case（A 类 + B 类 + 真实浏览器 UI 类）。下表按方案 §3 家族汇总；每个家族内全部 Case 均为有效 Run 且 PASS。逐 Case 级证据见各 Run 的 `cases/<case-id>/manifest.json`。

| Case 家族 / 方案 Case ID | 执行状态 | Verdict | Run ID / 证据 | 缺陷 / 备注 |
|---|---|---|---|---|
| ST-HEALTH-001..06 | 有效 Run | PASS | 2026-10-01/A-api（01/02）、B-api（03/04/05/06） | 6/6 PASS |
| ST-MODEL-001..07 | 有效 Run | PASS | 2026-10-01/A-api | 7/7 PASS |
| ST-RESP-001..27 | 有效 Run | PASS | 2026-10-01/A-api、B-api（004/011/016/018/019..027） | 27/27 PASS；`ST-RESP-004` A/B 双臂 |
| ST-RATELIMIT-001 | 有效 Run | PASS | 2026-10-01/B-api | 1/1 PASS（legacy `st_22` 迁入） |
| ST-SCAN-001 | 有效 Run | PASS | 2026-10-01/B-api | 1/1 PASS（legacy `st_04` 迁入，4 arm） |
| ST-EMB-001..10 | 有效 Run | PASS | 2026-10-01/A-api、B-api（008/009/010） | 10/10 PASS |
| ST-USAGE-001..09 | 有效 Run | PASS | 2026-10-01/A-api（001..007）、B-api（008/009） | 9/9 PASS |
| ST-PROV-001..17 | 有效 Run | PASS | 2026-10-01/A-api（001/003/004/014）、B-api（其余） | 17/17 PASS |
| ST-PMOD-001/02 | 有效 Run | PASS | 2026-10-01/A-api | 2/2 PASS |
| ST-PUSAGE-001..04 | 有效 Run | PASS | 2026-10-01/A-api | 4/4 PASS |
| ST-DEPL-001..12 | 有效 Run | PASS | 2026-10-01/A-api（001/003）、B-api（其余） | 12/12 PASS |
| ST-SL-001..13（含 012/013） | 有效 Run | PASS | 2026-10-01/A-api（001/003）、B-api（其余） | 13/13 PASS |
| ST-PROBE-001..03 | 有效 Run | PASS | 2026-10-01/A-api（001/002）、B-api（003） | 3/3 PASS |
| ST-RUNTIME-001..03 | 有效 Run | PASS | 2026-10-01/A-api | 3/3 PASS |
| ST-STATS-001..04 | 有效 Run | PASS | 2026-10-01/A-api | 4/4 PASS |
| ST-AUDIT-001..04 | 有效 Run | PASS | 2026-10-01/A-api | 4/4 PASS |
| ST-LOGS-001..03 | 有效 Run | PASS | 2026-10-01/A-api | 3/3 PASS |
| ST-AUSAGE-001..03 | 有效 Run | PASS | 2026-10-01/A-api（001/002）、B-api（003） | 3/3 PASS |
| ST-OBSDIAG-001..03 | 有效 Run | PASS | 2026-10-01/A-api（001）、B-api（002/003） | 3/3 PASS |
| ST-OBSSNAP-001..03 | 有效 Run | PASS | 2026-10-01/A-api（001）、B-api（002/003） | 3/3 PASS |
| ST-OBSSTATS-001..03 | 有效 Run | PASS | 2026-10-01/A-api（001/002）、B-api（003） | 3/3 PASS |
| ST-OBSTRACE-001..03 | 有效 Run | PASS | 2026-10-01/A-api（001）、B-api（002/003） | 3/3 PASS |
| ST-OBSDEPL-001..05 | 有效 Run | PASS | 2026-10-01/A-api（001）、B-api（002..005） | 5/5 PASS |
| ST-OBSREQTRACE-001..03 | 有效 Run | PASS | 2026-10-01/A-api | 3/3 PASS |
| ST-OBSALIAS-001..06 | 有效 Run | PASS | 2026-10-01/A-api（001/002/003/005/006）、B-api（004） | 6/6 PASS |
| ST-AUTH-001..10 | 有效 Run | PASS | 2026-10-01/A-api（除 007）、B-api（007） | 10/10 PASS |
| ST-UI-001..010（真实浏览器 UI） | 有效 Run | PASS | 2026-10-01/UI-1 | 10/10 PASS（headless Chrome over CDP；每 Case PNG 截图 + 网络日志） |

> **计数核对**：A 类 `junit.xml tests=105` 对应 102 个设计 Case ID；B 类 `tests=76` 对应 64 个设计 Case ID。参数化/双臂条目在 `case-status.json` 中按 Case ID 收敛；A∪B 去重 165 与方案 §3 非 UI 设计数一致；＋UI 10 = 175/175。

## 4. 偏差、无效执行与重跑

| 偏差 / 无效项 | 原因 | 影响 Case | 处置与重跑 Run |
|---|---|---|---|
| A 类 collected 105 vs 设计 ID 102 | 参数化（`ST-EMB-007` 4 arm）在 JUnit 计 105 条、按 Case ID 收敛为 102 | ST-EMB-007 | 非偏差：`case-status.json` 按 Case ID 归集，102/102 PASS |
| B 类 collected 76 vs 设计 ID 64 | 参数化（`ST-AUSAGE-003` 6、`ST-SCAN-001` 4、`ST-RESP-016/018/027`、`ST-USAGE-009` 各 2） | 上述 5 家族 | 非偏差：按 Case ID 收敛为 64/64 PASS |
| `ST-RESP-004` 同时被 A、B 两类收集 | 该 Case 的 marker/适用环境跨 A、B | ST-RESP-004 | 非偏差：A∪B 去重后仍为 165，两类均 PASS |
| 无无效执行（INVALID） | — | — | — |
| 无 SKIP / BLOCKED | B 类夹具 LAN IP 可用、假上游健康；UI 浏览器与 node ≥ 22 可用 | — | — |

- 重跑不覆盖历史：本日更早的 Run（`tests/system/reports/2026-09-30/A-api…A-api-6`、`B-api…B-api-5`、`tests/unit/reports/run-20260930-01…05`、`run-20261001-01…02`）全部保留，未删除；`2026-09-30/system-test-report.md` 与其 metadata 亦原样保留为历史记录。本报告只引用本轮三批 Run。

## 5. 覆盖复算（对照方案分母）

对照 `llmtier-system-test-scheme` §3 的每个来源 ID 与设计验证项（VRC）逐条复算；下表按来源归并展示（10 个 `ST-UI-*` 行并入同源一行，方案 §3 的 35 个来源串此处收敛为 26 行）。除 Verdict 外记录三列——结果已知性、副作用、清理状态。

| 方案来源 ID | 设计验证项 ID | Case ID | 报告状态 | 结果已知性 | 副作用 | 清理状态 | 剩余缺口 |
|---|---|---|---|---|---|---|---|
| §8 健康/就绪接口 | VRC-API-002、VRC-MGMT-003、VRC-UTIL-001 | ST-HEALTH-001..06 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| §8 逻辑模型清单接口 | VRC-INF-001/002 | ST-MODEL-001..07 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| §8 Responses 接口 | VRC-INF-001/003/004、VRC-DIAG-004 | ST-RESP-001..27 | PASS | 可独立判定（事件序列/注入命中） | 只读 + 一次性状态写（注入已 teardown） | 已回基线 | — |
| §8 接口面（absence 静态契约） | —（见 §4 裁决） | ST-SCAN-001 | PASS | 可独立判定（OpenAPI/清单/活体头 absence 扫描） | 只读 | 无需清理 | — |
| §8 Embeddings 接口 | VRC-INF-001/002/004 | ST-EMB-001..10 | PASS | 可独立判定 | 只读 + 一次性写 | 已回基线 | — |
| §8 Usage 查询接口 | VRC-MGMT-006、VRC-INF-004 | ST-USAGE-001..09 | PASS | 可独立判定（崩溃恢复不变量） | 只读 + 账本写（已复位） | 已回基线 | — |
| §8 Provider CRUD 接口 | VRC-MGMT-001/002 | ST-PROV-001..17 | PASS | 可独立判定 | 空库 CRUD 写（B 类临时实例） | 实例销毁 | — |
| §8 provider 上游模型目录接口 | VRC-MGMT-001 | ST-PMOD-001/02 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| §8 provider usage 快照接口 | VRC-MGMT-006、VRC-DIAG-004 | ST-PUSAGE-001..04 | PASS | 可独立判定 | 只读 + 一次性写 | 已回基线 | — |
| §8 Deployment CRUD 接口 | VRC-MGMT-001/002 | ST-DEPL-001..12 | PASS | 可独立判定 | 空库 CRUD 写 | 实例销毁 | — |
| §8 Service Level CRUD 接口 | VRC-MGMT-002 | ST-SL-001..13 | PASS | 可独立判定 | 空库 CRUD 写 | 实例销毁 | — |
| §8 探测接口 | VRC-DIAG-004 | ST-PROBE-001..03 | PASS | 可独立判定 | 只读 + 一次性写 | 已回基线 | — |
| §8 运行态接口 | VRC-INF-004、VRC-API-002 | ST-RUNTIME-001..03 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| §8 统计接口 | VRC-MGMT-006 | ST-STATS-001..04 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| §8 审计接口 | VRC-MGMT-003/006 | ST-AUDIT-001..04 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| §8 日志接口 | VRC-LOG-001 | ST-LOGS-001..03 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| §8 管理 usage 接口 | VRC-MGMT-006 | ST-AUSAGE-001..03 | PASS | 可独立判定 | 账本复位写（已 teardown） | 已回基线 | — |
| §8 诊断开关接口 | VRC-DIAG-001 | ST-OBSDIAG-001..03 | PASS | 可独立判定 | 开关一次性写 | 已回基线 | — |
| §8 诊断快照接口 | VRC-DIAG-002 | ST-OBSSNAP-001..03 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| §8 诊断统计接口 | VRC-DIAG-002 | ST-OBSSTATS-001..03 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| §8 诊断 trace 接口 | VRC-DIAG-002 | ST-OBSTRACE-001..03 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| §8 注入配置接口 | VRC-DIAG-004 | ST-OBSDEPL-001..05 | PASS | 可独立判定 | 注入写（已清空 teardown） | 已回基线 | — |
| §8 请求追踪接口 | VRC-DIAG-002、VRC-API-002 | ST-OBSREQTRACE-001..03 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| §8 契约别名命名空间 | VRC-DIAG-001/002/004 | ST-OBSALIAS-001..06 | PASS | 可独立判定 | 只读/一次性写 | 已回基线 | — |
| §8 认证与授权跨切面 | VRC-API-002、VRC-MGMT-003 | ST-AUTH-001..10 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| 模块设计 web-ui §14（同源 `/ui/`，真实浏览器） | VRC-UI-001..006、VRC-OBS-* 视觉子项 | ST-UI-001..010 | PASS | 可独立判定（真实 DOM + CDP 网络） | 只读（UI-003 用例内 Resume 回初态） | 实例销毁，已回基线 | — |

**覆盖复算小结**：

- **设计数 vs 已跑数**：方案 §3 设计 **175（A 102 / B 63 / UI 10 口径；实际 runner collect：`-m api_a`=105、`-m api_b`=76、`-m ui`=10，按 Case ID 去重为 A 102 / B 64 / UI 10，A∪B=165）**；本 Run 按设计 Case ID 去重命中 **175/175 已跑**（`NOT_RUN=0`）；**PASS 175/175**（A/B 165 + UI 10）。
- **逐来源 ID**：**35 个来源 ID 组**（§5 表按来源归并；含 `ST-SCAN-001` 的 absence 组与 `ST-USAGE-009` 的机制计量组，UI 家族按各 `RULE-UI-*`/`esc()` 契约分列），每组 `已跑=设计`、`PASS=已跑`（例：Responses 28、Provider CRUD 17、Service Level 13、Auth 10、Embeddings 10、Health 6）。
- **逐 VRC（本层 20 项有 Case 的）**：`VRC-INF-001` 31/31、`VRC-MGMT-006` 21/21、`VRC-MGMT-001` 22/22、`VRC-MGMT-002` 22/22、`VRC-API-002` 13/13、`VRC-DIAG-002` 15/15、`VRC-DIAG-004` 15/15、`VRC-MGMT-003` 9/9、`VRC-INF-004` **8/8**、`VRC-INF-002` 5/5、`VRC-DIAG-001` 4/4、**`VRC-UI-001` 4/4、`VRC-UI-002` 1/1、`VRC-UI-003` 1/1、`VRC-UI-004` 1/1、`VRC-UI-005` 2/2、`VRC-UI-006` 1/1**、`VRC-LOG-001` 3/3、`VRC-UTIL-001` 2/2、`VRC-INF-003` 1/1 —— **全部已跑且 PASS**。
  - **口径说明（`VRC-INF-004`、`VRC-UI-001`）**：方案 §3 对 `VRC-INF-004` 的散文声明为 7，但迁移后实际清单行为 **8**（`ST-RATELIMIT-001` 自 legacy `st_22` 迁入并声明 `VRC-INF-004`）；`VRC-UI-001` 散文声明为 4，与清单一致（`ST-UI-001/002/008/010`）。本表以**清单行**为准，逐条复核见上表。
- **其余 VRC 按方案 §4 本版审计重分类**：`VRC-INF-005`、`VRC-UTIL-002`、`VRC-API-001/003/004`、`VRC-MGMT-004/005`、`VRC-DIAG-003`、`VRC-OBS-001..005`（行为级）= **(a) COVERED**，由**真实单元行为测试**（`test_*` 断言被测返回/落库）覆盖，见方案 §4 逐项证据。
- **`VRC-UI-001..006`＋`VRC-OBS-*` 视觉子项 = 已由真实浏览器 Run `2026-10-01/UI-1` 执行（PASS 10/10）**：`ST-UI-001`(`VRC-UI-001`)、`ST-UI-002`(`VRC-UI-001`)、`ST-UI-003`(`VRC-UI-003`)、`ST-UI-004`(`VRC-UI-004`)、`ST-UI-005`(`VRC-UI-005`)、`ST-UI-006`(`VRC-UI-006`)、`ST-UI-007`(`VRC-UI-002`)、`ST-UI-008`(`VRC-UI-001`)、`ST-UI-009`(`VRC-UI-005`)、`ST-UI-010`(`VRC-UI-001`)，诊断页视觉子项并入 `ST-UI-006`。原 `RISK-UI-EXEC-1` **已关闭**（见 §6）。本 Run 系统层 `NOT_RUN=0`、无 MISSING、无开放 RISK。

## 6. 缺陷与残余风险

- 缺陷清单（关联 Case 与 Run）：
  - **产品缺陷**：本 Run **无 FAIL**，未发现产品缺陷。
  - **测试/文档缺陷**：legacy `tests/system/st_*.py` 家族的 Case-ID 迁移（`ST-SCAN-001`/`ST-RATELIMIT-001` 迁入，其余 9 个按方案 §4 覆盖性退役）在本轮 commit `36825b9` 完成；本 Run 的 `case-status.json` 中无历史别名残留，175/175 全部命中权威 `ST-*` ID。
- 残余风险：
  - **内容与容量不在本层**：不证明上游模型输出质量、不证明 FD 泄漏/30min 耐久/性能 SLO（方案 §1 已声明不证明；方案 §4 **(b) OUT-OF-SCOPE**，权威＝系统设计 §11.1「V0.3 不承诺未测量 SLO」＋`std-tailoring` `LT-TL-020`/`LT-TL-024`）。
  - **`RISK-UI-EXEC-1`（原开放 —— 已关闭）**：M002 `VRC-UI-001..006` 与 M005 诊断页视觉子项的行为级原仅由 `UT-UI-001..010` 的源码字符串契约断言覆盖，不执行 JS，行为回归可在系统 PASS 下漏检。**关闭事实**：引入真实浏览器 harness（headless Chrome over CDP，`tests/common/drivers/browser_driver.mjs`，node ≥ 22 内置 WebSocket，无 npm/下载依赖）＋系统层 `ST-UI-001..010`；本报告 Run `2026-10-01/UI-1` 在真实 DOM 与 CDP 网络记录上执行并通过（10/10 PASS）；每 Case 产出 PNG 截图 + 网络日志证据（`tests/system/artifacts/ST-UI-*/`）。`UT-UI-*` 字符串契约保留为快速下位防线。**Owner**：M002（共同 M005）。权威登记：scheme §4、unit scheme §4、plan §10-O6（均已更新为 Closed）。**重评触发**：新增/修改任一 UI 行为分支时须同步 `ST-UI-*`。
  - **真实 consumer 未联调**：Piko / Slinky 真实集成未验证；本层 PASS 只证明 LLMTier 自身运行行为。
  - **生产部署面未验证**：TLS/SSO/CSRF、`runtime_activation=true` 不在本层（方案 §4 Tailored-N/A，运维/验收承接）。

## 7. Gate 结论与建议

- Gate 结论（接受/条件接受/拒绝）：**ACCEPT 建议**（按计划 §8 口径给出，**非批准**）。
  - 适用 Case（方案 §3 全部 175，无裁剪）**全 PASS**：175/175（A/B 165 + UI 10）。
  - `FAIL=0`、`BLOCKED=0`、`INVALID=0`。
  - `SKIP=0`，在计划 §8 上限内（A ≤5 / B ≤3）。
  - 无 P0 MISSING（`NOT_RUN=0`）；无具名缺口新增（方案 §4 具名缺口已按裁决关闭/分类）。
  - 覆盖复算：35 个来源 ID 组与 20 个本层 VRC（含 `VRC-UI-001..006`）全部命中，计数与方案 §3 清单一致（`VRC-INF-004` 以清单行 8 为准）。
  - 真实浏览器 UI Run `2026-10-01/UI-1` 绿色（ST-UI-001..010，10/10 PASS），`RISK-UI-EXEC-1` 关闭。
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
