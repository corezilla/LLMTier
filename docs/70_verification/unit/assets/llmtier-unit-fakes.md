<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier 单元测试替身资产设计 — FakeAdapter / AppFixture

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-unit-fakes` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-09-30` |
| Template ID | `tests.asset-design` |
| Template Version | `0.2.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/unit/assets/llmtier-unit-fakes.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本资产文档绑定：资产 ID 经 Document ID 固定（`llmtier-unit-fakes`，候选 ID `FAKE-LLMTIER-ADAPTER` 的正式实例）；消费方在 §1 登记；所属测试 Owner 在 metadata 固定。

### 模板定位：资产、Case 与可测试性缺口的边界

- **契约 authority**：替身模拟什么/不模拟什么、注入命中语义、调用序断言范围，唯一登记在本文档 §2；Case 文档引用，不改写。
- **消费方索引**：§1 登记全部依赖方；资产变更须逐一评估影响。
- **不替产品补可测试性**：缺钩子走方案 Gap → 设计变更回路，不用工具绕。

### 状态语义：开发与自检

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 开发状态 | `Planned` / `Implemented` | 本文档 §6 | 计划中的资产冒充可用 |
| 验证状态 | `Unverified` / `Verified`（自检 Run 引用） | 本文档 §5–§6 | 未自检宣称 Verified；用产品 Case 的 PASS 冒充自检 |

## 1. 用途与消费方

- 资产 ID / 名称 / 形态：`llmtier-unit-fakes`（候选 ID `FAKE-LLMTIER-ADAPTER`）——单元层进程内替身资产，含 `FakeAdapter`（上游 provider adapter fake）与 `AppFixture`（隔离 `Application` 装配夹具，含 `seed()` 固定 tier/deployment）；实现于 `tests/unit/v03/fakes.py`。
- 用途与解决的问题：让单元层在**不触真实上游 provider、不依赖真实网络**的前提下，对 `ResponsesService`/`EmbeddingsService`/`Router` 的成功、失败、用量缺失、拒绝与终态路径做确定性断言；`AppFixture` 提供每 Case 隔离的临时 SQLite 与固定 tier 种子。

| 消费方 | 类型 | 依赖点 |
|---|---|---|
| `llmtier-unit-test-scheme` v0.1.0-draft.7 | 方案 | §1.6 替身矩阵、§1.7 ENV-3 |
| `llmtier-unit-test-plan` v0.1.0-draft.5 | 计划 | §4 ENV-3、§5 Step 0 资产就位 |
| `UT-INF-001..009` | Case | `FakeAdapter`（complete/embed/probe 返回与失败注入） |
| `UT-MGMT-005/006/010/011` | Case | `FakeAdapter.probe`/账号用量 HTTP 替身 |
| `UT-OBS-*`/`UT-DIAG-*` | Case | `AppFixture.seed()` 固定 tier/deployment |
| `llmtier-system-test-scheme` §4（间接） | 方案 | 模块级 VRC 的单元承接方声明 |

## 2. 行为契约（唯一 authority）

- 模拟的行为集：
  - `FakeAdapter.complete(model, request)`：返回 `ProviderResult`，默认一条 `message` 项（`content` 为 `output_text`，`text="ok"`）＋ `usage={input_tokens:2, output_tokens:1, total_tokens:3}`（`usage=False` 时为 `None`）；`refusal=True` 时 `content` 为 `{"type":"refusal","refusal":"no"}`；`status` 可配置为 `completed`/`incomplete`（`incomplete` 附 `incomplete_details={"reason":"max_output_tokens"}`）；`provider_request_id` 可配置（默认 `None`）；`fail=<Exception>` 时抛该异常。
  - `FakeAdapter.embed(model, request)`：返回标准 `EmbeddingResponse` 形状 `{object:"list", data:[{object:"embedding", index, embedding:[0.0]*dimension}]}`，`dimension=request.get("dimensions",1024)`，计数＝字符串输入 1 / 列表输入长度；`usage={prompt_tokens, total_tokens}`＝计数。
  - `FakeAdapter.probe()`：恒返回 `True`。
  - `AppFixture.seed(tier="Worker", capabilities=None, backend_model="synthetic-chat", health="healthy")`：在隔离库创建 provider＋deployment 并把该 deployment 挂到指定固定 tier；`capabilities` 默认 `response_capabilities()`（12 键）；`health` 写入 `deployments.health`。
- 不模拟 / 不证明的性质：
  - **不证明真实上游 provider 协议**（OpenAI-compatible HTTP wire、SSE 分帧、真实模型推理内容）；`FakeAdapter` 只代返回值/异常/终态，不代网络或序列化。
  - **不证明上游模型答案质量**（内容非 Oracle，见系统方案 §4 裁决）。
  - `FakeAdapter.probe()` 恒 `True` 只代表"探测健康结果"，不证明真实 `GET /models` 兼容性；探测不可达路径由 `UT-MGMT-010` 用专门 fake 注入。
  - `AppFixture` 的真实 SQLite 是**真实依赖**（非替身），其行为由 `UT-UTIL-*` 覆盖，不在本资产证明范围。
- 注入/命中语义：`fail` 是**直接抛异常**（非计数式注入），命中即由被测路径异常分支观察；用量缺失以 `usage=False`（`usage=None`）表达"上游未返回用量"，断言 `unknown` 不补零。
- 精度 / 推进接口（时钟类适用）：不适用（本资产无时钟）。
- 预定义故障场景与副作用前后绑定：场景＝`fail=ApiError/TimeoutError`（上游失败）、`usage=False`（用量 unknown）、`refusal=True`（拒绝内容）、`status="incomplete"`（截断终态）；均绑定被测服务调用点，观察点为返回结构/落库行，不核对上游副作用（fake 无副作用）。

## 3. 可测试性依赖与缺口回路

- 依赖的产品钩子（设计出处）：`ResponsesService(adapter=…)` / `EmbeddingsService(adapter=…)` / `Router` 的 adapter 注入点（`inference-design` §13、`inference-isd`）；`Application(database, settings)` 公开装配入口（`http-api-design` §13.1.1、`http-api-isd`）。
- 缺失钩子的 Gap 与移交：（无缺失——adapter 注入点与 `Application` 构造入口均为公开实现接口）。`FakeResponse`（account-usage HTTP / OpenAI SSE 响应 stub）是各测试模块**本地**定义（`test_account_usage.py`/`test_provider_openai.py`），非本资产成员，不在此登记。

## 4. 实现设计与版本耦合

- 实现位置与结构：`tests/unit/v03/fakes.py`（单文件）；`AppFixture`（隔离库装配）、`FakeAdapter`（provider fake）、`response_capabilities()`/`embedding_capabilities()`（能力键构造）。
- 版本耦合与适配规则：绑定 `src/inference/providers/base.py::ProviderResult` 与 `src/http_api/app.py::Application` 公开签名；二者变更时先改本契约再适配，消费方逐 Case 复跑。
- 并行隔离：`AppFixture` 每实例独立 `tempfile.TemporaryDirectory`＋新 SQLite；`FakeAdapter` 每 Case 新建实例，无跨 Case 状态。

## 5. 自身验证（自检）

| 自检项 | 验证的契约条款 | 判定 |
|---|---|---|
| `FakeAdapter(usage=True).complete` 返回含 usage 的 `ProviderResult` | §2 complete 返回集 | 断言 |
| `FakeAdapter(usage=False).complete` 的 `usage is None` | §2 用量缺失语义 | 断言 |
| `FakeAdapter(fail=ApiError(...)).complete` 抛该异常 | §2 失败注入 | 断言 |
| `FakeAdapter.embed` 计数＝输入长度且维度＝`dimensions` | §2 embed 返回集 | 断言 |
| `FakeAdapter.probe()` 返回 `True` | §2 probe | 断言 |
| `AppFixture.seed()` 后 tier 含该 deployment 且 `health` 已写 | §2 seed | 断言 |

- 自检执行入口：`PYTHONPATH=src python3 -m pytest tests/unit/v03 -q`（消费方 Case 即自检入口；资产无独立 runner，自检由使用它的单元 Case 覆盖）。
- 自检 Run 证据位置：`tests/unit/v03/reports/<run-id>/`（单元 Run 根；当前尚无录制 Run，见 `G-UT-1`）。

## 6. 状态与版本

- 开发状态 / 验证状态（自检 Run 引用）：`Implemented` / `Unverified`（资产已实现并被全部单元 Case 消费，但形式化自检 Run 尚未录制，见 `G-UT-1`；`tests/unit/v03` 当前 364 收集级通过，属于消费方 Case 的执行证据，不冒充本资产自检）。
- 最近契约变更与消费方影响：v1 初版；`FakeAdapter` 增加 `status`/`provider_request_id` 参数后 `UT-INF-003/008` 复评无影响。

## 7. 未决项

| 未决项 / 关联 | Owner / 最晚 Gate | 关闭所需事实或决定 |
|---|---|---|
| 自检 Run 正式录制与 `Verified` 状态 | LLMTier / 首次执行后报告评审 | 按 §5 录制一次自检 Run 于 `tests/unit/v03/reports/<run-id>/`，置 `Verified`；与 `G-UT-1` 同批关闭 |

<!-- 交付自查：契约是否完整到 Case 作者无需读源码；每个消费方是否都能反向找到本文档；Verified 是否可追到自检 Run；有没有用工具绕产品缺陷的痕迹？ -->
