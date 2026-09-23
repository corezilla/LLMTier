<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier M008 log 模块设计

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

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
| Last Modified Date | `2026-09-23` |
| Template ID | `design.definition` |
| Template Version | `2.4.0` |
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
- **输入与前提**：`limit` + 可选 `level/module/request_id` + `since/until`
- **行为**：条件查询，按时间倒序
- **输出**：`{data[], page}`
- **错误与边界**：缺时间 → 由调用方校验
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

#### 5.3.1 `IF-LOG-01` · 业务模块 → `logs.py`
- **签名 / 入口**：`OperationalLog.record(level, module, event, message, request_id=None)`、`page(...)`
- **输入与前置条件**：—（message 可为任意文本）
- **输出 / 异常**：行 / `{data,page}`
- **ownership / 生命周期**：持久（`operational_logs`）
- **实现与验证位置**：`logs.py`；`VRC-LOG-001`

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

## 6. 数据模型、状态与 ownership

#### 6.1 `LogEvent`（`operational_logs`）
- **Authority / 定义位置**：`logs.py` + `001_initial.sql`
- **字段**：`id`、`created_at`、`level`、`module`、`event`、`message(≤512,已脱敏)`、`request_id`
- **键与跨字段约束**：`message` 写前脱敏；不含正文/凭据
- **Writer / Reader**：I1 写；I2 读
- **创建、持有、借用/复制与释放**：持久；保留期由运维
- **状态转换 / 并发规则**：只追加
- **验证项**：`VRC-LOG-001`

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

## 9. 接口与机器契约

#### 9.1 `IF-LOG` · `OperationalLog` API
- **Direction / Operation / 责任模块 / backend**：in；`record`/`page`；M008；Store
- **Request / Response / Error / ownership**：写入字段 / 过滤条件 → 行/页
- **Contract authority / version / revision / hash / selector**：本文 §6.1
- **前提 / timeout / 兼容边界 / Error model**：字段名固定；错误由调用方映射
- **本地文件 / symbol 或 NOT_IMPLEMENTED**：`logs.py`
- **Constraint / VRC / Case / 环境 / Run**：脱敏约束（§1.1.1）、机制 M-OBS；`VRC-LOG-001`；NOT_RUN
- **关联类型字段 ID**：`LogEvent`（§6.1）

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

#### 13.1.1 `src/llmtier_v03/logs.py`
- **职责 / 非职责**：I1 写前脱敏写入、I2 过滤查询；不含审计/观测
- **关键 symbol / 导出范围**：`OperationalLog.record/page`、`_SENSITIVE`
- **承接 Function / Rule / Constraint / Interface ID**：`F-LOG-WRITE/QUERY`、`RULE-LOG-REDACT/ORDER`、脱敏约束、`IF-LOG`
- **构建目标 / 依赖 / 宿主装配**：随 `Application`；依赖 Store
- **实现状态**：Implemented
- **验证入口**：`VRC-LOG-001`

#### 13.1.2 `src/llmtier_v03/migrations/001_initial.sql`（日志表）
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
- **采用模式**：`embedded`
- **模块对象 ID**：M008
- **实现规格 Document ID**：`log`（本文）
- **metadata 覆盖映射入口**：§5/§6/§9/§10/§13/§14
- **理由 / 决定引用**：本文已含文件/符号/语义/验证

#### 15.1 `RISK-LOG-1` · 脱敏正则漏网
- **类型 / 影响的规则、接口、流程或约束**：Risk；影响 §8.1
- **事实缺口 / 触发条件**：出现未覆盖的凭据形态
- **影响 / 阻塞边界**：潜在泄漏；不阻塞设计
- **Owner / 最晚关闭 Gate**：LLMTier / 安全评审
- **选项 / 推荐 / 下一步取证**：补充正则；禁记正文作为兜底
- **关闭条件 / 决定或当前状态**：观察

引用：系统设计 §3.2/§11.3；`src/llmtier_v03/logs.py`；`migrations/001_initial.sql`。

## 附录 A. 机制承接表

**N/A — 本模块不参与任何机制。** 父系统机制清单核对结果：M-TRUST/M-INFER/M-METER/M-CONFIG/M-OBS 的 §14.4 均未向 `log` 分配 Requirement ID（日志属基础能力，由各机制在需要处引用 M008 §9）。Tailoring/决定依据：系统设计 §3.2 将 `log` 登记为独立基础模块，但其写入/查询不在任一机制的跨模块协作语义内；批准记录见本轮 review。若后续某机制新增日志写入要求（如可观测性要求特定事件），须回到该机制 §14.4 分配 Requirement ID 后在此承接。
