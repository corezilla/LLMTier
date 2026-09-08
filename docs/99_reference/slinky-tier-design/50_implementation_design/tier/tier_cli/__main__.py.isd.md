# `src/llm_tier/cli/__main__.py` ISD

Version: v1.1
Last Updated: 2026-09-08 12:18:44
Status: Implemented / Module Test Integration

target_file: `src/llm_tier/cli/__main__.py`
target_state: `existing`

所属边界：Tier / Tier CLI Module。
上游：`docs/40_module_design/tier/tier_cli_module.md`。

## 1. 文件职责

本文件提供唯一 Tier operator subprocess 入口，将命令行参数映射到既有 Tier HTTP Contract，并输出可由脚本稳定判定的结果。不得直接访问 Tier Server 内部 state。

## 2. Callable Contract

- `build_parser() -> argparse.ArgumentParser`
  - 返回唯一 command tree。
  - 全局参数：`--server-url: str=""`；`--output: Literal["json", "human"]="json"`。
  - 子命令：`health`、`runtime`、`debug`、`stats`、`invoke`、`reset`、`reload`、`probe`。
- `load_request(path_value: str) -> dict[str, Any]`
  - `path_value` 必须指向大小 `1..10485760` bytes 的 JSON object。
  - missing、empty、oversize、non-object、malformed 均抛 `ValueError("TIER_CLI_REQUEST_INVALID")` 或 JSON decode error。
- `command_request(args: argparse.Namespace) -> tuple[str, str, dict[str, Any] | None]`
  - 只返回既有 `/health`、`/runtime`、`/debug`、`/stats`、`/call`、`/reset`、`/reload`、`/backend/probe` operation。
  - `stats` query key 保持 Tier HTTP Contract 的 `task_id`、`task_key` 命名。
- `response_exit_code(status: int, payload: dict[str, Any]) -> int`
  - 成功 `0`；参数/validation `2`；transport/transient `3`；not found `4`；conflict/其他失败 `5`。
- `write_result(output_format: str, payload: dict[str, Any], stream: Any) -> None`
  - `json` 输出单个 JSON object；`human` 输出稳定 key/value 行。
- `main(argv: list[str] | None=None) -> int`
  - parse -> operation mapping -> `TierClient.proxy_request()` -> render -> exit mapping。
  - 参数/文件错误返回 `2`；transport error 返回 `3`；不得 silent success。

## 3. State、IO 与安全

- 允许读取显式 `--request` 文件、发起一个 Tier HTTP request、写 stdout/stderr。
- 不写 Tier 配置、runtime state 或 stats authority。
- `--server-url` 不允许在输出中泄露 credential；底层 `TierClient` 负责 URL Contract。

## 4. Module Test 数据与 Oracle

- 使用 case-local `data/input/argv.json` 驱动真实 `python -m llm_tier.cli` subprocess。
- 使用 loopback Tier Server replay 响应，不启动完整 Tier Subsystem。
- `data/authority/cli/invoke_request.json` 保存 invoke 的真实 request object。
- Oracle 同时校验 exit code、stdout/stderr、JSON subset、HTTP method/path/body、listener cleanup。
- 禁止以 `python -c print(marker)` 或直接调用 `main()` 替代 subprocess public boundary。
