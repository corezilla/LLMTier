# LLMTier 单元可执行用例 — `tests/unit/cases/`

> STD `78876c9`（`docs/repository-layout.md` §4.1.x）：单元层可执行脚本平铺于此，
> **文件名＝Case ID**（`UT-<对象>-<NNN>.py`）。

设计清单（唯一登记）见 [`llmtier-unit-test-scheme.md`](../../../docs/70_verification/unit/llmtier-unit-test-scheme.md) §3；
逐 Case 详细设计见 [`docs/70_verification/unit/cases/`](../../../docs/70_verification/unit/cases/)。
`docs/…/cases/UT-XXX-001.md` → 本目录 `UT-XXX-001.py`。

## 约定

- 一个 Case 的断言**物理上只落一个** Case 文件（文件名＝Case ID）。当同一断言被多个
  Case 复用时（例如 `UT-API-001` 与 `UT-MGMT-005` 共享 `test_probe_persists`），测试
  函数只在其**主 Case** 文件中被收集，其余 Case 的 §7 文档指向主 Case 文件。
- 跨模块共享替身（`AppFixture` / `FakeAdapter` 等）位于 [`tests/common/fakes.py`](../../common/fakes.py)；
  Case 专属辅助放 `tests/unit/cases/support/`。

## 运行

```bash
PYTHONPATH=src:tools python3 -m pytest tests/unit/cases -q            # 全量（426）
bash tests/common/harness/runner_unit.sh                              # 带报告入口
PYTHONPATH=src python3 -m pytest tests/unit/cases -k UT-UTIL -q       # 模块切片
```

报告落在 `tests/unit/reports/<run-id>/`（见单元测试计划 §7）。
