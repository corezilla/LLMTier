from __future__ import annotations

from dataclasses import dataclass


# 用途：
# - 表达一次运行身份解析后的统一执行层级与语义角色
# 输入：
# - execution_level/role_profile: 规范化后的层级与 profile
# 输出：
# - 可被日志、metadata 和 stats 共用的 ExecutionIdentity
@dataclass(frozen=True)
class ExecutionIdentity:
    execution_level: str
    role_profile: str


_SPECIAL_ROLE_IDENTITIES: dict[str, ExecutionIdentity] = {
    "escalator": ExecutionIdentity(execution_level="senior", role_profile="override"),
    "review_arbiter": ExecutionIdentity(execution_level="senior", role_profile="override"),
    "research_discovery_author": ExecutionIdentity(execution_level="junior", role_profile="planner"),
    "research_decision_author": ExecutionIdentity(execution_level="junior", role_profile="planner"),
    "research_publish_author": ExecutionIdentity(execution_level="worker", role_profile="author"),
    "drift_controller": ExecutionIdentity(execution_level="junior", role_profile="planner"),
    "drift_risk_manager": ExecutionIdentity(execution_level="junior", role_profile="planner"),
    "drift_classifier": ExecutionIdentity(execution_level="worker", role_profile="validator"),
    "rag_judger": ExecutionIdentity(execution_level="worker", role_profile="validator"),
    "preflight_engineer": ExecutionIdentity(execution_level="worker", role_profile="validator"),
}


# 用途：
# - 把当前旧式 role_name 收敛为 spec/43 的统一执行层级与 role_profile
# 输入：
# - role_name: 当前运行使用的稳定 role 名称
# 输出：
# - 规范化后的 ExecutionIdentity；缺少显式映射时按后缀规则回退
def resolve_execution_identity_for_role(role_name: str) -> ExecutionIdentity:
    normalized_role = str(role_name or "").strip().lower()
    if not normalized_role:
        return ExecutionIdentity(execution_level="worker", role_profile="author")
    special = _SPECIAL_ROLE_IDENTITIES.get(normalized_role)
    if special is not None:
        return special
    if normalized_role.endswith("_author"):
        return ExecutionIdentity(execution_level="worker", role_profile="author")
    if normalized_role.endswith("_reviewer"):
        return ExecutionIdentity(execution_level="worker", role_profile="reviewer")
    if normalized_role.endswith("_reviser"):
        return ExecutionIdentity(execution_level="worker", role_profile="reviser")
    if normalized_role.endswith("_fixer"):
        return ExecutionIdentity(execution_level="worker", role_profile="fixer")
    if "validator" in normalized_role:
        return ExecutionIdentity(execution_level="worker", role_profile="validator")
    if "planner" in normalized_role:
        return ExecutionIdentity(execution_level="junior", role_profile="planner")
    if "debug" in normalized_role:
        return ExecutionIdentity(execution_level="junior", role_profile="debugger")
    return ExecutionIdentity(execution_level="worker", role_profile="author")
