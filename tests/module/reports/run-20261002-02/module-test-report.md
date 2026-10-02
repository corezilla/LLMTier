<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Module Test Report — Run 2026-10-02-02

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-module-test-report-2026-10-02-02` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-10-02` |
| Last Modified Date | `2026-10-02` |
| Template ID | `tests.module-test-report` |
| Template Version | `0.3.1` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `tests/module/reports/run-20261002-02/module-test-report.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本报告由 Run 目录 `tests/module/reports/run-20261002-02/` 的机器产物整理而成（`test-run.env`、`case-status.json`、68 份逐 Case `MT-*.json`、`artifacts/{junit.xml,pytest.log}`）。**报告里的每个 Verdict 逐条取自对应 `MT-<Case ID>.json` 的 `status` 字段**，未运行/未命中/失败项一律如实保留，不补造结果。本 Run 是模块层**第 2 个 Run**；**前序 Run `run-20261002-01` 的失败证据与其报告草稿原样保留在本目录树内，不被本报告覆盖**（见 §1.3/§4.1）。

### 模板定位：报告、方案、用例、计划与 Run 证据的边界

- **Verdict 唯一持有**：执行状态（`NOT_RUN`/`BLOCKED`/`INVALID`）与实际判定（`PASS`/`FAIL`）只在测试报告与 Run 证据中产生；方案与 Case 文档不预填任何结果。
- **引用不复制**：逐 Case 结果引用 Run ID 与证据文件名，不把 stdout 全文搬进报告。
- **保留失败**：失败、阻塞、无效与未运行如实保留；**重跑生成新 Run，不覆盖旧失败**（计划 §7）。本报告即该规则的落地：前序 Run 的 `MT-INF-015` FAIL 记录未被删除或改写。
- **不越权**：Gate 建议不是批准；验收与发布授权另循其轨。

### 状态语义：执行状态与 Verdict

| 状态 | 取值 | 含义 | 判定事实 |
|---|---|---|---|
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | 未运行 / 环境阻断 / 执行未命中设计 | 运行记录与环境事实 |
| 实际判定 Verdict | `PASS` / `FAIL` | 断言与独立 Oracle 一致 / 不一致 | 有效 Run 的断言结果 |

## 1. 执行摘要与结论

### 1.1 范围与执行

- 报告范围（计划/方案版本）：
  - 方案：`llmtier-module-test-scheme`（[docs/70_verification/module/llmtier-module-test-scheme.md](../../../../docs/70_verification/module/llmtier-module-test-scheme.md)，`0.1.0-draft.8`，Template `tests.module-test-scheme` v0.6.1；**四层分母 91 条 → 68 个 Case**：① 接口行为 20 / ② 内部分支 47 / ③ 组合 10 / ④ 状态迁移 14；§3 为 Case 清单唯一登记处，§3.7 为分母→Case 核对表，§1.5.1 为异常/错误注入矩阵（(a) 37 个对外 `code` ＋ (b) 8 类上游异常 ＋ (c) 8 类传输/时间病态 ＝ 53 条），§4 为缺口裁决）。
  - 计划：`llmtier-module-test-plan`（[docs/70_verification/module/llmtier-module-test-plan.md](../../../../docs/70_verification/module/llmtier-module-test-plan.md)，`0.1.0-draft.7`，Template `tests.module-test-plan` v0.9.2；执行批次见其 §5.1，证据规则见其 §7，Gate 规则见其 §8）。
  - 机器契约 pin（取自 `test-run.env`）：`schema_version=2`、`openapi_version=0.3-simplified-candidate.8`。
- 被测对象：8 个软件模块 `M001`–`M008`（`M001 http-api`、`M002 web-ui`、`M003 inference`、`M004 management`、`M005 observability`、`M006 libdiag`、`M007 util`、`M008 log`；`M005 src/observability/` 无独立实现文件，其行为落在 M001 诊断路由与 M006 查询面，见方案 §1）。
- 执行范围：本 Run 一次整批执行 `tests/module/cases` 全量 68 个 Case（`python3 -m pytest --junitxml=tests/module/reports/run-20261002-02/artifacts/junit.xml tests/module/cases`；`test-run.env` 记录），`PYTHONPATH=src` 由 `tests/common/harness/runner_module.sh` 的 `export PYTHONPATH=src` 提供（计划 §6）。

### 1.2 结果分布与总结论

- **Case 粒度：68 个 Case 全部收集、全部执行、全部 `PASS`**；`NOT_RUN=0`、`BLOCKED=0`、`INVALID=0`（逐 Case `MT-*.json` 与 `case-status.json` 的 `cases` 段逐条一致，后者 `status` 计数为 `PASS=68`）。
- **测试函数粒度：354 collected、354 passed、0 failed、0 skipped、0 errors、0 xpassed；套件 102.74s**（`artifacts/junit.xml` testsuite `tests="354" failures="0" errors="0" skipped="0" time="102.736"`；`artifacts/pytest.log` 末行 `354 passed in 102.74s (0:01:42)`）。`case-status.json.counts` 记 `PASS=354 / FAIL=0 / BLOCKED=0 / INVALID=0 / NOT_RUN=0 / SKIP=0 / XPASS=0`，并置 `release_blocking=false`（无 `FAIL`/`BLOCKED`/`INVALID` 记录）。
- 四层分母 91 条**全部映射到已执行的 Case，未覆盖 0 条**（见 §5.1）；异常/错误注入矩阵 53 条**全部映射到已执行 Case 且全部 `PASS`**（见 §5.2）。
- 优先级与分类分布（方案 §3.6，与本 Run 逐 Case `status` 复算一致）：**P0 39 / P1 29**；negative 18 / boundary 13 / normal 11 / recovery 17 / security 6 / concurrency 3。

### 1.3 前序 Run 记录（`run-20261002-01`，保留不改写）

- 前序 Run `run-20261002-01`（`git_commit=982efae…`，`started_at=2026-10-02T08:40:20Z`）**不是全绿**：68 Case 中 67 `PASS`、1 `FAIL`，`case-status.json.counts` 为 `PASS=353 / FAIL=1`，`release_blocking=true`。
- 唯一 FAIL：`MT-INF-015`（M003，层②，boundary，**P1**）的 `OversizeTests::test_two_megabyte_output_normalized`，失败事实 `http_api.errors.ApiError: (503, 'provider_unavailable', 'Provider streaming request failed: TimeoutError: timed out')`，该节点耗时 **60.133s**（同套件其余 Case 均 0.5s 级；`artifacts/junit.xml` testsuite `failures="1" time="162.206"`）。
- 归因：**不在被测实现，而在 ENV-3 边界替身 `FakeUpstream` 的写侧**。`tests/module/cases/support/upstream.py::Handler._send` 原先一次性 `self.wfile.write(body)` 写出整个 2 MiB body；真实 SSE 上游是流式投递的，一次性写会在负载下卡在客户端 socket 缓冲上，表现为上游 60s 无进展、读侧回落到流空闲超时 → 503 `provider_unavailable`。
- 处置：改为**按 64 KiB 分块写出并逐块 `flush()`**（`for offset in range(0, len(body), 64 * 1024)`，随被测树 `f83f8da` 入库）。
- 复跑：按计划 §7「**重跑生成新 Run，不覆盖旧失败**」，以 `run-20261002-02` 重跑全量 68 Case —— **68/68 `PASS`、354/354 passed**；`MT-INF-015` 的同一代表节点耗时由 60.133s 降为 **0.517s**。缺陷 `D-MT-INF-015-1` 随之**关闭**（见 §6.1）。
- **旧 Run 证据目录 `tests/module/reports/run-20261002-01/`（含其 `MT-INF-015.json` 的 `status=FAIL` 与 `artifacts/` 原始失败记录、以及该 Run 的报告草稿）原样保留，本交付未改动其中任何文件。**

### 1.4 Gate 达成情况

- **闭合——按计划 §8 给出「接受（模块层闭合）」建议（Gate 建议，非批准）**。闭合分母＝方案 §3 的 **68 个 Case**（非 33 个 VRC），闭合条件＝「全部 68 Case 有 `PASS`」：本 Run **68/68 `PASS`，条件满足**；`FAIL=0`、`NOT_RUN=0`、`BLOCKED=0`、`INVALID=0`（P0 硬门、分支/组合/迁移覆盖达标门、注入类方法命中门、异常/错误矩阵封闭门均满足，见 §7）。
- **层级边界（必须随结论一起读）：module PASS ≠ system PASS**；**下层单元 PASS 不关闭本层**（本层分母独立来自模块设计 §9/§14 与 `src/` 分支），**本层 PASS 不关闭上层**（wire 互操作、OpenAPI 端到端一致性、真实上游 provider 协议、浏览器 E2E、性能耐久由 `llmtier-system-test-scheme` 承接）（计划 §8）。

## 2. 被测基线与实际环境

- 实际基线（与计划对照）——制品 pin，取自 `test-run.env`（本 Run 共 8 个字段，逐字段原样引用）：
  - `run_id`：`run-20261002-02`；`layer`：`MODULE`；`started_at`：`2026-10-02T09:15:23Z`。
  - `git_commit`：`f83f8da70dc9d632392f8d10f4236bd70518f2c5`（`case-status.json.git_commit` 同值；68 份 `MT-*.json` 的 `git_commit` 全部同值）。
  - `schema_version`：`2`（被测 DB schema 版本；`case-status.json` 另记 `schema_version_db: "2"` 与之一致；其顶层 `schema_version: 1` 是报告产物的**文件格式版本**，同名异义，非偏差）。
  - `openapi_version`：`0.3-simplified-candidate.8`（`case-status.json` 同值）。
  - `command`：`python3 -m pytest --junitxml=tests/module/reports/run-20261002-02/artifacts/junit.xml tests/module/cases`。
  - `python`：`3.14.3 (arm64)`；实测环境（`artifacts/pytest.log` 首部）：`platform darwin`、`pytest-9.1.0`、`pluggy-1.6.0`、`plugins: anyio-4.13.0`、`configfile: pyproject.toml`、`rootdir: /Users/ben/work/LLMTier`。
  - `case-status.json.generated_at`：`2026-10-02T09:17:06Z`；`artifacts/junit.xml` testsuite `timestamp="2026-10-02T17:15:23.779338+08:00"`、`hostname="192.168.1.8"`（与 `started_at` 的 UTC 值同一时刻）。
- 设计/模块基线（方案 §1.5，报告不预填结果、只引用版本）：M001 `http-api` v0.1.0-draft.2 / ISD `http-api-isd`；M002 `web-ui` v0.1.0-draft.2 / `web-ui-isd`；M003 `inference` v0.1.0-draft.1 / `inference-isd`；M004 `management` v0.1.0-draft.3 / `management-isd`；M005 `observability` v0.1.0-draft.6 / `observability-isd`；M006 `libdiag` v0.1.0-draft.6 / `libdiag-isd`；M007 `util` v0.1.0-draft.2 / `util-isd`；M008 `log` v0.1.0-draft.1 / `log-isd`。
- 与计划 §2 基线一致：被测为 `tests/module/cases` 全量；模块层为**本机隔离套件**——provider 为进程内 `FakeAdapter` 与 loopback `FakeUpstream`，HTTP 仅绑 `127.0.0.1:0` 临时端口（ENV-2），不触 LAN/m5air/真实 provider（方案 §1.6/§1.7）。
- 环境偏差及影响：
  - **证据版本绑定：本 Run pin 正确，无偏差（前序 Run 的该偏差已消除）**。`test-run.env.git_commit=f83f8da` 即被测树提交本身，且本 Run 执行时工作树在 `src/` 与 `tests/module/cases/` 下**无未提交修改**（唯一未提交改动为 harness `tests/common/harness/run_harness.sh`，不属于被测树；§2 的退出码字段一条即该改动）。前序 Run `run-20261002-01` 记录的 `git_commit=982efae` 落后被测树一个提交的问题，在本 Run 不再存在。
  - **退出码与 `PYTHONPATH` 仍未落进本 Run 的 `test-run.env`（已修 harness，但晚于本 Run）**：计划 §7 要求 Run 记录保存 `PYTHONPATH` 与 pytest 退出码。本 Run 的 `test-run.env` 只有上列 8 个字段——harness 已在工作树补录 `pythonpath` / `exit_code` / `pytest_exit_code` / `finished_at`（`tests/common/harness/run_harness.sh`），但该改动**在本 Run 开始之后**落地，故本 Run 证据不含这 4 个字段（记录粒度缺口，不影响判定）。等效事实可从既有机器产物判定：`artifacts/pytest.log` 末行 `354 passed`（pytest 退出码 0）、`case-status.json.release_blocking=false`（无 `FAIL`/`BLOCKED`/`INVALID`，与 runner 契约 `run_rc=0` 一致）；`PYTHONPATH=src` 由 `runner_module.sh` 在同一 shell 内 `export`，与计划 §6 入口一致，非环境错配。
  - **替身资产自检状态**：计划 §4 记 ENV-3/ENV-4 契约 `llmtier-unit-fakes` 为 `Ready（契约已建；自检 Run 待录制）`、`Unverified`；本 Run 使用其 `AppFixture`/`FakeAdapter` 与各测试模块本地 `FakeUpstream`/`FakeResponse` stub，**资产自检 Run 仍未录制**（不改变本 Run 判定，登记于 §8）。
  - **文档版本漂移（不影响本 Run 判定，已随本交付回溯更新）**：计划 §1/§3/§10 曾引用方案 `0.1.0-draft.6` 并记「68 份 `tests.module-case` 文档 0/68 已建」「模块可执行套件与 Run 证据未录」；方案 §3.6 曾写「module-case 文档本步尚未建立（下一交付步建立）」。实际 68 份 Case 文档（`docs/70_verification/module/cases/MT-*.md`）与 68 个脚本（`tests/module/cases/MT-*.py`）已建（`f83f8da`，本 Run 证据的来源）。**本交付已把两处表述回溯更新为实际状态**（方案 `0.1.0-draft.8`、计划 `0.1.0-draft.7`）；Case 清单、Case ID、四层分母 91/68 计数均未改动，故本报告的覆盖复算口径不变（见 §4/§8）。
- 证据版本绑定与待重验：
  - 本报告结论仅对「被测树＝`f83f8da` 内容」＋ `schema_version=2` ＋ `openapi_version=0.3-simplified-candidate.8` ＋ Python `3.14.3` 有效；`src/<module>/`、落库 schema、`interfaces/` 或 `pyproject.toml` 收集规则变更后须重跑并标「待重验」，不同基线的结果不合并统计。
  - 本 Run 无 `FAIL` 需保持 RED；其相对前序 Run 的唯一变化是被测树中的 ENV-3 夹具写侧修复（分块 flush），**该修复随 `f83f8da` 入库并被本 Run 的 pin 覆盖**（见 §6.2）。

## 3. 逐 Case 执行记录

本 Run 一条命令串行执行 `tests/module/cases` 全量，收集 354 个 pytest 测试函数。§3.1 按计划 §5.1 的模块批次汇总，§3.2 按方案 §3 的 68 个 Case 逐条列出。**每个 Case 的 Verdict 逐条读自 `tests/module/reports/run-20261002-02/<Case ID>.json` 的 `status` 字段**；逐测试函数的机器记录见 `artifacts/junit.xml` 与 `artifacts/pytest.log`。

> **粒度注（354 vs 68）**：方案 §3 的设计分母是 **68 个 Case**；`354` 是这 68 个 Case 的测试函数展开数（1–12 个/Case）。`case-status.json` 的 `counts` 按**测试函数**计数（`PASS=354`），其 `cases` 段按 **Case ID** 给出 68 条记录（68 `PASS`）。每份 `MT-*.json` 与 `case-status.json.cases.<Case ID>` 的 `node_id` **只登记该 Case 的一个代表节点**（`tools/test_report.py::build_report` 以 `case_id` 为键收敛，同 Case 的最后一个测试函数覆盖前值），该 Case 的其余测试函数结果以 `artifacts/junit.xml` 为准；同理 `time_seconds` 是该代表节点的耗时，**不是该 Case 的耗时合计**。这是 **Case ID 收敛口径**，不代表覆盖范围：68 个 Case 的全部 354 个测试函数均在 `artifacts/junit.xml` 中有独立记录。三者口径不同，无缺失、无虚计。

### 3.1 按模块 / 批次分组（方案 §3 × 计划 §5.1）

| 批次 | 模块（M-id） | Case 范围 | 分母层 / 分母行（方案 §3.7） | Case 数 | 测试函数数 | 执行状态 | Verdict | Run ID / 证据 |
|---|---|---|---|---|---|---|---|---|
| B1 | `util`（M007） | MT-UTIL-001..005 | ① MT-UTIL-001/002；②×3；④ T12-T13 | 5 | 19 | 全部执行 | PASS 5/5 | run-20261002-02 |
| B2 | `log`（M008） | MT-LOG-001..003 | ① MT-LOG-001；②×2；③ K10；④ T14 | 3 | 17 | 全部执行 | PASS 3/3 | run-20261002-02 |
| B3 | `http-api`（M001） | MT-API-001..013 | ①×3；②×9；③ K1-K2 | 13 | 51 | 全部执行 | PASS 13/13 | run-20261002-02 |
| B4 | `inference`（M003） | MT-INF-001..019 | ①×4；②×15；③ K4-K5；④ T1-T5 | 19 | 69 | 全部执行 | PASS 19/19 | run-20261002-02 |
| B5 | `management`（M004） | MT-MGMT-001..011 | ①×5；②×6；③ K3/K6-K7；④ T6-T8 | 11 | 60 | 全部执行 | PASS 11/11 | run-20261002-02 |
| B6 | `observability`（M005） | MT-OBS-001..004 | ①×1；②×3；④ T9 | 4 | 31 | 全部执行 | PASS 4/4 | run-20261002-02 |
| B7 | `libdiag`（M006） | MT-DIAG-001..007 | ①×2；②×5；③ K4/K8-K9；④ T9-T11 | 7 | 46 | 全部执行 | PASS 7/7 | run-20261002-02 |
| B8 | `web-ui`（M002） | MT-UI-001..006 | ①×2；②×4 | 6 | 61 | 全部执行 | PASS 6/6 | run-20261002-02 |
| BALL | 全量回归（8 模块） | 全部 68 Case | 91 条分母全覆盖 | 68 | 354 | 全部执行 | **PASS 68 / FAIL 0** | run-20261002-02 |

> Case 数与测试函数数逐批次取自 `artifacts/junit.xml`（按 `classname` 前缀 `MT-<OBJ>-<NNN>` 聚合）与 68 份 `MT-*.json`。P0 39 个 Case 全部 `PASS`、P1 29 个 Case 全部 `PASS`；分类分布（方案 §3.6）：negative 18 / boundary 13 / normal 11 / recovery 17 / security 6 / concurrency 3；本报告按逐 Case `status` 复算的分布与之一致。

### 3.2 逐 Case 明细（68 条，Verdict 取自 `MT-*.json`）

| Case ID | 模块 | 分母层（方案 §3） | 分类 | 优先级 | Verdict | Run 证据 | 测试函数数 |
|---|---|---|---|---|---|---|---|
| MT-API-001 | M001 http-api | ① | normal | P0 | PASS | `MT-API-001.json` | 4 |
| MT-API-002 | M001 http-api | ① | normal | P1 | PASS | `MT-API-002.json` | 4 |
| MT-API-003 | M001 http-api | ① | security | P1 | PASS | `MT-API-003.json` | 4 |
| MT-API-004 | M001 http-api | ② | negative | P0 | PASS | `MT-API-004.json` | 4 |
| MT-API-005 | M001 http-api | ② | negative | P0 | PASS | `MT-API-005.json` | 4 |
| MT-API-006 | M001 http-api | ②/③K1 | security | P0 | PASS | `MT-API-006.json` | 6 |
| MT-API-007 | M001 http-api | ② | boundary | P0 | PASS | `MT-API-007.json` | 5 |
| MT-API-008 | M001 http-api | ②/③K2 | recovery | P0 | PASS | `MT-API-008.json` | 3 |
| MT-API-009 | M001 http-api | ② | security | P1 | PASS | `MT-API-009.json` | 4 |
| MT-API-010 | M001 http-api | ② | normal | P1 | PASS | `MT-API-010.json` | 5 |
| MT-API-011 | M001 http-api | ②/③K1 | security | P0 | PASS | `MT-API-011.json` | 6 |
| MT-API-012 | M001 http-api | ② | recovery | P0 | PASS | `MT-API-012.json` | 1 |
| MT-API-013 | M001 http-api | ② | recovery | P1 | PASS | `MT-API-013.json` | 1 |
| MT-INF-001 | M003 inference | ① | normal | P0 | PASS | `MT-INF-001.json` | 3 |
| MT-INF-002 | M003 inference | ① | boundary | P0 | PASS | `MT-INF-002.json` | 6 |
| MT-INF-003 | M003 inference | ①/④T1/T2/T3 | recovery | P0 | PASS | `MT-INF-003.json` | 5 |
| MT-INF-004 | M003 inference | ①/④T4 | concurrency | P0 | PASS | `MT-INF-004.json` | 3 |
| MT-INF-005 | M003 inference | ② | negative | P0 | PASS | `MT-INF-005.json` | 4 |
| MT-INF-006 | M003 inference | ②/③K5 | negative | P0 | PASS | `MT-INF-006.json` | 4 |
| MT-INF-007 | M003 inference | ②/④T5 | concurrency | P0 | PASS | `MT-INF-007.json` | 5 |
| MT-INF-008 | M003 inference | ②/③K4 | recovery | P0 | PASS | `MT-INF-008.json` | 5 |
| MT-INF-009 | M003 inference | ②/④T1 | recovery | P0 | PASS | `MT-INF-009.json` | 2 |
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
| MT-MGMT-001 | M004 management | ①/④T6 | normal | P0 | PASS | `MT-MGMT-001.json` | 4 |
| MT-MGMT-002 | M004 management | ① | negative | P0 | PASS | `MT-MGMT-002.json` | 5 |
| MT-MGMT-003 | M004 management | ① | boundary | P0 | PASS | `MT-MGMT-003.json` | 4 |
| MT-MGMT-004 | M004 management | ① | normal | P1 | PASS | `MT-MGMT-004.json` | 5 |
| MT-MGMT-005 | M004 management | ① | negative | P1 | PASS | `MT-MGMT-005.json` | 5 |
| MT-MGMT-006 | M004 management | ②/④T7 | recovery | P0 | PASS | `MT-MGMT-006.json` | 7 |
| MT-MGMT-007 | M004 management | ②/③K6/④T8 | negative | P0 | PASS | `MT-MGMT-007.json` | 9 |
| MT-MGMT-008 | M004 management | ② | negative | P0 | PASS | `MT-MGMT-008.json` | 6 |
| MT-MGMT-009 | M004 management | ②/③K3 | boundary | P0 | PASS | `MT-MGMT-009.json` | 6 |
| MT-MGMT-010 | M004 management | ②/③K7 | negative | P1 | PASS | `MT-MGMT-010.json` | 6 |
| MT-MGMT-011 | M004 management | ② | negative | P1 | PASS | `MT-MGMT-011.json` | 3 |
| MT-OBS-001 | M005 observability | ① | normal | P1 | PASS | `MT-OBS-001.json` | 5 |
| MT-OBS-002 | M005 observability | ②/④T9 | normal | P1 | PASS | `MT-OBS-002.json` | 9 |
| MT-OBS-003 | M005 observability | ② | boundary | P1 | PASS | `MT-OBS-003.json` | 10 |
| MT-OBS-004 | M005 observability | ② | recovery | P1 | PASS | `MT-OBS-004.json` | 7 |
| MT-DIAG-001 | M006 libdiag | ①/④T9 | boundary | P1 | PASS | `MT-DIAG-001.json` | 8 |
| MT-DIAG-002 | M006 libdiag | ① | negative | P0 | PASS | `MT-DIAG-002.json` | 6 |
| MT-DIAG-003 | M006 libdiag | ②/③K8 | negative | P0 | PASS | `MT-DIAG-003.json` | 9 |
| MT-DIAG-004 | M006 libdiag | ②/④T10/T11 | negative | P0 | PASS | `MT-DIAG-004.json` | 6 |
| MT-DIAG-005 | M006 libdiag | ②/③K4 | boundary | P1 | PASS | `MT-DIAG-005.json` | 6 |
| MT-DIAG-006 | M006 libdiag | ②/③K9 | boundary | P1 | PASS | `MT-DIAG-006.json` | 6 |
| MT-DIAG-007 | M006 libdiag | ② | recovery | P1 | PASS | `MT-DIAG-007.json` | 5 |
| MT-UI-001 | M002 web-ui | ① | normal | P1 | PASS | `MT-UI-001.json` | 9 |
| MT-UI-002 | M002 web-ui | ① | normal | P0 | PASS | `MT-UI-002.json` | 12 |
| MT-UI-003 | M002 web-ui | ② | negative | P0 | PASS | `MT-UI-003.json` | 11 |
| MT-UI-004 | M002 web-ui | ② | normal | P1 | PASS | `MT-UI-004.json` | 10 |
| MT-UI-005 | M002 web-ui | ② | boundary | P1 | PASS | `MT-UI-005.json` | 9 |
| MT-UI-006 | M002 web-ui | ② | negative | P1 | PASS | `MT-UI-006.json` | 10 |
| MT-UTIL-001 | M007 util | ① | boundary | P0 | PASS | `MT-UTIL-001.json` | 4 |
| MT-UTIL-002 | M007 util | ①/④T12 | recovery | P0 | PASS | `MT-UTIL-002.json` | 4 |
| MT-UTIL-003 | M007 util | ② | boundary | P0 | PASS | `MT-UTIL-003.json` | 4 |
| MT-UTIL-004 | M007 util | ② | recovery | P0 | PASS | `MT-UTIL-004.json` | 4 |
| MT-UTIL-005 | M007 util | ②/④T13 | recovery | P1 | PASS | `MT-UTIL-005.json` | 3 |
| MT-LOG-001 | M008 log | ① | security | P0 | PASS | `MT-LOG-001.json` | 6 |
| MT-LOG-002 | M008 log | ②/③K10 | security | P0 | PASS | `MT-LOG-002.json` | 7 |
| MT-LOG-003 | M008 log | ②/④T14 | negative | P1 | PASS | `MT-LOG-003.json` | 4 |

> 68 份 `MT-*.json` 的 `reason` 字段全为空串（无失败/阻塞/无效原因），`artifacts` 与 `redactions` 均为空数组，`started_at` 全部为 `2026-10-02T09:15:23Z`。「测试函数数」列取自 `artifacts/junit.xml` 按 Case 聚合，非估算。

### 3.3 副作用与清理（逐 Case 口径）

| 项目 | 结果已知性 | 副作用 | 清理状态 |
|---|---|---|---|
| 全部 68 Case（ENV-1 组装隔离库为主） | 可独立判定：经被测模块公开入口驱动，断言 wire 信封 / 公开返回 / 落库行 + 关键内部 seam | 每 Case 在 `setUp` 新建 `tempfile.TemporaryDirectory` + 新 SQLite + 真实组装栈（`tests/common/fakes.py::AppFixture`）；初态经公开入口播种（方案 §1.5 规则 1） | 每 Case `tearDown` 调 `AppFixture.close()`（`store.close()` + `temp.cleanup()`）销毁临时目录；Case 间无共享可变状态 |
| 经 HTTP 的 Case（ENV-2，`MT-API-*`/`MT-OBS-*`/经 HTTP 的 `MT-MGMT-*`/`MT-DIAG-*`） | 可独立判定（真实 socket + 真实 `ThreadingHTTPServer` handler 栈） | loopback `127.0.0.1:0` 随机端口上的真实请求 | `tearDownClass`/`tearDown` 调 `server.shutdown()` + `server_close()` + `AppFixture.close()`（`tests/module/cases/support/http_env.py`） |
| `MT-INF-*`（ENV-3 loopback `FakeUpstream` / `FakeAdapter`） | 可独立判定（真实 `OpenAIProvider` 传输 + 边界外替身） | loopback 临时端口 + 经公开 Registry 入口接线的假上游 | `InferenceEnv.tearDown` 停上游；`AppFixture.close()` 销毁临时库 |
| 存储面注入 Case（`MT-UTIL-004/005`、`MT-DIAG-007`、`MT-OBS-004`、`MT-INF-009`） | 可独立判定（真实写失败/损坏/回滚） | 仅作用于该 Case 自己的临时库（`DROP TABLE`、损坏库、迁移中途失败） | 随临时目录销毁；无跨 Case 残留 |
| 传输病态 Case（`MT-API-012/013`） | 可独立判定（真实客户端 `close()` / `SO_LINGER 0` RST） | 真实 socket 中途断开 | 两 Case 自身取 `/dev/fd` 基线并断言无泄漏；`tearDownClass` 关停 loopback 实例释放端口 |
| 本 Run 整体 | 68 Case 串行于单一 pytest 进程 | 不触 LAN / m5air / 真实 provider；无外部共享资源 | 套件 102.74s 结束；未产生需人工清理的持久资源 |

## 4. 偏差、无效执行与重跑

### 4.1 前序 Run 的 FAIL 记录（已关闭，旧证据保留）

| 偏差 / 无效项 | 原因 | 影响 Case | 处置与重跑 Run |
|---|---|---|---|
| **前序 Run `run-20261002-01` 的 FAIL**：`MT-INF-015` `OversizeTests::test_two_megabyte_output_normalized`，`ApiError: (503, 'provider_unavailable', 'Provider streaming request failed: TimeoutError: timed out')`，节点耗时 60.133s | ENV-3 边界替身 `tests/module/cases/support/upstream.py::Handler._send` 一次性写出整个 2 MiB body，在负载下卡在客户端 socket 缓冲，表现为上游 60s 无进展 → 读侧流空闲超时 | MT-INF-015（层②，boundary，P1；方案 §1.5.1 c3） | **已修**（64 KiB 分块写出 + 逐块 `flush()`，随 `f83f8da` 入库）→ **以新 Run `run-20261002-02` 复跑**，`MT-INF-015` 取得 `PASS`（同一代表节点 0.517s）。按计划 §7「重跑生成新 Run，不覆盖旧失败」，`run-20261002-01/` 全部原始证据（含 `MT-INF-015.json` 的 `status=FAIL`、`artifacts/junit.xml` 的 `failures="1"`、`artifacts/pytest.log`）**原样保留**。缺陷 `D-MT-INF-015-1` 已关闭（见 §6.1） |

### 4.2 本 Run 的偏差登记

| 偏差 / 无效项 | 原因 | 影响 Case | 处置与重跑 Run |
|---|---|---|---|
| **Run 证据字段缺口**：`test-run.env` 未记录 `pythonpath` 与 `exit_code`/`pytest_exit_code`/`finished_at`（计划 §7 要求保存） | harness 把 `PYTHONPATH=src` 放在 runner 内 `export`，退出码只在 runner 退出时体现；本 Run 执行时 harness 尚未补录这 4 个字段（补录改动在本 Run 开始之后落地） | 无（仅影响记录粒度，不改变逐 Case 判定） | **harness 已修**（`tests/common/harness/run_harness.sh` 新增 `pythonpath` / `exit_code` / `pytest_exit_code` / `finished_at`），**下一次模块 Run 起落证据**；本 Run 的判定只取 `counts` 与逐 Case `status`，等效退出码事实见 §2 |
| **文档版本漂移**（本交付已回溯更新）：计划曾引用方案 `0.1.0-draft.6` 且记「0/68 Case 文档已建」「套件与 Run 证据未录」；方案 §3.6 曾记「module-case 文档本步尚未建立」 | 68 份 Case 文档与脚本在 `f83f8da` 建成后，两处表述未同步 | 无（Case 清单、ID、四层分母计数未变） | 已随本交付更新为实际状态（方案 `0.1.0-draft.8`、计划 `0.1.0-draft.7`）；本报告覆盖复算以方案 §3/§3.7 为准 |
| **替身资产自检 Run 未录制**（ENV-3/ENV-4 契约 `llmtier-unit-fakes` 为 `Implemented`/`Unverified`） | 资产自检属独立 Gate，尚未安排 | 无 | 登记于 §6.4/§8；不改变本 Run 判定 |
| 无失败（`FAIL`） | 本 Run 68 Case 全 `PASS`，`counts.FAIL=0`、`release_blocking=false` | — | — |
| 无无效执行（`INVALID`） | 注入类 Case 均以注入生效的可观测后果断言（见 §5.3），未出现「配置但未生效」 | — | — |
| 无 `BLOCKED` / `NOT_RUN` / `SKIP` / `XPASS` | 无环境缺失；68 Case 全部收集并执行，354 个测试函数无 skip/xfail | — | — |
| 重跑历史：1 次 | 本 Run 为模块层第 2 个 Run（`tests/module/reports/` 下仅 `run-20261002-01`、`run-20261002-02`），因前序 Run 的 `MT-INF-015` FAIL 而按 §7 规则新开 Run | — | 见 §4.1 |

## 5. 覆盖复算（对照方案分母）

分母权威＝方案 `llmtier-module-test-scheme` v0.1.0-draft.8 §3（四层：① 接口行为 20 ＋ ② 内部分支 47 ＋ ③ 组合 10 ＋ ④ 状态迁移 14 ＝ **91 条**），展开为 §3 的 **68 个 Case**；VRC 只作追溯（方案 §3.5/附录 A），不作分母。分母＝91 条，Case＝68 个，二者不同粒度。

### 5.1 四层分母闭合表

| 分母层 | 分母数（方案 §3） | 映射到的 Case 数 | 已执行 Case | 其中 `PASS` | 其中 `FAIL` | 未覆盖（分母无 Case / Case 未执行） |
|---|---|---|---|---|---|---|
| ① 对外接口端到端行为（§3.1） | 20 | 20（1:1） | 20 | 20 | 0 | **0** |
| ② 内部分支（§3.2） | 47 | 47（每分支 1 Case） | 47 | 47 | 0 | **0** |
| ③ 组合行（§3.3 K1–K10） | 10 | 12（含 K1 落地的 `MT-API-011`，其分母计入本层） | 12 | 12 | 0 | **0** |
| ④ 状态迁移（§3.4 T1–T14） | 14 | 13（T1/T2/T3 合并到 `MT-INF-003`＋`MT-INF-009` 等） | 13 | 13 | 0 | **0** |
| **合计** | **91** | **68 个去重 Case** | **68** | **68** | **0** | **0** |

- 粒度说明：层② 47 条 = 方案 §3.2 的 48 行减去 1 条「组合落地 Case」`MT-API-011`（方案 §3.2 尾注：其分母计入层③）；因此 20（①）＋ 47（②）＋ 1（`MT-API-011` 归③）＝ 68 个 Case，无重复计分母、无遗漏。
- 逐层未覆盖复核：91 条分母每条的「映射 Case」列（方案 §3.2/§3.3/§3.4/§3.7）在本 Run **全部有对应 Case 且该 Case 已执行并出 `PASS`**；**未覆盖 0 条、无静默消失的分支/组合/迁移**（计划 §8「分支/组合/迁移覆盖达标门」满足）。
- 逐层 Verdict 偏差：**0 条**（层② 的 `M003-超大 response 归一`（方案 §1.5.1 c3）→ `MT-INF-015` 在本 Run 为 `PASS`；前序 Run 的该项 FAIL 已在 §4.1 登记并关闭）。

### 5.2 异常/错误注入矩阵封闭核对（方案 §1.5.1，53 条；Oracle ＝ `src/`）

封闭判据：每行必须映射到 ≥1 个 `MT-*` Case 或具名 Gap；**0 静默缺失**。本 Run 逐行核对结果如下（Verdict 取自对应 `MT-*.json`，本 Run 全部 `PASS`）。

**(a) 每个对外 error code（37 条）**

| # | `code` | status（`src/`） | 映射 Case | 本 Run Verdict |
|---|---|---|---|---|
| a1 | `invalid_request` | 400 | `MT-API-007` / `MT-INF-005` / `MT-MGMT-007` | PASS |
| a2 | `unsupported_request` | 400 | `MT-INF-005` / `MT-INF-006` | PASS |
| a3 | `unsupported_field` | 400 | `MT-INF-005` | PASS |
| a4 | `unsupported_model` | 400 | `MT-INF-006` | PASS |
| a5 | `invalid_json` | 400 | `MT-API-007` | PASS |
| a6 | `request_too_large` | 413 | `MT-API-007` | PASS |
| a7 | `unsupported_dimensions` | 400 | `MT-INF-010` | PASS |
| a8 | `authentication_required` | 401 | `MT-API-006` | PASS |
| a9 | `permission_denied` | 403 | `MT-API-006` / `MT-MGMT-009` | PASS |
| a10 | `auth_not_configured` | 503 | `MT-API-006` | PASS |
| a11 | `model_not_found` | 404 | `MT-INF-007` | PASS |
| a12 | `not_found` | 404 | `MT-API-004` / `MT-MGMT-007` | PASS |
| a13 | `resource_conflict` | 409 | `MT-MGMT-007` | PASS |
| a14 | `capability_conflict` | 409 | `MT-MGMT-008` | PASS |
| a15 | `embedding_space_conflict` | 409 | `MT-MGMT-008` | PASS |
| a16 | `fixed_service_level` | 409 | `MT-MGMT-011` | PASS |
| a17 | `resource_in_use` | 409 | `MT-MGMT-007` | PASS |
| a18 | `version_conflict` | 412 | `MT-MGMT-007` | PASS |
| a19 | `cursor_expired` | 400 | `MT-MGMT-009` / `MT-DIAG-006` | PASS |
| a20 | `rate_limit_exceeded` | 429 | `MT-INF-007` / `MT-INF-008` / `MT-INF-018` | PASS |
| a21 | `provider_unavailable` | 503 | `MT-INF-003` / `MT-INF-008` / `MT-INF-013` / `MT-INF-014` | PASS |
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

- **(a)/(b)/(c) 汇总核对**：37 ＋ 8 ＋ 8 ＝ **53 条，每条均映射到已执行 Case，0 静默缺失、0 映射 Case 非 `PASS`**。10 个新增分支 Case（`MT-MGMT-011`、`MT-API-012/013`、`MT-INF-013…019`）承接 a16/a24、b4/b8、c1–c8 共 20 条，本 Run 全部 `PASS`。
- **真实 socket 专证（c4/c5，计划 §7/§8 要求）**：`MT-API-012`（客户端读首帧后 `close()`）与 `MT-API-013`（`SO_LINGER 0` 后 `close()` 触发 RST）均在 ENV-2 `ThreadingHTTPServer` 的真实 socket 上以真实客户端执行（未用进程内对象替代），本 Run 均 `PASS`；两 Case 自身在断开前后取 `/dev/fd` 基线（`_fds()`）并断言无 fd 泄漏，同时经 `/v1/runtime` 断言 `running` 归零（Router 许可释放）、账本不变。c1/c2 由 `MT-INF-013/014` 命中建连/流空闲超时；c3 由 `MT-INF-015` 的 2 MiB 单帧响应归一（分块 flush 后代表节点 0.517s，方案 §4 已记「已修」）；c8 由 `MT-INF-018` 断言 429 + `Retry-After` 与许可归零，全部 `PASS`。
- **design-vs-code 偏差的处置（`G-INF-NONJSON-MAPPING-1`）**：方案 §1.5.1 的 a25/b4/c7 三行把「非 JSON `data:` 帧 / 非 JSON embeddings 响应体」预期为 `502 provider_contract_error`；`src/` 实测为 **`503 provider_unavailable`（`retryable=true`）**，因 `OpenAIProvider.complete/_request` 把 `json.JSONDecodeError` 归入传输异常类。按方案 §4 的裁决（**Oracle ＝ `src/`，实测为准**），`MT-INF-017` 以 `src/` 断言：非 SSE Content-Type/多 terminal/terminal-status 矛盾/无合法 terminal → 502；非 JSON `data:` 帧 → 503；embeddings 非 JSON 体 → 503；且断言账本不伪装成功（`measurement_status=unknown`、tokens 为 NULL 不补零）。本 Run `MT-INF-017` **4 个测试函数全 `PASS`**（`test_non_sse_content_type_is_502` / `test_non_json_data_frame_maps_503_per_src` / `test_non_json_embeddings_body_maps_503_per_src` / `test_malformed_stream_never_fakes_success`），即该偏差**按设计侧登记、以 `src/` 为准断言通过**，未被改判为 PASS 掩盖、未把 503 写成 502。恢复条件（设计侧确认权威映射、或建立 `interfaces/error-codes/` 机器目录）挂在 §8。

### 5.3 注入类方法命中门（方案 §1.5/§3.7 注入面核对块；计划 §8）

主手段＝边界替身返回错误数据/行为；产品 diagnostics 注入为**可选补充**（ENV-4）。判定规则：替身按配置返回错误即视为命中，判定＝模块对该错误的映射；产品注入须命中方可判定，未命中即 `INVALID`。本 Run `INVALID=0`，注入类方法逐面命中如下：

| 注入分类 | 注入面 / 数据类型 | 映射 Case | 本 Run Verdict |
|---|---|---|---|
| 故障注入 | mock 返回 **5xx**（上游错误响应） | `MT-INF-003` / `MT-INF-008` | PASS |
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

### 5.4 设计验证项（VRC）追溯复核（33 项，非分母）

方案 §3.5/附录 A：VRC 在本层只作追溯列。33 项 `VRC-*` 每项至少映射 1 个本层 Case：

| VRC ID | 要验证什么 | 本层 Case | 本 Run Verdict |
|---|---|---|---|
| VRC-API-001 | 分发/错误/资源 | `MT-API-001` | PASS |
| VRC-API-002 | 鉴权 | `MT-API-006` | PASS |
| VRC-API-003 | body 与 SSE | `MT-API-007` | PASS |
| VRC-API-004 | 静态与健康 | `MT-API-003` | PASS |
| VRC-UI-001 | 加载与状态 | `MT-UI-001` | PASS |
| VRC-UI-002 | 编辑/鉴权 | `MT-UI-002` | PASS |
| VRC-UI-003 | Pause 边界 | `MT-UI-002` | PASS |
| VRC-UI-004 | 用量未知不填零 | `MT-UI-002` | PASS |
| VRC-UI-005 | 探测付费确认 | `MT-UI-002` | PASS |
| VRC-UI-006 | 诊断页 | `MT-UI-002` | PASS |
| VRC-INF-001 | 推理与流式契约 | `MT-INF-001` | PASS |
| VRC-INF-002 | 向量化契约 | `MT-INF-002` | PASS |
| VRC-INF-003 | 失败与用量 | `MT-INF-003` | PASS |
| VRC-INF-004 | 准入与目录 | `MT-INF-004` | PASS |
| VRC-INF-005 | 观测 fail-open | `MT-INF-011` | PASS |
| VRC-MGMT-001 | 引导与 Secret 引用 | `MT-MGMT-001` | PASS |
| VRC-MGMT-002 | CRUD 与不变量 | `MT-MGMT-002` | PASS |
| VRC-MGMT-003 | 审计与日志 | `MT-MGMT-002` | PASS |
| VRC-MGMT-004 | 分页与清空 | `MT-MGMT-003` | PASS |
| VRC-MGMT-005 | 探测 | `MT-MGMT-004` | PASS |
| VRC-MGMT-006 | 账号用量 | `MT-MGMT-005` | PASS |
| VRC-OBS-001 | 开关 | `MT-OBS-001` | PASS |
| VRC-OBS-002 | 快照/统计查询与脱敏 | `MT-OBS-001` | PASS |
| VRC-OBS-003 | 注入与 fail-open | `MT-OBS-004` | PASS |
| VRC-OBS-004 | trace 与关联标识 | `MT-API-010` / `MT-OBS-001` | PASS |
| VRC-OBS-005 | trace 时间窗 | `MT-OBS-001` | PASS |
| VRC-DIAG-001 | 开关 | `MT-DIAG-001` | PASS |
| VRC-DIAG-002 | 记录与查询 | `MT-DIAG-001` | PASS |
| VRC-DIAG-003 | fail-open | `MT-DIAG-007` | PASS |
| VRC-DIAG-004 | 注入与 traces | `MT-DIAG-002` | PASS |
| VRC-UTIL-001 | 连接与回收 | `MT-UTIL-001` | PASS |
| VRC-UTIL-002 | 事务与迁移 | `MT-UTIL-002` | PASS |
| VRC-LOG-001 | 脱敏与查询 | `MT-LOG-001` | PASS |

> 33/33 `VRC-*` 均有本层 Case 且已执行并 `PASS`。追溯覆盖 ＝ 33/33，**不替代四层分母（91 条）的行为覆盖结论**（方案 §3.5 注）。

### 5.5 覆盖复算小结

- 分母 91 条每条有着落：0 未映射、0 未执行、0 `NOT_RUN`；68 个 Case 全部执行并出 Verdict（**68 `PASS` / 0 `FAIL`**）。
- 53 条异常/错误矩阵项每条有着落且映射 Case 全 `PASS`，含 1 条 design-vs-code 偏差按 Oracle＝`src/` 断言通过并具名登记。
- 注入类方法 13 个注入面/数据类型全部命中（0 未命中、0 `INVALID`），产品诊断注入作为可选补充亦全部命中。
- 33 个 `VRC-*` 追溯覆盖 33/33（仅追溯，非分母）。

## 6. 缺陷与残余风险

### 6.1 缺陷清单（关联 Case 与 Run）

| 缺陷 ID | 关联 Case / Run | 严重度 | 状态 | 事实（取自 Run 证据） | Owner / 关闭事实 |
|---|---|---|---|---|---|
| `D-MT-INF-015-1` | `MT-INF-015`（层②，boundary，P1；方案 §1.5.1 c3）／发现于 run-20261002-01，关闭于 run-20261002-02 | 中（P1；不涉及 P0 分母、鉴权或数据正确性） | **CLOSED**（已修复并以新 Run 复跑验证） | 原始事实（`run-20261002-01`）：`OversizeTests::test_two_megabyte_output_normalized` FAIL，`http_api.errors.ApiError: (503, 'provider_unavailable', 'Provider streaming request failed: TimeoutError: timed out')`，节点耗时 60.133s。**根因在 ENV-3 夹具写侧**（`tests/module/cases/support/upstream.py::Handler._send` 一次性写出 2 MiB body → 卡客户端 socket 缓冲 → 60s 无进展），非被测实现缺陷。**关闭事实（`run-20261002-02`）**：改为 64 KiB 分块写出 + 逐块 `flush()`（随 `f83f8da` 入库）后，`MT-INF-015.json` `status=PASS`、`reason` 空，代表节点耗时 **0.517s**，该 Case 3 个测试函数全 `PASS` | Owner：LLMTier（M003 inference ＋ ENV-3 loopback `FakeUpstream` 夹具）。**关闭依据**：新 Run `run-20261002-02` 的 `MT-INF-015.json`（`status=PASS`）、`case-status.json`（`counts.FAIL=0`）、`artifacts/junit.xml`（`failures="0"`）、`artifacts/pytest.log`（`354 passed`）。**旧 Run 证据不覆盖**（计划 §7） |

> 本 Run 无其他 `FAIL`；无 `BLOCKED`/`INVALID`/`NOT_RUN`/`SKIP`/`XPASS`；未发现测试报告/工具缺陷（`tools/test_report.py` 的 `MT-*` Case ID 正则与平铺证据布局修复已随被测树 `f83f8da` 入库并在本 Run 生效，本 Run 正常产出 68 份 `MT-*.json` ＋ `case-status.json` ＋ `artifacts/`）。

### 6.2 本轮已修的产品/工具/夹具缺陷（回归在本 Run 内体现）

| 已修项 | 事实 | 回归证据（本 Run） |
|---|---|---|
| ENV-3 `FakeUpstream` 一次性写大 body（`tests/module/cases/support/upstream.py::Handler._send`） | 真实 SSE 上游是流式投递的；一次性 `write(2 MiB)` 在负载下卡在客户端 socket 缓冲，表现为上游 60s 无进展 → 读侧流空闲超时 → 503 `provider_unavailable`。已改为 64 KiB 分块写出 + 逐块 `flush()` | `MT-INF-015` 3 个测试函数全 `PASS`（代表节点 0.517s）；方案 §4 已记「已修」；原缺陷 `D-MT-INF-015-1` 关闭（§6.1） |
| `stream_idle_timeout` 静默 no-op（`src/inference/providers/openai.py::_stream_read_timeout`） | Python 3.14 `SocketIO` 无 `settimeout`，原实现 `except: pass` 静默 no-op → 读阶段回落到 `connect_timeout`（默认 30s），`stream_idle_timeout` 形同虚设；已补 `response.fp.raw._sock.settimeout(...)` 兜底 | `MT-INF-014` 命中流空闲超时并 `PASS`；`MT-INF-013/016/017` 同族 `PASS` |
| 模块用例无法被目录发现收集（`pyproject.toml` `python_files`） | 收集规则缺 `MT-*.py`，`pytest tests/module/cases` 收不到模块用例 | 本 Run `collected 354 items`（`artifacts/pytest.log`） |
| 逐 Case 证据无法生成（`tools/test_report.py` Case ID 正则） | Case ID 文件名正则缺 `MT-*`，逐 Case JSON 与平铺证据布局不成立 | 本 Run 生成 68 份 `MT-*.json` ＋ `case-status.json`，字段与 run_id/git_commit 全部一致（§2） |
| Run 证据未记录 `PYTHONPATH` 与退出码（计划 §7） | harness 把 `PYTHONPATH=src` 放在 runner 内 `export`，退出码只在 runner 退出时体现；已在 `tests/common/harness/run_harness.sh` 补录 `pythonpath` / `exit_code` / `pytest_exit_code` / `finished_at` | **本 Run 执行早于该 harness 改动，`test-run.env` 仍为 8 字段**（§2/§4.2）；下一次模块 Run 起可验证该字段落地 |

> **未修、按设计侧/实现侧具名挂起**（不改判本 Run 判定）：trace stage 同毫秒乱序（`G-OBS-STAGE-ORDER-1`，`MT-OBS-001` 只断言 stage 集合与非递减时戳，不断言位置序）；`/login` 路由缺失（`G-UI-LOGIN-ROUTE-1`，loopback `GET /login` 实测 404 `not_found`，`MT-UI-003` 的 401 分支只做静态契约断言与服务端锚点）。

### 6.3 方案 §4 缺口与观察项在本 Run 的落点

| 项 | 分类 | 本 Run 事实 | Owner | 恢复条件 |
|---|---|---|---|---|
| `G-INF-NONJSON-MAPPING-1`（非 JSON `data:` 帧 / 非 JSON embeddings 体：矩阵预期 502，`src/` 实测 503） | design-vs-code 缺口 | `MT-INF-017` 按 Oracle＝`src/` 断言 503 并 4/4 `PASS`；偏差未被掩盖（见 §5.2） | M003 inference ＋ 系统设计 §7.8 | 设计侧确认权威映射（503，或改实现为 502）后回溯修订 §1.5.1 a25/b4/c7；若建立 `interfaces/error-codes/` 目录以其为准 |
| `G-OBS-STAGE-ORDER-1`（trace stage 因果序：毫秒精度 + 随机 `tev_<uuid4>` 主键 → 同毫秒乱序） | design-vs-code 缺口 | `MT-OBS-001` 只断言 stage 集合与非递减时戳，**位置序未断言**；本 Run `PASS` | M006 libdiag | 增加每请求单调序号列或改 `ORDER BY rowid` 后，回溯修订 `VRC-OBS-004` 并把位置序断言补入 `MT-OBS-001` |
| `G-UI-LOGIN-ROUTE-1`（`app.js` `LOGIN_URL='/login'`，M001 无 `/login` 路由） | design-vs-code 缺口 | `MT-UI-003` 的 401 分支只做静态契约断言与服务端锚点，未做 `/login` 端到端；本 Run `PASS` | M002 web-ui ＋ M001 http-api | M001 提供 `/login`（或 ISD 改指真实登录入口）后，补 `/login` 端到端断言 |
| `O-OBS-STORECODE-1`（`_store_read` 把存储读失败统一映射 `usage_store_unavailable`，诊断查询面复用同 code） | 观察项（非阻断） | 第二个映射点为 `MT-OBS-003`（存储不可读 → 503 不伪装空页），本 Run `PASS` | M001 | 错误目录按面细分 `code` 时回溯修订 a27；否则把 a27 映射 Case 补记 `MT-OBS-003` |
| `O-UI-HEALTHDOMAIN-1`（`backendState` 4 个 health 分支在 `src/` 内无写点；`degraded` 合法但 UI 无分支） | 观察项 | `MT-UI-004` 对无写点取值只做静态契约断言；本 Run `PASS` | M002 web-ui | health 域扩展（如探测中态写入）后在 `MT-UI-004` 补行为级断言 |
| `O-UI-USAGEOK-1`（`usageSummary` 的 `ok` 分支需真实 provider 响应，M004 provider HTTP 面无边界替身资产） | 观察项 | `MT-UI-005` 只静态断言渲染分支（含 Unknown≠0）；本 Run `PASS` | M002 ＋ M004 | 为 account-usage 面建 `tests.asset-design` 替身后补行为级断言 |
| `G-TRANSPORT-BUDGET-1`（c3 超 2 MB **下游响应**资源预算） | Gap（跨层） | 本层只断言模块内归一不崩溃（`MT-INF-015`，本 Run `PASS`，§4.1）；下游预算未测 | LLMTier（系统层） | 系统层预算用例建立并引用本行 |
| c4/c5 真实**跨主机**网络 RST/半开连接 | Tailored-N/A（本层仅 loopback ENV-2 真实 socket） | `MT-API-012/013` 已覆盖 loopback 内可复现断连，本 Run `PASS` | LLMTier | 跨主机链路病态归系统/运维层 |
| 跨模块系统级流程（systemd/反向代理/Piko 联调）、真实 provider 协议与 wire 互操作、浏览器 E2E | Tailored-N/A | 本层不测（本 Run 未涉及） | 系统测试方案 `llmtier-system-test-scheme`／契约层 | 各自承接方建立对应用例 |
| performance / endurance 分类 | Tailored-N/A | 本层不纳入（方案 §2） | 系统测试方案 | 同上 |
| M002 `VRC-UI-001..006` 的**行为级**（真实 JS 执行） | Tailored-N/A | 本层 `MT-UI-*` 为静态产物/契约组装（61 个测试函数全 `PASS`）；行为级由系统层真实浏览器 `ST-UI-001..010` 承接 | M002 web-ui ＋ 系统层 | 已在系统层承接（`RISK-UI-EXEC-1` 已关闭） |

### 6.4 残余风险与本层已知限制

- **层级边界（最重要）**：**module PASS ≠ system PASS**；本层 `PASS` 不替代也不蕴含系统层结论。**下层单元 PASS 不关闭本层**（本层分母独立来自模块设计 §9/§14 与 `src/` 分支），**本层 PASS 不关闭上层**（wire 互操作、OpenAPI 端到端一致性、真实上游 provider 协议、浏览器 E2E 由 `llmtier-system-test-scheme` 承接）。
- **本层不测的范围**：跨模块系统级流程与进程装配（启动/systemd/反向代理/Piko 联调）；真实 provider 协议与 wire/OpenAPI 端到端一致性；浏览器 E2E 与真实 JS 行为级（归系统层 `ST-UI-*`，`MT-UI-*` 仅为静态产物/契约层快速下位防线）；性能/耐久/容量预算（归系统层）。
- **替身边界**：上游 provider 为进程内 `FakeAdapter` 与 loopback `FakeUpstream`，**不证明真实 provider 协议**；M004 account-usage HTTP 面的本地 stub 无共享资产契约（`O-UI-USAGEOK-1`）。ENV-3 夹具写侧本轮修过（§6.2），说明**替身自身的传输行为是本层判定的前置条件**；替身缺陷会被记为被测 Case 的 `FAIL`，须按 §4.1 的方式归因区分「替身缺陷」与「实现缺陷」。
- **已被削弱/未覆盖的断言（诚实保留）**：`MT-OBS-001` 未断言 trace stage 位置序（`G-OBS-STAGE-ORDER-1`）；`MT-UI-003/004/005/006` 的部分分支为静态契约断言而非行为级（`G-UI-LOGIN-ROUTE-1`、`O-UI-HEALTHDOMAIN-1`、`O-UI-USAGEOK-1`）。
- **替身资产未自检**：ENV-3/ENV-4 契约 `llmtier-unit-fakes` 仍为 `Implemented`/`Unverified`，资产自检 Run 未录制；本 Run 的 `PASS` 结论以「替身按设计返回」为前提，该前提尚无独立 Run 证据。
- **记录粒度缺口**：本 Run `test-run.env` 缺 `pythonpath`/退出码/`finished_at`（§2/§4.2），退出码事实靠 `pytest.log`/`release_blocking` 间接判定；harness 已补录，下一 Run 生效。
- **历史 flake 已归因关闭，非「未复现」类 RED**：`D-MT-INF-015-1` 有确定根因（ENV-3 写侧非分块）、有修复、有新 Run 复跑证据（60.133s → 0.517s），属**已关闭**；本 Run 证据中无「未复现/未关闭」类 RED 需保留（`artifacts/pytest.log` 无任何 `F`/`E`/`s` 标记）。
- **Run 证据可追溯性**：本 Run `test-run.env.git_commit=f83f8da` 与被测树一致、无未提交改动落在 `src/` 与 `tests/module/cases/`，前序 Run 的 pin 落后问题已消除，证据具备常规的不可变标识性质。

## 7. Gate 结论与建议

- Gate 结论（接受/条件接受/拒绝）：**接受（模块层闭合）**——按计划 §8 口径给出，**非批准**。
  - 闭合分母＝方案 §3 的 **68 个 Case**（非 33 个 VRC）：**68/68 `PASS`**，满足「全部 68 Case 有 `PASS`」的闭合条件，故**判闭合**。
  - `FAIL=0`、`BLOCKED=0`、`INVALID=0`、`NOT_RUN=0`、`SKIP=0`、`XPASS=0`（`case-status.json.counts`；`release_blocking=false`）。
  - **P0 39 个 Case 全部 `PASS`**，无任一 P0 处于 `NOT_RUN`/`BLOCKED`（计划 §8 的 P0 硬门满足）。
  - **分支/组合/迁移覆盖达标门满足**：91 条四层分母（①20/②47/③10/④14）**全部映射到已执行 Case，0 未覆盖**；33/33 `VRC-*` 追溯覆盖（追溯非分母）。
  - **注入类方法命中门满足**：「mock 返回」6 类 ＋ 存储/传输/准入 3 面 ＋ 数据注入 4 类共 13 个注入面/数据类型全部命中（`INVALID=0`）；产品诊断注入（ENV-4）作为可选补充亦全部命中生效。
  - **异常/错误矩阵封闭门满足**：53 条（(a)37＋(b)8＋(c)8）全部逐行映射，0 静默缺失，**53/53 映射 Case 均 `PASS`**（含 c3 → `MT-INF-015`，该行在前序 Run 为 `FAIL`、本 Run 已 `PASS`）；`G-INF-NONJSON-MAPPING-1` 按 Oracle＝`src/` 断言并具名登记。
  - **闭合不影响未决项**：`D-MT-INF-015-1` 已关闭；§6.3 的 `G-*`/`O-*` 与 Tailored-N/A 项、替身资产自检、Run 证据字段缺口仍按 §8 跟踪，闭合的是**本层 68 Case 的行为覆盖**。
  - **层级边界**：**module PASS ≠ system PASS**；下层单元 PASS 不关闭本层，本层 PASS 不关闭上层。
- 开放问题与责任方：
  - 方案 §4 的 `G-*`/`O-*` 与 Tailored-N/A 项 → Owner 见 §6.3，最晚 Gate：对应设计修订或系统层承接。
  - 替身资产 `llmtier-unit-fakes` 自检 Run 未录制、Run 证据 `pythonpath`/退出码字段待下一 Run 落地 → Owner LLMTier（见 §8）。
  - 上层 wire/E2E/真实 provider 协议/性能耐久 → 系统测试方案/计划与契约层承接，不在本层分母。
  - 本报告不授权 release，不代替批准决定。

## 8. 未决项

| 未决项 / 关联 | Owner / 最晚 Gate | 关闭所需事实或决定 |
|---|---|---|
| ~~`D-MT-INF-015-1`：`MT-INF-015` 超大响应归一 `FAIL`~~ | — | **已关闭**（§6.1）：根因为 ENV-3 夹具写侧非分块，已修为 64 KiB 分块 flush，并以 `run-20261002-02` 复跑取得 `PASS`；旧 Run 证据保留 |
| `G-INF-NONJSON-MAPPING-1`：非 JSON 帧/体 503 vs 矩阵预期 502 | M003 inference ＋ 系统设计 §7.8 / 设计修订 | 设计侧确认权威映射或改实现；回溯修订 §1.5.1 a25/b4/c7；建立 `interfaces/error-codes/` 后以其为准 |
| `G-OBS-STAGE-ORDER-1`：trace stage 同毫秒乱序，位置序未断言 | M006 libdiag / 设计修订 | 增单调序号或改 `ORDER BY rowid`；修订 `VRC-OBS-004` 并把位置序断言补入 `MT-OBS-001` |
| `G-UI-LOGIN-ROUTE-1`：`/login` 未实现（404） | M002 web-ui ＋ M001 http-api / 设计或实现修订 | 提供 `/login` 路由或 ISD 改指真实入口；补 `/login` 端到端断言 |
| `O-OBS-STORECODE-1` / `O-UI-HEALTHDOMAIN-1` / `O-UI-USAGEOK-1`：观察项 | M001 / M002 ＋ M004 / 设计或替身资产补齐 | 错误目录细分 `code`；health 域扩展；为 account-usage 面建 `tests.asset-design` 替身后补行为级断言 |
| `G-TRANSPORT-BUDGET-1`：c3 超 2 MB 下游响应预算 | LLMTier（系统层）/ 系统层 Gate | 系统层预算用例建立并引用本行 |
| c4/c5 跨主机 RST/半开连接（Tailored-N/A） | LLMTier（系统/运维层） | 由系统层或运维演练承接，本层不重开 |
| Run 证据 `pythonpath`/退出码/`finished_at` 字段：本 Run 尚未落证据（harness 已补录） | LLMTier / 下一次模块 Run | 下一次 `run-<date>-NN` 的 `test-run.env` 出现 `pythonpath` / `exit_code` / `pytest_exit_code` / `finished_at` 四个字段即关闭 |
| 替身资产 `llmtier-unit-fakes`（ENV-3/ENV-4）自检 Run 未录制（`Implemented`/`Unverified`） | LLMTier / 首次资产自检 Gate | 录制 assets self-check Run 并置 `Verified` |
| 计划/方案文档状态漂移（方案 §3.6「module-case 文档尚未建立」、计划 §1/§3/§10 的 `0/68` 与「套件待建」） | LLMTier | **本交付已回溯更新**（方案 `0.1.0-draft.8`、计划 `0.1.0-draft.7`）；91/68 分母与 Case 清单未动 |
| 上层承接（wire 互操作/真实 provider 协议/浏览器 E2E/性能耐久） | 系统测试方案与计划、契约层 / 系统层 Gate | 由 `llmtier-system-test-scheme`/`-plan` 建立对应用例；不在本层分母，本层不代为关闭 |

<!-- 交付自查：任一 Verdict 能否定位唯一 Run 与原始证据；失败与 NOT_RUN 是否如实保留（前序 Run 的 FAIL 已显式登记且旧证据未覆盖）；报告是否越权写成批准。 -->
