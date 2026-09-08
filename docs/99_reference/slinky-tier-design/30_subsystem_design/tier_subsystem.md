# Tier Subsystem Design

Version: v1.16
Last Updated: 2026-09-04 08:12:20
Status: Draft

## 1. 定位与边界

Tier是所有LLM/API/CLI/Agent调用的统一routing Subsystem，拥有`role_name → source Tier → account/backend/model` routing、Backend job、quota/concurrency、provider usage、config/runtime和LLM stats。MLEXP是独立测试执行Subsystem；Tier只通过MLEXP adapter提交和轮询job，不拥有MLEXP worker、Report或Artifact authority。

Tier不理解业务Artifact schema、不决定Task acceptance、不拥有Stage retry/fix。Stage Process只能传Role和业务上下文，不能直接选Backend。

Tier保持独立长驻进程和独立HTTP Service，不是Stage Process内嵌库。Tier HTTP只允许监听`localhost`、loopback或明确private IP，禁止`0.0.0.0`、`::`和public IP；同一受控网络内的Stage Process、Flow、Memory和Dashboard server端都通过`TierClient`调用同一个Tier authority。浏览器只访问统一Dashboard，Dashboard再以same-origin proxy转发Tier route。

## 2. Authority

settings中的`role_tier_map/llm_tiers/provider profiles`、Tier Service runtime/backend state、LLM stats SQLite、provider usage cache和每job response/error sidecar。Backend identity固定`tier:account:model`；credential只存在Tier进程config/ref。

## 3. Formal Module Catalog

| Module | 当前实现 | 职责 |
|---|---|---|
| Tier Client Module | `client.py`、`tier_core.py` | trusted-network HTTP入口、bounded retry/poll、normalized response；不可达时显式失败 |
| Tier Server Module | `server.py`、`router_core.py`、`quota_manager.py`、`concurrency.py`、`provider_usage.py`、`stats_collector.py`、`tier_config.py`、`tier_model.py`、`execution_identity.py`、`backends/` | 独立Tier进程的trusted-network listener、route dispatch、job/runtime lifecycle、routing、quota、stats和management |
| Tier CLI Module | 现有运行入口与运维脚本，后续收敛到独立CLI | 独立调试、runtime/stats 查询、management 与恢复入口 |

Tier Web页面属于WebUI Subsystem，不属于Tier内部Module；Dashboard HTTP Service通过Tier Client Module调用Tier Server Module，不直接import Router/Backend。

## 4. Internal Components

| Component | 当前实现 | 职责 |
|---|---|---|
| Config/Model | `tier_config.py`、`tier_model.py` | mapping、Backend model、persist/reload |
| Router/Quota/Concurrency | `router_core.py`、`quota_manager.py`、`concurrency.py` | selection、Upshift、fallback、capacity |
| Backend Adapters | `src/llm_tier/backends/` | API、CLI、Agent protocol，以及到MLEXP Subsystem的HTTP bridge |
| Provider Usage | `provider_usage.py` | quota usage/cookie/key读取与cache |
| Stats | `stats_collector.py`及`src/stats/llm_stats.py` | call events、query/grouping |
| Client/Service Boundary | `client.py`、`tier_core.py`、`server.py` | Client只走trusted-network HTTP；Tier Service独占Router/Backend/job/stats authority |
| MLEXP Integration Adapter | `backends/mlexp.py` | 使用显式`base_url`消费MLEXP job API，不拥有MLEXP authority |

### 4.1 当前代码调用链

唯一调用路径为`Tier Client Module` 的 `TierClient.invoke_role(payload)` → `Tier Server Module` trusted-network HTTP Service → job → `LLMRouter.call()` → Backend。`TierCore`仅是 client facade，不可达时不得import Router或创建本地job/stats。

迁移必须原子完成：保留唯一Tier HTTP Service与Client、迁移Dashboard/tests、删除Unix socket目标文档和`_TierEmbedded`，不得保留HTTP/IPC双transport。MLEXP adapter继续使用其跨机器HTTP Contract。

## 5. Provided Interfaces

| Interface ID | 名称 | 类型 | 状态 | 调用方 | 入口 |
|---|---|---|---|---|---|
| `TIR-HTTP-001` | Invoke Role与job | HTTP | Implemented | Stage Process/Memory/Flow | `TierClient.invoke_role/call_async/get_result` |
| `TIR-HTTP-002` | Runtime/Stats/Management | HTTP | Implemented | Dashboard/operator adapter | Tier HTTP read/management routes |
| `TIR-PROC-001` | Backend execution | HTTP/Process/File | Implemented | Router/Server | adapter invoke |
| `TIR-DATA-001` | Tier identity/usage/stats | State/SQLite | Implemented | Tier/WebUI | runtime snapshot、usage、stats rows |

### TIR-HTTP-001：Invoke Role与job

payload必填`role_name`以及`prompt`、`user_prompt`或`prompt_path`之一；可选`project/stage/phase/task`、`temperature`、`timeout_seconds`、response/raw/error paths和`response_type=json`。metadata默认`{}`并由Client补齐execution identity。当前返回`ok/content/model_name/error/tier/backend/execution_level/role_profile/latency_ms/token_usage/raw_response/artifact_paths/error_code`；`account`和`backend_type`不在`invoke_role()`顶层返回中，只存在runtime/stats记录，这是当前接口缺口。

### TIR-HTTP-002：Runtime/Stats/Management

HTTP request使用UTF-8 JSON object和明确Method/Path；body上限2 MiB。Tier URL沿用`TierClient.server_url`/`TIER_SERVER_URL`，只接受无credential、无额外path且host为`localhost`、loopback或明确private IP的trusted origin。read route覆盖health/runtime/stats/result；management覆盖probe、Backend、model、concurrency、config和usage。Dashboard只做allowlist proxy并保留Tier HTTP status/JSON error。

### TIR-PROC-001：Backend execution

输入resolved Backend config、prompt/paths、positive timeout和trace必填。API返回provider response/usage；CLI/Agent返回exit和sidecars；MLEXP adapter返回远端job Report。auth/quota/busy/timeout/nonzero/empty/malformed分开；Backend semaphore控制调用并发，MLEXP内部执行并发由MLEXP Subsystem拥有。

### TIR-DATA-001：Tier identity/usage/stats

字段tier/account/backend/model/role/execution identity/scope/status/timestamp必填，usage/error/latency按结果。返回runtime/usage/stats row。缺account、identity冲突或secret字段失败；append非幂等，query幂等。

成功与失败调用使用同一 Backend identity Contract。Router 已经选择并实际调用 Backend 后，即使最终因 quota、Backend error 或 unexpected error 失败，result 与 raw stats event 仍必须保留本次实际选择的`tier/account/backend/model`、latency 和可确定的 token usage；禁止用空 identity 写入失败事件，否则项目、Stage、Task 和账号维度的`fail_count`将失真。

## 6. Operational Contract

| Interface ID | 幂等/并发 | timeout/retry | 安全/可观测性 | 测试证据 |
|---|---|---|---|---|
| `TIR-HTTP-001` | call/job非幂等；Backend/account concurrency限制 | HTTP connect/read与operation deadline；bounded busy retry/poll | explicit trusted bind、禁止wildcard/public bind、credential Tier-side；job/stats/sidecars | HTTP client/service/job/system cases |
| `TIR-HTTP-002` | read幂等；management非幂等；race coordination Partial | HTTP timeout；save/reload不盲重试 | route allowlist、account/secret保护；management events | HTTP management/quota/concurrency/race cases |
| `TIR-PROC-001` | provider/process/job非幂等，Tier semaphore控制提交，MLEXP控制执行 | adapter timeout；Router bounded retry；MLEXP poll timeout | argv/path/secret隔离；MLEXP payload不得携带credential | API/CLI/Agent与`test_mlexp_backend.py` |
| `TIR-DATA-001` | stats append非幂等、query幂等 | SQLite/HTTP timeout | account/identity保留、secret禁入库 | LLM stats/identity/provider usage tests |

## 7. Failure And Module Design

quota exhausted/disabled/unreachable Backend不参与selection，busy Backend进入等待/重试语义；同Tier可fallback，context capacity可Upshift。全部不可用明确失败。Task Escalation由Stage Process拥有。Backend进入exhausted后，Server必须沿用现有single-backend probe接口每600秒执行一次真实恢复probe；失败保持exhausted并继续下一周期，成功通过现有quota reset路径恢复eligible并取消后续timer。provider reset时间保留为usage展示数据，不能替代或延后600秒周期probe。后续设计只围绕现有Client、Server/Job、Config、Router、Backend、Usage和Stats模块补齐接口测试，优先解决reload/probe/call/usage race及`invoke_role()`缺少account/backend_type的问题，不新增第二套routing。

### Known Bugs

- `TIR-BUG-001`：已完成。`TierCore`不可达时不再切换`_TierEmbedded`；唯一HTTP Service不可达会显式失败。
- `TIR-BUG-002`：已完成。Tier Server与Client不再硬编码loopback；现有HTTP机制允许明确private IP，使跨主机/容器调用共享唯一routing、quota与concurrency authority，同时拒绝wildcard/public listener。

## 8. 可测试性设计

Tier Subsystem 的可测试性设计必须覆盖 routing、quota、concurrency、provider usage 和 MLEXP adapter 边界，而不能只测普通成功调用。

固定要求如下：

- route / identity 可构造
  - 必须能用 fixture config、duplicate backend、missing account、role_tier_map drift 等数据独立验证 routing 和 identity 聚合。
- provider / backend 失败可分型
  - exhausted、busy、unreachable、auth failure、timeout、malformed response、nonzero CLI exit、MLEXP terminal failure 必须分开断言。
- runtime snapshot 可重置
  - runtime state、recent errors、quota probe、stats snapshot 必须支持在测试前初始化、清零或重建，避免旧状态污染结果。
- adapter 边界可独立验证
  - `mlexp` adapter 必须能在假 server / fixture response 下独立验证 payload、polling、timeout、terminal mapping 和 error precedence。
- observability 可核对
  - stats rows、backend identity、execution identity、usage source 和 grouped summary 必须能被独立断言，不允许只依赖 UI 间接观察。
  - 必须分别注入 quota、BackendCallError 和 unexpected exception，断言终止失败 result/raw stats event 保留实际选择的 Backend identity，并能按项目与账号聚合失败计数。

### 8.1 Runtime Topology 与关键业务 Flow

| Flow ID | Module 顺序 | Branch / barrier | 最终 authority |
|---|---|---|---|
| `TIR-FLOW-001` | TierClient -> HTTP Service -> Router -> Backend -> result | success/typed failure/unknown outcome | response sidecar |
| `TIR-FLOW-002` | submit -> job -> Backend -> poll -> terminal | timeout/cancel/restart | job authority |
| `TIR-FLOW-003` | role -> Tier -> eligible account/model -> fallback/upshift | disabled/exhausted/busy/context limit | selection trace |
| `TIR-FLOW-004` | management -> config/runtime -> probe/state commit | save/reload/enable/disable/race | config/runtime revision |
| `TIR-FLOW-005` | call result -> raw stats event -> grouping/filter | retry/replay/stats failure | stats DB/API |
| `TIR-FLOW-006` | MLEXP adapter -> submit/poll/cancel/artifact | queued/running/terminal/timeout | Tier job + MLEXP refs |
| `TIR-FLOW-007` | Dashboard proxy -> TierClient -> Tier HTTP | read/management/error | API + DOM evidence |

### 8.2 Failure Propagation 与 Recovery

- transport failure、unknown outcome、Backend typed error和stats failure必须分离。
- 非幂等submit收到unknown outcome时不得自动重提。
- 同Tier fallback与Capacity Upshift必须分别记录，不得互相替代。
- quota/concurrency claim必须原子，terminal后释放capacity。
- config reload、probe和running invoke竞态不得产生双authority。
- cleanup必须释放listener、probe timer和job资源，保留审计sidecar。

### 8.3 Subsystem Test Binding

Subsystem Test 必须启动真实Tier Service并通过TierClient/HTTP/CLI/Browser public entry执行；既要覆盖loopback，也要覆盖明确private IP的Server/Client admission。Backend provider、CLI和MLEXP远端可以使用controlled service；Client、HTTP、Router、quota/concurrency、stats、MLEXP adapter和same-origin proxy不得被mock。
