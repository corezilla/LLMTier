<!-- STD_DOCUMENT_COVER_BEGIN -->
# DP-RESP-22 — 注入上游 503 → provider_unavailable

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `DP-RESP-22` |
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
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/cases/dp-resp-22.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`DP-RESP-22` / 系统设计 §8 Responses 接口 / `VRC-DIAG-004` / recovery / P1（[方案清单 `DP-RESP-22`](../../schemes/llmtier-system-test-scheme.md)）；机制 `T-OBS-INJECT`（[observability 机制](../../../20_system_design/mechanisms/observability.md)）。
- 要测什么（责任展开）：`POST /v1/responses` 注入 `fault_503`：下一次命中 `depl_b` 的推理在 dispatch 上游前被拒，返回 `503 provider_unavailable`（`retryable=true`、`message` 含注入 `error_body`）（**MISSING** 自动化）。先 `PATCH /v1/deployments/{deployment_id}/diagnostics` 写入 `fault_503`；随后命中该 deployment 的 `POST /v1/responses`（`stream=true`）在 dispatch 上游**之前**由 M003 抛出 `ApiError(status=503, code="provider_unavailable", retryable=True)`，入口以**普通 JSON 错误信封**返回（非 `text/event-stream`）。需求 `R-INF-05`；错误目录 `ERR-PROVIDER-UNAVAIL` → wire `code=provider_unavailable`；实现 `src/inference/responses.py` 与 `src/libdiag/injections.py`。
- 明确不测什么 / 失败含义：不测 `fault_502`→`provider_failure`（DP-RESP-11）；不测真实上游 5xx 的归一（DP-RESP-23）；不测 SSE 序列（注入在流开始前抛出）；不测重试/exactly-once；本 case 的 503 由注入产生，**不是"上游真的不可用"**。失败含义＝注入命中→错误传播契约破坏。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `POST /v1/responses`（`data`）与注入写 `PATCH /v1/deployments/depl_b/diagnostics`（`admin`）。

```text
POST  /v1/responses                        Authorization: Bearer dev-data
PATCH /v1/deployments/depl_b/diagnostics   Authorization: Bearer dev-admin
```

- 初态构造（经公开入口）：**环境 B**（临时 LLMTier 实例）。`_baseline_settings`：`prov_b` + `depl_b` + 7 tier，`llmtier_b` probe `depl_b` 为 `healthy`。`prov_b.endpoint` 必须是 LAN IP 上的 fake provider（TS-003）。初始状态 = 1 provider / 1 deployment / 7 tier，且 **`diagnostic_injections` 为空**；7 tier 的 `deployment_ids` 均指向 `depl_b`，故 `model="Senior"` 必然路由到 `depl_b`。
- Fixture / 向量及版本：`llmtier_b`、`admin_client_b`、`api_client_b`；注入 body 与被测请求向量，随 Run manifest 存档。
- 依赖的测试资产（tests.asset-design 文档）：B 类 fixture `llmtier_b` / `admin_client_b` / `api_client_b`；TS-003 LAN fake provider。

## 3. 输入构造

- 逐参数输入构造：先写注入（admin），再发被测请求（data）。注入写：

```json
{"items": [{"type": "fault_503", "config": {"error_body": "injected upstream unavailable"}, "enabled": true}]}
```

被测请求：

```json
{"model": "Senior", "input": [{"role": "user", "content": "Hello"}], "stream": true, "store": false}
```

- 边界/非法取值及理由：`type` 必须为白名单枚举 `fault_503`；`config.error_body` 必须为非空字符串（>512B 静默截断）；`enabled=true` 生效；注入按 `(deployment_id, injection_type)` upsert，仅作用 `depl_b`；只写 `fault_503` 一项，不并发写其它类型（尤其不得残留 `fault_502`，否则前置优先级 `fault_502→fault_503` 会命中 502 臂）。
- 规模 / 时间域：一次注入写 + 一次被测请求；注入在 dispatch 前抛出。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | （fixture 前置）`llmtier_b` 启动并轮询 `/healthz` 200；确认初始 `GET /v1/deployments/depl_b/diagnostics` 为空 | 实例就绪 |
| 2 | `PATCH /v1/deployments/depl_b/diagnostics`（注入 body） | 200；解析 JSON 数组存在 `type=="fault_503"` 且 `enabled` 为真 |
| 3 | `POST /v1/responses`（上表 body，`data`）：注入在 dispatch 前抛出，响应是普通 JSON 错误信封，**不按 SSE 解析** | status |
| 4 | 断言 | `status_code == 503` |
| 5 | `err = resp.json()["error"]` | `code=="provider_unavailable"`、`type=="server_error"`、`retryable is True`、`message` 含 `"injected upstream unavailable"`、`param is None` |
| 6 | （teardown，`finally`）`PATCH .../diagnostics` body `{"items": []}` | 200；再 `GET` 校验无 `enabled=true` 项 |

- 重点关注步骤：① **注入命中证明（cause→effect）**——步骤 2 的 `200 + fault_503 enabled=true` 是因，步骤 4–5 的 `503 + provider_unavailable + message 含注入体` 是果，同 `depl_b` 闭环；② **503 臂锁定**——不得观测到 `fault_502` 的 `502 provider_failure`（若出现说明串了 DP-RESP-11 注入，判 FAIL）；③ **信封 identity**（恰 5 键、无 `category`、`type=server_error`、`retryable=true`）；④ **非 SSE**；⑤ **teardown 完整性**——`finally` 清空并二次校验。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：OpenAPI `ErrorEnvelope`/`ErrorDetail` + 系统设计 §7.8 `ERR-PROVIDER-UNAVAIL`（不依赖实现答案）。**判据语义以设计验证项 `VRC-DIAG-004` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：注入写 `PATCH` → `200`，`InjectionView[]` 含 `{type:"fault_503", enabled:true, deployment_id:"depl_b"}`；被测 HTTP `503`；`Content-Type: application/json`；`{"error":{"message":"injected upstream unavailable","type":"server_error","code":"provider_unavailable","param":null,"retryable":true}}`；teardown：`PATCH {"items":[]}` → 200，随后 `GET` 无启用项。

## 6. 错误路径、副作用与清理

- 错误出口与表现：注入 `fault_503` 命中 → `503 provider_unavailable`（`message` 含注入体），非 SSE。
- 副作用断言与清理：**必须 teardown（`finally`）**——`PATCH /v1/deployments/depl_b/diagnostics {"items":[]}` 清空注入后 `GET` 校验；不修改 `prov_b`/`depl_b`；不删除既有资源。B 类实例按计划整班销毁。清空失败须报错，不得把启用注入留给后续 Case。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/system/api_test_v03/at_dp_resp_22.py`（当前 **MISSING，尚未实现**）。
- 单 Case 执行命令（实现后）：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_resp_22.py -q`。
- 实现状态：Planned（MISSING）；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：注入写 200 且 `fault_503` 生效；被测 `503` + `provider_unavailable` + `type=server_error` + `retryable=true` + `message` 含 `error_body`；teardown 清空。
- FAIL：status 非 503（含 502 `provider_failure`）、`code`/`type`/`retryable`/`message` 错、注入写未生效、teardown 未清空。
- BLOCKED：注入写 API 不可用、注入无法命中。
- SKIP：B 类临时实例不可用、`provider_endpoint_b` 无 LAN IP（TS-003）。
- INVALID：注入未命中却按行为判定、或 `monkeypatch` 端点伪造 503（要求命中证明）。
- NOT_RUN：本 Case **无自动化实现**（MISSING）；未执行记 `NOT_RUN`。

**证据与 Run**：保存注入写/清空（`PATCH` body + `200` + 空数组）、被测请求与原始 503 信封、teardown 二次 `GET`、发出命令、exit code、环境快照（`/healthz` + 注入前/后 `GET .../diagnostics`）；可选 trace（`usage.source=="injected"`）（本 case `environment:"b"`）。

**依赖**：`OBS-DEPL-02`（注入写机制）；B 类 fixture `llmtier_b` / `admin_client_b` / `api_client_b`；实现 `src/libdiag/injections.py`、`src/inference/responses.py`；机制 `T-OBS-INJECT`（[observability 机制](../../../20_system_design/mechanisms/observability.md)）；错误目录 `ERR-PROVIDER-UNAVAIL`（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md) §7.8）。与 DP-RESP-11 互补。
