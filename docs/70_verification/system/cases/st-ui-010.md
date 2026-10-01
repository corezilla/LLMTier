<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-ui-010 — 极值文本渲染不溢出、不注入、不破坏布局

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-ui-010` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-10-01` |
| Last Modified Date | `2026-10-01` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/st-ui-010.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`ST-ui-010`）；责任摘要、分类与优先级以 [系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-ui-010` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-ui-010` / 模块设计 web-ui §14（ISD §9.1） / `VRC-UI-001` / `boundary` / `P2`
- 方案清单登记：`ST-ui-010`
- **UI 方法模式（§1.5 方法表行）**：**边界呈现**——极值数据（超长文本、HTML 元字符、空字段），打开该区域，断言不溢出/不错位/不被解析为标记，与契约呈现规则一致。
- **六要素映射（约束「每 Case 必须写明」）**：模式＝本节；构造的状态＝§3（播种超长且含 `<img onerror>`/`&`/引号的 deployment 名称与 backend_model）；执行的操作＝§4（打开 Home）；DOM 断言＝§4（精确文本以**文本**形式存在、无注入 `<img>`、无水平溢出）；网络断言＝§4（对应 GET 200）；证据位置＝§7（含 `boundary` 额外截图）。
- 要测什么（责任展开）：极端文本必须按契约转义为文本（不解析为标记）、完整呈现、且不使页面水平溢出。
- 明确不测什么 / 失败含义：不证明大数值/科学计数的格式化（本 UI 的数值经 `metric()` 原样呈现，无科学计数逻辑；见下「不适用项说明」）。失败含义＝极值输入导致 XSS/布局破坏/呈现失真。

**目的（被测契约）**：极值文本在真实浏览器中渲染为转义文本、布局不溢出、无标记注入。被测入口：`src/web_ui/`（同源 `/ui/`）；驱动：headless Chrome + CDP；编排：`tests/ui/test_ui_browser.py`。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（hermetic 临时 `LLMTierInstance`，loopback；上游为 LAN-bound fake provider，TS-003）。本 Case 自建实例，将 baseline `depl_b` 的 `name`/`backend_model` 替换为极值文本。规范依赖：`LLMTIER_BROWSER`、`LLMTIER_NODE`。无需 m5air。
- 被测入口声明与位置：`src/web_ui/index.html`、`src/web_ui/app.js`（同源 `/ui/`）。
- Fixture / 向量：`tests/ui/conftest.py::provider_endpoint_b`、`LLMTierInstance`、`baseline_settings`。

## 3. 输入构造

- **输入与构造**：`Page.navigate` 到 `<base_url>/ui/`；极值文本 ＝ `"L" + "X"*300 + "<img src=x onerror=alert(1)> & \"quoted\""`，作为 deployment 的 `name` 与 `backend_model` 播种。网络事实由 CDP `Network.*` 域记录。
- 边界/非法取值：超长（300+ 字符）、HTML 元字符（`<`/`>`/`&`/引号）；空字段由 `ST-ui-004` 承接。
- 规模 / 时间域：单页、单会话；`waitFor` 上限 10s，driver 总超时 180s。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 加载 `/ui/`；等待 `#tree details`。 |
| 2 | 断言 `#tree .backend-name b` 的 `textContent` **包含**完整极值串（逐字呈现）。 |
| 3 | 断言页面内 `#tree img` 计数 = 0（元字符被转义，未解析为 `<img>` 标记）。 |
| 4 | 断言 `textContent` 含字面量 `<img`（确为文本而非元素）。 |
| 5 | 断言 `document.documentElement.scrollWidth <= window.innerWidth + 2`（无水平溢出）。 |
| 6 | 截图 `boundary`（额外证据）。 |

**重点关注步骤**：断言对象是实时 DOM 文本/布局度量；出现注入元素或水平溢出即失败。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `esc()` 转义契约（`app.js` 对所有数据文本做 HTML 转义）＋ 布局不变量（页面无水平滚动）。**DOM 断言**：文本逐字存在、无注入元素、无溢出。**网络断言**：`GET /v1/deployments`→200。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：文本逐字呈现、无注入 `<img>`、无水平溢出。
  - **FAIL**：文本被截断/解析为标记，或出现水平溢出。
  - **BLOCKED**：浏览器/node 缺失或 CDP 握手失败（测试代码/环境问题）。
  - **SKIP**：无 LAN IP 起 fake provider，或 `LLMTIER_TEST_PROVIDER_URL` 覆盖（`fake_provider_b` 主动 skip）。
  - **NOT_RUN**：无（自动化入口已实现）。
  - **INVALID**：断言退化为源码字符串或未真正驱动浏览器却按行为判定。
- **不适用项说明**：模式表列的「大数/0/负、科学计数失真、多行」子项对本 UI 部分不适用——`metric()` 对数值原样 `esc()` 呈现（无科学计数格式化路径），0/负/多行不进入 UI 数据模型；空字段/无值态的「不臆造 0」由 `ST-ui-004` 承接。本 Case 聚焦 Web UI 真实可达的文本极值边界（超长 + 元字符 + 转义/布局）。

## 6. 错误路径、副作用与清理

- 错误出口与表现：driver 在 `finally` 中 `SIGKILL` 浏览器、删除临时 `user-data-dir`；本 Case 在 `finally` 中 `inst.stop()` 终止私有临时实例并 `rm -rf` 临时目录；`fake_provider_b` teardown 终止 fake provider。端口由内核分配。
- 副作用断言与清理：本 Case 只读；实例为本 Case 私有，结束销毁。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/ui/test_ui_browser.py::test_ui_boundary_long_text_renders_without_overflow`（`Case ID: ST-ui-010` 经 `record_property` 写入 JUnit）；驱动 `tests/ui/browser_driver.mjs`。入口：
  ```text
  PYTHONPATH=src python3 -m pytest tests/ui -m ui -q -k ST-ui-010
  # 或 tools/run_ui_tests.sh
  ```
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/ui -m ui -q -k ST-ui-010`
- 实现状态：`Implemented`（本地 PASS）；执行状态与 Verdict 归 Run 报告。
- **证据与 Run**：截图 `tests/ui/artifacts/ST-ui-010/ST-ui-010.png` 与 `ST-ui-010.boundary.png`，网络日志 `ST-ui-010.network.json`。

## 8. 需求与设计可追溯

- 设计验证项：`VRC-UI-001`（模块设计 web-ui §14.1 / [web-ui ISD §9.1](../../../50_implementation_design/web-ui.isd.md)）。
- 需求链：`LT-FUN-*`（控制台），以系统方案 §3.6 映射为准。本 Case 补充覆盖 §1.5「边界呈现」模式（原 UI 类无此模式 Case）。
