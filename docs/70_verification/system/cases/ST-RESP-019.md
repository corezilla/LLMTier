<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-RESP-019 — 全部候选不健康

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-RESP-019` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-RESP-019.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-RESP-019` / 系统设计 §8 Responses 接口 / `VRC-INF-004` / recovery / P1（[方案清单 `ST-RESP-019`](../llmtier-system-test-scheme.md)）；机制 `T-QUEUE`。
- **测试方法（§2.2 方法表行）**：故障注入（全部候选不健康）+ 复位阶梯
- 要测什么（责任展开）：`POST /v1/responses` 全部候选不健康：`503 model_unavailable`（`retryable=true`），无上游调用（自动化入口 `ST-RESP-019.py`）。service-level 存在且有候选 deployment，但没有任何 `health=="healthy"` 候选时，`Router.admit` 在 dispatch 前拒绝。
  错误目录 `ERR-MODEL-UNAVAIL` → wire `code=model_unavailable`；实现 `src/inference/routing.py`（`healthy=[c for c in candidates if c.health=="healthy"]; if not healthy: raise ApiError(503, "model_unavailable", "All configured backends are unhealthy", retryable=True)`）。
- 明确不测什么 / 失败含义：不测"无候选"（`404 model_not_found`，ST-RESP-005）；不测准入饱和 `429`（ST-RESP-020）；不测真实上游故障（ST-RESP-022/23）；不测模型答案。失败含义＝路由可用性契约破坏。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `POST /v1/responses`（`data`）与探测 `POST /v1/probes`（`admin`）。

```text
POST /v1/responses          Authorization: Bearer dev-data
POST /v1/probes             Authorization: Bearer dev-admin
```

- 初态构造（经公开入口）：**环境 B**（临时 LLMTier 实例）。需一个**专属**实例（不与共享 `llmtier_b` 混用，避免污染其它 case 的健康状态）：以 `_baseline_settings` 变体启动，其 `prov_b.endpoint` 指向一个**语法合法但不可达的 LAN 地址**（如 `http://192.168.1.254:9/v1`；TS-003 要求上游 endpoint 为 LAN IP）。初始状态 = 1 provider / 1 deployment / 7 tier，且该 deployment 尚未被 probe 为 healthy。
- Fixture / 向量及版本：`LLMTierInstance`；探测请求与被测请求向量，随 Run manifest 存档。
- 依赖的测试资产（tests.asset-design 文档）：B 类 fixture `LLMTierInstance`；TS-003 LAN endpoint。

## 3. 输入构造

- 逐参数输入构造：两步。

构造"不健康"：先以 admin 触发探测（`endpoint` 不可达 → `unhealthy`）：

```json
{"deployment_id": "depl_b", "confirm_external_call": true}
```

被测请求：

```json
{"model": "Senior", "input": [{"role": "user", "content": "hi"}], "stream": true, "store": false}
```

- 边界/非法取值及理由：`Senior` 的 `deployment_ids` 指向 `depl_b`，故必然路由到该唯一（不健康）候选；`POST /v1/probes` 的 body 键集必须恰为 `{deployment_id, confirm_external_call}`；探测对不可达 LAN endpoint 返回 `status=="unhealthy"` 并写库。
- 规模 / 时间域：一次探测 + 一次被测请求；探测对不可达地址的时延受控。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | （fixture 前置）启动专属 `LLMTierInstance`，轮询 `/healthz` 200；**不**断言 `depl_b` healthy | 实例就绪 |
| 2 | `POST /v1/probes`（`admin`） | 200 且 `status=="unhealthy"`（证明健康状态已被置为不健康） |
| 3 | `POST /v1/responses`（上表 body，`data`） | `status_code == 503` |
| 4 | 解析 `error` | `code=="model_unavailable"`、`type=="server_error"`、`retryable is True`、`param is None`，键集恰 5 键 |
| 5 | 交叉核对 | 无上游调用（trace/runtime 无该次 upstream_started），失败在 `admit` 内 |

- 重点关注步骤：① **区分"无候选"与"有不健康候选"**——本 case 必须让 `candidates()` 非空（deployment/provider 均 enabled）但 `health != healthy`，否则会得到 `404 model_not_found`；② **`retryable=true`**——可用性类错误；③ **拒绝在 dispatch 前**（`INV-5`）；④ **专属实例**——避免污染共享实例的健康状态；⑤ **自动化入口**——`ST-RESP-019.py` 与"不可达 LAN endpoint"fixture（`llmtier_b_unhealthy`）已实现。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：OpenAPI `ErrorEnvelope`/`ErrorDetail` + 系统设计 §7.8 `ERR-MODEL-UNAVAIL`（不依赖实现答案）。**判据语义以设计验证项 `VRC-INF-004` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：探测 `POST /v1/probes` → 200，`status="unhealthy"`；被测 HTTP `503`；`Content-Type: application/json`；`{"error":{"message":"All configured backends are unhealthy","type":"server_error","code":"model_unavailable","param":null,"retryable":true}}`；无 SSE。

## 6. 错误路径、副作用与清理

- 错误出口与表现：候选存在但全不健康 → `503 model_unavailable`（`retryable=true`），可观察且非 SSE。
- 副作用断言与清理：结束可由 fixture `stop()` 销毁专属实例；若复用共享实例则必须 `POST /v1/probes` 使 `depl_b` 恢复 `healthy`（或销毁实例），不得把不健康状态留给其它 case。离开前确认无残留不健康候选/临时进程。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：[`tests/system/cases/ST-RESP-019.py`](../../../../tests/system/cases/ST-RESP-019.py)（已实现；依赖"不可达 LAN endpoint"fixture `llmtier_b_unhealthy`）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/system/cases/ST-RESP-019.py -q`。
- 实现状态：Implemented；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：探测置 `unhealthy` 成功 + 后续 `503` + `model_unavailable` + `type=server_error` + `retryable=true` + 非 SSE。
- FAIL：得到 `404 model_not_found`（候选为空，构造错）或 `200`；code/type/retryable 错。
- BLOCKED：测试代码/fixture 不可实现（无法稳定构造不健康候选）。
- SKIP：B 类临时实例不可用、无可用 LAN IP 构造不可达 endpoint（TS-003）。
- INVALID：以 mock/`127.0.0.1` 上游冒充真实路径，或未真正置不健康却按行为判定。
- NOT_RUN：本 Case 有实现（`ST-RESP-019.py`），未执行记 `NOT_RUN`。

**证据与 Run**：保存探测请求/响应（`status=unhealthy`）、被测请求与原始 `503` 信封、健康状态证据、发出命令、exit code、环境快照（本 case `environment:"b"`）。

**依赖**：B 类 fixture `LLMTierInstance`；TS-003 LAN endpoint；`POST /v1/probes`（ST-PROBE-001/02）；实现 `src/inference/routing.py`；错误目录 `ERR-MODEL-UNAVAIL`（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md) §7.8）。**不依赖**其它 Case。
