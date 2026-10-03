<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-USAGE-008 — store 不可用不返回空页

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-USAGE-008` |
| Document Version | `0.1.0-draft.5` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-USAGE-008.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-USAGE-008`）；责任摘要、分类与优先级以 [系统测试方案 §6](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Usage 查询接口（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-006`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-USAGE-008` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-USAGE-008` / 系统设计 §8 Usage 查询接口 / `VRC-MGMT-006` / recovery / P1（[方案清单 `ST-USAGE-008`](../llmtier-system-test-scheme.md)，**新增 Case**）；机制 `T-MET-PAGE`（[usage-metering 机制](../../../20_system_design/mechanisms/usage-metering.md) §4.7「存储不可用返回 typed 503，不用空页冒充无记录」/§7）。
- **测试方法（§2.2 方法表行）**：故障注入（存储不可用 → 503 不空页）+ 复位阶梯
- 要测什么（责任展开）：Usage store 不可用时 `GET /v1/usage` 返回 `503 usage_store_unavailable`（typed server error），**不得**以 `200 + 空 data` 冒充"无记录"；
  恢复存储后查询回到 200。实现三处收敛为同一 wire 码：`src/inference/usage.py::page` 的 `except Exception → ApiError(503,"usage_store_unavailable")`、`src/http_api/app.py::_store_read` 同映射、`_run` 的 `except sqlite3.Error` 兜底到 `usage_store_unavailable`（另有 500 `internal_error` 仅用于非 sqlite 的未知异常）。
  机制需求 `R-MET-04`（HTTP 适配层 503 显式化 / CON-METER-005）；错误目录 `ERR-STORE` → `usage_store_unavailable`；需求链 `LT-FUN-004`、`LT-INT-004/005/007`、`CT-STORE-001`。
- 明确不测什么 / 失败含义：不测正常查询内容（ST-USAGE-001/02/03）、过期 cursor（ST-USAGE-004）、主体隔离（ST-USAGE-006）、重放幂等（ST-USAGE-007）；不测**启动期** schema/引导错误（`ERR-SCHEMA`/`ERR-BOOT`）与 symlink 路径拒绝（`ERR-PATH-UNSAFE`）；不测 `DELETE /v1/usage` 的 503 分支（由同机制的 ST-AUSAGE-003 邻近，不在本 case 断言）。失败含义＝存储不可用被冒充为"无记录"。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `GET /v1/usage`（专用 B 类实例，`data`）。

```text
GET /v1/usage?from=<now-30d>&to=<now>       Authorization: Bearer dev-data
```

- 初态构造（经公开入口）：**环境 B**（临时 LLMTier 实例 `127.0.0.1:<port>` + 临时 SQLite，同机第二个进程）。执行前满足**附加（B 类）**：临时实例可启动且 `GET /healthz` 200；
  `_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。fixture（**已落地**）：本 case 使用专用 `LLMTierInstance` fixture `llmtier_b_diag_store`（[`conftest.py`](../../../../tests/system/conftest.py)，session/module-scope，独立临时 SQLite 与端口，暴露临时库路径只读访问器）+ `store_triplet`，**不得**复用或就地改动 session-scope 的 `llmtier_b`（其 `_db_path` 被其它 B 类 case 共享，就地移库会污染它们）。
  **TS-003**：本 case 不触上游 provider，但仍不得把 `127.0.0.1` 写进被测服务上游 endpoint（`_baseline_settings` 已用 LAN fake provider）。
- Fixture / 向量及版本：专用 `LLMTierInstance` + 临时库只读访问器；触发动作脚本；Run manifest 存档。
- 依赖的测试资产（tests.asset-design 文档）：专用 B 类 fixture `llmtier_b_diag_store` + `store_triplet`（**已落地**）；`dev-data` 客户端。

## 3. 输入构造

- 逐参数输入构造：
  1. 正常基线（data）：`GET /v1/usage?from=<now-30d>&to=<now>`（动态窗口，禁止硬编码）→ 期望 200 `UsagePage`，记录 `data` 长度与 `snapshot_id`。
  2. **制造存储不可用**（专用实例自有临时库，可安全操作）：把被测实例的 SQLite 三件套移开，并在原路径放置一个**目录**，使 `sqlite3.connect(<db_path>)` 失败：

```python
db = inst.db_path            # 专用实例的只读访问器（非 llmtier_b._db_path）
for suffix in ("", "-wal", "-shm"):
    src = Path(str(db) + suffix)
    if src.exists(): os.replace(src, str(src) + ".disabled")
os.mkdir(db)          # 原路径变成目录 → 连接失败（不新建空库）
```

  备用触发（记录其一即可）：`os.chmod(db, 0o000)`（注意以 root 运行时无效，故以"目录占位"为主）。
  3. 同一查询重发：`GET /v1/usage?from=<w>&to=<w>`（`api_client_b`）。
  4. 恢复：删除占位目录/新文件，把 `.disabled` 原子移回原位，再发同一查询验证恢复。
- 边界/非法取值及理由：窗口由 `now()` 生成；两次查询的 `from`/`to` 完全一致；触发只针对**专用实例进程实际使用的库路径**，不 mock 任何 HTTP 行为。
- 规模 / 时间域：3 次查询 + 1 次触发 + 1 次恢复；触发只影响专用实例。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /healthz`/`GET /readyz`（`pytest_configure` 完成，B 类附加检查同节） | 实例就绪 |
| 2 | `baseline = inst_client.get("/v1/usage", params={"from": w0, "to": w1})` | 200；记录 `data` 长度与 `snapshot_id` |
| 3 | **try**：把库移开并 `mkdir` 占位；`resp = inst_client.get("/v1/usage", params={"from": w0, "to": w1})` | status |
| 4 | 断言 | `resp.status_code == 503` |
| 5 | `err = resp.json()["error"]` | `code == "usage_store_unavailable"`、`type == "server_error"`、信封恰 5 键 `{message,type,code,param,retryable}`（`retryable` 观测并记录） |
| 6 | 断言响应**不是** `UsagePage` | body 顶层**无** `data`/`has_more`/`snapshot_id`，且**有** `error`（非空页冒充的显式反证） |
| 7 | **finally**：删除占位目录/占位空库，将 `.disabled` 文件原子移回原路径（含 `-wal`/`-shm`），随后再次 `GET` 同一查询 | `200` 且为 `UsagePage`，证明恢复 |

- 重点关注步骤：① **503 而非空页**——核心断言是 `status==503` 且 body 为 `error` 信封；若返回 `200 + {"data":[],...}` 即 FAIL；② **typed 码**——必须 `usage_store_unavailable`（`ERR-STORE`），不是 `internal_error`/`not_found`；
  ③ **触发命中真实进程**——实现每请求新建 per-thread SQLite 连接（`ThreadingHTTPServer` 每请求新线程、`_run` 末尾 `store.close()`），故"路径 → 目录"会使下一次连接失败；
  **若未来实现改为持久连接池，路径法可能失效**——此时本 case 判 BLOCKED 并登记（不得改判 PASS）；④ **专用实例隔离**——必须使用本 case 专属 `LLMTierInstance`（独立临时库/端口），**不得**碰 session-scope `llmtier_b` 的库；
  `finally` 仍须移回并二次查询 200；⑤ **不 mock**——不得 monkeypatch handler/`page` 直接抛错来伪造 503（INVALID）；⑥ **信封 identity**——恰 5 键、`type` 由 503≥500 导出 `server_error`；
  ⑦ **恢复校验**——`finally` 移回库三件套后必须二次查询为 200，否则判 BLOCKED/FAIL。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：机制"存储不可用 ⇒ typed 503，不用空页冒充无记录" + OpenAPI `UsageStoreUnavailable`/`ErrorEnvelope` + `ERR-STORE`。**判据语义以设计验证项 `VRC-MGMT-006` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：基线：`200`，合法 `UsagePage`；存储不可用：HTTP `503`；body `{"error":{"message":<str>,"type":"server_error","code":"usage_store_unavailable","param":null,"retryable":<bool>}}`；**无** `data`/`has_more`/`snapshot_id` 顶层键；恢复：`200`，`UsagePage`。

## 6. 错误路径、副作用与清理

- 错误出口与表现：返回 `200`（尤以 `data:[]` 空页冒充）、或码非 `usage_store_unavailable`、或信封不合规；或恢复后无法回到 200（残留破坏）。
- 副作用断言与清理：**强制 teardown（`finally`）**——把 `.disabled` 文件（含 `-wal`/`-shm`）原子移回原路径、删除占位目录/占位空库，并二次查询验证 200；库属本 case **专用实例**，不得留其在存储不可用状态。专用实例整班结束由 fixture `stop()` + `rm -rf` 临时目录销毁。无法安全恢复时保留证据并报 BLOCKED，不做无边界清理。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/system/cases/ST-USAGE-008.py`（已实现；专用 fixture `llmtier_b_diag_store` + `StoreTriplet`）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/system/cases/ST-USAGE-008.py -q`。
- 实现状态：Implemented；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：存储不可用时 `503 + usage_store_unavailable + type=server_error` 且响应形态为错误信封（非 `UsagePage`）；`finally` 恢复后查询回到 `200`。
- FAIL：返回 `200`（尤以 `data:[]` 空页冒充）、或码非 `usage_store_unavailable`、或信封不合规；或恢复后无法回到 200（残留破坏）。
- BLOCKED：路径法因连接池失效（存储变为持久连接后"路径→目录"不再触发）、或无法安全恢复 / 无法取得专用实例的临时库路径——**可重试**，须写 `required_resolution` 与 `reproduction_cmd`；专用 fixture 已落地，不再构成 BLOCKED。
- SKIP：B 类临时实例不可用、附加前置不满足。
- INVALID：mock/替代路径伪造 503（未真正使存储不可用）。
- NOT_RUN：本 Case 有实现，本轮未执行时记 `NOT_RUN`。

**证据与 Run**：Run ID=`<date>/B-api`；保存原始 status/headers/body（脱敏后）、发出命令、exit code、`elapsed`、环境快照。**额外证据**：基线查询、触发动作（移动的文件清单与 `os.mkdir` 结果、`db_path`）、故障查询的原始 status/headers/body、恢复动作与恢复后查询、动态窗口值、环境快照（`/healthz`/`/readyz`）；B 类 `db_schema_version` 取临时库 `schema_meta.version`（本 case `environment:"b"`）。

**依赖**：附加（B 类）就绪检查；**本 case 专用 `LLMTierInstance` fixture**（独立临时库/端口，**已落地** `llmtier_b_diag_store` + `store_triplet`，暴露临时库只读访问器；
**不得**复用 session-scope `llmtier_b`）；机制 [`usage-metering` §4.7/§7](../../../20_system_design/mechanisms/usage-metering.md)；
`UsageStoreUnavailable`/`ErrorEnvelope` 机器契约；`ERR-STORE`。自动化入口 `ST-USAGE-008.py`（已实现）。**不依赖**其它 Case；与 ST-OBSDIAG-001 的 `ERR-STORE` 503 语义相邻（同一 `_store_read` 映射），但各自独立执行；
与 ST-USAGE-004（TTL 过期，非存储故障）严格区分。
