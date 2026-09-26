<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier 改进计划

> STD 使用入口：[项目采用说明与标准导航](../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-improvement-plan` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-21` |
| Last Modified Date | `2026-09-22` |
| Template ID | `management.quality-plan` |
| Template Version | `0.2.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/00_management/improvement-plan.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 改进项清单

| # | 改进项 | 优先级 | 状态 |
|---|--------|--------|------|
| 1 | 创建 PR Review Guide，加入架构层面检查项 | P0 | 待执行 |
| 2 | 更新测试计划 §2.2，补充 OMLX embedding 环境信息 | P0 | 待执行 |
| 3 | ST-12 头部加注释，说明依赖 m5air OMLX | P1 | 待执行 |
| 4 | 在测试计划添加"架构设计检查项"章节 | P1 | 待执行 |

---

## 改进计划执行

### 改进项 1：创建 PR Review Guide

**文件位置**：`docs/20_arch_and_design/PR-REVIEW-GUIDE.md`

**内容**：
```markdown
# LLMTier PR Review Guide

## 架构层面检查项（必查）

1. **LLMTier 是 LAN 服务** — 测试代码不能用 127.0.0.1，必须用局域网 IP
2. **Provider endpoint 配置** — 确认指向正确环境（m5mac: 9000, m5air: 9000）
3. **测试依赖的服务** — 测试文件头部要写清依赖哪个环境的什么服务
4. **环境约束** — 测试计划 §2.2 明确说明 m5air 不是测试环境

## 常规检查项

- [ ] 功能逻辑正确
- [ ] 测试覆盖正确
- [ ] 没有硬编码敏感信息
- [ ] 单元测试通过
- [ ] 系统测试通过

## 需要人工确认的

- [ ] ST-19 / ST-20（长时测试）需 operator 手动跑
```

### 改进项 2：更新测试计划 §2.2

**文件位置**：`docs/70_verification/plans/llmtier-test-plan.md`

**添加内容**：
```
OMLX embedding | m5air: http://192.168.1.9:9000/v1 (bge-m3, 1024维)
                m5mac: http://192.168.1.8:9000 (Qwen3-Embedding, 1024维)
                ST-12 需要连 m5air OMLX，通过局域网直连
```

### 改进项 3：ST-12 头部加注释

**文件位置**：`tests/system/st_12_embedding_invariant.py`

**添加注释**：
```python
"""ST-12 Slinky embedding invariant.

IMPORTANT: LLMTier is a LAN service. Tests must use LAN IP (192.168.1.9),
not 127.0.0.1 — because piko calls LLMTier over LAN.

This test depends on:
- m5air OMLX at http://192.168.1.9:9000/v1
- Model: bge-m3 (1024 dimensions)
- API key: from ~/.omlx/settings.json (same as m5mac)
"""
```

### 改进项 4：在测试计划添加"架构设计检查项"章节

**位置**：测试计划新增 §2.4

**内容**：
```
### 2.4 架构设计检查项

PR Review 时需确认：
1. 测试代码使用 LAN IP（192.168.1.x），不用 127.0.0.1
2. Provider endpoint 指向正确环境
3. 测试依赖的服务在目标环境可用
4. 测试文件头部写清依赖的服务和环境
```

---

## 检测点清单

| # | 检测点 | 验证方法 |
|---|--------|----------|
| 1 | PR Review Guide 文件存在 | `ls docs/20_arch_and_design/PR-REVIEW-GUIDE.md` |
| 2 | PR Review Guide 包含 LAN 服务检查项 | `grep -c "127.0.0.1" docs/20_arch_and_design/PR-REVIEW-GUIDE.md` 应为 0 |
| 3 | 测试计划 §2.2 包含 OMLX 环境信息 | `grep -c "192.168.1.9" docs/70_verification/plans/llmtier-test-plan.md` > 0 |
| 4 | ST-12 注释包含 LAN 服务说明 | `grep -c "LAN service" tests/system/st_12_embedding_invariant.py` > 0 |
| 5 | ST-12 不使用 127.0.0.1 | `grep "127.0.0.1" tests/system/st_12_embedding_invariant.py` 应无输出 |
| 6 | 所有测试仍然通过 | `PYTHONPATH=src python3 -m pytest tests/ tests/system/st_*.py -q` 221 pass |
```