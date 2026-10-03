<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-UTIL-001 — Store 组装后连接行为

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-UTIL-001` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-UTIL-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-UTIL-001`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-UTIL-001.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-UTIL-001` / M007 util §9 · `Store` 连接/PRAGMA/回收（组装） v0.1.0-draft.2 / VRC-UTIL-001（util-design §14 / util.isd §9.1，util 0.1.0-draft.2） / VRC-UTIL-001 / boundary / P0（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：边界值（上限/零/空/刚好满、长度、分页越界）+ 条件边界（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：无（层① 接口行为分母行）
- 要测什么（责任展开）：组装后连接：`foreign_keys=1`/`wal`、每线程一连接、fd 基线稳定、close 异常、world-writable、symlink 拒绝（本 Case 责任：真实组装后连接 PRAGMA、每线程一连接、fd 基线稳定、close 释放）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝util 组装后连接契约与 fd 回收与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/util/store.py::Store`（`__init__`/`_precheck`/`connection`/`close`）、`src/http_api/app.py::Application`（真实组装）

```text
Store(path); store.connection() -> sqlite3.Connection; store.close()
```

- 初态构造（经公开入口）：经 `AppFixture`（ENV-1）建空 `Application`：真实 `Store` 迁移建表，`Registry`/`Router`/`UsageRecorder`/`DiagnosticsService` 全部真实装配
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 组装隔离库（`AppFixture`，每 Case 新建临时目录）；ENV-2 loopback 组装 HTTP 实例（fd 基线经真实请求栈）
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture`（`FakeAdapter`/`AppFixture` 组装契约，见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：连接：`store.connection()`；线程：主线程 + 1 worker 线程；HTTP：`GET /healthz` ×45（3 轮 ×15）
- 边界/非法取值及理由：每线程一连接（同线程复用、跨线程互不共享）；fd 基线：3 轮请求后 fd 数相对首轮不增长（≤+2）
- 规模 / 时间域（数量、分页、复杂度、观测开销）：45 次 loopback 请求；每请求 1 连接；O(1) 每请求；观测开销为 `/dev/fd` 计数

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 主线程取 `store.connection()` 并读 PRAGMA | `foreign_keys=1`、`journal_mode=wal` |
| 2 | worker 线程取 `store.connection()`，主线程再取一次 | 跨线程不同连接对象；主线程仍为同一对象 |
| 3 | `store.close()` 后复用旧连接对象 | 旧连接执行语句抛异常（连接已关闭） |
| 4 | 经 ENV-2 连发 45 次 `/healthz`，按轮记录 fd 数 | 第 3 轮 fd ≤ 首轮 +2（无泄漏） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：util 模块设计 §9 连接契约；按 PRAGMA 语义与「每请求 finally 关闭线程本地连接」人工推导，不调用被测复算
- 互斥预期（成功 / 各错误分支）：`foreign_keys=1`；`journal_mode=wal`；同线程同连接、跨线程不同连接；close 后旧连接不可用；fd 基线不随请求数增长

## 6. 错误路径、副作用与清理

- 错误出口与表现：无额外错误出口（非本 Case 范围：symlink/world-writable 归 MT-UTIL-003）
- 副作用断言与清理：每请求线程本地连接被 `_run` finally 关闭；fd 无增长；无半写

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-UTIL-001.py`（4 个）：`test_foreign_keys_and_wal_on_connection`、`test_thread_local_connections`、`test_close_releases_connection`、`test_fd_baseline_stable_across_requests`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-UTIL-001.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
