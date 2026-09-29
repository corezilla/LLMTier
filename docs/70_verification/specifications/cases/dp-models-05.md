<!-- STD_DOCUMENT_COVER_BEGIN -->
# DP-MODELS-05 — URL 编码尾空格不匹配

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `DP-MODELS-05` |
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
| Canonical Path | `docs/70_verification/specifications/cases/dp-models-05.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。方案清单行见[系统测试方案 §3 覆盖分母与 Case 清单](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`DP-MODELS-05` / 系统设计 §8 逻辑模型清单接口（/v1/models） / `VRC-INF-001` / `negative` / `P1`。本文件名 `dp-models-05.md`，与 Case ID 唯一对应。
- 要测什么（责任展开）：`GET /v1/models/Senior%20`（URL 编码尾空格）不匹配任何 tier → HTTP 404 + `error.code=="model_not_found"`。
- 明确不测什么 / 失败含义：**不证明什么**——不证明正向精确返回（DP-MODELS-02）、小写/全大写负向（DP-MODELS-03/04）、其它不存在 id（DP-MODELS-06）；不证明服务端对**合法**含空格模型 id 的支持（无此 tier，本 case 只证明其被拒）；不证明凭据与 LAN trust（AUTH-01/02/06）；**不锁定"404 的具体成因是解码后带空格还是字面 `%20`"**——两者都落在"未命中"这一可观察契约上。**失败含义＝编码/空格边界拒绝契约破坏**。

**目的（被测契约）**：验证 Data Plane `GET /v1/models/{model}` 对**带编码尾空格的路径段**的负向契约。被测端点/规则：`model` 是**精确标识符**，"`Senior `（带尾空格）"不是任何 tier，必须**不命中**并返回 `404 model_not_found`，信封 `{error:{message,type,code,param,retryable}}`（5 键，`type=="request_error"`、`param==null`、`retryable==false`）。实现侧路径来自 `urlparse(self.path).path` 的 `[^/]+` 捕获（[`app.py`](../../../../src/http_api/app.py) 正则 `/v1/models/([^/]+)`），随后交 [`Registry.get_service_level()`](../../../../src/management/registry.py) 的 SQL `WHERE id=?` 精确等值匹配；[`ModelCatalog.get()`](../../../../src/inference/models.py) 将 404 `not_found` 转译为 `model_not_found`。设计验证项 `VRC-INF-001`；机制 `R-INF-04`（清单行）；家族需求链 `LT-FUN-002`、`R-INF-04`/`R-INF-07`、`T-TRUST-ENDPOINTS`、契约 `CT-MODEL-001`（[系统测试方案 §3](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明正向精确返回（DP-MODELS-02）、小写/全大写负向（DP-MODELS-03/04）、其它不存在 id（DP-MODELS-06）；不证明服务端对合法含空格模型 id 的支持；不证明凭据与 LAN trust；**不锁定 404 的具体成因**。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 现有实例，角色 `data`，无副作用；见[系统测试方案 §1 测试边界](../../schemes/llmtier-system-test-scheme.md)）；前置 = 就绪检查（由 `conftest.py::pytest_configure` 自动执行，任一失败 → 整班 BLOCKED/SKIP）。fixture = `api_client`（Data 角色客户端）。初始状态 = 3 provider / 4 deployment / 7 fixed tier；被拒绝的目标是 `Senior`（存在 tier）加尾空格后的形态，**不在** `FIXED_TIERS`（[`constants.py`](../../../../tests/system/api_test_v03/constants.py)）中。
- **被测入口**：

  ```http
  GET /v1/models/Senior%20 HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Accept: application/json
  ```

- **初态构造与客户端**：只读，无状态型初态需构造；凭据固定 `data`（经 `api_client` 注入）。
- **依赖的测试资产（tests.asset-design 文档）**：本阶段 `tests.asset-design` 文档尚未建立；`api_client` 等夹具契约见方案 §4。

## 3. 输入构造

- **输入与构造**：固定请求（无 body、无 query）：

  ```http
  GET /v1/models/Senior%20 HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Accept: application/json
  ```

  构造点：`model` 路径段固定为 `Senior%20`（`%20` 为空格编码；被拒目标 = `Senior` + 尾空格）；**必须**以已编码形式发送，不得让客户端把 `%20` 误还原成裸空格后由 httpx 再编码成同一字节序列（本 case 关注的是该编码路径段不命中）；凭据固定 `data`；不注入故障；不构造非法 JSON/其它错误输入。
- **规模 / 时间域**：单次 GET；无分页/并发；记录 `elapsed` 供报告。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认基线（`pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = api_client.get("/v1/models/Senior%20")`；记录 status、`Content-Type`、`X-Request-ID`、原始 body，以及实际发送的请求目标（含 `%20`）。
  3. 断言 `resp.status_code == 404`（精确 404，非 200/400/500）。
  4. 断言 `content-type` 含 `application/json`，且存在 `X-Request-ID` 响应头。
  5. 解析 JSON：断言顶层键集恰为 `{error}`，`err = body["error"]` 的键集恰为 `{message,type,code,param,retryable}`（5 键，无 `category`）。
  6. 断言 `err["code"] == "model_not_found"`、`err["type"] == "request_error"`、`err["param"] is None`、`err["retryable"] is False`；`err["message"]` 为非空字符串。

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 确认基线（`pytest_configure` 自动执行） | 就绪检查通过 |
| 2 | `api_client.get("/v1/models/Senior%20")` | status / headers / body；请求目标含 `%20` |
| 3 | 断言 status == 404 | HTTP 状态 |
| 4 | 断言 `application/json` + `X-Request-ID` | 响应头 |
| 5 | 顶层键集 `{error}`；error 键集恰 5 键（无 `category`） | 响应体 |
| 6 | `code=="model_not_found"`、`type=="request_error"`、`param is None`、`retryable is False` | 响应体 |

**重点关注步骤**：① **"未命中"是唯一被锁定的可观察契约**——`Senior `（带尾空格）不是 tier，故 404；实现当前**不做** percent-decode（`app.py` 直接取 `urlparse(...).path` 的 `[^/]+`），因此传入 Registry 的是字面 `Senior%20`，与"解码后 `Senior `"同样都**未命中**。本 case 的 Oracle 只管 `status==404 + code==model_not_found`，**不**断言具体成因；若未来实现改为先 `unquote` 再匹配，本 case 仍应 PASS。② **状态精确 404**；③ **错误信封 identity**——恰 5 键（无 `category`），`type=="request_error"`、`retryable=false`、`param=null`；④ **零副作用**——404 必须在 dispatch 前完成，不触上游、不写账本；⑤ **编码保持**——必须确认发送的是 `%20` 形态（请求行/httpx URL 快照）；⑥ **码值精确**——`model_not_found` 而非泛化 `not_found`。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = [openapi](../../../../interfaces/openapi/llmtier.openapi.json) `ModelNotFound`（引用 `ErrorEnvelope`/`ErrorDetail`）+ 系统设计 §7.8 `ERR-MODEL-NOTFOUND`（不依赖"清单看起来没有 `Senior `"）。**判据语义以设计验证项 `VRC-INF-001` 为唯一权威**。
  - HTTP：`404`；`Content-Type: application/json`；`X-Request-ID` 存在。
  - body：`{"error":{"message":<非空字符串>,"type":"request_error","code":"model_not_found","param":null,"retryable":false}}`；`error` 恰 5 键。
  - 无 `Model`/`ModelList` 形态的 200 body。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==404` 且 body 满足上述 `model_not_found` 信封（键集 + `code` + `type` + `param` + `retryable` + message 非空）。
  - **FAIL**：status 非 404（尤其 200）、`code` 非 `model_not_found`、信封键数不符、`type`/`param`/`retryable` 不符——记 FAIL 并给预期 vs 实际、`reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（fixture 写不出、断言逻辑错、编码构造/`openapi` 语义不清）——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：就绪前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或不触真实 Registry 却按行为判定——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 case 有实现（方案清单 `RUN`），未执行时记 `NOT_RUN`；不得以未跑冒充 PASS。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：本 case 的"错误出口"即被拒绝的 404（期望路径）；若返回 200/400 则按 §5 判 FAIL 并保留失败现场（含错误信封与请求目标快照）。
- **副作用断言与清理**：**无需 teardown**——本 case 为被拒绝的只读请求，未产生副作用（无上游调用、无账本义务、无注入）。退出前确认 `/readyz` 仍显示 7 tier 且无未清空注入项（本 case 不注入）；若被误跑于 B 类临时实例，则按[系统测试方案 §4 共同机制](../../schemes/llmtier-system-test-scheme.md) 整班 `stop()` + `rm -rf` 临时目录。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../../schemes/llmtier-system-test-scheme.md)：保存原始 HTTP status/headers/body、**含 `%20` 的请求目标快照**、发出命令、exit code、`elapsed`、环境快照（`/healthz`/`/readyz`）；manifest 与报告落位见 §4.8/§10（本 case `environment:"a"`）；失败现场不截断。
- **依赖**：[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`api_client` fixture（[系统测试方案 §4 共同机制](../../schemes/llmtier-system-test-scheme.md)）；实现 [`src/inference/models.py`](../../../../src/inference/models.py) `ModelCatalog.get()`、[`Registry.get_service_level()`](../../../../src/management/registry.py) 与路径捕获 [`app.py`](../../../../src/http_api/app.py)；`ModelNotFound`/`ErrorDetail` 机器契约（[`interfaces/openapi/llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)）；自动化入口 [`at_dp_models_05.py`](../../../../tests/system/api_test_v03/at_dp_models_05.py)。**不依赖**其它 Case；与 DP-MODELS-03/04/06 都以同一个 404 `model_not_found` 收口，但输入维度不同，各自独立执行、互不关闭。

> 实现状态：Implemented（`at_dp_models_05.py` 已断言本 case 契约）；执行状态与 Verdict 只在 Run 报告。
