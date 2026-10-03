<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-LOG-002 — 脱敏五模式 × 位置

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-LOG-002` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-10-02` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.module-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/module/cases/MT-LOG-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-LOG-002`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-LOG-002.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-LOG-002` / M008 脱敏分支：五种敏感模式命中 + 未命中（组装） v0.1.0-draft.1 / VRC-LOG-001（log-design §14 / log.isd §9.1，log 0.1.0-draft.1） / VRC-LOG-001 / security / P0（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：鉴权/脱敏/注入边界冒烟 + 契约 + 分支×端点配对（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M008-脱敏五模式；组合：K10
- 要测什么（责任展开）：Bearer/api_key/token/authorization/secret 命中→`[REDACTED]`；普通文本不误伤；长度 ≤512（本 Case 责任：Bearer/token/api_key/authorization/secret 五模式命中与普通文本不误伤）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝log 组装后脱敏模式与误伤边界与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/log/logs.py::_SENSITIVE`（经 `record`→`page` 观测）

```text
record(...); page(since, until) -> rows[].message
```

- 初态构造（经公开入口）：`AppFixture` 真实组装（ENV-1）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 组装隔离库
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture`（`FakeAdapter`/`AppFixture` 组装契约，见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：K10 五行：`Bearer abc123 trailing`（行首）、`prefix token=abc123 suffix`（行中）、`prefix api_key:XYZ999`（行尾）、`Authorization: Bearer q-token-1`（键值）、`token bucket limiter and keyboard`（不误伤）；另测 `secret=`/`access_key_id=`/`API_KEY=`
- 边界/非法取值及理由：命中条件为「键 + 分隔符 + 值」或 `bearer\s+\S+`；裸词（无 `:`/`=`）不命中；大小写不敏感
- 规模 / 时间域（数量、分页、复杂度、观测开销）：7 组消息；单连接；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 逐条 `record` 五种模式 | 每条读回均含 `[REDACTED]` 且原值消失 |
| 2 | `record` 裸词普通文本 | 原文逐字保留（无误伤） |
| 3 | `record` 大写 `API_KEY=upper` | 命中（大小写不敏感） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：log 模块设计 §14.1 + 方案 §6.3 K10；按 `_SENSITIVE` 正则逐条人工推导命中/不命中
- 互斥预期（成功 / 各错误分支）：五种模式命中并替换为 `[REDACTED]`；裸词文本不误伤

## 6. 错误路径、副作用与清理

- 错误出口与表现：无错误出口（非正则命中路径）
- 副作用断言与清理：只改写 message 列；其余列不变

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-LOG-002.py`（7 个）：`test_bearer_at_start`、`test_token_mid_line`、`test_api_key_at_end`、`test_authorization_header_style`、`test_secret_and_access_key`、`test_plain_text_not_redacted`、`test_case_insensitive_hit`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-LOG-002.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
