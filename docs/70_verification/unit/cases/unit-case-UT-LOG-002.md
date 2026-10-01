<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-LOG-002 — 日志 page 窗口必填与存储失败 503

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-LOG-002` |
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
| Canonical Path | `docs/70_verification/unit/cases/unit-case-UT-LOG-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-LOG-002`）；责任摘要、分类与优先级以 [单元测试方案 §3](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [log](../../../40_module_design/log-design.md) §14 / ISD [log.isd.md](../../../50_implementation_design/log.isd.md) §9.1，设计验证项 `VRC-LOG-001`（固定版本 `log 0.1.0-draft.1`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `log`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-LOG-002` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-LOG-002` / M008 log §14.1 · `page` 边界 v0.1.0-draft.1 / `VRC-LOG-001` / negative / P1（[方案清单 §3](../llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：边界值（缺 since/until/存储失败/脱敏）
- 要测什么（责任展开）：被测：`page` 缺 `since`/`until` → 400 `invalid_request`；`page` 存储失败 → 503 `usage_store_unavailable`；`token=`/`api_key` 键名**与值**整体脱敏用例（`RISK-LOG-1` 已关闭）。
- 明确不测什么 / 失败含义：不测：脱敏主用例（UT-LOG-001）；不测 `limit` 夹取（UT-LOG-001）。失败含义＝窗口必填校验/存储失败显式化/补充脱敏实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/log/logs.py::OperationalLog.page`（窗口必填 + 脱敏）与 `src/http_api/app.py::Handler._store_read`（503 映射）

```text
OperationalLog.page(limit=50, level=None, module=None, request_id=None, since=None, until=None) -> dict
```

- 初态构造（经公开入口）：`AppFixture().seed()` + loopback `handler_factory(app)`；patch `logs.page` 抛 `sqlite3.OperationalError`（ENV-1+ENV-2）
- Fixture / 向量及版本：`tests/unit/v03/test_logs.py::LogHttpFailureTests`/`LogsTests`；`fakes.py::AppFixture`（ENV-1）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库 / ENV-2 loopback 测试 HTTP 实例
- 依赖的测试资产（tests.asset-design 文档）：无（真实实现）

## 3. 输入构造

- 逐参数输入构造：无窗口的 `GET /v1/logs`；patch 存储失败带窗口的 `GET /v1/logs`；`token=…`/`api_key` 消息
- 边界/非法取值及理由：缺窗口→400；存储失败→503；脱敏文本
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单请求，O(行数)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /v1/logs` 无窗口 | 400 `invalid_request` |
| 2 | patch 存储失败 + 带窗口 | 503 `usage_store_unavailable` |
| 3 | `token=`/`api_key` 消息落库 | 文本脱敏 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`RULE-LOG-REDACT/ORDER` + `IF-LOG` 窗口必填 + 人工推导；不调用被测复算。**判据语义以设计验证项 `VRC-LOG-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：无窗口 400 `invalid_request`；存储失败 503 `usage_store_unavailable`；`token=`/`api_key`/`apikey` 键名与值整体脱敏；互斥

## 6. 错误路径、副作用与清理

- 错误出口与表现：400 `invalid_request`；503 `usage_store_unavailable`；无第三态
- 副作用断言与清理：脱敏后落库（隔离库）；loopback 实例清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/v03/test_logs.py::LogHttpFailureTests::test_missing_window_is_400` / `test_store_failure_is_503` + 补充脱敏 `LogRedactionGapTests::test_token_query_redacted` / `test_api_key_value_redaction`（值不落库） / `test_secret_redacted`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/v03/test_logs.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/v03/test_logs.py`）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。
