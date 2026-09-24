<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **LLMTier** (4376 symbols, 5812 relationships, 107 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({search_query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/LLMTier/context` | Codebase overview, check index freshness |
| `gitnexus://repo/LLMTier/clusters` | All functional areas |
| `gitnexus://repo/LLMTier/processes` | All execution flows |
| `gitnexus://repo/LLMTier/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

<!-- std:start -->
## STD 项目规范（强制）

**必须先读**：[项目规范总索引](docs/00_management/standards/README.md)

本项目已采用 STD `0.1.0-draft.26`（见 `docs/std.lock.json`）。所有文档必须遵循 STD 模板。

### 项目规范索引

项目自定义规范位于 `docs/00_management/standards/`，包括：
- `testing-standard.md` — 测试规范（编写测试、PR review 前必读）

### 关键规则

1. **先读规范索引**：开始任务前先读 `docs/00_management/standards/README.md`
2. **遵循测试规范**（TS-003）：LLMTier 是 LAN 服务，测试的 provider endpoint 必须使用 LAN IP（192.168.1.x），禁止使用 127.0.0.1
3. **测试依赖必须写清**：测试文件头部必须写明依赖的服务地址、端口、模型
4. **所有测试通过才能提交**：`PYTHONPATH=src python3 -m pytest tests/ tests/system/st_*.py -q` 必须 221 pass

<!-- std:end -->

## m5air 部署（强制）

**m5air** (`192.168.1.9`) 是 LLMTier 生产环境。

**详细指南**：[m5air-deploy-guide.md](docs/80_operations/manuals/m5air-deploy-guide.md)

修改代码后：
1. `rsync` 同步文件到 m5air
2. kill 旧进程并重启（用 Python 3.14）
3. 验证 `curl http://localhost:8181/healthz`
