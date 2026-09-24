# HANDOFF：STD《软件实现规格设计（ISD）》模板修改意见

- 日期：2026-09-23
- 提出方：LLMTier（`corezilla/LLMTier`，branch `docs/std-draft21-upgrade`）
- 接收方：STD 维护方（`/Users/ben/work/STD`）
- 触发：按 `design.implementation` 0.2.1 编写 **M007 util 的首个独立 ISD**（`docs/50_implementation_design/util.isd.md`），并经 Piko / Codex / "coder 视角"三轮评审
- 证据：`docs/50_implementation_design/util.isd.md`（+ `.metadata.json`）；模块设计 `docs/40_module_design/util-design.md`；`docs/99-reference/LT-OBS-Integration-Review.md`

## 0. 一句话任务

`design.implementation` 0.2.1 的**章节骨架与固定字段**对"状态型/持久化软件模块"支持不足——缺少**schema 演进拒绝语义、错误传播矩阵、函数并发契约、本地持久化安全**等必填语义，且继承了 C++/嵌入式示例口径。请按下文 **P0/P1** 修改模板（并以 `util.isd.md` 作第二示例）。

## 1. 背景与基线

- 该 ISD 是 LLMTier「模块设计**不兼作** ISD」后的首个独立稿（`mode=separate`），模块 M007 util（`store.py` + `migrations/*.sql`，SQLite 持久化）。
- 评审发现：模板可以承载"函数级实现规格"，但对**持久化/状态类**关键语义**不是必填**，编码者需自行裁决——这正是 ISD 要消除的。
- **设计先行原则**：设计期无代码，ISD 只讲"最终要实现成怎样"；**不**描述现有实现，**不**做 Current↔Target 差异（仅修改他人既有代码时才需要）。

## 2. 建议清单

### P0 — 必填语义缺失

| # | 位置 | 问题 | 建议 |
|---|---|---|---|
| **T1 schema 演进与拒绝语义** | §7 持久化 | 现模板的 persistence 表不足以迫使作者写清 **migration 策略、拒绝/接受条件、源/目标版本、崩溃恢复、旧程序兼容**；LLMTier 的 schema 演进策略在模板里属"按需增补"，易漏 | 增设**必填子节 §7.x「schema 演进与拒绝语义」**：①「策略决定」段**必须列出首版不接受的迁移模式**（无增量升级 / 无 downgrade / 无自动修复）；②固定 **5 列表**：`原规则 \| 升级/降级策略 \| 接受/拒绝条件 \| 源/目标版本与转换函数 \| 拒绝后如何处理` |
| **T1b 库状态分支** | §7.x | 未要求列**数据库各状态** → 编码者不知失败后能否重跑 | 追加固定表：`库状态(空库/版本匹配/版本不匹配/无版本表旧库/部分初始化/完整性失败) \| 判定事实 \| 启动结果 \| 是否允许重跑` |
| **T2 错误传播矩阵** | §5/§7 | 模板只在函数行的一个单元格写"错误冒泡"，无"底层异常→模块→宿主/public error→日志→retry" | 增设**必填「错误传播矩阵」**：`异常/场景 \| 模块是否处理 \| payload/状态码 \| 日志级别 \| 是否可重试`；并要求明确 **typed 异常 vs 原生异常** 的所有权（谁抛、谁映射） |
| **T3 函数并发契约字段** | §5 | 函数表无并发维度 → 易出现未经验证的"读事务可重入"这类结论 | 函数规格增**固定字段**：`thread-safe / reentrant / nested-call policy / transaction participation / blocking·timeout` |
| **T4 本地持久化安全子项** | §7 安全 | 模板安全表偏"鉴权/日志"，缺**文件/目录权限、symlink、umask、备份、敏感数据、删除、磁盘耗尽** | 安全子节增**本地持久化安全**固定项；并要求"**可执行**"（检查对象、时点、判定、出口） |

### P0 — Current/Target 与状态（与"设计先行"的一致性）

| # | 位置 | 问题 | 建议 |
|---|---|---|---|
| **T5 §2 条件化** | §2「当前实现与目标差异」 | 模板把该章设为**必填**；但**设计期无代码**，greenfield 项目无从填，且诱发"抄现有实现" | 把 §2 改为**条件章节**：仅 **brownfield**（存在既有代码、且声明 baseline commit）时必填；greenfield 标 `not_applicable`（给 tailoring 依据）。若保留必填，则须把它纳入 machine coverage（`isd-current-target`），否则作者可整章漏写而检查器不报 |
| **T6 状态一致性** | §9/§10/§5/§8 | `Current/Target`、映射表、实现任务、Verification 四处的 `Implemented/Planned/NOT_RUN/PASS` 无交叉检查 → 常出现"代码已存在 / 映射 Planned / 文档 NOT_RUN"互相矛盾（本例即被 Codex 指出） | 增加**状态一致性**要求（自动或人工）：同一对象在四处状态必须可解释一致；并**明确设计期以 `Planned`/`NOT_RUN` 为合法**（不因"代码存在"判不一致） |

### P1 — 可读性与示例

| # | 位置 | 问题 | 建议 |
|---|---|---|---|
| **T7 宽表 → 固定字段段落** | 全文 | 模板大量 5–9 列宽表（§1 承接 6 列、§2 6 列、§5 5 列、§7 5/6/7 列、§9 7 列、§10 6/9 列），Markdown 中不可读 | 沿用 `design.definition` 2.4.0 的通用规则：**记录型 → 固定字段段落；矩阵型（≤3–4 列）保留表**。`util.isd.md` 已示范（承接矩阵 §1.1–1.6、§3/§4/§5 均段落式；仅保留规范强制的 §1 承接矩阵/§7 持久化·安全/§9 验证列数） |
| **T8 §7 三表混排** | §7 | 并发/持久化/安全三张 5–7 列表挤一节 | 拆为 `§7.1 并发/失败`、`§7.2 持久化与 schema 演进`、`§7.3 安全（含本地持久化）` |
| **T9 纯软件裁剪** | §4 | 模板要求 字节/位宽/ABI/`sizeof`/端序/对齐，对纯软件（Python/JSON、HTTP 服务）大量 N/A | 增**纯软件裁剪指引**（N/A + 依据），并给纯软件示例 |
| **T10 持久化服务示例** | 示例 | 唯一示例 FrameDecoder 是**同步、无状态、C++/ABI** 语境，不示范 SQLite/迁移/线程连接/崩溃恢复/schema 演进 | 增补**持久化服务示例**（`util.isd.md` 可作范例）：SQLite、迁移、线程内连接、拒绝启动、schema 演进、错误矩阵 |

### P1 — metadata 与命名

| # | 位置 | 问题 | 建议 |
|---|---|---|---|
| **T11 metadata 必填项未在模板呈现** | 封面/尾部 | `isd-standard` §2.1 要求 `design_object_id` + `implementation_specification{mode/document_id/coverage_mapping/reason/decision_ref}` + 10 项 coverage 锚点（`isd-<item>`），模板未提示 | 模板尾部列出必填 metadata 与 10 项锚点清单（`scope/structure/data/functions/algorithms/lifecycle/resources/security/persistence/verification`）|
| **T12 命名/落位** | §1/§2 | 独立 ISD 的文件名/落位建议已给，但模板未回显 | 模板注明默认 `docs/50_implementation_design/<name>.isd.md`（或项目已批准路径）|

## 3. 以 `util.isd.md` 为例的对照（可作为模板修订的验收样本）

| 模板建议 | util.isd.md 中的落点 |
|---|---|
| T1/T1b schema 演进 + 库状态分支 | §6.2（策略决定 + 5 列表 + 状态分支表）|
| T2 错误传播矩阵 | §6.4（异常→模块→HTTP→日志→重试）+ §6.1 错误契约 |
| T3 函数并发契约 | §4 每函数 `不可改变 / 可自行决定`；§6 并发模型/嵌套契约 |
| T4 本地持久化安全 | §6.3（symlink 拒绝、world-writable 告警、检查对象/时点/出口）|
| T5 §2 条件化 | 本文档**无 §2**（前瞻设计；标注为条件章节的实证）|
| T7 宽表→段落 | §1.1–1.6 承接矩阵、§3/§4/§5 段落式；保留 §9 验证 8 列表 |
| T9 纯软件裁剪 | §3（明确无 ABI/位宽/对齐/端序 + 依据）|
| T10 持久化示例 | 整份文档即"持久化服务 ISD"样本 |

## 4. 验收 Gate

1. **G1**：§7 含必填「schema 演进与拒绝语义」（策略决定列出不接受的迁移模式 + 5 列表 + 库状态分支表）。
2. **G2**：含必填「错误传播矩阵」与「函数并发契约字段」。
3. **G3**：§2 为条件章节（greenfield 可 `not_applicable`），或已纳入 machine coverage。
4. **G4**：安全子节含可执行的本地持久化安全项。
5. **G5**：模板给纯软件裁剪指引与持久化服务示例；metadata 必填项在模板可见。
6. **G6**：`util.isd.md` 可直接套用修订后的模板（作为第二官方示例）。

## 5. 证据与环境

| 项 | 值 |
|---|---|
| ISD 样本 | `docs/50_implementation_design/util.isd.md`（+ `.metadata.json`，`mode=separate`）|
| 模块设计 | `docs/40_module_design/util-design.md` |
| 模板 | `/Users/ben/work/STD/templates/design/implementation-design.md`（0.2.1）|
| 规范 | `/Users/ben/work/STD/docs/isd-standard.md` |
| 评审输入 | `docs/99-reference/LT-OBS-Integration-Review.md`（Codex 7 条 + #5 + coder 视角）|
