<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Contract Test Specification

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-v0.3-contract-test-specification` |
| Document Version | `0.3.0` |
| Status | `Approved` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | LLMTier |
| Approver | LLMTier |
| Approval Date | `2026-09-07` |
| Created Date | `2026-09-07` |
| Last Modified Date | `2026-09-07` |
| STD Version | `0.1.0-draft.18` |
| Template ID | `assurance.test-specification` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/llmtier-v0.3-contract-test-specification.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

## 1. 目标、范围与被测对象

本规格描述 V0.3 candidate 的可执行 contract/schema/fixture 测试与 production-required case。被测对象为
OpenAPI、compatibility manifest、v0.3 fixtures、当前 Python package boundary 和迁移文档映射。现有测试源码
与 fixtures 仍是 executable oracle authority；本文不复制测试逻辑，也不表示 endpoint 已实现。

不在范围：V0.4 Chat/SSE/streaming、Provider-specific 准入策略、未批准的 persistence/HA/topology 方案。

## 2. 引用基线、环境与前置条件

- Project candidate：`aa2638283e77bc658e98df8d40396306cad17aa2`；C2 在此后形成未提交候选。
- Contract：`docs/contracts/openapi/llmtier-v0.3.openapi.json`。
- Activation：`docs/contracts/compatibility-manifest-v0.3.json`，必须保持 false。
- Fixtures：`docs/contracts/fixtures/v0.3/`；历史 v0.2 只作 provenance，不是 V0.3 Schema authority。
- Tests：`tests/test_contract_fixtures.py`、`tests/test_contract_semantics_v03.py`、
  `tests/test_independent_runtime_boundary.py`、`tests/test_standalone_imports.py`、
  `tests/test_std_migration.py`。
- 本地命令要求 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`；production case 另需固定部署、provider、store、
  consumer version 和脱敏 evidence 位置。

## 3. Case Matrix

| Case ID | Requirement | 场景 | 输入 | Oracle | Evidence | Priority |
|---|---|---|---|---|---|---|
| CT-AUTH-001 | 三分面 authority 与唯一调用路径 | 合法/越权 Client、Source、surface | authorization fixtures | OpenAPI scopes + expected result | semantic tests；production auth logs 待补 | P0 |
| CT-ID-001 | exact-case；无 alias/Role/cross-level fallback | Worker、worker、Role 与未知 ID | OpenAPI/manifest | only exact ID accepted | semantic tests；runtime capture 待补 | P0 |
| CT-DP-001 | Scope B Data Plane；deferred fail closed | Responses/Embeddings/Models/Chat/stream | data-plane/deferred fixtures | OpenAPI + manifest | fixture tests；Piko/consumer capture 待补 | P0 |
| CT-REC-001 | idempotency、202、terminal 与 canonical response | same/different digest、active/terminal | recovery fixtures | OpenAPI statuses/headers/body | semantic tests；durable-store run 待补 | P0 |
| CT-REC-002 | lost response、UnknownOutcome、M2-C | timeout/restart/forgotten key | recovery/policy fixtures | no blind redispatch；24h/168h | static PASS；crash evidence BLOCKED | P0 |
| CT-OBS-001 | Observation/Seat、ETag、pagination、invalidation | current/stale/invalid/unknown quota | observation/capacity fixtures | OpenAPI + capacity rules | semantic tests；Slinky E2E 待补 | P0 |
| CT-MGT-001 | Management method/path/DTO/concurrency | create/update/list/job/recovery | management fixtures | OpenAPI + typed errors | semantic tests；API/UI run BLOCKED | P0 |
| CT-SEC-001 | secret non-disclosure 与 Client isolation | read secret、cross-client/source | auth/management fixtures | deny/no secret material | static shape PASS；runtime security BLOCKED | P0 |
| CT-REG-001 | 单一 Registry/manifest/admission consistency | catalog/version/ETag change | manifest/OpenAPI | same exact catalog + activation false | semantic tests；runtime consistency BLOCKED | P1 |
| CT-PKG-001 | 独立 package/import boundary | import public package/entrypoints | `src/` package | imports without Slinky source | standalone tests | P1 |
| CT-MIG-001 | STD metadata/path/source integrity | project-root discovery | docs/std lock/sidecars | STD validator/source verifier | JSON result + unittest | P1 |
| CT-PERF-001 | capacity/fairness/SLO | concurrent load and limits | fixed provider/model/config | approved SLO and capacity oracle | NOT_RUN/BLOCKED | P0 activation |

## 4. 正常、边界、负向与并发场景

每个 P0 surface 至少覆盖一个正常、一个边界和一个负向 case。并发覆盖相同 idempotency key、不同 key、
同/不同 Client、Capacity Group overlap、Management ETag 冲突和 recovery poll。unknown、expired、missing
或 malformed input 必须 fail closed；不得自动 lowercasing、alias、Role mapping 或跨等级 fallback。

## 5. Recovery、重放、幂等与故障注入

测试顺序包含：首次请求、dispatch intent 持久化、backend 前/后 crash、响应丢失、同 key 同 digest 重试、
同 key 异 digest 冲突、active 202 查询、terminal canonical response/error、UnknownOutcome manual reconcile、
retention 边界。要求 `W=168h`、`M=24h`、产品 retry deadline `D=24h` 满足 `D<=W-M`。静态 fixture
只能验证规则；零重复 dispatch 必须由真实 durable-store/server evidence 证明。

## 6. 性能、容量、功耗或时序测试

本软件项目不适用功耗/硬件时序。performance/capacity 需固定 provider/model、Service Level、Client quota、
Capacity Group、并发、样本数、预热、超时和失败计数，报告 admission、queue、latency、throughput、fairness
与过期行为。当前没有可接受的 production baseline，CT-PERF-001 为 BLOCKED，不能用 fixture PASS 替代。

## 7. 执行步骤与自动化入口

1. 验证 STD source：`/Users/ben/work/STD/scripts/verify-source-manifest /Users/ben/work/LLMTier/docs/std-source-manifest.json --std-root /Users/ben/work/STD`。
2. 验证项目文档：`/Users/ben/work/STD/scripts/validate-design --project-root /Users/ben/work/LLMTier --require-immutable-std --json <artifact>`。
3. 执行项目测试：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests`。
4. 检查 patch：`git diff --check`；记录 HEAD、dirty path、digest 和所有 exit code。
5. production case 只在独立环境授权后执行；不由本文创建 runtime/config/fallback 路径。

## 8. Pass/Fail/Blocked/Invalid 判定

- PASS：在固定 baseline 和有效环境下，实际结果全部满足 oracle，证据完整。
- FAIL：有效执行产生与 oracle 不一致结果；不得用重试隐藏。
- BLOCKED：required dependency/environment/authority 缺失，且 case 无法安全执行。
- NOT_RUN：本 cohort 未安排执行；不能写成 PASS。
- INVALID：baseline、fixture、环境或证据损坏，结果不可判定，修正后重跑。

Migration Review 要求结构/source 与本地测试 PASS；Runtime Activation 要求所有 production-required P0 case
PASS 且独立 authority 批准。

## 9. Artifact、日志、测量与证据保存

保存 commit、dirty digest、环境版本、case selection、raw stdout/stderr、exit code、JSON/JUnit 或等价报告、
capture/log/metric hash、问题与重测关联。敏感 payload 必须脱敏；credential 永不进入 artifact。C2 evidence
位于 `docs/98_migration/evidence/`，未来 production evidence 使用独立获批位置并在 packet 中引用。

## 10. 安全、清理与可重复性

测试不得 reset/clean 用户工作树，不读取其他项目源码或凭据，不对 production 写入，除非另有明确环境授权。
临时文件使用系统临时目录并在成功后删除。重复执行必须固定 commit/config/dependency；随机或时间相关 case
记录 seed/clock。测试失败保持原始证据，不通过 fallback 或放宽 oracle 获得 PASS。
