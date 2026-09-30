<!-- STD_DOCUMENT_COVER_BEGIN -->
# DP-USAGE-04 — 过期 cursor

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `DP-USAGE-04` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-09-30` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/cases/dp-usage-04.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`DP-USAGE-04`）；责任摘要、分类与优先级以 [系统测试方案 §3](../../schemes/llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Usage 查询接口（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-006`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `DP-USAGE-04` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`DP-USAGE-04` / 系统设计 §8 Usage 查询接口 / `VRC-MGMT-006` / negative / P2（[方案清单 `DP-USAGE-04`](../../schemes/llmtier-system-test-scheme.md)）；机制 `T-MET-PAGE`（[usage-metering 机制](../../../20_system_design/mechanisms/usage-metering.md) §4.7「TTL 10 分钟」/CON-METER-004）。
- 要测什么（责任展开）：**真实过期**的 usage cursor → `400 cursor_expired`：先查首屏取 `snapshot_id`，经 `ssh m5air sqlite3` 把该行 `query_snapshots.expires_at` 改到过去后重放同一 cursor，`finally` 复位原值。`GET /v1/usage`（`cursor` 可选；过期/非法/不匹配 cursor 的 wire 码见错误目录 `ERR-CURSOR` → `cursor_expired`）。实现 `src/inference/usage.py::UsageRecorder._page`：`snapshot is None or expires_at <= now` → `ApiError(400,"cursor_expired",...)`，且该检查在 `filter_digest`/`authorization_digest` 复核**之前**。机制需求 `R-MET-02`；需求链 `LT-FUN-004`、`LT-OPS-005`、`CT-USAGE-001`。
- 明确不测什么 / 失败含义：不测 cursor 属于他人或 filter 不匹配时的 403/400（DP-USAGE-06/07）；不测分页内容（DP-USAGE-03）；不测重放幂等（DP-USAGE-07）；不测 store 不可用（DP-USAGE-08）；**不**用字面量 `cursor="expired"` 之类的伪触发（那会命中"snapshot 不存在"分支而非真实 TTL 分支）。失败含义＝cursor TTL 过期拒绝契约破坏。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `GET /v1/usage`（`data`）。

```text
GET /v1/usage?from=<now-30d>&to=<now>
GET /v1/usage?from=<now-30d>&to=<now>&cursor=<sid>:0
Authorization: Bearer dev-data
```

- 初态构造（经公开入口）：**环境 A**（m5air 已部署实例，只读/无状态）。初始状态 = m5air 现有基线。**关键额外权限**：允许 DP-USAGE-04 直接读取/改写 m5air `state.sqlite3` 的 `query_snapshots.expires_at`（执行前记录原值，执行后复位）——需要 `ssh m5air` 免交互（BatchMode）与非交互 `sqlite3`。DB 路径与 SSH 主机可由环境变量覆盖（现有脚本 `at_dp_usage_04.py` 用 `LLMTIER_M5AIR_SSH` 默认 `m5air`、`LLMTIER_M5AIR_DB` 默认 `/Users/mlp/LLMTier-dev/state.sqlite3`）。窗口由 `constants.recent_window()` **动态**生成（禁止硬编码日期）。
- Fixture / 向量及版本：`api_client`（`consumer`）；`ssh m5air` + `sqlite3` 渠道；Run manifest 存档。
- 依赖的测试资产（tests.asset-design 文档）：`api_client`；`ssh m5air` 非交互与非交互 `sqlite3`；`constants.recent_window()`。

## 3. 输入构造

- 逐参数输入构造：两步（生成快照 → 过期后续页）：

```bash
ssh -o BatchMode=yes m5air "sqlite3 /Users/mlp/LLMTier-dev/state.sqlite3 \
  \"SELECT expires_at FROM query_snapshots WHERE snapshot_id='<sid>';\""
ssh -o BatchMode=yes m5air "sqlite3 /Users/mlp/LLMTier-dev/state.sqlite3 \
  \"UPDATE query_snapshots SET expires_at='2000-01-01T00:00:00.000Z' WHERE snapshot_id='<sid>';\""
```

随后重放 `GET /v1/usage?from=<now-30d>&to=<now>&cursor=<sid>:0`。

- 边界/非法取值及理由：`<sid>` 取自首屏响应的 `snapshot_id`；cursor 用 `<sid>:0`（或原样 `next_cursor`）；改写的行必须**确实存在**（先 `SELECT` 校验非空）；`from`/`to` 与首屏保持逐字节相同（虽然过期检查先于 filter 校验，保持一致以排除歧义）；改写的过期值用明确的过去时间且格式与库内一致（`...Z`，含毫秒）。
- 规模 / 时间域：1 次首屏 + 1 次 SELECT + 1 次 UPDATE + 1 次过期重放 + 1 次复位；纯 A 类。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /healthz`/`GET /readyz`（`pytest_configure` 完成，不重复） | §2.1 基线 |
| 2 | 首屏 `GET /v1/usage?from&to` | 200 且 `snapshot_id` 非空，记为 `sid` |
| 3 | 探测 SSH/sqlite3 可用：`_ssh_sqlite("SELECT 1;")` | 不可用 → **BLOCKED**（不得退回用伪 cursor） |
| 4 | `original = _ssh_sqlite("SELECT expires_at FROM query_snapshots WHERE snapshot_id='<sid>';")` | 断言非空（快照确在服务端库内） |
| 5 | **try**：`UPDATE ... expires_at='2000-01-01T00:00:00.000Z'`；重放 `GET ...&cursor=<sid>:0` | `status_code == 400`；`err["code"]=="cursor_expired"`、`err["type"]=="request_error"`、信封恰 5 键 |
| 6 | **finally**：`UPDATE ... expires_at='<original>'`；`SELECT` 回读 | 与 `original` 逐字节相等，证明复位成功 |

- 重点关注步骤：① **真实 TTL 分支**——必须走"快照存在但 `expires_at` 已过"的分支，不得用不存在的 `snapshot_id`/字面量 "expired"；② **改写命中确认**——UPDATE 后应 `SELECT` 回读确认值为过去，证明改写生效；③ **复位完整性**——`finally` 必须恢复**原字符串**（不要用 `now()+10min` 重算），并回读校验；复位失败须保留证据并按 BLOCKED 报，**不得**把 m5air 快照留在过期状态；④ **principal/filter 一致**——用同一 `api_client`（consumer）与同一 `from`/`to`，避免把 403/400 混入；⑤ **无 SSH/DB 权限**——按 **BLOCKED**（可重试，需补 `ssh`/`sqlite3` 权限），并写 `required_resolution`；**不得**记为 SKIP；现有 [`at_dp_usage_04.py`](../../../../tests/system/api_test_v03/at_dp_usage_04.py) 在无权限时调用 `pytest.xfail`，报告工具必须把 `xfailed` **翻译**成 BLOCKED；⑥ **纯 A 类**。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：机制 TTL 规则（`expires_at <= now` ⇒ cursor 不可用）+ OpenAPI `ErrorEnvelope`/`ErrorDetail` + `ERR-CURSOR`（系统设计 §7.8）。**判据语义以设计验证项 `VRC-MGMT-006` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：首屏 `200`，`snapshot_id` 非空；过期重放 HTTP `400`；body `{"error":{"message":<str>,"type":"request_error","code":"cursor_expired","param":null,"retryable":false}}`（恰 5 键）；复位 `finally` 回读 `expires_at == original`。

## 6. 错误路径、副作用与清理

- 错误出口与表现：过期重放未返回 400、或 `code != cursor_expired`、或信封不合规；或复位未完成（即使行为正确，残留过期快照也判 FAIL 并保留证据）。
- 副作用断言与清理：**强制 teardown（`finally`）**——恢复该 `snapshot_id` 行的 `expires_at` 原值并回读校验；不改 provider/deployment/service-level，不写注入项，不删除用户 usage。若复位失败：保留现场、报 BLOCKED/FAIL，不做无边界清理。B 类不适用本 case；若误跑 B 类，按计划整班销毁。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：[`tests/system/api_test_v03/at_dp_usage_04.py`](../../../../tests/system/api_test_v03/at_dp_usage_04.py)。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_usage_04.py -q`。
- 实现状态：Implemented；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：能成功改写为过期并观测 `400 + cursor_expired + type=request_error`，且 `finally` 复位回读与 `original` 相等。
- FAIL：过期重放未返回 400、或 `code != cursor_expired`、或信封不合规；或复位未完成。
- BLOCKED：无 `ssh`/`sqlite3` 权限、SSH 不可达、快照行不可定位等**可重试**环境/工具缺失（须写 `required_resolution` 与 `reproduction_cmd`；**判 BLOCKED，不得降级为 SKIP**）。脚本用 `pytest.xfail` 表达此情形，报告工具须把 `xfailed` **翻译**为 BLOCKED。
- SKIP：就绪检查不满足（m5air 不可达等）。
- INVALID：用伪 cursor/mock 冒充真实过期分支，或用替代路径冒充真实 m5air 路径。
- NOT_RUN：本 Case 有实现，本轮未执行时记 `NOT_RUN`。

**证据与 Run**：Run ID=`<date>/A-api`；保存首屏响应（`snapshot_id`）、SSH 命令与输出（`SELECT` 原值、`UPDATE`、回读校验）、过期重放的原始 status/headers/body、动态窗口值、发出命令、exit code、`elapsed`、环境快照。**证据脱敏**：SSH/DB 命令不含 Secret；`Authorization` 脱敏；`git_commit` 取 m5air 同步来源 commit SHA（本 case `environment:"a"`）。

**依赖**：就绪检查与 DP-USAGE-04 直改 `expires_at` 授权；`ssh m5air` 非交互与非交互 `sqlite3`；`api_client`；机制 [`usage-metering` §4.7 TTL](../../../20_system_design/mechanisms/usage-metering.md)；自动化入口 `at_dp_usage_04.py`。**不依赖**其它 Case；与 DP-USAGE-03（正常分页）、DP-USAGE-07（同 cursor 重放）共享 cursor 语义但各自独立执行。
