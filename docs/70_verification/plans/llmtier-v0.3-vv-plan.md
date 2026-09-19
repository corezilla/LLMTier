<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 Verification and Validation Plan

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-v0.3-vv-plan` |
| Document Version | `0.3.2-draft.8` |
| Status | `In Review` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | llmtier |
| Reviewer | LLMTier, Piko, Slinky |
| Approver | 待定 |
| Approval Date | 待定 |
| Created Date | `2026-09-07` |
| Last Modified Date | `2026-09-18` |
| Template Version | `0.1.0` |
| Template ID | `assurance.vv-plan` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/plans/llmtier-v0.3-vv-plan.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 目标、范围与 V&V authority

验证simplified candidate的OpenAI-compatible Responses、Embeddings、Models、token Usage、health/readiness与精简Admin面；证明旧custom contract不再current。OpenAPI是machine authority，manifest只声明范围与activation。

## 2. 被验证基线与环境

基线：OpenAPI/manifest `0.3-simplified-candidate.7`、requirements/system/interface docs当前draft、v0.3 current fixtures。静态环境不等于production。

## 3. Verification 方法

JSON/OpenAPI解析、internal `$ref` resolution、Schema正负例、path/header/schema absence scan、文档版本/范围一致性、unit tests、CLI help与diff-check。

## 4. Validation 场景与用户目标

Piko完成完整输入的text/tool loop；Slinky Memory获得embedding；Piko/Slinky获得不重复计数的token事实；Operator在英文Web UI主页一屏查看全部Tier状态、添加/编辑/删除云/本地模型、安全探测并查询脱敏日志；服务恢复后分层确认。

## 5. 测试层级和责任边界

| Level | Owner | Evidence |
|---|---|---|
| Contract static | LLMTier | tests + fixtures |
| Provider adapter | LLMTier | controlled capture |
| Piko consumer | Piko | Responses SDK/agent test |
| Embeddings consumer | Slinky | Memory integration test |
| Admin UI/operations | LLMTier | browser/API/security test |

## 6. 环境、fixture、oracle 与数据治理

使用合成prompt/vector/usage/log，不使用生产credential或内容。probe测试必须用授权测试账号并记录可能费用。日志禁入内容使用合成canary验证，不能在证据中保存真实敏感值。

## 7. 覆盖、采样、统计和判定规则

每个current operation规划覆盖成功、validation、auth和provider failure。当前静态PASS范围：固定Pi请求的easy message、assistant文本/refusal历史、function call/output、image result和opaque reasoning；SSE的delta/done/terminal完整item identity、顺序、terminal/status、标准refusal content及terminal-only refusal改写负例；Usage的measured/estimated/unknown、source与token子集、单调版本、纯设计模型中的快照成员冻结、unknown义务跨模型restart保留和无obligation禁止dispatch；Embedding的float/base64表示与维数/有限数；Models exact-case。Admin删除期间稳定分页、cursor过期、terminal后Usage store失败、真实SQLite持久化与进程crash/restart、BGE-M3实际部署、admission并发/timeout、浏览器SSO/CSRF/三步保存以及systemd/backup/restore均为`NOT_RUN`，仍属后续行为验证；unknown值必须null。旧path/header/schema出现即FAIL。

## 8. 故障注入、恢复和非正常路径

计划覆盖429/Retry-After、provider timeout/502、service unavailable、Usage store failure、config invalid、restart；其中真实Usage store failure与进程restart当前为`NOT_RUN`。调用方retry不被声称exactly-once；LLMTier运维恢复不改变Piko任务状态。

## 9. 偏差、waiver、问题与重测

偏差必须关联requirement/case、影响、owner、截止和批准。不能以legacy `/call`通过替代目标`/v1`失败。

## 10. Evidence package、traceability 与签署

保存commit、artifact hash、命令、原始结果、环境摘要和签署。设计/static PASS不授权runtime；production activation需独立决定。
