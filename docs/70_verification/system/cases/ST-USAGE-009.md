<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-USAGE-009 — 账本崩溃/重启恢复（orphan unknown 不回填 0）

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-USAGE-009` |
| Document Version | `0.1.0-draft.4` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-USAGE-009.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-USAGE-009` / 系统设计 §8 Usage 查询接口（GET /v1/usage）；机制 §15 计量（T-MET-CRASH） / `VRC-INF-004、VRC-MGMT-006` / recovery / P0（[方案清单 `ST-USAGE-009`](../llmtier-system-test-scheme.md)）。
- **测试方法（§2.2 方法表行）**：故障注入（进程崩溃/重启）+ 复位阶梯（账本不变量）

- 要测什么（责任展开）：账本核心不变量：`authorize_dispatch` 在 dispatch 前提交**义务 + v1 `unknown` + head=1**（单事务）；此后进程崩溃/重启，该 orphan unknown **仍在**且**绝不回填为 0**；
  `GET /v1/usage` 仍返回该 `request_id`，`measurement_status=unknown`、token 全为 NULL、`is_final=false`。需求 `R-MET-04`；机制 `T-MET-CRASH`（[usage-metering §9/§14.3](../../../20_system_design/mechanisms/usage-metering.md)）；
  实现 `src/inference/usage.py::authorize_dispatch`（`INSERT OR IGNORE usage_obligations` + v1 `unknown/unavailable` + `usage_heads` head=1）与 `src/util/store.py`（SQLite 单文件持久性）。

- 明确不测什么 / 失败含义：不测正常 measured 终态（ST-USAGE-002）；不测分页/窗口/隔离（ST-USAGE-001/03/06）；不测注入产生的 `unknown/injected` 终态（ST-RESP-011/22 的 `finish(None, "injected")` 会写 v2，不是 orphan）；不测清空（ST-AUSAGE-003）；不测备份/恢复演练（方案 §4 Gap）。失败含义＝崩溃后"已登记但未测"的调用被静默丢失或回填为 0（误报"没有调用"）。

**目的（被测契约）**：验证**计量机制的核心崩溃恢复不变量**（`T-MET-CRASH`）：dispatch 前落库的 unknown 义务在进程重启后仍可见，且 token 为 NULL 而非 0。被测端点/规则：`POST /v1/responses`（触发义务）与 `GET /v1/usage`（观察）；机制 [`usage-metering`](../../../20_system_design/mechanisms/usage-metering.md) §4.1（unknown ≠ 0）、§9（中断点与 orphan unknown）、§14.3（`T-MET-CRASH`）。设计验证项 `VRC-INF-004`（机制承接）与 `VRC-MGMT-006`（查询可见性）。**不证明什么**：不测 measured 终态/分页/隔离/清空/备份演练。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite，同机第二个进程）。执行前满足**附加（B 类）**：实例可启动且 `GET /healthz` 200；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。fixture：本 case **使用专用 `LLMTierInstance`**（独立临时 SQLite 与端口）并具备**重启/硬杀能力**——`conftest.py` 提供 `LLMTierInstance.restart()`（同 db/settings 重启）、`kill()`（SIGKILL）与 fixture `llmtier_b_restart`（路径 A）、`llmtier_b_crash`（路径 B，`LLMTIER_SLOW_ADAPTER_DELAY=30` + probe healthy）。**不得**复用 session-scope `llmtier_b`。TS-003：上游为 LAN fake provider。
- **构造 orphan unknown 的两条路径**（择一或并用，均经公开入口）：
  - **(A) 准入失败法**（无需慢上游）：不 probe `depl_b`（health 非 `healthy`），`POST /v1/responses` 经校验后先 `authorize_dispatch` 提交义务，随后 `Router.admit` 因无健康候选抛 `503 model_unavailable`，`admitted=False` ⇒ **不调 `finish`** ⇒ 库中留 orphan unknown（head=1）。
  - **(B) 崩溃窗法**（更贴近 `T-MET-CRASH`，**已实现**）：以 `LLMTIER_SLOW_ADAPTER_DELAY=30` 启动，`depl_b` 健康；`POST /v1/responses` 在 `authorize_dispatch`+`bind_backend` 后于 `SlowAdapter.complete` 中 sleep；测试轮询 `usage_obligations` 确认义务已提交后 `kill()`（**SIGKILL，非 graceful SIGTERM**）进程 ⇒ `finish` 未执行 ⇒ orphan unknown。重启后验证不丢失 + **不重复**（直读账本三表各恰 1 行）。
- **被测入口**：

  ```http
  POST /v1/responses HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-data
  Content-Type: application/json
  ```

  ```http
  GET /v1/usage?from=<t0>&to=<t1> HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  ```

## 3. 输入构造

- **逐参数输入构造**：
  1. 启动专用实例（路径 A 不 probe；路径 B 设 `LLMTIER_SLOW_ADAPTER_DELAY` 并 probe `depl_b=healthy`）。
  2. 触发 orphan：`POST /v1/responses`：
     ```json
     {"model": "Senior", "input": [{"role": "user", "content": "hi"}], "stream": true, "store": false}
     ```
     路径 A：期望 `503 model_unavailable`（或 404，取决于候选），并记录 `X-Request-ID`。路径 B：请求挂起后 `kill` 进程。
  3. **重启**：以**同一 `db_path` 与 settings** 再次 `start()`。
  4. 观察：`GET /v1/usage?from=<t0>&to=<t1>`（admin，窗口覆盖触发时刻）→ 找到该 `request_id`，断言 `measurement_status=="unknown"`、`input_tokens is None`、`output_tokens is None`、`total_tokens is None`、`is_final is False`、`record_version==1`；**且 token 不为 0**。
- **边界/非法取值及理由**：窗口 `from`/`to` 覆盖触发时刻且为半开区间；`request_id` 来自响应头 `X-Request-ID`（路径 B 可从重启后 usage 页按时间定位）。不注入故障。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 启动专用实例；触发 orphan——路径 A（准入失败）或路径 B（SlowAdapter 挂起后 SIGKILL）；记录 `X-Request-ID`（路径 B 从已提交的 obligation 行取） | 义务已提交、进程被硬杀/被拒 |
| 2 | **重启**同一实例（同 `db_path`/settings） | `/healthz` 200 |
| 3 | `GET /v1/usage`（admin，窗口覆盖触发时刻） | 200；含该 `request_id`，且**恰 1 条** |
| 4 | 断言记录字段 | `measurement_status=="unknown"`、token 全 `None`（**非 0**）、`is_final is False`、`record_version==1` |
| 5 | **唯一性直读账本**（不变量"不重复"半）：直接读 `usage_obligations`/`usage_heads`/`usage_record_versions` | 该 `request_id` 各表**恰 1 行**（`_page` JOIN head 使重复对 API 不可见，故须直读） |
| 6 | （teardown）专用实例整班销毁 | 无残留 |

- **重点关注步骤**：① **unknown 义务跨重启存活**——重启后仍能查到该 `request_id`；② **unknown ≠ 0**——token 必须为 `None`，**不是** 0（0 会被误读为"没有调用"，INV-5/CON-METER-002）；③ **不得回填**——重启不得把 orphan 改写为 measured 或删除；④ **head 不降级**——`is_final=false`、`record_version==1`；⑤ **真实进程崩溃/重启**——路径 B 必须真正 `kill` 并重启，不得以"进程内异常"冒充；⑥ **专用实例隔离**；⑦ **BLOCKED 语义**——重启助手不可用（或无法取得专用实例临时库路径）时记 BLOCKED。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **独立 Oracle 来源与推导**：机制 `usage-metering` §4.1/§9/§14.3（`unknown ≠ 0`、崩溃后义务仍在）+ OpenAPI `UsagePage`/`ErrorEnvelope`。
  - 重启后 `GET /v1/usage` 含触发 `request_id` 的记录：`measurement_status="unknown"`、`source="unavailable"`、`input_tokens/output_tokens/total_tokens` 均 `null`、`is_final=false`、`record_version=1`。
  - 正常对照记录：`measurement_status="measured"`、token 为整数。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：重启后 orphan 记录仍在且 `unknown` + token 全 `null`（非 0）+ `is_final=false`。
  - **FAIL**：重启后记录消失、被回填为 measured、token 为 0、或查询为空页冒充。
  - **BLOCKED**：重启助手/专用 fixture 不可用，或路径 B 的 in-flight obligation 未在超时内出现。
  - **SKIP**：B 类临时实例不可用、附加前置不满足。
  - **INVALID**：未真正崩溃/重启，或 mock/直改库伪造。
  - **NOT_RUN**：有实现但本轮未执行。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：记录消失/被回填/token=0/空页 → FAIL；无法重启 → BLOCKED。保留触发前库快照、进程退出证据、重启后查询原始响应。
- **副作用断言与清理**：**专用实例整班 `stop()` + `rm -rf` 临时目录**（含 SQLite 三件套）；不触碰 session-scope `llmtier_b`。路径 B 的挂起请求随进程 `kill` 一并终止。离开前确认无残留进程/端口。

## 7. 自动化位置与状态

- **测试文件 / 测试函数**：`tests/system/cases/ST-USAGE-009.py`（已实现；`test_dp_usage_09_orphan_unknown_survives_real_crash` 路径 B + `test_dp_usage_09_orphan_unknown_survives_restart` 路径 A）。
- **单 Case 执行命令**：`PYTHONPATH=src python3 -m pytest tests/system/cases/ST-USAGE-009.py -q`。
- **实现状态**：Implemented；执行与 Verdict 归 Run 报告。

**证据与 Run**：保存触发请求与响应/进程终止证据、重启命令、重启后 `GET /v1/usage` 原始响应（脱敏后）、库路径与 `db_schema_version`、发出命令、exit code、`elapsed`、环境快照（本 case `environment:"b"`）。

**依赖**：附加（B 类）就绪检查；专用 `LLMTierInstance` + 重启/硬杀助手 fixture（`llmtier_b_restart`/`llmtier_b_crash`，已落地）；机制 [`usage-metering` §9/§14.3](../../../20_system_design/mechanisms/usage-metering.md)；`UsagePage`/`ErrorEnvelope` 机器契约；自动化入口 `ST-USAGE-009.py`（已实现）。**不依赖**其它 Case；与 ST-USAGE-008（存储不可用）同属账本持久性但语义不同。

