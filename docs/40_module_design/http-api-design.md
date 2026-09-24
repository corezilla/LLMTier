<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier M001 HTTP API 模块设计

> STD 使用入口：[项目采用说明与标准导航](../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `http-api` |
| Document Version | `0.1.0-draft.2` |
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
| Canonical Path | `docs/40_module_design/http-api-design.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 单元摘要：为什么存在

| 项目 | 内容 |
|---|---|
| 模块编号 / 正式英文名称 | **M001** / HTTP API |
| 直属父对象编号 / 名称 | LLMTier 软件系统（本项目无子系统）|
| 父设计 Document ID / 登记位置 | `llmtier-system-design` / 系统设计 §3.2（唯一登记表）|
| 上级系统 / 父单元 | LLMTier 软件系统 |
| 解决的问题 | 提供统一的 HTTP/SSE 入口：终止连接、路由分发、局域网访问信任与请求身份，使业务模块无需各自处理传输与鉴权 |
| 提供的能力 | 全部 `/v1/*` 端点与 `text/event-stream` 流式传输；`/healthz`、`/readyz`；Web UI 静态资源；`X-Request-ID` 与关联标识透传 |
| 主要使用者 | Consumer（Piko/Slinky）、Operator（浏览器/运维脚本）；下游 M003 Inference、M004 Management、M005 Observability |
| 不负责 | 业务规则（校验/路由/计量）；持久化访问；用户/会话/SSO 体系；不下发订阅启动/重定向 |

### 1.1 继承的上级约束与落实方式

#### 1.1.1 `C-TRUST-1` · 入口单点鉴权
- **上级基线与决定状态**：机制 M-TRUST §3.1；已采用
- **适用条件**：全部端点
- **继承预算或行为保证**：判定只在入口发生一次，下游不二次校验
- **可自行选择 / 不可改变**：实现方式可自选；单点不可变
- **本地落实 / 内部再分配**：I2；§8.2、§8.3
- **验证方法与结果 / 证据**：`VRC-API-002`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：无

#### 1.1.2 `C-TRUST-2` · 不建用户/会话/SSO 体系
- **上级基线与决定状态**：机制 M-TRUST §3.1；已采用
- **适用条件**：鉴权
- **继承预算或行为保证**：凭据仅作纵深
- **可自行选择 / 不可改变**：— 
- **本地落实 / 内部再分配**：I2
- **验证方法与结果 / 证据**：`VRC-API-002`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：无

#### 1.1.3 `C-TRUST-3` · 恒定时间比较
- **上级基线与决定状态**：机制 M-TRUST §3.1；已采用
- **适用条件**：凭据校验
- **继承预算或行为保证**：`hmac.compare_digest`
- **可自行选择 / 不可改变**：实现可自选；恒定时间不可变
- **本地落实 / 内部再分配**：`auth.py`
- **验证方法与结果 / 证据**：`VRC-API-002`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：无

#### 1.1.4 `C-TRUST-4` · 401/403 不泄露存在性
- **上级基线与决定状态**：机制 M-TRUST §3.1；已采用
- **适用条件**：错误映射
- **继承预算或行为保证**：响应不可区分
- **可自行选择 / 不可改变**：—
- **本地落实 / 内部再分配**：I1 错误信封；§8.5
- **验证方法与结果 / 证据**：`VRC-API-002`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：无

#### 1.1.5 `C-TRUST-5` · 免登录仅限受信网络
- **上级基线与决定状态**：机制 M-TRUST §3.1；已采用
- **适用条件**：免登录判定
- **继承预算或行为保证**：loopback / 受信私网 / DEV
- **可自行选择 / 不可改变**：网络集合可自选；范围不可变
- **本地落实 / 内部再分配**：`auth.py` `unauthenticated_principal`
- **验证方法与结果 / 证据**：`VRC-API-002`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：无

#### 1.1.6 `C-INFER-1/2` · 标准 Responses SSE、terminal 唯一
- **上级基线与决定状态**：机制 M-INFER §3.1；已采用
- **适用条件**：`POST /v1/responses`
- **继承预算或行为保证**：只发标准事件；恰好一个 terminal
- **可自行选择 / 不可改变**：传输实现可自选；事件子集/终态不可变
- **本地落实 / 内部再分配**：I3；§5.2、§7
- **验证方法与结果 / 证据**：`VRC-API-003`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：与 M003 一致

#### 1.1.7 `C-OBS-5` · 调试能力经 Observability 暴露
- **上级基线与决定状态**：系统设计 §3.1；已采用
- **适用条件**：调试开关
- **继承预算或行为保证**：入口层不直连基础层
- **可自行选择 / 不可改变**：—
- **本地落实 / 内部再分配**：I1 经 M005；§5.5
- **验证方法与结果 / 证据**：`VRC-API-001`；NOT_RUN
- **差距 / 变更影响 / 反馈责任**：与 M005 一致

### 1.2 使用场景（谁在什么情况下用它）

M001 是 LLMTier 的**唯一对外入口**：所有外部交互都先经过它，再按端点转给业务模块。因此它的使用场景覆盖三类使用者、七类调用：

![M001 使用场景](../assets/diagrams/diagram-m001-usecase.png)

[可编辑 SVG 源](../assets/diagrams/diagram-m001-usecase.svg)

图 M001-U1 · 使用场景：5 类外部角色经 M001 进入，M001 内部做信任判定/路由/SSE/静态/健康/错误信封，再转给 M003/M004/M005 或交付 M002 产物。外部系统只在场景图中出现，不进入 M001 内部。

#### 1.1.1 SC-API-INFER · 推理
- **使用方 / 角色**：Consumer（Piko）
- **何时触发**：Agent 需要一次模型推理
- **入口**：`POST /v1/responses`（SSE）
- **可观察结果**：标准 SSE + terminal + token Usage
- **去向**：M003 Inference（机制 M-INFER）

#### 1.1.2 SC-API-EMBED · 向量化
- **使用方 / 角色**：Consumer（Slinky）
- **何时触发**：业务需要向量化
- **入口**：`POST /v1/embeddings`
- **可观察结果**：向量 + Usage
- **去向**：M003 Inference

#### 1.1.3 SC-API-SELF-USAGE · 查自身用量
- **使用方 / 角色**：Consumer
- **何时触发**：需要核对自身 token 用量
- **入口**：`GET /v1/usage`
- **可观察结果**：分页用量（仅自身）
- **去向**：M004 Management（机制 M-METER）

#### 1.1.4 SC-API-ADMIN · 管理配置与探测
- **使用方 / 角色**：Operator
- **何时触发**：维护 provider/deployment/等级、探测后端
- **入口**：`GET/POST/PATCH/DELETE /v1/providers`、`/v1/deployments`、`/v1/service-levels`、`POST /v1/probes`
- **可观察结果**：配置版本 + `ETag` / 探测结果
- **去向**：M004 Management（机制 M-CONFIG）

#### 1.1.5 SC-API-OBS-QUERY · 查询审计/日志/统计/诊断
- **使用方 / 角色**：Operator
- **何时触发**：需要证据或排障
- **入口**：`/v1/audit`、`/v1/logs`、`/v1/stats`、`/v1/runtime`、`/v1/diagnostics*`、`/v1/trace/{id}`
- **可观察结果**：视图（审计/日志/统计/快照/trace）
- **去向**：M004 / M005（机制 M-OBS）

#### 1.1.6 SC-API-HEALTH · 存活/就绪探测
- **使用方 / 角色**：运维 / 探针
- **何时触发**：存活或可接流量的探测
- **入口**：`GET /healthz`、`GET /readyz`
- **可观察结果**：健康/就绪 JSON
- **去向**：本模块

#### 1.1.7 SC-API-CONSOLE · 打开控制台
- **使用方 / 角色**：Operator（浏览器）
- **何时触发**：打开 Web 控制台
- **入口**：`GET /ui/*`
- **可观察结果**：静态资源（M002 产物）
- **去向**：本模块（交付 M002）

**共性**：所有场景都走同一条入口链——**信任判定 → 路由 → （业务请求）转发 或 （健康/静态）直接响应**。这正是 M001 存在的理由：把"传输、鉴权、请求身份、错误信封"从各业务模块中收口到一处，业务模块只需面对已认证的 `Principal` 与已解析的 body。

**场景 → 端点 → 机制**：SC-API-INFER 承载机制 M-INFER（§9 端点、§10 失败）；SC-API-ADMIN/OBS-QUERY 承载 M-CONFIG/M-METER/M-OBS；全部场景承载 M-TRUST（信任判定）。

## 2. 需求、功能与验收条件

每个功能用固定字段列出（调用方 / 输入 / 行为 / 输出 / 错误 / 验收）。来源：使用场景 §1.1 与机制 §14.4。

### 2.1 F-API-LISTEN · 启动监听服务
- **调用方**：运维
- **输入**：`host` / `port` / `database` / `settings`
- **行为**：装配 `Application`，启动 `ThreadingHTTPServer`（每请求一线程）
- **输出**：监听就绪
- **错误**：端口占用 → 启动失败
- **验收**：进程监听指定地址

### 2.2 F-API-DISPATCH · 路由分发
- **调用方**：Consumer / Operator
- **输入**：`method` + `path` + `headers` + `body`
- **行为**：健康/静态优先 → 引导拦截 → 路由匹配 → 调用业务处理器
- **输出**：分发调用
- **错误**：未命中 → 404 `not_found`
- **验收**：已知路由命中，未知路由 404

### 2.3 F-API-AUTH · 访问信任判定
- **调用方**：全部
- **输入**：`Authorization` / 客户端地址 / 端点
- **行为**：按端点选 `data`/`admin` 角色，免登录或 Bearer 判定，产出 `Principal`
- **输出**：`Principal`
- **错误**：503 `auth_not_configured` / 401 / 403
- **验收**：端点→角色映射正确；**下游不二次校验**（C-TRUST-1）

### 2.4 F-API-REQID · 请求身份
- **调用方**：全部
- **输入**：—
- **行为**：每请求生成 `req_<32hex>`，写入响应头与日志/trace
- **输出**：`X-Request-ID`
- **错误**：—
- **验收**：响应头与日志/trace 一致

### 2.5 F-API-BODY · 请求体限长与解析
- **调用方**：POST / PATCH
- **输入**：JSON body
- **行为**：限长 2 MB 后 `json.loads`
- **输出**：`dict`
- **错误**：413 `request_too_large`；400 `invalid_json`
- **验收**：超限 413；非法 JSON 400

### 2.6 F-API-SSE · 流式传输
- **调用方**：Consumer
- **输入**：业务 `ResponsesResponse`
- **行为**：发送 `text/event-stream`，逐帧 `flush`
- **输出**：SSE 帧 + terminal
- **错误**：客户端断开 → 结束本次调用（不抛）
- **验收**：帧序与 terminal 唯一（C-INFER-1/2）

### 2.7 F-API-STATIC · 静态资源交付
- **调用方**：Operator
- **输入**：`/ui/*` 路径
- **行为**：安全解析并返回 Web UI 静态资源
- **输出**：文件响应
- **错误**：越界/缺失 → 404
- **验收**：目录穿越被拒

### 2.8 F-API-HEALTH · 健康与就绪
- **调用方**：运维 / 探针
- **输入**：—
- **行为**：`/healthz`（存活）、`/readyz`（就绪）
- **输出**：JSON 状态
- **错误**：not ready → 503
- **验收**：引导失败时 `/readyz` 503

### 2.9 F-API-ERRMAP · 统一错误信封
- **调用方**：全部
- **输入**：`ApiError` / 未知异常
- **行为**：统一错误信封；未知异常记日志后 500
- **输出**：错误 JSON
- **错误**：—
- **验收**：所有错误走同一信封

## 3. UI、CLI 或设备操作面

本模块是服务端点，无独立 CLI/UI；对外"操作面"即 HTTP 端点集合，逐条契约见 §9。

#### S-API-V1 · `/v1/*` 业务端点
- **操作**：HTTP 调用
- **输入**：见 §9
- **正常结果**：2xx JSON / SSE
- **Empty/Error/Disabled**：见 §2 各功能错误列

#### S-API-UI · `/ui/*` 控制台静态资源
- **操作**：浏览器
- **输入**：路径
- **正常结果**：静态资源
- **Empty/Error/Disabled**：404

#### S-API-HEALTH · 健康与就绪
- **操作**：GET
- **输入**：无
- **正常结果**：健康/就绪 JSON
- **Empty/Error/Disabled**：503 not_ready

## 4. 外部边界与依赖

#### 依赖 1 · M003 Inference
- **本单元调用或消费**：消费推理 / 向量化业务接口
- **本单元提供**：转发 `/v1/responses`、`/v1/embeddings`
- **契约**：内部函数（§9）
- **timeout/失败影响**：业务错误按 `ApiError` 映射

#### 依赖 2 · M004 Management
- **本单元调用或消费**：消费管理 / 审计 / 日志 / 统计接口
- **本单元提供**：转发 `/v1/providers` 等管理面
- **契约**：内部函数
- **timeout/失败影响**：同上

#### 依赖 3 · M005 Observability
- **本单元调用或消费**：消费诊断接口与关联标识
- **本单元提供**：转发 `/v1/diagnostics`、`/v1/trace`
- **契约**：内部函数
- **timeout/失败影响**：观测 fail-open

#### 依赖 4 · Consumer（外部）
- **本单元调用或消费**：—
- **本单元提供**：`/v1/responses`、`/v1/embeddings`、SSE
- **契约**：见 OpenAPI（机器 authority）
- **timeout/失败影响**：断开 → 结束本次调用

#### 依赖 5 · Operator（外部）
- **本单元调用或消费**：—
- **本单元提供**：管理面 + `/ui/*`
- **契约**：见 OpenAPI
- **timeout/失败影响**：—

## 5. 内部结构与实现位置

### 5.1 内部组成

本模块为单进程内的入口适配层
，内部由五个组件组成；组件共享同一请求上下文（`request_id`、`Principal`、body）。

![M001 内部结构](../assets/diagrams/diagram-m001-http-api-structure.png)

[可编辑 SVG 源](../assets/diagrams/diagram-m001-http-api-structure.svg)

图 M001-S1 · M001 内部结构：I1 Dispatch 与 I2 Auth/Validation 为公共层，I3 SSE Transport / I4 Static Server / I5 Health 为出口组件；对外是 Consumer/Operator（HTTP/SSE），对下调用 M003/M004/M005（内部函数）。

#### I1 · Dispatch
- **处理与协作**：解析 path/method、路由表匹配、调用业务处理器、统一错误出口
- **输入/输出**：`self.path` → 业务调用
- **文件/symbol**：`app.py` `Handler._dispatch`

#### I2 · Auth/Validation
- **处理与协作**：端点→角色、免登录/凭据判定、body 解析与限长
- **输入/输出**：headers/address/body → `Principal`、dict
- **文件/symbol**：`app.py` `_auth`/`_auth_either`/`_body` + `auth.py`

#### I3 · SSE Transport
- **处理与协作**：发送 SSE 头、逐帧 flush、断开捕获
- **输入/输出**：`ResponsesResponse` → 帧序列
- **文件/symbol**：`app.py`（`/v1/responses` 分支）+ `sse.py`

#### I4 · Static Server
- **处理与协作**：安全解析 `/ui/*`、返回静态文件
- **输入/输出**：路径 → 文件
- **文件/symbol**：`app.py` `_static` + `webui/`

#### I5 · Health/Readiness
- **处理与协作**：`/healthz`、`/readyz`、引导失败状态
- **输入/输出**：无 → 状态 JSON
- **文件/symbol**：`app.py` + `health.py`

图 A1（系统设计 §3.1）中 M001 的框即本模块边界；内部五个组件同进程、无线程池自建（由 `ThreadingHTTPServer` 每请求一线程提供）。请求级生命周期见 §6，主流程见 §7。

### 5.2 内部调用过程

#### 5.2.1 `CALL-API-REQ` · 一次请求的分发与调用链
- **入口与调用上下文**：`ThreadingHTTPServer` 每请求一线程 → `Handler._run`（进程内、请求线程）
- **调用链（文件 / symbol → 文件 / symbol）**：见下方调用链代码块
- **逐步传递的数据**：`self.path`/`method`/`headers` → `Principal` → body dict → 业务结果 → HTTP 响应
- **返回、异常与清理**：`ApiError` 统一信封；未知异常 500；`finally` 关闭线程内 Store 连接
- **对应流程 / 接口 / 验证**：§7 P-API-REQ / §9 端点 / `VRC-API-001..003`

```text
ThreadingHTTPServer（进程级）
 └─ Handler._run()                                # app.py：生成 self.request_id
      ├─ Handler._dispatch()                      # 路由（path/method）
      │    ├─ health_view(version)                # health.py  → dict           （/healthz）
      │    ├─ readiness_view(registry)            # health.py  → (dict, status)（/readyz）
      │    ├─ Handler._static(path)               # /ui/* 静态
      │    ├─ Handler._auth(role)                 # 端点→角色
      │    │    ├─ unauthenticated_principal(addr, headers, role)  # auth.py → Principal|None
      │    │    └─ authenticate(headers, role)                     # auth.py → Principal（否则 401/403）
      │    ├─ Handler._body()                     # 限长 2 MB → json.loads → dict（否则 413/400）
      │    ├─ diagnostics.record_trace(...)       # M005（received）
      │    ├─ ResponsesService.create(principal, request_id, body, ...)   # M003 业务
      │    ├─ response_stream(response)           # sse.py → Iterable[bytes] 逐帧
      │    └─ (except ApiError) ApiError.envelope()   # errors.py → 错误信封
      └─ finally: Store.close()                   # M007 线程内连接
```

### 5.3 文件间接口契约（实现级；对外机器契约见 §9）

每条接口给出所在文件、符号、签名、输入与输出/异常。

#### IF-1 `app.py` · `Handler._run`
- **签名**：`() -> None`
- **输入**：—
- **输出 / 异常**：写响应（统一错误出口）

#### IF-2 `app.py` · `Handler._dispatch`
- **签名**：`() -> None`
- **输入**：`self.path`,`self.command`,`self.headers`
- **输出 / 异常**：写响应；可抛 `ApiError`

#### IF-3 `app.py` · `Handler._auth`
- **签名**：`(role:str="data") -> Principal`
- **输入**：headers, client_address
- **输出 / 异常**：`Principal`；`ApiError(503/401/403)`

#### IF-4 `app.py` · `Handler._auth_either`
- **签名**：`() -> tuple[Principal,bool]`
- **输入**：headers, client_address
- **输出 / 异常**：`(Principal,is_admin)`；`ApiError`

#### IF-5 `app.py` · `Handler._body`
- **签名**：`() -> dict`
- **输入**：request body
- **输出 / 异常**：`dict`；`ApiError(413 request_too_large / 400 invalid_json)`

#### IF-6 `app.py` · `Handler._json`
- **签名**：`(status:int, data, headers:dict|None=None) -> None`
- **输入**：—
- **输出 / 异常**：写 JSON + `X-Request-ID`

#### IF-7 `app.py` · `Handler._static`
- **签名**：`(path:str) -> None`
- **输入**：路径
- **输出 / 异常**：写文件；`ApiError(404 not_found)`

#### IF-8 `auth.py` · `unauthenticated_principal`
- **签名**：`(client_address:str, headers, role:str) -> Principal|None`
- **输入**：地址/头
- **输出 / 异常**：免登录 `Principal` 或 `None`

#### IF-9 `auth.py` · `authenticate`
- **签名**：`(headers, role:str) -> Principal`
- **输入**：头
- **输出 / 异常**：`Principal`；`ApiError(503/401/403)`

#### IF-10 `auth.py` · `authenticate_any`
- **签名**：`(headers, client_address:str) -> Principal`
- **输入**：头/地址
- **输出 / 异常**：`Principal`；`ApiError(401/403)`

#### IF-11 `errors.py` · `ApiError`
- **签名**：`dataclass(status,code,message,param,retryable,headers,extra)`
- **输入**：—
- **输出 / 异常**：异常载体

#### IF-12 `errors.py` · `ApiError.envelope`
- **签名**：`() -> dict`
- **输入**：—
- **输出 / 异常**：`{"error":{message,type,code,param,retryable,...}}`

#### IF-13 `errors.py` · `require`
- **签名**：`(condition:bool, status:int, code:str, message:str, param:str|None=None) -> None`
- **输入**：—
- **输出 / 异常**：条件不成立抛 `ApiError`

#### IF-14 `sse.py` · `frame`
- **签名**：`(event:str, data:dict) -> bytes`
- **输入**：—
- **输出 / 异常**：单帧字节

#### IF-15 `sse.py` · `response_stream`
- **签名**：`(response:dict) -> Iterable[bytes]`
- **输入**：终态响应
- **输出 / 异常**：帧序列（terminal + `[DONE]`）

#### IF-16 `health.py` · `health_view`
- **签名**：`(version:str) -> dict`
- **输入**：—
- **输出 / 异常**：`{"status":"ok","version":...}`

#### IF-17 `health.py` · `readiness_view`
- **签名**：`(registry:Registry) -> tuple[dict,int]`
- **输入**：—
- **输出 / 异常**：就绪 JSON + HTTP 状态

### 5.4 HTTP 服务提供方式（服务器、线程模型与生命周期）

| 方面 | 本项目的做法 |
|---|---|
| 服务器 | Python 标准库 `http.server.ThreadingHTTPServer` + `BaseHTTPRequestHandler`（`app.py`）；**不**引入第三方 web 框架、不自建 WSGI/ASGI 栈 |
| 装配与启动 | `serve(host, port, database, settings)`：建 `Application` → `ThreadingHTTPServer((host,port), handler_factory(app))` → `serve_forever()`；`KeyboardInterrupt` → `server_close()` + `app.store.close()` |
| 处理器绑定 | `do_GET = do_POST = do_PATCH = do_DELETE = _run`；`server_version = "LLMTier/0.3"` |
| 线程模型 | `ThreadingHTTPServer` **每请求一线程**；无自建线程池/工作队列（并发上限受 OS 线程/连接数约束）|
| 连接与 fd 管理 | `Store` 按线程缓存 SQLite 连接（`threading.local`）；`Handler._run` 的 `finally` 调 `app.store.close()` 关闭**当前线程**连接，防止每请求泄漏 db/wal/shm fd（macOS 默认 256 fd 上限）|
| 请求生命周期 | `_run` 生成 `request_id` → `_dispatch` → 统一错误出口；每请求独立、无跨请求状态 |
| 绑定与安全边界 | 默认绑定 loopback / 私网；TLS **不在**进程内，生产由前置反向代理终止（系统设计 §6.3），进程由 systemd 托管 |
| 限流/超时 | 本模块不做业务限流；准入/队列/超时属 M003；本模块只做 body 限长（2 MB）与传输层读写 |

### 5.5 依赖方向

`app.py` 依赖
 `auth.py`/`errors.py`/`sse.py`/`health.py` 与业务服务；反向**不被**依赖（基础层不回调入口），符合系统设计 §3.1 的单向依赖。

## 6. 数据模型、状态与 ownership

#### `request_id`
- **所有者 / 访问方式**：I1 构造，随响应头/日志/trace 传递
- **出生与结束**：请求开始生成；请求结束废弃
- **成功 / 失败后的归属**：只读随请求；不持久化

#### `Principal`
- **所有者 / 访问方式**：I2 构造，交业务模块只读消费
- **出生与结束**：请求开始；请求结束
- **成功 / 失败后的归属**：请求级；不落库

#### request body
- **所有者 / 访问方式**：I2 解析，交业务模块只读
- **出生与结束**：请求开始；请求结束
- **成功 / 失败后的归属**：请求级

#### 线程 / 连接
- **所有者 / 访问方式**：`ThreadingHTTPServer` 提供
- **出生与结束**：每请求一线程；请求结束关闭
- **成功 / 失败后的归属**：每请求在 `finally` 关闭 Store 连接

**数据结构（字段级）**：

#### `Principal`
- **定义位置**：`auth.py`
- **字段**：`principal_id: str(≤128)`、`role: Literal["data","admin"]`
- **说明**：`@dataclass(frozen=True, slots=True)`；请求级、不持久化、不落日志

#### `ApiError`
- **定义位置**：`errors.py`
- **字段**：`status:int`、`code:str`、`message:str`、`param:str|None`、`retryable:bool`、`headers:dict|None`、`extra:dict|None`
- **说明**：`@dataclass(slots=True)`；`envelope()` 产出 `{"error":{...}}`

#### `request_id`
- **定义位置**：`app.py`
- **字段**：`str`（`req_<32hex>`）
- **说明**：请求身份；写入 `X-Request-ID`、日志与 trace

#### request body
- **定义位置**：—
- **字段**：`dict`
- **说明**：解析后的 JSON；只读交接给业务模块

#### SSE 帧
- **定义位置**：`sse.py`
- **字段**：`event:<name>\ndata:<json>\n\n`（UTF-8）
- **说明**：传输单元；`sequence_number` 单调递增

本模块**无自有持久状态**；不写库。持久化由 M007 `util` 承担。

## 7. 主流程与数据流

![M001 内部流程：分发与 SSE](../assets/diagrams/diagram-m001-http-api-flow.png)

[可编辑 SVG 源](../assets/diagrams/diagram-m001-http-api-flow.svg)

图 M001-P1 · M001 请求级内部流程：分发（P-API-REQ）与流式（P-API-SSE）在同一条入口链上，正常、拒绝、断开分支都展开。菱形判定来自 `_dispatch` 当前的路径/方法/信任/body 结果，不依赖远端等待。

**内部流程正文**：请求进入后由 **I1 Dispatch** 生成 `request_id` 并按路径分类；**健康/静态**由 I1 直接响应，**引导失败**在业务路由前拦截返回，**业务请求**交 **I2 Auth/Validation**。I2 先按端点选角色并判定信任（失败 → 401/403），再解析 body（超限 413 / 非法 400），随后回到 I1 调用业务处理器（M003/M004/M005）。业务返回后分两条路：**非 SSE** 由 I1 写 JSON 响应；**SSE** 交 **I3 SSE Transport** 发送流头并逐帧 `flush`——连接断开则记 `aborted` 结束本次调用，正常则记 `completed`。无论走到哪个出口，`finally` 都关闭线程内的 Store 连接。

#### P-API-REQ · 任意 HTTP 请求
- **触发/适用条件**：任意 HTTP 请求
- **图与正文位置**：本段 / 图 M001-P1
- **正常出口**：I1 分发并返回业务结果
- **异常出口**：`ApiError` 信封；未知异常 500；引导失败拦截

#### P-API-SSE · 流式返回
- **触发/适用条件**：`/v1/responses` 成功
- **图与正文位置**：本段 / 图 M001-P1；机制 M-INFER §6
- **正常出口**：SSE 帧 + terminal，记 `completed`
- **异常出口**：客户端断开 → 记 `aborted` 并结束

**P-API-REQ 步骤**（数据形态 / 执行上下文 / 状态变化）：

#### 步骤 1 · 生成请求身份
- **输入**：HTTP 请求
- **执行组件**：I1
- **处理/规则**：生成 `req_<hex>`
- **输出/交给谁**：`self.request_id`（贯穿全链）

#### 步骤 2 · 分类与路由
- **输入**：path/method
- **执行组件**：I1
- **处理/规则**：健康/静态优先 → 引导拦截 → 路由匹配
- **输出/交给谁**：命中分支；未命中 → 404

#### 步骤 3 · 角色与信任
- **输入**：端点
- **执行组件**：I2
- **处理/规则**：端点→角色；免登录/凭据判定
- **输出/交给谁**：`Principal`（交业务只读）

#### 步骤 4 · body 限长与解析
- **输入**：body（POST/PATCH）
- **执行组件**：I2
- **处理/规则**：限长 2 MB、JSON 解析
- **输出/交给谁**：dict（交业务只读）；413/400

#### 步骤 5 · 调用业务处理器
- **输入**：端点 + Principal + dict
- **执行组件**：I1
- **处理/规则**：调用业务处理器（M003/M004/M005）
- **输出/交给谁**：业务结果 或 `ApiError`

#### 步骤 6 · 写响应
- **输入**：结果
- **执行组件**：I1
- **处理/规则**：写响应头（`X-Request-ID` / `ETag` / 关联）与体
- **输出/交给谁**：HTTP 响应；非 SSE 出口

#### 步骤 7 · 清理连接
- **输入**：—
- **执行组件**：I1
- **处理/规则**：`finally` 关闭线程内 Store 连接
- **输出/交给谁**：fd 释放

**P-API-SSE 步骤**：Step 5 返回 `ResponsesResponse` 后，I1 发送 `Content-Type: text/event-stream` 与回显头 → I3 逐帧 `response_stream` 写出并 `flush`（帧序/terminal 唯一由 M003 保证）→ 断开捕获记 `aborted`，正常记 `completed`。SSE 的详细事件契约见机制 M-INFER §6，不在本模块重复。

## 8. 关键算法与业务规则

#### 8.1 `RULE-API-ROUTE` · 路由匹配
- **输入前提 / 适用条件**：任意请求
- **算法 / 规则 / 选择依据**：`path` 精确匹配 + 正则匹配（`/v1/models/{id}` 等）；先健康/静态 → `bootstrap_error` 拦截 → 业务路由
- **结果 / 不变量 / 边界**：无匹配 → 404 `not_found`
- **复杂度 / 资源限制**：O(路由数)
- **允许替换范围 / 不可改变保证**：匹配实现可自选；优先级不可变
- **具体输入推演 / 验证项**：未知路径 → 404；`VRC-API-001`

#### 8.2 `RULE-API-ROLE` · 端点→角色映射
- **输入前提 / 适用条件**：鉴权
- **算法 / 规则 / 选择依据**：`/v1/models`、`/v1/responses`、`/v1/embeddings` → `data`；`/v1/usage` → either（按凭据定 role）；其余管理面 → `admin`
- **结果 / 不变量 / 边界**：映射固定
- **复杂度 / 资源限制**：O(1)
- **允许替换范围 / 不可改变保证**：实现可自选；映射不可变
- **具体输入推演 / 验证项**：data 访问 admin 端点 → 403；`VRC-API-002`

#### 8.3 `RULE-API-TRUST` · 信任判定（M-TRUST）
- **输入前提 / 适用条件**：入口
- **算法 / 规则 / 选择依据**：无 `Authorization` 且地址为 loopback/受信私网（或 DEV loopback）→ 免登录；否则 Bearer 恒定时间比较
- **结果 / 不变量 / 边界**：401/403 不泄露存在性
- **复杂度 / 资源限制**：O(1)
- **允许替换范围 / 不可改变保证**：实现可自选；恒定时间不可变
- **具体输入推演 / 验证项**：受信地址免登录；`VRC-API-002`

#### 8.4 `RULE-API-STATIC` · 静态安全
- **输入前提 / 适用条件**：`/ui/*`
- **算法 / 规则 / 选择依据**：`target.resolve()` 必须落在 `webui/` 内
- **结果 / 不变量 / 边界**：越界/缺失 → 404
- **复杂度 / 资源限制**：O(1)
- **允许替换范围 / 不可改变保证**：实现可自选；越界拒绝不可变
- **具体输入推演 / 验证项**：`../` 路径 → 404；`VRC-API-004`

#### 8.5 `RULE-API-ERRMAP` · 错误信封
- **输入前提 / 适用条件**：任意错误
- **算法 / 规则 / 选择依据**：`ApiError.envelope()` → `{"error":{message,type,code,param,retryable,...}}`；未知异常记 `unhandled_error` 后 500
- **结果 / 不变量 / 边界**：所有错误走同一信封
- **复杂度 / 资源限制**：O(1)
- **允许替换范围 / 不可改变保证**：实现可自选；信封字段不可变
- **具体输入推演 / 验证项**：未知异常 → 500 + 日志；`VRC-API-001`

## 9. 接口与机器契约

对外契约的机器 authority 是 `interfaces/openapi/llmtier.openapi.json`；本模块不重复定义字段，只负责路由与传输语义。

### 9.1 **对外端点集合**
（按用途分组；字段/错误见 OpenAPI）

- **推理 / 向量化**：
	- `POST /v1/responses`（SSE）
	- `POST /v1/embeddings`
- **模型目录**：
	- `GET /v1/models`
	- `GET /v1/models/{id}`
- **用量 / 审计 / 日志**：
	- `GET /v1/usage`
	- `DELETE /v1/usage`
	- `GET /v1/audit`
	- `GET /v1/logs`
- **管理面**：
	- `/v1/providers`
	- `/v1/deployments`
	- `/v1/service-levels`（GET / POST / PATCH / DELETE）
	- `POST /v1/probes`
	- `GET /v1/providers/{id}/usage`
	- `GET /v1/providers/{id}/models`
- **运行时 / 统计**：
	- `GET /v1/runtime`
	- `GET /v1/stats`
- **诊断**：
	- `GET/PATCH /v1/diagnostics`
	- `GET /v1/diagnostics/snapshots`
	- `GET /v1/diagnostics/stats`
	- `GET/PATCH /v1/deployments/{id}/diagnostics`
	- `GET /v1/trace/{request_id}`
- **健康 / 静态**：
	- `GET /healthz`
	- `GET /readyz`
	- `GET /ui/*`

### 9.2**内部接口**
（供业务模块消费）

#### IF-API-1 `Handler._auth(role)` / `_auth_either()`
- **形态**：函数
- **语义**：产出 `Principal`（委托 `auth.py`）

#### IF-API-2 `Handler._body()`
- **形态**：函数
- **语义**：限长 / 解析 body

#### IF-API-3 `Handler._json(status, data, headers)`
- **形态**：函数
- **语义**：JSON 响应 + `X-Request-ID`

## 10. 并发、失败与恢复

#### 10.1 并发请求
- **并发/失败点**：每请求一线程
- **检测**：—
- **行为**：各请求独立；共享 `Application` 只读引用
- **幂等/重试**：无状态
- **最终状态**：正常

#### 10.2 客户端断开（SSE）
- **并发/失败点**：写失败
- **检测**：`BrokenPipeError` / `ConnectionResetError`
- **行为**：记 `aborted`，结束本次调用
- **幂等/重试**：不重放
- **最终状态**：结束

#### 10.3 请求体超限
- **并发/失败点**：请求处理
- **检测**：`Content-Length > 2MB`
- **行为**：413 `request_too_large`
- **幂等/重试**：可重试（改小）
- **最终状态**：拒绝

#### 10.4 未知异常
- **并发/失败点**：处理中
- **检测**：`except Exception`
- **行为**：记 `unhandled_error` 日志后 500
- **幂等/重试**：由调用方决定
- **最终状态**：500

#### 10.5 连接泄漏
- **并发/失败点**：线程结束
- **检测**：`finally`
- **行为**：关闭线程内 Store 连接
- **幂等/重试**：—
- **最终状态**：fd 释放

#### 10.6 引导失败
- **并发/失败点**：任意 `/v1/*`
- **检测**：`bootstrap_error`
- **行为**：返回引导错误（`/healthz`、`/readyz`、`/ui/*` 除外）
- **幂等/重试**：—
- **最终状态**：503 等

## 11. 安全、权限与可观测性

- **入口单点鉴权**（M-TRUST C-TRUST-1）：本模块是唯一判定点；下游只消费 `Principal`。
- **不泄露存在性**（INV-3）：401/403 语义统一。
- **观测**（M-OBS）：每请求 `X-Request-ID`；接收并回显 `X-Correlation-ID`/`traceparent`；`/v1/responses` 分支写 `received`/`aborted`/`completed` trace。
- 不记录凭据/body 正文；`log_message` 走脱敏日志（M008）。

## 12. 容量、性能与运行限制

#### 12.1 `CAP-API-BODY` · 请求体
- **目标 / 限制 / 单位**：≤ 2 MB
- **适用版本 / 配置 / 硬件 / 虚拟化 / 依赖**：HTTP 层
- **负载、数据规模与并发口径**：单请求
- **推导 / 测量方法与证据等级**：Specified
- **共享资源扣减 / 峰值重叠 / 余量**：—
- **超限行为 / 责任出口**：413
- **验证项 / Evidence**：`VRC-API-003`；NOT_RUN

#### 12.2 `CAP-API-CONC` · 并发
- **目标 / 限制 / 单位**：线程 / 请求
- **适用版本 / 配置 / 硬件 / 虚拟化 / 依赖**：`ThreadingHTTPServer`
- **负载、数据规模与并发口径**：局域网并发请求
- **推导 / 测量方法与证据等级**：Specified
- **共享资源扣减 / 峰值重叠 / 余量**：OS 线程上限
- **超限行为 / 责任出口**：OS 层拒绝
- **验证项 / Evidence**：`VRC-API-001`；NOT_RUN

#### 12.3 `CAP-API-SSE` · SSE 空闲超时
- **目标 / 限制 / 单位**：60 s
- **适用版本 / 配置 / 硬件 / 虚拟化 / 依赖**：业务侧 M003 规定
- **负载、数据规模与并发口径**：单流
- **推导 / 测量方法与证据等级**：Specified
- **共享资源扣减 / 峰值重叠 / 余量**：—
- **超限行为 / 责任出口**：结束本次调用
- **验证项 / Evidence**：`VRC-API-003`；NOT_RUN

#### 12.4 `CAP-API-FD` · 每请求 fd
- **目标 / 限制 / 单位**：每请求 ≤ 1 线程内 Store 连接，`finally` 关闭
- **适用版本 / 配置 / 硬件 / 虚拟化 / 依赖**：`Store`（M007）
- **负载、数据规模与并发口径**：持续请求
- **推导 / 测量方法与证据等级**：Measured（连接泄漏修复）
- **共享资源扣减 / 峰值重叠 / 余量**：OS fd 上限（macOS 256）
- **超限行为 / 责任出口**：`finally` 关闭兜底
- **验证项 / Evidence**：`VRC-API-001`；NOT_RUN

## 13. 实现步骤与文件清单

### 13.1 文件分解（设计 → 代码文件）

#### 13.1.1 `src/http_api/app.py`
- **职责（本模块内）**：I1 Dispatch、I2 Auth 分发、I3 SSE 传输、I4 静态、I5 健康；`Application` 装配
- **关键 symbol**：`Application`、`handler_factory`、`Handler._run/_dispatch/_auth/_auth_either/_body/_json/_static`
- **实现状态**：Implemented

#### 13.1.2 `src/http_api/auth.py`
- **职责（本模块内）**：信任判定（免登录 / Bearer），产出 `Principal`
- **关键 symbol**：`Principal`、`unauthenticated_principal`、`authenticate`、`authenticate_any`
- **实现状态**：Implemented

#### 13.1.3 `src/http_api/errors.py`
- **职责（本模块内）**：统一错误类型与错误信封
- **关键 symbol**：`ApiError`、`require`
- **实现状态**：Implemented

#### 13.1.4 `src/http_api/sse.py`
- **职责（本模块内）**：SSE 单帧与事件序列
- **关键 symbol**：`frame`、`response_stream`
- **实现状态**：Implemented

#### 13.1.5 `src/http_api/health.py`
- **职责（本模块内）**：健康/就绪视图
- **关键 symbol**：`health_view`、`readiness_view`
- **实现状态**：Implemented

#### 13.1.6 `src/web_ui/`
- **职责（本模块内）**：静态资源位（由 M002 提供；M001 只交付）
- **关键 symbol**：—
- **实现状态**：Implemented

### 13.2 实现步骤

#### 13.2.1 路由与分发
- **新增/修改文件**：`src/http_api/app.py`
- **关键 symbol**：`Handler._dispatch`
- **前置依赖**：业务服务实例
- **完成条件**：全部端点可达

#### 13.2.2 鉴权分发
- **新增/修改文件**：`app.py` / `src/http_api/auth.py`
- **关键 symbol**：`_auth` / `authenticate_any`
- **前置依赖**：M007 信任原语
- **完成条件**：端点→角色正确

#### 13.2.3 SSE 传输
- **新增/修改文件**：`app.py` / `src/http_api/sse.py`
- **关键 symbol**：`response_stream`
- **前置依赖**：M003 响应对象
- **完成条件**：帧序 + terminal

#### 13.2.4 静态服务
- **新增/修改文件**：`app.py` + `webui/`
- **关键 symbol**：`_static`
- **前置依赖**：M002 产物
- **完成条件**：无目录穿越

#### 13.2.5 健康/就绪
- **新增/修改文件**：`app.py` / `src/http_api/health.py`
- **关键 symbol**：`health_view` / `readiness_view`
- **前置依赖**：引导状态
- **完成条件**：503 语义正确

#### 13.2.6 错误信封
- **新增/修改文件**：`src/http_api/errors.py`
- **关键 symbol**：`ApiError.envelope`
- **前置依赖**：—
- **完成条件**：统一信封

## 14. 测试与验收

#### 14.1 F-API-DISPATCH · 路由分发
- **Test**：`at_*` 路由用例
- **正常/边界/失败场景**：正常 / 未知路由
- **Oracle**：200 / 404
- **Evidence**：系统测试报告
- **状态**：Implemented

#### 14.2 F-API-AUTH（C-TRUST-1）· 访问信任
- **Test**：T-TRUST-ENDPOINTS
- **正常/边界/失败场景**：data 凭据访问 admin 端点
- **Oracle**：403
- **Evidence**：契约 / 系统测试
- **状态**：Implemented

#### 14.3 F-API-BODY · 请求体
- **Test**：413 / invalid_json 用例
- **正常/边界/失败场景**：超限 / 非法 JSON
- **Oracle**：413 / 400
- **Evidence**：系统测试
- **状态**：Implemented

#### 14.4 F-API-SSE（C-INFER-1/2）· 流式传输
- **Test**：T-STREAM
- **正常/边界/失败场景**：事件序 / terminal 唯一
- **Oracle**：对照 OpenAPI 事件子集
- **Evidence**：契约测试
- **状态**：Implemented

#### 14.5 F-API-STATIC · 静态资源
- **Test**：目录穿越负例
- **正常/边界/失败场景**：`../` 路径
- **Oracle**：404
- **Evidence**：契约测试
- **状态**：Implemented

#### 14.6 F-API-HEALTH · 健康/就绪
- **Test**：引导失败用例
- **正常/边界/失败场景**：空库无 settings
- **Oracle**：`/readyz` 503
- **Evidence**：系统测试
- **状态**：Implemented

## 15. 风险、未决问题与引用

#### 15.ISD · 实现规格采用方式
- **采用模式**：`separate`（模块设计不兼作 ISD）
- **模块对象 ID**：M001
- **实现规格 Document ID**：`http-api-isd`（Planned）
- **metadata 覆盖映射入口**：`http-api-isd` 的 `implementation_specification.coverage_mapping`
- **理由 / 决定引用**：模块设计不兼作 ISD；独立 ISD 见 `docs/50_implementation_design/http-api-isd.md`（Planned）；原兼作理由：逻辑集中在 `app.py`，实现细节在本设计内

#### OPEN-API-1 · §5 结构图与 §3 操作面
- **问题**：§5 内部结构图已出（图 M001-S1）；§3 无独立 UI（服务端点型模块）
- **阻塞影响**：不影响实现
- **Owner**：LLMTier
- **截止/Gate**：本轮 review
- **决定或状态**：已闭环

引用：系统设计 §3.2/§7；机制 M-TRUST/M-INFER/M-METER/M-CONFIG/M-OBS §14.4；`interfaces/openapi/llmtier.openapi.json`；`tests/system/api_test_v03/`。

## 附录 A. 机制承接表

本表是**承接侧**：逐行承接各机制 §14.4 对 M001 的要求（要求侧见机制文档）。列名与机制 §14.4 对齐，改用段落式以容纳完整字段。

#### A.1 `llmtier-access-trust-mechanism` / R-TRUST-02 · 访问信任
- **来源 Capability / Step / Constraint / 接口成员**：C-TRUST-1/4、Step 3–5
- **本模块必须负责的行为与保证**：按端点选 `role`、分发；**不二次校验**
- **本模块提供 / 消费的接口**：`_auth()` / `_auth("admin")` / `_auth_either()`
- **本文落实位置**：§8、§9
- **代码文件 / symbol**：`app.py`
- **允许自行决定的范围**：分发实现
- **本地验证 / 组合验证交接**：契约

#### A.2 `llmtier-inference-stream-mechanism` / R-INF-01 · 推理与流式返回
- **来源 Capability / Step / Constraint / 接口成员**：C-INFER-1/2、Step 8、interface `response_stream`
- **本模块必须负责的行为与保证**：SSE 帧序、terminal 唯一、`request_id` 透传、请求体上限
- **本模块提供 / 消费的接口**：`response_stream`、`/v1/responses` 路由
- **本文落实位置**：§7、§8、§12
- **代码文件 / symbol**：`app.py` + `sse.py`
- **允许自行决定的范围**：缓冲/传输实现
- **本地验证 / 组合验证交接**：契约；组合（Piko 联调）

#### A.3 `llmtier-usage-metering-mechanism` / R-MET-04 · 用量计量
- **来源 Capability / Step / Constraint / 接口成员**：C-METER-5、`/v1/usage`
- **本模块必须负责的行为与保证**：路由与错误映射（503 显式化）
- **本模块提供 / 消费的接口**：路由
- **本文落实位置**：§9
- **代码文件 / symbol**：`app.py`
- **允许自行决定的范围**：映射实现
- **本地验证 / 组合验证交接**：503 用例

#### A.4 `llmtier-config-lifecycle-mechanism` / R-CFG-04 · 配置生命周期
- **来源 Capability / Step / Constraint / 接口成员**：Step 6
- **本模块必须负责的行为与保证**：管理面路由与 400/404/409/412 映射
- **本模块提供 / 消费的接口**：管理面路由
- **本文落实位置**：§8、§9
- **代码文件 / symbol**：`app.py`
- **允许自行决定的范围**：映射实现
- **本地验证 / 组合验证交接**：契约

#### A.5 `llmtier-observability-mechanism` / R-OBS-04 · 可观测性
- **来源 Capability / Step / Constraint / 接口成员**：Step 1
- **本模块必须负责的行为与保证**：诊断路由、关联标识透传/回显
- **本模块提供 / 消费的接口**：诊断路由
- **本文落实位置**：§11
- **代码文件 / symbol**：`app.py`
- **允许自行决定的范围**：解析实现
- **本地验证 / 组合验证交接**：契约
