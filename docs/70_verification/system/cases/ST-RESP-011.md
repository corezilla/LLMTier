<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-RESP-011 — 注入上游 502 → provider_failure

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-RESP-011` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-RESP-011.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。方案清单行见[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-RESP-011` / 系统设计 §8 Responses 接口（POST /v1/responses） / `VRC-DIAG-004` / `recovery` / `P0`。本文件名 `st-resp-011.md`，与 Case ID 唯一对应。
- **测试方法（§1.5 方法表行）**：故障注入（fault_502）+ 复位阶梯
- 要测什么（责任展开）：`POST /v1/responses` 注入 `fault_502`：下一次命中 `depl_b` 的推理在 dispatch 上游前被拒，返回 `502 provider_failure`（`retryable=true`、`message` 含注入 `error_body`）。
- 明确不测什么 / 失败含义：**不证明什么**——不证明真实上游 5xx 的归一（ST-RESP-023 / `ERR-PROVIDER-FAIL`）与 `fault_503`→`provider_unavailable` 路径（ST-RESP-022 / `ERR-PROVIDER-UNAVAIL`）；不证明 SSE 事件序列/terminal/`[DONE]`（注入在流开始前抛出，响应不是 SSE，见 ST-RESP-001）；不证明重试或 exactly-once；不证明模型答案或上游真实调用——本 case 的 502 由注入产生，**不是"模型失败"**。**失败含义＝注入命中与上游故障传播契约破坏**。

**目的（被测契约）**：验证 Data Plane `POST /v1/responses` 在 **M006 故障注入（`fault_502`）命中**时的**上游故障传播契约**。被测端点/规则：先 `PATCH /v1/deployments/{deployment_id}/diagnostics` 写入 `fault_502`；随后命中该 deployment 的 `POST /v1/responses`（`stream=true`）在 dispatch 上游**之前**由 M003 抛出 `ApiError(status=502, code="provider_failure", retryable=True)`，入口以**普通 JSON 错误信封**返回（不是 `text/event-stream`）。设计验证项 `VRC-DIAG-004`；机制 `T-OBS-INJECT`（见[observability 机制](../../../20_system_design/mechanisms/observability.md)）；错误目录 `ERR-PROVIDER-INJECTED` → wire `code=provider_failure`（系统设计 §7.8，见[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md)）；实现见 `src/inference/responses.py` 的 dispatch 前注入分支与 `src/libdiag/injections.py` 的注入校验/优先级（[系统测试方案 §3](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明真实上游 5xx 的归一（ST-RESP-023）与 `fault_503`→`provider_unavailable` 路径（ST-RESP-022）；不证明 SSE 事件序列/terminal/`[DONE]`（注入在流开始前抛出）；不证明重试或 exactly-once；不证明模型答案或上游真实调用——本 case 的 502 由注入产生，**不是"模型失败"**。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例，见[系统测试方案 §1 测试边界](../llmtier-system-test-scheme.md)）。前置 = 方案 §5 附加（B 类）就绪检查；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier，`llmtier_b` probe `depl_b` 为 `healthy`（否则 BLOCKED/SKIP）。`prov_b.endpoint` 必须是 LAN IP 上的 fake provider（TS-003，见[系统测试方案 §1](../llmtier-system-test-scheme.md)）。fixture = `llmtier_b`、`admin_client_b`（注入写/读）、`api_client_b`（Data Plane），见[系统测试方案 §4 共同机制](../llmtier-system-test-scheme.md)。初始状态 = 1 provider（`prov_b`）/ 1 deployment（`depl_b`）/ 7 fixed tier，且 **`diagnostic_injections` 为空（无任何启用注入）**；7 个 fixed tier 的 `deployment_ids` 均指向 `depl_b`，故 `model="Senior"` 必然路由到 `depl_b`。
- **被测入口**：

  ```http
  PATCH /v1/deployments/depl_b/diagnostics HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```

  ```http
  POST /v1/responses HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-data
  Content-Type: application/json
  Accept: text/event-stream
  ```

- **初态构造（经公开入口）**：经 `llmtier_b` 启动 B 类实例并 probe `depl_b` 为 `healthy`；`diagnostic_injections` 初始为空；注入经公开 `PATCH .../diagnostics` 写入（不直改内部状态）。
- **Fixture / 向量及版本**：`llmtier_b` / `admin_client_b` / `api_client_b` 与 `provider_endpoint_b`（LAN fake provider，TS-003）（[系统测试方案 §4 共同机制](../llmtier-system-test-scheme.md)）。
- **依赖的测试资产（tests.asset-design 文档）**：本阶段 `tests.asset-design` 文档尚未建立；B 类实例与 fake provider 夹具契约见方案 §4，引用其版本而不复制字节。

## 3. 输入构造

- **输入与构造**：先写注入（admin 面），再发被测请求（data 面）。注入写请求：

  ```http
  PATCH /v1/deployments/depl_b/diagnostics HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```

  ```json
  {
    "items": [
      {"type": "fault_502", "config": {"error_body": "injected upstream failure"}, "enabled": true}
    ]
  }
  ```

  被测请求：

  ```json
  {
    "model": "Senior",
    "input": [{"role": "user", "content": "Hello"}],
    "stream": true,
    "store": false
  }
  ```

  构造点：`type` 必须为白名单枚举 `fault_502`（`_TYPES`）；`config.error_body` 必须为非空字符串（>512B 按 UTF-8 静默截断到 512B；空串/非字符串 → 400 `invalid_injection`）；`enabled=true` 才生效；`stream=true` 且 `store=false` 是唯一受理形态（ST-RESP-006/07）；`model="Senior"` 指向唯一 deployment `depl_b`。注入按 `(deployment_id, injection_type)` upsert，仅作用于 `depl_b`；本 case 只写 `fault_502` 一项，不并发写其它类型。
- **规模 / 时间域**：单次注入写 + 单次被测请求；无分页/并发；记录 `elapsed` 供报告。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` 启动并轮询 `/healthz` 200，`_probe_deployment(depl_b)` 断言 `healthy`；确认初始 `GET /v1/deployments/depl_b/diagnostics` 为空。
  2. `PATCH /v1/deployments/depl_b/diagnostics`（注入 body，`admin_client_b`）→ 断言 `status_code == 200`；解析 JSON 数组，断言存在 `type == "fault_502"` 且 `enabled` 为真的项（写入并生效）。
  3. 以 `Bearer dev-data` 建 client（`base_url=llmtier_b.base_url`，`timeout=httpx.Timeout(30.0, connect=5.0)`），`POST /v1/responses`（上表 body）。因注入在 dispatch 之前抛出，响应是**普通 JSON 错误信封**而非 SSE 流；**不按 SSE 解析**。
  4. 断言 `resp.status_code == 502`。
  5. `err = resp.json()["error"]`：断言 `err["code"] == "provider_failure"`、`err["retryable"] is True`、`err["message"]` 含注入的 `error_body`（`"injected upstream failure"`）；并核对 `err["type"] == "server_error"`、`err["param"] is None`。
  6. （teardown，`finally` 内）`PATCH /v1/deployments/depl_b/diagnostics` body `{"items": []}` → 断言 200；再 `GET` 同路径 → 断言 200 且所有项 `enabled` 均为假（数组为空）；确认 `prov_b.endpoint` 未被改动。

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 启动 `llmtier_b`、probe `depl_b=healthy`、确认注入为空 | 实例就绪、初始无注入 |
| 2 | `PATCH .../diagnostics` 写入 `fault_502` | 200 + `fault_502 enabled=true`（因） |
| 3 | `POST /v1/responses`（`model=Senior`） | 普通 JSON 错误信封（非 SSE） |
| 4 | 断言 status == 502 | HTTP 状态 |
| 5 | `code=="provider_failure"`、`retryable is True`、message 含 `error_body`、`type=="server_error"`、`param None` | 响应体（果） |
| 6 | teardown `items:[]` 并二次 `GET` 校验为空 | 清理完整性 |

**重点关注步骤**：① **注入命中证明（cause）**——不是"模型失败"也不是"恰好返回 502"。步骤 2 的 `200 + fault_502 enabled=true` 是**因**，步骤 4–5 的 `502 + provider_failure + message 含注入 error_body` 是**果**；两者同 deployment（`depl_b`）闭环。按[系统测试方案 §4](../llmtier-system-test-scheme.md)，注入 Case 必须**证明命中**（响应状态/错误码，或 trace `source=injected`）——脚本既以"status+code+type+param+retryable+message"证明，**又**显式抓响应 `X-Request-ID` 并查 `GET /v1/trace/{request_id}` 断言 `usage.source=="injected"`（INV-3）。② **502 vs 503 的区分**——本 case 严格锁定 `fault_502` 臂，必须观测到 **502 + `provider_failure`**；若观测到 **503 + `provider_unavailable`**，说明生效的是 `fault_503`（串了 ST-RESP-022 的注入），判 FAIL。注入类型→错误码/状态的映射与前置优先级见方案 §4 与 [observability 机制](../../../20_system_design/mechanisms/observability.md)，本文不重复实现细节。③ **错误信封 identity**——恰 5 键 `{message,type,code,param,retryable}`（无 `category`），`type` 由状态导出（502≥500 ⇒ `server_error`），`retryable=true`；缺键/多键或 `type` 错即 FAIL。④ **非 SSE**——入口在 `create()` 抛 `ApiError` 时返回 `_json(status, envelope)`（`src/http_api/app.py`），不得把响应当 `text/event-stream` 吞掉或解析。⑤ **message 携带注入体**——`"injected upstream failure"` 与写入的 `error_body` 一致，是把响应与注入配置绑定的强证据。⑥ **teardown 完整性**——`finally` 中 `items:[]` 清空并二次 `GET` 校验为空；**绝不残留** `prov_b.endpoint` 被指向死端口（本设计走真实注入 API，不再 monkeypatch endpoint）；清空失败必须报错，不能把启用注入留给同 session 的后续 Case。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = OpenAPI `ErrorEnvelope`/`ErrorDetail` 契约（[`interfaces/openapi/llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)）+ 系统设计 §7.8 `ERR-PROVIDER-INJECTED`（**不依赖实现的"答案内容"**）。**判据语义以设计验证项 `VRC-DIAG-004` 为唯一权威**。
  - 注入写：`PATCH` → `200`，body 为 `InjectionView[]`，含 `{type:"fault_502", enabled:true, deployment_id:"depl_b"}`。
  - 被测响应：HTTP `502`；`Content-Type: application/json`（错误信封，非 SSE）；body `{"error":{"message":"injected upstream failure","type":"server_error","code":"provider_failure","param":null,"retryable":true}}`。
  - teardown：`PATCH {"items":[]}` → `200`；随后 `GET` → `200` 且 `InjectionView[]` 中无 `enabled=true` 项（数组为空）。
  - 可选独立交叉核对（非脚本 oracle 的充分条件）：`GET /v1/trace/{request_id}` 的 `usage.source == "injected"`（机制 INV-3），用于证明账本标注命中。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：注入写 `200` 且 `fault_502` 生效；被测响应 `502` + `error.code=="provider_failure"` + `type=="server_error"` + `retryable is True` + `message` 含 `error_body`；teardown `items:[]` 生效且 `GET` 校验为空。
  - **FAIL**：任一断言不符——status 非 502（含 503 `provider_unavailable`）、`code`/`type`/`retryable`/`message` 错、注入写未生效、或 teardown 未清空（注入已命中但行为不符时判 FAIL）。
  - **BLOCKED**：无法执行/无法判定且可重试——注入写 API 不可用、校验逻辑/断言不可实现、注入无法命中——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类临时实例不可用、`provider_endpoint_b` 无 LAN IP 可用（TS-003）、依赖 fixture 未满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：注入未命中却按行为判定、或以替代路径冒充真实路径——例如用 `127.0.0.1`/mock 当上游 endpoint、或 `monkeypatch` 把 `prov_b.endpoint` 指向死端口伪造 502，而非走真实 `PATCH` 注入——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)（方案 §4 要求命中证明）。
  - **NOT_RUN**：本 Case 有实现（方案清单 `RUN`），未执行时记 `NOT_RUN`；不得以未跑冒充 PASS。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：注入写失败（非 200/未生效）→ BLOCKED；被测响应非 502 / 错误码不符 / message 不含注入体 → FAIL；teardown 未清空 → FAIL。全部保留原始请求/响应与失败现场。
- **副作用断言与清理**：**必须 teardown（`finally` 强制）**——`PATCH /v1/deployments/depl_b/diagnostics` body `{"items":[]}` 清空本 deployment 的全部注入，随后 `GET` 校验 `InjectionView[]` 无启用项；不修改 `prov_b`/`depl_b` 配置，**不重指 `prov_b.endpoint`**（本 case 只写注入，provider endpoint 始终指向 LAN fake provider）；不删除任何既有资源或用户 usage。B 类实例按方案 §4 整班销毁。离开前确认无未清空的注入项；若清空失败，保留证据并判 FAIL，不得把启用注入留给后续 Case。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-system-test-scheme.md)：保存注入写请求/响应（`PATCH` body + `200` + `InjectionView[]`）、被测请求与原始响应（HTTP status/headers/body 错误信封，脱敏后）、teardown 的 `PATCH items:[]` 与随后 `GET` 空数组、`elapsed`、发出命令、exit code、环境快照（`/healthz` + 注入前/后 `GET /deployments/depl_b/diagnostics`）；可选 trace 证据（`GET /v1/trace/{request_id}` 的 `usage.source=injected`）。注意：现有 [`at_dp_resp_11.py`](../../../../tests/system/api_test_v03/at_dp_resp_11.py) 未自建 artifact 目录/manifest，须由 runner/report 层按 §4.8 补齐后方可判本 Case PASS；manifest 与报告落位见 §4.8/§10（本 case `environment:"b"`）；失败现场不截断。
- **依赖**：`ST-OBSDEPL-002`（`PATCH /v1/deployments/{id}/diagnostics` 写入注入，本 case 的注入写即其机制）；B 类 fixture `llmtier_b` / `admin_client_b` / `api_client_b` 与 `provider_endpoint_b`（LAN fake provider，TS-003）（[系统测试方案 §4 共同机制](../llmtier-system-test-scheme.md)）；自动化入口 [`at_dp_resp_11.py`](../../../../tests/system/api_test_v03/at_dp_resp_11.py)；错误目录 `ERR-PROVIDER-INJECTED`（系统设计 §7.8）与实现 `src/libdiag/injections.py` / `src/inference/responses.py`；机制 `T-OBS-INJECT`（[observability 机制](../../../20_system_design/mechanisms/observability.md)）。**不依赖**其它 Case；与 ST-RESP-022（`fault_503`→`provider_unavailable`）互补但各自独立执行，与 ST-RESP-023（真实上游非成功 HTTP）区分注入/真实两类来源。

> 实现状态：Implemented（`at_dp_resp_11.py` 已实现注入写与断言，且已含 `finally` teardown）；执行状态与 Verdict 只在 Run 报告。
