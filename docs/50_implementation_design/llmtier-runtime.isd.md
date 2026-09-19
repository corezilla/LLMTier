<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Runtime 实现设计

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-runtime-isd` |
| Document Version | `0.3.0-draft.6` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | Piko、Slinky、LLMTier |
| Approver | LLMTier |
| Approval Date | 待定 |
| Created Date | `2026-09-17` |
| Last Modified Date | `2026-09-17` |
| Template Version | `1.0.0` |
| Template ID | `design.definition` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/50_implementation_design/llmtier-runtime.isd.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 实现范围

本文规定V0.3目标实现的内部数据、事务、关键函数边界和启动顺序；不是当前legacy代码已经实现的声明。外部形状以candidate.6 OpenAPI为准，模块职责以`llmtier-core-module-design`为准。

## 2. 目标包结构

```text
src/llmtier_v03/
  app.py                 # 单一HTTP装配根
  auth.py                # Data/Admin principal与权限
  responses.py           # 标准SSE endpoint与事件验证
  embeddings.py          # 标准Embedding subset
  models.py              # exact logical model目录
  routing.py             # exact level内部路由
  providers/base.py      # provider adapter protocol
  providers/openai.py    # OpenAI-compatible cloud adapter
  providers/local.py     # local OpenAI-compatible adapter
  store.py               # SQLite事务与migration
  registry.py            # provider/deployment/level配置
  usage.py               # usage normalize/upsert/query
  admin.py               # Admin API
  health.py              # health/readiness
  audit.py               # 脱敏审计
  logs.py                # 写入前脱敏的有界运行日志与只读查询
  webui/                 # 四页英文静态资源和组件
```

不得让legacy `/call` router与上述目标surface并行成为consumer路径。迁移完成前目标包保持未激活；切换必须一次性更新唯一入口。

## 3. SQLite Schema

| 表 | 主键/唯一约束 | 关键列 |
|---|---|---|
| schema_meta | singleton | schema_version, initialized_at, bootstrap_sha256 |
| providers | id；name unique | kind, endpoint, secret_ref, enabled, version |
| deployments | id | provider_id FK, backend_model, capabilities_json, enabled, health, version |
| service_levels | id exact/case-sensitive | enabled, capabilities_json, version |
| service_level_deployments | (level_id,deployment_id) | ordinal |
| deployment_runtime_profiles | deployment_id FK | max_in_flight=1,connect_timeout_ms=30000,stream_idle_timeout_ms=60000,version |
| admission_queues | 仅内存、非SQLite authority | level_id,FIFO request refs；每level上限32、等待上限30000ms |
| usage_obligations | (principal_id,request_id) | model,endpoint,recorded_at,dispatch_authorized_at |
| usage_record_versions | (principal_id,request_id,record_version)；FK obligation | is_final,token fields,quality,source,timestamps |
| usage_heads | (principal_id,request_id)；FK immutable version | head_record_version,updated_at |
| query_snapshots | snapshot_id | principal_id,snapshot_kind,filter_digest,authorization_digest,created_at,expires_at |
| query_snapshot_items | (snapshot_id,ordinal)；unique(snapshot_id,request_id) | request_id,record_version；Admin项另存frozen_view_json,etag |
| probe_results | deployment_id | status,checked_at,request_id |
| audit_events | id | actor,action,target,result,created_at,request_id |
| operational_logs | id | created_at,level,module,event,message,request_id；message<=512且写入前脱敏 |

所有外键开启；WAL模式；配置mutation使用`BEGIN IMMEDIATE`。Usage事实只追加`usage_record_versions`，不得原位覆盖旧版本；同一事务仅把`usage_heads`推进到严格更高版本。final记录不得被低质量或低版本替代。未到期`query_snapshot_items`引用的版本不得清理；snapshot到期后先删除items和snapshot，之后才允许按保留策略清理不再被引用的旧版本。Admin snapshot item以冻结view/ETag而非活动表行作为分页内容。

## 4. 启动算法

```text
open store -> apply approved migrations -> integrity check
if empty store:
    require explicit bootstrap settings path
    parse and validate without logging secrets
    transactionally import + audit + mark initialized
else:
    ignore settings file for runtime authority
load immutable RegistrySnapshot
start health endpoint
verify required logical models and provider adapter configuration
only after explicit activation gate expose Data/Admin traffic
```

初始化失败回滚并保持readyz=not_ready。运行期不得监听settings文件变化或双写JSON。

## 5. 请求执行

`create_response(principal, request, trace)`：

1. 解析并严格校验固定Pi标准subset；分配server request ID。
2. 按exact model读取一个RegistrySnapshot；不存在返回404。
3. Internal Admission原子取得内部许可；失败返回429/Retry-After。
4. Router只在该level的兼容deployment中选择；embedding额外比较space ID。
5. 在允许任何provider dispatch之前，事务写入`UsageObligation(principal, request_id, recorded_at)`、不可变version 1 unknown `UsageRecordVersion`并建立`UsageHead`；写入失败返回503且不dispatch。
6. Adapter才可发起provider dispatch并输出标准SSE；emitter检查sequence、item ID、done与terminal完整item一致及单terminal，不实现未消费的JSON并行模式。terminal usage按标准结构返回后追加更高版本并原子推进`UsageHead`。更新失败不篡改已成功模型结果，原unknown版本继续可查并触发store告警；进程在terminal后更新前崩溃，重启后也仍返回该unknown事实而非空页。
7. Piko执行工具并以新HTTP调用发送完整历史；服务端不保存conversation。

`InternalAdmission.acquire(level_id, registry_version)`在单进程事件循环内维护每level FIFO和每deployment semaphore。
它先拒绝超过32项的队列，再等待最多30000ms；出队时重新读取同一或更高RegistrySnapshot，只选择enabled、healthy、
能力匹配且in-flight最少的deployment，相同按ordinal。没有候选时503，有候选但无许可/等待到期时429。
进程重启会丢弃未dispatch的内存队列，客户端得到连接失败并按自己的任务策略处理；队列不是durable任务或恢复协议。

## 6. Usage归一与更新

`normalize_usage(provider_usage)`保留字段存在性：没有字段为null，真实0才为0。标准响应只输出标准数字结构；无法提供可信usage时响应可省略/置null，由Piko标任务Usage unknown，但模型成功本身不改为失败。

`append_usage_version`：同principal/request ID只接受严格递增版本；estimated→measured合法，measured→estimated、final→nonfinal、重复或降序版本拒绝并审计。旧版本不可覆盖或删除；`UsageHead`只在同一事务指向新版本。

首次查询在同一SQLite事务创建`QuerySnapshot`与有序`QuerySnapshotItem(request_id, record_version, ordinal)`，并记录principal、完整filter摘要、授权摘要、created/expires时间。后续cursor携带加签的snapshot/filter/principal/ordinal，只读取固化版本；新记录和迟到更正不进入旧snapshot。每页重新认证授权；权限缩小、snapshot过期、filter或签名不符返回400 `invalid_request`。Admin列表复用同一机制，但snapshot item保存冻结的序列化view与ETag，使分页期间的修改/删除不改变旧页结果。后台只清理已到期snapshot，不能清理仍被未到期snapshot引用的Usage版本。

崩溃边界固定为：unknown义务提交成功→允许provider dispatch→输出业务结果→尽力追加计量版本。第一步失败时不调用provider；后两步之间崩溃时重启保留unknown。store整体不可读时查询返回503 `usage_store_unavailable`；store可读但计量未知时返回该unknown记录。两者都不得返回空页掩盖缺口。

## 7. Admin条件写

ETag格式为`"<resource-id>.v<version>"`。PATCH/DELETE事务先验证Admin权限和If-Match，再检查引用/embedding space，执行mutation并写Audit。412表示版本冲突；409只表示当前引用/业务不变量冲突。响应返回新ETag。Secret replacement在受控Secret backend完成后才提交reference；失败不改变旧reference。

## 8. Embedding发布检查

`publish_service_level`对embedding level执行：

- 每个deployment的space ID、模型版本、预处理契约相同；
- 支持维数交集非空并等于level声明；
- batch/input token限制取所有后端可保证的最小值；
- output数量=input数量、index为0..n-1且唯一、维数一致、float有限。

任一不满足则配置发布失败。非兼容升级必须新建level ID；无alias或静默切换。

首版bootstrap必须创建`Embedding-v1`并绑定本地`BAAI/bge-m3` dense family deployment；物理Provider模型ID按runtime实际API ID配置，固定
`embedding_space_id=bge-m3-dense-1024-v1`、dimensions `[1024]`、batch 32、single-input 8192 tokens、
provider tokenizer、无文本改写/无query instruction、L2 normalization。启动校验同时核对已配置的model/tokenizer
revision、runtime image digest与normalization；缺一则该deployment保持unhealthy，`readyz`不得把Embedding能力报为可用。

## 9. Web UI装配

Web UI与Admin API同源；production反向代理完成operator SSO/MFA、短期HttpOnly会话、CSRF和Admin bearer注入，
浏览器JavaScript不接触bearer。没有认证代理时Web UI不启用。所有mutation使用最近GET的ETag。添加模型只在内存保存
`ModelDraft`并按Provider→Deployment→ServiceLevel续作；不自动回滚或重发已完成POST。组件状态和四页布局见
`llmtier-webui-module-design`。前端不得把HTTP 200配置保存解释为provider健康。

## 10. 日志与安全

结构化日志写入`operational_logs`前先投影为level/module/event/有界message/request ID；只含route、logical model、status、latency、typed error和脱敏principal。禁止Authorization、Secret、prompt、response、embedding vector、opaque reasoning和原始headers。`GET /tier/admin/v1/logs`只读，首个页面在SQLite事务中冻结精确log ID并复用QuerySnapshot；每页重新鉴权，过期cursor返回400，store不可读返回503。日志保留7天；清理不得删除未过期snapshot引用项。主动probe、Secret变化、restart/restore都需要operator权限并写Audit。

## 11. 实现门禁

1. candidate.6 Schema/semantic tests通过的范围包括candidate.5既有语义以及脱敏LogEntry/LogPage、只读Admin日志path；真实日志持久化、清理和浏览器接线为`NOT_RUN`；
2. 固定Pi golden request和SSE parser capture通过；
3. SQLite bootstrap唯一authority及崩溃事务测试通过；
4. Admin ETag并发、Secret、引用删除测试通过；
5. Embedding same-space与索引重建边界通过；
6. 四页浏览器状态/可访问性测试通过，主页在目标视口完整显示当前Registry全部Tier；
7. production auth/TLS/backup/restore另行验收。

在这些门禁和独立activation批准前，`runtime_activation=false`。
