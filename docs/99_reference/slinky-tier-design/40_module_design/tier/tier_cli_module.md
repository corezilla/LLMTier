# Tier CLI Module Design

Version: v1.4
Last Updated: 2026-09-08 12:18:44
Status: Implemented / Module Test Integration

code_directory: `src/llm_tier/cli/`
current_source_files: `src/llm_tier/cli/__init__.py`, `src/llm_tier/cli/__main__.py`
provided_interfaces: 无独立业务接口；提供 operator-facing 命令行入口
consumed_interfaces: `TIR-HTTP-001`, `TIR-HTTP-002`

## 1. Ownership与职责

所属Subsystem：Tier。

本Module拥有 Tier 的命令行运维入口，负责把 operator 的启动、探活、runtime 查询、stats 查询、management 操作映射到既有 Tier Client / Tier Server Contract。

本Module不拥有新的 routing、config truth 或 backend authority。CLI 只是 operator-facing entry，不得绕过 Tier Client / Tier Server 直接改内部状态。

## 2. Source Boundary

| 位置 | 当前职责 |
|---|---|
| `src/llm_tier/cli/__main__.py` | 唯一 Tier operator CLI parser、HTTP operation 映射、结构化输出和退出码 |
| `src/llm_tier/cli/__init__.py` | Package boundary，不承载第二套命令实现 |

### 2.1 Current Implementation Baseline

当前唯一入口为 `python -m llm_tier.cli`。CLI 通过既有 `TierClient.proxy_request()` 调用 Tier HTTP Contract；不直接 import Tier Server 内部 state，不建立第二套 routing、stats 或 management authority。

## 3. Module Overview

### 3.1 模块定位

Tier CLI Module 为开发者和运维者提供脱离 WebUI 的独立调试与操作入口。

### 3.2 基本流程

1. 解析命令行参数。
2. 校验目标 operation、scope 和 identity。
3. 调用 Tier Client 或 management HTTP route。
4. 输出结构化结果、错误码和审计字段。

### 3.3 核心设计思路

- CLI 只复用既有 Contract，不定义第二套协议。
- CLI 结果必须适合脚本化断言和独立单元测试。
- CLI 与 WebUI 共享同一 server authority，不允许出现“CLI 能做、WebUI 看不到”的隐藏状态。

## 4. Command Contract

CLI 至少要覆盖以下能力：

| 命令类别 | 输入 | 输出 |
|---|---|---|
| health/runtime/stats | scope、time、filter | 结构化 JSON 或表格摘要 |
| invoke/debug | role、prompt source、timeout | 标准 Tier 调用结果 |
| management | backend identity、操作参数 | operation result / conflict / error |
| reset/recovery | 明确 reset scope | 清零/恢复结果与审计日志 |

统一约束：

- 所有命令必须支持结构化返回，不能只打印人类可读文本。
- 参数错误、Tier 不可达、协议错误、业务失败必须返回可区分 error code。
- Server启动入口的`--host`允许`localhost`、loopback或明确private IP，禁止wildcard/public bind；operator CLI的`--server-url`遵循同一trusted host规则。
- 不得发明绕过 `TIR-HTTP-001` / `TIR-HTTP-002` 的隐藏命令。

## 5. 可测试性设计

- 必须支持无 Slinky 主流程时的独立调试。
- 必须支持 fake Tier Server / fixture config / fixture stats 的命令级测试。
- 必须保留 debug 开关、耗时统计、请求摘要和错误分类，便于快速定位问题。
- 必须支持一键检查前置条件和快速恢复到可测试状态，避免 system test 被环境问题整体挡住。

## 6. Current Gap

当前实现已经提供正式 subprocess 入口。后续 Module Test 联调只处理具体 production 行为偏差，不再以临时 shell 或 marker process 替代 CLI。

## 7. ISD

- `docs/50_implementation_design/tier/tier_cli/__main__.py.isd.md`

## 8. Business Branch / Condition Design

| Branch ID | Decision owner / public entry | Exact predicate | True / selected path | False / else path | State / side effect | Failure / recovery | Required evidence |
|---|---|---|---|---|---|---|---|
| `TCLI-BR-001` | CLI parser | subcommand属于声明集合且required flags存在、类型/范围合法 | 构造typed command request | 打印usage与typed argument error，非零退出 | 不调用Tier Client | 修正argv后重跑 | argv、parsed request、exit code |
| `TCLI-BR-002` | Server readiness gate | configured URL可解析且health endpoint返回compatible version | 调用正式Tier Client | 返回connection/readiness error | 不启动替代server或扫描端口 | 服务恢复后重跑同命令 | URL、health response、client call absence/presence |
| `TCLI-BR-003` | Command dispatcher | action与唯一client method映射，request identity完整 | 执行一次client call | unknown映射在side effect前失败 | mutation action只执行一次 | timeout按command policy处理，不重复非幂等请求 | dispatch trace、request ID、call count |
| `TCLI-BR-004` | Output/exit mapper | typed result为success且requested output format可序列化 | stdout写JSON/text并退出0 | typed error写stderr/safe envelope并非零退出 | credential和secret始终redact | serialization失败返回internal error，不输出部分JSON | stdout/stderr、exit code、redaction audit |
