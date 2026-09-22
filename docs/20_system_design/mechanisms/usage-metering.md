<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier 用量计量机制

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-usage-metering-mechanism` |
| Document Version | `0.1.0-draft.2` |
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
| Canonical Path | `docs/20_system_design/mechanisms/usage-metering.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 机制摘要：解决什么问题

一次模型调用的 token 用量如何保证"不丢、不重复、可读、可对账"，并在崩溃/写入失败下不产生"没有调用"的假象。

## 2. 使用场景与功能

每次 dispatch 前登记 unknown 义务；后端返回后归一为 token 事实；consumer 查自身用量，operator 查全部并按范围清空。

## 3. 参与方、责任和 authority

### 3.1 系统约束与参与方承接

本机制为顶层机制（上级 Mechanism ID = none），约束继承自系统设计 §3。

参与方：Inference（写入）、Management（读取/清空）、libdiag/util（存储）。Authority 为 LLMTier。

### 3.2 运行时统筹与确认责任

写入由请求路径负责；账本版本只追加、单调推进 head。

### 3.3 拓扑、目标身份与共享故障域

单节点 SQLite；存储不可用返回 typed 503，不以空页冒充无记录。

## 4. 数据结构设计

### 4.1 类型目录与完整字段

`usage_obligations`（principal+request、model、endpoint、时间）、`usage_record_versions`（版本、is_final、token 字段、measurement_status、source）、`usage_heads`（当前版本）、`provider_request_bindings`（最终 provider/deployment）。

### 4.2 编码、布局与共享类型映射

字段见系统设计 §8.2 与实现设计。

### 4.3 一致性、可见性与数据寿命

同 request_id 只保留最高版本；unknown 不填零；保留期按策略。

## 5. 接口设计

### 5.1 逐操作签名、错误与调用演练

- `authorize_dispatch` / `bind_backend` / `finish`（内部）；
- `GET /v1/usage`（consumer 自身 / operator 全部，cursor + 时间窗）；
- `DELETE /v1/usage`（operator，按 model/deployment 或全部）。

## 6. 正常端到端流程

dispatch 前写 unknown 义务 → 绑定最终后端 → 后端返回 → 归一 token → 追加版本并推进 head → 查询按 `[from,to)` 与 `(recorded_at,request_id)` 稳定排序。

![用量计量时序](../../assets/diagrams/diagram-mech-meter-sequence.png)

[可编辑 SVG 源](../../assets/diagrams/diagram-mech-meter-sequence.svg)

图 M · 用量计量时序（实线=请求，虚线=响应；先后关系非时间比例）。

### 6.1 生命周期过程与交叠操作

一个记录一个生命周期；版本替换不累计。

## 7. 分支和替代流程

- 后端失败/未知 → measurement_status=unknown，成功结果不改成失败；
- 存储不可用 → 503。

## 8. 状态机与不变量

不变量：版本单调；final 不被低版本替换；相同 request_id 不累计。

### 8.1 资源预留、交付、释放与复位

unknown 义务即预留；终态即交付；清空即复位。

## 9. 失败传播、重试与恢复

terminal 后写入失败不影响已返回结果；重启后义务仍在，不会变成"没有调用"。

## 10. 并发、排序与容量

单事务推进 head；游标绑定 principal/授权/filter。

## 11. 安全、权限与信任边界

consumer 只见自身；operator 见全部；不记录 Cost/金额。

## 12. 可观测性与证据

### 12.1 统计、日志、时间与关联

用量事实为对账证据；数据面统计另属可观测性机制。

### 12.2 维护命令、自检与调试路径

`DELETE /v1/usage` 清空；清理关联孤儿记录。

## 13. 配置、兼容与部署

存储为 SQLite 单文件；清空为管理动作并审计。

## 14. 各参与方实现清单

| 参与方 | 义务 |
|---|---|
| Inference | 写义务与最终事实 |
| Management | 查询/清空/审计 |
| 基础层 | 事务与版本推进 |

## 15. 验证、上线与回滚

### 15.1 输入构造、故障控制与独立判据

用例覆盖版本替换、unknown、清空范围、孤儿清理。

### 15.2 环境部署、复位、并发隔离与自动化

测试实例隔离数据库。

### 15.3 组合验收、启用与旧机制退出

见 `LT-ADR-03`。

## 16. 风险、未决问题与决定

- `LT-ADR-03`：未知不补零；
- 风险：写放大；由单事务与保留策略约束。

## A. 输入基线、适用性与图文规则

输入：系统设计 §8、`LT-ADR-03`。

## B. 文档控制与修订记录

初版 `0.1.0-draft.1`；修订见 Git。
