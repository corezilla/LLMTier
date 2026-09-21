# 测试规范

> [项目规范总索引](README.md) · [项目STD采用入口](../../../README.md#std-entry)

| 控制项 | 内容 |
|---|---|
| 规范ID | `LLMTier-testing-standard` |
| 版本 / 状态 | `0.1.0 / Active` |
| Owner | `LLMTier` |
| 生效依据 / 最后核实日期 | `2026-09-21` |

## 适用范围与触发任务

- **适用目录**：`tests/`、`tools/`
- **适用对象**：所有测试代码（unit、system、integration）
- **触发任务**：编写测试、修改测试、PR review

## 规范要求与检查方法

| 条款ID | 要求 / 条件 | 检查方法与证据 | 责任方 |
|---|---|---|---|
| TS-001 | 测试必须是可重复的，使用临时目录和端口，不污染环境 | 代码审查：检查是否使用 `tempfile.TemporaryDirectory()` | Author |
| TS-002 | 测试依赖外部服务时，文件头部必须写明：服务地址、端口、模型名称 | 代码审查：检查文件头部注释是否完整 | Author / Reviewer |
| TS-003 | LLMTier 是 LAN 服务，测试的 provider endpoint 必须使用 LAN IP（192.168.1.x），禁止使用 127.0.0.1 | 代码审查：检查 provider endpoint 配置 | Author / Reviewer |
| TS-004 | 测试失败时，错误信息必须足够定位问题 | 代码审查：检查 assertion message 是否清晰 | Author / Reviewer |
| TS-005 | 所有单元测试和系统测试必须通过后才能提交 | CI 检查：`PYTHONPATH=src python3 -m pytest tests/ tests/system/st_*.py -q` 输出 221 pass | CI |

## 与STD的关系、例外及冲突

- 本规范补充 `assurance.test-specification` 模板的项目特定实现要求
- 测试计划详见 `docs/70_verification/plans/llmtier-v0.3-test-plan.md`

## 修订与替代记录

| 版本 | 修改内容 | 生效或替代决定 | 受影响范围 / 索引及引用检查 |
|---|---|---|---|
| 0.1.0 | 初始版本 | 2026-09-21 | 全部测试代码 |
