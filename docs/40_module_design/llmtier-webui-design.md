<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 English Web UI Design

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-webui-module-design` |
| Document Version | `0.3.0-draft.18` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | Piko、Slinky、LLMTier |
| Approver | LLMTier |
| Approval Date | 待定 |
| Created Date | `2026-09-17` |
| Last Modified Date | `2026-09-22` |
| Template Version | `1.0.0` |
| Template ID | `design.definition` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/40_module_design/llmtier-webui-design.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 设计原则

Web UI is LLMTier's English-language operator console. It calls `/v1` on the same origin and never reads SQLite, settings, or Secrets directly. It keeps the established compact frame: fixed narrow sidebar, page title and status header, and one primary card per short page. It has five pages only: Home, Providers, Usage & Audit, Logs, and Diagnostics. Runtime status and Tier membership are managed from the Tier tree; provider connections are managed on the Providers page. There is no global Add Model action.

[打开可切换的静态 Demo](../assets/webui-demo/index.html)。以下图片由该Demo在1280×760视口生成，作为布局和信息层级基线；它们不是已经接线的产品截图。

不提供独立访问控制、容量产品、恢复、费用或调用方页面；Provider编辑器只配置本网关执行所需的账号并发、最小间隔与RPM保护，主页只读显示当前running/max事实。宽度小于960px时侧栏折叠为顶部菜单；表格允许横向滚动，不把四个页面拼成长页。状态与高频操作优先使用紧凑图标，并用`title`、`aria-label`和非颜色文字保留可理解性。

### 1.1 图标系统

![LLMTier Web UI图标系统](../assets/webui/icon-set.svg)

运行页面只使用项目内固定的单线SVG图标库`src/llmtier_v03/webui/icons.svg`，不从CDN加载字体或图标，也不以emoji表达状态。图标在表格中只显示图形；鼠标悬停、键盘聚焦时通过`title`显示英文名称，辅助技术通过`aria-label`读取同一名称。颜色只是补充信息，不能改变图标语义。

| 图标名称 | 状态语义 |
|---|---|
| Idle / `circle-dot` | Deployment健康、允许路由且当前没有活动请求；Idle不是暂停 |
| Running / `activity` | 当前至少有一个活动请求；请求结束后回到Idle |
| Paused / `circle-pause` | operator暂停单个Deployment，阻止新请求；配置仍保留 |
| Probing / `scan-search` | 显式健康探测正在执行 |
| Exhausted / `gauge` | 当前没有可用并发槽位 |
| Attention / `triangle-alert` | 数据或配置需要operator检查 |
| Unreachable / `cloud-off` | Provider或后端不可达 |
| Disabled / `circle-off` | 上级Provider或Tier被禁用，不是单模型暂停 |
| Unknown / `circle-help` | 没有足够事实判定状态 |
| Empty / `package-open` | Tier当前没有成员 |
| Ready / `circle-check` | 网关readiness成功 |

导航和操作统一使用同一图标库：Home、Providers、Usage、Logs、Diagnostics、Refresh/Probe、Add、Edit、Save、Pause、Resume、Delete、Unlink和Close。Pause与Resume是同一Deployment的可逆操作，不创建新模型、不改变Tier成员关系。

## 2. 页面一：主页

![主页](../assets/webui/home.png)

- 主页使用无背景的两层树形布局，不显示额外的列标题行、Tier行底色、成员行底色或横向行框；层级只用缩进、展开箭头和浅色树枝线表达。Tier是父节点；展开后每个后端成为独立子节点，显示provider、model、类型、健康状态、版本与`running/max`并发。Tier状态直接采用`/readyz.models[].availability`：available显示Ready、degraded显示Attention、unavailable显示Unreachable；它不从成员状态聚合。成员状态独立来自Deployment health/runtime：健康、允许路由且`running=0`显示Idle，只有`running>0`才显示Running，单个Deployment的`enabled=false`显示Paused。Tier与成员状态互不覆盖。Tier行显示聚合并发及最近七日Tier级Calls/Tokens；token事实存在Unknown时不填0。由于当前Usage记录只保存逻辑Tier而不保存最终选中的Deployment，后端行不得虚构单模型用量，显示`—`并说明数据边界。
- 主页不显示重复的Gateway/Tier/Backend/Health统计卡，也不显示搜索、手工刷新或全局`Add Model`。全局页头紧凑显示Gateway总状态、可用Tier/总Tier、Running模型/总模型、当前请求/配置并发上限以及Version/Updated。每个Tier行右侧使用图标`Edit`。Tier父行的Type单元格完全留空，不显示Responses、Embeddings或占位符；Cloud/Local只在后端子行显示。V0.3当前Tier集合为`Senior`、`Junior`、`Worker`、`Associate`、`Engineer`、`Executor`与独立的`Embedding-v1`，不分页隐藏当前目录项。
- Tier集合和映射来自Registry；演示中的后端模型名仅用于布局，不构成生产配置。物理凭据不展示。
- 推理Tier可绑定不同供应商但必须能力兼容且保持同一exact Tier；`Embedding-v1`的三个deployment必须是同一`BAAI/bge-m3`模型版本、预处理和`embedding_space_id`，不能把不同向量空间挂在同一Tier下。物理Provider模型ID按各runtime实际API ID展示，不要求字符串都写成`BAAI/bge-m3`。
- 编辑先GET item保存ETag，PATCH携带If-Match。412显示“配置已被他人修改”，保留用户输入并提供重新载入，不自动覆盖。
- Tier是固定逻辑等级，主页不提供删除Tier；只允许编辑其后端绑定。Provider或Deployment等可删除资源仍须在对应编辑流程显示引用关系、携带If-Match；409显示引用列表摘要，禁止强删。
- 每个后端行提供图标化Pause/Resume。操作使用现有Deployment partial PATCH与`If-Match`切换`enabled`，不新增控制接口。Pause阻止新请求进入该Deployment，但不取消已开始的请求；若`running>0`，UI必须在暂停前确认并明确该边界。Resume只恢复参与路由的资格，不等于probe成功或健康状态已恢复。Provider被禁用时显示Disabled，不显示为Paused。
- Loading用表格骨架；空Tier显示“no members”并仍可进入`Edit`；401跳登录，403显示无operator权限；503保留旧画面并标“data may be stale”。

### 2.1 Tier成员编辑抽屉

![主页内模型编辑抽屉](../assets/webui/home-model-editor.png)

- 抽屉列出当前Tier全部成员，每项可修改已有Deployment的Provider、显示名、backend model ID与`Available for routing`；保存使用Deployment当前ETag与partial PATCH。该开关与主页Pause/Resume操作同源，关闭后状态为Paused。
- `Add Member`的Provider下拉框只列出Providers页面中已存在的Provider。页面不在此处创建Provider、Secret或第二套连接配置；没有Provider时禁用添加并提示先进入Providers页面。
- 添加成员先POST Deployment，再以Tier当前ETag PATCH ServiceLevel的`deployment_ids`。第一步成功、第二步失败时保留真实错误和已创建Deployment，不谎称原子成功，也不自动删除可能已被引用的资源。
- `Remove`只从当前Tier解绑Deployment，不删除Deployment或Provider。共享Deployment可继续被其他Tier使用；资源删除由其专属管理流程和409引用保护处理。
- Tier固定且不可删除。`Embedding-v1`新成员沿用该Tier固定的Embedding能力和向量空间约束；推理Tier新成员沿用Responses能力。跨向量空间变更不得通过仅修改backend model ID绕过。
- 保存成功只说明配置落库，不说明probe、health或ready成功。

主页首次进入和从其他页面返回时自动读取health/readiness，不触发模型请求。后端行的“探测”先显示二次确认：“可能产生费用并改变最后探测状态”，确认后发送`confirm_external_call=true`。探测中仅禁用对应后端；网络结果未知时提示重新进入主页核对，不自动重复。保存成功、health成功和probe成功仍是三个不同状态。

## 3. 页面二：供应商管理

- 页面列出Provider名称、类型、OpenAI-compatible API root、Secret是否已配置、运行状态、账号用量、Calls/Tokens、账号级`running/max`和操作。每次实际dispatch会把request绑定到最终Provider/Deployment，因此Calls/Tokens只聚合真实绑定后的最高Usage版本；任一token事实未知时不填0。
- 账号用量普通GET只读取SQLite最后快照，不自动触网。刷新图标要求operator确认后才调用Provider usage API并持久化结果；窗口按Provider实际返回显示5-hour/weekly/monthly、已用百分比和reset tooltip，缺失字段保持Unknown。
- `Add Provider`仅在本页出现。新增/编辑支持cloud/local、名称、API root、推理Secret reference、enabled、usage source、账号最大并发、最小请求间隔及RPM。Secret只写不回显，编辑时空白表示保持已有Secret。
- MiniMax Token Plan使用Provider API Key调用官方`GET https://www.minimaxi.com/v1/token_plan/remains`，可复用推理Secret reference，不需要console cookie。火山Coding Plan用独立OpenAPI AK/SK签名调用`GetCodingPlanUsage`；推理API Key不能代替AK/SK。
- 删除携带当前ETag。Provider仍被任何Deployment引用时，服务端409拒绝删除；UI显示错误，不级联删除Deployment或Tier成员。
- Provider API root通常以`/v1`结尾；运行时在其后调用`/models`、`/responses`或`/embeddings`，页面不得猜测或重复拼接版本段。

## 4. 页面三：用量与审计

![用量与审计页面](../assets/webui/records.png)

![用量与审计页面的审计页签](../assets/webui/records-audit.png)

页面顶部用页签切换`Token用量`和`管理审计`，一次只显示一张表，避免页面过长。页签切换不改变查询条件之外的服务状态，也不把用量事实与审计事件混成同一数据集。

### 4.1 Token用量

- 同request ID只展示最高record_version；版本更新替换原行，不累计。
- Unknown显示“未知”，绝不显示0；cache read/write和reasoning token在展开行展示。
- cursor绑定筛选与snapshot；翻页期间的新记录下次查询显示。503显示“用量存储不可用”，不能显示空表。
- 不显示Cost、币种或估算金额。

### 4.2 管理审计

- 只显示脱敏actor/action/target/result/time/request ID；无prompt/output/token/Secret。
- Audit只读；过滤与cursor保留在URL query，刷新可恢复同一视图。

## 5. 页面四：日志

![日志页面](../assets/webui/logs.png)

- 日志是服务运行与故障诊断事件；审计是operator管理动作，两者不混用。
- 只返回服务端先行脱敏的结构化字段：时间、级别、模块、事件、短消息和可空request ID。禁止Prompt、模型输出、reasoning正文、Embedding向量、Authorization、Secret或完整请求头进入日志记录和API。
- 支持时间、级别、模块和request ID过滤；游标绑定稳定快照。日志存储不可读时返回503，不用空页伪装“没有日志”。
- 日志详情文本有长度上限；UI不渲染HTML。保留期限和清理由运维设计控制，不提供浏览器下载全量日志。

## 6. 页面五：诊断（Diagnostics）

Diagnostics 页面用于 Piko 联调的可观测性调试，包含 4 个 tabs：Snapshots、Stats、Injection、Trace。页面顶部有全局调试开关。

### 6.1 全局调试开关

页面顶部始终显示全局调试开关状态栏：

![全局调试开关控件](../assets/diagrams/diagram-webui-diag-switches.png)

[可编辑 SVG 源](../assets/diagrams/diagram-webui-diag-switches.svg)

实际控件渲染：

| 控件 | 状态 | 含义 |
|---|---|---|
| Snapshot Capture | ● / ○ | ON / OFF |
| Stats Aggregation | ● / ○ | ON / OFF |

- Toggle 开关调用 `PATCH /v1/diagnostics` 实时切换
- 状态反映 `GET /v1/diagnostics` 的 `snapshots_enabled` / `stats_enabled`
- 关闭时对应 tab 内容显示"Disabled"提示

### 6.2 Tab 1：Snapshots（快照）

调用 `GET /v1/diagnostics/snapshots`，显示上游调用快照列表：

| 列 | 说明 |
|---|---|
| Time | `captured_at`（本地时间） |
| Request ID | `request_id`（可点击跳转 Trace） |
| Deployment | `deployment_id` |
| Model | 请求的 model |
| Upstream URL | `upstream_url`（已脱敏） |
| Status | `http_status`（颜色编码：2xx=绿，4xx=黄，5xx=红） |
| Latency (ms) | `latency_ms` |
| Error | `error_summary`（如有） |

- 支持时间范围筛选（since/until）
- 支持 deployment_id / model 筛选
- 分页（cursor-based），每页 50 条
- 点击行展开显示完整 snapshot 详情（JSON viewer）

### 6.3 Tab 2：Stats（统计）

调用 `GET /v1/diagnostics/stats`，显示数据面聚合统计：

- **数字卡片**：`Request Count`、`Error 4xx`、`Error 5xx`
- **延迟分布**：`P50`、`P95`、`Min`、`Max`、`Avg`
- 支持时间范围和 deployment_id/model 筛选
- 显示"数据仅供参考，对账以 Usage 账本为准"提示

### 6.4 Tab 3：Injection（注入配置）

按 deployment 显示注入配置。调用 `GET /v1/deployments` 列表 + `GET /v1/deployments/{id}/diagnostics`：

| Deployment | Type | Config | Enabled |
|---|---|---|---|
| depl_a | delay | delay_ms: 500 | [●──○] |
| depl_a | fault_502 | body: "backend error" | [○──●] |
| depl_b | rate_limit | retry_after_sec: 30 | [●──○] |

- 每行有 Edit 按钮，点击弹出 PATCH 对话框
- Edit 调用 `PATCH /v1/deployments/{id}/diagnostics`
- 新增注入：选择 type 后填写 config，保存后 POST

### 6.5 Tab 4：Trace（链路追踪）

输入 Request ID 调用 `GET /v1/trace/{request_id}`，显示请求全链路：

```
Request ID: req_abc123
Correlation ID: corr_xyz (if present)

Stages:
  [✓] received     2026-09-22T10:00:00.000Z
  [✓] validated    2026-09-22T10:00:00.050Z
  [✓] routed       2026-09-22T10:00:00.100Z  → depl_a
  [✓] upstream_started  2026-09-22T10:00:00.150Z
  [✓] upstream_ended    2026-09-22T10:00:00.650Z  (snapshot: snap_xxx)
  [✓] completed    2026-09-22T10:00:01.000Z

Usage:
  Model: Worker | Version: 1 | Final: Yes
  Input Tokens: 120 | Output Tokens: 340 | Total: 460
```

- 每个 stage 显示时间戳和耗时
- `upstream_ended` 阶段可点击查看关联的 snapshot
- Usage 部分关联 `usage_record_versions`

### 6.6 API 字段映射

| UI | Read | Mutation |
|---|---|---|
| Diagnostics | `GET /diagnostics`（开关）、`GET /diagnostics/snapshots`、`GET /diagnostics/stats`、`GET /deployments/{id}/diagnostics`、`GET /trace/{request_id}` | `PATCH /diagnostics`（开关）、`PATCH /deployments/{id}/diagnostics`（注入配置） |

## 7. 通用交互状态

| 状态 | 规则 |
|---|---|
| Loading | 保持页面框架，局部骨架；不清空上次成功数据 |
| Empty | 说明是"无数据"而不是"加载失败" |
| Validation | English field-level error beside the field; focus the first error |
| 401 | 清除UI会话并要求重新认证，不回显token |
| 403 | 显示无operator权限，不猜资源是否存在 |
| 409 | 显示引用冲突，可跳回主页 |
| 412 | 显示stale edit，允许复制未保存输入后重新载入 |
| 429/503 | 显示Retry-After（若有）；不自动无限重试 |
| Unknown result | 先GET核对，不盲目重发mutation |

All buttons support keyboard operation and visible focus. Status cells show only one consistent line-icon set; the English status label is exposed by hover tooltip, keyboard focus and `aria-label`, so status never relies on color alone. Delete and chargeable probes require confirmation. All visible page copy, labels, tooltip values, provider types, and empty/error states use English. Machine error codes remain available in Details for diagnosis.

## 8. 认证与浏览器安全

Web UI本身不提供"访问控制"业务页，也不实现账号库。production由同源TLS反向代理完成operator SSO/MFA，
浏览器只持有代理签发的`Secure; HttpOnly; SameSite=Strict`短期会话cookie；代理在服务端换取/注入Admin bearer，
bearer不进入JavaScript、URL、localStorage或sessionStorage。所有mutation还必须校验同源`Origin`和代理CSRF token。
401跳转到外部登录，403留在当前页并显示权限不足；logout由代理撤销会话后清空内存草稿。LLMTier Admin API仍只
接受现有`AdminBearerAuth`，不新增登录endpoint、用户管理Schema或第二认证路径。development若没有认证代理，
Web UI保持disabled，operator使用CLI/API；不提供把长期token粘贴进浏览器的降级模式。

## 9. API字段映射

| UI | Read | Mutation |
|---|---|---|
| 主页 | provider/deployment/service-level pages、healthz/readyz、admin runtime snapshot、admin usage page、deployment health + ETag | Tier抽屉POST Deployment、PATCH Deployment、PATCH Tier membership + If-Match；后端Pause/Resume使用现有Deployment PATCH切换enabled；不创建Provider |
| Providers | provider/deployment pages、admin runtime snapshot、provider usage snapshot + ETag | Provider POST/PATCH/DELETE + If-Match；显式POST usage refresh；引用中的Provider由409保护 |
| 用量与审计 | admin usage page、audit page | 无 |
| 日志 | sanitized log page | 无 |
| Diagnostics | `GET /diagnostics`、`GET /diagnostics/snapshots`、`GET /diagnostics/stats`、`GET /deployments/{id}/diagnostics`、`GET /trace/{request_id}` | `PATCH /diagnostics`、`PATCH /deployments/{id}/diagnostics` |

`runtime_activation=false`；本文是设计，不是浏览器实现或capture。
