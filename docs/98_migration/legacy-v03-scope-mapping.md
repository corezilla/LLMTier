# LLMTier C5 Legacy V0.3 Old-to-New Scope Mapping

Promotion 输入：`e1f9b796368ec5f358e466c7e6299cc16b1bf181`
规则：每个旧文档有效章节必须指向 successor Document ID/path、保留的机器 authority，并给出 residual。
`residual=none` 只表示正式 current prose 已有唯一 successor；旧 Git 历史和 review provenance 仍保留。

## 1. `docs/design/llmtier-v0.3-design-review.md`

旧文件 blob=`31370940272e51125c7c0900dcc30038c35eea9e`，SHA-256=
`ab0e305086e2cf73269efa06f3b3fb9bfc5908f99bbb9a902ad051b87ead5b08`。

| Old scope | Successor Document ID / path | Retained machine or execution authority | Disposition | Residual |
|---|---|---|---|---|
| §1 V0.3 交付目标 | `llmtier-v0.3-requirements` / `docs/10_requirements/llmtier-v0.3-requirements.md`; `llmtier-service-design` / `docs/30_subsystem_design/llmtier-service-design.md` | compatibility manifest v0.3 | canonical prose moves to successors | none |
| §2 责任与 authority | `llmtier-service-design`; three interface-control documents | OpenAPI/manifest remain LLMTier machine authority; Piko/Slinky keep external authority | canonical ownership prose moves | none |
| §3 系统分面 | `llmtier-service-design` | `src/` current implementation | canonical service decomposition moves | none |
| §4 Service Level Registry | `llmtier-service-design`; `llmtier-v0.3-contract-specification` / `docs/60_interfaces/contracts/llmtier-v0.3-contract-specification.md` | OpenAPI and compatibility manifest | canonical registry prose moves | none |
| §5.1 Data Plane surface | `llmtier-piko-data-plane-control` / `docs/60_interfaces/piko-data-plane-control.md`; `llmtier-v0.3-contract-specification` | OpenAPI v0.3 | canonical interface prose moves | none |
| §5.2 first/repeat/terminal | `llmtier-piko-data-plane-control`; `llmtier-v0.3-contract-test-specification` / `docs/70_verification/specifications/llmtier-v0.3-contract-test-specification.md` | recovery fixtures and tests | canonical recovery prose moves | none |
| §5.3 M2-C retention | `llmtier-piko-data-plane-control`; `llmtier-v0.3-requirements`; `llmtier-v0.3-traceability` | OpenAPI/manifest/fixtures/tests | canonical retention requirement moves; runtime evidence stays blocked | none |
| §6 Slinky Capacity/Observation | `llmtier-slinky-capacity-observation-control` / `docs/60_interfaces/slinky-capacity-observation-control.md` | OpenAPI and v0.3 capacity fixtures | canonical consumer boundary moves | none；Slinky `S-20260907-45938693e578` ACCEPTED exact draft.2 input |
| §7 Management API/Admin UI | `llmtier-management-control` / `docs/60_interfaces/llmtier-management-control.md` | OpenAPI and management fixtures/tests | canonical management prose moves | none |
| §8 Schema、安全与状态 | `llmtier-service-design`; three interface controls; `llmtier-v0.3-contract-specification` | OpenAPI/manifest/fixtures/tests | canonical cross-cutting prose moves | none |
| §9 Activation gates | `llmtier-v0.3-traceability`; `llmtier-v0.3-vv-plan` / `docs/70_verification/plans/llmtier-v0.3-vv-plan.md`; `llmtier-v0.3-release-and-operations` / `docs/80_operations/llmtier-v0.3-release-and-operations.md` | compatibility manifest keeps activation=false | gate prose moves; runtime remains independent | none |
| §10 实现顺序 | `llmtier-std-migration-plan` / `docs/98_migration/llmtier-std-migration-plan.md`; requirements traceability | source/tests remain implementation authority | historical planning sequence only | none |
| §11 本轮评审闭环 | C0-C4 review packets and machine decisions in `docs/91_reviews/` | Matrix messages and Git commits remain evidence | historical review provenance | none |
| §12 关联材料 | `current-document-inventory` / `docs/98_migration/current-document-inventory.md`; successor documents above | referenced artifacts remain at their canonical paths | navigation moves to README/inventory | none |

处置：全部有效 scope 均有 successor；Slinky 已接受 exact draft.2 immutable input，因此 residual=none，
旧文件在本次原子 promotion 中整体标为 Superseded。

## 2. `docs/contracts/piko-data-plane-contract-v0.3.md`

旧文件 blob=`0504fe4f977a6840ee8feeedf646183b81e210a6`，SHA-256=
`d22c494410cc9039afea7df6c3e49ea44921c3f40db1053898bd2b81e6621461`。

| Old scope | Successor Document ID / path | Retained machine or execution authority | Disposition | Residual |
|---|---|---|---|---|
| §1 authority/unique path | `llmtier-piko-data-plane-control` | compatibility manifest | canonical prose moves | none；Piko `P-20260907-e009921eda0a` ACCEPTED |
| §2 V0.3 surface | `llmtier-piko-data-plane-control`; `llmtier-v0.3-contract-specification` | OpenAPI v0.3 | canonical prose moves | none |
| §3 Service Level Registry | same two successors | OpenAPI/manifest | canonical prose moves | none |
| §4 identity/request/schema | same two successors | OpenAPI + authorization/metadata fixtures | canonical prose moves | none |
| §5 first/repeat/lost-response | `llmtier-piko-data-plane-control`; `llmtier-v0.3-contract-test-specification` | recovery fixtures/tests | canonical prose moves | none |
| §6 invocation/response recovery | same successors | OpenAPI + recovery fixtures/tests | canonical prose moves | none |
| §7 M2-C window | `llmtier-piko-data-plane-control`; requirements/traceability | OpenAPI/manifest/fixtures/tests | canonical prose moves | none |
| §8 deferred/Embeddings | `llmtier-piko-data-plane-control`; requirements/traceability | OpenAPI/manifest deferred-surface fixture | canonical fail-closed prose moves | none |
| §9 activation evidence | V&V plan, test specification, traceability, release/operations | compatibility manifest keeps activation=false | evidence ledger moves; L3 remains blocked | none |

处置：Piko verdict 已为 ACCEPTED，authority uniqueness 检查纳入 promotion Gate；residual=none，旧文件整体 Superseded。

## 3. `docs/contracts/slinky-capacity-observation-contract-v0.3.md`

旧文件 blob=`67dba4b033b184936de639684c48ac71693b41ee`，SHA-256=
`06167acbaa18f86c56ca094b650e6700b8a42ae86182cc81e3986e8becfebaf3`。

| Old scope | Successor Document ID / path | Retained machine or execution authority | Disposition | Residual |
|---|---|---|---|---|
| §1 authority/unique inference path | `llmtier-slinky-capacity-observation-control` | compatibility manifest | canonical prose moves | none；Slinky `S-20260907-45938693e578` ACCEPTED |
| §2 Observation surface | same successor; `llmtier-v0.3-contract-specification` | OpenAPI v0.3 | canonical prose moves | none |
| §3 Service Level Registry | same successors | OpenAPI/manifest | canonical prose moves | none |
| §4 CapacitySnapshot/Seat | same successor; test specification | OpenAPI + capacity fixtures/tests | canonical prose moves | none |
| §5 version/ETag/invalidation | same successor; test specification | OpenAPI + fixtures/tests | canonical prose moves | none |
| §6 retention/recovery observation | same successor; requirements/traceability | OpenAPI/recovery fixtures/tests | canonical prose moves | none |
| §7 metadata/evidence state | V&V plan, test specification, traceability | fixtures/tests | evidence ledger moves; production remains blocked | none |

处置：Slinky verdict 已为 ACCEPTED，authority uniqueness 检查纳入 promotion Gate；residual=none，旧文件整体 Superseded。

## 4. `docs/contracts/llmtier-management-contract-v0.3.md`

旧文件 blob=`fa30007750463b70943408042f1c212d8efa0445`，SHA-256=
`d4ff45c073b13a90533b91559831ed42ead6bfad38ed06c60e17a7f5d3c1433e`。

| Old scope | Successor Document ID / path | Retained machine or execution authority | Disposition | Residual |
|---|---|---|---|---|
| §1 authority/access boundary | `llmtier-management-control` | compatibility manifest | canonical prose moves | none |
| §2/§2.1 API surface/endpoints | `llmtier-management-control`; `llmtier-v0.3-contract-specification` | OpenAPI v0.3 + management fixtures/tests | canonical prose moves | none |
| §3 minimum Admin UI | `llmtier-management-control`; requirements/traceability | no current UI implementation evidence | required/open-gate prose moves | none; implementation remains blocked |
| §4 consistency/activation | management control, V&V plan, release/operations | compatibility manifest keeps activation=false | gate prose moves | none |

处置：全部正式 prose scope 已映射，旧文件整体 Superseded；未实现 UI 是 successor 中的 Open Gate，不是旧文档 residual。

## 5. `docs/qa/llm-tier-contract-qa-v0.3.md`

旧文件 blob=`24f42a02eb9012631f54dfe217ae578e18262062`，SHA-256=
`7ce467ab0c5c4bd5d4ef25bbf708f4b2d9dac786217c57113d994bc37da70277`。

| Old scope | Successor Document ID / path | Retained machine or execution authority | Disposition | Residual |
|---|---|---|---|---|
| §1 Slinky amendment traceability | `llmtier-v0.3-traceability`; C1/C2 review packets | Matrix verdict IDs and Git commits | traceability moves; message IDs retained as evidence | none；Slinky `S-20260907-45938693e578` ACCEPTED |
| §2 machine-readable consistency | `llmtier-v0.3-contract-specification`; test specification | OpenAPI/manifest/fixtures/tests | canonical validation index moves | none |
| §3 Piko review traceability | `llmtier-v0.3-traceability`; C1/C2 review packets | Matrix verdict IDs and Git commits | traceability moves; message IDs retained as evidence | none；Piko `P-20260907-e009921eda0a` ACCEPTED |
| §4 evidence boundary | V&V plan, test specification, traceability | tests/fixtures and future runtime artifacts | canonical evidence boundary moves | none |
| §5 remaining blockers | requirements/traceability, V&V plan, release/operations | runtime/external evidence remains NOT_RUN/BLOCKED | blocker ledger moves without converting to PASS | none |

处置：两方 consumer verdict 可审计且均为 ACCEPTED，Owner verdict 已完成，authority uniqueness 检查纳入
promotion Gate；§1/§3 residual=none，旧 QA 整体 Superseded。

## 6. 单一 current authority 检查

Promotion candidate 的机器检查规则：

1. 上述五份旧文件每个有效 heading 均恰有 mapping row；
2. successor Document ID 在项目 metadata 中唯一，path 与 metadata `source_path` 一致；
3. current prose scope 只能在拟 Approved successor 中出现；旧文件必须有 Superseded forward link；
4. OpenAPI/manifest/fixtures/tests 的 machine/execution authority 不被 prose 复制或降级；
5. Piko/Slinky verdict 均为 ACCEPTED，且 evidence ledger 中 commit/blob/SHA-256 与 Matrix ID 完整；
6. Runtime Activation 保持 false，L3 NOT_RUN/BLOCKED 不因文档 review 改写。

本次 promotion candidate 的上述检查由 `tests/test_std_migration.py` 执行；原始结果记录在
`docs/98_migration/evidence/c5-promotion-validation-evidence.txt`。旧文件继续保留在 Git 中，不移动、删除或
丢失历史；Superseded 仅退出 current prose authority。
