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
| Last Modified Date | `2026-09-23` |
| Template ID | `design.definition` |
| Template Version | `2.4.0` |
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
- **行为**：按序执行 `executescript`；`PRAGMA integrity_check`
- **输出**：表就绪 / 异常
- **错误与边界**：非 `ok` → `RuntimeError`
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

#### 5.3.1 `IF-UTIL-01` · 业务模块 → `store.py`
- **签名 / 入口**：`Store.connection/migrate/transaction(immediate)/one/all/close`
- **输入与前置条件**：库路径；SQL
- **输出 / 异常**：连接/行；sqlite3 异常
- **ownership / 生命周期**：连接线程内；业务模块负责关闭
- **实现与验证位置**：`store.py`；`VRC-UTIL-001/002`

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

## 6. 数据模型、状态与 ownership

#### 6.1 `Store`（连接缓存）
- **Authority / 定义位置**：`store.py`
- **字段**：`path:str`、`_local.connection:sqlite3.Connection|None`
- **键与跨字段约束**：每线程一连接
- **Writer / Reader**：I1
- **创建、持有、借用/复制与释放**：线程进入创建；`close()` 释放
- **状态转换 / 并发规则**：线程局部；跨线程不共享
- **验证项**：`VRC-UTIL-001`

#### 6.2 `migrations/*.sql`
- **Authority / 定义位置**：`src/util/migrations/`
- **字段**：`001_initial.sql`、`002_observability.sql`
- **键与跨字段约束**：幂等（`IF NOT EXISTS`）
- **Writer / Reader**：I3 执行
- **创建、持有、借用/复制与释放**：随仓库
- **状态转换 / 并发规则**：按文件名排序
- **验证项**：`VRC-UTIL-002`

## 7. 主流程与数据流

**内部流程正文**：启动时 `Store.migrate` 建表并完整性检查；请求内业务模块经 `store.connection()`（线程内复用）执行读写；写路径用 `store.transaction(immediate=True)` 原子提交/回滚；请求结束 `app.store.close()` 释放线程连接。

#### 7.1 `P-UTIL-MIGRATE` · 迁移
- **触发/适用条件**：启动
- **图与正文位置**：§5.1.3
- **正常出口**：表就绪
- **异常出口**：`RuntimeError`（integrity）

#### 7.2 `P-UTIL-TXN` · 事务
- **触发/适用条件**：任意写
- **图与正文位置**：§5.2.1
- **正常出口**：commit
- **异常出口**：rollback + 重抛

#### 7.3 `P-UTIL-CLOSE` · 连接关闭
- **触发/适用条件**：请求 `finally`
- **图与正文位置**：§5.1.1
- **正常出口**：fd 释放
- **异常出口**：静默

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

## 9. 接口与机器契约

#### 9.1 `IF-UTIL-STORE` · `Store` API
- **Direction / Operation / 责任模块 / backend**：in；`connection/migrate/transaction/one/all/close`；M007；SQLite
- **Request / Response / Error / ownership**：SQL/params → 连接/行；sqlite3 异常
- **Contract authority / version / revision / hash / selector**：本文 §6
- **前提 / timeout / 兼容边界 / Error model**：存储错误由调用方映射
- **本地文件 / symbol 或 NOT_IMPLEMENTED**：`store.py`
- **Constraint / VRC / Case / 环境 / Run**：`C-CFG-1/3`、`R-CFG-03`、`R-OBS-06`；`VRC-UTIL-001/002`；NOT_RUN
- **关联类型字段 ID**：`Store`（§6.1）

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
- **来源 Capability / Step / Constraint / 接口成员**：§8 4 张表
- **本模块必须负责的行为与保证**：4 张表的持久化与事务
- **本模块提供 / 消费的接口**：`Store`
- **本文落实位置**：§6.2、§13.1.2
- **代码文件 / symbol 或 NOT_IMPLEMENTED**：`migrations/002_observability.sql`
- **允许自行决定的范围**：表结构实现
- **本地验证 / 组合验证交接**：`VRC-UTIL-002`；M006
