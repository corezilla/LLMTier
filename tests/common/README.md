# `tests/common/` — 跨测试共享的 harness / drivers / oracles / 替身

> STD `78876c9`（`docs/repository-layout.md` §4.1.x）。

| 路径 | 用途 |
|---|---|
| `harness/run_harness.sh` | 共享运行 harness：分配 Run 目录、pin 元数据、跑 pytest、映射退出码、生成 per-Case manifest |
| `harness/runner_unit.sh` | 单元 runner（`tests/unit/cases/` → `tests/unit/reports/`） |
| `harness/runner_system_a.sh` | 系统 A 类 runner（`-m api_a`，直连 m5air） |
| `harness/runner_system_b.sh` | 系统 B 类 runner（`-m api_b`，临时实例） |
| `drivers/browser_driver.mjs` | 真实浏览器 CDP driver（headless Chrome，UI Case） |
| `drivers/ui_support.py` | UI driver 的 node/浏览器解析与 `run_scenario` 辅助 |
| `fakes.py` | 跨模块共享单元替身（`AppFixture` / `FakeAdapter` / capability 构造器） |

run harness 见 `harness/run_harness.sh` 头部注释；报告按 Run ID 分目录，见各层测试计划 §7。
