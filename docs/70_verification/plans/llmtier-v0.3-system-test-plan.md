<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 System Test Plan

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-v0.3-system-test-plan` |
| Document Version | `0.3.2-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | LLMTier, Piko, Slinky |
| Approver | 待定 |
| Approval Date | 待定 |
| Created Date | `2026-09-19` |
| Last Modified Date | `2026-09-19` |
| Template Version | `0.1.0` |
| Template ID | `assurance.system-test-plan` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | `llmtier-v0.3-vv-plan`, `llmtier-v0.3-contract-test-specification` |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/plans/llmtier-v0.3-system-test-plan.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 目标、范围与 authority

本文件定义 **runtime** 端的系统级测试计划，区别于 `llmtier-v0.3-contract-test-specification.md`（静态契约）与 `llmtier-v0.3-vv-plan.md`（高层 V&V）。系统测试在真实启服的 LLMTier 进程 + 受控 provider 上做端到端探针，证据是 HTTP 请求/响应、SQLite 状态、SSE 事件序列、FD 计数与日志抽样；单元 mock 与 fake provider 只在无法隔离的子路径上使用，且必须标注。

- 被测对象：运行中的 `llmtier_v03` 进程、与至少一个真实 OpenAI-compatible provider（Piko 端点、Mock 或受控云端）。
- 不被测：浏览器自动化 E2E、生产 TLS/auth/CSRF、`runtime_activation=true`、LLMTier 跨系统恢复状态机。这些保留为 §5.3 后续门禁（见 V&V plan §5）。
- authority：`/v1/responses`、`/v1/embeddings`、`/v1/models`、`/tier/v1/usage`、`/tier/admin/v1/*` 的运行时行为；OpenAPI 是字段层 machine authority。
- 编排权：本计划生成的测试脚本（`tools/system_test_*.py` 与 `tests/system/`）归属 LLMTier，可由 CI 或 operator 手动执行。

## 2. 被验证基线与环境

### 2.1 必满足的前置

| 前置 | 状态 / 期望值 |
|---|---|
| 代码 commit | 与本计划记录的 `expected_commit` 一致；HEAD 在 deploy 节点上是同一 SHA |
| `tests/` 单元测试 | 全绿，`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests` exit 0；baseline ≥191（截至 `dfac99e`） |
| 进程可启服 | `python3 -m llmtier_v03 --host 127.0.0.1 --port <port> --database <db> --settings <bootstrap>` 60 秒内 listen；`/healthz` 200，`/readyz` 200 且 7 个 tier 全部 `available` |
| 可信 LAN 模式 | 默认 `LLMTIER_TRUSTED_LAN_MODE=1`，RFC1918/ULA 来源自动获得 `trusted-lan-operator` / `trusted-lan-consumer` principal |
| Provider adapter | 至少一个 `local`（fake 或真 OMLX）和一个 `cloud`（Piko 端点或受控云）真实可达；调用超时 ≤ 30s |
| SQLite | `state.sqlite3` 启动时执行 `001_initial.sql` migration；`PRAGMA integrity_check` 输出 `ok` |
| FD baseline | 进程启服后 60 秒空闲状态下 `lsof -p $PID | wc -l` ≤ 60 |

### 2.2 排除条件

- 当前 commit 缺 FD 泄漏修复（`b89ba4d`）或 SSL 上下文修复（`a6f06af`）时，**禁止**执行 ST-08 长期并发；脚本必须先 `git rev-parse HEAD` 验证。
- 任何带 `confirm_external_call=true` 的真实云端 refresh 必须在 operator 显式授权下执行；测试固件中如使用真实云 key，必须先离线 `confirm_external_call` mock 化。

## 3. 测试类别与责任边界

| ID | 类别 | Owner | Evidence 落点 |
|---|---|---|---|
| ST-01..ST-04 | 启服与静态 smoke | LLMTier | `/healthz`、`/readyz`、单元测试报告 |
| ST-05..ST-09 | Data plane end-to-end（Piko 路径） | LLMTier + Piko fixture | SSE 序列、Usage 记录 |
| ST-10..ST-12 | Data plane end-to-end（Slinky embedding 路径） | LLMTier + Slinky fixture | `/v1/embeddings` 响应、`Embedding-v1` 维数与 space |
| ST-13..ST-17 | Admin operator 场景 | LLMTier | Web UI HTML + admin API CRUD 状态码 |
| ST-18..ST-20 | 可靠性（FD、restart、WAL 持久化） | LLMTier | `lsof` 计数、SQLite integrity、Audit 链 |
| ST-21..ST-23 | 性能与限速 | LLMTier | 端到端 latency、`/runtime` 快照 |
| ST-24..ST-25 | 安全与 TRUSTED_LAN | LLMTier | bearer 401、loopback/RFC1918 授权差异 |

每个 case 必须产生：调用前状态、调用、调用后状态、判定。失败 case 必须包含 `failure_reason` 字段，写明预期 vs 实际 + 触发步骤 + 复现命令。

## 4. Case 矩阵

| ID | Case 名 | 步骤摘要 | 预期 |
|---|---|---|---|
| ST-01 | 启服 baseline | 启服进程 → 60 秒 idle → `/healthz` `/readyz` 各 5 次 | 全部 200；7 tier `available`；FD ≤ 60 |
| ST-02 | 单元测试入口 | 跑 `tests/` 全集 | exit 0，全部 ≥191 PASS |
| ST-03 | `tools/contract_semantic_validator_v03.py` | 解析 + Schema 校验 | exit 0，stdout 空 |
| ST-04 | Forbidden path/header 扫描 | 跑 `test_contract_semantics_v03.SimplifiedV03ContractTests.test_admin_secret_is_not_returned` 等 | 全部 PASS，无 legacy `/call` 引用 |
| ST-05 | Piko Responses text | `POST /v1/responses` 模型=Worker 输入=hi，stream=true store=false max_output_tokens=128 | 200；SSE 含 `response.created / response.output_item.added / response.output_text.delta / response.output_text.done / response.output_item.done / response.completed / [DONE]`；terminal `response.completed`；`usage.input_tokens/output_tokens/total_tokens` 非 null |
| ST-06 | Piko Responses reasoning | 同 ST-05 但 OMLX/gemma 自动产出 reasoning item | SSE 额外含 `response.reasoning_text.delta / .done`；reasoning 与 message 两个 item 的 `item_id` 在所属 delta 内一致 |
| ST-07 | Piko Responses function tool | 带 `tools:[{type:function, ...}]`，期望 `response.function_call_arguments.delta / .done` | 上述 SSE 事件齐全；item id 一致 |
| ST-08 | Piko Responses 并发 8 路 | 临时禁非 OMLX deployment，让 Worker 强制走 OMLX；8 路并行 `POST /v1/responses` max_output_tokens=64 | ≥1 路 200；FD 数 ≤ 80；无 5xx 非限流错误 |
| ST-09 | Piko Responses 错误目录 | 5 个 400 + 1 个 404 子 case（`stream:false`、`store:true`、缺字段、`previous_response_id`、未知 model） | 全部 400/404；错误 envelope `code=invalid_request` 或 `model_not_found` |
| ST-10 | Slinky embedding | `POST /v1/embeddings` model=Embedding-v1 input="hello world" | 200；`data[0].embedding` 长度=1024；无 NaN/Inf |
| ST-11 | Slinky embedding base64 | 同 ST-10 + `encoding_format=base64` | base64 字符串解码后 1024 个 little-endian float32；全部 finite |
| ST-12 | Slinky embedding space 不变量 | 5 次 ST-10；每次 `model=Embedding-v1` | 每次维数=1024；同一 logical model `embedding_space_id` 相同 |
| ST-13 | Operator 创建 Provider | `POST /tier/admin/v1/providers` 含 secret_ref；GET 验证 `has_secret=true`；DELETE 清理 | 201；response 含 id/etag；DELETE 204 |
| ST-14 | Operator 创建 Deployment + bind Tier | POST deployment → POST tier PATCH 加 deployment_ids | 201/200；`/v1/models/{id}` 200 含新 capability |
| ST-15 | Operator Probe 授权 | `POST /tier/admin/v1/probes` 无 confirm → 400；带 confirm=true → 200，response 含 `status=healthy/unhealthy` | 两路状态码与字段正确 |
| ST-16 | Operator 账号 quota refresh | 同样 confirm 校验；针对已有 AK/SK 的 provider_volc 真实调用 | 400 / 200；snapshot 持久化；错误路径不污染窗口 |
| ST-17 | Operator 页面（headless） | curl `/`、`/ui/`、`/ui/index.html`、`/ui/app.js`、`/ui/styles.css`、`/ui/icons.svg` | 全部 200；`Cache-Control: no-store`；HTML 内含 5 个 `<section class="page">` 与 5 个 nav 按钮（Home / Providers / Stats / Usage & Audit / Logs） |
| ST-18 | FD 稳定性（短期） | 跑 Piko smoke 全部 ST-05..ST-09（约 50 个请求） | FD ≤ 80；`lsof | grep state.sqlite3` ≤ 8 |
| ST-19 | FD 稳定性（长期，2h） | 启服 → 维持 60 并发 5s 间隔发 `POST /v1/responses` 持续 2h；每 30 分钟采样 FD | FD 在 30 分钟内达到稳定值，不出现 `Too many open files` 或 `unable to open database file`；终值 ≤ 200 |
| ST-20 | Process crash + restart | kill -9；5 秒后重启；`PRAGMA integrity_check`；Audit 链连续；Usage 最新 `record_version` 仍可查 | integrity=ok；Audit 无丢；Usage obligation 在 restart 后仍能 finish unknown |
| ST-21 | End-to-end latency P50/P95 | 50 路顺序 Worker Responses（OMLX） | P50 ≤ 1.5s，P95 ≤ 3s；记录样本 N=50 |
| ST-22 | Provider 限速触发 | 临时把 `provider_local.max_concurrent_requests=1`；6 并发；至少 5 路返回 429 带 `Retry-After` | 5×429（`code=rate_limit_exceeded`）；`Retry-After` 头存在 |
| ST-23 | Tier 队列满 | 临时把服务级队列 32 → 1；33 路同时打 Worker；后续 32 路排队 | 第 33 路 `429`；已入队不被立即拒 |
| ST-24 | Auth bypass 阻击 | 从非 RFC1918 来源（不可达时跳过）或非 TRUSTED principal 发 `/v1/responses` 无 bearer | `401 authentication_required` |
| ST-25 | TRUSTED_LAN 主子分流 | 同主机 loopback 发 `/tier/v1/usage`；同主机 RFC1918 alias 发 `/v1/responses` | 数据面 usage 走 principal；admin `/tier/admin/v1/stats` 仍然返回完整聚合 |

## 5. 测试套件编排

### 5.1 工具与脚本

新增：

- `tools/system_test_runner.py`：编排器，参数 `--port`, `--database`, `--provider`, `--commit`, `--cases ST-01,ST-05,...`，按依赖顺序执行；每个 case 起子进程 `python3 -m tools.system_test_cases.<name>` 并捕获 stdout/stderr/exitcode，写入 `artifacts/system/<timestamp>/<case>.json`。
- `tools/system_test_cases/`：每个 case 一个文件，例如 `st05_responses_text.py`、`st18_fd_short.py`。
- `tests/system/`：firewall 把系统测试连进 `python3 -m unittest`，路径 `tests.system.test_st_*`；可与现有 191 个单元测试合并跑。

### 5.2 执行顺序与依赖

```
ST-01 → ST-02/ST-03/ST-04（可并行） → ST-05/ST-07（共用 Piko fixture）
                                → ST-08（独占临时 deployment 切换）
                                → ST-09（独立错误目录）
                                → ST-10/ST-11/ST-12（共用 Slinky fixture）
                                → ST-13/ST-14/ST-15/ST-16（按 CRUD 顺序）
                                → ST-17（headless 静态）
                                → ST-18（短期 FD，跑完 ST-05..ST-09 后顺跑）
                                → ST-19（2h FD 长期，需独立时间段）
                                → ST-20（crash + restart，独立窗口）
                                → ST-21/ST-22/ST-23（性能与限速，独立）
                                → ST-24/ST-25（安全，独立）
```

ST-19 因持续 2 小时，**默认不在 PR 阶段跑**；由 operator 在预发环境手动执行，结果写入 `artifacts/system/long_fd/`。

### 5.3 复跑与并发

- 每个 case 在新临时 SQLite（`/tmp/llmtier_system_<uuid>.sqlite3`）下重新启服，避免污染主 state。
- ST-08/ST-19/ST-22/ST-23 在 case 内自动恢复 deployment 状态（enablement、max_concurrent）。
- 测试结束后由 ST-19 维护一个 `teardown.sh`：kill 进程、rm 临时 SQLite 与临时 secret 文件、撤销 ST-08/ST-22 的 PATCH。

## 6. Pass / Fail / Blocked / Invalid 判定

| 状态 | 含义 |
|---|---|
| PASS | case 所有预期字段与 oracle 字段一致，exit 0，evidence 完整 |
| FAIL | 实际输出与预期至少一处不一致；记录 `failure_reason` 与重跑命令 |
| BLOCKED | 受真实外部依赖限制无法跑（如云端 API 限流、OMLX 未运行）；记录 blocker 字段与解除条件 |
| INVALID | case 设计错误或预期本身不成立；记录 issue，需重新设计 |

ST-19 与 ST-20 是 §5.3 阻塞项的解封步骤；只有当 ST-19 PASS 才能将 `runtime_activation` 决策前的 `process-restart` 门禁视为 GREEN。

## 7. Evidence、traceability 与签署

- 落档目录：`artifacts/system/<UTC-timestamp>/`，包含：
  - `summary.json`：所有 case 的 PASS/FAIL/BLOCKED/INVALID 计数
  - 每 case 一份 `<id>.json`：命令、stdout、stderr、exit、Oracle diff、duration_ms、commit SHA
  - `env.json`：OS、Python 版本、ulimit、provider endpoint 摘要（不含 secret）
- traceability：每个 case 在本计划里声明其关联的 requirement/contract：
  - ST-05..ST-09 → CT-DP-001（fixed-Pi Responses SSE）
  - ST-10..ST-12 → CT-EMB-001（embedding float/base64/space）
  - ST-13..ST-16 → CT-ADMIN-001（CRUD/probe/secret）
  - ST-17 → CT-WEBSEC-001（headless 起点，非 browser E2E）
  - ST-18/ST-19 → §5.3 长期并发/性能
  - ST-20 → §5.3 进程 crash/SQLite 恢复
  - ST-21 → CT-OPS-001（no-cost probe separation 的实际体验）
  - ST-22/ST-23 → CT-ADM-001（admission / 并发 / FIFO / 429）
  - ST-24/ST-25 → §5.3 安全 / auth / TRUSTED_LAN
- 不落档：任何 `secrets/` 下的文件、生产 prompt/output、provider payload、真实 credential。FAIL 时也只写差异，不重发受 payload 影响的请求。
- 签署：LLMTier author + operator +（若涉及 Piko / Slinky 集成）consumer owner；任何 FAIL 需在 summary 附 issue id。

## 8. 偏差、waiver、问题与重测

- 偏差需关联 `requirement id`、`case id`、`commit`、`env`、`owner`、`due`、`approver`，存于 `artifacts/system/<ts>/deviations.json`。
- 不可用 legacy `/call`、旧 `/admin` 路径、ASGI/Tornado 等非 Python stdlib HTTP 路径来绕过失败。
- 重测：每次 commit 含 `b89ba4d` / `a6f06af` 等修复时，重跑 ST-01、ST-02、ST-05、ST-09、ST-18；其它按变更范围。

## 9. 当前缺口与下版

- 本计划不覆盖浏览器自动化 E2E（Playwright/Selenium 套件）、生产 TLS/auth/CSRF、`runtime_activation=true` 后的多实例 / HA / 跨系统恢复——这些按 §5.3 单独规划。
- ST-19 默认不进入 PR；正式 release 前至少完整跑一次 ST-01..ST-25，并在 §5.3 解除对应门禁。
- 与现有 `tests/v03/test_*.py` 的 24 个单元测试文件并存；系统测试不取代单测，只覆盖 runtime + 多 component 集成。