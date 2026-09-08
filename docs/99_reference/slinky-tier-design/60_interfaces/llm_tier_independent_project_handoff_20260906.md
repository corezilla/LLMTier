# LLMTier 独立项目需求与设计交接

Version: v0.1
Last Updated: 2026-09-06 12:53:56
Status: 交接输入；供 LLMTier 重写独立项目设计，不代表实现验收或契约冻结
Owner: Slinky representative

## 1. 本次任务

用户已新建 LLMTier 独立项目。请 LLMTier representative 以本文、明确共享的旧设计和三方问答作为输入，在自己的项目目录重新编写独立服务设计。旧代码用于了解已有能力和耦合，不要求照搬旧架构、目录、API 或运行环境。本轮是设计交接，不执行代码搬迁、删除、部署或原子切换。

新的协作协议：/Users/ben/work/slinky-piko-qa/HANDOFF.md。
邮箱 identity 固定为 `llm-tier`；产品名使用 LLMTier / LLM Tier。
LLMTier 新项目目录由其代表在 ACK 中报告，不在此猜测路径。

## 2. 三方职责与 IR

```text
IR = Piko Agent Runtime Slot
   + LLMTier Tier Service Seat
   + Knowledge Capability Profile

Slinky Runtime -> Piko Agent Runtime -> LLMTier OpenAI-compatible Data Plane -> 模型 Backend
Slinky IR Management -> LLMTier scoped catalog/capacity/readiness -> Tier Service Seat
Slinky IR Management -> Piko Slot snapshot -> Agent Runtime Slot
Slinky Knowledge -> exact Knowledge Capability Profile / Execution Package
```

| 一方 | 拥有的职责 | 不拥有的职责 |
| --- | --- | --- |
| Slinky | Project/Plan/Work/Attempt、IR composition/allocation、Knowledge、Workspace Lease 协调、Review/Validation/Acceptance、Artifact effective version | Provider credential、physical routing、Pi Session |
| Piko | AgentRun/ParticipantRun、Agent Slot、Pi SDK Agent Loop、授权 Tool Loop、structured Result 与执行恢复 | Tier capacity/Provider 管理、Plan、IR 组合、Knowledge 选择、最终验收 |
| LLMTier | Logical Service Level、模型 Backend、认证授权、模型调用 admission/routing、capacity/quota、Invocation/usage/outcome、服务配置和运营 | Agent Loop、Piko Slot、Slinky Role/IR/Project/Stage/Task/Acceptance |

Piko 直接调用 LLMTier。对 Piko，模型服务由 `base_url + credential_binding_ref + model=exact service_level_id` 表达；Tier Seat 等外部关联 identity 保留用于审计，不要求 Piko 理解 Tier 内部资源管理。

Piko 不调用 Tier Management/Observation API；没有授权且可验证的 Data Plane outcome query 时，丢失响应必须保留 UnknownOutcome，不能盲目重派。Slinky 可通过自己的受限 Adapter 读取 Tier capacity/readiness/usage，不建立 IR-backed Work 的 direct inference fallback。Knowledge embedding 等非 Agent 使用场景如需调用模型，须在新设计中单独明确调用方和 scope，不能混成 Agent 执行旁路。

## 3. 现有代码在哪里

当前核对的 Slinky checkout：`/Users/ben/slinky`。
核对时 HEAD：`299bff1ea4f9ce63054c64b889524fb048d9fec2`。
`src/llm_tier`、`tier.sh`、`dashboard/tier.html` 在 scoped tracked status 中无变更；整个工作区另有大量未提交/未跟踪内容，不能把整个工作区视为该 commit 的不可变快照。

| 路径（绝对路径） | 参考用途 |
| --- | --- |
| /Users/ben/slinky/src/llm_tier/ | 旧 Python Tier 实现主体 |
| /Users/ben/slinky/src/llm_tier/__main__.py | 服务进程入口，创建 TierServer |
| /Users/ben/slinky/src/llm_tier/server.py | HTTP Service、job/runtime、运营接口 |
| /Users/ben/slinky/src/llm_tier/client.py | 旧 TierClient、HTTP 调用与轮询 |
| /Users/ben/slinky/src/llm_tier/tier_core.py | Client facade；不是新独立项目内部引擎规范 |
| /Users/ben/slinky/src/llm_tier/router_core.py | 旧 Router |
| /Users/ben/slinky/src/llm_tier/tier_config.py | 旧配置读取/模型配置机制 |
| /Users/ben/slinky/src/llm_tier/tier_model.py | 旧请求与结果类型 |
| /Users/ben/slinky/src/llm_tier/execution_identity.py | 旧 Role/execution identity 映射 |
| /Users/ben/slinky/src/llm_tier/quota_manager.py | 旧 quota 管理 |
| /Users/ben/slinky/src/llm_tier/concurrency.py | 并发控制 |
| /Users/ben/slinky/src/llm_tier/provider_usage.py | Provider usage 采集 |
| /Users/ben/slinky/src/llm_tier/stats_collector.py | 调用统计 |
| /Users/ben/slinky/src/llm_tier/redaction.py | 敏感内容脱敏 |
| /Users/ben/slinky/src/llm_tier/backends/ | API/CLI/Agent adapters；存在 mlexp、opencode、codex 等历史实现 |
| /Users/ben/slinky/src/stats/llm_stats.py | 旧统计依赖，需识别独立拆分边界 |
| /Users/ben/slinky/dashboard/tier.html | 旧 Tier 管理展示，历史上依赖 Slinky Dashboard |
| /Users/ben/slinky/tier.sh | 旧运维脚本位置，仅供定位，不是新项目启动命令 |

旧 client 还引用 Slinky `utils.response_parser`；独立项目不能通过把 Slinky src 加入 PYTHONPATH 解决耦合。上述仅是已核对的入口地图，不声称依赖审计完整。

代码路径是现状定位，不授权修改 Slinky、复制 Secret/配置/运行状态或共享测试环境。若协议边界下需要进一步源码材料，通过 NEEDS_INFO 请求 Slinky 提供受控摘要或明确迁移方案；不得挂载整个项目。本文与列出的设计文档按用户授权可通过绝对路径只读共享。

## 4. 旧设计阅读顺序

### 4.1 现有实现设计（历史语义）

优先阅读：

- /Users/ben/slinky/spec/30_subsystem_design/tier_subsystem.md
  - 当前 Version v1.16，Last Updated 2026-09-04 08:12:20。
  - 描述旧 role_name → source Tier → account/backend/model、HTTP Job、quota/concurrency、usage/stats 和 MLEXP bridge。
- /Users/ben/slinky/spec/40_module_design/tier/tier_server_module.md
- /Users/ben/slinky/spec/40_module_design/tier/tier_client_module.md
- /Users/ben/slinky/spec/40_module_design/tier/tier_cli_module.md
- /Users/ben/slinky/spec/40_module_design/webui/tier_dashboard_module.md
- /Users/ben/slinky/spec/20_system_mechanisms/execution_identity_and_tier_policy.md

更早历史资料：

- /Users/ben/slinky/spec/30_subsystem_design/legacy_root_migration/62_llm_tier_subsystem.md
- /Users/ben/slinky/spec/30_subsystem_design/legacy_root_migration/65_tier_dashboard_design.md

详细 ISD 目录：/Users/ben/slinky/spec/50_isd_design/tier/。
旧运行说明：/Users/ben/slinky/notes/tier_mlexp_user_guide.md。
旧测试入口目录：/Users/ben/slinky/test/unit/tier/、/Users/ben/slinky/test/module/tier/、/Users/ben/slinky/test/subsystem/tier/。
测试仅为现状位置，本次未运行；不把其数量或历史报告当作新服务 conformance Evidence。

### 4.2 已有 v0.3 目标设计（重写的重要输入，仍是 Draft）

- /Users/ben/slinky-v0.3-design/V0.3/v0_3_tier_llm_service_dependency_and_interface_draft_20260905.md
  - Version v0.20，Last Updated 2026-09-06 02:37:00。
  - §2–3 独立服务/Authority，§6–7 拓扑/API 分面，§9 OpenAI-compatible Data Plane，§11 capacity/entitlement，§12 Observation，§13 Management，§14 errors。
- /Users/ben/slinky-v0.3-design/V0.3/v0_3_piko_agent_runtime_service_requirements_and_interface_contract_draft_20260906.md
  - Version v0.2；§4 composite IR、§11 tier_binding、§15 Tier integration、§18 recovery、§21 Contract Test。
- /Users/ben/slinky-v0.3-design/V0.3/v0_3_intelligent_resource_management_draft_20260801.md
- /Users/ben/slinky-v0.3-design/V0.3/v0_3_knowledge_memory_skill_upgrade_draft_20260801.md
- /Users/ben/slinky-v0.3-design/V0.3/v0_3_architecture_upgrade_draft_20260801.md

所有旧设计是参考而非无条件继承。用户最新三方边界优先，冲突写入 QA 与 Interface Change Proposal，不通过兼容分支掩盖。

## 5. 新设计必须回答的两类 Client 契约

### 5.1 Slinky 侧：可计划的模型能力与容量

- exact Logical Service Level catalog、capability/compatibility、version、valid_until、readiness。
- Client/Source 隔离的 committed capacity、capacity group 共享关系、burst 与 queue 边界。
- Slinky 如何从权威 capacity 投影 Tier Service Seat，防止跨等级共享 Backend 被重复计算容量。
- capacity snapshot 不替代最终 admission；Slot capacity 不能由 Tier capacity 推导。
- service restart、capacity invalidation、usage 查询和错误如何形成 Slinky dependency/resource gap。
- 管理 API/Admin UI 属 LLMTier，普通 Slinky Project View 不复制 Provider/Account/Pool authority。

### 5.2 Piko 侧：标准云模型调用

- 与 pinned Pi SDK 匹配的 OpenAI-compatible surface；Responses/Chat Completions 若均提供，必须共用同一 admission/routing/Invocation/usage 机制，Piko 不失败后切 endpoint。
- Exact model ID、大小写、Client scope、unsupported/unknown parameter、context/output 限制。
- Function Tool schema、tool call/result ID、stream delta、并行 Tool 调用和 structured output 的确切支持。
- LLMTier 返回模型 Tool call，但不执行 Piko 的 file/process/browser Tool Loop。
- credential binding、认证 headers、request/invocation ID、usage 来源、unknown usage 不填零。
- 429/Retry-After、5xx、deadline、cancel、disconnect、lost acknowledgement、idempotency 与内部 retry budget。
- lost-response recovery 必须有确定可验证的语义；未确认 outcome 不记成功，不自动重复计费/执行。

## 6. 已知冲突和待问答事项

1. 旧 v0.3 Tier §9.7 要求断流后查询 Observation API；最新 Piko 边界禁止其调用 Observation。请 LLMTier/Piko 联合提出 Data Plane 可行行为；如果没有 outcome query，明确 UnknownOutcome 与人工/受控 reconciliation 责任，不能偷加 Observation 调用。
2. 旧 Tier Role routing、Upshift、Agent backend/MLEXP 与新 Piko Agent authority 不一致。新设计应给“保留通用能力 / 去除旧责任 / 待决定”对照表，不能把旧 Agent runner 再包装成新 Piko 旁路。
3. 旧 Tier model catalog 使用 exact Tier name，例如大写 Junior；Piko 早期需求中小写名称是示例。以版本化 catalog 的 exact service_level_id 为准，不擅自做大小写 alias 或第二套命名。
4. Piko 的 D1–D5 仍为候选，不因本文冻结。有关 Schema、错误码、Result、participant、SSE 的 review 已通过 S-20260906-001 线程传递。
5. 新独立项目的语言栈、存储、部署、容量、SLO 测试负载和迁移 cutover 方案需 LLMTier 提案；不把 Piko 的 TypeScript 决策自动套用到 LLMTier，也不预设必须重写全部旧 Python。
6. 新三方 HANDOFF §4 首个示例 to/cc 重复，但紧接的规则明确禁止重复；本轮按规则和 §6 正确示例发送，to 与 cc 保持不重叠。

## 7. Piko 当前参考与协作入口

当前已收到的中文提案：
- /Users/ben/work/piko/docs/design/agent-runtime-service-design-v0.2.md
- /Users/ben/work/piko/docs/qa/agent-runtime-contract-qa-v0.2.md

仅作为明确共享的设计文档只读参考；后续以 Piko 新消息公布的版本为准。

相关已发送消息（可只读）：
- /Users/ben/work/slinky-piko-qa/piko/outbox/S-20260906-001__009__AMENDMENT__chinese-docs-and-openai-cloud-model-boundary.md
- /Users/ben/work/slinky-piko-qa/slinky/outbox/S-20260906-001__010__ANSWER__v0-2-review-baseline-and-cloud-surface.md

这些是历史二方格式，不能据此推断新三方 reply_required_from。新的行动责任由本次三方 REQUEST 明确指定。

## 8. 请 LLMTier 交付的新设计包

1. 中文独立服务 System/Subsystem/Module 设计，含 Authority、调用拓扑、内部职责、独立配置/状态/发布边界。
2. Slinky Observation/capacity Contract 与 Piko Data Plane Contract；OpenAPI/JSON Schema/compatibility manifest 可从提案起步。
3. 旧实现能力和耦合审计表，明确保留、替换、删除或待决定，不现在修改旧代码。
4. client/source auth、quota/capacity、Invocation lifecycle、usage/audit、retry/unknown outcome 和恢复设计。
5. 与 Piko 配对的正反 fixture 计划，以及 capacity、shared pool、隔离、故障恢复、stream/tool call 测试矩阵。
6. LLMTier 单方维护的 versioned QA，按“设计资料已回答 / 需对方材料 / 需用户决定”分类。
7. 实施、独立交付和最终 cutover 计划；迁移不允许共享 config/state 或保留永久平行旧新路径。

文档正文中文，技术标识保留英文；每次版本更新带 Last Updated 到秒。通过新消息传绝对路径、版本、digest 和变更摘要。已发布版本保留，不覆盖历史引用。

## 9. 三方推进与验收

LLMTier 先 ACK 并报告新项目根目录、输入可读性和设计计划；Piko 提交实际需要的模型 surface/fixture 清单。两方独立回复后，由 Slinky 汇总下一步。

LLMTier 与 Piko 可直接互发新的有明确 reply_required_from 的问题，涉及整体 IR/Authority 的变化同时通知 Slinky。各方只写本方 outbox/state，cc 方不回复。没有新消息或用户决定时保持安静。

本轮“设计可 review”与“服务可接入”分开：只有后续交付实现、真实 Contract Test/恢复/隔离证据并冻结 release digest，才讨论服务验收；本次不声称新 LLMTier 已运行或已兼容 Pi。
