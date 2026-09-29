# OBS-ALIAS-04 — 别名 deployments diagnostics（GET+PATCH）

- **Case ID**：`OBS-ALIAS-04`
- **标题**：`/tier/admin/v1/deployments/{id}/diagnostics` 与 `/v1/deployments/{id}/diagnostics` 的 GET/PATCH 由同一 handler 服务：status 与响应体等价（PATCH 允许服务端 `updated_at` 差异）。
- **目的（被测契约）**：验证注入配置别名的**等价契约**。被测端点/规则：`GET`+`PATCH /tier/admin/v1/deployments/{deployment_id}/diagnostics` 是 `/v1/deployments/{deployment_id}/diagnostics` 的精确别名（openapi `x-llmtier-contract-aliases`），同一 handler、相同 `InjectionView[]` 形状、相同 `admin` 鉴权（[`src/http_api/app.py`](../../../../src/http_api/app.py) 两分支调用同一 `app.diagnostics.injections/set_injections`）；GET body 应逐字节等价；PATCH 因 `updated_at` 为服务端时间戳，等价判定为**除 `updated_at` 外逐字段相等**（[测试设计 §4.10](../llmtier-api-test-specification.md) 的"逐字节"在含服务端时间戳的写路径上须按此理解）。设计验证项 `VRC-DIAG-004`；机制 `T-TRUST-SHARED` + `T-OBS-INJECT`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §5.1 `IF-OBS-INJECT`）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）；机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`x-llmtier-contract-aliases`、`InjectionView`）。**不证明什么**：不证明写入/校验语义本身（OBS-DEPL-01/02/03/04 在扁平路径断言）、不证明别名 diagnostics 开关（OBS-ALIAS-01）、不证明其它别名、不证明别名鉴权负向（AUTH-08）。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）；前置=§2.1 附加（B 类）；`depl_b` 存在且 healthy；fixture：`llmtier_b` + `admin_client_b`（[测试设计 §4.4](../llmtier-api-test-specification.md)）。初始状态=基线，`diagnostic_injections` 为空。**写 case：PATCH 后必须清空注入**（[测试设计 §2.8](../llmtier-api-test-specification.md)）。
- **输入与构造**：
  - **GET 等价**：`GET /v1/deployments/depl_b/diagnostics` 与 `GET /tier/admin/v1/deployments/depl_b/diagnostics`（先写入一组固定注入使页非空，或先比空数组）。
  - **PATCH 等价**：`B = {"items":[{"type":"delay","config":{"delay_ms":1000},"enabled":true}]}`；分别 `PATCH /v1/deployments/depl_b/diagnostics` 与 `PATCH /tier/admin/v1/deployments/depl_b/diagnostics` body 同为 `B`（upsert 幂等，按 `(deployment_id,type)` 冲突更新，`id` 不变，`updated_at` 刷新）。
  - 边界点：PATCH 返回含 `updated_at`（服务端 `now()`），两次调用时间不同 → `updated_at` 可不同；`id` 在 upsert 下保持不变；`X-Request-ID` 不参与，也不列入 Oracle。
- **执行过程（逐步调用）**：
  1. `PATCH /v1/deployments/depl_b/diagnostics` body `B` → 记录 `patch_flat`（status/body）。
  2. `GET /v1/deployments/depl_b/diagnostics` 与别名同路径 → 断言两 `200` 且 `resp.content` 逐字节相等（GET 无时间戳，须完全等价）。
  3. `PATCH /tier/admin/v1/deployments/depl_b/diagnostics` body 同 `B` → 记录 `patch_alias`。
  4. 断言 `patch_alias.status_code == patch_flat.status_code == 200`；解析两数组，断言长度相同、按 `type` 排序后每个 `(id, deployment_id, type, config, enabled)` **相等**；仅允许 `updated_at` 不同（记录差异并说明）。
  5. （可选旁证）再 `GET` 两路径比对一次（此时两路径都已写入同一状态 → 应逐字节相等）。
  6. （teardown，`finally` 内）`PATCH {"items":[]}`（任一路径）→ 200；再 `GET` 两路径确认为 `[]` 且逐字节相等。
- **重点关注步骤**：① **GET 逐字节**——GET 无服务端时间戳，两路径必须 `content` 完全相同。② **PATCH 的时间戳例外**——`updated_at` 是服务端 `now()`，两次调用必然不同；等价判定必须**排除**该字段（否则会误判 FAIL）；`id`/`config`/`enabled`/`deployment_id`/`type` 必须相等。③ **upsert 一致性**——同 `type` 冲突更新，两路径都不得新增重复项。④ **只比 body**——`X-Request-ID` 不参与、不列入 Oracle。⑤ **鉴权等价**——都需 `admin`（正向；负向 AUTH-08）。⑥ **teardown 完整性**——`finally` 清空并双向 GET 校验，绝不把启用注入留给同 session 的 DP-RESP-11/22。⑦ **降级/存储**——`_UnavailableDiagnostics` 两路径同 handler 返回 `[]`（等价成立，判 BLOCKED/SKIP 说明语义）；`503 usage_store_unavailable` 判 BLOCKED/SKIP。注意：本 case 当前 `MISSING`（§3.2），无 `at_obs_alias_04.py`。
- **期望结果与独立 Oracle**：独立 Oracle = openapi `x-llmtier-contract-aliases` 的同一 handler/相同形状 + `InjectionView` wire 形态。
  - GET：两路径 `200`，`body_flat == body_alias`（逐字节）。
  - PATCH：两路径 `200`，`InjectionView[]` 同长且每项 `(id, deployment_id, type, config, enabled)` 相等，`updated_at` 允许不同（服务端时间戳）。
  - teardown：清空后两路径 GET 均 `[]` 且逐字节相等。
  - **fail-open**：降级实例两路径同样 `[]`（等价成立）；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**；GET body 不等价或 PATCH 关键字段不等 → **FAIL**。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：GET 两路径逐字节相等；PATCH 两路径 status 相同且除 `updated_at` 外逐字段相等；teardown 清空成功。
  - **FAIL**：GET 不等价、PATCH 关键字段不等/别名 404、或 teardown 未清空。
  - **BLOCKED**：测试代码/契约问题、降级实例、存储不可达——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类实例不可用、依赖 fixture 未满足（含 `depl_b` 非 healthy）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9。
  - **INVALID**：用 mock/替代路径冒充真实实例，或未真正比较两路径却按等价判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
- **证据与 Run**：保存两路径 GET body 与逐字节对比、两路径 PATCH 请求/响应（含 `updated_at` 差异说明）、teardown 与最终 GET、命令/exit code/`elapsed`、环境快照（`/healthz` + 注入前后 `/deployments/depl_b/diagnostics`）；落位与契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。
- **清理与复位**：**必须 teardown（`finally` 强制）**——`PATCH {"items":[]}` 清空并双向 GET 校验；不改 `prov_b`/`depl_b`、不重指 endpoint、不删除既有资源。离开前确认无未清空注入项。 B 类整班结束由 fixture `stop()` + `rm -rf` 临时目录（[测试设计 §2.8/§4.7](../llmtier-api-test-specification.md)）。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md)（B 类附加）；`llmtier_b`/`admin_client_b` fixture（[§4.4](../llmtier-api-test-specification.md)）；openapi `x-llmtier-contract-aliases`；实现 [`src/http_api/app.py`](../../../../src/http_api/app.py)（`/tier/admin/v1/deployments/.../diagnostics` 分支）、[`src/libdiag/injections.py`](../../../../src/libdiag/injections.py)。自动化入口 `at_obs_alias_04.py`（**当前 `MISSING`，尚未实现**）。**不依赖**其它 Case；与 OBS-DEPL-01/02（注入读写）、AUTH-08 语义相邻，与其它别名并列但各自独立执行。
