<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-resp-027 — 畸形事件注入 malformed_event

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-resp-027` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-10-01` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/st-resp-027.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-resp-027` / 系统设计 §8 Responses 接口（POST /v1/responses） / `VRC-DIAG-004` / recovery / P1（[方案清单 `ST-resp-027`](../llmtier-system-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：故障注入（malformed_event 畸形事件）+ 复位阶梯

- 要测什么（责任展开）：注入 `malformed_event` 后，`POST /v1/responses`（stream=true）的 SSE 流在达到 `malformed_after_events` 个事件后**追加一个畸形帧**（按 `malformed_event_type` 为 `invalid_json` 或 `unknown_event_type`）随后结束，客户端解析该帧会失败。需求 `R-OBS-01`；机制 `T-OBS-INJECT`；实现 `src/libdiag/stream.py`（`_MALFORMED_FRAME` 与 `count >= malformed_after_events → yield _MALFORMED_FRAME; return`）与 `src/libdiag/injections.py`（`malformed_event_type ∈ {invalid_json, unknown_event_type}`）。

- 明确不测什么 / 失败含义：不测 `stream_terminate`（ST-resp-026）；不测前置阶段注入（ST-resp-011/22/20）；不测正常流事件序列（ST-resp-001）；不测注入配置读写校验（ST-obsdepl-004）。失败含义＝畸形事件注入未生效或帧形态错误。

**目的（被测契约）**：验证 **SSE 流阶段的畸形事件注入**（`malformed_event`）行为。被测端点/规则：先 `PATCH /v1/deployments/{deployment_id}/diagnostics` 写入 `malformed_event`；随后 `POST /v1/responses`（stream=true）的响应经 [`stream.py::stream_wrapper`](../../../../src/libdiag/stream.py) 包裹，在达到 `malformed_after_events` 后 `yield _MALFORMED_FRAME` 并 `return`。设计验证项 `VRC-DIAG-004`；机制 `T-OBS-INJECT`。**不证明什么**：不测 `stream_terminate`/前置注入/正常序列/配置校验。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例）。前置 = 方案 §5 附加（B 类）就绪检查；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier，`llmtier_b` probe `depl_b` 为 `healthy`。`prov_b.endpoint` 必须是 LAN IP 上的 fake provider（TS-003）。fixture = `llmtier_b`、`admin_client_b`、`api_client_b`。初始状态 = `diagnostic_injections` 为空。
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

## 3. 输入构造

- **输入与构造**：先写注入（admin 面），再发被测请求（data 面）。
  注入写：
  ```json
  {"items": [{"type": "malformed_event", "config": {"malformed_after_events": 1, "malformed_event_type": "invalid_json"}, "enabled": true}]}
  ```
  被测请求：
  ```json
  {"model": "Senior", "input": [{"role": "user", "content": "Hello"}], "stream": true, "store": false}
  ```
- **边界/非法取值及理由**：`malformed_after_events` 范围 `[0,10000]`（0 表示首个事件后即注入）；`malformed_event_type ∈ {invalid_json, unknown_event_type}`；`enabled=true` 才生效。子测：`invalid_json` 与 `unknown_event_type` 各一次。
- **规模 / 时间域**：每个子测一次注入写 + 一次被测请求。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | （fixture 前置）启动 `llmtier_b`、probe `depl_b=healthy`、确认注入为空 | 实例就绪 |
| 2 | `PATCH .../diagnostics` 写入 `malformed_event`（`invalid_json`） | 200 + enabled=true（因） |
| 3 | `POST /v1/responses`（stream=true） | SSE 流 |
| 4 | 原始字节流解析 | 在正常事件后出现**畸形帧**（`_MALFORMED_FRAME`：`event: response.malformed` + 非法 JSON `data:`）；流随后结束 |
| 5 | 对子测 `unknown_event_type` 重复 2–4 | 帧类型反映 `unknown_event_type` |
| 6 | （teardown，`finally`）`PATCH .../diagnostics` body `{"items": []}` 并二次 `GET` | 清空校验 |

- **重点关注步骤**：① **注入命中证明**——步骤 2 是因，步骤 4 的畸形帧是果，同 deployment 闭环；② **帧形态**——`invalid_json` 子测的帧 `data:` 为非法 JSON（按原始字节断言，不做 SSE 解析吞掉）；`unknown_event_type` 子测的帧事件类型不在契约白名单；③ **不是截断**——本 case 追加畸形帧后结束，与 `stream_terminate`（ST-resp-026，无追加帧）区分；④ **客户端解析失败面**——这正是 VRC-DIAG-004 声明"流截断/畸形"的消费者可观察面；⑤ **teardown 完整性**。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **独立 Oracle 来源与推导**：OpenAPI Responses SSE 事件契约 + 机制 `observability` §14.4（`malformed_event`）+ [`stream.py`](../../../../src/libdiag/stream.py) 的 `_MALFORMED_FRAME` 定义。
  - 注入写：`PATCH` → `200`，`InjectionView[]` 含 `{type:"malformed_event", enabled:true}`。
  - 被测流：`200` + `text/event-stream`；在 `malformed_after_events` 后出现畸形帧（`invalid_json`：非法 JSON `data:`；`unknown_event_type`：未知事件类型）；流随后结束。
  - teardown：`PATCH {"items":[]}` → `200`；`GET` 校验为空。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：注入写 200 且生效；流出现与子测语义一致的畸形帧；teardown 生效。
  - **FAIL**：无畸形帧、帧形态与子测不符、或把畸形帧当合法事件；或 teardown 未清空。
  - **BLOCKED**：注入写 API 不可用或注入无法命中。
  - **SKIP**：B 类临时实例不可用、附加前置不满足。
  - **INVALID**：注入未命中却按行为判定，或以 mock/替代路径冒充。
  - **NOT_RUN**：有实现但本轮未执行。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：无畸形帧/帧形态错 → FAIL；注入写失败 → BLOCKED。保留原始 SSE 字节流与失败现场。
- **副作用断言与清理**：**必须 teardown（`finally` 强制）**——`PATCH /v1/deployments/depl_b/diagnostics` body `{"items":[]}` 清空，随后 `GET` 校验无启用项；不修改 `prov_b`/`depl_b` 配置。B 类实例按方案 §4 整班销毁。清空失败必须报错。

## 7. 自动化位置与状态

- **测试文件 / 测试函数**：[`tests/system/api_test_v03/at_dp_resp_27.py`](../../../../tests/system/api_test_v03/at_dp_resp_27.py)（已实现）。
- **单 Case 执行命令**：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_resp_27.py -q`。
- **实现状态**：Implemented；执行与 Verdict 归 Run 报告。

**证据与 Run**：保存注入写请求/响应、被测 SSE 原始字节流（含畸形帧）、teardown 的 `PATCH items:[]` 与随后 `GET`、发出命令、exit code、`elapsed`、环境快照（本 case `environment:"b"`）。

**依赖**：B 类 fixture `llmtier_b` / `admin_client_b` / `api_client_b`；`ST-obsdepl-002`（注入写）；实现 `src/libdiag/stream.py`、`src/libdiag/injections.py`；机制 `T-OBS-INJECT`。**不依赖**其它 Case；与 ST-resp-026 互补。

