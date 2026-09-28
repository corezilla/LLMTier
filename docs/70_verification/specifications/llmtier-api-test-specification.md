<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 API Test Specification

> STD 使用入口：[项目采用说明与标准导航](../../00_management/standards/README.md)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-api-test-specification` |
| Document Version | `0.4.0-draft.5` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-28` |
| Last Modified Date | `2026-09-28` |
| Template ID | `assurance.test-specification` |
| Template Version | `0.2.1` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/llmtier-api-test-specification.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. 目标、范围与被测对象

**本节目的**：固定本规格验证哪一组外部 HTTP 行为的设计保证，以及结论边界。

**被测保证**：LLMTier V0.3 对外的 **HTTP API 契约**——路径、方法、认证角色（`data` / `admin` / 无认证）、正常载荷、边界与负向行为、统一错误信封 `{error:{message,type,code,param,retryable}}`（5 键；`type` 即错误类别 `request_error`|`server_error`，无 `category` 键）与稳定错误码、SSE 事件序列、分页 cursor 语义。被测对象是**运行中的 LAN 服务**（A 类 = m5air `192.168.1.9:8181`；B 类 = 临时实例），不是静态 OpenAPI 文本，也不是 Web UI / SQLite 文件格式。

**不证明什么**：本规格不证明 Web UI 行为、FD 泄漏、30min 耐久、性能 SLO 校准、上游模型答案质量、上游 provider 的实际推理正确性；这些分别由 `llmtier-test-plan.md` / `llmtier-contract-test-specification.md` / 运维手册承接。**静态契约一致（contract specification STATIC PASS）不等于运行行为 PASS**，反之亦然。

**本规格的层级定位**：本规格是**顶层测试设计**，它 (a) 规约**全部 Case 的命名空间、分类与编号**并给出**权威 Case 清单**（§3.2，全部 140 个 Case），(b) 定义**每 Case 详细设计文档**的固定契约与落位（§3.3–§3.4）及**定量覆盖模型与 Traceability**（§3.5–§3.6），(c) 定义所有 Case 共用的**共同机制**（§4），(d) 保留**环境与前置**作为共同前置（§2）。**逐 Case 的输入/执行/Oracle/判定不在本规格内展开**，统一见各自 case 详细设计文档（当前待写）。本规格定义**预期**，不伪造执行结果。

**范围**：全部对外路由（见 §3 Case Matrix）：

- **Data Plane**（`data` token，LAN trust 下可匿名）：`POST /v1/responses`（SSE）、`POST /v1/embeddings`、`GET /v1/models`、`GET /v1/models/{model}`。
- **Usage**（`data` 或 `admin`）：`GET /v1/usage`（`from`/`to` 必填 + cursor 分页）；`DELETE /v1/usage`（仅 `admin`）。
- **Management**（`admin`）：`/v1/providers`（+`{id}`、`{id}/usage`、`{id}/models`）、`/v1/deployments`（+`{id}`）、`/v1/service-levels`（+`{id}`）、`POST /v1/probes`、`/v1/runtime`、`/v1/stats`、`/v1/audit`、`/v1/logs`。
- **Observability**（`admin`）：`/v1/diagnostics`（+`snapshots`/`stats`/`traces`）、`/v1/deployments/{id}/diagnostics`、`/v1/trace/{request_id}`。
- **No-auth**：`GET /healthz`、`GET /readyz`。
- **Alias namespace**：`/tier/admin/v1/*`（Management/Observability 的 6 条诊断/追踪子集，与 `/v1/*` 为同一 handler 的精确别名）。

**接口责任方**：M001（HTTP 入口/鉴权/序列化）、M003（推理编排/适配）、M004（Registry）、M005（观测读）、M006（观测写/注入）、M007（Store）。**设计验证项** `VRC-*`（系统设计）+ 机制 `T-*`（详见 §3）。

## 2. 引用基线、环境与前置条件

**本节目的**：固定被测版本、机器契约与运行基线，给出 A/B 两班各自的部署位置、更新/启动/复位步骤与就绪检查，使任一执行者都能得到同一初态。

> 本节是**所有 Case 的共同前置**：任何 case 详细设计文档（§3.3）中的"前置与环境/清理与复位"字段都引用本节，不重复其定义。

### 2.1 前置就绪检查（执行前必过，任一不满足 → 整班 BLOCKED/SKIP）

由 `tests/system/api_test_v03/conftest.py::pytest_configure` 在收集用例前自动执行下列 6 项；任一失败则整个 A 类 suite 被标记 skip（BLOCKED/SKIP），不得改跑替代路径声称真实通过。

1. **§2.1.1 A 类 m5air LLMTier `/healthz` 200** 且 body `status="ok"`（`version` 为字符串）。
2. **§2.1.2 A 类 m5air LLMTier `/readyz` 200** 且 `models[]`（或 `tiers[]`）含 7 个 fixed tier（`Senior/Junior/Worker/Associate/Engineer/Executor/Embedding-v1`）。
3. **§2.1.3 m5air OMLX `192.168.1.9:9000` 可达**：`GET /v1/models` 200（`Authorization: Bearer 9832`）。
4. **§2.1.4 m5mac OMLX `192.168.1.8:9000` 可达**：`GET /v1/models` 200（`Authorization: Bearer 9832`）。
5. **§2.1.5 `provider_omlx_m5mac` secret 可用**：`GET /v1/providers/provider_omlx_m5mac`（admin token）返回 `has_secret=true`，且 `secret_ref` 为 `file:` 引用（非 `env:`）。
6. **§2.1.6 必需 A 类资源已注册**：`provider_local`/`provider_minimax`/`provider_omlx_m5mac` 三个 provider 与 `dep_local_gemma`/`dep_local_bge_m3`/`dep_omlx_qwen36`/`dep_minimax_m27` 四个 deployment 均 `GET` 返回 200（缺则整个 A 类 suite skip，相关 Case BLOCKED）。

**附加（B 类）**：临时实例可启动并 `GET /healthz` 200；`_BASELINE_SETTINGS` fixture 注入 **1 provider（`prov_b`）+ 1 deployment（`depl_b`）** + 7 fixed tier（service-levels 由 bootstrap 建立）。注意：3 provider / 4 deployment 是 **A 类 m5air 已部署实例**的基线（§2.3/§2.4），不是 B 类 fixture。

**强制规范**：TS-003 —— **被测服务的所有上游 provider endpoint 必须使用 LAN IP（`192.168.x.x`）**，禁止 `127.0.0.1` 出现在被测服务的上游 endpoint 配置中（B 类临时实例内部 provider endpoint 亦须为可解析的 LAN 地址）。TS-002 —— 每个 `at_*.py` 文件头部写明 Endpoint / Upstream Provider / Model / Auth。

### 2.2 固定基线（可复查来源）

| 类别 | 基线 | 说明 |
|---|---|---|
| 机器契约 | `interfaces/openapi/llmtier.openapi.json`（OpenAPI 3.1.0） | 路由/方法/请求响应 schema/securitySchemes（`BearerAuth`、`AdminBearerAuth`）与 `x-llmtier-contract-aliases` 的**机器权威** |
| 错误目录 | 系统设计 §7.8（`ERR-*` 八字段 + `<!-- STD_PUBLIC_ERROR_CATALOG_BEGIN -->` 区块） | 错误**类别与调用方行为**权威；wire 信封为 `openapi` `ErrorEnvelope`/`ErrorDetail` |
| 数据/行为 | `docs/20_system_design/llmtier-system-design.md` §5–§7、§11 | 预算、超时、准入、账本、保留 |
| 接口控制 | `docs/60_interfaces/piko-data-plane-control.md`、`slinky-capacity-observation-control.md`、`llmtier-management-control.md` | 各成员的成功/失败条件、错误引用 |
| 机制 | `docs/20_system_design/mechanisms/{inference-stream,access-trust,usage-metering,observability,config-lifecycle}.md` | INC/INV/T-* 可验证断言 |
| 测试规范 | `testing-standard.md`（TS-002 依赖头部、TS-003 LAN IP） | 强制约束 |
| 运维基线 | `docs/80_operations/manuals/m5air-deploy-guide.md`、`docs/80_operations/m5air-operations-manual.md`、`docs/80_operations/llmtier-release-and-operations.md` | m5air 部署/启动/停止/复位命令的权威来源 |
| 项目标准 | `docs/std.lock.json`（STD `0.1.0-draft.44`） | 文档/流程基线 |

### 2.3 环境拓扑（A/B 两班）

| 环境 ID | 组成 | 用途 |
|---|---|---|
| **A** | m5air `192.168.1.9:8181`（已部署：3 provider / 4 deployment / 7 fixed tier）+ m5air OMLX `192.168.1.9:9000` + m5mac OMLX `192.168.1.8:9000` | 只读/观察/一次性无状态写；不污染 SQLite |
| **B** | 临时 LLMTier 实例：临时端口 + 临时 SQLite（`tests/system/api_test_v03/conftest.py` 的 `llmtier_b` / `llmtier_b_empty` / `llmtier_b_no_auth`），**同机第二个进程** | 创建/修改/删除 provider/deployment/service-level；空库；无鉴权场景；跑完销毁 |

A、B 两类**不共享 SQLite、端口或进程**；A 类 PASS 不关闭 B 类，B 类 PASS 不关闭 A 类。

### 2.4 LLMTier 部署位置

**A 类 —— m5air 已部署实例（`192.168.1.9:8181`）**

| 项目 | 值 |
|---|---|
| 主机 / 监听 | `192.168.1.9`，监听 `0.0.0.0:8181`（直接 LAN 暴露，无反向代理） |
| 部署目录（非 git 工作树） | `/Users/mlp/LLMTier-dev/` |
| 源码 / 导入根 | `/Users/mlp/LLMTier-dev/src`（启动时 `PYTHONPATH=src`） |
| Python | 3.14；`/usr/local/bin/python3`（或 `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`）；**禁止系统 Python 3.9** |
| 运行数据库 | `/Users/mlp/LLMTier-dev/state.sqlite3`（已初始化，SQLite 是唯一配置 authority） |
| 一次性 bootstrap 源 | 仅空库首启：仓库默认 `config/settings.json`；m5air 已初始化，正常启动**不再**传 `--settings` |
| Secret 目录 | `/Users/mlp/LLMTier-dev/secrets/`（`file:` 引用，如 `omlx-secret-key.txt`；`chmod 600`） |
| 日志 / PID | `/Users/mlp/LLMTier-dev/llmtier.log`、`/Users/mlp/LLMTier-dev/llmtier.pid` |
| 凭据来源 | `LLMTIER_ADMIN_TOKEN=dev-admin`、`LLMTIER_DATA_TOKEN=dev-data`；**当前实现**（`src/http_api/auth.py`）对 loopback/RFC1918 来源在**无 `Authorization` 头**时**无条件**解析为共享角色主体（`trusted-lan-operator`/`trusted-lan-consumer`）；`LLMTIER_DEV_MODE=1` 时 loopback 主体改名为 `loopback-*`。`LLMTIER_TRUSTED_LAN_MODE` **未被源码读取**（详见 §4.2） |
| 上游 OMLX | m5air `192.168.1.9:9000`、m5mac `192.168.1.8:9000`（Bearer `9832`） |

> 仓库默认布局（空库首启 / 新建本地实例）为 DB `state/llmtier-v03.sqlite3` + bootstrap `config/settings.json`，启动失败会要求一次性 `--settings`；m5air 实际使用上表路径，两套路径不得互相覆盖或双写。

**B 类 —— 临时本地实例（每班新建、跑完销毁）**

| 项目 | 值 |
|---|---|
| 创建方式 | `tests/system/api_test_v03/conftest.py` 的 `LLMTierInstance`：`_find_free_port()` 取临时端口 + `tempfile.mkdtemp(prefix="llmtier_b_")` 下临时 SQLite 与 `settings.json` |
| 监听 / 端口 | `127.0.0.1:<随机空闲端口>` |
| 数据库 | 临时目录内 `test.sqlite3`（`LLMTIER_DATABASE` 环境变量） |
| bootstrap / settings | 每 run 写入 `settings.json` 并置 `LLMTIER_SETTINGS`：`_BASELINE_SETTINGS`（prov_b + depl_b + 7 tier）、`_EMPTY_SETTINGS`（HEALTH-04/05）、`_NO_AUTH_SETTINGS`（HEALTH-06/AUTH-07） |
| Python | 执行机 Python（`sys.executable`），要求 3.11+；在 m5air 上跑用 3.14 |
| 凭据来源 | `LLMTIER_DEV_MODE=1` → 固定 `dev-data`/`dev-admin`；无鉴权场景 `_NO_AUTH_SETTINGS` + `dev_mode=False` |
| 生命周期 | fixture session-scope；`start()` 轮询 `/healthz`（最多 40×0.25 s）；`stop()` `terminate`→等待 5 s→`kill`，`shutil.rmtree` 临时目录 |

### 2.5 更新版本（部署到 m5air）

m5air 部署目录不是 git 工作树，`git push` 不会更新它，必须从开发机受控同步。**排除运行数据**（`state.sqlite3*`、`secrets/`、`llmtier.log`、`llmtier.pid`、`backups/`）。参考 `m5air-deploy-guide.md`。

1. **同步源码**（开发机 → m5air）：
   ```bash
   rsync -avz --exclude 'state.sqlite3*' --exclude 'secrets/' \
     --exclude 'llmtier.log' --exclude 'llmtier.pid' --exclude 'backups/' \
     /Users/ben/work/LLMTier/src/ m5air:/Users/mlp/LLMTier-dev/src/
   ```
   只改单个文件时亦可按 deploy guide 逐文件 rsync（如 `src/http_api/app.py`、`src/management/admin.py`、`src/http_api/auth.py`、`src/inference/providers/`）。
2. **查旧进程 / 端口占用**（确认无第二实例）：
   ```bash
   ssh m5air "ps aux | grep 'http_api.*8181' | grep -v grep"
   ssh m5air "/usr/sbin/lsof -nP -iTCP:8181 -sTCP:LISTEN"
   ```
3. **停止旧进程**（优先 TERM，最多等 60 s，勿直接 `kill -9`）：
   ```bash
   ssh m5air 'pid=$(cat /Users/mlp/LLMTier-dev/llmtier.pid); kill -TERM "$pid"'
   ```
   若无 PID 文件或命令不符，用第 2 步查到的实际 PID `kill <PID>`，再确认端口释放。
4. **用 Python 3.14 重启**：
   ```bash
   ssh m5air "cd /Users/mlp/LLMTier-dev && \
     LLMTIER_ADMIN_TOKEN=dev-admin LLMTIER_DATA_TOKEN=dev-data \
     PYTHONPATH=src /usr/local/bin/python3 -m http_api \
     --host 0.0.0.0 --port 8181 \
     --database /Users/mlp/LLMTier-dev/state.sqlite3 \
     >> /Users/mlp/LLMTier-dev/llmtier.log 2>&1 &"
   ```
5. **验证服务正常**：
   ```bash
   curl -fsS http://192.168.1.9:8181/healthz          # 期望 {"status":"ok",...}
   ssh m5air "curl -sS http://localhost:8181/healthz"
   ```
6. **确认无旧进程残留**：重跑第 2 步的 `ps`/`lsof`，应只出现一个新 PID 且仅一个 `*:8181` 监听者。

> **启动命令与 Python 路径 authority**：A 类的启动命令、解释器路径（Python 3.14）、环境变量与复位/回滚步骤以 [`docs/80_operations/manuals/m5air-deploy-guide.md`](../../80_operations/manuals/m5air-deploy-guide.md) 与 [`docs/80_operations/m5air-operations-manual.md`](../../80_operations/m5air-operations-manual.md) 为准；§2.5/§2.6 的命令是这两份运维权威的镜像，二者不一致时以运维手册为准并回填本节。`LLMTIER_TRUSTED_LAN_MODE` 不在源码读取范围（§4.2），示例命令不再传入以免误导。

回滚与数据库恢复按 [`docs/80_operations/m5air-operations-manual.md`](../../80_operations/m5air-operations-manual.md) §14/§15：先停服务、保全日志与 SQLite、恢复同版本冷备份后再启动；当前无自动 migration rollback / 蓝绿部署（A 类 schema 不兼容时的显式恢复路径见 §2.9）。

### 2.6 启动 / 服务

**标准启动命令**（仓库默认路径；`--settings` 仅空库首启，初始化后 SQLite 为唯一 authority，正常启动省略）：

```bash
LLMTIER_ADMIN_TOKEN='...' LLMTIER_DATA_TOKEN='...' \
  PYTHONPATH=src python3 -m http_api \
  --host 0.0.0.0 --port 8181 \
  --database state/llmtier-v03.sqlite3 \
  --settings config/settings.json
```

> **Python 路径 / 启动命令 authority**：本命令是**仓库默认**形态；A 类 m5air 的实际解释器（Python 3.14）、路径与命令以 [`m5air-deploy-guide.md`](../../80_operations/manuals/m5air-deploy-guide.md) 和 [`m5air-operations-manual.md`](../../80_operations/m5air-operations-manual.md) 为唯一 authority（§2.5 为其镜像）。二者不一致时以运维手册为准并回填本节。

**环境变量**

| 变量 | 作用 | 约束 |
|---|---|---|
| `LLMTIER_ADMIN_TOKEN` / `LLMTIER_DATA_TOKEN` | admin / data 角色 Bearer 凭据 | m5air 用 `dev-admin` / `dev-data` |
| `LLMTIER_TRUSTED_LAN_MODE` | **源码不读取**（`src/http_api/auth.py` 无此分支）；无 Bearer 的 loopback/RFC1918 当前**无条件**获共享角色。若要改为显式 env 门控，作为**代码修复项**由代码 owner 处理（§4.2） | 仅可信 LAN；不得暴露公网 |
| `LLMTIER_DEV_MODE=1` | 固定开发凭据 + loopback 免 Bearer | **仅限 loopback 合成调试**；禁止共享/生产监听地址 |
| `LLMTIER_DATABASE` / `LLMTIER_SETTINGS` | 覆盖 DB / bootstrap 路径（B 类 fixture 用） | 空库首启才需要 settings |
| `LLMTIER_STATE_DIR` | 覆盖默认运行状态目录 | server/client 同步解析 |

**空库首启**：SQLite 首次启动必须显式提供一次性 bootstrap（`providers`/`deployments`/`service_levels` 完整）；初始化成功后 SQLite 成为唯一运行配置 authority，后续启动忽略该文件内容。

### 2.7 API 客户端运行位置

- 测试执行机 = 开发机（如 m5mac `192.168.1.8`）；在项目根目录运行 `pytest` 与 `tools/inference_smoke.py`。
- **A 类**：执行机经 LAN 访问 m5air `http://192.168.1.9:8181`（`tools/inference_smoke.py --base http://192.168.1.9:8181`，默认即此值）。
- **B 类**：执行机连接本地临时实例 `http://127.0.0.1:<port>`；此处 loopback 仅指**客户端 → LLMTier** 的连接，**被测 LLMTier 内部的上游 provider endpoint 仍必须是 LAN IP**。
- TS-003 的核心禁令是：**禁止把 `127.0.0.1` 写成被测服务的上游 provider endpoint**；客户端访问 LLMTier 本身不在此禁令内（B 类允许）。

### 2.8 数据、隔离、清理与复位

- **A 类**：只读/观察/一次性无状态写；每个写 case 之后必须 teardown（PATCH 恢复原值/version、DELETE 删除本次创建物），不删除 m5air 既有 provider/deployment/service-level 或用户 usage；注入配置以 `items:[]` 清空后才离开。DP-USAGE-04 直接读取/改写 m5air `state.sqlite3` 的 `query_snapshots.expires_at`（需权限）——执行前记录原值，执行后复位。
- **B 类**：独立临时 SQLite + 临时端口，不与 A 共享 DB/进程；整班结束 `terminate` 进程并 `rm -rf` 临时目录。
- **残留核验**：下一轮开始前必须能确认"无前次残留"——`/readyz` 显示 7 tier、provider/deployment 列表等于 §2.1 基线、`lsof` 无遗留 8181/临时端口监听、无未清空的注入项。无法核验或无法安全释放时按 §9 判 BLOCKED 并保留证据。

### 2.9 A 类 schema 兼容、HARD-BLOCK 与显式恢复路径

**触发事实**：A 类（m5air 已部署实例）在启动/就绪时若 M007 报告 schema 不符（系统设计 §7.8 `ERR-SCHEMA`：`schema_version_mismatch`/`schema_unknown`/`schema_integrity_failed`）或 `ERR-BOOT`（`bootstrap_required`/`bootstrap_invalid`），服务保持 `not_ready`、不接流量。此时 A 类**所有依赖运行实例的 Case 为 HARD-BLOCKED**（区别于可重试的 BLOCKED：只有执行恢复动作后才可能解除），B 类不受影响，继续跑。

**不存在"无路径"死区**：schema 不兼容**总有**一条定义好的恢复路径；本规格不允许把 A 类 HARD-BLOCK 判成 INVALID 或以 B 类替代冒充 A 类。恢复动作二选一，必须在缺陷/Run 证据中登记所选路径：

- **(a) fresh-DB rebuild（清库重建）**：停服务 → 冷备份并保全 `state.sqlite3*` 与日志 → 以目标代码对空库首启（一次性 `config/settings.json` 完整 bootstrap `providers`/`deployments`/`service_levels`）→ 重启 → `/readyz` 回到 `ready` 且 7 tier 就绪。**authority 后果**：一次性 bootstrap 成功后，**新 `state.sqlite3` 成为唯一运行配置 authority**（§2.6、LT-REL-004）；m5air 历史状态只以冷备份形式保留、不再被服务读取；A 类基线（3 provider / 4 deployment / 7 tier）必须在恢复后**重新建立并重新核验**，否则本轮 A 类结果无效。此路径丢失运行历史（usage/audit/observability），只在无兼容迁移时使用。
- **(b) offline migration（离线迁移）**：停服务 → 备份 → 由 operator 用系统设计 §7.11 / config-lifecycle 的**单一版本迁移程序**离线升级 schema（不并行双写、不在运行中迁移）→ 校验 `schema_meta` 版本 → 重启 → `/readyz` 回到 `ready`。**authority 后果**：SQLite 仍是唯一 authority，`settings.json` 不得在迁移后覆盖 Admin 已提交变更（LT-REL-004）。若版本跨度**没有**受支持的迁移路径，则 (b) 不适用，(a) 成为**强制路径**。

**恢复后要求**：无论 (a)/(b)，必须重跑 §2.1 就绪检查、记录新 Run ID（不覆盖旧失败）、把 A 类被阻断 Case 从 HARD-BLOCKED 改为续跑；证据须包含 schema 前后 `schema_meta.version`、备份路径、所选路径与 operator 授权。无法在窗口内执行任一恢复动作时，A 类相关 Case 保持 BLOCKED（非 INVALID），并在报告写出 `required_resolution` 与 `reproduction_cmd`。

## 3. Case Matrix

**本节定位**：本节是**顶层 Case 规约**，回答"有哪些 Case、如何命名分类、每个 Case 的详细设计文档是什么契约"。它**不展开**逐 Case 的输入/执行/Oracle/判定——那些在**各自 case 详细设计文档**（§3.3 契约，当前待写，见 §3.4）中维护。共同机制见 §4；环境与前置见 §2。

- §3.1 定义 Case 命名空间、分类与编号规则。
- §3.2 给出**权威 Case 清单**：全部 **140** 个 Case，一行一个。
- §3.3 定义**每 Case 详细设计文档**的固定模板/字段与落位命名。
- §3.4 给出逐 Case 详细设计文档的**待写索引**（占位）。
- §3.5 给出**定量覆盖模型**（route×method×role×error-code）。
- §3.6 给出**Traceability 映射**（`LT-*` → `R-*` → `VRC-*` → `T-*` → `CT-*` → Case 家族）。

### 3.1 Case 命名空间、分类与编号规则

1. **ID 家族**：`HEALTH-*`（无认证健康/就绪）、`DP-MODELS-*`、`DP-RESP-*`、`DP-EMB-*`、`DP-USAGE-*`（Data Plane）、`ADM-*`（Management）、`OBS-*`（Observability/诊断/追踪/别名）、`AUTH-*`（认证与授权）。
2. **命名语法**：`<FAMILY>-<SEQUENCE>`；`SEQUENCE` 为两位零填充十进制（`01`…`25`）。家族内主题再分：
   - `ADM-<RESOURCE>-<SEQ>`，`RESOURCE ∈ {PROV, PROV-MODELS, PROV-USAGE, DEPL, SL, PROBE, RUNTIME, STATS, AUDIT, LOGS, USAGE}`；
   - `OBS-<AREA>-<SEQ>`，`AREA ∈ {DIAG, SNAP, STATS, TRACE, DEPL, REQTRACE, ALIAS}`；
   - `HEALTH`、`DP-MODELS`、`DP-RESP`、`DP-EMB`、`DP-USAGE`、`AUTH` 直接接序号。
3. **顺序补丁**：同一主题的补充/反向 Case 用原序号加小写字母后缀，如 `ADM-SL-02b`、`ADM-SL-04b`。
4. **稳定性**：Case ID 一经登记不复用、不改名；新增 Case 取同家族下一个未占用序号（含补丁后缀）；废弃 Case 标 `superseded`，不删除、不重编号。
5. **分类维度（登记列）**：`分类`（家族/主题）、`角色 ∈ {none, data, admin}`、`环境 ∈ {A, B}`（§2.3）、`优先级 ∈ {P0, P1, P2}`、`设计状态 ∈ {待写, 已写}`（= 该 Case 独立详细设计文档的状态）。
6. **被测契约列**：给出`端点` + 关键契约点/错误码；括号内给出**设计验证项** `VRC-*`（系统设计）、需求 `LT-*`、机制需求 `R-*` 与机制 `T-*`，保证 STD "每个设计验证项能追到 Case"（家族级 `LT-*`/`R-*`/`CT-*` 完整映射见 §3.6）。同一 Case 承接多个规则时全部列出。
7. **A/B 归属**：A 类 = m5air 已部署实例上的只读/观察/一次性无状态写；B 类 = 临时实例上的创建/修改/删除/空库/无鉴权/注入/并发（§2.3）。A、B 分别报告，互不关闭（§9）。
8. **自动化入口命名**：`at_<family>_<seq>.py`（`HEALTH-*` 由 `at_obs_01..03.py` 承接）；无实现登记为 `MISSING`。

### 3.2 权威 Case 清单（全部 140 个）

**Case 总数：140**（RUN 88 / MISSING 52；环境 A 90 / B 50；Priority P0 45 / P1 72 / P2 23）。**本表是唯一权威 Case 清单**：一行一个 Case，任何 case 详细设计文档（§3.3）的 Case ID 必须与本节一致。

列语义：`分类` 为家族/主题；`被测契约/端点` 为端点、关键契约/错误码与需求/设计/机制验证项（`LT-*`/`VRC-*`/`R-*`/`T-*`）；`角色` ∈ {`none`,`data`,`admin`}；`A/B` 为环境（§2.3）；`自动化入口` 为现有 `tests/system/api_test_v03/at_*.py`（`MISSING` = 尚无自动化实现，对应 RUN 88 之外的 52 项）；`设计状态` 为该 Case 独立详细设计文档（§3.3）的状态，当前 `DP-RESP-01`、`DP-RESP-11`、`OBS-DIAG-01`、`AUTH-01` 已 `已写`，其余 `待写`。逐 Case 的前置/输入/Oracle/执行/判定/证据/清理**见各自 case 文档**（§3.4）。

| Case ID | 分类 | 被测契约/端点 | 角色 | 标题 | A/B | 优先级 | 自动化入口 | 设计状态 |
|---|---|---|---|---|---|---|---|---|
| HEALTH-01 | 健康/就绪 | `GET /healthz`；`status="ok"`,`version:str`（VRC-API-002,T-TRUST-ENDPOINTS） | none | healthz 始终存活 | A | P0 | `at_obs_01.py` | 已写 |
| HEALTH-02 | 健康/就绪 | `GET /readyz`；就绪=7 tier 可用（VRC-MGMT-003,T-OBS） | none | readyz 就绪=全部 tier 可用 | A | P0 | `at_obs_02.py` | 已写 |
| HEALTH-03 | 健康/就绪 | `GET /readyz`；某候选非 healthy→503 degraded（VRC-MGMT-003,T-OBS） | none | readyz degraded | B | P1 | MISSING | 已写 |
| HEALTH-04 | 健康/就绪 | `GET /readyz`；无 deployment→503 not_ready（VRC-MGMT-003,VRC-UTIL-001/002） | none | readyz not_ready（无 deployment） | B | P0 | `at_obs_03.py` | 已写 |
| HEALTH-05 | 健康/就绪 | `GET /readyz`；bootstrap 失败→503（VRC-MGMT-003,VRC-UTIL-001/002） | none | readyz bootstrap 失败 | B | P1 | MISSING | 已写 |
| HEALTH-06 | 健康/就绪 | `GET /healthz`,`GET /readyz`；无需鉴权（T-TRUST-NOCFG,T-TRUST-SHARED） | none | 健康端点无需鉴权 | B | P1 | MISSING | 已写 |
| DP-MODELS-01 | 逻辑模型清单 | `GET /v1/models`；object=list,data[7]（VRC-INF-002,R-CFG-01） | data | 列出全部可见 tier | A | P0 | `at_dp_models_01.py` | 已写 |
| DP-MODELS-02 | 逻辑模型清单 | `GET /v1/models/{model}`；精确返回（VRC-INF-001/002,R-INF-04） | data | 精确返回模型 | A | P0 | `at_dp_models_02.py` | 已写 |
| DP-MODELS-03 | 逻辑模型清单 | `GET /v1/models/{model}`；小写→404 model_not_found（VRC-INF-001,R-INF-04） | data | 大小写敏感（小写） | A | P0 | `at_dp_models_03.py` | 已写 |
| DP-MODELS-04 | 逻辑模型清单 | `GET /v1/models/{model}`；全大写→404 model_not_found（VRC-INF-001,R-INF-04） | data | 大小写敏感（全大写） | A | P1 | `at_dp_models_04.py` | 已写 |
| DP-MODELS-05 | 逻辑模型清单 | `GET /v1/models/{model}`；URL 编码尾空格→404（VRC-INF-001,R-INF-04） | data | URL 编码尾空格不匹配 | A | P1 | `at_dp_models_05.py` | 已写 |
| DP-MODELS-06 | 逻辑模型清单 | `GET /v1/models/{model}`；不存在→404 model_not_found（VRC-INF-001,R-INF-04） | data | 不存在模型 | A | P0 | `at_dp_models_06.py` | 已写 |
| DP-MODELS-07 | 逻辑模型清单 | `GET /v1/models`；capabilities 固定 12 键（VRC-INF-002） | data | capabilities 固定 12 键 | A | P1 | `at_dp_models_07.py` | 已写 |
| DP-RESP-01 | Responses(SSE) | `POST /v1/responses`；事件序列+唯一 terminal+`[DONE]`+usage（VRC-INF-001,T-STREAM） | data | 流式成功 + 事件序列 | A | P0 | `at_dp_resp_01.py` | 已写 |
| DP-RESP-02 | Responses(SSE) | `POST /v1/responses`；`stream=false`→400 unsupported_request（ERR-REQ-UNSUPPORTED） | data | stream=false 被拒 | A | P0 | `at_dp_resp_02.py` | 已写 |
| DP-RESP-03 | Responses(SSE) | `POST /v1/responses`；推理输出 SSE 结构（`output_text.delta` 非空、终态 `completed`；不把模型内容当 oracle）（VRC-INF-001,T-STREAM） | data | 推理输出结构（不含内容 oracle） | A | P1 | `at_dp_resp_03.py` | 已写 |
| DP-RESP-04 | Responses(SSE) | `POST /v1/responses`；`tools` 透传（VRC-INF-001,T-TOOLS） | data | tools 透传 | A | P1 | `at_dp_resp_04.py` | 已写 |
| DP-RESP-05 | Responses(SSE) | `POST /v1/responses`；未知 model→404 model_not_found（ERR-MODEL-NOTFOUND,VRC-INF-001/004） | data | unknown model 路由失败 | A | P0 | `at_dp_resp_05.py` | 已写 |
| DP-RESP-06 | Responses(SSE) | `POST /v1/responses`；`stream=true` 受理（VRC-INF-001,T-STREAM） | data | stream=true 唯一受理形态 | A | P0 | `at_dp_resp_06.py` | 已写 |
| DP-RESP-07 | Responses(SSE) | `POST /v1/responses`；`store=true`→400 unsupported_request（ERR-REQ-UNSUPPORTED,LT-INT-006） | data | store=true 被拒 | A | P0 | `at_dp_resp_07.py` | 已写 |
| DP-RESP-08 | Responses(SSE) | `POST /v1/responses`；缺 `model`→400 invalid_request,param=model（ERR-REQ-VALIDATION,LT-FUN-001） | data | 缺 model | A | P0 | `at_dp_resp_08.py` | 已写 |
| DP-RESP-09 | Responses(SSE) | `POST /v1/responses`；禁字段 `previous_response_id`→400 unsupported_field（ERR-REQ-FIELD,LT-FUN-001） | data | 禁字段 previous_response_id | A | P0 | `at_dp_resp_09.py` | 已写 |
| DP-RESP-10 | Responses(SSE) | `POST /v1/responses`；`max_output_tokens=10`→incomplete（VRC-INF-001,T-STREAM） | data | max_output_tokens 截断 | A | P1 | `at_dp_resp_10.py` | 已写 |
| DP-RESP-11 | Responses(SSE) | `POST /v1/responses`+注入 fault_502→502/503 provider_failure（VRC-DIAG-004,T-OBS-INJECT,ERR-PROVIDER-INJECTED） | data | 注入上游 502 → provider_failure | B | P0 | `at_dp_resp_11.py` | 已写 |
| DP-RESP-12 | Responses(SSE) | `POST /v1/responses`；未知字段 `conversation_id`→400 invalid_request（ERR-REQ-VALIDATION,VRC-INF-001） | data | conversation_id 未知字段被拒 | A | P2 | `at_dp_resp_12.py` | 已写 |
| DP-RESP-13 | Responses(SSE) | `POST /v1/responses`；未知字段 `truncation`→400 invalid_request（ERR-REQ-VALIDATION,VRC-INF-001） | data | truncation 未知字段被拒 | A | P2 | `at_dp_resp_13.py` | 已写 |
| DP-RESP-14 | Responses(SSE) | `POST /v1/responses`；未知字段 `max_tokens`（非 `max_output_tokens`）→400 invalid_request（ERR-REQ-VALIDATION,VRC-INF-001） | data | max_tokens 未知字段被拒 | A | P2 | `at_dp_resp_14.py` | 已写 |
| DP-RESP-15 | Responses(SSE) | `POST /v1/responses`；`temperature` 接受、未知字段 `top_p`→400 invalid_request（ERR-REQ-VALIDATION,VRC-INF-001） | data | temperature 接受 / top_p 未知字段被拒 | A | P2 | `at_dp_resp_15.py` | 已写 |
| DP-RESP-16 | Responses(SSE) | `POST /v1/responses`；非法 JSON→400 invalid_json（ERR-REQ-JSON,LT-FUN-001） | data | 非法 JSON body | B | P1 | MISSING | 已写 |
| DP-RESP-17 | Responses(SSE) | `POST /v1/responses`；embedding-only 等级→400 unsupported_model（ERR-REQ-MODEL） | data | embedding-only 等级发 Responses | A | P1 | MISSING | 已写 |
| DP-RESP-18 | Responses(SSE) | `POST /v1/responses`；body 超 2 MB→413 request_too_large（ERR-REQ-TOO-LARGE,VRC-INF-001） | data | body 超 2 MB | B | P2 | MISSING | 已写 |
| DP-RESP-19 | Responses(SSE) | `POST /v1/responses`；全部候选不健康→503 model_unavailable（ERR-MODEL-UNAVAIL,VRC-INF-004） | data | 全部候选不健康 | B | P1 | MISSING | 已写 |
| DP-RESP-20 | Responses(SSE) | `POST /v1/responses`；准入饱和→429 rate_limit_exceeded+Retry-After（ERR-RATE-LIMIT,T-QUEUE,VRC-INF-004） | data | 准入饱和 → 429 | B | P1 | MISSING | 已写 |
| DP-RESP-21 | Responses(SSE) | `POST /v1/responses`；客户端中途断开→aborted（T-DISCONNECT,VRC-INF-001） | data | 客户端中途断开 | B | P1 | MISSING | 已写 |
| DP-RESP-22 | Responses(SSE) | `POST /v1/responses`+注入 `fault_503`→503 provider_unavailable（ERR-PROVIDER-UNAVAIL,R-INF-05,T-OBS-INJECT） | data | 注入上游 503 → provider_unavailable | B | P1 | MISSING | 已写 |
| DP-RESP-23 | Responses(SSE) | `POST /v1/responses`；上游非成功 HTTP→沿用上游状态 provider_error（ERR-PROVIDER-FAIL,R-INF-05） | data | 上游 4xx/5xx → provider_error | B | P1 | MISSING | 已写 |
| DP-RESP-24 | Responses(SSE) | `POST /v1/responses`；`secret_ref` 不可解析→503 provider_secret_unavailable（ERR-PROVIDER-SECRET,R-INF-05） | data | provider 凭据缺失 | B | P1 | MISSING | 已写 |
| DP-RESP-25 | Responses(SSE) | `POST /v1/responses`；上游响应无法归一→502 provider_contract_error（ERR-PROVIDER-CONTRACT,R-INF-05） | data | 上游契约错误 | B | P1 | MISSING | 已写 |
| DP-EMB-01 | Embeddings | `POST /v1/embeddings`；1024 维 finite（VRC-INF-001,LT-FUN-003） | data | 基本 embedding | A | P0 | `at_dp_emb_01.py` | 已写 |
| DP-EMB-02 | Embeddings | `POST /v1/embeddings`；`encoding_format=base64`（VRC-INF-001,LT-FUN-003） | data | base64 编码 | A | P0 | `at_dp_emb_02.py` | 已写 |
| DP-EMB-03 | Embeddings | `POST /v1/embeddings`；同输入 ×5 不变量（VRC-INF-002,LT-FUN-003） | data | 不变量（同输入 ×5） | A | P1 | `at_dp_emb_03.py` | 已写 |
| DP-EMB-04 | Embeddings | `POST /v1/embeddings`；未知 model→404 model_not_found（ERR-MODEL-NOTFOUND,VRC-INF-001） | data | unknown model | A | P0 | `at_dp_emb_04.py` | 已写 |
| DP-EMB-05 | Embeddings | `POST /v1/embeddings`；batch 33（VRC-INF-002） | data | batch 33 不强制上限 | A | P2 | `at_dp_emb_05.py` | 已写 |
| DP-EMB-06 | Embeddings | `POST /v1/embeddings`；`dimensions=768`→400 unsupported_dimensions（ERR-REQ-DIM） | data | dimensions 与冻结空间不符 | A | P1 | MISSING | 已写 |
| DP-EMB-07 | Embeddings | `POST /v1/embeddings`；`encoding_format ∉ {float,base64}`（如 `hex`）→400 invalid_request,param=encoding_format（ERR-REQ-VALIDATION,VRC-INF-001） | data | 非法 encoding_format | A | P2 | MISSING | 已写 |
| DP-USAGE-01 | Usage 查询 | `GET /v1/usage`；时间窗+cursor 元数据（VRC-MGMT-006,R-MET-02） | data | 时间窗查询 | A | P0 | `at_dp_usage_01.py` | 已写 |
| DP-USAGE-02 | Usage 查询 | `GET /v1/usage`；请求后可见记录（VRC-MGMT-006,T-MET-FINAL） | data | 请求后可见记录 | A | P1 | `at_dp_usage_02.py` | 已写 |
| DP-USAGE-03 | Usage 查询 | `GET /v1/usage`；`limit=1` cursor 分页（VRC-MGMT-006,T-MET-PAGE） | data | cursor 分页 | A | P1 | `at_dp_usage_03.py` | 已写 |
| DP-USAGE-04 | Usage 查询 | `GET /v1/usage`；过期 cursor→400 cursor_expired（ERR-CURSOR,T-MET-PAGE） | data | 过期 cursor | A | P2 | `at_dp_usage_04.py` | 已写 |
| DP-USAGE-05 | Usage 查询 | `GET /v1/usage`；缺 `from`/`to`→400 invalid_request（ERR-REQ-VALIDATION） | data | 缺 from/to | A | P1 | MISSING | 已写 |
| DP-USAGE-06 | Usage 查询 | `GET /v1/usage`；data ⊆ admin 主体隔离（VRC-MGMT-006,T-TRUST-SHARED,R-MET-02） | data/admin | 主体隔离：data 只见自身，admin 见全局 | A | P1 | MISSING | 已写 |
| DP-USAGE-07 | Usage 查询 | `GET /v1/usage`；同一 cursor 重放返回同一冻结 record version 成员（幂等/重放，R-MET-02,T-MET-PAGE） | data | 分页重放幂等 | A | P1 | MISSING | 已写 |
| DP-USAGE-08 | Usage 查询 | `GET /v1/usage`；store 不可用→503 usage_store_unavailable（ERR-STORE,R-MET-04） | data | store 不可用不返回空页 | B | P1 | MISSING | 已写 |
| ADM-PROV-01 | Provider CRUD | `GET /v1/providers`；列表+`has_more`（VRC-MGMT-001） | admin | 列出 providers | A | P0 | `at_adm_prov_01.py` | 已写 |
| ADM-PROV-02 | Provider CRUD | `POST /v1/providers`；201+自动 id+has_secret（VRC-MGMT-001,R-CFG-01） | admin | 创建 provider | B | P0 | `at_adm_prov_02.py` | 已写 |
| ADM-PROV-03 | Provider CRUD | `GET /v1/providers/{id}`；详情字段（VRC-MGMT-001） | admin | 获取 provider 详情 | A | P0 | `at_adm_prov_03.py` | 已写 |
| ADM-PROV-04 | Provider CRUD | `GET /v1/providers/{id}`；不存在→404 not_found（ERR-NOTFOUND,VRC-MGMT-001） | admin | 不存在 provider | A | P0 | `at_adm_prov_04.py` | 已写 |
| ADM-PROV-05 | Provider CRUD | `PATCH /v1/providers/{id}`；If-Match/ETag（VRC-MGMT-002,T-CFG-CAS） | admin | 更新 provider | B | P0 | `at_adm_prov_05.py` | 已写 |
| ADM-PROV-06 | Provider CRUD | `PATCH`；缺 If-Match→412 version_conflict（ERR-STALE,T-CFG-CAS） | admin | 更新缺 If-Match | B | P0 | `at_adm_prov_06.py` | 已写 |
| ADM-PROV-07 | Provider CRUD | `PATCH`；过期 ETag→412 version_conflict（ERR-STALE） | admin | 过期 ETag | B | P1 | `at_adm_prov_07.py` | 已写 |
| ADM-PROV-08 | Provider CRUD | `DELETE /v1/providers/{id}`；204（VRC-MGMT-001） | admin | 删除 provider | B | P0 | `at_adm_prov_08.py` | 已写 |
| ADM-PROV-09 | Provider CRUD | `DELETE`；缺 If-Match→412 version_conflict（ERR-STALE） | admin | 删除缺 If-Match | B | P1 | `at_adm_prov_09.py` | 已写 |
| ADM-PROV-10 | Provider CRUD | `DELETE`；被引用→409 resource_in_use（ERR-INUSE,T-CFG-DELREF） | admin | 删除被引用 provider | B | P1 | `at_adm_prov_10.py` | 已写 |
| ADM-PROV-11 | Provider CRUD | `POST`；`kind` 非法→400 invalid_request（VRC-MGMT-001） | admin | kind 枚举校验 | B | P1 | `at_adm_prov_11.py` | 已写 |
| ADM-PROV-12 | Provider CRUD | `POST`；`secret_ref` 格式（T-CFG-SECRET） | admin | secret_ref 格式 | B | P2 | `at_adm_prov_12.py` | 已写 |
| ADM-PROV-13 | Provider CRUD | `PATCH`；usage 子对象更新（VRC-MGMT-002） | admin | usage 子对象更新 | B | P2 | `at_adm_prov_13.py` | 已写 |
| ADM-PROV-14 | Provider CRUD | `GET /v1/providers` 与 `GET /v1/providers/{id}`；**响应永不回显 secret 值**（仅 `has_secret`/`secret_ref` 引用）（LT-SEC-001,VRC-MGMT-001,R-CFG-01,T-CFG-SECRET） | admin | provider 不泄露 secret | A | P0 | MISSING | 已写 |
| ADM-PROV-MODELS-01 | provider 上游模型目录 | `GET /v1/providers/{id}/models`（VRC-MGMT-001,R-CFG-01） | admin | provider 上游模型目录 | A | P1 | MISSING | 已写 |
| ADM-PROV-MODELS-02 | provider 上游模型目录 | `GET /v1/providers/{id}/models`；未知 id→404 not_found（ERR-NOTFOUND） | admin | 不存在 provider | A | P1 | MISSING | 已写 |
| ADM-PROV-USAGE-01 | provider usage 快照 | `GET /v1/providers/{id}/usage`（VRC-MGMT-006） | admin | 读取 provider usage 快照 | A | P1 | `at_adm_prov_usage_01.py` | 已写 |
| ADM-PROV-USAGE-02 | provider usage 快照 | `POST /v1/providers/{id}/usage`；缺确认→400（ERR-CONFIRM） | admin | 刷新缺确认 | A | P1 | `at_adm_prov_usage_02.py` | 已写 |
| ADM-PROV-USAGE-03 | provider usage 快照 | `POST /v1/providers/{id}/usage`；带确认→200（T-CFG-SECRET） | admin | 刷新带确认 | A | P1 | `at_adm_prov_usage_03.py` | 已写 |
| ADM-PROV-USAGE-04 | provider usage 快照 | `GET /v1/providers/{id}/usage`；未知 provider→404 not_found（ERR-NOTFOUND,R-CFG-01） | admin | usage 未知 provider | A | P1 | MISSING | 已写 |
| ADM-DEPL-01 | Deployment CRUD | `GET /v1/deployments`；列表（VRC-MGMT-001） | admin | 列出 deployments | A | P0 | `at_adm_depl_01.py` | 已写 |
| ADM-DEPL-02 | Deployment CRUD | `POST /v1/deployments`；201+capabilities 12 键（VRC-MGMT-001） | admin | 创建 deployment | B | P0 | `at_adm_depl_02.py` | 已写 |
| ADM-DEPL-03 | Deployment CRUD | `GET /v1/deployments/{id}`（VRC-MGMT-001） | admin | 获取 deployment | A | P0 | `at_adm_depl_03.py` | 已写 |
| ADM-DEPL-04 | Deployment CRUD | `PATCH /v1/deployments/{id}`；If-Match，provider_id 不可改（VRC-MGMT-002） | admin | 更新 deployment | B | P1 | `at_adm_depl_04.py` | 已写 |
| ADM-DEPL-05 | Deployment CRUD | `DELETE /v1/deployments/{id}`；204（VRC-MGMT-001） | admin | 删除 deployment | B | P0 | `at_adm_depl_05.py` | 已写 |
| ADM-DEPL-06 | Deployment CRUD | `POST`；capabilities 缺字段→400（VRC-MGMT-001） | admin | capabilities 缺字段 | B | P1 | `at_adm_depl_06.py` | 已写 |
| ADM-DEPL-07 | Deployment CRUD | `POST`；capabilities 未知字段→400（VRC-MGMT-001） | admin | capabilities 未知字段 | B | P1 | `at_adm_depl_07.py` | 已写 |
| ADM-DEPL-08 | Deployment CRUD | `POST`；引用不存在 provider→400（ERR-REQ-VALIDATION） | admin | 引用不存在 provider | B | P1 | `at_adm_depl_08.py` | 已写 |
| ADM-DEPL-09 | Deployment CRUD | `PATCH`；`provider_id` 不可改→400（VRC-MGMT-002） | admin | provider_id 不可 PATCH | B | P1 | `at_adm_depl_09.py` | 已写 |
| ADM-SL-01 | Service Level CRUD | `GET /v1/service-levels`；7 fixed tier（VRC-MGMT-002） | admin | 列出 service-levels | A | P0 | `at_adm_sl_01.py` | 已写 |
| ADM-SL-02 | Service Level CRUD | `POST /v1/service-levels`；非 fixed tier→400（VRC-MGMT-002） | admin | 创建非 fixed tier | B | P1 | `at_adm_sl_02.py` | 已写 |
| ADM-SL-02b | Service Level CRUD | `POST /v1/service-levels`；已存在 fixed tier→409 resource_conflict（ERR-CONFLICT） | admin | 创建已存在 fixed tier | B | P1 | `at_adm_sl_02b.py` | 已写 |
| ADM-SL-03 | Service Level CRUD | `GET /v1/service-levels/{id}`（VRC-MGMT-002） | admin | 获取 service-level | A | P0 | `at_adm_sl_03.py` | 已写 |
| ADM-SL-04 | Service Level CRUD | `PATCH /v1/service-levels/{id}`；If-Match（VRC-MGMT-002） | admin | 更新 service-level | B | P1 | `at_adm_sl_04.py` | 已写 |
| ADM-SL-04b | Service Level CRUD | `PATCH`；非法字段→400（VRC-MGMT-002） | admin | 更新非法字段 | B | P1 | `at_adm_sl_04b.py` | 已写 |
| ADM-SL-05 | Service Level CRUD | `DELETE /v1/service-levels/{id}` fixed tier→409 fixed_service_level（ERR-FIXED-LEVEL） | admin | 删除 fixed tier | B | P0 | `at_adm_sl_05.py` | 已写 |
| ADM-SL-06 | Service Level CRUD | `PATCH`；成员能力不一致→409 capability_conflict（ERR-CAPABILITY,R-CFG-01） | admin | 成员能力不一致 | B | P2 | `at_adm_sl_06.py` | 已写 |
| ADM-SL-07 | Service Level CRUD | `PATCH`；冻结向量空间冲突→409 embedding_space_conflict（ERR-EMBEDDING-SPACE） | admin | 冻结向量空间冲突 | B | P2 | `at_adm_sl_07.py` | 已写 |
| ADM-SL-08 | Service Level CRUD | `PATCH /v1/service-levels/{id}`；`deployment_ids` 非数组→500 internal_error 信封（ERR-INTERNAL,R-CFG-01；同时登记"非法类型未预校验"缺陷） | admin | 内部错误信封（非数组输入） | B | P2 | MISSING | 已写 |
| ADM-PROBE-01 | 探测 | `POST /v1/probes`；缺确认→400 confirmation_required（ERR-CONFIRM,VRC-DIAG-004） | admin | 探测缺确认 | A | P0 | `at_adm_probe_01.py` | 已写 |
| ADM-PROBE-02 | 探测 | `POST /v1/probes`；带确认→200 status（VRC-DIAG-004） | admin | 探测带确认 | A | P1 | `at_adm_probe_02.py` | 已写 |
| ADM-PROBE-03 | 探测 | `POST /v1/probes`；未知 deployment→404 not_found（ERR-NOTFOUND） | admin | 探测未知 deployment | B | P1 | MISSING | 已写 |
| ADM-RUNTIME-01 | 运行态 | `GET /v1/runtime`；运行时快照（VRC-INF-004） | admin | 运行时快照 | A | P1 | `at_adm_runtime_01.py` | 已写 |
| ADM-RUNTIME-02 | 运行态 | `GET /v1/runtime`；data token→403 permission_denied（ERR-AUTH-DENIED,R-TRUST-02） | data | 运行时快照负向（角色） | A | P1 | MISSING | 已写 |
| ADM-STATS-01 | 统计 | `GET /v1/stats`；聚合（VRC-MGMT-006） | admin | 统计聚合 | A | P1 | `at_adm_stats_01.py` | 已写 |
| ADM-STATS-02 | 统计 | `GET /v1/stats`；`group_by=tier`（VRC-MGMT-006） | admin | 分组 | A | P2 | `at_adm_stats_02.py` | 已写 |
| ADM-STATS-03 | 统计 | `GET /v1/stats`；缺时间窗→400（ERR-REQ-VALIDATION） | admin | 缺时间窗 | A | P1 | `at_adm_stats_03.py` | 已写 |
| ADM-AUDIT-01 | 审计 | `GET /v1/audit`；字段齐全+脱敏（VRC-MGMT-003,R-OBS-01,T-TRUST-LEAK） | admin | 审计事件 + 脱敏 | A | P0 | `at_adm_audit_01.py` | 已写 |
| ADM-AUDIT-02 | 审计 | `GET /v1/audit`；`limit=1` 分页（VRC-MGMT-006,T-MET-PAGE） | admin | 审计分页 | A | P1 | `at_adm_audit_02.py` | 已写 |
| ADM-AUDIT-03 | 审计 | `GET /v1/audit`；`limit=abc`→400 invalid_request（ERR-REQ-VALIDATION,R-OBS-01） | admin | 审计非法分页参数 | A | P1 | MISSING | 已写 |
| ADM-LOGS-01 | 日志 | `GET /v1/logs`；脱敏（VRC-LOG-001,T-TRUST-LEAK） | admin | 脱敏日志 | A | P0 | `at_adm_logs_01.py` | 已写 |
| ADM-LOGS-02 | 日志 | `GET /v1/logs`；缺时间窗→400（ERR-REQ-VALIDATION） | admin | 缺时间窗 | A | P1 | `at_adm_logs_02.py` | 已写 |
| ADM-USAGE-01 | 管理 usage | `GET /v1/usage`；聚合（VRC-MGMT-006） | admin | 管理面 usage | A | P1 | `at_adm_admin_usage_01.py` | 已写 |
| ADM-USAGE-02 | 管理 usage | `GET /v1/usage`；`limit=1` 分页（VRC-MGMT-006,T-MET-PAGE） | admin | 管理面分页 | A | P1 | `at_adm_admin_usage_02.py` | 已写 |
| ADM-USAGE-03 | 管理 usage | `DELETE /v1/usage`；deleted+审计+角色（T-MET-RESET） | admin | 清空 usage（admin + 审计） | A | P1 | `at_adm_admin_usage_03.py` | 已写 |
| OBS-DIAG-01 | 诊断开关 | `GET /v1/diagnostics`；SwitchState（VRC-DIAG-001,T-OBS-SWITCH） | admin | 读取诊断开关 | A | P1 | MISSING | 已写 |
| OBS-DIAG-02 | 诊断开关 | `PATCH /v1/diagnostics`；更新+审计（VRC-DIAG-001,T-OBS-SWITCH） | admin | 更新诊断开关 | B | P1 | MISSING | 已写 |
| OBS-DIAG-03 | 诊断开关 | `PATCH /v1/diagnostics`；非法值→400（ERR-REQ-VALIDATION） | admin | 开关更新非法值 | B | P2 | MISSING | 已写 |
| OBS-SNAP-01 | 诊断快照 | `GET /v1/diagnostics/snapshots`；SnapshotPage 脱敏（VRC-DIAG-002,T-OBS-SNAP） | admin | 快照页（脱敏） | A | P1 | MISSING | 已写 |
| OBS-SNAP-02 | 诊断快照 | `GET /v1/diagnostics/snapshots`；无效 cursor→400（ERR-CURSOR,T-MET-PAGE） | admin | 快照无效 cursor | B | P2 | MISSING | 已写 |
| OBS-STATS-01 | 诊断统计 | `GET /v1/diagnostics/stats`；聚合窗口（VRC-DIAG-002,T-OBS-STATS） | admin | 诊断统计窗口 | A | P1 | MISSING | 已写 |
| OBS-STATS-02 | 诊断统计 | `GET /v1/diagnostics/stats`；缺 `since`/`until`→400（ERR-REQ-VALIDATION） | admin | 统计缺 since/until | A | P1 | MISSING | 已写 |
| OBS-TRACE-01 | 诊断 trace | `GET /v1/diagnostics/traces`；去重稳定分页（VRC-DIAG-002,T-OBS-TRACE） | admin | trace 列表去重 | A | P1 | MISSING | 已写 |
| OBS-TRACE-02 | 诊断 trace | `GET /v1/diagnostics/traces`；`limit=1` 分页/非法 cursor→400（ERR-CURSOR,T-MET-PAGE） | admin | trace 列表分页/游标 | B | P2 | MISSING | 已写 |
| OBS-DEPL-01 | 注入配置 | `GET /v1/deployments/{id}/diagnostics`；InjectionView[]（VRC-DIAG-004,T-OBS-INJECT） | admin | 读取 deployment 注入配置 | A | P0 | MISSING | 已写 |
| OBS-DEPL-02 | 注入配置 | `PATCH /v1/deployments/{id}/diagnostics`；写入注入（VRC-DIAG-004,T-OBS-INJECT） | admin | 写入故障注入 | B | P0 | MISSING | 已写 |
| OBS-DEPL-03 | 注入配置 | `PATCH`；未知 deployment→404 not_found（ERR-NOTFOUND） | admin | 注入未知 deployment | B | P1 | MISSING | 已写 |
| OBS-DEPL-04 | 注入配置 | `PATCH`；非法注入项→400 invalid_injection（ERR-INJECTION,T-OBS-INJECT） | admin | 非法注入项 | B | P1 | MISSING | 已写 |
| OBS-REQTRACE-01 | 请求追踪 | `GET /v1/trace/{request_id}`；TraceView 全阶段（VRC-DIAG-002,T-OBS-TRACE） | admin | 请求全生命周期 trace | A | P1 | MISSING | 已写 |
| OBS-REQTRACE-02 | 请求追踪 | `GET /v1/trace/{request_id}`；未知 id→404 not_found（ERR-NOTFOUND） | admin | 未知 request_id | A | P1 | MISSING | 已写 |
| OBS-REQTRACE-03 | 请求追踪 | `GET /v1/trace/{request_id}`；data token→403 permission_denied（ERR-AUTH-DENIED,R-TRUST-02） | data | 请求追踪负向（角色） | A | P1 | MISSING | 已写 |
| OBS-ALIAS-01 | 契约别名 | `GET`+`PATCH /tier/admin/v1/diagnostics`；与 `/v1/diagnostics` 逐字节等价（VRC-DIAG-001,T-TRUST-SHARED） | admin | 别名 diagnostics（GET+PATCH） | A | P1 | MISSING | 已写 |
| OBS-ALIAS-02 | 契约别名 | `GET /tier/admin/v1/diagnostics/snapshots`；与扁平路径等价（VRC-DIAG-002） | admin | 别名 diagnostics/snapshots | A | P2 | MISSING | 已写 |
| OBS-ALIAS-03 | 契约别名 | `GET /tier/admin/v1/trace/{request_id}`；与 `/v1/trace/{id}` 等价（VRC-DIAG-002） | admin | 别名 trace | A | P2 | MISSING | 已写 |
| OBS-ALIAS-04 | 契约别名 | `GET`+`PATCH /tier/admin/v1/deployments/{id}/diagnostics`；同 handler（VRC-DIAG-004,T-OBS-INJECT） | admin | 别名 deployments diagnostics（GET+PATCH） | B | P2 | MISSING | 已写 |
| OBS-ALIAS-05 | 契约别名 | `GET /tier/admin/v1/diagnostics/stats`；与扁平路径等价（VRC-DIAG-002,R-OBS-02,T-OBS-STATS） | admin | 别名 diagnostics/stats | A | P2 | MISSING | 已写 |
| OBS-ALIAS-06 | 契约别名 | `GET /tier/admin/v1/diagnostics/traces`；与扁平路径等价（VRC-DIAG-002,R-OBS-02,T-OBS-TRACE） | admin | 别名 diagnostics/traces | A | P2 | MISSING | 已写 |
| AUTH-01 | 认证/授权 | `GET /v1/models`；LAN trust 无 token→200（T-TRUST-LAN,VRC-API-002） | none | Data 端点 LAN trust 无 token | A | P0 | `at_auth_01.py` | 已写 |
| AUTH-02 | 认证/授权 | `GET /v1/models`；错误 bearer→403 permission_denied（ERR-AUTH-DENIED） | data | 错误 bearer | A | P0 | `at_auth_02.py` | 已写 |
| AUTH-03 | 认证/授权 | `GET /v1/providers`；data token→403 permission_denied（ERR-AUTH-DENIED,R-TRUST-02） | data | Data token 访问 admin 面 | A | P0 | `at_auth_03.py` | 已写 |
| AUTH-04 | 认证/授权 | `GET /v1/providers`；LAN trust 无 token→200（T-TRUST-LAN） | none | Admin 端点 LAN trust 无 token | A | P0 | `at_auth_04.py` | 已写 |
| AUTH-05 | 认证/授权 | `GET /healthz`；公共端点无 token→200（T-TRUST-NOCFG） | none | 公共端点无需 token | A | P0 | `at_auth_05.py` | 已写 |
| AUTH-06 | 认证/授权 | `GET /v1/models`；空 bearer→403 permission_denied（ERR-AUTH-DENIED） | data | 空 bearer | A | P2 | `at_auth_06.py` | 已写 |
| AUTH-07 | 认证/授权 | 受保护端点；未配置鉴权→503 auth_not_configured（ERR-AUTH-NOCFG,VRC-MGMT-003,T-TRUST-NOCFG） | none | 未配置鉴权 | B | P0 | `at_auth_07.py` | 已写 |
| AUTH-08 | 认证/授权 | `GET /tier/admin/v1/diagnostics`；data token→403 permission_denied（R-TRUST-02,T-TRUST-SHARED） | data | 别名命名空间需 admin | A | P1 | MISSING | 已写 |
| AUTH-09 | 认证/授权 | `GET /v1/providers/{id}`；data token→403（不泄露 not_found）（ERR-AUTH-DENIED,T-TRUST-LEAK） | data | 管理面未授权优先于资源存在性 | A | P1 | MISSING | 已写 |
| AUTH-10 | 认证/授权 | 受保护端点；无 Bearer 且不命中免登录，或非法授权方案（如 `Basic`）→401 authentication_required（ERR-AUTH-REQUIRED,R-TRUST-01,T-TRUST-BEARER） | none | 缺/非法凭据 401 | A | P1 | MISSING | 已写 |

**分类汇总（与上表一致，交叉核对）**：

| Case ID 段 | 分类 | 端点 / 角色 | 数量 | A / B |
|---|---|---|---|---|
| `HEALTH-01..06` | 无认证健康/就绪 | `GET /healthz`、`GET /readyz`；无鉴权 | 6 | A 2 / B 4 |
| `DP-MODELS-01..07` | 逻辑模型清单 | `GET /v1/models`、`/v1/models/{model}`；data | 7 | A 7 |
| `DP-RESP-01..25` | Responses（SSE） | `POST /v1/responses`；data | 25 | A 15 / B 10 |
| `DP-EMB-01..07` | Embeddings | `POST /v1/embeddings`；data | 7 | A 7 |
| `DP-USAGE-01..08` | Usage 查询 | `GET /v1/usage`；data / admin | 8 | A 7 / B 1 |
| `ADM-PROV-01..14` | Provider CRUD | `/v1/providers(/{id})`；admin | 14 | A 4 / B 10 |
| `ADM-PROV-MODELS-01..02` | provider 上游模型目录 | `GET /v1/providers/{id}/models`；admin | 2 | A 2 |
| `ADM-PROV-USAGE-01..04` | provider usage 快照 | `/v1/providers/{id}/usage`；admin | 4 | A 4 |
| `ADM-DEPL-01..09` | Deployment CRUD | `/v1/deployments(/{id})`；admin | 9 | A 2 / B 7 |
| `ADM-SL-01..07(+02b,04b,08)` | Service Level CRUD | `/v1/service-levels(/{id})`；admin | 10 | A 2 / B 8 |
| `ADM-PROBE/RUNTIME/STATS/AUDIT/LOGS/USAGE` | 探测/运行态/统计/审计/日志/管理 usage | `/v1/probes`、`/v1/runtime`、`/v1/stats`、`/v1/audit`、`/v1/logs`、`DELETE /v1/usage`；admin | 16 | A 15 / B 1 |
| `OBS-01..22` | 观测/诊断/追踪/别名 | `/v1/diagnostics*`、`/v1/deployments/{id}/diagnostics`、`/v1/trace/{id}`、`/tier/admin/v1/*`；admin | 22 | A 14 / B 8 |
| `AUTH-01..10` | 认证与授权 | 全端点角色 / LAN trust / no-auth | 10 | A 9 / B 1 |

**Case 计数**：HEALTH 6 + DP-MODELS 7 + DP-RESP 25 + DP-EMB 7 + DP-USAGE 8 + ADM 55（14+2+4+9+10+16）+ OBS 22 + AUTH 10 = **140 个 Case**（RUN 88 / MISSING 52；A 90 / B 50；P0 45 / P1 72 / P2 23）。125 原有 + 15 新增（AUTH-10、DP-RESP-22..25、DP-USAGE-07..08、ADM-PROV-14、ADM-PROV-USAGE-04、ADM-RUNTIME-02、ADM-AUDIT-03、ADM-SL-08、OBS-REQTRACE-03、OBS-ALIAS-05..06）= 140；**以 §3.2 逐行权威清单为准**。

### 3.3 每 Case 详细设计文档契约

**目的**：每个 Case 有**且仅有一份独立详细设计文档**，承载该 Case 的前置/输入/执行/Oracle/判定/证据/清理。本规格只**规约其模板与落位**，不在此展开逐 Case 细节。case 文档通过引用（而非复制）§2 环境、§4 共同机制、§9 判定、§10 证据。

**落位与命名**：

- 目录：`docs/70_verification/specifications/cases/`
- 文件名：`<case-id>.md`，`<case-id>` 为 Case ID **小写**（例 `docs/70_verification/specifications/cases/dp-resp-01.md`、`docs/70_verification/specifications/cases/adm-sl-02b.md`）。
- 与报告分离：设计写在该文件；Run 证据写在 `tests/system/reports/<date>/<A-api|B-api>/<case-id>/`（§10）。

**固定字段（必须齐备，固定顺序）**：

| 字段 | 必填 | 内容要求 |
|---|---|---|
| Case ID | 是 | 与 §3.2 权威清单一致的 Case ID；与本文件名对应且唯一 |
| 标题 | 是 | 一句话被测行为（与 §3.2 一致或更具体） |
| 目的（被测契约） | 是 | 被测端点/规则、设计 V（`VRC-*`）、机制（`T-*`）、错误码；并说明"不证明什么" |
| 前置与环境 | 是 | A/B 环境（§2.3）、§2.1 就绪检查、fixture（§4.4）、初始状态；引用而不重复 §2 |
| 输入与构造 | 是 | 固定输入、body/headers/ETag/cursor/时间窗构造、边界与非法输入、种子；LLM Case 用固定 prompt |
| 执行过程（逐步调用） | 是 | 有序调用序列（含前置调用，如注入/先发请求），每步的请求与观察点 |
| 重点关注步骤 | 是 | 该 Case 最易误判/易漏的步骤（如 terminal 唯一、拒绝零副作用、注入命中证明） |
| 期望结果与独立 Oracle | 是 | 与实现独立的预期：HTTP status、body 关键字段、错误 `code`、SSE 事件序列；禁止写"答案正确" |
| 判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID） | 是 | 六态判定（§9）：该 Case 达到 PASS 的充分条件；FAIL/BLOCKED/SKIP/NOT_RUN/INVALID 判据引用 §9 全局定义 |
| 证据与 Run | 是 | 必须保存的原始证据、Run ID（§4.8）、保存位置（§10） |
| 清理与复位 | 是 | teardown / 恢复字段与 version / 删除本次创建物 / 清空注入 / 复位 DB 值（§2.8、§4.7） |
| 依赖 | 是 | 依赖的其它 Case、fixture、上游服务、权限（如 DP-RESP-11 依赖 OBS-DEPL-02） |

**模板骨架**（case 文档以此结构填写；字段缺失视为设计状态未达 `已写`）：

```markdown
# <Case ID> — <标题>

- **Case ID**：
- **标题**：
- **目的（被测契约）**：
- **前置与环境**：
- **输入与构造**：
- **执行过程（逐步调用）**：
- **重点关注步骤**：
- **期望结果与独立 Oracle**：
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- **证据与 Run**：
- **清理与复位**：
- **依赖**：
```

**状态**：case 文档建立并满足上述字段要求后，§3.2 该 Case 的 `设计状态` 由 `待写` 更新为 `已写`。

### 3.4 逐 Case 详细设计文档索引

共 **140** 份 case 详细设计文档：`DP-RESP-01`（样例）、`DP-RESP-11`、`OBS-DIAG-01`、`AUTH-01` 已 `已写`，其余 **0** 份 `待写`。每份文档路径按 §3.3 由 Case ID 推导为 `docs/70_verification/specifications/cases/<case-id>.md`（小写）。**命名规则与模板契约见 [`cases/README.md`](cases/README.md)：所有 Case 一律遵循 `cases/<lowercased-case-id>.md`。** 逐 Case 的输入/Oracle/执行/判定/证据/清理见各自 case 文档；本规格不再内联维护。下表按类别汇总文档范围。

| 类别 | Case 段 | 待写文档数 | 文档路径模式 | 状态 |
|---|---|---|---|---|
| 无认证健康/就绪 | HEALTH-01..06 | 6 | `cases/health-01.md` … `cases/health-06.md` | 已写 6 / 待写 0 |
| 逻辑模型清单 | DP-MODELS-01..07 | 7 | `cases/dp-models-01.md` … `cases/dp-models-07.md` | 已写 7 / 待写 0 |
| Responses（SSE） | DP-RESP-01..25 | 25 | `cases/dp-resp-01.md` … `cases/dp-resp-25.md` | `DP-RESP-01`、`DP-RESP-11` 已写；其余 待写 |
| Embeddings | DP-EMB-01..07 | 7 | `cases/dp-emb-01.md` … `cases/dp-emb-07.md` | 已写 25 / 待写 0 |
| Usage 查询 | DP-USAGE-01..08 | 8 | `cases/dp-usage-01.md` … `cases/dp-usage-08.md` | 已写 7 / 待写 0 |
| Provider CRUD | ADM-PROV-01..14 | 14 | `cases/adm-prov-01.md` … `cases/adm-prov-14.md` | 已写 8 / 待写 0 |
| provider 上游模型目录 | ADM-PROV-MODELS-01..02 | 2 | `cases/adm-prov-models-01.md` … `cases/adm-prov-models-02.md` | 已写 14 / 待写 0 |
| provider usage 快照 | ADM-PROV-USAGE-01..04 | 4 | `cases/adm-prov-usage-01.md` … `cases/adm-prov-usage-04.md` | 已写 2 / 待写 0 |
| Deployment CRUD | ADM-DEPL-01..09 | 9 | `cases/adm-depl-01.md` … `cases/adm-depl-09.md` | 已写 4 / 待写 0 |
| Service Level CRUD | ADM-SL-01,02,02b,03,04,04b,05,06,07,08 | 10 | `cases/adm-sl-01.md` … `cases/adm-sl-08.md`（含 `adm-sl-02b.md`、`adm-sl-04b.md`） | 已写 9 / 待写 0 |
| 探测/运行态/统计/审计/日志/管理 usage | ADM-PROBE/RUNTIME/STATS/AUDIT/LOGS/USAGE | 16 | `cases/adm-probe-01.md` … `cases/adm-usage-03.md`（含 `adm-runtime-02.md`、`adm-audit-03.md`） | 已写 10 / 待写 0 |
| 观测/诊断/追踪/别名 | OBS-* | 22 | `cases/obs-diag-01.md` … `cases/obs-alias-06.md` | `OBS-DIAG-01` 已写；其余 待写 |
| 认证与授权 | AUTH-01..10 | 10 | `cases/auth-01.md` … `cases/auth-10.md` | `AUTH-01` 已写；其余 待写 |

**文档总数**：6+7+25+7+8+14+2+4+9+10+16+22+10 = **140**（已写 140 / 待写 0），与 §3.2 权威清单一一对应。

### 3.5 定量覆盖模型（route × method × role × error-code）

**目的**：给出可复核的定量覆盖，而不是"看起来覆盖了"。Case 一律按**主路由**只计一次（AUTH 为跨切面家族单列，避免与路由重复计数；AUTH-05 命中 `/healthz`、AUTH-08 命中别名，仅在注中说明）。下表合计 = 140 = §3.2 权威清单。

| 路由 | 方法 | 角色 | Case 数 | 正向 / 负向 | 覆盖错误码 |
|---|---|---|---:|---:|---|
| `/v1/responses` | POST | data | 25 | 12 / 13 | `invalid_request`、`unsupported_request`、`unsupported_field`、`invalid_json`、`request_too_large`、`model_not_found`、`model_unavailable`、`rate_limit_exceeded`、`provider_unavailable`、`provider_error`、`provider_failure`、`provider_secret_unavailable`、`provider_contract_error` |
| `/v1/embeddings` | POST | data | 7 | 4 / 3 | `invalid_request`、`unsupported_dimensions`、`model_not_found` |
| `/v1/models` | GET | data | 2 | 2 / 0 | —（负向由 AUTH-02/06 跨切面覆盖） |
| `/v1/models/{model}` | GET | data | 5 | 1 / 4 | `model_not_found` |
| `/v1/usage` | GET | data / admin | 10 | 6 / 4 | `invalid_request`、`cursor_expired`、`permission_denied`、`usage_store_unavailable` |
| `/v1/usage` | DELETE | admin | 1 | 1 / 0 | `permission_denied`、`usage_store_unavailable` |
| `/v1/providers` | GET / POST | admin | 5 | 3 / 2 | `invalid_request`、`not_found` |
| `/v1/providers/{id}` | GET / PATCH / DELETE | admin | 9 | 3 / 6 | `not_found`、`version_conflict`、`resource_in_use` |
| `/v1/providers/{id}/models` | GET | admin | 2 | 1 / 1 | `not_found` |
| `/v1/providers/{id}/usage` | GET / POST | admin | 4 | 2 / 2 | `confirmation_required`、`not_found` |
| `/v1/deployments` | GET / POST | admin | 5 | 2 / 3 | `invalid_request` |
| `/v1/deployments/{id}` | GET / PATCH / DELETE | admin | 4 | 3 / 1 | `invalid_request` |
| `/v1/service-levels` | GET / POST | admin | 3 | 1 / 2 | `invalid_request`、`resource_conflict` |
| `/v1/service-levels/{id}` | GET / PATCH / DELETE | admin | 7 | 2 / 5 | `fixed_service_level`、`capability_conflict`、`embedding_space_conflict`、`internal_error` |
| `/v1/probes` | POST | admin | 3 | 1 / 2 | `confirmation_required`、`not_found` |
| `/v1/runtime` | GET | admin | 2 | 1 / 1 | `permission_denied` |
| `/v1/stats` | GET | admin | 3 | 2 / 1 | `invalid_request` |
| `/v1/audit` | GET | admin | 3 | 2 / 1 | `invalid_request` |
| `/v1/logs` | GET | admin | 2 | 1 / 1 | `invalid_request` |
| `/v1/diagnostics` | GET / PATCH | admin | 3 | 1 / 2 | `invalid_request` |
| `/v1/diagnostics/snapshots` | GET | admin | 2 | 1 / 1 | `cursor_expired` |
| `/v1/diagnostics/stats` | GET | admin | 2 | 1 / 1 | `invalid_request` |
| `/v1/diagnostics/traces` | GET | admin | 2 | 1 / 1 | `cursor_expired` |
| `/v1/deployments/{id}/diagnostics` | GET / PATCH | admin | 4 | 2 / 2 | `not_found`、`invalid_injection` |
| `/v1/trace/{id}` | GET | admin / data | 3 | 1 / 2 | `not_found`、`permission_denied` |
| `/tier/admin/v1/*`（6 条别名路径） | GET / PATCH | admin | 6 | 6 / 0 | —（负向由 AUTH-08 覆盖） |
| `/healthz` | GET | none | 1 | 1 / 0 | — |
| `/readyz` | GET | none | 5 | 1 / 4 | —（503 body 为 `ReadinessView`，非 `ErrorEnvelope`，无 `code`；启动失败状态以 `status="not_ready"` 表达） |
| （跨切面 AUTH） | GET / POST | none / data / admin | 10 | 8 / 2（401/403/503） | `authentication_required`、`permission_denied`、`auth_not_configured` |
| **合计** | | | **140** | | |

**覆盖率结论**（分子/分母）：
- **路由覆盖**：**32/32 路由条目 = 100%**（24 条扁平 `/v1/*` 路径 + 6 条别名路径 + `/healthz`/`/readyz`）。别名 6/6，含 `diagnostics`、`diagnostics/snapshots`、`diagnostics/stats`、`diagnostics/traces`、`deployments/{id}/diagnostics`、`trace/{id}`，与 `openapi` `x-llmtier-contract-aliases` 一一对应。
- **负向覆盖**：除公开存活端点 `/healthz` 外，**31/31 路由条目 ≥1 负向 = 100%**（`/v1/models` 与 6 条别名的负向由跨切面 `AUTH-02/06/08` 承接，`/readyz` 由 HEALTH-03/04/05，见注）。
- **角色覆盖**：`none`（AUTH-01/04/05/07/10 + HEALTH）11 例、`data`、`admin` 三类均 ≥1 = 100%。
- **错误码覆盖**：`ERR-*` 目录共 34 个（含多 code 合并项），本规格以 Case 承接 **30 / 34 = 88.2%**，具名缺口 **4 / 34 = 11.8%**（`ERR-BOOT` 部分由 HEALTH-05 的 `/readyz not_ready` 表达，仍列具名缺口）。逐码映射见 §11.1。
- **P0 覆盖**：45 个 P0 Case 中 RUN 42 / MISSING 3 = 93.3%；3 个 P0 缺口为 `ADM-PROV-14`、`OBS-DEPL-01`、`OBS-DEPL-02`（MISSING，Gate 阻断，见 §9）。

> **注**：`/v1/models` 与 `/tier/admin/v1/*` 别名本身无独立负向 Case；按 §9 "覆盖门"，跨切面认证负向（AUTH-02/06 与 AUTH-08）计入对应路由的负向覆盖，不重复计入 AUTH 家族总数。

### 3.6 Traceability（`LT-*` → `R-*` → `VRC-*` → `T-*` → `CT-*` → Case）

**目的**：把 §3.2 每个 Case 家族追到需求（`LT-*`，[`llmtier-requirements.md`](../../10_requirements/llmtier-requirements.md)）、机制需求（`R-*`，[mechanisms/](../../20_system_design/mechanisms/)）、设计验证项（`VRC-*`）、机制测试项（`T-*`）与契约测试（`CT-*`，[`llmtier-traceability.md`](../../10_requirements/llmtier-traceability.md) / [`llmtier-contract-test-specification.md`](llmtier-contract-test-specification.md)）。任一 Case 详细设计文档（§3.3）的"目的"字段必须能回指本表。

| Case 家族 | 需求 `LT-*` | 机制需求 `R-*` | 设计验证 `VRC-*` | 机制 `T-*` | 契约 `CT-*` |
|---|---|---|---|---|---|
| `HEALTH-01..06` | LT-FUN-006、LT-OPS-001 | R-CFG-02、R-TRUST-04 | VRC-API-002、VRC-MGMT-003、VRC-UTIL-001/002 | T-TRUST-NOCFG、T-OBS | CT-OPS-001 |
| `DP-MODELS-01..07` | LT-FUN-002 | R-INF-04、R-INF-07 | VRC-INF-001/002 | T-TRUST-ENDPOINTS | CT-MODEL-001 |
| `DP-RESP-01..25` | LT-FUN-001/008、LT-INT-001/006、LT-PERF-001、LT-REL-001 | R-INF-01..06、R-TRUST-01、R-TRUST-02 | VRC-INF-001/003/004、VRC-DIAG-004 | T-STREAM、T-TOOLS、T-QUEUE、T-TIMEOUT、T-DISCONNECT、T-OBS-INJECT | CT-DP-001、CT-BOUNDARY-001、CT-ADM-001 |
| `DP-EMB-01..07` | LT-FUN-003、LT-OPEN-02 | R-INF-04/05/07 | VRC-INF-001/002 | —（同步 JSON，无流机制项） | CT-EMB-001 |
| `DP-USAGE-01..08` | LT-FUN-004、LT-INT-004/005/007 | R-MET-01..04 | VRC-MGMT-006 | T-MET-FINAL、T-MET-PAGE、T-MET-RESET、T-MET-UNKNOWN | CT-USAGE-001、CT-STORE-001 |
| `ADM-PROV-01..14` | LT-FUN-005、LT-SEC-001、LT-INT-008、LT-REL-004 | R-CFG-01、R-CFG-03 | VRC-MGMT-001/002 | T-CFG-CAS、T-CFG-SECRET、T-CFG-DELREF、T-CFG-BADREF | CT-ADMIN-001 |
| `ADM-PROV-MODELS-01..02` | LT-FUN-005 | R-CFG-01 | VRC-MGMT-001 | T-CFG-SECRET | CT-ADMIN-001 |
| `ADM-PROV-USAGE-01..04` | LT-FUN-005/006、LT-OPS-002 | R-CFG-01、R-OBS-01 | VRC-MGMT-006、VRC-DIAG-004 | T-CFG-SECRET | CT-ADMIN-001、CT-OPS-001 |
| `ADM-DEPL-01..09` | LT-FUN-005、LT-INT-008 | R-CFG-01 | VRC-MGMT-001/002 | T-CFG-CAS | CT-ADMIN-001 |
| `ADM-SL-01..08` | LT-FUN-005、LT-PERF-002 | R-CFG-01 | VRC-MGMT-002 | T-CFG-SPACE、T-CFG-CAS | CT-ADMIN-001 |
| `ADM-PROBE/RUNTIME/STATS/AUDIT/LOGS/USAGE` | LT-FUN-005/006、LT-OPS-002/006、LT-SEC-004 | R-OBS-01/02、R-MET-03、R-CFG-01、R-INF-03 | VRC-MGMT-003/006、VRC-LOG-001、VRC-DIAG-004、VRC-INF-004 | T-OBS、T-MET-RESET、T-MET-PAGE | CT-ADMIN-001、CT-LOG-001、CT-OPS-001、CT-USAGE-001 |
| `OBS-*` | LT-FUN-005、LT-OPS-006、LT-INT-007 | R-OBS-01..06 | VRC-DIAG-001/002/004 | T-OBS-SWITCH、T-OBS-SNAP、T-OBS-STATS、T-OBS-TRACE、T-OBS-INJECT | CT-ADMIN-001、CT-LOG-001 |
| `AUTH-01..10` | LT-INT-001、LT-SEC-001/003 | R-TRUST-01..04 | VRC-API-002、VRC-MGMT-003 | T-TRUST-BEARER、T-TRUST-LAN、T-TRUST-SHARED、T-TRUST-NOCFG、T-TRUST-LEAK、T-TRUST-ENDPOINTS | CT-WEBSEC-001、CT-ADMIN-001 |

> `CT-UI-001`/`CT-WEBSEC-001`（Web UI / TLS 反代 SSO/MFA）与 `CT-SCOPE-001`/`CT-BOUNDARY-001` 的 absence 断言**不在**本运行时 HTTP 规格内，见 §11.2 非目标。

## 4. Common Mechanisms（共同机制）

**本节目的**：集中定义**所有 Case 共用的机制**。case 详细设计文档（§3.3）**引用**本节，不重复其定义；当 case 需要"怎么做客户端/怎么鉴权/怎么解析 SSE/怎么判错误码/怎么复位/存哪/对应哪个自动化入口"时，指向本节。

### 4.1 测试 harness 与客户端

- **位置**：`tests/system/api_test_v03/`；`conftest.py::pytest_configure` 在收集前执行 §2.1 就绪检查；`LLMTierInstance` 提供 B 类临时实例 fixture（§2.4）。
- **客户端**：测试执行机（开发机）用 `httpx`/`urllib` 直连 HTTP。A 类 `http://192.168.1.9:8181`；B 类 `http://127.0.0.1:<port>`（loopback 仅指客户端→LLMTier，§2.7）。
- **骨架 smoke**：`tools/inference_smoke.py`（建连/骨架，不替代断言）、`tools/api_smoke_test.py`（21 端点 status-only，手动）。
- **要求**：自动化必须检查**动作命中**；环境缺失 → BLOCKED，禁止静默改用 mock/loopback 冒充真实路径（§9 INVALID）。

### 4.2 鉴权与凭据模型

- **角色**：`none`（公共端点 `/healthz`、`/readyz`）、`data`（Data Plane）、`admin`（Management/Observability）。Case 的 `角色` 列见 §3.2。
- **凭据**：`Authorization: Bearer <token>`；开发凭据 `dev-data` / `dev-admin`；上游 OMLX Bearer `9832`。
- **LAN trust（按实现描述，非按期望）**：`src/http_api/auth.py::unauthenticated_principal` 对**无 `Authorization` 头**且来源为 loopback 或 RFC1918（`10/8`、`172.16/12`、`192.168/16`、`fc00::/7`）的请求，**无条件**返回共享角色主体（`trusted-lan-operator`/`trusted-lan-consumer`）；`LLMTIER_DEV_MODE=1` 只把 loopback 主语改名为 `loopback-*`。**源码中不存在 `LLMTIER_TRUSTED_LAN_MODE` 分支**——本规格不声称该 env 门控存在。若希望引入显式 env 门控（默认关闭、仅可信 LAN 启用），这是一个**代码修复项**（`src/http_api/auth.py`，不在本规格范围内，需与代码 owner 协调并登记偏差）。
- **错误语义**：**缺凭据**（无 Bearer 且不命中免登录）或 **Bearer 形态非法**（非 `Bearer ` 前缀）→ 401 `authentication_required`；凭据无权 → 403 `permission_denied`；未配置鉴权 → 503 `auth_not_configured`。注意：受信 LAN/loopback 因无 `Authorization` 头即被授予共享角色，因此 401 需以**非法授权方案**（如 `Authorization: Basic ...`、`Token ...`）或非受信来源触发（AUTH-10）。
- **别名命名空间**：`/tier/admin/v1/*` 与 `/v1/*` 为同一 handler，鉴权与响应逐字节等价（OBS-ALIAS-01..04、AUTH-08）。

### 4.3 A/B 类执行模型

- **A 类**（m5air 已部署，`192.168.1.9:8181`）：只读/观察/一次性无状态写；**不得污染** m5air SQLite（写后立即 teardown）。
- **B 类**（临时实例，`127.0.0.1:<port>` + 临时 SQLite）：创建/修改/删除、空库、无鉴权、注入/并发；跑完销毁。
- **互斥**：A/B **不共享** SQLite/端口/进程；A 类 PASS 不关闭 B 类，反之亦然（§9）。

### 4.4 Fixtures（fake provider、seeded registry）

- **`LLMTierInstance` fixtures**：`llmtier_b`（`_BASELINE_SETTINGS`：provider `prov_b` + deployment `depl_b` + 7 tier）、`llmtier_b_empty`（`_EMPTY_SETTINGS`，HEALTH-04/05）、`llmtier_b_no_auth`（`_NO_AUTH_SETTINGS`，HEALTH-06/AUTH-07）。
- **A 类基线**：m5air 现有 **3 provider / 4 deployment / 7 fixed tier**；`/readyz` 显示 7 tier（§2.1/§2.3）。
- **本地假上游**：`tests/fixtures/v03_fake_provider.py`（TS-003：provider endpoint 用 LAN IP）。
- **种子注册表**：由 bootstrap（空库首启 `config/settings.json`）建立；初始化后 SQLite 为唯一 authority（§2.6）。

### 4.5 SSE 解析与 terminal 断言

- **解析**：逐帧读取 `text/event-stream`，解析 `event:`/`data:`，累积 `output_text`。
- **事件序列**（DP-RESP-01）：`response.created → response.output_item.added → response.output_text.delta×N → response.output_item.done → response.completed`（或 `response.incomplete`/`response.failed`）`→ data: [DONE]`；序列中**不存在**独立的 `output_text` 完成事件。
- **terminal**：恰好一个 `response.completed` / `response.incomplete` / `response.failed`，且以 `[DONE]` 收尾；`sequence_number` 自 0 **严格递增**。
- **异常路径**：`stream_terminate` / `malformed_event` / 客户端断开（DP-RESP-21）不得产生半个成功（§6）。

### 4.6 错误信封与错误码断言

- **wire 信封**：`{error:{message,type,code,param,retryable}}` —— 与 `src/http_api/errors.py::ApiError.envelope` 及 `openapi` `ErrorDetail` 一致，恰 5 个必填键。**没有 `category` 键**；**`type` 就是错误类别**（`request_error`|`server_error`），不要另加/另读 `category`。`additionalProperties: true`（`extra` 可并入 `error`，如 412 的 `current_version`）。
- **`type`**：由 HTTP 状态导出（`<500` = `request_error`，否则 `server_error`）。
- **`code`**：稳定码值（系统设计 §7.8 `ERR-*` 目录，machine `openapi` `ErrorDetail.code` enum）；负向 Case 断言 `status + code`（必要时 `param`）。
- **拒绝与副作用**：校验/鉴权类失败（400/403/404/409/412）在 dispatch 之前完成，无上游调用、无账本义务。**但 `authorize_dispatch` 先于 `admit`**（`src/inference/responses.py:94/98`；embeddings 同构），故 `admit` 阶段的拒绝（429 `rate_limit_exceeded`、503 `model_unavailable`）可能已在账本留下 pending/orphan obligation（`measurement_status="unknown"`）；必须以 usage/runtime/trace 交叉核对并在报告中解释该记录，**不得**宣称绝对零义务。
- **别名等价**：同一错误在 `/v1/*` 与 `/tier/admin/v1/*` 上逐字节等价。

### 4.7 DB 初始化 / 复位 / 清理

- **空库首启**：显式一次性 bootstrap（providers/deployments/service_levels 完整）；此后 SQLite 为唯一 authority（§2.6）。
- **B 类**：每班临时 SQLite（`LLMTIER_DATABASE`）+ 临时端口；`stop()` `terminate`→等待→`kill` + `rm -rf` 临时目录。
- **A 类写 case**：立即 teardown（PATCH 恢复原值/version、DELETE 本次创建物）；注入 `items:[]` 清空；DP-USAGE-04 执行后复位 `query_snapshots.expires_at`。
- **残留核验**：`/readyz` 7 tier、provider/deployment 列表 = §2.1 基线、`lsof` 无遗留 8181/临时端口监听（§2.8）。

### 4.8 Run ID、证据 Artifact、Manifest 与被测版本锁定

- **Run ID**：`<date>/<class>-<phase>`（如 `2026-09-28/A-api`、`2026-09-28/B-api`）。
- **被测版本锁定（artifact pin，强制）**：每个 Run 必须在 manifest 记录三项，禁止以 branch/tag/`HEAD` 名代替：
  1. `git_commit`：被测代码的完整 40 位 commit SHA（`git -C <repo> rev-parse HEAD`；m5air 部署目录非 git 工作树时，记录同步来源 commit SHA）。
  2. `db_schema_version`：运行库 `schema_meta.version`（SQLite 读取；B 类为临时库，A 类为 `state.sqlite3`）。
  3. `openapi_version`：`interfaces/openapi/llmtier.openapi.json` 的 `info.version`。
- **每 Case 证据 Artifact**：每个 Case 产出目录 `tests/system/reports/<date>/<A-api|B-api>/<case-id>/`（A/B 各占 `A-api`/`B-api` 子目录），内含 `manifest.json` 与原始证据文件（`response.http.txt`、`sse.events.jsonl`、`headers.txt`、`stdout/stderr` 等）。
- **Manifest 必填字段**（每个 Case 一份，缺项该 Case 不得判 PASS）：
  | 字段 | 内容 |
  |---|---|
  | `run_id` | `<date>/<class>-<phase>` |
  | `case_id` | §3.2 权威 Case ID |
  | `target_artifact` | `{git_commit, db_schema_version, openapi_version}`（上文三项） |
  | `environment` | `a` 或 `b`（§2.3） |
  | `inputs` | 固定输入、headers、ETag、cursor、时间窗、注入项、fixture settings（§4.4/§3.3） |
  | `oracle` | 独立 Oracle / 期望（status + body 关键字段 + error `code` + SSE 序列） |
  | `actual` | 实测 status/headers/body/SSE 逐帧（脱敏后） |
  | `verdict` | `PASS` / `FAIL` / `BLOCKED` / `SKIP` / `NOT_RUN` / `INVALID`（§9） |
  | `evidence_files` | 本目录原始证据文件清单 |
  | `redactions` | 已脱敏项清单（§10/§11） |
  | `reproduction_cmd` | 复现命令（FAIL/BLOCKED/INVALID 必填） |
- **证据**：命令、exit code、HTTP status/headers/body、SSE 逐帧、注入命中（trace `source=injected`）、环境快照（`/healthz`/`/readyz` + provider/deployment 列表）；与 manifest `actual` 同源。
- **报告落位**：`tests/system/reports/<date>/<A-api|B-api>/<case-id>/`（含 `manifest.json`）；失败现场不截断；重跑生成新 Run（§10）。

### 4.9 Case → 自动化入口映射

- **一 Case 一入口**：`at_<family>_<seq>.py`（单文件可含同主题多断言）；`HEALTH-*` 由 `at_obs_01..03.py` 承接（旧 ID OBS-01..03）。
- **运行器**：`bash tests/system/api_test_v03/runner_a.sh` / `runner_b.sh`；全量 `PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/ -q`。
- **系统/集成测试**：`tests/system/st_*.py`；Data Plane smoke `tools/inference_smoke.py`。
- **`MISSING`**：`自动化入口` 为 `MISSING` 表示尚无实现（§3.2）；不得以未实现冒充已通过（§9 NOT_RUN）。

### 4.10 关键契约常量（共同断言基线）

**目的**：集中固定跨 Case 共享的**契约常量**（管理/配置面），供 case 详细设计文档与脚本引用；下方如与实现冲突，以机器契约（`interfaces/openapi/llmtier.openapi.json`）与代码为准并登记偏差。

- **If-Match / ETag**：格式 `"<resource_id>.v<version>"`（**含双引号**，`src/management/registry.py`）；PATCH/DELETE 必须严格匹配；缺或过期 → 412 `version_conflict`，body 含 `current_version`；412 后重新 GET 取新 ETag 再 PATCH（不覆盖）。
- **`confirm_external_call`**：`POST /v1/providers/{id}/usage` 与 `POST /v1/probes` 需显式确认。`/v1/providers/{id}/usage` body 键集必须等于 `{confirm_external_call}`（否则 400 `invalid_request`）；`/v1/probes` body 键集必须等于 `{deployment_id, confirm_external_call}`（缺 → 400 `confirmation_required`）。`GET /v1/providers/{id}/models` 可能触上游（只读目录）。
- **`capabilities` 12 键全集**（registry `CAPABILITY_KEYS`）：`responses, embeddings, tools, structured_outputs, input_modalities, output_modalities, context_window, max_output_tokens, embedding_space_id, embedding_dimensions, embedding_max_batch_inputs, embedding_max_input_tokens`；缺/多即 400。
- **固定 tier**：service-level `id` 必须在 7 个 FIXED_TIERS（`Senior/Junior/Worker/Associate/Engineer/Executor/Embedding-v1`）内，否则 400 `invalid_request`；删除固定 tier → 409 `fixed_service_level`；PATCH 仅接受 `deployment_ids`/`enabled`。
- **`/readyz` 状态**：`ready`（全 available，200）| `degraded`（有候选但非全健康，503）| `not_ready`（无候选/启动失败，503）；body `{status, models[{id,availability}]}`。**503 wire shape 是 `ReadinessView`（`{"status":"degraded"|"not_ready","models":[…]}`）而非 `ErrorEnvelope`**——`/readyz` 不返回 `{error:...}`（`openapi` 正修正为一致，现网以实现为准）。
- **分页时间参数**：`/v1/usage`、`/v1/stats`、`/v1/logs` 用 **`from`/`to`**；`/v1/diagnostics/stats` 用 **`since`/`until`**（缺 → 400 `invalid_request`）。
- **别名命名空间**：`/tier/admin/v1/*` 的 6 条诊断/追踪路由与 `/v1/*` 为**同一 handler 的精确别名**（openapi `x-llmtier-contract-aliases`），body 应逐字节等价；仍要求 `admin` 角色。
- **错误信封/SSE/注入**：分别见 §4.6 / §4.5 / §6，本节不重复。

## 5. 正常、边界、负向与并发场景

**正常（happy path，独立 Oracle）**

- DP-RESP-01：SSE 事件**顺序与 identity**（INV-1）+ 恰好一个 terminal + `[DONE]`（INV-2）+ `sequence_number` 严格递增；不是"HTTP 200 即通过"。
- DP-EMB-01/02/03：维度 1024、base64 严格解码、同输入不变量（cosine > 0.99）。
- ADM CRUD 正常流（ADM-PROV-02/05/08、ADM-DEPL-02/04/05、ADM-SL-04）：201/200/204 + ETag `"<id>.v<N>"` 推进 + teardown。
- HEALTH-02：`ready` 判定。
- OBS-DEPL-02 → DP-RESP-11 → OBS-DEPL-02 清空：注入命中并回收。

**边界**

- 大小写与 URL 编码（DP-MODELS-03/04/05）；`limit` 取 1（DP-USAGE-03、ADM-AUDIT-02、ADM-USAGE-02）；`max_output_tokens=10`（DP-RESP-10）；batch 33（DP-EMB-05）；`context_window` 极大不可用普通 input 触发（DP-RESP-10 注）。
- 数值范围：注入 `delay_ms∈[0,60000]`、`retry_after_sec∈[0,300]`、`stream_terminate_after_events∈[1,10000]`（OBS-DEPL-04）。
- body 上限 2 MB（DP-RESP-18，系统设计 §11.1）。

**负向（拒绝位置 + 零副作用）**

- 校验失败集中在 dispatch 之前（INV-5）：400 `invalid_request`/`unsupported_request`/`unsupported_field`/`invalid_json`/`unsupported_model`/`unsupported_dimensions`；413 `request_too_large`。
- 认证失败 `authentication_required`/`permission_denied`/`auth_not_configured`（AUTH-*）。
- 资源与并发：404 `not_found`/`model_not_found`、409 `resource_conflict`/`capability_conflict`/`embedding_space_conflict`/`fixed_service_level`/`resource_in_use`、412 `version_conflict`、400 `cursor_expired`/`invalid_injection`/`confirmation_required`。
- 上游：502/503 `provider_unavailable`（DP-RESP-22）/`provider_error`（DP-RESP-23）/`provider_failure`（DP-RESP-11）/`provider_secret_unavailable`（DP-RESP-24）/`provider_contract_error`（DP-RESP-25）；504 超时；`model_unavailable`；429 `rate_limit_exceeded` + `Retry-After`。
- 存储与兜底：`usage_store_unavailable`（DP-USAGE-08，503 不用空页冒充）；`internal_error`（ADM-SL-08，500 信封不含栈/Secret）。
- **拒绝与副作用**：校验/鉴权拒绝（400/403/404/409/412）无上游 dispatch、无账本义务；但 `authorize_dispatch` 先于 `admit`，429/503 可能在账本留下 pending/orphan obligation，需以 usage/runtime/trace 交叉核对（DP-RESP-20 的 429 后应核对 `GET /v1/usage` 中该 request 的 pending/`unknown` 记录并解释，而非假定无新增）。

**并发**

- DP-RESP-20：并发请求共享同一 tier 的**准入许可与队列**（非独立资源），断言 429 只发生在饱和时、`Retry-After` 存在、前序成功请求账本各归各 principal。禁止用不同 Case ID 假定隔离。
- ADM-PROV-05/06/07：并发编辑以 `If-Match` / 412 串行化；两写者同 version 只能一个成功。
- OBS-DEPL-02 + 并发推理：注入配置变更与在途流的关系按 §6 定义，不假设原子。

**LLM 判据**：所有 Responses 断言基于**结构/事件序列/字段契约**，不写"答案正确"、不把上游模型的具体内容（如某个数字串）当 oracle；`temperature` 的采样语义不参与内容断言，`top_p` 仅以未知字段被拒（DP-RESP-15）作结构断言。

## 6. Recovery、重放、幂等与故障注入

**故障注入入口**：`PATCH /v1/deployments/{id}/diagnostics`（M006），`items[].type ∈ {fault_502, fault_503, delay, rate_limit, stream_terminate, malformed_event}`；前置阶段优先级 `fault_502→fault_503→rate_limit→delay`，流阶段 `stream_terminate→malformed_event`；撤销 = PATCH 同 `type` `enabled=false` 或 `items:[]`。每个注入 Case 必须**证明命中**（响应状态/错误码/trace `source=injected`），否则判 INVALID。

| 场景 | Case | 注入/触发 | 期望终态 | 撤销/证据 |
|---|---|---|---|---|
| 上游 502 | DP-RESP-11 | `fault_502` | `provider_failure`，`retryable=true`，trace `injected`；账本按 measured/unknown 收敛，不写成 0 | 清空 items；trace + usage 交叉核对 |
| 上游 503 | DP-RESP-22 | `fault_503` | `provider_unavailable`，`retryable=true` | 清空 items；trace + usage 交叉核对 |
| 上游延迟/首字节超时 | `delay` + 超时预算 | `delay` | 适配层超时 → `provider_unavailable`；不在本规格强制时点（§7） | 清除 delay |
| 流中途终止 | `stream_terminate` | 达到 `stream_terminate_after_events` | 无终端 `response.completed`，consumer 可判失败；不产生半个成功 | 清空；对照 INV-2 |
| 畸形事件 | `malformed_event` | `invalid_json`/`unknown_event_type` | 流被终止，记为失败而非成功 | 清空 |
| 客户端断开 | DP-RESP-21 | 客户端在 SSE 发送阶段断开 | 出口记 `aborted`；无 terminal；许可释放；账本已在 `create()` 返回前收敛 | 服务端 trace；后续请求可正常准入 |

**重放/幂等**

- 本版本**不定义**自定义 model-call recovery/exactly-once。测试标准 client 在 429/502/503 下的 retry（尊重 `Retry-After`），**不声称 exactly-once**；同一 `request_id` 的 usage **版本不累计**（追加式，head 单调）。
- 分页重放（DP-USAGE-07）：同一 cursor 重放返回同一冻结的 record version 成员（`query_snapshots`），cursor 绑定 principal + 授权 + 原 filter（`R-MET-02`）；重放不产生新版本、不改变 head。
- 配置重放：`If-Match` 412 后重新 GET 取新 ETag 再 PATCH（不覆盖）。
- 进程 crash/restart 后：已登记 unknown 义务仍可查，不回填为 0（`T-MET-CRASH`）——归运维/系统测试，引用 `llmtier-test-plan.md`。

## 7. 性能、容量、功耗或时序测试

**适用性**：功耗/FPGA 硬件时序**不适用**（纯软件）。本规格只定义**时序/预算类可观察断言**，不发布 SLO 结论：

- SSE 首字节与流完成：inference smoke 记录 `elapsed`；DP-RESP-01 不设固定 ms 门限。
- 准入：队列上限 32、排队上限 30 s、并发许可按部署配置；DP-RESP-20 观测 429 + `Retry-After`（`ERR-RATE-LIMIT` 预算）。
- 超时：上游建连/首字节/流空闲超时按系统设计 §5.3；`delay` 注入用于命中超时路径。
- 账本/分页：`limit` 与 cursor 稳定排序 `(recorded_at, request_id)`（`VRC-MGMT-006`）。
- 采样方法：同一 A 环境下固定 prompt/model/时间窗；记录并发度与输入规模；**Modeled/Simulated ≠ Measured**，本规格不将 smoke 计时当容量结论。
- 容量压测（FD 泄漏、30min 耐久、50 并发）在 `llmtier-test-plan.md` ST-18/ST-19/ST-21，本规格只引用不重复。

## 8. 执行步骤与自动化入口

**运行位置**：执行机 = 开发机（如 m5mac `192.168.1.8`）；A 类经 LAN 直连 m5air `http://192.168.1.9:8181`，B 类在本机起临时实例 `http://127.0.0.1:<port>`（见 §2.7）。**TS-003：禁止 `127.0.0.1` 作为被测服务的上游 provider endpoint。**

### 8.1 端到端执行流程（环境就绪 → 部署/启动 → 跑 case → 收证据 → 复位）

1. **环境就绪（§2.1）**：在开发机对 m5air 执行 6 项检查（`/healthz`、`/readyz` 7 tier、m5air OMLX、m5mac OMLX、`provider_omlx_m5mac` secret、A 类既有 provider/deployment 资源注册）。`pytest_configure` 自动执行；任一失败 → 整班 SKIP/BLOCKED，**不得**静默改用模拟路径声称真实通过。
2. **部署 / 启动待测版本**：
   - **A 类**：m5air 已部署。如需更新，按 §2.5 顺序执行：`rsync` 源码（排除运行数据）→ 查旧进程/端口 → `kill -TERM` 并等待 → 用 Python 3.14 重启 → `curl http://192.168.1.9:8181/healthz` 验证 → 确认无旧进程残留。
   - **B 类**：`conftest.py` 的 `LLMTierInstance` 按 fixture 启动本机临时实例（临时端口 + 临时 SQLite + 每 run settings），`start()` 轮询 `/healthz`。
3. **跑 case**：
   - 全量：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/ -q`；
   - 单 case：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_resp_01.py -v`；
   - A/B 分跑：`bash tests/system/api_test_v03/runner_a.sh` / `runner_b.sh`；
   - Data Plane smoke：`python3 tools/inference_smoke.py --base http://192.168.1.9:8181`。
   - **建议顺序**：A 类只读/无状态写 → 每写完立即 teardown → B 类串行（含注入/并发）→ 注入 case 必须与 `OBS-DEPL-02` 配套（写入 → 命中 → 清空）。A/B 互斥同一实例，不与 A 类并行跑并发写。
4. **收证据（§10）**：记录命令、exit code、HTTP status/headers/body、SSE 逐帧、注入命中证据（trace `source=injected`）、环境快照（`/healthz`/`/readyz` + provider/deployment 列表）。Run ID `<date>/<class>-<phase>`；存 `tests/system/reports/<date>/<A-api|B-api>/<case-id>/`；失败现场不截断。
5. **复位**：A 类每个写 case teardown（PATCH 复原/ DELETE 本次创建物）、注入 `items:[]`、DP-USAGE-04 复位 `query_snapshots.expires_at`；B 类整班 `stop()` 终止进程并 `rm -rf` 临时目录。核验 `/readyz` + provider/deployment 列表回到 §2.1 基线、无遗留端口监听、无未清空注入。
6. **判定与登记**：按 §9 为每个执行项给出 PASS/FAIL/BLOCKED/SKIP/INVALID/NOT_RUN；FAIL/BLOCKED/INVALID 登记缺陷并保留现场，不得把未运行项补造为成功。**单 Case 受阻不中断整轮**（就地恢复后继续下一个 Case）；某批小范围系统性受阻时先诊断根因再**断点续跑**（不回跑已 PASS），见执行层计划 §7.1。

### 8.2 重点关注的过程步骤

- **SSE terminal 唯一性**（DP-RESP-01/10、DP-RESP-21、`stream_terminate`/`malformed_event`）：必须恰好一个 terminal（`response.completed`/`response.incomplete`/`response.failed`）且带 `[DONE]`；`sequence_number` 自 0 严格递增；错误/中断路径不得产生半个成功。
- **错误信封等价**（全部负向 case）：wire 信封 `{error:{message,type,code,param,retryable}}`（5 键，`type` 即类别，无 `category`）；`type` 由 HTTP 状态导出（`<500`=`request_error`，否则 `server_error`）；`code` 用 §7.8 稳定码值与 `openapi` enum；同一错误在扁平路径与 `/tier/admin/v1/*` 别名上应逐字节等价。
- **幂等 / If-Match**（ADM-PROV/DEPL/SL 的 PATCH/DELETE）：ETag 格式 `"<id>.v<N>"`（含双引号）严格匹配；缺/过期 → 412 `version_conflict`，body 含 `current_version`；412 后重新 GET 取新 ETag 再 PATCH（不覆盖）；并发两写者同 version 只能一个成功。
- **容器 / 上游超时**：V0.3 首版不做容器化（container image 非必要，见 release-and-operations §2/§3），因此超时关注点集中在上游 provider 建连 30 s、首字节 30 s、SSE 空闲 60 s 与准入队列上限 30 s（系统设计 §5.3）；用 `delay` 注入命中超时路径并记录观测时点；本规格不设 ms 级 SLO 门限。
- **注入命中证明**（`OBS-DEPL-02/04` + DP-RESP-11）：注入必须留下 trace `source=injected` 或响应状态/错误码证据，否则判 INVALID；撤销 `items:[]` 后必须回到合法终态。
- **分页 cursor**（DP-USAGE-03/04、ADM-AUDIT-02、ADM-USAGE-02、OBS-*）：稳定排序 `(recorded_at, request_id)`；同 cursor 重放返回同一冻结的 record version 成员；非法/过期 → 400 `cursor_expired`。
- **拒绝与副作用**：校验/鉴权类（400/403/404/409/412）在 dispatch 之前完成，无上游调用、无账本义务；但 `authorize_dispatch` 先于 `admit`（`responses.py:94/98`），429/503 可能有 pending/orphan obligation，须以 usage/runtime/trace 交叉核对并解释，**不假定**绝对为零。

### 8.3 入口（命令）

```bash
# 全量（A 类 + B 类同目录）
PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/ -q

# 单个 Case（文件名对应 Case ID）
PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_resp_01.py -v

# A 类 runner / B 类 runner
bash tests/system/api_test_v03/runner_a.sh
bash tests/system/api_test_v03/runner_b.sh

# Data Plane 端到端 smoke（非替代断言，只验建连与骨架）
python3 tools/inference_smoke.py --base http://192.168.1.9:8181

# 全 21 端点 status-only smoke（手动）
python3 tools/api_smoke_test.py

# 本地假上游（TS-003：provider endpoint 用 LAN IP，见下）
PYTHONPATH=src python3 tests/fixtures/v03_fake_provider.py --port 9191
PYTHONPATH=src python3 tests/integration/v03_smoke.py
```

### 8.4 步骤模板

① 就绪检查 → ② 发送请求（curl/httpx）→ ③ 校验 HTTP status → ④ 校验 body 关键字段与 error `code` → ⑤ SSE 需校验事件序列与 terminal → ⑥ teardown → ⑦ 记录 Run（命令、exit code、stdout/stderr、产物路径）。**自动化必须检查动作命中**；环境缺失应 BLOCKED，不得静默改用模拟路径声称真实通过。

### 8.5 Case ↔ 文件映射

`at_<family>_<seq>.py`；`HEALTH-*` 由 `at_obs_01..03.py` 承接（旧 ID OBS-01..03）。MISSING（52）：`HEALTH-03/05/06`、`DP-RESP-16..25`、`DP-EMB-06..07`、`DP-USAGE-05..08`、`ADM-PROV-14`、`ADM-PROV-MODELS-01..02`、`ADM-PROV-USAGE-04`、`ADM-SL-08`、`ADM-PROBE-03`、`ADM-RUNTIME-02`、`ADM-AUDIT-03`、全部 `OBS-*`（22）、`AUTH-08..10`，见 §3 与 §9。逐 Case 的输入/Oracle/执行/判定见各自 case 详细设计文档（§3.3、§3.4）。

## 9. Pass/Fail/Blocked/Skip/Not_Run/Invalid 判定

| 状态 | 判定 | 阻塞 release | 报告必含 |
|---|---|---|---|
| **PASS** | HTTP status + body 关键字段 + error `code`（+ SSE 事件序列无误、terminal 唯一、`[DONE]`）全部 match | 否 | — |
| **FAIL** | 断言不符：status/字段错、error code 不符、SSE 序列断裂、terminal 缺失或重复、注入已命中但行为不符 | 是 | 预期 vs 实际、`reproduction_cmd`、`failure_step` |
| **BLOCKED** | 无法执行/无法判定且**可重试**（测试代码/契约问题且恢复动作未解除：fixture 写不出、断言逻辑错、ISD/OpenAPI 语义不清、注入无法命中） | 是 | `block_reason`、`required_resolution`、**已执行/待执行的恢复动作**、`reproduction_cmd` |
| **SKIP** | 明确不适用或依赖失败（§2 前置不满足、上游 provider 离线、B 类临时实例不可用、依赖链前置未满足） | 否（有上限） | `skip_reason`（引用 §2 检查项/依赖）、`fix_owner`、`eta` |
| **INVALID** | 注入未命中却按行为判定、或替代路径冒充真实路径（如错误地用 `127.0.0.1` 或 mock 结果当实测） | 是 | `invalid_reason`、证据缺口 |
| **NOT_RUN** | Case 已定义但本轮未执行（含 MISSING 实现） | 不适用 | 缺口引用（§3） |

**规则**：MISSING ≠ NOT_RUN；无实现是缺口，不是跳过。N/A 需裁剪依据（如功耗）。**SKIP 上限**：A 类 ≤ 5、B 类 ≤ 3；超出视为覆盖不足，须补 fixture/注入后重跑。**禁止**"未跑"无状态：runner 必须为每个执行项给出明确状态。**跨 backend 隔离**：A 类 PASS 不关闭 B 类；静态 contract PASS 不关闭运行保证。**HARD-BLOCKED** 是 BLOCKED 的子类：仅当 A 类 schema/引导不可用（§2.9）等**须先执行恢复动作才可能解除**时使用，报告额外记录所选恢复路径 (a)/(b)。

**"适用（applicable）"定义与 Gate 判定**：

- **适用**：§3.2 全部 140 个 Case **默认为适用**；仅当某 Case 被本规格正文或经批准的裁剪（如 §7 功耗/硬件时序、§11.2 非目标）**具名**声明为不适用时，才可标 `N/A`/`SKIP`。未具名声明不适用即视为适用——**不得**用"没跑"或"未实现"把适用 Case 降级为不适用。
- **Gate（release 放行门槛）**：**所有适用 Case 均为 PASS**，且 FAIL/BLOCKED/INVALID = 0，且 SKIP 在上限内，方可放行。因此 **P0 MISSING（如 OBS-DEPL-01/02、DP-RESP-22..25 等新增 P0/P1 未实现项）一律阻断 Gate**（MISSING = NOT_RUN 缺口，不自动放行）；非 P0 缺口若经具名批准可暂记。具名缺口（§11.1 的 4 项 `ERR-*`）经运行报告具名批准后不单独阻断。
- **Gate ≠ "本轮跑完"**：Gate 是 release 决策；"本轮跑完"（Exit）是执行里程碑，定义见执行层计划 §7.2——**所有 Case 有终态（PASS/FAIL/BLOCKED/SKIP）且无未诊断的系统性阻塞**即可收轮，即使仍有 FAIL/BLOCKED。两者不得互相替代。

**执行韧性（引用执行层计划 §7.1）**：单 Case 受阻不中断整轮（就地恢复后继续）；系统性受阻先诊断根因再**断点续跑**（不回跑已 PASS）；恢复目录与续跑语义见执行层计划 `llmtier-api-test-plan.md` §7.1。本规格只定义判定状态，不重复执行编排。**本轮 Exit ≠ 全 PASS**，以"所有 Case 有终态（PASS/FAIL/BLOCKED/SKIP）且无未诊断的系统性阻塞"为准（执行层计划 §7.2）。

## 10. Artifact、日志、测量与证据保存

- **Run ID 与被测版本锁定**：同 §4.8。每个 Run 必录 `{git_commit, db_schema_version, openapi_version}`；`db_schema_version` 在运行开始时与恢复到的新库上分别记录，作为 schema 恢复（§2.9）的前后对照。
- **每 Case artifact + manifest**：`tests/system/reports/<date>/<A-api|B-api>/<case-id>/manifest.json`（字段见 §4.8 表）+ 原始证据文件；Case ↔ Run 对应表在 Run 报告中维护。
- **固定输入**：prompt、model、时间窗、注入项、If-Match ETag 字面值、fixture settings；随 Run manifest 存档。
- **原始输出**：命令、HTTP status/headers、body、SSE 逐帧、exit code、耗时；失败现场保留不截断（脱敏后）。
- **环境快照**：m5air 部署版本（commit SHA）、DB `schema_version`、`/healthz`/`/readyz` 响应、provider/deployment 列表、`tools/api_smoke_test.py` 输出。
- **保存位置**：`tests/system/reports/<date>/<A-api|B-api>/<case-id>/`（沿用现有约定；每 Case 一份 `manifest.json`）。
- **重跑**：生成新 Run，不覆盖旧失败，不把未运行项目补造为成功。
- **保密/脱敏（强制）**：Artifact 入库前必须 scrub：`Authorization` 头（`Bearer dev-data`/`Bearer dev-admin` 可保留为测试凭据，但真实凭据一律替换为 `<redacted>`）、上游 OMLX Bearer 字面 `9832`、任何 key 文件内容（如 `omlx-secret-key.txt`）与解析后的 secret 值、完整 provider payload。manifest `redactions` 必须列出已脱敏项。

## 11. 安全、清理与可重复性

- **凭据**：测试用 `dev-data`/`dev-admin`/`9832` 为本地开发凭据，不出现在证据中作为"秘密"；真实 Secret 绝不出现在日志/审计/证据（ADM-AUDIT-01、ADM-LOGS-01 显式断言不含 `9832` 与 key 文件内容；ADM-PROV-14 显式断言 provider 读取响应不回显 secret 值）。**证据脱敏**：Authorization、上游 `9832`、key 文件内容在归档前一律替换，见 §10。
- **范围与非目标（当前静默省略项）**：见 §11.2。
- **探针/费用**：`POST /v1/probes`、`POST /v1/providers/{id}/usage`、`GET /v1/providers/{id}/models` 可能触上游或产生费用——必须显式 `confirm_external_call`（provider-models 按只读目录处理并记录）；执行者需授权。
- **清理**：A 类每个写 Case teardown（恢复字段/删除本次创建物）；B 类整班销毁临时实例与临时 SQLite；注入配置 `items:[]` 清空后才离开。
- **复用性**：清理后下一轮可核验初态（§2 前置 + `/readyz`）；不得删除 m5air 既有 provider/deployment/service-level 或用户 usage。
- **隔离**：B 类不与 A 类共享 SQLite/端口；测试进程退出 ≠ 设备停止（B 类须显式 `terminate` 并等待）。
- **不可安全释放时**：保留证据并报告 BLOCKED（例如 B 类进程无法终止），不做无边界清理。

### 11.1 `ERR-*` → Case / 具名缺口 映射（覆盖门配套）

系统设计 §7.8 公共错误目录共 34 项；本表逐项给出**承接 Case**或**具名缺口**。有 Case 的项不再需要缺口批准；具名缺口须在运行报告中单列。

| `ERR-*`（源 ID） | wire `code` | 端点 / 模块 | 承接 Case 或具名缺口 |
|---|---|---|---|
| ERR-REQ-VALIDATION | `invalid_request` | 全端点 | DP-RESP-08、DP-RESP-12..15、DP-EMB-07、DP-USAGE-05、ADM-PROV-11、ADM-DEPL-08、ADM-STATS-03、ADM-AUDIT-03、ADM-LOGS-02、OBS-DIAG-03、OBS-STATS-02 |
| ERR-REQ-UNSUPPORTED | `unsupported_request` | `/v1/responses` | DP-RESP-02、DP-RESP-07 |
| ERR-REQ-FIELD | `unsupported_field` | `/v1/responses` | DP-RESP-09 |
| ERR-REQ-MODEL | `unsupported_model` | `/v1/responses` | DP-RESP-17 |
| ERR-REQ-JSON | `invalid_json` | `/v1/responses`、`/v1/embeddings` | DP-RESP-16 |
| ERR-REQ-TOO-LARGE | `request_too_large` | `/v1/responses` | DP-RESP-18 |
| ERR-REQ-DIM | `unsupported_dimensions` | `/v1/embeddings` | DP-EMB-06 |
| ERR-AUTH-REQUIRED | `authentication_required` | 受保护端点 | AUTH-10 |
| ERR-AUTH-DENIED | `permission_denied` | 受保护端点 | AUTH-02/03/06/08/09、ADM-RUNTIME-02、OBS-REQTRACE-03 |
| ERR-AUTH-NOCFG | `auth_not_configured` | 受保护端点 | AUTH-07 |
| ERR-MODEL-NOTFOUND | `model_not_found` | models/responses/embeddings | DP-MODELS-03/04/05/06、DP-RESP-05、DP-EMB-04 |
| ERR-NOTFOUND | `not_found` | 资源子路径、trace | ADM-PROV-04、ADM-PROV-MODELS-02、ADM-PROV-USAGE-04、ADM-PROBE-03、OBS-DEPL-03、OBS-REQTRACE-02 |
| ERR-CONFLICT | `resource_conflict` | service-levels | ADM-SL-02b |
| ERR-CAPABILITY | `capability_conflict` | service-levels | ADM-SL-06 |
| ERR-EMBEDDING-SPACE | `embedding_space_conflict` | service-levels | ADM-SL-07 |
| ERR-FIXED-LEVEL | `fixed_service_level` | service-levels/{id} DELETE | ADM-SL-05 |
| ERR-INUSE | `resource_in_use` | providers/deployments | ADM-PROV-10 |
| ERR-STALE | `version_conflict` | providers/deployments/service-levels PATCH/DELETE | ADM-PROV-06/07/09 |
| ERR-CURSOR | `cursor_expired` | 分页端点 | DP-USAGE-04、OBS-SNAP-02、OBS-TRACE-02 |
| ERR-RATE-LIMIT | `rate_limit_exceeded` | responses/embeddings | DP-RESP-20 |
| ERR-PROVIDER-UNAVAIL | `provider_unavailable` | responses/embeddings | DP-RESP-22 |
| ERR-PROVIDER-FAIL | `provider_error` | responses/embeddings | DP-RESP-23 |
| ERR-PROVIDER-INJECTED | `provider_failure` | responses | DP-RESP-11 |
| ERR-PROVIDER-SECRET | `provider_secret_unavailable` | responses/embeddings | DP-RESP-24 |
| ERR-PROVIDER-CONTRACT | `provider_contract_error` | responses/embeddings | DP-RESP-25 |
| ERR-MODEL-UNAVAIL | `model_unavailable` | responses/embeddings | DP-RESP-19 |
| ERR-STORE | `usage_store_unavailable` | usage/audit/logs/观测查询 | DP-USAGE-08 |
| ERR-INTERNAL | `internal_error` | 全端点 | ADM-SL-08（信封契约；同时登记输入校验缺陷） |
| ERR-BOOT | `bootstrap_required` / `bootstrap_invalid` | 启动、`/readyz` | **具名缺口**：`/readyz` 503 body 为 `ReadinessView`（非 `ErrorEnvelope`，无 `code`）；HEALTH-04/05 仅以 `/readyz status="not_ready"` 覆盖表现，不覆盖 envelope code |
| ERR-SCHEMA | `schema_version_mismatch` / `schema_unknown` / `schema_integrity_failed` | 启动、`/readyz` | **具名缺口**：需 M007 特有构造；恢复路径见 §2.9 |
| ERR-PATH-UNSAFE | `store_path_unsafe` | 启动、`/readyz` | **具名缺口**：需 symlink DB 路径的破坏性构造 |
| ERR-UTIL-TXN | `E-UTIL-NESTED-TXN` | 全部写入/事务路径 | **具名缺口**：嵌套事务为内部不变量，无法从 HTTP 无破坏触发 |
| ERR-INJECTION | `invalid_injection` | `/v1/deployments/{id}/diagnostics` | OBS-DEPL-04 |
| ERR-CONFIRM | `confirmation_required` | `/v1/probes`、`/v1/providers/{id}/usage` POST | ADM-PROBE-01、ADM-PROV-USAGE-02 |

**覆盖结论**：34 项中 **30 项有承接 Case（88.2%）**，**4 项具名缺口（11.8%：`ERR-BOOT`、`ERR-SCHEMA`、`ERR-PATH-UNSAFE`、`ERR-UTIL-TXN`）**；具名缺口不自动阻断 Gate，但需在运行报告具名批准（§9）。

### 11.2 范围与非目标（当前静默省略项，显式化）

以下项**不在**本运行时 HTTP 规格范围，列出以免被误认为"已覆盖"：

1. **legacy `/call`、Role selector、custom header/schema absence**（`LT-INT-003`、`LT-REL-002`、`CT-SCOPE-001`/`CT-BOUNDARY-001`）：absence 属静态契约回归，由 [`llmtier-contract-test-specification.md`](llmtier-contract-test-specification.md) 与 `tests/system/st_04_forbidden_scan.py` 承接；本规格只测 current `/v1/*` 运行行为。
2. **保留/备份/恢复与 QuerySnapshot TTL**（`LT-OPS-005`）：属运维计划（`llmtier-test-plan.md` ST-*）与既有系统测试；本规格只以 DP-USAGE-04（过期 cursor）间接触及 snapshot TTL，不测备份/恢复演练。
3. **生产 SSO/MFA、TLS 反向代理、HttpOnly/CSRF、浏览器无 bearer**（`LT-SEC-003`、`CT-WEBSEC-001`）：Web UI 生产部署面，非 HTTP API 运行时；本规格不测。
4. **Web UI E2E**（`CT-UI-001`）、**FD 泄漏 / 30min 耐久 / 50 并发压测**（`llmtier-test-plan.md` ST-18/19/21）、**Cost/quota 组合**：分别由 UI 测试、容量测试与合同/运维承接。
5. **非受信来源的真实"缺凭据"**：受信 LAN/loopback 因实现无条件授予共享角色（§4.2），无法从 A/B 受信网段制造 401 `authentication_required`；AUTH-10 改以**非法授权方案**触发 401。生产非 LAN 缺凭据与 SSO 属第 3 项。
6. **`ERR-BOOT`/`ERR-SCHEMA`/`ERR-PATH-UNSAFE`/`ERR-UTIL-TXN` 的 envelope code**：见 §11.1 具名缺口；A 类 schema 不兼容的恢复路径见 §2.9。
