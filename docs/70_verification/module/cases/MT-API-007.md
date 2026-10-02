<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-API-007 — `_body` 四出口

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-API-007` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-10-02` |
| Last Modified Date | `2026-10-02` |
| Template ID | `tests.module-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/module/cases/MT-API-007.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-API-007`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-API-007.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-API-007` / M001 `_body` 分支：非法 Content-Length/413/非法 JSON/非对象（组装） v0.1.0-draft.2 / VRC-API-003（http-api-design §14 / http-api.isd §9.1，http-api 0.1.0-draft.2） / VRC-API-003 / boundary / P0（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：边界值（上限/零/空/刚好满、长度、分页越界）+ 条件边界（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M001-Content-Length/413/JSON/非对象
- 要测什么（责任展开）：四出口分别断言 400 `invalid_request` / 413 `request_too_large` / 400 `invalid_json` ×2（本 Case 责任：非法 Content-Length/超 2 MiB/非法 JSON/顶层非对象四出口码精确，阈值不误伤）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝http-api 组装后请求体解析四出口与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/http_api/app.py::Handler._body`

```text
_body() -> dict  # Content-Length / 2 MiB / JSON / 顶层类型四出口
```

- 初态构造（经公开入口）：同 MT-API-001；超大请求经原始 socket 注入
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2
- 依赖的测试资产（tests.asset-design 文档）：无（全部真实实现；不经替身）

## 3. 输入构造

- 逐参数输入构造：`Content-Length: abc`；`Content-Length: 2 MiB + 1`；`{nope`；`[1,2]`；刚好 2 MiB 的合法 JSON
- 边界/非法取值及理由：`>2 MiB`→413；非法 Content-Length→400 `invalid_request`；非法 JSON 与顶层非对象→400 `invalid_json`；恰好 2 MiB 不触发 413
- 规模 / 时间域（数量、分页、复杂度、观测开销）：4–5 请求；超大请求只发头 + 8 KiB 体；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 原始 socket 发 `Content-Length: abc` | 400 `invalid_request` |
| 2 | 原始 socket 声明 `2 MiB + 1` 体 | 响应行含 `413` + `request_too_large` |
| 3 | 原始体 `{nope` | 400 `invalid_json` |
| 4 | 原始体 `[1,2]` | 400 `invalid_json` |
| 5 | 体长恰好 2 MiB 的合法 JSON | 不返回 413（进入后续校验） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：http-api 模块设计 §14.3 + 错误码契约；按 `_body` 四处 `raise` 人工推导
- 互斥预期（成功 / 各错误分支）：四出口码精确；2 MiB 阈值不误伤

## 6. 错误路径、副作用与清理

- 错误出口与表现：400 `invalid_request` / 413 `request_too_large` / 400 `invalid_json`（×2）
- 副作用断言与清理：413 时服务端不读全量体即应答

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-API-007.py`（5 个）：`test_invalid_content_length_is_400`、`test_oversized_body_is_413`、`test_non_json_body_is_400_invalid_json`、`test_non_object_json_is_400_invalid_json`、`test_exactly_2mb_body_passes_body_gate`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-API-007.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
