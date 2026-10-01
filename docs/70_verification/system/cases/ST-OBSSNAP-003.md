<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-OBSSNAP-003 — 诊断快照 store 不可用 503

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-OBSSNAP-003` |
| Document Version | `0.1.0-draft.3` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-10-01` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-OBSSNAP-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-OBSSNAP-003` / 系统设计 §8 诊断快照接口（GET /v1/diagnostics/snapshots） / `VRC-DIAG-002` / recovery / P1（[方案清单 `ST-OBSSNAP-003`](../llmtier-system-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：故障注入（诊断存储不可用 → 503）+ 复位阶梯

- 要测什么（责任展开）：诊断 store 不可用时 `GET /v1/diagnostics/snapshots` 返回 `503 usage_store_unavailable`（typed server error），**不得**以 200/空结果冒充"无数据"；恢复存储后回到 200。实现经 [`_store_read`](../../../../src/http_api/app.py) 或 `mutate` 把存储异常收敛为 `usage_store_unavailable`。

- 明确不测什么 / 失败含义：不测正常读/写语义（其正向 Case）；不测 400 校验（缺窗/非法 cursor/缺 items）；不测启动期 schema/引导错误（`ERR-SCHEMA`/`ERR-BOOT`）与 symlink 路径拒绝（`ERR-PATH-UNSAFE`）；不测 `/v1/usage` 的 503（ST-USAGE-008）。失败含义＝存储不可用被冒充为空结果/静默降级。

**目的（被测契约）**：验证 **观测读/写面的存储不可用显式化**。被测端点/规则：`GET /v1/diagnostics/snapshots`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json)，声明 `503`）；GET 经 [`_store_read`](../../../../src/http_api/app.py) 包裹，非 `ApiError` 异常 → `ApiError(503, "usage_store_unavailable")`；PATCH 经 [`AdminService.mutate`](../../../../src/management/admin.py) 触发存储异常，由 `_run` 的 `sqlite3.Error` 兜底到同码。设计验证项 `VRC-DIAG-002`；机制 `CON-METER-005`/`ERR-STORE`。**不证明什么**：不测成功语义/400 校验/启动期错误/`/v1/usage` 503。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite，同机第二个进程）。执行前满足**附加（B 类）**：实例可启动且 `GET /healthz` 200；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。fixture（**已落地**）：本 case 使用专用 `LLMTierInstance` fixture `llmtier_b_diag_store`（[`conftest.py`](../../../../tests/system/conftest.py)，独立临时 SQLite 与端口，暴露临时库路径只读访问器）+ `store_triplet`（三件套移开/恢复工厂），**不得**复用或就地改动 session-scope 的 `llmtier_b`（其库被其它 B 类 case 共享，就地移库会污染它们）。TS-003：本 case 不触上游。
- **被测入口**：

  ```http
  GET /v1/diagnostics/snapshots HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```

## 3. 输入构造

- **逐参数输入构造**：
  1. 基线：`GET /v1/diagnostics/snapshots`（admin）→ 期望 200 + {"items": [...], "next_cursor": ...}。
  2. **制造存储不可用**（专用实例自有临时库，可安全操作）：把被测实例的 SQLite 三件套（`<db>`、`<db>-wal`、`<db>-shm`）移开，并在原路径放置一个**目录**，使 `sqlite3.connect(<db_path>)` 失败（同 ST-USAGE-008 技法）。
  3. 故障：再次 `GET /v1/diagnostics/snapshots`（admin）→ 期望 503。
  4. 恢复：把三件套原子移回、删除占位目录，再次 `GET /v1/diagnostics/snapshots` → 期望 200。

- **边界/非法取值及理由**：以"路径→目录"使每次新建连接失败；实现每请求新建 per-thread 连接（`_run` 末尾 `store.close()`），故技法有效。**若未来改为持久连接池，路径法可能失效**——此时判 BLOCKED 并登记，不得改判 PASS。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 启动专用实例，`GET /v1/diagnostics/snapshots`（admin） | 200 + {"items": [...], "next_cursor": ...} |
| 2 | 移开 SQLite 三件套并在原路径 `mkdir` | `db_path` → 目录 |
| 3 | `GET /v1/diagnostics/snapshots`（admin） | `resp.status_code == 503` |
| 4 | `err = resp.json()["error"]` | `code == "usage_store_unavailable"`、`type == "server_error"`、信封恰 5 键 |
| 5 | （teardown，`finally`）移回三件套、删占位目录，再次 `GET /v1/diagnostics/snapshots` | 200 + {"items": [...], "next_cursor": ...} |

- **重点关注步骤**：① **503 而非空结果**——核心断言是 `status==503` 且 body 为错误信封；若 200 + 空结果即 FAIL；② **typed 码**——必须 `usage_store_unavailable`（`ERR-STORE`），不是 `internal_error`/`not_found`；③ **触发命中真实进程**——技法依赖每请求新建连接；④ **专用实例隔离**——不得碰 session-scope `llmtier_b` 的库；`finally` 必须恢复；⑤ **不 mock**——不得 monkeypatch 直接抛错伪造 503（INVALID）；⑥ **信封 identity**——恰 5 键、`type` 由 503≥500 导出 `server_error`。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **独立 Oracle 来源与推导**：OpenAPI `ErrorEnvelope` + `ERR-STORE`（不依赖实现内部）。
  - 基线：`200`，合法 {"items": [...], "next_cursor": ...}；存储不可用：HTTP `503`；body `{"error":{"message":<str>,"type":"server_error","code":"usage_store_unavailable","param":null,"retryable":<bool>}}`；恢复：`200`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：存储不可用时 `503 + usage_store_unavailable + type=server_error`；`finally` 恢复后回到 `200`。
  - **FAIL**：返回 `200`（含空结果冒充）、码非 `usage_store_unavailable`、信封不合规、或恢复后无法回到 200。
  - **BLOCKED**：路径法因连接池失效（存储变为持久连接后"路径→目录"不再触发）、或无法安全恢复 / 无法取得专用实例的临时库路径——**可重试**，须写 `required_resolution` 与 `reproduction_cmd`；专用 fixture 已落地，不再构成 BLOCKED。
  - **SKIP**：B 类临时实例不可用、附加前置不满足。
  - **INVALID**：mock/替代路径伪造 503（未真正使存储不可用）。
  - **NOT_RUN**：有实现但本轮未执行。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：返回 200/空结果、码非 `usage_store_unavailable`、信封不合规，或恢复后无法回到 200 → FAIL。
- **副作用断言与清理**：**强制 teardown（`finally`）**——把三件套（含 `-wal`/`-shm`）原子移回原路径、删除占位目录，并二次请求验证 200；库属专用实例，不得留在不可用状态。专用实例整班 `stop()` + `rm -rf` 销毁。无法安全恢复时保留证据并报 BLOCKED。

## 7. 自动化位置与状态

- **测试文件 / 测试函数**：`tests/system/cases/ST-OBSSNAP-003.py`（已实现；依赖专用实例 fixture）。
- **单 Case 执行命令**：`PYTHONPATH=src python3 -m pytest tests/system/cases/ST-OBSSNAP-003.py -q`。
- **实现状态**：Implemented（`ST-OBSSNAP-003.py` 已断言 store 不可用 → 503 `usage_store_unavailable` + 恢复 200；B 类运行通过）；执行与 Verdict 归 Run 报告。

**证据与 Run**：保存基线请求/响应、触发动作（移动文件清单与 `mkdir` 结果、`db_path`）、故障请求原始 status/headers/body、恢复动作与恢复后请求、发出命令、exit code、`elapsed`、环境快照（本 case `environment:"b"`）。

**依赖**：附加（B 类）就绪检查；**专用 `LLMTierInstance` fixture**（独立库/端口，**已落地** `llmtier_b_diag_store` + `store_triplet`）；实现 `src/http_api/app.py::_store_read`、`src/libdiag/*`；错误目录 `ERR-STORE`。**不依赖**其它 Case；与 ST-USAGE-008 同技法但端点不同。

