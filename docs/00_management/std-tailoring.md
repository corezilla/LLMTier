<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier STD 裁剪清单

| 文档字段 | 值 |
|---|---|
| Document ID | `std-tailoring` |
| Document Version | `0.1.0-draft.6` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-07` |
| Last Modified Date | `2026-09-07` |
| STD Version | `0.1.0-draft.18` |
| Template ID | `management.tailoring` |
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/00_management/std-tailoring.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. 适用背景

- 项目：`LLMTier`
- 生命周期阶段：V0.3 design/contract candidate；production implementation 尚未激活
- 产品类型：single-service software
- Repository model：单应用、单服务或单库；根目录使用 `src/`、`tests/`、`docs/`
- 设计层级：`subsystem`，表示 LLMTier 在跨项目链路中的服务层级；不表示本仓库拥有跨项目系统
- 安全或业务关键性：模型服务控制面和数据面；涉及 credential、跨 Client 隔离、容量与恢复
- STD 来源：`0.1.0-draft.18`，锁定 commit
  `9841083c4d8d0ed1556bdc413d77b4567ac696b4` 与 annotated tag
  `std-v0.1.0-draft.18`
- 本轮范围：纠正首轮 `design.system` 误分类并迁移 V0.3 单服务设计；不改变 Scope B 或机器契约

## 2. 启用模板

| Template ID | Profile | 是否必需 | 计划文档 | Owner |
|---|---|---|---|---|
| `management.tailoring` | management | 是 | `docs/00_management/std-tailoring.md` | LLMTier |
| `design.definition` | software | 是 | `docs/30_subsystem_design/llmtier-service-design.md` | LLMTier |
| `requirements.specification` | software | 是，C3 active | `docs/10_requirements/llmtier-v0.3-requirements.md` | LLMTier；外部需求 authority 不迁入 |
| `requirements.traceability` | software | 是，C3 active | `docs/10_requirements/llmtier-v0.3-traceability.md` | LLMTier |
| `interfaces.control` | software | 是，C1 active | Data Plane、Observation、Management interface migration | LLMTier；消费边界由 Piko/Slinky reviewer 复核 |
| `contracts.specification` | software | 是，C1 active | OpenAPI/manifest/error/schema 说明层；机器文件原位保留 | LLMTier |
| `assurance.vv-plan` | software | 是，C2 candidate | V0.3 activation-gate V&V plan | LLMTier |
| `assurance.test-specification` | software | 是，C2 candidate | Contract/SDK/recovery/isolation tests | LLMTier |
| `review.packet` | management/software | 是，本批 | STD migration review packet；不请求 V0.3 activation | LLMTier owner；项目授权 reviewer 待指定 |
| `decisions.adr` | software | 条件必需 | persistence/HA/deployment 等新重大决定 | LLMTier |
| `operations.release` | operations/software | 是，C4 active | `docs/80_operations/llmtier-v0.3-release-and-operations.md`；Open Gate 不伪造 | LLMTier |

## 3. 裁剪决定

| ID | 模板/章节 | keep / simplify / omit | 理由 | 风险 | 批准人 | ADR |
|---|---|---|---|---|---|---|
| LT-TL-001 | `design.definition` 全部 14 节 | keep | 单服务的 boundary、runtime、recovery、capacity、security、implementation mapping、verification 和 gate 均适用 | 无 | 待项目 review | N/A |
| LT-TL-002 | `design.definition` deployment/physical detail | simplify | topology、DB、HA、RPO/RTO 尚未冻结，只记录逻辑部署与 Open Gate | 选型不足阻塞 retention/recovery | 待项目 review | 选型时新增 ADR |
| LT-TL-003 | `design.system` | omit | LLMTier 是单一独立服务；跨项目 system authority 不属于本仓库，不能由 LLMTier 服务设计冒充 | 外部上下文可能被误写为本仓库 ownership | 待项目 review | 若未来指定跨项目 system owner，再由该 owner 建立 |
| LT-TL-004 | `requirements.specification` + `requirements.traceability` | keep，C3 active | 独立 shall statements 与矩阵能分离 LLMTier 自有需求、外部输入、静态 evidence 和 runtime gap | 若复制外部需求会越权；由引用和 reviewer boundary 控制 | LLMTier owner 已决定启用；文档仍待 review | N/A |
| LT-TL-005 | `design.hardware`/`design.fpga` | omit | 本项目无硬件/FPGA ownership；Provider/Local Deployment 是外部资源 | 无 | 待项目 review | N/A |
| LT-TL-006 | `interfaces.control` | keep，C1 active | 三个 API 分面需保持独立 authority 与演进规则 | promotion 前旧 Markdown 仍为说明 authority | 待项目 review | N/A |
| LT-TL-007 | `contracts.specification` | keep，C1 active | OpenAPI、manifest、fixtures 保持机器可执行 authority | 不得转写出第二契约 | 待项目 review | N/A |
| LT-TL-008 | assurance templates | keep，后续迁移 | candidate 与 runtime activation 必须由证据区分 | QA 尚缺正式执行报告层 | 待项目 review | N/A |
| LT-TL-009 | `management.project-plan` | omit | 排期/资源管理不在本轮设计迁移范围，现无稳定计划基线 | 实施顺序不等于项目计划 | 待项目 review | N/A |
| LT-TL-010 | `decisions.adr` | simplify/按需 | 已有决定保留原 Matrix Review ID，不伪造 retrospective ADR | 决策分散 | 待项目 review | 新决定必须用 ADR |
| LT-TL-011 | 原设计与 v0.1/v0.2 历史材料 | keep | review 前不删除；inventory 标明 current/historical/superseded | 误检索历史语义 | 待项目 review | review 后归档建议 |
| LT-TL-012 | STD 来源清单 / 项目 RAG ingestion | keep source manifest；omit ingestion 到 canonical promotion 后 | source manifest 记录 draft.18 的 71 个规范、模板、Schema 和工具 SHA-256；不把 review candidate 写入项目 RAG | 来源可校验，候选暂不可由项目 RAG 检索 | 待项目 review | N/A |
| LT-TL-013 | 多服务目录 `apps/`、`services/`、`packages/` | omit | 当前只有一个部署边界、一个服务 owner，根目录 `src/tests/docs` 已满足 STD | 过早分层会制造虚假 subsystem 与平行路径 | 用户已确认单服务 | ownership/deploy boundary 改变时重新 tailoring |
| LT-TL-014 | `operations.release` | keep，C4 active | 当前 package/CLI 与 release/rollback/recovery Gate 需要集中，但 production procedure/evidence 尚不存在 | 文档被误作 production runbook；以 Draft/Blocked 和独立 activation Gate 控制 | LLMTier owner；待 review | topology/persistence 等实际决定形成时另建 ADR |

## 4. 禁止裁剪项

以下内容若适用，不得无理由删除：authority、接口、状态与数据所有权、失败恢复、安全、
验证方法、traceability、版本和来源证据。

本项目还不得删除或弱化：

- Slinky/Piko/LLMTier authority 与唯一 `Runtime -> Piko -> LLMTier` inference path；
- exact-case Service Level ID、单一 Registry、单一 OpenAPI authority；
- Scope B 与 Chat/SSE V0.4 deferred/fail-closed 边界；
- `concurrent_invocation`、shared/overlapping Capacity Group、quota unknown 和 Seat invalidation；
- durable idempotency、lost-response recovery、UnknownOutcome 不盲重派、M2-C 24h/168h；
- Client/Source/SourceInstance 隔离语义、Secret 只写不读、audit；
- candidate 与 runtime activation=false 的区别；
- Current Baseline、Approved Delta 与 Future/Open Gate 的边界；
- 单服务 repo layout，不未经批准增加新机制、config path、selector、fallback 或并行实现。

## 5. Review 与生效

本文件与迁移后的 service design 当前状态保持为 `review`，没有发生 Document Status 升级。
`docs/std.lock.json` 锁定 STD draft.18 的完整 commit SHA 与 annotated tag，
`docs/std-source-manifest.json` 保存 71 个来源 artifact 的 SHA-256。来源记录不等于项目 RAG
ingestion，候选不得标记 accepted/released；本轮 review verdict 也不授权 runtime activation。

重新评审触发条件：

1. STD immutable commit/tag 或 path/template policy 变化；
2. Slinky/Piko 修改 authority、Scope B、recovery 或 header/path contract；
3. production persistence/HA/deployment 形成 ADR；
4. 服务拆成多个独立部署/发布/owner 单元；
5. activation gate 关闭或重新打开；
6. 下一批接口、contract 或 assurance 文档迁移。

批准 commit、生效日期与 reviewer 结论在项目 review 后填写。本轮保留原始设计对未迁移 scope 的
authority；此前错误的 `design.system` 迁移候选在本次输入 dirty worktree 中已处于删除状态，
本轮不 reset、不恢复，也不把该删除解释为 canonical promotion。
