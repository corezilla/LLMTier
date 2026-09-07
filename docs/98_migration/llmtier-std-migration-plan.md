# LLMTier STD draft.17 分阶段迁移计划

计划状态：ACTIVE
计划日期：2026-09-07
项目根：/Users/ben/work/LLMTier
项目输入 HEAD：8dc6a54c92608ab6373f40c78cc954da7086f30e
本轮输入 dirty snapshot digest：dfe350dded17c0173f61acb52cba065c1ed307ccf23e7d68710f1861f9c3616c
STD revision：94c0262de35b5b989bba9f8d23f212af709c9dbf
STD tag：std-v0.1.0-draft.17

## 1. 采用范围与不变边界

- project_profile=software；enabled_domains=[management, software]。
- LLMTier 采用单应用/单服务根结构，继续使用 src/、tests/、tools/、docs/；不建立
  services/llmtier/、software/llmtier/、apps/ 或 packages/ 平行 ownership。
- LLMTier 只拥有本服务设计、实现与接口提供方事实。Slinky 的 Project/Plan/IR 和 Piko 的 Agent
  Runtime/adapter authority 不迁入本项目。
- docs/contracts/openapi/llmtier-v0.3.openapi.json 保持字段级机器契约 authority；
  docs/contracts/compatibility-manifest-v0.3.json 保持 capability/runtime-activation candidate
  authority；tests/ 与 fixtures 保持可执行源码和 oracle authority。
- 迁移只生成可审阅候选，不 reset/clean，不覆盖其他任务修改，不改变业务 ID、错误、状态、恢复、
  capacity、quota、安全或无 fallback 语义。
- 每个 cohort 的 Review Verdict、Document Status、canonical promotion、RAG publication 与 Runtime
  Activation 分别过 Gate；前者不推导后者。

## 2. Cohort 总览与顺序

| Cohort | 状态 | 交付范围 | 启动依赖 | 首要 Owner Gate |
|---|---|---|---|---|
| C0 Foundation | immutable candidate / Owner ACCEPTED | inventory、tailoring、lock/source manifest、单服务 design、review packet | draft.17 immutable STD | consumer-independent final decision update |
| C1 Interface + Contract | immutable candidate / Owner ACCEPTED | 三个 v0.3 interface candidate、一个 contract specification、mapping、review packet | C0 结构通过 | Piko/Slinky consumer reviews；终局 decision update |
| C2 Assurance | READY_FOR_COMMIT | V&V plan、contract test specification、evidence boundary、review packet | immutable C1 mapping；Owner ACCEPTED | STD pre-commit Gate；runtime evidence 如实 NOT_RUN/BLOCKED |
| C3 Requirements + Traceability | ENABLED / PLANNED | 独立 requirements specification 与 traceability matrix | Owner 已决定启用；C2 traceability mapping 稳定 | LLMTier owner；不得复制 Slinky/Piko requirements authority |
| C4 Decisions + Operations | DEFERRED | persistence/HA/RPO/RTO ADR、deployment/release/operations 文档 | 对应设计决定与实现证据存在 | LLMTier architecture/operations owner |
| C5 Canonical Promotion | BLOCKED | scope-level authority 切换、索引与旧文档状态 | 各 cohort ACCEPTED、文档批准、immutable project commit | LLMTier canonical authority |
| C6 Publication / Runtime | BLOCKED | 项目 RAG manifest/索引；独立 runtime activation packet | C5 publication commit；production L3 evidence | publication owner；独立 runtime authority |

C0/C1 已由 commit `aa2638283e77bc658e98df8d40396306cad17aa2` 固定；LLMTier Owner 对两者
ACCEPTED，Piko/Slinky consumer-boundary review 与终局 decision 更新仍独立。C2 assurance 候选与三层
证据已完成，当前等待 STD pre-commit Gate。Owner 已决定 C3 启用独立 requirements/traceability 实例；C4 仍只在
已有决定和事实可映射时生成，不预建虚假的 architecture/operations 结论。

## 3. C0 Foundation：已完成候选

| 来源 | 目标 / Template ID | residual authority |
|---|---|---|
| 项目现状、旧候选和文档集合 | docs/98_migration/current-document-inventory.md | 原路径在 promotion 前保持各自现有状态 |
| 项目采用决定 | docs/00_management/std-tailoring.md / management.tailoring | 旧 tailoring deletion 是输入 dirty state，不视为 promotion |
| docs/design/llmtier-v0.3-design-review.md 的服务设计 scope | docs/30_subsystem_design/llmtier-service-design.md / design.definition | 旧设计继续负责 review 结论、跨项目输入与未迁出 scope |
| STD draft.17 | docs/std.lock.json + docs/std-source-manifest.json | STD 只管理模板与规则，不取得项目业务 authority |
| C0 变更和验证 | docs/91_reviews/llmtier-std-draft16-migration-review.md / review.packet | decision 保持 PENDING |

完成标准：source verifier 71 artifacts、project-root validator 0 issue、项目 41 tests PASS；L3
NOT_RUN 已显式记录。C0 仍等待 immutable project candidate commit 与授权 reviewer，不能 promotion。

## 4. C1 Interface + Contract：首个活动 cohort

### 4.1 源→目标和模板映射

| Source authority / evidence | 新候选 | Template ID | 迁移规则 |
|---|---|---|---|
| docs/contracts/piko-data-plane-contract-v0.3.md | docs/60_interfaces/piko-data-plane-control.md | interfaces.control | 保留 Responses/Embeddings、exact-case ID、idempotency/recovery、M2-C、deferred surface；不复制 Piko runtime authority |
| docs/contracts/slinky-capacity-observation-contract-v0.3.md | docs/60_interfaces/slinky-capacity-observation-control.md | interfaces.control | 保留 read-only observation、capacity/Seat、ETag/invalidation、Client scope；不复制 Slinky Project/Plan/IR authority |
| docs/contracts/llmtier-management-contract-v0.3.md | docs/60_interfaces/llmtier-management-control.md | interfaces.control | 保留 /tier/admin/v1、Admin UI、secret non-disclosure、audit/concurrency Gate |
| OpenAPI v0.3、compatibility manifest v0.3、v0.3 fixtures、三份说明 | docs/60_interfaces/contracts/llmtier-v0.3-contract-specification.md | contracts.specification | 只建立 schema/error/evolution/authority 索引；机器文件原位且仍为字段级 authority |
| 上述 C1 diff、mapping 与验证 | docs/91_reviews/llmtier-std-c1-interface-contract-review.md | review.packet | PENDING decision；不请求状态升级或 activation |

旧三份 v0.3 prose contract 在 C1 review 和 C5 promotion 前继续承担其现有说明 authority；新候选
Supersedes=none。v0.1/v0.2 继续作为 historical/provenance，不在本 cohort 移动或删除。

### 4.2 依赖、验证与完成标准

- 依赖：C0 draft.17 source lock/manifest；当前均已通过，无安全启动 blocker。
- L1：source verifier；project-root validator；cover/sidecar/conformance/path/link/ID 检查。
- L2：现有 41 项 unittest/contract semantics；新增旧→新关键语义一致性断言；OpenAPI、manifest、
  fixtures 的 JSON/schema/semantic tests。
- L3：production Data Plane/Observation/Management、真实 provider、persistence、lost-response、
  multi-client isolation 与 UI evidence。本 cohort 预计为 NOT_RUN/BLOCKED，不伪装成 PASS。
- 完成标准：四份 candidate 无字段级 contract 复制冲突；所有冻结 ID/error/status/header/path 保持；
  Piko、Slinky、LLMTier authority 分明；C1 packet 固定 changed files、hash、三层结果和 blockers。
- Owner Gate：LLMTier owner 审整体；Piko reviewer 只审 Piko consumer boundary；Slinky reviewer 只审
  Observation consumer boundary。任何跨项目 amendment 单独处理，不藏进格式迁移。

首个可审阅 milestone：C1 四份 candidate + sidecar、migration map 增量、PENDING review packet，L1/L2
完成，L3 如实标注。

## 5. C2 Assurance

| Source | 新候选 | Template ID | residual authority |
|---|---|---|---|
| docs/qa/llm-tier-contract-qa-v0.3.md 的 strategy/gates | docs/70_verification/llmtier-v0.3-vv-plan.md | assurance.vv-plan | 旧 QA 在 promotion 前继续为 review/traceability evidence |
| v0.3 fixtures、tests/test_*v03.py、OpenAPI/manifest oracle | docs/70_verification/llmtier-v0.3-contract-test-specification.md | assurance.test-specification | executable tests/fixtures 保持 source authority，Markdown 不复制 oracle |
| C2 diff 与 execution evidence | docs/91_reviews/llmtier-std-c2-assurance-review.md | review.packet | actual run 与 NOT_RUN/BLOCKED 分开记录 |

依赖 C1 冻结 interface/contract mapping。目标路径为
`docs/70_verification/plans/llmtier-v0.3-vv-plan.md` 和
`docs/70_verification/specifications/llmtier-v0.3-contract-test-specification.md`。完成标准是
Requirement/Review→Design/Contract→suite/case→execution evidence 可追踪，静态 PASS 不被写成
production evidence。L3 缺口继续阻塞 Runtime Activation，但不阻止形成诚实的 Migration Review candidate。

## 6. C3 Requirements + Traceability（条件 cohort）

候选映射为 docs/10_requirements/llmtier-v0.3-requirements.md / requirements.specification 和
docs/10_requirements/llmtier-v0.3-traceability.md / requirements.traceability。来源仅限 LLMTier
service requirements、既有 Review ID、C1/C2 contract/test mapping；Slinky/Piko 拥有的需求只作为
外部输入引用。

Owner Gate 已决定启用独立实例，因为 V0.3 自有 service requirements、external consumer inputs、contract
cases 和 activation evidence 需要稳定的双向追踪。C3 启动时先更新 tailoring，再生成非空候选；不得把
Slinky/Piko 拥有的需求复制成本项目 authority。

## 7. C4 Decisions + Operations（依赖驱动）

- persistence、HA、backup、RPO/RTO、deployment topology 等新决定使用 decisions.adr，不能从旧草案
  倒推已批准选择。
- deployment、release、rollback、recovery、retirement 在实现和证据存在后映射
  operations.release，必要时再启用 installation/operations/maintenance 模板。
- Provider measured SLO、Admin UI 技术栈和 production isolation 未决定前只保留 Open Gate，不生成
  假完成文档。

## 8. C5/C6 后置 Gate

C5 只有在对应 packet 终局 ACCEPTED、独立 Document Status 批准、实际 reviewed commit 和 immutable
candidate commit 均具备后才能开始。promotion 必须在同一个可审查变更中按 scope 更新 README、索引、
authority registry、新旧文档状态和 residual map；只有旧文档全部 scope 迁出后才能整体 Supersede。

C6 只在 promotion commit 存在后生成 rag/project-ingestion-manifest.jsonl，明确新 canonical inclusion、
旧/历史/candidate exclusion 和 publication commit。Runtime Activation 需要另一份独立 authority 与
production L3 evidence；文档 review、RAG publication 或 contract tests 均不能代替。

## 9. 每 cohort 的固定证据清单

1. 输入 HEAD、tracked diff hash、untracked set hash、稳定 dirty snapshot digest；
2. source→target/template map、changed files、每个候选和 sidecar hash；
3. STD source verifier、project-root validator 的原始命令、exit code、关键输出和 JSON artifact；
4. 项目 contract/schema/test 的原始命令、exit code、关键输出和 artifact；
5. runtime/external evidence 的 PASS/FAIL/NOT_RUN/BLOCKED/N/A 与理由；
6. blockers、Owner/reviewer、requested verdict、Document Status before/after 和
   runtime_activation_requested=false；
7. 原文档 residual authority、建议的未来 promotion/supersession 范围；
8. 明确声明未 reset/clean、未 promotion、未项目 RAG ingestion、未外部发布、未 runtime activation。

## 10. 提交前 STD 复核 Gate

每个 cohort 完成候选后先发送 READY_FOR_COMMIT，提供计划、精确候选/变更文件清单、review
packet/decision、三层验证原始证据、项目 HEAD 以及 tracked/untracked dirty preservation digest。
STD 在项目根只读复核；收到明确 COMMIT_APPROVED 前不得 commit 或 push。

COMMIT_APPROVED 必须给出允许提交的精确 pathspec。若某个共享 foundation 文件在 cohort 开始前已经
dirty，应单独标为 shared dependency；不得把 README、旧候选 deletion、legacy RAG manifest、
test_contract_semantics_v03.py 或其他未批准路径夹带进提交。获批后的 commit 仍只是 immutable review
candidate，不是 canonical promotion、Document Status 升级、RAG ingestion、外部发布或 Runtime
Activation。
