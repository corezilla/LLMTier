<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-UI-008 — 配了 secret 的 provider 只显示脱敏标记，secret 值不落 DOM/URL/日志

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-UI-008` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-UI-008.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`ST-UI-008`）；责任摘要、分类与优先级以 [系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-UI-008` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-UI-008` / 模块设计 web-ui §14（ISD §9.1） / `VRC-UI-001` / `security` / `P1`
- 方案清单登记：`ST-UI-008`
- **UI 方法模式（§1.5 方法表行）**：**脱敏 / 安全呈现**——provider 配了 secret，打开展示页与编辑抽屉，断言 secret 值**永不出现**在 DOM/URL/网络日志中，只显示脱敏标记（`Configured`）。
- **六要素映射（约束「每 Case 必须写明」）**：模式＝本节；构造的状态＝§3（播种一个 `secret_ref="env:LLMTIER_UI_SECRET_008"` 的 provider，其环境值为已知哨兵）；执行的操作＝§4（打开 Providers、打开该 provider 的编辑抽屉）；DOM 断言＝§4（行内显示 `Configured`、`secret_ref` 输入为空、`documentElement.outerHTML` 与 `location.href` 均不含哨兵值/引用串）；网络断言＝§5（网络日志不含哨兵值/引用串）；证据位置＝§7。
- 要测什么（责任展开）：provider 视图只暴露 `has_secret`（布尔），**不得**暴露 secret 值或其引用串；UI 只显示脱敏标记 `Configured`，编辑态不回填任何 secret。
- 明确不测什么 / 失败含义：不证明服务端密钥存储加密、不证明上游鉴权（归 ST-AUTH-* / 安全 Case）。失败含义＝secret 值/引用以任何形式泄露到浏览器可见面。

**目的（被测契约）**：配了 `secret_ref` 的 provider 在真实浏览器中只呈现脱敏标记，secret 值与引用串不得出现在 DOM、URL 或 CDP 网络日志中。被测入口：`src/web_ui/`（同源 `/ui/`）；驱动：headless Chrome + CDP（`tests/ui/browser_driver.mjs`）；编排：`tests/ui/test_ui_browser.py`。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（hermetic 临时 `LLMTierInstance`，loopback；上游为 LAN-bound fake provider `tests/fixtures/v03_fake_provider.py`，TS-003）。本 Case 自建实例并注入 `LLMTIER_UI_SECRET_008` 环境值（哨兵）；baseline 之上追加 `prov_secret`（`kind=cloud`，`secret_ref="env:LLMTIER_UI_SECRET_008"`）。规范依赖：`LLMTIER_BROWSER`、`LLMTIER_NODE`。无需 m5air。
- 被测入口声明与位置：`src/web_ui/index.html`、`src/web_ui/app.js`（同源 `/ui/`）。
- Fixture / 向量：`tests/ui/conftest.py::provider_endpoint_b`、`LLMTierInstance`、`baseline_settings`。

## 3. 输入构造

- **输入与构造**：`Page.navigate` 到 `<base_url>/ui/`；provider 通过 bootstrap settings 播种（`secret_ref=env:...`）。网络事实由 CDP `Network.*` 域记录（request/response + 请求头；日志落盘后由 §5 扫描）。哨兵：值 `SUPERSECRET_008_VALUE`、引用串 `env:LLMTIER_UI_SECRET_008`。
- 边界/非法取值：见 §4 各步。无故障注入。
- 规模 / 时间域：单页、单会话；`waitFor` 上限 10s，driver 总超时 180s。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 加载 `/ui/`；点击 Providers tab；等待 ≥2 个 `#provider-tree .provider-row`。 |
| 2 | 断言 `Secret Provider 008` 行文本含脱敏标记 `Configured`。 |
| 3 | 点击该 provider 的 `.provider-edit`；等待 `#provider-mask.open`；断言 `secret_ref` 输入值为空（不回填）。 |
| 4 | 断言 `document.documentElement.outerHTML` 不含哨兵值，也不含引用串。 |
| 5 | 断言 `location.href` 不含哨兵值与引用串。 |

**重点关注步骤**：断言对象是 `document.*` 的实时值与 CDP 网络记录；secret 值/引用一旦出现即失败。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = 服务端 provider 视图契约（`registry` 只返回 `has_secret`，不返回 `secret_ref`/值）＋ 脱敏标记 `Configured`。**网络断言**：`ST-UI-008.network.json`（URL/请求头）不含哨兵值或引用串。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：DOM/URL/网络日志均不含哨兵值或引用串，且行显示 `Configured`。
  - **FAIL**：任一形式泄露，或标记缺失。
  - **BLOCKED**：浏览器/node 缺失或 CDP 握手失败（测试代码/环境问题）。
  - **SKIP**：无 LAN IP 起 fake provider，或 `LLMTIER_TEST_PROVIDER_URL` 覆盖（`fake_provider_b` 主动 skip）。
  - **NOT_RUN**：无（自动化入口已实现）。
  - **INVALID**：断言退化为源码字符串或未真正驱动浏览器却按行为判定。

## 6. 错误路径、副作用与清理

- 错误出口与表现：driver 在 `finally` 中 `SIGKILL` 浏览器、删除临时 `user-data-dir`；本 Case 在 `finally` 中 `inst.stop()` 终止临时实例并 `rm -rf` 临时目录；`fake_provider_b` teardown 终止 fake provider。端口由内核分配。
- 副作用断言与清理：本 Case 只读；实例为本 Case 私有，结束销毁。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/ui/test_ui_browser.py::test_ui_provider_secret_never_shown`（`Case ID: ST-UI-008` 经 `record_property` 写入 JUnit）；驱动 `tests/ui/browser_driver.mjs`。入口：
  ```text
  PYTHONPATH=src python3 -m pytest tests/ui -m ui -q -k ST-UI-008
  # 或 tools/run_ui_tests.sh
  ```
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/ui -m ui -q -k ST-UI-008`
- 实现状态：`Implemented`（本地 PASS）；执行状态与 Verdict 归 Run 报告。
- **证据与 Run**：截图 `tests/ui/artifacts/ST-UI-008/ST-UI-008.png` 与网络日志 `ST-UI-008.network.json`；另经 DOM/URL/网络日志全扫描断言无泄露。

## 8. 需求与设计可追溯

- 设计验证项：`VRC-UI-001`（模块设计 web-ui §14.1 / [web-ui ISD §9.1](../../../50_implementation_design/web-ui.isd.md)）。
- 需求链：`LT-FUN-*`（控制台）/ `LT-OPS-*`（可观测），以系统方案 §3.6 映射为准。本 Case 补充覆盖 §1.5「脱敏 / 安全呈现」模式（原 UI 类无此模式 Case）。
