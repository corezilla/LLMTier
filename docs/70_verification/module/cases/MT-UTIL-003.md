<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-UTIL-003 — Store 连接分支

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-UTIL-003` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-UTIL-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-UTIL-003`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-UTIL-003.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-UTIL-003` / M007 连接分支：symlink 503/world-writable/fd 基线/close 异常（组装） v0.1.0-draft.2 / VRC-UTIL-001（util-design §14 / util.isd §9.1，util 0.1.0-draft.2） / VRC-UTIL-001 / boundary / P0（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：边界值（上限/零/空/刚好满、长度、分页越界）+ 条件边界（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M007-连接四分支
- 要测什么（责任展开）：symlink→503 `store_path_unsafe`；world-writable 警告；多请求 fd 基线不泄漏；close 异常上抛（本 Case 责任：symlink 拒绝、world-writable 告警、连接回收、close 幂等）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝util 组装后连接建立前的拒绝与告警分支与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/util/store.py::Store._precheck`/`connection`/`close`

```text
Store(path)  # _precheck: symlink 拒绝 / world-writable 告警
```

- 初态构造（经公开入口）：临时目录 + 真实文件（symlink/权限经文件系统注入，方案 §2.2 存储面）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 组装隔离库
- 依赖的测试资产（tests.asset-design 文档）：无（全部真实实现；不经替身）

## 3. 输入构造

- 逐参数输入构造：symlink 指向的目标库；mode `0o666` 的库文件；同连接反复取用 5 次并连开 3 次
- 边界/非法取值及理由：symlink→503 `store_path_unsafe`；world-writable→`RuntimeWarning`；fd 基线≤+1；`close()` 幂等可重连
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单连接、5 次取用；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `Store(symlink)` | 抛 503 `store_path_unsafe` |
| 2 | `Store(0o666 文件)` 并捕获告警 | 迁移成功且有 world-writable 告警 |
| 3 | 反复取连接 5 次、再连开 3 次 | fd ≤ 基线 +1 |
| 4 | `close()` ×2 后再取用 | 重连成功并读到 `schema_version=2` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：util 模块设计 §9 分支行；按 `_precheck` 的 `lstat` 判定与 PRAGMA 语义人工推导
- 互斥预期（成功 / 各错误分支）：symlink 拒绝 503；world-writable 告警但可用；连接回收不泄漏 fd；close 幂等可重连

## 6. 错误路径、副作用与清理

- 错误出口与表现：symlink→503 `store_path_unsafe`；world-writable 告警不阻断
- 副作用断言与清理：拒绝时不创建新文件；close 后旧 fd 释放

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-UTIL-003.py`（4 个）：`test_symlink_path_rejected_503`、`test_world_writable_warns_but_opens`、`test_many_connections_fd_baseline_stable`、`test_close_is_idempotent_and_reconnect_works`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-UTIL-003.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
