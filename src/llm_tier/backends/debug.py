from __future__ import annotations

import json
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from llm_tier.backends import register_backend
from llm_tier.backends.base import BaseBackendClient
from llm_tier.exceptions import BackendCallError, QuotaExhaustedError


# 用途：
# - 将 debug backend 配置中的文件路径解析成绝对路径
# 输入：
# - path_value: 配置或 metadata 里的文件路径
# - base_dir: 相对路径参考目录
# 输出：
# - 绝对 Path；空路径时返回 None
def _resolve_path(path_value: str, *, base_dir: Path) -> Path | None:
    normalized = str(path_value or "").strip()
    if not normalized:
        return None
    candidate = Path(normalized).expanduser()
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return candidate.resolve()


# 用途：
# - 从 JSON 或文本文件加载 debug backend 响应内容
# 输入：
# - path_value: 文件路径
# - base_dir: 相对路径参考目录
# 输出：
# - 文件正文；JSON 文件会 pretty print，读取失败时抛 BackendCallError
def _read_content_file(path_value: str, *, base_dir: Path) -> str:
    content_path = _resolve_path(path_value, base_dir=base_dir)
    if content_path is None or not content_path.is_file():
        raise BackendCallError("debug", f"debug content file not found: {path_value}")
    try:
        raw_text = content_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BackendCallError("debug", f"debug content file unreadable: {content_path}", original_error=exc) from exc
    if content_path.suffix.lower() != ".json":
        return raw_text
    try:
        return json.dumps(json.loads(raw_text), ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        return raw_text


# 用途：
# - 读取当前 workspace 的 Research routing authority，供 requirement assessment fixture 对齐当前真实流程选择
# 输入：
# - workspace_root: metadata 中声明的 workspace 根目录
# 输出：
# - research/index.json payload；缺失或非法时返回空字典，保持 debug backend 容错
def _read_workspace_research_payload(workspace_root: str) -> dict[str, Any]:
    root = Path(str(workspace_root or "").strip()).expanduser()
    if not str(root):
        return {}
    research_index = root / "docs" / "research" / "index.json"
    if not research_index.is_file():
        return {}
    try:
        payload = json.loads(research_index.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


# 用途：
# - 按当前 workspace 的 Research routing authority 修正 requirement assessment fixture 的机器可读块
# 输入：
# - content: 冻结 requirement fixture 正文
# - metadata: 当前 role prompt metadata，至少包含 workspace_root
# 输出：
# - 已与当前 research/index.json 对齐的 requirement fixture 正文
def _specialize_requirement_author_content(content: str, *, metadata: Mapping[str, object]) -> str:
    research_payload = _read_workspace_research_payload(str(metadata.get("workspace_root") or ""))
    routing_mode = str(
        research_payload.get("routing_mode") or research_payload.get("process_selection") or ""
    ).strip()
    if routing_mode not in {
        "multi_subsystem_flow",
        "single_component_flow",
        "single_module_flow",
    }:
        return content
    enable_subsystem_design = research_payload.get("enable_subsystem_design")
    enable_module_design = research_payload.get("enable_module_design")
    if not isinstance(enable_subsystem_design, bool) or not isinstance(enable_module_design, bool):
        return content
    design_topology = {
        "multi_subsystem_flow": {
            "runtime_boundaries": ["api_adapter", "task_ledger", "audit_log"],
            "subsystem_strategy": "required",
            "module_strategy": "from_subsystem_design",
            "isd_strategy": "file_level_from_module_design",
        },
        "single_component_flow": {
            "runtime_boundaries": ["single_deployable_application"],
            "subsystem_strategy": "skip",
            "module_strategy": "direct_from_system_design",
            "isd_strategy": "file_level_from_module_design",
        },
        "single_module_flow": {
            "runtime_boundaries": ["single_module"],
            "subsystem_strategy": "skip",
            "module_strategy": "skip",
            "isd_strategy": "direct_from_system_design",
        },
    }[routing_mode]
    technical_options = {
        "multi_subsystem_flow": {
            "option_id": "multi_subsystem_split",
            "summary": "CLI、HTTP adapter、Task Ledger 与 Audit Log 分层协作",
            "fit": "high",
            "tradeoffs": ["设计链更长", "边界清晰，便于独立验证"],
        },
        "single_component_flow": {
            "option_id": "single_cli_service",
            "summary": "单一 CLI/service 与 SQLite authority",
            "fit": "high",
            "tradeoffs": ["部署简单", "不提供独立分布式边界"],
        },
        "single_module_flow": {
            "option_id": "single_module_runtime",
            "summary": "单模块内完成公开入口、持久化与审计",
            "fit": "high",
            "tradeoffs": ["实现最短", "边界最少，扩展空间更小"],
        },
    }[routing_mode]
    rationale = {
        "multi_subsystem_flow": "Research authority 已确认存在多个协作边界，需要保留 Subsystem Design。",
        "single_component_flow": "Research authority 已确认单一 deployable application 即可覆盖当前需求。",
        "single_module_flow": "Research authority 已确认单模块形态足以覆盖当前需求。",
    }[routing_mode]
    replacement_payload = {
        "schema_version": 1,
        "routing_mode": routing_mode,
        "process_selection": routing_mode,
        "enable_subsystem_design": enable_subsystem_design,
        "enable_module_design": enable_module_design,
        "enable_isd_design": True,
        "technical_options": [technical_options],
        "design_topology": design_topology,
        "decision_rationale": [rationale],
        "risks": [],
        "review_notes": [],
    }
    replacement_block = "```json\n" + json.dumps(replacement_payload, ensure_ascii=False, indent=2) + "\n```"
    return content.replace(
        "```json\n{\n  \"schema_version\": 1,\n  \"routing_mode\": \"single_component_flow\",\n  \"process_selection\": \"single_component_flow\",\n  \"enable_subsystem_design\": false,\n  \"enable_module_design\": true,\n  \"enable_isd_design\": true,\n  \"technical_options\": [\n    {\n      \"option_id\": \"single_cli_service\",\n      \"summary\": \"单一 CLI/service 与 SQLite authority\",\n      \"fit\": \"high\",\n      \"tradeoffs\": [\"部署简单\", \"不提供独立分布式边界\"]\n    }\n  ],\n  \"design_topology\": {\n    \"runtime_boundaries\": [\"single_deployable_application\"],\n    \"subsystem_strategy\": \"skip\",\n    \"module_strategy\": \"direct_from_system_design\",\n    \"isd_strategy\": \"file_level_from_module_design\"\n  },\n  \"decision_rationale\": [\n    \"需求没有证明存在多个独立 deployable 或 runtime boundary。\"\n  ],\n  \"risks\": [],\n  \"review_notes\": []\n}\n```",
        replacement_block,
    )


# Purpose: Align one controlled Unit Test catalog fixture with its function-level source authority.
# Inputs: Frozen catalog JSON and Role prompt metadata containing workspace_root and task_key.
# Outputs: Catalog JSON whose entrypoint and interface identity match the current catalog index item.
def _specialize_unit_test_case_catalog_content(
    content: str,
    *,
    metadata: Mapping[str, object],
) -> str:
    workspace_root = Path(str(metadata.get("workspace_root") or "").strip()).expanduser()
    task_key = str(metadata.get("task_key") or "").strip()
    catalog_index_path = workspace_root / "test" / "unit" / "catalog" / "index.json"
    if not task_key or not catalog_index_path.is_file():
        return content
    try:
        template = json.loads(content)
        catalog_index = json.loads(catalog_index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return content
    if not isinstance(template, list) or not template or not isinstance(catalog_index, dict):
        return content
    source_item = next(
        (
            item
            for item in catalog_index.get("items", [])
            if isinstance(item, dict) and str(item.get("task_key") or "").strip().lower() == task_key.lower()
        ),
        None,
    )
    if not isinstance(source_item, dict):
        return content
    output = source_item.get("output") if isinstance(source_item.get("output"), dict) else {}
    entrypoint = str(output.get("source_entrypoint") or "").strip()
    if not entrypoint:
        return content

    specialized: list[object] = []
    for raw_row in template:
        if not isinstance(raw_row, dict):
            specialized.append(raw_row)
            continue
        row = dict(raw_row)
        previous_entrypoint = str(row.get("source_entrypoint") or "").strip()
        row["source_entrypoint"] = entrypoint
        row["source_schema_id"] = str(output.get("schema_id") or row.get("source_schema_id") or "").strip()
        row["source_interface_id"] = str(
            output.get("source_interface_id") or row.get("source_interface_id") or ""
        ).strip()
        row["module_interface_schema_path"] = str(
            output.get("module_interface_schema_path")
            or row.get("module_interface_schema_path")
            or ""
        ).strip()
        behavior_chain = row.get("behavior_chain")
        if isinstance(behavior_chain, list):
            row["behavior_chain"] = [
                {
                    **dict(step),
                    "symbol": (
                        entrypoint
                        if isinstance(step, dict)
                        and previous_entrypoint
                        and str(step.get("symbol") or "").strip() == previous_entrypoint
                        else str(step.get("symbol") or "")
                    ),
                }
                if isinstance(step, dict)
                else step
                for step in behavior_chain
            ]
        specialized.append(row)
    return json.dumps(specialized, ensure_ascii=False, indent=2)


# Purpose: Resolve the current Unit Test case identity and source entrypoint from accepted catalog authority.
# Inputs: Role prompt metadata containing workspace_root and task_key.
# Outputs: Canonical case id and public source entrypoint, or empty values when authority is unavailable.
def _unit_test_case_identity(metadata: Mapping[str, object]) -> tuple[str, str]:
    workspace_root = Path(str(metadata.get("workspace_root") or "").strip()).expanduser()
    task_key = str(metadata.get("task_key") or "").strip().upper()
    case_id = task_key.replace("_", ".")
    catalog_id = case_id.split(".", 1)[0]
    catalog_path = workspace_root / "test" / "unit" / "catalog" / f"{catalog_id}.json"
    if not case_id or not catalog_path.is_file():
        return case_id, ""
    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return case_id, ""
    entrypoint = (
        str(payload.get("source_entrypoint") or "").strip()
        if isinstance(payload, dict)
        else ""
    )
    return case_id, entrypoint


# Purpose: Align a controlled Unit Test case with its accepted function-level catalog authority.
# Inputs: Frozen case JSON and current Role prompt metadata.
# Outputs: Case JSON with method-specific stimulus, expected result, and source references.
def _specialize_unit_test_case_content(content: str, *, metadata: Mapping[str, object]) -> str:
    case_id, entrypoint = _unit_test_case_identity(metadata)
    method_name = entrypoint.rsplit(".", 1)[-1]
    if method_name not in {"create_task", "get_task", "complete_task", "list_tasks"}:
        return content
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return content
    if not isinstance(payload, dict):
        return content
    contracts = {
        "create_task": {
            "objective": "Verify create_task persists the returned Task and one task.created Audit Event.",
            "calls": ["create_task('Task 1', 'request-create')"],
            "expected": {"task": {"task_id": "T0001", "title": "Task 1", "status": "open"}, "event_types": ["task.created"]},
        },
        "get_task": {
            "objective": "Verify get_task returns the matching Task without mutating repository state.",
            "calls": ["get_task('T0001', 'request-get')"],
            "expected": {"task": {"task_id": "T0001", "title": "Task 1", "status": "open"}, "event_types": []},
        },
        "complete_task": {
            "objective": "Verify complete_task persists done state and repeated completion is idempotent.",
            "calls": ["complete_task('T0001', 'request-complete')", "complete_task('T0001', 'request-repeat')"],
            "expected": {"task": {"task_id": "T0001", "title": "Task 1", "status": "done"}, "event_types": ["task.completed"]},
        },
        "list_tasks": {
            "objective": "Verify list_tasks returns stable insertion-order copies without mutation.",
            "calls": ["list_tasks('request-list')"],
            "expected": {"tasks": [{"task_id": "T0001", "title": "Task 1", "status": "open"}, {"task_id": "T0002", "title": "Task 2", "status": "done"}], "event_types": []},
        },
    }[method_name]
    payload.update(
        {
            "case_name": f"case_{case_id.lower().replace('.', '_')}_{method_name}",
            "case_path": f"test/unit/case/{case_id}.json",
            "target_module": "src/task_ledger/service.py",
            "objective": contracts["objective"],
            "related_files": ["src/task_ledger/service.py"],
            "related_symbols": [entrypoint],
            "setup": {
                "imports": ["from task_ledger.service import TaskService"],
                "store": "case-local in-memory repository",
                "clock": "2026-07-22T00:00:00+00:00",
            },
            "stimulus": {"calls": contracts["calls"]},
            "expected": contracts["expected"],
        }
    )
    return json.dumps(payload, ensure_ascii=False, indent=2)


# Purpose: Generate a controlled executable Unit Test script from the accepted case and catalog authorities.
# Inputs: Frozen script fallback and current Role prompt metadata.
# Outputs: Self-contained script exercising the selected public TaskService method with final-state assertions.
def _specialize_unit_test_script_content(content: str, *, metadata: Mapping[str, object]) -> str:
    case_id, entrypoint = _unit_test_case_identity(metadata)
    method_name = entrypoint.rsplit(".", 1)[-1]
    if method_name not in {"create_task", "get_task", "complete_task", "list_tasks"}:
        return content
    exercise = {
        "create_task": "result = service.create_task(\"Task 1\", \"request-create\")",
        "get_task": "result = service.get_task(\"T0001\", \"request-get\")",
        "complete_task": "service.complete_task(\"T0001\", \"request-complete\")\n        result = service.complete_task(\"T0001\", \"request-repeat\")",
        "list_tasks": "result = service.list_tasks(\"request-list\")",
    }[method_name]
    initial_tasks = {
        "create_task": "[]",
        "get_task": '[{"task_id": "T0001", "title": "Task 1", "status": "open"}]',
        "complete_task": '[{"task_id": "T0001", "title": "Task 1", "status": "open"}]',
        "list_tasks": '[{"task_id": "T0001", "title": "Task 1", "status": "open"}, {"task_id": "T0002", "title": "Task 2", "status": "done"}]',
    }[method_name]
    expected_result = {
        "create_task": '{"task_id": "T0001", "title": "Task 1", "status": "open"}',
        "get_task": '{"task_id": "T0001", "title": "Task 1", "status": "open"}',
        "complete_task": '{"task_id": "T0001", "title": "Task 1", "status": "done"}',
        "list_tasks": initial_tasks,
    }[method_name]
    expected_events = {
        "create_task": '["task.created"]',
        "get_task": "[]",
        "complete_task": '["task.completed"]',
        "list_tasks": "[]",
    }[method_name]
    next_id = 1 if method_name == "create_task" else 3 if method_name == "list_tasks" else 2
    function_name = f"run_case_{case_id.lower().replace('.', '_')}_{method_name}"
    return f'''from copy import deepcopy

from unit_test_runner import exception_result, failed, passed, run_unit_test_script


class MemoryRepository:
    def __init__(self):
        self.snapshot = {{"next_id": {next_id}, "tasks": {initial_tasks}, "events": []}}

    def load(self):
        return deepcopy(self.snapshot)

    def commit(self, snapshot):
        self.snapshot = deepcopy(snapshot)


def {function_name}(workspace_root):
    del workspace_root
    test_id = "{case_id}"
    related_files = ["src/task_ledger/service.py"]
    related_symbols = ["{entrypoint}"]
    expected = {{"result": {expected_result}, "event_types": {expected_events}}}
    try:
        from task_ledger.service import TaskService

        repository = MemoryRepository()
        service = TaskService(repository, clock=lambda: "2026-07-22T00:00:00+00:00")
        {exercise}
        actual = {{"result": result, "event_types": [row["event_type"] for row in repository.snapshot["events"]]}}
    except Exception as exc:
        return exception_result(test_id, exc, related_files=related_files, related_symbols=related_symbols, expected=expected)
    if actual == expected:
        return passed(test_id, message="public behavior and final state match", related_files=related_files, related_symbols=related_symbols, expected=expected, actual=actual)
    return failed(test_id, message="public behavior or final state mismatch", related_files=related_files, related_symbols=related_symbols, expected=expected, actual=actual)


if __name__ == "__main__":
    raise SystemExit(run_unit_test_script([{function_name}]))
'''


# 用途：
# - 按当前 Scenario Index authority 专门化受控 Scenario Design fixture，避免并行 Task 共用错误身份
# 输入：
# - content: 冻结 Scenario Design JSON 正文
# - metadata: 当前 role prompt metadata，包含 workspace_root 与 task_key
# 输出：
# - 与当前 Scenario Task 的身份、追踪义务和 Family obligation 对齐的 JSON 正文
def _specialize_system_testing_scenario_design_content(
    content: str,
    *,
    metadata: Mapping[str, object],
) -> str:
    workspace_root = Path(str(metadata.get("workspace_root") or "").strip()).expanduser()
    task_key = str(metadata.get("task_key") or "").strip()
    scenario_index_path = workspace_root / "test" / "system" / "scenario" / "index.json"
    if not task_key or not scenario_index_path.is_file():
        return content
    try:
        template = json.loads(content)
        scenario_index = json.loads(scenario_index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return content
    if not isinstance(template, dict) or not isinstance(scenario_index, dict):
        return content
    source_item = next(
        (
            item
            for item in scenario_index.get("items", [])
            if isinstance(item, dict) and str(item.get("task_key") or "").strip() == task_key
        ),
        None,
    )
    if not isinstance(source_item, dict):
        return content

    source_input = source_item.get("input") if isinstance(source_item.get("input"), dict) else {}
    scenario_id = str(source_item.get("scenario_id") or task_key).strip()
    coverage_ids = [str(value) for value in source_item.get("coverage_ids", []) if str(value).strip()]
    design_rule_ids = [str(value) for value in source_item.get("design_rule_ids", []) if str(value).strip()]
    case_rule_ids = [
        str(value) for value in source_item.get("case_generation_rule_ids", []) if str(value).strip()
    ]
    requirement_ids = [str(value) for value in source_item.get("requirement_ids", []) if str(value).strip()]
    criterion_ids = [str(value) for value in source_item.get("criterion_ids", []) if str(value).strip()]
    family = dict(template.get("case_family_obligations", [{}])[0])
    family.update(
        {
            "family_obligation_id": f"FAM_{task_key}",
            "coverage_ids": coverage_ids,
            "design_rule_ids": design_rule_ids,
            "case_generation_rule_ids": case_rule_ids,
            "family_objective": str(source_input.get("scenario_objective") or source_item.get("scenario_scope") or "").strip(),
        }
    )
    template.update(
        {
            "scenario_id": scenario_id,
            "scenario_name": str(source_item.get("scenario_name") or scenario_id).strip(),
            "suite_ids": [str(value) for value in source_item.get("suite_ids", []) if str(value).strip()],
            "behavior_path": str(source_item.get("scenario_scope") or "system behavior").strip(),
            "entrypoints": ["python -m task_ledger.cli"],
            "case_family_obligations": [family],
            "family_count_lower_bound": 1,
            "traceability": {
                "requirement_ids": requirement_ids,
                "criterion_ids": criterion_ids,
                "coverage_ids": coverage_ids,
            },
        }
    )
    return json.dumps(template, ensure_ascii=False, indent=2)


# 用途：
# - 按当前 Family Index authority 专门化受控 Family Design fixture
# 输入：
# - content: 冻结 Family Design JSON 正文
# - metadata: 当前 role prompt metadata，包含 workspace_root 与 task_key
# 输出：
# - 与当前 Family Task 身份、Scenario 来源和 Case variant 义务一致的 JSON 正文
def _specialize_system_testing_family_design_content(
    content: str,
    *,
    metadata: Mapping[str, object],
) -> str:
    workspace_root = Path(str(metadata.get("workspace_root") or "").strip()).expanduser()
    task_key = str(metadata.get("task_key") or "").strip()
    family_index_path = workspace_root / "test" / "system" / "family" / "index.json"
    if not task_key or not family_index_path.is_file():
        return content
    try:
        template = json.loads(content)
        family_index = json.loads(family_index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return content
    if not isinstance(template, dict) or not isinstance(family_index, dict):
        return content
    source_item = next(
        (
            item
            for item in family_index.get("items", [])
            if isinstance(item, dict) and str(item.get("task_key") or "").strip() == task_key
        ),
        None,
    )
    if not isinstance(source_item, dict):
        return content

    source_input = source_item.get("input") if isinstance(source_item.get("input"), dict) else {}
    family_id = str(source_item.get("family_id") or task_key).strip()
    scenario_id = str(source_item.get("scenario_id") or "").strip()
    coverage_ids = [str(value) for value in source_item.get("coverage_ids", []) if str(value).strip()]
    design_rule_ids = [str(value) for value in source_item.get("design_rule_ids", []) if str(value).strip()]
    case_rule_ids = [
        str(value) for value in source_item.get("case_generation_rule_ids", []) if str(value).strip()
    ]
    variant = dict(template.get("required_case_variants", [{}])[0])
    variant.update(
        {
            "case_variant_id": f"VAR_{task_key.replace('.', '_')}",
            "coverage_ids": coverage_ids,
            "design_rule_ids": design_rule_ids,
            "case_generation_rule_ids": case_rule_ids,
        }
    )
    template.update(
        {
            "family_id": family_id,
            "family_design_id": family_id,
            "family_type": str(source_item.get("family_type") or "functional_and_negative").strip(),
            "scenario_id": scenario_id,
            "scenario_design_id": str(source_item.get("scenario_design_id") or scenario_id).strip(),
            "suite_ids": [str(value) for value in source_item.get("suite_ids", []) if str(value).strip()],
            "family_objective": str(source_input.get("family_objective") or "Verify the declared family behavior.").strip(),
            "coverage_ids": coverage_ids,
            "design_rule_ids": design_rule_ids,
            "case_generation_rule_ids": case_rule_ids,
            "required_case_variants": [variant],
            "case_count_lower_bound": 1,
            "traceability": {
                "requirement_ids": [str(value) for value in source_item.get("requirement_ids", []) if str(value).strip()],
                "criterion_ids": [str(value) for value in source_item.get("criterion_ids", []) if str(value).strip()],
                "coverage_ids": coverage_ids,
            },
        }
    )
    return json.dumps(template, ensure_ascii=False, indent=2)


# 用途：
# - 按当前 Case Design Index authority 专门化受控 Case Design Markdown fixture
# 输入：
# - content: 含稳定占位符的冻结 Case Design Markdown
# - metadata: 当前 role prompt metadata，包含 workspace_root 与 task_key
# 输出：
# - 与当前 Case Plan 身份、数据规则、Oracle 和 traceability 对齐的 Markdown
def _specialize_system_testing_case_design_content(
    content: str,
    *,
    metadata: Mapping[str, object],
) -> str:
    workspace_root = Path(str(metadata.get("workspace_root") or "").strip()).expanduser()
    task_key = str(metadata.get("task_key") or "").strip()
    case_index_path = workspace_root / "test" / "system" / "case_design" / "index.json"
    if not task_key or not case_index_path.is_file():
        return content
    try:
        case_index = json.loads(case_index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return content
    if not isinstance(case_index, dict):
        return content
    source_item = next(
        (
            item
            for item in case_index.get("items", [])
            if isinstance(item, dict) and str(item.get("task_key") or "").strip() == task_key
        ),
        None,
    )
    if not isinstance(source_item, dict):
        return content
    source_input = source_item.get("input") if isinstance(source_item.get("input"), dict) else {}

    def _ids(field_name: str) -> str:
        values = [str(value) for value in source_item.get(field_name, []) if str(value).strip()]
        return ", ".join(f"`{value}`" for value in values)

    replacements = {
        "<case_key>": task_key,
        "<case_id>": str(source_item.get("case_id") or task_key).strip(),
        "<scenario_id>": str(source_item.get("scenario_id") or "").strip(),
        "<scenario_design_id>": str(source_item.get("scenario_design_id") or "").strip(),
        "<family_id>": str(source_item.get("family_id") or "").strip(),
        "<family_design_id>": str(source_item.get("family_design_id") or "").strip(),
        "<variant_source>": str(source_input.get("case_variant_id") or source_item.get("variant_source") or "family obligation").strip(),
        "<coverage_intent>": str(source_input.get("coverage_intent") or "验证声明的系统行为。 ").strip(),
        "<test_data_intent>": "构造隔离、确定且可重复的 CLI 输入与 store 状态。",
        "<oracle_intent>": "比较真实进程输出、typed error 和持久化 authority 状态。",
        "<coverage_ids>": _ids("coverage_ids"),
        "<design_rule_ids>": _ids("design_rule_ids"),
        "<case_rule_ids>": _ids("case_generation_rule_ids"),
        "<requirement_ids>": _ids("requirement_ids"),
        "<criterion_ids>": _ids("criterion_ids"),
    }
    specialized = content
    for placeholder, value in replacements.items():
        specialized = specialized.replace(placeholder, value)
    return specialized


# 用途：
# - 按当前 Case Design Index authority 专门化受控可执行 Case JSON fixture
# 输入：
# - content: 冻结 Case JSON 正文
# - metadata: 当前 role prompt metadata，包含 workspace_root 与 task_key
# 输出：
# - 与当前 Case 身份、追踪义务和 case-local data/script 路径一致的 JSON 正文
def _specialize_system_testing_case_content(
    content: str,
    *,
    metadata: Mapping[str, object],
) -> str:
    workspace_root = Path(str(metadata.get("workspace_root") or "").strip()).expanduser()
    task_key = str(metadata.get("task_key") or "").strip()
    case_index_path = workspace_root / "test" / "system" / "case_design" / "index.json"
    if not task_key or not case_index_path.is_file():
        return content
    try:
        template = json.loads(content)
        case_index = json.loads(case_index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return content
    if not isinstance(template, dict) or not isinstance(case_index, dict):
        return content
    source_item = next(
        (
            item
            for item in case_index.get("items", [])
            if isinstance(item, dict) and str(item.get("task_key") or "").strip() == task_key
        ),
        None,
    )
    if not isinstance(source_item, dict):
        return content
    source_input = source_item.get("input") if isinstance(source_item.get("input"), dict) else {}
    template.update(
        {
            "case_id": str(source_item.get("case_id") or task_key).strip(),
            "name": str(source_input.get("coverage_intent") or f"系统测试 {task_key}").strip(),
            "case_design_path": str(source_item.get("case_design_path") or f"test/system/case/{task_key}/design.md").strip(),
            "scenario_id": str(source_item.get("scenario_id") or "").strip(),
            "scenario_design_id": str(source_item.get("scenario_design_id") or "").strip(),
            "family_id": str(source_item.get("family_id") or "").strip(),
            "family_design_id": str(source_item.get("family_design_id") or "").strip(),
            "suite_ids": [str(value) for value in source_item.get("suite_ids", []) if str(value).strip()],
            "coverage_ids": [str(value) for value in source_item.get("coverage_ids", []) if str(value).strip()],
            "design_rule_ids": [str(value) for value in source_item.get("design_rule_ids", []) if str(value).strip()],
            "case_generation_rule_ids": [str(value) for value in source_item.get("case_generation_rule_ids", []) if str(value).strip()],
            "case_variant": str(source_input.get("case_variant") or "functional_and_negative").strip(),
            "variant_source": str(source_input.get("case_variant_id") or source_item.get("variant_source") or "family obligation").strip(),
            "requirement_ids": [str(value) for value in source_item.get("requirement_ids", []) if str(value).strip()],
            "criterion_ids": [str(value) for value in source_item.get("criterion_ids", []) if str(value).strip()],
        }
    )
    return json.dumps(template, ensure_ascii=False, indent=2)


# 用途：
# - 按当前 Data Task identity 构造可被下游 Script 真实消费的受控输入
# 输入：
# - content: 冻结 Case Data JSON 正文
# - metadata: 当前 role prompt metadata，包含 task_key
# 输出：
# - 具有独立 identity、store 和场景命令序列的 JSON 正文
def _specialize_system_testing_case_data_content(
    content: str,
    *,
    metadata: Mapping[str, object],
) -> str:
    task_key = str(metadata.get("task_key") or "").strip()
    if not task_key:
        return content
    case_key = task_key.rsplit(".D", 1)[0]
    scenario_key = case_key.split(".", 1)[0]
    command_sets = {
        "S1": ["create", "get"],
        "S2": ["create", "complete", "restart", "list"],
        "S3": ["create", "get_missing"],
        "S4": ["create", "complete", "read_audit"],
        "S5": ["unknown_command", "invalid_store_path"],
    }
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return content
    if not isinstance(payload, dict):
        return content
    safe_identity = case_key.lower().replace(".", "_")
    payload.update(
        {
            "case_key": case_key,
            "scenario_key": scenario_key,
            "task_id": f"task_{safe_identity}",
            "title": f"受控系统测试任务 {case_key}",
            "request_id": f"request_{safe_identity}",
            "store_path": f"data/{safe_identity}_tasks.json",
            "commands": command_sets.get(scenario_key, ["create", "get"]),
        }
    )
    return json.dumps(payload, ensure_ascii=False, indent=2)


# 用途：
# - debug backend：不真实调用 LLM，而是从场景文件返回固定成功内容或固定错误
# 输入：
# - scenario_file/content/default_content/latency_ms: backend 初始化配置
# 输出：
# - 可被 llm_tier router 调用的 backend client
class DebugBackendClient(BaseBackendClient):
    # 用途：
    # - 初始化 debug backend 的默认场景配置
    # 输入：
    # - scenario_file/content/default_content/latency_ms/kwargs: backend 凭证和默认行为
    # 输出：
    # - 可在每次 call 中用 metadata 覆盖的 debug client
    def __init__(
        self,
        scenario_file: str = "",
        content: str = "",
        default_content: str = "DEBUG OK",
        latency_ms: int = 0,
        **kwargs: Any,
    ) -> None:
        self._scenario_file = str(scenario_file or "").strip()
        self._content = str(content or "")
        self._default_content = str(default_content or "DEBUG OK")
        self._latency_ms = int(latency_ms or 0)

    @property
    # 用途：
    # - 返回 backend provider 注册名
    # 输入：
    # - 无
    # 输出：
    # - provider 名称 `debug`
    def backend(self) -> str:
        return "debug"

    @property
    # 用途：
    # - 返回 backend 类型
    # 输入：
    # - 无
    # 输出：
    # - 调试 backend 类型标识
    def backend_type(self) -> str:
        return "DEBUG"

    # 用途：
    # - 声明 debug backend 支持的虚拟模型名
    # 输入：
    # - 无
    # 输出：
    # - 调试用模型名列表
    def supported_models(self) -> list[str]:
        return ["debug-success", "debug-error", "debug-quota"]

    # 用途：
    # - 执行一次 debug backend 调用，返回固定内容或固定错误
    # 输入：
    # - model_name/prompt/system_prompt/temperature/timeout_seconds/metadata/kwargs: Tier 路由透传参数
    # 输出：
    # - llm_tier 统一格式的调用结果字典；错误场景抛 QuotaExhaustedError 或 BackendCallError
    def call(
        self,
        model_name: str,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.0,
        timeout_seconds: int = 600,
        metadata: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        resolved_metadata = dict(metadata or {})
        scenario = self._load_scenario(resolved_metadata)
        target_error_model = str(resolved_metadata.get("debug_error_model_name") or "").strip()
        if target_error_model and target_error_model != str(model_name or "").strip():
            scenario.pop("error_type", None)
            scenario.pop("error_message", None)
        latency_ms = int(scenario.get("latency_ms", self._latency_ms) or 0)
        timeout_ms = max(0, int(timeout_seconds or 0) * 1000)
        if timeout_ms > 0 and latency_ms > timeout_ms:
            raise BackendCallError(
                self.backend,
                f"debug timeout after {int(timeout_seconds)}s: latency_ms={latency_ms}",
            )
        if latency_ms > 0:
            time.sleep(latency_ms / 1000.0)

        error_type = str(scenario.get("error_type") or "").strip().lower()
        error_message = str(scenario.get("error_message") or "").strip()
        if error_type == "quota":
            raise QuotaExhaustedError(self.backend, str(model_name or "debug"), error_message or "debug quota exhausted")
        if error_type in {"backend", "error"}:
            raise BackendCallError(self.backend, error_message or "debug backend error")
        if error_type == "exception":
            raise RuntimeError(error_message or "debug unexpected exception")

        content = self._resolve_content(
            scenario,
            prompt=str(prompt or ""),
            metadata=resolved_metadata,
        )
        token_usage = self._resolve_token_usage(scenario, content)
        raw_response = {
            "debug": True,
            "model_name": model_name,
            "scenario_file": str(scenario.get("_scenario_file") or ""),
            "content_source": str(scenario.get("_content_file") or ""),
            "prompt_preview": str(prompt or "")[:200],
            "system_prompt_preview": str(system_prompt or "")[:200],
            "temperature": temperature,
            "timeout_seconds": timeout_seconds,
            "metadata": resolved_metadata,
        }
        return {
            "ok": True,
            "content": content,
            "model_name": str(scenario.get("model_name") or model_name or "debug-success"),
            "latency_ms": float(latency_ms),
            "token_usage": token_usage,
            "raw_response": raw_response,
            "error_code": 0,
            "error_message": "",
        }

    # 用途：
    # - 读取本次请求的 debug scenario，优先 metadata 覆盖，再回退到 backend 默认配置
    # 输入：
    # - metadata: Tier 请求 metadata
    # 输出：
    # - 归一化后的 scenario dict
    def _load_scenario(self, metadata: dict[str, str]) -> dict[str, Any]:
        workspace_root = str(metadata.get("workspace_root") or "").strip()
        base_dir = Path(workspace_root).resolve() if workspace_root else Path.cwd()
        scenario_file = str(metadata.get("debug_scenario_file") or self._scenario_file or "").strip()
        scenario: dict[str, Any] = {}
        if scenario_file:
            scenario_path = _resolve_path(scenario_file, base_dir=base_dir)
            if scenario_path is None or not scenario_path.is_file():
                raise BackendCallError(self.backend, f"debug scenario file not found: {scenario_file}")
            try:
                scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise BackendCallError(self.backend, f"debug scenario file is not valid JSON: {scenario_path}", original_error=exc) from exc
            except OSError as exc:
                raise BackendCallError(self.backend, f"debug scenario file unreadable: {scenario_path}", original_error=exc) from exc
            scenario["_scenario_base_dir"] = str(scenario_path.parent)
            scenario["_scenario_file"] = str(scenario_path)
        else:
            scenario["_scenario_base_dir"] = str(base_dir)
        override_error_type = str(metadata.get("debug_error_type") or "").strip()
        if override_error_type:
            scenario["error_type"] = override_error_type
        override_error_message = str(metadata.get("debug_error_message") or "").strip()
        if override_error_message:
            scenario["error_message"] = override_error_message
        override_content = str(metadata.get("debug_content") or "").strip()
        if override_content:
            scenario["content"] = override_content
        override_content_file = str(metadata.get("debug_content_file") or "").strip()
        if override_content_file:
            scenario["content_file"] = override_content_file
        override_latency_ms = str(metadata.get("debug_latency_ms") or "").strip()
        if override_latency_ms:
            scenario["latency_ms"] = int(override_latency_ms)
        return scenario

    # 用途：
    # - 解析本次成功响应正文，支持内联 content、外部 content_file 或受控 Role Agent/RAG fixture
    # 输入：
    # - scenario/prompt/metadata: 归一化场景、当前请求正文与 Tier metadata
    # 输出：
    # - 最终返回给调用方的文本内容
    def _resolve_content(
        self,
        scenario: dict[str, Any],
        *,
        prompt: str,
        metadata: Mapping[str, object],
    ) -> str:
        response_mode = str(scenario.get("response_mode") or "").strip()
        if response_mode == "role_agent_fixture" and str(metadata.get("prompt_name") or "").strip() == "rag_judger":
            return self._resolve_rag_judge_fixture(metadata=metadata)
        if response_mode == "role_agent_fixture" and self._is_role_agent_fixture_request(
            prompt,
            metadata=metadata,
        ):
            return self._resolve_role_agent_fixture(
                scenario,
                prompt=prompt,
                metadata=metadata,
            )
        base_dir = Path(str(scenario.get("_scenario_base_dir") or Path.cwd()))
        content_file = str(scenario.get("content_file") or "").strip()
        if content_file:
            content = _read_content_file(content_file, base_dir=base_dir)
            scenario["_content_file"] = str(_resolve_path(content_file, base_dir=base_dir) or "")
            return content
        if "content" in scenario:
            return str(scenario.get("content") or "")
        if self._content:
            return self._content
        return self._default_content

    # 用途：
    # - 为受控 Stage Process 场景生成符合 batch RAG judge Contract 的确定性响应
    # 输入：
    # - metadata: RAG judge 请求 metadata，必须包含当前批次 section_keys
    # 输出：
    # - 每个候选 section_key 恰好一条 accept decision 的严格 JSON 文本
    def _resolve_rag_judge_fixture(self, *, metadata: Mapping[str, object]) -> str:
        raw_section_keys = metadata.get("section_keys")
        if not isinstance(raw_section_keys, list):
            raise BackendCallError(self.backend, "debug RAG judge section_keys contract missing")
        section_keys = [str(value).strip() for value in raw_section_keys if str(value).strip()]
        if not section_keys or len(section_keys) != len(raw_section_keys) or len(set(section_keys)) != len(section_keys):
            raise BackendCallError(self.backend, "debug RAG judge section_keys contract invalid")
        return json.dumps(
            {
                "decisions": [
                    {
                        "section_key": section_key,
                        "decision": "accept",
                        "relevance": "high",
                        "affects": ["context"],
                        "reason": "Controlled fixture accepts the declared retrieval candidate.",
                    }
                    for section_key in section_keys
                ]
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

    # 用途：
    # - 区分 Role Agent 协议请求与 Tier startup probe/普通 DEBUG 调用
    # 输入：
    # - prompt/metadata: 当前请求正文与 Tier metadata
    # 输出：
    # - 仅当请求属于 planner、Review、Adjudication 或 Upgrade 时返回 True
    def _is_role_agent_fixture_request(
        self,
        prompt: str,
        *,
        metadata: Mapping[str, object],
    ) -> bool:
        try:
            payload = json.loads(prompt)
        except json.JSONDecodeError:
            return False
        if not isinstance(payload, Mapping):
            return False
        if isinstance(payload.get("flow_step"), Mapping):
            return True

        prompt_name = str(metadata.get("prompt_name") or "").strip()
        if prompt_name == "role_agent_multi_angle_review":
            return isinstance(payload.get("angle"), str) and bool(payload["angle"])
        if prompt_name == "role_agent_review_adjudication":
            return isinstance(payload.get("reports"), list)
        if prompt_name == "role_agent_upgrade":
            return isinstance(payload.get("required_output"), Mapping)
        return False

    # Purpose: Resolve a deterministic Role Agent planner, Review, adjudication, or upgrade response.
    # Inputs: Controlled scenario, current JSON prompt, and Tier request metadata.
    # Outputs: Strict JSON text selected from the existing Role Agent fixture contract.
    def _resolve_role_agent_fixture(
        self,
        scenario: dict[str, Any],
        *,
        prompt: str,
        metadata: Mapping[str, object],
    ) -> str:
        fixture = scenario.get("role_agent_fixture")
        if not isinstance(fixture, Mapping):
            raise BackendCallError(self.backend, "debug role_agent_fixture contract missing")
        try:
            payload = json.loads(prompt)
        except json.JSONDecodeError as exc:
            raise BackendCallError(
                self.backend,
                "debug role_agent_fixture prompt is not valid JSON",
                original_error=exc,
            ) from exc
        if not isinstance(payload, Mapping):
            raise BackendCallError(self.backend, "debug role_agent_fixture prompt must be a JSON object")

        prompt_name = str(metadata.get("prompt_name") or "").strip()
        if isinstance(payload.get("flow_step"), Mapping):
            plan = self._build_role_agent_fixture_plan(
                scenario,
                fixture=fixture,
                payload=payload,
                prompt_name=prompt_name,
                metadata=metadata,
            )
            return json.dumps(plan, ensure_ascii=False, separators=(",", ":"))
        if prompt_name == "role_agent_multi_angle_review":
            response = self._project_marker_fixture_response(
                fixture=fixture,
                response_key="multi_angle_review_responses_by_project_marker",
                metadata=metadata,
                discriminator=str(payload.get("angle") or "").strip(),
            )
            if response is None:
                response = fixture.get("review_response", {"review_status": "passed", "findings": []})
            return self._encode_fixture_mapping(response, response_name="review_response")
        if prompt_name == "role_agent_review_adjudication":
            response = self._project_marker_fixture_response(
                fixture=fixture,
                response_key="adjudication_responses_by_project_marker",
                metadata=metadata,
            )
            if response is None:
                response = fixture.get(
                    "adjudication_response",
                    {"review_status": "passed", "findings": []},
                )
            return self._encode_fixture_mapping(response, response_name="adjudication_response")
        if prompt_name == "role_agent_upgrade":
            marker_response = self._project_marker_fixture_response(
                fixture=fixture,
                response_key="upgrade_responses_by_project_marker",
                metadata=metadata,
            )
            required_output = payload.get("required_output")
            if marker_response is not None and isinstance(required_output, Mapping):
                response = {**dict(required_output), **dict(marker_response)}
            else:
                response = marker_response
            if response is None:
                response = fixture.get("upgrade_response")
            if response is None:
                response = required_output
            return self._encode_fixture_mapping(response, response_name="upgrade_response")
        raise BackendCallError(
            self.backend,
            f"debug role_agent_fixture request is unsupported: prompt_name={prompt_name or '<empty>'}",
        )

    # Purpose: Select one controlled response by project marker and optional Review angle.
    # Inputs: Fixture mapping key, Tier metadata, and optional discriminator such as Review angle.
    # Outputs: Matching strict response mapping, wildcard response, or None when no marker applies.
    def _project_marker_fixture_response(
        self,
        *,
        fixture: Mapping[str, object],
        response_key: str,
        metadata: Mapping[str, object],
        discriminator: str = "",
    ) -> Mapping[str, object] | None:
        responses_by_marker = fixture.get(response_key)
        project_name = str(metadata.get("project_name") or "")
        if not isinstance(responses_by_marker, Mapping) or not project_name:
            return None
        response = next(
            (
                candidate
                for marker, candidate in responses_by_marker.items()
                if str(marker) and str(marker) in project_name
            ),
            None,
        )
        if not isinstance(response, Mapping):
            return None
        if discriminator:
            selected = response.get(discriminator, response.get("*"))
            return selected if isinstance(selected, Mapping) else None
        return response

    # 用途：
    # - 构造一个只使用当前 fixed Flow step 允许动作的确定性 ActionPlan
    # 输入：
    # - scenario/fixture/payload/prompt_name/metadata: 场景、fixture 合同、planner prompt、源 prompt 名与 Task metadata
    # 输出：
    # - 满足 MLEXP planner 严格 schema 的 ActionPlan mapping
    def _build_role_agent_fixture_plan(
        self,
        scenario: dict[str, Any],
        *,
        fixture: Mapping[str, object],
        payload: Mapping[str, object],
        prompt_name: str,
        metadata: Mapping[str, object],
    ) -> dict[str, object]:
        flow_step = payload.get("flow_step")
        if not isinstance(flow_step, Mapping):
            raise BackendCallError(self.backend, "debug role_agent_fixture flow_step missing")
        step_id = str(flow_step.get("step_id") or "").strip()
        step_type = str(flow_step.get("step_type") or "").strip()
        flow_family = str(payload.get("flow_family") or "").strip()
        flow_profile = str(payload.get("flow_profile") or "").strip()
        allowed_actions = tuple(
            str(action)
            for action in payload.get("allowed_actions", ())
            if isinstance(action, str) and action
        )
        if not step_id or not flow_family or not flow_profile or not allowed_actions:
            raise BackendCallError(self.backend, "debug role_agent_fixture planner identity missing")

        artifact_steps = {
            str(value)
            for value in fixture.get("artifact_steps", ())
            if isinstance(value, str) and value
        }
        review_after_write_steps = {
            str(value)
            for value in fixture.get("review_after_write_steps", ())
            if isinstance(value, str) and value
        }
        actions: list[dict[str, object]] = []
        if step_id in artifact_steps:
            actions.append(
                self._fixture_action(
                    step_id,
                    len(actions) + 1,
                    "write_artifact",
                    self._artifact_write_arguments(
                        scenario,
                        fixture=fixture,
                        payload=payload,
                        prompt_name=prompt_name,
                        metadata=metadata,
                    ),
                )
            )
            if step_id in review_after_write_steps and "run_review_step" in allowed_actions:
                actions.append(
                    self._fixture_action(
                        step_id,
                        len(actions) + 1,
                        "run_review_step",
                        {},
                    )
                )
        elif step_type == "review":
            actions.append(self._fixture_action(step_id, 1, "run_review_step", {}))
        elif step_type == "validate":
            validation_action = (
                "run_validation_step"
                if "run_validation_step" in allowed_actions
                else "run_test_step"
            )
            declared_commands = [
                str(command)
                for command in payload.get("declared_validation_commands", ())
                if isinstance(command, str) and command
            ]
            arguments = {"command": declared_commands[0]} if declared_commands else {}
            actions.append(self._fixture_action(step_id, 1, validation_action, arguments))
        elif "retrieve_memory" in step_id and "retrieve_memory" in allowed_actions:
            actions.append(self._fixture_action(step_id, 1, "retrieve_memory", {}))
        elif step_id.startswith("load_"):
            ref = self._first_working_context_ref(payload)
            if ref and "read_workspace" in allowed_actions:
                actions.append(self._fixture_action(step_id, 1, "read_workspace", {"ref": ref}))
        elif step_id == "execute_test" and "run_test_step" in allowed_actions:
            declared_commands = [
                str(command)
                for command in payload.get("declared_validation_commands", ())
                if isinstance(command, str) and command
            ]
            arguments = {"command": declared_commands[0]} if declared_commands else {}
            actions.append(self._fixture_action(step_id, 1, "run_test_step", arguments))

        if not actions:
            if "write_evidence" not in allowed_actions:
                raise BackendCallError(
                    self.backend,
                    f"debug role_agent_fixture has no safe action for step: {step_id}",
                )
            actions.append(
                self._fixture_action(
                    step_id,
                    1,
                    "write_evidence",
                    {
                        "evidence_id": step_id,
                        "payload": {
                            "fixture": "controlled_role_agent",
                            "step_id": step_id,
                        },
                    },
                )
            )
        forbidden = [
            str(action["action_type"])
            for action in actions
            if action["action_type"] not in allowed_actions
        ]
        if forbidden:
            raise BackendCallError(
                self.backend,
                f"debug role_agent_fixture action is not allowed: {','.join(forbidden)}",
            )
        return {
            "flow_family": flow_family,
            "flow_profile": flow_profile,
            "step_id": step_id,
            "actions": actions,
            "replan_reason": None,
        }

    # 用途：
    # - 构造严格五字段 ActionPlan action
    # 输入：
    # - step_id/sequence/action_type/arguments: 当前 step 与动作参数
    # 输出：
    # - 可被 MLEXP parse_action_plan 接受的 action mapping
    def _fixture_action(
        self,
        step_id: str,
        sequence: int,
        action_type: str,
        arguments: Mapping[str, object],
    ) -> dict[str, object]:
        return {
            "action_id": f"{step_id}_fixture_{sequence}",
            "action_type": action_type,
            "arguments": dict(arguments),
            "expected_observation": f"{action_type} completed with persisted controlled evidence",
            "timeout_seconds": 300,
        }

    # 用途：
    # - 从冻结 fixture 读取当前源 prompt 对应的完整 Artifact 正文
    # 输入：
    # - scenario/fixture/payload/prompt_name/metadata: 场景、fixture、planner prompt、源 prompt 名与 Task metadata
    # 输出：
    # - write_artifact 所需 ref 和 content
    def _artifact_write_arguments(
        self,
        scenario: dict[str, Any],
        *,
        fixture: Mapping[str, object],
        payload: Mapping[str, object],
        prompt_name: str,
        metadata: Mapping[str, object],
    ) -> dict[str, str]:
        required_outputs = [
            str(ref)
            for ref in payload.get("required_outputs", ())
            if isinstance(ref, str) and ref
        ]
        if not required_outputs:
            raise BackendCallError(self.backend, "debug role_agent_fixture required output missing")
        output_ref = required_outputs[0]
        inline_by_prompt = fixture.get("artifact_contents")
        file_by_prompt = fixture.get("artifact_content_files")
        fixture_prompt_name = prompt_name
        if prompt_name in {"role_agent_turn", "role_agent_upgrade"}:
            fixture_prompt_name = str(metadata.get("source_prompt_name") or "").strip()
        if prompt_name == "module_design_author_generation":
            task_type = str(metadata.get("task_type") or "").strip()
            if not task_type:
                phase_name = str(metadata.get("phase_name") or "").strip()
                task_type = {
                    "interface": "module_interface",
                    "data_error": "module_data_error",
                    "lifecycle": "module_lifecycle",
                }.get(phase_name, "")
            if not task_type and str(metadata.get("phase_name") or "").strip() == "quality":
                working_context = payload.get("working_context")
                context_text = "\n".join(
                    str(value)
                    for value in (
                        working_context.values()
                        if isinstance(working_context, Mapping)
                        else ()
                    )
                )
                if '"doc_kind": "test_strategy"' in context_text:
                    task_type = "module_test_strategy"
                elif '"doc_kind": "implementation_guidance"' in context_text:
                    task_type = "module_implementation_guidance"
            fixture_prompt_name = {
                "module_interface": "module_design_author_interface_generation",
                "module_data_error": "module_design_author_data_error_generation",
                "module_lifecycle": "module_design_author_lifecycle_generation",
                "module_test_strategy": "module_design_author_test_strategy_generation",
                "module_implementation_guidance": (
                    "module_design_author_implementation_guidance_generation"
                ),
            }.get(task_type, prompt_name)
        elif prompt_name == "requirement_author_generation":
            task_key = str(metadata.get("task_key") or "").strip()
            fixture_prompt_name = {
                "vision_scope": "requirement_author_vision_scope_generation",
                "users_context": "requirement_author_users_context_generation",
                "model": "requirement_author_model_generation",
                "use_cases": "requirement_author_use_cases_generation",
                "main": "requirement_author_main_generation",
                "assessment": "requirement_author_assessment_generation",
                "acceptance_criteria": "requirement_author_acceptance_criteria_generation",
                "risks_open_questions": (
                    "requirement_author_risks_open_questions_generation"
                ),
            }.get(task_key, prompt_name)
        content: str | None = None
        marker_review_content = self._project_marker_review_artifact_content(
            fixture=fixture,
            prompt_name=prompt_name,
            metadata=metadata,
        )
        if marker_review_content is not None:
            content = marker_review_content
        elif isinstance(inline_by_prompt, Mapping) and fixture_prompt_name in inline_by_prompt:
            content = str(inline_by_prompt[fixture_prompt_name])
        elif isinstance(file_by_prompt, Mapping) and fixture_prompt_name in file_by_prompt:
            base_dir = Path(str(scenario.get("_scenario_base_dir") or Path.cwd()))
            content = _read_content_file(
                str(file_by_prompt[fixture_prompt_name]),
                base_dir=base_dir,
            )
        elif prompt_name.endswith("_review") and fixture.get("review_artifact_content_file"):
            base_dir = Path(str(scenario.get("_scenario_base_dir") or Path.cwd()))
            content = _read_content_file(
                str(fixture["review_artifact_content_file"]),
                base_dir=base_dir,
            )
        elif prompt_name in {"role_agent_turn", "role_agent_upgrade"}:
            objective = str(payload.get("objective") or "").strip()
            working_context = payload.get("working_context")
            consumed_refs = [
                str(ref)
                for ref in (working_context if isinstance(working_context, Mapping) else {})
                if isinstance(ref, str)
                and ref
                and not ref.startswith("session_evidence::")
            ]
            consumed = "\n".join(f"- `{ref}`" for ref in consumed_refs) or "- No declared upstream Artifact"
            content = (
                "# Role Session CLI Fixture Result\n\n"
                f"## Objective\n\n{objective}\n\n"
                f"## Consumed Evidence\n\n{consumed}\n\n"
                "## Flow Evidence\n\n"
                "The controlled candidate was produced from the declared authorities and is subject "
                "to the fixed Review and validation gates before terminal acceptance.\n\n"
                "## Final Status\n\npassed\n\n"
                f"## Produced Artifact\n\n- `{output_ref}`\n"
            )
        if content is None:
            raise BackendCallError(
                self.backend,
                f"debug role_agent_fixture Artifact missing: prompt_name={prompt_name or '<empty>'}",
            )
        if fixture_prompt_name in {
            "contract_test_case_author_generation",
            "coding_fixer_fix",
        }:
            content = self._specialize_contract_case_target(
                content,
                metadata=metadata,
            )
        elif fixture_prompt_name.startswith("requirement_author_"):
            content = _specialize_requirement_author_content(
                content,
                metadata=metadata,
            )
        elif fixture_prompt_name == "system_testing_scenario_design_author_scenario_design_generation":
            content = _specialize_system_testing_scenario_design_content(
                content,
                metadata=metadata,
            )
        elif fixture_prompt_name == "system_testing_family_design_author_family_design_generation":
            content = _specialize_system_testing_family_design_content(
                content,
                metadata=metadata,
            )
        elif fixture_prompt_name == "system_testing_case_design_author_case_design_generation":
            content = _specialize_system_testing_case_design_content(
                content,
                metadata=metadata,
            )
        elif fixture_prompt_name == "system_testing_case_author_case_generation":
            content = _specialize_system_testing_case_content(
                content,
                metadata=metadata,
            )
        elif fixture_prompt_name == "system_testing_case_data_item_author_case_data_item_generation":
            content = _specialize_system_testing_case_data_content(
                content,
                metadata=metadata,
            )
        elif fixture_prompt_name == "unit_test_case_catalog_author_generation":
            content = _specialize_unit_test_case_catalog_content(
                content,
                metadata=metadata,
            )
        elif fixture_prompt_name == "unit_test_case_author_generation":
            content = _specialize_unit_test_case_content(
                content,
                metadata=metadata,
            )
        elif fixture_prompt_name == "unit_test_script_author_generation":
            content = _specialize_unit_test_script_content(
                content,
                metadata=metadata,
            )
        return {"ref": output_ref, "content": content}

    # Purpose: Convert the existing project-marker response into the target Review Role's Artifact.
    # Inputs: Shared fixture, source prompt name, and request metadata containing the project identity.
    # Outputs: Deterministic Review markdown for a matching marker, otherwise None.
    def _project_marker_review_artifact_content(
        self,
        *,
        fixture: Mapping[str, object],
        prompt_name: str,
        metadata: Mapping[str, object],
    ) -> str | None:
        if not prompt_name.endswith("_review"):
            return None
        responses_by_marker = fixture.get("review_responses_by_project_marker")
        project_name = str(metadata.get("project_name") or "")
        if not isinstance(responses_by_marker, Mapping) or not project_name:
            return None
        response = next(
            (
                candidate
                for marker, candidate in responses_by_marker.items()
                if str(marker) and str(marker) in project_name
            ),
            None,
        )
        if not isinstance(response, Mapping):
            return None
        findings = response.get("findings")
        finding_rows = [
            row
            for row in findings
            if isinstance(row, Mapping)
        ] if isinstance(findings, list) else []
        review_status = str(response.get("review_status") or "").strip().lower()
        decision = "APPROVED" if review_status in {"pass", "passed", "approved"} else "CONTINUE"
        detail_blocks = []
        for index, row in enumerate(finding_rows, start=1):
            severity = str(row.get("severity") or "major").strip().lower()
            normalized_severity = {
                "critical": "High",
                "high": "High",
                "major": "High",
                "medium": "Medium",
                "minor": "Low",
                "low": "Low",
            }.get(severity, "Medium")
            detail_blocks.append(
                "\n".join(
                    (
                        f"REVIEW_ITEM-{index:03d} | Severity: {normalized_severity} | "
                        f"{str(row.get('finding_id') or 'controlled-review-finding')}",
                        "STATUS: AGREED",
                        f"Finding: {str(row.get('description') or row.get('message') or 'controlled Review rejection')}",
                        f"Evidence: {str(row.get('evidence') or 'controlled Review fixture')}",
                        "Required Change: Resolve this blocking finding before Artifact promotion.",
                    )
                )
            )
        if not detail_blocks and decision != "APPROVED":
            detail_blocks = [
                "\n".join(
                    (
                        "REVIEW_ITEM-001 | Severity: High | controlled-review-finding",
                        "STATUS: AGREED",
                        "Finding: controlled Review rejection",
                        "Evidence: controlled Review fixture",
                        "Required Change: Resolve this blocking finding before Artifact promotion.",
                    )
                )
            ]
        findings_text = "\n\n".join(detail_blocks) if detail_blocks else "No blocking findings."
        return (
            "# Review Report\n\n"
            "## Resolved Review Items\n\n"
            + findings_text
            + f"\n\nDECISION: {decision}\n"
        )

    # 用途：
    # - 让受控 Coding JSON Artifact 使用当前 Task 的权威 target_file，避免并行 Task 复用错误目标
    # 输入：
    # - content/metadata: 冻结 JSON Artifact 与包含 workspace_root、task_id/task_key 的 Tier metadata
    # 输出：
    # - target_file 已按 isd_queue.json 当前 Task 唯一匹配后的 JSON；无运行态 identity 时保留冻结内容
    def _specialize_contract_case_target(
        self,
        content: str,
        *,
        metadata: Mapping[str, object],
    ) -> str:
        from framework.task_state import normalize_task_identity

        workspace_root = str(metadata.get("workspace_root") or "").strip()
        task_identity = str(
            metadata.get("task_key")
            or str(metadata.get("task_id") or "").rsplit("::", 1)[-1]
        ).strip()
        if not workspace_root or not task_identity:
            return content

        queue_path = Path(workspace_root).resolve() / "isd_queue.json"
        if not queue_path.is_file():
            raise BackendCallError(
                self.backend,
                f"debug coding fixture authority missing: {queue_path}",
            )
        try:
            queue_payload = json.loads(queue_path.read_text(encoding="utf-8"))
            content_payload = json.loads(content)
        except (OSError, json.JSONDecodeError) as exc:
            raise BackendCallError(
                self.backend,
                "debug coding fixture authority is not valid JSON",
                original_error=exc,
            ) from exc
        queue_entries = (
            queue_payload.get("isd_queue")
            if isinstance(queue_payload, Mapping)
            else None
        )
        if not isinstance(queue_entries, list) or not isinstance(content_payload, dict):
            raise BackendCallError(
                self.backend,
                "debug coding fixture authority schema is invalid",
            )

        normalized_identity = normalize_task_identity(task_identity, default="")
        matched_targets = [
            str(entry.get("target_file") or "").strip()
            for entry in queue_entries
            if isinstance(entry, Mapping)
            and normalize_task_identity(
                str(entry.get("target_file") or ""),
                default="",
            )
            == normalized_identity
        ]
        matched_targets = [target for target in matched_targets if target]
        if len(matched_targets) != 1:
            raise BackendCallError(
                self.backend,
                "debug coding fixture target must resolve exactly once: "
                f"task_identity={task_identity}, matches={len(matched_targets)}",
            )
        content_payload["target_file"] = matched_targets[0]
        return json.dumps(content_payload, ensure_ascii=False, indent=2)

    # 用途：
    # - 从 planner working_context 中选择首个真实 workspace authority
    # 输入：
    # - payload: planner JSON prompt
    # 输出：
    # - workspace-relative authority ref；不存在时返回空字符串
    def _first_working_context_ref(self, payload: Mapping[str, object]) -> str:
        working_context = payload.get("working_context")
        if not isinstance(working_context, Mapping):
            return ""
        return next(
            (
                str(ref)
                for ref in working_context
                if isinstance(ref, str)
                and ref
                and not ref.startswith("session_evidence::")
            ),
            "",
        )

    # 用途：
    # - 验证并编码 Review、Adjudication 或 Upgrade fixture mapping
    # 输入：
    # - response/response_name: fixture 内容及错误定位名
    # 输出：
    # - 紧凑 JSON 文本
    def _encode_fixture_mapping(self, response: object, *, response_name: str) -> str:
        if not isinstance(response, Mapping):
            raise BackendCallError(
                self.backend,
                f"debug role_agent_fixture {response_name} must be a JSON object",
            )
        return json.dumps(dict(response), ensure_ascii=False, separators=(",", ":"))

    # 用途：
    # - 解析本次成功响应的 token usage；缺失时给出稳定缺省值
    # 输入：
    # - scenario/content: debug scenario 与最终内容
    # 输出：
    # - llm_tier 统一 token_usage 字典
    def _resolve_token_usage(self, scenario: dict[str, Any], content: str) -> dict[str, int]:
        usage = scenario.get("token_usage")
        if isinstance(usage, dict):
            prompt_tokens = int(usage.get("prompt_tokens") or 0)
            completion_tokens = int(usage.get("completion_tokens") or 0)
            total_tokens = int(usage.get("total_tokens") or prompt_tokens + completion_tokens)
            return {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            }
        completion_tokens = max(1, (len(str(content or "")) + 3) // 4) if content else 0
        return {
            "prompt_tokens": int(scenario.get("prompt_tokens") or 16),
            "completion_tokens": completion_tokens,
            "total_tokens": int(scenario.get("prompt_tokens") or 16) + completion_tokens,
        }


register_backend("debug", DebugBackendClient)
