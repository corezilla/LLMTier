<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-EMB-002 — base64 编码

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-EMB-002` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-EMB-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-EMB-002`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Embeddings 接口（parent `llmtier-system-design`），设计验证项 `VRC-INF-001`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-EMB-002` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-EMB-002` / 系统设计 §8 Embeddings 接口 / `VRC-INF-001` / normal / P0（[方案清单 `ST-EMB-002`](../llmtier-system-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：等价类划分 + 契约字段比对（base64 严格解码）
- 要测什么（责任展开）：`POST /v1/embeddings` `encoding_format=base64`：`data[0].embedding` 为 RFC 4648 base64 字符串，独立解码得 1024 个 little-endian IEEE-754 float32，全部 finite。需求 `LT-FUN-003`/`LT-OPEN-02`；机制需求 `R-INF-04`/`R-INF-07`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；契约 `CT-EMB-001`；OpenAPI `EmbeddingRequest.encoding_format`（`enum:[float,base64]`）与 `EmbeddingItem.embedding`（`contentEncoding:"base64"`，little-endian float32）。
- 明确不测什么 / 失败含义：不测 `float`（默认）表示的形状/有限性（ST-EMB-001）；不测重复不变量（ST-EMB-003）；不测未知 model（ST-EMB-004）、batch>1（ST-EMB-005）、`dimensions` 不符（ST-EMB-006）、非法 `encoding_format`（ST-EMB-007）；不对向量语义/L2 归一化数值做门限。失败含义＝base64 表示契约破坏。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `POST /v1/embeddings`；角色 `data`，只读/无状态。

```text
POST /v1/embeddings
Authorization: Bearer dev-data
Content-Type: application/json
Accept: application/json
```

- 初态构造（经公开入口）：**环境 A**（m5air 已部署实例，只读/无状态）。`Embedding-v1` 已启用（上游本地 bge-m3，LAN，TS-003）。本 case 为纯读。
- Fixture / 向量及版本：固定请求 body（`encoding_format="base64"`），随 Run manifest 存档。
- 依赖的测试资产（tests.asset-design 文档）：`api_client`；`conftest.py::pytest_configure` 就绪检查。

## 3. 输入构造

- 逐参数输入构造：固定请求：

```json
{
  "model": "Embedding-v1",
  "input": "Hello world",
  "encoding_format": "base64"
}
```

- 边界/非法取值及理由：`encoding_format` 取合法枚举值 `base64`（非 `float`、非非法值——后者属 ST-EMB-007）；`input` 取字符串；`model="Embedding-v1"`；不注入故障。独立解码所需的 `base64`/`struct` 标准库由测试侧使用，不依赖被测实现。
- 规模 / 时间域：单输入、单次请求；解码在测试侧完成。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /healthz`、`GET /readyz`（`pytest_configure` 自动执行） | §2.1 基线 |
| 2 | `resp = api_client.post("/v1/embeddings", json={"model": "Embedding-v1", "input": "Hello world", "encoding_format": "base64"})` | status / `Content-Type` / body |
| 3 | 断言 status 与形态 | `status_code == 200` 且 content-type 含 `application/json`；非错误信封 |
| 4 | 顶层键集恰为 `{object,data,model,usage}` | `object=="list"`、`model=="Embedding-v1"`；`data` 非空 |
| 5 | 取 `emb = data[0]["embedding"]` | `isinstance(emb, str)`（**必须是字符串**，不得是 JSON 数组） |
| 6 | 独立解码：`raw = base64.b64decode(emb, validate=True)`；`arr = struct.unpack("<" + "f" * (len(raw)//4), raw)` | `len(raw) == 4096`；`len(arr) == 1024` 且 `all(math.isfinite(v) for v in arr)` |
| 7 | （可选、非门限）比较缺省 float 与 base64 的向量关系 | 同源应一致，仅作旁证，不作 PASS 条件 |

- 重点关注步骤：① **类型区分**——base64 路径返回**字符串**；若返回 JSON 数组说明忽略/未实现 `encoding_format`，判 FAIL；② **严格解码**——用 `validate=True`；③ **字节数 = 4096**——1024×4 字节，避免只解出任意长度；④ **little-endian float32**——`struct.unpack("<f")`，字节序错会得到不同数值但不报错；⑤ **finite 检查**——解码后仍须 `isfinite`（base64 可承载 `NaN`/`Inf` 位模式）；⑥ **独立 Oracle**——测试侧自行 base64 解码，不能只依赖实现"返回 200 即视为合法"。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：OpenAPI `EmbeddingItem.embedding`（`contentEncoding:"base64"` + "contiguous little-endian IEEE-754 float32"）与 `bge-m3-dense-1024-v1` 的 1024 维契约。**判据语义以设计验证项 `VRC-INF-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：HTTP `200`；`Content-Type: application/json`；`X-Request-ID` 存在；顶层键集恰为 `{object,data,model,usage}`，`object=="list"`、`model=="Embedding-v1"`；`data[0]`：`object=="embedding"`、`index==0`、`embedding` 为 `str`；解码 `len(...) == 4096`，`struct.unpack("<1024f", raw)` 得 1024 个 float32，全部 finite。

## 6. 错误路径、副作用与清理

- 错误出口与表现：本 case 不应出现错误信封；任何非 200 须确认是数据库/上游可解释错误，而非把错误体读成成功。
- 副作用断言与清理：**无需 teardown**——只读 embedding 调用，不改配置/不写注入项；不删除既有资源或用户 usage。退出前确认 `/readyz` 7 tier、无未清空注入项；若误跑于 B 类实例，按计划整班销毁。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：[`tests/system/cases/ST-EMB-002.py`](../../../../tests/system/cases/ST-EMB-002.py)。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/system/cases/ST-EMB-002.py -q`。
- 实现状态：Implemented；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：`status==200`，键集/Oracle 一致，`embedding` 为合法 base64 字符串，独立解码后恰 1024 个 little-endian float32 且全部 finite。
- FAIL：status 非 200、`embedding` 非字符串、base64 非法/长度非 4096/解码非 1024/含非有限值，或以错误信封冒充成功。
- BLOCKED：测试代码/契约本身问题（解码器/断言逻辑错等）。
- SKIP：就绪检查不满足。
- INVALID：用 `127.0.0.1`/mock/替代路径冒充真实实例，或用 B 类结果冒充 A 类。
- NOT_RUN：有实现但本轮未执行。

**证据与 Run**：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、测试侧解码脚本与 `raw` 字节数/`arr` 摘要、发出命令、exit code、`elapsed`、环境快照（本 case `environment:"a"`）。

**依赖**：就绪检查；`api_client`；`Embedding-v1` 上游 tier；`EmbeddingItem.embedding` 机器契约；实现 [`src/inference/embeddings.py`](../../../../src/inference/embeddings.py)（第 53–58 行解码分支）；自动化入口 `ST-EMB-002.py`。**不依赖**其它 Case；与 ST-EMB-001（float 形态）互补。
