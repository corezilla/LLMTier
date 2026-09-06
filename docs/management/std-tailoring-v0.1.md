# LLMTier STD 裁剪清单 v0.1

## 1. 适用背景

- 项目：`LLMTier`
- 生命周期阶段：V0.3 design/contract candidate；production implementation 尚未激活
- 产品类型：software
- 安全或业务关键性：模型服务控制面和数据面；涉及 credential、跨 Client 隔离、容量与恢复
- STD 来源：`0.1.0-draft.1`，尚无 immutable revision
- 本轮范围：只迁移 V0.3 系统设计；不借模板迁移改变已冻结的 Scope B 或机器契约

## 2. 启用模板

| Template ID | Profile | 是否必需 | 计划文档 | Owner |
|---|---|---:|---|---|
| `management.tailoring` | management | 是 | `docs/management/std-tailoring-v0.1.md` | LLMTier |
| `design.system` | systems/software | 是 | `docs/design/llmtier-v0.3-system-design.md` | LLMTier |
| `interfaces.control` | software | 是，后续批次 | Piko Data Plane、Slinky Observation、Management interface migration | LLMTier |
| `contracts.specification` | software | 是，后续批次 | OpenAPI/manifest/error/schema 的说明层；机器文件保持原位 | LLMTier |
| `assurance.vv-plan` | software | 是，后续批次 | V0.3 activation-gate V&V plan | LLMTier |
| `assurance.test-specification` | software | 是，后续批次 | Contract/SDK/recovery/isolation test specification | LLMTier |
| `review.packet` | management/software | 是，冻结前 | STD migration 与 V0.3 activation review packet | LLMTier owner；Slinky/Piko reviewer |
| `decisions.adr` | software | 条件必需 | 新增持久化/HA/部署等重大决定时逐项建立 | LLMTier |
| `operations.release` | operations/software | production 前必需 | deployment、backup、rollback、retirement | LLMTier |

## 3. 裁剪决定

| ID | 模板/章节 | 决定 | 理由 | 风险 | 批准人 | ADR |
|---|---|---|---|---|---|---|
| LT-TL-001 | `design.system` 全部正文与附录 | keep | authority、runtime、recovery、capacity、security、traceability 和 gate 均适用 | 无 | 待项目 review | N/A |
| LT-TL-002 | `design.system` 部署/物理视图 | simplify | production topology、DB、HA、RPO/RTO 尚未冻结，只记录逻辑部署与 Open Gate | 选型不足可能阻塞 retention/recovery | 待项目 review | 选型时新增 ADR |
| LT-TL-003 | `requirements.specification` | omit 本轮 | 产品需求 authority 在 Slinky；LLMTier 不复制或替 Slinky 批准需求 | 需求检索跨文档 | 待项目 review | N/A；以 Review ID/Contract traceability 缓解 |
| LT-TL-004 | `design.definition` | omit 本轮 | 当前仅迁移系统级设计；下级模块责任尚未形成稳定实现边界 | 构建块实现细节不足 | 待项目 review | 模块冻结后重新裁剪 |
| LT-TL-005 | `design.hardware`/`design.fpga` | omit | 项目当前无硬件/FPGA ownership；Provider/Local Deployment 仅为外部资源 | 无 | 待项目 review | N/A |
| LT-TL-006 | `interfaces.control` | keep，后续迁移 | 三个 API 分面必须保持独立 authority 与演进规则 | 延后期间旧 Markdown 仍是说明 authority | 待项目 review | N/A |
| LT-TL-007 | `contracts.specification` | keep，后续迁移 | OpenAPI、manifest、fixtures 必须保留机器可执行 authority | 不能把机器契约转写成不一致 Markdown | 待项目 review | N/A |
| LT-TL-008 | assurance templates | keep，后续迁移 | candidate 与 runtime activation 必须以证据区分 | 未迁移 QA 可能缺少执行报告层 | 待项目 review | N/A |
| LT-TL-009 | `management.project-plan` | omit | 项目排期/资源管理不在本轮设计迁移范围，现无稳定计划基线 | 实施顺序不等于项目计划 | 待项目 review | N/A |
| LT-TL-010 | `decisions.adr` | simplify/按需 | 已有决定保留原 Matrix Review ID，不伪造 retrospective ADR | 决策分散 | 待项目 review | 新决定必须使用 ADR |
| LT-TL-011 | 原文档与 v0.1/v0.2 历史材料 | keep | 首轮 review 前禁止删除；inventory 标注 current/historical/superseded | 误检索历史语义 | 待项目 review | review 后归档建议 |
| LT-TL-012 | RAG ingestion | omit 到 review 后 | 候选尚未成为 canonical artifact | 暂时不能从项目 RAG 检索新文档 | 待项目 review | N/A |

## 4. 禁止裁剪项

不得删除或弱化：

- Slinky/Piko/LLMTier authority 与唯一 `Runtime -> Piko -> LLMTier` inference path；
- exact-case Service Level ID、单一 Registry、单一 OpenAPI authority；
- Scope B 与 Chat/SSE V0.4 deferred/fail-closed 边界；
- `concurrent_invocation`、shared/overlapping Capacity Group、quota unknown 和 Seat invalidation；
- durable idempotency、lost-response recovery、UnknownOutcome 不盲重派、M2-C 24h/168h；
- Client/Source/SourceInstance 隔离语义、Secret 只写不读、audit；
- candidate 与 runtime activation=false 的区别；
- Review ID、Contract、fixture、test 和 execution evidence traceability；
- 当前实现基线、批准增量与未来设想之间的边界。

## 5. Review 与生效

本文件和迁移后的系统设计当前状态为 `review`。STD 尚无 immutable source revision，因此
`docs/std.lock.json.source_revision` 保持 `null`；不得标记 accepted/released。重新评审触发条件：

1. STD 首个 immutable commit/tag；
2. Slinky 或 Piko 修改已冻结 authority、Scope B、recovery 或 header/path contract；
3. production persistence/HA/deployment 形成 ADR；
4. 任何 activation gate 关闭或重新打开；
5. 下一批接口、contract 或 assurance 文档迁移。

批准 commit、生效日期和 reviewer 结论在项目 review 后填写。本轮不删除或替换旧设计文档。
