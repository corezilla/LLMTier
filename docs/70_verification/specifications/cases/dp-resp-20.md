<!-- STD_DOCUMENT_COVER_BEGIN -->
# DP-RESP-20 — 准入饱和 → 429

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `DP-RESP-20` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-09-29` |
| Template ID | `tests.system-test-design` |
| Template Version | `2.3.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/cases/dp-resp-20.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`DP-RESP-20` / 系统设计 §8 Responses 接口 / `VRC-INF-004` / concurrency / P1（[方案清单 `DP-RESP-20`](../../schemes/llmtier-system-test-scheme.md)）；机制 `T-QUEUE`。
- 要测什么（责任展开）：`POST /v1/responses` 准入饱和：`429 rate_limit_exceeded` 且带 `Retry-After`（**MISSING** 自动化）。并发超过 `depl_b` 的运行时并发许可与队列上限（队列 32）时，`Router.admit` 拒绝并返回稳定 `429` 与 `Retry-After`。需求 `R-INF-05`；错误目录 `ERR-RATE-LIMIT` → wire `code=rate_limit_exceeded`；实现 `src/inference/routing.py`（队列满 `len(self._queues[level_id]) >= 32` → `ApiError(429, "rate_limit_exceeded", "Service-level queue is full", retryable=True, headers={"Retry-After":"30"})`；等待超时 → `Retry-After:"1"`）。
- 明确不测什么 / 失败含义：不测 `model_unavailable`（DP-RESP-19）；不测超时预算的 ms 级时点（不设 SLO）；不测 exactly-once/重试语义。失败含义＝准入/排队契约破坏。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `POST /v1/responses`（`data`）与诊断注入 `PATCH /v1/deployments/depl_b/diagnostics`（`admin`）。

```text
POST /v1/responses                                  Authorization: Bearer dev-data
PATCH /v1/deployments/depl_b/diagnostics            Authorization: Bearer dev-admin
```

- 初态构造（经公开入口）：**环境 B**（临时 LLMTier 实例）。建议使用专属实例，避免与其它 case 的并发/注入互相干扰。`_baseline_settings`：`prov_b` + `depl_b` + 7 tier；`depl_b` 的运行时 `max_in_flight` 默认 1，provider 并发默认 1。初始状态无启用注入项。
- Fixture / 向量及版本：`LLMTierInstance`、`admin_client_b`、`api_client_b`；占槽注入与 `N` 个并发请求向量，随 Run manifest 存档。
- 依赖的测试资产（tests.asset-design 文档）：B 类 fixture `LLMTierInstance` / `admin_client_b` / `api_client_b`。

## 3. 输入构造

- 逐参数输入构造：以 `delay` 注入占用许可（`delay` 前置阶段在 `admit` 上下文内 sleep，占住唯一并发槽），再并发灌入请求。

占槽注入（`PATCH /v1/deployments/depl_b/diagnostics`，`admin`）：

```json
{"items": [{"type": "delay", "config": {"delay_ms": 60000}, "enabled": true}]}
```

被测并发：以同一 `data` token 同时发起 `N`（建议 `N >= 34`）个相同请求：

```json
{"model": "Senior", "input": [{"role": "user", "content": "hi"}], "stream": true, "store": false}
```

- 边界/非法取值及理由：`delay_ms` 取上限 `60000`（`_RANGES.delay_ms ∈ [0,60000]`）使槽位长时间占用；`N` 需超过 1（占槽）+ 32（队列上限）；`delay` 属前置阶段注入，命中后 `time.sleep` 发生在 `with router.admit(model)` 内（`responses.py`），故确实持槽。
- 规模 / 时间域：`N >= 34` 并发；`delay_ms=60000` 保持槽位占用；不发布时延 SLO。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | （fixture 前置）启动专属实例并 probe `depl_b` → `healthy`；确认无启用注入 | 实例就绪 |
| 2 | `PATCH /v1/deployments/depl_b/diagnostics`（上表注入） | 200 且 `delay` 生效 |
| 3 | 以线程/异步并发发起 `N` 个 `POST /v1/responses` | 各响应 status |
| 4 | 收集响应：断言**至少一个**为 `429`；对首个 429 解析 `error` | `code=="rate_limit_exceeded"`、`type=="request_error"`、`retryable is True`、`param is None` |
| 5 | 断言 429 响应含 `Retry-After` 头 | 值为正整数秒（队列满为 `"30"`，等待超时为 `"1"`） |
| 6 | （teardown，`finally`）`PATCH .../diagnostics` body `{"items": []}` | 清空注入，`GET` 校验为空 |
| 7 | 交叉核对拒绝零副作用 | 429 无上游调用；账本按实现处理（准入失败可能保留 orphan，不作为"零义务"硬断言，只断言无上游调用） |

- 重点关注步骤：① **饱和才 429**——只有超过许可+队列上限时拒绝，非首个请求；② **`Retry-After` 存在且为正整数**；③ **区分两条 429 分支**——队列满（`Retry-After:30`）vs 等待超时（`Retry-After:1`），只断"存在+正整数"以免耦合内部时点；④ **并发共享同一 tier 的许可/队列**，不得假设各请求独立资源；⑤ **注入必须清空**，不得残留 `delay`；⑥ **MISSING**——自动化入口为 `MISSING`，须先实现 `at_dp_resp_20.py`。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：OpenAPI `ErrorEnvelope`/`ErrorDetail` + HTTP `Retry-After` 语义 + 系统设计 §7.8 `ERR-RATE-LIMIT`（不依赖实现答案）。**判据语义以设计验证项 `VRC-INF-004` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：至少一个请求 HTTP `429`；`Content-Type: application/json`；`Retry-After` 头存在且为正整数；body：`error.code=="rate_limit_exceeded"`、`type=="request_error"`、`retryable==true`、`param==null`；teardown：`PATCH {"items":[]}` → 200，`GET` 无 `enabled` 项。

## 6. 错误路径、副作用与清理

- 错误出口与表现：准入饱和 → `429 rate_limit_exceeded` + `Retry-After`，可观察且非 SSE。
- 副作用断言与清理：**必须 teardown**——`PATCH /v1/deployments/depl_b/diagnostics {"items":[]}` 清空 `delay` 后 `GET` 校验；不修改 `prov_b`/`depl_b`。专属实例按计划整班销毁。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/system/api_test_v03/at_dp_resp_20.py`（当前 **MISSING，尚未实现**）。
- 单 Case 执行命令（实现后）：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_resp_20.py -q`。
- 实现状态：Planned（MISSING）；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：饱和时至少一个 `429 rate_limit_exceeded` + `Retry-After` 正整数 + `retryable=true`；teardown 清空。
- FAIL：从未 429（饱和构造失败）、`Retry-After` 缺失/非正整数、code/type 错、注入残留。
- BLOCKED：并发/注入 fixture 不可实现。
- SKIP：B 类临时实例不可用。
- INVALID：以 mock/替代路径冒充真实路径，或注入未命中却按 429 判定。
- NOT_RUN：本 Case **无自动化实现**（MISSING）；未执行记 `NOT_RUN`。

**证据与 Run**：保存注入写/清空、并发请求清单与各响应（含 429 与 `Retry-After`）、上游调用计数/runtime 快照、发出命令、exit code、环境快照（本 case `environment:"b"`）。

**依赖**：B 类 fixture `LLMTierInstance` / `admin_client_b` / `api_client_b`；`OBS-DEPL-02`（`PATCH .../diagnostics` 注入）；实现 `src/inference/routing.py`；错误目录 `ERR-RATE-LIMIT`（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md) §7.8）。**不依赖**其它 Case。
