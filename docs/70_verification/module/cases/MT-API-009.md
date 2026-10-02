<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-API-009 — `_static` 三分支

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-API-009` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-API-009.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-API-009`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-API-009.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-API-009` / M001 `_static` 分支：穿越 404/未命中 404/`/ui/`→index（组装） v0.1.0-draft.2 / VRC-API-004（http-api-design §14 / http-api.isd §9.1，http-api 0.1.0-draft.2） / VRC-API-004 / security / P1（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：鉴权/脱敏/注入边界冒烟 + 契约 + 分支×端点配对（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M001-穿越/未命中/`/ui/`
- 要测什么（责任展开）：`../` 穿越→404；缺失文件→404；`/ui/`→`index.html`；三态分别断言（本 Case 责任：目录穿越→404；缺失文件→404；`/ui/`→index.html 200）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝http-api 组装后静态文件三分支与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/http_api/app.py::Handler._static`

```text
GET /ui/../http_api/app.py, /ui/../../etc/passwd, /ui/missing.css, /ui/, /
```

- 初态构造（经公开入口）：同 MT-API-001；真实 `src/web_ui/` 产物
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2
- 依赖的测试资产（tests.asset-design 文档）：无（全部真实实现；不经替身）

## 3. 输入构造

- 逐参数输入构造：两条未规范化穿越路径、一条缺失文件、`/ui/`、`/`
- 边界/非法取值及理由：穿越→404（不泄漏文件）；缺失→404；`/ui/`→`index.html` 200
- 规模 / 时间域（数量、分页、复杂度、观测开销）：5 请求；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /ui/../http_api/app.py`（原始路径） | 404 且响应体含 `not_found` |
| 2 | `GET /ui/../../etc/passwd` | 404 |
| 3 | `GET /ui/does-not-exist.css` | 404 `not_found` |
| 4 | `GET /ui/` | 200 `text/html` |
| 5 | `GET /` | 200 且正文含 `LLMTier` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：http-api 模块设计 §14.5 + ISD 静态安全；按 `_static` 的 resolve/边界判定人工推导
- 互斥预期（成功 / 各错误分支）：穿越与缺失均 404；index 映射正确

## 6. 错误路径、副作用与清理

- 错误出口与表现：穿越/未命中→404 `not_found`
- 副作用断言与清理：不读取 webui 根目录外文件

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-API-009.py`（4 个）：`test_traversal_is_404`、`test_missing_file_is_404`、`test_ui_root_maps_to_index`、`test_root_path_serves_index_too`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-API-009.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
