# LLMTier

LLMTier 是从 Slinky 中拆出的独立模型服务项目。当前代码基线保留旧 Tier 实现，后续在此基础上完成独立配置、状态、发布，以及面向 Piko 的 OpenAI-compatible Data Plane 和面向 Slinky 的受限 capacity/observation contract。

## 当前状态

- 已完成旧源码与最小 Python 依赖的独立复制。
- 已验证 package 可在不引用 Slinky `src` 的情况下导入。
- OpenAI-compatible Data Plane、capacity/observation 新契约和 conformance 尚未完成。
- 不应将旧 Role routing、Agent backend、mlexp、CLI runner 或 fallback 语义视为新架构已接受的行为。

复制来源和工作树差异见 [`docs/migration/source-provenance-v0.1.md`](docs/migration/source-provenance-v0.1.md)。

V0.3 的统一系统范围、责任边界和激活门槛已按 STD `design.system` 模板迁移到
[`docs/design/llmtier-v0.3-system-design.md`](docs/design/llmtier-v0.3-system-design.md)。旧的
[`docs/design/llmtier-v0.3-design-review.md`](docs/design/llmtier-v0.3-design-review.md) 在迁移 review
完成前保留为来源记录；两者及关联 Contract/Schema/Manifest 当前仍是评审候选，不表示生产 Data
Plane、Management、Observation 或恢复能力已实现。STD 裁剪决定和文档盘点分别见
[`docs/management/std-tailoring-v0.1.md`](docs/management/std-tailoring-v0.1.md) 与
[`docs/management/current-document-inventory.md`](docs/management/current-document-inventory.md)。
V0.3 的唯一机器契约为
[`docs/contracts/openapi/llmtier-v0.3.openapi.json`](docs/contracts/openapi/llmtier-v0.3.openapi.json)；历史 v0.2 Schema 不作为 V0.3 Data Plane authority。

## 本地检查

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m llm_tier --help
```
