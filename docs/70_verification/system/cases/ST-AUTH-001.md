<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-AUTH-001 — Data 端点 LAN trust 无 token

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-AUTH-001` |
| Document Version | `0.1.0-draft.3` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-10-01` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-AUTH-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`ST-AUTH-001`）；责任摘要、分类与优先级以 [系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-AUTH-001` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-AUTH-001` / 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） / `VRC-API-002` / `security` / `P0`
- **测试方法（§1.5 方法表行）**：鉴权/授权/脱敏冒烟 + 角色隔离
- 方案清单登记：`ST-AUTH-001`（与 §3.2 权威清单一致；本文件名 `st-auth-001.md`，唯一对应）。
- 要测什么（责任展开）：`GET /v1/models` 在受信 LAN 来源且**不带** `Authorization` 头时被无条件受理，返回 200 + 合法模型清单（LAN trust 免登录）。
- 明确不测什么 / 失败含义：不证明 任何**凭据**路径——不证明错误 bearer 被拒（ST-AUTH-002）、空 bearer 被拒（ST-AUTH-006）、非受信来源缺凭据→401 `authentication_required`（ST-AUTH-010）、admin 端点同样受 LAN trust（ST-AUTH-004）、公共端点无需 token（ST-AUTH-005）、data/admin 角色隔离（ST-AUTH-003/ST-AUTH-008）、鉴权未配置→503（ST-AUTH-007）；也不证明恒定时间比较（`T-TRUST-BEARER`）与错误信封（负向属 ST-AUTH-002/06/10）。特别地，本 case **不**证明存在 `LLMTIER_TRUSTED_LAN_MODE` 环境门控：源码 [auth.py](../../../../src/http_api/auth.py) **不读取**该变量，LAN 免登录是**无条件**的（测试设计 §4.2；[conftest.py](../../../../tests/system/conftest.py) 仍设该 env 仅为对齐文档意图）。

**目的（被测契约）**：验证 access-trust 机制的 **LAN trust 免登录路径**。被测端点/规则：`GET /v1/models`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listModels`）；入口 [`_auth()`](../../../../src/http_api/app.py) 在请求**无 `Authorization` 头**且 `client_address` 属于 loopback 或 RFC1918 受信私网（`10/8`、`172.16/12`、`192.168/16`、`fc00::/7`）时，经 [`unauthenticated_principal()`](../../../../src/http_api/auth.py) 返回共享主体 `Principal("trusted-lan-consumer","data")`，端点因而在**零凭据**下返回 200。**角色澄清**：代码以 `_auth()`（默认 role=`data`）守护 `/v1/models`，而 §3.2 把本 Case 角色记为 `none`（LAN-trust 免 token）；二者不冲突——本 case 的**wire 契约**是"无 token + 受信 LAN → 200"，与 role 标签无关，不据此断言任何角色隔离（角色负向属 ST-AUTH-003/08）。设计验证项 `VRC-API-002`；机制 `T-TRUST-LAN`（需求 `R-TRUST-01`；见 [access-trust 机制 §5.1/§7/§8 INV-5](../../../20_system_design/mechanisms/access-trust.md)）；成功响应头 `X-Request-ID`，成功体 `ModelList`。**不证明什么**：不证明任何**凭据**路径——不证明错误 bearer 被拒（ST-AUTH-002）、空 bearer 被拒（ST-AUTH-006）、非受信来源缺凭据→401 `authentication_required`（ST-AUTH-010）、admin 端点同样受 LAN trust（ST-AUTH-004）、公共端点无需 token（ST-AUTH-005）、data/admin 角色隔离（ST-AUTH-003/ST-AUTH-008）、鉴权未配置→503（ST-AUTH-007）；也不证明恒定时间比较（`T-TRUST-BEARER`）与错误信封（负向属 ST-AUTH-002/06/10）。特别地，本 case **不**证明存在 `LLMTIER_TRUSTED_LAN_MODE` 环境门控：源码 [auth.py](../../../../src/http_api/auth.py) **不读取**该变量，LAN 免登录是**无条件**的（测试设计 §4.2；[conftest.py](../../../../tests/system/conftest.py) 仍设该 env 仅为对齐文档意图）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `none`（§3.2）/ `data`（入口 `_auth()` 默认）；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；**关键环境约束（TS-003）**：测试执行机必须位于 `192.168.x.x` RFC1918 LAN，其到 m5air 的源地址必须命中 `192.168.0.0/16`；若执行机处于非受信网段，本 case 会得到 401，**不可判 PASS**，须先修复网络前置。本 case **不复用** `api_client`/`admin_client` fixture（二者已注入 `Authorization`，会走凭据路径），使用独立 `httpx.Client`（无默认头）；初始状态=§2.3 A 类基线（3 provider / 4 deployment / 7 fixed tier）。

## 3. 输入构造

- **输入与构造**：固定请求（无请求体、无查询参数）：
  ```http
  GET /v1/models HTTP/1.1
  Host: 192.168.1.9:8181
  Accept: application/json
  ```
  构造点：**`Authorization` 头完全缺省**——既不是空串也不是 `Bearer `；任何存在值都会使 `unauthenticated_principal()` 立即返回 `None`（[auth.py](../../../../src/http_api/auth.py) `if headers.get("Authorization"): return None`）并转入 `authenticate()` 凭据路径。源地址固定为执行机到 m5air 可达的 LAN IP（`192.168.x.x`）。不注入故障；不构造非法输入。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. 建立独立客户端：`httpx.Client(base_url="http://192.168.1.9:8181", timeout=10.0)`，**不设 `Authorization`**（对应 [`ST-AUTH-001.py`](../../../../tests/system/cases/ST-AUTH-001.py) 的 `httpx.Client(base_url=...)`）。
  3. `resp = client.get("/v1/models")`；记录 status、headers、body。
  4. 断言 `resp.status_code == 200`（LAN trust 命中 ⇒ 未被 401/403）。
  5. 解析 body：断言 `object == "list"` 且 `data` 为非空数组；抽查至少一个元素的 `object=="model"`、`owned_by=="llmtier"`、`id:str`、`availability ∈ {available,degraded,unavailable}`；核对 `data` 长度与 `/readyz` 的 7 个 fixed tier 一致（m5air 基线）。
  6. （可选交叉核对）对同一 `GET /v1/models` 注入 `Authorization: Bearer dev-data` 再发一次，确认除请求头外 body 语义一致——佐证 LAN trust 与 data token 落到同一 handler（该次请求的通过不由本 case 断言）。

**重点关注步骤**：① **头缺省而非空值**——必须完全不发送 `Authorization`；`Bearer `（空 bearer）会因 `hmac.compare_digest("", configured)` 失败而 403（ST-AUTH-006），从而把本 case 误判 FAIL；② **来源受信**——200 成立的前提是 `client_address` 命中 loopback/RFC1918；断言前应确认执行机 LAN IP，非受信来源的 401 属环境前置不满足（SKIP），不是 ST-AUTH-001 的行为错误；③ **Oracle 是"trusted-LAN 规则"而非"auth 可用"**——只断言 200 不够，必须同时验证合法 `ModelList` body，排除把其它 200 当成功；④ **不得用带 token 的 fixture**——`api_client`/`admin_client` 已带 header，误用会把"data token 生效"当成"LAN trust 生效"，令断言失去意义；⑤ **不要声称 env 门控**——`LLMTIER_TRUSTED_LAN_MODE` 不被源码读取，本 case 不得断言"门控开启才 200"（现有 [`ST-AUTH-001.py`](../../../../tests/system/cases/ST-AUTH-001.py) 文件头注释称该 env"默认开启"属不准确表述，设计以源码行为为准）；⑥ 不在此 case 断言 401/403 负向（属 ST-AUTH-002/06/10）。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = access-trust 规则本身——"无 `Authorization` + 来源 ∈ 受信私网 ⇒ 共享 `data` 主体 ⇒ `GET /v1/models` 受理"，与 m5air 具体数据无关。
  - HTTP：`200`；响应头含 `X-Request-ID`（openapi `listModels` 200 header）。
  - body：`{"object":"list","data":[...]}`；`data` 为非空数组，元素满足 `Model` schema（`id`/`object=="model"`/`created`/`owned_by=="llmtier"`/`availability`/`capabilities`）。
  - m5air 基线：`data` 含 7 个 fixed tier（`Senior/Junior/Worker/Associate/Engineer/Executor/Embedding-v1`）。
  - 无错误信封：本 case 不应出现 `{"error":{...}}`。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` 且 body 满足 `object=="list"` + `data` 非空数组 + 元素 `Model` 关键字段（即"无 token + 受信 LAN → 受理且返回合法模型清单"）。
  - **FAIL**：返回 401/403/其它 status，或 body 非合法 `ModelList`（LAN trust 规则或模型清单契约不成立）；须给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（如独立无头客户端构造错、断言不可实现）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足，或执行机不在 `192.168.x` LAN 而无法制造受信来源——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或以**带 token** 的请求冒充 LAN trust——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：Case 已定义但本轮未执行（例如 suite 因 §2.1 失败整班 skip）。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——本 case 为只读 `GET`，无状态，不创建/修改/删除资源、不写 usage/账本。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存独立请求的原始命令、发送 headers 快照（证明**无** `Authorization`）、HTTP status/headers/body、执行机 LAN IP、exit code、`elapsed`、环境快照（`/healthz`/`/readyz`）；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查（m5air `/healthz`、`/readyz` 7 tier、双 OMLX、`provider_omlx_m5mac` secret）；执行机位于 `192.168.x` LAN（TS-003）；独立 `httpx` 无头客户端（不复用 `api_client`/`admin_client`）；m5air `GET /v1/models` 可用（该端点只读逻辑模型清单、不触上游；上游 OMLX 在线由 §2.1 就绪检查强制）；自动化入口 [`ST-AUTH-001.py`](../../../../tests/system/cases/ST-AUTH-001.py)。**不依赖**其它 Case；与 ST-AUTH-002/ST-AUTH-004/ST-AUTH-006/ST-AUTH-010 共享同一鉴权机制但各自独立执行、互不关闭。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
