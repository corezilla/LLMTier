<!-- STD_DOCUMENT_COVER_BEGIN -->
# DP-EMB-07 — 非法 encoding_format

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `DP-EMB-07` |
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
| Canonical Path | `docs/70_verification/specifications/cases/dp-emb-07.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`DP-EMB-07` / 系统设计 §8 Embeddings 接口 / `VRC-INF-001` / negative / P2（[方案清单 `DP-EMB-07`](../../schemes/llmtier-system-test-scheme.md)）。
- 要测什么（责任展开）：`POST /v1/embeddings` `encoding_format=hex`（非 `float|base64`）：返回 `400 invalid_request`（`param="encoding_format"`），不触上游。`encoding_format` 仅允许 `float|base64`（OpenAPI `EmbeddingRequest.encoding_format.enum`）；取非法值 `"hex"` 时应在 dispatch 之前被拒。错误目录 `ERR-REQ-VALIDATION`；需求 `LT-FUN-003`；机制需求 `R-INF-04`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；契约 `CT-EMB-001`。实现 `src/inference/embeddings.py` 第 34 行：`require(encoding in {"float","base64"}, 400, "invalid_request", "encoding_format must be one of: float, base64", "encoding_format")`——该值级校验在 model/`embeddings` 能力/`dimensions` 校验与 `authorize_dispatch`（第 44 行）之前，故非法值零副作用被拒。**同一校验分支的相邻负向（"缺/多字段"）**：`EmbeddingRequest` 顶层 `additionalProperties:false` 且 `required:[model,input]`；缺 `model`/`input` 或带未知顶层键时，第 32 行 `require(...)` 亦返回 `400 invalid_request`（该 `require` 未传 `param`，故 `param==null`）。
- 明确不测什么 / 失败含义：不测合法 `float`/`base64` 的成功（DP-EMB-01/02）；不测未知 model（DP-EMB-04）、`dimensions` 不符（DP-EMB-06）、batch（DP-EMB-05）、base64 形态（DP-EMB-02）；**不声称**本 case 已实现（当前 `MISSING`，无 `at_dp_emb_07.py`）。失败含义＝`encoding_format` 值级校验缺失或被后置错误掩盖。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `POST /v1/embeddings`；角色 `data`，只读/无状态。

```text
POST /v1/embeddings
Authorization: Bearer dev-data
Content-Type: application/json
Accept: application/json
```

- 初态构造（经公开入口）：**环境 A**（m5air 已部署实例，只读/无状态）。m5air 现有 3 provider / 4 deployment / 7 fixed tier。**A 类构造**：A 基线的 `dep_local_bge_m3` 为 embeddings-capable，固定 tier `Embedding-v1` 指向它，故 `model="Embedding-v1"` 能通过 model/`embeddings` 能力校验，使失败点唯一落在 `encoding_format` 值校验，不会先命中 `unsupported_model`/404。本 case 为纯负向读，无副作用。
- Fixture / 向量及版本：非法值 `"hex"` 及缺字段构造，随 Run manifest 固定。
- 依赖的测试资产（tests.asset-design 文档）：`api_client`；`conftest.py::pytest_configure` 就绪检查。

## 3. 输入构造

- 逐参数输入构造：固定请求：

```json
{
  "model": "Embedding-v1",
  "input": "Hello world",
  "encoding_format": "hex"
}
```

- 边界/非法取值及理由：`encoding_format="hex"` 为**非空字符串**但**不在** `enum:[float,base64]` 内；`input`/`model` 取合法值（`Embedding-v1` 指向 embeddings-capable 的 `dep_local_bge_m3`），使失败点唯一落在编码格式值校验。**可选加强负向**（同一校验分支）：分别构造缺 `input`、缺 `model`、带未知顶层键（如 `"foo":1`）的 body，期望均为 `400 invalid_request`（`param==null`）。
- 规模 / 时间域：主请求 1 次 + 可选加强 3 次；均在 dispatch 前拒绝。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /healthz`、`GET /readyz`（`pytest_configure` 自动执行） | §2.1 基线 |
| 2 | （可选）记录 `GET /v1/usage` 基线 | 用于证明零副作用 |
| 3 | `resp = api_client.post("/v1/embeddings", json={"model": "Embedding-v1", "input": "Hello world", "encoding_format": "hex"})` | status / headers / body |
| 4 | 断言 `resp.status_code == 400` | body 为错误信封（无顶层 `object`/`data`） |
| 5 | 解析 `err = resp.json()["error"]` | 键集恰为 `{message,type,code,param,retryable}`，`code=="invalid_request"`、`param=="encoding_format"`、`type=="request_error"`、`retryable is False` |
| 6 | （可选加强）对缺 `input`/缺 `model`/未知顶层键各发一次 | 均 `400 invalid_request`（`param==null`），覆盖"invalid input"路径 |
| 7 | （可选）核对 usage 基线未新增 dispatch | 零副作用交叉核对 |

- 重点关注步骤：① **错误码 `invalid_request` 与 `param="encoding_format"`**——因第 34 行 `require(..., "encoding_format")` 显式传参，`param` 必须为 `"encoding_format"`；写成 `null` 即 FAIL；② **值级校验已落地**——非法值在 model/能力/`dimensions` 校验之前被拒；③ **model 指向 embeddings-capable tier**——`Embedding-v1` 必须指向 `dep_local_bge_m3`（A 基线），否则观测到的 400 不是编码值校验；④ **零副作用**——校验失败须在 dispatch 前完成；⑤ **MISSING 事实**——当前 `MISSING`，尚无 `at_dp_emb_07.py`；判定按 NOT_RUN，不得以其它 emb case 的通过冒充；⑥ **相邻负向边界**——缺字段/未知顶层键走第 32 行键集 `require`，其 `param==null`，与值级校验的 `param=="encoding_format"` 区分记录。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：OpenAPI `EmbeddingRequest.encoding_format.enum`（+ `additionalProperties:false`/`required`）+ `ErrorEnvelope`（`code=="invalid_request"`）+ 方案错误映射。**判据语义以设计验证项 `VRC-INF-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：HTTP `400`；`Content-Type: application/json`；`{"error":{"message":<str>,"type":"request_error","code":"invalid_request","param":"encoding_format","retryable":false}}`；可选加强（缺字段/未知键）：同形 `400 invalid_request`，`param==null`；无成功字段；无上游 dispatch、无账本新增义务（可选交叉核对）。

## 6. 错误路径、副作用与清理

- 错误出口与表现：非法 `encoding_format` → `400 invalid_request`（`param=encoding_format`）；若 `"hex"` 被当作合法值（200），登记**实现未校验 `encoding_format` 值**的缺口。
- 副作用断言与清理：**无需 teardown**——被拒请求，不改 provider/deployment/service-level、不写注入项、不删除用户 usage。退出前确认 `/readyz` 7 tier、无未清空注入项；若误跑于 B 类实例，按计划整班销毁。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/system/api_test_v03/at_dp_emb_07.py`（当前 **MISSING，尚未实现**）。
- 单 Case 执行命令（实现后）：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_emb_07.py -q`。
- 实现状态：Planned（MISSING）；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：`status==400` 且 `error.code=="invalid_request"`、`param=="encoding_format"`、`type=="request_error"`、`retryable is False`，键集恰 5；且（若核对）无新账本义务。
- FAIL：status 非 400、`code` 非 `invalid_request`（如 `unsupported_model`、`provider_error`）、`param` 非 `"encoding_format"`、`type`/`retryable` 不符、键集多/缺，或产生上游调用/账本义务——尤其当 `"hex"` 被当作合法值时，登记**实现未校验 `encoding_format` 值**的缺口。
- BLOCKED：测试代码/契约本身问题（`api_client` 写不出、断言逻辑错、`param` 语义不清等）。
- SKIP：就绪检查不满足（m5air 不可达、`/readyz` 非 7 tier、双 OMLX 离线等）。
- INVALID：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或用 B 类结果冒充 A 类。
- NOT_RUN：本 case 自动化入口 `MISSING`；缺口引用方案 §9（MISSING ≠ NOT_RUN）。

**证据与 Run**：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、发出命令、exit code、`elapsed`、环境快照。**额外证据**：请求/响应、可选 usage 前后快照、环境快照（`/healthz` + provider/deployment 列表；确认 `Embedding-v1`→`dep_local_bge_m3`）（本 case `environment:"a"`）。

**依赖**：就绪检查；`api_client`；A 基线 embeddings-capable 部署 `dep_local_bge_m3` / 固定 tier `Embedding-v1`；`EmbeddingRequest.encoding_format` 机器契约；实现 `src/inference/embeddings.py` 第 32/33/34/53–58 行与 `src/inference/routing.py`；`ErrorDetail.code` 机器契约。自动化入口 `at_dp_emb_07.py`（**当前 `MISSING`**）。**不依赖**其它 Case；与 DP-EMB-06（`dimensions` 不符）同属 embeddings 本地校验负向，各自独立执行。
