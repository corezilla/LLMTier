<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 English Web UI Design

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-webui-module-design` |
| Document Version | `0.3.0-draft.7` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | Piko、Slinky、LLMTier |
| Approver | LLMTier |
| Approval Date | 待定 |
| Created Date | `2026-09-17` |
| Last Modified Date | `2026-09-18` |
| Template Version | `1.0.0` |
| Template ID | `design.definition` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/40_module_design/webui-design.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 设计原则

Web UI is LLMTier's English-language operator console. It calls `/tier/admin/v1` on the same origin and never reads SQLite, settings, or Secrets directly. It keeps the established compact frame: fixed narrow sidebar, page title and status header, and one primary card per short page. It has three pages only: Home, Usage & Audit, and Logs. Add/Edit Model uses a drawer on Home rather than a separate page; runtime status is visible directly in the Tier tree.

[打开可切换的静态 Demo](demos/webui/index.html)。以下图片由该Demo在1280×760视口生成，作为布局和信息层级基线；它们不是已经接线的产品截图。

不提供访问控制、容量、恢复、费用、调用方页面。宽度小于960px时侧栏折叠为顶部菜单；表格允许横向滚动，不把三个页面拼成长页。

## 2. 页面一：主页

![主页](assets/webui/home.png)

- 主页使用两层树形表格，而不是把三个后端横向塞进同一行。Tier是父节点；展开后每个后端成为独立子节点，显示provider、model、类型、健康状态与版本。主页不再显示重复的Gateway/Tier/Backend/Health统计卡，也不显示搜索或手工刷新工具栏；网关状态保留在全局页头，`Add Model`紧邻状态放在右上角。V0.3当前Tier集合为`Senior`、`Junior`、`Worker`、`Associate`、`Engineer`、`Executor`与独立的`Embedding-v1`，不分页隐藏当前目录项。
- Tier集合和映射来自Registry；演示中的后端模型名仅用于布局，不构成生产配置。物理凭据不展示。
- 推理Tier可绑定不同供应商但必须能力兼容且保持同一exact Tier；`Embedding-v1`的三个deployment必须是同一`BAAI/bge-m3`模型版本、预处理和`embedding_space_id`，不能把不同向量空间挂在同一Tier下。物理Provider模型ID按各runtime实际API ID展示，不要求字符串都写成`BAAI/bge-m3`。
- 编辑先GET item保存ETag，PATCH携带If-Match。412显示“配置已被他人修改”，保留用户输入并提供重新载入，不自动覆盖。
- Tier是固定逻辑等级，主页不提供删除Tier；只允许编辑其后端绑定。Provider或Deployment等可删除资源仍须在对应编辑流程显示引用关系、携带If-Match；409显示引用列表摘要，禁止强删。
- Loading用表格骨架；空状态提供“添加模型”；401跳登录，403显示无operator权限；503保留旧画面并标“数据可能过期”。

### 2.1 主页内添加/修改模型

![主页内模型编辑抽屉](assets/webui/home-model-editor.png)

- 添加按Provider→Deployment→ServiceLevel顺序提交；任一步失败显示已完成步骤，不谎称整体成功。后续实现可用单次页面编排，但不新增外部聚合endpoint。
- Provider“接口根地址”填写OpenAI-compatible API root（通常以`/v1`结尾；供应商若使用等价版本根则填写该根），运行时在其后调用`/models`、`/responses`或`/embeddings`，页面不得猜测或重复拼接版本段。
- 页面先在浏览器内存创建`ModelDraft`，只保存非Secret表单值和本次已创建资源的ID/ETag。每一步成功后立即更新进度：
  `Provider已保存 → Deployment已保存 → ServiceLevel已保存`。失败后“继续保存”从第一个未完成步骤开始，
  已完成步骤改用GET+ETag核对，不重复POST。刷新或关闭页面会丢弃草稿，但不会删除已落库资源；重新进入时可从
  主页继续编辑。取消也不自动补偿删除，避免误删已被其他等级引用的资源；用户只能通过已有带If-Match
  的显式删除操作清理。这样没有伪原子事务，也不新增聚合endpoint。
- 修改时Secret空白=保持；用户选择“移除Secret”才发null。页面不读取原值。
- Embedding必须填写space ID、允许维数、batch/input token上限；同逻辑等级绑定不兼容space时保存前阻止并提示新建逻辑model ID。
- 保存成功只说明配置落库，不说明probe或ready成功。

主页首次进入和从其他页面返回时自动读取health/readiness，不触发模型请求。后端行的“探测”先显示二次确认：“可能产生费用并改变最后探测状态”，确认后发送`confirm_external_call=true`。探测中仅禁用对应后端；网络结果未知时提示重新进入主页核对，不自动重复。保存成功、health成功和probe成功仍是三个不同状态。

## 3. 页面二：用量与审计

![用量与审计页面](assets/webui/records.png)

![用量与审计页面的审计页签](assets/webui/records-audit.png)

页面顶部用页签切换`Token用量`和`管理审计`，一次只显示一张表，避免页面过长。页签切换不改变查询条件之外的服务状态，也不把用量事实与审计事件混成同一数据集。

### 3.1 Token用量

- 同request ID只展示最高record_version；版本更新替换原行，不累计。
- Unknown显示“未知”，绝不显示0；cache read/write和reasoning token在展开行展示。
- cursor绑定筛选与snapshot；翻页期间的新记录下次查询显示。503显示“用量存储不可用”，不能显示空表。
- 不显示Cost、币种或估算金额。

### 3.2 管理审计

- 只显示脱敏actor/action/target/result/time/request ID；无prompt/output/token/Secret。
- Audit只读；过滤与cursor保留在URL query，刷新可恢复同一视图。

## 4. 页面三：日志

![日志页面](assets/webui/logs.png)

- 日志是服务运行与故障诊断事件；审计是operator管理动作，两者不混用。
- 只返回服务端先行脱敏的结构化字段：时间、级别、模块、事件、短消息和可空request ID。禁止Prompt、模型输出、reasoning正文、Embedding向量、Authorization、Secret或完整请求头进入日志记录和API。
- 支持时间、级别、模块和request ID过滤；游标绑定稳定快照。日志存储不可读时返回503，不用空页伪装“没有日志”。
- 日志详情文本有长度上限；UI不渲染HTML。保留期限和清理由运维设计控制，不提供浏览器下载全量日志。

## 5. 通用交互状态

| 状态 | 规则 |
|---|---|
| Loading | 保持页面框架，局部骨架；不清空上次成功数据 |
| Empty | 说明是“无数据”而不是“加载失败” |
| Validation | English field-level error beside the field; focus the first error |
| 401 | 清除UI会话并要求重新认证，不回显token |
| 403 | 显示无operator权限，不猜资源是否存在 |
| 409 | 显示引用冲突，可跳回主页 |
| 412 | 显示stale edit，允许复制未保存输入后重新载入 |
| 429/503 | 显示Retry-After（若有）；不自动无限重试 |
| Unknown result | 先GET核对，不盲目重发mutation |

All buttons support keyboard operation and visible focus; status never relies on color alone; delete and chargeable probes require confirmation. All visible page copy, labels, status values, provider types, and empty/error states use English. Machine error codes remain available in Details for diagnosis.

## 6. 认证与浏览器安全

Web UI本身不提供“访问控制”业务页，也不实现账号库。production由同源TLS反向代理完成operator SSO/MFA，
浏览器只持有代理签发的`Secure; HttpOnly; SameSite=Strict`短期会话cookie；代理在服务端换取/注入Admin bearer，
bearer不进入JavaScript、URL、localStorage或sessionStorage。所有mutation还必须校验同源`Origin`和代理CSRF token。
401跳转到外部登录，403留在当前页并显示权限不足；logout由代理撤销会话后清空内存草稿。LLMTier Admin API仍只
接受现有`AdminBearerAuth`，不新增登录endpoint、用户管理Schema或第二认证路径。development若没有认证代理，
Web UI保持disabled，operator使用CLI/API；不提供把长期token粘贴进浏览器的降级模式。

## 7. API字段映射

| UI | Read | Mutation |
|---|---|---|
| 主页 | provider/deployment/service-level pages、healthz/readyz、deployment health + ETag | 模型抽屉POST/partial PATCH；Tier仅PATCH；后端资源按其管理流程PATCH/DELETE + If-Match；授权probe |
| 用量与审计 | admin usage page、audit page | 无 |
| 日志 | sanitized log page | 无 |

`runtime_activation=false`；本文是设计，不是浏览器实现或capture。
