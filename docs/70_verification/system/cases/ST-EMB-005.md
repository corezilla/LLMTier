<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-EMB-005 — batch 33 不强制上限

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-EMB-005` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-EMB-005.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-EMB-005`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Embeddings 接口（parent `llmtier-system-design`），设计验证项 `VRC-INF-002`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-EMB-005` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-EMB-005` / 系统设计 §8 Embeddings 接口 / `VRC-INF-002` / boundary / P2（[方案清单 `ST-EMB-005`](../llmtier-system-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：边界值抽样 + 契约字段比对
- 要测什么（责任展开）：`POST /v1/embeddings` 输入数组长度 33（超过 `embedding_max_batch_inputs=32`）：LLMTier 层不强制该上限，返回 200 且 `data` 含 33 个 embedding 对象。`model="Embedding-v1"`、`input` 为 33 个字符串的数组（`EmbeddingRequest.input` 的数组形态，`minItems:1` 无 `maxItems`）。需求 `LT-FUN-003`/`LT-OPEN-02`（`Embedding-v1` 声明 `batch 32`）；机制需求 `R-INF-04`/`R-INF-07`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；契约 `CT-EMB-001`。**当前实现的边界事实**：`capabilities.embedding_max_batch_inputs=32` 在 `src/management/registry.py` 中为 **informational**（用于 `/v1/models` 元数据），`src/inference/embeddings.py` 的 `create()` 校验逻辑**不含** batch 上限检查（只校验请求键集、model、`embeddings` 能力、`dimensions`），故 33 项被原样转发上游；实际 batch 限制由上游 bge-m3 处理。
- 明确不测什么 / 失败含义：不测 batch **上限**（本 case 恰证明"超声明值不被本地拒绝"）；不测超大 batch（如数百项）或上游真实 batch 上限；不测 base64 形态下的 batch 编码（ST-EMB-002）；不测未知 model（ST-EMB-004）、`dimensions`（ST-EMB-006）、非法 `encoding_format`（ST-EMB-007）；不对向量语义做断言。失败含义＝与"本地不强制上限"的实现边界事实不符。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `POST /v1/embeddings`；角色 `data`，只读/无状态。

```text
POST /v1/embeddings
Authorization: Bearer dev-data
Content-Type: application/json
Accept: application/json
```

- 初态构造（经公开入口）：**环境 A**（m5air 已部署实例，只读/无状态）。`Embedding-v1` 已启用（上游本地 bge-m3，LAN，TS-003），其声明 `embedding_max_batch_inputs=32`。**上游依赖**：本 case 期望上游接受 33 项；若上游拒绝，结果将非 200（属上游限制，按判定处理）。
- Fixture / 向量及版本：固定请求 body（33 项固定输入），随 Run manifest 存档。
- 依赖的测试资产（tests.asset-design 文档）：`api_client`；`conftest.py::pytest_configure` 就绪检查。

## 3. 输入构造

- 逐参数输入构造：固定请求：

```json
{
  "model": "Embedding-v1",
  "input": ["hello", "hello", "... (共 33 项)"]
}
```

- 边界/非法取值及理由：`input` 为 33 个**相同**字符串 `"hello"`（构造简单、可复现；`embedding_max_batch_inputs` 声明为 32，故意 +1 越界以证明"本地不强制"）；`encoding_format` 缺省 `float`；`model="Embedding-v1"`；不注入故障；不与其它写操作并发。
- 规模 / 时间域：33 项 batch；属功能边界，不发布时延 SLO。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /healthz`、`GET /readyz`（`pytest_configure` 自动执行） | §2.1 基线 |
| 2 | （可选前置）`GET /v1/models/Embedding-v1` 读取 `capabilities.embedding_max_batch_inputs==32` | "本地声明上限 32 但不强制"的证据锚点 |
| 3 | `resp = api_client.post("/v1/embeddings", json={"model": "Embedding-v1", "input": ["hello"] * 33})` | status / `Content-Type` / body |
| 4 | 断言 `resp.status_code == 200` | 若拒绝则记录实际 status + 错误信封，按判定 FAIL/BLOCKED |
| 5 | 断言 `object=="list"`、`data` 为数组且 `len(data) == 33` | 数量一致 |
| 6 | 断言每个 `item` 的 `object=="embedding"`、`index` 覆盖 `0..32`（顺序稳定）、`embedding` 为有限的 1024 维数值数组 | 逐项形状/有限性 |

- 重点关注步骤：① **长度恰 33**——不是"≥1"也不是"≥33"；本地不得因声明上限 32 而截断/拒绝；② **`index` 与输入顺序对应**——`data[i].index==i`（或按实现稳定排序）；③ **每个向量的维度/有限性**——33 项都须 1024 维 finite，避免只抽查第一项；④ **上游行为风险**——本 case 的 200 依赖上游 bge-m3 接受 33 项；若上游返回非 2xx（经适配层归一为 `provider_error`/`provider_contract_error` 等），设计将其列为正常/边界成功场景，故上游拒绝应按 FAIL 登记；若因上游离线等环境问题则 SKIP；⑤ **"informational" 事实**——`embedding_max_batch_inputs` 不参与 `create()` 校验；⑥ **非性能判定**。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：OpenAPI `EmbeddingRequest.input`（数组形态无 `maxItems`）+ `EmbeddingResponse.data`（`EmbeddingItem[]`，长度与输入项数一致）+ 实现边界（`embedding_max_batch_inputs` 为 informational）。**判据语义以设计验证项 `VRC-INF-002` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：HTTP `200`；`Content-Type: application/json`；`X-Request-ID` 存在；body `object=="list"`、`model=="Embedding-v1"`、`data` 长度 `== 33`；`data[i]`：`object=="embedding"`、`index==i`、`embedding` 为 1024 个有限数值。

## 6. 错误路径、副作用与清理

- 错误出口与表现：本地以 400/其它码拒绝 33 项、或返回数量非 33、`index` 不对齐、维度/有限性不符、上游因可解释原因拒绝。
- 副作用断言与清理：**无需 teardown**——只读 embedding 调用，不改配置/不写注入项；不删除既有资源或用户 usage。退出前确认 `/readyz` 7 tier、无未清空注入项；若误跑于 B 类实例，按计划整班销毁。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：[`tests/system/cases/ST-EMB-005.py`](../../../../tests/system/cases/ST-EMB-005.py)。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/system/cases/ST-EMB-005.py -q`。
- 实现状态：Implemented；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：`status==200` 且 `data` 长度 33 且每项 `object`/`index`/`embedding` 形状与有限性成立。
- FAIL：本地以 400/其它码拒绝 33 项（与"不强制上限"不符），或返回数量非 33、`index` 不对齐、维度/有限性不符、上游因可解释原因拒绝。
- BLOCKED：测试代码/契约本身问题（fixture/断言不可实现）。
- SKIP：就绪检查不满足（上游 OMLX 离线、m5air 不可达等）。
- INVALID：用 `127.0.0.1`/mock/替代路径冒充真实实例，或用 B 类结果冒充 A 类。
- NOT_RUN：有实现但本轮未执行。

**证据与 Run**：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、请求/响应（或 33 项 `index`/维度摘要）、可选的 `/v1/models/Embedding-v1` capabilities 快照、发出命令、exit code、`elapsed`、环境快照（本 case `environment:"a"`）。

**依赖**：就绪检查；`api_client`；`Embedding-v1` 上游 tier（bge-m3）；`EmbeddingRequest.input`/`EmbeddingResponse.data` 机器契约；实现 `src/inference/embeddings.py` 与 `src/management/registry.py`（`embedding_max_batch_inputs` 仅元数据）；自动化入口 `ST-EMB-005.py`。**不依赖**其它 Case；与 ST-EMB-001（单输入）互补。
