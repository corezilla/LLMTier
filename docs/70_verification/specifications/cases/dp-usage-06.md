<!-- STD_DOCUMENT_COVER_BEGIN -->
# DP-USAGE-06 — 主体隔离：data ⊆ admin

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `DP-USAGE-06` |
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
| Canonical Path | `docs/70_verification/specifications/cases/dp-usage-06.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`DP-USAGE-06` / 系统设计 §8 Usage 查询接口 / `VRC-MGMT-006` / normal / P1（[方案清单 `DP-USAGE-06`](../../schemes/llmtier-system-test-scheme.md)）；机制 `T-TRUST-SHARED`、`R-MET-02`（[usage-metering 机制](../../../20_system_design/mechanisms/usage-metering.md) §4.6/§4.7 与 [access-trust 机制](../../../20_system_design/mechanisms/access-trust.md)）。
- 要测什么（责任展开）：`GET /v1/usage` 的主体隔离：`data` 凭据只见到本主体（`consumer`）的 record，`admin` 凭据见到全局，`data` 结果集 ⊆ `admin` 结果集；data 产生的 cursor 以 admin 重放被拒 `403 permission_denied`。OpenAPI `listUsage` description 明确 "With a data credential the caller sees only its own records; with the admin credential the response includes all principals"；实现 `src/http_api/app.py` 经 `_auth_either()`→`authenticate_any()` 得 `is_admin`，`src/inference/usage.py::_page` 在 `not admin` 时追加 `h.principal_id=?` 过滤，admin 不加；cursor 的 `authorization_digest = sha256("admin"|principal)` 与 `principal_id` 绑定，跨主体重放 → `403 permission_denied`（**openapi↔code 差异须登记**：实现区分——过期→`400 cursor_expired`、跨主体重放→`403 permission_denied`、filter 不匹配→`400 invalid_request`；本 case 以 **code 为准**取 `403 permission_denied`）。需求链 `LT-FUN-004`、`LT-INT-004/005/007`、`CT-USAGE-001`。
- 明确不测什么 / 失败含义：不测 LAN 无 token 的免登录解析（`AUTH-01`，且注意无 `Authorization` 会被解析为 **admin** 角色而非 data）；不测分页内容（DP-USAGE-03）、过期 cursor（DP-USAGE-04）、同主体 cursor 重放幂等（DP-USAGE-07）、`DELETE /v1/usage` 的 admin 校验（ADM-USAGE-03）、store 不可用（DP-USAGE-08）。失败含义＝主体隔离/ cursor 绑定契约破坏。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `GET /v1/usage`（`data` 与 `admin` 两种凭据）与前置 `POST /v1/embeddings`（两主体各一次）。

```text
POST /v1/embeddings                                 Bearer dev-data  → rid_d
POST /v1/embeddings                                 Bearer dev-admin → rid_a
GET  /v1/usage?from&to&request_id=<rid>
GET  /v1/usage?from&to&limit=1&cursor=<c_d>         Bearer dev-admin（跨主体重放）
```

- 初态构造（经公开入口）：**环境 A**（m5air 已部署实例，角色 `data` + `admin`，只读/无状态）。初始状态 = m5air 现有基线；embeddings tier `Embedding-v1`/`dep_local_bge_m3` 可路由。**关键**：必须用**显式** `Authorization` 头区分角色；**不得**用无头 LAN trust 请求——`src/http_api/auth.py::unauthenticated_principal` 对无头发起者按 `role="admin"` 授予共享 admin 主体，会使 data 侧隔离无从体现。窗口由 `constants.recent_window()` 动态生成。
- Fixture / 向量及版本：`api_client`（data 主体 `consumer`）、`admin_client`（admin 主体 `operator`）；两次前置 embeddings（固定 body）与 `X-Request-ID`；Run manifest 存档。
- 依赖的测试资产（tests.asset-design 文档）：`api_client`/`admin_client`；embeddings tier `Embedding-v1`。

## 3. 输入构造

- 逐参数输入构造：分别以两个主体各发一次 embeddings，再按 `request_id` 过滤查询（把窗口噪声排除）：

```text
POST /v1/embeddings  (api_client,  Bearer dev-data)   → 捕获 X-Request-ID = rid_d
POST /v1/embeddings  (admin_client, Bearer dev-admin) → 捕获 X-Request-ID = rid_a
GET  /v1/usage?from=<w>&to=<w>&request_id=<rid_d>   (Bearer dev-data)   → 期望 1 条
GET  /v1/usage?from=<w>&to=<w>&request_id=<rid_a>   (Bearer dev-data)   → 期望 0 条
GET  /v1/usage?from=<w>&to=<w>&request_id=<rid_a>   (Bearer dev-admin)  → 期望 1 条
```

跨主体 cursor：先 `GET /v1/usage?from&to&limit=1`（dev-data）取 `next_cursor=c_d`，再以 dev-admin 重放 `?from&to&limit=1&cursor=c_d`。

- 边界/非法取值及理由：embeddings body 固定（`model="Embedding-v1"`、固定输入）；`request_id` 用响应头 `X-Request-ID` 实际值；`from`/`to` 为同一动态窗口。
- 规模 / 时间域：2 次写 + 数次查询；按 `request_id` 过滤使断言确定。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /healthz`/`GET /readyz`（`pytest_configure` 完成，不重复） | §2.1 基线 |
| 2 | 以 `api_client` `POST /v1/embeddings` 取 `rid_d`；以 `admin_client` 同法取 `rid_a` | 两者非空且不同 |
| 3 | `data_d = api_client.get("/v1/usage", params={"from":w0,"to":w1,"request_id":rid_d})` | 200 且 `data` 恰 1 条、`request_id==rid_d` |
| 4 | `data_a = api_client.get(..., request_id=rid_a)` | 200 且 `data == []`（data 不见 admin 主体记录） |
| 5 | `admin_a = admin_client.get(..., request_id=rid_a)` | 200 且 `data` 恰 1 条、`request_id==rid_a` |
| 6 | `admin_d = admin_client.get(..., request_id=rid_d)` | 200 且含 `rid_d` |
| 7 | **子集核对**：`data_wide = api_client.get("?from&to&limit=200")`、`admin_wide = admin_client.get("?from&to&limit=200")` | `{r.request_id for r in data_wide.data} ⊆ {r.request_id for r in admin_wide.data}` |
| 8 | **跨主体 cursor**：`first = api_client.get("?from&to&limit=1")`；`c_d = first.next_cursor`（若 null 用 `f"{first.snapshot_id}:0"`）；`admin_client.get("?from&to&limit=1&cursor=c_d")` | `status_code==403`、`error.code=="permission_denied"`、`error.type=="request_error"` |

- 重点关注步骤：① **必须用显式 token**——无头请求被解析为 admin，会破坏 data 侧断言；② **principal 名不固定写死**——`consumer`/`operator` 是当前实现默认（无 `X-Principal-ID` 时）；断言应基于"同主体可见、异主体不可见"，避免硬编码 `consumer`；③ **用 `request_id` 过滤**——A 类有全局历史，按 id 过滤是唯一确定构造；`rid_a` 在 data 侧应为**空数组**（200 而非 403/404），这是隔离语义；④ **子集而非相等**——admin 全局含其它主体，只断言 `data ⊆ admin`；⑤ **cursor 绑主体**——跨主体重放期望 `403 permission_denied`，不要与过期/不匹配混判；⑥ **cursor 为 null 的兜底**——若窗口内 `limit=1` 无更多记录，`next_cursor=null`，可用 `<snapshot_id>:0` 构同一快照的 cursor；⑦ **MISSING 语义**——无实现是缺口（NOT_RUN），不是跳过。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：OpenAPI `listUsage` description 的隔离语义 + 机制 cursor 绑定（`R-MET-02`：cursor 绑定 principal + 当前授权 + 原 filter）；跨主体 cursor 的拒绝码以**实现 code 为准**取 `403 permission_denied`（openapi 已修正对齐），不依赖实现返回顺序/内容。**判据语义以设计验证项 `VRC-MGMT-006` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：`rid_d`：data 见 1 条、admin 见 ≥1 条；`rid_a`：data 见 0 条（`data==[]`）、admin 见 1 条；宽窗口：data 的 `request_id` 集合 ⊆ admin 的 `request_id` 集合；跨主体 cursor：HTTP `403`，`error.code=="permission_denied"`，`error.type=="request_error"`，信封恰 5 键。

## 6. 错误路径、副作用与清理

- 错误出口与表现：data 侧见到 admin 主体记录、或 admin 侧看不到自身记录、或子集不成立、或跨主体 cursor 未被拒（返回 200/其它码）。
- 副作用断言与清理：**无需额外 teardown**——两次 embeddings 属被测行为，不删用户 usage；查询只创建 10 分钟 TTL 快照；不改 provider/deployment/service-level、不写注入。退出前 `/readyz` 仍 7 tier；若误跑 B 类则按计划销毁。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/system/api_test_v03/at_dp_usage_06.py`（当前 **MISSING，尚未实现**）。
- 单 Case 执行命令（实现后）：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_usage_06.py -q`。
- 实现状态：Planned（MISSING）；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：步骤 3–8 全部 match（同主体可见、异主体在 data 侧不可见、子集成立、跨主体 cursor 403）。
- FAIL：data 侧见到 admin 主体记录、或 admin 侧看不到自身记录、或子集不成立、或跨主体 cursor 未被拒（返回 200/其它码）。
- BLOCKED：断言逻辑/契约问题、双主体前置无法命中。
- SKIP：就绪检查不满足。
- INVALID：用无头/带 token 混淆冒充角色、mock/替代路径冒充真实路径。
- NOT_RUN：本 Case 自动化入口 `MISSING`；缺口引用方案 §9。

**证据与 Run**：Run ID=`<date>/A-api`；保存两次前置 embeddings（含 `X-Request-ID`）、各主体查询的请求/响应（`request_id`、`data` 长度、cursor 值）、宽窗口集合、跨主体重放的原始响应、动态窗口值、发出命令、exit code、`elapsed`、环境快照（本 case `environment:"a"`）。

**依赖**：就绪检查与鉴权模型；`api_client`/`admin_client`；embeddings tier `Embedding-v1`；机制 [`usage-metering` §4.6/§4.7](../../../20_system_design/mechanisms/usage-metering.md)、[`access-trust`](../../../20_system_design/mechanisms/access-trust.md)；`listUsage` 机器契约。自动化入口 `at_dp_usage_06.py`（**当前 `MISSING`**）。**不依赖**其它 Case；与 AUTH-01（LAN 免登录）、AUTH-03（data 访问 admin 面 403）区分但机制相邻；与 DP-USAGE-07（同主体重放）互补。
