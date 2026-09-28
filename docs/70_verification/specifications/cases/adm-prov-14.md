# ADM-PROV-14 — provider 不泄露 secret

- **Case ID**：`ADM-PROV-14`（与 §3.2 权威清单一致；本文件名 `adm-prov-14.md`，唯一对应）。
- **标题**：`GET /v1/providers` 与 `GET /v1/providers/{id}` **响应永不回显 secret 值**——仅 `has_secret` 布尔与（写-only 的）`secret_ref` 引用，响应体不含解析后的秘密。
- **目的（被测契约）**：验证 Management Provider CRUD 的**秘密不泄露契约**。被测端点/规则：`GET /v1/providers`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listProviders`）与 `GET /v1/providers/{id}`（`getProvider`），角色 `admin`；`ProviderView` 为 `additionalProperties:false`，**不含 `secret_ref` 键**，仅以 `has_secret:boolean` 表达"是否配置了秘密"；[`registry.get_provider`](../../../../src/management/registry.py) 只拼装 `has_secret = bool(row["secret_ref"])`，从不解引用/回传秘密值或引用串。设计验证项 `VRC-MGMT-001`；机制 `T-CFG-SECRET`；需求/机制链 `LT-FUN-005`、`LT-SEC-001`、`R-CFG-01`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明写入/更新（ADM-PROV-02/05）、不证明 `secret_ref` 格式校验（ADM-PROV-12）、不证明审计/日志脱敏（ADM-AUDIT-01、ADM-LOGS-01）、不证明 `/v1/providers/{id}/models` 或 `/usage` 的出站凭据处理；本 case 只覆盖 provider **读取响应体**的安全不变量。
  > 实现状态：本 case 在 §3.2 的自动化入口为 **`MISSING`**（尚无 `at_adm_prov_14.py`），`设计状态` 现为 `待写`；本设计完成后其文档状态达 `已写`，但**实现缺口**仍阻断 release Gate（[测试设计 §9](../llmtier-api-test-specification.md)：MISSING = NOT_RUN 缺口，不得冒充 PASS）。
- **前置与环境**：**环境 A**（m5air 已部署实例 `http://192.168.1.9:8181`，角色 `admin`，只读；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 **6 项就绪检查**，其中 **§2.1.5** 已保证 `provider_omlx_m5mac` 的 `GET` 返回 `has_secret=true` 且 `secret_ref` 为 `file:` 引用（本 case 的天然被测样本）；由 `pytest_configure` 自动执行；任一失败 → 整班 BLOCKED/SKIP。fixture 见[测试设计 §4.4](../llmtier-api-test-specification.md)：`admin_client`（`Bearer dev-admin`）。初始状态 = m5air 现有 3 provider / 4 deployment / 7 tier；至少一个 provider（`provider_omlx_m5mac`）具有秘密引用。
- **输入与构造**：固定两个只读请求（无 body）：
  ```http
  GET /v1/providers HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json

  GET /v1/providers/provider_omlx_m5mac HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：列表 + 详情两个读路径；详情对象选 `provider_omlx_m5mac`（§2.1.5 保证 `has_secret=true`）。**独立 Oracle 的"秘密值"来源**：实现侧的解析秘密（`file:` 指向的 key 文件内容）与上游 OMLX Bearer 字面 `9832`——但**不得**把 secret 值本身写入证据；证据归档前必须按[测试设计 §10](../llmtier-api-test-specification.md) 把 `Authorization`、上游 `9832`、key 文件内容替换为 `<redacted>`。不注入故障；不构造非法输入。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（`pytest_configure` 自动执行，本 case 不重复）。
  2. `list_resp = admin_client.get("/v1/providers")`；断言 `200`；解析 `data[]`。
  3. 断言每个元素**不含**顶层或嵌套键 `secret_ref`，且无任何字段携带形如秘密值/`env:`/`file:` 引用串的值（`endpoint`/`name`/`id` 等业务字段除外，但它们不得等于解析后的秘密）。
  4. `detail_resp = admin_client.get("/v1/providers/provider_omlx_m5mac")`；断言 `200`。
  5. 断言 `detail` 的键集恰为 `ProviderView` 9 键 `{id,name,kind,endpoint,has_secret,enabled,usage,request_usage,version}`（`additionalProperties:false`）；`has_secret is True`；**不存在** `secret_ref` 键。
  6. 对列表与详情的**原始响应字节**做否定扫描：断言不含 key 文件内容、不含上游 Bearer `9832`、不含请求的 `Authorization` 值（`dev-admin`）；执行前先把真实秘密读入本地变量但**不回写证据**。
- **重点关注步骤**：① **`secret_ref` 缺失是契约**——`ProviderView` 无该键；若出现即为泄露面回归，判 FAIL；② **`has_secret` 只表达存在性**——布尔 `true` 不得伴随任何引用串/值；③ **否定扫描覆盖原始字节**——不能只检查解析后的 JSON 键，须对原始 body 文本扫描秘密/`9832`/key 文件内容；④ **列表与详情都测**——列表最容易漏（`list_providers` 复用 `get_provider`，但须显式断言）；⑤ **证据脱敏**——`manifest.redactions` 必须列 `Authorization`、`9832`、key 文件内容；归档后不得保留真实秘密；⑥ **不证明写路径**——本 case 只读，写入 `secret_ref` 的行为不在此断言。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ProviderView`（无 `secret_ref`、`additionalProperties:false`）+ `T-CFG-SECRET` 不泄露规则。
  - 列表/详情：`200`；元素/体键集恰为 `ProviderView` 必填键，**无 `secret_ref`**；`has_secret` 为合法布尔。
  - 否定扫描：原始响应不含 key 文件内容、不含 `9832`、不含 `Authorization` 凭据。
  - 无错误信封：成功路径不应出现 `{"error":{...}}`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：列表与详情均 `200`、键集恰为 `ProviderView`、无 `secret_ref`、`has_secret` 正确，且原始响应否定扫描通过。
  - **FAIL**：任一读路径回显 `secret_ref`/秘密值/`9832`，或键集不符——安全不变量回归，须给预期 vs 实际与 `reproduction_cmd`（**不得**在证据中留存真实秘密）。
  - **BLOCKED**：无法执行/无法判定且可重试（断言不可实现、秘密来源不可解析导致无法做否定扫描）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（含 §2.1.5 `provider_omlx_m5mac` 秘密不可用）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air，或伪造否定扫描结论——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 case 自动化入口 **`MISSING`**（§3.2，尚无 `at_adm_prov_14.py`），本轮未执行按 §9 记 `NOT_RUN`（MISSING = 缺口，不得以"未实现"当 PASS/SKIP）；`ADM-PROV-14` 为 **P0 MISSING**，阻断 release Gate（[测试设计 §9](../llmtier-api-test-specification.md)）。
- **证据与 Run**：保存列表/详情原始 status/headers/body（**脱敏后**：`Authorization`、`9832`、key 文件内容 → `<redacted>`）、否定扫描方法与被扫字符串的哈希/占位、发出命令、exit code、`elapsed`、环境快照。`manifest.json` 必含 `{run_id,case_id,target_artifact{git_commit,db_schema_version,openapi_version},environment:"a",inputs,oracle,actual,verdict,evidence_files,redactions,reproduction_cmd}`；`redactions` 必须显式列出上述三项。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`；失败现场不截断但**必须先脱敏**。证据/报告契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
  > 自动化缺口：本 case 尚无 `at_adm_prov_14.py`，须由实现者按 §4.9/§8.5 新增 `at_adm_prov_14.py`（A 类，`admin_client`）并接入 runner；在实现落地前，本 case 保持 `NOT_RUN`（P0 缺口）。
- **清理与复位**：**无需 teardown**——纯读，不改 provider/deployment、不写注入。退出前确认 `/readyz` 7 tier、provider 列表未变、无未清空注入项；确认证据已完成脱敏。若被误跑于 B 类临时实例，则按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf`。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 就绪检查，尤其 **§2.1.5**（`provider_omlx_m5mac` `has_secret=true`、`secret_ref` 为 `file:`）；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；`ProviderView` 机器契约（`interfaces/openapi/llmtier.openapi.json`）；`registry.get_provider`/`list_providers`；机制 `T-CFG-SECRET`；自动化入口 **`MISSING`（待实现 `at_adm_prov_14.py`）**。**不依赖**其它 Case；与 ADM-PROV-01/03 共享读路径，但承担其安全断言；与 ADM-AUDIT-01/ADM-LOGS-01（审计/日志脱敏）互补但各自独立。
