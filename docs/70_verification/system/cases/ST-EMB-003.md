<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-EMB-003 — 不变量（同输入 ×5）

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-EMB-003` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-EMB-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-EMB-003`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Embeddings 接口（parent `llmtier-system-design`），设计验证项 `VRC-INF-002`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-EMB-003` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-EMB-003` / 系统设计 §8 Embeddings 接口 / `VRC-INF-002` / normal / P1（[方案清单 `ST-EMB-003`](../llmtier-system-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：等价类划分 + 契约字段比对 + 重复采样不变量（同输入 ×5，cosine>0.99）
- 要测什么（责任展开）：`POST /v1/embeddings` 同一输入连续 5 次：每次 200、维度均 1024，且 5 个向量两两 cosine 相似度 `> 0.99`。`model="Embedding-v1"`、`input` 固定为同一字符串，连续发起 5 次 `POST /v1/embeddings`（`encoding_format` 缺省 `float`）。需求 `LT-FUN-003`/`LT-OPEN-02`；机制需求 `R-INF-04`/`R-INF-07`（[inference-stream 机制](../../../20_system_design/mechanisms/inference-stream.md)）；契约 `CT-EMB-001`；方案正常场景明确"ST-EMB-001/02/03：维度 1024、base64 严格解码、同输入不变量（cosine > 0.99）"。
- 明确不测什么 / 失败含义：不测"逐位相等"（本 case 接受高相似而非 bitwise 相同）；不测不同输入间的区分度；不测 base64 形态（ST-EMB-002）；不测未知 model（ST-EMB-004）、batch>1（ST-EMB-005）、`dimensions`（ST-EMB-006）、非法 `encoding_format`（ST-EMB-007）；不对向量语义/答案做断言。失败含义＝同输入稳定性契约破坏。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `POST /v1/embeddings`；角色 `data`，只读/无状态。

```text
POST /v1/embeddings
Authorization: Bearer dev-data
Content-Type: application/json
Accept: application/json
```

- 初态构造（经公开入口）：**环境 A**（m5air 已部署实例，只读/无状态）。`Embedding-v1` 已启用（上游本地 bge-m3，LAN，TS-003）。本 case 为纯读，5 次调用无状态。
- Fixture / 向量及版本：固定请求 body（5 次完全相同），固定 prompt 随 Run manifest 存档。
- 依赖的测试资产（tests.asset-design 文档）：`api_client`；`conftest.py::pytest_configure` 就绪检查。

## 3. 输入构造

- 逐参数输入构造：固定请求（连续 5 次，body 完全相同）：

```json
{
  "model": "Embedding-v1",
  "input": "Hello world"
}
```

- 边界/非法取值及理由：`input` 在 5 次间**逐字符相同**（同 prompt，按方案固定输入存档）；`encoding_format` 缺省 `float`；`model` 固定；不注入故障；不并发（串行 5 次，避免把并发/准入影响混入不变量判定）。相似度阈值取自方案正常场景（`> 0.99`）。
- 规模 / 时间域：5 次串行调用；10 组两两比较；不发布时延 SLO。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /healthz`、`GET /readyz`（`pytest_configure` 自动执行） | §2.1 基线 |
| 2 | 循环 5 次：`resp = api_client.post("/v1/embeddings", json={"model": "Embedding-v1", "input": "Hello world"})` | 每次 `status_code == 200`、`data[0].object == "embedding"`、`embedding` 非空数值数组且 `len == 1024`，收集向量到 `vectors` |
| 3 | 对每一对 `(i,j)`（`0<=i<j<5`）计算 `cosine(vectors[i], vectors[j])` | 断言 `> 0.99` |
| 4 | 记录 5 次 `X-Request-ID` 与 `elapsed` | 仅供证据，不参与 PASS/FAIL |

- 重点关注步骤：① **同输入一致性**——5 次必须使用**完全相同的 body**（尤其 `input` 与省略字段一致），任一字段漂移会使比较失去意义；② **相似度而非相等**——Oracle 是 `cosine > 0.99`（软阈值，容忍上游推理的浮点/批次差异），**不是**逐位相等；③ **维度一致性**——5 个向量都须 1024，长度不一致须先判 FAIL；④ **cosine 实现独立**——测试侧自行计算点积/范数（见 [`at_dp_emb_03.py`](../../../../tests/system/api_test_v03/at_dp_emb_03.py) 的 `_cosine`），不调用被测实现的归一化；⑤ **零向量保护**——范数为 0 时 cosine 未定义，测试实现返回 0（判 FAIL），须显式处理；⑥ **串行执行**——避免并发导致的不相关差异。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导："同逻辑 model + 同输入 ⇒ 高相似（cosine > 0.99）"的稳定性规则，与具体向量值无关。**判据语义以设计验证项 `VRC-INF-002` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：5 次 HTTP 均 `200`；`Content-Type: application/json`；每次 `data[0].object=="embedding"`、`len(embedding)==1024`、元素为有限数值；任意两向量 `cosine > 0.99`（测试侧独立计算）。

## 6. 错误路径、副作用与清理

- 错误出口与表现：任一次非 200 或某对 cosine `<= 0.99` 均构成契约违反；不得因向量不完全相同而误判 FAIL。
- 副作用断言与清理：**无需 teardown**——5 次只读调用，不改配置/不写注入项；不删除既有资源或用户 usage。退出前确认 `/readyz` 7 tier、无未清空注入项；若误跑于 B 类实例，按计划整班销毁。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：[`tests/system/api_test_v03/at_dp_emb_03.py`](../../../../tests/system/api_test_v03/at_dp_emb_03.py)。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_emb_03.py -q`。
- 实现状态：Implemented；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：5 次均 200 且维度 1024，且 10 个两两组合的 cosine 全部 `> 0.99`。
- FAIL：任一次非 200、维度非 1024、或某对 cosine `<= 0.99`（不满足不变量契约）。
- BLOCKED：测试代码/契约本身问题（cosine 实现错、断言不可实现）。
- SKIP：就绪检查不满足。
- INVALID：用 `127.0.0.1`/mock/替代路径冒充真实实例，或对每次输入做了不同构造却声称"同输入"。
- NOT_RUN：有实现但本轮未执行。

**证据与 Run**：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、5 次请求/响应（或各自向量摘要）、测试侧 cosine 矩阵、发出命令、exit code、`elapsed`、环境快照（本 case `environment:"a"`）。

**依赖**：就绪检查；`api_client`；`Embedding-v1` 上游 tier；方案不变量阈值；实现 `src/inference/embeddings.py`；自动化入口 `at_dp_emb_03.py`。**不依赖**其它 Case；与 ST-EMB-001/02 共享成功路径但独立执行。
