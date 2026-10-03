<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-UI-009 — 探测按钮连点只发一次有效调用（幂等/防重）

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-UI-009` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-10-01` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-UI-009.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`ST-UI-009`）；责任摘要、分类与优先级以 [系统测试方案 §6 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-UI-009` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-UI-009` / 模块设计 web-ui §14（ISD §9.1） / `VRC-UI-005` / `boundary` / `P1`
- 方案清单登记：`ST-UI-009`
- **UI 方法模式（§2.2 方法表行）**：**幂等 / 防重**——动作可触发，连点/重复提交，断言只发生**一次**有效调用（或幂等语义成立），页面不重复追加。
- **六要素映射（约束「每 Case 必须写明」）**：模式＝本节；构造的状态＝§3（探测为可触发的付费动作，确认通过）；执行的操作＝§4（同一任务内同步点击 Probe 两次）；DOM 断言＝§4（`#tree details` 计数保持不变，未重复追加）；网络断言＝§4（`POST /v1/probes` **计数 = 1**）；证据位置＝§7。
- 要测什么（责任展开）：确认通过后，同一任务内连点 Probe 两次，因首次点击**同步**置 `button.disabled=true`，第二次点击为 no-op，只发出一次 `POST /v1/probes`，页面不重复追加行。
- 明确不测什么 / 失败含义：不证明服务端探测去重（本 Case 只证明 UI 防重语义）。失败含义＝连点导致重复调用/重复渲染。

**目的（被测契约）**：UI 的付费/开销性动作在 in-flight 期间禁用，连点只产生一次有效能力调用，页面不重复追加。被测入口：`src/web_ui/`（同源 `/ui/`）；驱动：headless Chrome + CDP；编排：`tests/system/cases/ST-UI-001.py`。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（hermetic 临时 `LLMTierInstance`，loopback；上游为 LAN-bound fake provider，TS-003）。baseline（1 provider/1 deployment（探测 healthy）/7 fixed tiers）。规范依赖：`LLMTIER_BROWSER`、`LLMTIER_NODE`。无需 m5air。
- 被测入口声明与位置：`src/web_ui/index.html`、`src/web_ui/app.js`（同源 `/ui/`）。
- Fixture / 向量：`tests/system/cases conftest.py::ui_instance` / `fake_provider_b`。

## 3. 输入构造

- **输入与构造**：`Page.navigate` 到 `<base_url>/ui/`；`window.confirm=()=>true`；注入为同一任务内的两次 `el.click()`。网络事实由 CDP `Network.*` 域记录。
- 边界/非法取值：见 §4 各步。无故障注入。
- 规模 / 时间域：单页、单会话；`waitFor`/`waitForNetwork` 上限 10s，driver 总超时 180s。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 加载 `/ui/`；`window.confirm=()=>true`；等待 `#tree .backend-probe`；断言 `#tree details` 计数 = 7。 |
| 2 | 同一任务内同步执行 `b.click();b.click()`（首击同步禁用按钮）。 |
| 3 | 等待 `POST /v1/probes`→200。 |
| 4 | 断言 `POST /v1/probes` **计数 = 1**（只发生一次有效调用）。 |
| 5 | 断言 `#tree details` 计数仍 = 7（页面未重复追加）。 |

**重点关注步骤**：断言对象是 CDP 网络记录与实时 DOM；出现第二次 POST 或行数增长即失败。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `probeDeployment` 契约（首击同步 `button.disabled=true` 再 await）＋ CDP 网络计数。**网络断言**：`POST /v1/probes` 计数 = 1。**DOM 断言**：`#tree details` 计数不变。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`POST /v1/probes` 计数 = 1 且行数不变。
  - **FAIL**：计数 > 1 或行数增长。
  - **BLOCKED**：浏览器/node 缺失或 CDP 握手失败（测试代码/环境问题）。
  - **SKIP**：无 LAN IP 起 fake provider，或 `LLMTIER_TEST_PROVIDER_URL` 覆盖（`fake_provider_b` 主动 skip）。
  - **NOT_RUN**：无（自动化入口已实现）。
  - **INVALID**：断言退化为源码字符串或未真正驱动浏览器却按行为判定。

## 6. 错误路径、副作用与清理

- 错误出口与表现：driver 在 `finally` 中 `SIGKILL` 浏览器、删除临时 `user-data-dir`；`ui_instance.stop()` 终止实例（session 级）；`fake_provider_b` teardown 终止 fake provider。端口由内核分配。
- 副作用断言与清理：探测为一次性只读动作，不改注册表；本 Case 无额外复位需要。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/system/cases/ST-UI-001.py::test_ui_double_click_probe_is_not_duplicated`（`Case ID: ST-UI-009` 经 `record_property` 写入 JUnit）；驱动 `tests/common/drivers/browser_driver.mjs`。入口：
  ```text
  PYTHONPATH=src python3 -m pytest tests/system/cases -m ui -q -k ST-UI-009
  # 或 tools/run_ui_tests.sh
  ```
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/system/cases -m ui -q -k ST-UI-009`
- 实现状态：`Implemented`（本地 PASS）；执行状态与 Verdict 归 Run 报告。
- **证据与 Run**：截图 `tests/system/artifacts/ST-UI-009/ST-UI-009.png` 与网络日志 `ST-UI-009.network.json`（网络计数为判据）。

## 8. 需求与设计可追溯

- 设计验证项：`VRC-UI-005`（模块设计 web-ui §14.4 / [web-ui ISD §9.1](../../../50_implementation_design/web-ui.isd.md)）。
- 需求链：`LT-FUN-*`（控制台），以系统方案 §6.1 映射为准。本 Case 补充覆盖 §2.1「幂等 / 防重」模式（原 UI 类无此模式 Case）。
