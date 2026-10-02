<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-OBSDEPL-001 — 读取 deployment 注入配置

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-OBSDEPL-001` |
| Document Version | `0.1.0-draft.3` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-10-01` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-OBSDEPL-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`ST-OBSDEPL-001`）；责任摘要、分类与优先级以 [系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-OBSDEPL-001` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-OBSDEPL-001` / 系统设计 §8 注入配置接口（/v1/deployments/{id}/diagnostics） / `VRC-DIAG-004` / `normal` / `P0`
- **测试方法（§1.5 方法表行）**：等价类划分 + 契约字段比对
- 方案清单登记：`ST-OBSDEPL-001`
- 要测什么（责任展开）：`GET /v1/deployments/{id}/diagnostics` 返回该 deployment 的故障注入配置：HTTP 200 + `InjectionView[]`（每项恰 6 键）。
- 明确不测什么 / 失败含义：不证明 写入注入（ST-OBSDEPL-002）、不证明未知 deployment 的 404（ST-OBSDEPL-003）、不证明非法注入项的 400（ST-OBSDEPL-004）、不证明注入对推理的命中效果（ST-RESP-011/22，属 `T-OBS-INJECT` 命中证明）、不证明别名等价（ST-OBSALIAS-004）。

**目的（被测契约）**：验证 Observability `GET /v1/deployments/{deployment_id}/diagnostics` 的**只读注入配置契约**。被测端点/规则：`GET /v1/deployments/{deployment_id}/diagnostics`，成功返回 `InjectionView[]`（顶层为数组），每项 `InjectionView` 必填 6 键（`id, deployment_id, type, config, enabled, updated_at`），`type ∈ {fault_502, fault_503, delay, rate_limit, stream_terminate, malformed_event}`，`config` 为对象、`enabled` 为布尔；
未知 deployment → 404 `not_found`（本 case 用已知 id，负向属 ST-OBSDEPL-003）；认证 `admin`；失败走统一信封 `{error:{message,type,code,param,retryable}}`（401/403/404/503）。
设计验证项 `VRC-DIAG-004`；机制 `T-OBS-INJECT`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §4.2 `D-OBS-INJECTION[]`、§4.9 `D-OBS-INJECTION-CONFIG`、§5.1 `IF-OBS-INJECT`）；
错误目录 `ERR-INJECTION`/`ERR-NOTFOUND`/`ERR-STORE`；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）；
机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`InjectionView`，`security=AdminBearerAuth`）。
**不证明什么**：不证明写入注入（ST-OBSDEPL-002）、不证明未知 deployment 的 404（ST-OBSDEPL-003）、不证明非法注入项的 400（ST-OBSDEPL-004）、不证明注入对推理的命中效果（ST-RESP-011/22，属 `T-OBS-INJECT` 命中证明）、不证明别名等价（ST-OBSALIAS-004）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；初始状态=§2.3 A 类基线；以 §2.1 已注册的 deployment（如 `dep_local_gemma`）为目标；`diagnostic_injections` 对既有 deployment **预期为空**（无启用注入；残留核验见 §2.8）。本 case 纯读，初态即终态。

## 3. 输入构造

- **输入与构造**：固定请求（无 body）：
  `GET /v1/deployments/dep_local_gemma/diagnostics`、`Authorization: Bearer dev-admin`、`Accept: application/json`。边界点：**无请求体**；`{id}` 取 §2.1 已注册 deployment（4 选 1）；不构造未知 id（ST-OBSDEPL-003）；不写入、不注入；`{}` 与 `[]` 的区分——成功 body 是**数组**（可为空数组），不是 `{items:[...]}` 包封对象（注意与 ST-RESP-011 的写入 body 形态不同）。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz`（§2.1，自动执行）。
  2. `GET /v1/deployments/dep_local_gemma/diagnostics`（`admin_client`）→ 记录 status/`Content-Type`/原始 body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 JSON，断言顶层为**数组**（不是对象）。
  5. 对每个 `item`：断言键集**恰为** `{id, deployment_id, type, config, enabled, updated_at}`；`id`/`deployment_id`/`updated_at` 为字符串、`type ∈` 枚举、`config` 为对象、`enabled` 为 JSON 布尔。
  6. 断言每个 `item.deployment_id == "dep_local_gemma"`（只返回该 deployment 的注入）。
  7. （交叉核对，不改变判定）与别名 `GET /tier/admin/v1/deployments/dep_local_gemma/diagnostics` 同凭据下响应体逐字节比对，作为 ST-OBSALIAS-004 的旁证；本 case 不承担别名判定。

**重点关注步骤**：① **顶层数组 vs 包封对象**——成功体是 `InjectionView[]` 裸数组；若是 `{items:[...]}` 判 FAIL（PATCH body 才是 `{items}`）。② **项键集精确**——恰 6 键（`additionalProperties:false`）。
③ **`type` 枚举**——6 值白名单，越界即 FAIL。④ **`config` 为对象**——不得为 `null`/字符串；具体字段随 `type` 变化（如 `fault_502` → `error_body`、`delay` → `delay_ms`）。
⑤ **`enabled` 布尔**——不得用 `0/1`。⑥ **deployment 作用域**——返回项必须与路径 id 一致，不得混入其它 deployment。⑦ **空数组合法**——无注入时 `[]` 合法（PASS），不要求非空。
⑧ **降级/存储**——`_UnavailableDiagnostics.injections` 恒返回 `[]` 的 **200**（fail-open，形状 PASS）；`503 usage_store_unavailable` 判 BLOCKED/SKIP。
自动化入口 `ST-OBSDEPL-001.py` 已实现（§3.5 P0 Gate 阻断项已消解）。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `InjectionView` wire 形态 + 机制 §4.2/§4.9 映射（不依赖实现内部）。
  - HTTP：`200`；`Content-Type: application/json`（openapi 未为 200 声明响应头）。
  - body：JSON 数组；每项键集恰 6、`type` 枚举、`config` 对象、`enabled` 布尔、`deployment_id` 等于路径 id。
  - 空数组合法。
  - **fail-open**：降级实例 `200 + []` → **PASS**（本 case 不要求非空）；健康实例非 200、顶层非数组、项键集/枚举/类型不符 → **FAIL**；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + 顶层数组 + 每项恰 6 键且 `type`/`config`/`enabled` 正确 + `deployment_id` 匹配路径（含空数组 fail-open）。
  - **FAIL**：非 200（存储健康时）、顶层为对象、项键集不符、`type` 越枚举、`enabled` 非布尔、或返回别的 deployment 的注入。
  - **BLOCKED**：测试代码/契约问题或存储不可达 `503 usage_store_unavailable`——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足（含 `dep_local_gemma` 未注册）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：无（自动化入口已实现；P0 Gate 阻断项已消解，执行状态见 Run 报告）。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air，或未命中真实诊断服务却按行为判定——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——纯读，不写 `diagnostic_injections`、不改开关、不注入。退出前确认无未清空注入项（本 case 不注入）、`/readyz` 仍 7 tier。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存原始 HTTP status/headers/body、命令/exit code/`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 6 项就绪检查（含 `dep_local_gemma` 注册）；`admin_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；M007 `diagnostic_injections`（`002_observability.sql`）；`InjectionView` 机器契约；实现 [`src/libdiag/injections.py`](../../../../src/libdiag/injections.py)、[`src/http_api/app.py`](../../../../src/http_api/app.py)。自动化入口 `ST-OBSDEPL-001.py`（已实现）。**不依赖**其它 Case；与 ST-OBSDEPL-002（写入）、ST-OBSDEPL-003（未知 404）、ST-OBSDEPL-004（非法项 400）语义相邻但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
