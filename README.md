# LLMTier

LLMTier 是一个独立的、单服务 Python 项目，拥有自己的源码、配置、运行状态、接口契约、发布与运维边界。
Slinky 和 Piko 是外部 consumer/协作项目，不是 LLMTier 的源码目录、配置 authority、父进程或部署容器。

## 当前能力边界

- 当前实现可作为独立进程启动，提供现有 trusted-network Tier HTTP API 与 operator CLI。
- V0.3 简化候选目标接口包含 OpenAI-compatible Responses、Embeddings、Models、token Usage、
  health/readiness、精简 Management API 和中文 Admin Web UI。
- V0.3 OpenAPI 和设计是 review candidate，但 production wiring、consumer capture 和
  Runtime Activation 尚未完成；`overall.runtime_activation=false`。
- Piko 固定 Pi `9767ba2` 的 `openai-responses` adapter 固定发送 `stream:true`；首个实现因此采用标准 Responses SSE，不另建 endpoint、fallback 或自定义恢复路径。
- LLMTier 不持有 Agent Session/Conversation，不压缩上下文、不执行工具、不管理后端 KV identity。
- SourceInstance、外部 capacity/Seat/claim、自定义 Invocation/idempotency recovery、Cost 与专用 compatibility
  negotiation 已退出 current external contract。
- 旧 Role routing、Agent backend、mlexp、CLI runner 或 fallback 只属于当前 legacy implementation
  baseline，不构成 V0.3 兼容承诺。

历史来源与拆分证据只保留在
[`docs/98_migration/source-provenance-v0.1.md`](docs/98_migration/source-provenance-v0.1.md)；它们不定义当前
项目身份或使用方式。

## 仓库布局

| 路径 | 当前职责 |
|---|---|
| `src/` | 单服务 Python 源码；采用 flat module/package layout |
| `tests/` | 单元、边界、契约语义和 STD 一致性测试 |
| `config/settings.json` | 默认本地配置；被 Git 忽略，可用 `LLMTIER_CONFIG` 或 `--settings` 覆盖 |
| `config/secrets/` | 本地只写凭据文件目录；被 Git 忽略，禁止进入日志、证据或 RAG |
| `state/` | 默认本地运行状态、统计和 trace；被 Git 忽略，可用 `LLMTIER_STATE_DIR` 覆盖；单文件 debug-state 可再由既有 `TIER_TRACE_STATE_PATH` 显式选择 |
| `interfaces/` | V0.3 OpenAPI、compatibility manifest、Schema 与 contract vectors |
| `docs/` | 当前 requirements、设计、接口、验证、运维与受控历史 |
| `docs/99_reference/` | 历史、superseded 或 future-only 资料；不是当前 authority |

项目不使用 Slinky workspace 路径，也不从 Slinky 配置目录读取配置。不要创建旧路径副本、alias 或第二套
config/state/contract authority。

## 安装与启动

要求 Python 3.11 或更高版本。在独立虚拟环境中从仓库根目录安装：

```bash
python3 -m pip install -e .
```

安装后的服务入口是 `llm-tier`，operator CLI 是 `llm-tier-cli`：

```bash
llm-tier --host 127.0.0.1 --port 8765 --settings config/settings.json
llm-tier-cli --server-url http://127.0.0.1:8765 health
```

不安装 editable package 时，可从源码树使用等价入口：

```bash
PYTHONPATH=src python3 -m tier_service --host 127.0.0.1 --port 8765 --settings config/settings.json
PYTHONPATH=src python3 -m cli --server-url http://127.0.0.1:8765 health
```

默认监听 `127.0.0.1:8765`。client 可用 `TIER_SERVER_URL` 选择 credential-free 的 localhost、loopback、
RFC1918 或 IPv6 ULA origin。当前 transport 不等同于 production TLS/auth 部署批准。

当前 operator CLI 提供 `health`、`runtime`、`debug`、`stats`、`invoke`、`reset`、`reload` 和 `probe`。
这些命令对应 legacy 实现接口，不是目标 OpenAI-compatible consumer surface；V0.3 consumer 应以
[`interfaces/openapi/llmtier-v0.3.openapi.json`](interfaces/openapi/llmtier-v0.3.openapi.json) 和
[`interfaces/compatibility/compatibility-manifest-v0.3.json`](interfaces/compatibility/compatibility-manifest-v0.3.json)
为准，并在 activation gate 关闭前不得按 production capability 使用。

## Canonical V0.3 文档

LLMTier 采用 STD `software` profile 与单服务根结构：

- [STD 裁剪清单](docs/00_management/std-tailoring.md)
- [V0.3 Requirements](docs/10_requirements/llmtier-v0.3-requirements.md) 与
  [Traceability](docs/10_requirements/llmtier-v0.3-traceability.md)
- [系统设计](docs/20_system_design/llmtier-system-design.md)
- [Piko Data Plane](docs/60_interfaces/piko-data-plane-control.md)、
  [Slinky Capacity/Observation](docs/60_interfaces/slinky-capacity-observation-control.md) 与
  [Management](docs/60_interfaces/llmtier-management-control.md) interface controls
- [V0.3 Contract Specification](docs/60_interfaces/contracts/llmtier-v0.3-contract-specification.md)
- [V&V Plan](docs/70_verification/plans/llmtier-v0.3-vv-plan.md) 与
  [Contract Test Specification](docs/70_verification/specifications/llmtier-v0.3-contract-test-specification.md)
- [Release and Operations](docs/80_operations/llmtier-v0.3-release-and-operations.md)

批准的 prose authority 不表示 production endpoint、durable recovery、Admin UI 或 Runtime Activation 已完成。
旧 V0.3 prose 已逐 scope 映射并移至 `docs/99_reference/`；迁移和批准证据位于 `docs/91_reviews/` 与
`docs/98_migration/`。

## Engineering Standard 与本地检查

本项目采用 STD `0.1.0-draft.26`，由 [`docs/std.lock.json`](docs/std.lock.json) 固定完整来源 commit，
并由 [`docs/std-source-manifest.json`](docs/std-source-manifest.json) 记录来源 artifact 摘要。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m tier_service --help
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m cli --help
```
