# LLMTier

LLMTier 是一个独立的、单服务 Python 项目，拥有自己的源码、配置、运行状态、接口契约、发布与运维边界。
Slinky 和 Piko 是外部 consumer/协作项目，不是 LLMTier 的源码目录、配置 authority、父进程或部署容器。

<a id="std-entry"></a>

## 工程文档标准：STD

本项目采用 STD `0.1.0-draft.26`，固定来源见 [std.lock.json](docs/std.lock.json)。
STD 提供工程文档模板、编写规范、AI 指南与检查工具；它不代替项目设计决定。
编写或修改文档前，先读 [STD 主说明与执行流程](https://github.com/corezilla/STD/blob/5a1e71f4e2baa6e6761b685e91deecbd58cf0649/README.md)，
再按任务选择已采用的模板、通用指南及专项指南，依据项目事实完成正文、图和适用检查。
不自动检查或跟随最新 STD/模板；只有用户明确要求升级才重新对齐。
结构检查通过不等于设计质量、实现或运行验证通过；提交和发布仍需遵循用户授权。

## 当前范围与状态

- 当前实现可作为独立进程启动，提供现有 trusted-network Tier HTTP API 与 operator CLI。
- V0.3 简化候选目标接口包含 OpenAI-compatible Responses、Embeddings、Models、token Usage、
  health/readiness、精简 Management API 和 English Admin Web UI。
- V0.3 目标包的编码、开发调试和Gate U正式单元测试已完成；consumer capture、部署和
  Runtime Activation 尚未完成；`overall.runtime_activation=false`。
- Piko 固定 Pi `9767ba2` 的 `openai-responses` adapter 固定发送 `stream:true`；首个实现因此采用标准 Responses SSE，不另建 endpoint、fallback 或自定义恢复路径。
- LLMTier 不持有 Agent Session/Conversation，不压缩上下文、不执行工具、不管理后端 KV identity。
- SourceInstance、外部 capacity/Seat/claim、自定义 Invocation/idempotency recovery、Cost 与专用 compatibility
  negotiation 已退出 current external contract。
- 旧 Role routing、Agent backend、mlexp、CLI runner 或 fallback 只属于当前 legacy implementation
  baseline，不构成 V0.3 兼容承诺。

历史来源与拆分证据只保留在
[`docs/98_migration/source-provenance.md`](docs/98_migration/source-provenance.md)；它们不定义当前
项目身份或使用方式。

## 快速开始

要求 Python 3.11 或更高版本。在独立虚拟环境中从仓库根目录安装：

```bash
python3 -m pip install -e .
```

安装后的服务入口是 `llm-tier-v03`。空SQLite首次启动必须显式提供一次性bootstrap文件；初始化后SQLite是唯一配置authority，后续启动忽略该文件内容：

```bash
LLMTIER_ADMIN_TOKEN='...' LLMTIER_DATA_TOKEN='...' \
  PYTHONPATH=src python3 -m llmtier_v03 \
  --host 127.0.0.1 --port 8180 \
  --database state/llmtier-v03.sqlite3 \
  --settings config/settings.json
```

仅限loopback合成调试时可设置`LLMTIER_DEV_MODE=1`；这会启用固定开发凭据并允许同源Web UI在loopback免Bearer访问，禁止用于共享或生产监听地址。English Web UI位于`/ui/`。开发期Fake Provider和冒烟入口分别为`tests/fixtures/v03_fake_provider.py`与`tests/integration/v03_smoke.py`。

## 文档导航

| 类别 | 文档 |
|---|---|
| 裁剪与计划 | [STD 裁剪清单](docs/00_management/std-tailoring.md)、[V0.3 编码与测试计划](docs/00_management/llmtier-implementation-plan.md) |
| 需求 | [V0.3 Requirements](docs/10_requirements/llmtier-requirements.md)、[Traceability](docs/10_requirements/llmtier-traceability.md) |
| 系统设计 | [系统设计](docs/20_system_design/llmtier-system-design.md) |
| 模块设计 | [HTTP API](docs/40_module_design/http-api-design.md)、[Web UI](docs/40_module_design/web-ui-design.md)、[Inference](docs/40_module_design/inference-design.md)、[Management](docs/40_module_design/management-design.md)、[Observability](docs/40_module_design/observability-design.md)、[libdiag](docs/40_module_design/libdiag-design.md)、[util](docs/40_module_design/util-design.md)、[log](docs/40_module_design/log-design.md) |
| 接口 | [Piko Data Plane](docs/60_interfaces/piko-data-plane-control.md)、[Slinky Capacity/Observation](docs/60_interfaces/slinky-capacity-observation-control.md)、[Management API](docs/60_interfaces/llmtier-management-control.md)、[Contract Specification](docs/60_interfaces/contracts/llmtier-contract-specification.md) |
| 验证 | [V&V Plan](docs/70_verification/plans/llmtier-vv-plan.md)、[Test Plan](docs/70_verification/plans/llmtier-test-plan.md)、[Contract Test Specification](docs/70_verification/specifications/llmtier-contract-test-specification.md) |
| 运维 | [Release and Operations](docs/80_operations/llmtier-release-and-operations.md)、**[m5air 调试环境手册](docs/80_operations/m5air-operations-manual.md)** |

批准的 prose authority 不表示 production endpoint、durable recovery、Admin UI 或 Runtime Activation 已完成。
其中V0.3 Gate C/Gate U通过不表示production activation通过；真实provider capture、浏览器E2E、部署和三方联调仍是后续门禁。
旧 V0.3 prose 已逐 scope 映射并移至 `docs/99_reference/`。

## 开发与验证

### 仓库布局

| 路径 | 当前职责 |
|---|---|
| `src/` | 单服务 Python 源码；采用 flat module/package layout |
| `tests/` | 单元、边界、契约语义和 STD 一致性测试 |
| `config/settings.json` | 空SQLite首次启动的一次性bootstrap输入；初始化后不再是运行authority |
| `config/secrets/` | 本地只写凭据文件目录；被 Git 忽略，禁止进入日志、证据或 RAG |
| `state/` | 默认本地运行状态、统计和 trace；被 Git 忽略，可用 `LLMTIER_STATE_DIR` 覆盖 |
| `interfaces/` | V0.3 OpenAPI、compatibility manifest、Schema 与 contract vectors |
| `docs/` | 当前 requirements、设计、接口、验证、运维与受控历史 |
| `docs/99_reference/` | 历史、superseded 或 future-only 资料；不是当前 authority |

项目不使用 Slinky workspace 路径，也不从 Slinky 配置目录读取配置。不要创建旧路径副本、alias 或第二套
config/state/contract authority。

### 本地检查

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m tier_service --help
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m cli --help
```

### STD 合规规则（prose 文档）

任何新增或修改的 `docs/**/*.md` 必须满足：

1. **Cover 必填**。每个 prose 文档必须以 `<!-- STD_DOCUMENT_COVER_BEGIN -->` 块开头，包含 `Document ID`、`Template ID`、`Template Conformance`、`Canonical Path` 至少这四列。模板见 STD 仓库 `templates/` 下对应领域的 `<template>.md`。
2. **Template ID 不得发明**。`Template ID` 必须来自本项目 [`docs/00_management/std-tailoring.md`](docs/00_management/std-tailoring.md) §2「启用模板」表中的真实 template id（如 `assurance.test-plan`、`contracts.specification`、`design.system`），不得自行编造。
3. **命名遵循模板**。文件名沿用 STD 模板基名，例如：
   - `verification-validation-plan.md` → 本仓库文件应命名为 `*-vv-plan.md`
   - `test-plan.md` → `*-test-plan.md`
   - `test-specification.md` → `*-test-specification.md`
   - `design.system` → `*-system-design.md`
   - 不允许自造如 `*-system-test-plan.md` 这样的不存在的模板基名。
4. **覆盖裁剪有引用**。如果 `Template Conformance = tailored`，`Tailoring Reference` 必须指向 `std-tailoring.md` §3 裁剪表中的具体 LT-TL-XXX 条目；`native` 则不需要裁剪引用。
5. **路径与 cover 自洽**。`Canonical Path` 必须与文件实际路径一致（相对仓库根）。

不满足以上规则的 prose 文档视为非合规，review 时退回作者按 STD 模板重写。机器契约层（OpenAPI / manifest / fixtures / Schema）由 `tools/contract_semantic_validator_v03.py` 校验，不在本节范围。

## 贡献与维护

当前 operator CLI 提供 `health`、`runtime`、`debug`、`stats`、`invoke`、`reset`、`reload` 和 `probe`。
这些命令对应 legacy 实现接口，不是目标 OpenAI-compatible consumer surface；V0.3 consumer 应以
[`interfaces/openapi/llmtier.openapi.json`](interfaces/openapi/llmtier.openapi.json) 和
[`interfaces/compatibility/compatibility-manifest-v0.3.json`](interfaces/compatibility/compatibility-manifest-v0.3.json)
为准，并在 activation gate 关闭前不得按 production capability 使用。
