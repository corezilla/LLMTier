<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier M005 Observability 实现规格设计（ISD）

> STD 使用入口：[项目采用说明与标准导航](../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `observability-isd` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Document Owner | LLMTier |
| Last Modified Date | `2026-09-23` |
| Template ID | `design.implementation` |
| Template Version | `0.3.0` |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 实现目标与输入基线

<a id="isd-scope"></a>

### 1.1 实现对象

- **模块 ID / 名称**：M005 / Observability
- **直属父对象 / 父设计**：LLMTier 软件系统 / `llmtier-system-design`（§3.2 登记）
- **模块设计 Document ID / 版本 / 路径 / 摘要**：`observability` / `0.1.0-draft.2` / `docs/40_module_design/observability-design.md` / §2 F-OBS-*、§5.1 I1–I4、§8 RULE-OBS-*
- **需求与 Constraint ID**：`C-OBS-1`（默认关零开销）、`C-OBS-2`（fail-open）、`C-OBS-3`（不记 Secret/正文）、`C-OBS-4`（注入标注）、`C-OBS-5`（libdiag 提供/Observability 呈现）；机制 `R-OBS-02`
- **实现范围 / 非目标**：实现诊断查询与呈现（快照/统计/注入/trace/traces）、开关切换、关联标识透传；**非目标**：观测记录底层读写（M006）、HTTP 传输（M001）、页面渲染细节（M002）
- **ISD 默认落位或项目批准路径**：`docs/50_implementation_design/observability.isd.md`

### 1.2.1 `HO-OBS-01` · 观测查询与开关呈现

- **上游信息项 / 规则 ID**：`R-OBS-02`
- **固定来源 / 版本 / 锚点 / 摘要**：机制 `M-OBS` §14.4 `R-OBS-02`
- **ISD 细化内容 / 章节**：诊断路由、查询整形、开关切换 → §5.1.1–5.1.4
- **唯一权威位置**：行为在 M-OBS §14.4；本层管落实
- **实现自由度**：呈现实现
- **原 V/Case 及本地验证位置**：`VRC-OBS-001..005` → §9.1

### 1.2.2 `HO-OBS-02` · 关联标识透传

- **上游信息项 / 规则 ID**：`R-OBS-04`
- **固定来源 / 版本 / 锚点 / 摘要**：机制 `M-OBS` §14.4 `R-OBS-04`
- **ISD 细化内容 / 章节**：接收/回显（仅提供时）→ §5.1.5
- **唯一权威位置**：行为在 M-OBS §14.4；本层管落实
- **实现自由度**：解析实现
- **原 V/Case 及本地验证位置**：`VRC-OBS-004` → §9.1

### 1.2.3 `HO-OBS-03` · 诊断页面数据

- **上游信息项 / 规则 ID**：`R-OBS-05`（经 M002）
- **固定来源 / 版本 / 锚点 / 摘要**：机制 `M-OBS` §14.4 `R-OBS-05`
- **ISD 细化内容 / 章节**：4 tabs + 开关数据 → §5.1.6
- **唯一权威位置**：行为在 M-OBS §14.4；本层管数据供给
- **实现自由度**：数据装载实现
- **原 V/Case 及本地验证位置**：`VRC-OBS-005` → §9.1

## 2. 既有实现差异（条件章节）

<a id="isd-current-target"></a>

### 2.1 适用性

- **适用性**：`not_applicable`
- **依据**：greenfield/设计先行
- **Tailoring / 范围决定引用**：`std-tailoring`（设计先行）

## 3. 文件、内部组件与调用关系

<a id="isd-structure"></a>

```text
app.py            # 诊断路由：/v1/diagnostics*、/v1/trace/{id}、/v1/deployments/{id}/diagnostics
webui/app.js      # /ui/diagnostics 4 tabs + 全局开关（属 M002，本模块供数据）
diagnostics.py    # 查询方法：switches/set_switches/snapshots_page/stats/trace/traces/injections/set_injections
```

### 3.1 `app.py`（诊断路由）

- **职责及调用者**：诊断端点路由、开关/注入经审计、关联标识透传；caller=HTTP 客户端
- **类型 / 函数**：`/v1/diagnostics`、`/v1/diagnostics/snapshots`、`/v1/diagnostics/stats`、`/v1/diagnostics/traces`、`/v1/deployments/{id}/diagnostics`、`/v1/trace/{request_id}` 分支
- **可见性**：public（端点）
- **调用与类型依赖**：调用 `DiagnosticsService`；`admin.mutate`（写）
- **构建目标 / 生成源 / 输出**：随 M001 进程
- **实现状态**：PLANNED

### 3.2 `diagnostics.py`（查询）

- **职责及调用者**：本模块消费查询方法；记录读写归 M006
- **类型 / 函数**：`switches`、`snapshots_page`、`stats`、`trace`、`traces`、`injections`
- **可见性**：private
- **调用与类型依赖**：`Store`
- **构建目标 / 生成源 / 输出**：随包
- **实现状态**：PLANNED

### 3.3 `webui/app.js`（诊断页）

- **职责及调用者**：诊断页 4 tabs + 开关数据装载；caller=浏览器
- **类型 / 函数**：`loadStats`/`loadTrace`/注入读写（见 M002）
- **可见性**：public（静态资源）
- **调用与类型依赖**：经 M001 同源
- **构建目标 / 生成源 / 输出**：静态资源
- **实现状态**：PLANNED

## 4. 内部数据与所有权

<a id="isd-data"></a>

纯软件：无原生 ABI（HTTP/JSON）。

### 4.1 `DiagnosticSnapshotView` / `TraceView`

- **类型 / 字段**：SnapshotView `{id,request_id,captured_at,upstream_url,backend_model,http_status,latency_ms,error_summary,model,deployment_id,snapshot_type}`；TraceView `{request_id,correlation_id?,stages[],snapshot?,usage?}`
- **单位 / 初值 / 范围 / 不变量**：URL 去 query；summary ≤256B；stages 有序
- **逻辑编码与原生 ABI 适用性**：N/A + 依据（OpenAPI JSON）
- **创建 / 修改者**：M006 写；本模块读
- **Owner / 借用期限 / 释放者**：请求级视图
- **公共类型 authority**：OpenAPI / M006 表契约
- **持久化与敏感性**：transient 视图；脱敏

### 4.2 `StatsView` / `InjectionView` / 开关状态

- **类型 / 字段**：StatsView `{request_count,error_count,status_breakdown,error_4xx_count,error_5xx_count,p50,p95,min,max,avg}`；InjectionView `{id,deployment_id,injection_type,enabled,config}`；开关 `{snapshots_enabled,stats_enabled}`
- **单位 / 初值 / 范围 / 不变量**：`status_breakdown` per-status；开关默认 false
- **逻辑编码与原生 ABI 适用性**：N/A
- **创建 / 修改者**：M006；本模块读写
- **Owner / 借用期限 / 释放者**：请求级视图
- **公共类型 authority**：本 ISD
- **持久化与敏感性**：transient 视图

## 5. 函数与接口实现规格

<a id="isd-functions"></a>

### 5.1.1 `FUNC-OBS-SWITCH` · 开关

- **文件 / symbol / 可见性**：`app.py`（路由）+ `diagnostics.py` `switches/set_switches` / public 端点
- **原成员 ID 或私有来源**：`F-OBS-SWITCH`、`R-OBS-02`
- **完整签名与 caller**：`GET/PATCH /v1/diagnostics`；caller=operator
- **输入参数 / 数据结构 authority**：PATCH `{snapshots_enabled?, stats_enabled?}`
- **输入约束 / 校验顺序 / 失败映射**：部分更新；经 `admin.mutate` 审计
- **成功输出 / 数据结构 / 后置条件**：开关状态
- **错误输出 / 触发条件 / 优先级**：401/403（入口）
- **副作用 / 执行上下文 / 幂等性**：写开关（经 M006）
- **输入输出 ownership 与寿命**：持久（M006）
- **不可改变的规则 / Constraint ID**：默认关；关闭零写入
- **实现自由度**：路由实现
- **Thread-safe / reentrant**：每请求线程
- **Nested-call policy**：allowed
- **Transaction participation**：joins existing（mutate）
- **Blocking / timeout / cancellation**：`timeout=10`
- **实现状态 / 验证项**：PLANNED；`VRC-OBS-001`

### 5.1.2 `FUNC-OBS-QUERY` · 查询路由

- **文件 / symbol / 可见性**：`app.py`（route）+ `diagnostics.py`（query）
- **原成员 ID 或私有来源**：`F-OBS-SNAPSHOTS/STATS/TRACE/TRACES`
- **完整签名与 caller**：`GET /v1/diagnostics/snapshots|stats|traces`、`GET /v1/trace/{id}`；caller=operator/consumer
- **输入参数 / 数据结构 authority**：查询参数
- **输入约束 / 校验顺序 / 失败映射**：时间窗必填（stats）；cursor 校验；失败 → `E-OBS-QUERY`
- **成功输出 / 数据结构 / 后置条件**：视图
- **错误输出 / 触发条件 / 优先级**：400（缺时间/cursor）、503（存储不可用）
- **副作用 / 执行上下文 / 幂等性**：只读；幂等
- **输入输出 ownership 与寿命**：请求级
- **不可改变的规则 / Constraint ID**：脱敏；503 不伪装空结果
- **实现自由度**：呈现实现
- **Thread-safe / reentrant**：每请求线程
- **Nested-call policy**：allowed
- **Transaction participation**：none
- **Blocking / timeout / cancellation**：`timeout=10`
- **实现状态 / 验证项**：PLANNED；`VRC-OBS-002/004`

### 5.1.3 `FUNC-OBS-INJECT` · 注入配置入口

- **文件 / symbol / 可见性**：`app.py`（route）+ `diagnostics.py` `set_injections/injections`
- **原成员 ID 或私有来源**：`F-OBS-INJECTIONS`、`R-OBS-02`
- **完整签名与 caller**：`GET/PATCH /v1/deployments/{id}/diagnostics`；caller=operator
- **输入参数 / 数据结构 authority**：注入项列表（部分更新）
- **输入约束 / 校验顺序 / 失败映射**：白名单/范围（M006）；非法 → `E-OBS-INJECT`(400)
- **成功输出 / 数据结构 / 后置条件**：注入项列表
- **错误输出 / 触发条件 / 优先级**：400/404
- **副作用 / 执行上下文 / 幂等性**：写配置（经审计）
- **输入输出 ownership 与寿命**：持久（M006）
- **不可改变的规则 / Constraint ID**：白名单；确定性优先级
- **实现自由度**：转发实现
- **Thread-safe / reentrant**：每请求线程
- **Nested-call policy**：allowed
- **Transaction participation**：joins existing（mutate）
- **Blocking / timeout / cancellation**：`timeout=10`
- **实现状态 / 验证项**：PLANNED；`VRC-OBS-003`

### 5.1.4 `FUNC-OBS-PAGE` · 诊断页数据（M002）

- **文件 / symbol / 可见性**：`webui/app.js` / `loadStats`/`loadTrace`/注入（属 M002）/ public
- **原成员 ID 或私有来源**：`F-OBS-DIAG`（`R-OBS-05`）
- **完整签名与 caller**：`load*() -> Promise<void>`；caller=页面
- **输入参数 / 数据结构 authority**：查询参数
- **输入约束 / 校验顺序 / 失败映射**：失败 → I9
- **成功输出 / 数据结构 / 后置条件**：4 tabs 渲染
- **错误输出 / 触发条件 / 优先级**：见 I9
- **副作用 / 执行上下文 / 幂等性**：只读
- **输入输出 ownership 与寿命**：页面
- **不可改变的规则 / Constraint ID**：开关关闭 → Disabled
- **实现自由度**：呈现实现
- **Thread-safe / reentrant**：浏览器单线程
- **Nested-call policy**：allowed
- **Transaction participation**：none
- **Blocking / timeout / cancellation**：浏览器
- **实现状态 / 验证项**：PLANNED；`VRC-OBS-005`

### 5.1.5 `FUNC-OBS-CORR` · 关联标识

- **文件 / symbol / 可见性**：`app.py` / 关联标识处理 / public
- **原成员 ID 或私有来源**：`F-OBS-CORRELATION`、`R-OBS-04`
- **完整签名与 caller**：随请求头；caller=consumer
- **输入参数 / 数据结构 authority**：`X-Correlation-ID` / `traceparent`
- **输入约束 / 校验顺序 / 失败映射**：仅当 consumer 提供时回显
- **成功输出 / 数据结构 / 后置条件**：回显头 + trace detail
- **错误输出 / 触发条件 / 优先级**：缺省不影响
- **副作用 / 执行上下文 / 幂等性**：无
- **输入输出 ownership 与寿命**：请求级
- **不可改变的规则 / Constraint ID**：**仅提供时回显**
- **实现自由度**：解析实现
- **Thread-safe / reentrant**：每请求线程
- **Nested-call policy**：allowed
- **Transaction participation**：none
- **Blocking / timeout / cancellation**：——
- **实现状态 / 验证项**：PLANNED；`VRC-OBS-004`

### 5.2 错误传播矩阵

#### 5.2.1 `E-OBS-QUERY` · 查询失败

- **底层异常 / 失败事实**：存储不可读 / 缺时间
- **模块是否处理及处理函数**：reject/propagate
- **Typed 异常与原生异常所有权**：`ApiError(400/503)`；M001 映射
- **宿主 / public payload 或状态码**：400/503
- **日志级别 / 脱敏 / 关联字段**：warning
- **是否可重试及前提**：稍后重试
- **状态与副作用影响 / 验证项**：`VRC-OBS-002`

#### 5.2.2 `E-OBS-INJECT` · 注入非法

- **底层异常 / 失败事实**：非法类型/参数
- **模块是否处理及处理函数**：reject
- **Typed 异常与原生异常所有权**：`ApiError(400/404)`
- **宿主 / public payload 或状态码**：400/404
- **日志级别 / 脱敏 / 关联字段**：——
- **是否可重试及前提**：修参数
- **状态与副作用影响 / 验证项**：`VRC-OBS-003`

#### 5.2.3 `E-OBS-WRITE` · 观测写入失败

- **底层异常 / 失败事实**：记录写入失败（M006）
- **模块是否处理及处理函数**：recover（fail-open）
- **Typed 异常与原生异常所有权**：内部捕获
- **宿主 / public payload 或状态码**：——
- **日志级别 / 脱敏 / 关联字段**：warning
- **是否可重试及前提**：尽力而为
- **状态与副作用影响 / 验证项**：不改推理；`VRC-OBS-003`

## 6. 关键流程与算法

<a id="isd-algorithms"></a>

### 6.1 `P-OBS-QUERY` · 诊断查询

- **触发与执行者**：`GET /v1/diagnostics*`；请求线程
- **入口函数及数据**：`app.py` 路由 → `DiagnosticsService` 查询
- **步骤 / 算法 / 复杂度**：校验参数 → 查询 → 整形视图；O(页大小)
- **判断事实来源**：查询参数 / 存储
- **成功可见点**：视图
- **失败、取消与清理**：400/503
- **代表输入与中间值**：`?since=&until=` → 视图
- **规则 / 接口 / 验证引用**：`FUNC-OBS-QUERY`；`VRC-OBS-002/004`

### 6.2 `P-OBS-SWITCH` · 开关/注入变更

- **触发与执行者**：`PATCH /v1/diagnostics`；请求线程
- **入口函数及数据**：`admin.mutate` → `set_switches`/`set_injections`
- **步骤 / 算法 / 复杂度**：审计包裹 → 写；O(1)/O(items)
- **判断事实来源**：PATCH body
- **成功可见点**：新状态 + 审计 success
- **失败、取消与清理**：400/404 + 审计 failed
- **代表输入与中间值**：`{stats_enabled:true}`
- **规则 / 接口 / 验证引用**：`FUNC-OBS-SWITCH/INJECT`；`VRC-OBS-001/003`

## 7. 并发、失败、持久化与安全生命周期

<a id="isd-lifecycle"></a>

### 7.1 并发、交错与失败收口

#### 7.1.1 `CF-OBS-FAILOPEN` · 观测故障

- **参与线程 / 回调 / 事务**：请求线程
- **已产生或可能产生的副作用**：无
- **检测事实 / 期限**：写入异常（M006）
- **状态 / 错误 / 结果已知性**：——
- **保留 / 释放责任**：M006
- **允许的 query / replay / takeover / retry**：尽力而为
- **验证项**：`VRC-OBS-003`

<a id="isd-persistence"></a>

### 7.2 持久化、恢复与 schema 演进

#### 7.2.1.1 N/A · 无自有持久化

- **原规则 / 事务**：本模块不写库；记录由 M006、存储由 M007
- **原子范围 / 事务外副作用**：——
- **开始 / 提交 / 回滚函数**：——
- **持久提交点 / 对外响应点**：——
- **响应丢失后的权威核对**：——
- **恢复入口 / 判定记录 / 重复恢复条件**：——
- **验证项**：——

#### 7.2.2 Schema 演进策略决定

- **Schema authority / 当前版本事实来源**：不适用（本模块无 schema）
- **允许的升级模式**：随 M007
- **明确不接受的迁移模式**：无本层独立迁移
- **兼容边界**：——
- **失败后的系统状态与责任方**：随 M007

#### 7.2.3 库状态分支矩阵

不适用（本模块无自有 schema）。

<a id="isd-security"></a>

### 7.3 安全、权限与可观测性

#### 7.3.1.1 `SEC-OBS-AUTH` · operator 呈现 + 脱敏

- **原规则**：`C-OBS-3/5`
- **可信输入 / 敏感字段 / 检查对象**：operator `Principal`；查询结果
- **检查函数 / 时点**：入口鉴权；查询结果脱敏
- **拒绝 / 宿主交付出口**：401/403
- **脱敏 / 禁止输出**：URL 去 query、summary 截断、不记 Secret/正文
- **日志 / 指标 / trace 口径及触发**：呈现 M006 数据
- **验证项**：`VRC-OBS-002`

#### 7.3.2.1 `LSS-OBS-DB` · 存储安全

- **适用对象 / 路径 / Owner**：观测表（经 M006/M007）
- **文件与目录权限 / umask**：由 M007
- **Symlink / hardlink / 路径替换策略**：由 M007
- **备份 / 恢复 / 敏感数据静态保护**：不记 Secret/正文
- **删除 / 擦除 / 保留期限**：7 天（M006）
- **磁盘耗尽 / 只读文件系统行为**：随 M006 fail-open
- **检查时点 / 判定 / 拒绝或降级出口**：随 M007
- **验证项**：`VRC-OBS-002`

## 8. 资源、构建与宿主接入

<a id="isd-resources"></a>

### 8.1 配置实现（条件项）

- **适用性 / 固定 authority**：applicable（分页/时间参数）
- **配置 key / 来源 / 优先级**：查询参数 `since/until/deployment_id/model/limit/cursor`；无独立配置
- **类型 / 单位 / 默认值 / 范围 / 字段约束**：`limit` 夹值；时间 ISO8601
- **读取 / 解析 / 校验 symbol**：`app.py` 路由
- **生效点 / reload / 原子性 / 在途操作**：请求级
- **缺失 / 非法 / 部分更新的错误出口**：400（缺时间）
- **敏感值存储 / 日志脱敏**：无敏感配置
- **验证项**：`VRC-OBS-002`

### 8.2.1 `RB-OBS-BUILD` · 构建与装配

- **目标文件 / 产物 / 构建目标**：`app.py`（诊断路由）+ `diagnostics.py`（查询）+ `webui/app.js`；无独立库
- **工具链 / 语言 / 依赖版本**：Python 3.14 + 浏览器 JS
- **宿主接入 / 初始化 / 退出次序**：随 M001 装配；随进程
- **环境 / 数据规模 / 冷热条件**：单库；保留 7 天
- **峰值构成 / 上限 / 共享额度**：快照/traces 500/页；stats 无分页
- **分段预算 / 总期限 / 计时点**：查询无超时（连接 `timeout=10`）
- **超限、部分启动与清理出口**：fail-open
- **构建或运行命令及前置条件**：`PYTHONPATH=src python3 -m pytest tests/ -q`

## 9. 验证规格与实现任务

<a id="isd-verification"></a>

### 9.1.1 `VRC-OBS-001` · 开关

- **Rule / 成员**：`FUNC-OBS-SWITCH`、`C-OBS-1`
- **V / Case / Vector**：v1 默认关；v2 开/关；v3 关闭零写入
- **输入 / 故障 / 环境**：开关切换；隔离库
- **独立 Oracle / Expected**：默认 `{False,False}`；关闭时无新行
- **Actual / Evidence**：NOT_RUN
- **Verdict**：NOT_RUN
- **测试入口 / 清理**：`tests/unit`；隔离库
- **Run ID / Status**：NOT_RUN

### 9.1.2 `VRC-OBS-002` · 快照/统计查询与脱敏

- **Rule / 成员**：`FUNC-OBS-QUERY`、`C-OBS-3`
- **V / Case / Vector**：v1 上游调用后查询；v2 `?token=` URL；v3 503
- **输入 / 故障 / 环境**：隔离库
- **独立 Oracle / Expected**：字段完整；URL 去 query；503 不空页
- **Actual / Evidence**：NOT_RUN
- **Verdict**：NOT_RUN
- **测试入口 / 清理**：`tests/unit`
- **Run ID / Status**：NOT_RUN

### 9.1.3 `VRC-OBS-003` · 注入与 fail-open

- **Rule / 成员**：`FUNC-OBS-INJECT`、`C-OBS-2/4`
- **V / Case / Vector**：v1 合法/非法注入；v2 观测库写失败
- **输入 / 故障 / 环境**：隔离库
- **独立 Oracle / Expected**：400/404；推理结果不变
- **Actual / Evidence**：NOT_RUN
- **Verdict**：NOT_RUN
- **测试入口 / 清理**：`tests/unit`
- **Run ID / Status**：NOT_RUN

### 9.1.4 `VRC-OBS-004` · trace/traces 与关联标识

- **Rule / 成员**：`FUNC-OBS-QUERY/CORR`、`R-OBS-04`
- **V / Case / Vector**：v1 固定 request_id；v2 带/不带 `X-Correlation-ID`；v3 traces 时间窗/分页
- **输入 / 故障 / 环境**：隔离库
- **独立 Oracle / Expected**：stage 有序；仅提供时回显；去重 request
- **Actual / Evidence**：NOT_RUN
- **Verdict**：NOT_RUN
- **测试入口 / 清理**：`tests/unit`
- **Run ID / Status**：NOT_RUN

### 9.1.5 `VRC-OBS-005` · 诊断页

- **Rule / 成员**：`FUNC-OBS-PAGE`、`R-OBS-05`
- **V / Case / Vector**：v1 4 tabs；v2 开关关闭 → Disabled
- **输入 / 故障 / 环境**：诊断页
- **独立 Oracle / Expected**：开关语义
- **Actual / Evidence**：NOT_RUN
- **Verdict**：NOT_RUN
- **测试入口 / 清理**：系统用例
- **Run ID / Status**：NOT_RUN

**运行命令**：全量 `PYTHONPATH=src python3 -m pytest tests/ tests/system/st_*.py -q`

<a id="isd-tasks"></a>

### 9.2.1 `TASK-OBS-ROUTES` · 诊断路由

- **顺序 / 前置项**：1 / —
- **文件 / symbol / 构建目标**：`app.py`
- **不可改变的规则**：端点集合、脱敏、503 显式化
- **实施动作**：实现诊断路由
- **完成检查**：`VRC-OBS-001/002/004`
- **实现状态**：PLANNED
- **验证状态 / Run**：NOT_RUN

### 9.2.2 `TASK-OBS-PAGE` · 诊断页

- **顺序 / 前置项**：2 / `TASK-OBS-ROUTES`
- **文件 / symbol / 构建目标**：`webui/app.js`
- **不可改变的规则**：4 tabs + 开关语义
- **实施动作**：实现诊断页数据装载
- **完成检查**：`VRC-OBS-005`
- **实现状态**：PLANNED
- **验证状态 / Run**：NOT_RUN

## 10. 映射、复核与未决项

<a id="isd-mapping"></a>

### 10.1.1 `MAP-OBS` · 映射

- **模块 / 原成员 ID**：M005 / `F-OBS-*`
- **唯一来源 / 版本 / selector / hash**：`observability` / `0.1.0-draft.2`
- **提供或消费 / backend**：提供（诊断端点）/ M006
- **实际位置或 Planned 计划位置**：`src/llmtier_v03/app.py`、`diagnostics.py`、`webui/app.js`
- **验证项**：`VRC-OBS-001..005`
- **实现状态**：PLANNED
- **验证状态 / Run**：NOT_RUN

### 10.2.1 `SC-OBS` · 状态一致性复核

- **上游承接状态 / 固定来源**：模块 `observability` §15.ISD 声明 `separate`
- **本层派生状态 / 事实依据**：无实际实现/Run；全部 `PLANNED`/`NOT_RUN`
- **§2 Current / Target**：N/A（greenfield）
- **§3 / §5 文件与函数状态**：PLANNED
- **§9 任务 / Actual / Verdict / Run**：PLANNED / NOT_RUN / NOT_RUN / NOT_RUN
- **§10 汇总状态**：PLANNED
- **差异解释 / Owner / 收敛动作**：none

### 10.3.1 `RISK-OBS-1` · 统计可丢

- **既有台账引用 / 具体缺口 / 反例**：`RISK-OBS-1`
- **风险等级 / 判定依据**：Low；统计非账本
- **Owner**：LLMTier
- **最晚关闭阶段 / 截止 Gate**：——
- **阻断范围**：`FUNC-OBS-QUERY`
- **分析 / 决策引用**：模块 §15.1
- **所需输入 / 下一步选择判据**：——
- **解决动作 / 完成条件**：明示非账本语义
- **状态**：Open

### 10.3.2 `OPEN-OBS-1` · 与 M006 文件边界

- **既有台账引用 / 具体缺口 / 反例**：`OPEN-OBS-1`
- **风险等级 / 判定依据**：Low；`diagnostics.py` 同时含 M005 查询与 M006 记录
- **Owner**：LLMTier
- **最晚关闭阶段 / 截止 Gate**：本轮 review
- **阻断范围**：§3
- **分析 / 决策引用**：模块 §15.2
- **所需输入 / 下一步选择判据**：确认划分
- **解决动作 / 完成条件**：以"记录=M006 / 查询呈现=M005"划分，或后续拆文件
- **状态**：Open

### 10.4 Metadata 与 coverage 交付检查

metadata 必须包含：`design_object_id=M005`、`implementation_view_of_document_id=observability`、`volume_of_document_id=null`；模块设计 `implementation_specification.mode=separate/document_id=observability-isd`。

`coverage_mapping` 恰好覆盖十项：`scope`(#isd-scope)、`structure`(#isd-structure)、`data`(#isd-data)、`functions`(#isd-functions)、`algorithms`(#isd-algorithms)、`lifecycle`(#isd-lifecycle)、`resources`(#isd-resources)、`security`(#isd-security)、`persistence`(#isd-persistence)、`verification`(#isd-verification)。

交付前运行 `validate-design <完整设计目录> --check-isd-delivery --json`。
