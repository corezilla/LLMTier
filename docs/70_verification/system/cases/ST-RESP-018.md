<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-RESP-018 — body 超 2 MB

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-RESP-018` |
| Document Version | `0.1.0-draft.4` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-RESP-018.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-RESP-018` / 系统设计 §8 Responses 接口 / `VRC-INF-001` / recovery / P2（[方案清单 `ST-RESP-018`](../llmtier-system-test-scheme.md)）。
- **测试方法（§2.2 方法表行）**：边界值抽样（body 2 MB 边界）+ 错误猜测 + 反例驱动
- 要测什么（责任展开）：`POST /v1/responses` body 超过 2 MB：`413 request_too_large`，读取前拒绝（自动化入口 `ST-RESP-018.py`）。`Content-Length > 2 MiB` 时在解析业务体前返回 `413 request_too_large`。错误目录 `ERR-REQ-TOO-LARGE` → wire `code=request_too_large`；实现 `src/http_api/app.py` `_body()`（`if int(Content-Length) > 2 * 1024 * 1024: raise ApiError(413, "request_too_large", "Request body is too large")`，系统设计 §11.1）。
- 明确不测什么 / 失败含义：不测非法 `Content-Length`（`400 invalid_request`）或非法 JSON（ST-RESP-016）；不测上游调用。恰好 2 MiB 的边界（`== 2097152` 应受理）作为本 case 的边界子测。失败含义＝请求体上限制破坏。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `POST /v1/responses`；角色 `data`。

```text
POST /v1/responses
Authorization: Bearer dev-data
Content-Type: application/json
Content-Length: 2097153
```

- 初态构造（经公开入口）：**环境 B**（临时 LLMTier 实例）。初始状态 = 1 provider / 1 deployment / 7 tier。**不需要上游**（在上限检查阶段拒绝）。
- Fixture / 向量及版本：`llmtier_b`（可启动且 `/healthz` 200）、`api_client_b`；>2 MiB bytes body 与恰好 2 MiB body，随 Run manifest 存档。
- 依赖的测试资产（tests.asset-design 文档）：B 类 fixture `llmtier_b` / `api_client_b`。

## 3. 输入构造

- 逐参数输入构造：构造 `Content-Length` 略超 2 MiB 的请求体（关键：必须设置 `Content-Length`）：body 为合法 JSON，但总字节数**严格大于 `2097152`**（2 MiB）——例如 `2097153` 字节（约 2 MiB + 1 B，用一段 `'a'` 串填充 `input`）；用 `httpx` 的 `content=`（bytes）发送以自动带 `Content-Length`。
- 边界/非法取值及理由：**边界语义（显式）**——上限判定为 `Content-Length > 2 * 1024 * 1024`，故 `Content-Length == 2097152`（恰好 2 MiB）**不**因本上限被拒、应进入 JSON 解析；`2097153` 起才触发 `413`。
- 规模 / 时间域：2 MiB 量级 body；上限检查在读取前，不解析 JSON。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | （fixture 前置）`llmtier_b` 启动并轮询 `/healthz` 200 | 实例就绪 |
| 2 | 构造 >2 MiB 的 bytes body，`api_client_b.post("/v1/responses", content=body, headers={"Content-Type":"application/json"})` | status / Content-Type / body |
| 3 | 断言观测形态 | `status_code == 413`，JSON 错误信封（非 SSE） |
| 4 | 解析 `error` | `code=="request_too_large"`、`type=="request_error"`、`param is None`、`retryable is False`，键集恰 5 键 |
| 5 | 边界子测：构造恰好 2 MiB 的合法 body | 精确断言被受理：`200` + `text/event-stream` + 含 `response.completed`（非 413、非其它错误） |

- 重点关注步骤：① **上限在读取前检查**——>2 MiB 直接 413，不解析 JSON；② **必须有 `Content-Length`**——若缺（chunked/未设），`_body()` 读 0 字节，会偏离 413 路径；③ **边界语义**——`>` 2 MiB 拒绝、`==` 2 MiB 允许；④ **信封 identity**（5 键、无 `category`）；⑤ **边界可判别**——超限子测断 413 + `request_too_large`；边界子测精确断 200 + `text/event-stream`（不再用 `code != request_too_large` 的宽松门）；⑥ **自动化入口**——`ST-RESP-018.py` 已实现。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：OpenAPI `ErrorEnvelope`/`ErrorDetail` + 系统设计 §7.8 / §11.1 `ERR-REQ-TOO-LARGE`。**判据语义以设计验证项 `VRC-INF-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：HTTP `413`；`Content-Type: application/json`；body：`{"error":{"message":"Request body is too large","type":"request_error","code":"request_too_large","param":null,"retryable":false}}`；无 SSE 帧/`[DONE]`；恰好 2 MiB 被受理（`200` + `text/event-stream`）。

## 6. 错误路径、副作用与清理

- 错误出口与表现：>2 MiB → `413 request_too_large`，可观察且非 SSE。
- 副作用断言与清理：**无需 teardown**——只在上限检查层拒绝；B 类实例按计划整班销毁。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：[`tests/system/cases/ST-RESP-018.py`](../../../../tests/system/cases/ST-RESP-018.py)（已实现：超限 413 + 边界 200 两子测）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/system/cases/ST-RESP-018.py -q`。
- 实现状态：Implemented；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：>2 MiB → 413 + `request_too_large` + 非 SSE；边界 2 MiB 被受理（`200` + `text/event-stream` + `response.completed`）。
- FAIL：status/code 错、超限未被拒、边界误拒。
- BLOCKED：测试代码/契约问题。
- SKIP：B 类临时实例不可用。
- INVALID：以 mock/替代路径冒充真实路径。
- NOT_RUN：本 Case 有实现（`ST-RESP-018.py`），未执行记 `NOT_RUN`。

**证据与 Run**：保存请求 `Content-Length` 与字节数、HTTP status/headers、原始错误信封、边界子测结果、发出命令、exit code、环境快照（本 case `environment:"b"`）。

**依赖**：B 类 fixture `llmtier_b` / `api_client_b`；实现 `src/http_api/app.py` `_body()`；错误目录 `ERR-REQ-TOO-LARGE`（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md) §7.8/§11.1）。**不依赖**其它 Case。
