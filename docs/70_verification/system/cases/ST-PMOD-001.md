<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-PMOD-001 — provider 上游模型目录

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-PMOD-001` |
| Document Version | `0.1.0-draft.4` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-PMOD-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-PMOD-001`）；责任摘要、分类与优先级以 [系统测试方案 §6](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 provider 上游模型目录接口（GET /v1/providers/{id}/models）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-001`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-PMOD-001` 可追到方案清单行与 Run 报告。

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-PMOD-001` / 系统设计 §8 provider 上游模型目录接口（GET /v1/providers/{id}/models） / `VRC-MGMT-001` / `normal` / `P1`
- **测试方法（§2.2 方法表行）**：等价类划分 + 契约字段比对
- 方案清单登记：`ST-PMOD-001`（与 计划 §3 权威清单一致；本文件名 `st-pmod-001.md`，唯一对应）。
- 要测什么（责任展开）：`GET /v1/providers/{id}/models` 读取 provider 上游模型目录：HTTP 200 + `ProviderModelsView`（`data: string[]`），同步只读且不改任何本地资源。
- 明确不测什么 / 失败含义：不证明 未知 provider 的 404（ST-PMOD-002）、不证明 provider 读取不回显 secret（ST-PROV-014）、不证明 deployment/provider CRUD（ST-PROV-*/ST-DEPL-*）、不证明上游目录**内容正确**（上游模型 ID 由上游决定，本 case 只断言 `data` 为字符串数组，**不把具体模型名当 oracle**）；本 case 为注册表（A 类）上的只读目录查询，允许触上游 `/models`（只读），不产生费用类副作用。

**目的（被测契约）**：验证 Management **provider 上游模型目录读契约**。被测端点/规则：`GET /v1/providers/{provider_id}/models`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listProviderModels`，`security=AdminBearerAuth`），认证角色 `admin`；
成功 `200` + `ProviderModelsView`（`data: string[]`，`additionalProperties:false`，`required=[data]`）；失败走统一错误信封 `{error:{message,type,code,param,retryable}}`（401 `authentication_required` / 403 `permission_denied` / 404 `not_found`）。
实现见 [`admin.list_provider_models`](../../../../src/management/admin.py) → [`registry.get_provider`](../../../../src/management/registry.py) → [`OpenAIProvider.list_models`](../../../../src/inference/providers/openai.py)（`[m["id"] for m in payload.get("data", []) if isinstance(m.get("id"), str)]`——即 `data` 缺省按空数组处理，且仅保留 `id` 为字符串的元素）。
设计验证项 `VRC-MGMT-001`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`T-CFG-SECRET`、`CT-ADMIN-001`（[系统测试方案 §6 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。
**不证明什么**：不证明未知 provider 的 404（ST-PMOD-002）、不证明 provider 读取不回显 secret（ST-PROV-014）、不证明 deployment/provider CRUD（ST-PROV-*/ST-DEPL-*）、不证明上游目录**内容正确**（上游模型 ID 由上游决定，本 case 只断言 `data` 为字符串数组，**不把具体模型名当 oracle**）；
本 case 为注册表（A 类）上的只读目录查询，允许触上游 `/models`（只读），不产生费用类副作用。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例；角色 `admin`，只读；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。执行前必须通过[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 的 6 项就绪检查（详见计划 §3）；任一失败 → 整班 BLOCKED/SKIP，不得改用模拟路径。fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）：`admin_client`。初始状态：m5air 现有 3 provider / 4 deployment / 7 fixed tier；被测 provider 取 计划 §3 必需的 `provider_local`（必在，避免依赖历史 provider）。**自动化入口 `ST-PMOD-001.py` 为 `Implemented`（A 类）**，落位与命名按 §4.9/§8.5。

## 3. 输入构造

- **输入与构造**：固定请求（无请求体、无查询参数；`{provider_id}` 取 `provider_local`）：
  ```http
  GET /v1/providers/provider_local/models HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`provider_id` 固定为注册表内既存 provider（`provider_local`）；**无 body**（GET 不携带）；**无 query**（该端点不接受参数）；不注入故障；不构造非法输入（非法/缺凭据属 ST-AUTH-*，未知 id 属 ST-PMOD-002）。`data` 的**元素值不固定**（上游决定），只断言 `data` 为字符串数组。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 计划 §2 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/providers/provider_local/models")`；记录 status、`Content-Type`、原始 body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 body：断言其为对象且键集**恰为** `{data}`（`additionalProperties:false`，多一个键即违反）。
  5. 断言 `isinstance(body["data"], list)` 且 `all(isinstance(x, str) for x in body["data"])`；允许空数组（上游无模型），但**不得**出现对象/数字元素。
  6. （交叉核对，不改变本 case 判定）`GET /v1/providers/provider_local` 断言 `200`，佐证该 provider 存在（200 是"既存 provider 的目录读取"，不是未知 id 的兜底）。

**重点关注步骤**：① **键集精确性**——不是"含 `data`"，而是"键集恰为 `{data}`"，防止 provider 视图字段误并入；② **元素类型**——必须是字符串（上游 `/models` 返回对象，网关按 `id` 投影），把对象当元素即违反 `ProviderModelsView`；
③ **不硬编码模型名**——上游目录随环境变化，Oracle 只约束 `string[]`；④ **允许触上游**——该端点会调 `provider.endpoint + /models`（只读目录，[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)），执行者需授权并登记；
`confirm_external_call` **不**是此只读路由的参数（对比 ADM-PROV-USAGE/PROBE）；⑤ **admin 面**——data/none 凭据的 401/403 由 AUTH 家族承接，本 case 不重测；
⑥ **不得把错误信封当目录**——非 200 必须先确认是可解释的 `ERR-*`，而非把 `{error:...}` 当 `data` 读。
  > **实现 vs 契约偏差（登记，不在本 case 失败面）**：系统设计 §`GET /v1/providers/{provider_id}/models` 与 `openapi` 声明"上游不可用 → `ERR-PROVIDER-UNAVAIL`（503）"，实现 [`OpenAIProvider.list_models`](../../../../src/inference/providers/openai.py) 捕获上游失败：上游 5xx/网络/超时/JSON 解析失败 → `503 provider_unavailable`（`retryable=True`），上游 4xx → `provider_error`（状态码沿用上游，`retryable` 仅 408/429）；
    并非落 `_run` 兜底的 **500 `internal_error`**。本 case 只走 happy path，不据此判 FAIL；偏差在运行报告登记。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ProviderModelsView` wire 形态（不依赖上游具体模型名）。
  - HTTP：`200`；`Content-Type: application/json`。
  - body：JSON 对象，键集**恰为** `{data}`；`data` 为数组，元素均为 JSON 字符串。
  - 无错误信封：本 case 不应出现 `{"error":{...}}`。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` 且 body 键集恰为 `{data}` 且 `data` 为字符串数组（含空数组）。
  - **FAIL**：status 非 200 且实例/上游健康；或 body 键集不符/`data` 非数组/含非字符串元素；或以错误信封冒充目录。
  - **BLOCKED**：无法执行/无法判定且可重试（测试代码/契约问题、上游目录端点在窗口内不可达而无法建立 Oracle）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：计划 §3 前置不满足（m5air 不可达、`/readyz` 非 7 tier、双 OMLX 离线、`provider_local` 未注册）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或伪造目录列表——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§7，`ST-PMOD-001.py`），本轮未执行时按 §9 记 `NOT_RUN`；不得以未跑冒充 PASS。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需资源 teardown**——本 case 为只读 `GET`，不改 provider/deployment/service-level、不写注入、不写快照（仅查询上游目录）。退出前确认 `/readyz` 仍显示 7 tier、provider 列表未变、无未清空注入项；若被误跑于 B 类临时实例，则按[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理) 整班 `stop()` + `rm -rf` 临时目录。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见计划 §7/§10；失败现场不截断。**本 case 额外证据**：上游目录端点被调用的事实记录；`inputs` 含 `provider_id`。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查（含 计划 §3 必需 provider/deployment）；`admin_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；既存 provider `provider_local`；`ProviderModelsView` 机器契约（`interfaces/openapi/llmtier.openapi.json`）；实现 `src/management/admin.py` / `src/inference/providers/openai.py`；自动化入口 `ST-PMOD-001.py`（`Implemented`）。**不依赖**其它 Case；与 ST-PMOD-002（未知 provider → 404）成对但各自独立执行。

> 实现状态：Implemented（`ST-PMOD-001.py`）；执行状态与 Verdict 只在 Run 报告。
