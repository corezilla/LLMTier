<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-MODEL-001 — 列出全部可见 tier

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-MODEL-001` |
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
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-MODEL-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。方案清单行见[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-MODEL-001` / 系统设计 §8 逻辑模型清单接口（/v1/models） / `VRC-INF-002`（清单行另记 `R-CFG-01`） / `normal` / `P0`。本文件名 `st-model-001.md`，与 Case ID 唯一对应。
- **测试方法（§1.5 方法表行）**：等价类划分 + 契约字段比对
- 要测什么（责任展开）：`GET /v1/models` 返回全部可见逻辑模型（fixed tier）清单：HTTP 200 + `object=="list"` + `data` 恰含 7 个 tier、id 互不重复。
- 明确不测什么 / 失败含义：**不证明什么**——不证明单模型精确返回（ST-MODEL-002）、大小写/URL 编码/不存在负向（ST-MODEL-003/04/05/06）、`capabilities` 键集完整性（ST-MODEL-007）；不证明凭据负向与 LAN trust（ST-AUTH-001/02/06）；不证明 `availability` 与上游健康一致（本 case 只断言枚举合法，不断言具体值）；不触上游，故不证明任何 provider/模型可用性。**失败含义＝模型清单读契约破坏**。

**目的（被测契约）**：验证 Data Plane `GET /v1/models`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listModels`，全局 `security=BearerAuth`，role=`data`）的**模型清单读契约**。
被测端点/规则：成功返回 `ModelList`（`{object:"list", data:[Model...]}`，`additionalProperties:false`）；`data` 元素为 `Model`（`{id,object,created,owned_by,availability,capabilities}`，`additionalProperties:false`），`object=="model"`、`owned_by=="llmtier"`、`availability∈{available,degraded,unavailable}`；
`data` 恰含 7 个 fixed tier（`FIXED_TIERS`）。实现见 [`ModelCatalog.list()`](../../../../src/inference/models.py) 与 [`Registry.list_service_levels()`](../../../../src/management/registry.py)；
该端点**只读 Registry、不 dispatch 上游**。设计验证项 `VRC-INF-002`；家族需求链 `LT-FUN-002`、机制 `R-INF-04`/`R-INF-07`、`T-TRUST-ENDPOINTS`、契约 `CT-MODEL-001`（[系统测试方案 §3](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。
**不证明什么**：不证明单模型精确返回（ST-MODEL-002）、大小写/URL 编码/不存在负向（ST-MODEL-003/04/05/06）、`capabilities` 键集完整性（ST-MODEL-007）；不证明凭据负向与 LAN trust（ST-AUTH-001/02/06）；
不证明 `availability` 与上游健康一致；不触上游。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 现有实例，角色 `data`，只读/无副作用；见[系统测试方案 §1 测试边界](../llmtier-system-test-scheme.md)）；前置 = 就绪检查（由 `conftest.py::pytest_configure` 自动执行，任一失败 → 整班 BLOCKED/SKIP）。fixture = `api_client`（Data 角色客户端，见[系统测试方案 §4 共同机制](../llmtier-system-test-scheme.md)）。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier；基线 tier 集合见 [`constants.FIXED_TIERS`](../../../../tests/system/constants.py)。
- **被测入口**：

  ```http
  GET /v1/models HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Accept: application/json
  ```

- **初态构造与客户端**：只读，无状态型初态需构造；凭据固定 `data`（经 `api_client` 注入，见[系统测试方案 §4 共同机制](../llmtier-system-test-scheme.md)）。
- **依赖的测试资产（tests.asset-design 文档）**：本阶段 `tests.asset-design` 文档尚未建立；`api_client` 等夹具契约见方案 §4，引用其版本而不复制字节。

## 3. 输入构造

- **输入与构造**：固定请求（无请求体、无查询参数）：

  ```http
  GET /v1/models HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Accept: application/json
  ```

  构造点：**无 body**（GET 不携带）；**无 query**（清单端点不接受参数）；凭据固定 `data`（经 `api_client` 注入）；不注入故障；不构造非法输入（错误/空/缺凭据属 ST-AUTH-001/02/06）。基线期望由 `FIXED_TIERS` 常量决定（**集合/数量**；不依赖实现返回顺序）。
- **规模 / 时间域**：单次 GET，固定 7 元素；无分页/并发；记录 `elapsed` 供报告。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = api_client.get("/v1/models")`；记录 status、`Content-Type`、`X-Request-ID`、原始 body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`，且存在 `X-Request-ID` 响应头。
  4. 解析 JSON：断言顶层为对象且键集**恰为** `{object, data}`（`additionalProperties:false`），`body["object"] == "list"`，`body["data"]` 为数组。
  5. 断言 `len(data) == 7`；`[m["id"] for m in data]` 无重复；`set(ids) == set(FIXED_TIERS)`（**只断言集合/数量，不断言顺序**）。
  6. 抽每个元素：键集**恰为** `{id,object,created,owned_by,availability,capabilities}`；`object=="model"`、`owned_by=="llmtier"`、`created` 为正整数、`availability` 在枚举内、`capabilities` 为对象。

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 确认基线（`pytest_configure` 自动执行） | 就绪检查通过 |
| 2 | `api_client.get("/v1/models")` | status / headers / body |
| 3 | 断言 200 + `application/json` + `X-Request-ID` | 响应头 |
| 4 | 顶层键集恰 `{object, data}`、`object=="list"` | 响应体 |
| 5 | `len(data)==7`、id 无重复、集合恰为 `FIXED_TIERS` | 响应体（不判顺序） |
| 6 | 每元素键集与字段值（`object`/`owned_by`/`created`/`availability`/`capabilities`） | 响应体 |

**重点关注步骤**：① **精确元素数**——不是"至少含 7 个"，而是 `len(data)==7` 且 id 集合恰等于 7 个 fixed tier（多/少/重复即 FAIL）；② **键集精确性**——顶层 `ModelList` 与每个 `Model` 均为 `additionalProperties:false`，多一个键即违约；
③ **不得以错误信封冒充**——非 200 时须确认是 `ERR-AUTH-*`/其它可解释错误，而非把 `{error:...}` 当 `ModelList` 读；④ **不触上游**——本端点不应产生上游调用或账本义务，区别于 `/v1/responses`；
⑤ **`availability` 只验枚举**——m5air 各 tier 的实际可用性随上游状态变化，不写死具体值；⑥ **`created` 是响应时刻**——实现为 `int(time.time())`（[`models.py`](../../../../src/inference/models.py) `_view`），**不是**持久化创建时间，故只断言"正整数"，不得断言跨请求稳定。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = [openapi](../../../../interfaces/openapi/llmtier.openapi.json) `ModelList`/`Model` 的 wire 形态 + 固定 tier 基线（**集合/数量**，不依赖"清单看起来对"，也不依赖实现顺序）。**判据语义以设计验证项 `VRC-INF-002` 为唯一权威**。
  - HTTP：`200`；`Content-Type: application/json`；`X-Request-ID` 存在。
  - 顶层键集恰 `{object, data}`；`object=="list"`；`data` 长度 7。
  - `data` 的 id **集合恰为** `set(FIXED_TIERS)` = `{Senior, Junior, Worker, Associate, Engineer, Executor, Embedding-v1}`；**不断言数组顺序**。
  - 每个元素键集恰 `{id,object,created,owned_by,availability,capabilities}`，`object=="model"`、`owned_by=="llmtier"`、`created` 为正整数、`availability∈{available,degraded,unavailable}`。
  - 无 `{"error":{...}}` 信封。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：上述期望结果与独立 Oracle 全部 match（status + content-type + 顶层键集 + `object=="list"` + `len(data)==7` + id 集合 + 每元素 `Model` 键集与字段值）。
  - **FAIL**：任一断言不符（status 非 200、`object` 错、元素数/id 集合不符、键集多/缺、字段类型或枚举错）——记 FAIL 并给预期 vs 实际、`reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（fixture 写不出、断言逻辑错、`openapi` 语义不清）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：就绪前置不满足（m5air 不可达、`/readyz` 非 7 tier、双 OMLX 离线等）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或不触真实 Registry 却按行为判定——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 case 有实现（方案清单 `RUN`），未执行时记 `NOT_RUN`；不得以未跑冒充 PASS。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：本 case 为只读成功路径；非 200/非法 body 时按 §5 判 FAIL 并保留失败现场（含错误信封）。
- **副作用断言与清理**：**无需 teardown**——本 case 为只读 `GET`，不创建/修改 provider/deployment/service-level、不写注入项、不写 usage/账本。退出前确认 `/readyz` 仍显示 7 tier 且无未清空注入项（本 case 不注入）；若被误跑于 B 类临时实例，则按[系统测试方案 §4 共同机制](../llmtier-system-test-scheme.md) 整班 `stop()` + `rm -rf` 临时目录。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-system-test-scheme.md)：保存原始 HTTP status/headers/body、发出命令（httpx/`curl`）、exit code、`elapsed`、环境快照（`/healthz`/`/readyz` + provider/deployment 列表）；manifest 与报告落位（`tests/system/reports/...`）见 §4.8/§10（本 case `environment:"a"`）；失败现场不截断。
- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`api_client` fixture（[系统测试方案 §4 共同机制](../llmtier-system-test-scheme.md)）；`FIXED_TIERS` 基线（[`constants.py`](../../../../tests/system/constants.py) / [`registry.py`](../../../../src/management/registry.py)）；实现 [`src/inference/models.py`](../../../../src/inference/models.py)；`ModelList`/`Model` 机器契约（[`interfaces/openapi/llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)）；自动化入口 [`ST-MODEL-001.py`](../../../../tests/system/cases/ST-MODEL-001.py)。**不依赖**其它 Case；与 ST-MODEL-007（同一清单上的 capabilities 键集断言）共享响应但各自独立执行、互不关闭。

> 实现状态：Implemented（`ST-MODEL-001.py` 已断言本 case 契约）；执行状态与 Verdict 只在 Run 报告。
