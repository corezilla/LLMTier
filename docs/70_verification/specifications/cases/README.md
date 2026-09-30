# LLMTier Case 详细设计文档目录

本目录承载 LLMTier 的**逐 Case 详细设计文档**（case design，STD `tests.system-case`）。它是文档链的中间层：

```
系统测试方案（llmtier-system-test-scheme.md：分类体系 + §3 Case 清单唯一登记）
        ↓
case 设计（本目录：一 Case 一文档，承载入口/前置/输入/执行/Oracle/判定/清理/自动化位置）
        ↓
case 脚本（tests/system/api_test_v03/at_*.py 等可执行断言）
```

## 命名规则（固定，所有 Case 一律遵循）

- 目录：`docs/70_verification/specifications/cases/`
- 文件名：`cases/<lowercased-case-id>.md`，即 **Case ID 全小写**，后缀 `.md`；每份文档配一份 `<lowercased-case-id>.metadata.json`（STD `document-metadata` schema）。
- 示例：
  - `DP-RESP-01` → `cases/dp-resp-01.md` + `cases/dp-resp-01.metadata.json`
  - `ADM-SL-02b` → `cases/adm-sl-02b.md`
  - `OBS-DEPL-04` → `cases/obs-depl-04.md`
- **一 Case 一文件**，文件名与 Case ID 唯一对应；Case ID 以系统测试方案 §3 权威清单为准，本目录不得引入清单外的 ID。
- **Document ID＝Case ID**（小写），写入 metadata；设计状态在方案清单，实现状态在本文档 §7，执行状态与 Verdict 只在 Run 报告。

## 模板契约（STD `tests.system-case` 固定章节）

每份 case 文档**必须齐备且按固定顺序**使用以下章节：

1. `## 1. Case 概述与责任`——Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）；要测什么；明确不测什么 / 失败含义。
2. `## 2. 被测入口与前置`
3. `## 3. 输入构造`
4. `## 4. 执行步骤与观察点`
5. `## 5. 独立 Oracle 与预期结果`——判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写。
6. `## 6. 错误路径、副作用与清理`
7. `## 7. 自动化位置与状态`

case 文档**引用**系统测试方案 §3（Case 清单）与系统测试计划（§3 执行前检、§5 环境操作、§6 证据与 Run、§7 报告产出与 Gate 规则），不重复其定义。样例见 [`dp-resp-01.md`](./dp-resp-01.md)。

## 状态语义（三层分离）

| 状态 | 取值 | 唯一权威记录处 |
|---|---|---|
| Case 设计状态 | `Designed` / `Gap` / `Tailored-N/A` | 系统测试方案 §3 清单 |
| 测试代码实现状态 | `Planned` / `Implemented` | 本目录 case 文档 §7 |
| 执行状态 / Verdict | `NOT_RUN`/`BLOCKED`/`INVALID`；`PASS`/`FAIL` | Run 报告（`tests/system/reports/`） |

## 与报告分离

设计写在本目录；Run 证据写在 `tests/system/reports/<date>/`，两者不混写。
