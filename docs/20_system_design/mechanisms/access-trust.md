<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier 访问信任机制

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-access-trust-mechanism` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-22` |
| Last Modified Date | `2026-09-22` |
| Template ID | `design.system-mechanism` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/20_system_design/mechanisms/access-trust.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 机制摘要：解决什么问题

LLMTier 部署在局域网，需要判定"请求来自谁、以什么角色"，并在不引入用户/会话/SSO 体系的前提下区分 consumer 与 operator 权限。本机制规定该判定如何端到端运行、失败与恢复。

## 2. 使用场景与功能

- consumer（Piko/Slinky）调用推理/向量化端点；
- operator 调用管理端点与 Web UI；
- 内网/loopback 客户端免登录；显式携带 Bearer 时按凭据校验，作为纵深防护。

## 3. 参与方、责任和 authority

### 3.1 系统约束与参与方承接

本机制为顶层机制（上级 Mechanism ID = none），约束继承自系统设计 §3。

无父设计（纯软件项目顶层）。参与方：入口层（判定发生处）、业务层（消费 Principal）。Authority 为 LLMTier。

### 3.2 运行时统筹与确认责任

入口层在每个请求前调用信任判定，产出 `Principal(principal_id, role)`；role ∈ {consumer, operator}。判定结果同时决定可用端点集合。

### 3.3 拓扑、目标身份与共享故障域

单进程单节点；判定为进程内无状态函数，无共享故障域，无跨节点协调。

## 4. 数据结构设计

### 4.1 类型目录与完整字段

`Principal { principal_id: string(≤128), role: enum(consumer, operator) }`。

### 4.2 编码、布局与共享类型映射

Principal 不持久化，仅随请求在内存传递。

### 4.3 一致性、可见性与数据寿命

请求级寿命；不跨请求共享。

## 5. 接口设计

### 5.1 逐操作签名、错误与调用演练

- `authenticate(headers, role) -> Principal`；缺凭据、凭据不匹配分别抛 401/403。
- `unauthenticated_principal(client_address, headers, role) -> Principal | null`；命中 loopback/私网返回免登录 Principal。
- `authenticate_any(headers, client_address) -> Principal`；同一端点接受两种凭据。

错误：`auth_not_configured`(503)、`authentication_required`(401)、`permission_denied`(403)。

## 6. 正常端到端流程

请求进入 → 解析客户端地址 → 若命中受信网络且无 Authorization，返回免登录 Principal → 否则校验 Bearer 凭据 → 产出 Principal → 交由业务层使用。

### 6.1 生命周期过程与交叠操作

判定为纯函数，无生命周期；并发请求各自独立判定。

## 7. 分支和替代流程

- 无凭据 + 外网地址 → 401；
- 凭据存在但不匹配 → 403；
- 未配置凭据（非 dev） → 503。

## 8. 状态机与不变量

不变量：Principal.role 只由凭据或受信网络决定；同一请求内 role 不可变。

### 8.1 资源预留、交付、释放与复位

无资源预留。

## 9. 失败传播、重试与恢复

判定失败以标准错误返回，不重试；调用方决定重试。

## 10. 并发、排序与容量

无共享状态，容量不受限。

## 11. 安全、权限与信任边界

信任边界为受信网络集合（loopback + RFC1918 + ULA）。凭据使用常量时间比较。生产由反向代理完成 SSO；本机制不实现用户库、会话或第二认证路径。

## 12. 可观测性与证据

### 12.1 统计、日志、时间与关联

判定失败记录脱敏日志（不含凭据值）与 request_id。

### 12.2 维护命令、自检与调试路径

`/healthz` 与 `/readyz` 不参与本机制；拒绝原因通过标准错误码暴露。

## 13. 配置、兼容与部署

凭据来源为环境变量（`LLMTIER_ADMIN_TOKEN`/`LLMTIER_DATA_TOKEN`），dev 模式提供默认值。运行时不热更。

## 14. 各参与方实现清单

| 参与方 | 实现义务 |
|---|---|
| 入口层 | 每请求调用判定并传递 Principal |
| 业务层 | 只消费 Principal，不自行判定 |

## 15. 验证、上线与回滚

### 15.1 输入构造、故障控制与独立判据

用例：免登录命中、错误凭据、缺失凭据、两种凭据在同一端点。判据为状态码与 Principal.role。

### 15.2 环境部署、复位、并发隔离与自动化

本机实例 dev 模式可复现；测试实例隔离。

### 15.3 组合验收、启用与旧机制退出

随入口层实现启用；legacy CLI 退出 consumer authority。

## 16. 风险、未决问题与决定

- `LT-OPEN-03` 关联：生产 TLS 与反向代理 SSO 由部署证据承接。
- 风险：受信网络范围过宽；由部署网络策略约束。

## A. 输入基线、适用性与图文规则

输入：`docs/10_requirements/llmtier-requirements.md`、系统设计 §14。

## B. 文档控制与修订记录

初版 `0.1.0-draft.1`；修订见 Git。
