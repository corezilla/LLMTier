<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-RESP-024 — provider 凭据缺失

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-RESP-024` |
| Document Version | `0.1.0-draft.4` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-RESP-024.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-RESP-024` / 系统设计 §8 Responses 接口 / `VRC-INF-001` / recovery / P1（[方案清单 `ST-RESP-024`](../llmtier-system-test-scheme.md)）。
- **测试方法（§2.2 方法表行）**：故障注入（provider 凭据缺失）+ 复位阶梯
- 要测什么（责任展开）：`POST /v1/responses` provider `secret_ref` 不可解析：`503 provider_secret_unavailable`（自动化入口 `ST-RESP-024.py`）。所选 provider 的 `secret_ref` 指向缺失/不可读的凭据时，适配层在建立上游请求前抛 `503 provider_secret_unavailable`。
  需求 `R-INF-05`；错误目录 `ERR-PROVIDER-SECRET` → wire `code=provider_secret_unavailable`；实现 `src/inference/providers/openai.py`（`_secret()`：`file:` 读取 `OSError` → `ApiError(503, "provider_secret_unavailable", "Provider secret file is unreadable")`；
  非 `env:`/`file:` → "Unsupported provider secret reference"）。
- 明确不测什么 / 失败含义：不测 `secret_ref` 格式校验的 400 `invalid_request`（`registry._validate_secret_ref`，属写侧管理契约，见 ST-PROV-012）；不测 401/403 上游鉴权失败；不测上游不可达（`provider_unavailable`）；不测答案。失败含义＝provider 凭据可用性契约破坏。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `POST /v1/responses`（`data`）与 `GET/PATCH /v1/providers/prov_b`（`admin`）。

```text
POST  /v1/responses                 Authorization: Bearer dev-data
GET   /v1/providers/prov_b          Authorization: Bearer dev-admin
PATCH /v1/providers/prov_b          Authorization: Bearer dev-admin
```

- 初态构造（经公开入口）：**环境 B**（临时 LLMTier 实例）。建议专属实例以免改动共享 `prov_b`。`_baseline_settings`：`prov_b` + `depl_b` + 7 tier；`depl_b` 已 probe `healthy`（此时 `secret_ref=None`）。初始状态无注入项。
- Fixture / 向量及版本：`LLMTierInstance`、`admin_client_b`、`api_client_b`；`secret_ref` 改值与恢复向量，随 Run manifest 存档。
- 依赖的测试资产（tests.asset-design 文档）：B 类 fixture `LLMTierInstance` / `admin_client_b` / `api_client_b`。

## 3. 输入构造

- 逐参数输入构造：先以 admin PATCH 把 `prov_b.secret_ref` 改为一个**语法合法但文件不存在**的 `file:` 引用（通过 `_validate_secret_ref`，但读取时失败），再发被测请求。

改 `secret_ref`（需 `If-Match`，先 `GET /v1/providers/prov_b` 取 `ETag`）：

```json
{"secret_ref": "file:/nonexistent/llmtier-test/secret.txt"}
```

> **`If-Match` 取值**：必须在发送 `PATCH` 前先 `GET /v1/providers/prov_b`，取响应头返回的**当前** `ETag`（形如 `"prov_b.v<N>"`，含双引号）作为 `If-Match` 值，**不得硬编码**；teardown 恢复时同样须重新 `GET` 取新 `ETag`。

被测请求：

```json
{"model": "Senior", "input": [{"role": "user", "content": "hi"}], "stream": true, "store": false}
```

- 边界/非法取值及理由：`file:` 前缀必须保留（否则 PATCH 先被 `_validate_secret_ref` 拒为 `400 invalid_request,param=secret_ref`，观测不到 503）；`ETag` 格式 `"<id>.v<N>"`（含双引号）；只改 `secret_ref` 一个字段。
- 规模 / 时间域：1 次 GET + 1 次 PATCH + 1 次被测请求 + 1 次恢复 PATCH；读取凭据在 `urlopen` 前失败。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | （fixture 前置）启动实例并 probe `depl_b` → `healthy`；确认无启用注入 | 实例就绪 |
| 2 | `GET /v1/providers/prov_b`（`admin`） | 记录当前 `ETag` 与原始 `secret_ref`（用于 teardown） |
| 3 | `PATCH /v1/providers/prov_b`（`If-Match`，body 改 `secret_ref` 为不存在的 `file:`） | 200，且响应 `has_secret` 为真 |
| 4 | `POST /v1/responses`（上表 body） | 普通 JSON 错误信封（非 SSE） |
| 5 | 断言 `status_code == 503`；解析 `error` | `code=="provider_secret_unavailable"`、`type=="server_error"`、`retryable is False`、`param is None`，键集恰 5 键 |
| 6 | （teardown，`finally`）`PATCH /v1/providers/prov_b` 用新 `ETag` 将 `secret_ref` 恢复为原始值 → 断言 200；`GET` 校验 | `has_secret` 与原始一致 |

- 重点关注步骤：① **格式校验 vs 读取失败**——`file:` 通过写侧格式校验，失败发生在适配层读取凭据；② **拒绝位置**——在 `urlopen` 上游请求前抛错；③ **`retryable=false`**——凭据缺失不可重试（与 `provider_unavailable` 的 `true` 区分）；④ **信封 identity**（5 键、`type=server_error`）；⑤ **teardown 必恢复 `secret_ref`**，且必须重新 `GET` 取新 `ETag` 再 PATCH（412 后不覆盖）；⑥ **自动化入口**——`ST-RESP-024.py` 已实现。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：OpenAPI `ErrorEnvelope`/`ErrorDetail` + 系统设计 §7.8 `ERR-PROVIDER-SECRET`（不依赖实现答案）。**判据语义以设计验证项 `VRC-INF-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：PATCH `200`，`has_secret=true`；非 `file:`/`env:` 的引用才会 400（本 case 不用）；被测 HTTP `503`；`Content-Type: application/json`；`{"error":{"message":"Provider secret file is unreadable","type":"server_error","code":"provider_secret_unavailable","param":null,"retryable":false}}`；无 SSE；teardown `secret_ref` 恢复原值，`GET` 校验。

## 6. 错误路径、副作用与清理

- 错误出口与表现：`secret_ref` 不可读 → `503 provider_secret_unavailable`（`retryable=false`），非 SSE。
- 副作用断言与清理：**必须 teardown（`finally`）**——将 `prov_b.secret_ref` 恢复为原值（新 `ETag` + PATCH），`GET` 校验；不删除 `prov_b`/`depl_b`；无注入。专属实例按计划整班销毁。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：[`tests/system/cases/ST-RESP-024.py`](../../../../tests/system/cases/ST-RESP-024.py)（已实现）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/system/cases/ST-RESP-024.py -q`。
- 实现状态：Implemented；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：PATCH 200 且引用改成功；被测 `503` + `provider_secret_unavailable` + `type=server_error` + `retryable=false` + 非 SSE；teardown 恢复成功。
- FAIL：status/code/retryable 错、PATCH 被拒（构造错）、teardown 未恢复。
- BLOCKED：PATCH/If-Match 流程不可用、无法构造不可读 secret。
- SKIP：B 类临时实例不可用。
- INVALID：以 mock/替代路径冒充真实路径、或凭据未真正缺失却按行为判定。
- NOT_RUN：本 Case 有实现（`ST-RESP-024.py`），未执行记 `NOT_RUN`。

**证据与 Run**：保存原始/新 `secret_ref` 与 `ETag`、PATCH 请求响应、被测请求与原始 503 信封、teardown 恢复请求与 `GET` 校验、发出命令、exit code、环境快照。**脱敏**：不得记录任何真实 secret 值（本 case `environment:"b"`）。

**依赖**：B 类 fixture `LLMTierInstance` / `admin_client_b` / `api_client_b`；`PATCH /v1/providers/{id}`（ST-PROV-005/06）；实现 `src/inference/providers/openai.py`（`_secret`）、`src/management/registry.py`（`_validate_secret_ref`）；错误目录 `ERR-PROVIDER-SECRET`（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md) §7.8）。与 ST-PROV-012（`secret_ref` 格式）区分。
