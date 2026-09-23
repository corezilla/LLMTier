<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier 访问信任机制

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-access-trust-mechanism` |
| Document Version | `0.1.0-draft.4` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-22` |
| Last Modified Date | `2026-09-22` |
| Template ID | `design.system-mechanism` |
| Template Version | `2.4.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/20_system_design/mechanisms/access-trust.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 机制摘要：解决什么问题

LLMTier 部署在局域网，需要判定"**请求来自谁、以什么角色**"，并在**不引入用户/会话/SSO 体系**的前提下区分 consumer（data）与 operator（admin）权限。

**为什么是跨模块机制**：判定发生在**入口层**，但结果（`Principal`）被**业务层全部模块消费**，且决定了**可用端点集合**（data 端点 vs admin 端点）；"单点判定 + 下传 + 角色隔离"横跨入口与业务，是安全边界机制。

**输入 → 处理 → 输出**：
- 输入：HTTP 头（`Authorization`、`X-Principal-ID`）、客户端地址
- 处理：内网/loopback 免登录判定 **或** Bearer 恒定时间比较
- 输出：`Principal(principal_id, role)`，role ∈ {`data`, `admin`}

**核心取舍**：**入口单点鉴权**——判定只在入口发生一次，业务模块**不得二次校验**；凭据仅作纵深，不建用户体系。

## 2. 使用场景与功能

| Capability ID | 业务任务与触发 | 输入与可观察结果 | 提供方 / 消费者 | 实现状态 | 验证判据 |
|---|---|---|---|---|---|
| CAP-TRUST-LAN | 内网/loopback 免登录访问 | 无 `Authorization` + 受信地址 → Principal | HTTP API / 全体 | Implemented | 免登录用例 |
| CAP-TRUST-BEARER | 显式 Bearer 凭据 | token 匹配 → 对应 role | HTTP API / 全体 | Implemented | 凭据用例 |
| CAP-TRUST-DATA | data 角色访问推理/向量化 | 可用 data 端点 | HTTP API / Consumer | Implemented | 端点集合用例 |
| CAP-TRUST-ADMIN | admin 角色访问管理面 | 可用 admin 端点 | HTTP API / Operator | Implemented | 401/403 用例 |
| CAP-TRUST-ANY | 共享端点接受两种凭据 | 按匹配 role 返回 | HTTP API / 两者 | Implemented | `/v1/usage` 用例 |
| CAP-TRUST-DEV | 本地测试免登录 | `LLMTIER_DEV_MODE=1` + loopback | HTTP API / 测试 | Implemented | 测试环境 |

**不提供**：用户/会话/SSO、OAuth、细粒度 RBAC、跨节点信任传递。

## 3. 参与方、责任和 authority

### 3.1 系统约束与参与方承接

本机制为顶层机制（上级 Mechanism ID = none），约束继承自系统设计 §3。

| Constraint ID | 约束 | 参与方保证 | 自由度 | 本文落实位置 |
|---|---|---|---|---|
| C-TRUST-1 | 判定只在入口发生一次，业务不二次校验 | HTTP API | 实现方式 | §3.2、§8 |
| C-TRUST-2 | 不建用户/会话/SSO 体系 | HTTP API | — | §1、§11 |
| C-TRUST-3 | 凭据比较恒定时间，不泄露存在性 | Auth | 算法 | §5.1、§8 |
| C-TRUST-4 | 401/403 不泄露资源存在性 | 全体 | 错误映射 | §7、§11 |
| C-TRUST-5 | 免登录仅在受信网络/loopback/DEV | Auth | 网络集合 | §4.1、§7 |

### 3.2 运行时统筹与确认责任

入口层在每个请求前判定，产出 `Principal` 并下传；业务模块**只消费** `principal.role` 决定视图/权限，**不再判定**。判定结果同时决定可用端点集合。

### 3.3 拓扑、目标身份与共享故障域

单进程单节点；判定为**进程内无状态函数**，无共享故障域、无跨节点协调、无持久状态。

## 4. 数据结构设计

### 4.1 类型目录与完整字段

> 数据定义分支：**已有机器源**（见下表“机器源”列）；正文只给阅读视图与差异，不另抄完整规范。

| 类型 | 字段 | 说明 |
|---|---|---|
| `Principal` | `principal_id: str(≤128)`、`role: enum(data, admin)` | 请求级、不持久化 |

**受信网络集合**：`10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16`、`fc00::/7`（私网/loopback 免登录）。

**角色映射**：`data` = consumer（推理/向量化/自身用量）；`admin` = operator（管理面/全部用量/诊断）。

### 4.2 编码、布局与共享类型映射

不适用二进制 ABI：`Principal` 仅内存传递，不序列化、不落库。

### 4.3 一致性、可见性与数据寿命

请求级寿命；不跨请求共享、不缓存凭据。`principal_id` 取自 `X-Principal-ID`（截断 128）或按角色默认（`operator`/`consumer`）。

## 5. 接口设计

### 5.1 逐操作签名、错误与调用演练

| 操作 | 签名 | 语义 | 失败 |
|---|---|---|---|
| `unauthenticated_principal` | `(client_address, headers, role) → Principal \| None` | 无 `Authorization` 且地址受信 → 免登录 Principal | 返回 None（继续凭据路径）|
| `authenticate` | `(headers, role) → Principal` | 校验指定 role 的 Bearer | 503/401/403 |
| `authenticate_any` | `(headers, client_address) → Principal` | 共享端点接受 admin 或 data | 401/403 |

| 项 | 内容 |
|---|---|
| 缺配置 | `auth_not_configured`(503)（未设 token 且非 DEV）|
| 缺凭据 | `authentication_required`(401) |
| 凭据不匹配 | `permission_denied`(403)（**不区分 admin/data**，不泄露存在性）|
| 比较 | `hmac.compare_digest`（恒定时间）|
| 幂等 | 只读判定，无副作用 |

**调用演练**：请求带 `Authorization: Bearer <data-token>` + `X-Principal-ID: piko` → `authenticate(headers,"data")` → `Principal("piko","data")` → 业务按 role 限制到 data 端点与自身用量。无 `Authorization` 且地址 `192.168.1.42` → `unauthenticated_principal` → `Principal("trusted-lan-consumer","data")`。

## 6. 正常端到端流程

![访问信任判定时序](../../assets/diagrams/diagram-mech-trust-sequence.png)

[可编辑 SVG 源](../../assets/diagrams/diagram-mech-trust-sequence.svg)

图 M · 访问信任判定时序（实线=请求，虚线=响应；先后关系非时间比例）。

1. **解析地址**：取 `client_address`（去 zone id）。
2. **免登录判定**：无 `Authorization` 且（DEV+loopback 或 loopback/私网）→ 返回免登录 Principal（role 由端点决定）。
3. **凭据判定**：否则校验 `Bearer`，恒定时间比较 admin/data token。
4. **产出 Principal**：role + principal_id（`X-Principal-ID` 或默认）。
5. **下传**：业务模块按 `role` 选择视图/端点集合，**不再判定**。

### 6.1 交叠请求、跨轮次与生命周期边界

判定 = 每请求一次（无状态）。**交叠**：多请求各自独立判定；`authenticate_any` 先 admin 后 data（顺序固定）；无共享状态、无锁。

## 7. 分支和替代流程

| 分支 | 触发 | 处理 |
|---|---|---|
| 未配置凭据 | 无 token 环境且非 DEV | 503 `auth_not_configured` |
| 无凭据且地址不受信 | 无 `Authorization` + 非受信 | 401 `authentication_required` |
| 凭据错误 | token 不匹配 | 403 `permission_denied` |
| 未认证 loopback（DEV）| DEV 且 loopback | 免登录 operator/consumer |
| 受信 LAN | 私网地址 | 免登录 |
| 共享端点 | `authenticate_any` | 按匹配 role 返回 |

## 8. 状态机与不变量

| INV-ID | 可验证断言（量词、条件和预期必须明确） | Enforcement / 事实来源 | 反例输入/违反后的结果 | 验证项 |
|---|---|---|---|---|
| INV-1 | 判定只在入口发生一次；∀ 业务模块无鉴权调用点 | `_auth*` 仅在 HTTP Adapter | 下游二次校验 → 边界分叉 | T-TRUST-ENDPOINTS |
| INV-2 | 凭据比较恒定时间（不因前缀匹配提前返回）| `hmac.compare_digest` | 提前返回 → 时序侧信道 | T-TRUST-BEARER |
| INV-3 | ∀ 401/403：不泄露资源存在性与凭据角色差异 | 错误映射（§7）| 可区分响应 → 信息泄露 | T-TRUST-LEAK |
| INV-4 | ∀ Principal：`role ∈ {data, admin}`；无第三种 | `Principal` 类型 | 新增角色 → 端点集合不确定 | T-TRUST-ENDPOINTS |
| INV-5 | 免登录仅在 loopback / 受信私网 / DEV 命中 | `unauthenticated_principal` | 公网免登录 → 越权 | T-TRUST-LAN |
| INV-6 | 不持久化 Principal 与凭据 | 仅内存传递 | 落库/日志 → 泄密 | T-TRUST-LEAK |

### 8.1 资源预留、交付、释放与复位

无预留/租约（无状态判定）。**交付** = 每请求返回 Principal；**复位** = 请求结束即释放（无残留）。

## 9. 失败传播、重试与恢复

| Failure ID / 检测方 | 失败点与传播 | 结果已知性 | 已发生/可能副作用 | 访问安全/证据 | 操作终态 | 资源释放 | 重新准入/重试条件 |
|---|---|---|---|---|---|---|---|
| F-TRUST-1 / Auth | 未配置凭据 | 已知失败 | 无 | 无 | 503 | 无 | 配置后重试 |
| F-TRUST-2 / Auth | 缺凭据 | 已知失败 | 无 | 无 | 401 | 无 | 补凭据后重试 |
| F-TRUST-3 / Auth | 凭据错误 | 已知失败 | 无 | 无 | 403 | 无 | 修正凭据后重试 |

**恢复边界**：判定失败**不影响**已认证请求；无状态、无重试队列。凭据错误不触发任何后端调用。

## 10. 并发、排序与容量

| 作用域 | 约束 | 行为 |
|---|---|---|
| 判定 | 无状态纯函数 | 无锁、无竞争 |
| `authenticate_any` | 固定顺序 admin→data | 确定性 |
| 容量 | 无状态 | 无限流（限流属 M-INFER 准入）|

## 11. 安全、权限与信任边界

| 资产 | 身份来源 | 强制点 | 拒绝 | 审计 |
|---|---|---|---|---|
| data 端点 | Bearer(data) / 免登录 | `_auth("data")` | 401/403 | — |
| admin 端点 | Bearer(admin) / 免登录 | `_auth("admin")` | 401/403 | — |
| 共享端点 | 任一 | `_auth_either()` | 401/403 | — |

边界：consumer 只见自身数据；operator 见全部；不记录凭据；**不泄露资源存在性**（INV-3）。凭据为纵深，不替代网络边界。

## 12. 可观测性与证据

### 12.1 统计、日志、时间与关联

判定结果（role）随请求进入 trace/日志的关联上下文（M-OBS），但**凭据与 Principal 秘密不入日志**。

### 12.2 维护命令、自检与调试路径

| Maintenance API / Command / Diagnostic ID | 执行位置、入口、目标、权限 | 完整请求/语法与结果/错误契约 | 施加/回读点及覆盖 | 依赖/占用/恢复退出 | 验证 |
|---|---|---|---|---|---|
| 配置凭据 `LLMTIER_ADMIN_TOKEN` / `LLMTIER_DATA_TOKEN` | 进程环境变量；部署方 | 值 = token；无 HTTP 契约；未配置则运行期 503 | 施加=进程环境；回读=请求结果 | 需重启生效 | T-TRUST-NOCFG |
| 测试免登录 `LLMTIER_DEV_MODE=1` | 进程环境变量（**仅测试**）| 值 = `1`；仅 loopback 生效 | 施加=进程环境 | 仅测试；非生产 | T-TRUST-LAN |

## 13. 配置、兼容与部署

凭据经环境变量注入；DEV 模式仅限测试。兼容：role 集合与错误码为契约；新增角色需显式变更并回写系统设计 §3.5。

## 14. 跨责任单元分解与接口分配（下级设计输入）

本章是**要求侧**：把本机制分解到各责任单元（LLMTier 为纯软件，责任单元 = 软件模块），说明每个对象必须负责什么、提供什么接口。下级模块设计在附录"机制承接表"逐条记录**落实侧**。

### 14.1 参与方到架构对象映射

| 机制参与方（§3） | 责任单元/Owner | 架构对象 ID / 类型 / 层或领域 | 下级设计文档 | 在本机制中的主责与非职责 |
|---|---|---|---|---|
| 判定 | HTTP API / LLMTier | Auth/Validation（入口层）| `llmtier-core-design.md` | 免登录/凭据判定、产出 Principal；不建用户体系 |
| 下传与消费 | 业务模块 / LLMTier | Inference/Management/Observability（业务层）| `llmtier-core-design.md` | 按 `role` 选择视图/端点，**不二次校验** |
| 入口分发 | HTTP API / LLMTier | HTTP Adapter（入口层）| `llmtier-core-design.md` | `_auth()`/`_auth("admin")`/`_auth_either()` |
| 配置 | 启动 / LLMTier | env 读取 | `llmtier-core-design.md` | token 存在性；不存 Secret |

### 14.2 功能和步骤到责任单元分配

| Capability / Process Step / Constraint | 主责架构对象 | 协作对象 | 必须产生或消费的结果 | 固定行为 / 本地自由度 | 组合验证责任 |
|---|---|---|---|---|---|
| Step 1 解析地址（C-TRUST-5）| Auth/Validation | — | client address | 地址解析实现可自定 | T-TRUST-LAN |
| Step 2 免登录判定 | Auth/Validation | — | 免登录 Principal | 网络集合固定 | T-TRUST-LAN |
| Step 3 凭据判定（C-TRUST-3）| Auth/Validation | — | Principal | 恒定时间比较固定 | T-TRUST-BEARER |
| Step 4 产出 Principal（C-TRUST-2/4）| Auth/Validation | — | `(id, role)` | role 集合固定 | T-TRUST-ENDPOINTS |
| Step 5 下传与消费（C-TRUST-1）| 业务模块 | HTTP Adapter | 端点集合/视图 | 不二次校验固定 | T-TRUST-ENDPOINTS |

### 14.3 责任单元间接口契约

| 接口成员 ID / 固定 baseline | 提供对象 | 全部消费对象 | 调用/事件形态 | 本机制固定的语义与错误 | 期限/取消/重复及边界 |
|---|---|---|---|---|---|
| `unauthenticated_principal(client_address, headers, role)` | Auth/Validation | HTTP Adapter | 函数 | 免登录 Principal 或 None | — |
| `authenticate(headers, role)` | Auth/Validation | HTTP Adapter | 函数 | 校验指定 role | 503/401/403 |
| `authenticate_any(headers, client_address)` | Auth/Validation | HTTP Adapter | 函数 | 共享端点接受两者 | 401/403 |
| `Principal(principal_id, role)` | Auth/Validation | 全体业务模块 | 数据类 | 消费方只读 | — |

### 14.4 下级设计输入清单

| 下级要求 ID | 承接对象 ID / 下级设计文档 | 来源 Capability / Step / Constraint / 接口成员 | 必须负责的行为与保证 | 必须提供/消费的接口 | 下级必须展开的问题 | 允许自行决定的范围 | 本地验证 / 组合验证交接 |
|---|---|---|---|---|---|---|---|
| R-TRUST-01 | Auth/Validation · `llmtier-core-design.md` | C-TRUST-1/3/5、Step 1–4、interface `authenticate*` | 单点判定、恒定时间比较、不泄露存在性 | `authenticate`/`authenticate_any`/`unauthenticated_principal` | 地址解析、网络集合、错误映射 | 解析/映射实现 | 契约 |
| R-TRUST-02 | HTTP Adapter · `llmtier-core-design.md` | Step 3–5 | 按端点选 role、分发 | `_auth()`/`_auth("admin")`/`_auth_either()` | 端点→role 映射 | 分发实现 | 契约 |
| R-TRUST-03 | 业务模块（全体）· `llmtier-core-design.md` | C-TRUST-1/4、Step 5 | **不二次校验**，按 `role` 限制视图 | — | 消费点、越权防护 | 视图实现 | 组合 |
| R-TRUST-04 | 启动 · `llmtier-core-design.md` | C-TRUST-2、F-TRUST-1 | env token 存在性 | — | 503 语义 | 读取实现 | T-TRUST-NOCFG |

**约束**：任何业务模块**不得**新增鉴权调用点（C-TRUST-1）；新增角色/端点须回写本节并关联模块设计。

## 15. 验证、上线与回滚

### 15.1 输入构造、故障控制与独立判据

| Test / Constraint | 输入与预置事实 | arm/hit/release | 独立 Oracle |
|---|---|---|---|
| T-TRUST-LAN / C-TRUST-5 | 私网地址、无 Authorization | — | 免登录 Principal |
| T-TRUST-BEARER / C-TRUST-3 | 正确/错误 token | — | 200 / 403 |
| T-TRUST-ENDPOINTS / CAP-TRUST-DATA | data 凭据访问 admin 端点 | — | 403 |
| T-TRUST-SHARED / CAP-TRUST-ANY | 两种凭据访问 `/v1/usage` | — | 视图按 role 区分 |
| T-TRUST-NOCFG / F-TRUST-1 | 无 token 环境 | — | 503 |
| T-TRUST-LEAK / INV-3 | 不存在 vs 无权限资源 | — | 响应不可区分 |

### 15.2 环境部署、复位、并发隔离与自动化

测试可用 DEV 免登录；凭据用例显式设 token；复位无状态、无需清理。

### 15.3 组合验收、启用与旧机制退出

组合验收 = Consumer（Piko）以 data 凭据调用 + Operator 以 admin 凭据管理。

## 16. 风险、未决问题与决定

| ID | 类别 | 影响 | 下一步 | 状态 |
|---|---|---|---|---|
| R-TRUST-1 | 风险 | 内网免登录依赖网络边界 | 明文声明边界，凭据作纵深 | 已接受 |
| R-TRUST-2 | 风险 | 单一共享 token（无 per-user）| 与"不建用户体系"取舍一致 | 已接受 |

## A. 输入基线、适用性与图文规则

- 输入：系统设计 §3、`auth.py`、`app.py`。
- 适用性：纯软件、单进程、入口单点鉴权机制。§4.2（二进制 ABI）不适用；§8.1（租约）不适用（无状态）。
- 图：时序图（§6）表达免登录/凭据判定与下传。

## B. 文档控制与修订记录

初版 `0.1.0-draft.1`；`draft.3` 补实全部章节、增模块分解与不变量。修订见 Git。
