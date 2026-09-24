# HANDOFF：STD 全设计文档《数据结构 / 接口》描述格式修改意见

- 日期：2026-09-24
- 提出方：LLMTier（`corezilla/LLMTier`，branch `docs/std-draft21-upgrade`）
- 接收方：STD 维护方（`/Users/ben/work/STD`，STD `0.1.0-draft.31`）
- 触发：按 `design.definition` 编写 LLMTier 模块设计，§6 数据模型 / §9 接口与机器契约逐条落到**字段级**、并用于给其它模块写实现与测试用例后的实证
- 证据：`docs/40_module_design/libdiag-design.md` §5.3/§6/§9.1/§9.2（8 个模块设计样板）；`src/libdiag/*.py` + `src/util/migrations/002_observability.sql`（逐项对照校验）

## 0. 一句话任务

把**数据结构的固定格式**与**接口的固定格式**升为 STD 通用规范，**所有设计文档**的数据/接口章节统一采用；并按文档类型规定各自应描述的数据结构与接口（见 §3 表，含各模板的实际章节号）。请按下文 **P0/P1** 修改模板与配套设施。

## 1. 背景与基线

- STD 多个设计模板都含"数据 / 接口"章节，但**格式各异、粒度不一**，消费方无法据此直接编码或写用例。各模板的实际落点：
  - `design.system`（architecture）：§9 数据、描述符与存储结构；§10 接口与通信协议（§10.1 接口总表、§10.5 公共数据结构与编码）
  - `design.software-system`：§8 数据与存储设计；§9 接口与通信协议（§9.2 单项操作、类型与错误实例）
  - `design.system-mechanism`：§4 数据结构设计；§5 接口设计；§14.3 责任单元间接口契约
  - `design.subsystem`：§5 数据与状态设计；§6 接口设计与 interfaces 映射
  - `design.definition`（模块）：§6 数据模型；§9 接口与机器契约；§5.3 文件间接口契约
  - `design.data-dictionary`：§3 Entity/Object Catalog；§4 Field Dictionary；§5 Enum/Status/Error；§6 Identity/Key/Ownership
  - `design.implementation`（ISD）：§4 内部数据与所有权；§5 函数与接口实现规格
  - `design.hardware` / `design.fpga`：数据/接口节（板级/端口级）
  - `contracts.specification`：§2 Operation/Message/Event Catalog；§3 Request/Response/Event 与数据对象（§5 幂等/并发/事务、§8 版本/兼容为契约专有）
  - `interfaces.control`：§2 接口注册表；§4 数据、命令与 Schema（§6 错误/超时/重试/幂等、§9 版本/兼容为契约专有）
- LLMTier 在 `libdiag-design.md` 试点：§9.1 数据结构（11 个，4 段）、§9.2 接口（15 个，6 段）、§6 数据模型（6 表，4 段）、§5.3 文件间接口（6 段）。一次 correctness review 据此逐项对照代码，纠正了可空性等 7 处——证明该格式**可校验、可交付**。
- 原则：**数据结构与接口分开描述**（被复用结构只描述一次）、**同一对象只有一处字段级 authority**、**粒度自外向内**。

## 2. 建议清单

### P0 — 统一两套固定格式（全局）

| # | 位置 | 问题 | 建议 |
|---|---|---|---|
| **F1 数据结构固定格式** | 所有设计文档的数据结构/数据模型/数据字典节 | 字段描述格式不一，字段级信息常缺失 | 统一 **4 段**：`定义` / `字段`（逐字段行：`名称`：`类型`｜必填性｜范围·枚举·单位｜说明）/ `不变量` / `来源`。见 §4.1 |
| **F2 接口固定格式** | 所有设计文档的接口/契约节 | 接口缺逐参数/逐字段/返回值条件，消费方无法写用例 | 统一 **6 段**：`功能` / `输入`（逐参数行）/ `输出`（数据结构 ID）/ `返回值`（每条件一行）/ `统计 · 日志` / `数据库`。见 §4.2。后两段**适用时**；非持久/非软件接口写 `无`/`N/A` |
| **F3 分离与复用规则** | 全文 | 结构被逐接口重复描述 | 数据结构与接口**分节**；被复用结构只在一处描述，接口用 **ID 引用**；字段级 authority 唯一（`interfaces/*` 或 `design.data-dictionary`），设计文档与之一致 |
| **F4 文档/领域变体** | 硬件/FPGA + 契约模板 | 软件口径不适用 | ①硬件/FPGA：接口后两段换 `时序 · 资源` / `持久化 · 寄存器`，字段行以 `位宽 / 端序 / 复位值` 替代软件类型；②**契约类**（`contracts.specification`/`interfaces.control`）：接口除 F2 六段外**补契约专有段** `幂等 · 并发 · 事务`、`版本 · 兼容 · 弃用`，或保留契约现有固定节，F1/F2 只覆盖其中的数据对象与操作 |

### P0 — 各模板必填语义与分工（含章节号）

| # | 位置 | 问题 | 建议 |
|---|---|---|---|
| **D1 `design.data-dictionary`** | §3/§4/§5/§6 | 已承载字段级 authority，但未规定固定格式，也未声明与其它设计文档的关系 | 与 F1 对齐并**声明为字段级 authority**；其它文档的数据结构**引用**它，不复制两份 |
| **D2 `design.definition`（模块）** | §6 数据模型 / §9 接口与机器契约 / §5.3 文件间接口 | §6/§9 字段要求不完整；文件间接口无固定格式 | §6 用 F1；§9 用 F2（对外接口）；§5.3 用 F2（文件间接口）；对外可复用结构放数据结构节、只描述一次 |
| **D3 `design.implementation`（ISD）** | §4 内部数据与所有权 / §5 函数与接口实现规格 | 内部数据与函数契约格式不统一，易与模块设计重复 | §4 私有数据（文件内类型/内存对象/表/状态机）用 F1；§5 函数契约沿用现字段并**引用**模块设计结构 ID；"数据库"落到具体表列 |
| **D4 `design.system-mechanism`** | §4 数据结构设计 / §5 接口设计 / §14.3 | 格式不统一 | §4 用 F1（状态/消息/阶段）；§5 与 §14.3 用 F2 |
| **D5 `design.software-system`** | §8 数据与存储设计 / §9 接口与通信协议 | 系统级边界数据/接口粒度未定，易与模块设计重复 | 用 F1/F2 但**只到跨边界必需字段**；接口指向 `contracts.specification`，不复制 wire 细节 |
| **D6 `design.subsystem`；`design.system`（架构）** | subsystem §5/§6；architecture §9/§10 | 子系统与架构两级都要用，但粒度不同（现模板 architecture **已有详细 §9/§10**，非仅索引） | 子系统（§5/§6）用 F1/F2（对外暴露对象/接口）；架构 `design.system`（§9/§10）**按层级**：单系统/板卡可到字段级，**平台/多系统**才降为对象/接口**目录索引**（名称/owner/权威文档/方向） |
| **D7 `contracts.specification` / `interfaces.control`** | contracts §2/§3；interfaces.control §2/§4 | 若仅用 F2 会丢失契约专有语义 | 数据对象用 F1、操作用 F2 **+ 契约专有段**（contracts §5 幂等/并发/事务、§8 版本/兼容；interfaces.control §6 错误/超时/重试/幂等、§9 版本/兼容）；F2 的 `数据库` 段对契约写 `N/A` |

### P1 — 校验、迁移与示例

| # | 位置 | 问题 | 建议 |
|---|---|---|---|
| **V1 校验器** | `validate-design` | 格式无法校验 | 对采用该格式的章节：每个数据结构含 4 段、每个接口含 6 段（契约类允许额外专有段）且 `返回值`/`数据库` 非空；字段行/参数行按 `｜` 分列 |
| **V2 共享指南** | `docs/ai-guides/` | 格式无单一出处 | 新增 `design-data-interface-format.md` 承载 §3 表与 §4 格式；各模板引用 |
| **V3 迁移** | 各模板 | 直接必填会打断既有项目 | 先设"推荐"，稳定后改"必需"，并提供 F1/F2 示例 |
| **V4 示例** | 示例节 | 现有示例未示范 | `libdiag-design.md` §5.3/§6/§9 作模块级范例；data-dictionary 另给 F1 范例 |

## 3. 每种设计文档应描述的数据结构与接口

| 设计文档（template） | 数据 / 接口章节 | 应描述的**数据结构** | 应描述的**接口** | 粒度 |
|---|---|---|---|---|
| 架构设计 `design.system` | §9 数据、描述符与存储结构；§10 接口与通信协议（§10.5 公共数据结构与编码） | 平台/多系统：对象/接口**目录索引**；单系统/板卡：字段级 | 接口总表（§10.1）；单系统/板卡可到操作级 | 索引级～字段级（按层级） |
| 软件系统设计 `design.software-system` | §8 数据与存储设计；§9 接口与通信协议（§9.2 操作/类型/错误实例） | **系统级对外数据对象**（跨边界顶层对象） | **系统边界接口**（责任模块 + 权威契约引用） | 跨边界必需字段 |
| 系统机制设计 `design.system-mechanism` | §4 数据结构设计；§5 接口设计；§14.3 责任单元间接口契约 | 机制**状态与消息**（状态机/事件/阶段/判定事实） | **参与方交互**（每步发起/接收、输入/输出/失败出口） | 机制内部必需 |
| 子系统设计 `design.subsystem` | §5 数据与状态设计；§6 接口设计与 interfaces 映射 | 子系统**对外暴露数据对象**（类型/枚举/状态） | **子系统对外接口**（被谁调用、提供/消费、依赖方向） | 子系统边界 |
| **模块/组件设计** `design.definition` | §6 数据模型；§9 接口与机器契约；§5.3 文件间接口契约 | 模块**对外可复用结构**（视图/DTO/枚举/开关）：F1，复用只描述一次 | **模块对外接口**（F2）+ **文件间接口**（F2） | 字段级（对外） |
| **数据字典** `design.data-dictionary` | §3 Entity/Object Catalog；§4 Field Dictionary；§5 Enum/Status/Error；§6 Identity/Key/Ownership | **字段级权威**（Entity/Field/Enum/Key/Ownership/序列化/持久化）：F1 | 只被接口**引用**，不描述 | 字段级（权威） |
| **实现规格（ISD）** `design.implementation` | §4 内部数据与所有权；§5 函数与接口实现规格 | 模块**内部私有数据**（文件内类型/内存对象/表/状态机）：F1 | **关键函数实现契约**（签名/参数/成功·错误返回/前置/副作用/幂等/并发）；对外结构引用模块设计 ID | 函数级（私有） |
| 硬件设计 `design.hardware` | 数据/接口节 | 板级**寄存器/接口信号/时序参数**（F1 变体） | 板级**连接器/总线协议/引脚**（F2 变体） | 板级 |
| FPGA 设计 `design.fpga` | 数据/接口节 | RTL **接口信号/寄存器 map/状态**（F1 变体） | RTL **模块端口/握手协议**（F2 变体） | 端口级 |
| 接口契约 `contracts.specification` | §2 Operation/Message/Event Catalog；§3 请求/响应/事件与数据对象 | wire Schema（F1） | 操作契约（F2 + 契约专有段 §5/§8） | 字段级（权威） |
| 接口控制 `interfaces.control` | §2 接口注册表；§4 数据、命令与 Schema | 命令/数据 Schema（F1） | 接口契约（F2 + 契约专有段 §6/§9） | 字段级（权威） |

## 4. 两个固定格式（精确）

### 4.1 数据结构（4 段）

```markdown
#### <Data ID> · `<名称>`
- **定义**：<一句话语义、用途、边界>
- **字段**：
  - `名称`：`类型`｜必填性（必填 / 可空）｜范围·枚举·单位｜说明
- **不变量**：<跨字段约束、默认、唯一性、寿命>
- **来源**：<定义/产出该结构的权威位置（文件·symbol 或 schema 路径）>
```

### 4.2 接口（6 段）

```markdown
#### <Interface ID> · `<签名 / 操作名>`
- **功能**：<做什么、为谁、边界>
- **输入**：
  - `名称: 类型`｜必填·默认｜范围·枚举｜说明
- **输出**：<数据结构 ID（§数据） / 字节流 / 无>
- **返回值**：<每条件一行：`<条件> → <值>`；含错误码与其触发条件>
- **统计 · 日志**：<对外可见的统计/日志口径与触发；无则 `无`；适用时>
- **数据库**：<何种情况改哪些表/列；只读/无则 `只读`/`无`；适用时>
```

- 时间统一 RFC3339（UTC，毫秒）；`?` 表示可空。

## 5. 验收 Gate

1. **G1**：两套固定格式（F1/F2）写入共享指南 `docs/ai-guides/design-data-interface-format.md`，并被各设计模板对应章节引用。
2. **G2**：§3 表随模板落地；每个模板明确"本层应描述的数据结构与接口 + 章节号 + 粒度"。
3. **G3**：数据结构与接口分节、复用结构只描述一次、字段级 authority 唯一（互不复制）。
4. **G4**：`validate-design` 支持 4 段/6 段与字段行/参数行的机械校验；`返回值`/`数据库` 非空（契约类允许额外专有段）。
5. **G5**：硬件/FPGA（F4①）与契约类（F4②）有明确的格式变体说明。
6. **G6**：`libdiag-design.md` §5.3/§6/§9 可直接套用修订后的模块模板（作为官方模块级示例）。

## 6. 证据与环境

| 项 | 值 |
|---|---|
| 模块设计样本 | `docs/40_module_design/libdiag-design.md`（§5.3/§6/§9.1/§9.2） |
| 代码对照 | `src/libdiag/{settings,traces,snapshots,stats,injections,stream,retention,common,diagnostics}.py` |
| DDL 对照 | `src/util/migrations/002_observability.sql` |
| 模板 | `/Users/ben/work/STD/templates/design/{architecture-design,software-system-design,system-mechanism-design,subsystem-design,design-definition,data-dictionary,implementation-design,hardware-design,fpga-design}.md`；`/Users/ben/work/STD/templates/contracts/contract-specification.md`；`/Users/ben/work/STD/templates/interfaces/interface-control.md` |
| 版本 | STD `0.1.0-draft.31`（`dbcf87a`） |
