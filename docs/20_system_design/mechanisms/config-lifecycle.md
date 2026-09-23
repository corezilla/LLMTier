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
| Last Modified Date | `2026-09-22` |
| Template ID | `design.system-mechanism` |
| Template Version | `2.4.0` |
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
| C-CFG-1 | 初始化后 SQLite 是唯一运行权威 | Management | 存储布局 | §4.3、§8 |
| C-CFG-2 | Secret 明文不入库，只存引用 | Management | 引用形式 | §4.1、§11 |
| C-CFG-3 | 发布先验证引用/不变量，再原子推进 | Management | 事务实现 | §6、§8 |
| C-CFG-4 | 变更失败回滚且不改 active snapshot | Management | — | §7、§9 |
| C-CFG-5 | 初始化失败服务 not_ready | 启动 | — | §9 |

### 3.2 运行时统筹与确认责任

**bootstrap** 统筹于启动事务；**变更**统筹于管理动作，成功即写审计。发布事务是唯一的"确认"点。

### 3.3 拓扑、目标身份与共享故障域

单节点单文件；无跨节点协调。SQLite 为唯一权威；`config/settings.json` 仅为一次性输入，**故障域之外**（不参与运行期）。

## 4. 数据结构设计

### 4.1 类型目录与完整字段

> 数据定义分支：**已有机器源**（见下表“机器源”列）；正文只给阅读视图与差异，不另抄完整规范。

| 实体 | 关键字段 | 说明 |
|---|---|---|
| `providers` | id、name（唯一）、kind(`cloud`/`local`)、endpoint、`secret_ref`、enabled、version | Secret 只存引用 |
| `deployments` | id、name、provider_id、backend_model、`capabilities`(JSON)、enabled、health、version | health ∈ {unknown,healthy,unhealthy} |
| `service_levels` | id ∈ 7 个固定 Tier、enabled、`capabilities`(JSON)、version | 等级能力为绑定 deployment 的交集 |
| `service_level_deployments` | level_id、deployment_id、ordinal | 选择顺序稳定 |
| `schema_meta` | `bootstrap_sha256` | 一次性引导标记 |
| `audit_events` | id、actor、action、target、result、时间 | 脱敏审计 |

**capabilities 键集**（固定 12 键）：`responses`、`embeddings`、`tools`、`structured_outputs`、`input_modalities`、`output_modalities`、`context_window`、`max_output_tokens`、`embedding_space_id`、`embedding_dimensions`、`embedding_max_batch_inputs`、`embedding_max_input_tokens`。

**固定 Tier**：`Senior`、`Junior`、`Worker`、`Associate`、`Engineer`、`Executor`、`Embedding-v1`。

### 4.2 编码、布局与共享类型映射

不适用二进制 ABI：JSON 列（紧凑分隔符）+ SQLite 行。schema 见 `interfaces/schemas/llmtier-settings-v0.3.schema.json` 与系统设计 §8.2。

### 4.3 一致性、可见性与数据寿命

初始化后文件变化不自动重导入；不双写。每次变更 `version+1`，ETag = `"<id>.v<version>"`。`Embedding-v1` 冻结 `bge-m3-dense-1024-v1` 空间与上限。

## 5. 接口设计

### 5.1 逐操作签名、错误与调用演练

**启动**：`bootstrap_settings(path)` → 校验 → 单事务写入 → `bootstrap_sha256` 置位（可重入：已有 hash 则 no-op）。

**管理面（Management，operator 凭据）**：

| 资源 | 操作 | 成功 | 关键错误 |
|---|---|---|---|
| `providers` | GET/POST/PATCH/DELETE `/v1/providers[/{id}]` | 视图 + ETag | 400、404、409 `resource_conflict`/`resource_in_use`、412 `version_conflict` |
| `deployments` | 同上 `/v1/deployments` | 视图 + ETag | 400（未知 provider/能力）、409、412 |
| `service-levels` | GET/POST/PATCH `/v1/service-levels`，DELETE 禁止 | 视图 + ETag | 400、409 `capability_conflict`/`embedding_space_conflict`、412、409 `fixed_service_level`（删除）|

| 项 | 内容 |
|---|---|
| 并发控制 | PATCH/DELETE 必须带 `If-Match`；不匹配 412 `version_conflict`（附 `current_version`）|
| PATCH 语义 | 只改出现字段；省略=保持 |
| 删除保护 | 被引用时 409 `resource_in_use`（provider 被 deployment、deployment 被 level）|
| 幂等 | GET 只读；POST 非幂等（唯一名冲突 409）；DELETE 幂等 |

**调用演练**：POST `/v1/providers`(name=local,kind=local,endpoint=…,secret_ref=env:OMLX,enabled=true) → POST `/v1/deployments`(provider_id=…,capabilities=12 键) → PATCH `/v1/service-levels/Worker`(deployment_ids=[…],`If-Match`) → 能力交集校验通过 → 版本 +1 → Inference 可查询候选。

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
| INV-1 | 初始化后 SQLite 是唯一运行权威；文件不再影响运行 | `bootstrap_sha256` 置位（§4.3）| 文件热载 → 双写歧义 | T-CFG-BOOT |
| INV-2 | `bootstrap_sha256` 一旦置位不再改变（重复启动 no-op）| 引导事务 | 重复导入 → 覆盖已改配置 | T-CFG-BOOT |
| INV-3 | ∀ provider：Secret 明文不入库，只存 `env:`/`file:` 引用 | 校验 + 存储（§4.1）| 明文入库 → 泄密 | T-CFG-SECRET |
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
| 引导 | 启动 / LLMTier | 启动流程（`__main__`）| `llmtier-core-design.md` | 迁移、校验、事务写入、not_ready；不处理运行期变更 |
| 变更 | Management / LLMTier | Registry/Config、Admin（业务层）| `llmtier-core-design.md` | CRUD、ETag、能力/不变量校验、审计；不承载推理 |
| 候选查询 | Management / LLMTier | Registry/Config（业务层）| `llmtier-core-design.md` | 等级候选（只读）|
| 入口 | HTTP API / LLMTier | HTTP Adapter（入口层）| `llmtier-core-design.md` | 管理面路由、错误映射；不含业务规则 |
| 存储/审计 | LLMTier | Store、Audit Writer（基础层）| `llmtier-core-design.md` | 事务、审计 |
| 管理 UI | Web UI / LLMTier | 管理控制台（入口层）| `llmtier-webui-design.md` | 操作管理面；不直读库/Secret |

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

| 接口成员 ID / 固定 baseline | 提供对象 | 全部消费对象 | 调用/事件形态 | 本机制固定的语义与错误 | 期限/取消/重复及边界 |
|---|---|---|---|---|---|
| `bootstrap_settings(path)` | Management | 启动 | 函数 | 一次性引导 | 503 |
| `create/get/list/update/delete_{provider,deployment,service_level}` | Management | HTTP Adapter | 函数 | CRUD + ETag | 400/404/409/412 |
| `candidates(level_id)` | Management | Internal Admission | 只读查询 | 有序候选 | — |
| `get_service_level(model)` | Management | Inference 编排 | 只读查询 | 等级 + 能力 | 404 |
| `transaction(True)` | `util` Store | Management | 上下文 | 原子提交 | 存储错误 |

### 14.4 下级设计输入清单

| 下级要求 ID | 承接对象 ID / 下级设计文档 | 来源 Capability / Step / Constraint / 接口成员 | 必须负责的行为与保证 | 必须提供/消费的接口 | 下级必须展开的问题 | 允许自行决定的范围 | 本地验证 / 组合验证交接 |
|---|---|---|---|---|---|---|---|
| R-CFG-01 | Management（Registry/Config）· `llmtier-core-design.md` | C-CFG-1/2/3/4、Step 3/4/6、interface `bootstrap_settings`/CRUD/`candidates`/`get_service_level` | 唯一权威、发布事务、能力不变量、审计 | `bootstrap_settings`、CRUD、`candidates`、`get_service_level` | 事务边界、ETag、交集算法、Embedding 冻结 | 存储/算法实现 | 契约；系统用例 |
| R-CFG-02 | 启动 · `llmtier-core-design.md` | C-CFG-5、Step 1/2/5 | 迁移、引导、not_ready | 启动流程 | 失败回滚、就绪判定 | 引导实现 | T-CFG-BOOT |
| R-CFG-03 | Store · `llmtier-core-design.md` | Step 1/4、interface `transaction` | 事务与版本 | `transaction` | 原子性、迁移 | 存储实现 | T-CFG-BOOT |
| R-CFG-04 | HTTP Adapter · `llmtier-core-design.md` | Step 6 | 管理面路由与错误映射 | 路由 | 400/404/409/412 映射 | 映射实现 | 契约 |
| R-CFG-05 | Web UI · `llmtier-webui-design.md` | CAP-CFG-CRUD | 管理控制台 | 管理面调用 | 不直读库/Secret | 呈现实现 | 组合 |

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
- 适用性：纯软件、单节点 SQLite 配置机制。§4.2（二进制 ABI）不适用；§8.1（租约）不适用。
- 图：时序图（§6）表达引导与变更。

## B. 文档控制与修订记录

初版 `0.1.0-draft.1`；`draft.3` 补实全部章节、增模块分解与不变量。修订见 Git。
