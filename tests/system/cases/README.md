# LLMTier 系统可执行用例 — `tests/system/cases/`

> STD `78876c9`（`docs/repository-layout.md` §4.1.x）：系统层可执行脚本平铺于此，
> **文件名＝Case ID**（`ST-<对象>-<NNN>.py`）。legacy `tests/system/st_*.py` 家族已迁移/退役（不再存在）；映射见方案 §4。

设计清单（唯一登记）见 [`llmtier-system-test-scheme.md`](../../../docs/70_verification/system/llmtier-system-test-scheme.md) §3；
逐 Case 详细设计见 [`docs/70_verification/system/cases/`](../../../docs/70_verification/system/cases/)。
`docs/…/cases/ST-XXX-001.md` → 本目录 `ST-XXX-001.py`。

## 分类与运行

| 类 | marker | collected | 执行环境 |
|---|---|---|---|
| A | `@pytest.mark.api_a` | 105 | 直连 m5air (`192.168.1.9:8181`) 现有实例（读 / 无状态写） |
| B | `@pytest.mark.api_b` | 76 | 临时 SQLite + 临时端口 LLMTier 实例（CRUD / 注入 / absence 扫描），teardown 清理 |
| UI | `@pytest.mark.ui` | 10 | 真实浏览器 headless Chrome over CDP，hermetic 临时实例 + LAN fake provider |

`conftest.py` / `constants.py` 位于上一层 `tests/system/`；A/B 共用同一套 fixtures
（`_b` suffix），按 marker 分流。

## 文件头部依赖（TS-002 / TS-003）

每个 `ST-*.py` 文件头部写明依赖：

```python
"""Case ID: <ID>

Endpoint: <METHOD> <PATH>
Upstream Provider: <id>（如适用）
Model: <backend_model>（如适用）
Auth: Bearer <token> | LAN trust
"""
```

TS-003：provider **endpoint** 必须是 LAN IP（192.168.x.x），禁止 127.0.0.1 / localhost。

## 运行

```bash
bash tests/common/harness/runner_system_a.sh          # A 类（需 m5air）
bash tests/common/harness/runner_system_b.sh          # B 类（hermetic）
PYTHONPATH=src python3 -m pytest tests/system/cases -m ui -q   # UI 类
bash tools/run_ui_tests.sh                            # UI 类包装入口
```

报告落在 `tests/system/reports/<run-id>/`（见系统测试计划 §7）。
