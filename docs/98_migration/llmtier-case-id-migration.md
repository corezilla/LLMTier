# LLMTier Case ID 迁移记录（旧族名 → ST-<对象>-<NNN>）

> STD 使用入口：[项目采用说明与标准导航](../../README.md#std-entry)。本文件是 `docs/98_migration/`
> 下的迁移记录（STD `repository-layout.md` §4「迁移盘点、路径映射和阶段性记录」），非 STD 模板文档，
> 不做封面/metadata 控制。

## 1. 迁移背景

STD `78876c9` 在 `docs/software-object-identifiers.md` §2 正式codify Case ID 格式为
**`<阶段前缀>-<对象>-<NNN>`**（系统测试前缀 `ST`；`<对象>`＝被测对象 token；`<NNN>` 三位十进制）。
本文件记录 LLMTier 显式采用时的**旧 ID → 新 ID** 迁移映射（spec §3「历史项目显式采用后迁移」）。

- 适用范围：`docs/70_verification/system/`（系统测试 Case）。
- 单元测试 Case（`UT-<对象>-<NNN>`）经核查**已符合**新规范（3 位序号、阶段前缀 `UT`、对象 token 一致），
  本次**不改名**，仅随按测试阶段的目录重组移动路径。
- 阶段前缀由模板旧草案示例的 `SYS` 定为 **`ST`**；旧族名（`HEALTH`/`DP-*`/`ADM-*`/`OBS-*`/`AUTH`/`UIT-UI`）不再使用。
- `<NNN>` 在该对象 token 段内从 `001` 顺序分配；旧补丁后缀（`ADM-SL-02B`、`ADM-SL-04B`）以 3 位序号吸收。

## 2. 对象 token 映射表

| 旧 Case 族（被测对象） | 新对象 token | 说明 |
|---|---|---|
| `ADM-AUDIT-*` | `audit` | 管理面审计（/v1/audit） |
| `ADM-USAGE-*` | `ausage` | 管理面 usage（GET/DELETE /v1/usage） |
| `AUTH-*` | `auth` | 认证与授权跨切面（角色/LAN trust/无鉴权） |
| `ADM-DEPL-*` | `depl` | 管理面 Deployment CRUD（/v1/deployments） |
| `DP-EMB-*` | `emb` | 数据面 Embeddings（/v1/embeddings） |
| `HEALTH-*` | `health` | 健康/就绪接口（/healthz、/readyz） |
| `ADM-LOGS-*` | `logs` | 管理面日志（/v1/logs） |
| `DP-MODELS-*` | `model` | 数据面逻辑模型清单（/v1/models） |
| `OBS-ALIAS-*` | `obsalias` | 契约别名（/tier/admin/v1/*） |
| `OBS-DEPL-*` | `obsdepl` | 注入配置（/v1/deployments/{id}/diagnostics） |
| `OBS-DIAG-*` | `obsdiag` | 诊断开关（/v1/diagnostics） |
| `OBS-REQTRACE-*` | `obsreqtrace` | 请求追踪（/v1/trace/{request_id}） |
| `OBS-SNAP-*` | `obssnap` | 诊断快照（/v1/diagnostics/snapshots） |
| `OBS-STATS-*` | `obsstats` | 诊断统计（/v1/diagnostics/stats） |
| `OBS-TRACE-*` | `obstrace` | 诊断 trace（/v1/diagnostics/traces） |
| `ADM-PROV-MODELS-*` | `pmod` | Provider 上游模型目录（/v1/providers/{id}/models） |
| `ADM-PROBE-*` | `probe` | 管理面探测（/v1/probes） |
| `ADM-PROV-*` | `prov` | 管理面 Provider CRUD（/v1/providers） |
| `ADM-PROV-USAGE-*` | `pusage` | Provider usage 快照（/v1/providers/{id}/usage） |
| `DP-RESP-*` | `resp` | 数据面 Responses（/v1/responses） |
| `ADM-RUNTIME-*` | `runtime` | 管理面运行态（/v1/runtime） |
| `ADM-SL-*` | `sl` | 管理面 Service Level CRUD（/v1/service-levels） |
| `ADM-STATS-*` | `stats` | 管理面统计（/v1/stats） |
| `UIT-UI-*` | `ui` | web-ui 真实浏览器（模块设计 web-ui §14） |
| `DP-USAGE-*` | `usage` | 数据面 Usage 查询（/v1/usage） |

## 3. 旧 ID → 新 ID 全量映射

共 173 个系统层 Case（0 冲突）。

| 旧 Case ID | 新 Case ID | 新文件名 |
|---|---|---|
| `ADM-AUDIT-01` | `ST-AUDIT-001` | `st-audit-001.md` |
| `ADM-AUDIT-02` | `ST-AUDIT-002` | `st-audit-002.md` |
| `ADM-AUDIT-03` | `ST-AUDIT-003` | `st-audit-003.md` |
| `ADM-AUDIT-04` | `ST-AUDIT-004` | `st-audit-004.md` |
| `ADM-USAGE-01` | `ST-AUSAGE-001` | `st-ausage-001.md` |
| `ADM-USAGE-02` | `ST-AUSAGE-002` | `st-ausage-002.md` |
| `ADM-USAGE-03` | `ST-AUSAGE-003` | `st-ausage-003.md` |
| `AUTH-01` | `ST-AUTH-001` | `st-auth-001.md` |
| `AUTH-02` | `ST-AUTH-002` | `st-auth-002.md` |
| `AUTH-03` | `ST-AUTH-003` | `st-auth-003.md` |
| `AUTH-04` | `ST-AUTH-004` | `st-auth-004.md` |
| `AUTH-05` | `ST-AUTH-005` | `st-auth-005.md` |
| `AUTH-06` | `ST-AUTH-006` | `st-auth-006.md` |
| `AUTH-07` | `ST-AUTH-007` | `st-auth-007.md` |
| `AUTH-08` | `ST-AUTH-008` | `st-auth-008.md` |
| `AUTH-09` | `ST-AUTH-009` | `st-auth-009.md` |
| `AUTH-10` | `ST-AUTH-010` | `st-auth-010.md` |
| `ADM-DEPL-01` | `ST-DEPL-001` | `st-depl-001.md` |
| `ADM-DEPL-02` | `ST-DEPL-002` | `st-depl-002.md` |
| `ADM-DEPL-03` | `ST-DEPL-003` | `st-depl-003.md` |
| `ADM-DEPL-04` | `ST-DEPL-004` | `st-depl-004.md` |
| `ADM-DEPL-05` | `ST-DEPL-005` | `st-depl-005.md` |
| `ADM-DEPL-06` | `ST-DEPL-006` | `st-depl-006.md` |
| `ADM-DEPL-07` | `ST-DEPL-007` | `st-depl-007.md` |
| `ADM-DEPL-08` | `ST-DEPL-008` | `st-depl-008.md` |
| `ADM-DEPL-09` | `ST-DEPL-009` | `st-depl-009.md` |
| `ADM-DEPL-10` | `ST-DEPL-010` | `st-depl-010.md` |
| `ADM-DEPL-11` | `ST-DEPL-011` | `st-depl-011.md` |
| `ADM-DEPL-12` | `ST-DEPL-012` | `st-depl-012.md` |
| `DP-EMB-01` | `ST-EMB-001` | `st-emb-001.md` |
| `DP-EMB-02` | `ST-EMB-002` | `st-emb-002.md` |
| `DP-EMB-03` | `ST-EMB-003` | `st-emb-003.md` |
| `DP-EMB-04` | `ST-EMB-004` | `st-emb-004.md` |
| `DP-EMB-05` | `ST-EMB-005` | `st-emb-005.md` |
| `DP-EMB-06` | `ST-EMB-006` | `st-emb-006.md` |
| `DP-EMB-07` | `ST-EMB-007` | `st-emb-007.md` |
| `DP-EMB-08` | `ST-EMB-008` | `st-emb-008.md` |
| `DP-EMB-09` | `ST-EMB-009` | `st-emb-009.md` |
| `DP-EMB-10` | `ST-EMB-010` | `st-emb-010.md` |
| `HEALTH-01` | `ST-HEALTH-001` | `st-health-001.md` |
| `HEALTH-02` | `ST-HEALTH-002` | `st-health-002.md` |
| `HEALTH-03` | `ST-HEALTH-003` | `st-health-003.md` |
| `HEALTH-04` | `ST-HEALTH-004` | `st-health-004.md` |
| `HEALTH-05` | `ST-HEALTH-005` | `st-health-005.md` |
| `HEALTH-06` | `ST-HEALTH-006` | `st-health-006.md` |
| `ADM-LOGS-01` | `ST-LOGS-001` | `st-logs-001.md` |
| `ADM-LOGS-02` | `ST-LOGS-002` | `st-logs-002.md` |
| `ADM-LOGS-03` | `ST-LOGS-003` | `st-logs-003.md` |
| `DP-MODELS-01` | `ST-MODEL-001` | `st-model-001.md` |
| `DP-MODELS-02` | `ST-MODEL-002` | `st-model-002.md` |
| `DP-MODELS-03` | `ST-MODEL-003` | `st-model-003.md` |
| `DP-MODELS-04` | `ST-MODEL-004` | `st-model-004.md` |
| `DP-MODELS-05` | `ST-MODEL-005` | `st-model-005.md` |
| `DP-MODELS-06` | `ST-MODEL-006` | `st-model-006.md` |
| `DP-MODELS-07` | `ST-MODEL-007` | `st-model-007.md` |
| `OBS-ALIAS-01` | `ST-OBSALIAS-001` | `st-obsalias-001.md` |
| `OBS-ALIAS-02` | `ST-OBSALIAS-002` | `st-obsalias-002.md` |
| `OBS-ALIAS-03` | `ST-OBSALIAS-003` | `st-obsalias-003.md` |
| `OBS-ALIAS-04` | `ST-OBSALIAS-004` | `st-obsalias-004.md` |
| `OBS-ALIAS-05` | `ST-OBSALIAS-005` | `st-obsalias-005.md` |
| `OBS-ALIAS-06` | `ST-OBSALIAS-006` | `st-obsalias-006.md` |
| `OBS-DEPL-01` | `ST-OBSDEPL-001` | `st-obsdepl-001.md` |
| `OBS-DEPL-02` | `ST-OBSDEPL-002` | `st-obsdepl-002.md` |
| `OBS-DEPL-03` | `ST-OBSDEPL-003` | `st-obsdepl-003.md` |
| `OBS-DEPL-04` | `ST-OBSDEPL-004` | `st-obsdepl-004.md` |
| `OBS-DEPL-05` | `ST-OBSDEPL-005` | `st-obsdepl-005.md` |
| `OBS-DIAG-01` | `ST-OBSDIAG-001` | `st-obsdiag-001.md` |
| `OBS-DIAG-02` | `ST-OBSDIAG-002` | `st-obsdiag-002.md` |
| `OBS-DIAG-03` | `ST-OBSDIAG-003` | `st-obsdiag-003.md` |
| `OBS-REQTRACE-01` | `ST-OBSREQTRACE-001` | `st-obsreqtrace-001.md` |
| `OBS-REQTRACE-02` | `ST-OBSREQTRACE-002` | `st-obsreqtrace-002.md` |
| `OBS-REQTRACE-03` | `ST-OBSREQTRACE-003` | `st-obsreqtrace-003.md` |
| `OBS-SNAP-01` | `ST-OBSSNAP-001` | `st-obssnap-001.md` |
| `OBS-SNAP-02` | `ST-OBSSNAP-002` | `st-obssnap-002.md` |
| `OBS-SNAP-03` | `ST-OBSSNAP-003` | `st-obssnap-003.md` |
| `OBS-STATS-01` | `ST-OBSSTATS-001` | `st-obsstats-001.md` |
| `OBS-STATS-02` | `ST-OBSSTATS-002` | `st-obsstats-002.md` |
| `OBS-STATS-03` | `ST-OBSSTATS-003` | `st-obsstats-003.md` |
| `OBS-TRACE-01` | `ST-OBSTRACE-001` | `st-obstrace-001.md` |
| `OBS-TRACE-02` | `ST-OBSTRACE-002` | `st-obstrace-002.md` |
| `OBS-TRACE-03` | `ST-OBSTRACE-003` | `st-obstrace-003.md` |
| `ADM-PROV-MODELS-01` | `ST-PMOD-001` | `st-pmod-001.md` |
| `ADM-PROV-MODELS-02` | `ST-PMOD-002` | `st-pmod-002.md` |
| `ADM-PROBE-01` | `ST-PROBE-001` | `st-probe-001.md` |
| `ADM-PROBE-02` | `ST-PROBE-002` | `st-probe-002.md` |
| `ADM-PROBE-03` | `ST-PROBE-003` | `st-probe-003.md` |
| `ADM-PROV-01` | `ST-PROV-001` | `st-prov-001.md` |
| `ADM-PROV-02` | `ST-PROV-002` | `st-prov-002.md` |
| `ADM-PROV-03` | `ST-PROV-003` | `st-prov-003.md` |
| `ADM-PROV-04` | `ST-PROV-004` | `st-prov-004.md` |
| `ADM-PROV-05` | `ST-PROV-005` | `st-prov-005.md` |
| `ADM-PROV-06` | `ST-PROV-006` | `st-prov-006.md` |
| `ADM-PROV-07` | `ST-PROV-007` | `st-prov-007.md` |
| `ADM-PROV-08` | `ST-PROV-008` | `st-prov-008.md` |
| `ADM-PROV-09` | `ST-PROV-009` | `st-prov-009.md` |
| `ADM-PROV-10` | `ST-PROV-010` | `st-prov-010.md` |
| `ADM-PROV-11` | `ST-PROV-011` | `st-prov-011.md` |
| `ADM-PROV-12` | `ST-PROV-012` | `st-prov-012.md` |
| `ADM-PROV-13` | `ST-PROV-013` | `st-prov-013.md` |
| `ADM-PROV-14` | `ST-PROV-014` | `st-prov-014.md` |
| `ADM-PROV-15` | `ST-PROV-015` | `st-prov-015.md` |
| `ADM-PROV-16` | `ST-PROV-016` | `st-prov-016.md` |
| `ADM-PROV-17` | `ST-PROV-017` | `st-prov-017.md` |
| `ADM-PROV-USAGE-01` | `ST-PUSAGE-001` | `st-pusage-001.md` |
| `ADM-PROV-USAGE-02` | `ST-PUSAGE-002` | `st-pusage-002.md` |
| `ADM-PROV-USAGE-03` | `ST-PUSAGE-003` | `st-pusage-003.md` |
| `ADM-PROV-USAGE-04` | `ST-PUSAGE-004` | `st-pusage-004.md` |
| `DP-RESP-01` | `ST-RESP-001` | `st-resp-001.md` |
| `DP-RESP-02` | `ST-RESP-002` | `st-resp-002.md` |
| `DP-RESP-03` | `ST-RESP-003` | `st-resp-003.md` |
| `DP-RESP-04` | `ST-RESP-004` | `st-resp-004.md` |
| `DP-RESP-05` | `ST-RESP-005` | `st-resp-005.md` |
| `DP-RESP-06` | `ST-RESP-006` | `st-resp-006.md` |
| `DP-RESP-07` | `ST-RESP-007` | `st-resp-007.md` |
| `DP-RESP-08` | `ST-RESP-008` | `st-resp-008.md` |
| `DP-RESP-09` | `ST-RESP-009` | `st-resp-009.md` |
| `DP-RESP-10` | `ST-RESP-010` | `st-resp-010.md` |
| `DP-RESP-11` | `ST-RESP-011` | `st-resp-011.md` |
| `DP-RESP-12` | `ST-RESP-012` | `st-resp-012.md` |
| `DP-RESP-13` | `ST-RESP-013` | `st-resp-013.md` |
| `DP-RESP-14` | `ST-RESP-014` | `st-resp-014.md` |
| `DP-RESP-15` | `ST-RESP-015` | `st-resp-015.md` |
| `DP-RESP-16` | `ST-RESP-016` | `st-resp-016.md` |
| `DP-RESP-17` | `ST-RESP-017` | `st-resp-017.md` |
| `DP-RESP-18` | `ST-RESP-018` | `st-resp-018.md` |
| `DP-RESP-19` | `ST-RESP-019` | `st-resp-019.md` |
| `DP-RESP-20` | `ST-RESP-020` | `st-resp-020.md` |
| `DP-RESP-21` | `ST-RESP-021` | `st-resp-021.md` |
| `DP-RESP-22` | `ST-RESP-022` | `st-resp-022.md` |
| `DP-RESP-23` | `ST-RESP-023` | `st-resp-023.md` |
| `DP-RESP-24` | `ST-RESP-024` | `st-resp-024.md` |
| `DP-RESP-25` | `ST-RESP-025` | `st-resp-025.md` |
| `DP-RESP-26` | `ST-RESP-026` | `st-resp-026.md` |
| `DP-RESP-27` | `ST-RESP-027` | `st-resp-027.md` |
| `ADM-RUNTIME-01` | `ST-RUNTIME-001` | `st-runtime-001.md` |
| `ADM-RUNTIME-02` | `ST-RUNTIME-002` | `st-runtime-002.md` |
| `ADM-RUNTIME-03` | `ST-RUNTIME-003` | `st-runtime-003.md` |
| `ADM-SL-01` | `ST-SL-001` | `st-sl-001.md` |
| `ADM-SL-02` | `ST-SL-002` | `st-sl-002.md` |
| `ADM-SL-02B` | `ST-SL-012` | `st-sl-012.md` |
| `ADM-SL-03` | `ST-SL-003` | `st-sl-003.md` |
| `ADM-SL-04` | `ST-SL-004` | `st-sl-004.md` |
| `ADM-SL-04B` | `ST-SL-013` | `st-sl-013.md` |
| `ADM-SL-05` | `ST-SL-005` | `st-sl-005.md` |
| `ADM-SL-06` | `ST-SL-006` | `st-sl-006.md` |
| `ADM-SL-07` | `ST-SL-007` | `st-sl-007.md` |
| `ADM-SL-08` | `ST-SL-008` | `st-sl-008.md` |
| `ADM-SL-09` | `ST-SL-009` | `st-sl-009.md` |
| `ADM-SL-10` | `ST-SL-010` | `st-sl-010.md` |
| `ADM-SL-11` | `ST-SL-011` | `st-sl-011.md` |
| `ADM-STATS-01` | `ST-STATS-001` | `st-stats-001.md` |
| `ADM-STATS-02` | `ST-STATS-002` | `st-stats-002.md` |
| `ADM-STATS-03` | `ST-STATS-003` | `st-stats-003.md` |
| `ADM-STATS-04` | `ST-STATS-004` | `st-stats-004.md` |
| `UIT-UI-001` | `ST-UI-001` | `st-ui-001.md` |
| `UIT-UI-002` | `ST-UI-002` | `st-ui-002.md` |
| `UIT-UI-003` | `ST-UI-003` | `st-ui-003.md` |
| `UIT-UI-004` | `ST-UI-004` | `st-ui-004.md` |
| `UIT-UI-005` | `ST-UI-005` | `st-ui-005.md` |
| `UIT-UI-006` | `ST-UI-006` | `st-ui-006.md` |
| `UIT-UI-007` | `ST-UI-007` | `st-ui-007.md` |
| `UIT-UI-008` | `ST-UI-008` | `st-ui-008.md` |
| `UIT-UI-009` | `ST-UI-009` | `st-ui-009.md` |
| `UIT-UI-010` | `ST-UI-010` | `st-ui-010.md` |
| `DP-USAGE-01` | `ST-USAGE-001` | `st-usage-001.md` |
| `DP-USAGE-02` | `ST-USAGE-002` | `st-usage-002.md` |
| `DP-USAGE-03` | `ST-USAGE-003` | `st-usage-003.md` |
| `DP-USAGE-04` | `ST-USAGE-004` | `st-usage-004.md` |
| `DP-USAGE-05` | `ST-USAGE-005` | `st-usage-005.md` |
| `DP-USAGE-06` | `ST-USAGE-006` | `st-usage-006.md` |
| `DP-USAGE-07` | `ST-USAGE-007` | `st-usage-007.md` |
| `DP-USAGE-08` | `ST-USAGE-008` | `st-usage-008.md` |
| `DP-USAGE-09` | `ST-USAGE-009` | `st-usage-009.md` |

## 4. 编号说明

- 新 `NNN` 在各自对象 token 段内从 `001` 顺序追加，与旧数字**基本保持对应**；仅在旧编号不连续或含补丁后缀时重排。
- 无编号冲突、无重复；旧 ID 一律标记为 **Retired**，编号不复用。
- 单元 Case（`UT-*`）编号未变，不在本表内。

## 5. 未迁移项（显式例外）

- `tests/system/reports/**`、`tests/system/cases reports/**` 下的**历史 Run 证据**（`case-status.json`、`cases/<id>/manifest.json`）
  保留原 Case ID 键：STD `repository-layout.md` §4.1.1「既有项目不自动搬迁历史报告；采用新布局时保留旧引用」。
  这些目录记录既往执行（各自 `git_commit` 固定），改写会篡改历史；新 Run 将按新 Case ID 生成证据。
- `docs/00_management/std-tailoring.md` 等历史评审/裁剪记录中出现的旧 ID 仅作为**存档**保留。
