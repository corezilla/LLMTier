<!-- STD_DOCUMENT_COVER_BEGIN -->
# DP-RESP-01 — 流式成功 + 事件序列

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `DP-RESP-01` |
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
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/cases/dp-resp-01.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。方案清单行见[系统测试方案 §3 覆盖分母与 Case 清单](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`DP-RESP-01` / 系统设计 §8 Responses 接口（POST /v1/responses） / `VRC-INF-001` / `normal` / `P0`。本文件名 `dp-resp-01.md`，与 Case ID 唯一对应。
- 要测什么（责任展开）：`POST /v1/responses` 流式成功：SSE 事件序列有序、恰好一个 terminal、`[DONE]` 收尾、usage 非空。
- 明确不测什么 / 失败含义：**不证明什么**——不证明上游模型答案正确性或文本内容（只断言结构/事件序列），不证明 `stream_terminate`/`malformed_event`/客户端断开等异常路径（见 DP-RESP-10/11/21），不证明 `store=true`/`stream=false` 等被拒形态（DP-RESP-02/06/07），不发布时延 SLO（只记录 `elapsed`）。**失败含义＝流式成功契约破坏**。

**目的（被测契约）**：验证 Data Plane `POST /v1/responses`（`stream=true`）的 **SSE 成功路径契约**。被测端点/规则：`POST /v1/responses`，事件序列 `response.created → response.output_item.added → response.output_text.delta×N → response.output_item.done → response.completed`（或 `response.incomplete`/`response.failed`）`→ data: [DONE]`；恰好一个终态事件，`sequence_number` 自 0 严格递增，`response.completed.response.usage.{input_tokens,output_tokens,total_tokens}` 非 null。设计验证项 `VRC-INF-001`；机制 `T-STREAM`（见 [inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；响应头 `Content-Type: text/event-stream`（[系统测试方案 §3](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明上游模型答案正确性或文本内容（只断言结构/事件序列），不证明异常路径（DP-RESP-10/11/21），不证明被拒形态（DP-RESP-02/06/07），不发布时延 SLO。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 现有实例，角色 `data`，无状态；见[系统测试方案 §1 测试边界](../../schemes/llmtier-system-test-scheme.md)）。前置 = 就绪检查（由 `conftest.py::pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP）。fixture = `api_client`（Data 角色客户端）。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier。请求不指定路由（三选一调度），只断言最终 200 + SSE 合法。
- **被测入口**：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Content-Type: application/json
  Accept: text/event-stream
  ```

- **初态构造与客户端**：只读无状态；凭据固定 `data`（经 `api_client` 注入）；固定 prompt 见 [系统测试方案 §4 共同机制](../../schemes/llmtier-system-test-scheme.md)。
- **依赖的测试资产（tests.asset-design 文档）**：本阶段 `tests.asset-design` 文档尚未建立；`api_client` 等夹具契约见方案 §4。

## 3. 输入构造

- **输入与构造**：固定请求（固定 prompt）：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Content-Type: application/json
  Accept: text/event-stream
  ```

  ```json
  {
    "model": "Worker",
    "input": [{"role": "user", "content": "Hello"}],
    "stream": true,
    "store": false,
    "max_output_tokens": 50
  }
  ```

  构造点：`model` 必须为 responses-capable fixed tier（此处 `Worker`）；`stream=true` 是唯一受理形态（DP-RESP-06）；`store=false` 避免落库副作用；`max_output_tokens` 取小值 50 以限制流长、不触发 DP-RESP-10 的截断断言。不注入故障；不构造非法输入。
- **规模 / 时间域**：单个 SSE 流（`max_output_tokens=50`）；无分页/并发；记录 `elapsed` 供报告，不发布时延 SLO。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `POST /v1/responses`（上表 body），以流式方式读取：`resp = api_client.stream("POST", "/v1/responses", json=...)`；断言 `resp.status_code == 200` 且 `content-type` 含 `text/event-stream`；并断言 `GET /healthz`/`GET /readyz`、双 OMLX、`provider_omlx_m5mac` secret 五项前置全部通过（引用就绪检查，不重复其定义）。
  3. 逐帧解析 `text/event-stream`：按空行分帧，取 `event:` 名与 `data:` JSON；`data: [DONE]` 不计为事件但必须出现。
  4. 校验事件名集合与顺序（子序列关系）：`response.created` 在首位；其后出现 `response.output_item.added`、≥1 个 `response.output_text.delta`、`response.output_item.done`；`response.completed` 为唯一 terminal 且各帧 `sequence_number` 自 0 严格递增。注意：本版本**不存在**独立的文本完成事件（`src/http_api/sse.py` 只发 `output_item.done` 与终态事件），不得把它加入期望序列。
  5. 从 `response.completed` 事件读取 `response.usage`，断言 `input_tokens`/`output_tokens`/`total_tokens` 非 null。
  6. 读取直到流关闭，断言出现 `data: [DONE]` 终止标记。

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 确认基线（`pytest_configure` 自动执行） | 就绪检查通过 |
| 2 | 流式 `POST /v1/responses` | 200 + `text/event-stream` |
| 3 | 逐帧解析 SSE（`[DONE]` 单独识别） | 事件名 / `data` JSON |
| 4 | 校验事件集合/顺序与唯一 terminal、`sequence_number` 递增 | 事件序列 |
| 5 | 读 `response.completed.response.usage` | `input/output/total_tokens` 非 null |
| 6 | 读到流关闭 | `data: [DONE]` 收尾 |

**重点关注步骤**：① **terminal 唯一性**——不是"出现 `response.completed`"而是"恰好一个终态事件（`response.completed`|`response.incomplete`|`response.failed`）"，重复/缺失即 FAIL；② **`[DONE]` 哨兵**——必须位于 terminal 之后，是独立于 JSON 事件的收尾；③ **事件 identity 与顺序**——`delta` 至少 1 个且累积文本非空；④ **`sequence_number` 严格递增**（不允许相等/回退）；⑤ **`Content-Type`** 必须为 `text/event-stream`，防止把错误信封当成功流吞掉；⑥ **不依赖答案文本**——不对生成内容做语义断言。注意：现有 [`at_dp_resp_01.py`](../../../../tests/system/api_test_v03/at_dp_resp_01.py) **已断言** `[DONE]`（约第 76 行 `assert saw_done, ...`）**且已断言"恰好一个 terminal"**（第 87-89 行 `assert len(terminal_events) == 1`，terminal 为 `{response.completed, response.incomplete, response.failed}`），并断言 `[DONE]` 收尾与 `response.completed` 为唯一终态；[`tools/inference_smoke.py`](../../../../tools/inference_smoke.py) 的 `sse_events()` 仅作 smoke 级交叉核对，不替代断言。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = 标准 Responses SSE wire 形态（不依赖实现的答案内容）。**判据语义以设计验证项 `VRC-INF-001` 为唯一权威**。
  - HTTP：`200`；响应头 `Content-Type: text/event-stream`。
  - 事件序列（有序）：`response.created` 首帧；含 `response.output_item.added`、`response.output_text.delta`（≥1，累积文本非空）、`response.output_item.done`；终态事件恰好 1 个且为 `response.completed`（`status="completed"`）；最后一帧为 `data: [DONE]`。
  - 帧内：所有含 `sequence_number` 的事件从 0 起严格递增。
  - `response.completed.response.usage`：`input_tokens`、`output_tokens`、`total_tokens` 均非 null。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：上述期望结果与独立 Oracle 全部 match（status + content-type + 事件 identity/顺序 + terminal 唯一 + `[DONE]` + sequence 递增 + usage 非空）。
  - **FAIL**：任一断言不符（status/字段错、SSE 序列断裂、terminal 缺失或重复、`[DONE]` 缺失、sequence 非递增）。
  - **BLOCKED**：测试代码/契约本身问题（如解析器逻辑错、断言不可实现）——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：就绪前置不满足（如上游 OMLX 离线、m5air 不可达）——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或注入未命中却按行为判定——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（方案清单 `RUN`），未执行时记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：本 case 为成功路径；SSE 序列断裂、terminal 缺失/重复、`[DONE]` 缺失按 §5 判 FAIL 并保留原始逐帧现场。异常路径（断开/注入/截断）见 DP-RESP-10/11/21。
- **副作用断言与清理**：**无需 teardown**——`store=false`、环境 A 只读/无状态，不创建/修改 provider/deployment/service-level，不写注入项，不删除任何既有资源或用户 usage。退出前确认无未清空的注入项（本 case 不注入）、`/readyz` 仍显示 7 tier；若被误跑于 B 类临时实例，则按[系统测试方案 §4 共同机制](../../schemes/llmtier-system-test-scheme.md) 整班 `stop()` + `rm -rf` 临时目录。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../../schemes/llmtier-system-test-scheme.md)：保存原始 SSE 逐帧、HTTP status/headers、发出命令、exit code、`elapsed`、环境快照（`/healthz`/`/readyz`）；manifest 与报告落位见 §4.8/§10（本 case `environment:"a"`）；失败现场不截断。
- **依赖**：[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查（m5air `/healthz`、`/readyz` 7 tier、双 OMLX、`provider_omlx_m5mac` secret）；`api_client` fixture（[系统测试方案 §4 共同机制](../../schemes/llmtier-system-test-scheme.md)）；responses-capable 上游 tier `Worker`；自动化入口 [`at_dp_resp_01.py`](../../../../tests/system/api_test_v03/at_dp_resp_01.py)（case 级）与 [`tools/inference_smoke.py`](../../../../tools/inference_smoke.py)（smoke 级交叉核对，不替代断言）。**不依赖**其它 Case；与 DP-USAGE-02（成功后可见记录）共享同一成功请求语义，但各自独立执行。

> 实现状态：Implemented（`at_dp_resp_01.py` 已断言本 case 契约）；执行状态与 Verdict 只在 Run 报告。
