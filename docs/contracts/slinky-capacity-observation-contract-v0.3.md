# llmtier 面向 Slinky 的 Capacity/Observation 契约提案 v0.3

Last Updated: 2026-09-06 15:34:00 +08:00

Status: Candidate；继承 v0.2 中已通过方向，并补 M4 机器语义验证

## 1. 保持不变的边界

Authority、共享/重叠 capacity group 的 all-constraints 投影、version/ETag/valid_until 以及 invalidation 不回滚 active IR 的设计保持 v0.2 语义。唯一计量单位仍为 `concurrent_invocation`，burst 不进入 committed Seat。

## 2. CapacitySnapshot 语义约束（M4）

JSON Schema 负责字段类型/必填/枚举；semantic validator 还必须满足：

1. `capacity_group_id` 在 snapshot 内唯一。
2. `service_level_id` 在 snapshot 内唯一。
3. `available_committed_concurrency <= committed_concurrency`。
4. group 的 `member_service_level_ids` 与 service level 的 `capacity_group_ids` 双向完全一致，且引用必须存在。
5. `observed_at < valid_until`；投影时还要求 evaluation time 不晚于 `valid_until`。
6. `request_quota_remaining=null` 允许作为 snapshot observation，但对该等级的新 committed Seat 投影必须返回 blocked：`client_quota_unknown`，不能按无限处理。
7. blocking reason 非空或 status 为 `Unavailable` 时，新投影为 blocked。

可执行负例位于 `fixtures/v0.3/capacity-semantic-negative-fixtures.json`；本地 test validator 对每个 mutation 断言预期 code。它证明 candidate 语义算法对这些输入 fail closed，不证明真实 API 已接入该 validator。

## 3. Metadata UTF-8 byte 语义（M4）

Manifest 的限制统一为 UTF-8 encoded bytes：key 64 bytes、value 512 bytes。JSON Schema 的 `maxLength` 只作为字符长度粗筛，并增加 `x-utf8-max-bytes` annotation；authoritative semantic validator 必须以 `len(value.encode("utf-8"))` 判断。

多字节正反例位于 `fixtures/v0.3/metadata-utf8-byte-fixtures.json`。超限分别返回 `metadata_key_too_large` 或 `metadata_value_too_large`，不得静默截断。

## 4. 证据状态

- Planned：真实 Capacity endpoint、admission 与 runtime validation wiring。
- Implemented：candidate semantic validator test harness 与 fixtures。
- Verified：duplicate IDs、available 超 committed、反向 membership、时间逆序、quota unknown 和 UTF-8 多字节限制的本地执行检查。
