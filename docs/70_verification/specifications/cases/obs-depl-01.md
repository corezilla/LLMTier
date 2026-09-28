# OBS-DEPL-01 — 读取 deployment 注入配置

- **Case ID**：`OBS-DEPL-01`
- **标题**：`GET /v1/deployments/{id}/diagnostics` 返回该 deployment 的故障注入配置：HTTP 200 + `InjectionView[]`（每项恰 6 键）。
- **目的（被测契约）**：验证 Observability `GET /v1/deployments/{deployment_id}/diagnostics` 的**只读注入配置契约**。被测端点/规则：`GET /v1/deployments/{deployment_id}/diagnostics`，成功返回 `InjectionView[]`（顶层为数组），每项 `InjectionView` 必填 6 键（`id, deployment_id, type, config, enabled, updated_at`），`type ∈ {fault_502, fault_503, delay, rate_limit, stream_terminate, malformed_event}`，`config` 为对象、`enabled` 为布尔；未知 deployment → 404 `not_found`（本 case 用已知 id，负向属 OBS-DEPL-03）；认证 `admin`；失败走统一信封 `{error:{message,type,code,param,retryable}}`（401/403/404/503）。设计验证项 `VRC-DIAG-004`；机制 `T-OBS-INJECT`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §4.2 `D-OBS-INJECTION[]`、§4.9 `D-OBS-INJECTION-CONFIG`、§5.1 `IF-OBS-INJECT`）；错误目录 `ERR-INJECTION`/`ERR-NOTFOUND`/`ERR-STORE`；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）；机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`InjectionView`，`security=AdminBearerAuth`）。**不证明什么**：不证明写入注入（OBS-DEPL-02）、不证明未知 deployment 的 404（OBS-DEPL-03）、不证明非法注入项的 400（OBS-DEPL-04）、不证明注入对推理的命中效果（DP-RESP-11/22，属 `T-OBS-INJECT` 命中证明）、不证明别名等价（OBS-ALIAS-04）。
- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读/无副作用；见[测试设计 §2.3](../llmtier-api-test-specification.md)）。执行前必须通过[测试设计 §2.1](../llmtier-api-test-specification.md) 的 **6 项**就绪检查；任一失败 → 整班 BLOCKED/SKIP。fixture：`admin_client`（[§4.4](../llmtier-api-test-specification.md)）。初始状态 = 3 provider / 4 deployment / 7 tier；以 §2.1 已注册的 deployment（如 `dep_local_gemma`）为目标；`diagnostic_injections` 对既有 deployment **预期为空**（无启用注入；残留核验见 §2.8）。本 case 纯读，初态即终态。
- **输入与构造**：固定请求（无 body）：
  `GET /v1/deployments/dep_local_gemma/diagnostics`、`Authorization: Bearer dev-admin`、`Accept: application/json`。边界点：**无请求体**；`{id}` 取 §2.1 已注册 deployment（4 选 1）；不构造未知 id（OBS-DEPL-03）；不写入、不注入；`{}` 与 `[]` 的区分——成功 body 是**数组**（可为空数组），不是 `{items:[...]}` 包封对象（注意与 DP-RESP-11 的写入 body 形态不同）。
- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz`（§2.1，自动执行）。
  2. `GET /v1/deployments/dep_local_gemma/diagnostics`（`admin_client`）→ 记录 status/`Content-Type`/原始 body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 JSON，断言顶层为**数组**（不是对象）。
  5. 对每个 `item`：断言键集**恰为** `{id, deployment_id, type, config, enabled, updated_at}`；`id`/`deployment_id`/`updated_at` 为字符串、`type ∈` 枚举、`config` 为对象、`enabled` 为 JSON 布尔。
  6. 断言每个 `item.deployment_id == "dep_local_gemma"`（只返回该 deployment 的注入）。
  7. （交叉核对，不改变判定）与别名 `GET /tier/admin/v1/deployments/dep_local_gemma/diagnostics` 同凭据下响应体逐字节比对，作为 OBS-ALIAS-04 的旁证；本 case 不承担别名判定。
- **重点关注步骤**：① **顶层数组 vs 包封对象**——成功体是 `InjectionView[]` 裸数组；若是 `{items:[...]}` 判 FAIL（PATCH body 才是 `{items}`）。② **项键集精确**——恰 6 键（`additionalProperties:false`）。③ **`type` 枚举**——6 值白名单，越界即 FAIL。④ **`config` 为对象**——不得为 `null`/字符串；具体字段随 `type` 变化（如 `fault_502` → `error_body`、`delay` → `delay_ms`）。⑤ **`enabled` 布尔**——不得用 `0/1`。⑥ **deployment 作用域**——返回项必须与路径 id 一致，不得混入其它 deployment。⑦ **空数组合法**——无注入时 `[]` 合法（PASS），不要求非空。⑧ **降级/存储**——`_UnavailableDiagnostics.injections` 恒返回 `[]` 的 **200**（fail-open，形状 PASS）；`503 usage_store_unavailable` 判 BLOCKED/SKIP。注意：本 case 当前 `MISSING`（§3.2），无 `at_obs_depl_01.py`；且 §3.5 将 OBS-DEPL-01 列为 **P0 MISSING Gate 阻断项**。
- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `InjectionView` wire 形态 + 机制 §4.2/§4.9 映射（不依赖实现内部）。
  - HTTP：`200`；`Content-Type: application/json`（openapi 未为 200 声明响应头）。
  - body：JSON 数组；每项键集恰 6、`type` 枚举、`config` 对象、`enabled` 布尔、`deployment_id` 等于路径 id。
  - 空数组合法。
  - **fail-open**：降级实例 `200 + []` → **PASS**（本 case 不要求非空）；健康实例非 200、顶层非数组、项键集/枚举/类型不符 → **FAIL**；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + 顶层数组 + 每项恰 6 键且 `type`/`config`/`enabled` 正确 + `deployment_id` 匹配路径（含空数组 fail-open）。
  - **FAIL**：非 200（存储健康时）、顶层为对象、项键集不符、`type` 越枚举、`enabled` 非布尔、或返回别的 deployment 的注入。
  - **BLOCKED**：测试代码/契约问题或存储不可达 `503 usage_store_unavailable`——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **SKIP**：§2.1 前置不满足（含 `dep_local_gemma` 未注册）——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：自动化入口 `MISSING`（§3.2；P0 Gate 阻断项），本轮未执行；缺口引用见 §9。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air，或未命中真实诊断服务却按行为判定——见[测试设计 §9](../llmtier-api-test-specification.md)。
- **证据与 Run**：保存原始 HTTP status/headers/body、命令/exit code/`elapsed`、环境快照（`/healthz`/`/readyz` + provider/deployment 列表）。`manifest.json` 含 `target_artifact` 与 `redactions`。Run ID = `<date>/A-api`，落位 `tests/system/reports/<date>/A-api/<case-id>/`；失败现场不截断（[测试设计 §4.8/§10](../llmtier-api-test-specification.md)）。
- **清理与复位**：**无需 teardown**——纯读，不写 `diagnostic_injections`、不改开关、不注入。退出前确认无未清空注入项（本 case 不注入）、`/readyz` 仍 7 tier；若误跑于 B 类实例，按[测试设计 §4.7](../llmtier-api-test-specification.md) 整班 `stop()` + `rm -rf`。
- **依赖**：[测试设计 §2.1](../llmtier-api-test-specification.md) 6 项就绪检查（含 `dep_local_gemma` 注册）；`admin_client` fixture（[§4.4](../llmtier-api-test-specification.md)）；M007 `diagnostic_injections`（`002_observability.sql`）；`InjectionView` 机器契约；实现 [`src/libdiag/injections.py`](../../../../src/libdiag/injections.py)、[`src/http_api/app.py`](../../../../src/http_api/app.py)。自动化入口 `at_obs_depl_01.py`（**当前 `MISSING`，尚未实现**）。**不依赖**其它 Case；与 OBS-DEPL-02（写入）、OBS-DEPL-03（未知 404）、OBS-DEPL-04（非法项 400）语义相邻但各自独立执行。
