<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 System Test Plan

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-system-test-plan` |
| Document Version | `0.1.0-draft.10` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-10-01` |
| Template ID | `tests.system-test-plan` |
| Template Version | `0.9.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | `llmtier-api-test-plan, llmtier-api-test-execution, llmtier-test-plan, llmtier-vv-plan` |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/llmtier-system-test-plan.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本计划绑定软件系统

> 本文档对设计验证项（VRC/V-xxx）的引用规则：只引用 ID 与状态，不复制定义/判据；ENV 实例编号归 tests.asset-design，本计划编排 ENV 编号与 Case 分配时若变更设计须回溯修订并记录。：父设计 Document ID 经 `--parent-document-id` 写入 metadata；系统设计基线在 §2 固定。

### 模板定位：方案、用例、计划与报告的边界

- **权威分工**：Case 清单归 `tests.system-test-scheme`；单 Case 展开归 `tests.system-case`（一 Case 一文档）；本计划是**可执行作业指令**——执行者（含 Agent）按它从执行前检做到报告产出；执行结果与 Verdict 权威在 `tests.system-test-report` 与 Run 证据。
- **只索引**：构成表引用方案版本与 Case ID 范围，不复制清单或 Case 细节。
- **测试资产**：工具/夹具/替身/受控时钟的契约与自检在 `tests.asset-design`（一资产一文档，阶段共享）；本计划 §5 Step 0 使其就位。
- **不是授权书**：按用户当前授权交付；计划到期不改判任何事实状态。

### 计划条目状态语义

| 条目状态 | 含义 | 禁止 |
|---|---|---|
| `Planned` | 已排入计划，方案与责任已定位 | 用 Planned 冒充已执行或已通过 |
| `Deferred` | 经批准裁剪或延后，有 tailoring 依据与恢复条件 | 无依据的“暂不做” |
| `Blocked` | 依赖缺失（设计缺口、环境、上游合同） | 不登记缺口就长期挂起 |

## 1. 目标、范围与测试构成

**验证对象**：LLMTier V0.3 在 m5air 生产部署（及其临时实例）上对外暴露的**运行中 HTTP API 行为**——机器契约 `interfaces/openapi/llmtier.openapi.json`（OpenAPI 3.1.0，`info.version=0.3-simplified-candidate.8`）声明的 **26 条 path / 39 个 operation**（Data Plane／Usage／Management／Observability／No-auth／Alias）、认证角色（`none`/`data`/`admin`）、统一错误信封与稳定错误码、SSE 事件序列、分页 cursor 语义。被测对象是**运行中的 LAN 服务**，不是静态 OpenAPI 文本。

**不证明什么**：本计划不证明 Web UI 行为、FD 泄漏、30min 耐久、性能 SLO 校准、上游模型答案质量与上游 provider 实际推理正确性；也不证明静态契约一致（后者由 `docs/60_interfaces/contracts/llmtier-contract-specification.md` 与静态契约测试承接）。**静态契约 PASS ≠ 运行行为 PASS**，反之亦然。

**测试策略**：单服务 / 单进程 / 单 SQLite 部署边界内的 runtime 端到端；unit mock 与假上游 provider 仅用于无法隔离的子路径（如 SSE stream、限速注入）。**浏览器 UI 行为级（真实 headless Chrome over CDP，`ST-UI-*`，`-m ui`）在本层**；生产 TLS/SSO/CSRF、`runtime_activation=true`、多实例/HA、跨系统恢复不在本层（见 scheme §4 裁决与 §9）。覆盖模型＝surface → contract → case：每个对外 surface（启服/健康就绪、Data Plane、Embedding、Admin CRUD/probe/refresh、Audit/Log、观测诊断、Auth/TRUSTED_LAN）映射到来源 ID 与契约（`CT-*`），再落到 scheme §3 的 Case ID；缺口显式列入 scheme §4，不静默从分母消失。

**构成清单**（只索引，不复制清单或 Case 细节）：

| 构成层 | 文档 / 入口（Document ID 或缺口） | 覆盖责任摘要 | 条目状态 |
|---|---|---|---|
| 系统方案 ×1 | `llmtier-system-test-scheme`（`docs/70_verification/system/llmtier-system-test-scheme.md`；§3 已登记全部 173 个 Case：A/B 163 + 真实浏览器 UI 10） | 系统层测试分类与 Case 清单唯一登记处 | Planned |
| Case 文档 ×173 | `docs/70_verification/system/cases/<lowercased-case-id>.md`（一 Case 一文档，173 已写 / 0 待写；含 `st-ui-001..010`） | 逐 Case 输入/执行/Oracle/判定/证据/清理 | Planned |
| 测试资产 ×2 | `llmtier-unit-fakes`（`docs/70_verification/unit/assets/llmtier-unit-fakes.md`，`Implemented`/`Unverified`）＋系统 B 类 fixture（`tests/fixtures/models/v03_fake_provider.py`＋`tests/system/conftest.py`，契约见 `testing-standard.md` TS-002/TS-003） | harness/客户端/假上游/受控构造的契约与自检 | Planned（O2 已关闭；资产自检 Run 待录制） |
| 子系统计划引用 | 无（LLMTier 为单服务，当前无独立子系统测试层） | — | Deferred（无对象，O4 最终决定） |
| 验收交接 | 验收活动（tailoring 承接，不在 tests 家族，见 `std-tailoring` `LT-TL-022`） | 客户/发布验收场景 | Deferred（按项目 tailoring 承接） |

**责任边界**（谁证明什么；下层/相邻方 PASS 不关闭本层，本层 PASS 不关闭上层组合目标）：

| 层级 | Owner | 证据 | 与本计划关系 |
|---|---|---|---|
| 系统（本计划） | LLMTier | 本 Run 证据 + `tests.system-test-report` | 运行中 HTTP API 行为 |
| Contract static（`CT-*`） | LLMTier | `tests/contract/` + fixtures | 静态契约一致；**不替代**运行行为 |
| Provider adapter | LLMTier | 受控捕获（假上游） | 本层替身边界，只证明本服务行为 |
| Piko consumer | Piko | Responses SDK/agent test | 真实 consumer 联调，非本层分母（scheme §4 验收交接，`std-tailoring` `LT-TL-022`） |
| Embeddings consumer | Slinky | Memory integration test | 同上 |
| Admin UI/operations | LLMTier | browser/API/security test | Web UI 行为不在本层 |
| 验收活动 | LLMTier + Piko + Slinky | 验收报告 | **不在 tests 家族**，按 tailoring 承接（见 std-tailoring） |

## 2. 被测基线与变更重跑范围

- 设计 / 源码 / 依赖基线：
  - 设计基线：`llmtier-system-design`（`design.software-system`）§5–§7、§11；机器契约 `interfaces/openapi/llmtier.openapi.json`（OpenAPI 3.1.0）；系统设计 §7.8 公共错误目录（`ERR-*` 八字段）。
  - 源码 / 部署基线：**当前 `main` 工作树的 m5air 部署版本**；每 Run 必须 pin `{git_commit, db_schema_version, openapi_version}`（§7），禁止以 branch/tag/`HEAD` 名代替。
  - 依赖：m5air OMLX `192.168.1.9:9000`、m5mac OMLX `192.168.1.8:9000`（Bearer `9832`）；Python 3.14；`docs/std.lock.json`（STD `0.1.0-draft.69`，`source_revision=8fe0cd2`，adopted 2026-09-30）；`testing-standard.md`（TS-002 依赖头部、TS-003 LAN IP）。
  - 数据库：`schema_version = 2`（`src/util/store.py::EXPECTED_SCHEMA_VERSION`）。
- 变更 → 重跑范围规则（重跑生成新 Run 与新报告，**不覆盖旧失败**）：
  - 机器契约（路由/schema/securitySchemes）变更 → 全部路由/schema 相关 Case 重跑。
  - 错误目录（§7.8）变更 → 全部负向 Case 重跑。
  - 机制（inference-stream／access-trust／usage-metering／observability／config-lifecycle）变更 → 其 `T-*`/`VRC-*` 映射 Case 重跑。
  - 单个 Case 的输入/Oracle 变更 → 只重跑该 Case 及其依赖边下游。
  - 测试规范（TS-002/TS-003）或项目标准变更 → 全部 Case。
  - 单模块修复 → 该 family＋共享 `T-*`/`VRC-*` 家族；错误信封变更 → 全部负向 Case。

## 3. 执行前检（Go / No-Go）

| 前检项 | 判定事实 | 通过条件 | 不满足时 |
|---|---|---|---|
| 方案就绪度 | `llmtier-system-test-scheme` §3 权威清单 173 条（**设计数**：A 102 / B 61 / UI 10）、计数与 A/B/UI、P0/P1/P2 分布固定；与 §2 分类体系交叉核对 | 清单无未登记缺口、版本固定 | No-Go：Blocked＋缺口语义（§9-O1） |
| Case 实现状态盘点 | **设计数 = 已实现数 173（A 102 / B 61 / UI 10）**：原 163 个设计 Case 均有 `ST-*.py`（文件名＝Case ID）自动化入口（`--collect-only` 实际 collect=176 项，多出者为参数化/双臂测试——`-m api_a`＝105、`-m api_b`＝71）；**真实浏览器 UI Case `ST-UI-001..010`（`-m ui`，`tests/system/cases/ST-UI-001.py`；本版由 7 增至 10，补齐脱敏/幂等/边界模式）**，**无 MISSING**。逐 Case 清单见 `llmtier-system-test-scheme` §3 与逐 Case 设计文档 | 全部已实现；无 P0 缺口 | No-Go 或按 §4 记 NOT_RUN 缺口 |
| 环境与工具（引用 `tests.asset-design` 的 Verified 状态） | A 类：m5air `/healthz`、`/readyz`(7 tier)、双 OMLX、`provider_omlx_m5mac` 已注册且 `has_secret=true`（`secret_ref` 只写不返回）、provider/deployment 就绪（6 项，§6）；B 类：执行机临时实例（`tests/fixtures/models/v03_fake_provider.py`＋`llmtier_b` fixtures 已在位）。**可执行实现**：`tools/check_env.py`（§3 前检 Go/No-Go 的独立入口，`--class a\|b\|all`，human table＋`--json`，exit 0 全过 / 2 任一失败）复算上述 6 项 A 检查与 2 项 B 前置 | A 类：`pytest_configure` 6 项全过（或 `tools/check_env.py --class a` exit 0）；B 类：执行机具 LAN IP（`_detect_lan_ip()` 命中 RFC1918）且临时实例可启停（或 `tools/check_env.py --class b` exit 0） | **按类分别判定**：A 类 6 项不过 → 仅 A 类 Blocked/Skip（§6，不静默降级）；B 类无 LAN IP／临时实例不可用／`llmtier_b` 基线 probe 不健康 → B 类整体 Blocked（§6-B，见 §3 Exit 与 §9 风险） |
| 构建接线（全量交付构建 / 消费者链接实际库） | m5air 部署版本已 pin 且与执行机同步来源一致；解释器为 Python 3.14（禁系统 3.9）；`schema_version=2` | pin 三项可解析；服务可服务 | 按 §6 恢复（重启／schema 二选一）；仍失败 → Blocked |

**Entry criteria**：上表 4 项全过（commit/schema/openapi 三项 pin、单测基线全绿、A 类 6 项就绪、B 类 LAN＋临时实例可用）方可起跑。**A 与 B 独立判定**：A 类就绪失败只阻断 A 类，B 类照跑；反之亦然（见 §6 与 conftest `pytest_collection_modifyitems`——就绪失败只 skip `api_a`，`api_b` 继续）。

**Exit criteria 与判定口径**（本计划只固定口径，实际判定只在报告与 Run 证据）：

| 状态 | 含义 |
|---|---|
| PASS | Case 全部预期字段与独立 Oracle 一致，exit 0，证据完整 |
| FAIL | 实际输出与预期至少一处不一致；记录 `failure_reason`（预期 vs 实际＋复现命令） |
| BLOCKED | 受真实外部依赖限制无法跑（OMLX 未运行、云端限流等），或**按类整体前检不满足**（A 类 6 项不过 / B 类无 LAN IP 或 `llmtier_b` 基线不健康）；记录 blocker 与解除条件（见 §6-B 恢复阶梯） |
| SKIP | 依赖链前置未满足（如 A 类整班就绪失败），按依赖顺序补跑 |
| INVALID | Case 设计错误或预期本身不成立；记录 issue，需重新设计 |
| NOT_RUN | 未运行（自动化入口未实现 / 未排入本轮）；如实保留，不补造成功 |

> **BLOCKED 语义（诚实的恢复语义）**：BLOCKED ＝ 该项**本轮未得出任何判定**，必须在报告与 Run 证据中记 blocker 与解除条件，不得静默降级为 PASS/SKIP。按类整体 BLOCKED 的解除路径：A 类 → 修 m5air 6 项后重跑整类；B 类 → ① 执行机补 RFC1918 LAN IP（或设 `LLMTIER_TEST_LAN_IP` 覆盖）② 修假上游/基线 probe 后重跑整类。**注意环境性静默 skip**：`_detect_lan_ip()` 未命中 LAN 时 B 类 fixtures 会 `pytest.skip`（见 §6-B），故“B 类未报错”不等于“B 类通过”——必须核对 Run 记录中的 skip 计数。

**Exit**：全部适用 Case 走完且 FAIL/INVALID＝0、BLOCKED/SKIP 在上限内（A ≤5 / B ≤3）→ 可提 Gate 建议；任一 FAIL/INVALID 或 P0 MISSING → 阻断 release；BLOCKED 同样阻断 release。

## 4. 环境实例分配（plan 编排）

<span style="color:#1f6feb"><em>**本节目相**：把方案 §1.7 的环境类型落实为具体的**实例编号**，并分配给具体 Case——同一类型可多套（如多 docker 用于并行），编号与分配是 plan 的责任，Case 只引用编号。</em></span>
<span style="color:#1f6feb"><em>**必须写清楚**：列出本计划分配的全部 ENV 实例（编号 + 类型 + 具体配置/位置 + Owner + 分配给哪些 Case + 准备时限 + 状态）；ENV 实例类型与方案 §1.7 类型一致；准备失败标 Blocked 并登记缺口，不静默换其他实例。</em></span>
<span style="color:#1f6feb"><em>**抽象示例**：见下方灰字——系统层 ENV 实例分配（同一类型多套用于并行/隔离，多 Case 复用同一实例）。</em></span>
<span style="color:#1f6feb"><em>**完成条件**：每个 §3.1 的 Case 在本表有 ENV 实例；类型一致；准备未完成标 Blocked 并登记缺口，不静默换实例。</em></span>

| ENV 实例编号 | 环境类型 | 具体配置/位置 | Owner | 分配给哪些 Case | 准备时限 | 状态 |
|---|---|---|---|---|---|---|
| ENV-A | A 类 m5air 已部署实例 | `192.168.1.9:8181`，现有 state.sqlite3（只读/观察/一次性无状态写） | 环境 Owner（m5air owner） | HEALTH/DP-*/只读 ADM-*/只读 OBS-*（**设计 A 类 102，已实现 102**（`-m api_a` collect=105）） | 每班开跑前 | Ready（以 §3 A 类 6 项为准） |
| ENV-B | B 类执行机临时实例 | 随机空闲端口＋临时 SQLite（`tempfile.mkdtemp(prefix="llmtier_b_")`）＋LAN 绑定的假上游（`tests/fixtures/models/v03_fake_provider.py`） | 执行者 | CRUD/空库/无鉴权/注入/并发（**设计 B 类 61，已实现 61**（`-m api_b` collect=71）） | Step 0 前 | Ready（fixtures/假上游已在位、`llmtier_b` 可启停）；**运行期若执行机无 RFC1918 LAN IP 或基线 probe 不健康 → 整类 Blocked**（§6-B，非 asset-design 缺口） |
| ENV-UI | 真实浏览器 UI 执行环境（复用 ENV-B 的临时实例＋假上游；新增 headless 浏览器） | 临时 `LLMTierInstance`（loopback）＋ LAN 假上游 ＋ headless Chrome/chrome-headless-shell（`LLMTIER_BROWSER`，默认 `/Applications/Google Chrome.app/...` 或缓存）＋ node ≥ 22（`LLMTIER_NODE`，内置 WebSocket，无 npm） | 执行者 | UI 行为级（**设计 10，已实现 10**：`ST-UI-001..010`，`-m ui`） | 环境新增后（本轮） | Ready（`tests/system/cases/` (ST-UI-*) 已在位，本地 10/10 PASS）；**运行期若执行机无浏览器可执行文件或 node<22 → 整类 SKIP**（`ui_browser`/`ui_node` fixture 主动 skip，非覆盖缺口） |

> ENV-A 与 ENV-B 不共享 SQLite/端口/进程且不并行（方案 §1.7）；A 类 PASS 不关闭 B 类，反之亦然。准备未完成标 Blocked 并登记缺口，不静默以 A 类替代 B 类。**B 类不依赖 `tests.asset-design` 文档**：其 fixtures（假上游＋`llmtier_b`）已在 `tests/system/conftest.py` 实现，契约见 `testing-standard.md` TS-002/TS-003；资产文档 `llmtier-unit-fakes`（O2 已关闭）覆盖单元替身，与 B 类执行互不阻断。

## 5. 执行流程（逐 Case 作业序列）

| Step | 动作 | 输入 / 依据 | 产出 |
|---|---|---|---|
| 0 | 资产就位：按消费索引构建全部依赖测试资产（harness、客户端、假上游、受控构造）并跑自检 | `llmtier-unit-fakes`（`docs/70_verification/unit/assets/`）＋B 类 fixture（`conftest.py`） | 就绪清单（Verified）；自检不过即环境性 Blocked，不进入 Case 执行 |
| 1 | 读取方案清单并按优先级排序（A 先于 B，家族内按依赖） | 方案 §3（`llmtier-system-test-scheme`） | 执行队列 |
| 2 | 逐 Case：定位 Case 文档（`cases/<lowercased-case-id>.md`） | Case ID | 实施依据 |
| 3 | 按 Case 文档执行前检与运行（A 类按 §6 打 m5air；B 类临时实例） | Case 文档 §2–§7 | Run 记录 |
| 4 | 判定并分路（PASS/FAIL/BLOCKED/SKIP/INVALID/NOT_RUN） | 断言与环境事实 | Verdict 归报告 |
| 5 | 全部完成后生成测试报告 | 本计划 §8 | `tests.system-test-report` |

| 阶段门 | 目的 | 进入条件 |
|---|---|---|
| 1 最小真实链 | 先打通健康/就绪→models→单条 responses SSE 端到端 | Step 0 通过，`A-gate`＋`A-data` 冒烟可用 |
| 2 规模控制面 | 覆盖 Management/Observability 只读面与 CRUD | 阶段 1 PASS 或具名登记 |
| 3 完整业务 | A/B 全部适用 Case 跑完 | 阶段 2 完成，B 类临时实例可用 |
| 4 恢复 / 全量回归 | 故障注入、恢复路径与契约回归 | 阶段 3 完成；基线/golden 就位 |

- 失败（FAIL）处理路径：保留现场与 Run 证据 → 登记缺陷并关联 Case ID → **继续后续 Case**；不重跑覆盖原失败；回归重跑按 §2 范围生成新 Run。
- 阻塞/无效（BLOCKED/INVALID）处理路径：BLOCKED（环境缺失/可重试无法判定）→ 就地恢复（§6 阶梯）后继续，不中断整轮；INVALID（流程未真正走到观察点，如注入未命中却判行为）→ 修 Case 或标无效；依赖链前置未满足 → 标 SKIP 并按依赖顺序补跑。

## 6. 环境操作（搭建 / 复位 / 隔离 / 清理）

- 环境搭建与复位操作：**两层被测对象，一套执行机**。A 类＝m5air 现有实例（`192.168.1.9:8181`，只读/观察/一次性无状态写，写后即 teardown）；B 类＝执行机本机临时实例（随机空闲端口＋`tempfile.mkdtemp(prefix="llmtier_b_")` 临时 SQLite，CRUD/空库/无鉴权/注入/并发，整班销毁）。执行机＝开发机，`cwd="$(git rev-parse --show-toplevel)"`、`PYTHONPATH=src`。
  - 版本锚定与更新：每 Run pin `{git_commit, db_schema_version, openapi_version}`（§7），缺任一不得开跑；m5air 部署目录非 git 工作树，须从开发机受控 `rsync`（排除 `state.sqlite3*`、`secrets/`、`llmtier.log`、`llmtier.pid`、`backups/`）；回滚＝用旧 commit 源码快照重新 `rsync`。
  - 启动/重启（A 类）：查旧进程与端口 → `kill -TERM`（勿 `kill -9`）→ Python 3.14 `python3 -m http_api --host 0.0.0.0 --port 8181 --database …/state.sqlite3` → `curl /healthz`＋`/readyz` 验证 → 确认恰好一个 PID、一个 `*:8181` 监听者。幂等：已启动即已满足，不得起第二实例。**可执行实现**：`tools/deploy.py` 将本节＋`m5air-deploy-guide.md` 的事实固化为脚本——pin `{git_commit, openapi_version, schema_version}` → `rsync src/` → `lsof -iTCP:8181 -sTCP:LISTEN` 找旧 PID 并 `kill -TERM` → 以 Python 3.14＋`LLMTIER_{ADMIN,DATA}_TOKEN`＋`PYTHONPATH=src -m http_api` 启动 → `curl /healthz`＋`/readyz`；`--rollback <db-bak>` 恢复 DB，`--dry-run` 只打印命令，不打印任何 secret。**部署/启停/备份/恢复唯一 authority 是 `m5air-deploy-guide.md` 与 `m5air-operations-manual.md`；本节是其测试用镜像，脚本冲突以运维手册为准并回填本节。**
- 隔离键与清理：A 类与 B 类**不共享 SQLite/进程且不并行**；B 类隔离键＝临时端口＋临时目录＋每 run `settings.json`；清理＝A 类写 Case teardown、注入 `items:[]` 清空、`DELETE /v1/usage` 复位账本；B 类 `stop()`（`terminate`→等 5 s→`kill`）＋`rm -rf` 临时目录。**不得删除 m5air 既有 provider/deployment/service-level 或用户 usage。** **可执行实现**：`tools/reset_env.py`（幂等、安全）——先 sqlite backup API 备份 DB（`--no-backup` 跳过）→ 可选 `--restore <bak>` / `--rebuild` → 逐 deployment `GET diagnostics` 后 `PATCH {"items":[]}` 并断言为空 → `DELETE /v1/usage`（`--no-ledger` 跳过）→ 杀死遗留本地测试 `LLMTierInstance`/临时实例进程并释放临时端口 → 末尾重跑 `tools/check_env.py`；`--dry-run` 只打印动作、`--yes` 为非交互 guard，任一步失败退出非零。
- 复位阶梯与时限（软复位→重启→驱动恢复）：
  1. **case 前检查**：跑 §3 A 类 6 项（`pytest_configure` 自动执行；或 `tools/check_env.py --class a`）；**不通过只 skip A 类**（`pytest_collection_modifyitems` 只对非 `api_b` 用例加 skip），**B 类用各自临时实例照跑**——不存在“整班 Blocked/Skip”，A 与 B 独立判定（方案 §1.7）。
  2. **软复位**：A 类每个写 Case 后恢复被改字段（带正确 `If-Match` 的 `PATCH`）、清注入（`PATCH …/diagnostics {"items":[]}` 后 `GET` 确认空）、`DELETE /v1/usage`；B 类丢弃临时 DB 重起。**可执行实现**：`tools/reset_env.py` 步骤 (c)/(d)，见上。
  3. **重启**：`/healthz` 不通或 schema/版本不匹配 → A 类按 §6 重启；schema 不匹配走**显式二选一**（fresh-DB rebuild / offline migration），`--settings` 仅空库首启有效，禁止删 `schema_meta` 行当未知库。**可执行实现**：`tools/deploy.py`（重启）与 `tools/reset_env.py --rebuild`｜`--restore <bak>`（二选一）。
  4. **驱动恢复/时限**：上游超时→调大 deployment runtime profile（`connect_timeout_ms`/`stream_idle_timeout_ms`，默认 30000/60000）＋有界重试 ≤3；store 锁→退避重试（1→2→4 s，≤3 次）；flaky→有限重试 ≤3 并记录并发度与时间窗。
  5. **复位后核验**：A 类重跑 §3 6 项，确认 `/readyz` 7 tier、provider/deployment 列表回基线、无遗留端口、无未清空注入。**失败后必须确认回到基线，不能只 kill 后继续。** **可执行实现**：`tools/reset_env.py` 步骤 (f) 末尾自动重跑 `tools/check_env.py`。

#### 6-B B 类前检与恢复语义（单点毒性诚实披露）

B 类的"可运行"取决于**执行机网络与基线 probe**，非 `tests.asset-design`；两个已实现的失败模式必须如实登记：

1. **无 LAN IP → B 类整体静默 skip**：`provider_endpoint_b` 调 `_detect_lan_ip()`（`tests/system/conftest.py` B fixtures），未命中 RFC1918 地址即 `pytest.skip("TS-003: no LAN IP available…")`。执行机若不在 `192.168.x`（如 CI/云端），全部 B 类用例被 skip——**这是环境性 skip，不是 PASS**。解除：设 `LLMTIER_TEST_LAN_IP` 覆盖，或接入 RFC1918 网段后重跑；Run 记录须核对 skip 计数，skip 计入 SKIP 上限（B ≤3），超限即本轮 B 类视为 Blocked。
2. **`llmtier_b` 基线 probe 硬断言 → 全局毒性**：`llmtier_b` fixture（session 期）启动临时实例后调 `_probe_deployment(inst,"depl_b")` 并 `assert status == "healthy"`。假上游或 LAN 探测任一抖动 → session fixture error → **全部依赖 `llmtier_b` 的 B 类用例连带 error**，属单点全局毒性；当前**无 teardown 隔离/重试**。解除：先修 LAN/假上游使其 healthy 再整类重跑；不得把连带 error 记作个别 Case FAIL。**该项恢复语义归 §9 风险行与 W2 工具流（若需重试/隔离由工具流补）。**

## 7. 证据与 Run 记录规则

- Run ID 规则与证据位置：
  - Run ID＝`<date>/<class>-<phase>`（如 `2026-09-29/A-api`、`2026-09-29/B-api`）。
  - 保存位置：**`tests/system/reports/<run-id>/`**（系统报告随测试保存，**不集中到 `tests/reports/`**），每 Case 一份 `manifest.json`＋原始证据文件（`response.http.txt`、`sse.events.jsonl`、`headers.txt`、`stdout/stderr`）；大型/敏感原始输出放该 Run 下的 `artifacts/`（默认不入 Git，按 CI 保留策略）。正式 Markdown 报告保留 metadata。
  - **现状（W2 已交付）**：证据链工具已落地——`tests/common/harness/run_harness.sh`（pin `git_commit`/`schema_version`/`openapi_version`、`--junitxml`、产物目录）＋`tools/test_report.py`（`case-status.json`＋逐 Case `manifest.json`）；`runner_a.sh`/`runner_b.sh`/`tests/unit/v03/runner.sh` 均经该 harness。首个单元 Run `tests/unit/v03/reports/run-20260930-01` 已产出完整证据链。**系统 Run 已产出**：A 类 `tests/system/reports/2026-09-30/A-api-6`、B 类 `tests/system/reports/2026-09-30/B-api-5`、单元 `tests/unit/v03/reports/run-20260930-05`，均由 harness 产出完整证据链（A 105 PASS / B 71 PASS / UNIT 425 PASS，均 exit 0），正式报告见 `tests/system/reports/2026-09-30/system-test-report.md`（`llmtier-system-test-report-2026-09-30`）。
  - 每 Run 必须保存（目标契约）：命令、构建/配置、随机种子、输入、HTTP status/headers/body、SSE 逐帧、stdout/stderr、退出码、耗时、环境快照（`/healthz`/`/readyz`＋provider/deployment 列表＋`api_smoke_test.py` 输出）。**缺 pin 的 Case 不得判 PASS。**
  - 保留期：正式报告及 metadata 永久保留；`artifacts/` 按 CI/外部证据库策略；外部证据记录稳定制品 ID/URI、摘要与保留要求。
- 保存内容与脱敏要求：Artifact 入库前必须 scrub——`Authorization` 头（`Bearer dev-data`/`dev-admin` 为测试凭据可保留，真实凭据替换 `<redacted>`）、上游 OMLX Bearer 字面 `9832`、任何 key 文件内容与解析后 secret 值、完整 provider payload；`manifest` 的 `redactions` 必须列出已脱敏项。失败现场保留不截断。
- 重跑规则：重跑生成**新 Run、新报告，不覆盖旧失败**；不把未运行项目补造为成功。
- **`xfailed → BLOCKED` 状态映射（W2 已交付并实现）**：`tools/test_report.py` 已实现——`failed`→`FAIL`、`errored`→`BLOCKED`（环境性）或断言性 `FAIL`、`xfailed`→`BLOCKED`、`xpassed`→`XPASS`（告警，不计 PASS）、`skipped`→`SKIP`；映射落点为每 Run 的 `case-status.json`（每 Case 终态＋原因）。**`xfailed` 不产生"全 PASS"，仍进 release 阻断口径（BLOCKED 阻断 release）。**
  - **实现状态**：`tools/test_report.py` 已交付（322 行，`--junit`/`--run-metadata`/`--manifests`/`--check-cap` 全部可用），`tests/unit/v03/reports/run-20260930-01/case-status.json` 已由该工具机械产出（`{PASS:341, FAIL:0, BLOCKED:0, INVALID:0, NOT_RUN:0, SKIP:0, XPASS:0}`），映射可复算。

## 8. 报告产出与 Gate 规则

- 报告生成时机与模板：全部 Case 走完（或按 Exit 出口准则提前结束）后生成 `tests.system-test-report` 实例（Gate 是 release 决策，"本轮跑完"是执行里程碑，二者不得互相替代）；报告只汇总实际运行，分开预期/实际结果、未运行、阻塞与失败，引用 Run 证据不复制原始输出。
- Gate 建议规则（报告只按规则给建议，**不越权批准**）：
  - **适用 Case**（默认全部 173，仅经批准裁剪可标 N/A）全 PASS，且 FAIL/BLOCKED/INVALID＝0，且 SKIP 在上限内（A ≤5 / B ≤3）。
  - **P0 MISSING 阻断**（MISSING＝NOT_RUN 缺口，非 SKIP）；非 P0 MISSING 与具名缺口（scheme §4 裁决的 `ERR-BOOT`/`ERR-SCHEMA`/`ERR-PATH-UNSAFE`/`ERR-UTIL-TXN` 已于本版按单元宿主关闭为 Tailored-N/A 下层承接，见 scheme §4）需具名批准（owner/ETA）。
  - 覆盖复算：路由×方法×角色×错误码四维下限满足（scheme §3 分类计数与逐 Case 责任摘要）。
  - 报告给出覆盖数（应跑/已跑/PASS/FAIL/SKIP/BLOCKED/INVALID/NOT_RUN）、未关闭缺陷、MISSING 与具名缺口清单；Gate Owner/Approver/Baseline Run ID 进入 Gate 状态时填写，不伪造。

## 9. 责任、排期与风险

| 构成项 / 风险 | Owner | 时间窗 / 最晚 Gate | 冲突或缓解出口 |
|---|---|---|---|
| 方案维护（scheme／现行清单） | LLMTier（测试设计 Owner） | 本迭代 | 清单变更同步本计划 §1 构成表 |
| Case 编写与实现（设计 173：A/B 163 + UI 10；已实现 173，无 MISSING） | LLMTier（Case 作者） | 进入 Gate 前 | 已全部落地；后续仅随设计与契约变更维护 |
| 环境提供（m5air 部署/secret/OMLX/就绪） | 环境 Owner（m5air owner） | 每班开跑前 | 执行者不擅自改部署拓扑；拓扑变更走评审（§10-O3） |
| 执行（按 §5 序列跑批次、teardown、记录 Run） | 执行者 / Agent | 每班 | A/B 互斥同一实例，不并行 |
| 见证/裁决（BLOCKED/INVALID 裁决、回归门） | 见证者 | Gate | 失败分级见 §8 |
| 风险：上游 provider 离线 | 环境 Owner | 触发＝§3 检查失败 | 受影响批次标 SKIP，不终止整轮，恢复后补跑 |
| 风险：写测试污染 m5air 现有 state | 执行者 | 触发＝teardown 失败/残留 | 停止 B 类、隔离实例，不删既有资源，按 §6 复位 |
| 风险：注入未清除 | 执行者 | 触发＝`GET diagnostics` 非空 | 阻止下一轮，`items:[]` 清空后复核 |
| 风险：`schema_version` 不匹配 | 环境 Owner | 触发＝启动 503/`schema_version_mismatch` | §6 显式二选一；复位前先冷备份 |
| 风险：SKIP 超上限 | 执行者 | 触发＝A>5 / B>3 | 补 fixture/注入后重跑；**超限退出码语义已由 W2 工具流实现**：`tests/common/harness/run_harness.sh` 调 `tools/test_report.py --check-cap`，超限将 runner 退出码置 2（`tests/common/harness/runner_system_a.sh / runner_system_b.sh` 不再只透传 pytest exit code） |
| 风险：BLOCKED vs FAIL 判定分歧 | 见证者 | 全局 | 强制六态判定；FAIL/BLOCKED/INVALID 均阻断 release |

## 10. 未决项

> **关闭状态（本版终审）**：O1/O2 已关闭；O3/O4 为**最终决定**（非开放项）；O5 为**实现排期追踪**（Gate 条件，非覆盖缺口）；**O6（`RISK-UI-EXEC-1`）本版已关闭**（引入真实浏览器 harness + `ST-UI-001..010`）。本表无未解释条目、无开放 RISK。

| 未决项 / 关联 | Owner / 最晚 Gate | 关闭事实或最终决定 |
|---|---|---|
| O1（已关闭）：`llmtier-system-test-scheme` 已填充并成为 Case 清单唯一登记（163 条）；原 `llmtier-api-test-specification` §3.2 已退役并迁入 scheme §3 | 测试设计 Owner / 进入 Gate 前 | 权威清单现为 scheme §3；本计划引用 scheme 版本，不再引用已退役规格 |
| O2（已关闭/已修复）：`tests.asset-design` 测试资产文档 | 测试设计 Owner / Step 0 执行前 | **已建立** `llmtier-unit-fakes`（`docs/70_verification/unit/assets/llmtier-unit-fakes.md`），覆盖单元层 `FakeAdapter`/`AppFixture`；**系统 B 类假上游/harness** 的真实契约归 `tests/fixtures/models/v03_fake_provider.py`＋`tests/system/conftest.py`（实现）＋`testing-standard.md` TS-002/TS-003（依赖头部与 LAN IP 约束），B 类 fixture 已在位且已在 §4 ENV-B 登记。§5 Step 0 现可判定就绪（单元资产 `Unverified`，自检 Run 待录制，记于资产 §7）。 |
| O3（最终决定，非开放项）：A 类沿用 m5air 现有实例，不另建专用测试部署 | 环境 Owner / 拓扑变更时重评 | **决定**：A 类只做只读/观察/一次性无状态写（方案 §1.7、§6），不污染 m5air 既有 state；B 类以临时实例承载有状态写。故无需专用 A 类部署。重评触发＝出现"需有状态写／现 state 视为不可污染生产数据／A-B 需并行"任一情形（同 std-tailoring 重评触发 4/7）。 |
| O4（最终决定，非开放项）：LLMTier 单服务无独立子系统测试层 | 测试设计 Owner / 若引入子系统时 | **决定**：无 `design.subsystem` 对象（单服务，模块 M001–M008 直接归系统设计），子系统计划引用**保持空并具名登记**（与 scheme §4「子系统测试级别」Tailored-N/A 一致）；引入子系统时补 `tests.subsystem-test-plan` 引用。 |
| O5（已关闭）：设计 163（A 102 / B 61）已全部实现——163 个自动化入口（`tests/system/cases/ST-*.py`），无 MISSING；逐 Case 见 `llmtier-system-test-scheme` §3 与逐 Case 设计文档 | Case 作者 / 进入 Gate 前 | **关闭事实**：163 个设计 Case 均有自动化入口（`--collect-only` collect=176 项，多出者为参数化/双臂测试）。原"尚余 49 MISSING"为旧盘点，已由本轮实现补齐。后续无 MISSING 排期项。 |
| **O6（已关闭）：`RISK-UI-EXEC-1` — Web UI 真实 JS 执行验证已建立** | **M002 web-ui（共同 Owner M005） / 已关闭** | **原风险事实**：`VRC-UI-001..006`（M002）与 M005 诊断页视觉子项的行为级原仅由 `UT-UI-001..010`/`UT-OBS-*` 的源码字符串契约（`assertIn`）覆盖，不执行 JS，行为回归可在系统 163/163 + 单元全绿下漏检。**关闭事实（本版）**：引入真实浏览器 harness（headless Chrome over CDP，`tests/common/drivers/browser_driver.mjs`，node ≥ 22 内置 WebSocket，无 npm/下载依赖），在**系统层新增真实执行 Case `ST-UI-001..010`**（本版由 7 增至 10：补齐脱敏/幂等/边界呈现，并使数据变更两侧与错误恢复落地）（`tests/system/cases/ST-UI-001.py`，hermetic 临时 `LLMTierInstance` + LAN fake provider，`-m ui` 标记），在真实 DOM 与 CDP 网络记录上断言：页面渲染 + Provider 行来自 API、tab 切换改可见区并触发 API、确认门控 Pause 发 `If-Match` PATCH 并重渲染、用量未知渲染 Unknown、未确认探测不触网、诊断页 4 tabs 与 Disabled 视觉、注入 API 错误显示错误态并保留上一屏。每 Case 产出 PNG 截图 + 网络日志证据。`VRC-UI-001..006` 与诊断页视觉子项现**已由真实执行验证**，`RISK-UI-EXEC-1` 从 `llmtier-unit-test-scheme` §4 与 `llmtier-system-test-scheme` §4 关闭。**关闭条件达成**：原条件＝引入浏览器/JS 宿主并升级 `UT-UI-*` 为真实执行断言——已由系统层浏览器执行替代（`UT-UI-*` 字符串契约保留为快速下位防线）。**重评触发**：新增/修改任一 UI 行为分支时须同步 `ST-UI-*`。 |

