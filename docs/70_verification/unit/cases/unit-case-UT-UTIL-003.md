<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-UTIL-003 — Store fd 基线、busy/lock、close 异常与 world-writable

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-UTIL-003` |
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
| Canonical Path | `docs/70_verification/unit/cases/unit-case-UT-UTIL-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-UTIL-003`）；责任摘要、分类与优先级以 [单元测试方案 §3](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [util](../../../40_module_design/util-design.md) §14 / ISD [util.isd.md](../../../50_implementation_design/util.isd.md) §9.1，设计验证项 `VRC-UTIL-001`（固定版本 `util 0.1.0-draft.1`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `util`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-UTIL-003` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-UTIL-003` / M007 util §14.1 · `Store` 边界分支 v0.1.0-draft.1 / `VRC-UTIL-001` / recovery / P1（[方案清单 §3](../llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：故障注入 + 异常路径恢复（fd 不泄漏/busy/close 异常/world-writable）
- 要测什么（责任展开）：被测：`Store` fd 基线（多请求后不泄漏）；busy/lock→`OperationalError`；`close()` 异常上抛；world-writable → `RuntimeWarning`。
- 明确不测什么 / 失败含义：不测：PRAGMA/事务主路径（UT-UTIL-001/002）；不测迁移（UT-UTIL-004）。失败含义＝fd 回收/锁异常/close 异常/world-writable 告警实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/util/store.py::Store.close`/`connection`（线程本地连接、close 置 None、world-writable 检查）

```text
Store.close(); Store.connection(); Store.transaction(immediate=True)
```

- 初态构造（经公开入口）：`tempfile.TemporaryDirectory` 隔离库；构造 holding 写事务以触发 lock（ENV-1）
- Fixture / 向量及版本：`tests/unit/v03/test_store_gaps.py::FdHygieneTests`/`BusyLockTests`/`CloseRaisesTests`/`WorldWritableTests`
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库
- 依赖的测试资产（tests.asset-design 文档）：无（真实 SQLite）

## 3. 输入构造

- 逐参数输入构造：多请求后检查 fd；holding 写事务；patch 连接 close 抛异常；chmod world-writable 库文件
- 边界/非法取值及理由：fd 不增长；lock→`OperationalError`；close 异常上抛；world-writable 告警
- 规模 / 时间域（数量、分页、复杂度、观测开销）：O(请求数)；fd 基线对比

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 请求后 close | 释放 fd，下一次重连 |
| 2 | 重复 close | 幂等 |
| 3 | 持有写事务再写 | `OperationalError` |
| 4 | close 底层异常 | 上抛 |
| 5 | world-writable 文件 | `RuntimeWarning` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`RULE-UTIL-FD`/`CON-CFG-001` + 人工推导；不调用被测复算。**判据语义以设计验证项 `VRC-UTIL-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：close 释放并允许重连、幂等；lock 抛 `OperationalError`；close 异常上抛；world-writable 告警；互斥

## 6. 错误路径、副作用与清理

- 错误出口与表现：busy/lock `OperationalError`；close 异常上抛；无第三态
- 副作用断言与清理：临时库由 fixture 清理；无 fd 泄漏

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/v03/test_store_gaps.py::FdHygieneTests::test_close_releases_and_reconnects_after_request` / `test_close_is_idempotent` / `BusyLockTests::test_locked_write_raises_operational_error` / `CloseRaisesTests::test_close_exception_propagates` / `WorldWritableTests::test_world_writable_warns`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/v03/test_store_gaps.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/v03/test_store_gaps.py`）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。
