# Local Tier Configuration

LLMTier 的默认本地运行配置位于 `config/settings.json`，文件型凭据位于 `config/secrets/`。这两个路径只保存本机运行输入，均被 `.gitignore` 排除，不得提交到 Git、Knowledge Base 或 RAG。

安全要求：

- `config/` 和 `config/secrets/` 使用 owner-only 目录权限；
- `config/settings.json` 及 `config/secrets/` 内文件使用 owner-only 文件权限；
- `settings.json` 中的相对凭据路径以项目根为工作目录解析，例如 `config/secrets/<name>`；
- 验证和审计只记录配置结构、文件存在性及摘要，不输出密钥、Token 或 Cookie 内容。

可使用 `LLMTIER_CONFIG` 或服务的 `--settings` 参数显式选择另一份配置；不要为旧 Slinky 路径建立并行配置或兼容副本。
