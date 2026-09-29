<!-- STD_DOCUMENT_COVER_BEGIN -->
# DP-EMB-06 — dimensions 与冻结空间不符

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `DP-EMB-06` |
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
| Canonical Path | `docs/70_verification/specifications/cases/dp-emb-06.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`DP-EMB-06` / 系统设计 §8 Embeddings 接口 / `VRC-INF-001` / negative / P1（[方案清单 `DP-EMB-06`](../../schemes/llmtier-system-test-scheme.md)）。
- 要测什么（责任展开）：`POST /v1/embeddings` `dimensions=768`（与 `Embedding-v1` 冻结向量空间不符）：返回 `400 unsupported_dimensions`（`param="dimensions"`），不触上游。`model="Embedding-v1"`（冻结空间 `bge-m3-dense-1024-v1`，`embedding_dimensions=[1024]`）、`dimensions=768`；请求在 dispatch 之前被拒。错误目录 `ERR-REQ-DIM`；需求 `LT-FUN-003`/`LT-OPEN-02`；机制需求 `R-INF-04`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；契约 `CT-EMB-001`。实现见 `src/inference/embeddings.py` 第 42–43 行（`require(body["dimensions"] in caps["embedding_dimensions"], 400, "unsupported_dimensions", "Unsupported embedding dimensions", "dimensions")`）。
- 明确不测什么 / 失败含义：不测合法 `dimensions=1024` 的成功；不测未知 model（DP-EMB-04）、非法 `encoding_format`（DP-EMB-07）、batch 上限（DP-EMB-05）、base64 形态（DP-EMB-02）；不测 `dimensions` 的 `minimum:1` 边界或上游对该参数的实际行为（本 case 在本地即被拒，不上游）。失败含义＝冻结维度成员校验破坏。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `POST /v1/embeddings`；角色 `data`，只读/无状态。

```text
POST /v1/embeddings
Authorization: Bearer dev-data
Content-Type: application/json
Accept: application/json
```

- 初态构造（经公开入口）：**环境 A**（m5air 已部署实例，只读/无状态）。`Embedding-v1` 已启用且 `capabilities.embedding_dimensions==[1024]`（与 `registry.py` 冻结校验一致）。本 case 为纯负向读，无副作用。
- Fixture / 向量及版本：固定请求 body（`dimensions=768`），768 字面量随 Run manifest 固定。
- 依赖的测试资产（tests.asset-design 文档）：`api_client`；`conftest.py::pytest_configure` 就绪检查。

## 3. 输入构造

- 逐参数输入构造：固定请求：

```json
{
  "model": "Embedding-v1",
  "input": "Hello world",
  "dimensions": 768
}
```

- 边界/非法取值及理由：`dimensions=768` 为**正整数、语法合法**（满足 `EmbeddingRequest.dimensions.minimum:1`）但**不在** `embedding_dimensions=[1024]` 内，确保失败点在冻结空间成员校验而非形态校验；`input`/`model` 均取合法值。若请求同时带非法 `model`，会先命中 404 而掩盖本码——故模型固定为已启用 tier。
- 规模 / 时间域：单次请求；在 dispatch 前拒绝。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /healthz`、`GET /readyz`（`pytest_configure` 自动执行） | §2.1 基线 |
| 2 | （前置证据）`GET /v1/models/Embedding-v1` 读取 `capabilities.embedding_dimensions` | 断言为 `[1024]`——判定"768 不符"的事实依据 |
| 3 | （可选前置）`GET /v1/usage` 记录 usage 基线 | 用于证明无新增账本义务 |
| 4 | `resp = api_client.post("/v1/embeddings", json={"model": "Embedding-v1", "input": "Hello world", "dimensions": 768})` | status / headers / body |
| 5 | 断言 `resp.status_code == 400` | `body` 为错误信封（无顶层 `object`/`data`） |
| 6 | 解析 `err = resp.json()["error"]` | 键集恰为 `{message,type,code,param,retryable}`，`code=="unsupported_dimensions"`、`param=="dimensions"`、`type=="request_error"`、`retryable is False` |
| 7 | （可选）核对 usage 基线未新增 dispatch | 零副作用交叉核对 |

- 重点关注步骤：① **精确错误码与 `param`**——`unsupported_dimensions` + `param="dimensions"`（见第 43 行 `require(..., "dimensions")`）；写成 `invalid_request` 或 `param=null` 即 FAIL；② **冻结空间成员语义**——比较对象是 `capabilities.embedding_dimensions` 列表（`[1024]`），不是单值；③ **不被后置错误掩盖**——必须确保 `model` 已启用且 embeddings-capable，否则会先命中 404/`unsupported_model`；④ **零副作用**——400 在 dispatch 之前，无上游调用、无账本义务；⑤ **`dimensions` 缺省不受影响**——双重条件：缺省时不进入校验，本 case 仅覆盖"提供且不符"；⑥ **MISSING 事实**——本 case 当前 `MISSING`（方案），**尚无** `at_dp_emb_06.py`；判定按 NOT_RUN，不得以邻近脚本的通过冒充本 case 通过。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：OpenAPI `ErrorEnvelope`/`ErrorDetail`（`code` enum 含 `unsupported_dimensions`）+ `Embedding-v1` 冻结空间 `embedding_dimensions=[1024]` + 方案错误映射。**判据语义以设计验证项 `VRC-INF-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：HTTP `400`；`Content-Type: application/json`；`{"error":{"message":<str>,"type":"request_error","code":"unsupported_dimensions","param":"dimensions","retryable":false}}`；无成功字段；无上游 dispatch、无账本新增义务（可选交叉核对）。

## 6. 错误路径、副作用与清理

- 错误出口与表现：`dimensions` 与冻结空间不符 → `400 unsupported_dimensions`（`param=dimensions`），可观察。
- 副作用断言与清理：**无需 teardown**——被拒请求，无配置/资源/注入改动，无用户 usage 删除。退出前确认 `/readyz` 7 tier、无未清空注入项；若误跑于 B 类实例，按计划整班销毁。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/system/api_test_v03/at_dp_emb_06.py`（当前 **MISSING，尚未实现**）。
- 单 Case 执行命令（实现后）：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_emb_06.py -q`。
- 实现状态：Planned（MISSING）；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：`status==400` 且 `error.code=="unsupported_dimensions"`、`param=="dimensions"`、`type=="request_error"`、`retryable is False`，键集恰 5；且（若核对）无新账本义务。
- FAIL：status 非 400、`code`/`param`/`type`/`retryable` 不符、键集多/缺，或产生上游调用/账本义务。
- BLOCKED：测试代码/契约本身问题（入口待实现导致断言不可执行等）。
- SKIP：就绪检查不满足。
- INVALID：用 `127.0.0.1`/mock/替代路径冒充真实实例，或用 B 类结果冒充 A 类。
- NOT_RUN：本 case 自动化入口 `MISSING`；缺口引用方案 §9（MISSING ≠ NOT_RUN：无实现是缺口，不是跳过）。

**证据与 Run**：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、`/v1/models/Embedding-v1` 的 `embedding_dimensions` 快照、请求/响应、可选 usage 前后快照、发出命令、exit code、`elapsed`、环境快照（本 case `environment:"a"`）。

**依赖**：就绪检查；`api_client`；`Embedding-v1` 冻结空间 `embedding_dimensions=[1024]`（OpenAPI + `src/management/registry.py`）；实现 `src/inference/embeddings.py` 第 42–43 行；`ErrorDetail.code` 机器契约。自动化入口 `at_dp_emb_06.py`（**当前 `MISSING`**）。**不依赖**其它 Case；与 DP-EMB-07（非法 `encoding_format`）同属 embeddings 本地校验负向，各自独立执行。
