<!-- STD_DOCUMENT_COVER_BEGIN -->
# DP-RESP-25 — 上游契约错误

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `DP-RESP-25` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-09-30` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/cases/dp-resp-25.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`DP-RESP-25` / 系统设计 §8 Responses 接口 / `VRC-INF-001` / recovery / P1（[方案清单 `DP-RESP-25`](../../schemes/llmtier-system-test-scheme.md)）。
- 要测什么（责任展开）：`POST /v1/responses` 上游响应无法归一：`502 provider_contract_error`（**MISSING** 自动化）。无法从上游响应提取合法 terminal 时，适配层以 `502 provider_contract_error` 拒绝。需求 `R-INF-05`；错误目录 `ERR-PROVIDER-CONTRACT` → wire `code=provider_contract_error`；实现 `src/inference/providers/openai.py`（非 `text/event-stream` → "Provider did not return Responses SSE"；多个 terminal → "more than one terminal"；无合法 terminal → "no valid terminal response"；`status` 与 terminal 类型不一致 → "terminal event and response status disagree"）。
- 明确不测什么 / 失败含义：不测上游非成功 HTTP（DP-RESP-23）；不测真实 5xx/不可达（`provider_unavailable`）；不测 SSE `malformed_event` 注入路径；不测答案。失败含义＝上游响应契约归一破坏（把非法上游响应当成功流出）。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `POST /v1/responses`（`data`）；`prov_b.endpoint` 指向专属违规 stub。

```text
POST /v1/responses
Authorization: Bearer dev-data
Content-Type: application/json
Accept: text/event-stream
```

- 初态构造（经公开入口）：**环境 B**（临时 LLMTier 实例）。需一个**专属**上游 stub（扩展 `tests/fixtures/v03_fake_provider.py` 或等价 fixture），对 `POST /v1/responses` 返回**违反契约**的响应之一。`prov_b.endpoint` 必须是该 stub 的 LAN IP 地址（TS-003）。`depl_b` 已 probe `healthy`（probe 打 `/models`，需返回合法目录）。
- Fixture / 向量及版本：`LLMTierInstance`、`api_client_b`；四类违规 stub 配置，随 Run manifest 存档。
- 依赖的测试资产（tests.asset-design 文档）：B 类 fixture `LLMTierInstance` / `api_client_b`；违规 stub；TS-003 LAN endpoint。

## 3. 输入构造

- 逐参数输入构造：被测请求（stub 需被配置为下述任一种契约违规）：

```json
{"model": "Senior", "input": [{"role": "user", "content": "hi"}], "stream": true, "store": false}
```

- 边界/非法取值及理由：契约违规构造（各子测，逐一独立）：① 上游 `Content-Type: application/json`（非 SSE）；② SSE 含**两个** terminal（`response.completed` ×2）；③ SSE **无任何** terminal（只有 `response.created`）；④ terminal 事件类型为 `response.completed` 但 `response.status=="failed"`（类型与状态不一致）。
- 规模 / 时间域：4 个子测各一次请求；stub 快速返回。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | （fixture 前置）启动专属 stub 与实例，probe `depl_b` → `healthy`；确认无启用注入 | 实例就绪 |
| 2 | 对每个子测配置 stub 使其返回对应契约违规响应 | stub 违规形态 |
| 3 | `POST /v1/responses`（上表 body） | 普通 JSON 错误信封（非 SSE） |
| 4 | 断言 `status_code == 502`；解析 `error` | `code=="provider_contract_error"`、`type=="server_error"`、`retryable is False`、`param is None`，键集恰 5 键 |
| 5 | 断言 `message` 与子测语义一致 | 非 SSE / 多 terminal / 无 terminal / status 不一致 |

- 重点关注步骤：① **契约归一在适配层完成**——不把非法上游响应当成功流出给客户端；② **502 而非 503**——契约错误是 `provider_contract_error`，与 `provider_unavailable`（5xx/不可达）区分；③ **`retryable=false`**（实现默认）；④ **信封 identity**（5 键、`type=server_error`）；⑤ **四个子测各自独立**，不得以一个子测的 PASS 覆盖其它；⑥ **MISSING**——自动化入口为 `MISSING`，须先实现 `at_dp_resp_25.py` 与违规 stub。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：OpenAPI `ErrorEnvelope`/`ErrorDetail` + 系统设计 §7.8 `ERR-PROVIDER-CONTRACT`（不依赖实现答案）。**判据语义以设计验证项 `VRC-INF-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：HTTP `502`；`Content-Type: application/json`；`error.code=="provider_contract_error"`、`type=="server_error"`、`param=null`、`retryable=false`；无 SSE 帧/`[DONE]`；`message` 反映具体违规（非 SSE / 多 terminal / 无 terminal / status 不一致）。

## 6. 错误路径、副作用与清理

- 错误出口与表现：上游契约违规 → `502 provider_contract_error`，非 SSE，绝不流出为成功。
- 副作用断言与清理：无注入/无持久写；专属 stub 与实例按计划整班销毁。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/system/api_test_v03/at_dp_resp_25.py`（当前 **MISSING，尚未实现**；依赖违规 stub）。
- 单 Case 执行命令（实现后）：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_resp_25.py -q`。
- 实现状态：Planned（MISSING）；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：每个子测均 `502` + `provider_contract_error` + `type=server_error` + `retryable=false` + 非 SSE，且 `message` 与违规对应。
- FAIL：status/code 错、把非法上游响应当成功、信封键集错、retryable 错。
- BLOCKED：无法稳定让 stub 产出四类违规之一。
- SKIP：B 类临时实例不可用、无 LAN IP 部署 stub（TS-003）。
- INVALID：以 `127.0.0.1`/mock 冒充真实上游 endpoint。
- NOT_RUN：本 Case **无自动化实现**（MISSING）；未执行记 `NOT_RUN`。

**证据与 Run**：保存 stub 配置（违规形态）、被测请求与原始 502 信封、四个子测结果、发出命令、exit code、环境快照（本 case `environment:"b"`）。

**依赖**：B 类 fixture `LLMTierInstance` / `api_client_b`；违规 stub（扩展 `tests/fixtures/v03_fake_provider.py`）；TS-003 LAN endpoint；实现 `src/inference/providers/openai.py`（`complete` 的契约归一）；错误目录 `ERR-PROVIDER-CONTRACT`（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md) §7.8）。与 DP-RESP-23（非成功 HTTP）区分。
