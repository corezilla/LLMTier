<!-- STD_DOCUMENT_COVER_BEGIN -->
# LLMTier V0.3 API Test Execution Plan

> 配套文档：[`llmtier-v0.3-api-test-plan.md`](./llmtier-v0.3-api-test-plan.md)（测试设计 + case 矩阵）。本文件是**执行层面**的计划：分阶段、产出物、依赖、人/工时估算、风险与回滚。

| 文档字段 | 值 |
|---|---|
| Document ID | `llmtier-v0.3-api-test-execution` |
| Document Version | `0.2.0-draft.4` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-21` |
| Last Modified Date | `2026-09-21` |
| Template ID | `assurance.test-execution-plan` |
| Template Version | `0.1.0` |
| Template Conformance | `tailored` |
| Tailoring Reference | `std-tailoring` |
| Migration Map Reference | `llmtier-v0.3-api-test-plan` |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/plans/llmtier-v0.3-api-test-execution.md` |
| Supersedes | none |
<!-- STD_DOCUMENT_COVER_END -->

## 1. 目标与定位

把 [`llmtier-v0.3-api-test-plan.md`](./llmtier-v0.3-api-test-plan.md) §4 的 **89 个 case** 从"设计"落到"可执行 + 可回归"。

- 每个 case 有一个 pytest 文件（或 at_*.py）
- 每个 case 跑前自动做环境就绪检查（test plan §2.1），失败则 SKIP
- 每个 case 跑后产出 PASS/FAIL/SKIP/BLOCKED + 必要字段
- 全量结果落 `docs/70_verification/reports/llmtier-v0.3-api-test-report.md`

**不在本执行计划范围**：单元测试、contract static、UI E2E、performance SLA 校准。

---

## 2. 阶段划分（按 A/B 类）

### 2.1 A 类 vs B 类回顾

| 类 | 含义 | 数量 | 执行方式 |
|---|---|---|---|
| **A** | 读 / 观察 / 无状态写 | 63 | 直接打 m5air (`192.168.1.9:8181`) 现有实例 |
| **B** | 创建/修改/删除 provider / deployment / service-level | 26 | 临时 SQLite + 临时端口（**m5air 同机第二个进程**），teardown 清理 |

A 类与 B 类不能共享同一进程的 SQLite（写干扰），所以分两阶段跑。

### 2.2 阶段表

| 阶段 | 名称 | 产出物 | 依赖 | 工时 |
|---|---|---|---|---|
| **P0** | 测试基线 + A 类 conftest + runner | `tests/system/api_test_v03/` 目录骨架、A 类 conftest、A 类 runner | 无 | 3h |
| **P1** | A 类 case（53 个） | 53 个 at_*.py | P0 | 11h |
| **P2** | B 类 conftest（临时实例 lifecycle）+ B 类 case（15 个） | B 类 conftest、15 个 at_*.py | P1（验证 A 类不污染 m5air） | 7h |
| P3 | 首跑 + 报告 | `llmtier-v0.3-api-test-report.md` | P1 + P2 | 2h |
| P4 | CI 接入（可选） | GitHub Actions workflow | P3 | 4h |
| **总计** | | | | **~28 人·小时**（比 v0.1 估 33h 减少 5h：消除 m5mac 临时实例 + 注入 fixture 的工作量） |

---

## 3. 每阶段详细计划

### P0 — A 类测试基线 + runner（3h）

**目标**：搭好目录、写好 A 类 conftest、确认 §2.1 检查能跑通。

**任务**：

1. 建目录 `tests/system/api_test_v03/`
2. 写 `tests/system/api_test_v03/conftest.py`：
   - `pytest_configure(session)`：跑 §2.1 五项检查；不通过 → 整个 A 类 suite skip + 输出原因（pytest.skip 机制）
   - `fixture(scope="session") m5air_api_client`：httpx.Client，base_url=`http://192.168.1.9:8181`，headers `Authorization: Bearer dev-data`，timeout=30s
   - `fixture(scope="session") m5air_admin_client`：同上 + `Authorization: Bearer dev-admin`
   - `fixture` 工具：`make_request(client, method, path, ...)`，统一处理 SSE 流解析（pytest fixture for SSE reader）
3. 写 `runner_a.sh`：执行 A 类全部 case；输出格式按 §5.4 判定
4. **首次跑验证**：故意把 m5air 关掉 → 确认 suite skip + 输出"§2.1 第 1 项 /healthz 不通"

**验收**：
- `pytest tests/system/api_test_v03/ -q` 跑起来不报错
- m5air 正常时无 skip；m5air 挂时整 suite skip
- SSE 解析器 fixture 能用（写个 fake SSE event 测试）

### P1 — A 类 53 个 case（11h）

**目标**：A 类 53 个 case 全部 PASS，建立测试框架信心。

**任务**：按 test plan §4.1 / §4.2 / §4.3 / §4.4 / §4.5 / §4.6（GET 部分）/ §4.7（GET 部分）/ §4.8（GET 部分）/ §4.9 / §4.10 / §4.11 写 at_*.py。

**关键 case**（最容易踩坑的，按 test plan §8 P1~P14）：

- DP-RESP-01（SSE 完整序列）：实现 SSE 解析器（httpx.stream + 手工解析 `event:` / `data:` 行），断言 9 个事件 + `data: [DONE]` 终止
- DP-RESP-02（stream=false 拒绝）：**注意当前实现强制 stream=true**（responses.py:50），此 case 期望 400 unsupported_request
- DP-RESP-04（tools 透传）：不验上游是否调用工具，**只验 HTTP 200 + SSE 完整**
- DP-EMB-03（不变量 ×5）：写循环 + cosine similarity 计算（用 numpy 或纯 Python）
- DP-USAGE-04（cursor expired）：**sqlite3 直连 m5air 数据库** UPDATE expires_at 后再请求；这需要 SSH + sqlite3 权限
- ADM-AUDIT-01 / ADM-LOGS-01（敏感信息扫描）：断言响应 body 不含 `"9832"` 字面值、不含 `omlx-secret-key.txt` 字面值
- AUTH-02/AUTH-03/AUTH-06：注意 LAN trust 模式下错误 token 仍 401，错误 principal 403

**验收**：
- A 类 53 个 case 全部 PASS 或 SKIP（上游挂 → SKIP，不超过 5 个）
- 测试文件头部按 TS-002 写明依赖

### P2 — B 类 conftest + 15 个 case（7h）

**目标**：B 类 15 个 case 全部 PASS；teardown 干净不污染 m5air。

**任务**：

1. 写 `tests/system/api_test_v03/conftest_b.py`（与 P0 分离，避免 fixture 冲突）：
   - `fixture(scope="session") tmp_llmtier`：启第二个 LLMTier 进程
     - 端口：随机 49152~65535
     - 数据库：`/tmp/llmtier_api_<uuid>/state.sqlite3`
     - env：`LLMTIER_ADMIN_TOKEN=dev-admin`、`LLMTIER_DATA_TOKEN=dev-data`
     - Python 3.14：`/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`
     - 启动命令：`PYTHONPATH=src python3 -m llmtier_v03 --host 127.0.0.1 --port <random> --database /tmp/...`
     - 等待 `/healthz` 200（最多 30s）
   - `fixture tmp_admin_client`：base_url=127.0.0.1:<随机端口>，Bearer dev-admin
   - session 结束：kill PID + rm -rf /tmp/llmtier_api_<uuid>/
   - `fixture(scope="session") tmp_llmtier_state`（helper）：临时实例启好后，POST/PATCH 注入 3 provider + 4 deployment + 7 service-level（m5air 上同样的 fixture；service-level 用全部 7 个 FIXED_TIERS，会触发 409 resource_conflict 处理；实际 7 个都已存在 → 注入步骤只补 3 provider + 4 deployment 即可，service-level 跳过）
2. 写 19 个 at_*.py，按 test plan §4.6/§4.7/§4.8 写 case
3. 写 `runner_b.sh`

**关键 case**：

- ADM-PROV-02（create provider）：fixture 模板**禁止传 id**；secret_ref 用 `file:/tmp/at-test-secret-<uuid>.txt` mode 600
- ADM-PROV-05（update）：If-Match `'"<id>.v<N>"'`（**带双引号**）
- ADM-PROV-06（缺 If-Match → 412 + current_version）：断言 body 含 `current_version` 字段
- ADM-DEPL-02（create deployment）：capabilities **12 字段全集**（responses/embeddings/tools/structured_outputs/input_modalities/output_modalities/context_window/max_output_tokens/embedding_space_id/embedding_dimensions/embedding_max_batch_inputs/embedding_max_input_tokens）
- ADM-DEPL-04（update）：body 仅 allowed 字段（`name`/`enabled`/`backend_model`/`capabilities`），不能传 `provider_id`
- ADM-SL-02（创建非固定 tier）：期望 400 invalid_request
- ADM-SL-02b（创建已存在 FIXED_TIER）：期望 409 resource_conflict
- ADM-SL-05（删除 FIXED_TIER）：期望 409 fixed_service_level
- **teardown 必须做**：每个 case 跑完要 DELETE 自己创建的资源；runner_b 跑完 kill 整个临时实例 + rm tmpdir

**验收**：
- 19/19 PASS
- m5air 现有 state 完全未变（curl 对比前后 provider/deployment/service-level 列表）

### P3 — 首跑 + 报告（2h）

**任务**：

1. `./runner_a.sh && ./runner_b.sh`，捕获所有 case 结果
2. 按 test plan §5.4 判定 PASS/FAIL/SKIP/BLOCKED
3. 写 `docs/70_verification/reports/llmtier-v0.3-api-test-report.md`：
   - 总览（89 case 状态分布；A 类 63 / B 类 26）
   - 失败 case 详情（`failure_reason` + `reproduction_cmd`）
   - 跳过 case 列表（`skip_reason` + `fix_owner` + `eta`）
   - 阻塞 case 列表（`block_reason` + `required_resolution`）
   - 与 9-20 / 9-21 报告对比（test plan §8 P1~P14 回归检查）
4. 评审：FAIL + BLOCKED = 0 通过；SKIP ≤ 5

### P4 — CI 接入（可选，4h）

**前提**：CI runner 能访问 m5air（`192.168.1.9`）和 m5mac OMLX——**目前云端 GitHub Actions 不可行**。可选项：
- 本地 self-hosted runner（装在 m5air 或 m5mac 上）
- 仅本地 pre-push hook，不上 CI

**任务**（如选 self-hosted）：

1. `.github/workflows/api-test.yml`：触发 `pull_request` + `push to main`
2. runner step：`bash tests/system/api_test_v03/runner_all.sh`
3. 上传报告到 artifacts

---

## 4. 依赖与前置条件

| 依赖 | 详情 | 状态 |
|---|---|---|
| m5air LLMTier 服务运行 | `192.168.1.9:8181` | ✅ 已知运行（handoff §1） |
| m5air OMLX 9000 | 上游 provider_local | ✅ 已知健康 |
| m5mac OMLX 9000 | 上游 provider_omlx_m5mac（DP-RESP fallback） | ⚠️ 9-21 修复后未实测 |
| provider_omlx_m5mac.secret_ref | `file:/Users/mlp/LLMTier-dev/secrets/omlx-secret-key.txt` | ✅ 已修（9-21 上午） |
| m5air sqlite3 直连权限 | DP-USAGE-04 fixture 需要 | ⚠️ 待 P1 验证 |
| Python 3.14 | m5air + m5mac 临时实例启动 | ✅ handoff §1 |
| 89 case 在测试计划中明确 | v0.3.0-draft.5（新增加强 case 后） | ✅ |
| 测试机在 192.168.x LAN 内 | TS-003 | ✅ m5air 自带 |
| 临时实例启停权限 | /tmp 写、端口 bind | ✅ mlp 用户 |

---

## 5. 风险与缓解

| 风险 | 影响 | 概率 | 缓解 |
|---|---|---|---|
| m5mac OMLX 挂掉 | DP-RESP fallback case SKIP | 中 | §2.1 检查第 4 项；P1 跑完后看 SKIP 列表 |
| OMLX 临时挂 | 多 case SKIP | 中 | conftest 输出原因 + §2.1 检查项编号 |
| B 类 teardown 不彻底 | m5air 残留 provider/deployment | 中 | runner_b 跑完强制 kill + 校验 m5air 状态对比 |
| m5air sqlite3 不可写（DP-USAGE-04） | case BLOCKED | 低 | 若 /Users/mlp/LLMTier-dev/state.sqlite3 mode 不允许直连 → 改用临时 SQLite 启新实例专门造 cursor |
| BLOCKED vs FAIL 判定分歧 | 报告不统一 | 中 | runner 强制四态判定；FAIL/BLOCKED 都阻塞 release |
| ADM-PROV-05 ETag 双引号 | 412 假阴性 | 低 | §3.3.1 已给完整示例，runner 测试代码复制粘贴 |
| ADM-DEPL-02 capabilities 漏字段 | 400 false negative | 低 | §4.7 fixture 模板已列 12 字段全集，runner 用常量引用 |
| SSE 解析器在不同 Python httpx 版本下行为不同 | false PASS | 低 | 锁定 httpx 版本；用纯字节解析（不依赖 httpx SSE helper） |

---

## 6. 决策记录（v0.2 → v0.3 之间的改动理由）

| 决策 | 理由 |
|---|---|
| 测试执行机从 m5mac 改回 m5air | m5air 已有完整 state，注入 fixture 是冗余；ST 文档说的"m5air 不是测试环境"语境是 FD/长期/性能压测，不适用 API 端点 |
| 删除 §2.3 配置基线 | 上一条同 |
| A 类 / B 类分流 | B 类 15 个写 case 用临时实例；A 类 53 个读 case 用 m5air 现有 state |
| ADM-SL 5 → 7 个 case | FIXED_TIERS 约束（registry.py:292）让 POST 必有 400/409 两种路径；PATCH 必有 allowed-field 边界；DELETE 必为 409 fixed_service_level |
| DP-RESP-04 去掉 gemma 行为假设 | 原 case 测"gemma 是否调用工具"，是上游行为不是 LLMTier 契约；改成"LLMTier 透传 tools" |
| DP-RESP-03 fixture 改 390 关键词 | 原 "345" 关键词脆性——gemma 输出格式不固定 |
| DP-USAGE-04 改 sqlite3 UPDATE | 原 cursor="expired" 字面值是骗测试；现在真造 expired cursor |
| §6 缺口从 13 项压到 5 项 | 大部分已被 v0.3 fixture 解决 |
| case 总数 72 → 89 | 新增加强 case（DP-MODELS-07, DP-RESP-12~15, ADM-PROV-11~13, ADM-DEPL-06~09, ADM-SL-06~07, AUTH-07）|

---

## 7. 执行节奏

**单人 ~25h（3 个完整工作日）**：

```
Day 1：P0（3h） + P1 前半（5h）
Day 2：P1 后半（3h） + P2 conftest（3h） + P2 部分 case（2h）
Day 3：P2 收尾（3h） + P3（2h） + 评审（1h）
Day 4（可选）：P4
```

**双人 ~14h（1.5 天）**：

- A：P0 + P1（A 类 53 个，量大）
- B：P2 conftest + 19 个 B 类 case
- 共同：P3 + P4 评审

---

## 8. 验收标准（P3 阶段交付）

报告 `docs/70_verification/reports/llmtier-v0.3-api-test-report.md` 必须满足：

- [ ] 89 个 case 每个都有明确状态（PASS/FAIL/SKIP/BLOCKED）
- [ ] 0 个"未跑"
- [ ] FAIL + BLOCKED 总数 = 0
- [ ] SKIP ≤ 5，每个 SKIP 都有 §2.1 检查项引用 + fix_owner + ETA
- [ ] test plan §8 P1~P14 每条都验证已修复或明确未修复
- [ ] B 类跑完后 m5air 现有 state 未变（curl 比对前后 providers/deployments/service-levels 列表）

---

## 9. 文档索引

- 测试设计：[`llmtier-v0.3-api-test-plan.md`](./llmtier-v0.3-api-test-plan.md)（**v0.3.0-draft.3**）
- 高层 V&V：[`llmtier-v0.3-vv-plan.md`](./llmtier-v0.3-vv-plan.md)
- 系统测试：[`llmtier-v0.3-test-plan.md`](./llmtier-v0.3-test-plan.md)（ST-01~ST-26）
- 历史报告：`docs/70_verification/reports/2026-09-2{0,1}-test-report.md`
- m5air 部署：`docs/80_operations/manuals/m5air-deploy-guide.md`
- m5air 操作：`docs/80_operations/m5air-operations-manual.md`
- API handoff：`docs/80_operations/manuals/api-testing-handoff.md`
- 测试规范：`docs/00_management/standards/testing-standard.md`（TS-001~TS-005）
