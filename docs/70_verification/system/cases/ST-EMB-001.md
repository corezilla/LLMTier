<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-EMB-001 — 基本 embedding（1024 维 finite）

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-EMB-001` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-EMB-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-EMB-001`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Embeddings 接口（parent `llmtier-system-design`），设计验证项 `VRC-INF-001`、`VRC-INF-002`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-EMB-001` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-EMB-001` / 系统设计 §8 Embeddings 接口 / `VRC-INF-001`、`VRC-INF-002` / normal / P0（[方案清单 `ST-EMB-001`](../llmtier-system-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：等价类划分 + 契约字段比对
- 要测什么（责任展开）：`POST /v1/embeddings` 基本 embedding：`Embedding-v1`（bge-m3，冻结空间 `bge-m3-dense-1024-v1`）成功返回，`object="list"`、`data[0].object="embedding"`、`embedding` 为 1024 个有限数值。`model="Embedding-v1"`、`input` 为字符串、`encoding_format` 缺省（默认 `float`）；成功返回 OpenAPI `EmbeddingResponse`（顶层键 `{object,data,model,usage}`）。需求 `LT-FUN-003`/`LT-OPEN-02`；机制需求 `R-INF-04`/`R-INF-05`/`R-INF-07`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；契约 `CT-EMB-001`。
- 明确不测什么 / 失败含义：不测 `encoding_format=base64`（ST-EMB-002）；不测多次同输入不变量/相似度（ST-EMB-003）；不测未知 model 404（ST-EMB-004）；不测 batch>1（ST-EMB-005）；不测 `dimensions` 不符拒绝（ST-EMB-006）；不测非法 `encoding_format`（ST-EMB-007）；不发布时延/吞吐 SLO；不对向量语义/答案/L2 归一化做门限。失败含义＝成功路径 wire 契约破坏。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `POST /v1/embeddings`；角色 `data`，只读/无状态。

```text
POST /v1/embeddings
Authorization: Bearer dev-data
Content-Type: application/json
Accept: application/json
```

- 初态构造（经公开入口）：**环境 A**（m5air 已部署实例，只读/无状态）。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier；`Embedding-v1` 已启用且指向本地 bge-m3 deployment（上游走 LAN，TS-003）。本 case 为纯读，初态即终态。
- Fixture / 向量及版本：固定请求 body（`input="Hello world"`，省略 `encoding_format`/`dimensions`/`user`），固定 prompt 随 Run manifest 存档。
- 依赖的测试资产（tests.asset-design 文档）：`api_client`；`conftest.py::pytest_configure` 就绪检查。

## 3. 输入构造

- 逐参数输入构造：固定请求：

```json
{
  "model": "Embedding-v1",
  "input": "Hello world"
}
```

- 边界/非法取值及理由：`input` 取**字符串**（`EmbeddingRequest.input` 的 `oneOf` 最小合法形态之一，另一形态为非空字符串数组，见 ST-EMB-005）；`model` 必须为 embeddings-capable fixed tier（此处 `Embedding-v1`）；**省略** `encoding_format`（走 openapi 默认 `float`）、`dimensions`、`user`，以验证缺省路径；不注入故障；不构造非法输入（缺字段/多字段 → 400 `invalid_request` 属 ST-EMB-007 邻域，未知 model → ST-EMB-004）。
- 规模 / 时间域：单输入、单次请求；不发布时延 SLO。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /healthz`、`GET /readyz`（由 `pytest_configure` 自动执行） | §2.1 基线 |
| 2 | `resp = api_client.post("/v1/embeddings", json={"model": "Embedding-v1", "input": "Hello world"})` | status / `Content-Type` / `X-Request-ID` / body |
| 3 | 断言 status 与形态 | `status_code == 200` 且 content-type 含 `application/json`；body **不是** `{"error":{...}}` |
| 4 | 顶层键集**恰为** `{object, data, model, usage}`（`additionalProperties:false`） | `object == "list"`；`model == "Embedding-v1"` |
| 5 | 取 `item = data[0]`，键集**恰为** `{object, index, embedding}` | `item["object"] == "embedding"`、`item["index"] == 0`（单输入） |
| 6 | `item["embedding"]` 为 JSON 数组，长度 `== 1024`，每元素为 `int`/`float`（非 `bool`）且 `math.isfinite(x)` | 无 `NaN`/`Infinity` |
| 7 | （可选、非门限）读取顶层 `usage` | 为 `null` 或 JSON 对象；具体数值不作 PASS 条件 |

- 重点关注步骤：① **键集严格性**——"键集恰等"，`EmbeddingResponse`/`EmbeddingItem` 均 `additionalProperties:false`，多键即契约违反；② **数值有限性**——`isfinite` 覆盖 `NaN`/`±Infinity`；仅"是数字"不够；③ **维数 1024**——bge-m3 冻结空间硬约束，误按 768/1536 断言即错；④ **`model` 回显逻辑模型**——实现把上游结果 `result["model"] = model` 覆盖为请求的 `Embedding-v1`；⑤ **`usage` 直通风险**——响应 `usage` 来自上游且未经归一；只断言"存在且为 `null` 或对象"；⑥ **不依赖向量语义**。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：OpenAPI `EmbeddingResponse`/`EmbeddingItem` 的 wire 形态（不依赖实现的具体向量值）。**判据语义以设计验证项 `VRC-INF-001`/`VRC-INF-002` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：HTTP `200`；`Content-Type: application/json`；`X-Request-ID` 存在；顶层键集恰为 `{object, data, model, usage}`，`object=="list"`、`model=="Embedding-v1"`；`data[0]` 键集恰为 `{object,index,embedding}`，`object=="embedding"`、`index==0`；`embedding` 为 1024 个有限 `int`/`float`；`usage` 为 `null` 或对象；无 `{"error":{...}}`。

## 6. 错误路径、副作用与清理

- 错误出口与表现：本 case 不应出现错误信封；任何非 200 须确认是可解释的 `ERR-AUTH-*`/`ERR-STORE` 等，而非把错误体读成成功。
- 副作用断言与清理：**无需 teardown**——只读 `POST`（embedding 不落配置、不写注入项；账本可能记录一次 dispatch，属正常计量不回收）。不删除既有资源或用户 usage。退出前确认无未清空注入项、`/readyz` 仍 7 tier；若误跑于 B 类实例，按计划整班销毁。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：[`tests/system/api_test_v03/at_dp_emb_01.py`](../../../../tests/system/api_test_v03/at_dp_emb_01.py)。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_emb_01.py -q`。
- 实现状态：Implemented；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：`status==200` 且 content-type 为 JSON，顶层/`data[0]` 键集与 Oracle 一致，`object`/`index`/`embedding` 长度 1024 且全部 finite（`usage` 存在且为 null 或对象）。
- FAIL：任一断言不符（status 非 200、键集不等、`object`/`index` 错、维数非 1024、含非有限值或非数值、以错误信封冒充成功）。
- BLOCKED：测试代码/契约本身问题。
- SKIP：就绪检查不满足（m5air 不可达、`/readyz` 非 7 tier、双 OMLX 离线等）。
- INVALID：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或以 B 类临时实例结果冒充 A 类。
- NOT_RUN：本 Case 有实现，本轮未执行时记 `NOT_RUN`；不得以未跑冒充 PASS。

**证据与 Run**：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、发出命令、exit code、`elapsed`、环境快照；manifest 与报告落位见系统测试计划（本 case `environment:"a"`）。

**依赖**：就绪检查；`api_client`；embeddings-capable 上游 tier `Embedding-v1`（本地 bge-m3，1024 维）；机器契约 `EmbeddingResponse`/`EmbeddingItem`/`EmbeddingUsage`；实现 `src/inference/embeddings.py`；自动化入口 `at_dp_emb_01.py`。**不依赖**其它 Case；与 ST-EMB-002/03 共享同一成功路径语义但各自独立执行。
