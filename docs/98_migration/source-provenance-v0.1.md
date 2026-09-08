# LLMTier 源码复制来源记录 v0.1

Last Updated: 2026-09-06 13:22:57 +08:00

## 来源

- 源仓库：`/Users/ben/slinky`
- 源仓库 HEAD：`299bff1ea4f9ce63054c64b889524fb048d9fec2`
- 复制方式：从源工作树只读复制到 `/Users/ben/work/LLMTier`
- 源项目处理：未修改、未删除、未停止服务，未复制配置、Secret、live state、模型或大型构建产物

## 复制清单

- `src/`：33 个 Python 源文件，完整复制现有 Tier 实现
- `src/utils/__init__.py`
- `src/utils/response_parser.py`
- `src/utils/sqlite.py`
- `src/stats/__init__.py`
- `src/stats/llm_stats.py`

排除项：`.DS_Store`、`__pycache__/`、`*.pyc`、环境文件、真实 credential、运行状态、日志、模型和构建产物。

## 必要依赖

- `client` 直接依赖 `utils.response_parser`
- `stats_collector` 直接依赖 `utils.sqlite`
- `stats.llm_stats` 是旧统计入口，对 `stats_collector` 和 `tier_model` 构成反向依赖

目标代码已用仅指向 `/Users/ben/work/LLMTier/src` 的 `PYTHONPATH` 验证可导入，不需要把 Slinky `src` 加入 `PYTHONPATH`。

## 源工作树差异

复制时 Tier 范围存在一项未提交源工作树差异：

- `src/backends/volc.py` 相对 HEAD 增加模型名称 `doubao-seed-2.1-turbo`
- 源工作树文件 SHA-256：`80c07c5e99fcb16fa4dab450bfd0332703cd78f27838efef30a9a20d45b118b7`
- HEAD 版本 SHA-256：`93717ea96bf3acc39bb5ff86c77315aaef348dd568951736501451591e38cf71`
- 目标复制的是源工作树版本；目标文件 SHA-256 与源工作树一致

该差异属于源仓库原有用户修改，本次没有在 Slinky 中创建或更改它。

## 暂不直接复制的参考入口

- `/Users/ben/slinky/tier.sh`：依赖 Slinky 根目录、`.venv`、`workspaces/settings.json` 和 `workspaces/tier_state`，需改造成独立项目入口后再引入
- `/Users/ben/slinky/dashboard/tier.html`：依赖旧 Slinky Dashboard 集成，先作为设计和能力审计输入

## 下一步

1. 初始化独立项目的构建、测试和配置边界。
2. 将旧 `SLINKY_*` 环境变量与 Workspace 路径耦合分类为保留、替换、删除或待决定。
3. 保留可复用 admission/routing/quota/usage 基础，移除 Agent、Role、mlexp、CLI runner 和 fallback authority。
4. 实现并验证 Piko 所需 OpenAI-compatible Data Plane，以及 Slinky 所需 scoped capacity/observation surface。
