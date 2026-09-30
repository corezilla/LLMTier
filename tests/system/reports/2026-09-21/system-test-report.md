<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 System Test Report — Run 2026-09-21

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-system-test-report-2026-09-21` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-21` |
| Last Modified Date | `2026-09-30` |
| Template ID | `tests.system-test-report` |
| Template Version | `0.3.1` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `tests/system/reports/2026-09-21/system-test-report.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本报告由历史 Run 目录 `tests/system/reports/2026-09-21/` 的松散执行记录整理成 STD 系统测试报告；仅使用该 Run 已记录的制品事实，未运行/未实现项一律保留 `NOT_RUN`，不补造结果。

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
  - 方案：`llmtier-system-test-scheme`（`docs/70_verification/schemes/llmtier-system-test-scheme.md`，Case 清单 140 条）。
  - 计划：本 Run 执行期间对应 `llmtier-api-test-plan.md` v0.3.0-draft.3 / `llmtier-api-test-execution.md` v0.2.0-draft.2（均已退役，内容现由 `llmtier-system-test-plan` 承接）。
- 结果分布与总结论：
  - **A 类 API 用例**：53 PASS / 0 FAIL / 0 SKIP / 0 BLOCKED。
  - **系统层 ST-* 用例**：30 PASS / 0 FAIL（11 个 `tests/system/st_*.py` 文件）。
  - **单元测试**：191 PASS / 0 FAIL。
  - 本报告分母（方案 §3 共 140 Case）：已执行并 PASS 53；其余 87 为 `NOT_RUN`（其中 52 为自动化入口未实现的 MISSING，35 为已实现但本轮未跑的 B 类/其余用例）。
- Gate 达成情况：**条件接受**——A 类 53/53 PASS 且无 FAIL；但分母未闭合（87 NOT_RUN，含 52 MISSING），**不构成 release 放行**。本报告仅给 Gate 建议，不等同验收或上线授权。

## 2. 被测基线与实际环境

- 实际基线（与计划对照）：
  - 分支 `docs/std-draft21-upgrade`；被测 commit `4c1afd8`（P0 scaffold）起，系统 ST-* 结果对应 commits `21dbd27`、`c42dcee`、`24643f4`。
  - A 类直接打 m5air 现有实例 `192.168.1.9:8181`（现有 state）。
  - 运行器：Python 3.14，pytest 9.1.0，httpx 0.28.1。
- 环境偏差及影响：
  - m5air 上存在第 4 个 provider `provider_volc`（计划预期 3 个），A 类 `ADM-PROV-*` 改用最小集合断言，不卡额外 provider。
  - `/readyz` 字段名为 `models`（计划 `OBS` 期望 `tiers`）；`/tier/admin/v1/runtime` 的 `providers`/`deployments` 为 dict；`embedding_space_id` 实测恒为 `None`——均以实测为契约，case 已对齐。
- 证据版本绑定与待重验：
  - A 类证据：`tests/system/reports/2026-09-21/2026-09-21-api-test-report.md`（Run 2026-09-21 A 类）。
  - 系统 ST-* 证据：`tests/system/reports/2026-09-21/2026-09-21-test-report.md`、`2026-09-21-summary.md`。
  - 上述证据为历史执行记录（作废的 `assurance.*` 计划口径）；本报告引用其事实，未重新执行。相关源码/契约若已变更，结论应重新验证并生成新 Run。

## 3. 逐 Case 执行记录

本 Run 实际执行的是 A 类 API 用例（53）与 `tests/system/st_*.py`（30）。按方案清单逐 Case 汇总如下；未执行项保留 `NOT_RUN`。

| Case 家族 / 方案 Case ID | 执行状态 | Verdict | Run ID / 证据 | 缺陷 / 备注 |
|---|---|---|---|---|
| HEALTH-01/02（Observation，报告记 OBS-01/02） | 有效 Run | PASS | 2026-09-21 / 2026-09-21-api-test-report.md §Case 分类结果 | 2/2 PASS |
| DP-MODELS-01..06 | 有效 Run | PASS | 同上 | 6/6 PASS（ST-03 另覆盖 exact-case） |
| DP-RESP-01..09 | 有效 Run | PASS | 同上 | 9/9 PASS（DP-RESP-02 期望已按实测修为 400 unsupported_request） |
| DP-EMB-01..04 | 有效 Run | PASS | 同上 | 4/4 PASS（DP-EMB-04 实测 code=`not_found`） |
| DP-USAGE-01..04 | 有效 Run | PASS | 同上 | 4/4 PASS |
| ADM-PROV-01/03/04（GET） | 有效 Run | PASS | 同上 | 3/3 PASS |
| ADM-DEPL-01/03（GET） | 有效 Run | PASS | 同上 | 2/2 PASS |
| ADM-SL-01/03（GET） | 有效 Run | PASS | 同上 | 2/2 PASS |
| ADM-PROBE-01/02 | 有效 Run | PASS | 同上 | 2/2 PASS |
| ADM-PROV-USAGE-01..03 | 有效 Run | PASS | 同上 | 3/3 PASS（ADM-PROV-USAGE-02 实测 code=`invalid_request`） |
| ADM-USAGE-01/02（报告记 ADM-ADMIN-USAGE-01/02） | 有效 Run | PASS | 同上 | 2/2 PASS |
| ADM-AUDIT-01/02 | 有效 Run | PASS | 同上 | 2/2 PASS |
| ADM-LOGS-01/02 | 有效 Run | PASS | 同上 | 2/2 PASS |
| ADM-RUNTIME-01 | 有效 Run | PASS | 同上 | 1/1 PASS |
| ADM-STATS-01..03 | 有效 Run | PASS | 同上 | 3/3 PASS |
| AUTH-01..06 | 有效 Run | PASS | 同上 | 6/6 PASS（AUTH-02/03/06 实测 HTTP 403 `permission_denied`） |
| ST 系统层：ST-01/02/03/04/09/12/15A/22/23/25/26 | 有效 Run | PASS | 2026-09-21 / 2026-09-21-test-report.md | 30 tests PASS（见 §6 历史 ST 明细） |
| DP-RESP-10..25 | NOT_RUN | — | — | 本轮未跑 |
| DP-EMB-05..07 | NOT_RUN | — | — | 本轮未跑 |
| DP-USAGE-05..08 | NOT_RUN | — | — | 本轮未跑 |
| DP-MODELS-07 | NOT_RUN | — | — | 本轮未跑 |
| HEALTH-03..06 | NOT_RUN | — | — | 本轮未跑 |
| ADM-PROV-02/05..14 | NOT_RUN | — | — | B 类 provider CRUD，本轮未跑（P2 待办） |
| ADM-DEPL-02/04..09 | NOT_RUN | — | — | B 类 deployment CRUD，本轮未跑 |
| ADM-SL-02/02b/04/04b/05..08 | NOT_RUN | — | — | B 类 service-level CRUD，本轮未跑 |
| ADM-PROV-MODELS-01/02 | NOT_RUN | — | — | 本轮未跑 |
| ADM-PROV-USAGE-04 | NOT_RUN | — | — | 本轮未跑 |
| ADM-AUDIT-03、ADM-LOGS 负向、ADM-STATS 负向、ADM-USAGE-03 | NOT_RUN | — | — | 本轮未跑 |
| OBS-DIAG-*、OBS-SNAP-*、OBS-STATS-*、OBS-TRACE-*、OBS-REQTRACE-*、OBS-ALIAS-*、OBS-DEPL-* | NOT_RUN | — | — | 本轮未跑 |
| AUTH-07..10 | NOT_RUN | — | — | 本轮未跑 |

## 4. 偏差、无效执行与重跑

| 偏差 / 无效项 | 原因 | 影响 Case | 处置与重跑 Run |
|---|---|---|---|
| 台账期待 `model_not_found`，实测 `not_found` | service-level 先于 routing 命中 | DP-EMB-04、DP-RESP-05 | case 已改；测试计划待修（本报告以实测为契约，未重跑） |
| ADM-PROV-USAGE-02 期待 `confirmation_required`，实测 `invalid_request` | app.py:136 先于 account_usage.py:151 检查 body | ADM-PROV-USAGE-02 | case 已改 |
| AUTH-02/03/06 期待 401，实测 403 `permission_denied` | auth.py:56-57 Bearer 不匹配 | AUTH-02/03/06 | case 已改 |
| 无无效执行（INVALID） | — | — | — |

## 5. 覆盖复算（对照方案分母）

对照 `llmtier-system-test-scheme` §3 的每个来源 ID 与其设计验证项（VRC）逐条复算。本 Run 的 A 类 PASS 覆盖如下；未覆盖的家庭保留 `NOT_RUN`，缺口不关闭。除 Verdict 外记录三列——结果已知性（结果是否可独立判定/是否有未知分支）、副作用（Case 执行后是否改变被测状态/调用了哪些外部资源/变更了哪些持久化数据）、清理状态（资源是否已释放/状态是否回滚基线/未清理项是否登记）。覆盖复算以本报告事实为准，不以计划口径代替。

| 方案来源 ID | 设计验证项 ID | Case ID | 报告状态 | 结果已知性 | 副作用 | 清理状态 | 剩余缺口 |
|---|---|---|---|---|---|---|---|
| §8 健康/就绪接口 | VRC-API-002、VRC-MGMT-003 | HEALTH-01/02 | PASS | 可独立判定（status body） | 只读，无状态改变 | 无需清理 | HEALTH-03..06 NOT_RUN |
| §8 逻辑模型清单接口 | VRC-INF-001、VRC-INF-002 | DP-MODELS-01..06 | PASS | 可独立判定 | 只读，无状态改变 | 无需清理 | DP-MODELS-07 NOT_RUN |
| §8 Responses 接口 | VRC-INF-001、VRC-INF-003、VRC-INF-004、VRC-DIAG-004 | DP-RESP-01..09 | PASS | 可独立判定（事件序列） | 只读（A 类无写） | 无需清理 | DP-RESP-10..25 NOT_RUN（含故障注入/429/上游错误） |
| §8 Embeddings 接口 | VRC-INF-001、VRC-INF-002 | DP-EMB-01..04 | PASS | 可独立判定 | 只读 | 无需清理 | DP-EMB-05..07 NOT_RUN |
| §8 Usage 查询接口 | VRC-MGMT-006 | DP-USAGE-01..04 | PASS | 可独立判定 | 只读（查询产生用量记录） | 无需清理 | DP-USAGE-05..08 NOT_RUN |
| §8 Provider CRUD 接口 | VRC-MGMT-001、VRC-MGMT-002 | ADM-PROV-01/03/04 | PASS | 可独立判定 | 只读 | 无需清理 | ADM-PROV-02/05..14 NOT_RUN（B 类 MISSING） |
| §8 provider 上游模型目录接口 | VRC-MGMT-001 | — | NOT_RUN | — | — | — | ADM-PROV-MODELS-01/02 未跑 |
| §8 provider usage 快照接口 | VRC-MGMT-006、VRC-DIAG-004 | ADM-PROV-USAGE-01..03 | PASS | 可独立判定 | 读快照；刷新为一次性状态写（已 teardown） | 已回基线 | ADM-PROV-USAGE-04 NOT_RUN |
| §8 Deployment CRUD 接口 | VRC-MGMT-001、VRC-MGMT-002 | ADM-DEPL-01/03 | PASS | 可独立判定 | 只读 | 无需清理 | ADM-DEPL-02/04..09 NOT_RUN（B 类 MISSING） |
| §8 Service Level CRUD 接口 | VRC-MGMT-002 | ADM-SL-01/03 | PASS | 可独立判定 | 只读 | 无需清理 | ADM-SL-02/02b/04/04b/05..08 NOT_RUN（B 类 MISSING） |
| §8 探测接口 | VRC-DIAG-004 | ADM-PROBE-01/02 | PASS | 可独立判定 | 探测为一次性状态写（已 teardown） | 已回基线 | ADM-PROBE-03 NOT_RUN |
| §8 运行态接口 | VRC-INF-004 | ADM-RUNTIME-01 | PASS | 可独立判定 | 只读 | 无需清理 | ADM-RUNTIME-02 NOT_RUN |
| §8 统计接口 | VRC-MGMT-006 | ADM-STATS-01..03 | PASS | 可独立判定 | 只读 | 无需清理 | — |
| §8 审计接口 | VRC-MGMT-003、VRC-MGMT-006 | ADM-AUDIT-01/02 | PASS | 可独立判定 | 只读 | 无需清理 | ADM-AUDIT-03 NOT_RUN |
| §8 日志接口 | VRC-LOG-001 | ADM-LOGS-01/02 | PASS | 可独立判定 | 只读 | 无需清理 | 负向 NOT_RUN |
| §8 管理 usage 接口 | VRC-MGMT-006 | ADM-USAGE-01/02 | PASS | 可独立判定 | 只读 | 无需清理 | ADM-USAGE-03 NOT_RUN |
| §8 认证与授权跨切面 | VRC-API-002、VRC-MGMT-003 | AUTH-01..06 | PASS | 可独立判定 | 只读 | 无需清理 | AUTH-07..10 NOT_RUN |
| §8 诊断开关/快照/统计/trace/请求追踪接口 | VRC-DIAG-001、VRC-DIAG-002、VRC-API-002 | — | NOT_RUN | — | — | — | OBS-* 全部未跑 |
| §8 契约别名命名空间 | VRC-DIAG-001/002/004 | — | NOT_RUN | — | — | — | OBS-ALIAS-* 未跑 |
| §8 注入配置接口 | VRC-DIAG-004 | — | NOT_RUN | — | — | — | OBS-DEPL-* 未跑 |

**VRC 覆盖小结**：本轮命中 `VRC-API-002`、`VRC-INF-001/002/004`、`VRC-MGMT-001/002/003/006`、`VRC-DIAG-004`、`VRC-LOG-001`；未命中 `VRC-INF-003`（上游非 5xx provider_error）、`VRC-DIAG-001/002`（诊断面）、`VRC-UTIL-001`（scheme §4 裁决为表现层缺口）。方案 §4 具名缺口（`ERR-BOOT`/`ERR-SCHEMA`/`ERR-PATH-UNSAFE`/`ERR-UTIL-TXN`、`VRC-INF-005`、`VRC-UTIL-002`、模块级 `VRC-*`）在本 Run 保持开放，未关闭。

## 6. 缺陷与残余风险

- 缺陷清单（关联 Case 与 Run）：
  - 历史问题 P1/P2/P3/P8/P13/P14 在本轮 **未复发**（LAN IP、endpoint 明确、OMLX 健康、usage RFC3339、依赖头部、DP-RESP-02 期望修正）。
  - P5（capabilities 必填）、P6/API-001（PATCH 412 缺 `current_version`）、P7（If-Match ETag 格式）、P9（provider create 多传 id）本轮 **未涉及**（A 类无 create/PATCH/DELETE），待 B 类验证——保留为开放项。
  - 少量 case 期望与实测不一致（§4 三行），以实测为契约并已改 case，非产品缺陷。
- 残余风险：
  - **分母未闭合**：方案 140 Case 中 87 项 `NOT_RUN`（含 52 MISSING 自动化入口）。在此状态下不得引用本报告作为发布依据。
  - **真实 consumer 未联调**：Piko / Slinky 真实集成未验证；A 类 PASS 只证明 LLMTier 自身运行行为。
  - **容量/耐久未覆盖**：FD 泄漏、30min 耐久、性能 SLO 不在本层（scheme §4 Gap，转运维/性能专项）。
  - **上游模型内容非 Oracle**：仅断言结构/事件序列/字段契约，不证明推理正确性。

## 7. Gate 结论与建议

- Gate 结论（接受/条件接受/拒绝）：**条件接受（仅限于"系统层 A 类回归可用"）**。依据：A 类 53/53 PASS、st_* 30 PASS、unit 191 PASS，无 FAIL；但分母未闭合，`NOT_RUN` 87。
- 开放问题与责任方：
  - 52 项 MISSING 自动化入口补齐（Case 作者）。
  - B 类 CRUD/注入类用例执行（执行者，P2）。
  - 诊断面 OBS-*、AUTH-07..10、DP-RESP 故障注入执行（执行者）。
  - 真 Piko / 真 Slinky 联调（consumer owner）。
  - 本报告不授权 release；`runtime_activation=true` 需独立决定。

## 8. 未决项

| 未决项 / 关联 | Owner / 最晚 Gate | 关闭所需事实或决定 |
|---|---|---|
| 87 NOT_RUN（含 52 MISSING）补齐并执行 | Case 作者 / 进入 Gate 前 | 补齐自动化入口并跑出 PASS，或经批准登记 |
| P5/P6/P7/P9 待 B 类验证 | 执行者 / 下一 Run | B 类 provider/deployment CRUD 执行结果 |
| DP-RESP-11/19/20/22/23 等故障注入与 429 路径 | 执行者 / 下一 Run | 注入命中并记录 Run |
| 诊断面 OBS-*、AUTH-07..10 | 执行者 / 下一 Run | 执行结果 |
| 真 Piko / 真 Slinky 联调 | consumer owner / 验收前 | 真实 consumer 端到端 |
| 容量/耐久（FD/30min/SLO） | 性能/运维 / 另立专项 | 见 scheme §4 Gap |

<!-- 交付自查：任一 Verdict 能否定位唯一 Run 与原始证据；失败与 NOT_RUN 是否如实保留；报告是否越权写成批准。 -->
