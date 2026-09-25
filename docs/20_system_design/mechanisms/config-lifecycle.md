<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier 配置生命周期机制

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-config-lifecycle-mechanism` |
| Document Version | `0.1.0-draft.5` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-22` |
| Last Modified Date | `2026-09-25` |
| Template ID | `design.system-mechanism` |
| Template Version | `3.0.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/20_system_design/mechanisms/config-lifecycle.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 机制摘要：解决什么问题

配置**从哪里来、如何校验、何时生效、如何变更与审计**，以及初始化失败时系统如何**保持不可接流量**。

**为什么不能由一个单元独立完成**：启动引导、运行期变更、查询一致性、Secret 解析与审计横跨启动路径、管理面、存储；且必须保证"**初始化后单一权威**"，否则文件与库双写会产生不可判定状态。

**输入 → 处理 → 输出**：
- 输入：空库首次启动（可选 `config/settings.json`）、管理面 CRUD、离线迁移
- 处理：一次性 bootstrap 校验+事务写入 → **SQLite 成为唯一运行权威** → 此后仅经管理面变更（事务 + 审计）
- 输出：可查询的 Registry（providers/deployments/service-levels）+ 审计事件

**核心取舍**：**单次 bootstrap、不热载文件**。初始化后即使文件变化也不自动重导入（避免双写歧义）。

## 2. 使用场景与功能

| Capability ID | 业务任务与触发 | 输入与可观察结果 | 提供方 / 消费者 | 实现状态 | 验证判据 |
|---|---|---|---|---|---|
| CAP-CFG-BOOTSTRAP | 空库首次启动 | settings → 库中 Registry + `bootstrap_sha256` | Management / 启动 | Implemented | 首次/重复启动用例 |
| CAP-CFG-CRUD | Operator 管理 provider/deployment/level | ETag 强校验的增删改 | Management / Operator | Implemented | Admin 契约用例 |
| CAP-CFG-VALIDATE | 发布前校验引用与不变量 | 拒绝并回滚 | Management | Implemented | 非法引用/space 用例 |
| CAP-CFG-CANDIDATE | 推理查询等级候选 | 同等级有序候选 | Management / Inference | Implemented | 路由用例 |
| CAP-CFG-MIGRATE | 显式离线迁移 | 备份 + 单一版本命令 | Operator（离线）| Manual | 运维演练 |
| CAP-CFG-NOTREADY | 初始化失败保持不可用 | `/readyz` 未就绪 | 启动 | Implemented | 引导失败用例 |

**不提供**：settings 热加载、双写、Seat/capacity 产品、调用方管理。

## 3. 参与方、责任和 authority

### 3.1 系统约束与参与方承接

本机制为顶层机制（上级 Mechanism ID = none），约束继承自系统设计 §3 与 §10。

| Constraint ID | 约束 | 参与方保证 | 自由度 | 本文落实位置 |
|---|---|---|---|---|
| C-CFG-1 | 初始化后 SQLite 是唯一运行权威 | Management | 存储布局 | §4.6、§4.10、§8 |
| C-CFG-2 | Secret 明文不入库，只存引用 | Management | 引用形式 | §4.3、§11 |
| C-CFG-3 | 发布先验证引用/不变量，再原子推进 | Management | 事务实现 | §6、§8 |
| C-CFG-4 | 变更失败回滚且不改 active snapshot | Management | — | §7、§9 |
| C-CFG-5 | 初始化失败服务 not_ready | 启动 | — | §9 |

### 3.2 运行时统筹与确认责任

**bootstrap** 统筹于启动事务；**变更**统筹于管理动作，成功即写审计。发布事务是唯一的"确认"点。

### 3.3 拓扑、目标身份与共享故障域

单节点单文件；无跨节点协调。SQLite 为唯一权威；`config/settings.json` 仅为一次性输入，**故障域之外**（不参与运行期）。

## 4. 数据结构设计

> 按 STD `design-data-interface-format` 1.2.0 §2：主章“数据结构设计”，章内按**数据性质**分类（§4.1–§4.8），本层特有分析见 §4.9–§4.10。仅保留适用类别。继承/机器源结构只定位原定义与本层投影，不复制字段权威。本机制拥有的类型 ID 前缀 `D-CFG-*`；配置持久 authority = `util/migrations/*.sql`，机器源 = `interfaces/schemas/llmtier-settings-v0.3.schema.json` + `openapi`。

**类别适用性**：§4.1 公共基础类型与枚举 ✓｜§4.2 业务与操作数据结构 ✓｜§4.3 配置与规则数据结构 ✓｜§4.4 通信报文结构 ✓（管理面 wire 继承 `openapi`）｜§4.5 设备与 FPGA 表项结构 ✗（纯软件，无设备/RTL）｜§4.6 运行状态数据结构 ✓｜§4.7 数据库表结构 ✓｜§4.8 错误码与错误结构 ✓（引用系统 §8.8）。

### 4.1 公共基础类型与枚举

#### `D-CFG-KIND` · ProviderKind（`registry.py`）
- **定义、Data/Type ID 与唯一来源**：provider 连接类型；`D-CFG-KIND`；唯一来源 `src/management/registry.py`（bootstrap `kind` 校验）与系统 §8.1 共享枚举 `kind ∈ {cloud,local}`。
- **字段 / 取值**：`kind: str` ∈ {`cloud`, `local`}。
- **约束 / 不变量**：`local` 使用本地部署/自带凭据；`cloud` 使用云端账号；决定默认 usage profile（`_usage_values`）。
- **状态 · 所有权 · 寿命**：随 `providers.kind` 持久；operator 经 M004 拥有。
- **合法与拒绝实例**：合法 `local`；拒绝其他值 → 引导 503 `bootstrap_invalid` / CRUD 400。
- **验证**：`T-CFG-BOOT`、`T-CFG-CAS`。

#### `D-CFG-HEALTH` · DeploymentHealth（`registry.py`）
- **定义、Data/Type ID 与唯一来源**：deployment 健康事实；`D-CFG-HEALTH`；系统 §8.1 共享枚举 `health ∈ {unknown,healthy,unhealthy}`。
- **字段 / 取值**：`health: str` ∈ {`unknown`, `healthy`, `unhealthy`}；新建默认 `unknown`。
- **约束 / 不变量**：由探测/运行事实更新，不由 bootstrap 输入直接设定；Router 仅选 `healthy`。
- **状态 · 所有权 · 寿命**：随 `deployments.health` 持久；运行期由健康检查写。
- **合法与拒绝实例**：合法 `healthy`；边界：未探测为 `unknown`（Router 视为不可选）。
- **验证**：`T-CFG-BOOT`、路由用例。

#### `D-CFG-TIER` · ServiceLevelName（`registry.py`）
- **定义、Data/Type ID 与唯一来源**：固定逻辑等级名；`D-CFG-TIER`；唯一来源 `src/management/registry.py` `FIXED_TIERS`。
- **字段 / 取值**：`id` ∈ {`Senior`,`Junior`,`Worker`,`Associate`,`Engineer`,`Executor`,`Embedding-v1`}（7 个，exact-case）。
- **约束 / 不变量**：启动 `ensure_fixed_tiers` 保证 7 行恒存在；非固定 Tier 名拒绝；`Embedding-v1` 只能 embedding-only。
- **状态 · 所有权 · 寿命**：随 `service_levels.id` 持久；operator 经 M004 管理。
- **合法与拒绝实例**：合法 `Worker`；拒绝 `worker`/`Custom` → 400 `invalid_request`。
- **验证**：`T-CFG-SPACE`、`T-CFG-BOOT`。

### 4.2 业务与操作数据结构

#### `D-CFG-CANDIDATE` · Candidate（`registry.py`）
- **定义、Data/Type ID 与唯一来源**：Router 准入的候选后端投影；`D-CFG-CANDIDATE`；唯一来源 `src/management/registry.py` `Candidate`（`dataclass`），本机制 §5 `candidates()` 产出。
- **字段 / 取值**：`level_id: str`、`deployment_id: str`、`provider_id: str`、`endpoint: str`、`backend_model: str`、`kind: D-CFG-KIND`、`health: D-CFG-HEALTH`、`ordinal: int`。
- **约束 / 不变量**：同一 `level_id` 内 `ordinal` 有序且唯一；只含 enabled 成员；`health` 为当时快照。
- **状态 · 所有权 · 寿命**：请求级只读投影；M004 Registry 产出、M003 Router 消费；不持久。
- **合法与拒绝实例**：合法 `Candidate("Worker","dep_local_gemma",...)`；边界：无成员 → 空列表（Router 转 404/503）。
- **验证**：路由用例、`T-CFG-CAS`。

#### `D-CFG-VERSION-TAG` · Version/ETag
- **定义、Data/Type ID 与唯一来源**：资源乐观并发标记；`D-CFG-VERSION-TAG`；唯一来源 `registry.py` `_etag`（`"<id>.v<version>"`）。
- **字段 / 取值**：`version: int`（≥1，单调 +1）；`etag: str` = `"<id>.v<version>"`。
- **约束 / 不变量**：`version` 与 ETag 对应；PATCH/DELETE 必须匹配 `If-Match`，否则 412。
- **状态 · 所有权 · 寿命**：随各资源行的 `version` 列持久；写事务拥有。
- **合法与拒绝实例**：合法 `provider_id.v3` 匹配；拒绝 stale ETag → 412 `version_conflict`。
- **验证**：`T-CFG-CAS`。

### 4.3 配置与规则数据结构

#### `D-CFG-SETTINGS` · SettingsDocument（`config/settings.json`）
- **定义、Data/Type ID 与唯一来源**：一次性 bootstrap 输入文档；`D-CFG-SETTINGS`；机器源 `interfaces/schemas/llmtier-settings-v0.3.schema.json`。
- **字段 / 取值**：顶层节集**恰为** {`providers`, `deployments`, `service_levels`}；`providers[]` 项字段集恰为 {`id`,`name`,`kind`,`endpoint`,`secret_ref`,`enabled`}；`deployments[]` 项字段集恰为 {`id`,`name`,`provider_id`,`backend_model`,`capabilities`,`enabled`}；`service_levels[]` 项含 `id`∈`D-CFG-TIER`、`deployment_ids[]`、`enabled`。
- **约束 / 不变量**：ID 唯一；引用完整；`secret_ref` 仅 `env:`/`file:` 且可达；`capabilities` 键 ⊆ `CAPABILITY_KEYS` 且四个布尔键为 bool。
- **状态 · 所有权 · 寿命**：仅引导时读取；不参与运行期（C-CFG-1）；文件不热载。
- **合法与拒绝实例**：合法三节齐备且引用可达；拒绝：缺节/未知节/引用错误 → 503 `bootstrap_invalid` + 回滚。
- **验证**：`T-CFG-BOOT`、`T-CFG-BADREF`、`T-CFG-SECRET`。

#### `D-CAPABILITY` · Capability（继承系统 §8.1）
- **定义、Data/Type ID 与唯一来源**：`D-CAPABILITY`；系统设计 §8.1 唯一来源，本机制只定位投影与校验点。
- **本层投影**：12 键固定集（`responses`/`embeddings`/`tools`/`structured_outputs`/`input_modalities`/`output_modalities`/`context_window`/`max_output_tokens`/`embedding_space_id`/`embedding_dimensions`/`embedding_max_batch_inputs`/`embedding_max_input_tokens`）；deployment 存 JSON，level 存成员交集。
- **本层约束**：level `capabilities` = 绑定 deployment 交集的 12 键结果（`_capability_intersection`）；`Embedding-v1` 冻结 `bge-m3-dense-1024-v1` 空间与上限（INV-6）。
- **验证**：`T-CFG-SPACE`。

#### `D-PROVIDER` / `D-DEPLOYMENT` / `D-SERVICE-LEVEL`（继承系统 §8.2/§8.3）
- **定义、Data/Type ID 与唯一来源**：系统设计 §8.2（`D-PROVIDER`/`D-DEPLOYMENT`/`D-SERVICE-LEVEL`）为唯一来源；持久 DDL `util/migrations/*.sql`；本机制不重列字段全集。
- **本层投影/约束**：`D-PROVIDER.name` 唯一、`secret_ref` 只存引用；`D-DEPLOYMENT.provider_id` 必须存在、`capabilities` 12 键；`D-SERVICE-LEVEL.id`∈`D-CFG-TIER`、成员有序、可删除性受限（`fixed_service_level`）。
- **状态 · 所有权 · 寿命**：operator 经 M004 写、M003 读；SQLite 持久带 `version`。
- **合法与拒绝实例**：合法引用已存在 provider；拒绝删除被引用 provider → 409 `resource_in_use`。
- **验证**：`T-CFG-DELREF`、`T-CFG-SPACE`。

### 4.4 通信报文结构

#### `D-CFG-ADMIN-WRITE` · 管理面写入报文（继承 `openapi`）
- **定义、Data/Type ID 与唯一来源**：CRUD 请求/响应 wire 载荷（`ProviderWrite`/`ProviderPatch`/`DeploymentWrite`/`DeploymentPatch`/`ServiceLevelWrite` 与对应 View + `ETag` 头）；`D-CFG-ADMIN-WRITE`；机器权威 `interfaces/openapi/llmtier.openapi.json` 与 `llmtier-management-contract-v0.3`，本节只给阅读视图。
- **字段（阅读视图）**：写入体字段同 §4.3 各结构；`secret_ref` 只写不回显（`has_secret` 投影）；响应带强 `ETag`。
- **约束 / 不变量**：PATCH 为 partial（只改出现字段）；`If-Match` 必填；错误以 `D-ERROR-ENVELOPE` 返回。
- **状态 · 所有权 · 寿命**：请求级 wire；M001 解析、M004 消费。
- **合法与拒绝实例**：合法 POST provider → 201+ETag；拒绝 `secret_ref="sk-…"` → 400。
- **验证**：`T-CFG-BADREF`、`T-CFG-CAS`。

### 4.5 设备与 FPGA 表项结构

不适用：LLMTier 为纯软件，无连接器、总线、寄存器或 FPGA 端口（tailoring `LT-TL-003`）。

### 4.6 运行状态数据结构

#### `D-CFG-BOOTSTRAP-STATE` · 引导状态
- **定义、Data/Type ID 与唯一来源**：空库是否已完成一次性 bootstrap 的权威事实；`D-CFG-BOOTSTRAP-STATE`；持久于 `schema_meta.bootstrap_sha256`（`registry.py` `bootstrap_settings`）。
- **字段 / 取值**：`bootstrap_sha256: str?`（settings 原始字节的 SHA-256；置位后不再改变）；派生 `ready: bool`（`/readyz` 布尔投影）。
- **约束 / 不变量**：唯一写者 = 引导事务；已有 hash → no-op（INV-2）；失败保持 `not_ready` 且不接流量（C-CFG-5）。
- **状态 · 所有权 · 寿命**：单行持久，库寿命；M004 写、启动/健康读。
- **合法与拒绝实例**：合法：空库 + 合法 settings → hash 置位 + ready；边界：已有 hash 时再次启动 → no-op，hash 不变。
- **验证**：`T-CFG-BOOT`。

### 4.7 数据库表结构

Authority = `util/migrations/*.sql`（M007 `migrate()` 执行）；列级阅读视图见 `util.isd` §4.4。本机制覆盖以下表：

| 表 | 主键 / 唯一 | 写入者 / 读者 | 寿命 |
|---|---|---|---|
| `providers` | `id` PK；`name` UNIQUE | M004 / M003 | 库寿命 |
| `deployments` | `id` PK；`name` UNIQUE；`provider_id` FK | M004 / M003 | 库寿命 |
| `deployment_runtime_profiles` | `deployment_id` PK | M004 / M003 | 库寿命 |
| `provider_usage_profiles` | `provider_id` PK | M004 / M003 | 库寿命 |
| `service_levels` | `id` PK（固定 Tier） | M004 / M003 | 库寿命 |
| `service_level_deployments` | `(service_level_id,deployment_id,ordinal)` | M004 / M003 | 库寿命 |
| `schema_meta` | `singleton`(=1) | 引导 / 启动、健康 | 库寿命 |
| `audit_events` | `id` PK | M004 / M005 | 审计策略 |

- **约束 / 不变量**：`provider_id` FK 必须存在；`service_level_deployments` 有序唯一；`capabilities_json` 12 键；`bootstrap_sha256` 置位后不再改写。
- **合法与拒绝实例**：合法：空库由迁移建表并 bootstrap 一次；拒绝：非空库 schema 版本不符由 M007 拒绝启动（系统 `ERR-SCHEMA`）。
- **验证**：`T-CFG-BOOT`、`T-CFG-CAS`。

### 4.8 错误码与错误结构

本机制不新增公共错误码；对外错误引用系统目录（`llmtier-system-design` §8.8）：

| 本层错误 | 条件 | 系统 Error ID | 结果已知性/副作用 | 合法下一步 |
|---|---|---|---|---|
| 503 `bootstrap_required` / `bootstrap_invalid` | 空库缺 settings 或 settings 非法 | `ERR-BOOT` | 已知失败；回滚；not_ready | 修正 settings 后重启 |
| schema 不符/完整性失败 | 版本不匹配/旧库未知 | `ERR-SCHEMA` | 已知失败；拒启动 | 运维离线迁移 |
| 400 `invalid_request` | 字段非法/非固定 Tier | `ERR-REQ-VALIDATION` | 未写入；无副作用 | 修正后重试 |
| 409 `resource_conflict` | name/唯一冲突 | `ERR-CONFLICT` | 未生效；事务回滚 | 改名重试 |
| 409 `resource_in_use` | 删除被引用资源 | `ERR-INUSE` | 未生效；资源不变 | 先解除引用 |
| 412 `version_conflict` | `If-Match` 过期 | `ERR-STALE` | 未生效；资源不变 | 重新 GET 后重试 |
| 404 | 未知 ID | `ERR-NOTFOUND` | 未受理；无副作用 | 修正 ID |
| 503 | 存储不可用 | `ERR-STORE` | 本次失败 | 稍后重试 |

- **约束 / 不变量**：错误载荷统一 `D-ERROR-ENVELOPE`；引导失败绝不以 legacy settings 覆盖已有 Store。
- **验证**：`T-CFG-BADREF`、`T-CFG-CAS`、`T-CFG-DELREF`。

### 4.9 编码、布局与共享类型映射

不适用二进制 ABI：SQLite 行 + JSON 列（紧凑分隔符 `,`/`:`）。

| 类型 ID / 编码源基线 | 逻辑宽度/序列化长度 | 实际 ABI 定位或不适用理由 | 原类型 → 投影/转换/损失 | 验证项 |
|---|---|---|---|---|
| `D-CFG-SETTINGS`（schema `llmtier-settings-v0.3`） | UTF-8 JSON 文档 | 无 wire offset；仅文件读取 | 文件 JSON → 行；`secret_ref` 保留引用，无明文 | `T-CFG-SECRET` |
| `D-CAPABILITY`（系统 §8.1） | 12 键 JSON 对象 | `deployments.capabilities_json` TEXT | 交集运算后写回，字段无损失 | `T-CFG-SPACE` |
| `D-CFG-ADMIN-WRITE`（`openapi`） | UTF-8 JSON + `ETag` 头 | 无端序/对齐 | wire → Registry 行；`secret_ref` 不回显 | `T-CFG-CAS` |
| `D-CFG-BOOTSTRAP-STATE` | 64 hex / bool | `schema_meta.bootstrap_sha256` TEXT | 原始字节 SHA-256 | `T-CFG-BOOT` |

### 4.10 一致性、可见性与数据寿命

初始化后 SQLite 是唯一运行权威；`config/settings.json` 变化不自动重导入、不双写（INV-1）。每次变更在单事务内提交并写审计，`version` 单调 +1，ETag 对应；并发写由 ETag 乐观并发串行化（stale→412）。读取不承诺跨请求一致快照：`candidates()` 在每次请求时重新核验 Registry version 与健康，避免读到陈旧快照。`Embedding-v1` 冻结空间与上限，非兼容变更须显式迁移/新建逻辑 ID。持久性保证对应 SQLite 文件；进程退出/重启以库内事实为准，引导失败不覆盖已有 Store。

## 5. 接口设计

> 按 STD `design-data-interface-format` 1.2.0 §3：主章“接口设计”，按**接口形态**分类逐接口完整记录；标题为真实调用形式，标题下先给完整接口声明，再就地说明输入/输出，最后按 §3.1 六项。数据结构引用 §4；错误引用系统 §8.8。

### 5.1 软件接口（适用时）

#### `Registry.bootstrap_settings(settings_path: str | None) -> None`
```text
Registry.bootstrap_settings(settings_path: str | None) -> None
```
- **Interface/Member ID、状态、文件·symbol**：`IF-CFG-BOOTSTRAP`；Implemented；唯一契约=本设计 + `llmtier-settings-v0.3.schema.json`；`src/management/registry.py` `Registry.bootstrap_settings`；由启动流程调用。
- **输入**：`settings_path: str | None`；前置=迁移已建表（`schema_meta` 单行存在）；授权=启动路径，无 HTTP 授权；校验顺序=读文件/解析 JSON → 顶层节集 == {providers,deployments,service_levels} → ID 唯一 → provider 引用完整 → 固定 Tier 与 deployment 引用 → `secret_ref` 仅 `env:`/`file:` 且可达 → 逐项字段集精确匹配。
- **成功输出**：无返回值——受理/生效/完成为同一事务：写入 providers/deployments/levels/成员 + `schema_meta.bootstrap_sha256` + bootstrap 审计；副作用=持久化；随后 `/readyz` 就绪（§4.6）。
- **错误与异常**：无 settings 且空库 → `ERR-BOOT`（503 `bootstrap_required`，未受理、无副作用）；解析/校验/事务失败 → `ERR-BOOT`（503 `bootstrap_invalid`，回滚、not_ready）；schema 不符由 M007 提前以 `ERR-SCHEMA` 拒绝；载荷 `D-ERROR-ENVELOPE`。合法下一步：修正 settings/迁移后重启。
- **交互与生命周期**：同步阻塞；启动期一次；事务全成功或全回滚（`store.transaction(True)`）；可重入：已有 `bootstrap_sha256` → 立即 no-op，不重导入（INV-2）；不热载文件（§13）。
- **实例与验证**：正常：空库 + 合法三节 settings → hash 置位、`/readyz` 就绪；边界：重复启动 → no-op 且 hash 不变。`T-CFG-BOOT`；Run=NOT_RUN。

#### `GET/POST /v1/providers`；`GET/PATCH/DELETE /v1/providers/{provider_id}`
```text
GET    /v1/providers?cursor=&limit=             -> 200 ProviderPage
POST   /v1/providers {ProviderWrite}            -> 201 ProviderView (ETag)
GET    /v1/providers/{provider_id}              -> 200 ProviderView (ETag)
PATCH  /v1/providers/{provider_id} {ProviderPatch} If-Match -> 200 ProviderView (ETag)
DELETE /v1/providers/{provider_id} If-Match     -> 204
  -> 4xx/5xx: ErrorEnvelope
```
- **Interface/Member ID、状态、文件·symbol**：`IF-CFG-PROVIDERS`；Implemented；唯一契约=`openapi` + `llmtier-management-contract-v0.3`；`src/http_api/app.py` → `src/management/registry.py`（`create/get/list/update/delete_provider`）。
- **输入**：`D-CFG-ADMIN-WRITE`（§4.4）；路径 `provider_id`；PATCH/DELETE 必填 `If-Match: D-CFG-VERSION-TAG`；授权=`admin` 角色（系统 `ERR-AUTH-*`）；校验顺序=鉴权 → body schema → `If-Match` → 业务约束。
- **成功输出**：`ProviderView`（`D-PROVIDER` 投影，`secret_ref` 只写不回显）+ 强 `ETag`；受理=写事务未提交前不对外；生效=提交后可见；副作用=同事务写 `D-AUDIT-EVENT`。
- **错误与异常**：`ERR-AUTH-*`（401/403/503）；`ERR-REQ-VALIDATION`（400）；`ERR-CONFLICT`（409 重名）；`ERR-INUSE`（409 被引用删除）；`ERR-STALE`（412 `If-Match` 过期）；`ERR-NOTFOUND`（404）；`ERR-STORE`（503）；逐条件结果已知、失败无副作用，载荷 `D-ERROR-ENVELOPE`。
- **交互与生命周期**：同步；PATCH partial（只改出现字段）；DELETE 幂等；ETag 乐观并发；版本单调 +1。
- **实例与验证**：正常 POST → 201+ETag；拒绝 stale PATCH → 412。`T-CFG-CAS`、`T-CFG-DELREF`；Run=NOT_RUN。

#### `GET/POST /v1/deployments`；`GET/PATCH/DELETE /v1/deployments/{deployment_id}`
```text
GET    /v1/deployments?cursor=&limit=            -> 200 DeploymentPage
POST   /v1/deployments {DeploymentWrite}         -> 201 DeploymentView (ETag)
GET    /v1/deployments/{deployment_id}           -> 200 DeploymentView (ETag)
PATCH  /v1/deployments/{deployment_id} {DeploymentPatch} If-Match -> 200 DeploymentView (ETag)
DELETE /v1/deployments/{deployment_id} If-Match  -> 204
  -> 4xx/5xx: ErrorEnvelope
```
- **Interface/Member ID、状态、文件·symbol**：`IF-CFG-DEPLOYMENTS`；Implemented；`src/http_api/app.py` → `src/management/registry.py`。
- **输入**：`D-CFG-ADMIN-WRITE`；`provider_id` 必须存在；`capabilities` 为 `D-CAPABILITY` 12 键；`If-Match`；授权=`admin`。
- **成功输出**：`DeploymentView` + `ETag`；副作用=同事务审计；新建时创建 `deployment_runtime_profiles` 行。
- **错误与异常**：未知 provider/能力非法 → `ERR-REQ-VALIDATION`（400）；重名 `ERR-CONFLICT`；删除被 level 引用 `ERR-INUSE`；`ERR-STALE`/`ERR-NOTFOUND`/`ERR-STORE`。
- **交互与生命周期**：同步；partial PATCH；DELETE 幂等；ETag 乐观并发。
- **实例与验证**：正常引用已存在 provider；拒绝未知 provider。`T-CFG-BADREF`；Run=NOT_RUN。

#### `GET/POST /v1/service-levels`；`GET/PATCH /v1/service-levels/{level_id}`（DELETE 禁止）
```text
GET   /v1/service-levels?cursor=&limit=          -> 200 ServiceLevelPage
POST  /v1/service-levels {ServiceLevelWrite}     -> 201 ServiceLevelView (ETag)
GET   /v1/service-levels/{level_id}              -> 200 ServiceLevelView (ETag)
PATCH /v1/service-levels/{level_id} {…} If-Match -> 200 ServiceLevelView (ETag)
DELETE /v1/service-levels/{level_id}             -> 409 fixed_service_level
  -> 4xx/5xx: ErrorEnvelope
```
- **Interface/Member ID、状态、文件·symbol**：`IF-CFG-LEVELS`；Implemented；`src/http_api/app.py` → `src/management/registry.py`。
- **输入**：`level_id`∈`D-CFG-TIER`；`deployment_ids[]` 有序；`If-Match`；授权=`admin`。
- **成功输出**：`ServiceLevelView`（含 `capabilities`=成员交集）+ `ETag`；副作用=写成员表（ordinal）+ 审计；版本 +1。
- **错误与异常**：非固定 Tier → `ERR-REQ-VALIDATION`（400）；成员无共同能力 → 409 `capability_conflict`；非兼容 Embedding → 409 `embedding_space_conflict`；删除固定 Tier → 409 `fixed_service_level`（`ERR-CONFLICT` 语义，系统无专码）；`ERR-STALE`/`ERR-NOTFOUND`。
- **交互与生命周期**：同步；DELETE 恒定拒绝；partial PATCH；ordinal 决定候选顺序，重启后不漂移。
- **实例与验证**：正常 PATCH Worker 成员 → 交集通过、版本 +1；拒绝 DELETE 固定 Tier → 409。`T-CFG-SPACE`；Run=NOT_RUN。

#### `Registry.candidates(level_id: str) -> list[Candidate]`
```text
Registry.candidates(level_id: str) -> list[Candidate]
```
- **Interface/Member ID、状态、文件·symbol**：`IF-CFG-CANDIDATES`；Implemented；`src/management/registry.py` `Registry.candidates`。
- **输入**：`level_id: D-CFG-TIER`；前置=调用方已鉴权（推理数据面）；授权=无额外（只读）；校验=level 存在且 enabled 成员。
- **成功输出**：`list[D-CFG-CANDIDATE]`（按 `ordinal` 升序）；受理/生效=逐次请求重新读取，不缓存陈旧快照；副作用=无。
- **错误与异常**：无 Error ID；未知/无成员 → 空列表（由 Router 转 404/503）；存储异常 → `ERR-STORE`。
- **交互与生命周期**：同步只读；请求级；幂等；每次调用重新核验版本与健康。
- **实例与验证**：正常返回有序候选；边界：未配置成员 → `[]`。路由用例；Run=NOT_RUN。

#### `Registry.get_service_level(level_id: str) -> tuple[dict, str]`
```text
Registry.get_service_level(level_id: str) -> tuple[dict, str]
```
- **Interface/Member ID、状态、文件·symbol**：`IF-CFG-GET-LEVEL`；Implemented；`src/management/registry.py`。
- **输入**：`level_id`；授权=内部调用；校验=读取 `service_levels` + 成员。
- **成功输出**：`(ServiceLevelView, ETag)`；受理/生效=只读即时；副作用=无。
- **错误与异常**：未知 ID → `ERR-NOTFOUND`（404）；载荷 `D-ERROR-ENVELOPE`。
- **交互与生命周期**：同步只读；幂等。
- **实例与验证**：正常读 `Worker`；拒绝未知 → 404。路由用例；Run=NOT_RUN。

### 5.2 消息与数据流接口（适用时）

不适用：配置变更为同步 HTTP 请求/响应，无事件/队列/流；`candidates()` 为同步只读查询。

### 5.3 硬件与固件接口（适用时）

不适用：无连接器、总线、寄存器或 FPGA 端口。

### 5.4 人机与维护接口（适用时）

#### `GET /readyz`
```text
GET /readyz -> 200 {status:"ready", models:[…]} | 503 {status:"not_ready", models:[]}
```
- **Interface/Member ID、状态、文件·symbol**：`IF-CFG-READY`；Implemented；`src/http_api/app.py` → `health.readiness_view`。
- **输入**：无参数；前置=进程存活；执行位置=LLMTier 管理面；授权=无鉴权或 operator 均可；校验=无。
- **成功输出**：`{status:"ready", models:[…]}`——受理/生效=即时；副作用=无。
- **错误与异常**：初始化失败 → 503 `{status:"not_ready", models:[]}`（以就绪状态表达，非 `D-ERROR-ENVELOPE`）；结果已知、无副作用；合法下一步=修正配置后重启。
- **交互与生命周期**：同步只读；幂等；无占用/取消/恢复。
- **实例与验证**：正常就绪返回 ready；引导失败返回 not_ready。`T-CFG-BOOT`；Run=NOT_RUN。

#### 离线迁移（单一版本命令）
```text
migrate(store_path) -> {from_version, to_version} | non-zero exit
```
- **Interface/Member ID、状态、文件/命令**：`IF-CFG-MIGRATE`；Manual；契约=本项目运维流程（`util` 迁移程序）。
- **输入**：目标=SQLite 文件；输入=单一目标版本；前置=已备份；执行位置=管理主机；授权=operator。
- **成功输出**：`{from_version, to_version}`——受理/完成=迁移提交；副作用=库 schema 变更（先备份）。
- **错误与异常**：失败 → 非零退出码；结果可能需按备份还原；不双写、不可并行（§13）。
- **交互与生命周期**：离线执行；不可与运行实例并行；终止后以备份/迁移结果为基线。
- **实例与验证**：运维演练；Run=NOT_RUN。

> `GET /healthz`（存活探针）为项目健康契约，记录于 §12.2，不构成本机制的数据/接口分配对象。

## 6. 正常端到端流程

![配置引导与变更时序](../../assets/diagrams/diagram-mech-config-sequence.png)

[可编辑 SVG 源](../../assets/diagrams/diagram-mech-config-sequence.svg)

图 M · 配置引导与变更时序（实线=请求，虚线=响应；先后关系非时间比例）。

1. **迁移 schema**：启动建表（含 `schema_meta` singleton）。
2. **引导判定**：读 `bootstrap_sha256`；空库且未提供路径 → 503 `bootstrap_required`。
3. **校验**：字段全集、ID 唯一、引用完整、Secret 引用可达（`env:`/`file:`）。
4. **事务写入**：providers/deployments/levels + `bootstrap_sha256` + bootstrap 审计；任一步失败回滚。
5. **就绪**：写入成功 → `/readyz` 就绪。
6. **运行期变更**：管理面事务 + ETag + 能力/不变量校验 + 审计。

### 6.1 交叠请求、跨轮次与生命周期边界

引导 = 一次生命周期（迁移→校验→写入→就绪）。变更 = 每管理动作一事务。**交叠**：并发变更由 ETag 串行化（stale → 412）；`candidates()` 在每次请求出队时重新核验 Registry version 与健康（避免读到陈旧快照）。

## 7. 分支和替代流程

| 分支 | 触发 | 处理 |
|---|---|---|
| 空库无路径 | 首次启动未给 settings | 503 `bootstrap_required`；not_ready |
| settings 不可读/非法 | 缺节/未知节/引用错误 | 503 `bootstrap_invalid`；**回滚**；not_ready |
| Secret 引用不可达 | `env:` 空或 `file:` 不存在 | 503 `bootstrap_invalid`；not_ready |
| 已 bootstrap | 再次启动 | no-op（不重导入）|
| 并发 PATCH | ETag 过期 | 412 `version_conflict` |
| 删除被引用 | provider/deployment 在用 | 409 `resource_in_use` |
| 能力不兼容 | 绑定集合无共同能力 | 409 `capability_conflict` |
| 非固定 Tier | 非法等级 ID | 400 `invalid_request` |
| 删固定 Tier | DELETE service-level | 409 `fixed_service_level` |
| 再导入 | 运维需要 | 显式离线迁移（备份 + 单一命令，不双写）|

## 8. 状态机与不变量

| INV-ID | 可验证断言（量词、条件和预期必须明确） | Enforcement / 事实来源 | 反例输入/违反后的结果 | 验证项 |
|---|---|---|---|---|
| INV-1 | 初始化后 SQLite 是唯一运行权威；文件不再影响运行 | `bootstrap_sha256` 置位（§4.6）| 文件热载 → 双写歧义 | T-CFG-BOOT |
| INV-2 | `bootstrap_sha256` 一旦置位不再改变（重复启动 no-op）| 引导事务 | 重复导入 → 覆盖已改配置 | T-CFG-BOOT |
| INV-3 | ∀ provider：Secret 明文不入库，只存 `env:`/`file:` 引用 | 校验 + 存储（§4.3）| 明文入库 → 泄密 | T-CFG-SECRET |
| INV-4 | 发布事务失败不改变 active snapshot（原子性）| 单事务（§6）| 半写 → 引用悬空 | T-CFG-BADREF |
| INV-5 | ∀ level：`capabilities` = 绑定 deployment 能力的交集（12 键）| `_validate_level` | 非交集 → 声明能力未实现 | T-CFG-SPACE |
| INV-6 | `Embedding-v1` 绑定 embedding-only 且 space/dim/上限与冻结契约一致 | `_validate_level` 特判 | 非兼容 space → 向量不可比 | T-CFG-SPACE |
| INV-7 | ∀ 资源：`version` 与 ETag 对应，变更单调 +1 | CRUD 事务 | 版本复用 → 并发覆盖 | T-CFG-CAS |

### 8.1 资源预留、交付、释放与复位

无租约/预留。**交付** = 事务提交 + 审计；**复位** = 误变更由备份/离线迁移回滚。初始化的"复位"即重建空库重引导。

## 9. 失败传播、重试与恢复

| Failure ID / 检测方 | 失败点与传播 | 结果已知性 | 已发生/可能副作用 | 访问安全/证据 | 操作终态 | 资源释放 | 重新准入/重试条件 |
|---|---|---|---|---|---|---|---|
| F-CFG-1 / 启动 | bootstrap 校验/事务失败 | 已知失败 | 无（回滚）| 无 | 进程 not_ready | 事务资源回滚 | 修正 settings 后重启 |
| F-CFG-2 / Management | 变更事务失败 | 已知失败 | 无（回滚）| 无 | 保持旧版本 | 事务资源回滚 | 修正后重试 |
| F-CFG-3 / Management | ETag 不匹配 | 已知失败 | 无 | 无 | 412 + `current_version` | 无 | 重新读取后重试 |
| F-CFG-4 / 启动 | Secret 引用不可达 | 已知失败 | 无 | 无 | not_ready | 无 | 修引用后重启 |
| F-CFG-5 / 迁移 | 离线迁移误操作 | 已知失败 | 需还原 | 备份为证据 | 按备份还原 | 备份恢复 | 运维流程 |

**恢复边界**：引导失败**绝不以 legacy settings 覆盖已有 Store**；重启以 SQLite 事实为准。

## 10. 并发、排序与容量

| 作用域 | 约束 | 行为 |
|---|---|---|
| 变更 | ETag `If-Match` | stale → 412，串行化 |
| 读取一致性 | 事务 + 出队复核 | 不读陈旧快照 |
| 容量 | 配置量小、变更低频 | 无专门限流 |
| 排序 | `service_level_deployments.ordinal` | 候选顺序重启后不漂移 |

## 11. 安全、权限与信任边界

| 资产 | 身份 | 强制点 | 拒绝 | 审计 |
|---|---|---|---|---|
| 配置变更 | operator 凭据 | Management 授权 | 401/403（不泄露存在性）| `audit_events` |
| Secret 引用 | operator | 只写引用 | 明文拒绝 | — |
| 配置读取 | operator | 管理面 | 401/403 | — |

边界：Secret 明文不进入库、普通响应、日志或 UI 回显（C-CFG-2）。

## 12. 可观测性与证据

### 12.1 统计、日志、时间与关联

变更写 `audit_events`（actor/action/target/result/时间）；`/readyz` 暴露初始化状态与就绪判断；时间统一 UTC。

### 12.2 维护命令、自检与调试路径

| Maintenance API / Command / Diagnostic ID | 执行位置、入口、目标、权限 | 完整请求/语法与结果/错误契约 | 施加/回读点及覆盖 | 依赖/占用/恢复退出 | 验证 |
|---|---|---|---|---|---|
| 就绪自检 `GET /readyz` | LLMTier 管理面；无鉴权/operator | 无参数；结果 = 初始化/依赖状态；错误 503 | 只读 | 无 | T-CFG-BOOT |
| 健康 `GET /healthz` | LLMTier；无鉴权 | 无参数；结果 = 存活 | 只读 | 无 | — |
| 离线迁移（CLI）| 管理主机；operator | 单一版本命令；结果 = 迁移结果；错误非零退出码 | 施加=库迁移；回读=版本 | 需备份；不双写 | 运维演练 |

## 13. 配置、兼容与部署

`config/settings.json` 仅 bootstrap 输入；生产变更只落 SQLite。迁移**先备份、单一版本命令、不双写**。兼容：能力键集与固定 Tier 为契约，变更需显式迁移。

## 14. 跨责任单元分解与接口分配（下级设计输入）

本章是**要求侧**：把本机制分解到各责任单元（LLMTier 为纯软件，责任单元 = 软件模块），说明每个对象必须负责什么、提供什么接口。下级模块设计在附录"机制承接表"逐条记录**落实侧**。

### 14.1 参与方到架构对象映射

| 机制参与方（§3） | 责任单元/Owner | 架构对象 ID / 类型 / 层或领域 | 下级设计文档 | 在本机制中的主责与非职责 |
|---|---|---|---|---|
| 引导 | 启动 / LLMTier | 启动流程（`__main__`）| `management-design.md` | 迁移、校验、事务写入、not_ready；不处理运行期变更 |
| 变更 | Management / LLMTier | Registry/Config、Admin（业务层）| `management-design.md` | CRUD、ETag、能力/不变量校验、审计；不承载推理 |
| 候选查询 | Management / LLMTier | Registry/Config（业务层）| `management-design.md` | 等级候选（只读）|
| 入口 | HTTP API / LLMTier | HTTP Adapter（入口层）| `http-api-design.md` | 管理面路由、错误映射；不含业务规则 |
| 存储/审计 | LLMTier | Store、Audit Writer（基础层）| `util-design.md` | 事务、审计 |
| 管理 UI | Web UI / LLMTier | 管理控制台（入口层）| `web-ui-design.md` | 操作管理面；不直读库/Secret |

### 14.2 功能和步骤到责任单元分配

| Capability / Process Step / Constraint | 主责架构对象 | 协作对象 | 必须产生或消费的结果 | 固定行为 / 本地自由度 | 组合验证责任 |
|---|---|---|---|---|---|
| Step 1 迁移 schema | 启动 / Store | — | 表结构 | 迁移实现可自定 | T-CFG-BOOT |
| Step 2 引导判定 | 启动 | Management | 503 或继续 | `bootstrap_sha256` 语义固定 | T-CFG-BOOT |
| Step 3 校验（C-CFG-3）| Management | Store（引用可达）| 通过或 typed error | 校验顺序固定；实现可自定 | T-CFG-BADREF |
| Step 4 事务写入（C-CFG-1/4）| Management | Store、Audit Writer | Registry + hash + 审计 | 原子性固定 | T-CFG-BOOT |
| Step 5 就绪（C-CFG-5）| 启动 | Health | `/readyz` | 就绪判定固定 | T-CFG-BADREF |
| Step 6 运行期变更 | Management | Store、Audit Writer | 新版本 + 审计 | ETag 固定 | T-CFG-CAS |
| 候选查询 | Management | Inference | 候选列表 | 排序 `ordinal` 固定 | 路由用例 |

### 14.3 责任单元间接口契约

> 本节为**分配视图**：只把 §14.1 的责任单元映射到 §5 已定义的接口成员 ID 与 §4 结构 ID；完整签名、字段、编码和错误码由 §5 与系统 §8.8 唯一维护，本节不复制。

| 责任单元（§14.1） | 承接的成员/结构 ID（§4/§5） | 角色 | 本机制固定的语义与边界（引用） |
|---|---|---|---|
| 启动流程 | `IF-CFG-BOOTSTRAP`、`D-CFG-SETTINGS`（§4.3）、`D-CFG-BOOTSTRAP-STATE`（§4.6） | 消费/提供 | 迁移、一次性引导、not_ready；不处理运行期变更（§5.1） |
| Management（Registry/Config、Admin） | `IF-CFG-PROVIDERS`、`IF-CFG-DEPLOYMENTS`、`IF-CFG-LEVELS`、`IF-CFG-CANDIDATES`、`IF-CFG-GET-LEVEL` | 提供 | CRUD+ETag、能力/不变量校验、审计、有序候选（§5.1） |
| HTTP Adapter | `IF-CFG-PROVIDERS`、`IF-CFG-DEPLOYMENTS`、`IF-CFG-LEVELS` | 消费/映射 | 管理面路由与错误映射；不含业务规则 |
| Inference 编排 / Internal Admission | `IF-CFG-CANDIDATES`、`IF-CFG-GET-LEVEL` | 消费 | 只读等级/能力与有序候选；不做跨等级 fallback |
| Store / Audit Writer | 各持久表（§4.7） | 提供 | 事务、审计；唯一持久化 |
| Web UI | `IF-CFG-PROVIDERS`、`IF-CFG-DEPLOYMENTS`、`IF-CFG-LEVELS` | 消费 | 管理控制台；不直读库/Secret |

### 14.4 下级设计输入清单

| 下级要求 ID | 承接对象 ID / 下级设计文档 | 来源 Capability / Step / Constraint / 接口成员 | 必须负责的行为与保证 | 必须提供/消费的接口 | 下级必须展开的问题 | 允许自行决定的范围 | 本地验证 / 组合验证交接 |
|---|---|---|---|---|---|---|---|
| R-CFG-01 | Management（Registry/Config）· `management-design.md` | C-CFG-1/2/3/4、Step 3/4/6、interface `bootstrap_settings`/CRUD/`candidates`/`get_service_level` | 唯一权威、发布事务、能力不变量、审计 | `bootstrap_settings`、CRUD、`candidates`、`get_service_level` | 事务边界、ETag、交集算法、Embedding 冻结 | 存储/算法实现 | 契约；系统用例 |
| R-CFG-02 | 启动 · `management-design.md` | C-CFG-5、Step 1/2/5 | 迁移、引导、not_ready | 启动流程 | 失败回滚、就绪判定 | 引导实现 | T-CFG-BOOT |
| R-CFG-03 | Store · `util-design.md` | Step 1/4、interface `transaction` | 事务与版本 | `transaction` | 原子性、迁移 | 存储实现 | T-CFG-BOOT |
| R-CFG-04 | HTTP Adapter · `http-api-design.md` | Step 6 | 管理面路由与错误映射 | 路由 | 400/404/409/412 映射 | 映射实现 | 契约 |
| R-CFG-05 | Web UI · `web-ui-design.md` | CAP-CFG-CRUD | 管理控制台 | 管理面调用 | 不直读库/Secret | 呈现实现 | 组合 |

**约束**：下游不得新增路径前缀或旁路存储；新增配置维度须回写本节并关联模块设计。

## 15. 验证、上线与回滚

### 15.1 输入构造、故障控制与独立判据

| Test / Constraint | 输入与预置事实 | arm/hit/release | 独立 Oracle |
|---|---|---|---|
| T-CFG-BOOT / C-CFG-1 | 空库 + 合法 settings | — | Registry 与 hash 一致；重复启动 no-op |
| T-CFG-BADREF / C-CFG-3 | 非法引用/缺节 | — | 503 + 回滚 + not_ready |
| T-CFG-SECRET / C-CFG-2 | 含 Secret 明文引用 | — | 库中只有引用、无明文 |
| T-CFG-CAS / §7 | 并发 PATCH | — | 一个成功、一个 412 |
| T-CFG-DELREF / §7 | 删除被引用资源 | — | 409 `resource_in_use` |
| T-CFG-SPACE / INV-6 | 非兼容 Embedding | — | 409 `embedding_space_conflict` |

### 15.2 环境部署、复位、并发隔离与自动化

测试用独立临时库；复位 = 重建空库；并发用例核验 ETag 串行化。

### 15.3 组合验收、启用与旧机制退出

`LT-ADR-05`（单次 bootstrap，不热载）。组合验收 = Operator 管理面 + 推理候选联调。

## 16. 风险、未决问题与决定

| ID | 类别 | 影响 | 下一步 | 状态 |
|---|---|---|---|---|
| LT-ADR-05 | 决定 | 单次 bootstrap、不热载 | 已采用 | 已定 |
| RISK-CFG-1 | 风险 | 离线迁移误操作 | 由备份 + 单一命令约束 | 观察 |

## A. 输入基线、适用性与图文规则

- 输入：系统设计 §10、§3.4、`LT-ADR-05`、`registry.py`、`store.py`。
- 适用性：纯软件、单节点 SQLite 配置机制。§4.9（二进制 ABI）不适用；§8.1（租约）不适用。
- 图：时序图（§6）表达引导与变更。

## B. 文档控制与修订记录

初版 `0.1.0-draft.1`；`draft.3` 补实全部章节、增模块分解与不变量。修订见 Git。
