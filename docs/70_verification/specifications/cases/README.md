# LLMTier Case 详细设计文档目录

本目录承载 LLMTier 的**逐 Case 详细设计文档**（case design）。它是文档链的中间层：

```
测试设计（llmtier-api-test-specification.md：Case 清单 + 共同机制 + 环境）
        ↓
case 设计（本目录：一 Case 一文件，承载输入/执行/Oracle/判定/证据/清理）
        ↓
case 脚本（tests/system/api_test_v03/at_*.py 与 tools/inference_smoke.py 等可执行断言）
```

## 命名规则（固定，所有 Case 一律遵循）

- 目录：`docs/70_verification/specifications/cases/`
- 文件名：`cases/<lowercased-case-id>.md`，即 **Case ID 全小写**，后缀 `.md`。
- 示例：
  - `DP-RESP-01` → `cases/dp-resp-01.md`
  - `ADM-SL-02b` → `cases/adm-sl-02b.md`
  - `OBS-DEPL-04` → `cases/obs-depl-04.md`
- **一 Case 一文件**，文件名与 Case ID 唯一对应；Case ID 以测试设计 §3.2 权威清单为准，本目录不得引入清单外的 ID。

## 模板契约（固定 12 字段）

每份 case 文档**必须齐备且按固定顺序**填写测试设计 §3.3 的 12 个字段：

1. Case ID
2. 标题
3. 目的（被测契约）
4. 前置与环境
5. 输入与构造
6. 执行过程（逐步调用）
7. 重点关注步骤
8. 期望结果与独立 Oracle
9. 判定（Pass/Fail/Blocked/Invalid）
10. 证据与 Run
11. 清理与复位
12. 依赖

字段缺失视为设计状态未达 `已写`。case 文档**引用**测试设计 §2（环境与前置）、§4（共同机制）、§9（判定）、§10（证据），不重复其定义。样例见 [`dp-resp-01.md`](./dp-resp-01.md)。

## 状态回填

case 文档建立并满足上述字段要求后，需把测试设计 §3.2 该 Case 的 `设计状态` 由 `待写` 更新为 `已写`（并同步 §3.4 索引）。

## 与报告分离

设计写在本目录；Run 证据写在 `tests/system/reports/<date>/`（测试设计 §10），两者不混写。
