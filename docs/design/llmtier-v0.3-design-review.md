# LLMTier V0.3 总体设计评审稿

Last Updated: 2026-09-06

Status: Review Amendment 2；已纳入 Piko baseline/recovery 信息，scope 冲突待裁决，不构成兼容性激活

Reviewers: Slinky、Piko

Code baseline: `https://github.com/corezilla/LLMTier`，review base `main@b452b63`

## 1. V0.3 交付目标

LLMTier 从 Slinky 的旧 embedded Tier 拆分为独立模型服务。V0.3 必须形成一个可管理、可观测、可由 Piko 调用的完整系统范围：

1. 面向 Piko 的统一 OpenAI-compatible Data Plane：Responses、Chat Completions、Embeddings、Models 与 SSE。
2. 显式的 `llmtier_recovery_extension_v1`，覆盖 idempotency、lost response、Invocation/Response 查询和 M2-C 有限保证窗口。
3. 面向 Slinky 的只读、Client-scoped Capacity/Observation，用于投影 Tier Service Seat。
4. LLMTier Management API 与最小可用 Admin Web UI，管理 Provider/Account/Deployment、Registry/Pool、Client/Source/Entitlement、Probe、Capacity/Usage/Audit/Recovery。
5. 单一 authoritative Service Level Registry 驱动 Models、Observation、admission 和 Compatibility Manifest。

V0.3 不授予 Slinky Provider credential 或推理 authority，不让 Piko 理解 physical provider/account/pool/capacity group，不让 LLMTier 获得 Agent/Plan/IR authority，也不保留旧 embedded Tier、Role routing、Agent backend、Provider-direct 或跨 Service Level fallback 路径。

## 2. 责任与 authority

| 参与方 | 权威职责 | 明确不负责 |
| --- | --- | --- |
| Slinky | Project、Plan、IR、Forecast/Risk/Action；读取 Observation 并投影 Seat | Provider routing、credential、最终 admission、直接执行 IR-backed inference |
| Piko | Agent Runtime；以 assigned exact `service_level_id` 调用 LLMTier；SDK/recovery adapter | Capacity Group、Provider/account/pool、模型服务内部路由 |
| LLMTier | 模型服务、admission/routing、Invocation/idempotency ledger、Registry、Management、Client-scoped Observation | Agent/Plan/IR composition、Knowledge/Artifact/Acceptance authority |

唯一 IR-backed inference 路径是：

```text
Runtime -> Piko -> LLMTier -> Provider/Local Deployment
```

任何 Role selector、Provider-direct 调用或跨 Service Level fallback 都是拒绝项，而不是兼容分支。

## 3. 系统分面

```text
Admin -> /tier/admin/v1 + Admin Web UI
          -> inventory / secret-write / probe / registry publish / entitlement
          -> authoritative Service Level Registry
             |-> /v1/models
             |-> /tier/v1/service-levels
             |-> admission + capacity membership
             `-> compatibility manifest

Piko -> /v1 Responses | Chat | Embeddings | Models | SSE
          -> auth + canonical Client/Source
          -> validation + idempotency/Invocation ledger
          -> exact Service Level admission
          -> backend routing
          -> canonical result + usage/recovery

Slinky -> /tier/v1 readiness | service-levels | capacity | invocation | usage | compatibility
          -> version/ETag/valid_until validation
          -> all-constraints committed Seat projection
```

三个 API 分面共享 Registry/ledger 的事实，但权限和 DTO 分离；不得复制出第二套状态机或 Registry。

## 4. Service Level Registry

LLMTier 是 catalog authority。`service_level_id` 使用 exact、大小写敏感名称，例如 `Worker`、`Junior`。禁止 Piko/Slinky/LLMTier 将它们转换为 `worker/junior`，禁止 alias、Role selector 和跨等级 fallback。

同一个 Registry 必须驱动 Data Plane Models、Observation service levels、admission、capacity membership 和 Compatibility Manifest。Provider/account/pool mapping 与同等级 Backend override 属于 LLMTier；Contract/SLO 不变时可替换 physical mapping而不改 ID，破坏兼容性的变化必须创建新 ID 或新 API major。

Registry 发布必须包含 catalog version、强 ETag、`effective_at` 和 `valid_until`，并通过 exact ID 唯一性、capacity membership 和多分面一致性 Contract Test。

## 5. Piko Data Plane

### 5.1 唯一 V0.3 surface

| Surface | V0.3 scope | Stock SDK / adapter 边界 |
| --- | --- | --- |
| `POST /v1/responses` | non-stream + SSE | 标准首次成功/错误/SSE 由 pinned capture 验证；active `202`/recovery 由 Piko adapter 处理 |
| `POST /v1/chat/completions` | non-stream + SSE | 保持 Chat 标准 body/event；不是 Responses fallback |
| `POST /v1/embeddings` | 标准 request/response | completed replay 返回原标准 body；recovery 编排仍需 adapter |
| `GET /v1/models[/...]` | exact Service Level catalog | 目标是 stock models API，来源必须是同一 Registry |
| `GET /v1/invocations/{id}` | recovery extension | 必须显式 adapter 调用 |
| `GET /v1/responses/{id}` | Responses recovery read | body 为 canonical Response；恢复策略由 adapter 编排 |

这里不存在 Responses-only 降级面。尚无 Piko capture 的能力保持 candidate、阻止整体 production activation，但不能从 V0.3 scope 静默删除或改走另一 endpoint。

“stock SDK”仅描述标准 endpoint 形状。Piko 仍需配置 Source/idempotency headers；只替换 `base_url/api_key` 不会自动处理 `202`、Invocation 查询、lost response 或 `UnknownOutcome`。

### 5.2 首次、重复与 terminal

调用 Backend 前必须持久化 idempotency record、Invocation 和 dispatch intent。

| 情形 | POST 返回 | dispatch |
| --- | --- | --- |
| 首次成功 | endpoint 标准 `200` body；SSE 为 `200 text/event-stream` | 一次 |
| active replay | `202 InvocationAccepted` + `Location` + Invocation header + `Retry-After` | 零次 |
| completed replay | 原 endpoint 标准成功 body | 零次 |
| Failed/Cancelled/UnknownOutcome replay | typed non-2xx OpenAI-compatible Error envelope | 零次 |

POST 的 HTTP 200 只返回该 endpoint 的标准成功 body，绝不返回 `InvocationView`。terminal 详情通过 `GET /v1/invocations/{id}` 查询；证据不足进入 `UnknownOutcome`，不得盲目重派。

Invocation 已建立后，active `202` 和 terminal non-2xx 都必须返回 `Location: /v1/invocations/{id}` 与 `X-Tier-Invocation-ID`；active `202` 另带 `Retry-After`。Invocation GET 使用 `recovery_ready` 和 `recovery_disposition=wait|retrieve_response|replay_same_request|raise_terminal_error|manual_reconcile` 提供 lost-response readiness，不要求 adapter 从 HTTP 200 猜状态。

### 5.3 M2-C retention

V0.3 单一方向冻结为 C：

- `W=168h`，从 Invocation terminal 起提供连续去重保证；`M=24h`，其中 clock skew 最多 5 分钟，其余为恢复安全余量。
- 必须满足 `max_client_retry_deadline <= W-M = 144h`；Slinky 产品值 `D=24h` 满足该式。不能满足时必须在实现前提出一个唯一替代值，不得运行时降级。
- active idempotency record 保留到 Invocation terminal。
- terminal 后 content-free digest/tombstone 去重保证至少 7 天。
- Invocation terminal view 与 canonical Response 从 terminal 起至少保留 7 天。
- Prompt/output privacy retention 可独立配置，但 digest/tombstone 不得提前消失。
- 完全删除后不保证识别历史 key，不宣称无限期 exactly-once。

## 6. Slinky Capacity/Observation

唯一容量单位是 `concurrent_invocation`。投影必须同时满足 direct committed capacity、全部 shared/overlapping Capacity Group、Client quota、readiness/blocking reason 和 `valid_until`。burst 不进入 committed Seat；`request_quota_remaining=null` 阻断新增 Seat。

Snapshot 失效的精确定义：

1. 关联 `TierServiceSeat` / `IRBackingSeat` 立即 `Invalidated`，不得用于新 dispatch；
2. IR Management 通知 Plan 更新 Forecast/Risk/Action；
3. 已被 LLMTier admission 的 in-flight Invocation 不由 Slinky 撤销，也不跨 Stage rollback；
4. 当前 Attempt 只在该已 admission Invocation 的安全边界内收敛；
5. 后续 Work 必须重新投影和 admission，不能继续使用失效 Seat。

Semantic validator 必须在生产路径检查 ID 唯一、exact-case Registry membership、双向 capacity membership、`available <= committed`、时间顺序、quota unknown 和 blocking reason。Schema 不能替代运行时语义检查。

## 7. Management API 与 Admin Web UI

V0.3 必须交付 `/tier/admin/v1` Management API 和最小 Admin Web UI，覆盖：

- Provider、Account、Local Deployment 与 credential write/rotate；
- Model discovery、Probe/readiness；
- Service Level Registry、Pool、同等级 Backend override 和发布；
- Client、Source、Entitlement、committed/burst/quota policy；
- Capacity、Usage、Audit、Invocation/Recovery 管理。

Secret 只写不读；API/UI/日志只显示配置状态、版本/轮换时间和健康证据。所有 mutation 鉴权、授权、审计并带并发版本检查。UI 至少支持 list/detail/edit/disable/rotate/probe/publish/recovery、明确确认、typed result、状态和 audit 展示。

Management 不得创建 Provider-direct Data Plane、Role selector、跨等级 fallback 或第二 Registry。详细 required scope 见 `docs/contracts/llmtier-management-contract-v0.3.md`。

## 8. Schema、安全与状态

- 独立 LLMTier 配置是唯一运行时覆盖入口，不回读 Slinky 配置。
- credential binding 得到 `client_id`；canonical `source_id` 进入授权、idempotency namespace 和 recovery scope。
- Provider credential、physical routing 和内部 error evidence不进入 Piko/Slinky DTO。
- Metadata 最多 16 对，key/value 权威限制为 64/512 UTF-8 encoded bytes，不得静默截断。
- Observation 与 Data Plane recovery 投影自同一 Invocation ledger。
- Prompt/output/usage retention 与 privacy policy 显式配置，但受 M2-C digest/tombstone 下限约束。
- V0.3 唯一机器权威是 `docs/contracts/openapi/llmtier-v0.3.openapi.json`；历史 standalone Schema 不由当前 Manifest 装载。

## 9. Activation gates

V0.3 只有以下条件全部满足才可从 candidate 激活：

1. production implementation commit 与正负 Contract Test；
2. Management API/UI 正负、权限、并发冲突和 secret non-disclosure 测试；
3. 同一 Registry 驱动 Models、Observation、admission 和 manifest 的一致性测试；
4. multi-client/source isolation、entitlement 与公平性证据；
5. Capacity semantic validator 生产接线证据；
6. Piko pinned SDK/adapter 对首次 200、active 202、terminal error、lost response、UnknownOutcome、Responses/Chat/Embeddings/Models/SSE 的真实 capture；
7. M2-C 24h/7d retention 与 privacy policy 配置/执行证据；
8. 旧 embedded Tier、Role routing、Agent backend、Provider-direct path 删除扫描；
9. 文档、Schema、fixtures、manifest 与真实 route 行为一致。

当前本地测试只证明 candidate artifacts 自洽，不证明 production route、ledger、SDK、Registry、UI 或 admission 已实现。

## 10. 实现顺序

1. 冻结 Piko SDK/adapter、Source identity、Service Level catalog 与 M2-C 数值。
2. 建立 authoritative Registry、durable Invocation/idempotency ledger 与 canonical result store。
3. 实现统一 Data Plane surface 和 recovery extension，补 crash/lost-response tests。
4. 实现 Management API/UI、secret-write、inventory/probe/registry publish。
5. 实现 Observation/capacity snapshot 与 production semantic validation。
6. 完成三方 conformance、删除旧/直连路径，再激活 manifest。

## 11. 本轮评审闭环

已吸收 Slinky `S-20260906-59891d73fa13`：authority/Seat 方向接受；invalidation 精确定义；M2-C 24h/7d；LLMTier Registry authority 和 exact-case ID；Management API/UI 恢复为 V0.3 required；统一 Responses+Chat+Embeddings+Models+SSE；terminal replay 改为 non-2xx Error；补齐 activation gates。

已吸收 Piko `P-20260906-b8a2e107f0b8`：固定 Pi/SDK/OpenAI dependency、provider/adapter 名称、canonical Client/Source、Responses namespace/digest、内建 adapter 五类 capture、202/non-2xx header 和 recovery readiness；LLMTier 冻结 `W=168h`、`M=24h`、Invocation/Response terminal retention 168h。

已吸收 Slinky Amendment 2 `S-20260906-7f86cf4103bd`：全链统一 Management path 与 canonical headers；用唯一 OpenAPI 3.1 authority 覆盖 Data Plane/SSE/Recovery/Observation/Management；create/retrieve 复用 canonical Response；policy selection 与 runtime activation 分离；移除 V0.3 Manifest 对两份 Data Plane Schema authority 的并列装载。

未决 scope：Piko 请求 V0.3 仅 non-stream Responses 并把 Streaming/Chat 延至 V0.4；Slinky Amendment 1 要求 V0.3 保持 Responses+Chat+Embeddings+Models+SSE。当前保留统一 candidate surface 且 activation=false，等待 Slinky/用户明确裁决，不创建第二路径。

## 12. 关联材料

- `docs/contracts/piko-data-plane-contract-v0.3.md`
- `docs/contracts/slinky-capacity-observation-contract-v0.3.md`
- `docs/contracts/llmtier-management-contract-v0.3.md`
- `docs/contracts/compatibility-manifest-v0.3.json`
- `docs/contracts/openapi/llmtier-v0.3.openapi.json`
- `docs/contracts/fixtures/v0.3/data-plane-openapi-fixtures.json`
- `docs/contracts/fixtures/v0.3/sse-event-sequences.json`
- `docs/qa/llm-tier-contract-qa-v0.3.md`
