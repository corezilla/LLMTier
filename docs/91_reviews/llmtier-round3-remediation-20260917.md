<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier 第三轮集中整改处置

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-round3-remediation-20260917` |
| Document Version | `0.1.0-draft.4` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | Piko, Slinky |
| Approver | 待定 |
| Approval Date | 待定 |
| Created Date | `2026-09-17` |
| Last Modified Date | `2026-09-17` |
| Template Version | `0.1.0` |
| Template ID | `review.packet` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/91_reviews/llmtier-round3-remediation-20260917.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 范围与状态

基线为`0398f5633edbef53cba29578ce1c592000ca8cd9`。本文件记录第三轮三方意见在未提交工作树中的集中处置；不是复审结论、实现证据、runtime activation或提交批准。Piko与Slinky应直接只读本文件列出的普通路径和candidate.5机器字节复审。

## 2. Piko意见逐项处置

| Finding | 处置 | 证据 |
|---|---|---|
| LT-R3-PK-01 | fixed-candidate：按固定Pi真实shape补`store:false`、easy message、assistant/function/reasoning历史与array tool result；未启用未需求工具扩展 | OpenAPI ResponsesRequest；openai-surface fixtures |
| LT-R3-PK-02 | fixed-candidate：message/function/reasoning item加入稳定ID/status，SSE added/done/terminal执行identity oracle | OpenAPI output/event schemas；semantic validator |
| LT-R3-PK-03 | fixed-candidate：恢复标准nested Usage；缺失计数为Unknown且不把模型成功改失败 | TokenUsage；Piko interface §4；usage fixtures |
| LT-R3-PK-04 | fixed-candidate：每request唯一记录、单调版本替换、`[from,to)`、稳定snapshot/cursor、store 503；response/query不相加 | UsageRecord/Page；core module §6 |
| LT-R3-PK-05 | fixed-candidate：Admin采用ETag/If-Match/412、partial PATCH、401/403/409和稳定分页 | Admin OpenAPI；Management control；Admin fixtures |
| LT-R3-PK-06 | fixed-candidate：settings仅空库首次bootstrap；初始化后SQLite为唯一authority | Operational Store ADR；Runtime ISD §3-4；operations §4 |
| LT-R3-PK-07 | fixed-candidate：负例调用真实语义oracle；测试/库存同步candidate.5和锁定STD | tests；V&V/test spec；historical inventory notice |
| LT-R3-PK-08 | fixed-candidate/downstream-design：五个中文短页逐页定义字段、状态、错误、并发与安全交互 | `docs/40_module_design/webui-design.md` |

## 3. Slinky意见逐项处置

| Finding | 处置 | 证据 |
|---|---|---|
| LT-R3-SL-01 | fixed-candidate：同PK-01，真实首轮与历史请求成为正例 | OpenAPI + fixtures/tests |
| LT-R3-SL-02 | fixed-candidate：reasoning/refusal事件、item ID/status、terminal type/status关联和缺terminal负例 | OpenAPI + semantic validator |
| LT-R3-SL-03 | fixed-candidate：标准input/output details；cache是input子集，查询质量放UsageRecord | TokenUsage、requirements、Piko interface |
| LT-R3-SL-04 | fixed-candidate：唯一记录、版本替换、分页snapshot、授权绑定与store 503；内部attempt先归并 | Usage schemas；core module/ISD |
| LT-R3-SL-05 | fixed-candidate：invalid unknown-zero与missing/mismatched terminal实际被validator拒绝 | `tests/test_contract_semantics_v03.py` |
| LT-R3-SL-06 | fixed-candidate：Admin标准条件更新与原子引用检查已进入wire | Admin OpenAPI、fixtures、module/ISD |
| LT-R3-SL-07 | fixed-candidate：logical embedding model固定space；不兼容变化新ID；结果语义oracle补齐 | Models能力、Slinky control、embedding validator |
| LT-R3-SL-08 | fixed-candidate：历史inventory明确不再current；candidate.5、STD draft.26与验证说明同步 | inventory、contract/V&V/test docs |

## 4. LLMTier自评逐项处置

| Finding | 处置 | 证据 |
|---|---|---|
| LT-R3-LT-01 | fixed-candidate：固定Pi真实request/history字段纳入机器契约 | OpenAPI/fixture |
| LT-R3-LT-02 | fixed-candidate：标准SSE identity、reasoning/refusal与terminal闭合 | OpenAPI/validator |
| LT-R3-LT-03 | fixed-candidate：标准Usage字段及Unknown边界闭合 | OpenAPI/usage fixture |
| LT-R3-LT-04 | fixed-candidate：SSE事件、能力目录及固定Pi消费范围一致 | OpenAPI/manifest/fixture/validator |
| LT-R3-LT-05 | fixed-candidate：Usage唯一记录、Unknown、版本替换、分页及store failure闭合 | module/ISD/contract/usage fixture |
| LT-R3-LT-06 | fixed-candidate：Admin条件更新、partial write、权限错误与分页闭合 | Management/OpenAPI/Admin fixture |
| LT-R3-LT-07 | fixed-candidate/downstream-design：五个中文短页逐页定义字段、状态、错误、并发与安全交互 | Web UI design |
| LT-R3-LT-08 | fixed-candidate/downstream-design：补核心模块设计与Runtime ISD，不虚构subsystem | `docs/40_module_design/llmtier-core-design.md`；`docs/50_implementation_design/llmtier-runtime.isd.md` |
| LT-R3-LT-09 | fixed-candidate：current authority与历史inventory已消歧 | README/current inventory |
| LT-R3-LT-10 | fixed-candidate：负例执行真实语义oracle，测试范围不冒充运行证据 | tests/V&V/inventory |

## 4.1 candidate.3 定向复审处置

| Finding | 处置 | 证据 |
|---|---|---|
| LT-R3-PK-01-R1 | candidate.5新增标准`OutputRefusalContent`并用于assistant history/output；refusal fixture不再伪装为`output_text`，语义oracle拒绝类型改写 | OpenAPI；openai fixture；semantic tests |
| LT-R4-SL-01 | 保留已承诺base64标准分支，固定RFC4648+little-endian float32，校验请求/响应表示、严格解码、长度、有限值与维数 | OpenAPI；contract §3；embedding tests |
| LT-R4-SL-02 | Usage使用不可变版本和持久QuerySnapshot成员；Admin snapshot冻结序列化view/ETag；逐页复核权限，过期/冲突走现有400 | core §6/8；Runtime ISD §6；sequence fixture |
| LT-R4-SL-03 | provider dispatch前持久unknown Usage义务；后续追加计量失败或崩溃仍可查询unknown，store不可读才503；不改变模型结果 | core §6；Runtime ISD §5/6；crash-order fixture |
| LT-R4-SL-04 | semantic validator新增Usage subset/source/version和SSE delta/done/terminal identity真实拒绝测试 | validator；unit tests |
| LT-R4-SL-05 | 本表恢复原LT-R3-LT-04..10的finding语义，不再以SQLite/Embedding等他方finding错位替换 | 本节§4 |
| LT-R3-PK-01-R2 | candidate.5保存done完整item并要求terminal同index/id的item逐字段一致；增加terminal-only refusal改写负例和assistant-history refusal请求Schema正例 | OpenAI fixture；semantic validator；unit tests |
| LT-R4-SL-02-R1 | Runtime ISD删除`usage_records`原位upsert，统一为Obligation/immutable Version/Head/QuerySnapshot/Item表、FK与清理顺序；dispatch前事务顺序前移 | Runtime ISD §3/§5/§6 |
| LT-R4-SL-02/03-R2 | 收窄验证声明：当前纯设计模型实际执行的仅为更正/插入后旧snapshot成员不变、unknown义务跨模型restart保留及无obligation禁止dispatch；Admin删除、cursor过期、terminal后store失败与真实SQLite/crash均标`NOT_RUN`，fixture标签不作为PASS证据 | usage fixture；semantic validator；unit tests；V&V/test spec |

## 5. 候选基线与验证

- Machine candidate：`0.3-simplified-candidate.5`，`runtime_activation=false`。
- Responses首阶段只支持固定Pi实际使用的`stream:true/store:false`标准SSE；不建立未消费JSON、自定义恢复或fallback。
- 单元测试、Schema/语义测试与锁定STD验证的命令和结果在本次Matrix交付中报告；静态通过不等于runtime实现。
- 确定性外部设计未决项：无。仍需Piko复审Responses/Usage字节、Slinky复审Embeddings/Usage字节；实现与capture保持后续Gate。

## 6. 复审关注点

1. Piko：真实golden request是否全部被接受，SSE事件是否与固定parser一致，Usage缺失是否按任务Unknown处理。
2. Slinky：embedding space/limits/result oracle与Usage查询是否足够且未恢复旧管理机制。
3. 两方：确认没有SourceInstance、Seat/capacity、Invocation recovery、Cost、会话或兼容fallback重新进入current contract。
