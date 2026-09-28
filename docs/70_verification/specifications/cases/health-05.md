# HEALTH-05 — readyz bootstrap 失败

- **Case ID**：`HEALTH-05`（与 §3.2 权威清单一致；本文件名 `health-05.md`，唯一对应）。
- **标题**：空库在缺一次性 bootstrap 或 bootstrap 非法时，`GET /readyz` 返回 HTTP 503 + `{status:"not_ready", models:[]}`（空 `models`）；同时 `GET /healthz` 仍为 200（进程存活）。
- **目的（被测契约）**：验证 IF-HEALTH 在**引导失败**时的就绪契约。端点 `GET /readyz`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getReadiness`）。实现 [`Application.__init__`](../../../../src/http_api/app.py) 捕获 `registry.bootstrap_settings()`/`ensure_fixed_tiers()` 抛出的 `ApiError` 到 `app.bootstrap_error`（[`registry.py`](../../../../src/management/registry.py)：空库缺 settings → `bootstrap_required`；settings 读/解析/校验失败 → `bootstrap_invalid`）；随后 [`app.py:188-189`](../../../../src/http_api/app.py) 在 `/readyz` 短路返回 `_json(503, {"status":"not_ready","models":[]})`。设计验证项 `VRC-MGMT-003`、`VRC-UTIL-001/002`；机制 `T-CFG-BOOT`/`R-CFG-02`（[config-lifecycle 机制](../../../20_system_design/mechanisms/config-lifecycle.md)）；需求链 `LT-FUN-006`/`LT-OPS-001`、`CT-OPS-001`（[测试设计 §3.6](../llmtier-api-test-specification.md)）。**不证明什么**：不证明无 deployment 但 bootstrap 成功时的 `not_ready`（HEALTH-04，其 `models` 为 7 个 `unavailable`，非 `[]`）；不证明健康端点无需鉴权（HEALTH-06）；不证明错误信封 code——**`ERR-BOOT`（`bootstrap_required`/`bootstrap_invalid`）的 wire envelope code 是 §11.1 具名缺口**（[测试设计 §11.1](../llmtier-api-test-specification.md)），本 case 只覆盖 `/readyz not_ready` 的表现，不断言其 envelope 码；不证明 schema 不兼容（`ERR-SCHEMA`，属 §2.9 恢复路径，见 HEALTH-05 边界注）；不触发 provider 计费调用（`LT-OPS-001`）。
- **前置与环境**：**环境 B**（临时 LLMTier 实例：`127.0.0.1:<随机空闲端口>` + 临时 SQLite；见[测试设计 §2.3](../llmtier-api-test-specification.md)/§2.4 B 类）。执行前必须满足[测试设计 §2.1](../llmtier-api-test-specification.md) **附加（B 类）**：临时实例可启动。**本 case 的关键构造**：让 `bootstrap_settings` 失败——两种等价构造：
  - **(a) 缺 bootstrap**：以空/新 SQLite 启动且**不提供** `LLMTIER_SETTINGS`/`--settings`；`bootstrap_settings(None)` 在空库（`schema_meta.bootstrap_sha256` 为空）时抛 `ApiError(503, "bootstrap_required")`。
  - **(b) 非法 bootstrap**：提供指向**不存在/无法解析/校验失败**的 settings 文件；`bootstrap_settings` 抛 `ApiError(503, "bootstrap_invalid")`。

  两种构造下 [`serve`](../../../../src/http_api/app.py) 仍启动并监听（`Application` 只把异常记入 `bootstrap_error`），且 `/healthz` 分支（[`app.py:187`](../../../../src/http_api/app.py)）在 bootstrap 检查之前，故可轮询 200。fixture：需要**尚未存在**的"无引导/坏引导"实例 fixture（如 `llmtier_b_no_bootstrap`，`LLMTierInstance(settings=None)`，其 `__init__` 在不传 settings 时不写 `LLMTIER_SETTINGS`；见 [`conftest.py`](../../../../tests/system/api_test_v03/conftest.py)）。**不得复用 `llmtier_b`/`llmtier_b_empty`**：二者 bootstrap 均成功，`bootstrap_error` 为 `None`。TS-003 与上游无关（本构造不接上游）。
- **输入与构造**：固定请求（无 body、无查询参数、无 `Authorization`）：

  ```http
  GET /healthz HTTP/1.1
  Host: 127.0.0.1:<port>
  ```

  ```http
  GET /readyz HTTP/1.1
  Host: 127.0.0.1:<port>
  ```

  边界/构造点：空库 + 无/坏 bootstrap；**不**提供合法 settings；不创建任何 provider/deployment/service-level；不注入故障；不构造非法 query（非法输入不在本 case 范围）。
- **执行过程（逐步调用）**：
  1. （fixture 前置）以构造 (a) 或 (b) 启动临时实例；轮询 `GET /healthz` 200（`LLMTierInstance.start()` 依赖此点，故启动应成功）。
  2. `GET /healthz`：断言 `status_code == 200`，`status == "ok"`——证明"引导失败 ≠ 进程死亡"。
  3. `GET /readyz`：断言 `status_code == 503`。
  4. 解析 body：断言键集**恰为** `{status, models}`，`status == "not_ready"`，`models == []`（**空数组**）。
  5. 断言 body 中**不存在** `{"error":...}` 信封（`/readyz` 不以 envelope 表达引导失败；envelope 码属具名缺口）。
  6. （清理）整班结束时由 fixture `stop()` 销毁实例。
- **重点关注步骤**：① **`models:[]` 是核心区分点**——HEALTH-04 的 `not_ready` 是 7 个 `unavailable`；本 case 的 bootstrap 失败是**空 `models`**（[`app.py:188-189`](../../../../src/http_api/app.py) 直接返回 `models:[]`）。观测到 7 元素即说明命中了 HEALTH-04 路径而非本 case，判 FAIL/BLOCKED。② **`/healthz` 仍 200**——必须同时断言，证明存活与就绪分离（`/healthz` 位于 `bootstrap_error` 检查前）。③ **`bootstrap_error` 的 status 与 `/readyz` 无关**——进程内 `bootstrap_error` 是 `ApiError(503, code∈{bootstrap_required,bootstrap_invalid})`，但 `/readyz` 只回 `{"status":"not_ready","models":[]}`，**不回**该 `code`；不得断言 envelope（属 §11.1 具名缺口）。④ **构造确定性**——缺 settings 与坏 settings 两种臂都可用；若选 (b) 需写明坏 settings 的具体形态（不存在路径/非法 JSON/未知 section）。⑤ **不得被替代路径冒充**——必须真实启动临时实例使其 bootstrap 失败，不得直接 mock `readiness_view` 或 `bootstrap_error`。⑥ **边界注（不属本 case 判定）**：A 类 m5air 的 schema/引导失败场景（§2.9）为 HARD-BLOCKED，且恢复路径为其专属；本 case 只在 B 类空/坏库触发，不触碰 A 类库。
- **期望结果与独立 Oracle**：独立 Oracle = 系统设计 §8.1 `GET /readyz` 的 `not_ready` 契约 + [`app.py:188-189`](../../../../src/http_api/app.py) 的实现形态（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md)、[测试设计 §4.10](../llmtier-api-test-specification.md)），不依赖实现内部数据。
  - `GET /healthz`：`200`；body 键集 `{status, version}`、`status=="ok"`、`version` 非空字符串。
  - `GET /readyz`：`503`；`Content-Type: application/json; charset=utf-8`；body 键集**恰为** `{status, models}`；`status=="not_ready"`；`models==[]`；无 `{"error":...}`。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`/healthz` 200 + `{"status":"ok",...}`；`/readyz` 503 + `status=="not_ready"` + `models==[]` + 无 envelope。
  - **FAIL**：`/readyz` status/body 不符——含误为 `models` 非空（HEALTH-04 路径）、误为 200、或返回错误信封；`/healthz` 非 200；给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：**无法构造引导失败实例**——例如缺少无引导/坏引导 fixture、`LLMTierInstance(settings=None)` 无法启动、或进程在 `Application.__init__` 之外提前退出导致 `/healthz` 不可达（依赖失败，视情形 BLOCKED/SKIP）；或测试代码/断言不可实现（见[测试设计 §9](../llmtier-api-test-specification.md)）。本 case 当前 `自动化入口 = MISSING`（§3.2），无脚本时应按 §9 记为缺口而非 PASS。
  - **SKIP**：B 类临时实例不可用等 §2 前置不满足——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **INVALID**：未真实制造引导失败却按 `not_ready` 判定，或以 mock/替代路径冒充真实临时实例——见[测试设计 §9](../llmtier-api-test-specification.md)。
  - **NOT_RUN**：本 case `自动化入口 = MISSING`（§3.2），本轮未执行；缺口引用见[测试设计 §9/§8.5](../llmtier-api-test-specification.md)（MISSING ≠ NOT_RUN：无实现是缺口，不是跳过）。
- **证据与 Run**：保存构造证据（选 (a)/(b)、坏 settings 内容或"未提供 settings"、DB 为空且无 `bootstrap_sha256`）、`/healthz` 与 `/readyz` 的原始 HTTP status/headers/body、`elapsed`。`manifest.json` 含 `target_artifact{git_commit,db_schema_version,openapi_version}`、`environment:"b"` 与 `redactions`。Run ID = `<date>/B-api`，落位 `tests/system/reports/<date>/B-api/<case-id>/`，失败现场不截断。契约见[测试设计 §4.8/§10](../llmtier-api-test-specification.md)。
- **清理与复位**：B 类实例由 fixture `stop()`（`terminate`→等待 5s→`kill`）+ `shutil.rmtree` 临时目录销毁（[测试设计 §2.8/§4.7](../llmtier-api-test-specification.md)）；本 case 只读两个健康端点，不创建/修改资源、不写注入。离开前确认无未清空注入项（本 case 不注入）。
- **依赖**：B 类 fixture（**待新增**的"无引导/坏引导"实例，如 `llmtier_b_no_bootstrap`；**不可复用** `llmtier_b`/`llmtier_b_empty`）（[测试设计 §4.4](../llmtier-api-test-specification.md)）；[`registry.py`](../../../../src/management/registry.py) 的 `bootstrap_required`/`bootstrap_invalid` 与 [`app.py:188-189`](../../../../src/http_api/app.py) 的短路；系统设计 `ERR-BOOT` 与 §8.1（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md)、[测试设计 §11.1](../llmtier-api-test-specification.md) 具名缺口）；自动化入口 **`MISSING`**（§3.2，尚无脚本；落位按[测试设计 §4.9/§8.5](../llmtier-api-test-specification.md)）。**不依赖**其它 Case；与 HEALTH-04 同 `not_ready` 但 `models` 形态互斥（空 vs 7×`unavailable`），各自独立执行。
