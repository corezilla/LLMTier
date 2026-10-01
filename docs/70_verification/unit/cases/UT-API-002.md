<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-API-002 — 访问信任与鉴权矩阵

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-API-002` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-10-01` |
| Template ID | `tests.unit-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/unit/cases/UT-API-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-API-002`）；责任摘要、分类与优先级以 [单元测试方案 §3](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [http-api-design.md](../../../40_module_design/http-api-design.md) §14 / ISD [http-api.isd.md](../../../50_implementation_design/http-api.isd.md) §9.1，设计验证项 `VRC-API-002`（固定版本 `http-api 0.1.0-draft.2`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `API`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-API-002` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-API-002` / `VRC-API-002`（http-api 模块设计 §14 / http-api-isd §9.1，http-api 0.1.0-draft.2） / `VRC-API-002` / security / P0（[方案清单 §3](../llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：鉴权/脱敏/注入边界冒烟（免登录/bearer/缺失配置/角色不可区分）
- 要测什么（责任展开）：被测：`src/http_api/auth.py::authenticate` 的免登录/凭据/角色/信任地址判定，及 data 凭据访问 admin 端点 403、不泄露存在性。
- 明确不测什么 / 失败含义：不测：真实 TLS/网关鉴权；不测上游。失败含义＝信任/鉴权语义实现错误（越权或误拒）。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/http_api/auth.py`（`authenticate`/`unauthenticated_principal`）；HTTP 层经 `app.py`

```text
authenticate(headers, config, remote_addr) -> Principal
```

- 初态构造（经公开入口）：`AppFixture` 空库；HTTP 层用 ENV-2 loopback 实例 + `handler_factory`
- Fixture / 向量及版本：`tests/unit/v03/fakes.py::AppFixture`
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库 / ENV-2 loopback 测试 HTTP 实例 / ENV-3 provider 进程内 fake（按 Case 需要，见 §4）
- 依赖的测试资产（tests.asset-design 文档）：无（真实实现）

## 3. 输入构造

- 逐参数输入构造：缺配置、缺/错 Bearer、data/admin/dev token、principal 头、loopback 与 LAN 信任地址
- 边界/非法取值及理由：loopback vs 私网地址边界；Bearer 显式提供时关闭 no-auth 路径
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单次判定，O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 无配置 → authenticate | 503 语义 |
| 2 | 缺 Bearer / 错 token | 401 / 403 |
| 3 | data/admin/dev token 与 principal 头 | Principal 角色 |
| 4 | loopback 与 192.168.x 地址信任 | 是否免登录（`patch.dict(clear=True)` 固定环境，防 `LLMTIER_DEV_MODE` 泄漏翻转） |
| 5 | 显式 Bearer 覆盖 no-auth 路径 | 按凭据判定（环境固定） |

> 说明：`test_trusted_lan_mode_accepts_private_addresses` 额外断言公网 IPv6（`2001:...`）与伪造 `X-Forwarded-For` 不授予 principal，`test_explicit_bearer_disables_no_auth_path` 亦在清空环境下运行。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：auth 规则 `RULE-API-ROLE/TRUST` + 系统 §11；独立期望为状态码/角色，不从被测复算。**判据语义以设计验证项 `VRC-API-002` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：缺配置 503；缺 Bearer 401；错 token 403；data 访问 admin → 403 且响应不泄露资源存在性；受信私网地址免登录

## 6. 错误路径、副作用与清理

- 错误出口与表现：无（各分支为互斥预期）
- 副作用断言与清理：无持久化副作用；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/v03/test_auth.py`（全部 10 个测试）（注意：本 Case 的测试函数当前按子句（test case method）映射；若与设计 VRC 不一致，以设计修订回溯后重裁）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/v03/test_auth.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/v03`）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。

