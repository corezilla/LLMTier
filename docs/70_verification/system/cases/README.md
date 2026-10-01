# LLMTier 系统测试 Case 详细设计文档目录

本目录承载 LLMTier 的**系统层逐 Case 详细设计文档**（case design，STD `tests.system-case`）。它是文档链的中间层：

```
系统测试方案（../llmtier-system-test-scheme.md：分类体系 + §3 Case 清单唯一登记）
        ↓
case 设计（本目录：一 Case 一文档，承载入口/前置/输入/执行/Oracle/判定/清理/自动化位置）
        ↓
case 脚本（tests/system/api_test_v03/at_*.py 等可执行断言；UI 类在 tests/ui/）
```

阶段/用例/计划/资产的域级落位见 [`../../README.md`](../../README.md)。

## 命名规则（固定，所有 Case 一律遵循）

- 目录：`docs/70_verification/system/cases/`
- 文件名：`<lowercased-case-id>.md`，即 **Case ID 全小写**，后缀 `.md`；每份文档配一份 `<lowercased-case-id>.metadata.json`（STD `document-metadata` schema）。
- **Case ID 格式为 `ST-<对象>-<NNN>`**（STD `software-object-identifiers.md` §2：阶段前缀 `ST`；`<对象>`＝被测对象 token；`<NNN>` 三位十进制）。对象 token 与旧→新映射见 `docs/98_migration/llmtier-case-id-migration.md`。
- 示例：
  - `ST-RESP-001` → `cases/st-resp-001.md` + `cases/st-resp-001.metadata.json`
  - `ST-SL-012` → `cases/st-sl-012.md`
  - `ST-OBSDEPL-004` → `cases/st-obsdepl-004.md`
- **一 Case 一文件**，文件名与 Case ID 唯一对应；Case ID 以系统测试方案 §3 权威清单为准，本目录不得引入清单外的 ID。
- **Document ID＝Case ID**，写入 metadata；设计状态在方案清单，实现状态在本文档 §7，执行状态与 Verdict 只在 Run 报告。

## 模板契约（STD `tests.system-case` 固定章节）

每份 case 文档**必须齐备且按固定顺序**使用以下章节：

1. `## 1. Case 概述与责任`——Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）；**测试方法（§1.5 方法表行）声明**；要测什么；明确不测什么 / 失败含义。
2. `## 2. 被测入口与前置`
3. `## 3. 输入构造`
4. `## 4. 执行步骤与观察点`
5. `## 5. 独立 Oracle 与预期结果`——判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写。
6. `## 6. 错误路径、副作用与清理`
7. `## 7. 自动化位置与状态`

**测试方法声明（强制契约条款）**：§1 的固定章节内**必须**含一条方法声明行，且**只作为 §1 的列表项，不新增章节**：

- 系统层 case：`- **测试方法（§1.5 方法表行）**：<technique(s)>`，`<technique(s)>` 须**指名**系统测试方案 [§1.5 测试方法与测试设计技术](../llmtier-system-test-scheme.md#15-测试方法与测试设计技术) 家族表的**确切行/技术组合**（`等价类划分`/`边界值抽样`/`契约字段比对`/`错误猜测`/`反例驱动（ERR-*）`/`状态机驱动`/`固定并发度/种子`/`故障注入`/`有界重试`/`复位阶梯`/`鉴权·授权·脱敏冒烟`/`角色隔离`/`单 Case 基线采样`）。UI 类 case（`ST-UI-*`）沿用 §1.5「UI 类测试方法（按行为模式）」表的模式标签（`- **UI 方法模式（§1.5 方法表行）**：…`），并同时满足 §1.5 的「UI Case 约束」（六要素映射）。
- 单元层 case：`- **测试方法（§1.5 方法表行）**：<technique(s)>`，`<technique(s)>` 须指名单元测试方案 [§1.5 测试方法与测试设计技术](../../unit/llmtier-unit-test-scheme.md#15-测试方法与测试设计技术) 家族表的**确切行/技术组合**（`等价类划分`/`边界值`/`错误猜测 + 反例驱动`/`线程对偶 + 受控时序`/`故障注入 + 异常路径恢复`/`鉴权·脱敏·注入边界冒烟`）。
- **诚实性**：技术须由该 case 的**实际分类 + 步骤/断言**推导；跨两类技术时并列（如 412/ETag case＝`状态机驱动 + 契约字段比对`；`fault_502`/流中断＝`故障注入`；role-403＝`鉴权/角色隔离冒烟`；边界值 case＝`边界值抽样`）。**禁止**不读步骤直接按分类照抄。

case 文档**引用**系统测试方案 §3（Case 清单）与系统测试计划（§3 执行前检、§5 环境操作、§6 证据与 Run、§7 报告产出与 Gate 规则），不重复其定义。样例见 [`st-resp-001.md`](./st-resp-001.md)（系统层）与 [`../../unit/cases/unit-case-UT-API-005.md`](../../unit/cases/unit-case-UT-API-005.md)（单元层）。

## 状态语义（三层分离）

| 状态 | 取值 | 唯一权威记录处 |
|---|---|---|
| Case 设计状态 | `Designed` / `Gap` / `Tailored-N/A` | 系统测试方案 §3 清单 |
| 测试代码实现状态 | `Planned` / `Implemented` | 本目录 case 文档 §7 |
| 执行状态 / Verdict | `NOT_RUN`/`BLOCKED`/`INVALID`；`PASS`/`FAIL` | Run 报告（`tests/system/reports/`） |

## 与报告分离

设计写在本目录；Run 证据写在 `tests/system/reports/<run-id>/`，两者不混写。
