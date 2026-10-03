<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Module Test Report — Run 2026-10-03-01

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-module-test-report-2026-10-03-01` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-10-03` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.module-test-report` |
| Template Version | `0.3.1` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `tests/module/reports/run-20261003-01/module-test-report.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本报告由 Run 目录 `tests/module/reports/run-20261003-01/` 的机器产物整理而成（`test-run.env`、`case-status.json`、72 份逐 Case `MT-*.json`、`artifacts/{junit.xml,pytest.log}`）。**报告里的每个 Verdict 逐条取自对应 `MT-<Case ID>.json` 的 `status` 字段**，未运行/未命中/失败项一律如实保留，不补造结果。本 Run 是模块层**第 9 个 Run、章节重编号（STD `f073396` 连续编号规则）后的首个复跑**：被测面（`src/`、`tests/module/cases`、`tests/common/`、`tools/`、`pyproject.toml`）相对 run-08 的 pin `e27dca9` **零差异**，`git_commit=851d172` 与执行时 `HEAD` 一致、工作树干净，结果与 run-08 完全一致（371/371 测试函数、72/72 Case `PASS`），证据可作最终 pin 依据（§2）。**前 8 个 Run（`run-20261002-01`…`-08`）的证据目录原样保留在目录树内，全部不被本报告覆盖或改写**；run-04、run-06 与 run-08 的既有定稿报告（`llmtier-module-test-report-2026-10-02-04`、`-2026-10-02-06`、`-2026-10-02-08`）作为历史记录保留（其 `document_id` 与本报告不同、不冲突；本报告 `Supersedes: none`，不做文首声明的替代关系，历史定性由本报告 §4.1/§4.2 追述，§1.3、§4.2）。本报告同时是**章节重编号后的最终定稿报告**：正文对方案/计划/case 文档的章节引用全部按新编号（方案 §2 方法、§2.1–§2.4、§3 替身、§4 环境、§5 分类、§6.1–§6.7 分母与清单、§7 缺口裁决、§8 联动）。

### 模板定位：报告、方案、用例、计划与 Run 证据的边界

- **Verdict 唯一持有**：执行状态（`NOT_RUN`/`BLOCKED`/`INVALID`）与实际判定（`PASS`/`FAIL`）只在测试报告与 Run 证据中产生；方案与 Case 文档不预填任何结果。
- **引用不复制**：逐 Case 结果引用 Run ID 与证据文件名，不把 stdout 全文搬进报告。
- **保留失败**：失败、阻塞、无效与未运行如实保留；**重跑生成新 Run，不覆盖旧失败**（计划 §7）。本报告即该规则的落地：run-01 与 run-03 的 `MT-INF-015` 失败记录、run-02 的「假绿」定性均未被删除或改写（§1.3、§4.1）。
- **不越权**：Gate 建议不是批准；验收与发布授权另循其轨。

### 状态语义：执行状态与 Verdict

| 状态 | 取值 | 含义 | 判定事实 |
|---|---|---|---|
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | 未运行 / 环境阻断 / 执行未命中设计 | 运行记录与环境事实 |
| 实际判定 Verdict | `PASS` / `FAIL` | 断言与独立 Oracle 一致 / 不一致 | 有效 Run 的断言结果 |

## 1. 执行摘要与结论

### 1.1 范围与执行

- 报告范围（计划/方案版本）：
  - 方案：`llmtier-module-test-scheme`（[docs/70_verification/module/llmtier-module-test-scheme.md](../../../../docs/70_verification/module/llmtier-module-test-scheme.md)，`0.1.0-draft.12`，Template `tests.module-test-scheme` v0.6.1；**四层分母 95 条 → 72 个 Case**：① 接口行为 23 / ② 内部分支 48 / ③ 组合 10 / ④ 状态迁移 14；§6 为 Case 清单唯一登记处，§6.7 为分母→Case 核对表，§2.3 为异常/错误注入矩阵（(a) 37 个对外 `code` ＋ (b) 8 类上游异常 ＋ (c) 8 类传输/时间病态 ＝ 53 条），§7 为缺口裁决（含已闭合的 `G-MT-COVERAGE-1`）。以上章节编号为按 STD `f073396` 连续编号规则重排后的**新编号**（原「缺口裁决 §4」现为 §7）。
  - 计划：`llmtier-module-test-plan`（[docs/70_verification/module/llmtier-module-test-plan.md](../../../../docs/70_verification/module/llmtier-module-test-plan.md)，`0.1.0-draft.14`，Template `tests.module-test-plan` v0.9.2；执行批次见其 §5.1，证据规则见其 §7，Gate 规则见其 §8，未决项见其 §10）。
  - 模块 Case 文档：72 份（`docs/70_verification/module/cases/`，`tests.module-case` v0.1.0-draft.2，章节同步重编号）。
  - 机器契约 pin（取自 `test-run.env`）：`schema_version=2`、`openapi_version=0.3-simplified-candidate.8`。
- 被测对象：8 个软件模块 `M001`–`M008`（`M001 http-api`、`M002 web-ui`、`M003 inference`、`M004 management`、`M005 observability`、`M006 libdiag`、`M007 util`、`M008 log`；`M005 src/observability/` 无独立实现文件，其行为落在 M001 诊断路由与 M006 查询面，见方案 §1）。
- 执行范围：本 Run 一次整批执行 `tests/module/cases` 全量 72 个 Case（`python3 -m pytest --junitxml=tests/module/reports/run-20261003-01/artifacts/junit.xml tests/module/cases`；`test-run.env` 记录），`PYTHONPATH=src` 由 `tests/common/harness/runner_module.sh` 的 `export PYTHONPATH=src` 提供，并在本 Run 的 `test-run.env` 中以 `pythonpath=src` 落证（计划 §6/§7）。

### 1.2 结果分布与总结论

- **Case 粒度：72 个 Case 全部收集、全部执行、全部 `PASS`**；`NOT_RUN=0`、`BLOCKED=0`、`INVALID=0`（逐 Case `MT-*.json` 与 `case-status.json` 的 `cases` 段逐条一致，后者 `status` 计数为 `PASS=371`）。
- **测试函数粒度：371 collected、371 passed、0 failed、0 skipped、0 errors、0 xpassed；套件 112.963s**（`artifacts/junit.xml` testsuite `tests="371" failures="0" errors="0" skipped="0" time="112.963"`；`artifacts/pytest.log` 首部 `collected 371 items`、末行 `371 passed in 112.96s (0:01:52)`）。`case-status.json.counts` 记 `PASS=371 / FAIL=0 / BLOCKED=0 / INVALID=0 / NOT_RUN=0 / SKIP=0 / XPASS=0`，并置 `release_blocking=false`（无 `FAIL`/`BLOCKED`/`INVALID` 记录）。
- 四层分母 95 条**全部映射到已执行的 Case，未覆盖 0 条**（见 §5.1）；异常/错误注入矩阵 53 条**全部映射到已执行 Case 且全部 `PASS`**（见 §5.2，含 c3「超长/超大 response」→ `MT-INF-015`，该行在 run-01/run-03 为失败事实、在本 Run 为 `PASS`）。
- 优先级与分类分布（方案 §6.6，与本 Run 逐 Case `status` 复算一致）：**P0 41 / P1 31**；negative 21 / boundary 13 / normal 12 / recovery 17 / security 6 / concurrency 3。
- **本 Run 相对 run-08 无资产与结果变化**：`e27dca9..851d172` 区间的提交（`11bf928`、`851d172`）全部只触 `docs/`——`11bf928` 修正 24 份 case 文档 §1 覆盖 ID、`851d172` 重锁 STD 并按新规则连续重编号三层测试文档章节；被测面（`src/`、`tests/module/cases`、`tests/common/`、`tools/`、`pyproject.toml`）零差异（`git diff --stat` 为空）。因此本 Run 是**纯章节重编号后的复跑**，371/371 与 72/72 `PASS`、`release_blocking=false` 与 run-08 完全一致（§1.3.9）。

### 1.3 模块层 Run 历史（9 个 Run，逐一如实叙述）

模块层在 `tests/module/reports/` 下共 **9 个 Run**（`run-20261002-01`…`-08`、`run-20261003-01`）。按计划 §7「**重跑生成新 Run，不覆盖旧失败**」，九者并存、互不覆盖；下表逐字段取自各自 `test-run.env` / `case-status.json` / `artifacts/junit.xml`。

| Run | `started_at` | `finished_at` | `git_commit` | 替身（ENV-3 `FakeUpstream`）写形态 | 测试函数（`artifacts/junit.xml`） | `case-status.json.counts` | Case 级状态 | `release_blocking` | 结论 |
|---|---|---|---|---|---|---|---|---|---|
| `run-20261002-01` | `2026-10-02T08:40:20Z` | 未落证（字段缺失） | `982efae9…`（落后被测树 1 个提交） | `Content-Length` + **单次 `write()` 整块 2 MiB** | `tests=354 failures=1 time=162.206` | `PASS=353 / FAIL=1` | 67 `PASS` + 1 `FAIL`（`MT-INF-015`） | `true` | **RED**：`MT-INF-015` 读阶段 60s `TimeoutError`→503 `provider_unavailable` |
| `run-20261002-02` | `2026-10-02T09:15:23Z` | 未落证（字段缺失） | `f83f8da7…` | `Content-Length` + 64 KiB 分块写 + 末尾 `flush()` | `tests=354 failures=0 time=102.736` | `PASS=354 / FAIL=0` | 68 `PASS` | `false` | **假绿**：全绿但替身仍是 `Content-Length` 大 body 形态，缺陷条件仍在 |
| `run-20261002-03` | `2026-10-02T09:23:14Z` | `2026-10-02T09:25:57Z` | `f83f8da7…` | 同 run-02（未再改替身） | `tests=354 failures=1 time=162.135` | `PASS=353 / FAIL=1` | **68 `PASS`（与 counts 不一致，见 §4.2）** | `true` | **RED**：同一 flake 再次复现（`test_service_remains_healthy_after_oversize` 60.126s） |
| `run-20261002-04` | `2026-10-02T09:40:31Z` | `2026-10-02T09:42:14Z` | `f83f8da7…`（**不含未提交替身修复**） | **`Transfer-Encoding: chunked` + 16 KiB 分片** | `tests=354 failures=0 time=102.520` | `PASS=354 / FAIL=0` | 68 `PASS` | `false` | **GREEN**：替身根除后首个全绿 Run；已有定稿报告（`llmtier-module-test-report-2026-10-02-04`），判闭合 |
| `run-20261002-05` | `2026-10-02T09:52:36Z` | `2026-10-02T09:54:19Z` | `f83f8da7…`（**≠ 执行树**：执行树含未入库的替身/工具修复） | `Transfer-Encoding: chunked` + 16 KiB 分片 | `tests=354 failures=0 time=102.672` | `PASS=354 / FAIL=0` | 68 `PASS`（`cases` 段逐条 `PASS`） | `false` | 复跑确认；**pin 与执行树不一致，不可作最终 pin 依据**，未生成报告实例 |
| `run-20261002-06` | `2026-10-02T09:57:55Z` | `2026-10-02T09:59:37Z` | `a1cb672b…`（＝执行时 HEAD，工作树干净） | `Transfer-Encoding: chunked` + 16 KiB 分片 | `tests=354 failures=0 time=102.515` | `PASS=354 / FAIL=0` | 68 `PASS` | `false` | **68 Case 基线的可采信 Run**：已有定稿报告（`llmtier-module-test-report-2026-10-02-06`，Gate 判闭合） |
| `run-20261002-07` | `2026-10-02T12:54:18Z` | `2026-10-02T12:56:12Z` | `998d879c…`（**≠ 执行树**：执行树含未提交的 4 个新脚本、`MT-MGMT-005` 扩充与 `src/inference/providers/openai.py` 修复） | `Transfer-Encoding: chunked` + 16 KiB 分片 | `tests=371 failures=0 time=113.149` | `PASS=371 / FAIL=0` | 72 `PASS` | `false` | 覆盖补齐后首个 371/72 Run；**pin 与执行树不一致，不作最终 pin 依据**，未生成报告实例 |
| `run-20261002-08` | `2026-10-02T13:58:52Z` | `2026-10-02T14:00:46Z` | `e27dca9d…`（＝执行时 HEAD，工作树无未提交改动） | `Transfer-Encoding: chunked` + 16 KiB 分片 | `tests=371 failures=0 time=113.159` | `PASS=371 / FAIL=0` | 72 `PASS` | `false` | **95 分母/72 Case 口径下首个 Gate 闭合 Run**：定稿报告 `llmtier-module-test-report-2026-10-02-08` 判闭合；「当前 Run」由本 Run（`run-20261003-01`）承接 |
| **`run-20261003-01`** | `2026-10-03T04:19:32Z` | `2026-10-03T04:21:25Z` | **`851d1724…`（＝执行时 HEAD，工作树干净）** | `Transfer-Encoding: chunked` + 16 KiB 分片 | `tests=371 failures=0 time=112.963` | `PASS=371 / FAIL=0` | 72 `PASS` | `false` | **最终 Run（本报告对象）＝章节重编号后复跑与最终定稿**：被测面与 run-08 零差异，结果与 run-08 一致（371/72 全 `PASS`），pin 与被测树逐字一致，证据可采信，Gate 判闭合 |

**1.3.1 `run-20261002-01`（RED，事实照录）**——68 Case 中 67 `PASS`、1 `FAIL`；`counts` 为 `PASS=353 / FAIL=1`，`release_blocking=true`；`artifacts/pytest.log` 末行 `1 failed, 353 passed in 162.21s (0:02:42)`。唯一 FAIL 为 `MT-INF-015`（M003，层②，boundary，**P1**）的 `OversizeTests::test_two_megabyte_output_normalized`，`MT-INF-015.json` 的 `reason` 记 `http_api.errors.ApiError: (503, 'provider_unavailable', 'Provider streaming request failed: TimeoutError: timed out')`，该节点耗时 **60.133s**（同套件其余 Case 均 0.5s 级）。该 Run 的 `test-run.env` 只有 8 个字段，无 `pythonpath`/`exit_code`/`pytest_exit_code`/`finished_at`（计划 §7 要求项，见 §2）。

**1.3.2 `run-20261002-02`（全绿，但是「假绿」）**——处置动作是把替身写侧改为 64 KiB 分块并逐块 `flush()`，随后整批复跑取得 `354/354 passed`、68/68 `PASS`（其报告 `llmtier-module-test-report-2026-10-02-02` 判 Gate「接受」）。**但该处置只是缓解，不是根除**：替身仍以 `Content-Length` 声明长度并在单条连接上写完整个 2 MiB body，写侧与真实流式上游形态不同；缺陷条件（间歇性不推进）依然成立，因此该 Run 的全绿**不构成缺陷已消除的证据**。run-02 自身也留下记录粒度缺口：其 `test-run.env` 同样只有 8 个字段（无 `pythonpath`/退出码/`finished_at`）。

**1.3.3 `run-20261002-03`（RED，证明 02 的「修复」只是缓解）**——未再改替身即整批复跑，**同一 flake 再次复现**：`artifacts/junit.xml` 的 failure 落在 `OversizeTests::test_service_remains_healthy_after_oversize`（耗时 **60.126s**，同样 `503 provider_unavailable` / `TimeoutError`），`artifacts/pytest.log` 末行 `1 failed, 353 passed in 162.14s (0:02:42)`，`release_blocking=true`。**该 Run 的 `test-run.env` 已含 harness 补录的四字段**（`pythonpath=src`、`exit_code=1`、`pytest_exit_code=1`、`finished_at=2026-10-02T09:25:57Z`）。需同时如实记录一处**证据内部不一致**：run-03 的 `MT-INF-015.json` 与 `case-status.json.cases` 记 `PASS`（代表节点 `test_two_megabyte_output_normalized` 通过，0.515s），而 `counts.FAIL=1`、`release_blocking=true`（失败发生在同 Case 的另一个测试函数上）——成因是 `tools/test_report.py::build_report` 以 `case_id` 为键收敛、Case 级状态只保留最后一个被采集的测试函数（详见 §4.2、§6.2）。

**1.3.4 `run-20261002-04`（GREEN，替身根除）**——把 ENV-3 替身改为**真实流式上游形态**：`Handler._send` 统一发 `Transfer-Encoding: chunked` + `Connection: close`，body 按 **16 KiB 分片**逐片写出并 `flush()`，末尾补 `0\r\n\r\n` 终止块；写侧异常（对端已关闭）不再挂在 handler 上。整批复跑结果：`artifacts/junit.xml` `tests=354 failures=0 errors=0 skipped=0 time=102.520`，`artifacts/pytest.log` 末行 `354 passed in 102.52s (0:01:42)`，`case-status.json` 68/68 `PASS`、`counts.PASS=354 / FAIL=0`、`release_blocking=false`。**该 Run 的判定有效但 pin 有缺口**：替身 chunked 化与 harness 四字段补录当时仍在工作树未提交，`git_commit=f83f8da` 不含这些修复（其报告 §2/§4.2 已如实登记，§4.1 沿用）。

**1.3.5 `run-20261002-05`（复跑确认，但 pin 不可采信）**——替身未再改动即整批复跑，`artifacts/junit.xml` `tests=354 failures=0 errors=0 skipped=0 time=102.672`、`artifacts/pytest.log` 末行 `354 passed in 102.67s (0:01:42)`、`case-status.json` 68/68 `PASS`、`release_blocking=false`；本 Run 起逐 Case `MT-*.json` 首次带 `test_functions` 明细（报告生成器修复生效，计划 §7 末条 (b)）。**但其 `test-run.env.git_commit=f83f8da`，而执行树含未提交的 ENV-3 替身 chunked 化、`run_harness.sh` 四字段补录与 `tools/test_report.py` 修复**——pin 与执行树不一致，因此**不可作最终 pin 依据**，也未为其生成报告实例（其未决项已由 run-06 报告关闭，本报告不重开）。

**1.3.6 `run-20261002-06`（68 Case 基线的可采信 Run）**——在上述三处修复全部入库（提交 `a1cb672`，`fix(test-harness): 根除 MT-INF-015 flake、修 Case 级状态覆盖、补 Run 记录字段`）后整批复跑。**pin 自洽性**：`test-run.env.git_commit=a1cb672b6a7c5892a3dbf61f96d0315486fc6e73` 恰为执行时的 `HEAD`，执行树干净。运行结果：`tests=354 failures=0 errors=0 skipped=0 time=102.515`，`case-status.json` 68/68 `PASS`、`counts.PASS=354 / FAIL=0`、`release_blocking=false`。其定稿报告 `llmtier-module-test-report-2026-10-02-06` 已判 Gate 闭合，作为 68 Case 基线的历史记录保留（§4.1）。

**1.3.7 `run-20261002-07`（覆盖补齐后首个 371/72 Run，但 pin 不可采信）**——在「反向核对补齐组装覆盖缺口」的 4 个新脚本（`MT-MGMT-012/013/014`、`MT-INF-020`）、`MT-MGMT-005` 扩充与 `src/inference/providers/openai.py` 修复所在的工作树上执行：`artifacts/junit.xml` `tests=371 failures=0 errors=0 skipped=0 time=113.149`，`artifacts/pytest.log` 末行 `371 passed in 113.15s (0:01:53)`，`case-status.json` 72/72 `PASS`、`counts.PASS=371 / FAIL=0`、`release_blocking=false`。**但其 `test-run.env.git_commit=998d879` 不含执行时实际生效的新脚本与 openai 修复**（二者由 `eb62302` 才提交）——pin 与执行树不一致（与 run-05 同类），因此**不可作最终 pin 依据**，也未为其生成报告实例。其对应的计划 §10 未决项已由 run-08 报告关闭（§4.3）。

**1.3.8 `run-20261002-08`（95 分母/72 Case 首个 Gate 闭合 Run）**——在新脚本与 openai 修复全部入库（提交 `eb62302`，`test(module): 反向核对补齐 5 个组装覆盖缺口（分母 91→95，Case 68→72）`；以及 `e27dca9`，`docs(module-test): 修正反向核对补齐的计数、VRC 追溯与计划同步`）后整批复跑。pin 自洽性：`test-run.env.git_commit=e27dca9d7bc04a4bbc91e2b34d661298c25c2f88` 为执行时的 `HEAD`，工作树无未提交改动。运行结果：`artifacts/junit.xml` `tests=371 failures=0 errors=0 skipped=0 time=113.159`，`case-status.json` 72/72 `PASS`、`counts.PASS=371 / FAIL=0`、`release_blocking=false`。其定稿报告 `llmtier-module-test-report-2026-10-02-08` 判 Gate 闭合，作为历史记录保留（§4.1）；该报告的 §3.2/§6.2 逐 Case 测试函数数列有 3 处誊写偏差（`MT-INF-020`/`MT-MGMT-012`/`MT-MGMT-013` 记 5/6/8，按其自身 `artifacts/junit.xml` 复算应为 2/3/5），本报告按本 Run 证据修正并登记（§4.2）。本 Run 的被测面与该 pin 逐字一致（零差异，§1.2），run-08 的全部结果由本 Run 复跑确认。

**1.3.9 `run-20261003-01`（章节重编号后复跑，最终 Run，本报告对象）**——在三层测试文档按 STD `f073396` 连续编号规则完成章节重编号（提交 `851d172`；前置 `11bf928` 修正 24 份 case 文档 §1 覆盖 ID）后整批复跑。**pin 自洽性（本 Run 最重要的证据属性）**：`test-run.env.git_commit=851d17246ad7dc01965c131abf43fc01f9eaf3cb` 恰为执行时的 `HEAD`，且 `git status --porcelain` 对 `src/`、`tests/module/cases`、`tests/common/`、`tools/`、`pyproject.toml` 均为空（唯一未跟踪项是本 Run 自己的证据目录 `tests/module/reports/run-20261003-01/`），即**被测树与 pin 逐字一致，证据可采信**。运行结果：`artifacts/junit.xml` `tests=371 failures=0 errors=0 skipped=0 time=112.963`，`artifacts/pytest.log` 末行 `371 passed in 112.96s (0:01:52)`，`case-status.json` 72/72 `PASS`、`counts.PASS=371 / FAIL=0`、`release_blocking=false`；`MT-INF-015` 的三个测试函数耗时 0.522s / 0.529s / 0.521s（无一进入 60s 量级），`MT-INF-020` 代表节点 1.017s、`MT-MGMT-013` 代表节点 1.018s、`MT-MGMT-012` 0.526s、`MT-MGMT-014` 0.517s，均正常。**与 run-08 的一致性非巧合**：`git diff --stat e27dca9..851d172 -- src/ tests/module/cases tests/common/ tools/ pyproject.toml` 为空（差异全部在 `docs/` 与各 Run 证据），本 Run 是资产未变的重编号后复跑，371/371 与 72/72 `PASS` 复跑成立，Gate 判闭合（§1.4、§7）。

**1.3.10 缺陷不是产品缺陷；产品的超时行为正确**——读阶段 60s 无进展即返回 503 `provider_unavailable`，是 `stream_idle_timeout`（默认 60s）对「已建连但长期无字节进展的上游」的设计行为，**与方案 §2.3 c1/c2 的病态设定一致**（`MT-INF-013` stall/hang、`MT-INF-014` 慢速 trickle 均按此命中并 `PASS`）。缺陷位于**测试替身的写侧**（ENV-3 `FakeUpstream`），不是 `src/` 的读侧：`src/inference/providers/openai.py` 的读路径在本 Run 面对 2 MiB chunked 流 0 失败。因此 `D-MT-INF-015-1` 记为 **CLOSED（根因在测试替身，非产品）**，且**不改判产品的超时语义、不下调该超时**。

**1.3.11 旧 Run 证据全部保留**——按计划 §7「重跑生成新 Run，不覆盖旧失败」：`tests/module/reports/run-20261002-01/`…`-08/` 八个目录（含各自 `MT-*.json`、`case-status.json`、`test-run.env`、`artifacts/{junit.xml,pytest.log}`）**本交付未改动其中任何证据文件**；`-02/`、`-04/`、`-06/`、`-08/` 的 `module-test-report.md` 及其 `module-test-report.metadata.json`（`document_id` 分别为 `llmtier-module-test-report-2026-10-02-02`、`-2026-10-02-04`、`-2026-10-02-06`、`-2026-10-02-08`）作为历史记录保留、不改写。本报告的 `document_id` 带 Run 后缀 `-2026-10-03-01`，遵循「每 Run 一份报告、一个带 Run 后缀的 id」的仓库惯例；`Supersedes: none`（不做历史报告的替代声明）。

**1.3.12 复现率证据（分两类，标注证据等级，不混用）**

| 证据 | 内容 | 等级 |
|---|---|---|
| 持久化 Run 证据 | run-01 `test_two_megabyte_output_normalized` 60.133s `FAIL`；run-03 `test_service_remains_healthy_after_oversize` 60.126s `FAIL`；run-04/05/06 三轮连续 354/354 `PASS`，run-07/08 两轮 371/371 `PASS`，本 Run（`run-20261003-01`）371/371 `PASS`，`MT-INF-015` 三个函数均 0.52s 级 | **权威**（`test-run.env` / `case-status.json` / `artifacts/`） |
| 分诊期观测（**不是 Run 证据**，未落证据目录） | 纯 `http.client` 直连 2 MiB 体 30/30 稳定、`urllib` 4/30 失败 → 定位在替身**写侧**；chunked 替身下产品路径 20 轮 0 失败、纯客户端读 60 次 0 stall-or-fail | **参考**（可复现，但不在 Run 证据树内） |

- **诚实限定**：上述分诊数字来自缺陷定位期的临时探针，**不在 Run 证据树内**，故只作**归因线索**标注，不作为关闭判据。`D-MT-INF-015-1` 的关闭依据是持久化 Run 证据本身：确定根因（ENV-3 替身非流式写形态）＋ 消除根因条件的改动（chunked ＋ 16 KiB 分片，已入库）＋ 新 Run 复跑证据（run-04/05/06 连续三轮零失败 ＋ run-07/08 两轮零失败 ＋ 本 Run 章节重编号后复跑零失败）。该 flake 属负载/时序相关的间歇性现象，**不写「修前 N/N 失败、修后 0/N 成功」这类受控对照数字**（受控复刻在定稿复测中未复现停顿，见 run-04 报告 §1.3.5）。

### 1.4 Gate 达成情况

- **闭合——按计划 §8 给出「接受（模块层闭合）」建议（Gate 建议，非批准）**。闭合分母＝方案 §6 的 **72 个 Case**（非 33 个 VRC），闭合条件＝「全部 72 Case 有 `PASS`」：本 Run **72/72 `PASS`，条件满足**；`FAIL=0`、`NOT_RUN=0`、`BLOCKED=0`、`INVALID=0`（P0 硬门、分支/组合/迁移覆盖达标门、注入类方法命中门、异常/错误矩阵封闭门均满足，见 §7）。
- **层级边界（必须随结论一起读）：module PASS ≠ system PASS**；**下层单元 PASS 不关闭本层**（本层分母独立来自模块设计 §9/§14 与 `src/` 分支），**本层 PASS 不关闭上层**（wire 互操作、OpenAPI 端到端一致性、真实上游 provider 协议、浏览器 E2E、性能耐久由 `llmtier-system-test-scheme` 承接）（计划 §8）。

## 2. 被测基线与实际环境

- 实际基线（与计划对照）——制品 pin，取自 `test-run.env`（本 Run 共 **12** 个字段，逐字段原样引用）：
  - `run_id`：`run-20261003-01`；`layer`：`MODULE`；`started_at`：`2026-10-03T04:19:32Z`；`finished_at`：`2026-10-03T04:21:25Z`。
  - `git_commit`：`851d17246ad7dc01965c131abf43fc01f9eaf3cb`（`case-status.json.git_commit` 同值；72 份 `MT-*.json` 的 `git_commit` 全部同值）。
  - `schema_version`：`2`（被测 DB schema 版本；`case-status.json` 另记 `schema_version_db: "2"` 与之一致；其顶层 `schema_version: 1` 是报告产物的**文件格式版本**，同名异义，非偏差）。
  - `openapi_version`：`0.3-simplified-candidate.8`（`case-status.json` 同值）。
  - `command`：`python3 -m pytest --junitxml=tests/module/reports/run-20261003-01/artifacts/junit.xml tests/module/cases`。
  - `pythonpath`：`src`；`python`：`3.14.3 (arm64)`。
  - `exit_code`：`0`；`pytest_exit_code`：`0`（与 `artifacts/pytest.log` 末行 `371 passed`、`case-status.json.release_blocking=false` 三方一致）。
  - 实测环境（`artifacts/pytest.log` 首部）：`platform darwin`、`Python 3.14.3`、`pytest-9.1.0`、`pluggy-1.6.0`、`plugins: anyio-4.13.0`、`configfile: pyproject.toml`、`rootdir: /Users/ben/work/LLMTier`。
  - `case-status.json.generated_at`：`2026-10-03T04:21:25Z`（＝`finished_at`）；`artifacts/junit.xml` testsuite `timestamp="2026-10-03T12:19:32.549385+08:00"`、`hostname="192.168.1.8"`（与 `started_at` 的 UTC 值同一时刻）。
- **harness 四字段的落证历史（如实记录，不给旧 Run 补造）**：`tests/common/harness/run_harness.sh` 补录了 `pythonpath` / `exit_code` / `pytest_exit_code` / `finished_at`（计划 §7 要求 Run 记录含命令、版本、`PYTHONPATH`、pytest stdout/退出码），已随 `a1cb672` 入库。九个 Run 的实际落证情况：

  | Run | `pythonpath` | `exit_code` | `pytest_exit_code` | `finished_at` | 字段总数 |
  |---|---|---|---|---|---|
  | `run-20261002-01` | 无 | 无 | 无 | 无 | 8 |
  | `run-20261002-02` | 无 | 无 | 无 | 无 | 8 |
  | `run-20261002-03` | `src` | `1` | `1` | `2026-10-02T09:25:57Z` | 12 |
  | `run-20261002-04` | `src` | `0` | `0` | `2026-10-02T09:42:14Z` | 12 |
  | `run-20261002-05` | `src` | `0` | `0` | `2026-10-02T09:54:19Z` | 12 |
  | `run-20261002-06` | `src` | `0` | `0` | `2026-10-02T09:59:37Z` | 12 |
  | `run-20261002-07` | `src` | `0` | `0` | `2026-10-02T12:56:12Z` | 12 |
  | `run-20261002-08` | `src` | `0` | `0` | `2026-10-02T14:00:46Z` | 12 |
  | **`run-20261003-01`** | `src` | `0` | `0` | `2026-10-03T04:21:25Z` | 12 |

  即：**run-01 与 run-02 的 `test-run.env` 无这四个字段（记录粒度缺口，其退出码事实只能由 `artifacts/pytest.log` 与 `release_blocking` 间接判定）；run-03 起（含 run-04…08 与本 Run）四字段齐备**。旧 Run 的字段缺失**不补写、不追认**。
- 设计/模块基线（方案 §2，报告不预填结果、只引用版本）：M001 `http-api` v0.1.0-draft.2 / ISD `http-api-isd`；M002 `web-ui` v0.1.0-draft.2 / `web-ui-isd`；M003 `inference` v0.1.0-draft.1 / `inference-isd`；M004 `management` v0.1.0-draft.3 / `management-isd`；M005 `observability` v0.1.0-draft.6 / `observability-isd`；M006 `libdiag` v0.1.0-draft.6 / `libdiag-isd`；M007 `util` v0.1.0-draft.2 / `util-isd`；M008 `log` v0.1.0-draft.1 / `log-isd`。
- 与计划 §2 基线一致：被测为 `tests/module/cases` 全量；模块层为**本机隔离套件**——provider 为进程内 `FakeAdapter` 与 loopback `FakeUpstream`，HTTP 仅绑 `127.0.0.1:0` 临时端口（ENV-2），不触 LAN/m5air/真实 provider（方案 §3/§4）。本层 `127.0.0.1` 仅为 loopback 测试 HTTP 实例与占位 provider endpoint（不真正拨号到生产 provider），TS-003 的 LAN IP 约束在系统/契约层强制（计划 §9）。
- 环境偏差及影响：
  - **被测树与 pin 逐字一致（本 Run 无偏差）**：`git_commit=851d172` 即执行时 `HEAD`；`git status --porcelain src/ tests/module/cases tests/common tools/ pyproject.toml` 输出为空，唯一未跟踪项为本 Run 自己的证据目录。故产品代码、测试资产、报告生成器三者均被该 pin 完整覆盖（**本 Run 被测面与 run-08 pin `e27dca9` 之间零差异**，§1.2/§1.3.9）。
  - **跨 Run 差异已核实**：`git diff --stat e27dca9..851d172` 在被测面（`src/`、`tests/module/cases`、`tests/common/`、`tools/`、`pyproject.toml`）为空；差异全部在 `docs/`（`11bf928` 修正 24 份 case 文档 §1 覆盖 ID、`851d172` 重锁 STD `f073396` 并重排三层测试文档章节编号）与各 Run 证据。因此本 Run 与 run-08 的逐批次、逐 Case 函数数完全一致，属**复跑**而非资产变更。
  - **替身资产自检状态**：计划 §4 记 ENV-3/ENV-4 契约 `llmtier-unit-fakes` 为 `Ready（契约已建；自检 Run 待录制）`、`Unverified`；本 Run 使用其 `AppFixture`/`FakeAdapter` 与各测试模块本地 `FakeUpstream`/`FakeResponse` stub，**资产自检 Run 仍未录制**（不改变本 Run 判定，登记于 §6.3/§8）。
  - **文档版本漂移（不影响本 Run 判定）**：方案 §6.6 的 Run 现状描述仍记「共 **8** 个 Run（`…-01`…`-08`）」且以 run-08 为「最终 Run」——**该计数与真实 Run 数（9）不一致**，本 Run 未列入；同段「case 文档 `0.1.0-draft.1`」措辞也落后于现行 72 份 `0.1.0-draft.2`。本报告不动方案（交付边界），如实登记于 §4.2/§6.3/§8；计划侧的同一批引用（§1/§3/§7/§10）已随本次交付同步到 `run-20261003-01`（计划版本升 `0.1.0-draft.14`）。
- 证据版本绑定与待重验：
  - 本报告结论仅对「被测产品树＝`851d172`（被测面与 `e27dca9` 零差异，含 `src/inference/providers/openai.py` 的 adapter 重取修复）」＋ ENV-3 替身 chunked 形态 ＋ `schema_version=2` ＋ `openapi_version=0.3-simplified-candidate.8` ＋ Python `3.14.3` 有效；`src/<module>/`、落库 schema、`interfaces/` 或 `pyproject.toml` 收集规则变更后须重跑并标「待重验」，不同基线的结果不合并统计。
  - 本 Run 无 `FAIL` 需保持 RED；其相对 run-08 的关系是**章节重编号后、资产零差异的复跑确认**（§1.3.9）。

## 3. 逐 Case 执行记录

本 Run 一条命令串行执行 `tests/module/cases` 全量，收集 371 个 pytest 测试函数。§3.1 按计划 §5.1 的模块批次汇总，§3.2 按方案 §6 的 72 个 Case 逐条列出。**每个 Case 的 Verdict 逐条读自 `tests/module/reports/run-20261003-01/<Case ID>.json` 的 `status` 字段**；逐测试函数的机器记录见 `artifacts/junit.xml` 与 `artifacts/pytest.log`。

> **粒度注（371 vs 72）**：方案 §6 的设计分母是 **72 个 Case**；`371` 是这 72 个 Case 的测试函数展开数（1–12 个/Case）。`case-status.json` 的 `counts` 按**测试函数**计数（`PASS=371`），其 `cases` 段按 **Case ID** 给出 72 条记录（72 `PASS`）。
> **记录口径（承 run-06 工具修复）**：`tools/test_report.py` 现按 `case_id` 聚合后**取最严重状态**作为 Case 级 `status`，并为**多测试函数**的 Case 落 `test_functions` 明细。因此：① Case 级 `PASS` 现在蕴含「该 Case 全部测试函数均非 `FAIL`/`BLOCKED`/`INVALID`」，run-03 那种「`counts.FAIL=1` 而 `cases[…].status=PASS`」的自相矛盾不可能再出现；② `case-status.json.cases.<Case ID>` 与 `MT-<Case ID>.json` 的 `node_id`/`time_seconds` 仍只登记该 Case 的**一个代表测试函数**（同分值时取首个），**不是该 Case 的耗时合计**（如 `MT-INF-015` 记 0.522s，而该 Case 三个函数在 junit 中的耗时合计为 1.572s）；③ `test_functions` 仅在该 Case 有 **>1** 个测试函数时落盘，故 `MT-API-012`（`test_client_disconnect_mid_stream`）与 `MT-API-013`（`test_rst_mid_stream_aborts_without_crash`）两个单函数 Case **无该字段**——这是工具的既定行为而非证据缺失，两者的函数级结果仍完整记录在 `node_id`/`status` 与 `artifacts/junit.xml` 中。72 个 Case 的全部 371 个测试函数均在 `artifacts/junit.xml` 中有独立记录。

### 3.1 按模块 / 批次分组（方案 §6 × 计划 §5.1）

| 批次 | 模块（M-id） | Case 范围 | 分母层 / 分母行（方案 §6.7） | Case 数 | 测试函数数 | 执行状态 | Verdict | Run ID / 证据 |
|---|---|---|---|---|---|---|---|---|
| B1 | `util`（M007） | MT-UTIL-001..005 | ① MT-UTIL-001/002；②×3；④ T12-T13 | 5 | 19 | 全部执行 | PASS 5/5 | run-20261003-01 |
| B2 | `log`（M008） | MT-LOG-001..003 | ① MT-LOG-001；②×2；③ K10；④ T14 | 3 | 17 | 全部执行 | PASS 3/3 | run-20261003-01 |
| B3 | `http-api`（M001） | MT-API-001..013 | ①×3；②×9；③ K1-K2 | 13 | 51 | 全部执行 | PASS 13/13 | run-20261003-01 |
| B4 | `inference`（M003） | MT-INF-001..020 | ①×4；②×16；③ K4-K5；④ T1-T5 | 20 | 71 | 全部执行 | PASS 20/20 | run-20261003-01 |
| B5 | `management`（M004） | MT-MGMT-001..014 | ①×8；②×6；③ K3/K6-K7；④ T6-T8 | 14 | 75 | 全部执行 | PASS 14/14 | run-20261003-01 |
| B6 | `observability`（M005） | MT-OBS-001..004 | ①×1；②×3；④ T9 | 4 | 31 | 全部执行 | PASS 4/4 | run-20261003-01 |
| B7 | `libdiag`（M006） | MT-DIAG-001..007 | ①×2；②×5；③ K4/K8-K9；④ T9-T11 | 7 | 46 | 全部执行 | PASS 7/7 | run-20261003-01 |
| B8 | `web-ui`（M002） | MT-UI-001..006 | ①×2；②×4 | 6 | 61 | 全部执行 | PASS 6/6 | run-20261003-01 |
| BALL | 全量回归（8 模块） | 全部 72 Case | 95 条分母全覆盖 | 72 | 371 | 全部执行 | **PASS 72 / FAIL 0** | run-20261003-01 |

> Case 数与测试函数数逐批次取自 `artifacts/junit.xml`（按 `classname` 前缀 `MT-<OBJ>-<NNN>` 聚合）与 72 份 `MT-*.json`；合计 72 Case / 371 测试函数与套件 `tests="371"` 一致。P0 41 个 Case 全部 `PASS`、P1 31 个 Case 全部 `PASS`；分类分布（方案 §6.6）：negative 21 / boundary 13 / normal 12 / recovery 17 / security 6 / concurrency 3；本报告按逐 Case `status` 复算的分布与之一致。

### 3.2 逐 Case 明细（72 条，Verdict 取自 `run-20261003-01/MT-*.json`）

| Case ID | 模块 | 分母层（方案 §6） | 分类 | 优先级 | Verdict | Run 证据 | 测试函数数 |
|---|---|---|---|---|---|---|---|
| MT-UTIL-001 | M007 util | ① | boundary | P0 | PASS | `MT-UTIL-001.json` | 4 |
| MT-UTIL-002 | M007 util | ①（④T12） | recovery | P0 | PASS | `MT-UTIL-002.json` | 4 |
| MT-UTIL-003 | M007 util | ② | boundary | P0 | PASS | `MT-UTIL-003.json` | 4 |
| MT-UTIL-004 | M007 util | ② | recovery | P0 | PASS | `MT-UTIL-004.json` | 4 |
| MT-UTIL-005 | M007 util | ②（④T13） | recovery | P1 | PASS | `MT-UTIL-005.json` | 3 |
| MT-LOG-001 | M008 log | ① | security | P0 | PASS | `MT-LOG-001.json` | 6 |
| MT-LOG-002 | M008 log | ②（③K10） | security | P0 | PASS | `MT-LOG-002.json` | 7 |
| MT-LOG-003 | M008 log | ②（④T14） | negative | P1 | PASS | `MT-LOG-003.json` | 4 |
| MT-API-001 | M001 http-api | ① | normal | P0 | PASS | `MT-API-001.json` | 4 |
| MT-API-002 | M001 http-api | ① | normal | P1 | PASS | `MT-API-002.json` | 4 |
| MT-API-003 | M001 http-api | ① | security | P1 | PASS | `MT-API-003.json` | 4 |
| MT-API-004 | M001 http-api | ② | negative | P0 | PASS | `MT-API-004.json` | 4 |
| MT-API-005 | M001 http-api | ② | negative | P0 | PASS | `MT-API-005.json` | 4 |
| MT-API-006 | M001 http-api | ②（③K1） | security | P0 | PASS | `MT-API-006.json` | 6 |
| MT-API-007 | M001 http-api | ② | boundary | P0 | PASS | `MT-API-007.json` | 5 |
| MT-API-008 | M001 http-api | ②（③K2） | recovery | P0 | PASS | `MT-API-008.json` | 3 |
| MT-API-009 | M001 http-api | ② | security | P1 | PASS | `MT-API-009.json` | 4 |
| MT-API-010 | M001 http-api | ② | normal | P1 | PASS | `MT-API-010.json` | 5 |
| MT-API-011 | M001 http-api | ②（③K1） | security | P0 | PASS | `MT-API-011.json` | 6 |
| MT-API-012 | M001 http-api | ② | recovery | P0 | PASS | `MT-API-012.json` | 1 |
| MT-API-013 | M001 http-api | ② | recovery | P1 | PASS | `MT-API-013.json` | 1 |
| MT-INF-001 | M003 inference | ① | normal | P0 | PASS | `MT-INF-001.json` | 3 |
| MT-INF-002 | M003 inference | ① | boundary | P0 | PASS | `MT-INF-002.json` | 6 |
| MT-INF-003 | M003 inference | ①（④T1,T2,T3） | recovery | P0 | PASS | `MT-INF-003.json` | 5 |
| MT-INF-004 | M003 inference | ①（④T4） | concurrency | P0 | PASS | `MT-INF-004.json` | 3 |
| MT-INF-005 | M003 inference | ② | negative | P0 | PASS | `MT-INF-005.json` | 4 |
| MT-INF-006 | M003 inference | ②（③K5） | negative | P0 | PASS | `MT-INF-006.json` | 4 |
| MT-INF-007 | M003 inference | ②（④T5） | concurrency | P0 | PASS | `MT-INF-007.json` | 5 |
| MT-INF-008 | M003 inference | ②（③K4） | recovery | P0 | PASS | `MT-INF-008.json` | 5 |
| MT-INF-009 | M003 inference | ②（④T1） | recovery | P0 | PASS | `MT-INF-009.json` | 2 |
| MT-INF-010 | M003 inference | ② | boundary | P0 | PASS | `MT-INF-010.json` | 5 |
| MT-INF-011 | M003 inference | ② | recovery | P1 | PASS | `MT-INF-011.json` | 2 |
| MT-INF-012 | M003 inference | ② | recovery | P1 | PASS | `MT-INF-012.json` | 5 |
| MT-INF-013 | M003 inference | ② | recovery | P0 | PASS | `MT-INF-013.json` | 3 |
| MT-INF-014 | M003 inference | ② | recovery | P1 | PASS | `MT-INF-014.json` | 2 |
| MT-INF-015 | M003 inference | ② | boundary | P1 | PASS | `MT-INF-015.json` | 3 |
| MT-INF-016 | M003 inference | ② | recovery | P0 | PASS | `MT-INF-016.json` | 2 |
| MT-INF-017 | M003 inference | ② | negative | P0 | PASS | `MT-INF-017.json` | 4 |
| MT-INF-018 | M003 inference | ② | concurrency | P1 | PASS | `MT-INF-018.json` | 2 |
| MT-INF-019 | M003 inference | ② | negative | P1 | PASS | `MT-INF-019.json` | 4 |
| MT-INF-020 | M003 inference | ② | normal | P0 | PASS | `MT-INF-020.json` | 2 |
| MT-MGMT-001 | M004 management | ①（④T6） | normal | P0 | PASS | `MT-MGMT-001.json` | 4 |
| MT-MGMT-002 | M004 management | ① | negative | P0 | PASS | `MT-MGMT-002.json` | 5 |
| MT-MGMT-003 | M004 management | ① | boundary | P0 | PASS | `MT-MGMT-003.json` | 4 |
| MT-MGMT-004 | M004 management | ① | normal | P1 | PASS | `MT-MGMT-004.json` | 5 |
| MT-MGMT-005 | M004 management | ① | negative | P1 | PASS | `MT-MGMT-005.json` | 7 |
| MT-MGMT-006 | M004 management | ②（④T7） | recovery | P0 | PASS | `MT-MGMT-006.json` | 7 |
| MT-MGMT-007 | M004 management | ②（③K6 ④T8） | negative | P0 | PASS | `MT-MGMT-007.json` | 9 |
| MT-MGMT-008 | M004 management | ② | negative | P0 | PASS | `MT-MGMT-008.json` | 6 |
| MT-MGMT-009 | M004 management | ②（③K3） | boundary | P0 | PASS | `MT-MGMT-009.json` | 6 |
| MT-MGMT-010 | M004 management | ②（③K7） | negative | P1 | PASS | `MT-MGMT-010.json` | 6 |
| MT-MGMT-011 | M004 management | ② | negative | P1 | PASS | `MT-MGMT-011.json` | 3 |
| MT-MGMT-012 | M004 management | ① | negative | P0 | PASS | `MT-MGMT-012.json` | 3 |
| MT-MGMT-013 | M004 management | ① | negative | P1 | PASS | `MT-MGMT-013.json` | 5 |
| MT-MGMT-014 | M004 management | ① | negative | P1 | PASS | `MT-MGMT-014.json` | 5 |
| MT-OBS-001 | M005 observability | ① | normal | P1 | PASS | `MT-OBS-001.json` | 5 |
| MT-OBS-002 | M005 observability | ②（④T9） | normal | P1 | PASS | `MT-OBS-002.json` | 9 |
| MT-OBS-003 | M005 observability | ② | boundary | P1 | PASS | `MT-OBS-003.json` | 10 |
| MT-OBS-004 | M005 observability | ② | recovery | P1 | PASS | `MT-OBS-004.json` | 7 |
| MT-DIAG-001 | M006 libdiag | ①（④T9） | boundary | P1 | PASS | `MT-DIAG-001.json` | 8 |
| MT-DIAG-002 | M006 libdiag | ① | negative | P0 | PASS | `MT-DIAG-002.json` | 6 |
| MT-DIAG-003 | M006 libdiag | ②（③K8） | negative | P0 | PASS | `MT-DIAG-003.json` | 9 |
| MT-DIAG-004 | M006 libdiag | ②（④T10,T11） | negative | P0 | PASS | `MT-DIAG-004.json` | 6 |
| MT-DIAG-005 | M006 libdiag | ②（③K4） | boundary | P1 | PASS | `MT-DIAG-005.json` | 6 |
| MT-DIAG-006 | M006 libdiag | ②（③K9） | boundary | P1 | PASS | `MT-DIAG-006.json` | 6 |
| MT-DIAG-007 | M006 libdiag | ② | recovery | P1 | PASS | `MT-DIAG-007.json` | 5 |
| MT-UI-001 | M002 web-ui | ① | normal | P1 | PASS | `MT-UI-001.json` | 9 |
| MT-UI-002 | M002 web-ui | ① | normal | P0 | PASS | `MT-UI-002.json` | 12 |
| MT-UI-003 | M002 web-ui | ② | negative | P0 | PASS | `MT-UI-003.json` | 11 |
| MT-UI-004 | M002 web-ui | ② | normal | P1 | PASS | `MT-UI-004.json` | 10 |
| MT-UI-005 | M002 web-ui | ② | boundary | P1 | PASS | `MT-UI-005.json` | 9 |
| MT-UI-006 | M002 web-ui | ② | negative | P1 | PASS | `MT-UI-006.json` | 10 |

> 72 份 `MT-*.json` 的 `status` 全为 `PASS`、`reason` 字段全为空串（无失败/阻塞/无效原因），`artifacts` 与 `redactions` 均为空数组，`started_at` 全部为 `2026-10-03T04:19:32Z`，`git_commit` 全部为 `851d17246ad7dc01965c131abf43fc01f9eaf3cb`。「测试函数数」列**取自本 Run `artifacts/junit.xml` 按 Case 聚合复算（非估算、不承抄前序报告）**，与 `MT-*.json` 的 `test_functions` 条目数一致（两个单函数 Case 除外，见本节粒度注③）；分类/优先级/分母层列与方案 §6.1–§6.4 清单逐条复算一致（0 处偏差）。`MT-MGMT-005` 因 `eb62302` 的 `atomic=False` 审计例外扩充为 7 个测试函数（原 5 个）；`MT-MGMT-012/013/014`、`MT-INF-020` 的本 Run 函数数分别为 **3/5/5/2**——该列与 run-08 报告的誊写值（6/8/5/5）不同，系 run-08 报告的誊写错误，本 Run 与 run-08 的 junit 复算一致（登记见 §4.2）。

### 3.3 副作用与清理（逐 Case 口径）

| 项目 | 结果已知性 | 副作用 | 清理状态 |
|---|---|---|---|
| 全部 72 Case（ENV-1 组装隔离库为主） | 可独立判定：经被测模块公开入口驱动，断言 wire 信封 / 公开返回 / 落库行 + 关键内部 seam | 每 Case 在 `setUp` 新建 `tempfile.TemporaryDirectory` + 新 SQLite + 真实组装栈（`tests/common/fakes.py::AppFixture`）；初态经公开入口播种（方案 §2 规则 1） | 每 Case `tearDown` 调 `AppFixture.close()`（`store.close()` + `temp.cleanup()`）销毁临时目录；Case 间无共享可变状态 |
| 经 HTTP 的 Case（ENV-2，`MT-API-*`/`MT-OBS-*`/经 HTTP 的 `MT-MGMT-*`/`MT-DIAG-*`） | 可独立判定（真实 socket + 真实 `ThreadingHTTPServer` handler 栈） | loopback `127.0.0.1:0` 随机端口上的真实请求 | `tearDownClass`/`tearDown` 调 `server.shutdown()` + `server_close()` + `AppFixture.close()`（`tests/module/cases/support/http_env.py`） |
| `MT-INF-*`（ENV-3 loopback `FakeUpstream` / `FakeAdapter`） | 可独立判定（真实 `OpenAIProvider` 传输 + 边界外替身） | loopback 临时端口 + 经公开 Registry 入口接线的假上游 | `InferenceEnv.tearDown` 停上游；`AppFixture.close()` 销毁临时库。替身每响应以 `Connection: close` 收尾并置 `close_connection=True`，连接不再复用，端口随 `stop()`/`shutdown()` 释放 |
| 存储面注入 Case（`MT-UTIL-004/005`、`MT-DIAG-007`、`MT-OBS-004`、`MT-INF-009`） | 可独立判定（真实写失败/损坏/回滚） | 仅作用于该 Case 自己的临时库（`DROP TABLE`、损坏库、迁移中途失败） | 随临时目录销毁；无跨 Case 残留 |
| 传输病态 Case（`MT-API-012/013`） | 可独立判定（真实客户端 `close()` / `SO_LINGER 0` RST） | 真实 socket 中途断开 | 两 Case 自身取 `/dev/fd` 基线并断言无泄漏；`tearDownClass` 关停 loopback 实例释放端口 |
| 配置变更接线 Case（`MT-INF-020`、`MT-MGMT-012`） | 可独立判定（经公开入口变更 endpoint/secret_ref 或禁用三态后请求） | 仅作用于该 Case 自己的临时库与 loopback 上游 | 随临时目录销毁；无跨 Case 残留 |
| 本 Run 整体 | 72 Case 串行于单一 pytest 进程 | 不触 LAN / m5air / 真实 provider；无外部共享资源 | 套件 112.963s 结束；未产生需人工清理的持久资源 |

## 4. 偏差、无效执行与重跑

### 4.1 前序 Run 的 FAIL 记录（均已关闭，旧证据原样保留）

| 偏差 / 无效项 | 原因 | 影响 Case | 处置与重跑 Run |
|---|---|---|---|
| **`run-20261002-01` 的 FAIL**：`MT-INF-015` `OversizeTests::test_two_megabyte_output_normalized`，`ApiError: (503, 'provider_unavailable', 'Provider streaming request failed: TimeoutError: timed out')`，节点耗时 60.133s | ENV-3 边界替身 `tests/module/cases/support/upstream.py::Handler._send` 以 `Content-Length` 声明长度并**单次写出整个 2 MiB body**；在 macOS loopback 上间歇性不推进，读侧 60s 无进展 → 回落到流空闲超时 | MT-INF-015（层②，boundary，P1；方案 §2.3 c3） | 首次处置（`f83f8da`）：改为 64 KiB 分块写 + 逐块 `flush()` → 以 `run-20261002-02` 复跑取得全绿，**但为假绿**（替身仍非流式形态） |
| **`run-20261002-03` 的 FAIL**：`MT-INF-015` `OversizeTests::test_service_remains_healthy_after_oversize`，同一 `ApiError`（503 `provider_unavailable` / `TimeoutError`），节点耗时 60.126s | 同一根因未消除（02 的分块 flush 形态仍以 `Content-Length` 单连接大 body 写出），负载下再次复现 | MT-INF-015（同上） | **根除处置**：替身改为 `Transfer-Encoding: chunked` + 16 KiB 分片（真实流式上游形态）→ 以 `run-20261002-04` 复跑，`failures="0"`、354/354 passed、`MT-INF-015` 三函数 0.52s 级（§1.3.4/§6.2）。后续 `run-05`/`run-06` 两轮全量复跑持续为 354/354；修复随 `a1cb672` 入库，pin 覆盖问题在 run-06 消除；扩充资产后 `run-07`/`run-08` 继续 371/371；章节重编号后本 Run 再次 371/371。按计划 §7「重跑生成新 Run，不覆盖旧失败」，`run-20261002-01/` 与 `run-20261002-03/` 的全部原始证据（`MT-INF-015.json`、`case-status.json`、`artifacts/junit.xml`、`artifacts/pytest.log`）**原样保留** |
| `run-20261002-02` 的**假绿**（非 FAIL 记录，但为方法论缺陷） | 以「一次全绿」判定缺陷关闭，未验证替身写形态是否已对齐真实上游；缺陷条件仍成立，故 run-03 复现 | MT-INF-015 所在族 | 已在本报告显式记为**假绿**并给出判据：缺陷关闭须同时具备（a）确定根因、（b）消除根因条件的改动、（c）新 Run 复跑证据；仅（c）不成立。run-04/05/06 三轮零失败 ＋ 入库后 pin 自洽（run-06）＋ run-07/08 两轮零失败 ＋ 本 Run 复跑零失败共同满足三项 |

### 4.2 本 Run 的偏差登记

| 偏差 / 无效项 | 原因 | 影响 Case | 处置与重跑 Run |
|---|---|---|---|
| **证据内部不一致（前序 Run `run-20261002-03`）**：`case-status.json.cases` 记 68/68 `PASS`（含 `MT-INF-015`），而 `counts.FAIL=1`、`release_blocking=true`，junit 的 failure 落在同 Case 的**另一个**测试函数上 | `tools/test_report.py::build_report` 以 `cases[record["case_id"]] = {...}` 收敛，Case 级 `status`/`node_id`/`time_seconds` 只保留该 Case **最后一个被采集**的测试函数；Case 内任一函数失败不会翻转 Case 级状态（`counts` 与 `release_blocking` 仍按测试函数统计，故不受影响） | 记录口径影响全部 68 Case（工具侧，非产品行为） | **已于 run-06 轮修复**（§6.2）：Case 级取最严重状态 ＋ 多函数 Case 落 `test_functions`；本 Run 证据无该不一致（`counts.FAIL=0` 与 `cases` 72 `PASS` 一致，`artifacts/junit.xml` `failures="0"`）。**旧 Run（`-01`/`-03`）的 `case-status.json`/`MT-*.json` 不追溯改写** |
| **前序 Run `run-20261002-05` 的 pin 与执行树不一致**：`test-run.env.git_commit=f83f8da`，而执行树含未入库的 ENV-3 替身 chunked 化、`run_harness.sh` 四字段补录、`tools/test_report.py` 修复 | 修复未入库即执行 Run（登记于 run-04 报告 §2/§4.2） | 无（`src/` 无未提交改动，产品代码与 pin 一致；替身属测试资产） | **已于 run-06 消除**：三处修复入库为 `a1cb672` 后重跑（run-06）。run-05 证据原样保留，但其 `git_commit` **不作为最终 pin 依据** |
| **前序 Run `run-20261002-07` 的 pin 与执行树不一致**：`test-run.env.git_commit=998d879`，而执行树含未提交的 4 个新脚本（`MT-MGMT-012/013/014`、`MT-INF-020`）、`MT-MGMT-005` 扩充与 `src/inference/providers/openai.py` 修复 | 新脚本与修复未入库即执行 Run（由 `eb62302` 才提交） | 无（这些资产是新增/修复面，产品代码与执行树之间的差异即为该未入库修复） | **已由 run-08 消除并由本 Run 延续**：新脚本与 openai 修复入库为 `eb62302`（并经 `e27dca9` 修正计数/追溯/计划同步）后重跑；本 Run `test-run.env.git_commit=851d172` ＝ 执行时 `HEAD`、工作树无未提交改动（§1.3.9）。run-07 证据原样保留，其 `git_commit` **不作为最终 pin 依据**，也未为其生成报告实例（§4.3） |
| **前序报告（run-08）逐 Case 测试函数数的 3 处誊写偏差**：其 §3.2 与 §6.2 把 `MT-INF-020`/`MT-MGMT-012`/`MT-MGMT-013` 记为 5/6/8 个测试函数，而 run-08 自身 `artifacts/junit.xml` 与本 Run junit 复算均为 **2/3/5**（两 Run 的逐 Case 函数数逐项一致；批次合计 71/75 与总数 371 不受影响） | 报告整理时按文档描述估算、未按 junit 逐 Case 聚合复核 | 仅前序报告的记录列（非证据、非覆盖） | 本报告全部按**本 Run `artifacts/junit.xml` 复算值**登记（§3.2 表注）；run-08 报告及其 metadata **不改写**（旧报告为历史记录，计划 §7 不覆盖原则同样适用于报告产物） |
| **方案 §6.6 的 Run 现状描述过期**：`run-20261002-08` 仍被记为「最终 Run」，且写「共 **8** 个 Run（`…-01`…`-08`）」——与真实 Run 数（9）不一致，本 Run（`run-20261003-01`）未列入；同段「case 文档 `0.1.0-draft.1`」措辞落后于现行 72 份 `0.1.0-draft.2` | 方案文档在本 Run 之后未再同步（章节重编号提交 `851d172` 未含 Run 现状更新） | 无（设计文档不预填 Verdict） | 本交付不改方案（边界约束），如实登记于 §6.3/§8；计划侧同一批引用已随本次交付同步到 `run-20261003-01`（§1/§3/§7/§10，计划升 `0.1.0-draft.14`） |
| **单测试函数 Case 无 `test_functions` 明细**：`MT-API-012`、`MT-API-013` 的 `MT-*.json` 只有 `node_id`/`status`，无 `test_functions` 数组 | `tools/test_report.py::emit_manifests` 仅在 `len(group) > 1` 时落该字段 | 仅这 2 个 Case 的记录形态（非覆盖缺口） | 工具既定行为，不改工具；两 Case 各 1 个测试函数的结果已由 `node_id`/`status=PASS`（代表节点耗时 0.524s / 0.521s）与 `artifacts/junit.xml` 完整落证（§3 粒度注③） |
| **替身资产自检 Run 未录制**（ENV-3/ENV-4 契约 `llmtier-unit-fakes` 为 `Implemented`/`Unverified`） | 资产自检属独立 Gate，尚未安排 | 无 | 登记于 §6.3/§8；不改变本 Run 判定 |
| 无失败（`FAIL`） | 本 Run 72 Case 全 `PASS`，`counts.FAIL=0`、`release_blocking=false`、`junit failures="0"` | — | — |
| 无无效执行（`INVALID`） | 注入类 Case 均以注入生效的可观测后果断言（见 §5.3），未出现「配置但未生效」 | — | — |
| 无 `BLOCKED` / `NOT_RUN` / `SKIP` / `XPASS` | 无环境缺失；72 Case 全部收集并执行，371 个测试函数无 skip/xfail | — | — |
| 重跑历史：8 次 | 模块层共 9 个 Run（`run-20261002-01`…`-08`、`run-20261003-01`）；run-02、run-03、run-04 均因 run-01 的 `MT-INF-015` FAIL 按计划 §7 规则新开 Run，run-05、run-06 分别为工具侧入库前后的复跑与 pin Run，run-07、run-08 为覆盖补齐后入库前后的复跑与首个 Gate 闭合 pin Run，本 Run（`run-20261003-01`）为章节重编号后的最终定稿复跑 | — | 见 §1.3、§4.1 |

### 4.3 计划未决项关闭链与本次同步

- 计划 §10 原列「`run-20261002-07` 报告未生成 ＋ pin 待重跑」为**未决**，已随 run-08 交付关闭：可采信 Run-08 ＝ 371/371 测试函数 `PASS`、72/72 Case `PASS`、`release_blocking=false`、pin `e27dca9` ＝ 执行时 `HEAD` 且工作树干净，其定稿报告 `llmtier-module-test-report-2026-10-02-08` 判 Gate 闭合（历史记录保留）。run-07 因 pin（`998d879`）与执行树不一致**不作最终 pin 依据**，其报告实例不再补齐、证据目录原样保留。
- **本次交付的同步**：三层文档章节按 STD `f073396` 重编号后，以资产零差异的本 Run（`run-20261003-01`）作最终定稿复跑，并出具本报告（`llmtier-module-test-report-2026-10-03-01`）；计划 §1/§3/§7/§10 中「当前 Run／最终报告＝run-20261002-08」的引用同步改为 `run-20261003-01`（共 9 个 Run），计划版本升 `0.1.0-draft.13`→`0.1.0-draft.14`（cover 与 metadata 同步，Last Modified `2026-10-03`）；**方案与 case 文档不动**（方案 §6.6 的 Run 现状漂移如实登记于 §4.2/§6.3/§8，待下一次方案修订同步）。

## 5. 覆盖复算（对照方案分母）

分母权威＝方案 `llmtier-module-test-scheme` v0.1.0-draft.12 §6（四层：① 接口行为 23 ＋ ② 内部分支 48 ＋ ③ 组合 10 ＋ ④ 状态迁移 14 ＝ **95 条**），展开为 §6 的 **72 个 Case**；VRC 只作追溯（方案 §6.5/附录 A），不作分母。分母＝95 条，Case＝72 个，二者不同粒度。

### 5.1 四层分母闭合表

| 分母层 | 分母数（方案 §6.6） | 映射到的 Case 数 | 已执行 Case | 其中 `PASS` | 其中 `FAIL` | 未覆盖（分母无 Case / Case 未执行） |
|---|---|---|---|---|---|---|
| ① 对外接口端到端行为（§6.1） | 23 | 23（1:1） | 23 | 23 | 0 | **0** |
| ② 内部分支（§6.2） | 48 | 48（每分支 1 Case） | 48 | 48 | 0 | **0** |
| ③ 组合行（§6.3 K1–K10） | 10 | 12（含 K1 落地的 `MT-API-011`，其分母计入本层） | 12 | 12 | 0 | **0** |
| ④ 状态迁移（§6.4 T1–T14） | 14 | 13（T1/T2/T3 合并到 `MT-INF-003`＋`MT-INF-009` 等） | 13 | 13 | 0 | **0** |
| **合计** | **95** | **72 个去重 Case** | **72** | **72** | **0** | **0** |

- 粒度说明：层② 48 条 = 方案 §6.2 的 49 行减去 1 条「组合落地 Case」`MT-API-011`（方案 §6.2 尾注：其独自分母计入层③）；因此 23（①）＋ 48（②）＋ 1（`MT-API-011` 归③）＝ 72 个 Case，无重复计分母、无遗漏。
- 逐层未覆盖复核：95 条分母每条的「映射 Case」列（方案 §6.2/§6.3/§6.4/§6.7）在本 Run **全部有对应 Case 且该 Case 已执行并出 `PASS`**；**未覆盖 0 条、无静默消失的分支/组合/迁移**（计划 §8「分支/组合/迁移覆盖达标门」满足）。`G-MT-COVERAGE-1` 修复新增的 4 个 Case 与 `MT-MGMT-005` 扩充均在本 Run 执行并 `PASS`。
- 逐层 Verdict 偏差：**0 条**。层② 的 `M003-超大 response 归一`（方案 §2.3 c3）→ `MT-INF-015` 在本 Run 为 `PASS`（三个测试函数 0.522s / 0.529s / 0.521s）；该行在 run-01（60.133s `FAIL`）与 run-03（60.126s `FAIL`）的失败事实已在 §4.1 登记并关闭，**本 Run 不再是例外行**。

### 5.2 异常/错误注入矩阵封闭核对（方案 §2.3，53 条；Oracle ＝ `src/`）

封闭判据：每行必须映射到 ≥1 个 `MT-*` Case 或具名 Gap；**0 静默缺失**。本 Run 逐行核对结果如下（Verdict 取自对应 `MT-*.json`，本 Run 全部 `PASS`；矩阵行数按方案 §2.3 复算为 (a)37＋(b)8＋(c)8＝53，与方案声明一致）。

**(a) 每个对外 error code（37 条）**

| # | `code` | status（`src/`） | 映射 Case | 本 Run Verdict |
|---|---|---|---|---|
| a1 | `invalid_request` | 400 | `MT-API-007` / `MT-INF-005` / `MT-MGMT-007` / `MT-MGMT-014` | PASS |
| a2 | `unsupported_request` | 400 | `MT-INF-005` / `MT-INF-006` | PASS |
| a3 | `unsupported_field` | 400 | `MT-INF-005` | PASS |
| a4 | `unsupported_model` | 400 | `MT-INF-006` | PASS |
| a5 | `invalid_json` | 400 | `MT-API-007` | PASS |
| a6 | `request_too_large` | 413 | `MT-API-007` | PASS |
| a7 | `unsupported_dimensions` | 400 | `MT-INF-010` | PASS |
| a8 | `authentication_required` | 401 | `MT-API-006` | PASS |
| a9 | `permission_denied` | 403 | `MT-API-006` / `MT-MGMT-009` | PASS |
| a10 | `auth_not_configured` | 503 | `MT-API-006` | PASS |
| a11 | `model_not_found` | 404 | `MT-INF-007` / `MT-MGMT-012` | PASS |
| a12 | `not_found` | 404 | `MT-API-004` / `MT-MGMT-007` / `MT-MGMT-013` | PASS |
| a13 | `resource_conflict` | 409 | `MT-MGMT-007` | PASS |
| a14 | `capability_conflict` | 409 | `MT-MGMT-008` | PASS |
| a15 | `embedding_space_conflict` | 409 | `MT-MGMT-008` | PASS |
| a16 | `fixed_service_level` | 409 | `MT-MGMT-011` | PASS |
| a17 | `resource_in_use` | 409 | `MT-MGMT-007` | PASS |
| a18 | `version_conflict` | 412 | `MT-MGMT-007` | PASS |
| a19 | `cursor_expired` | 400 | `MT-MGMT-009` / `MT-DIAG-006` | PASS |
| a20 | `rate_limit_exceeded` | 429 | `MT-INF-007` / `MT-INF-008` / `MT-INF-018` | PASS |
| a21 | `provider_unavailable` | 503 | `MT-INF-003` / `MT-INF-008` / `MT-INF-013` / `MT-INF-014` / `MT-MGMT-013` | PASS |
| a22 | `provider_error` | 上游码（4xx/5xx） | `MT-INF-012` | PASS |
| a23 | `provider_failure` | 502 | `MT-INF-008` | PASS |
| a24 | `provider_secret_unavailable` | 503 | `MT-INF-019` | PASS |
| a25 | `provider_contract_error` | 502 | `MT-INF-010` / `MT-DIAG-005` / `MT-INF-016` / `MT-INF-017` | PASS |
| a26 | `model_unavailable` | 503 | `MT-INF-007` | PASS |
| a27 | `usage_store_unavailable` | 503 | `MT-API-005` / `MT-OBS-003` | PASS |
| a28 | `internal_error` | 500 | `MT-API-005` | PASS |
| a29 | `bootstrap_required` | 503 | `MT-MGMT-001` | PASS |
| a30 | `bootstrap_invalid` | 503 | `MT-MGMT-001` / `MT-MGMT-006` | PASS |
| a31 | `schema_version_mismatch` | 503 | `MT-UTIL-004` | PASS |
| a32 | `schema_unknown` | 503 | `MT-UTIL-004` | PASS |
| a33 | `schema_integrity_failed` | 503 | `MT-UTIL-004` | PASS |
| a34 | `store_path_unsafe` | 503 | `MT-UTIL-003` | PASS |
| a35 | `E-UTIL-NESTED-TXN` | 409 | `MT-UTIL-005` | PASS |
| a36 | `invalid_injection` | 400 | `MT-DIAG-003` | PASS |
| a37 | `confirmation_required` | 400 | `MT-MGMT-004` / `MT-MGMT-010` | PASS |

> 覆盖补齐（`eb62302`，`G-MT-COVERAGE-1`）带来的映射增量：a1 增 `MT-MGMT-014`（`from`/`to` 缺失→400）、a11 增 `MT-MGMT-012`（禁用态 →404 `model_not_found`）、a12 增 `MT-MGMT-013`（未知 provider→404）、a21 增 `MT-MGMT-013`（上游 5xx→503）。新增项在本 Run 全部 `PASS`。

**(b) 上游异常类别（8 类，边界替身返回）**

| # | 上游异常 | 映射 Case | 本 Run Verdict |
|---|---|---|---|
| b1 | 上游 4xx（非配额） | `MT-INF-012` | PASS |
| b2 | 上游 5xx | `MT-INF-003` / `MT-INF-008` | PASS |
| b3 | 配额/额度耗尽（429/402/403） | `MT-INF-012` | PASS |
| b4 | 非 JSON 响应 | `MT-INF-017` | PASS |
| b5 | 坏数据·非 SS 帧 | `MT-DIAG-005` / `MT-INF-016` | PASS |
| b6 | 坏数据·坏向量/非法维数 | `MT-INF-010` | PASS |
| b7 | 坏数据·非法 base64 | `MT-INF-010` | PASS |
| b8 | 凭据缺失（`env:`/`file:`/非法引用） | `MT-INF-019` | PASS |

**(c) 传输/时间病态（8 类，真实 socket / 真实 `Store` / `Router.admit`）**

| # | 传输/时间病态 | 映射 Case | 本 Run Verdict |
|---|---|---|---|
| c1 | stall/hang（上游建连成功但永不响应） | `MT-INF-013` | PASS |
| c2 | slow-response timeout（慢速 trickle 超过流空闲超时） | `MT-INF-014` | PASS |
| c3 | 超长/超大 response | `MT-INF-015` | PASS |
| c4 | broken pipe / client disconnect mid-stream | `MT-API-012` | PASS |
| c5 | connection reset (RST) | `MT-API-013` | PASS |
| c6 | truncated stream / early EOF（上游在 terminal 前关流） | `MT-INF-016` | PASS |
| c7 | malformed frame（非 JSON `data:` 行 / 坏 SSE 块） | `MT-INF-017` | PASS |
| c8 | concurrency timeout + permit leak | `MT-INF-018` | PASS |

- **(a)/(b)/(c) 汇总核对**：37 ＋ 8 ＋ 8 ＝ **53 条，每条均映射到已执行 Case，0 静默缺失、0 映射 Case 非 `PASS`**。10 个新增分支 Case（`MT-MGMT-011`、`MT-API-012/013`、`MT-INF-013…019`）承接 a16/a24、b4/b8、c1–c8 共 20 条；`MT-MGMT-012/013/014` 承接 a11/a12/a21/a1 的增量映射，本 Run 全部 `PASS`。
- **真实 socket 专证（c4/c5，计划 §7/§8 要求）**：`MT-API-012`（客户端读首帧后 `close()`）与 `MT-API-013`（`SO_LINGER 0` 后 `close()` 触发 RST）均在 ENV-2 `ThreadingHTTPServer` 的真实 socket 上以真实客户端执行（未用进程内对象替代），本 Run 均 `PASS`；两 Case 自身在断开前后取 `/dev/fd` 基线（`_fds()`）并断言无 fd 泄漏，同时经 `/v1/runtime` 断言 `running` 归零（Router 许可释放）、账本不变。c1/c2 由 `MT-INF-013/014` 命中建连/流空闲超时；c3 由 `MT-INF-015` 的 2 MiB 响应归一承接（替身为 chunked 16 KiB 形态，本 Run 三个函数 0.52s 级，见 §1.3.9）；c8 由 `MT-INF-018` 断言 429 + `Retry-After` 与许可归零，全部 `PASS`。
- **design-vs-code 偏差的处置（`G-INF-NONJSON-MAPPING-1`）**：方案 §2.3 的 a25/b4/c7 三行把「非 JSON `data:` 帧 / 非 JSON embeddings 响应体」预期为 `502 provider_contract_error`；`src/` 实测为 **`503 provider_unavailable`（`retryable=true`）**，因 `OpenAIProvider.complete/_request` 把 `json.JSONDecodeError` 归入传输异常类。按方案 §7 的裁决（**Oracle ＝ `src/`，实测为准**），`MT-INF-017` 以 `src/` 断言：非 SSE Content-Type/多 terminal/terminal-status 矛盾/无合法 terminal → 502；非 JSON `data:` 帧 → 503；embeddings 非 JSON 体 → 503；且断言账本不伪装成功（`measurement_status=unknown`、tokens 为 NULL 不补零）。本 Run `MT-INF-017` **4 个测试函数全 `PASS`**，即该偏差**按设计侧登记、以 `src/` 为准断言通过**，未被改判为 PASS 掩盖、未把 503 写成 502。恢复条件（设计侧确认权威映射、或建立 `interfaces/error-codes/` 机器目录）挂在 §8。

### 5.3 注入类方法命中门（方案 §2.2/§6.7 注入面核对块；计划 §8）

主手段＝边界替身返回错误数据/行为；产品 diagnostics 注入为**可选补充**（ENV-4）。判定规则：替身按配置返回错误即视为命中，判定＝模块对该错误的映射；产品注入须命中方可判定，未命中即 `INVALID`。本 Run `INVALID=0`，注入类方法逐面命中如下：

| 注入分类 | 注入面 / 数据类型 | 映射 Case | 本 Run Verdict |
|---|---|---|---|
| 故障注入 | mock 返回 **5xx**（上游错误响应） | `MT-INF-003` / `MT-INF-008` / `MT-MGMT-013` | PASS |
| 故障注入 | mock 挂起 **超时** | `MT-INF-003` / `MT-INF-008` | PASS |
| 故障注入 | mock 抛错 **断连** | `MT-INF-003` / `MT-INF-011` | PASS |
| 故障注入 | mock 返回 **配额/额度耗尽（quota exhausted，4xx 429/402/403）** | `MT-INF-012` | PASS |
| 故障注入 | mock 返回 **坏数据（契约违规：非 SS 帧·坏向量·非法 base64）** | `MT-INF-010` / `MT-INF-002` | PASS |
| 故障注入 | mock 返回 **畸形流（非法 SSE/多 terminal/坏帧）** | `MT-DIAG-005` / `MT-INF-003` | PASS |
| 故障注入 | 存储面：库写失败 / 表损坏 / 迁移中途失败 | `MT-INF-009` / `MT-DIAG-007` / `MT-OBS-004` / `MT-UTIL-004` / `MT-UTIL-005` | PASS |
| 故障注入 | 传输面：客户端中途断开 / 超大流 / 畸形事件 | `MT-API-008` / `MT-API-007` / `MT-DIAG-005` | PASS |
| 故障注入 | 准入面：队列饱和 429 / 全不健康 503 / 等待超时 | `MT-INF-007` / `MT-INF-004` | PASS |
| 数据注入 | 初态数据（经公开入口播种，禁止直写表） | `MT-MGMT-001` / `MT-INF-003` / `MT-DIAG-004` / `MT-OBS-002` | PASS |
| 数据注入 | 边界数据（2 MB / `limit` 上限 / 512 / 极值·空·未知） | `MT-API-007` / `MT-MGMT-009` / `MT-LOG-001` / `MT-LOG-003` | PASS |
| 数据注入 | 诊断数据注入（`PATCH /v1/deployments/{id}/diagnostics`） | `MT-DIAG-002` / `MT-DIAG-003` / `MT-DIAG-004` / `MT-OBS-004` | PASS |
| 数据注入 | 冻结向量（SSE 字节帧 / 32-hex traceparent / base64 / UI 资产字符串） | `MT-API-008` / `MT-API-010` / `MT-INF-002` / `MT-INF-010` / `MT-UI-001` / `MT-UI-002` | PASS |

- **「mock 返回」6 类**（5xx / 超时 / 断连 / 配额耗尽 / 坏数据 / 畸形流）全部命中且映射 Case 全 `PASS`；**存储面 / 传输面 / 准入面 3 面**全部命中且全 `PASS`；**数据注入 4 类**（初态 / 边界 / 诊断 / 冻结向量）全部命中且全 `PASS`——**13 行 0 未映射、0 未命中**（其中「边界数据 2 MB」请求侧由 `MT-API-007` 承接 413；**响应侧 2 MB 归一属 c3，本 Run 由 `MT-INF-015` `PASS` 承接**）。
- **产品诊断注入（ENV-4，可选补充）的命中情况**：`MT-INF-008` 经公开入口 `set_injections` 配置 `fault_502/fault_503/rate_limit/delay`，断言 `ApiError.piko_injected == {deployment_id, type}` 标记与账本 `source=injected`（注入**已生效**的证据）；`MT-DIAG-005` 断言 `stream_terminate` 到点截断且无 `[DONE]`、`malformed_event` 到点追加 `response.malformed` 畸形帧；`MT-OBS-004` 经 `PATCH /v1/deployments/{id}/diagnostics` 断言合法注入改变推理分支、非法类型 400、未知 deployment 404。三者本 Run 全 `PASS`，**产品注入未出现「配置但未生效」**；命中以注入生效的**可观测后果**断言（标记 / 帧序 / 分支），非独立数值计数。
- **数据注入的公开入口前置**：初态一律经 `AppFixture.seed`／HTTP 端点／服务方法／`Store` 公开方法播种；`MT-UI-001/002` 对真实 `webui/` 静态产物做字符串契约断言（快速下位防线），行为级由系统层 `ST-UI-*` 承接（见 §6.4）。
- **替身形态对注入面无影响**：ENV-3 替身对所有 mode 统一使用 chunked（run-04 起），(a)/(b) 各行的错误响应体与 (c) 各行的病态响应仍按同一 `mode` 分派（`_dispatch`/`_responses` 未改），仅传输层编码变化；本 Run 对应 Case 全 `PASS` 即为该等价性的运行证据。

### 5.4 设计验证项（VRC）追溯复核（33 项，非分母）

方案 §6.5/附录 A：VRC 在本层只作追溯列。33 项 `VRC-*` 每项至少映射 1 个本层 Case（映射列取自方案附录 A 的「§6 Case 覆盖」列）：

| VRC ID | 要验证什么 | 设计来源 | 本层 Case | 本 Run Verdict |
|---|---|---|---|---|
| VRC-API-001 | 分发/错误/资源 | `http-api-design` §14.1 / `http-api-isd` §9.1.1 | `MT-API-001` / `MT-API-002` / `MT-API-004` / `MT-API-005` | PASS |
| VRC-API-002 | 鉴权 | `http-api-design` §14.2 / `http-api-isd` §9.1.2 | `MT-API-006` / `MT-API-011` | PASS |
| VRC-API-003 | body 与 SSE | `http-api-design` §14.3/§14.4 / `http-api-isd` §9.1.3 | `MT-API-007` / `MT-API-008` / `MT-API-012` / `MT-API-013` | PASS |
| VRC-API-004 | 静态与健康 | `http-api-design` §14.5/§14.6 / `http-api-isd` §9.1.4 | `MT-API-003` / `MT-API-009` | PASS |
| VRC-UI-001 | 加载与状态 | `web-ui-design` §14.1 / `web-ui-isd` §9.1.1 | `MT-UI-001` / `MT-UI-004` | PASS |
| VRC-UI-002 | 编辑/鉴权 | `web-ui-design` §14.2 / `web-ui-isd` §9.1.2 | `MT-UI-002` / `MT-UI-003` / `MT-UI-006` | PASS |
| VRC-UI-003 | Pause 边界 | `web-ui-design` §14.3 / `web-ui-isd` §9.1.3 | `MT-UI-002` | PASS |
| VRC-UI-004 | 用量未知不填零 | `web-ui-design` §14.5 / `web-ui-isd` §9.1.4 | `MT-UI-002` / `MT-UI-005` | PASS |
| VRC-UI-005 | 探测付费确认 | `web-ui-design` §14.4 / `web-ui-isd` §9.1.5 | `MT-UI-002` | PASS |
| VRC-UI-006 | 诊断页 | `web-ui-design` §14.7 / `web-ui-isd` §9.1.6 | `MT-UI-002` | PASS |
| VRC-INF-001 | 推理与流式契约 | `inference-design` §14.1 / `inference-isd` §9.1.1 | `MT-INF-001` / `MT-INF-005` / `MT-INF-006` / `MT-INF-020` | PASS |
| VRC-INF-002 | 向量化契约 | `inference-design` §14.2 / `inference-isd` §9.1.2 | `MT-INF-002` / `MT-INF-010` | PASS |
| VRC-INF-003 | 失败与用量 | `inference-design` §14.3 / `inference-isd` §9.1.3 | `MT-INF-003` / `MT-INF-008` / `MT-INF-009` / `MT-INF-012` / `MT-INF-013` / `MT-INF-014` / `MT-INF-015` / `MT-INF-016` / `MT-INF-017` / `MT-INF-019` | PASS |
| VRC-INF-004 | 准入与目录 | `inference-design` §14.4 / `inference-isd` §9.1.4 | `MT-INF-004` / `MT-INF-007` / `MT-INF-018` | PASS |
| VRC-INF-005 | 观测 fail-open | `inference-design` §14.5 / `inference-isd` §9.1.5 | `MT-INF-011` | PASS |
| VRC-MGMT-001 | 引导与 Secret 引用 | `management-design` §14.1 / `management-isd` §9.1.1 | `MT-MGMT-001` / `MT-MGMT-006` | PASS |
| VRC-MGMT-002 | CRUD 与不变量 | `management-design` §14.2 / `management-isd` §9.1.2 | `MT-MGMT-002` / `MT-MGMT-007` / `MT-MGMT-008` / `MT-MGMT-011` / `MT-MGMT-012` / `MT-MGMT-013` | PASS |
| VRC-MGMT-003 | 审计与日志 | `management-design` §14.3 / `management-isd` §9.1.3 | `MT-MGMT-002` / `MT-MGMT-005`（`atomic=False` 审计例外） | PASS |
| VRC-MGMT-004 | 分页与清空 | `management-design` §14.4 / `management-isd` §9.1.4 | `MT-MGMT-003` / `MT-MGMT-009` / `MT-MGMT-014` | PASS |
| VRC-MGMT-005 | 探测 | `management-design` §14.5 / `management-isd` §9.1.5 | `MT-MGMT-004` | PASS |
| VRC-MGMT-006 | 账号用量 | `management-design` §14.6 / `management-isd` §9.1.6 | `MT-MGMT-005` / `MT-MGMT-010` | PASS |
| VRC-OBS-001 | 开关 | `observability-design` §14.1 / `observability-isd` §9.1.1 | `MT-OBS-001` / `MT-OBS-002` | PASS |
| VRC-OBS-002 | 快照/统计查询与脱敏 | `observability-design` §14.2 / `observability-isd` §9.1.2 | `MT-OBS-001` / `MT-OBS-003` | PASS |
| VRC-OBS-003 | 注入与 fail-open | `observability-design` §14.3 / `observability-isd` §9.1.3 | `MT-OBS-004` | PASS |
| VRC-OBS-004 | trace 与关联标识 | `observability-design` §14.4 / `observability-isd` §9.1.4 | `MT-API-010` / `MT-OBS-001` | PASS |
| VRC-OBS-005 | trace 时间窗 | `observability-design` §14.5 / `observability-isd` §9.1.5 | `MT-OBS-001` | PASS |
| VRC-DIAG-001 | 开关 | `libdiag-design` §14.1 / `libdiag-isd` §9.1.1 | `MT-DIAG-001` | PASS |
| VRC-DIAG-002 | 记录与查询 | `libdiag-design` §14.2 / `libdiag-isd` §9.1.2 | `MT-DIAG-001` / `MT-DIAG-006` | PASS |
| VRC-DIAG-003 | fail-open | `libdiag-design` §14.3 / `libdiag-isd` §9.1.3 | `MT-DIAG-007` | PASS |
| VRC-DIAG-004 | 注入与 traces | `libdiag-design` §14.4 / `libdiag-isd` §9.1.4 | `MT-DIAG-002` / `MT-DIAG-003` / `MT-DIAG-004` / `MT-DIAG-005` | PASS |
| VRC-UTIL-001 | 连接与回收 | `util-design` §14.1 / `util-isd` §9.1.1 | `MT-UTIL-001` / `MT-UTIL-003` | PASS |
| VRC-UTIL-002 | 事务与迁移 | `util-design` §14.2 / `util-isd` §9.1.2 | `MT-UTIL-002` / `MT-UTIL-004` / `MT-UTIL-005` | PASS |
| VRC-LOG-001 | 脱敏与查询 | `log-design` §14.1 / `log-isd` §9.1.1 | `MT-LOG-001` / `MT-LOG-002` / `MT-LOG-003` | PASS |

> 33/33 `VRC-*` 均有本层 Case 且已执行并 `PASS`。追溯覆盖 ＝ 33/33，**不替代四层分母（95 条）的行为覆盖结论**（方案 §6.5 注）。`eb62302` 补齐后的追溯增量（VRC-MGMT-002 增 `MT-MGMT-012/013`、VRC-MGMT-003 增 `MT-MGMT-005`（`atomic=False`）、VRC-MGMT-004 增 `MT-MGMT-014`、VRC-INF-001 增 `MT-INF-020`）已由 `e27dca9` 的 VRC 追溯修正落入方案附录 A，本 Run 按该映射逐条复核一致。

### 5.5 覆盖复算小结

- 分母 95 条每条有着落：0 未映射、0 未执行、0 `NOT_RUN`；72 个 Case 全部执行并出 Verdict（**72 `PASS` / 0 `FAIL`**）。
- 53 条异常/错误矩阵项每条有着落且映射 Case 全 `PASS`，含 1 条 design-vs-code 偏差按 Oracle＝`src/` 断言通过并具名登记。
- 注入类方法 13 个注入面/数据类型全部命中（0 未命中、0 `INVALID`），产品诊断注入作为可选补充亦全部命中。
- 33 个 `VRC-*` 追溯覆盖 33/33（仅追溯，非分母）。
## 6. 缺陷与残余风险

### 6.1 缺陷清单（关联 Case 与 Run）

| 缺陷 ID | 关联 Case / Run | 严重度 | 状态 | 事实（取自 Run 证据） | Owner / 关闭事实 |
|---|---|---|---|---|---|
| `D-MT-INF-015-1` | `MT-INF-015`（层②，boundary，P1；方案 §2.3 c3）／发现于 `run-20261002-01`，**复现于 `run-20261002-03`**，根除于 `run-20261002-04`，pin 自洽确认于 `run-20261002-06`，首个 Gate 闭合复核于 `run-20261002-08`，**章节重编号后复跑复核于 `run-20261003-01`（本 Run）** | 中（P1；不涉及 P0 分母、鉴权或数据正确性） | **CLOSED（根因在测试替身，非产品）** | 原始事实（`run-20261002-01`）：`OversizeTests::test_two_megabyte_output_normalized` `FAIL`，`http_api.errors.ApiError: (503, 'provider_unavailable', 'Provider streaming request failed: TimeoutError: timed out')`，节点耗时 60.133s。二次事实（`run-20261002-03`）：同 Case 的 `test_service_remains_healthy_after_oversize` `FAIL`，同一 `ApiError`，耗时 60.126s。**根因在 ENV-3 夹具写侧**（`tests/module/cases/support/upstream.py::Handler._send` 以 `Content-Length` 声明长度、单条连接写出 2 MiB body，间歇性不推进 → 读侧 60s 无进展 → `stream_idle_timeout`（默认 60s）→ 503），**非被测实现缺陷**。中间处置（`f83f8da` 起的 64 KiB 分块 flush）为**缓解**，run-03 证明其不足。**关闭事实（`run-20261003-01`）**：替身 chunked 化已随 `a1cb672` 入库，pin 与被测树一致；`MT-INF-015.json` `status=PASS`、`reason` 空，三个测试函数 0.522s / 0.529s / 0.521s | Owner：LLMTier（M003 inference ＋ ENV-3 loopback `FakeUpstream` 夹具）。**关闭依据**：`run-20261003-01/MT-INF-015.json`（`status=PASS`）、`case-status.json`（`counts.FAIL=0`、`release_blocking=false`、`cases` 72/72 `PASS`）、`artifacts/junit.xml`（`tests="371" failures="0" errors="0" skipped="0"`）、`artifacts/pytest.log`（`371 passed in 112.96s`）、`test-run.env`（`git_commit=851d172…` ＝ 执行时 `HEAD`，工作树干净）。**旧 Run 证据不覆盖**（计划 §7）：`run-20261002-01/`、`-03/` 的失败记录原样保留 |

**复现率证据（关闭判据的支撑，标注证据等级）**

| 度量 | 数值 | 证据等级 | 出处 |
|---|---|---|---|
| 历史复现：run-01 `test_two_megabyte_output_normalized` | 1 次失败 / 354，60.133s | 权威（Run 证据） | `run-20261002-01/{MT-INF-015.json,case-status.json,artifacts/*}` |
| 历史复现：run-03 `test_service_remains_healthy_after_oversize` | 1 次失败 / 354，60.126s | 权威（Run 证据） | `run-20261002-03/{MT-INF-015.json,case-status.json,artifacts/*}` |
| 修复后整批：run-04 / run-05 / run-06（连续三轮，68 Case 基线） | **各 0 次失败 / 354**（各自 `failures="0"`、354 passed；套件 102.520s / 102.672s / 102.515s） | 权威（Run 证据） | `run-20261002-0{4,5,6}/artifacts/{junit.xml,pytest.log}` |
| 扩充资产后整批：run-07 / run-08（两轮，72 Case 基线） | **各 0 次失败 / 371**（各自 `failures="0"`、371 passed；套件 113.149s / 113.159s） | 权威（Run 证据） | `run-20261002-0{7,8}/artifacts/{junit.xml,pytest.log}` |
| 章节重编号后复跑：run-20261003-01（本 Run，72 Case 基线） | **0 次失败 / 371**（`failures="0"`、371 passed；套件 112.963s；`MT-INF-015` 三函数 0.522s / 0.529s / 0.521s） | 权威（Run 证据） | `run-20261003-01/artifacts/{junit.xml,pytest.log}`、`run-20261003-01/MT-INF-015.json` |
| 修复后定稿复测：产品路径 `MT-INF-015` 重复 20 轮 | **0 轮失败 / 20** | 参考（临时探针，未落 Run 证据） | run-04 报告 §1.3.5 ② |
| 修前形态复刻（`Content-Length` ＋ 单次写 / ＋64 KiB 分块） | **0 次 stall-or-fail / 100 与 / 100**（4 并发） | 参考（临时探针） | run-04 报告 §1.3.5 ③；**本次未复现停顿，故不给「修前 N/N 失败」的受控对照数字** |

- **不夸大声明**：本报告称「已根除」的依据是「持久化 Run 连续六轮零失败（68 Case 基线的 run-04/05/06 ＋ 72 Case 基线的 run-07/08 ＋ 章节重编号后复跑的 run-20261003-01）＋ 定稿复测 0/20 轮 ＋ 0/60 次客户端读」，**不是**「已在受控条件下证明修前必失败、修后必成功」。该 flake 的负载相关性使其在复测中不复现；`urllib` 与 `http.client` 的客户端不对称属分诊期线索，未落 Run 证据。
- **产品语义不改判**：读阶段 60s 无进展即 503 `provider_unavailable` 是 `stream_idle_timeout` 的设计行为（与 c1/c2 病态一致），**不作为产品缺陷登记**，也不下调该超时。

> 本 Run 无其他 `FAIL`；无 `BLOCKED`/`INVALID`/`NOT_RUN`/`SKIP`/`XPASS`。run-06 轮修复的 `tools/test_report.py` 两处缺陷（Case ID 正则补 `MT-*`；Case 级状态取最严重 ＋ 落 `test_functions`）已随 `a1cb672` 入库并在本 Run 生效——本 Run 正常产出 72 份 `MT-*.json`（70 份带 `test_functions`）＋ `case-status.json` ＋ `artifacts/`，且 Case 级状态与 `counts` 互相一致（§6.2）。

### 6.2 工具 / harness 变更登记（回归在本 Run 内体现）

| 已修项 | 事实 | 回归证据（本 Run） |
|---|---|---|
| ENV-3 `FakeUpstream` 大 body 写侧（`tests/module/cases/support/upstream.py::Handler._send`） | 真实 SSE 上游是流式投递的；三阶段演进：run-01「`Content-Length` + 单次 `write(2 MiB)`」→ run-02/03「`Content-Length` + 64 KiB 分块 + `flush()`」（**缓解，未根除**）→ run-04 起「`Transfer-Encoding: chunked` + 16 KiB 分片 + 逐片 `flush()` + 终止块」（真实流式上游形态，根除） | `MT-INF-015` 3 个测试函数全 `PASS`（0.522s / 0.529s / 0.521s）；`artifacts/junit.xml` `failures="0"`；原缺陷 `D-MT-INF-015-1` 关闭（§6.1）；本 Run 复跑再次确认 |
| `stream_idle_timeout` 静默 no-op（`src/inference/providers/openai.py::_stream_read_timeout`） | Python 3.14 `SocketIO` 无 `settimeout`，原实现 `except: pass` 静默 no-op → 读阶段回落到 `connect_timeout`（默认 30s），`stream_idle_timeout` 形同虚设；已补 `response.fp.raw._sock.settimeout(...)` 兜底（方案 §7 记「已修」，无恢复条件） | `MT-INF-014` 命中流空闲超时并 `PASS`；`MT-INF-013/016/017` 同族 `PASS`。**注**：本 Run 的 60s 超时路径因此是**按设计生效**的（§1.3.10） |
| provider adapter 每请求重取（`src/inference/providers/openai.py`，`eb62302` 修复） | endpoint/secret_ref 经公开入口变更后，下一次请求须使用新值，不得跨请求复用 adapter/连接缓存 | `MT-INF-020` `test_endpoint_change_routes_next_request_to_new_upstream` 等 2 个测试函数全 `PASS`（代表节点 1.017s） |
| 覆盖缺口补齐（`tests/module/cases/MT-MGMT-012/013/014.py`、`MT-INF-020.py`、`MT-MGMT-005.py` 扩充，`eb62302`） | 「配置变更→运行态」与次要端点组装面反向核对新增 4 个 Case 并扩充 1 个 | `MT-MGMT-012` 3/3、`MT-MGMT-013` 5/5、`MT-MGMT-014` 5/5、`MT-INF-020` 2/2、`MT-MGMT-005` 7/7 全 `PASS`；72/72 Case、371/371 测试函数（函数数按本 Run junit 复算，与前序报告誊写差异见 §4.2） |
| 模块用例无法被目录发现收集（`pyproject.toml` `python_files`） | 收集规则缺 `MT-*.py`，`pytest tests/module/cases` 收不到模块用例 | 本 Run `collected 371 items`（`artifacts/pytest.log`） |
| 逐 Case 证据无法生成（`tools/test_report.py` Case ID 正则） | `_CASE_ID_IN_FILENAME` 补 `MT-*`；此前模块用例无法按文件名收敛 Case ID | 本 Run 生成 72 份 `MT-*.json` ＋ `case-status.json`，`run_id`/`git_commit`/`schema_version_db`/`openapi_version` 全部与 `test-run.env` 一致（§2） |
| **Case 级状态被同 Case 内后续通过函数覆盖（记录口径缺陷，run-03 暴露；run-06 轮修复）** | `build_report`/`emit_manifests` 原按 `case_id` 逐条覆盖 → `counts.FAIL=1` 而 `cases[MT-INF-015].status=PASS`。修复后：Case 级取**最严重状态**（`FAIL`>`BLOCKED`>`INVALID`>`XPASS`>`SKIP`>`NOT_RUN`/`PASS`），并为多测试函数 Case 落 `test_functions` 明细 | 本 Run `counts.FAIL=0` 与 `cases` 72/72 `PASS` **互相一致**；70 份 `MT-*.json` 带 `test_functions`（合计 369 条，全部 `PASS`、`reason` 空），与 junit 的 371 条 testcase 对齐（差额 2 条＝两个单函数 Case 的代表节点，已由 `node_id` 记录）。**旧 Run 证据不追溯改写**（计划 §7） |
| Run 证据未记录 `PYTHONPATH` 与退出码（计划 §7） | harness 把 `PYTHONPATH=src` 放在 runner 内 `export`，退出码只在 runner 退出时体现；已在 `tests/common/harness/run_harness.sh` 补录 `pythonpath` / `exit_code` / `pytest_exit_code` / `finished_at` | **本 Run 已落证**：`test-run.env` 12 字段，`pythonpath=src`、`exit_code=0`、`pytest_exit_code=0`、`finished_at=2026-10-03T04:21:25Z`（§2）。run-03 起即具备；**run-01/run-02 无此四字段，不补造** |

> **变更的证据归属规则（登记）**：上述测试资产/工具修复与 harness 补录已随 `a1cb672`/`eb62302` 入库，故本 Run 的 `test-run.env.git_commit=851d172` **完整覆盖**被测树（且被测面与 run-08 的 pin `e27dca9` 零差异）——这是 run-04（修复未入库，pin 不含替身）、run-05（pin 仍为 `f83f8da`，与执行树不一致）与 run-07（pin 为 `998d879`，不含新脚本与 openai 修复）都不具备的属性。**旧 Run 的证据与字段一律不追溯补写、不追认**（计划 §7）。

> **替身保真度注记（不是缺陷）**：`_send` 现对**所有** mode 统一使用 chunked + `Connection: close`，其中包括非 SSE 的 JSON 错误体（quota/5xx/非 JSON 等）。真实 provider 的非流式错误响应通常以 `Content-Length` 返回，故替身在这些行上的传输编码与真实上游**不完全一致**（比原实现更「严」而非更松：产品必须能消费 chunked 错误体）。运行证据：依赖错误体映射的 Case（`MT-INF-012/013/017`、`MT-MGMT-013` 等）本 Run 全 `PASS`。记此注记以免把「替身形态」误读为「真实上游协议已被本层证明」（真实 provider 协议归系统层，§6.4）。

> **未修、按设计侧/实现侧具名挂起**（不改判本 Run 判定）：trace stage 同毫秒乱序（`G-OBS-STAGE-ORDER-1`，`MT-OBS-001` 只断言 stage 集合与非递减时戳，不断言位置序）；`/login` 路由缺失（`G-UI-LOGIN-ROUTE-1`，loopback `GET /login` 实测 404 `not_found`，`MT-UI-003` 的 401 分支只做静态契约断言与服务端锚点）。

### 6.3 方案 §7 缺口与观察项在本 Run 的落点

| 项 | 分类 | 本 Run 事实 | Owner | 恢复条件 |
|---|---|---|---|---|
| `G-MT-COVERAGE-1`（"配置变更→运行态"类组装保证未登记为分母维度；两个次要端点遗漏） | 覆盖缺口（**已修复**，方案 `0.1.0-draft.12`） | 已新增 `MT-MGMT-012`（禁用三态→404）、`MT-INF-020`（adapter 重取）、`MT-MGMT-013`（provider 模型目录）、`MT-MGMT-014`（`/v1/stats`）并扩充 `MT-MGMT-005`（`atomic=False` 审计）；分母 91→95、Case 68→72；本 Run 5 个 Case 全 `PASS` | LLMTier | 已闭合；设计侧后续若新增"运行态可变配置"维度须同步登记 |
| `G-INF-NONJSON-MAPPING-1`（非 JSON `data:` 帧 / 非 JSON embeddings 体：矩阵预期 502，`src/` 实测 503） | design-vs-code 缺口 | `MT-INF-017` 按 Oracle＝`src/` 断言 503 并 4/4 `PASS`；偏差未被掩盖（见 §5.2） | M003 inference ＋ 系统设计 §7.8 | 设计侧确认权威映射（503，或改实现为 502）后回溯修订 §2.3 a25/b4/c7；若建立 `interfaces/error-codes/` 目录以其为准 |
| `G-OBS-STAGE-ORDER-1`（trace stage 因果序：毫秒精度 + 随机 `tev_<uuid4>` 主键 → 同毫秒乱序） | design-vs-code 缺口 | `MT-OBS-001` 只断言 stage 集合与非递减时戳，**位置序未断言**；本 Run `PASS` | M006 libdiag | 增加每请求单调序号列或改 `ORDER BY rowid` 后，回溯修订 `VRC-OBS-004` 并把位置序断言补入 `MT-OBS-001` |
| `G-UI-LOGIN-ROUTE-1`（`app.js` `LOGIN_URL='/login'`，M001 无 `/login` 路由） | design-vs-code 缺口 | `MT-UI-003` 的 401 分支只做静态契约断言与服务端锚点，未做 `/login` 端到端；本 Run `PASS` | M002 web-ui ＋ M001 http-api | M001 提供 `/login`（或 ISD 改指真实登录入口）后，补 `/login` 端到端断言 |
| `O-OBS-STORECODE-1`（`_store_read` 把存储读失败统一映射 `usage_store_unavailable`，诊断查询面复用同 code） | 观察项（非阻断） | 第二个映射点为 `MT-OBS-003`（存储不可读 → 503 不伪装空页），本 Run `PASS` | M001 | 错误目录按面细分 `code` 时回溯修订 a27；否则把 a27 映射 Case 补记 `MT-OBS-003` |
| `O-UI-HEALTHDOMAIN-1`（`backendState` 4 个 health 分支在 `src/` 内无写点；`degraded` 合法但 UI 无分支） | 观察项 | `MT-UI-004` 对无写点取值只做静态契约断言；本 Run `PASS` | M002 web-ui | health 域扩展（如探测中态写入）后在 `MT-UI-004` 补行为级断言 |
| `O-UI-USAGEOK-1`（`usageSummary` 的 `ok` 分支需真实 provider 响应，M004 provider HTTP 面无边界替身资产） | 观察项 | `MT-UI-005` 只静态断言渲染分支（含 Unknown≠0）；本 Run `PASS` | M002 ＋ M004 | 为 account-usage 面建 `tests.asset-design` 替身后补行为级断言 |
| `G-TRANSPORT-BUDGET-1`（c3 超 2 MB **下游响应**资源预算） | Gap（跨层） | 本层只断言模块内归一不崩溃（`MT-INF-015`，本 Run `PASS`，§4.1）；下游预算未测 | LLMTier（系统层） | 系统层预算用例建立并引用本行 |
| c4/c5 真实**跨主机**网络 RST/半开连接 | Tailored-N/A（本层仅 loopback ENV-2 真实 socket） | `MT-API-012/013` 已覆盖 loopback 内可复现断连，本 Run `PASS` | LLMTier | 跨主机链路病态归系统/运维层 |
| 跨模块系统级流程（systemd/反向代理/Piko 联调）、真实 provider 协议与 wire 互操作、浏览器 E2E | Tailored-N/A | 本层不测（本 Run 未涉及） | 系统测试方案 `llmtier-system-test-scheme`／契约层 | 各自承接方建立对应用例 |
| performance / endurance 分类 | Tailored-N/A | 本层不纳入（方案 §5 裁剪依据） | 系统测试方案 | 同上 |
| M002 `VRC-UI-001..006` 的**行为级**（真实 JS 执行） | Tailored-N/A | 本层 `MT-UI-*` 为静态产物/契约组装（61 个测试函数全 `PASS`）；行为级由系统层真实浏览器 `ST-UI-001..010` 承接 | M002 web-ui ＋ 系统层 | 已在系统层承接（`RISK-UI-EXEC-1` 已关闭） |
| ENV-3/ENV-4 契约 `llmtier-unit-fakes` 自检 Run 未录制（`Implemented`/`Unverified`） | 资产 Gate 未闭合（不改变本 Run 判定） | 本 Run 使用其 `AppFixture`/`FakeAdapter` 与各 Case 本地 stub；**替身自检仍无独立 Run 证据** | LLMTier | 录制 assets self-check Run 并置 `Verified`（§8） |
| **方案 §6.6 的 Run 现状描述过期**（仍记 run-08 为「最终 Run」，且「共 8 个 Run」与真实 9 个不符，`run-20261003-01` 未列入；同段 case 文档版本措辞 `0.1.0-draft.1` 落后于现行 `0.1.0-draft.2`） | 文档漂移（不改变本 Run 判定） | 实际已有 9 个 Run 目录；本报告不动方案，如实登记（§4.2） | LLMTier | 下一次方案修订时同步为 9 个 Run（`-01`…`-08`、`run-20261003-01`）与本报告的正式记录 |

### 6.4 残余风险与本层已知限制

- **层级边界（最重要）**：**module PASS ≠ system PASS**；本层 `PASS` 不替代也不蕴含系统层结论。**下层单元 PASS 不关闭本层**（本层分母独立来自模块设计 §9/§14 与 `src/` 分支），**本层 PASS 不关闭上层**（wire 互操作、OpenAPI 端到端一致性、真实上游 provider 协议、浏览器 E2E 由 `llmtier-system-test-scheme` 承接）。
- **本层不测的范围**：跨模块系统级流程与进程装配（启动/systemd/反向代理/Piko 联调）；真实 provider 协议与 wire/OpenAPI 端到端一致性；浏览器 E2E 与真实 JS 行为级（归系统层 `ST-UI-*`，`MT-UI-*` 仅为静态产物/契约层快速下位防线）；性能/耐久/容量预算（归系统层）。
- **替身边界**：上游 provider 为进程内 `FakeAdapter` 与 loopback `FakeUpstream`，**不证明真实 provider 协议**；M004 account-usage HTTP 面的本地 stub 无共享资产契约（`O-UI-USAGEOK-1`）。ENV-3 夹具写侧连续两轮修复（§1.3、§6.2）说明**替身自身的传输行为是本层判定的前置条件**：替身缺陷会被记为被测 Case 的 `FAIL`，须按 §4.1 的方式归因区分「替身缺陷」与「实现缺陷」；本轮证据同时说明**替身形态向真实上游形态靠拢（chunked）能降低此类误判**。
- **Case 级记录口径（承 run-06 已闭合）**：`MT-*.json` / `case-status.json.cases` 的 `node_id`/`time_seconds` 仍只记每个 Case 的一个代表测试函数，**不代表该 Case 的函数级明细**；但 Case 级 `status` 已取最严重状态，且多函数 Case 另有 `test_functions` 全量落证，故 run-03 那种 Case 级与 `counts` 矛盾的情形已不可复现。判定仍以 `artifacts/junit.xml` 的函数级 `failures/errors` 为最终依据（§3 粒度注、§4.2）。
- **已被削弱/未覆盖的断言（诚实保留）**：`MT-OBS-001` 未断言 trace stage 位置序（`G-OBS-STAGE-ORDER-1`）；`MT-UI-003/004/005/006` 的部分分支为静态契约断言而非行为级（`G-UI-LOGIN-ROUTE-1`、`O-UI-HEALTHDOMAIN-1`、`O-UI-USAGEOK-1`）。
- **替身资产未自检**：ENV-3/ENV-4 契约 `llmtier-unit-fakes` 仍为 `Implemented`/`Unverified`，资产自检 Run 未录制；本 Run 的 `PASS` 结论以「替身按设计返回」为前提，该前提尚无独立 Run 证据。
- **历史 flake 已归因关闭，非「未复现」类 RED**：`D-MT-INF-015-1` 有确定根因（ENV-3 替身写侧非流式形态）、有根除性修复（chunked，已入库）、有连续六轮 Run 复跑证据（run-01 60.133s `FAIL` → run-04/05/06 ＋ run-07/08 ＋ 本 Run，`MT-INF-015` 三函数 0.52s 级 `PASS`），属**已关闭**；本 Run 证据中无「未复现/未关闭」类 RED 需保留。**限定**：修前形态在定稿复测中未复现停顿，故「根除」的强度受可复现性限制（§1.3.12、§6.1）。
- **记录粒度**：本 Run `test-run.env` 12 字段（`pythonpath`/退出码/`finished_at` 齐备，退出码与 `pytest.log`、`release_blocking` 三方一致），**pin 与执行树一致**（§2）；遗留缺口是 run-01/run-02 的 8 字段历史记录（**不补造**）与 run-05、run-07 的 pin 不一致（该两个 Run 不作最终 pin 依据）。
- **Run 证据可追溯性**：本 Run `test-run.env.git_commit=851d172`，执行时工作树无未提交改动（被测树与 pin 逐字一致，被测面与 run-08 pin 零差异）；前序 Run 的三类 pin 偏差——run-01 落后被测树 1 个提交、run-04/run-05 不含执行时实际生效的未入库测试资产、run-07 不含未入库的新脚本与 openai 修复——**已在 run-08 消除并由本 Run 延续**。

## 7. Gate 结论与建议

- Gate 结论（接受/条件接受/拒绝）：**接受（模块层闭合）**——按计划 §8 口径给出，**非批准**。
  - 闭合分母＝方案 §6 的 **72 个 Case**（非 33 个 VRC）：**72/72 `PASS`**，满足「全部 72 Case 有 `PASS`」的闭合条件，故**判闭合**。
  - `FAIL=0`、`BLOCKED=0`、`INVALID=0`、`NOT_RUN=0`、`SKIP=0`、`XPASS=0`（`case-status.json.counts`；`release_blocking=false`；函数级 `artifacts/junit.xml` `failures="0" errors="0" skipped="0"`，`artifacts/pytest.log` `371 passed`）。
  - **P0 41 个 Case 全部 `PASS`**，无任一 P0 处于 `NOT_RUN`/`BLOCKED`（计划 §8 的 P0 硬门满足）。
  - **分支/组合/迁移覆盖达标门满足**：95 条四层分母（①23/②48/③10/④14）**全部映射到已执行 Case，0 未覆盖**；33/33 `VRC-*` 追溯覆盖（追溯非分母）。
  - **注入类方法命中门满足**：「mock 返回」6 类 ＋ 存储/传输/准入 3 面 ＋ 数据注入 4 类共 13 个注入面/数据类型全部命中（`INVALID=0`）；产品诊断注入（ENV-4）作为可选补充亦全部命中生效。
  - **异常/错误矩阵封闭门满足**：53 条（(a)37＋(b)8＋(c)8）全部逐行映射，0 静默缺失，**53/53 映射 Case 均 `PASS`**（含 c3 → `MT-INF-015`：该行在 run-01/run-03 为 `FAIL`、本 Run 已 `PASS`）；`G-INF-NONJSON-MAPPING-1` 按 Oracle＝`src/` 断言并具名登记。
  - **证据可采信性满足**：pin `851d172` ＝ 执行时 `HEAD`，工作树无未提交改动；本 Run 被测面与 run-08（首个 Gate 闭合报告对象）零差异，结果复跑一致（371/371、72/72）——本 Run 作模块层**当前最终 pin 依据**（§1.3.9/§2）。
  - **覆盖缺口已闭合**：`G-MT-COVERAGE-1` 的 4 个新增 Case ＋ `MT-MGMT-005` 扩充在本 Run 全 `PASS`，分母 95/72 相对旧版 91/68 的增量已被覆盖（§5.1/§6.3）。
  - **闭合不影响未决项**：`D-MT-INF-015-1` 已关闭（根因在测试替身）；§6.3 的 `G-*`/`O-*` 与 Tailored-N/A 项、替身资产自检、方案 §6.6 文档漂移、run-01/run-02 字段缺失仍按 §8 跟踪，闭合的是**本层 72 Case 的行为覆盖**。
  - **层级边界**：**module PASS ≠ system PASS**；下层单元 PASS 不关闭本层，本层 PASS 不关闭上层。
- 开放问题与责任方：
  - 方案 §7 的 `G-*`/`O-*` 与 Tailored-N/A 项 → Owner 见 §6.3，最晚 Gate：对应设计修订或系统层承接。
  - 替身资产 `llmtier-unit-fakes` 自检 Run 未录制 → Owner LLMTier（§8）。
  - 方案 §6.6 的 Run 现状描述与计数过期 → Owner LLMTier（§8；本交付按边界不改方案）。
  - 上层 wire/E2E/真实 provider 协议/性能耐久 → 系统测试方案/计划与契约层承接，不在本层分母。
  - 本报告不授权 release，不代替批准决定。

## 8. 未决项

| 未决项 / 关联 | Owner / 最晚 Gate | 关闭所需事实或决定 |
|---|---|---|
| ~~`D-MT-INF-015-1`：`MT-INF-015` 超大响应归一 `FAIL`~~ | — | **已关闭**（§6.1）：根因为 ENV-3 替身写侧非流式形态（非产品缺陷），已改为 chunked + 16 KiB 分片并随 `a1cb672` 入库；以 `run-20261002-04`/`-05`/`-06`（68 Case 基线）、`-07`/`-08`（72 Case 基线）与 `run-20261003-01`（章节重编号后复跑）连续六轮复跑取得 `PASS`（三函数 0.52s 级），其中 `run-20261002-08` 与 `run-20261003-01` 的 pin 与被测树一致；run-01/run-03 旧证据保留 |
| ~~替身/harness/工具修复未入库，Run pin 不覆盖被测树~~ | — | **已关闭**（§1.3.9/§6.2）：`tests/module/cases/support/upstream.py`（chunked 化）、`tests/common/harness/run_harness.sh`（四字段补录）、`tools/test_report.py`（Case ID 正则 ＋ Case 级最严重状态/`test_functions`）已入库为 `a1cb672`；新增 4 个脚本与 `src/inference/providers/openai.py`（adapter 重取）修复入库为 `eb62302`；`run-20261003-01` 的 `test-run.env.git_commit=851d172` 覆盖被测树并作当前最终 pin 依据 |
| ~~`run-20261002-05` 报告实例未生成~~ | — | **已关闭**（run-06 报告）：前序最终报告落于 `run-20261002-06`（`llmtier-module-test-report-2026-10-02-06`，68/68 Case `PASS`、354/354、Gate 判「接受」）；run-05 因 pin（`f83f8da`）与执行树不一致**不作最终 pin 依据**，其报告实例不再补齐，证据目录原样保留 |
| ~~`run-20261002-07` 报告未生成 ＋ pin 待重跑（计划 §10）~~ | — | **已关闭**（run-08 交付，§4.3）：可采信 Run-08 报告 `llmtier-module-test-report-2026-10-02-08` 判 Gate 闭合。run-07 因 pin（`998d879`）与执行树不一致**不作最终 pin 依据**，其报告实例不再补齐，证据目录原样保留 |
| ~~章节重编号后的最终定稿报告（计划 §7/§10「当前 Run／最终报告」引用待同步）~~ | — | **已关闭**（本交付）：章节重编号后以资产零差异的 `run-20261003-01` 复跑并出具本报告 `tests/module/reports/run-20261003-01/module-test-report.md`（`llmtier-module-test-report-2026-10-03-01`）——72/72 Case `PASS`、371/371、`release_blocking=false`、`git_commit=851d172` ＝ 执行时 `HEAD` 且工作树干净，Gate 判闭合；计划 §1/§3/§7/§10 已同步（计划升 `0.1.0-draft.14`） |
| ~~`G-MT-COVERAGE-1`：配置变更→运行态与次要端点组装覆盖缺口~~ | — | **已闭合**（§6.3）：`0.1.0-draft.12` 新增 `MT-MGMT-012/013/014`、`MT-INF-020` 并扩充 `MT-MGMT-005`，分母 91→95、Case 68→72；本 Run 5 个 Case 全 `PASS` |
| ~~Case 级状态收敛口径（Case 内任一函数失败不翻转 Case 级状态）~~ | — | **已关闭**（§6.2）：`build_report`/`emit_manifests` 改为 Case 级取最严重状态并落 `test_functions`；本 Run `counts` 与 `cases` 一致。**旧 Run 证据不追溯改写**，报告判定仍以 `artifacts/junit.xml` 为最终依据 |
| Run 证据 `pythonpath`/退出码/`finished_at` 字段 | LLMTier / 本 Run 已闭合 | **run-03…run-08 与本 Run 的 `test-run.env` 已含四字段**（12 字段）→ 该项对本 Run 关闭；**run-01/run-02 无此字段，属历史记录粒度缺口，不补造** |
| 方案 §6.6 的 Run 现状描述与计数过期（记 run-08 为「最终 Run」，且「共 8 个 Run」与真实 9 个不符，`run-20261003-01` 未列入；case 文档版本措辞 `0.1.0-draft.1` 落后于 `0.1.0-draft.2`） | LLMTier / 下一次方案修订 | 同步为 9 个 Run（`run-20261002-01`…`-08`、`run-20261003-01`）的真实历史与本报告的正式记录；分母 95/72 与 Case 清单不动。本交付按边界不改方案 |
| `G-INF-NONJSON-MAPPING-1`：非 JSON 帧/体 503 vs 矩阵预期 502 | M003 inference ＋ 系统设计 §7.8 / 设计修订 | 设计侧确认权威映射或改实现；回溯修订 §2.3 a25/b4/c7；建立 `interfaces/error-codes/` 后以其为准 |
| `G-OBS-STAGE-ORDER-1`：trace stage 同毫秒乱序，位置序未断言 | M006 libdiag / 设计修订 | 增单调序号或改 `ORDER BY rowid`；修订 `VRC-OBS-004` 并把位置序断言补入 `MT-OBS-001` |
| `G-UI-LOGIN-ROUTE-1`：`/login` 未实现（404） | M002 web-ui ＋ M001 http-api / 设计或实现修订 | 提供 `/login` 路由或 ISD 改指真实入口；补 `/login` 端到端断言 |
| `O-OBS-STORECODE-1` / `O-UI-HEALTHDOMAIN-1` / `O-UI-USAGEOK-1`：观察项 | M001 / M002 ＋ M004 / 设计或替身资产补齐 | 错误目录细分 `code`；health 域扩展；为 account-usage 面建 `tests.asset-design` 替身后补行为级断言 |
| `G-TRANSPORT-BUDGET-1`：c3 超 2 MB 下游响应预算 | LLMTier（系统层）/ 系统层 Gate | 系统层预算用例建立并引用本行 |
| c4/c5 跨主机 RST/半开连接（Tailored-N/A） | LLMTier（系统/运维层） | 由系统层或运维演练承接，本层不重开 |
| 替身资产 `llmtier-unit-fakes`（ENV-3/ENV-4）自检 Run 未录制（`Implemented`/`Unverified`） | LLMTier / 首次资产自检 Gate | 录制 assets self-check Run 并置 `Verified` |
| 修前形态未在定稿复测中复现：间歇性 flake 的受控对照缺失（修前复刻 0/100、0/100 无停顿） | LLMTier / 可选 | 若需更强证据，在受控负载下重复修前/修后对照并落为 Run 证据；否则维持本报告的限定表述 |
| 上层承接（wire 互操作/真实 provider 协议/浏览器 E2E/性能耐久） | 系统测试方案与计划、契约层 / 系统层 Gate | 由 `llmtier-system-test-scheme`/`-plan` 建立对应用例；不在本层分母，本层不代为关闭 |

<!-- 交付自查：任一 Verdict 能否定位唯一 Run 与原始证据（是：§3.2 每条指向 `run-20261003-01/MT-<Case>.json`，函数级指向 `artifacts/junit.xml`）；失败与 NOT_RUN 是否如实保留（前序 run-01/run-03 的 FAIL 已显式登记、run-02 的假绿、run-05/run-07 的 pin 不一致均已显式登记、旧证据未覆盖；前序 run-08 报告的 3 处函数数誊写偏差已登记且不改写旧报告）；复现率是否区分证据等级（是：§1.3.12/§6.1 分「权威 Run 证据」与「参考复测」两栏，修前形态未复现已如实写明）；报告是否越权写成批准（否：Gate 为「建议接受」，明写非批准、不授权 release）；章节引用是否全部按 STD f073396 重编号后的新编号（是：方案 §2/§2.1–§2.4/§3/§4/§5/§6.1–§6.7/§7/§8，计划 §5.1/§6/§7/§8/§9/§10）。 -->
