<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-RESP-023 — 上游非成功 HTTP → provider_error

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-RESP-023` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-RESP-023.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-RESP-023` / 系统设计 §8 Responses 接口 / `VRC-INF-003` / recovery / P1（[方案清单 `ST-RESP-023`](../llmtier-system-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：故障注入（上游非 5xx → provider_error）+ 复位阶梯
- 要测什么（责任展开）：`POST /v1/responses` 上游返回非成功 HTTP（4xx）：沿用非 5xx 状态并归一为 `provider_error`（自动化入口 `at_dp_resp_23.py`；5xx 分支为 `provider_unavailable`，见偏差）。需求 `R-INF-05`；错误目录 `ERR-PROVIDER-FAIL` → wire `code=provider_error`；实现 `src/inference/providers/openai.py`（`except urllib.error.HTTPError as exc:` — `if exc.code >= 500: raise ApiError(503, "provider_unavailable", ..., retryable=True)`；否则 `raise ApiError(exc.code, "provider_error", f"Provider returned HTTP {exc.code}", retryable=exc.code in {408,429})`）。
- 明确不测什么 / 失败含义：不测注入类故障（ST-RESP-011/22，`fault_502`/`fault_503` 是 M006 注入，非真实上游 HTTP）；不测上游不可达/超时（亦归一 `provider_unavailable`）；不测上游契约异常（ST-RESP-025，`provider_contract_error`）；不测答案。失败含义＝真实上游非成功 HTTP 归一契约破坏。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `POST /v1/responses`（`data`）；`prov_b.endpoint` 指向专属 4xx/5xx stub。

```text
POST /v1/responses
Authorization: Bearer dev-data
Content-Type: application/json
Accept: text/event-stream
```

- 初态构造（经公开入口）：**环境 B**（临时 LLMTier 实例）。需一个**专属**上游 stub（扩展 `tests/fixtures/v03_fake_provider.py` 或等价 fixture），使其对 `POST /v1/responses` 返回预置的 **4xx**（如 `422` 或 `404`）且 body 非 SSE。`prov_b.endpoint` 必须是该 stub 的 LAN IP 地址（TS-003）。初始状态 = 1 provider / 1 deployment / 7 tier，`depl_b` 已 probe `healthy`（probe 打 stub 的 `/models`，需返回合法目录）。
- Fixture / 向量及版本：`LLMTierInstance`、`api_client_b`；stub 返回码配置与被测请求向量，随 Run manifest 存档。
- 依赖的测试资产（tests.asset-design 文档）：B 类 fixture `LLMTierInstance` / `api_client_b`；4xx/5xx stub；TS-003 LAN endpoint。

## 3. 输入构造

- 逐参数输入构造：stub 配置为对 `/v1/responses` 返回 `422`（不创建 provider conversation 状态）。被测请求：

```json
{"model": "Senior", "input": [{"role": "user", "content": "hi"}], "stream": true, "store": false}
```

- 边界/非法取值及理由：必须区分"真实上游 4xx"与"注入 4xx"——本 case **不写任何 `diagnostic_injections`**；stub 通过 `prov_b.endpoint` 指向的独立进程返回 4xx；`422` 的 `type` 应为 `request_error`（<500），`retryable` 仅当 `exc.code in {408,429}` 才为真（422 ⇒ false）。可加子测：stub 返回 `429` → status 429 + `provider_error` + `retryable=true`。
- 规模 / 时间域：单次请求 + 可选子测；stub 快速返回。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | （fixture 前置）启动专属 stub 与实例，probe `depl_b` → `healthy`；确认无启用注入 | 实例就绪 |
| 2 | 配置 stub 使其 `/v1/responses` 返回 `422` | stub 返回码 |
| 3 | `POST /v1/responses`（上表 body） | 普通 JSON 错误信封（非 SSE） |
| 4 | 断言 | `status_code == 422`（**沿用**上游非 5xx 状态） |
| 5 | 解析 `error` | `code=="provider_error"`、`type=="request_error"`、`param is None`、`retryable is False`，键集恰 5 键 |
| 6 | 子测（可选）：stub 改返回 `429` | `status==429` + `provider_error` + `retryable is True` |
| 7 | 子测（对照）：stub 改返回 `503` | 归一为 `503 provider_unavailable` + `retryable=true`（证明 5xx 分支：本条为**真实上游** 5xx；ST-RESP-022 是 M006 **注入** 503，两者来源不同） |

- 重点关注步骤：① **4xx 沿用原状态**——非 5xx 的 `exc.code` 作为 HTTP status，`code=provider_error`；② **5xx 分支不同**——真实上游 5xx 归一为 `503 provider_unavailable`（**偏差**：方案标题写"上游 4xx/5xx → provider_error"，而实现 `openai.py` 对 5xx 返回 `provider_unavailable`；以代码为准并登记）；③ **`retryable` 规则**——仅 `{408,429}` 为真；④ **信封 identity**（5 键、无 `category`）；⑤ **无注入**——不得用 `PATCH .../diagnostics` 伪造（注入是 ST-RESP-011/22 的来源）；⑥ **自动化入口**——`at_dp_resp_23.py` 与 4xx/5xx stub（`force-http-*`）已实现。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：OpenAPI `ErrorEnvelope`/`ErrorDetail` + 系统设计 §7.8 `ERR-PROVIDER-FAIL`（不依赖实现答案）。**判据语义以设计验证项 `VRC-INF-003` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：4xx 子测：HTTP `422`（或所配 4xx）；`Content-Type: application/json`；`{"error":{"message":"Provider returned HTTP 422","type":"request_error","code":"provider_error","param":null,"retryable":false}}`；无 SSE。429 子测：`429` + `provider_error` + `retryable=true`。5xx 对照：`503` + `provider_unavailable` + `retryable=true`（与方案标题的偏差按代码登记）。

## 6. 错误路径、副作用与清理

- 错误出口与表现：真实上游 4xx → 沿用状态 + `provider_error`；5xx → `503 provider_unavailable`；均非 SSE。
- 副作用断言与清理：无注入/无持久写；专属 stub 与实例按计划整班销毁。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：[`tests/system/api_test_v03/at_dp_resp_23.py`](../../../../tests/system/api_test_v03/at_dp_resp_23.py)（已实现；依赖 4xx stub）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_resp_23.py -q`。
- 实现状态：Implemented；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：4xx → 沿用状态 + `provider_error` + `type=request_error` + `retryable` 符合 `{408,429}` 规则；无 SSE。
- FAIL：status/code 错（如把 4xx 未保留或写成 `provider_unavailable`）、`retryable` 错、返回 SSE、信封键集错。
- BLOCKED：无法稳定让 stub 返回目标 4xx/5xx、4xx stub 不可实现。
- SKIP：B 类临时实例不可用、无 LAN IP 部署 stub（TS-003）。
- INVALID：以 `127.0.0.1`/mock 冒充真实上游 endpoint、或注入未命中却按行为判定。
- NOT_RUN：本 Case 有实现（`at_dp_resp_23.py`），未执行记 `NOT_RUN`。

**证据与 Run**：保存 stub 配置（返回码）、被测请求与原始错误信封、5xx 对照、发出命令、exit code、环境快照（本 case `environment:"b"`）。

**依赖**：B 类 fixture `LLMTierInstance` / `api_client_b`；4xx/5xx stub（扩展 `tests/fixtures/v03_fake_provider.py`）；TS-003 LAN endpoint；实现 `src/inference/providers/openai.py`；错误目录 `ERR-PROVIDER-FAIL`（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md) §7.8）。与 ST-RESP-022（注入 5xx）/ST-RESP-025（契约错误）区分。
