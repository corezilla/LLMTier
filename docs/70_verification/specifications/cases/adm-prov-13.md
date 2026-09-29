# ADM-PROV-13 — usage 子对象更新

- **Case ID**：`ADM-PROV-13`（与 §3.2 权威清单一致；本文件名 `adm-prov-13.md`，唯一对应）。
- **标题**：`PATCH /v1/providers/{id}` 更新 `usage` 子对象（`max_concurrent_requests`）：HTTP 200，且回读可见新值，随后复位。
- **目的（被测契约）**：验证 Management Provider CRUD 的**嵌套配置更新契约**。被测端点/规则：`PATCH /v1/providers/{id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `updateProvider`，`ProviderPatch.usage → ProviderUsageProfileWrite`）；[`registry.update_provider`](../../../../src/management/registry.py) 对 `usage` 走 `_usage_values(body.get("usage"), values["kind"], current)` 合并/校验并写 `provider_usage_profiles`（`version` 推进），且**清空该 provider 的 usage 快照**（`DELETE FROM provider_usage_snapshots`）；`If-Match` 必须匹配当前 ETag；成功 `200` + 新 `ProviderView`（`usage.max_concurrent_requests` 为新值）。设计验证项 `VRC-MGMT-002`；机制 `T-CFG-CAS`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明标量字段更新（ADM-PROV-05）、不证明 `usage` 校验负向（非法 `usage_provider`/`*_ref`/负值 → 400，见 `_usage_values`，未单列 case）、不证明 `/v1/providers/{id}/usage` 快照刷新（ADM-PROV-USAGE-*）；本 case 只验证合法 `usage` 子对象的持久化与复位。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[§2.3](../llmtier-api-test-specification.md)/§2.4）。执行前须满足[§2.1](../llmtier-api-test-specification.md) **附加（B 类）**：实例 `/healthz` 200；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。fixture（[§4.4](../llmtier-api-test-specification.md)）：`llmtier_b`、`admin_client_b`。初始状态：m5air 上级基线由 `_baseline_settings` 提供；`depl_b` probe `healthy`。本 case 直接更新 baseline `prov_b` 的 usage（**必须复位**，见清理）。
- **输入与构造**：固定两步（先取真实 ETag，再 PATCH）：
  ```http
  GET /v1/providers/prov_b HTTP/1.1
  Authorization: Bearer dev-admin

  PATCH /v1/providers/prov_b HTTP/1.1
  Authorization: Bearer dev-admin
  If-Match: "<GET 返回的 ETag>"
  Content-Type: application/json
  ```
  ```json
  {"usage": {"max_concurrent_requests": 5}}
  ```
  构造点：`If-Match` **取自 `GET` 响应头**（绝不硬编码；B 类前序写 case 会推进 `prov_b` 版本）；`usage.max_concurrent_requests=5`（≥1 的合法整数，区别于默认值 1，便于观测生效）；PATCH 体仅含 `usage`（`minProperties:1` 满足）。不注入故障；不构造非法输入（非法 usage 字段负向不在本 case）。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `current = admin_client_b.get("/v1/providers/prov_b")`；断言 `200`，记 `original = current.json()["usage"]["max_concurrent_requests"]`、`original_version = current.json()["version"]`、`etag = current.headers["ETag"]`。
  3. `patch = admin_client_b.patch("/v1/providers/prov_b", json={"usage":{"max_concurrent_requests":5}}, headers={"If-Match": etag})`；断言 `200`。
  4. 解析 `patch.json()`：`usage.max_concurrent_requests == 5`；`patch.json()["version"] > original_version`；响应头含新 `ETag`。
  5. `after = admin_client_b.get("/v1/providers/prov_b")`；断言 `200`、`usage.max_concurrent_requests == 5`（持久化）。
  6. （teardown，`finally` 强制）`restore = GET`；若 `restore.usage.max_concurrent_requests != original`，以 `restore` 的 ETag `PATCH` 回 `{"usage":{"max_concurrent_requests": original}}`；再 `GET` 断言已复位。
- **重点关注步骤**：① **嵌套更新语义**——`usage` 子对象按白名单键合并，只改提交字段，其余保留；② **`If-Match` 实取**——B 类共享 session，`prov_b` 版本受前序 case 影响，硬编码必 412；③ **持久化回读**——第 5 步确认 5 生效而非仅响应回显；④ **容量约束**——`max_concurrent_requests` 必须 ≥1（`_usage_values` 校验），本 case 用 5；⑤ **快照副作用**——更新 `usage` 会删除该 provider 的 usage 快照（`provider_usage_snapshots`），这是既定行为，报告须登记；⑥ **复位必达**——`prov_b` 是全 B 类 session 的 baseline，必须恢复原值（版本会前进，但值复原），否则影响后继 case（如 ADM-PROV-10 取 ETag 仍能工作，但值被污染）。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ProviderPatch.usage`/`ProviderUsageProfileView` + `_usage_values` 规则。
  - GET：`200`，`usage.max_concurrent_requests == original`（默认 1）。
  - PATCH：`200`；body `usage.max_concurrent_requests == 5`；`version` 推进；新 `ETag`。
  - 回读：`200` 且值 5。
  - teardown：恢复 `original` 并回读确认。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：PATCH `200` 且 `usage.max_concurrent_requests==5`、`version` 推进；回读一致；teardown 复位成功。
  - **FAIL**：任意步骤 status/字段不符、值未持久化、或 teardown 未复位（污染 baseline）。
  - **BLOCKED**：无法执行/无法判定且可重试（fixture/断言逻辑问题）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：硬编码/伪造 ETag 绕过 CAS、或用 mock 冒充——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-api-test-specification.md)：Run ID=`<date>/B-api`；保存请求与原始响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：初始 GET、PATCH 请求/响应（含 `If-Match`/`ETag`）、回读、复位 PATCH/回读。
- **清理与复位**：**必须 teardown（`finally` 强制）**——把 `prov_b.usage.max_concurrent_requests` 恢复为初始 `original`（先 `GET` 取新 ETag 再 PATCH）；不改 `prov_b` 其它字段/`depl_b`、不写注入。B 类整班结束由 fixture `stop()` + `rm -rf` 销毁（[§4.7](../llmtier-api-test-specification.md)）。离开前 `GET` 确认已复位、`/readyz` 7 tier。
- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b` 与 baseline `prov_b`（[§4.4](../llmtier-api-test-specification.md)）；`ProviderPatch`/`ProviderUsageProfileWrite`/`ProviderUsageProfileView` 机器契约；`registry.update_provider`/`_usage_values`；机制 `T-CFG-CAS`；自动化入口 [`at_adm_prov_13.py`](../../../../tests/system/api_test_v03/at_adm_prov_13.py)。**不依赖**其它 Case（自复位）；与 ADM-PROV-05 同属 PATCH 但本 case 专测嵌套 `usage`。
