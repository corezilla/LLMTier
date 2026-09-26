<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier M008 log 模块设计

> STD 使用入口：[项目采用说明与标准导航](../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `log` |
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
| Canonical Path | `docs/40_module_design/log-design.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 单元摘要：为什么存在

| 项目 | 值 |
|---|---|
| 模块编号 / 正式英文名称 | **M008** / `log` |
| 直属父对象编号 / 名称 | LLMTier 软件系统（本项目无子系统）|
| 父设计 Document ID / 登记位置 | `llmtier-system-design` / 系统设计 §3.2（唯一登记表）|
| 上级系统 / 父单元 | LLMTier 软件系统 |
| 解决的问题 | 运行过程中需要一份**写入前即脱敏**、可结构化过滤的运行日志；若由各模块自行打印，敏感信息会泄漏且无法统一留存/查询 |
| 提供的能力 | 运行日志的写入（写入前正则脱敏 + 长度截断）、按时间/级别/模块/request_id 过滤查询 |
| 主要使用者 | M001/M003/M004/M006（写）；M004/M002（查）|
| 不负责 | 审计（M004 `audit`）；观测记录（M006）；持久化机制（M007）；对外的日志端点（M001）|

### 1.1 继承的上级约束与落实方式

#### 1.1.1 脱敏（禁 Secret/正文）
- **上级基线与决定状态**：系统设计 §11.3（不记录 Secret/credential/完整正文）；已采用
- **适用条件**：全部写入
- **继承预算或行为保证**：写入前完成脱敏，查询侧不再兜底
- **可自行选择 / 不可改变**：脱敏正则可自选；"写前脱敏"不可变
- **本地落实 / 内部再分配**：I1 写入；§8
- **验证方法与结果 / 证据**：`VRC-LOG-001`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：与 M006/M004 的脱敏口径一致

#### 1.1.2 不阻塞主路径
- **上级基线与决定状态**：系统设计 §11.3（观测类写入不改变业务结果）；已采用
- **适用条件**：全部写入
- **继承预算或行为保证**：日志写入失败不使业务失败
- **可自行选择 / 不可改变**：— 
- **本地落实 / 内部再分配**：I1
- **验证方法与结果 / 证据**：`VRC-LOG-001`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：无

## 2. 需求、功能与验收条件

### 2.1 `F-LOG-WRITE` · 写入运行日志
- **上级需求 / Constraint ID**：脱敏约束（§1.1.1）
- **调用方**：M001/M003/M004/M006
- **输入与前提**：`(level, module, event, message, request_id?)`
- **行为**：`_SENSITIVE` 正则替换 `[REDACTED]`；换行折叠；截断 ≤512；写入 `operational_logs`
- **输出**：日志行
- **错误与边界**：写入失败不抛到主路径
- **验收条件**：含 `Authorization`/`Bearer …`/`secret`/`api_key`/`token=` 的文本被脱敏

### 2.2 `F-LOG-QUERY` · 查询运行日志
- **上级需求 / Constraint ID**：机制 M-OBS（日志查询）
- **调用方**：M004（`GET /v1/logs`）；M002 呈现
- **输入与前提**：`limit` + 可选 `level/module/request_id` + **必填 `since/until`**
- **行为**：条件查询，按时间倒序
- **输出**：`{data[], page}`
- **错误与边界**：缺 `since`/`until` → 400 `invalid_request`
- **验收条件**：只返回已脱敏字段；不返回正文/凭据

## 3. UI、CLI、服务端点或设备操作面

**N/A — 本模块没有直接操作面。** 日志查询由 **M001** 暴露（`GET /v1/logs`）、由 **M002 Web UI** 呈现。Tailoring 依据：系统设计 §3.2 规定入口层终止 HTTP/SSE。

## 4. 外部边界与依赖

#### 4.1 `DEP-ALL` · 全部业务模块（写）
- **角色 / 运行位置 / Owner**：消费方；同进程；LLMTier
- **本模块调用或消费**：—
- **本模块提供**：`OperationalLog.record`
- **契约 authority / 版本 / selector**：本文 §9
- **同步方式 / timeout / 生命周期**：同步、尽力而为
- **不可用或失败影响 / 责任出口**：不阻塞业务

#### 4.2 `DEP-M004` · Management（查询）
- **角色 / 运行位置 / Owner**：消费方；同进程；LLMTier
- **本模块调用或消费**：—
- **本模块提供**：`OperationalLog.page`
- **契约 authority / 版本 / selector**：本文 §9
- **同步方式 / timeout / 生命周期**：同步
- **不可用或失败影响 / 责任出口**：503

#### 4.3 `DEP-M007` · util（存储）
- **角色 / 运行位置 / Owner**：依赖；同进程；LLMTier
- **本模块调用或消费**：`Store.connection/all`
- **本模块提供**：—
- **契约 authority / 版本 / selector**：机制 R-CFG-03
- **同步方式 / timeout / 生命周期**：同步
- **不可用或失败影响 / 责任出口**：写入失败静默；查询失败 503

## 5. 内部结构与实现位置

### 5.1 内部组成

#### 5.1.1 `I1` · 脱敏写入
- **职责与非职责**：写入前脱敏/截断并落库；不做查询
- **输入、处理与输出**：`(level, module, event, message, request_id)` → 行
- **协作对象**：M007
- **文件 / symbol / 实现状态**：`logs.py` `OperationalLog.record`、`_SENSITIVE`；Implemented
- **拆分依据与替代方案代价**：写前脱敏保证任何读路径都安全

#### 5.1.2 `I2` · 过滤查询
- **职责与非职责**：按条件查询并整形；不做脱敏（已在写入时完成）
- **输入、处理与输出**：过滤条件 → `{data,page}`
- **协作对象**：M007、M004
- **文件 / symbol / 实现状态**：`logs.py` `OperationalLog.page`；Implemented
- **拆分依据与替代方案代价**：查询与写入分离

### 5.2 内部调用过程

#### 5.2.1 `CALL-LOG-WRITE` · 一次写入
- **入口与调用上下文**：任意模块 `logs.record(...)`
- **调用链**：`record` → `_SENSITIVE.sub` + 截断 → `Store.connection().execute(INSERT)`
- **逐步传递的数据**：`(level, module, event, message, request_id)` → 行
- **返回、异常与清理**：无返回
- **对应流程 / 接口 / 验证**：§7 P-LOG-WRITE / `VRC-LOG-001`

### 5.3 文件间接口契约

> 本模块内部/跨模块文件交接逐项映射到 §9 的成员定义；签名、输入输出、错误与寿命以 §9 对应记录为唯一来源，本节不再复写。

| 内部契约 ID | provider → consumer | §9 成员 | 本文件责任 | 验证 |
|---|---|---|---|---|
| `IF-LOG-01` | 全部业务模块 → `src/log/logs.py` | §9.1 `IF-LOG-RECORD`、`IF-LOG-QUERY` | 写入方只调 `record`；查询方只调 `page` | `VRC-LOG-001` |

### 5.4 服务提供方式（条件适用）

- **运行载体与入口**：N/A + 依据 —— 嵌入式库，无独立 server
- **并发/线程模型**：N/A + 依据 —— 使用调用方线程；写经 `Store.connection()`（线程内）
- **初始化、Ready、生效与停止**：随 `Application` 构造
- **宿主装配、失败和资源回收责任**：由 M001/启动装配

### 5.5 依赖方向

- **允许方向**：全部业务模块 → M008 → M007
- **禁止方向与原因**：M008 不得 import 业务模块；不直连 HTTP
- **循环/越层检查**：`logs.py` 只 import `store`
- **变更影响**：脱敏规则变更影响所有写入方

## 6. 数据结构设计

> 按 STD `design-data-interface-format` 1.2.0：主章“数据结构设计”，章内按**数据性质分类**。M008 为进程内库，无 wire、无设备；`6.4 通信报文` 与 `6.5 设备与 FPGA 表项` 不适用。继承结构只定位原定义；本层拥有的结构逐项完整记录（Data/Type ID、用途与来源／逐字段／跨字段与寿命／合法与拒绝实例／验证），每个结构以真实名称作带编号小节标题，先给类型声明再逐字段展开。

**适用性**：6.1 公共基础类型与枚举 ✓｜6.2 业务与操作数据结构 ✓｜6.3 配置与规则数据结构 ✓｜6.4 通信报文 ✗（进程内函数调用，无 wire 报文）｜6.5 设备与 FPGA 表项 ✗（无连接器/总线/寄存器/FPGA 端口）｜6.6 运行状态数据结构 ✗（写入即落库、查询无状态，无跨步骤状态）｜6.7 数据库表结构 ✓（authority = `util/migrations/001_initial.sql`）｜6.8 错误码与错误结构 ✓（引用系统 Error ID）。

### 6.1 公共基础类型与枚举

**6.1.1 `LogLevel`（公共基础类型与枚举）**

```text
enum LogLevel { info, warning, error }
```

- **Data/Type ID、用途与来源**：

  `D-LOG-LEVEL`；运行日志级别，调用方约定集合、代码不校验；来源 `src/log/logs.py` 调用约定。

- **`info`**：

  提示级；记录正常业务里程碑。

- **`warning`**：

  警告级；记录可继续但需关注的异常（如 fail-open 丢日志）。

- **`error`**：

  错误级；记录失败事实。

- **跨字段与寿命**：

  无强制白名单，未知级别按原样存储并可按 `level=` 过滤；随 `operational_logs.level` 持久，保留期由运维决定。

- **合法/拒绝实例**：

  合法 `info`；边界：未知 `trace` 可写入（消费方按未知处理），不构成拒绝。

- **验证**：

  `VRC-LOG-001`；实现 `src/log/logs.py`。

### 6.2 业务与操作数据结构

**6.2.1 `LogEvent`（业务与操作数据结构）**

```text
LogEvent {
  id: string,              // log_<16hex>
  created_at: string,      // RFC3339 毫秒
  level: LogLevel,
  module: string,
  event: string,
  message: string,         // ≤512，已脱敏
  request_id: string?
}
```

- **Data/Type ID、用途与来源**：

  `D-LOG-EVENT`；一条写前脱敏的运行日志行及其视图；authority `util/migrations/001_initial.sql` + `src/log/logs.py`。

- **`id`**：

  必填、非空字符串，格式 `log_<16hex>`；日志行稳定身份，写入时生成。

- **`created_at`**：

  必填、RFC3339 毫秒字符串；写入时刻；只追加，不改写。

- **`level`**：

  必填，取 §6.1 `LogLevel`；未知值原样存储。

- **`module`**：

  必填、非空字符串；产生日志的模块名。

- **`event`**：

  必填、非空字符串；事件名。

- **`message`**：

  必填字符串，长度 ≤512；写入前经 `_SENSITIVE` 替换、换行折叠并截断；不含正文/凭据。

- **`request_id`**：

  可空字符串；关联请求身份；非请求上下文产生的日志为空。

- **跨字段与寿命**：

  `message` 在任何写入前完成脱敏与截断；持久 `operational_logs`，I1 写、I2 读，只追加；无更新/删除路径（保留期由运维）。

- **合法/拒绝实例**：

  合法 `{level:"info",module:"http",event:"request",message:"GET /v1/models",request_id:"req_ab12"}`；边界：含敏感串的文本先脱敏再写入，无拒绝路径（写失败 fail-open）。

- **验证**：

  `VRC-LOG-001`；实现 `src/log/logs.py` + `util/migrations/001_initial.sql`。

**6.2.2 `LogPage`（业务与操作数据结构）**

```text
LogPage {
  data: LogEvent[],        // ≤ limit
  page: {
    has_more: bool,
    next_cursor: string?   // 当前实现恒 null
  }
}
```

- **Data/Type ID、用途与来源**：

  `D-LOG-PAGE`；运行日志分页结果；来源 `src/log/logs.py` `OperationalLog.page`。

- **`data`**：

  必填数组，元素为 §6.2.1 `LogEvent`，长度 ≤ `limit`。

- **`page.has_more`**：

  必填布尔；当前实现恒 `false`（无后续页）。

- **`page.next_cursor`**：

  可空字符串；当前实现恒 `null`。

- **跨字段与寿命**：

  按 `created_at DESC,id DESC` 倒序；`limit` 夹 `[1,200]`；请求级只读，不持久。

- **合法/拒绝实例**：

  合法 `{data:[…],page:{has_more:false,next_cursor:null}}`；边界：无匹配 → `data=[]`。

- **验证**：

  `VRC-LOG-001`。

### 6.3 配置与规则数据结构

**6.3.1 `RedactionRule`（配置与规则数据结构）**

```text
RedactionRule {
  pattern: regex,          // _SENSITIVE
  replacement: string,     // "[REDACTED]"
  newline_fold: bool,      // true
  max_length: uint32       // 512
}
```

- **Data/Type ID、用途与来源**：

  `D-LOG-REDACTION-RULE`；写前脱敏规则；来源 `src/log/logs.py` `_SENSITIVE`，随代码版本固定。

- **`pattern`**：

  必填正则 `(?i)(authorization|bearer\s+\S+|secret|api[_-]?key|token\s*[=:]\s*\S+)`；匹配敏感文本。

- **`replacement`**：

  必填字符串 `[REDACTED]`；替换命中片段。

- **`newline_fold`**：

  必填布尔，恒 `true`；替换后折叠换行。

- **`max_length`**：

  必填正整数 `512`；折叠后截断上限。

- **跨字段与寿命**：

  规则在写入前应用；查询侧不再兜底；正则可调、"写前脱敏"不可变；模块级常量，随代码版本。

- **合法/拒绝实例**：

  合法 `Authorization: Bearer x` → `Authorization: [REDACTED]`；边界：未覆盖的凭据形态由 §15 `RISK-LOG-1` 跟踪。

- **验证**：

  `VRC-LOG-001`。

### 6.7 数据库表结构

Authority = `util/migrations/001_initial.sql`（由 M007 `migrate()` 执行）；列级定义见 `util.isd` §4.4。本模块拥有 1 张表。

**6.7.1 `operational_logs`（数据库表结构）**

```sql
CREATE TABLE operational_logs (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  level TEXT NOT NULL,
  module TEXT NOT NULL,
  event TEXT NOT NULL,
  message TEXT NOT NULL CHECK (length(message) <= 512),
  request_id TEXT NULL
);
```

- **Data/Type ID、用途与来源**：

  `D-LOG-TABLE`；保存写前脱敏的运行日志行；authority `util/migrations/001_initial.sql`，由 M007 `migrate()` 执行。

- **`id`**：

  非空主键，对应 §6.2.1 `LogEvent.id`。

- **`created_at`**：

  NOT NULL，RFC3339 毫秒；写入时刻。

- **`level`**：

  NOT NULL，采用 §6.1 枚举的存储值。

- **`module`**：

  NOT NULL，产生模块名。

- **`event`**：

  NOT NULL，事件名。

- **`message`**：

  NOT NULL，`CHECK(length(message)<=512)`；写入前已脱敏，约束为兜底。

- **`request_id`**：

  可空，关联请求身份。

- **跨字段与寿命**：

  只追加，I1 写、I2 读；无更新/删除；保留期由运维决定；不在本层做迁移（迁移归 M007）。

- **合法/拒绝实例**：

  合法：一行脱敏日志（`message` ≤512）；边界：`message` >512 在写入前被截断，`CHECK` 不再触发。

- **验证**：

  `VRC-LOG-001`；authority `util/migrations/001_initial.sql`。

### 6.8 错误码与错误结构

本模块**不新增公共错误码**；对外错误引用系统目录（`llmtier-system-design` §8.8）：

| 本层错误 | 条件 | 系统 Error ID | 合法下一步 |
|---|---|---|---|
| 写入失败（fail-open 静默） | `Store` 不可写 | 无（fail-open，记 warning） | 不重试；不阻塞业务 |
| `ApiError(400,"invalid_request")` | `page` 缺 `since`/`until` | `ERR-REQ-VALIDATION` | 补时间窗后重试 |
| 查询失败 → HTTP 503 | 存储不可读 | `ERR-STORE` | 稍后重试 |

- **约束 / 不变量**：`record` 失败不抛、不产生公共错误；`page` 缺时间窗 → 400，存储失败由 M004/M001 映射为 `ERR-STORE`。
- **实例**：拒绝：存储不可读 → `ERR-STORE`；边界：写失败 → 静默，无错误返回。
- **来源 / 验证**：`logs.py` + 系统 §8.8；`VRC-LOG-001`。

## 7. 主流程与数据流

**内部流程正文**：写入方调用 `record`，`message` 先经 `_SENSITIVE` 替换与截断，再 `INSERT` 到 `operational_logs`；查询方调用 `page`，按过滤条件 `SELECT` 并返回。写入不阻塞主路径；查询存储不可用返回 503（由 M004/M001 映射）。

#### 7.1 `P-LOG-WRITE` · 写入
- **触发/适用条件**：任意模块记录
- **图与正文位置**：§5.2.1
- **正常出口**：行写入
- **异常出口**：静默（不阻塞）

#### 7.2 `P-LOG-QUERY` · 查询
- **触发/适用条件**：`GET /v1/logs`
- **图与正文位置**：§5.1.2
- **正常出口**：`{data,page}`
- **异常出口**：存储错误 → 503

## 8. 关键算法与业务规则

#### 8.1 `RULE-LOG-REDACT` · 写前脱敏
- **输入前提 / 适用条件**：任意写入
- **算法 / 规则 / 选择依据**：`_SENSITIVE = (?i)(authorization|bearer\s+\S+|secret|api[_-]?key|token\s*[=:]\s*\S+)` → `[REDACTED]`；换行折叠；`[:512]`
- **结果 / 不变量 / 边界**：落库文本不含匹配敏感串
- **复杂度 / 资源限制**：O(len)
- **允许替换范围 / 不可改变保证**：正则可自选；写前脱敏不可变
- **具体输入推演 / 验证项**：`Authorization: Bearer x` → `Authorization: [REDACTED]`；`VRC-LOG-001`

#### 8.2 `RULE-LOG-ORDER` · 查询顺序与上限
- **输入前提 / 适用条件**：查询
- **算法 / 规则 / 选择依据**：`ORDER BY created_at DESC,id DESC`；`limit ≤ 200`
- **结果 / 不变量 / 边界**：稳定倒序
- **复杂度 / 资源限制**：O(limit)
- **允许替换范围 / 不可改变保证**：实现可自选；顺序/上限不可变
- **具体输入推演 / 验证项**：`limit=1000` → 200；`VRC-LOG-001`

## 9. 接口设计

> 按 STD `design-data-interface-format` 1.2.0 §3：主章“接口设计”，按**接口设计用途**分类（面向使用方的 API 与组件/系统间协作的消息与数据流接口），逐接口完整记录；标题为真实调用形式，标题下先给**完整接口声明**，再就地说明参数/结果字段，最后按固定六项。本模块接口全部为进程内方法调用，归 API；消息流/硬件/人机三类不适用。数据结构引用 §6。`OperationalLog`（`src/log/logs.py`）为唯一对外面。

### 9.1 API（适用时）

#### `OperationalLog.record(level, module, event, message, request_id=None) -> None`

```text
record(level: str, module: str, event: str, message: str, request_id: str | None = None) -> None
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-LOG-RECORD`；写入一条写前脱敏运行日志；M008 `log` 提供；状态=Implemented；唯一契约=本设计；文件·symbol `src/log/logs.py` `OperationalLog.record`。
- **输入与前提**：`level: str`（∈§6.1 `LogLevel`）、`module: str`、`event: str`、`message: str`（任意文本，写前脱敏/截断）、`request_id: str|None`；无鉴权前提（基础层）。
- **成功输出与保证**：无返回；受理即向 `operational_logs`（§6.7）插入一行；副作用=持久一行脱敏日志。
- **错误与合法下一步**：写失败 → **fail-open**：不抛、不产生公共错误，调用方静默；结果已知性=丢失该条日志；无半写。
- **交互与生命周期**：同步；使用调用方线程；无期限；不幂等（每次一行）；单条 `INSERT`，不另开事务。
- **实现与验证**：正常 `record("info","m","e","hello")`；边界：`message` 含 `Authorization` → 落库为 `[REDACTED]`。`VRC-LOG-001`；`src/log/logs.py`。

#### `OperationalLog.page(limit=50, level=None, module=None, request_id=None, since=None, until=None) -> dict`

```text
page(limit: int = 50, level: str | None = None, module: str | None = None, request_id: str | None = None, since: str | None = None, until: str | None = None) -> dict
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-LOG-QUERY`；按条件分页查询运行日志；M008 提供；状态=Implemented；唯一契约=本设计；文件·symbol `src/log/logs.py` `OperationalLog.page`。
- **输入与前提**：`limit: int`（夹 `[1,200]`）；`level/module/request_id: str|None`（等值过滤）；`since/until: str`（**均必填**，`created_at` 半开窗）。
- **成功输出与保证**：返回 §6.2.2 `LogPage`，按 `created_at DESC,id DESC`；只返回已脱敏字段，不返回正文/凭据。
- **错误与合法下一步**：缺 `since`/`until` → `ApiError(400,"invalid_request")`（系统 `ERR-REQ-VALIDATION`）；存储不可读 → 原生 `sqlite3.Error` 冒泡，由 M004/M001 映射 `ApiError(503,"usage_store_unavailable")`（系统 `ERR-STORE`）；调用方稍后重试，不伪装空页。
- **交互与生命周期**：同步只读；`limit ≤200`；幂等。
- **实现与验证**：正常 `page(level="error")`；边界：无匹配 → `{data:[],page:{has_more:false,next_cursor:null}}`。`VRC-LOG-001`；`src/log/logs.py`。

### 9.2 消息与数据流接口（适用时）

不适用：本模块为进程内库，不拥有事件/队列/流/file exchange；写入为同步方法调用（tailoring：M008 只提供函数能力，不承载跨边界协作）。

### 9.3 硬件与固件接口（适用时）

不适用（无连接器/总线/寄存器/FPGA 端口）。

### 9.4 人机与维护接口（适用时）

不适用（无 UI/CLI；日志查询入口归 M001 `GET /v1/logs`、呈现归 M002）。

## 10. 并发、失败与恢复

#### 10.1 `F-LOG-WRITE` · 写入失败
- **初始条件 / 并发交错 / 失败点**：Store 错误
- **检测事实 / authority / 期限**：异常
- **处理行为 / 副作用边界**：静默；不阻塞业务
- **状态查询 / 同请求重放 / 接管 / 新业务重试**：N/A + 理由：尽力而为
- **最终状态 / 资源归属 / 后续合法入口**：缺失日志
- **验证项 / 组合责任**：`VRC-LOG-001`

#### 10.2 `F-LOG-QUERY` · 查询失败
- **初始条件 / 并发交错 / 失败点**：存储不可读
- **检测事实 / authority / 期限**：Store 异常
- **处理行为 / 副作用边界**：503（不伪装空页）
- **状态查询 / 同请求重放 / 接管 / 新业务重试**：稍后重试
- **最终状态 / 资源归属 / 后续合法入口**：503
- **验证项 / 组合责任**：`VRC-LOG-001`

## 11. 安全、权限与可观测性

- **脱敏**：写前完成，任何查询结果都不含敏感串（§8.1）
- **禁止**：Prompt/模型输出/reasoning 正文/Embedding 向量/Authorization/Secret/完整请求头
- **权限**：不鉴权（基础层）；访问控制由 M001/M004

## 12. 容量、性能与运行限制

#### 12.1 `CAP-LOG-MSG` · 单条消息
- **目标 / 限制 / 单位**：≤ 512 字符（截断后）
- **适用版本 / 配置 / 硬件 / 虚拟化 / 依赖**：`record`
- **负载、数据规模与并发口径**：单条
- **推导 / 测量方法与证据等级**：Specified
- **共享资源扣减 / 峰值重叠 / 余量**：—
- **超限行为 / 责任出口**：截断
- **验证项 / Evidence**：`VRC-LOG-001`；NOT_RUN

#### 12.2 `CAP-LOG-QUERY` · 查询上限
- **目标 / 限制 / 单位**：`limit ≤ 200`
- **适用版本 / 配置 / 硬件 / 虚拟化 / 依赖**：`page`
- **负载、数据规模与并发口径**：单查询
- **推导 / 测量方法与证据等级**：Specified
- **共享资源扣减 / 峰值重叠 / 余量**：—
- **超限行为 / 责任出口**：上限截断
- **验证项 / Evidence**：`VRC-LOG-001`；NOT_RUN

## 13. 实现步骤与文件清单

### 13.1 文件分解（设计 → 代码文件）

#### 13.1.1 `src/log/logs.py`
- **职责 / 非职责**：I1 写前脱敏写入、I2 过滤查询；不含审计/观测
- **关键 symbol / 导出范围**：`OperationalLog.record/page`、`_SENSITIVE`
- **承接 Function / Rule / Constraint / Interface ID**：`F-LOG-WRITE/QUERY`、`RULE-LOG-REDACT/ORDER`、脱敏约束、`IF-LOG`
- **构建目标 / 依赖 / 宿主装配**：随 `Application`；依赖 Store
- **实现状态**：Implemented
- **验证入口**：`VRC-LOG-001`

#### 13.1.2 `src/util/migrations/001_initial.sql`（日志表）
- **职责 / 非职责**：`operational_logs` 表；不含逻辑
- **关键 symbol / 导出范围**：`operational_logs`
- **承接 Function / Rule / Constraint / Interface ID**：`F-LOG-WRITE`
- **构建目标 / 依赖 / 宿主装配**：由 `Store.migrate`
- **实现状态**：Implemented
- **验证入口**：`VRC-LOG-001`

### 13.2 实现步骤

#### 13.2.1 写前脱敏
- **前置输入 / 依赖**：`_SENSITIVE`
- **新增 / 修改文件与 symbol**：`logs.py`
- **固定语义 / 可自行决定范围**：写前脱敏固定；正则可自选
- **交付结果**：脱敏写入
- **完成检查**：`VRC-LOG-001`

#### 13.2.2 过滤查询
- **前置输入 / 依赖**：`operational_logs`
- **新增 / 修改文件与 symbol**：`logs.py` `page`
- **固定语义 / 可自行决定范围**：顺序/上限固定；实现可自选
- **交付结果**：`{data,page}`
- **完成检查**：`VRC-LOG-001`

## 14. 测试与验收

#### 14.1 `VRC-LOG-001` · 脱敏与查询
- **覆盖 Function / Rule / Constraint / Interface**：`F-LOG-WRITE/QUERY`、`RULE-LOG-REDACT/ORDER`、脱敏约束、`IF-LOG`
- **Case / 正常、边界与失败输入**：含 `Authorization: Bearer …`/`api_key: x`/`token=…` 的消息；超长；过滤查询
- **环境 / 配置 / 隔离与复位**：隔离库
- **独立 Oracle / Expected**：落库文本含 `[REDACTED]`；长度 ≤512；顺序倒序
- **Actual / Evidence / Run ID**：NOT_RUN
- **Verdict / 状态**：NOT_RUN
- **父级组合验证交接**：M004/M002

## 15. 风险、未决问题与引用

#### 15.ISD · 实现规格采用方式
- **采用模式**：`separate`（模块设计不兼作 ISD）
- **模块对象 ID**：M008
- **实现规格 Document ID**：`log-isd`
- **metadata 覆盖映射入口**：`log-isd` 的 `implementation_specification.coverage_mapping`
- **理由 / 决定引用**：本文已含文件/符号/语义/验证

#### 15.1 `RISK-LOG-1` · 脱敏正则漏网
- **类型 / 影响的规则、接口、流程或约束**：Risk；影响 §8.1
- **事实缺口 / 触发条件**：出现未覆盖的凭据形态
- **影响 / 阻塞边界**：潜在泄漏；不阻塞设计
- **Owner / 最晚关闭 Gate**：LLMTier / 安全评审
- **选项 / 推荐 / 下一步取证**：补充正则；禁记正文作为兜底
- **关闭条件 / 决定或当前状态**：观察

引用：系统设计 §3.2/§11.3；`src/log/logs.py`；`migrations/001_initial.sql`。

## 附录 A. 机制承接表

**N/A — 本模块不参与任何机制。** 父系统机制清单核对结果：M-TRUST/M-INFER/M-METER/M-CONFIG/M-OBS 的 §14.4 均未向 `log` 分配 Requirement ID（日志属基础能力，由各机制在需要处引用 M008 §9）。Tailoring/决定依据：系统设计 §3.2 将 `log` 登记为独立基础模块，但其写入/查询不在任一机制的跨模块协作语义内；批准记录见本轮 review。若后续某机制新增日志写入要求（如可观测性要求特定事件），须回到该机制 §14.4 分配 Requirement ID 后在此承接。
