<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-UI-006 — 诊断页 4 tabs 与 Disabled 视觉

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-UI-006` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-UI-006.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`ST-UI-006`）；责任摘要、分类与优先级以 [系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-UI-006` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-UI-006` / 模块设计 web-ui §14（ISD §9.1） / `VRC-UI-006` / `normal` / `P1`
- 方案清单登记：`ST-UI-006`
- **UI 方法模式（§1.5 方法表行）**：**导航 / 可见性**——切换 tab/子 tab，断言 `.page.active`/`.dsub.active` 真的变了，且懒加载调用**按需触发（不重复、不遗漏）**。
- **六要素映射（约束「每 Case 必须写明」）**：模式＝本节；构造的状态＝§3（页面已加载；诊断开关默认关闭）；执行的操作＝§4（点击 Diagnostics → 点击 dstats）；DOM 断言＝§4（4 个 `[data-dtab]`、`#snapshots.dsub.active`、`#dstats.dsub.active`、Disabled 行真实绘制）；网络断言＝§4（`GET /v1/diagnostics`→200；dstats 关闭时 `assertNoNetwork GET /v1/diagnostics/stats`）；证据位置＝§7。
- 要测什么（责任展开）：Diagnostics 页 4 个子 tab 渲染并可切换；开关关闭时 Snapshots/Stats 表体真实渲染 `Disabled — ...`（OBS 视觉子项：Disabled 状态被实际绘制，非空屏）。
- 明确不测什么 / 失败含义：不证明开关读写的服务端语义（ST-OBSDIAG-001/02）。

**目的（被测契约）**：Diagnostics 页 4 个子 tab 渲染并可切换；开关关闭时 Snapshots/Stats 表体真实渲染 `Disabled — ...`（OBS 视觉子项：Disabled 状态被实际绘制，非空屏）。 本 Case 是 `RISK-UI-EXEC-1` 关闭证据之一——在**真实浏览器**中执行 `src/web_ui/index.html`、`src/web_ui/app.js`，取代此前的源码字符串契约断言。被测入口：`src/web_ui/`（由 LLMTier 同源静态服务 `/ui/`）；驱动：headless Chrome + CDP（`tests/common/drivers/browser_driver.mjs`）；编排：`tests/system/cases/ST-UI-001.py`。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（hermetic 临时 `LLMTierInstance`，loopback；上游为 LAN-bound fake provider `tests/fixtures/models/v03_fake_provider.py`，TS-003）。规范依赖：`LLMTIER_BROWSER`（浏览器可执行路径，默认 `/Applications/Google Chrome.app/...` 或缓存 Chromium）、`LLMTIER_NODE`（node ≥ 22，内置 `WebSocket`）。无需 m5air。初始状态=baseline（1 provider `prov_b` / 1 deployment `depl_b`（探测为 healthy）/ 7 fixed tiers）。
- 被测入口声明与位置：`src/web_ui/index.html`、`src/web_ui/app.js`（同源 `/ui/`）。
- Fixture / 向量：`tests/system/cases conftest.py::ui_instance` / `fake_provider_b`。

## 3. 输入构造

- **输入与构造**：`Page.navigate` 到 `<base_url>/ui/`；后续为真实 DOM 事件（click/change）与注入（`window.confirm` stub、`window.fetch` 包装）。网络事实由 CDP `Network.*` 域记录（request/response + 请求头）。
- 边界/非法取值：见 §4 各步。无故障注入。
- 规模 / 时间域：单页、单会话；`waitFor` 上限 10s，driver 总超时 180s。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 加载 `/ui/`；点击 Diagnostics tab。 |
| 2 | 断言 `[data-dtab]` 计数 = 4；`#snapshots.dsub.active`。 |
| 3 | 等待并断言 `#snapshots-body` 文本含 `Disabled`。 |
| 4 | 点击 `[data-dtab='dstats']`；断言 `#dstats.dsub.active`；等待并断言 `#dstats-body` 文本含 `Disabled`。 |
| 5 | 断言 `GET /v1/diagnostics`→200；**负向**：dstats 开关关闭时断言 **无** `GET /v1/diagnostics/stats`（懒加载按需、不遗漏也不多余）。 |

**重点关注步骤**：真实 DOM 与真实网络为准；断言对象是 `document.*` 的实时值或 CDP 网络记录，**不是** `app.js` 源码文本。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `index.html` 的 4 个 `[data-dtab]` 与 `#snapshots-body`/`#dstats-body` 的 Disabled 行 ＋ `GET /v1/diagnostics` 200。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：全部 `assert*`/`assertNetwork` 步通过，且产出 screenshot 证据。
  - **FAIL**：任一断言失败（DOM 状态不符或未见期望网络调用），或选中文本与 API 数据不一致。
  - **BLOCKED**：浏览器/node 缺失或 CDP 握手失败（测试代码/环境问题）。
  - **SKIP**：无 LAN IP 起 fake provider，或 `LLMTIER_TEST_PROVIDER_URL` 覆盖（`fake_provider_b` 主动 skip）。
  - **NOT_RUN**：无（自动化入口已实现）。
  - **INVALID**：断言退化为源码字符串或未真正驱动浏览器（例如 mock DOM）却按行为判定。

## 6. 错误路径、副作用与清理

- 错误出口与表现：见 §4（`ST-UI-007` 为注入 500）。driver 在 `finally` 中 `SIGKILL` 浏览器、删除临时 `user-data-dir`；`ui_instance.stop()` 终止实例并 `rm -rf` 临时目录；`fake_provider_b` teardown 终止 fake provider。端口由内核分配（无固定端口泄漏）。
- 副作用断言与清理：`ST-UI-003` 必须在用例内 Resume 回初态；其余用例只读。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/system/cases/ST-UI-001.py`（`Case ID: ST-UI-006` 经 `record_property` 写入 JUnit，供 `tools/test_report.py` 归集）；驱动 `tests/common/drivers/browser_driver.mjs`。入口：
  ```text
  PYTHONPATH=src python3 -m pytest tests/system/cases -m ui -q -k ST-UI-006
  # 或 tools/run_ui_tests.sh
  ```
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/system/cases -m ui -q -k ST-UI-006`
- 实现状态：`Implemented`（`tests/system/cases/` (ST-UI-*) 已建并本地 PASS）；执行状态与 Verdict 归 Run 报告。
- **证据与 Run**：截图 `tests/system/artifacts/ST-UI-006/ST-UI-006.png`与网络日志 `ST-UI-006.network.json`。测试包 `tests/system/cases`（ST-UI-*） 为独立 `-m ui` 标记，不并入 A/B 系统班；`RISK-UI-EXEC-1` 关闭证据见系统方案 §4 与系统计划 §10-O6。

## 8. 需求与设计可追溯

- 设计验证项：`VRC-UI-006`（模块设计 web-ui §14 / [web-ui ISD §9.1](../../../50_implementation_design/web-ui.isd.md)）。
- 需求链：`LT-FUN-*`（控制台）/ `LT-OPS-*`（可观测）/ `R-OBS-05`（诊断页），以系统方案 §3.6 映射为准。本 Case 关闭 `RISK-UI-EXEC-1`（Owner M002 web-ui/共同 M005）。
