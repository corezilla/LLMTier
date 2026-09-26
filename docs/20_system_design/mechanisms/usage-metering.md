<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier 用量计量机制

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-usage-metering-mechanism` |
| Document Version | `0.1.0-draft.5` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-22` |
| Last Modified Date | `2026-09-25` |
| Template ID | `design.system-mechanism` |
| Template Version | `3.2.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/20_system_design/mechanisms/usage-metering.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 机制摘要：解决什么问题

一次模型调用的 token 用量必须"**不丢、不重复、可读、可对账**"，并在崩溃/写入失败下**不产生"没有调用"的假象**。

**为什么不能由一个单元独立完成**：Inference 只知"要调用"，后端只知"返回了什么"，Consumer 只该看到"自己的量"，Operator 需要"全部并可按范围清空"；计量横跨请求路径、存储事务与查询接口，是**账本型**机制。

**输入 → 处理 → 输出**：
- 输入：`(principal, request_id)` + dispatch 意图 + 后端返回的 usage
- 处理：dispatch 前登记 **unknown 义务** → 绑定最终后端 → 归一 token → **追加不可变版本并原子推进 head**
- 输出：`GET /v1/usage` 的稳定分页视图；`DELETE /v1/usage` 的范围清空

**核心取舍**：**只追加不改写** + **unknown 不补零**。宁可留一个"已调用但未测"的 unknown 事实，也绝不写成 0（0 会被误读为"没有调用"）。

## 2. 使用场景与功能

| Capability ID | 业务任务与触发 | 输入与可观察结果 | 提供方 / 消费者 | 实现状态 | 验证判据 |
|---|---|---|---|---|---|
| CAP-METER-WRITE | 每次 dispatch 前登记义务 | dispatch 前存在 unknown 记录 | Usage Recorder / Inference | Implemented | 崩溃序 fixture |
| CAP-METER-FINAL | 后端返回后写 measured | head 推进到 measured 版本 | Usage Recorder / Inference | Implemented | 契约用例 |
| CAP-METER-QUERY | Consumer 查自身用量 | 时间窗 + cursor 分页，稳定 | Management / Consumer | Implemented | 分页 snapshot 用例 |
| CAP-METER-ADMIN | Operator 查全部 | 401/403 语义，不泄露存在性 | Management / Operator | Implemented | Admin 用例 |
| CAP-METER-RESET | Operator 按 model/deployment 或全部清空 | `{deleted}` 计数 | Management / Operator | Implemented | 清空范围用例 |
| CAP-METER-SNAPSHOT | 分页期间冻结成员 | 旧页不受后续更正影响 | Management / Consumer | Implemented | snapshot 序列 fixture |

**不提供**：Cost/金额、业务任务汇总、自动对账、跨 principal 聚合。

## 3. 参与方、责任和 authority

### 3.1 系统约束与参与方承接

本机制为顶层机制（上级 Mechanism ID = none），约束继承自系统设计 §3 与 §3.4。

| Constraint ID | 约束 | 参与方保证 | 自由度 | 本文落实位置 |
|---|---|---|---|---|
| C-METER-1 | 账本只追加不改写，同 request 只留最新版本 | Usage Recorder | 存储布局 | §4.2、§4.7、§8 |
| C-METER-2 | 未知不补零（unknown ≠ 0）| Usage Recorder | 归一实现 | §4.1、§7 |
| C-METER-3 | dispatch 前先持久义务，失败则不 dispatch | Inference | 事务边界 | §6、§9 |
| C-METER-4 | 查询稳定分页（snapshot 冻结）| Management | 分页实现 | §6、§10 |
| C-METER-5 | 存储不可用显式 503，不用空页冒充 | Management | 错误映射 | §7、§9 |

### 3.2 运行时统筹与确认责任

写入由**请求路径**在事务内完成（Inference 触发，Usage Recorder 执行）；读取/清空由 Management 面负责。head 的推进是"确认"，且只能单调向前。

### 3.3 拓扑、目标身份与共享故障域

单节点 SQLite（唯一持久化由 `util` 承担）。记录身份为 `(principal_id, request_id)`；不使用 Agent/Run/Project/SourceInstance。存储不可用为独立故障域，**不得**降级为"无记录"。

## 4. 数据结构设计

> 按 STD `design-data-interface-format` 1.2.0 §2：主章“数据结构设计”，章内按**数据性质**分类（§4.1–§4.8），本层特有分析见 §4.9–§4.10。仅保留适用类别。账本结构唯一来源系统设计 §8.2/§8.7（`D-USAGE-*`/`D-PROVIDER-BINDING`）与 `util/migrations/*.sql`；本机制拥有类型 ID 前缀 `D-MET-*`，不复制列级权威。

**类别适用性**：§4.1 公共基础类型与枚举 ✓｜§4.2 业务与操作数据结构 ✓｜§4.3 配置与规则数据结构 ✓（保留/snapshot TTL）｜§4.4 通信报文结构 ✗（账本为 SQLite 行/内部函数，无消息 wire；查询报文是 HTTP JSON 投影）｜§4.5 设备与 FPGA 表项结构 ✗（纯软件，无设备/RTL）｜§4.6 运行状态数据结构 ✗（状态均在持久账本，无独立内存跨步骤状态）｜§4.7 数据库表结构 ✓｜§4.8 错误码与错误结构 ✓（引用系统 §8.8）。

### 4.1 公共基础类型与枚举

**4.1.1 `D-MET-MEASUREMENT-STATUS` · MeasurementStatus（公共基础类型与枚举）**

```text
enum MeasurementStatus { unknown, measured }
```

- **Data/Type ID、用途与来源**：

  `D-MET-MEASUREMENT-STATUS`；一次用量是否被测量的判定；唯一来源系统 §8.1 共享枚举与 `src/inference/usage.py` `finish`。

- **`unknown`**：

  必填枚举值；未测量；token 字段为 NULL（不补零）。

- **`measured`**：

  必填枚举值；仅当 `input_tokens`/`output_tokens`/`total_tokens` **三者皆为 int**。

- **跨字段与寿命**：

  `measured` 仅当三 token 皆 int；否则整体 unknown 且 token 全为 NULL（不写部分值，INV-5）；随 `usage_record_versions.measurement_status` 持久。

- **合法/拒绝实例**：

  合法 `measured`（三 token 皆 int）；边界：任一缺失 → `unknown` + NULL。

- **验证**：

  `T-MET-UNKNOWN`。

**4.1.2 `D-MET-SOURCE` · MeasurementSource（公共基础类型与枚举）**

```text
enum MeasurementSource { unavailable, provider, injected }
```

- **Data/Type ID、用途与来源**：

  `D-MET-SOURCE`；用量事实来源；唯一来源 `usage.py`（`source_override or ("provider" if measured else "unavailable")`）。

- **`unavailable`**：

  必填枚举值；未测得；`unknown ⇒ unavailable`。

- **`provider`**：

  必填枚举值；后端返回；`measured ⇒ provider`（或被 override）。

- **`injected`**：

  必填枚举值；注入路径经 `source_override=injected` 标注（C-OBS-4）。

- **跨字段与寿命**：

  `measured ⇒ source=provider`（或被 override）；`unknown ⇒ unavailable`；随 `usage_record_versions.source` 持久。

- **合法/拒绝实例**：

  合法 `provider`；边界：后端无 usage → `unavailable`。

- **验证**：

  `T-MET-UNKNOWN`、`T-OBS-INJECT`。

### 4.2 业务与操作数据结构

**4.2.1 `D-USAGE-OBLIGATION` · UsageObligation（业务与操作数据结构，继承系统 §8.2）**

```text
UsageObligation {
  principal_id: string, request_id: string, model: string,
  endpoint: string, recorded_at: timestamp, updated_at: timestamp
}
```

- **Data/Type ID、用途与来源**：

  `D-USAGE-OBLIGATION`；dispatch 前登记的一次调用义务（账本锚点）；系统设计 §8.2 唯一来源，持久 authority `util/migrations/*.sql`。

- **`principal_id`/`request_id`**：

  必填；PK `(principal_id,request_id)`。

- **`model`/`endpoint`**：

  必填字符串；等级与端点。

- **`recorded_at`/`updated_at`**：

  必填时间；首次记录 / 最近更新。

- **跨字段与寿命**：

  PK `(principal_id,request_id)`；dispatch 前必先存在；同 request 只保留一条（`INSERT OR IGNORE`）；M003 写；按 principal 隔离；追加式，随账本保留策略。

- **合法/拒绝实例**：

  合法：非流式外请求登记 unknown 义务后 dispatch；拒绝：无义务即 dispatch 被业务禁止。

- **验证**：

  `T-MET-CRASH`、系统 `VRC-INF-004`。

**4.2.2 `D-USAGE-RECORD` · UsageRecordVersion（业务与操作数据结构，继承系统 §8.2）**

```text
UsageRecordVersion {
  principal_id: string, request_id: string, record_version: int, is_final: bool,
  model: string, endpoint: string, recorded_at: timestamp, updated_at: timestamp,
  measurement_status: MeasurementStatus, source: MeasurementSource,
  input_tokens: int?, output_tokens: int?, total_tokens: int?,
  cached_input_tokens: int?, cache_write_tokens: int?, reasoning_tokens: int?
}
```

- **Data/Type ID、用途与来源**：

  `D-USAGE-RECORD`；一次调用的一次用量事实版本；系统设计 §8.2 唯一来源，authority `util/migrations/*.sql`。

- **`principal_id`/`request_id`/`record_version`**：

  必填；PK `(principal_id,request_id,record_version)`。

- **`is_final`**：

  必填布尔；是否终态版本。

- **`measurement_status`/`source`**：

  必填 `D-MET-MEASUREMENT-STATUS`（§4.1.1）/ `D-MET-SOURCE`（§4.1.2）。

- **`input_tokens`/`output_tokens`/`total_tokens`**：

  可空整数；`unknown` 时为空（不补零）。

- **`cached_input_tokens`/`cache_write_tokens`/`reasoning_tokens`**：

  可空整数；细分字段。

- **跨字段与寿命**：

  PK `(principal_id,request_id,record_version)`；**只追加**、不累计；`unknown` 时 token 为空（不补零）；M003 写；追加式，按 retention policy 保留。

- **合法/拒绝实例**：

  合法 version=2（final，measured）；边界：`unknown` → token 全空且不填零。

- **验证**：

  `T-MET-FINAL`、`T-MET-UNKNOWN`、`T-MET-CRASH`。

**4.2.3 `D-USAGE-HEAD` · UsageHead（业务与操作数据结构，继承系统 §8.2）**

```text
UsageHead {
  principal_id: string, request_id: string,
  head_record_version: int, updated_at: timestamp
}
```

- **Data/Type ID、用途与来源**：

  `D-USAGE-HEAD`；指向某 request 当前最新版本；系统设计 §8.2 唯一来源。

- **`principal_id`/`request_id`**：

  必填；PK `(principal_id,request_id)`。

- **`head_record_version`**：

  必填整数；单调不减；FK 指向存在的 record version（INV-2）。

- **`updated_at`**：

  必填时间；最近推进时间。

- **跨字段与寿命**：

  单调不减；FK 指向存在的 record version（INV-2）；读者只取 head 指向的单条版本、绝不累加（INV-3）；M003 写、按 principal 隔离；随账本保留。

- **合法/拒绝实例**：

  合法 head=2 指向 version 2；拒绝：指向不存在版本 → 约束失败。

- **验证**：

  `T-MET-FINAL`。

**4.2.4 `D-PROVIDER-BINDING` · ProviderRequestBinding（业务与操作数据结构，继承系统 §8.2）**

```text
ProviderRequestBinding {
  principal_id: string, request_id: string,
  provider_id: string, deployment_id: string, bound_at: timestamp
}
```

- **Data/Type ID、用途与来源**：

  `D-PROVIDER-BINDING`；request 与最终 provider/deployment 的绑定；系统设计 §8.2 唯一来源。

- **`principal_id`/`request_id`**：

  必填；PK `(principal_id,request_id)`。

- **`provider_id`/`deployment_id`**：

  必填字符串；最终后端绑定。

- **`bound_at`**：

  必填时间；绑定时间。

- **跨字段与寿命**：

  PK `(principal_id,request_id)`；每 request 至多一个绑定；首次为准（`ON CONFLICT DO NOTHING`）；M003 写；与 UsageRecord 一致；按 retention policy。

- **合法/拒绝实例**：

  合法：一次调用绑定一个 deployment；边界：重复绑定被 PK 拒绝/忽略。

- **验证**：

  `T-MET-FINAL`。

**4.2.5 `D-MET-USAGE-VIEW` · UsageRecordView（业务与操作数据结构）**

```text
UsageRecordView {
  request_id: string, record_version: int, is_final: bool, model: string, endpoint: string,
  recorded_at: timestamp, updated_at: timestamp,
  measurement_status: MeasurementStatus, source: MeasurementSource,
  input_tokens: int?, output_tokens: int?, total_tokens: int?,
  cached_input_tokens: int?, cache_write_tokens: int?, reasoning_tokens: int?
}
```

- **Data/Type ID、用途与来源**：

  `D-MET-USAGE-VIEW`；`GET /v1/usage` 返回的单条版本视图；唯一来源 `usage.py` `_record()`。

- **`request_id`/`record_version`/`is_final`**：

  必填；版本标识。

- **`measurement_status`/`source`**：

  必填；字段与 `D-USAGE-RECORD` 一致。

- **token 字段**：

  可空整数；`unknown` 时 token 为 null 而非 0。

- **跨字段与寿命**：

  字段与 `D-USAGE-RECORD` 一致；`unknown` 时 token 为 null 而非 0；只读投影；请求级；不持久（来自冻结 snapshot）。

- **合法/拒绝实例**：

  合法 measured 视图；边界：unknown 视图 token=null。

- **验证**：

  `T-MET-PAGE`、`T-MET-UNKNOWN`。

**4.2.6 `D-MET-QUERY-SNAPSHOT` · QuerySnapshot / QuerySnapshotItem（业务与操作数据结构）**

```text
QuerySnapshot {
  snapshot_id: string, principal_id: string, resource: string,
  filter_digest: string, auth: string, created_at: timestamp, expires_at: timestamp
}
QuerySnapshotItem {
  snapshot_id: string, ordinal: int, request_id: string,
  record_version: int, frozen_view_json: object
}
```

- **Data/Type ID、用途与来源**：

  `D-MET-QUERY-SNAPSHOT`；分页冻结快照与其有序成员；唯一来源 `usage.py` `_page`。

- **`snapshot_id`**：

  必填字符串；快照主键。

- **`principal_id`/`resource`/`filter_digest`/`auth`**：

  必填；主体/资源/filter 摘要/授权摘要。

- **`created_at`/`expires_at`**：

  必填时间；`expires_at` = 创建 + 10 分钟。

- **`QuerySnapshotItem`**：

  `(snapshot_id, ordinal)`、`request_id`、`record_version`、`frozen_view_json`；有序成员。

- **跨字段与寿命**：

  `(recorded_at,request_id)` 稳定排序；`filter_digest` 绑定 filter；`expires_at` = 创建 + 10 分钟；旧页不受后续更正影响（INV-6 的口径）；持久、有期限（TTL 10 分钟）；M003 写、M003 读。

- **合法/拒绝实例**：

  合法首屏创建 snapshot；拒绝：过期/跨 principal/filter 不符的 cursor。

- **验证**：

  `T-MET-PAGE`。

### 4.3 配置与规则数据结构

**4.3.1 `D-MET-RETENTION-POLICY` · 账本保留与 snapshot TTL（配置与规则数据结构）**

```text
RetentionPolicy {
  snapshot_ttl_s: int,
  retention: string
}
```

- **Data/Type ID、用途与来源**：

  `D-MET-RETENTION-POLICY`；账本保留期与分页 snapshot TTL；唯一来源 `usage.py`（TTL 10 分钟）与运维保留策略（§13）。

- **`snapshot_ttl_s`**：

  必填整数，默认 600；分页 snapshot TTL（秒）。

- **`retention`**：

  必填字符串；operator 保留策略。

- **跨字段与寿命**：

  TTL 必须覆盖一次正常分页耗时；保留策略不改变“只追加/不补零”语义；配置项；operator 拥有；变更需审计。

- **合法/拒绝实例**：

  合法 600s；边界：过短 TTL → 分页中途 `cursor_expired`。

- **验证**：

  `T-MET-PAGE`。

### 4.4 通信报文结构

不适用：账本为 SQLite 行与进程内函数调用，无消息/事件/流 wire；`GET /v1/usage` 的 HTTP JSON 报文是 `D-MET-USAGE-VIEW` 的投影，机器权威在 `openapi`，不构成本机制拥有的独立通信报文结构。

### 4.5 设备与 FPGA 表项结构

不适用：LLMTier 为纯软件，无连接器、总线、寄存器或 FPGA 端口（tailoring `LT-TL-003`）。

### 4.6 运行状态数据结构

不适用：账本状态均在 SQLite 持久表（义务/版本/head/绑定/snapshot）；无独立内存跨步骤运行状态，进程退出以库内事实为准（§9）。

### 4.7 数据库表结构

**4.7.1 `usage_*` / `provider_request_bindings` / `query_snapshots*`（数据库表）**

```text
tables {
  usage_obligations { (principal_id, request_id) PK },
  usage_record_versions { (principal_id, request_id, record_version) PK },
  usage_heads { (principal_id, request_id) PK, head_record_version FK },
  provider_request_bindings { (principal_id, request_id) PK },
  query_snapshots { snapshot_id PK },
  query_snapshot_items { (snapshot_id, ordinal) PK }
}
```

- **Data/Type ID、用途与来源**：

  Authority = `util/migrations/*.sql`（M007 `migrate()` 执行）；列级阅读视图见 `util.isd` §4.4；本机制覆盖上列 6 张表。

- **`usage_obligations`**：

  主键 `(principal_id,request_id)`；与记录同寿。

- **`usage_record_versions`**：

  主键 `(principal_id,request_id,record_version)`；只追加。

- **`usage_heads`**：

  主键 `(principal_id,request_id)`；`head_record_version` 单调推进并 FK 指向存在的版本。

- **`provider_request_bindings`**：

  主键 `(principal_id,request_id)`；首次为准。

- **`query_snapshots` / `query_snapshot_items`**：

  `snapshot_id` / `(snapshot_id,ordinal)` 主键；TTL 10 分钟。

- **跨字段与寿命**：

  版本只追加、head 单调且指向存在版本；同 request 版本绝不累计；snapshot 冻结后新写入只对新 snapshot 可见。

- **合法/拒绝实例**：

  合法：一次成功调用产生 v1 unknown → v2 measured；拒绝：指向不存在版本的 head/重复版本。

- **验证**：

  `T-MET-FINAL`、`T-MET-PAGE`。

### 4.8 错误码与错误结构

**4.8.1 `D-MET-ERROR-MAP` · 用量错误映射（错误码与错误结构，引用系统 §8.8）**

```text
enum UsageErrorRef { ERR-STORE, ERR-CURSOR, ERR-REQ-VALIDATION, ERR-AUTH-DENIED, ERR-NOTFOUND }
```

- **Data/Type ID、用途与来源**：

  `D-MET-ERROR-MAP`；本机制对外错误的系统码引用，不新增公共错误码；唯一来源系统设计 §8.8（公共含义）与 `openapi`（产生）；载荷 `D-ERROR-ENVELOPE`。

- **`ERR-STORE`（503 `usage_store_unavailable`）**：

  读/写存储异常；本次失败、**不返回空页**；稍后重试/以权威查询核对。

- **`ERR-CURSOR`（400 `cursor_expired`）**：

  snapshot 超 TTL；未返回页、无副作用；从头重开查询。

- **`ERR-REQ-VALIDATION`（400 `invalid_request`）**：

  时间窗非法/filter 不符；未返回页、无副作用；修正 from/to/filter。

- **`ERR-AUTH-DENIED`（403 `permission_denied`）**：

  他人 cursor / 非 admin 清空；未执行、无副作用；用自身 cursor/换 admin。

- **`ERR-NOTFOUND`（404）**：

  未知资源；未受理；修正 ID。

- **跨字段与寿命**：

  写失败 → 不 dispatch；读失败 → 503，不用空页冒充无记录（C-METER-5）；载荷 `D-ERROR-ENVELOPE`；请求级返回，不持久。

- **合法/拒绝实例**：

  拒绝：读存储不可用 → 503（非空页）。

- **验证**：

  `T-MET-3`/503 用例、`T-MET-PAGE`。

### 4.9 编码、布局与共享类型映射

不适用二进制 ABI：SQLite 行 + JSON（`frozen_view_json`/`filter_digest` 输入，紧凑分隔符）。

| 类型 ID / 编码源基线 | 逻辑宽度/序列化长度 | 实际 ABI 定位或不适用理由 | 原类型 → 投影/转换/损失 | 验证项 |
|---|---|---|---|---|
| `D-USAGE-RECORD`（系统 §8.2） | 16 列行；token 可 NULL | `usage_record_versions` 行 | 后端 usage → 版本行；非 int ⇒ unknown/NULL | `T-MET-UNKNOWN` |
| `D-MET-USAGE-VIEW` | JSON 对象 | `frozen_view_json` TEXT | 行 → 视图；字段一一映射 | `T-MET-PAGE` |
| `D-MET-QUERY-SNAPSHOT` | `filter_digest` = SHA-256；`auth` = SHA-256 | `query_snapshots` 行 | filter → digest；不含明文凭据 | `T-MET-PAGE` |
| `D-ERROR-ENVELOPE`（系统 §8.4） | UTF-8 JSON | 无 wire offset | `ApiError.envelope()` | 503 用例 |

### 4.10 一致性、可见性与数据寿命

账本局部一致：同一 `(principal_id,request_id)` 的版本只追加，`head_record_version` 在单事务内单调推进，绝不累计（INV-1/2/3）；`recorded_at` 固定为首次记录时间，`updated_at` 随替换推进（INV-6），因此按 `(recorded_at,request_id)` 排序稳定可续。dispatch 前义务已持久，故崩溃/写入失败后重启仍见 unknown，绝不出现“没有调用”的假象（C-METER-3、INV-5）。查询首屏在单事务内冻结 `query_snapshots` + 有序成员；后续页按 `sid:offset` 读冻结视图，页间的更正/插入/删除只对**新** snapshot 可见。存储不可用返回 typed 503，不用空页冒充无记录。snapshot TTL 10 分钟覆盖一次正常分页；`DELETE /v1/usage` 为管理动作（+审计），一次性删除义务/版本/head/绑定，不可回滚；持久性对应 SQLite 单文件，进程退出以库内事实为准。

## 5. 接口设计

> 按 STD `design-data-interface-format` 1.2.0 §3：主章“接口设计”，按**接口用途**分类逐接口完整记录；标题为真实调用形式，标题下先给完整接口声明，再就地说明输入/输出，最后按六项写完。数据结构引用 §4；错误引用系统 §8.8。用量钩子由本机制拥有并在此唯一定义；M-INFER 只引用。分类：API = 向 Consumer/Operator 提供可调用能力（本机制为 `/v1/usage` HTTP 端点）；消息与数据流 = 责任单元之间为协作而交换的命令/状态/事实（含进程内函数）。

### 5.1 API（适用时）

#### `GET /v1/usage`；`DELETE /v1/usage`

```text
GET    /v1/usage?from=&to=&model=&request_id=&limit=&cursor= -> 200 {data,next_cursor,has_more,snapshot_id,snapshot_at}
DELETE /v1/usage?model=&deployment_id=                        -> 200 {deleted}
  -> 4xx/5xx: ErrorEnvelope
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-MET-API-USAGE`；Consumer 查询自身用量 / Operator 查询全部并按范围清空；M003 Usage Recorder 提供、M001 暴露；交接边界=用量查询与清空 HTTP；状态=Implemented；唯一契约=`openapi`；`src/http_api/app.py` → `app.usage.page/reset_usage`。
- **输入与前提**：GET 查询参数；DELETE 范围参数；授权=consumer/operator（`IF-TRUST-AUTH-ANY`，DELETE 需 admin）；校验=时间窗/cursor/filter。
- **成功输出与保证**：见上；GET 只读；DELETE 副作用=范围删除 + 审计。
- **错误与合法下一步**：同 `IF-MET-PAGE`/`IF-MET-RESET`；`ERR-STORE`（503 显式化，不用空页冒充）。
- **交互与生命周期**：同步；GET 幂等只读；DELETE 幂等且不可回滚。
- **实现与验证**：正常 GET 返回 v2（非 v1+v2）；拒绝非 admin DELETE → 403。`T-MET-PAGE`、`T-MET-RESET`；Run=NOT_RUN。

### 5.2 消息与数据流接口（适用时）

#### `UsageRecorder.authorize_dispatch(principal, request_id, model, endpoint) -> None`

```text
authorize_dispatch(principal: str, request_id: str, model: str, endpoint: str) -> None
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-MET-AUTHORIZE`；dispatch 前向账本登记一次调用义务（unknown 锚点）；Inference 编排消费、Usage Recorder 提供；交接边界=校验通过后、后端调用前；状态=Implemented；唯一契约=本设计；`src/inference/usage.py` `UsageRecorder.authorize_dispatch`。
- **输入与前提**：`principal`、`request_id`、`model`（等级）、`endpoint`；前置=请求已校验通过、**dispatch 之前**；授权=内部调用（已鉴权请求上下文）；校验=无（幂等登记）。
- **成功输出与保证**：无返回——受理/完成=`usage_obligations` + 首个 v1 `unknown/unavailable` 版本 + `usage_heads`，单事务提交；副作用=账本锚点持久。
- **错误与合法下一步**：事务失败 → 抛出（由调用方决定不 dispatch）；结果已知、无半写；**不产生公共错误载荷**（内部）。
- **交互与生命周期**：同步；可重入（`INSERT OR IGNORE`，已有 head 则 no-op）；请求级；不释放资源。
- **实现与验证**：正常 `authorize_dispatch("piko","req_1","Worker","/v1/responses")` → v1 义务；边界：重复调用 no-op。`T-MET-CRASH`；Run=NOT_RUN。

#### `UsageRecorder.bind_backend(principal, request_id, provider_id, deployment_id) -> None`

```text
bind_backend(principal: str, request_id: str, provider_id: str, deployment_id: str) -> None
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-MET-BIND`；把 request 绑定到最终 provider/deployment；Inference 编排消费、Usage Recorder 提供；交接边界=准入选出候选后；状态=Implemented；`src/inference/usage.py`。
- **输入与前提**：`principal`、`request_id`、`provider_id`、`deployment_id`；前置=准入已选候选；授权=内部。
- **成功输出与保证**：无返回——写 `provider_request_bindings`（首次为准，`ON CONFLICT DO NOTHING`）；副作用=绑定持久。
- **错误与合法下一步**：冲突被忽略（不抛）；事务失败由存储层异常表达。
- **交互与生命周期**：同步；幂等（首次为准）；请求级。
- **实现与验证**：正常绑定 `prov_local`/`dep_local_gemma`；边界：重复绑定保持首次。`T-MET-FINAL`；Run=NOT_RUN。

#### `UsageRecorder.finish(principal, request_id, usage, source_override=None) -> None`

```text
finish(principal: str, request_id: str, usage: dict | None, source_override: str | None = None) -> None
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-MET-FINISH`；追加终态用量版本并单调推进 head；Inference 编排消费、Usage Recorder 提供；交接边界=后端返回后 / 异常路径；状态=Implemented；`src/inference/usage.py`。
- **输入与前提**：`principal`、`request_id`、`usage: dict | None`（后端返回，三 token 皆 int 才判 measured）、可选 `source_override`（注入标注）；前置=义务存在。
- **成功输出与保证**：无返回——追加 v(n+1) 版本 + 单调推进 head，单事务提交；受理/完成=提交后账本事实；副作用=版本持久。
- **错误与合法下一步**：无义务 → no-op（不影响已返回结果）；写失败 → 由存储层异常表达，结果已返回不改判；结果已知性=保留 unknown 至后续版本或重启可见。
- **交互与生命周期**：同步；同 request 并发由单事务推进 head；不影响已返回的业务结果。
- **实现与验证**：正常 `finish(..., {input:2,output:1,total:3})` → head=2、measured；边界：usage 非 int → unknown + NULL。`T-MET-FINAL`、`T-MET-UNKNOWN`；Run=NOT_RUN。

#### `UsageRecorder.page(principal, cursor, limit=50, admin=False, since=None, until=None, model=None, request_id=None) -> dict`

```text
page(principal: str, cursor: str | None, limit: int = 50, admin: bool = False, since: str | None = None, until: str | None = None, model: str | None = None, request_id: str | None = None) -> dict
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-MET-PAGE`；以冻结 snapshot 提供稳定分页用量查询；Management Usage Reader 消费、Usage Recorder 提供；交接边界=用量查询 HTTP 端点；状态=Implemented；`src/inference/usage.py`。
- **输入与前提**：`principal`；`cursor`（`sid:offset`）；`limit`；`admin`（是否跨 principal）；`since`/`until`（`[from,to)`），`model`、`request_id`；授权=consumer（自身）/operator（全部）。
- **成功输出与保证**：`{data: D-MET-USAGE-VIEW[], next_cursor, has_more, snapshot_id, snapshot_at}`；受理=首屏创建 `D-MET-QUERY-SNAPSHOT`（§4.2.6）并冻结成员；生效=旧页不受后续更正影响；副作用=snapshot 行写入（TTL 10 分钟）。
- **错误与合法下一步**：`ERR-REQ-VALIDATION`（400 时间窗/`filter_digest` 不符）；`ERR-CURSOR`（400 过期）；`ERR-AUTH-DENIED`（403 他人 cursor）；`ERR-STORE`（503）；载荷 `D-ERROR-ENVELOPE`。
- **交互与生命周期**：同步只读；cursor 绑定 principal/授权/filter；按 `(recorded_at,request_id)` 稳定排序。
- **实现与验证**：正常首屏 + 后续页；拒绝他人 cursor → 403。`T-MET-PAGE`；Run=NOT_RUN。

#### `UsageRecorder.reset_usage(model=None, deployment_id=None, conn=None) -> dict`

```text
reset_usage(model: str | None = None, deployment_id: str | None = None, conn: Connection | None = None) -> dict
```

- **Interface/Member ID、用途、提供责任与唯一来源**：`IF-MET-RESET`；按范围删除义务+版本+head+绑定；Management Admin 消费、Usage Recorder 提供；交接边界=用量清空管理动作；状态=Implemented；`src/inference/usage.py`。
- **输入与前提**：`model`（等级）/`deployment_id`（或两者/均无）；授权=operator；校验=范围语义。
- **成功输出与保证**：`{deleted: int}`——按范围删除义务+版本+head+绑定，单事务；副作用=删除 + 审计（经 M001 `Admin.mutate`）。
- **错误与合法下一步**：非 admin → `ERR-AUTH-DENIED`（403）；`ERR-STORE`（503）；失败回滚。
- **交互与生命周期**：同步；幂等（重复清空 `deleted=0`）；不可回滚。
- **实现与验证**：正常按 model 清空返回计数；边界：无匹配 → `deleted=0`。`T-MET-RESET`；Run=NOT_RUN。

### 5.3 硬件与固件接口（适用时）

不适用：无连接器、总线、寄存器或 FPGA 端口。

### 5.4 人机与维护接口（适用时）

不适用：清空为 HTTP 管理操作（`IF-MET-API-USAGE`，§5.1）与账本函数（`IF-MET-RESET`，§5.2），其运维入口记录于 §12.2；本机制不另造 CLI/页面。

## 6. 正常端到端流程

![用量计量时序](../../assets/diagrams/diagram-mech-meter-sequence.png)

[可编辑 SVG 源](../../assets/diagrams/diagram-mech-meter-sequence.svg)

图 M · 用量计量时序（实线=请求，虚线=响应；先后关系非时间比例）。

1. **登记义务**：dispatch 前写 `usage_obligations` + v1 `unknown/unavailable`（C-METER-3）。
2. **绑定后端**：准入选定候选后写 `provider_request_bindings`。
3. **归一**：后端返回 → 判定 `measured`（三 token 皆 int）→ 追加 v(n+1) → 推进 head。
4. **查询（首屏）**：同一事务创建 `query_snapshots` + 固化有序成员 `(principal, request_id, record_version)`。
5. **查询（后续页）**：按 `sid:offset` 读冻结项；`(recorded_at, request_id)` 稳定排序。
6. **清空**：按 model/deployment/全部范围删义务+版本+head+绑定。

### 6.1 交叠请求、跨轮次与生命周期边界

一条记录 = 一个生命周期（义务→绑定→终态）。**交叠**：同 request 的并发 `finish` 由单事务推进 head（§10）；分页期间的新写入只对新 snapshot 可见（§4.10）；`finish` 与查询并发不互相阻塞（读快照）。

## 7. 分支和替代流程

| 分支 | 触发 | 处理 |
|---|---|---|
| 后端失败/无 usage | 返回值非 int 或缺失 | `unknown/unavailable`；**成功结果不改判为失败**，但保留 unknown 事实 |
| 存储不可用 | 写/读失败 | 写：不 dispatch；读：503（**不返回空页**）|
| cursor 过期 | snapshot 超 10 分钟 | 400 `cursor_expired` |
| cursor 跨 principal | 非 admin 用他人 cursor | 403 `permission_denied` |
| filter 不符 | cursor 的 filter_digest 不一致 | 400 `invalid_request` |
| 清空范围 | model / deployment / 全部 | 删除对应义务+版本+head+绑定 |

## 8. 状态机与不变量

| INV-ID | 可验证断言（量词、条件和预期必须明确） | Enforcement / 事实来源 | 反例输入/违反后的结果 | 验证项 |
|---|---|---|---|---|
| INV-1 | ∀ 记录：`usage_record_versions` 只追加，`(principal, request_id, record_version)` 唯一 | 单事务插入 + 主键 | 覆盖旧版本 → 不可复现的对账 | T-MET-FINAL |
| INV-2 | ∀ 记录：`head_record_version` 单调不减，且 = 当前最高版本 | `finish` 单事务 `UPDATE` | head 回退 → 读到旧事实 | T-MET-FINAL |
| INV-3 | ∀ 读取：同 request 只取 head 指向的单条版本，**不累加** | `page` join head | 版本相加 → 重复计量 | T-MET-FINAL |
| INV-4 | ∀ 记录：`is_final=true` 后不得降级或改小版本 | 版本只增 | 终态被改 → 对账漂移 | T-MET-CRASH |
| INV-5 | ∀ 未测记录：`measurement_status=unknown` 时 token 字段为 NULL（**≠ 0**）| 归一判定（§4.1）| 未测填 0 → 误报"没有调用" | T-MET-UNKNOWN |
| INV-6 | ∀ 记录：`recorded_at` 跨版本不变，`updated_at` 随版本推进 | `finish` 保留 `recorded_at` | 时间漂移 → 排序错乱 | T-MET-PAGE |

### 8.1 资源预留、交付、释放与复位

**预留 = unknown 义务**（dispatch 前落库，崩溃后仍存在）；**交付 = 终态版本 + head**；**复位 = `DELETE /v1/usage`**（管理动作 + 审计）。无租约、TTL 只作用于查询 snapshot。

## 9. 失败传播、重试与恢复

| Failure ID / 检测方 | 失败点与传播 | 结果已知性 | 已发生/可能副作用 | 访问安全/证据 | 操作终态 | 资源释放 | 重新准入/重试条件 |
|---|---|---|---|---|---|---|---|
| F-MET-1 / Usage Recorder | 义务写入失败 | 已知失败 | 无 | 无 | **不 dispatch** | 无预留 | 请求失败；修正后重试 |
| F-MET-2 / Usage Recorder | terminal 后 `finish` 写入失败 | 结果已返回 | 已返回结果不改判 | 义务证据在库 | head 停留 | 无 | 保留 unknown，重启可见 |
| F-MET-3 / Store | 查询存储不可用 | 已知失败 | 无 | 无 | 503 | 无 | 稍后重试 |
| F-MET-4 / 崩溃 | 义务在、终态缺 | **未知** | 无 | 义务即证据 | 重启后仍为 unknown | 无 | 不回填为 0 |

**恢复边界**：重启以 SQLite 事实为准；**不得**把"已发生但计量缺失"误报为"没有调用"。

## 10. 并发、排序与容量

| 作用域 | 约束 | 上限/行为 |
|---|---|---|
| 同 request 写 | 单事务推进 head | 无竞争丢失 |
| 分页 | snapshot 冻结 + cursor | TTL 10 分钟（覆盖一次正常分页）|
| 排序 | `(recorded_at, request_id)` | 稳定、可续 |
| 清空 | 单事务 | 与查询互不阻塞（快照读）|

## 11. 安全、权限与信任边界

| 资产 | 身份 | 强制点 | 拒绝 | 审计 |
|---|---|---|---|---|
| 自身用量 | consumer 凭据 | `page(admin=False)` 过滤 principal | 403（他人 cursor）| — |
| 全部用量 | operator 凭据 | `page(admin=True)` | 401/403 | — |
| 清空 | operator | `DELETE /v1/usage` | 403 | 审计 |

边界：consumer 只见自身；不记录 Cost/金额；用量不含 Secret/prompt 正文。

## 12. 可观测性与证据

### 12.1 统计、日志、时间与关联

用量事实即**对账证据**；与 M-OBS 的数据面统计**不同**（后者是观测、可丢，前者是账本、不可补零）。时间统一 UTC ISO8601（毫秒、`Z`）。

### 12.2 维护命令、自检与调试路径

| Maintenance API / Command / Diagnostic ID | 执行位置、入口、目标、权限 | 完整请求/语法与结果/错误契约 | 施加/回读点及覆盖 | 依赖/占用/恢复退出 | 验证 |
|---|---|---|---|---|---|
| 查用量 `GET /v1/usage` | LLMTier 管理面；consumer/operator | 参数 = `from,to,model,request_id,limit,cursor`；结果 = 分页视图；错误 400/403/503 | 只读查询 | 无 | T-MET-PAGE |
| 清空 `DELETE /v1/usage` | LLMTier 管理面；operator | 参数 = `model,deployment_id`；结果 = `{deleted}`；错误 403/503 | 施加=范围删除；回读=计数 | 单事务；不可回滚 | T-MET-RESET |
| 孤儿清理 `reset_usage`（管理动作）| 同上 | 一并清 obligations/bindings | 施加=范围 | 依赖 `util` 事务 | T-MET-RESET |

## 13. 配置、兼容与部署

存储为 SQLite 单文件（`util` 唯一持久化）；snapshot TTL（10 分钟）为配置项，须覆盖一次正常分页耗时。清空为管理动作，变更需审计。保留期策略按运维配置。

## 14. 跨责任单元分解与接口分配（下级设计输入）

本章是**要求侧**：把本机制分解到各责任单元（LLMTier 为纯软件，责任单元 = 软件模块），说明每个对象必须负责什么、提供什么接口。下级模块设计在附录"机制承接表"逐条记录**落实侧**。

### 14.1 参与方到架构对象映射

| 机制参与方（§3） | 责任单元/Owner | 架构对象 ID / 类型 / 层或领域 | 下级设计文档 | 在本机制中的主责与非职责 |
|---|---|---|---|---|
| 计量写入 | Inference / LLMTier | Usage Recorder（业务层）| `inference-design.md` | 义务/绑定/终态、unknown；不含 Cost |
| 查询/清空 | Management / LLMTier | Usage Reader、Admin（业务层）| `management-design.md` | 分页、清空、授权；不承载推理 |
| 入口 | HTTP API / LLMTier | HTTP Adapter（入口层）| `http-api-design.md` | `/v1/usage` 路由、错误映射；不含业务规则 |
| 存储 | LLMTier | Store（基础层）| `util-design.md` | 事务、快照表 |

### 14.2 功能和步骤到责任单元分配

| Capability / Process Step / Constraint | 主责架构对象 | 协作对象 | 必须产生或消费的结果 | 固定行为 / 本地自由度 | 组合验证责任 |
|---|---|---|---|---|---|
| Step 1 登记义务（C-METER-3）| Usage Recorder | — | v1 unknown | 未测不补零固定；存储可自定 | 系统用例 |
| Step 2 绑定后端 | Usage Recorder | Internal Admission（触发）| binding | 首次为准固定 | 系统用例 |
| Step 3 归一与推进 head（C-METER-1）| Usage Recorder | — | 终态版本 + head | head 单调固定；归一实现可自定 | 系统用例 |
| Step 4 查询首屏（C-METER-4）| Usage Reader | Store | snapshot + 冻结项 | 排序 `(recorded_at,request_id)` 固定 | T-MET-PAGE |
| Step 5 后续页 | Usage Reader | Store | 冻结视图 | cursor 实现可自定 | T-MET-PAGE |
| Step 6 清空 | Admin | Store、Audit Writer | `{deleted}` + 审计 | 范围语义固定 | T-MET-RESET |

### 14.3 责任单元间接口契约

> 本节为**分配视图**：只把 §14.1 的责任单元映射到 §5 已定义的接口成员 ID 与 §4 结构 ID；完整签名、字段、编码和错误码由 §5 与系统 §8.8 唯一维护，本节不复制。

| 责任单元（§14.1） | 承接的成员/结构 ID（§4/§5） | 角色 | 本机制固定的语义与边界（引用） |
|---|---|---|---|
| Usage Recorder（计量写入） | `IF-MET-AUTHORIZE`、`IF-MET-BIND`、`IF-MET-FINISH`；`D-USAGE-OBLIGATION`/`D-USAGE-RECORD`/`D-USAGE-HEAD`（§4.2） | 提供 | 义务→绑定→终态；只追加、head 单调、unknown 不补零（§5.2） |
| Usage Reader / Admin（查询/清空） | `IF-MET-PAGE`、`IF-MET-RESET`；`D-MET-QUERY-SNAPSHOT`（§4.2） | 提供 | snapshot 冻结分页、范围清空、授权每页复核（§5.1/§5.2） |
| HTTP Adapter（入口） | `IF-MET-API-USAGE` | 提供/映射 | `/v1/usage` 路由与错误映射（400/403/503）；不含业务规则 |
| Inference 编排 | `IF-MET-AUTHORIZE`/`IF-MET-BIND`/`IF-MET-FINISH` | 消费 | 在 dispatch 前后调用钩子；unknown 语义（§9） |
| Store（存储） | 各账本/snapshot 表（§4.7） | 提供 | 单事务原子提交、快照表 |

### 14.4 下级设计输入清单

| 下级要求 ID | 承接对象 ID / 下级设计文档 | 来源 Capability / Step / Constraint / 接口成员 | 必须负责的行为与保证 | 必须提供/消费的接口 | 下级必须展开的问题 | 允许自行决定的范围 | 本地验证 / 组合验证交接 |
|---|---|---|---|---|---|---|---|
| R-MET-01 | Usage Recorder · `inference-design.md` | C-METER-1/2/3、Step 1/2/3/9、interface `authorize_dispatch/bind_backend/finish` | 只追加版本、head 单调、unknown 不补零 | `authorize_dispatch`/`bind_backend`/`finish` | 事务边界、并发写、归一 | 存储实现 | 系统用例 |
| R-MET-02 | Usage Reader · `management-design.md` | C-METER-4、Step 4/5、interface `page` | snapshot 冻结分页、权限每页复核 | `page()` | cursor 结构、TTL、排序 | 分页实现 | T-MET-PAGE |
| R-MET-03 | Admin · `management-design.md` | CAP-METER-RESET、Step 6、interface `reset_usage` | 范围清空 + 审计 | `reset_usage()` | 范围语义、孤儿清理 | 范围实现 | T-MET-RESET |
| R-MET-04 | HTTP Adapter · `http-api-design.md` | C-METER-5、`/v1/usage` | 路由与错误映射 | 路由 | 503 显式化 | 映射实现 | 503 用例 |

**约束**：下游不得改变"只追加/不补零"语义；新增查询维度须回写本节并关联模块设计。

## 15. 验证、上线与回滚

### 15.1 输入构造、故障控制与独立判据

| Test / Constraint | 输入与预置事实 | arm/hit/release | 独立 Oracle |
|---|---|---|---|
| T-MET-FINAL / C-METER-1..2 | 一次成功调用 | — | head=2、v2 measured、token 相等 |
| T-MET-CRASH / C-METER-3 | 断开故障注入 | — | 崩溃后存在 unknown 义务 |
| T-MET-UNKNOWN / C-METER-2 | 后端无 usage | — | `unknown` 且 token 为 NULL（非 0）|
| T-MET-PAGE / C-METER-4 | 首屏后更正记录 | — | 旧页返回冻结版本 |
| T-MET-RESET / CAP-METER-RESET | 按 model/deployment | — | `{deleted}` 与范围一致 |

### 15.2 环境部署、复位、并发隔离与自动化

本机实例 + 隔离数据库；复位 = 重建库 + 重启；并发用例核验 head 单调与查询隔离。

### 15.3 组合验收、启用与旧机制退出

见 `LT-ADR-03`（unknown 不补零）。组合验收 = Consumer 查自身 + Operator 清空联调。

## 16. 风险、未决问题与决定

| ID | 类别 | 影响 | 下一步 | 状态 |
|---|---|---|---|---|
| LT-ADR-03 | 决定 | 未知不补零；以义务保证崩溃可见 | 已采用 | 已定 |
| RISK-METER-1 | 风险 | 写放大（每请求多行）| 由单事务与保留策略约束 | 观察 |

## A. 输入基线、适用性与图文规则

- 输入：系统设计 §3.4/§8、`LT-ADR-03`、`usage.py`、`store.py`。
- 适用性：纯软件、单节点 SQLite 账本机制。§4.9（二进制 ABI）不适用；§8.1 的"预留/释放"映射为义务/清空（无租约）。
- 图：时序图（§6）表达义务→绑定→终态与冻结分页。

## B. 文档控制与修订记录

初版 `0.1.0-draft.1`；`draft.3` 补实全部章节、增模块分解与不变量。修订见 Git。
