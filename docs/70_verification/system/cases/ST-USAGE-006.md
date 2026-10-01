<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-USAGE-006 — 主体隔离：data ⊆ admin

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-USAGE-006` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-USAGE-006.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-USAGE-006`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Usage 查询接口（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-006`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-USAGE-006` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-USAGE-006` / 系统设计 §8 Usage 查询接口 / `VRC-MGMT-006` / normal / P1（[方案清单 `ST-USAGE-006`](../llmtier-system-test-scheme.md)）；机制 `T-TRUST-SHARED`、`R-MET-02`（[usage-metering 机制](../../../20_system_design/mechanisms/usage-metering.md) §4.6/§4.7 与 [access-trust 机制](../../../20_system_design/mechanisms/access-trust.md)）。
- **测试方法（§1.5 方法表行）**：等价类划分 + 契约字段比对 + 鉴权/角色隔离冒烟（主体隔离）
- 要测什么（责任展开）：`GET /v1/usage` 的主体隔离：`data` 凭据只见到本主体的 record（脚本以 `X-Principal-ID` 指派两个不同 data 主体），`admin` 凭据见到全局，`data` 结果集 ⊆ `admin` 结果集；data 产生的 cursor 以 admin 重放被拒 `403 permission_denied`。OpenAPI `listUsage` description 明确 "With a data credential the caller sees only its own records; with the admin credential the response includes all principals"；实现 `src/http_api/app.py` 经 `_auth_either()`→`authenticate_any()` 得 `is_admin`，`src/inference/usage.py::_page` 在 `not admin` 时追加 `h.principal_id=?` 过滤，admin 不加；cursor 的 `authorization_digest = sha256("admin"|principal)` 与 `principal_id` 绑定，跨主体重放 → `403 permission_denied`（**openapi↔code 差异须登记**：实现区分——过期→`400 cursor_expired`、跨主体重放→`403 permission_denied`、filter 不匹配→`400 invalid_request`；本 case 以 **code 为准**取 `403 permission_denied`）。需求链 `LT-FUN-004`、`LT-INT-004/005/007`、`CT-USAGE-001`。
- 明确不测什么 / 失败含义：不测 LAN 无 token 的免登录解析（`ST-AUTH-001`，且注意无 `Authorization` 会被解析为 **admin** 角色而非 data）；不测分页内容（ST-USAGE-003）、过期 cursor（ST-USAGE-004）、同主体 cursor 重放幂等（ST-USAGE-007）、`DELETE /v1/usage` 的 admin 校验（ST-AUSAGE-003）、store 不可用（ST-USAGE-008）。失败含义＝主体隔离/ cursor 绑定契约破坏。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `GET /v1/usage`（`data` 与 `admin` 两种凭据）与前置 `POST /v1/embeddings`（两主体各一次）。

```text
POST /v1/embeddings  Bearer dev-data + X-Principal-ID=<A>   → rid_a
POST /v1/embeddings  Bearer dev-data + X-Principal-ID=<B>   → rid_b
GET  /v1/usage?from&to&request_id=<rid>              Bearer dev-data（+ X-Principal-ID）
GET  /v1/usage?from&to&limit=1&cursor=<c_a>          Bearer dev-admin（跨主体重放）
```

> **实现事实（embeddings 是 data-plane 写入）**：`app.py` 的 `/v1/embeddings` 路由走
> `self._auth()`（默认 `role="data"`），**不接受 admin 凭据**（`Bearer dev-admin` → 403
> `permission_denied`）。故本 case 用**两个不同 data 主体**（同一 `Bearer dev-data` +
> 不同 `X-Principal-ID`）构造隔离，而非「dev-data vs dev-admin」。admin 仅用于全局可见
> 与跨主体 cursor 重放。

- 初态构造（经公开入口）：**环境 A**（m5air 已部署实例，角色 `data` + `admin`，只读/无状态）。初始状态 = m5air 现有基线；embeddings tier `Embedding-v1`/`dep_local_bge_m3` 可路由。**关键**：必须用**显式** `Authorization` 头区分角色；**不得**用无头 LAN trust 请求——`src/http_api/auth.py::unauthenticated_principal` 对无头发起者按 `role="admin"` 授予共享 admin 主体，会使 data 侧隔离无从体现。窗口由 `constants.recent_window()` 动态生成。
- Fixture / 向量及版本：`api_client`（data 主体 `consumer`）、`admin_client`（admin 主体 `operator`）；两次前置 embeddings（固定 body）与 `X-Request-ID`；Run manifest 存档。
- 依赖的测试资产（tests.asset-design 文档）：`api_client`/`admin_client`；embeddings tier `Embedding-v1`。

## 3. 输入构造

- 逐参数输入构造：分别以两个主体各发一次 embeddings，再按 `request_id` 过滤查询（把窗口噪声排除）：

```text
POST /v1/embeddings  (Bearer dev-data, X-Principal-ID=A) → 捕获 X-Request-ID = rid_a
POST /v1/embeddings  (Bearer dev-data, X-Principal-ID=B) → 捕获 X-Request-ID = rid_b
GET  /v1/usage?from=<w>&to=<w>&request_id=<rid_a>   (A) → 期望 1 条
GET  /v1/usage?from=<w>&to=<w>&request_id=<rid_b>   (A) → 期望 0 条（隔离）
GET  /v1/usage?from=<w>&to=<w>&request_id=<rid_b>   (admin) → 期望 1 条
```

跨主体 cursor：先 `GET /v1/usage?from&to&limit=1`（主体 A）取 `next_cursor=c_a`，再以 admin 重放 `?from&to&limit=1&cursor=c_a`。

- 边界/非法取值及理由：embeddings body 固定（`model="Embedding-v1"`、固定输入）；`request_id` 用响应头 `X-Request-ID` 实际值；`from`/`to` 为同一动态窗口。
- 规模 / 时间域：2 次写 + 数次查询；按 `request_id` 过滤使断言确定。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /healthz`/`GET /readyz`（`pytest_configure` 完成，不重复） | §2.1 基线 |
| 2 | 以 `api_client` + `X-Principal-ID=A` 发 embeddings 取 `rid_a`；以 `X-Principal-ID=B` 取 `rid_b` | 两者非空且不同 |
| 3 | `own = api_client.get("/v1/usage", params={"from":w0,"to":w1,"request_id":rid_a}, headers=A)` | 200 且可见集合恰 `{rid_a}` |
| 4 | `other = api_client.get(..., request_id=rid_b, headers=A)` | 200 且 `data == []`（A 不见 B 主体记录） |
| 5 | `admin_b = admin_client.get(..., request_id=rid_b)` | 200 且含 `rid_b` |
| 6 | `admin_a = admin_client.get(..., request_id=rid_a)` | 200 且含 `rid_a` |
| 7 | **子集核对（按本 case 自建 rid 界定）**：`data_wide = api_client.get("?from&to&limit=200")` 取 `data_visible = ids(data_wide) ∩ {rid_a, rid_b}`；再对 `rid ∈ {rid_a, rid_b}` 逐个 `admin_client.get("?from&to&request_id=rid")` 取 `admin_visible` | `data_visible == {rid_a}`（A 只见到自建记录、看不到 rid_b）且 `data_visible ⊆ admin_visible` 且 `admin_visible == {rid_a, rid_b}` |
| 8 | **跨主体 cursor**：`first = api_client.get("?from&to&limit=1")`；`c_d = first.next_cursor`（若 null 用 `f"{first.snapshot_id}:0"`）；`admin_client.get("?from&to&limit=1&cursor=c_d")` | `status_code==403`、`error.code=="permission_denied"`、`error.type=="request_error"` |

- 重点关注步骤：① **必须用显式 token**——无头请求被解析为 admin，会破坏 data 侧断言；② **principal 名不固定写死**——脚本用 `X-Principal-ID` 显式指派两个随机 data 主体；断言基于"同主体可见、异主体不可见"，不硬编码默认主体名；③ **用 `request_id` 过滤**——A 类有全局历史，按 id 过滤是唯一确定构造；`rid_a` 在 data 侧应为**空数组**（200 而非 403/404），这是隔离语义；④ **子集而非相等**——admin 全局含其它主体，只断言 `data ⊆ admin`；⑤ **cursor 绑主体**——跨主体重放期望 `403 permission_denied`，不要与过期/不匹配混判；⑥ **cursor 为 null 的兜底**——若窗口内 `limit=1` 无更多记录，`next_cursor=null`，可用 `<snapshot_id>:0` 构同一快照的 cursor；⑦ **窗口在写后计算**——先发 embeddings 再生成窗口，且 `to` 留头部余量，避免边界竞态（S2）。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：OpenAPI `listUsage` description 的隔离语义 + 机制 cursor 绑定（`R-MET-02`：cursor 绑定 principal + 当前授权 + 原 filter）；跨主体 cursor 的拒绝码以**实现 code 为准**取 `403 permission_denied`（openapi 已修正对齐），不依赖实现返回顺序/内容。**判据语义以设计验证项 `VRC-MGMT-006` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：`rid_a`：data 见 1 条、admin 见 1 条；`rid_b`：data 见 0 条（`data==[]`）、admin 见 1 条；子集：data 在宽查询中可见的**自建 rid 集合**（`ids(data_wide) ∩ {rid_a, rid_b}`）恰为 `{rid_a}`，且 ⊆ admin 的对应集合（`{rid_a, rid_b}`）；跨主体 cursor：HTTP `403`，`error.code=="permission_denied"`，`error.type=="request_error"`，信封恰 5 键。**子集口径**：共享实例窗口内记录数远超一页且分页按 `recorded_at` 升序，两个各自截断的首页无可比性——子集只在**本 case 自建 rid 的有界集合**上断言（每 rid 用 `request_id` 过滤，确定且与实例历史规模无关）。

## 6. 错误路径、副作用与清理

- 错误出口与表现：data 侧见到 admin 主体记录（或 `rid_b`）、或 admin 侧看不到自建记录、或子集（在自建 rid 集合上）不成立、或跨主体 cursor 未被拒（返回 200/其它码）。**注意**：不得以两个各自截断的宽窗口首页比较集合大小——那会把分页截断误判为隔离破坏（本 case 原始失败即此构造缺陷，见 §7 偏差登记）。
- 副作用断言与清理：**无需额外 teardown**——两次 embeddings 属被测行为，不删用户 usage；查询只创建 10 分钟 TTL 快照；不改 provider/deployment/service-level、不写注入。退出前 `/readyz` 仍 7 tier；若误跑 B 类则按计划销毁。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/system/cases/ST-USAGE-006.py::test_dp_usage_06_subject_isolation`（已实现）。
- 单 Case 执行命令（实现后）：`PYTHONPATH=src python3 -m pytest tests/system/cases/ST-USAGE-006.py -q`。
- 实现状态：Implemented（`ST-USAGE-006.py`）；执行与 Verdict 归 Run 报告。

> **实现 vs 设计偏差（2026-09-30，已登记）**：本 case §2/§3 设计用 `admin_client`（Bearer dev-admin）发 `POST /v1/embeddings` 构造 admin 主体 record。当前实现 `app.py:232` 的 embeddings 路由走 `self._auth()`（默认 `role="data"`），admin 凭据被拒（403 `permission_denied`）——embeddings 是 data-plane 写入，不接受 admin 凭据。`ST-USAGE-006.py` 改用**两个不同 data 主体**（同一 `Bearer dev-data` + 不同 `X-Principal-ID`）演示同/异主体可见性 + admin 全局可见 + `data ⊆ admin` + 跨主体 cursor 403；隔离语义等价且对当前 code 有效。
>
> **子集构造修正（2026-09-30，已登记）**：原 step 7 直接比较 `?limit=200` 的两个宽窗口首页集合。共享 m5air 实例窗口内记录数远超一页（实测 >5000 条）且 `_page` 按 `recorded_at` **升序**分页，data 侧按主体过滤后首页与 admin 全局首页互不覆盖，`data ⊆ admin` 因**分页截断**而假失败（并非隔离破坏）。修正为：data 宽查询仅取 `ids(data_wide) ∩ {rid_a, rid_b}`（本 case 自建记录），admin 侧对每个自建 rid 用 `?request_id=` 精确查询；断言 `data_visible == {rid_a}`、`data_visible ⊆ admin_visible == {rid_a, rid_b}`。口径与隔离契约一致，且与实例历史规模无关。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：步骤 3–8 全部 match（同主体可见、异主体在 data 侧不可见、子集成立、跨主体 cursor 403）。
- FAIL：data 侧见到 admin 主体记录、或 admin 侧看不到自身记录、或子集不成立、或跨主体 cursor 未被拒（返回 200/其它码）。
- BLOCKED：断言逻辑/契约问题、双主体前置无法命中。
- SKIP：就绪检查不满足。
- INVALID：用无头/带 token 混淆冒充角色、mock/替代路径冒充真实路径。
- NOT_RUN：本 Case 有实现（`ST-USAGE-006.py`），本轮未执行时记 `NOT_RUN`。

**证据与 Run**：Run ID=`<date>/A-api`；保存两次前置 embeddings（含 `X-Request-ID`）、各主体查询的请求/响应（`request_id`、`data` 长度、cursor 值）、宽窗口集合、跨主体重放的原始响应、动态窗口值、发出命令、exit code、`elapsed`、环境快照（本 case `environment:"a"`）。

**依赖**：就绪检查与鉴权模型；`api_client`/`admin_client`；embeddings tier `Embedding-v1`；机制 [`usage-metering` §4.6/§4.7](../../../20_system_design/mechanisms/usage-metering.md)、[`access-trust`](../../../20_system_design/mechanisms/access-trust.md)；`listUsage` 机器契约。自动化入口 `ST-USAGE-006.py`（已实现）。**不依赖**其它 Case；与 ST-AUTH-001（LAN 免登录）、ST-AUTH-003（data 访问 admin 面 403）区分但机制相邻；与 ST-USAGE-007（同主体重放）互补。
