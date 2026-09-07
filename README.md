# LLMTier

LLMTier 是从 Slinky 中拆出的独立模型服务项目。当前代码基线保留旧 Tier 实现，后续在此基础上完成独立配置、状态、发布，以及面向 Piko 的 OpenAI-compatible Data Plane 和面向 Slinky 的受限 capacity/observation contract。

## 当前状态

- 已完成旧源码与最小 Python 依赖的独立复制。
- 已验证 package 可在不引用 Slinky `src` 的情况下导入。
- OpenAI-compatible Data Plane、capacity/observation 新契约和 conformance 尚未完成。
- 不应将旧 Role routing、Agent backend、mlexp、CLI runner 或 fallback 语义视为新架构已接受的行为。

复制来源和工作树差异见 [`docs/migration/source-provenance-v0.1.md`](docs/migration/source-provenance-v0.1.md)。

## Canonical V0.3 文档

LLMTier 采用 STD `software` profile 与单服务根结构。以下文档是当前 Approved prose authority；批准文档不表示
production Data Plane、Management、Observation、恢复能力或 Runtime Activation 已完成：

- [STD 裁剪清单](docs/00_management/std-tailoring.md)
- [V0.3 Requirements](docs/10_requirements/llmtier-v0.3-requirements.md) 与
  [Traceability](docs/10_requirements/llmtier-v0.3-traceability.md)
- [单服务设计](docs/30_subsystem_design/llmtier-service-design.md)
- [Piko Data Plane](docs/60_interfaces/piko-data-plane-control.md)、
  [Slinky Capacity/Observation](docs/60_interfaces/slinky-capacity-observation-control.md) 与
  [Management](docs/60_interfaces/llmtier-management-control.md) interface controls
- [V0.3 Contract Specification](docs/60_interfaces/contracts/llmtier-v0.3-contract-specification.md)
- [V&V Plan](docs/70_verification/plans/llmtier-v0.3-vv-plan.md) 与
  [Contract Test Specification](docs/70_verification/specifications/llmtier-v0.3-contract-test-specification.md)
- [Release and Operations](docs/80_operations/llmtier-v0.3-release-and-operations.md)

V0.3 字段级机器契约仍唯一由
[`docs/contracts/openapi/llmtier-v0.3.openapi.json`](docs/contracts/openapi/llmtier-v0.3.openapi.json) 定义；
[`compatibility-manifest-v0.3.json`](docs/contracts/compatibility-manifest-v0.3.json) 保持
`overall.runtime_activation=false`，测试源码与 fixtures 保持 executable oracle authority。五份旧 V0.3 prose
已经逐 scope 映射并标为 Superseded，仅保留历史；详见
[`legacy-v03-scope-mapping.md`](docs/98_migration/legacy-v03-scope-mapping.md)。迁移与批准证据位于
[`docs/91_reviews/`](docs/91_reviews/) 和 [`docs/98_migration/`](docs/98_migration/)。

## 本地检查

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m llm_tier --help
```
