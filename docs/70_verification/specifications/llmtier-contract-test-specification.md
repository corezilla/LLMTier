<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Contract Test Specification

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-contract-test-specification` |
| Document Version | `0.3.2-draft.7` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | LLMTier, Piko, Slinky |
| Approver | 待定 |
| Approval Date | 待定 |
| Created Date | `2026-09-07` |
| Last Modified Date | `2026-09-17` |
| Template Version | `0.1.0` |
| Template ID | `assurance.test-specification` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/llmtier-contract-test-specification.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 目标、范围与被测对象

被测对象是OpenAPI/manifest、current fixtures、authority docs和legacy-removal rules；不把未实现runtime当PASS。

## 2. 引用基线、环境与前置条件

使用candidate.6机器字节、Draft 2020-12 validator、语义validator和Python unit tests。生产adapter、credential和模型不可作为静态前置。

## 3. Case Matrix

| ID | Subject | Oracle | Runtime state |
|---|---|---|---|
| CT-DP-001 | 固定Pi Responses SSE/text/tool/history/reasoning/refusal | 真实请求shape有效；delta/done/terminal identity、标准refusal content及terminal语义通过；LLMTier不执行tool | BLOCKED |
| CT-MODEL-001 | Models exact ID/capabilities | case-sensitive；no alias/fallback | BLOCKED |
| CT-EMB-001 | Embeddings float/base64/batch/space | 请求/响应表示一致；base64严格解码为little-endian float32；数量/index/维数/有限数；`Embedding-v1`固定BGE-M3/1024/8192/batch32/L2及immutable revisions；同logical model同space | BLOCKED |
| CT-USAGE-001 | per-call/query usage | 标准details；unknown null；record替换不相加；store 503；no Cost | BLOCKED |
| CT-ADMIN-001 | cloud/local CRUD/probe/audit | Secret不返回；probe确认；If-Match/partial PATCH/分页 | BLOCKED |
| CT-LOG-001 | read-only sanitized logs | LogPage Schema、级别/模块/request过滤、禁入内容、稳定cursor及store 503 | STATIC CONTRACT PASS；runtime BLOCKED |
| CT-ADM-001 | 内部admission与routing | 并发1、FIFO 32/30秒、least-in-flight+ordinal、429/503、30/60秒timeout、无跨等级/space fallback | BLOCKED |
| CT-WEBSEC-001 | Web UI认证与分步保存 | TLS代理SSO/MFA、HttpOnly/CSRF、browser无bearer；三步失败续作不重复POST或自动删除 | BLOCKED |
| CT-OPS-001 | health/readiness/restart confirmation | no-cost probe separation | BLOCKED |
| CT-BOUNDARY-001 | stateless gateway | no Agent session/context/tool/KV ownership | STATIC PASS candidate |
| CT-SCOPE-001 | removed extensions | forbidden path/header/schema absent | STATIC PASS candidate |

## 4. 正常、边界、负向与并发场景

已执行的静态场景：标准 SSE text/function/reasoning/refusal、assistant-history refusal、function result roundtrip、embedding float/base64、model list、measured/unknown Usage、LogPage Schema及禁入字段扫描；快照模型执行更正和插入后旧snapshot成员不变，unknown obligation在模型restart后仍可查，无obligation dispatch被拒绝。已执行负例包括SSE event必填/identity/content/terminal冲突、embedding表示/解码/数量/index/维数、Usage source/subset/version降级。

仅定义而`NOT_RUN`的场景：Admin配置删除期间继续读取冻结snapshot、cursor过期、terminal后Usage store失败、真实SQLite写入/清理以及进程crash/restart；BGE-M3实际向量、admission并发/超时、浏览器SSO/CSRF和分步保存恢复；systemd、加密backup/restore及60秒摘流。它们保留为实现/联调门禁；fixture中的`expired_cursor_error`等oracle标签只是预期，不是已执行证据。并发编辑规划使用If-Match/412，引用冲突规划使用409；不测试外部Seat/claim。

## 5. Recovery、重放、幂等与故障注入

V0.3不定义custom model-call recovery/idempotency。测试标准client retry下的429/502/503和网络不明，不声称exactly-once。运维故障注入覆盖config/provider/store/restart；不创建跨系统恢复状态机。

## 6. 性能、容量、功耗或时序测试

功耗/硬件时序不适用。性能和内部保护需固定provider/model/config实测；不发布外部capacity snapshot或SLO前置结论。

## 7. 执行步骤与自动化入口

1. JSON parse + OpenAPI ref resolution。
2. fixture schema/semantic validation。
3. forbidden term/path/header scan。
4. `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests`。
5. CLI help、STD validator和diff-check。

## 8. Pass/Fail/Blocked/Invalid 判定

Static PASS仅表示候选一致；runtime未执行为BLOCKED。旧custom机制仍在current machine authority为FAIL。用legacy `/call`替代目标API为INVALID。

## 9. Artifact、日志、测量与证据保存

保存commit/hash、命令、exit code、validator结果和合成fixture；不保存Secret、生产prompt/output或provider payload。

## 10. 安全、清理与可重复性

测试credential独立；probe需明确授权并记录费用可能性；清理测试资源但保留脱敏audit。重复执行不得依赖旧candidate或另一条fallback。
