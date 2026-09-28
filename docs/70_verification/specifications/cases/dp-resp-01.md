# DP-RESP-01 — 流式成功 + 事件序列

- **Case ID**：`DP-RESP-01`
- **标题**：`POST /v1/responses` 流式成功：SSE 事件序列有序、恰好一个 terminal、`[DONE]` 收尾、usage 非空。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses`（`stream=true`）的 **SSE 成功路径契约**。被测端点/规则：`POST /v1/responses`，事件序列 `response.created → response.output_item.added → response.output_text.delta×N → response.output_text.done → response.output_item.done → response.completed → [DONE]`；恰好一个终态事件，`sequence_number` 自 0 严格递增，`response.completed.response.usage.{input_tokens,output_tokens,total_tokens}` 非 null。设计验证项 `VRC-INF-001`；机制 `T-STREAM`（见[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；响应头 `Content-Type: text/event-stream`。**不证明什么**：不证明上游模型答案正确性或文本内容（只断言结构/事件序列/可复现字符串），不证明 `stream_terminate`/`malformed_event`/客户端断开等异常路径（见 DP-RESP-10/11/21），不证明 `store=true`/`stream=false` 等被拒形态（DP-RESP-02/06/07），不发布时延 SLO（只记录 `elapsed`）。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，角色 `data`，无状态；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 5 项就绪检查（m5air `/healthz`、`/readyz` 含 7 tier、m5air OMLX `192.168.1.9:9000`、m5mac OMLX `192.168.1.8:9000`、`provider_omlx_m5mac.secret_ref` 为 `file:`）；任一失败 → 整班 BLOCKED/SKIP，不得改用模拟路径。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`api_client`（`httpx.Client`，`Authorization: Bearer dev-data`）。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier。请求不指定路由（三选一调度），只断言最终 200 + SSE 合法。
- **输入与构造**：固定请求（固定 prompt，见[测试设计 §4.4](../llmtier-api-test-specification.md) 与 §10 固定输入要求）：

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

  边界/构造点：`model` 必须为 responses-capable fixed tier（此处 `Worker`）；`stream=true` 是唯一受理形态（DP-RESP-06）；`store=false` 避免落库副作用；`max_output_tokens` 取小值 50 以限制流长、不触发 DP-RESP-10 的截断断言。不注入故障；不构造非法输入。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `POST /v1/responses`（上表 body），以流式方式读取：`resp = api_client.stream("POST", "/v1/responses", json=...)`；断言 `resp.status_code == 200` 且 `content-type` 含 `text/event-stream`。
  3. 逐帧解析 `text/event-stream`：按空行分帧，取 `event:` 名与 `data:` JSON；`data: [DONE]` 不计为事件但必须出现（见[测试设计 §4.5](../llmtier-api-test-specification.md)）。
  4. 校验事件名集合与顺序（子序列关系）：`response.created` 在首位；其后出现 `response.output_item.added`、≥1 个 `response.output_text.delta`、`response.output_text.done`、`response.output_item.done`；`response.completed` 为唯一 terminal 且各帧 `sequence_number` 自 0 严格递增。
  5. 从 `response.completed` 事件读取 `response.usage`，断言 `input_tokens`/`output_tokens`/`total_tokens` 非 null。
  6. 读取直到流关闭，断言出现 `data: [DONE]` 终止标记。
- **重点关注步骤**：① **terminal 唯一性**——不是"出现 `response.completed`"而是"恰好一个终态事件（`response.completed`|`response.incomplete`|`response.failed`）"，重复/缺失即 FAIL；② **`[DONE]` 哨兵**——必须位于 terminal 之后，是独立于 JSON 事件的收尾；③ **事件 identity 与顺序**——`delta` 至少 1 个且累积文本非空；④ **`sequence_number` 严格递增**（不允许相等/回退）；⑤ **`Content-Type`** 必须为 `text/event-stream`，防止把错误信封当成功流吞掉；⑥ **不依赖答案文本**——不对生成内容做语义断言。注意：现有 [`at_dp_resp_01.py`](../../../../tests/system/api_test_v03/at_dp_resp_01.py) 尚未断言 `[DONE]`（文件末尾注释"这里不强求"），而 [`tools/inference_smoke.py`](../../../../tools/inference_smoke.py) 的 `sse_events()` 已断言 `[DONE]`；按本设计，case 级入口须补齐 `[DONE]` 断言后方可判本 case PASS。
- **期望结果与独立 Oracle**：独立 Oracle = 标准 Responses SSE wire 形态（不依赖实现的答案内容）。
  - HTTP：`200`；响应头 `Content-Type: text/event-stream`。
  - 事件序列（有序）：`response.created` 首帧；含 `response.output_item.added`、`response.output_text.delta`（≥1，累积文本非空）、`response.output_text.done`、`response.output_item.done`；终态事件恰好 1 个且为 `response.completed`（`status="completed"`）；最后一帧为 `data: [DONE]`。
  - 帧内：所有含 `sequence_number` 的事件从 0 起严格递增。
  - `response.completed.response.usage`：`input_tokens`、`output_tokens`、`total_tokens` 均非 null。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：上述期望结果与独立 Oracle 全部 match（status + content-type + 事件 identity/顺序 + terminal 唯一 + `[DONE]` + sequence 递增 + usage 非空）。
  - **FAIL**：任一断言不符（status/字段错、SSE 序列断裂、terminal 缺失或重复、`[DONE]` 缺失、sequence 非递增）。
  - **BLOCKED**：测试代码/契约本身问题（如解析器逻辑错、断言不可实现）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（如上游 OMLX 离线、m5air 不可达）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或注入未命中却按行为判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
- **证据与 Run**：保存原始 SSE 逐帧、HTTP status/headers、发出命令、exit code、`elapsed`、环境快照（`/healthz`/`/readyz`）。Run ID = `<date>/A-api`（如 `2026-09-28/A-api`），落位 `tests/system/reports/<date>/`，失败现场不截断。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：**无需 teardown**——`store=false`、环境 A 只读/无状态，不创建/修改 provider/deployment/service-level，不写注入项，不删除任何既有资源或用户 usage。退出前确认无未清空的注入项（本 case 不注入）、`/readyz` 仍显示 7 tier；若被误跑于 B 类临时实例，则按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf` 临时目录。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查（m5air `/healthz`、`/readyz` 7 tier、双 OMLX、`provider_omlx_m5mac` secret）；`api_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；responses-capable 上游 tier `Worker`；自动化入口 [`at_dp_resp_01.py`](../../../../tests/system/api_test_v03/at_dp_resp_01.py)（case 级）与 [`tools/inference_smoke.py`](../../../../tools/inference_smoke.py)（smoke 级交叉核对，不替代断言）。**不依赖**其它 Case；与 DP-USAGE-02（成功后可见记录）共享同一成功请求语义，但各自独立执行。
