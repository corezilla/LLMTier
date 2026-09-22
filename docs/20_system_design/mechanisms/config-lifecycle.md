<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier 配置生命周期机制

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-config-lifecycle-mechanism` |
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
| Canonical Path | `docs/20_system_design/mechanisms/config-lifecycle.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 机制摘要：解决什么问题

配置从哪里来、如何校验、何时生效、如何变更与审计，以及初始化失败时系统如何保持不可接流量。

## 2. 使用场景与功能

空库首次启动从 `config/settings.json` 一次性 bootstrap；此后由管理面变更并落 SQLite；离线迁移为显式操作。

## 3. 参与方、责任和 authority

### 3.1 系统约束与参与方承接

本机制为顶层机制（上级 Mechanism ID = none），约束继承自系统设计 §3。

参与方：Management（变更）、util（存储）。Authority 为 LLMTier。

### 3.2 运行时统筹与确认责任

bootstrap 统筹于启动事务；变更统筹于管理动作并写审计。

### 3.3 拓扑、目标身份与共享故障域

单节点单文件；SQLite 为唯一运行权威。

## 4. 数据结构设计

### 4.1 类型目录与完整字段

Provider、Deployment、ServiceLevel 版本化记录；`schema_meta` 记录 bootstrap hash。

### 4.2 编码、布局与共享类型映射

字段见 `interfaces/schemas/llmtier-settings-v0.3.schema.json` 与系统设计 §8.2。

### 4.3 一致性、可见性与数据寿命

初始化后文件变化不自动重导入；不双写。

## 5. 接口设计

### 5.1 逐操作签名、错误与调用演练

- 启动：`bootstrap_settings(path)` → 校验 → 单事务写入 → `store_initialized=true`；
- 管理面：`GET/POST/PATCH/DELETE /v1/{providers,deployments,service-levels}`（ETag/If-Match）。

## 6. 正常端到端流程

启动 → 迁移 schema → 若无 bootstrap hash 则读 settings 校验并写入 → 否则跳过 → 服务就绪。

![配置引导与变更时序](../../assets/diagrams/diagram-mech-config-sequence.png)

[可编辑 SVG 源](../../assets/diagrams/diagram-mech-config-sequence.svg)

图 M · 配置引导与变更时序（实线=请求，虚线=响应；先后关系非时间比例）。

### 6.1 生命周期过程与交叠操作

变更走事务；并发变更由 ETag 保护（stale → 412）。

## 7. 分支和替代流程

- 校验失败 → 回滚并保持 not_ready；
- 再导入 → 显式离线迁移（先备份、单一版本命令）。

## 8. 状态机与不变量

不变量：初始化后 SQLite 是唯一 authority；Secret 明文不入库。

### 8.1 资源预留、交付、释放与复位

变更即交付；误变更由备份/迁移回滚。

## 9. 失败传播、重试与恢复

bootstrap 失败进程 not_ready；运行期变更失败回滚事务。

## 10. 并发、排序与容量

配置量小；变更低频，ETag 串行化。

## 11. 安全、权限与信任边界

管理面需 operator 凭据；Secret 只存引用。

## 12. 可观测性与证据

### 12.1 统计、日志、时间与关联

变更写 `audit_events`（actor/action/target/result）。

### 12.2 维护命令、自检与调试路径

`/readyz` 暴露初始化状态；迁移命令离线执行。

## 13. 配置、兼容与部署

settings 仅 bootstrap 输入；生产变更只落 SQLite。

## 14. 各参与方实现清单

| 参与方 | 义务 |
|---|---|
| 启动 | bootstrap 校验与事务 |
| Management | 变更 + 审计 |
| 基础层 | 存储与版本 |

## 15. 验证、上线与回滚

### 15.1 输入构造、故障控制与独立判据

用例覆盖首次 bootstrap、重复启动、非法引用、并发 PATCH。

### 15.2 环境部署、复位、并发隔离与自动化

测试用独立临时库。

### 15.3 组合验收、启用与旧机制退出

`LT-ADR-05`。

## 16. 风险、未决问题与决定

- `LT-ADR-05`：单次 bootstrap，不热载；
- 风险：离线迁移误操作；由备份与单一命令约束。

## A. 输入基线、适用性与图文规则

输入：系统设计 §10、`LT-ADR-05`。

## B. 文档控制与修订记录

初版 `0.1.0-draft.1`；修订见 Git。
