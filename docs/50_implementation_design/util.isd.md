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
- **模块设计 Document ID / 版本 / 路径 / 摘要**：`util` / `0.1.0-draft.1` / `docs/40_module_design/util-design.md` / `§5.1 F-UTIL-CONN/TXN/MIGRATE/QUERY/CLOSE`、`§8 RULE-UTIL-PRAGMA/TXN/MIGRATE/FD`
- **直属父对象 / 父设计**：LLMTier 软件系统 / `llmtier-system-design`（§3.2 登记）
- **需求与 Constraint ID**：`C-CFG-1`（唯一持久化）、`C-CFG-3`（原子推进）、机制 `R-CFG-03`、`R-OBS-06`
- **实现范围 / 非目标**：实现 `Store`；不做业务规则、不直连外部、不定义表语义

<a id="isd-handoff"></a>

**承接矩阵（上游 → 本 ISD 细化）**

#### 1.1 `F-UTIL-CONN` / `RULE-UTIL-PRAGMA` · 连接与 PRAGMA
- **固定来源**：`util` / `0.1.0-draft.1` / `#5.1.1`
- **ISD 细化内容 / 章节**：`connection()` 的 `threading.local` 缓存与 PRAGMA
- **唯一权威位置**：行为在模块 §5.1.1；ISD 管实现
- **实现自由度**：缓存结构可自选
- **原 V/Case 及本地验证位置**：`VRC-UTIL-001` → §8

#### 1.2 `F-UTIL-TXN` / `RULE-UTIL-TXN` · 事务
- **固定来源**：`util` / `0.1.0-draft.1` / `#5.1.2`
- **ISD 细化内容 / 章节**：`transaction()` 的 `BEGIN [IMMEDIATE]` / commit / rollback
- **唯一权威位置**：行为在模块 §8.2；ISD 管实现
- **实现自由度**：实现可自选
- **原 V/Case 及本地验证位置**：`VRC-UTIL-002` → §8

#### 1.3 `F-UTIL-MIGRATE` / `RULE-UTIL-MIGRATE` · 迁移
- **固定来源**：`util` / `0.1.0-draft.1` / `#5.1.3`
- **ISD 细化内容 / 章节**：迁移文件枚举、`executescript`、`integrity_check`
- **唯一权威位置**：行为在模块 §8.3；ISD 管实现
- **实现自由度**：实现可自选
- **原 V/Case 及本地验证位置**：`VRC-UTIL-002` → §8

#### 1.4 `F-UTIL-QUERY` · 只读查询
- **固定来源**：`util` / `0.1.0-draft.1` / `#5.1.4`
- **ISD 细化内容 / 章节**：`one()` / `all()` 与 `Row` 工厂
- **唯一权威位置**：行为在模块 §5.1.4；ISD 管实现
- **实现自由度**：实现可自选
- **原 V/Case 及本地验证位置**：`VRC-UTIL-002` → §8

#### 1.5 `F-UTIL-CLOSE` / `RULE-UTIL-FD` · 连接关闭
- **固定来源**：`util` / `0.1.0-draft.1` / `#5.1.1`
- **ISD 细化内容 / 章节**：`close()` 清空线程连接
- **唯一权威位置**：行为在模块 §8.4；ISD 管实现
- **实现自由度**：实现可自选
- **原 V/Case 及本地验证位置**：`VRC-UTIL-001` → §8

#### 1.6 `R-OBS-06` · 观测表存储
- **固定来源**：`libdiag` / `0.1.0-draft.2` / `#isd-data`
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
- **可见性 / 构建目标**：模块私有 API；随 `Application` 装配
- **依赖**：`sqlite3`、`threading`、`contextlib`、`pathlib`

#### 2.2 `migrations/*.sql`
- **职责 / 调用者**：DDL；由 `migrate()` 执行
- **类型 / 函数**：SQL 脚本
- **可见性 / 构建目标**：数据文件，随包
- **依赖**：—

## 3. 内部数据与所有权

<a id="isd-data"></a>

以下为**纯软件**实现，无 ABI/位宽/对齐/端序（不适用，依据：Python `sqlite3`，无二进制 wire）。

#### 3.1 `Store`（私有类）
- **字段**：`path: str`（SQLite 文件路径）；`_local: threading.local`
- **初值 / 约束**：`path` 只读；父目录在 `__init__` 创建
- **创建 / 修改者**：`Application.__init__` 创建
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
- **借用期限 / 释放者**：调用方持有；行不跨连接寿命
- **公共类型来源**：标准库

**所有权图**

```text
Application 持有 Store（进程级）
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

#### 4.2 `Store.connection(self) -> sqlite3.Connection`
- **前置条件**：—
- **行为**：取 `getattr(self._local,"connection",None)`；为 `None` 时 `sqlite3.connect(self.path, timeout=10, isolation_level=None)`，设 `row_factory=Row` 并执行 PRAGMA，缓存回 `_local`
- **返回**：线程内 `Connection`
- **错误**：连接失败 → `sqlite3.Error`（冒泡）
- **副作用**：可能新建连接并在同一连接执行 PRAGMA
- **幂等**：同线程多次调用返回同一对象
- **所有权**：连接归线程；调用方**不得**关闭（由 `close()` 统一）

#### 4.3 `Store.migrate(self) -> None`
- **前置条件**：`store.py` 同目录存在 `migrations/`
- **行为**：`sorted(migrations.glob("*.sql"))` 逐个 `executescript(read_text())`；随后 `PRAGMA integrity_check`
- **返回**：None
- **错误**：`integrity_check != "ok"` → `RuntimeError(f"sqlite_integrity_check_failed:{result}")`
- **副作用**：建表（幂等 DDL）
- **幂等**：脚本使用 `IF NOT EXISTS`/`INSERT OR IGNORE`，重复执行安全
- **所有权**：无（连接经 `connection()`）

#### 4.4 `Store.transaction(self, immediate: bool = False) -> Iterator[Connection]`
- **前置条件**：—
- **行为**：`conn.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")`；`yield conn`；正常 `commit()`，异常 `rollback()` 后 `raise`
- **返回**：上下文管理器，yield `Connection`
- **错误**：块内异常 → rollback 并重抛
- **副作用**：库内事务
- **幂等**：不幂等（写事务）；读事务可重入
- **所有权**：事务内连接由调用方使用；不得嵌套非立即事务

#### 4.5 `Store.one(sql, params) -> Row | None` / `Store.all(sql, params) -> [Row]`
- **前置条件**：SQL 合法
- **行为**：`connection().execute(sql, params)` 的 `fetchone()` / `fetchall()`
- **返回**：单行 / 行列表
- **错误**：SQL 错误 → `sqlite3.Error`
- **副作用**：无（只读约定）
- **幂等**：只读
- **所有权**：行返回调用方；不跨连接寿命

#### 4.6 `Store.close(self) -> None`
- **前置条件**：—
- **行为**：取线程连接；非 None 则 `conn.close()` 并置 `_local.connection=None`
- **返回**：None
- **错误**：关闭异常静默（调用方 `finally` 兜底）
- **副作用**：释放 fd
- **幂等**：重复调用安全
- **所有权**：释放线程连接

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
| `P-UTIL-MIGRATE` | 启动 `Application.__init__` | `migrate` + SQL 文件 | `integrity_check` | 表就绪 | `RuntimeError` |
| `P-UTIL-CLOSE` | 请求 `finally` | `close` | `_local.connection` | fd 释放 | 静默 |

## 6. 并发、失败与生命周期

<a id="isd-lifecycle"></a>

- **执行上下文**：Python 线程（`ThreadingHTTPServer` 每请求一线程）；无 async/回调。
- **并发模型**：每线程独立 `Connection`（`threading.local`），**无共享可变状态**；写用 `BEGIN IMMEDIATE` 串行化；`timeout=10` 应对锁等待。
- **锁范围/顺序**：无显式锁；SQLite 内部锁。锁内不调用外部 I/O。
- **取消/超时**：无取消接口；锁等待超 `timeout` 抛 `sqlite3.OperationalError`。
- **生命周期**：`migrate()` 在 `Application.__init__` 调用；请求 `finally` 调 `close()`；停机 `app.store.close()`。

**状态查询/重放/接管/新业务重试**：N/A（基础层无副作用编排；由业务模块决定）。

#### 6.1 交错/故障

| 交错/故障 | 已产生副作用 | 检测事实 | 状态/错误 | 保留/释放责任 | 后续允许操作 |
|---|---|---|---|---|---|
| 库不可写/损坏 | 无 | `integrity_check`/`sqlite3.Error` | `RuntimeError`/异常 | 调用方（启动失败或 503）| 修复后重启 |
| 事务内 SQL 错误 | 无（未提交）| 异常 | rollback | 连接保留 | 修正后重试 |
| 连接未关闭 | 无 | fd 增长 | 无 | `finally: close()` | — |

<a id="isd-persistence"></a>

#### 6.2 持久化与数据升级

| 原规则/事务 | 原子范围/事务外副作用 | 提交点/响应点 | 恢复入口/判定记录 | 源/目标数据版本及转换函数 | 校验/切换/失败出口 | 验证项 |
|---|---|---|---|---|---|---|
| `RULE-UTIL-TXN` | 单事务内 SQL；无事务外副作用 | `commit()` 为持久提交点 | 启动 `migrate()` | 无版本字段（SQLite 文件即版本）| `integrity_check`；失败 `RuntimeError` | `VRC-UTIL-002` |

崩溃后由启动重跑 `migrate()`；幂等 DDL 保证重复恢复安全。无独立升级转换（首版）。

<a id="isd-security"></a>

#### 6.3 安全、权限与可观测性

| 原规则 | 可信输入/敏感字段 | 检查函数/时点 | 拒绝/宿主交付出口 | 脱敏/禁止输出 | 日志/指标口径及触发 | 验证项 |
|---|---|---|---|---|---|---|
| 模块 §11（不鉴权） | 无（基础层）| — | — | 本层不记录任何值 | 本层不写日志/指标（避免反向依赖）| `VRC-UTIL-001` |

不拥有权限/日志/诊断能力；向宿主（业务模块）返回结构化异常，由宿主映射 503 与日志。

## 7. 资源、构建与宿主接入

<a id="isd-resources"></a>

- **工具链/语言**：Python 3.14；标准库 `sqlite3`（无第三方依赖）。
- **产物**：`store.py`（模块文件）+ `migrations/*.sql`；无独立库/二进制。
- **宿主接入**：`Application.__init__(database, settings)` 构造 `Store(database)` 并 `store.migrate()`；业务服务持 `Store` 引用；`Handler._run` 的 `finally` 调 `app.store.close()`。
- **峰值构成 / 上限**：每线程 1 连接（fd ≤ 3/连接：db+wal+shm）；`timeout=10`；WAL。
- **超限行为**：fd 上限（macOS 256）→ 依赖 `close()` 兜底；锁等待超时 → 异常。
- **计时**：无自有预算；由宿主请求生命周期约束。

**构建/运行命令**：`PYTHONPATH=src python3 -m pytest tests/unit/v03 -q`（前置：仓库根）。

## 8. 验证规格与实现任务

<a id="isd-verification"></a>

| Rule/成员 | V / Case / Vector | 输入/故障/环境 | Oracle/Expected | Actual/Evidence | Verdict | 测试入口/清理 | Run ID/Status |
|---|---|---|---|---|---|---|---|
| `RULE-UTIL-PRAGMA` | `VRC-UTIL-001`/v1 | 打开连接 | `PRAGMA foreign_keys`=1；`journal_mode`=wal | NOT_RUN | NOT_RUN | `tests/unit/v03` | NOT_RUN |
| `RULE-UTIL-FD` | `VRC-UTIL-001`/v2 | 并发请求后 | 每请求 fd 稳定（`close()` 兜底）| NOT_RUN | NOT_RUN | 并发用例 | NOT_RUN |
| `RULE-UTIL-TXN` | `VRC-UTIL-002`/v1 | 事务内抛异常 | 无半写；库不变 | NOT_RUN | NOT_RUN | `tests/unit/v03` | NOT_RUN |
| `RULE-UTIL-MIGRATE` | `VRC-UTIL-002`/v2 | 连续两次 `migrate()` | 幂等、不报错 | NOT_RUN | NOT_RUN | `tests/unit/v03` | NOT_RUN |
| `RULE-UTIL-MIGRATE` | `VRC-UTIL-002`/v3 | 损坏库 | `integrity_check`≠ok → `RuntimeError` | NOT_RUN | NOT_RUN | 故障注入 | NOT_RUN |

**独立 Oracle**：SQLite PRAGMA 实际值；事务后行数；fd 计数。

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
| `RISK-UTIL-1` | 高并发写串行/锁超时 | LLMTier | 实测阶段 | `F-UTIL-TXN` 性能 | `util` §15.1 | 实测数据 | WAL + IMMEDIATE；实测调参 | 观察 |
