# LLMTier 验证域总索引（docs/70_verification）

> STD 使用入口：[项目采用说明与标准导航](../../README.md#std-entry)。本目录按 **测试阶段** 组织
> （STD `0.1.0-draft.72` / `f073396`，见 `docs/std.lock.json`；布局依据 STD
> `docs/repository-layout.md` §4「测试authority / 按测试类型保存报告」与 §4.1.2 文件级示例）。

本目录承载 LLMTier 的**测试方案（scheme）**、**用例详细设计（case）**、**测试计划（plan）** 与
**测试资产（asset）** 四类文档。可执行测试与运行证据按测试类型共置于 `tests/` 侧，本目录不维护
报告副本（见下文「报告落位」）。

## 1. 阶段 → 文档落位

每个测试阶段一个子目录；该阶段内固定四类文档：方案、用例、计划、资产。

| 阶段目录 | 测试阶段 | Case 前缀 | 方案（scheme，1 份） | 用例（case，一 Case 一文档） | 计划（plan，1 份） | 资产（asset） |
|---|---|---|---|---|---|---|
| `unit/` | 单元测试 | `UT` | `unit/llmtier-unit-test-scheme.md` | `unit/cases/UT-<OBJ>-<NNN>.md` | `unit/llmtier-unit-test-plan.md` | `unit/assets/llmtier-unit-fakes.md` |
| `module/` | 模块测试 | `MT` | `module/llmtier-module-test-scheme.md` | `module/cases/MT-<OBJ>-<NNN>.md`（37 份，待建） | `module/llmtier-module-test-plan.md` | 复用 `unit/assets/llmtier-unit-fakes.md`（见 §3） |
| `subsystem/` | 子系统/集成测试 | `IT` | N/A（本项目未设独立子系统阶段，见 §3） | — | — | — |
| `system/` | 系统测试 | `ST` | `system/llmtier-system-test-scheme.md` | `system/cases/<ID 小写>.md` | `system/llmtier-system-test-plan.md` | 暂无（系统层资产由 `tests/system/conftest.py` 承载，见 §3） |

- 命名规则：方案/计划/资产文档沿用项目既有 document-id 命名；**用例文档文件名＝Case ID 全小写**（`<ID 小写>.md`），
  Document ID ＝ Case ID。每份文档配同名 `<文件名>.metadata.json`。
- 旧 `schemes/`、`plans/`、`assets/`、`specifications/` 扁平目录已被本布局取代（迁移记录见
  `docs/98_migration/llmtier-case-id-migration.md`）。
- 方案/用例/计划/资产的分工与状态语义见各阶段方案 §「模板定位」：方案持有**用例状态**
  （Designed/Gap/Tailored-N/A），用例文档持有**实现状态**（Planned/Implemented），执行状态与
  Verdict 只在 Run 报告。

## 2. Case ID 前缀表（STD `software-object-identifiers.md` §2）

Case ID 格式 **`<阶段前缀>-<对象>-<NNN>`**：

| 测试阶段 | 阶段前缀 | 示例 |
|---|---|---|
| 单元测试 | `UT` | `UT-API-001` |
| 模块测试 | `MT` | `MT-API-001` |
| 子系统/集成测试 | `IT` | N/A |
| 系统测试 | `ST` | `ST-RESP-001` |

- `<对象>` 为被测对象命名空间 token（正式短名或对象 ID），项目选定一种后一致使用并保持可反查映射；
  系统层对象 token 映射见各阶段方案 §3 清单与 `docs/98_migration/llmtier-case-id-migration.md`。
- `<NNN>` 为**三位十进制**序号，在所属阶段前缀内从 `001` 顺序追加；Case ID 稳定且唯一，删除保留
  Retired 记录、编号不复用，前缀不因对象迁移或重命名改变。
- 阶段前缀唯一确定，不与其他命名空间前缀（`F`/`IF`/`VRC`/`RISK`/`CON`）复用或只靠补零区分。

## 3. 本项目实际范围（N/A 声明）

- **module（`MT`）**：**已设**。本项目按用户授权合并 M001-M008 为一份项目级模块测试方案/计划（LT-TL-025，与单元层 LT-TL-023 同一处理方式），目录 `module/`。模块层测试**整模块组装**（内部单元真实、仅模块边界外协作者用替身，状态只经公开入口，主要手段＝公开入口 + 边界替身），分母＝**四层**（方案 §3：①接口行为 20 ＋ ②分支 36 ＋ ③组合 10 ＋ ④迁移 14 ＝ 80 条），展开为 **57 个 `MT-*` Case**；8 个模块设计 §14 / ISD §9.1 的 33 个验证项只作追溯、不作分母。模块层测试资产**复用** `unit/assets/llmtier-unit-fakes.md`（同一 `FakeAdapter`/`AppFixture`），不另立资产；`module/cases/` 的 57 份 Case 文档为下一交付步建立。**模块层 PASS 不关闭上层**：系统层组合目标（wire/E2E/真实 provider 协议）独立承接。
- **subsystem（`IT`）**：**N/A**。本项目未单独设立子系统/集成测试阶段；子系统集成语义由系统层
  `ST-*`（`tests/system/`）承接，不另建目录。
- **system 资产**：系统层测试资产（`LLMTierInstance` / `provider_endpoint_*` / B 类 fixture）以
  `tests/system/conftest.py` 承载，尚未落为 `tests.asset-design` 文档；在建立前
  `system/assets/` 为空、不创建（仅创建实际需要的目录）。

## 4. 报告落位（不在本目录维护副本）

正式报告与运行证据按测试类型共置于 `tests/` 侧（STD `repository-layout.md` §4.1.1）：

- 系统测试：`tests/system/reports/<run-id>/`（如 `2026-09-30/system-test-report.md`）。
- 单元测试：`tests/unit/reports/<run-id>/`（脚本 `tests/unit/cases/`）。
- 模块测试：`tests/module/reports/<run-id>/`（脚本 `tests/module/cases/`；首次执行时建立）。
- UI（系统层真实浏览器）：`tests/system/reports/<run-id>/`。

本目录只引用报告，不复制原始结果。历史 Run 报告保留原 Case ID 键（迁移不改写既有 Run 证据）。
