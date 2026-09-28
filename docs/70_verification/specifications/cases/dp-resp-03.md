# DP-RESP-03 — 推理任务流式结构

- **Case ID**：`DP-RESP-03`
- **标题**：`POST /v1/responses` 固定推理 prompt：SSE 结构完整（事件序列/唯一 terminal/`[DONE]`），不把模型输出内容当 oracle。
- **目的（被测契约）**：验证 Data Plane `POST /v1/responses`（`stream=true`）在**固定推理 prompt** 下的正常路径：事件序列有序、恰好一个 terminal、`output_text.delta` 累积文本非空。被测端点/规则：`POST /v1/responses`；设计验证项 `VRC-INF-001`；机制 `T-STREAM`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；固定 prompt 见[测试设计 §5 LLM 判据](../llmtier-api-test-specification.md)（结构/事件序列，不写"答案正确"、不把内容当 oracle）。**不证明什么**：不证明模型答案的语义正确性、不证明 upstream 推理质量、不发布时延 SLO；不证明 `stream=false`/`store=true` 被拒（DP-RESP-02/07）、不证明截断（DP-RESP-10）或异常路径（DP-RESP-11/21）。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，角色 `data`，无状态；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查（含 m5air OMLX `192.168.1.9:9000`、m5mac OMLX `192.168.1.8:9000`）；fixture `api_client`（Bearer `dev-data`，[§4.4](../llmtier-api-test-specification.md)）。初始状态 = 3 provider / 4 deployment / 7 fixed tier；`model="Worker"` 由三选一调度，只断言最终 200 + SSE 合法。
- **输入与构造**：固定请求（固定推理 prompt `Calculate 15 * 23 + 45 step by step`；**模型输出内容不作为 Oracle**，见下可复现性风险）：

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
    "input": [{"role": "user", "content": "Calculate 15 * 23 + 45 step by step"}],
    "stream": true,
    "store": false,
    "max_output_tokens": 200
  }
  ```

  边界/构造点：`max_output_tokens=200` 保证推理任务不易被截断（不触发 DP-RESP-10）；`model` 为 responses-capable tier；`store=false` 避免落库副作用；不注入故障。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行）。
  2. `POST /v1/responses` 以流式读取；断言 `status_code == 200` 且 `content-type` 含 `text/event-stream`。
  3. 逐帧解析 `text/event-stream`（按空行分帧，取 `event:`/`data:`；`data: [DONE]` 单独识别，[§4.5](../llmtier-api-test-specification.md)）。
  4. 断言事件集合/顺序（子序列）：`response.created` 首帧；含 `response.output_item.added`、≥1 个 `response.output_text.delta`、`response.output_item.done`；`response.completed` 为唯一 terminal（本版本无独立的文本完成事件，见 DP-RESP-01）。
  5. 断言 `response.completed.response.status == "completed"`；各帧 `sequence_number` 自 0 严格递增。
  6. 累积所有 `delta`，断言累积文本非空（结构断言；**不断言模型内容**，如是否含 `"390"`）。
  7. 断言流末尾出现 `data: [DONE]`。
- **重点关注步骤**：① **模型内容不是 Oracle**——`"390"` 仅为示例数字串，上游 LLM 输出格式不稳定，**不作为 PASS/FAIL 条件**；若未观察到该串，只作可复现性风险记录（见下），不得据此判 FAIL、也不得改写成"语义对即可"的反向断言；② **terminal 唯一 + `[DONE]`**（[§4.5](../llmtier-api-test-specification.md)）；③ **`sequence_number` 严格递增**；④ **`Content-Type` 必须 `text/event-stream`**，防止把错误信封当成功流；⑤ **事件 identity**——`delta` 至少 1 个且累积文本非空。
> **可复现性风险（记录，非判据）**：固定 prompt 期望输出含数字串 `"390"`，但上游 LLM 输出不稳定、该子串可能不出现；本设计据此把 `"390"` 移出 PASS 条件，case 保持结构性。若后续要用它做回归，须先在上游侧锁定确定性（如 greedy / `temperature=0`）并在[测试设计 §5](../llmtier-api-test-specification.md) 另立判据。
- **期望结果与独立 Oracle**：独立 Oracle = 标准 Responses SSE wire 形态（**不依赖实现的"答案内容"与语义正确性**；固定 prompt 仅用于稳定触发推理输出，其内容不作断言）。
  - HTTP：`200`；`Content-Type: text/event-stream`。
  - 事件序列：`response.created` 首帧 → `output_item.added` → `output_text.delta`（≥1）→ `output_item.done` → 唯一 terminal `response.completed`（`status="completed"`）→ `data: [DONE]`。
  - 帧内 `sequence_number` 自 0 严格递增；累积 delta 文本非空（**不约束内容**，`"390"` 非判据）。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：status + content-type + 事件序列/唯一 terminal + `[DONE]` + `sequence_number` 递增 + 累积文本非空 全部 match。
  - **FAIL**：任一断言不符（status/序列/terminal/`[DONE]`/递增/累积文本为空）。
  - **BLOCKED**：测试代码/断言不可实现——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（上游 OMLX 离线等）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：以 `127.0.0.1`/mock/替代路径冒充真实 m5air——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存原始 SSE 逐帧、HTTP status/headers、累积文本、发出命令、exit code、`elapsed`、环境快照（`/healthz`/`/readyz`）。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`，含 `manifest.json`（[§4.8](../llmtier-api-test-specification.md)）与原始证据；失败现场不截断。**注**：现有 [`at_dp_resp_03.py`](../../../../tests/system/api_test_v03/at_dp_resp_03.py) 断言事件集合（`response.created`/`response.output_text.delta`/`response.output_item.done`）与 `status=completed`，并显式断言 `response.output_text.done not in names`（第 76 行），与本设计的事件序列（见 DP-RESP-01）一致。`"390"` 已移出 PASS 条件，无需补齐。
- **清理与复位**：**无需 teardown**——`store=false`、环境 A 无状态，不创建/修改资源；退出前确认无注入项、`/readyz` 仍 7 tier。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查；`api_client`（[§4.4](../llmtier-api-test-specification.md)）；上游 tier `Worker`；自动化入口 [`at_dp_resp_03.py`](../../../../tests/system/api_test_v03/at_dp_resp_03.py)。**不依赖**其它 Case；与 DP-RESP-01（通用流式成功）共享 SSE 机制但用固定推理 prompt 区分。
