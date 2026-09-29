# ADM-SL-04 — 更新 service-level

- **Case ID**：`ADM-SL-04`（与 §3.2 权威清单一致；本文件名 `adm-sl-04.md`，唯一对应）。
- **标题**：`PATCH /v1/service-levels/{id}` 携带正确 `If-Match` 切换 `enabled`：HTTP 200 + 字段生效 + `version`/`ETag` 推进。
- **目的（被测契约）**：验证 Service Level 的**乐观并发更新契约**。被测端点/规则：`PATCH /v1/service-levels/{service_level_id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `updateServiceLevel`，body `ServiceLevelPatch`=`{deployment_ids?,enabled?}` 且 `minProperties:1`，`additionalProperties:false`；header `If-Match` 必填），[`registry.update_service_level`](../../../../src/management/registry.py) 仅接受 `deployment_ids`/`enabled`，`If-Match` 必须等于当前 ETag `"<id>.v<N>"`，成功 `200` + 新 `ServiceLevelView` + `ETag: "<id>.v<N+1>"`。设计验证项 `VRC-MGMT-002`；机制 `T-CFG-CAS`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明非法字段 400（ADM-SL-04b）、不证明成员能力/向量空间冲突 409（ADM-SL-06/07）、不证明删除 409（ADM-SL-05）、不证明缺/过期 `If-Match` 412（未单独构 SL 的 412 Case，语义同 ADM-PROV-06/07）、不证明并发两写者竞争（[测试设计 §5](../llmtier-api-test-specification.md) 不单独构 case）。
- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[测试设计 §2.3/§2.4](../llmtier-api-test-specification.md)）；前置=§2.1 附加（B 类）；fixture `admin_client_b`（[测试设计 §4.4](../llmtier-api-test-specification.md)）；初始状态=`Junior` 存在且 `enabled=true`、`deployment_ids=["depl_b"]`。
- **输入与构造**：
  ```http
  PATCH /v1/service-levels/Junior HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  If-Match: "<从 GET 读取的真实 ETag>"
  Content-Type: application/json
  ```
  ```json
  {"enabled": false}
  ```
  构造点：先 `GET /v1/service-levels/Junior` 取 `original_etag`（**绝不硬编码 `"Junior.v1"`**）；PATCH body 只含 `enabled`（`additionalProperties:false`，`enabled` 为 bool）。不注入故障。
- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `get = admin_client_b.get("/v1/service-levels/Junior")`；断言 200；记 `original_etag = get.headers["ETag"]`、`original_version = body["version"]`；断言 `body["enabled"] is True`。
  3. `patch = admin_client_b.patch("/v1/service-levels/Junior", json={"enabled":False}, headers={"If-Match": original_etag})`。
  4. 断言 `patch.status_code == 200`；`updated = patch.json()`：`enabled is False`、`version > original_version`（期望 `+1`）；`patch.headers` 含 `ETag`。
  5. （teardown，`finally` 内）重新 `GET` 取当前 ETag（版本可能已推进），若 `enabled is not True` 则 PATCH `{"enabled": True}` 复位；断言复位后 `enabled is True`。
- **重点关注步骤**：① **真实 ETag**——必须取自刚做的 `GET` 响应头；硬编码版本会在创建/并发后失效；② **版本推进**——`version` 必 `+1` 且新 ETag `"Junior.v<N+1>"` 与之一致；③ **字段生效**——`enabled` 回显更新值，`deployment_ids`/`capabilities` 未提交字段保持原值（PATCH 是合并语义，[`update_service_level`](../../../../src/management/registry.py) 用 `current_ids`）；④ **412 恢复**——若因并发得 412，须重新 `GET` 取新 ETag 再 PATCH，不覆盖式重发（本 case 正常路径不触发）；⑤ **teardown 到位**——复位必须用最新 ETag；复位后不得把后续 Case 置于 `enabled=false` 状态（`enabled=false` 会使 `registry.candidates` 返回空，影响路由类 Case）。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ServiceLevelPatch`/`ServiceLevelView` + ETag/CAS 规则。
  - PATCH：`200`；body `enabled is False`、`version == original+1`；响应头 `ETag == "Junior.v<original+1>"`。
  - 回读：`GET` → 200，`enabled` 持久化为 false。
  - teardown：PATCH 复位 → 200，`enabled is True`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：PATCH `200` + `enabled` 生效 + `version` 推进 + 新 ETag 一致；teardown 成功复位为 true。
  - **FAIL**：status 错、`version` 未推进、`enabled` 未生效、ETag 不符、或 teardown 未复位。
  - **BLOCKED**：fixture/断言逻辑问题——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：B 类临时实例不可用——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：硬编码/伪造 ETag 绕过真实 `GET` 语义，或用 `127.0.0.1` 作上游 endpoint——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
- **证据与 Run**：保存GET/PATCH/复位 PATCH 的请求与原始响应（含 `If-Match`/`ETag` 头，脱敏后）、发出命令、exit code、`elapsed`、环境快照；落位与契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。
- **清理与复位**：**必须 teardown（`finally` 强制）**——把 `Junior.enabled` 恢复为 `true`（用最新 ETag）；不改其它 tier、不删资源、不写注入。退出前确认 `GET /v1/service-levels/Junior` 的 `enabled is True`、`/readyz` 仍 ready。 B 类整班结束由 fixture `stop()` + `rm -rf` 临时目录（[测试设计 §2.8/§4.7](../llmtier-api-test-specification.md)）。
- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[§4.4](../llmtier-api-test-specification.md)）；`ServiceLevelPatch`/`ServiceLevelView` 机器契约；`registry.update_service_level`/`_etag`；机制 `T-CFG-CAS`。自动化入口 [`at_adm_sl_04.py`](../../../../tests/system/api_test_v03/at_adm_sl_04.py)。**不依赖**其它 Case；与 ADM-SL-04b（非法字段 400）互补但各自独立执行。
