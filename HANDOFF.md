# LLMTier → OpenCode 开发交接

> 快照日期：2026-09-19（Asia/Hong_Kong）。这是接手导航和待办记录，不是新的设计或机器契约 authority。开始工作时先复核 Git、测试和 m5air 实况；不要把本页的时间敏感状态当成永久事实。

## 1. 从哪里接手

- 仓库：`/Users/ben/work/LLMTier`；远端：`git@github.com:corezilla/LLMTier.git`。
- 当前分支：`docs/std-draft21-upgrade`；HEAD 与该远端分支在交接检查时均为 `868a3eecbc929ea8218a5cd8c3ef7780a1750187`。不是 `main`。
- 本机工作树的 `.claude/`、`AGENTS.md`、`CLAUDE.md` 是已有未跟踪项；不要顺手加入、覆盖或清理。
- 开发目标是 `src/llmtier_v03/` 的单节点 OpenAI-compatible 网关。`src/` 中的 legacy Tier 实现及 `docs/99_reference/` 仅作历史参考，不是并行 consumer 路径或配置 authority。
- 当前 OpenAPI/compatibility manifest 版本为 `0.3-simplified-candidate.7`，`overall.runtime_activation=false`。已有局域网测试服务不等于生产激活。
- 当前锁定 STD 为 `0.1.0-draft.26`、revision `f892b167b9fc7b8beb9dbdebb9209009d4334ce1`（`docs/std.lock.json`）。不要因为本机 STD checkout 不匹配而擅自升级锁。

阅读顺序：`README.md` → 本文件 → `docs/80_operations/m5air-operations-manual.md` → `docs/20_system_design/llmtier-system-design.md` → `docs/40_module_design/llmtier-core-design.md`、`docs/40_module_design/webui-design.md` → `interfaces/openapi/llmtier-v0.3.openapi.json` 与 `interfaces/compatibility/compatibility-manifest-v0.3.json` → 相关测试。字段以 OpenAPI 为准；历史文档或旧 UI 不得覆盖它。`README.md` 和部分计划/验证文档仍有旧“中文三页 UI”“/ui/ 为入口”等叙述，修改相关功能前应与实际代码及手册核对。

## 2. 当前已实现和已验证范围

- 标准 `/v1/responses`（固定 Pi 所需 SSE、文本、tool、refusal、history）、`/v1/embeddings`、`/v1/models`；LLMTier 不保存 Agent 会话、不压缩上下文、不执行工具。
- 固定 Tier、Provider/Deployment 管理、健康探测、内部路由/并发保护、SQLite token Usage、审计和脱敏日志；英文 Web UI 有 Home、Providers、Usage & Audit、Logs 四页。
- 最近一次提交迁回旧版所需的账号能力：MiniMax Token Plan 读取、火山 Coding Plan 读取、Provider 账号级最大并发/请求间隔/RPM、最终选中 Provider 的调用/Token 归属、Providers 页面手动刷新及状态展示。实现集中在 `src/llmtier_v03/account_usage.py`、`registry.py`、`routing.py`、`usage.py`、`app.py` 和 `webui/`。
- 2026-09-18 的只读真实接口验证：MiniMax 用现有推理 API Key 调用 `GET https://www.minimaxi.com/v1/token_plan/remains` 成功，**不需要 console Cookie**；火山用独立 OpenAPI AK/SK 签名调用 `GetCodingPlanUsage` 成功，推理 API Key 不能替代 AK/SK。没有把凭据值写进 Git/文档。供应商用量只能由 operator 显式刷新；普通 GET 读本地快照，不自动触网。
- m5air 测试部署设置：MiniMax 账号最大 5 并发、最小间隔 500 ms、120 RPM；火山最大 10 并发、500 ms、120 RPM；本地 Provider 最大 4 并发。这些是部署配置，不要擅自当作所有环境默认值。

## 3. 交接时的验证结果与首要问题

2026-09-19 本机重新执行：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
```

结果为 **185 tests，184 通过、1 失败**。失败项是 `tests/test_contract_semantics_v03.py::SimplifiedV03ContractTests.test_admin_surface_is_model_focused`：测试第 241 行仍期望中文六页 `['主页','添加模型','运行状态','用量','审计','日志']`，而 current manifest 的 `admin_web_ui.pages` 已改为英文四页 `['Home','Providers','Usage & Audit','Logs']`，与实际 `src/llmtier_v03/webui/index.html` 一致。上一轮报告的 185/185 PASS **不是当前工作树的事实**。第一步应统一 current manifest、测试及受影响的当前文档；不要为了让测试绿而把产品页面改回旧布局。修订测试函数前遵守本项目 `AGENTS.md` 的 GitNexus impact 要求。

已运行的 m5air 只读检查：`state.sqlite3` 的 `PRAGMA integrity_check` 返回 `ok`；`/healthz` 返回 `ok`，`/readyz` 中七个 Tier 均为 `available`；8181 由单个 `llmtier_v03` 进程监听。健康与 readiness **不证明**本轮全部模型调用、故障恢复、长期容量或浏览器 E2E 已通过。Provider Calls/Tokens 在部署中当前为 0/Unknown；新归属功能不对历史调用做凭空回填。若要验证该计数，使用获授权的明确测试请求并核对 Usage，不能把 Unknown 写成 0。

推荐接手检查：

```bash
git status --short && git branch --show-current && git rev-parse HEAD
git ls-remote origin refs/heads/docs/std-draft21-upgrade
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/contract_semantic_validator_v03.py
git diff --check
```

## 4. m5air 测试部署与安全边界

- SSH：`ssh m5air`（当前目标 `mlp@192.168.1.9`，IP 使用前重查）。部署目录 `/Users/mlp/LLMTier-dev` **不是 Git 工作树**；不能在该目录 `git pull`。Python 用 `/usr/local/bin/python3`，不是 macOS 自带的旧解释器。
- 服务直接监听 `0.0.0.0:8181`；Web UI 入口为 `http://192.168.1.9:8181/`。无开机自启，机器重启后按 `docs/80_operations/m5air-operations-manual.md` 手动启动。不要另开并行端口/进程。
- 现有 SQLite 是 `/Users/mlp/LLMTier-dev/state.sqlite3`，配置 authority 在 SQLite。`settings.json` 仅是空库 bootstrap 来源，不能拿它覆盖现有运行配置。部署更新前先确认端口/进程，并用 SQLite backup API 或手册方式备份现有库；`src/llmtier_v03/migrations/001_initial.sql` 在启动时执行。
- m5air 的 Secret 目录是 `/Users/mlp/LLMTier-dev/secrets/`，含 MiniMax 推理 API Key、火山推理 API Key 与火山用量 AK/SK 文件；只传引用，保持 owner-only 权限。不要打印、复制到 handoff、提交、上传或放入测试输出。旧 MiniMax console Cookie 不属于现行 V0.3 用量方案。
- 目前 `LLMTIER_TRUSTED_LAN_MODE=1`：可信局域网主机无需登录即可获得共享 operator/data 权限。不得暴露到公网、访客 Wi-Fi 或不可信 LAN；它也不提供用户级管理审计隔离。生产认证/TLS/CSRF 仍是独立门禁。
- 操作、启动/停止、备份、回滚、Provider/Tier 管理的完整步骤见上述运维手册。更新源码后必须核对部署文件版本、浏览器页面、`/healthz`、`/readyz`，并复跑适当测试；不要仅凭 push 声称 m5air 已更新。

> 2026-09-19 17:30 HKT 补做：sync commit `1c026e7`（5 docs + 1 test，共 6 文件）至 m5air；冷备份 `state.sqlite3.*.cold-pre-1c026e7-20260919-124217` 已留存于 `/Users/mlp/LLMTier-dev/backups/`；当前 LLMTier PID 6663；OMLX PID 698（operator 重启，配置已变化）。FD 泄漏与 OMLX auth 不匹配见 §5.3。

## 5. 下一步工作与完成判据

1. **先消除当前回归**：英文四页 UI 与 manifest/test/当前文档达成一致，完整本机测试与 contract validator 通过；记录命令和计数。当前 README、实现计划与 V&V 中的旧页面、旧阶段文字需要逐项审视，但不要把历史 review 文件机械改成 current。
2. **单系统补测**：对账号用量解析错误、缺凭据、外部超时、手动刷新授权、快照失效、账号并发/间隔/RPM、Provider 绑定后 Usage Unknown/Partial、UI 状态进行定向测试。真实供应商请求可能计费或改变 quota，运行前遵循用户授权和运维手册。
3. **设计/实现门禁继续分离**：浏览器 E2E、进程 crash/SQLite 恢复、长期并发/性能、Piko 固定 Pi consumer、Slinky Embedding consumer、生产 TLS/auth/CSRF 与 `runtime_activation=true` 均未由本 handoff 宣称完成。联调和生产激活须分别获得明确决定，不自行扩大范围。
4. **提交纪律**：先查 `AGENTS.md`；任何函数/方法改动前对该 symbol 做 GitNexus upstream impact 并报告直接调用方、流程和风险；HIGH/CRITICAL 先告知用户；提交前运行 `detect_changes()`、测试和 `git diff --check`。只 add 本任务文件，保留其他未跟踪项。需要部署或 push 时分别核对远端 SHA 与实际 m5air 状态。
5. **§5.2 单系统补测进度（2026-09-19 17:30 HKT，operator=ben，全真实路径）**：

   | # | 项目 | 结果 |
   |---|---|---|
   | T8 | UI 状态 | ✓ Home / Providers / Usage & Audit / Logs 四页 200，7 Tiers available，3 Providers，4 Deployments |
   | T4 | 手动刷新授权 | ✓ 不带 `confirm_external_call` → 400 `invalid_request: Usage refresh accepts only confirm_external_call` |
   | T2 | 缺凭据 | ✓ 带 confirm 但 secret_ref 为空 → snapshot 200, `source=credentials_missing`, `error=minimax_usage_requires_api_key`，零真实 quota 调用 |
   | T1 | 解析 / 4xx | ✓ `file:` 引用 junk key → 真实 MiniMax 返回 401-style 错误 → snapshot 200, `source=provider_api_error`，上游错误原文保留（≤160 字符） |
   | T5 | 快照一致性 | ✓ 同参数两次读产生不同 snapshot_id；cursor 命中 frozen view；bad cursor → 400 `cursor_expired` |
   | T7 | Usage Unknown | ◐ 失败 Responses（OMLX 暂不可用时）→ obligation 已写：`measurement_status=unknown, source=unavailable, record_version=2, is_final=true, tokens=null`；成功路径未跑通（OMLX auth 阻塞） |
   | T6 | 账号并发/间隔/RPM | ✗ 未做（FD 泄漏 + OMLX auth 阻塞） |
   | T3 | 外部超时 | — 按 operator 决定跳过 |

   测试过程中已临时创建 / 删除若干测试 Provider（id 含 `provider_test` 或类似随机后缀），不留存。

6. **§5.3 §5.2 测试中暴露的阻塞（pre-existing）**：

   1. **FD 泄漏**（commit `b89ba4d` 已修）：LLMTier 原 PID 6663 运行约 3h 已达 118/256 fds（macOS 默认 `ulimit -n=256`）。日志反复出现 `OSError: [Errno 24] Too many open files: '.../webui/{index.html,app.js,styles.css,icons.svg}'` 并触发级联 `sqlite3.OperationalError: unable to open database file`。根因：每个请求由 `ThreadingHTTPServer` 起新线程，`BaseHTTPRequestHandler.finish()` 关闭 rfile/wfile 但不动 `Store._local` 缓存的 SQLite 连接；连接持有的 db+wal+shm 三 fd 在 Python 延迟的 thread-local 清理之前一直滞留。修复：在 `src/llmtier_v03/app.py:_run` finally 加 `app.store.close()`。本地与 m5air 验证：250 个 mixed 请求后 FD 数恒为 40（修复前每请求 +3），SQLite fds 恒为 5（1 db + 1 wal + 1 shm + lsof artifact）。同时顺手修 `src/llmtier_v03/registry.py:144` `has_secret` 判定从 `is not None` 改为 `bool(...)`，让空字符串 `secret_ref` 正确显示 `False`（之前误报 `True`）。回归风险：LOW——per-request 开连接的开销本来就在（每请求一个线程），仅是把 close 提前到 finally。

   2. **OMLX auth 不匹配**（部署配置修复，commit 留空）：当前 OMLX（PID 698）`/Users/mlp/.omlx/settings.json` 的 `auth.api_key="9832"`，需要 `Authorization: Bearer 9832`；LLMTier 原 `provider_local.secret_ref=""` 不发送 Authorization 头。修复（部署配置，非代码）：在 `/Users/mlp/LLMTier-dev/secrets/omlx-secret-key.txt` 写入 `9832`（mode 600），PATCH `provider_local.secret_ref` 指向该文件（v3→v5），LLMTier 即按 `file:` 路径读 secret 并发送 Authorization 头。验证：直接 `curl /v1/responses` Bearer 9832 → 200 + 正常 SSE；LLMTier 经 OMLX 调通后，Usage 写入 `req_2fadeec4...` `measurement_status="measured" source="provider" input=14 output=3 total=17`（T7 measured 路径打通）。

7. **§5.2 测试补完（2026-09-19 18:00 HKT）**：

   - **T7 measured** ✓（OMLX 修复后）：临时禁用 Worker 路由中排在前面的 dep_minimax_m27 / dep_volc_deepseek（routes 经 dep_local_gemma 走 OMLX），发送 `{"model":"Worker","input":"say hi in one word","stream":true,"store":false,"max_output_tokens":16}`，得到 200 + SSE 含 `"usage":{"input_tokens":14,"output_tokens":3,"total_tokens":17}`；`/tier/admin/v1/usage` 出现 `measurement_status="measured" source="provider"` 记录。之后 PATCH 回 enabled=true 还原。
   - **T6 并发限速** ◐（部分）：临时禁 dep_volc_deepseek 让 Worker 仅 dep_minimax → dep_local 顺序路由，6 个并发 `Responses` 请求得到 4×200 / 2×503（OMLX localhost 并发连接受限 + provider_minimax `max_in_flight=1` 排队）；FD 数 41 → 46，稳。完整 RPM / interval 验证需要 cloud provider 突发流量（已超出本轮范围）。`routing.py:_provider_ready_in` 的 interval / RPM 计算与 `_limit` / `_inflight` 的 in-flight 计数也已实现并在生产路径生效。
   - **T3 外部超时** — 按 operator 决定跳过（fake-only）；不入 commit。

   2026-09-19 17:45 HKT 更新：FD 泄漏已在 m5air（PID 7079，commit `b89ba4d`）验证修复，250 个 mixed 请求 FD 数稳定。
   2026-09-19 18:00 HKT 更新：OMLX auth 通过部署层 secret_ref 已修复，T7 measured 路径打通，T6 并发部分验证。

## 6. 不要恢复的旧设计

不要从 legacy 迁回 Agent Session/Conversation authority、模型内部 KV identity、跨系统 Seat/claim/capacity 产品、自定义 Invocation/幂等恢复、Cost、SourceInstance、额外管理页面或 `/call` consumer fallback。真实需求若超出标准 OpenAI-compatible surface，先给出具体缺口、最小扩展、成本和兼容影响，再做显式设计审查。
