<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Verification and Validation Plan（迁移候选）

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-v0.3-vv-plan` |
| Document Version | `0.3.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Created Date | `2026-09-07` |
| Last Modified Date | `2026-09-07` |
| STD Version | `0.1.0-draft.17` |
| Template ID | `assurance.vv-plan` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/plans/llmtier-v0.3-vv-plan.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. 目标、范围与 V&V authority

本计划把 `docs/qa/llm-tier-contract-qa-v0.3.md` 的策略、Gate 和 evidence boundary 迁为 STD
`assurance.vv-plan` 候选。范围是 V0.3 的 Data Plane、Observation、Management、Registry、capacity、
recovery、安全与 activation gate；不覆盖 V0.4 streaming/Chat，也不激活任何 runtime surface。

Authority 保持分层：OpenAPI v0.3 是字段级机器契约，compatibility manifest v0.3 是 capability 与
activation 状态 authority，`tests/` 和 fixtures 是可执行 oracle，运行环境产物才是 production evidence。
本文只定义验证方法、责任和判定规则，不能用 Markdown 结果替代上述 authority。

## 2. 被验证基线与环境

| 基线 | 固定对象 | 当前状态 |
|---|---|---|
| 迁移候选 | immutable commit `aa2638283e77bc658e98df8d40396306cad17aa2` | C0/C1 Owner ACCEPTED；consumer review 独立进行 |
| STD | `94c0262de35b5b989bba9f8d23f212af709c9dbf` / `std-v0.1.0-draft.17` | source verifier 71 artifacts PASS |
| 服务设计 | `docs/30_subsystem_design/llmtier-service-design.md` | Draft candidate |
| 接口说明 | `docs/60_interfaces/` | Draft candidate；OpenAPI 仍为字段 authority |
| 机器契约 | `docs/contracts/openapi/llmtier-v0.3.openapi.json` | Candidate；runtime 未激活 |
| Activation | `docs/contracts/compatibility-manifest-v0.3.json` | `overall.runtime_activation=false` |
| 可执行验证 | `tests/`、`docs/contracts/fixtures/v0.3/` | 本地静态/语义验证可执行 |
| Production 环境 | provider、durable store、Admin UI、Piko/Slinky consumers | NOT_RUN/BLOCKED |

每次执行必须记录 project commit、dirty worktree、Python/依赖版本、命令、exit code、关键输出和 artifact。
环境差异不得由隐式 fallback、alias、Role selector 或跨 Service Level 路由吸收。

## 3. Verification 方法

| Requirement | Analysis | Inspection | Demonstration | Test | Owner | Evidence |
|---|---:|---:|---:|---:|---|---|
| 唯一 `Runtime -> Piko -> LLMTier` 路径与 authority | x | x |  | x | LLMTier/Piko/Slinky | design、controls、authority scan tests |
| exact-case Service Level；无 alias/Role selector/cross-level fallback | x | x |  | x | LLMTier | OpenAPI/manifest、semantic tests |
| Responses/Embeddings non-stream 与 deferred surface fail closed | x | x |  | x | LLMTier/Piko | OpenAPI、fixtures、consumer capture |
| idempotency、lost response、UnknownOutcome、M2-C retention | x | x | x | x | LLMTier/Piko | recovery fixtures、crash/consumer evidence |
| Observation/Seat、ETag、invalidation 与 Client scope | x | x | x | x | LLMTier/Slinky | fixtures、consumer contract/E2E evidence |
| Management secret、并发、审计与 recovery safety | x | x | x | x | LLMTier | API/UI negative tests、audit evidence |
| 单一 Registry、admission、capacity/fairness 与 isolation | x | x | x | x | LLMTier | consistency、load、multi-client evidence |
| Runtime Activation 保持独立 | x | x |  | x | LLMTier activation authority | manifest 与 activation Gate packet |

## 4. Validation 场景与用户目标

1. Piko 能以 exact `service_level_id` 调用唯一 non-stream Data Plane，并在 202、lost response、terminal
   error 和 UnknownOutcome 下安全恢复且不重复 dispatch。
2. Memory/Knowledge consumer 能使用 Embeddings non-stream，且不形成 Provider-direct generation path。
3. Slinky 能只读观察 readiness、capacity、Invocation 与 usage，正确投影 Seat；无效或过期数据 fail closed。
4. 管理员能安全管理 Registry、Provider、Client/Source、capacity、Job 与 recovery，secret 只写不读。
5. 不同 Client/Source/SourceInstance 的数据、quota、usage 和 error evidence 隔离；并发与 capacity
   约束可审计。
6. production evidence 未齐时，manifest 必须继续报告 candidate/false，不得由文档或静态测试激活。

## 5. 测试层级和责任边界

| 层级 | 当前覆盖 | Owner | 当前判定 |
|---|---|---|---|
| Unit/Module | Python utility、backend、独立包导入 | LLMTier | PASS（本地） |
| Contract/Schema | OpenAPI、manifest、fixtures、接口语义 | LLMTier | PASS（本地 candidate） |
| Subsystem | 路由、ledger、Registry、Management/Observation wiring | LLMTier | NOT_RUN/BLOCKED |
| Consumer | Piko adapter；Slinky Observation consumer；Embeddings consumer | 各 consumer authority | NOT_RUN/BLOCKED，独立 review/evidence |
| Recovery/Security | crash、lost response、secret、isolation、audit | LLMTier + consumer | NOT_RUN/BLOCKED |
| Performance/Capacity | admission、fairness、真实 provider、SLO | LLMTier | NOT_RUN/BLOCKED |
| Acceptance/Activation | 全 Gate 与 production evidence | 独立 activation authority | BLOCKED；不在迁移 Gate 内 |

## 6. 环境、fixture、oracle 与数据治理

- 静态环境使用项目锁定 commit、`PYTHONPATH=src` 和项目既有 Python 依赖，不读取其他项目源码。
- v0.3 fixtures 覆盖 authorization scope、capacity negative、UTF-8 digest、idempotency policy、recovery、
  Data Plane fail-closed 与 Observation/Management；fixture 是测试输入，不是 production capture。
- OpenAPI schema、manifest selection 和明确 expected result 组成静态 oracle。生产 oracle 必须来自真实
  endpoint、durable store、audit、metrics 和 consumer capture，并记录脱敏与 retention policy。
- 不在 evidence 中保存 credential、prompt/output 私密内容或跨 Client 数据；secret 只验证不可读性质。

## 7. 覆盖、采样、统计和判定规则

- 静态 Gate 要求 source verifier、project-root validator、全部 project tests 和 `git diff --check` 均 exit 0。
- contract case 必须包含 normal、boundary、negative；关键 recovery/isolation case 还须包含 restart、retry、
  duplicate、timeout 和并发。
- performance/capacity 必须在固定 provider/model/config、预热规则、样本数和置信摘要下报告；未定义或未执行
  时只能写 NOT_RUN/BLOCKED。
- 单项 PASS 不向上推导整层 PASS；任何 production-required case FAIL/BLOCKED 都阻止 Runtime Activation。

## 8. 故障注入、恢复和非正常路径

至少覆盖：dispatch 前/后进程退出、响应丢失、同 key 同/异 digest 重放、active 202 轮询、terminal typed
error、UnknownOutcome manual reconcile、Registry/ETag 变化、capacity 过期、quota unknown、storage failure、
secret access、跨 Client/Source 请求、consumer timeout。禁止通过 silent retry、cross-level fallback、Role
selector 或第二 endpoint 绕过失败。

## 9. 偏差、waiver、问题与重测

偏差必须记录 case ID、受影响 requirement、原因、Owner、到期条件和重测基线。Runtime-required case 不允许
以文档迁移 waiver 关闭；environment unavailable 记 BLOCKED，未计划执行记 NOT_RUN，输入/环境无效记
INVALID。修复后只在同一 immutable baseline 或明确的新 baseline 上重测并保存前后证据。

## 10. Evidence package、traceability 与签署

每个 evidence package 包含：commit/dirty digest、环境清单、case selection、原始命令与 exit code、日志/报告
hash、Requirement→Design/Contract→Case→Evidence 映射、未执行项、问题与 reviewer。C2 review packet 只请求
Migration Review verdict；Document Status、canonical promotion、RAG publication 与 Runtime Activation 分别签署。
旧 `docs/qa/llm-tier-contract-qa-v0.3.md` 在 scope-level promotion 前继续承担历史 review ledger 与 residual
evidence authority。
