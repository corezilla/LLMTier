<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier M007 util 模块设计

> STD 使用入口：[项目采用说明与标准导航](../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `util` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-23` |
| Last Modified Date | `2026-09-25` |
| Template ID | `design.definition` |
| Template Version | `3.2.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/40_module_design/util-design.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 单元摘要：为什么存在

| 项目 | 内容 |
|---|---|
| 模块编号 / 正式英文名称 | **M007** / `util` |
| 直属父对象编号 / 名称 | LLMTier 软件系统（本项目无子系统）|
| 父设计 Document ID / 登记位置 | `llmtier-system-design` / 系统设计 §3.2（唯一登记表）|
| 上级系统 / 父单元 | LLMTier 软件系统 |
| 解决的问题 | 全部持久化数据（配置、账本、审计、日志、观测）需要一个**唯一**的存取层与事务边界，避免多模块直连数据库、各自实现连接/迁移 |
| 提供的能力 | SQLite 线程内连接管理、迁移、事务、只读查询；bootstrap settings 路径的读取入口；配置/状态文件位置的唯一约定 |
| 主要使用者 | 全部业务模块（M003/M004/M005/M006/M008）|
| 不负责 | 业务规则；配置语义（M004）；账本/审计/日志/观测的语义（各自模块）|

### 1.1 继承的上级约束与落实方式

#### 1.1.1 `C-CFG-1` · 唯一持久化
- **上级基线与决定状态**：系统设计 §3.4；已采用
- **适用条件**：全部持久化
- **继承预算或行为保证**：所有写路径经 M007；不旁路
- **可自行选择 / 不可改变**：存储引擎可自选（当前 SQLite）；唯一性不可变
- **本地落实 / 内部再分配**：I1 连接、I2 事务；§8
- **验证方法与结果 / 证据**：`VRC-UTIL-001`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：无

#### 1.1.2 `C-OBS-…`（观测表）与 `C-METER-…`（账本表）的存储承接
- **上级基线与决定状态**：机制 M-OBS `R-OBS-06`、M-METER `R-MET-01/02`；已采用
- **适用条件**：账本/观测表
- **继承预算或行为保证**：原子事务、只追加语义由业务模块维护，M007 只提供事务
- **可自行选择 / 不可改变**：表结构可自选；事务语义不可变
- **本地落实 / 内部再分配**：I2 事务；§8
- **验证方法与结果 / 证据**：`VRC-UTIL-002`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：与 M-METER/M-OBS 一致

## 2. 需求、功能与验收条件

### 2.1 `F-UTIL-CONN` · 线程内连接
- **上级需求 / Constraint ID**：`C-CFG-1`
- **调用方**：全部业务模块
- **输入与前提**：库路径
- **行为**：按线程缓存连接；`PRAGMA foreign_keys=ON`、`journal_mode=WAL`；`timeout=10`
- **输出**：`sqlite3.Connection`
- **错误与边界**：连接失败 → 异常
- **验收条件**：同线程复用连接；每请求 `finally` 关闭

### 2.2 `F-UTIL-MIGRATE` · 迁移与完整性检查
- **上级需求 / Constraint ID**：`C-CFG-1`
- **调用方**：启动
- **输入与前提**：`migrations/*.sql`
- **行为**：注释行剥离后**逐语句**执行（不用 `executescript`）；`PRAGMA integrity_check`
- **输出**：表就绪 / 异常
- **错误与边界**：非 `ok` → `ApiError(503,"schema_integrity_failed")`
- **验收条件**：迁移幂等（`IF NOT EXISTS`）；完整性 ok

### 2.3 `F-UTIL-TXN` · 事务
- **上级需求 / Constraint ID**：`C-CFG-1/3`；机制 R-CFG-03
- **调用方**：全程业务模块
- **输入与前提**：`immediate` 标志
- **行为**：`BEGIN [IMMEDIATE]` → yield conn → commit / rollback
- **输出**：连接（上下文）
- **错误与边界**：异常 → rollback 并重抛
- **验收条件**：原子提交/回滚

### 2.4 `F-UTIL-QUERY` · 只读查询
- **上级需求 / Constraint ID**：`C-CFG-1`
- **调用方**：全程业务模块
- **输入与前提**：SQL + params
- **行为**：`one`/`all` 返回 `sqlite3.Row`
- **输出**：行
- **错误与边界**：SQL 错误 → 异常
- **验收条件**：返回行工厂为 `Row`

### 2.5 `F-UTIL-CLOSE` · 连接关闭
- **上级需求 / Constraint ID**：`C-CFG-1`
- **调用方**：M001 `finally`
- **输入与前提**：—
- **行为**：关闭当前线程连接并清空缓存
- **输出**：—
- **错误与边界**：—
- **验收条件**：每请求后 fd 释放

## 3. UI、CLI、服务端点或设备操作面

**N/A — 本模块没有直接操作面。** M007 是基础层存储库，由业务模块在进程内调用；对外端点由 M001 暴露。Tailoring 依据：系统设计 §3.2 规定 util 提供唯一持久化存取。

## 4. 外部边界与依赖

#### 4.1 `DEP-ALL` · 全部业务模块（消费）
- **角色 / 运行位置 / Owner**：消费方；同进程；LLMTier
- **本模块调用或消费**：—
- **本模块提供**：`Store.connection/migrate/transaction/one/all/close`
- **契约 authority / 版本 / selector**：本文 §9
- **同步方式 / timeout / 生命周期**：同步；线程内连接
- **不可用或失败影响 / 责任出口**：存储错误 → 调用方处理（503/回滚）

#### 4.2 `DEP-FS` · 文件系统 / SQLite（外部）
- **角色 / 运行位置 / Owner**：外部；进程外；OS
- **本模块调用或消费**：SQLite 文件、`migrations/*.sql`
- **本模块提供**：—
- **契约 authority / 版本 / selector**：SQLite
- **同步方式 / timeout / 生命周期**：同步；连接超时 10 s
- **不可用或失败影响 / 责任出口**：异常冒泡

## 5. 内部结构与实现位置

### 5.1 内部组成

#### 5.1.1 `I1` · 连接管理
- **职责与非职责**：按线程缓存 `sqlite3.Connection` 并设置 PRAGMA；不做事务/迁移
- **输入、处理与输出**：路径 → 连接
- **协作对象**：I2、I3
- **文件 / symbol / 实现状态**：`store.py` `Store.connection/close`；Implemented
- **拆分依据与替代方案代价**：线程内复用避免每请求重连；`finally` 关闭防 fd 泄漏

#### 5.1.2 `I2` · 事务
- **职责与非职责**：`transaction(immediate)` 上下文；不做业务校验
- **输入、处理与输出**：— → conn
- **协作对象**：I1
- **文件 / symbol / 实现状态**：`store.py` `Store.transaction`；Implemented
- **拆分依据与替代方案代价**：`BEGIN IMMEDIATE` 供写路径串行化

#### 5.1.3 `I3` · 迁移
- **职责与非职责**：按序执行迁移 + 完整性检查；不含业务 DDL 语义
- **输入、处理与输出**：— → 表就绪
- **协作对象**：I1
- **文件 / symbol / 实现状态**：`store.py` `Store.migrate`；Implemented
- **拆分依据与替代方案代价**：SQL 文件式迁移，简单可审

#### 5.1.4 `I4` · 查询
- **职责与非职责**：`one`/`all` 只读；不做写入
- **输入、处理与输出**：SQL+params → 行
- **协作对象**：I1
- **文件 / symbol / 实现状态**：`store.py` `Store.one/all`；Implemented
- **拆分依据与替代方案代价**：统一 Row 工厂

### 5.2 内部调用过程

#### 5.2.1 `CALL-UTIL-TXN` · 一次写事务
- **入口与调用上下文**：业务模块 `with store.transaction(True) as conn:`
- **调用链**：`transaction` → `connection`（线程内）→ `BEGIN IMMEDIATE` → 业务 SQL → `commit`/`rollback`
- **逐步传递的数据**：SQL/params → 行/计数
- **返回、异常与清理**：异常 → rollback + 重抛
- **对应流程 / 接口 / 验证**：§7 P-UTIL-TXN / `VRC-UTIL-002`

### 5.3 文件间接口契约

> 本模块内部/跨模块文件交接逐项映射到 §9 的成员定义；签名、输入输出、错误与寿命以 §9 对应记录为唯一来源，本节不再复写。

| 内部契约 ID | provider → consumer | §9 成员 | 本文件责任 | 验证 |
|---|---|---|---|---|
| `IF-UTIL-01` | 全部业务模块 → `src/util/store.py` | §9.1 `IF-UTIL-CONN`–`IF-UTIL-TXN`、`IF-UTIL-QUERY`、`IF-UTIL-CLOSE` | 业务模块只经 `Store` 取得连接/事务/只读行并负责关闭 | `VRC-UTIL-001/002` |
| `IF-UTIL-02` | `src/util/store.py` → `migrations/*.sql` | §9.1 `IF-UTIL-MIGRATE` | `migrate()` 按文件名排序执行 SQL 并做完整性检查 | `VRC-UTIL-002` |

### 5.4 服务提供方式（条件适用）

- **运行载体与入口**：N/A + 依据 —— 嵌入式库；无独立 server
- **并发/线程模型**：N/A + 依据 —— 每线程一连接（`threading.local`）；写用 `BEGIN IMMEDIATE`
- **初始化、Ready、生效与停止**：`migrate()` 在 `Application.__init__` 调用；`close()` 在请求 `finally`/停机
- **宿主装配、失败和资源回收责任**：由 M001 装配；fd 回收见 §8.4

### 5.5 依赖方向

- **允许方向**：全部业务模块 → M007 → SQLite/FS
- **禁止方向与原因**：M007 不得 import 任何业务模块（基础层不反向依赖）
- **循环/越层检查**：`store.py` 只 import 标准库
- **变更影响**：`transaction`/`connection` 语义变更影响全部业务模块

## 6. 数据结构设计

> 按 STD `design-data-interface-format` 1.2.0：主章“数据结构设计”，章内按**数据性质分类**。M007 为纯软件存储库，无 wire、无设备；`6.2 业务与操作数据结构`（无业务载荷，只提供存取原语）、`6.4 通信报文` 与 `6.5 设备与 FPGA 表项` 不适用。继承结构只定位原定义；本层拥有的结构逐项完整记录（Data/Type ID、用途与来源／逐字段／跨字段与寿命／合法与拒绝实例／验证），每个结构以真实名称作带编号小节标题。

**适用性**：6.1 公共基础类型与枚举 ✓｜6.2 业务与操作数据结构 ✗（基础层无业务载荷，只有连接/事务/查询原语）｜6.3 配置与规则数据结构 ✓｜6.4 通信报文 ✗（无 wire 报文）｜6.5 设备与 FPGA 表项 ✗（无连接器/总线/寄存器/FPGA 端口）｜6.6 运行状态数据结构 ✓｜6.7 数据库表结构 ✓（authority = `util/migrations/*.sql`）｜6.8 错误码与错误结构 ✓（引用系统 Error ID）。

### 6.1 公共基础类型与枚举

**6.1.1 `SchemaVersion`（公共基础类型与枚举）**

```text
SchemaVersion {
  value: uint32   // EXPECTED_SCHEMA_VERSION；当前 = 2
}
```

- **Data/Type ID、用途与来源**：

  `D-UTIL-SCHEMA-VERSION`；本进程唯一期望的库 schema 版本；来源 `src/util/store.py` `EXPECTED_SCHEMA_VERSION`。

- **`value`**：

  必填正整数，当前恒 `2`；只接受与期望值精确相等；无升级/降级/自动修复（init-only）。

- **跨字段与寿命**：

  模块常量与 `schema_meta.schema_version` 持久；随代码版本；进程启动时比对，不匹配即拒绝启动。

- **合法/拒绝实例**：

  合法启动 `schema_version=2`；拒绝 `schema_version!=2` → `ApiError(503,"schema_version_mismatch")`。

- **验证**：

  `VRC-UTIL-002`；实现 `src/util/store.py`。

**6.1.2 `TxnMode`（公共基础类型与枚举）**

```text
enum TxnMode { DEFERRED, IMMEDIATE }
```

- **Data/Type ID、用途与来源**：

  `D-TXN` 的模式取值；事务开启模式；来源 `store.transaction(immediate)`。

- **`DEFERRED`**：

  `immediate=false`；以 `BEGIN` 开启；用于读事务。

- **`IMMEDIATE`**：

  `immediate=true`；以 `BEGIN IMMEDIATE` 开启；写路径串行化。

- **跨字段与寿命**：

  单次上下文取值；无持久；异常必经 rollback、成功必 commit。

- **合法/拒绝实例**：

  合法写事务 `IMMEDIATE`；边界：读事务 `DEFERRED`。

- **验证**：

  `VRC-UTIL-002`。

### 6.3 配置与规则数据结构

**6.3.1 `BootstrapConfig`（配置与规则数据结构）**

```text
BootstrapConfig {
  providers: ProviderSpec[],
  deployments: DeploymentSpec[],
  service_levels: ServiceLevelSpec[]
}
```

- **Data/Type ID、用途与来源**：

  `D-CFG-SETTINGS`；空库首次引导输入的 settings 结构，bootstrap 后不再是运行权威；authority `config/settings.json`，字段语义由 M004 `F-MGMT-BOOTSTRAP` 定义。

- **`providers`**：

  必填数组；provider 定义集合（字段与引用规则见 M004 §2.1）。

- **`deployments`**：

  必填数组；deployment 定义集合（引用 `providers`，见 M004 §2.1）。

- **`service_levels`**：

  必填数组；固定 tier 绑定集合（引用 `deployments`，见 M004 §2.1）。

- **跨字段与寿命**：

  仅在空库缺 `schema_meta` 时读取一次；先验证（字段/ID/引用/Secret 可达）再单事务写入；不双写；文件随仓库，运行期权威在 SQLite（M004）。

- **合法/拒绝实例**：

  合法：合法引用集合被单事务写入；拒绝：非法字段/引用 → M004 回滚并 `not_ready`（`ERR-BOOT`）。

- **验证**：

  `VRC-MGMT-001`；来源 M004 §2.1。

### 6.6 运行状态数据结构

**6.6.1 `Store`（运行状态数据结构）**

```text
Store {
  path: string,
  _local.connection: sqlite3.Connection?   // threading.local
}
```

- **Data/Type ID、用途与来源**：

  `D-UTIL-STORE`；库路径与每线程连接的持有者；来源 `src/util/store.py`，随进程。

- **`path`**：

  必填字符串；SQLite 文件路径；构造前做 symlink/权限预检。

- **`_local.connection`**：

  可空 `sqlite3.Connection`；线程内连接缓存；首次 `connection()` 建立、`close()` 置 `None`。

- **跨字段与寿命**：

  每线程一连接；`close()` 关闭并置 `None`；跨线程不共享；线程进入创建、随进程存活。

- **合法/拒绝实例**：

  合法：同线程复用连接；边界：请求结束未关闭 → fd 泄漏（由 `finally` 兜底）。

- **验证**：

  `VRC-UTIL-001`；实现 `src/util/store.py`。

**6.6.2 `TxnContext`（运行状态数据结构）**

```text
TxnContext {
  store: Store,
  conn: sqlite3.Connection,
  immediate: bool,
  owns_txn: bool           // txn(conn) 传入时为外借，不提交
}
```

- **Data/Type ID、用途与来源**：

  `D-TXN`；一次事务的运行时上下文；来源 `store.transaction` / `txn`。

- **`store`**：

  必填；所属 `Store`。

- **`conn`**：

  必填；本次事务使用的连接。

- **`immediate`**：

  必填布尔；见 §6.1.2 `TxnMode`。

- **`owns_txn`**：

  必填布尔；`txn(conn)` 传入已有连接时为 `false`（并入调用方事务，不提交）。

- **跨字段与寿命**：

  只有一个写者提交；嵌套调用经 `conn` 复用不另开事务；上下文作用域，退出即 commit/rollback。

- **合法/拒绝实例**：

  合法 `with store.transaction(True)`；边界：业务传入已有 `conn` → 并入调用方事务。

- **验证**：

  `VRC-UTIL-002`。

### 6.7 数据库表结构

Authority = `util/migrations/001_initial.sql`、`util/migrations/002_observability.sql`（由 `Store.migrate()` 执行）。M007 拥有全部 DDL 与 `schema_meta`；业务表的列语义归各自模块，本节只列 M007 直接拥有的结构。

**6.7.1 `schema_meta`（数据库表结构）**

```sql
CREATE TABLE schema_meta (
  singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
  schema_version INTEGER NOT NULL,
  initialized_at TEXT NOT NULL
);
```

- **Data/Type ID、用途与来源**：

  `D-UTIL-SCHEMA-META`；库初始化的单行版本哨兵；authority `util/migrations/001_initial.sql`。

- **`singleton`**：

  非空主键，恒 `1`；保证单行。

- **`schema_version`**：

  NOT NULL 整数；与 §6.1.1 `SchemaVersion.value` 精确比对。

- **`initialized_at`**：

  NOT NULL 文本时间；初始化时刻。

- **跨字段与寿命**：

  恒单行；有业务表却无本表 → `ERR-SCHEMA`（旧库未知版本）；库寿命，只由 `_initialize` 写一次。

- **合法/拒绝实例**：

  合法：空库初始化写入 `schema_version=2`；拒绝：非空库无 `schema_meta` → 拒绝启动。

- **验证**：

  `VRC-UTIL-002`；authority `util/migrations/001_initial.sql`。

**6.7.2 `migrations/*.sql`（数据库表结构）**

```text
migrations/*.sql {
  files: ordered SQL[]   // 001_initial.sql, 002_observability.sql, ...
}
```

- **Data/Type ID、用途与来源**：

  `D-UTIL-MIGRATIONS`；按文件名排序、逐语句执行的 DDL/数据迁移集合；authority `util/migrations/*.sql`。

- **`files`**：

  必填有序集合；`001_initial.sql`（`schema_meta`/providers/deployments/service_levels/…/operational_logs）、`002_observability.sql`（`diagnostic_settings`/`diagnostic_snapshots`/`data_plane_stats`/`data_plane_latency_samples`/`diagnostic_injections`/`trace_events`）。其中 `provider_request_bindings` 含可空列 `provider_request_id TEXT`（上游 provider request id，语义归 M-METER，由 M003 在 `complete()` 成功后回填）。

- **跨字段与寿命**：

  幂等（`IF NOT EXISTS`/`INSERT OR IGNORE`）；原子初始化单事务；注释行剥离后逐语句执行；随仓库，`migrate()` 每次启动执行。

- **合法/拒绝实例**：

  合法：连续两次 `migrate()` 成功且不改变已建表；拒绝：`PRAGMA integrity_check != ok` → 抛错。

- **验证**：

  `VRC-UTIL-002`；authority `util/migrations/*.sql`。

### 6.8 错误码与错误结构

本模块**不新增公共错误码**；对外错误引用系统目录（`llmtier-system-design` §8.8）：

| 本层错误 | 条件 | 系统 Error ID | 合法下一步 |
|---|---|---|---|
| `ApiError(503,"store_path_unsafe")` | DB 路径为 symlink | `ERR-PATH-UNSAFE` | 修正路径后重启 |
| `ApiError(503,"schema_unknown")` | 非空库无 `schema_meta` | `ERR-SCHEMA` | 运维离线处理 |
| `ApiError(503,"schema_version_mismatch")` | 版本不等于期望 | `ERR-SCHEMA` | 运维离线处理 |
| `ApiError(503,"schema_integrity_failed")` | `integrity_check` 失败 | `ERR-SCHEMA` | 运维离线处理 |
| 原生 `sqlite3.Error` | 连接/读写异常 | `ERR-STORE` | 调用方按接口边界处理 |

- **约束 / 不变量**：M007 只抛出上述 typed/原生错误；不伪造空页；上层负责映射。
- **实例**：拒绝：symlink 路径 → `ERR-PATH-UNSAFE`；边界：世界可写文件只 `RuntimeWarning`，不报错。
- **来源 / 验证**：`store.py` + 系统 §8.8；`VRC-UTIL-001/002`。

## 7. 主流程与数据流

**内部流程正文**：启动时 `Store.migrate` 建表并完整性检查；请求内业务模块经 `store.connection()`（线程内复用）执行读写；写路径用 `store.transaction(immediate=True)` 原子提交/回滚；请求结束 `app.store.close()` 释放线程连接。

#### 7.1 `P-UTIL-MIGRATE` · 迁移
- **触发/适用条件**：启动
- **图与正文位置**：§5.1.3
- **正常出口**：表就绪
- **异常出口**：`ApiError(503,"schema_integrity_failed")`（integrity）；`schema_unknown`/`schema_version_mismatch`（库状态）

#### 7.2 `P-UTIL-TXN` · 事务
- **触发/适用条件**：任意写
- **图与正文位置**：§5.2.1
- **正常出口**：commit
- **异常出口**：rollback + 重抛

#### 7.3 `P-UTIL-CLOSE` · 连接关闭
- **触发/适用条件**：请求 `finally`
- **图与正文位置**：§5.1.1
- **正常出口**：fd 释放
- **异常出口**：向上抛（**不吞异常**）

## 8. 关键算法与业务规则

#### 8.1 `RULE-UTIL-PRAGMA` · 连接初始化
- **输入前提 / 适用条件**：首次取连接
- **算法 / 规则 / 选择依据**：`timeout=10`、`isolation_level=None`、`row_factory=Row`、`foreign_keys=ON`、`journal_mode=WAL`
- **结果 / 不变量 / 边界**：外键开启、WAL
- **复杂度 / 资源限制**：O(1)
- **允许替换范围 / 不可改变保证**：实现可自选；外键/WAL 语义不可变
- **具体输入推演 / 验证项**：`PRAGMA foreign_keys` = 1；`VRC-UTIL-001`

#### 8.2 `RULE-UTIL-TXN` · 事务原子性
- **输入前提 / 适用条件**：写
- **算法 / 规则 / 选择依据**：`BEGIN IMMEDIATE`；异常 rollback
- **结果 / 不变量 / 边界**：失败不改变库
- **复杂度 / 资源限制**：—
- **允许替换范围 / 不可改变保证**：实现可自选；原子性不可变
- **具体输入推演 / 验证项**：中途异常 → 无半写；`VRC-UTIL-002`

#### 8.3 `RULE-UTIL-MIGRATE` · 迁移幂等
- **输入前提 / 适用条件**：重复启动
- **算法 / 规则 / 选择依据**：SQL 用 `IF NOT EXISTS`/`INSERT OR IGNORE`
- **结果 / 不变量 / 边界**：重复执行不报错、不改变已建表
- **复杂度 / 资源限制**：O(文件数)
- **允许替换范围 / 不可改变保证**：实现可自选；幂等不可变
- **具体输入推演 / 验证项**：连续两次 migrate 成功；`VRC-UTIL-002`

#### 8.4 `RULE-UTIL-FD` · 连接回收
- **输入前提 / 适用条件**：请求结束/停机
- **算法 / 规则 / 选择依据**：`close()` 关闭线程连接并置 None
- **结果 / 不变量 / 边界**：每请求 fd 不泄漏（macOS 256 上限）
- **复杂度 / 资源限制**：O(1)
- **允许替换范围 / 不可改变保证**：实现可自选；不泄漏不可变
- **具体输入推演 / 验证项**：压测 fd 稳定；`VRC-UTIL-001`

## 9. 接口设计

> 按 STD `design-data-interface-format` 1.2.0 §3：主章“接口设计”，按**接口设计用途**分类（面向使用方的 API 与组件/系统间协作的消息与数据流接口），逐接口完整记录；标题为真实调用形式，标题下先给**完整接口声明**，再就地说明参数/结果字段，最后按固定六项。本模块接口全部为进程内方法调用，归 API；消息流/硬件/人机三类不适用。数据结构引用 §6。`Store`（`src/util/store.py`）为唯一对外面。

### 9.1 API（适用时）

#### `Store(path) -> Store`

```text
Store(path: str | Path) -> Store
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-UTIL-CONN`；构造存储句柄并做路径安全预检；M007 `util` 提供；状态=Implemented；唯一契约=本设计；文件·symbol `src/util/store.py` `Store.__init__` / `_precheck`。
- **输入与前提**：`path`（SQLite 文件路径）；构造前做 symlink/权限预检。
- **成功输出与保证**：`Store` 实例（§6.6.1）；构造即建父目录，不建连接（首次 `connection()` 建）。
- **错误与合法下一步**：路径为 symlink → `ApiError(503,"store_path_unsafe")`（`ERR-PATH-UNSAFE`）；世界可写 → `RuntimeWarning`（不失败）。
- **交互与生命周期**：同步；调用方线程；随进程存活。
- **实现与验证**：正常建 Store；拒绝 symlink → 503。`VRC-UTIL-001`；`src/util/store.py`。

#### `Store.connection() -> sqlite3.Connection`

```text
connection() -> sqlite3.Connection
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-UTIL-CONN`；取得当前线程连接；M007 提供；状态=Implemented；唯一契约=本设计；文件·symbol `store.py` `Store.connection`。
- **输入与前提**：无。
- **成功输出与保证**：当前线程缓存的连接——`timeout=10`、`isolation_level=None`、`row_factory=Row`、`PRAGMA foreign_keys=ON`、`journal_mode=WAL`。
- **错误与合法下一步**：连接失败 → 原生 `sqlite3.Error`（`ERR-STORE`）；调用方按接口边界处理。
- **交互与生命周期**：同步；线程内复用；所有权归 `Store`，由 `close()` 释放。
- **实现与验证**：正常：同线程两次调用返回同一连接；边界：`PRAGMA foreign_keys`=1。`VRC-UTIL-001`；`store.py`。

#### `Store.migrate() -> None`

```text
migrate() -> None
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-UTIL-MIGRATE`；初始化/校验库 schema；M007 提供；状态=Implemented；唯一契约=本设计；文件·symbol `store.py` `Store.migrate` / `_initialize`。
- **输入与前提**：无（读取 `migrations/*.sql`）。
- **成功输出与保证**：无返回——空库建立全部表；已有库校验版本与完整性。
- **错误与合法下一步**：无 `schema_meta` 的非空库 → `ApiError(503,"schema_unknown")`；版本不符 → `ApiError(503,"schema_version_mismatch")`；完整性失败 → `ApiError(503,"schema_integrity_failed")`（均 `ERR-SCHEMA`）；运维离线处理，不改库。
- **交互与生命周期**：启动时调用；单事务原子初始化；异常回滚。
- **实现与验证**：正常：空库建表；重复启动 no-op；拒绝：未知旧库 → 503。`VRC-UTIL-002`；`store.py`。

#### `Store.transaction(immediate=False) -> ContextManager` / `txn(store, conn=None) -> ContextManager`

```text
transaction(immediate: bool = False) -> ContextManager[sqlite3.Connection]
txn(store: Store, conn: Connection | None = None) -> ContextManager[sqlite3.Connection]
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-UTIL-TXN`；开启事务并在退出时提交/回滚；M007 提供；状态=Implemented；唯一契约=本设计；文件·symbol `store.py` `Store.transaction` / `txn`。
- **输入与前提**：`immediate`（`true` → `BEGIN IMMEDIATE`）；`txn` 的 `conn`（传入则并入调用方事务，不提交）。
- **成功输出与保证**：上下文内可用连接；退出 `commit`，异常 `rollback` 并重抛。
- **错误与合法下一步**：SQL/约束错误 → rollback 后原生异常冒泡（`ERR-STORE`/由调用方映射）；不产生半写。
- **交互与生命周期**：同步；写路径 `immediate=True` 串行化；`conn` 非空时不拥有事务。
- **实现与验证**：正常：中途异常 → 无半写；边界：嵌套 `txn(conn)` 不二次开事务。`VRC-UTIL-002`；`store.py`。

#### `Store.one(sql, params=()) -> sqlite3.Row | None`

```text
one(sql: str, params: Sequence[object] = ()) -> sqlite3.Row | None
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-UTIL-QUERY`；单行查询；M007 提供；状态=Implemented；唯一契约=本设计；文件·symbol `store.py` `Store.one`。
- **输入与前提**：`sql`、`params`。
- **成功输出与保证**：首行 `Row` 或 `None`。
- **错误与合法下一步**：SQL 错误 → 原生 `sqlite3.Error`（`ERR-STORE`）；调用方处理。
- **交互与生命周期**：同步只读；无事务保证（随调用方）。
- **实现与验证**：正常：命中返回 Row；边界：无行 → `None`。`VRC-UTIL-002`；`store.py`。

#### `Store.all(sql, params=()) -> list[sqlite3.Row]`

```text
all(sql: str, params: Sequence[object] = ()) -> list[sqlite3.Row]
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-UTIL-QUERY`；多行查询；M007 提供；状态=Implemented；唯一契约=本设计；文件·symbol `store.py` `Store.all`。
- **输入与前提**：`sql`、`params`。
- **成功输出与保证**：全部行列表。
- **错误与合法下一步**：SQL 错误 → 原生 `sqlite3.Error`（`ERR-STORE`）。
- **交互与生命周期**：同步只读。
- **实现与验证**：正常：返回行列表；边界：无行 → `[]`。`VRC-UTIL-002`；`store.py`。

#### `Store.close() -> None`

```text
close() -> None
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-UTIL-CLOSE`；释放当前线程连接；M007 提供；状态=Implemented；唯一契约=本设计；文件·symbol `store.py` `Store.close`。
- **输入与前提**：无。
- **成功输出与保证**：无返回——关闭当前线程连接并置缓存 `None`。
- **错误与合法下一步**：关闭失败**向上抛**（`Store` 不吞异常），由调用方/宿主兜底处理。
- **交互与生命周期**：每请求 `finally`/停机调用；幂等（无连接时不动作）。
- **实现与验证**：正常：请求后 fd 释放；边界：重复 `close()` 无副作用。`VRC-UTIL-001`；`store.py`。

### 9.2 消息与数据流接口（适用时）

不适用（同步函数调用，不拥有事件/队列/流/file exchange；tailoring：M007 只提供进程内存取原语）。

### 9.3 硬件与固件接口（适用时）

不适用（无连接器/总线/寄存器/FPGA 端口）。

### 9.4 人机与维护接口（适用时）

不适用（无 UI/CLI；存取由业务模块在进程内调用、端点归 M001）。

## 10. 并发、失败与恢复

#### 10.1 `F-UTIL-CONN` · 连接失败
- **初始条件 / 并发交错 / 失败点**：库不可写/损坏
- **检测事实 / authority / 期限**：sqlite3 异常 / integrity check
- **处理行为 / 副作用边界**：异常冒泡；调用方 503/启动失败
- **状态查询 / 同请求重放 / 接管 / 新业务重试**：稍后重试
- **最终状态 / 资源归属 / 后续合法入口**：503/启动失败
- **验证项 / 组合责任**：`VRC-UTIL-001`

#### 10.2 `F-UTIL-TXN` · 事务失败
- **初始条件 / 并发交错 / 失败点**：SQL 错误/约束冲突
- **检测事实 / authority / 期限**：异常
- **处理行为 / 副作用边界**：rollback
- **状态查询 / 同请求重放 / 接管 / 新业务重试**：由调用方决定
- **最终状态 / 资源归属 / 后续合法入口**：库不变
- **验证项 / 组合责任**：`VRC-UTIL-002`

#### 10.3 `F-UTIL-FD` · 连接泄漏
- **初始条件 / 并发交错 / 失败点**：请求未关闭连接
- **检测事实 / authority / 期限**：fd 增长
- **处理行为 / 副作用边界**：`finally: app.store.close()`
- **状态查询 / 同请求重放 / 接管 / 新业务重试**：—
- **最终状态 / 资源归属 / 后续合法入口**：fd 稳定
- **验证项 / 组合责任**：`VRC-UTIL-001`

## 11. 安全、权限与可观测性

- **权限**：不鉴权（基础层）
- **Secret**：M007 不解析 Secret，只存引用字符串（语义在 M004）
- **可观测**：本模块不写观测/日志（避免基础层反向依赖）；由调用方记录

## 12. 容量、性能与运行限制

#### 12.1 `CAP-UTIL-CONN` · 连接与 fd
- **目标 / 限制 / 单位**：每线程 1 连接；每请求关闭
- **适用版本 / 配置 / 硬件 / 虚拟化 / 依赖**：`threading.local`
- **负载、数据规模与并发口径**：并发请求
- **推导 / 测量方法与证据等级**：Measured（连接泄漏修复）
- **共享资源扣减 / 峰值重叠 / 余量**：macOS 256 fd
- **超限行为 / 责任出口**：连接泄漏风险 → `close()` 兜底
- **验证项 / Evidence**：`VRC-UTIL-001`；NOT_RUN

#### 12.2 `CAP-UTIL-TXN` · 写串行化
- **目标 / 限制 / 单位**：`BEGIN IMMEDIATE` 串行写
- **适用版本 / 配置 / 硬件 / 虚拟化 / 依赖**：WAL
- **负载、数据规模与并发口径**：并发写
- **推导 / 测量方法与证据等级**：Specified
- **共享资源扣减 / 峰值重叠 / 余量**：`timeout=10`
- **超限行为 / 责任出口**：锁超时 → 异常
- **验证项 / Evidence**：`VRC-UTIL-002`；NOT_RUN

## 13. 实现步骤与文件清单

### 13.1 文件分解（设计 → 代码文件）

#### 13.1.1 `src/util/store.py`
- **职责 / 非职责**：I1–I4 连接/事务/迁移/查询；不含业务语义
- **关键 symbol / 导出范围**：`Store.connection/migrate/transaction/one/all/close`
- **承接 Function / Rule / Constraint / Interface ID**：`F-UTIL-*`、`RULE-UTIL-*`、`C-CFG-1/3`、`IF-UTIL-STORE`
- **构建目标 / 依赖 / 宿主装配**：标准库 `sqlite3`；随 `Application` 构造
- **实现状态**：Implemented
- **验证入口**：`VRC-UTIL-001/002`

#### 13.1.2 `src/util/migrations/001_initial.sql` / `002_observability.sql`
- **职责 / 非职责**：建表（配置/账本/审计/日志/观测）；不含业务逻辑
- **关键 symbol / 导出范围**：全部表
- **承接 Function / Rule / Constraint / Interface ID**：`R-OBS-06`；各业务模块的表契约
- **构建目标 / 依赖 / 宿主装配**：由 `Store.migrate` 执行
- **实现状态**：Implemented
- **验证入口**：`VRC-UTIL-002`

#### 13.1.3 `config/settings.json`
- **职责 / 非职责**：空库首次 bootstrap 输入；不是运行期权威
- **关键 symbol / 导出范围**：providers/deployments/service_levels
- **承接 Function / Rule / Constraint / Interface ID**：`C-CFG-1`（输入）
- **构建目标 / 依赖 / 宿主装配**：路径经启动参数
- **实现状态**：Implemented
- **验证入口**：M004 `VRC-MGMT-001`

### 13.2 实现步骤

#### 13.2.1 连接与 PRAGMA
- **前置输入 / 依赖**：库路径
- **新增 / 修改文件与 symbol**：`store.py` `connection/close`
- **固定语义 / 可自行决定范围**：外键/WAL 固定；实现可自选
- **交付结果**：线程内连接
- **完成检查**：`VRC-UTIL-001`

#### 13.2.2 事务与查询
- **前置输入 / 依赖**：连接
- **新增 / 修改文件与 symbol**：`store.py` `transaction/one/all`
- **固定语义 / 可自行决定范围**：原子性固定；实现可自选
- **交付结果**：事务/查询
- **完成检查**：`VRC-UTIL-002`

#### 13.2.3 迁移
- **前置输入 / 依赖**：`migrations/*.sql`
- **新增 / 修改文件与 symbol**：`store.py` `migrate`
- **固定语义 / 可自行决定范围**：幂等固定；实现可自选
- **交付结果**：表就绪
- **完成检查**：`VRC-UTIL-002`

## 14. 测试与验收

#### 14.1 `VRC-UTIL-001` · 连接与回收
- **覆盖 Function / Rule / Constraint / Interface**：`F-UTIL-CONN/CLOSE`、`RULE-UTIL-PRAGMA/FD`、`C-CFG-1`、`IF-UTIL-STORE`
- **Case / 正常、边界与失败输入**：并发请求；`finally` 关闭
- **环境 / 配置 / 隔离与复位**：隔离库
- **独立 Oracle / Expected**：外键=1；fd 稳定
- **Actual / Evidence / Run ID**：NOT_RUN
- **Verdict / 状态**：NOT_RUN
- **父级组合验证交接**：M001

#### 14.2 `VRC-UTIL-002` · 事务与迁移
- **覆盖 Function / Rule / Constraint / Interface**：`F-UTIL-TXN/MIGRATE`、`RULE-UTIL-TXN/MIGRATE`、`C-CFG-3`
- **Case**：中途异常回滚；重复迁移
- **环境 / 配置 / 隔离与复位**：隔离库
- **独立 Oracle / Expected**：无半写；幂等
- **Actual / Evidence / Run ID**：NOT_RUN
- **Verdict / 状态**：NOT_RUN
- **父级组合验证交接**：M004/M-METER/M-OBS

## 15. 风险、未决问题与引用

#### 15.ISD · 实现规格采用方式
- **采用模式**：`separate`（模块设计不兼作 ISD）
- **模块对象 ID**：M007
- **实现规格 Document ID**：`util-isd`
- **metadata 覆盖映射入口**：`util-isd` 的 `implementation_specification.coverage_mapping`
- **理由 / 决定引用**：本文已含文件/符号/语义/验证

#### 15.1 `RISK-UTIL-1` · 单文件 SQLite 的写串行
- **类型 / 影响的规则、接口、流程或约束**：Risk；影响 `F-UTIL-TXN`
- **事实缺口 / 触发条件**：高并发写
- **影响 / 阻塞边界**：写排队/锁超时
- **Owner / 最晚关闭 Gate**：LLMTier / 实测
- **选项 / 推荐 / 下一步取证**：WAL + `BEGIN IMMEDIATE`；实测调参
- **关闭条件 / 决定或当前状态**：观察

引用：系统设计 §3.2/§10；机制 M-CONFIG §14.4（`R-CFG-03`）、M-OBS §14.4（`R-OBS-06`）；`src/util/store.py`、`migrations/`。

## 附录 A. 机制承接表

#### A.1 `llmtier-config-lifecycle-mechanism` / `R-CFG-03` · 存储事务
- **来源 Capability / Step / Constraint / 接口成员**：Step 1/4、interface `transaction`
- **本模块必须负责的行为与保证**：原子事务与版本
- **本模块提供 / 消费的接口**：`Store.transaction`
- **本文落实位置**：§5.1.2、§8.2、§9.1
- **代码文件 / symbol 或 NOT_IMPLEMENTED**：`store.py`
- **允许自行决定的范围**：存储实现
- **本地验证 / 组合验证交接**：`VRC-UTIL-002`

#### A.2 `llmtier-observability-mechanism` / `R-OBS-06` · 观测表存储
- **来源 Capability / Step / Constraint / 接口成员**：§8 6 张表
- **本模块必须负责的行为与保证**：6 张表的持久化与事务
- **本模块提供 / 消费的接口**：`Store`
- **本文落实位置**：§6.7、§13.1.2
- **代码文件 / symbol 或 NOT_IMPLEMENTED**：`migrations/002_observability.sql`
- **允许自行决定的范围**：表结构实现
- **本地验证 / 组合验证交接**：`VRC-UTIL-002`；M006
