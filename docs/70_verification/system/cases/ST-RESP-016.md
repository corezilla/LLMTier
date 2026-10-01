<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-RESP-016 — 非法 JSON body

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-RESP-016` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-RESP-016.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-RESP-016` / 系统设计 §8 Responses 接口 / `VRC-INF-001` / recovery / P1（[方案清单 `ST-RESP-016`](../llmtier-system-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（ERR-REQ-JSON：非法 JSON body）
- 要测什么（责任展开）：`POST /v1/responses` 发送非法 JSON body：`400 invalid_json`，dispatch 前拒绝（自动化入口 `ST-RESP-016.py`）。body 不是合法 JSON（或不是 JSON 对象）时，M001 在业务校验/dispatch 前返回 `400 invalid_json`。需求 `LT-FUN-001`；错误目录 `ERR-REQ-JSON` → wire `code=invalid_json`；实现 `src/http_api/app.py` `_body()`（`json.loads` 失败 → `ApiError(400, "invalid_json", "Request body is not valid JSON")`；解析成功但非对象 → `ApiError(400, "invalid_json", "Request body must be a JSON object")`）。
- 明确不测什么 / 失败含义：不测 schema 级字段校验（缺 `model` 见 ST-RESP-008；未知字段见 ST-RESP-012..15）；不测 `Content-Length` 非法（`400 invalid_request`）或超限（ST-RESP-018）；不测上游调用。失败含义＝请求体解析契约破坏。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `POST /v1/responses`（原始字节 body）。

```text
POST /v1/responses
Authorization: Bearer dev-data
Content-Type: application/json
```

- 初态构造（经公开入口）：**环境 B**（临时 LLMTier 实例，见[系统测试计划 §2](../llmtier-system-test-plan.md)）。初始状态 = 1 provider / 1 deployment / 7 tier。**不需要上游**（在解析阶段拒绝，早于路由）。
- Fixture / 向量及版本：`llmtier_b`（可启动且 `/healthz` 200）、`api_client_b`；非法 JSON 字节与 `[1,2,3]` 向量，随 Run manifest 存档。
- 依赖的测试资产（tests.asset-design 文档）：B 类 fixture `llmtier_b` / `api_client_b`（契约与自检见 asset/计划文档）。

## 3. 输入构造

- 逐参数输入构造：固定请求（原始 body 为非法 JSON 字节）：

```text
{"model": "Senior", "input": [{"role": "user", "content": "hi"}], "stream": true, "store": false,
```

（末行截断，缺右花括号，非法 JSON）。请求必须带 `Content-Length`（`httpx` 以 `content=` 发送时自动设置），否则 `_body()` 按 0 字节读成 `{}`。
- 边界/非法取值及理由：另测 `[1,2,3]`（合法 JSON 但非对象）→ 同样 `invalid_json`。
- 规模 / 时间域：2 次请求，均在解析层拒绝。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | （fixture 前置）`llmtier_b` 启动并轮询 `/healthz` 200 | 实例就绪 |
| 2 | 以 `api_client_b` 发送原始非法 JSON：`client.post("/v1/responses", content=b'{...', headers={"Content-Type":"application/json"})` | status / Content-Type / body |
| 3 | 断言观测形态 | `status_code == 400`，JSON 错误信封（非 SSE） |
| 4 | 解析 `error` | `code=="invalid_json"`、`type=="request_error"`、`param is None`、`retryable is False`，键集恰 5 键 |
| 5 | 边界：以 `content=b'[1,2,3]'` 重发 | 同样 `400 invalid_json`（"must be a JSON object"） |

- 重点关注步骤：① **解析先于业务校验**——非法 JSON 不得报 `invalid_request`/`unsupported_request`；② **`Content-Length` 必须存在**——否则 `_body()` 读 0 字节变 `{}`，会错误地走到字段齐备性校验；③ **信封 identity**（5 键、无 `category`）；④ **非 SSE**；⑤ **自动化入口**——`ST-RESP-016.py` 已实现并覆盖上述断言。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：OpenAPI `ErrorEnvelope`/`ErrorDetail` + 系统设计 §7.8 `ERR-REQ-JSON`（不依赖实现答案）。**判据语义以设计验证项 `VRC-INF-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：HTTP `400`；`Content-Type: application/json`；body：`{"error":{"message":"Request body is not valid JSON","type":"request_error","code":"invalid_json","param":null,"retryable":false}}`；`[1,2,3]` 时 `message="Request body must be a JSON object"`；无 SSE 帧/`[DONE]`。

## 6. 错误路径、副作用与清理

- 错误出口与表现：非法 JSON / 非对象 JSON → `400 invalid_json`，可观察且非 SSE。
- 副作用断言与清理：**无需 teardown**——只在解析层拒绝，不创建/修改资源；B 类实例按计划整班销毁。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：[`tests/system/cases/ST-RESP-016.py`](../../../../tests/system/cases/ST-RESP-016.py)（已实现：`invalid_json` 两子测）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/system/cases/ST-RESP-016.py -q`。
- 实现状态：Implemented；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：status 400 + `code=invalid_json` + `type=request_error` + `param=null` + `retryable=false` + 非 SSE。
- FAIL：status/code 错、报业务校验错误、返回 200/SSE、信封键集错。
- BLOCKED：测试代码/契约问题。
- SKIP：B 类临时实例不可用。
- INVALID：以 mock/替代路径冒充真实路径。
- NOT_RUN：本 Case 有实现（`ST-RESP-016.py`），未执行记 `NOT_RUN`。

**证据与 Run**：保存原始请求字节、`Content-Length`、HTTP status/headers、原始错误信封、发出命令、exit code、环境快照（本 case `environment:"b"`）。

**依赖**：B 类 fixture `llmtier_b` / `api_client_b`；实现 `src/http_api/app.py` `_body()`；错误目录 `ERR-REQ-JSON`（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md) §7.8）；需求 `LT-FUN-001`。**不依赖**其它 Case。
