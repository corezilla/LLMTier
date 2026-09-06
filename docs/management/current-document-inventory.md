# LLMTier 当前文档盘点与 STD 映射

盘点日期：2026-09-07  
盘点基线：`7607f55f249a2b63d2495566895fb598a5b4eaaa`  
范围：项目 README 与 `docs/` 下现有人工/机器文档；源码和测试代码不列为设计文档。

## 1. Authority 与状态规则

- LLMTier 是本仓库设计、接口实现和模型服务事实的 authority。
- Slinky 的 Project/Plan/IR 与 Scope 决策、Piko 的 Agent Runtime/adapter 事实仍由各自项目负责。
- V0.3 字段级机器接口 authority 是 `docs/contracts/openapi/llmtier-v0.3.openapi.json`；
  compatibility activation authority 是 v0.3 manifest。
- v0.1/v0.2 是历史输入，不得与 v0.3 同时作为 current authority。
- 本次迁移只新增 review candidate，不把任何未实现能力提升为 accepted/released/active。

## 2. 文档清单

| 路径 | 类型/版本 | Authority | 状态 | 上位/下位与重复冲突 | STD Template ID / 处置 |
|---|---|---|---|---|---|
| `README.md` | 项目索引 | LLMTier | current，部分状态需随迁移更新 | 指向 provenance、总体设计、OpenAPI | project index；保留并更新链接 |
| `docs/design/llmtier-v0.3-design-review.md` | 系统设计 v0.3 | LLMTier | current source；Review Amendment 4 | 新 STD design.system 的迁移来源；review 前不删除 | `design.system` → 新候选 |
| `docs/design/llmtier-v0.3-system-design.md` | 系统设计 v0.3 STD | LLMTier | new review candidate | 结构化承接上一文件，不改变契约 | `design.system`；本轮主交付 |
| `docs/design/legacy-capability-audit-v0.1.md` | 现状/差距审计 v0.1 | LLMTier | current design input | 支撑 implementation baseline，不是新契约 | `review.packet` evidence；保留 |
| `docs/migration/source-provenance-v0.1.md` | 迁移 provenance v0.1 | LLMTier | current evidence | 记录从 Slinky 复制的源码边界 | `review.packet` evidence；保留 |
| `docs/future/llmtier-v0.4-data-plane.md` | future scope | LLMTier/Slinky decision | future/not implemented | 与 V0.3 current OpenAPI 明确分离 | 后续 `design.definition`/`contracts.specification`；保留 |
| `docs/contracts/piko-data-plane-contract-v0.1.md` | interface v0.1 | LLMTier | historical/superseded | 被 v0.2/v0.3 取代；surface 语义过期 | `interfaces.control`；后续归档 |
| `docs/contracts/piko-data-plane-contract-v0.2.md` | interface v0.2 | LLMTier | historical/superseded | 被 v0.3 Scope B 取代 | `interfaces.control`；后续归档 |
| `docs/contracts/piko-data-plane-contract-v0.3.md` | interface v0.3 | LLMTier | current candidate/not active | 说明 OpenAPI Data Plane/recovery | `interfaces.control`；下一批迁移 |
| `docs/contracts/slinky-capacity-observation-contract-v0.1.md` | interface v0.1 | LLMTier | historical/superseded | 被 v0.2/v0.3 取代 | `interfaces.control`；后续归档 |
| `docs/contracts/slinky-capacity-observation-contract-v0.2.md` | interface v0.2 | LLMTier | historical/superseded | 被 v0.3 取代 | `interfaces.control`；后续归档 |
| `docs/contracts/slinky-capacity-observation-contract-v0.3.md` | interface v0.3 | LLMTier | current candidate/not active | 说明 Client-scoped Observation | `interfaces.control`；下一批迁移 |
| `docs/contracts/llmtier-management-contract-v0.3.md` | interface v0.3 | LLMTier | current required candidate/not implemented | 说明 Management API/UI；字段由 OpenAPI 约束 | `interfaces.control`；下一批迁移 |
| `docs/contracts/openapi/llmtier-v0.3.openapi.json` | OpenAPI 3.1 v0.3 | LLMTier | current machine authority/candidate | 唯一 current Data Plane/Observation/Management Schema；不得与 v0.2 并列 | `contracts.specification` machine artifact；原位保留 |
| `docs/contracts/compatibility-manifest-v0.1.json` | manifest v0.1 | LLMTier | historical/superseded | 被 v0.2/v0.3 取代 | contract evidence；后续归档 |
| `docs/contracts/compatibility-manifest-v0.2.json` | manifest v0.2 | LLMTier | historical/superseded | 被 v0.3 取代 | contract evidence；后续归档 |
| `docs/contracts/compatibility-manifest-v0.3.json` | manifest v0.3 | LLMTier | current candidate；activation=false | compatibility/activation machine authority | `contracts.specification` machine artifact；原位保留 |
| `docs/contracts/schemas/llmtier-contracts-v0.2.schema.json` | JSON Schema v0.2 | LLMTier | historical；非 V0.3 authority | 与 v0.3 部分同名 DTO 冲突，manifest 不装载 | contract provenance；后续归档 |
| `docs/contracts/fixtures/v0.2/*` | fixtures v0.2 | LLMTier | historical | v0.2 capacity/idempotency/recovery evidence | assurance evidence；后续归档 |
| `docs/contracts/fixtures/v0.3/capacity-semantic-negative-fixtures.json` | fixture v0.3 | LLMTier | current candidate evidence | capacity semantic validator negative cases | `assurance.test-specification` evidence；原位保留 |
| `docs/contracts/fixtures/v0.3/data-plane-openapi-fixtures.json` | fixture v0.3 | LLMTier | current candidate evidence | Responses/Embeddings strict positive/negative | assurance evidence；原位保留 |
| `docs/contracts/fixtures/v0.3/deferred-surface-fail-closed.json` | fixture v0.3 | LLMTier | current candidate evidence | 证明 Chat/SSE V0.3 不存在 | assurance evidence；原位保留 |
| `docs/contracts/fixtures/v0.3/idempotency-forgotten-key-options.json` | fixture v0.3 | LLMTier | current policy evidence/not active | policy selected 与 runtime activation 分离 | assurance evidence；原位保留 |
| `docs/contracts/fixtures/v0.3/metadata-utf8-byte-fixtures.json` | fixture v0.3 | LLMTier | current candidate evidence | metadata byte limits | assurance evidence；原位保留 |
| `docs/contracts/fixtures/v0.3/observation-management-openapi-fixtures.json` | fixture v0.3 | LLMTier | current candidate evidence | Observation/Management DTO 与 aggregate cases | assurance evidence；原位保留 |
| `docs/contracts/fixtures/v0.3/recovery-protocol-fixtures.json` | fixture v0.3 | LLMTier | current candidate evidence | active/terminal/recovery headers/status | assurance evidence；原位保留 |
| `docs/qa/llm-tier-contract-qa-v0.1.md` | QA ledger v0.1 | LLMTier | historical/superseded | open items later resolved/changed | `assurance.vv-plan` provenance；后续归档 |
| `docs/qa/llm-tier-contract-qa-v0.2.md` | QA ledger v0.2 | LLMTier | historical/superseded | 被 Amendment 4 QA 更新 | assurance provenance；后续归档 |
| `docs/qa/llm-tier-contract-qa-v0.3.md` | QA/traceability v0.3 | LLMTier | current candidate evidence | Review→artifact→test；实现 evidence 仍开放 | `assurance.vv-plan` + `assurance.test-specification`；下一批迁移 |

## 3. 旧→新映射与未迁移内容

| 旧 authority/内容 | 新候选/目标 | 本轮结果 |
|---|---|---|
| `llmtier-v0.3-design-review.md` | `llmtier-v0.3-system-design.md` | 已按 `design.system` 全章节迁移；旧文件保留待 review |
| 三份 v0.3 interface Markdown | `interfaces.control` 实例 | 未迁移；保持 current candidate，下一批处理 |
| OpenAPI/manifest/error/schema | `contracts.specification` 说明 + 原机器文件 | 未转写机器内容；下一批只补说明层 |
| v0.3 QA 与 fixtures/tests | assurance templates + 原 evidence | 未迁移；现有执行证据继续有效 |
| Matrix review ledger | `review.packet` | 未迁移；保留原 Review ID，冻结前生成 |

## 4. 冲突与归档建议

1. v0.1/v0.2 Markdown、Schema、manifest 和 fixtures 应在 STD migration review 通过后移动到明确的
   archive/provenance 区域，或由检索 ACL/status 排除；首轮不删除。
2. 旧总体设计 §11 同时记录早期全 surface proposal 与后来的 Scope B，历史上正确但容易误读；
   新系统设计只把 Scope B 作为 current，并在决策表保留来源。
3. README 的“当前状态”应继续强调 candidate 与 production implementation 的区别，并新增新设计入口。
4. `rag/std-ingestion-manifest.jsonl` 在新候选通过项目 review 成为 canonical artifact 后再生成；当前不索引。
