<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-LOG-001 — 日志脱敏与查询

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-LOG-001` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-10-01` |
| Template ID | `tests.unit-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/unit/cases/UT-LOG-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-LOG-001`）；责任摘要、分类与优先级以 [单元测试方案 §3](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [log-design.md](../../../40_module_design/log-design.md) §14 / ISD [log.isd.md](../../../50_implementation_design/log.isd.md) §9.1，设计验证项 `VRC-LOG-001`（固定版本 `log 0.1.0-draft.1`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `LOG`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-LOG-001` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-LOG-001` / `VRC-LOG-001`（log 模块设计 §14 / log-isd §9.1，log 0.1.0-draft.1） / `VRC-LOG-001` / security / P0（[方案清单 §3](../llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（脱敏/长度/排序/夹取）
- 要测什么（责任展开）：被测：`OperationalLog.record/page` 脱敏（`Authorization` 键名；`Bearer …`；`api_key`/`apikey`/`secret`/`access_key[_id]`/`token` 后跟 `[:=]` 的**键名与值整段** → `[REDACTED]`，`RISK-LOG-1` 已关闭）、换行折叠、长度 ≤512、倒序、按 level/module 过滤、`limit` 夹到 200。
- 明确不测什么 / 失败含义：不测：真实日志文件轮转（运维）；不测跨模块事件语义。失败含义＝脱敏漏网或查询实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/log/logs.py::OperationalLog.record/page`

```text
OperationalLog.record(level, module, event, message, request_id=None); OperationalLog.page(limit=..., level=..., module=...)
```

- 初态构造（经公开入口）：`AppFixture`（隔离库）
- Fixture / 向量及版本：`tests/unit/v03/fakes.py::AppFixture`（ENV-1）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库 / ENV-2 loopback 测试 HTTP 实例 / ENV-3 provider 进程内 fake（按 Case 需要，见 §4）
- 依赖的测试资产（tests.asset-design 文档）：无（真实实现）

## 3. 输入构造

- 逐参数输入构造：含 `Bearer …`/`Authorization`/`token=`/`api_key=…`/`apikey=…`/`access_key=…`/`X-Api-Key: …`/`secret: …` 消息；超长 900；换行；过滤 level/module
- 边界/非法取值及理由：512 长度边界；limit 上限
- 规模 / 时间域（数量、分页、复杂度、观测开销）：O(记录数)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `Bearer`/`Authorization`/`api_key`/`token` 等脱敏 | 键名与值均不含原文（整体 `[REDACTED]`） |
| 2 | 换行折叠 | 单行 |
| 3 | 长度 ≤512 | 截断 |
| 4 | 过滤 level/module | 全部命中 |
| 5 | 倒序/limit | 顺序与条数 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`RULE-LOG-REDACT/ORDER` + 脱敏规范；人工推导。**判据语义以设计验证项 `VRC-LOG-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：落库文本含 `[REDACTED]` 且凭据值（`api_key=`/`apikey=`/`access_key=`/`X-Api-Key:` 的值）不出现；换行折叠为空格；长度 ≤512；按过滤返回；倒序；limit 夹到 200

## 6. 错误路径、副作用与清理

- 错误出口与表现：无（分支互斥）
- 副作用断言与清理：日志落库；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/v03/test_logs.py::LogsTests`（7 个）＋ `LogRedactionGapTests`（含 `test_api_key_redacted`、`test_api_key_value_redaction`、`test_access_key_value_redacted`、`test_x_api_key_header_value_redacted`、`test_secret_redacted`、`test_token_query_redacted`、`test_bearer_redacted`、`test_authorization_redacted`）（注意：本 Case 的测试函数当前按子句（test case method）映射；若与设计 VRC 不一致，以设计修订回溯后重裁）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/v03/test_logs.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/v03`）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。

