<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier M007 util 实现规格设计（ISD）

> STD 使用入口：[项目采用说明与标准导航](../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `util-isd` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Document Owner | LLMTier |
| Last Modified Date | `2026-09-23` |
| Template ID | `design.implementation` |
| Template Version | `0.2.1` |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 实现目标与输入基线

<a id="isd-scope"></a>

本 ISD 把 **M007 util**（模块设计 `util`，`0.1.0-draft.1`）落实到 `src/llmtier_v03/store.py` 与 `migrations/*.sql`：SQLite 线程内连接、迁移与完整性检查、事务、只读查询、连接关闭。本次范围是"唯一持久化的存取层"；**非目标**：业务语义（配置/账本/审计/日志/观测由各模块维护）、连接池、迁移框架、ORM。代表输入：库路径；代表输出：`sqlite3.Connection` 与行。

**模块与来源**
- **模块设计 Document ID / 版本 / 路径 / 摘要**：`util` / `0.1.0-draft.1` / `docs/40_module_design/util-design.md` / `§2 F-UTIL-CONN/MIGRATE/TXN/QUERY/CLOSE`、`§8 RULE-UTIL-PRAGMA/TXN/MIGRATE/FD`
- **直属父对象 / 父设计**：LLMTier 软件系统 / `llmtier-system-design`（§3.2 登记）
- **需求与 Constraint ID**：`C-CFG-1`（唯一持久化）、`C-CFG-3`（原子推进）、机制 `R-CFG-03`、`R-OBS-06`
- **实现范围 / 非目标**：实现 `Store`；不做业务规则、不直连外部、不定义表语义

<a id="isd-handoff"></a>

**承接矩阵（上游 → 本 ISD 细化）**

#### 1.1 `F-UTIL-CONN` / `RULE-UTIL-PRAGMA` · 连接与 PRAGMA
- **固定来源**：`util` / `0.1.0-draft.1` / `#5.1.1`
- **ISD 细化内容 / 章节**：`connection()` 的 `threading.local` 缓存与 PRAGMA
- **唯一权威位置**：行为在模块 §2.1 / §8.1；ISD 管实现
- **实现自由度**：缓存结构可自选
- **原 V/Case 及本地验证位置**：`VRC-UTIL-001` → §8

#### 1.2 `F-UTIL-TXN` / `RULE-UTIL-TXN` · 事务
- **固定来源**：`util` / `0.1.0-draft.1` / `#5.1.2`
- **ISD 细化内容 / 章节**：`transaction()` 的 `BEGIN [IMMEDIATE]` / commit / rollback
- **唯一权威位置**：行为在模块 §2.3 / §8.2；ISD 管实现
- **实现自由度**：实现可自选
- **原 V/Case 及本地验证位置**：`VRC-UTIL-002` → §8

#### 1.3 `F-UTIL-MIGRATE` / `RULE-UTIL-MIGRATE` · 迁移
- **固定来源**：`util` / `0.1.0-draft.1` / `#5.1.3`
- **ISD 细化内容 / 章节**：迁移/初始化文件枚举、`executescript`、`integrity_check`、**仅初始化 + 版本拒绝**
- **唯一权威位置**：行为在模块 §2.2 / §8.3；ISD 管实现
- **实现自由度**：实现可自选
- **原 V/Case 及本地验证位置**：`VRC-UTIL-002` → §8

#### 1.4 `F-UTIL-QUERY` · 查询 helper
- **固定来源**：`util` / `0.1.0-draft.1` / `#5.1.4`
- **ISD 细化内容 / 章节**：`one()` / `all()` 与 `Row` 工厂
- **唯一权威位置**：行为在模块 §2.4；ISD 管实现
- **实现自由度**：实现可自选
- **原 V/Case 及本地验证位置**：`VRC-UTIL-002` → §8

#### 1.5 `F-UTIL-CLOSE` / `RULE-UTIL-FD` · 连接关闭
- **固定来源**：`util` / `0.1.0-draft.1` / `#5.1.1`
- **ISD 细化内容 / 章节**：`close()` 清空线程连接
- **唯一权威位置**：行为在模块 §2.5 / §8.4；ISD 管实现
- **实现自由度**：实现可自选
- **原 V/Case 及本地验证位置**：`VRC-UTIL-001` → §8

#### 1.6 `R-OBS-06` · 观测表存储
- **固定来源**：机制 `M-OBS` §14.4 `R-OBS-06`（Store·4 张观测表）；表契约见 M006 §6 / M007 附录 A
- **ISD 细化内容 / 章节**：`002_observability.sql` 的表与列由 `migrate` 执行
- **唯一权威位置**：表契约在 M006/M007；ISD 管 DDL 落点
- **实现自由度**：DDL 可自选
- **原 V/Case 及本地验证位置**：`VRC-UTIL-002` → §8

## 2. 文件、内部组件与调用关系

<a id="isd-structure"></a>

```text
python 标准库 sqlite3
 ├─ store.py
 │    └─ class Store
 │         ├─ __init__(path)              # 建父目录；threading.local
 │         ├─ connection() -> Connection  # 线程内缓存 + PRAGMA
 │         ├─ migrate()                   # 执行 migrations/*.sql + integrity_check
 │         ├─ transaction(immediate)      # 上下文管理器：BEGIN/commit/rollback
 │         ├─ one(sql, params) -> Row|None
 │         ├─ all(sql, params) -> [Row]
 │         └─ close()                     # 关闭线程连接
 └─ migrations/
      ├─ 001_initial.sql
      └─ 002_observability.sql
```

#### 2.1 `store.py` · `Store`
- **职责 / 调用者**：连接/迁移/事务/查询；被全部业务模块调用
- **类型 / 函数**：`Store.connection/migrate/transaction/one/all/close`
- **可见性 / 构建目标**：模块私有 API；由宿主在装配阶段构造
- **依赖**：`sqlite3`、`threading`、`contextlib`、`pathlib`

#### 2.2 `migrations/*.sql`
- **职责 / 调用者**：DDL；由 `migrate()` 执行
- **类型 / 函数**：SQL 脚本
- **可见性 / 构建目标**：数据文件，随包
- **依赖**：—
- **权威边界**：DDL 是**跨模块内部契约**，业务模块按列名/插入顺序依赖；本层不得自由更改，见 §2.3 表契约。

#### 2.3 表契约（跨模块内部权威）

DDL 是跨模块内部契约；本层是 schema 的**唯一落点**，改动须评估下列受影响模块。

| 表 | Schema authority | Writer / Reader | 键 / 约束 | 保留 / 删除规则 | 变更受影响模块 |
|---|---|---|---|---|---|
| `schema_meta` | 本 ISD | 启动写；`migrate` 读 | `singleton=1` | 不删 | bootstrap（M004）|
| `providers` / `deployments` / `service_levels` / `service_level_deployments` | 本 ISD | M004 写；M003/M005 读 | 见 `001_initial.sql`；name 唯一 | 删除受引用保护（M004）| M004/M003 |
| `usage_*`（obligations/record_versions/heads）、`provider_request_bindings` | 本 ISD | M003/M004 写；M004 读 | `(principal_id,request_id[,version])` | 只追加；清空由 M004 | M003/M004 |
| `audit_events` / `operational_logs` | 本 ISD | M004/M008 写；M004 读 | 只追加 | 保留期由运维 | M004/M008 |
| 观测 4 表（`diagnostic_*`、`trace_events`、`data_plane_stats`）| 本 ISD（契约见 M006 §6）| M006 写；M005 读 | 见 `002_observability.sql` | 7 天清理（M006）| M005/M006 |
| `query_snapshots` / `query_snapshot_items` | 本 ISD | M004 写/读 | TTL 10 分钟 | 到期由查询拒绝 | M004 |

## 3. 内部数据与所有权

<a id="isd-data"></a>

以下为**纯软件**实现，无 ABI/位宽/对齐/端序（不适用，依据：Python `sqlite3`，无二进制 wire）。

#### 3.1 `Store`（私有类）
- **字段**：`path: str`（SQLite 文件路径）；`_local: threading.local`
- **初值 / 约束**：`path` 只读；父目录在 `__init__` 创建
- **创建 / 修改者**：宿主装配阶段创建
- **借用期限 / 释放者**：进程级；`close()` 释放线程连接
- **公共类型来源**：—（模块私有）

#### 3.2 `sqlite3.Connection`（线程局部）
- **字段**：由 `sqlite3.connect(path, timeout=10, isolation_level=None)` 产生；`row_factory = sqlite3.Row`
- **初值 / 约束**：每线程一个；`PRAGMA foreign_keys=ON`、`journal_mode=WAL`
- **创建 / 修改者**：`connection()` 首次调用创建并缓存
- **借用期限 / 释放者**：线程寿命；`close()` 置 `None`
- **公共类型来源**：标准库

#### 3.3 `sqlite3.Row`
- **字段**：按列名访问
- **初值 / 约束**：只读
- **创建 / 修改者**：查询产生
- **借用期限 / 释放者**：`Row` 已物化，可在连接关闭后读取；调用方持有
- **公共类型来源**：标准库

#### 3.4 SQLite 表结构（DDL，本层权威）

编码以本表为权威；`migrations/001_initial.sql`、`002_observability.sql` 是它的编码（列/约束不得偏离）。

**基础表（`001_initial.sql`）**

| 表 | 列（类型 / 约束）|
|---|---|
| `schema_meta` | `singleton` INTEGER PK CHECK=1；`schema_version` INTEGER NOT NULL；`initialized_at` TEXT NOT NULL；`bootstrap_sha256` TEXT |
| `providers` | `id` TEXT PK；`name` TEXT UNIQUE NOT NULL；`kind` TEXT CHECK IN(cloud,local)；`endpoint` TEXT；`secret_ref` TEXT；`enabled` INTEGER；`version` INTEGER |
| `deployments` | `id` PK；`name` UNIQUE；`provider_id` FK→providers；`backend_model`；`capabilities_json`；`enabled`；`health` DEFAULT 'unknown'；`version` |
| `service_levels` | `id` PK；`enabled`；`capabilities_json`；`version` |
| `service_level_deployments` | `level_id` FK ON DELETE CASCADE；`deployment_id` FK；`ordinal`；PK(level_id,deployment_id)；UNIQUE(level_id,ordinal) |
| `deployment_runtime_profiles` | `deployment_id` PK FK CASCADE；`max_in_flight` DEFAULT 1；`connect_timeout_ms` DEFAULT 30000；`stream_idle_timeout_ms` DEFAULT 60000；`version` |
| `provider_usage_profiles` | `provider_id` PK FK CASCADE；`usage_provider` DEFAULT 'none'；`usage_api_key_ref`/`usage_access_key_ref`/`usage_secret_key_ref`；`max_concurrent_requests` DEFAULT 1；`min_request_interval_ms` DEFAULT 0；`requests_per_minute` DEFAULT 0；`version` |
| `provider_usage_snapshots` | `provider_id` PK FK CASCADE；`snapshot_json`；`checked_at` |
| `provider_request_bindings` | `principal_id`；`request_id`；`provider_id` FK；`deployment_id` FK；`bound_at`；PK(principal_id,request_id) |
| `usage_obligations` | `principal_id`；`request_id`；`model`；`endpoint`；`recorded_at`；`dispatch_authorized_at`；PK(principal_id,request_id) |
| `usage_record_versions` | `principal_id`；`request_id`；`record_version`；`is_final`；`model`；`endpoint`；`recorded_at`；`updated_at`；`measurement_status`；`source`；`input_tokens`；`output_tokens`；`total_tokens`；`cached_input_tokens`；`cache_write_tokens`；`reasoning_tokens`；PK(principal_id,request_id,record_version)；FK→`usage_obligations` |
| `usage_heads` | `principal_id`；`request_id`；`head_record_version`；`updated_at`；PK(principal_id,request_id)；FK→`usage_record_versions` |
| `query_snapshots` | `snapshot_id` PK；`principal_id`；`snapshot_kind`；`filter_digest`；`authorization_digest`；`created_at`；`expires_at` |
| `query_snapshot_items` | `snapshot_id` FK CASCADE；`ordinal`；`request_id`；`record_version`；`frozen_view_json`；`etag`；PK(snapshot_id,ordinal)；UNIQUE(snapshot_id,request_id) |
| `probe_results` | `deployment_id` PK FK CASCADE；`status`；`checked_at`；`request_id`；`detail` |
| `audit_events` | `id` PK；`actor`；`action`；`target`；`result`；`created_at`；`request_id` |
| `operational_logs` | `id` PK；`created_at`；`level`；`module`；`event`；`message` CHECK(length≤512)；`request_id` |

**观测表（`002_observability.sql`）**

| 表 | 列（类型 / 约束）|
|---|---|
| `diagnostic_settings` | `singleton` PK CHECK=1；`snapshots_enabled` DEFAULT 0；`stats_enabled` DEFAULT 0 |
| `diagnostic_snapshots` | `id` PK；`request_id`；`captured_at`；`upstream_url`；`backend_model`；`http_status`；`latency_ms`；`error_summary`；`model`；`deployment_id`；`snapshot_type` DEFAULT 'upstream' |
| `diagnostic_injections` | `id` PK；`deployment_id`；`injection_type`；`fault_status`；`fault_body`；`delay_ms`；`retry_after_sec`；`stream_terminate_after_events`；`malformed_after_events`；`malformed_event_type`；`enabled` DEFAULT 0；`updated_at`；UNIQUE(deployment_id,injection_type) |
| `data_plane_stats` | `stat_hour`；`deployment_id`；`model`；`status`；`request_count` DEFAULT 0；`error_count` DEFAULT 0；`updated_at`；PK(stat_hour,deployment_id,model,status) |
| `data_plane_latency_samples` | `stat_hour`；`deployment_id`；`model`；`latency_ms` NOT NULL；`created_at` |
| `trace_events` | `id` PK；`request_id`；`stage`；`stage_timestamp`；`detail`；`correlation_id`；`created_at` |

**初始化行**：`INSERT OR IGNORE schema_meta(1,1,...)`；`provider_usage_profiles` 对每个 provider 补默认（`local`→`local`，否则 `none`）。

**所有权图**

```text
宿主持有 Store（进程级）
  Store._local 每线程持有一个 Connection
    查询返回 Row（借用该连接；调用方消费后不保留）
  请求 finally → Store.close() → 丢弃线程 Connection
```

## 4. 函数与接口实现规格

<a id="isd-functions"></a>

#### 4.1 `Store.__init__(self, path: str | Path) -> None`
- **前置条件**：`path` 可写；父目录存在或可创建
- **行为**：`Path(path).parent.mkdir(parents=True, exist_ok=True)`；`self._local = threading.local()`
- **返回**：None
- **错误**：目录不可创建 → `OSError`（冒泡）
- **副作用**：创建父目录
- **幂等**：可重复构造不同 `Store`
- **所有权**：`path` 保存为 `str`；`_local` 归实例
- **不可改变**：父目录自动创建
- **可自行决定**：目录创建实现

#### 4.2 `Store.connection(self) -> sqlite3.Connection`
- **前置条件**：—
- **行为**：取 `getattr(self._local,"connection",None)`；为 `None` 时 `sqlite3.connect(self.path, timeout=10, isolation_level=None)`，设 `row_factory=Row` 并执行 PRAGMA，缓存回 `_local`
- **返回**：线程内 `Connection`
- **错误**：连接失败 → `sqlite3.Error`（冒泡）
- **副作用**：可能新建连接并在同一连接执行 PRAGMA
- **幂等**：同线程多次调用返回同一对象
- **所有权**：连接归线程；调用方**不得**关闭（由 `close()` 统一）
- **不可改变**：`timeout=10`、`isolation_level=None`、`row_factory=Row`、`foreign_keys=ON`、`journal_mode=WAL`
- **可自行决定**：PRAGMA 执行时机/方式

#### 4.3 `Store.migrate(self) -> None`
- **常量**：`EXPECTED_SCHEMA_VERSION = 1`（模块级）
- **前置条件**：`store.py` 同目录存在 `migrations/`
- **行为**（**仅初始化 + 版本拒绝**）：
  1. 读 `schema_meta.schema_version`；若库非空且 `≠ EXPECTED_SCHEMA_VERSION` → 抛 `ApiError(503, "schema_version_mismatch")`（拒绝启动，见 §6.2）
  2. `for f in sorted(migrations.glob("*.sql")): connection().executescript(f.read_text())`
  3. `PRAGMA integrity_check`；`≠ "ok"` → 抛 `ApiError(503, "schema_integrity_failed")`
- **返回**：None
- **错误**：版本不符 → `schema_version_mismatch`；完整性失败 → `schema_integrity_failed`
- **副作用**：建表（幂等 DDL）
- **幂等**：脚本使用 `IF NOT EXISTS`/`INSERT OR IGNORE`；空库重复执行安全
- **迁移文件契约**：命名 `NNN_<slug>.sql`（三位序号，字典序即执行序）；**一文件一事**、可重复执行（幂等）、不含数据回填以外的业务逻辑
- **不可改变**：`schema_version` 固定 `1`；拒绝语义
- **可自行决定**：迁移目录定位方式、文件内部组织

#### 4.4 `Store.transaction(self, immediate: bool = False) -> Iterator[Connection]`
- **前置条件**：—
- **行为**：`conn.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")`；`yield conn`；正常 `commit()`，异常 `rollback()` 后 `raise`
- **返回**：上下文管理器，yield `Connection`
- **错误**：块内异常 → rollback 并重抛
- **副作用**：库内事务
- **幂等**：不幂等
- **嵌套契约**：**不可嵌套**——SQLite 不允许事务内再 `BEGIN`（调用方若已在事务中，必须直接使用传入的 `Connection`，不得再次调用 `Store.transaction()`）。本设计**不**提供 SAVEPOINT 嵌套语义
- **所有权**：事务内连接由调用方使用，退出上下文提交/回滚
- **不可改变**：异常必 rollback；`immediate=True` 用 `BEGIN IMMEDIATE`
- **可自行决定**：上下文管理器实现

#### 4.5 `Store.one(sql, params) -> Row | None` / `Store.all(sql, params) -> [Row]`
- **前置条件**：SQL 合法
- **行为**：`connection().execute(sql, params)` 的 `fetchone()` / `fetchall()`
- **返回**：单行 / 行列表
- **错误**：SQL 错误 → `sqlite3.Error`
- **语义**：**"执行并取行"的通用 helper**，**不**做只读限制（可执行 `INSERT ... RETURNING` 等）；需要只读时应由调用方约束 SQL
- **幂等**：取决于传入 SQL
- **所有权**：`sqlite3.Row` 已物化，可在连接关闭后读取；调用方持有
- **不可改变**：返回 `Row`（非 `tuple`）
- **可自行决定**：无

#### 4.6 `Store.close(self) -> None`
- **前置条件**：—
- **行为**：取线程连接；非 None 则 `conn.close()` 并置 `_local.connection=None`
- **返回**：None
- **错误**：**不吞异常**（`conn.close()` 的异常向上抛；由调用方/宿主 `finally` 捕获）
- **副作用**：释放**当前线程**的连接
- **幂等**：重复调用安全（第二次为 None 直接返回）
- **所有权**：只释放线程内连接；**不能**关闭其他线程的连接
- **不可改变**：只关本线程、不吞异常
- **可自行决定**：无

## 5. 关键流程与算法

<a id="isd-algorithms"></a>

#### 5.1 `ALGO-UTIL-TXN` · 事务提交/回滚

```text
transaction(immediate):
  conn = connection()            # 线程内复用
  conn.execute(BEGIN [IMMEDIATE])
  try:
      yield conn                 # 调用方执行 SQL
  except:
      conn.rollback(); raise
  else:
      conn.commit()
```

输入推演：块内 `INSERT` 后 `raise` → 无半写；正常退出 → 已提交。

#### 5.2 `ALGO-UTIL-MIGRATE` · 幂等迁移

```text
for f in sorted(migrations.glob("*.sql")):
    connection().executescript(f.read_text())
assert integrity_check() == "ok" else RuntimeError
```

输入推演：连续两次 `migrate()` → 不报错、表结构不变。

#### 5.3 `ALGO-UTIL-FD` · 连接回收

```text
close():
  conn = _local.connection
  if conn: conn.close(); _local.connection = None
```

输入推演：并发请求 → 每请求 `finally: store.close()` → fd 不增长。

**过程清单**

| 过程/规则ID | 触发与执行者 | 入口函数及数据 | 判断事实来源 | 成功可见点 | 失败与清理 |
|---|---|---|---|---|---|
| `P-UTIL-TXN` | 业务模块 `with transaction()` | `transaction` + SQL | 块内异常 | `commit` 生效 | `rollback` |
| `P-UTIL-MIGRATE` | 宿主启动（schema 初始化）| `migrate` + SQL 文件 | `integrity_check` | 表就绪 | `RuntimeError` |
| `P-UTIL-CLOSE` | 请求 `finally` | `close` | `_local.connection` | fd 释放 | 静默 |

## 6. 并发、失败与生命周期

<a id="isd-lifecycle"></a>

- **执行上下文**：Python 线程（`ThreadingHTTPServer` 每请求一线程）；无 async/回调。
- **并发模型**：每线程独立 `Connection`（`threading.local`），**无共享可变状态**；写用 `BEGIN IMMEDIATE` 串行化；`timeout=10` 应对锁等待。
- **锁范围/顺序**：无显式锁；SQLite 内部锁。锁内不调用外部 I/O。
- **取消/超时**：无取消接口；锁等待超 `timeout` 抛 `sqlite3.OperationalError`。
- **生命周期**：宿主启动时执行 schema 初始化（`migrate()`）；每请求结束释放该线程连接（`close()`）；宿主停机时释放其自身线程连接。
- **`close()` 调用点（契约）**：由**宿主**在每请求结束（`finally`）与停机时调用；本层**不**自行调度、不后台回收连接。
- **并发启动裁决**：多实例同时启动时，`migrate()` 的 DDL 由 SQLite 写锁串行化；未获锁方按 `timeout=10` 等待，超时抛 `OperationalError`（宿主判为启动失败）。仅初始化下：先到者建表并把 `schema_version` 置 `1`；后到者见库非空 + 版本匹配 → 直接继续。

**状态查询/重放/接管/新业务重试**：N/A（基础层无副作用编排；由业务模块决定）。

#### 6.1 交错/故障

| 交错/故障 | 已产生副作用 | 检测事实 | 状态/错误 | 保留/释放责任 | 后续允许操作 |
|---|---|---|---|---|---|
| 库不可写/损坏 | 无 | `integrity_check`/`sqlite3.Error` | `RuntimeError`/异常 | 调用方（启动失败或 503）| 修复后重启 |
| 事务内 SQL 错误 | 无（未提交）| 异常 | rollback | 连接保留 | 修正后重试 |
| 连接未关闭 | 无 | fd 增长 | 无 | `finally: close()` | — |

<a id="isd-persistence"></a>

#### 6.2 schema 演进与拒绝语义

**策略决定**——首版只支持 **schema initialization**（空库建当前结构）。**首版不接受的迁移模式**：

- **无增量升级**：不执行 N→N+1 的原地升级
- **无 downgrade**：不支持降级
- **无自动修复**：损坏/不一致库不自动修复

库已存在且版本 ≠ 期望 → **拒绝启动（not_ready）**，由运维走显式离线迁移/重建。增量升级列 `LT-OPEN-UTIL-1`。

| 原规则 | 升级/降级策略 | 接受/拒绝条件 | 源/目标版本与转换函数 | 拒绝后如何处理 |
|---|---|---|---|---|
| `RULE-UTIL-MIGRATE` | 仅初始化；无升级、无降级 | 接受：空库（建表）；拒绝：非空且 `schema_version`≠期望 | 无转换函数；`schema_version` 固定 `1` | 置 `not_ready` + error 日志；运维离线迁移/重建 |
| `RULE-UTIL-TXN` | 不涉及 schema 版本 | — | — | — |

**检查点与动作**：宿主装配阶段检查 `schema_meta.schema_version`；不匹配 → 置 `not_ready`、写 error 日志、拒绝接流量（映射见 §6.4）。

- 仅初始化语义：空库重跑安全（DDL 幂等）；**旧版本库不自动升级**（拒绝）。
- **无** migration ledger / checksum / from-to version（`LT-OPEN-UTIL-1`）。
- 本设计**不要求**迁移在 Store 事务内（仅初始化可接受）；若未来支持增量升级，必须改为逐语句在 `BEGIN IMMEDIATE…COMMIT` 内。

<a id="isd-security"></a>

#### 6.3 安全、权限与可观测性

| 原规则 | 可信输入/敏感字段 | 检查函数/时点 | 拒绝/宿主交付出口 | 脱敏/禁止输出 | 日志/指标口径及触发 | 验证项 |
|---|---|---|---|---|---|---|
| 模块 §11（不鉴权）| DB 文件含配置/审计/日志/用量（**不含 Secret 明文**，只含 `secret_ref` 引用）| 启动时文件/目录权限检查 | 不合规→启动告警/拒绝 | 本层不记录任何值 | 不写日志/指标（避免反向依赖）| `VRC-UTIL-001` |

- **本地持久化安全**（本层唯一安全责任）：DB 文件与目录权限、symlink、umask 属**部署配置**；本层做最小检查（**非 symlink**、权限不含 world-writable），不合规时告警。
- **不含凭据**：库中只有引用字符串。
- **错误交付**：本层抛 `sqlite3.Error` / `RuntimeError`；由业务模块按 **§6.4 错误传播矩阵** 映射。


#### 6.4 错误传播矩阵

本层抛出的底层异常如何被映射（`Store 异常 → 业务模块是否处理 → HTTP 状态/code → 日志 → 是否可重试`）。**本矩阵由宿主/业务模块实现**；`store.py` 只抛底层异常（`sqlite3.Error` / `ApiError`）。

| Store 异常 / 场景 | 业务模块是否处理 | HTTP 状态 / code | 记录日志 | 允许重试 |
|---|---|---|---|---|
| connect / open 失败 | 否（启动即失败）| 启动失败 / `not_ready` | error | 修环境后重启 |
| busy / locked timeout（`OperationalError`）| 是 | 503 `store_unavailable` | warning | 是（退避重试）|
| constraint violation（`IntegrityError`）| 是 | 409 / 400（按业务）| warning | 否 |
| migration / version mismatch | 否（启动拒绝）| `not_ready` | error | 运维处理 |
| integrity_check 失败 | 否（启动拒绝）| `not_ready` | error | 运维修复 |
| close 失败 | 否 | 不影响响应 | warning | — |


## 7. 资源、构建与宿主接入

<a id="isd-resources"></a>

- **工具链/语言**：Python 3.14；标准库 `sqlite3`（无第三方依赖）。
- **产物**：`store.py`（模块文件）+ `migrations/*.sql`；无独立库/二进制。
- **宿主接入（本层要求）**：宿主须（1）在装配阶段构造 `Store` 并执行 schema 初始化；（2）由业务模块持有 `Store` 引用；（3）在每请求结束释放该线程连接。具体宿主符号由宿主设计给出，本 ISD 不重复。
- **峰值构成 / 上限**：每线程 1 连接（`timeout=10`；WAL）。**注意**：fd 数量不是稳定契约——WAL/SHM 句柄可能共享或临时打开，`fd ≤ 3/连接` 不作为保证。
- **超限行为**：fd 上限（macOS 默认 256）风险由**宿主**请求生命周期 + 每请求 `close()` 缓解；锁等待超时 → `OperationalError`。
- **计时**：无自有预算；由宿主请求生命周期约束。

**构建/运行命令**：`PYTHONPATH=src python3 -m pytest tests/unit/v03 -q`（前置：仓库根）。

## 8. 验证规格与实现任务

<a id="isd-verification"></a>

| Rule/成员 | V / Case / Vector | 输入/故障/环境 | Oracle/Expected | Actual/Evidence | Verdict | 测试入口/清理 | Run ID/Status |
|---|---|---|---|---|---|---|---|
| `RULE-UTIL-PRAGMA` | `VRC-UTIL-001`/v1 | 打开连接 | `PRAGMA foreign_keys`=1；`journal_mode`=wal | NOT_RUN | NOT_RUN | `tests/unit/v03` | NOT_RUN |
| `RULE-UTIL-FD` | `VRC-UTIL-001`/v2 | N 次请求（每请求 `close()`）| 结束后进程 fd 数 ≤ 基线（不随请求数增长）| NOT_RUN | NOT_RUN | 并发用例 | NOT_RUN |
| `RULE-UTIL-TXN` | `VRC-UTIL-002`/v1 | 事务内抛异常 | 无半写；库不变 | NOT_RUN | NOT_RUN | `tests/unit/v03` | NOT_RUN |
| `RULE-UTIL-MIGRATE` | `VRC-UTIL-002`/v2 | 连续两次 `migrate()` | 幂等、不报错 | NOT_RUN | NOT_RUN | `tests/unit/v03` | NOT_RUN |
| `RULE-UTIL-MIGRATE` | `VRC-UTIL-002`/v3 | 损坏库 | `integrity_check`≠ok → 启动失败 | NOT_RUN | NOT_RUN | 故障注入 | NOT_RUN |
| `RULE-UTIL-MIGRATE` | `VRC-UTIL-002`/v4 | 非空库 + 版本≠期望 | **拒绝启动（not_ready）** | NOT_RUN | NOT_RUN | `tests/unit/v03` | NOT_RUN |
| `RULE-UTIL-MIGRATE` | `VRC-UTIL-002`/v5 | 迁移脚本中途失败 | 仅初始化下不接受部分应用（见 §6.2）| NOT_RUN | NOT_RUN | 故障注入 | NOT_RUN |
| `RULE-UTIL-TXN` | `VRC-UTIL-002`/v6 | 事务内再 `BEGIN` | `OperationalError`（不可嵌套）| NOT_RUN | NOT_RUN | `tests/unit/v03` | NOT_RUN |
| `RULE-UTIL-PRAGMA` | `VRC-UTIL-001`/v3 | busy 锁等待 | 超 `timeout` → `OperationalError` | NOT_RUN | NOT_RUN | 并发用例 | NOT_RUN |
| `RULE-UTIL-MIGRATE` | `VRC-UTIL-002`/v7 | 两实例并发 `migrate()` | 一个成功建表；另一个成功或明确 `OperationalError`；**无部分/损坏表** | NOT_RUN | NOT_RUN | 并发用例 | NOT_RUN |
| `RULE-UTIL-FD` | `VRC-UTIL-001`/v4 | close 异常 | 向上抛（不吞）| NOT_RUN | NOT_RUN | `tests/unit/v03` | NOT_RUN |
| `RULE-UTIL-CONN` | `VRC-UTIL-001`/v5 | world-writable 文件 | 启动告警 | NOT_RUN | NOT_RUN | 故障注入 | NOT_RUN |

**独立 Oracle**：SQLite PRAGMA 实际值；事务后行数；fd 计数；`schema_version`。

**运行命令**：局部 `PYTHONPATH=src python3 -m pytest tests/unit/v03 -q`；**提交前**按测试规范执行全量 `PYTHONPATH=src python3 -m pytest tests/ tests/system/st_*.py -q`。

<a id="isd-tasks"></a>

| 顺序 | 实现任务/文件/symbol | 前置项 | 不可改变的规则 | 完成检查 |
|---|---|---|---|---|
| 1 | 连接与 PRAGMA / `store.py` `connection/close` | — | 外键/WAL 固定 | `VRC-UTIL-001` |
| 2 | 事务与查询 / `store.py` `transaction/one/all` | 1 | 原子性固定 | `VRC-UTIL-002` |
| 3 | 迁移 / `store.py` `migrate` + `migrations/*.sql` | 1 | 幂等固定 | `VRC-UTIL-002` |

## 9. 映射、复核与未决项

| 模块/原成员ID | 唯一来源/版本/selector/hash | 提供或消费/后端 | 计划位置（Planned）| 验证项 | 状态 |
|---|---|---|---|---|---|
| M007 / `F-UTIL-CONN` | `util` / `0.1.0-draft.1` / `#5.2` | 提供 / sqlite3 | `src/llmtier_v03/store.py` `Store.connection` | `VRC-UTIL-001` | Planned |
| M007 / `F-UTIL-TXN` | `util` / `#5.4` | 提供 / sqlite3 | `store.py` `Store.transaction` | `VRC-UTIL-002` | Planned |
| M007 / `F-UTIL-MIGRATE` | `util` / `#5.3` | 提供 / sqlite3 | `store.py` `Store.migrate` | `VRC-UTIL-002` | Planned |

**复核**：编码者视角——函数职责/参数/错误/清理齐全，可直接编码；接口消费者——公共类型引用标准库，无第二权威；并发/资源——每线程连接与 fd 说明清楚；测试——Rule→V→Case→Oracle 对应。

| 问题ID/既有台账引用 | 具体缺口/反例 | Owner | 最晚关闭阶段/截止Gate | 阻断范围 | 分析/决策引用 | 所需输入/下一步选择判据 | 解决动作/完成条件 | 状态 |
|---|---|---|---|---|---|---|---|---|
| `RISK-UTIL-1` | 高并发写串行/锁超时 | LLMTier | 性能验证阶段 | `F-UTIL-TXN` 性能 | `util` §15.1 | 性能数据 | WAL + IMMEDIATE；按验证结果调参 | 观察 |
