<!-- STD_DOCUMENT_COVER_BEGIN -->
# DP-MODELS-02 — 精确返回模型

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `DP-MODELS-02` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-09-29` |
| Template ID | `tests.system-test-design` |
| Template Version | `2.3.0` |
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/cases/dp-models-02.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。方案清单行见[系统测试方案 §3 覆盖分母与 Case 清单](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`DP-MODELS-02` / 系统设计 §8 逻辑模型清单接口（/v1/models） / `VRC-INF-001/002` / `normal` / `P0`。本文件名 `dp-models-02.md`，与 Case ID 唯一对应。
- 要测什么（责任展开）：`GET /v1/models/Worker` 按精确 id 返回单个逻辑模型：HTTP 200 + `id=="Worker"` + `object=="model"` + `created` 为正整数。
- 明确不测什么 / 失败含义：**不证明什么**——不证明清单聚合（DP-MODELS-01）、大小写/URL 编码/不存在负向（DP-MODELS-03/04/05/06）、`capabilities` 键集完整性（DP-MODELS-07）；不证明凭据与 LAN trust（AUTH-01/02/06）；不证明 `availability` 与上游健康一致（只断言枚举合法）；不触上游。**失败含义＝单模型精确读契约破坏**。

**目的（被测契约）**：验证 Data Plane `GET /v1/models/{model}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getModel`，`model` 为**精确大小写敏感**路径参数，全局 `security=BearerAuth`，role=`data`）的**单模型精确读契约**。被测端点/规则：成功返回 `Model`（`{id,object,created,owned_by,availability,capabilities}`，`additionalProperties:false`），其中 `id` 等于请求的 `model` 字面值、`object=="model"`、`owned_by=="llmtier"`；实现 [`Registry.get_service_level(model_id)`](../../../../src/management/registry.py) 以 SQL 精确等值匹配（`WHERE id=?`），[`ModelCatalog.get()`](../../../../src/inference/models.py) 在未命中时转译 404。该端点**只读 Registry、不 dispatch 上游**。设计验证项 `VRC-INF-001/002`；机制 `R-INF-04`（清单行）；家族需求链 `LT-FUN-002`、`R-INF-04`/`R-INF-07`、`T-TRUST-ENDPOINTS`、契约 `CT-MODEL-001`（[系统测试方案 §3](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明清单聚合（DP-MODELS-01）、大小写/URL 编码/不存在负向（DP-MODELS-03/04/05/06）、`capabilities` 键集完整性（DP-MODELS-07）；不证明凭据与 LAN trust；不证明 `availability` 与上游健康一致；不触上游。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 现有实例，角色 `data`，只读/无副作用；见[系统测试方案 §1 测试边界](../../schemes/llmtier-system-test-scheme.md)）；前置 = 就绪检查（由 `conftest.py::pytest_configure` 自动执行，任一失败 → 整班 BLOCKED/SKIP）。fixture = `api_client`（Data 角色客户端，见[系统测试方案 §4 共同机制](../../schemes/llmtier-system-test-scheme.md)）。初始状态 = 3 provider / 4 deployment / 7 fixed tier；本 case 选取存在的 fixed tier `Worker`（[`FIXED_TIERS`](../../../../tests/system/api_test_v03/constants.py)）。
- **被测入口**：

  ```http
  GET /v1/models/Worker HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Accept: application/json
  ```

- **初态构造与客户端**：只读，无状态型初态需构造；凭据固定 `data`（经 `api_client` 注入）。
- **依赖的测试资产（tests.asset-design 文档）**：本阶段 `tests.asset-design` 文档尚未建立；`api_client` 等夹具契约见方案 §4。

## 3. 输入构造

- **输入与构造**：固定请求（无 body、无 query）：

  ```http
  GET /v1/models/Worker HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Accept: application/json
  ```

  构造点：`model` 路径段固定取 `Worker`（精确大小写，属 7 fixed tier）；**不得**用 `worker`/`WORKER`（属 DP-MODELS-03/04），不得附加尾空格（DP-MODELS-05），不得用不存在的 id（DP-MODELS-06）；凭据固定 `data`；不注入故障；不构造非法输入。**不做归一化尝试**——`Worker` 必须**逐字节**命中。
- **规模 / 时间域**：单次 GET（＋一次清单交叉核对 GET）；无分页/并发；记录 `elapsed` 供报告。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认基线（`pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = api_client.get("/v1/models/Worker")`；记录 status、`Content-Type`、`X-Request-ID`、原始 body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`，且存在 `X-Request-ID` 响应头。
  4. 解析 JSON：断言键集**恰为** `{id,object,created,owned_by,availability,capabilities}`（`Model`，`additionalProperties:false`）。
  5. 断言 `body["id"] == "Worker"`、`body["object"] == "model"`、`body["owned_by"] == "llmtier"`、`isinstance(body["created"], int) and body["created"] > 0`、`body["availability"] ∈ {"available","degraded","unavailable"}`、`body["capabilities"]` 为对象。
  6. （独立交叉核对）再 `GET /v1/models`，取 `data` 中 `id=="Worker"` 的元素，与本步单模型响应逐字段比对 `id`/`object`/`owned_by`/`capabilities`（`created` 因按响应时刻生成可不同，不参与比对）——证明单模型读取与清单成员是同一 Registry 视图（该交叉核对不改变本 case 判定）。

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 确认基线（`pytest_configure` 自动执行） | 就绪检查通过 |
| 2 | `api_client.get("/v1/models/Worker")` | status / headers / body |
| 3 | 断言 200 + `application/json` + `X-Request-ID` | 响应头 |
| 4 | 键集恰 `{id,object,created,owned_by,availability,capabilities}` | 响应体 |
| 5 | `id=="Worker"`、`object=="model"`、`owned_by=="llmtier"`、`created` 正整数、`availability` 枚举、`capabilities` 对象 | 响应体 |
| 6 | 与 `/v1/models` 中 `id=="Worker"` 元素逐字段比对（`created` 除外） | 同一 Registry 视图佐证 |

**重点关注步骤**：① **精确大小写命中**——`Worker` 必须原样返回，不得被小写化/大写化；② **`id` 回显等于请求路径段**，而非某个默认 tier；③ **键集精确性**（`additionalProperties:false`），多/缺键即 FAIL；④ **不得以错误信封冒充 `Model`**；⑤ **`created` 只断言正整数**——实现为 `int(time.time())`，跨请求可不相等，不是持久化时间戳；⑥ **不触上游**；⑦ 交叉核对只用于佐证，不在本 case 断言 `availability` 与上游一致。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = [openapi](../../../../interfaces/openapi/llmtier.openapi.json) `Model` 的 wire 形态（不依赖"返回看起来像 Worker"）。**判据语义以设计验证项 `VRC-INF-001/002` 为唯一权威**。
  - HTTP：`200`；`Content-Type: application/json`；`X-Request-ID` 存在。
  - body 键集恰 `{id,object,created,owned_by,availability,capabilities}`。
  - 值：`id=="Worker"`、`object=="model"`、`owned_by=="llmtier"`、`created` 正整数、`availability` 枚举内、`capabilities` 对象。
  - 无 `{"error":{...}}` 信封。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：上述期望结果与独立 Oracle 全部 match（status + content-type + 键集 + `id=="Worker"` + `object=="model"` + 字段类型/枚举）。
  - **FAIL**：任一断言不符（status 非 200、`id` 回显错、键集不符、字段类型或枚举错）——记 FAIL。
  - **BLOCKED**：测试代码/契约本身问题（fixture 写不出、断言逻辑错、`openapi` 语义不清）——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：就绪前置不满足（m5air 不可达、`/readyz` 非 7 tier、双 OMLX 离线等）——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或不触真实 Registry 却按行为判定——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 case 有实现（方案清单 `RUN`），未执行时记 `NOT_RUN`；不得以未跑冒充 PASS。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：本 case 为只读成功路径；非 200/非法 body 时按 §5 判 FAIL 并保留失败现场（含错误信封）。
- **副作用断言与清理**：**无需 teardown**——纯读 `GET`，不创建/修改 provider/deployment/service-level、不写注入项、不写 usage/账本。退出前确认 `/readyz` 仍显示 7 tier 且无未清空注入项（本 case 不注入）；若被误跑于 B 类临时实例，则按[系统测试方案 §4 共同机制](../../schemes/llmtier-system-test-scheme.md) 整班 `stop()` + `rm -rf` 临时目录。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../../schemes/llmtier-system-test-scheme.md)：保存原始 HTTP status/headers/body、发出命令、exit code、`elapsed`、环境快照（`/healthz`/`/readyz`）、可选交叉核对响应；manifest 与报告落位见 §4.8/§10（本 case `environment:"a"`）；失败现场不截断。
- **依赖**：[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`api_client` fixture（[系统测试方案 §4 共同机制](../../schemes/llmtier-system-test-scheme.md)）；fixed tier `Worker` 已 bootstrap（[`registry.py`](../../../../src/management/registry.py)）；实现 [`src/inference/models.py`](../../../../src/inference/models.py) 与 [`Registry.get_service_level()`](../../../../src/management/registry.py)；`Model` 机器契约（[`interfaces/openapi/llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)）；自动化入口 [`at_dp_models_02.py`](../../../../tests/system/api_test_v03/at_dp_models_02.py)。**不依赖**其它 Case；与 DP-MODELS-01（同一模型在清单中的成员）语义相邻但各自独立执行、互不关闭。

> 实现状态：Implemented（`at_dp_models_02.py` 已断言本 case 契约）；执行状态与 Verdict 只在 Run 报告。
