# LLMTier

LLMTier 是从 Slinky 中拆出的独立模型服务项目。当前代码基线保留旧 Tier 实现，后续在此基础上完成独立配置、状态、发布，以及面向 Piko 的 OpenAI-compatible Data Plane 和面向 Slinky 的受限 capacity/observation contract。

## 当前状态

- 已完成旧源码与最小 Python 依赖的独立复制。
- 已验证 package 可在不引用 Slinky `src` 的情况下导入。
- OpenAI-compatible Data Plane、capacity/observation 新契约和 conformance 尚未完成。
- 不应将旧 Role routing、Agent backend、mlexp、CLI runner 或 fallback 语义视为新架构已接受的行为。

复制来源和工作树差异见 [`docs/migration/source-provenance-v0.1.md`](docs/migration/source-provenance-v0.1.md)。

## 本地检查

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m llm_tier --help
```

