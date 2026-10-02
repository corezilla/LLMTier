<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-HEALTH-005 — readyz bootstrap 失败

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-HEALTH-005` |
| Document Version | `0.1.0-draft.4` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-10-01` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-HEALTH-005.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。方案清单行见[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-HEALTH-005` / 系统设计 §8 健康/就绪接口（/healthz、/readyz） / `VRC-MGMT-003`（另记 `VRC-UTIL-001/002`） / `recovery` / `P1`。本文件名 `st-health-005.md`，与 Case ID 唯一对应。
- **测试方法（§1.5 方法表行）**：状态机驱动（bootstrap 失败 → not_ready）+ 契约字段比对
- 要测什么（责任展开）：空库在缺一次性 bootstrap 或 bootstrap 非法时，`GET /readyz` 返回 HTTP 503 + `{status:"not_ready", models:[]}`（空 `models`）；同时 `GET /healthz` 仍为 200（进程存活）。
- 明确不测什么 / 失败含义：**不证明什么**——不证明无 deployment 但 bootstrap 成功时的 `not_ready`（ST-HEALTH-004，其 `models` 为 7 个 `unavailable`，非 `[]`）；
  不证明健康端点无需鉴权（ST-HEALTH-006）；不证明错误信封 code——**`ERR-BOOT`（`bootstrap_required`/`bootstrap_invalid`）的 wire envelope code 不在本 case 断言**：它已在单元层关闭（`UT-MGMT-001::test_empty_store_without_settings_is_bootstrap_required`/`test_missing_section_fails` 等直接断言 `ApiError.status/code`，见[系统测试方案 §4](../llmtier-system-test-scheme.md)），本 case 只覆盖 `/readyz not_ready` 的表现，不断言其 envelope 码；
  不证明 schema 不兼容（`ERR-SCHEMA`）；不触发 provider 计费调用（`LT-OPS-001`）。**失败含义＝引导失败就绪契约破坏**。

**目的（被测契约）**：验证 IF-HEALTH 在**引导失败**时的就绪契约。端点 `GET /readyz`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getReadiness`）。
实现 [`Application.__init__`](../../../../src/http_api/app.py) 捕获 `registry.bootstrap_settings()`/`ensure_fixed_tiers()` 抛出的 `ApiError` 到 `app.bootstrap_error`（[`registry.py`](../../../../src/management/registry.py)：空库缺 settings → `bootstrap_required`；
settings 读/解析/校验失败 → `bootstrap_invalid`）；随后 [`app.py:188-189`](../../../../src/http_api/app.py) 在 `/readyz` 短路返回 `_json(503, {"status":"not_ready","models":[]})`。
设计验证项 `VRC-MGMT-003`、`VRC-UTIL-001/002`；机制 `T-CFG-BOOT`/`R-CFG-02`（[config-lifecycle 机制](../../../20_system_design/mechanisms/config-lifecycle.md)）；
需求链 `LT-FUN-006`/`LT-OPS-001`、`CT-OPS-001`（[系统测试方案 §3](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明无 deployment 但 bootstrap 成功时的 `not_ready`（ST-HEALTH-004）；
不证明健康端点无需鉴权（ST-HEALTH-006）；不证明错误信封 code——`ERR-BOOT` 的 wire envelope code 不在本 case 断言（其单元层宿主见 §1，[系统测试方案 §4](../llmtier-system-test-scheme.md) 已按单元覆盖关闭），本 case 只覆盖 `/readyz not_ready` 的表现，不断言其 envelope 码；
不证明 schema 不兼容（`ERR-SCHEMA`）；不触发 provider 计费调用（`LT-OPS-001`）。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例，见[系统测试方案 §1 测试边界](../llmtier-system-test-scheme.md)）。执行前须满足方案 §5 **附加（B 类）**：临时实例可启动。**当前状态：Implemented——fixture `llmtier_b_no_bootstrap`（[`conftest.py`](../../../../tests/system/conftest.py)）与脚本 [`ST-HEALTH-005.py`](../../../../tests/system/cases/ST-HEALTH-005.py) 已落地并通过。** 本 case 的关键构造是让 `bootstrap_settings` 失败，两种等价臂：
  - **(a) 缺 bootstrap**：以空/新 SQLite 启动且**不提供** `LLMTIER_SETTINGS`/`--settings`；`bootstrap_settings(None)` 在空库（`schema_meta.bootstrap_sha256` 为空）时抛 `ApiError(503, "bootstrap_required")`。
  - **(b) 非法 bootstrap**：提供指向**不存在/无法解析/校验失败**的 settings 文件；`bootstrap_settings` 抛 `ApiError(503, "bootstrap_invalid")`。

  两种构造下 [`serve`](../../../../src/http_api/app.py) 仍启动并监听（`Application` 只把异常记入 `bootstrap_error`），且 `/healthz` 分支（[`app.py:187`](../../../../src/http_api/app.py)）在 bootstrap 检查之前，故可轮询 200。
**fixture（已落地）**：[`conftest.py`](../../../../tests/system/conftest.py) 提供 `llmtier_b_no_bootstrap`（**(a) 无引导臂**——`LLMTierInstance(settings=None)`（其 `__init__` 在不传 settings 时不写 `LLMTIER_SETTINGS`），以空/新 SQLite 启动，`bootstrap_settings(None)` 抛 `bootstrap_required`；
脚本 [`ST-HEALTH-005.py`](../../../../tests/system/cases/ST-HEALTH-005.py) 已断言 `/healthz` 200 + `/readyz` 503 `not_ready` + `models==[]`。
（**(b) 坏引导臂**可选，本轮以 (a) 覆盖。）**不得复用 `llmtier_b`/`llmtier_b_empty`**：二者 bootstrap 均成功，`bootstrap_error` 为 `None`。TS-003 与上游无关（本构造不接上游）。
- **被测入口**：

  ```http
  GET /healthz HTTP/1.1
  Host: 127.0.0.1:<port>
  ```

  ```http
  GET /readyz HTTP/1.1
  Host: 127.0.0.1:<port>
  ```

- **初态构造（经公开入口）**：空库 + 无/坏 bootstrap；**不**提供合法 settings；不创建任何 provider/deployment/service-level；不注入故障；不构造非法 query（非法输入不在本 case 范围）。
- **Fixture / 向量及版本**：B 类 fixture `llmtier_b_no_bootstrap` 已落地（见 §2）；依赖 [`registry.py`](../../../../src/management/registry.py) 的 `bootstrap_required`/`bootstrap_invalid` 与 [`app.py:188-189`](../../../../src/http_api/app.py) 的短路（[系统测试方案 §4 共同机制](../llmtier-system-test-scheme.md)）。
- **依赖的测试资产（tests.asset-design 文档）**：本阶段 `tests.asset-design` 文档尚未建立；B 类实例夹具契约见方案 §4，引用其版本而不复制字节。

## 3. 输入构造

- **输入与构造**：固定请求（无 body、无查询参数、无 `Authorization`）：

  ```http
  GET /healthz HTTP/1.1
  Host: 127.0.0.1:<port>
  ```

  ```http
  GET /readyz HTTP/1.1
  Host: 127.0.0.1:<port>
  ```

  构造点：空库 + 无/坏 bootstrap；**不**提供合法 settings；不创建任何 provider/deployment/service-level；不注入故障；不构造非法 query（非法输入不在本 case 范围）。
- **规模 / 时间域**：两次 GET；无分页/并发；记录 `elapsed` 供报告。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置——已完成）"无引导/坏引导"实例 fixture `llmtier_b_no_bootstrap` 已在 [`conftest.py`](../../../../tests/system/conftest.py) 中落地（脚本 [`ST-HEALTH-005.py`](../../../../tests/system/cases/ST-HEALTH-005.py) 已通过），故可执行本步：以构造 (a) 或 (b) 启动临时实例，轮询 `GET /healthz` 200（`LLMTierInstance.start()` 依赖此点，故启动应成功）。
  2. `GET /healthz`：断言 `status_code == 200`，`status == "ok"`——证明"引导失败 ≠ 进程死亡"。
  3. `GET /readyz`：断言 `status_code == 503`。
  4. 解析 body：断言键集**恰为** `{status, models}`，`status == "not_ready"`，`models == []`（**空数组**）。
  5. 断言 body 中**不存在** `{"error":...}` 信封（`/readyz` 不以 envelope 表达引导失败；`ERR-BOOT` envelope 码由单元层 `UT-MGMT-001` 断言，见[系统测试方案 §4](../llmtier-system-test-scheme.md)）。
  6. （清理）整班结束时由 fixture `stop()` 销毁实例。

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 以构造 (a)/(b) 启动临时实例，轮询 `/healthz` 200 | 实例启动成功且 bootstrap 失败 |
| 2 | `GET /healthz` 断言 200 + `status=="ok"` | 引导失败 ≠ 进程死亡 |
| 3 | `GET /readyz` 断言 503 | HTTP 状态 |
| 4 | 解析 body：键集恰 `{status, models}`、`status=="not_ready"`、`models==[]` | 响应体 |
| 5 | 断言无 `{"error":...}` 信封 | 响应体 |
| 6 | fixture `stop()` 销毁实例 | 无残留 |

**重点关注步骤**：① **`models:[]` 是核心区分点**——ST-HEALTH-004 的 `not_ready` 是 7 个 `unavailable`；本 case 的 bootstrap 失败是**空 `models`**（[`app.py:188-189`](../../../../src/http_api/app.py) 直接返回 `models:[]`）。
观测到 7 元素即说明命中了 ST-HEALTH-004 路径而非本 case，判 FAIL/BLOCKED。② **`/healthz` 仍 200**——必须同时断言，证明存活与就绪分离（`/healthz` 位于 `bootstrap_error` 检查前）。
③ **`bootstrap_error` 的 status 与 `/readyz` 无关**——进程内 `bootstrap_error` 是 `ApiError(503, code∈{bootstrap_required,bootstrap_invalid})`，但 `/readyz` 只回 `{"status":"not_ready","models":[]}`，**不回**该 `code`；
不得断言 envelope（其单元层宿主见 §1，[系统测试方案 §4](../llmtier-system-test-scheme.md)）。④ **构造确定性**——缺 settings 与坏 settings 两种臂都可用；若选 (b) 需写明坏 settings 的具体形态（不存在路径/非法 JSON/未知 section）。
⑤ **不得被替代路径冒充**——必须真实启动临时实例使其 bootstrap 失败，不得直接 mock `readiness_view` 或 `bootstrap_error`。⑥ **边界注（不属本 case 判定）**：A 类 m5air 的 schema/引导失败场景为 HARD-BLOCKED，且恢复路径为其专属；
本 case 只在 B 类空/坏库触发，不触碰 A 类库。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = 系统设计 §8.1 `GET /readyz` 的 `not_ready` 契约 + [`app.py:188-189`](../../../../src/http_api/app.py) 的实现形态（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md)、[系统测试方案 §4](../llmtier-system-test-scheme.md)），不依赖实现内部数据。**判据语义以设计验证项 `VRC-MGMT-003` 为唯一权威**。
  - `GET /healthz`：`200`；body 键集 `{status, version}`、`status=="ok"`、`version` 非空字符串。
  - `GET /readyz`：`503`；`Content-Type: application/json; charset=utf-8`；body 键集**恰为** `{status, models}`；`status=="not_ready"`；`models==[]`；无 `{"error":...}`。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`/healthz` 200 + `{"status":"ok",...}`；`/readyz` 503 + `status=="not_ready"` + `models==[]` + 无 envelope。
  - **FAIL**：`/readyz` status/body 不符——含误为 `models` 非空（ST-HEALTH-004 路径）、误为 200、或返回错误信封；`/healthz` 非 200；给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：仅在 `llmtier_b_no_bootstrap` 不可启动、或进程在 `Application.__init__` 之外提前退出导致 `/healthz` 不可达（依赖失败）时判 BLOCKED/SKIP。fixture（`llmtier_b_no_bootstrap`）与脚本（[`ST-HEALTH-005.py`](../../../../tests/system/cases/ST-HEALTH-005.py)）均已落地并通过，不再是当前状态。
  - **SKIP**：B 类临时实例不可用等 §2 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：未真实制造引导失败却按 `not_ready` 判定，或以 mock/替代路径冒充真实临时实例——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 case 有实现（[`ST-HEALTH-005.py`](../../../../tests/system/cases/ST-HEALTH-005.py)），未执行时记 `NOT_RUN`；不得以未跑冒充 PASS。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：构造失败（实例无法以引导失败启动、`/healthz` 不可达、或误命中 ST-HEALTH-004 路径得到 7 元素 `models`）是主要错误出口；按 §5 判 FAIL/BLOCKED 并保留失败现场。
- **副作用断言与清理**：B 类实例按方案 §4 由 fixture `stop()` + `shutil.rmtree` 临时目录销毁；本 case 只读两个健康端点，不创建/修改资源、不写注入。离开前确认无未清空注入项（本 case 不注入）。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-system-test-scheme.md)：保存构造证据（选 (a)/(b)、坏 settings 内容或"未提供 settings"、DB 为空且无 `bootstrap_sha256`）、`/healthz` 与 `/readyz` 的原始 HTTP status/headers/body、`elapsed`；manifest 与报告落位（`tests/system/reports/...`）见 §4.8/§10（本 case `environment:"b"`）；失败现场不截断。
- **依赖**：B 类 fixture `llmtier_b_no_bootstrap`（[`conftest.py`](../../../../tests/system/conftest.py)：(a) `LLMTierInstance(settings=None)` 空库 → `bootstrap_required`；**(b) 臂可选**）；**不可复用** `llmtier_b`/`llmtier_b_empty`（bootstrap 均成功）。另依赖[系统测试方案 §4 共同机制](../llmtier-system-test-scheme.md)；[`registry.py`](../../../../src/management/registry.py) 的 `bootstrap_required`/`bootstrap_invalid` 与 [`app.py:188-189`](../../../../src/http_api/app.py) 的短路；系统设计 `ERR-BOOT` 与 §8.1（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md)；`ERR-BOOT` envelope 码的单元层宿主见 §1）；自动化入口 [`ST-HEALTH-005.py`](../../../../tests/system/cases/ST-HEALTH-005.py)。**不依赖**其它 Case；与 ST-HEALTH-004 同 `not_ready` 但 `models` 形态互斥（空 vs 7×`unavailable`），各自独立执行。

> 实现状态：Implemented（`ST-HEALTH-005.py` 已断言 `/healthz` 200 + `/readyz` 503 `not_ready` + `models==[]`）；执行状态与 Verdict 只在 Run 报告。
