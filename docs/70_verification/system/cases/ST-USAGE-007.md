<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-USAGE-007 — 分页重放幂等

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-USAGE-007` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-USAGE-007.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-USAGE-007`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Usage 查询接口（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-006`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-USAGE-007` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-USAGE-007` / 系统设计 §8 Usage 查询接口 / `VRC-MGMT-006` / boundary / P1（[方案清单 `ST-USAGE-007`](../llmtier-system-test-scheme.md)，**新增 Case**）；机制 `T-MET-PAGE`（[usage-metering 机制](../../../20_system_design/mechanisms/usage-metering.md) §4.7/CON-METER-004，INV-6「旧页不受后续更正影响」、Step 5 冻结视图）。
- **测试方法（§1.5 方法表行）**：边界值抽样（cursor 重放幂等/冻结视图）+ 契约字段比对
- 要测什么（责任展开）：同一 usage `cursor` **重放**返回同一冻结的 record version 成员：后续页重放逐字段相同，不新建 `snapshot`、不推进 head；首屏冻结后新增记录对旧页不可见。首屏在单事务内写 `query_snapshots` 并冻结有序成员 `(principal, request_id, record_version)`；
  后续页仅按 `<snapshot_id>:<offset>` 读**冻结视图** `query_snapshot_items`（含 `frozen_view_json`）；读操作不写账本。实现 `src/inference/usage.py::UsageRecorder._page`。
  机制需求 `R-MET-02`；需求链 `LT-FUN-004`、`LT-INT-004/005/007`、`CT-USAGE-001`。
- 明确不测什么 / 失败含义：不测过期 cursor（ST-USAGE-004）、主体绑定/跨主体拒绝（ST-USAGE-006）、分页稳定排序本身（ST-USAGE-003）、store 不可用（ST-USAGE-008）；不测跨请求的 exactly-once 重试语义（本版本不定义）；不测 `recorded_at`/版本推进（由 ST-USAGE-002 的 `T-MET-FINAL` 承接）。失败含义＝cursor 重放幂等/快照冻结契约破坏。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `GET /v1/usage`（`data`）与前置 `POST /v1/embeddings`（3+1 次）。

```text
GET /v1/usage?from=<w>&to=<w>&limit=1                 → page1（无 cursor，创建 snapshot sid）
GET /v1/usage?from=<w>&to=<w>&limit=1&cursor=<sid>:1  → page2（冻结视图 offset 1）
GET /v1/usage?from=<w>&to=<w>&limit=1&cursor=<sid>:1  → page2'（重放）
GET /v1/usage?from=<w>&to=<w>&limit=1&cursor=<sid>:1  → page2''（追加一条记录后再重放）
```

- 初态构造（经公开入口）：**环境 A**（m5air 已部署实例，只读/无状态）。初始状态 = m5air 现有基线。embeddings tier `Embedding-v1`/`dep_local_bge_m3`。**自含前置**：发 3 次 `POST /v1/embeddings`（固定输入）得到 `rid_1..rid_3`；用**紧致动态窗口**（`from=now-5min`、`to=now+1min`，由 `now()` 生成，禁止硬编码）圈定；分页全程 `from`/`to` 逐字节不变（否则 `filter_digest` 不匹配 → 400 `invalid_request`）。
- Fixture / 向量及版本：4 次 embeddings（`rid_1..rid_4`）；紧致动态窗口；Run manifest 存档。
- 依赖的测试资产（tests.asset-design 文档）：`api_client`（`consumer`）；embeddings tier `Embedding-v1`。

## 3. 输入构造

- 逐参数输入构造：分页序列见上；另发第 4 次 embeddings（`rid_4`）在 page1 之后，用于验证"插入对旧页不可见"。
- 边界/非法取值及理由：cursor 取首屏 `next_cursor` 原样（或 `f"{sid}:1"`）；每次重放带**同一** `from`/`to`/`limit`；`sid` 取自 page1 `snapshot_id`。
- 规模 / 时间域：4 次写 + 多次分页/重放；读操作不写账本。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /healthz`/`GET /readyz`（`pytest_configure` 完成，不重复） | §2.1 基线 |
| 2 | 发 3 次 embeddings，断 200 | 捕获 `rid_1..rid_3` |
| 3 | `page1 = GET ?from&to&limit=1` | 200，`snapshot_id=sid`，`next_cursor=c`（形如 `<sid>:1`） |
| 4 | `page2 = GET ?...&cursor=c` | 200 且 `snapshot_id==sid`，记录 `page2.data`（含 `request_id`+`record_version`）与 `next_cursor`/`has_more` |
| 5 | `page2r = GET ?...&cursor=c`（重放） | `page2r.data == page2.data`（逐字段，**含 `record_version`**）、`snapshot_id == sid`、`next_cursor`/`has_more` 相等 |
| 6 | 发第 4 次 embeddings（`rid_4`，落在同一窗口） | — |
| 7 | `page2r2 = GET ?...&cursor=c`（再次重放） | `page2r2.data == page2.data`（旧页**不受**新增 `rid_4` 影响；`rid_4` 不得出现在重放结果中） |
| 8 | （对照，不改变判定）`fresh = GET ?from&to&limit=200`（无 cursor，新快照） | `rid_4` **出现**在新快照中 |

- 重点关注步骤：① **重放相等必须含 `record_version`**——冻结的是 `(request_id, record_version)` 成员，版本号必须一致；② **snapshot 不因重放新建**——`snapshot_id` 在三/四次请求间恒为 `sid`；
  ③ **旧页冻结**——page1 后新增 `rid_4` 对 `cursor=c` 的重放不可见（INV-6）；④ **读不改账本**——重放不推进 `usage_heads.head_record_version`；⑤ **filter 一致**——重放的 `from`/`to`/`limit` 必须与原 cursor 完全一致，否则 400 `invalid_request`（属误操作，非本 case 期望）；
  ⑥ **cursor 为 null 兜底**——若 `limit=1` 窗口内仅 1 条，`next_cursor=null`，改用 `f"{sid}:1"` 生成第二页 cursor，但需确保窗口内确有 ≥2 条；⑦ **末页 invariant**——沿 cursor 走到 `has_more=false` 时 `next_cursor is null`（同 `snapshot_id`）。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：机制 CON-METER-004/Step 5（冻结视图按 `sid:offset` 读）+ INV-6（旧页不受后续更正/插入影响），不依赖实现的返回顺序/内容。**判据语义以设计验证项 `VRC-MGMT-006` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：page2 与两次重放：`data` 逐字段相等（含 `request_id`、`record_version`）；`snapshot_id` 恒为 `sid`；`next_cursor`/`has_more` 相等；page1 之后新增的 `rid_4` 不出现在 `cursor=c` 的任何重放结果中；新快照（无 cursor）中可见。

## 6. 错误路径、副作用与清理

- 错误出口与表现：重放结果不一致（含 `record_version` 漂移）、重放生成新 `snapshot_id`、旧页泄漏新增记录、或 `next_cursor`/`has_more` 漂移。
- 副作用断言与清理：**无需 teardown**——4 次 embeddings 属被测行为，不删用户 usage；查询只创建 10 分钟 TTL 快照；不改 provider/deployment/service-level、不写注入。退出前 `/readyz` 仍 7 tier；若误跑 B 类则按计划销毁。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/system/cases/ST-USAGE-007.py`（已实现；含末页 invariant）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/system/cases/ST-USAGE-007.py -q`。
- 实现状态：Implemented；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：步骤 5 与 7 的重放逐字段相等、`snapshot_id` 稳定、`rid_4` 不进旧页，且步骤 8 新快照可见 `rid_4`。
- FAIL：重放结果不一致（含 `record_version` 漂移）、重放生成新 `snapshot_id`、旧页泄漏新增记录、或 `next_cursor`/`has_more` 漂移。
- BLOCKED：断言逻辑/契约问题、embeddings 前置无法命中。
- SKIP：就绪检查不满足。
- INVALID：mock/替代路径冒充真实路径。
- NOT_RUN：本 Case 有实现，本轮未执行时记 `NOT_RUN`。

**证据与 Run**：Run ID=`<date>/A-api`；保存 4 次前置 embeddings 的 `X-Request-ID`、page1/page2/各次重放/新快照的完整响应（`request_id`、`record_version`、`snapshot_id`、`next_cursor`、`has_more`）、cursor 实际值、动态窗口值、发出命令、exit code、`elapsed`、环境快照（本 case `environment:"a"`）。

**依赖**：就绪检查；`api_client`；embeddings tier `Embedding-v1`；机制 [`usage-metering` §4.7/CON-METER-004/INV-6](../../../20_system_design/mechanisms/usage-metering.md)；重放/幂等边界说明；`UsagePage`/`UsageRecord` 机器契约。自动化入口 `ST-USAGE-007.py`（已实现）。**不依赖**其它 Case；与 ST-USAGE-003（游标推进）、ST-USAGE-004（过期）、ST-USAGE-006（主体绑定）共享 cursor 语义但各自独立执行。
