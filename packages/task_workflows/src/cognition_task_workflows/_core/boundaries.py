"""Boundary guards for candidate task workflow descriptors."""

from __future__ import annotations

from typing import Any


FORBIDDEN_TASK_WORKFLOW_METADATA_KEYS = frozenset(
    {
        "adk_object",
        "api_key",
        "config_root",
        "credential",
        "live_model_payload",
        "message",
        "messages",
        "payload",
        "prompt",
        "provider_payload",
        "provider_response",
        "raw",
        "raw_adk_object",
        "raw_input",
        "raw_output",
        "raw_payload",
        "raw_prompt",
        "raw_provider_response",
        "raw_response",
        "raw_tool_input",
        "raw_tool_output",
        "raw_user_message",
        "response",
        "secret",
        "token",
        "tool_input",
        "tool_output",
        "user_message",
    }
)


def validate_task_workflow_metadata_boundary(
    value: Any,
    *,
    field_name: str = "metadata",
) -> None:
    """Reject raw payload-like fields from task workflow candidate metadata."""

    violations = [
        f"{field_name} contains forbidden raw payload at {path}."
        for path, item in _walk(value)
        if _is_forbidden_metadata(path, item)
    ]
    if violations:
        raise ValueError("; ".join(violations))


def _walk(value: Any, path: str = "$") -> list[tuple[str, Any]]:
    items = [(path, value)]
    if isinstance(value, dict):
        for key, item in value.items():
            items.extend(_walk(item, f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            items.extend(_walk(item, f"{path}[{index}]"))
    return items


def _is_forbidden_metadata(path: str, value: Any) -> bool:
    key = path.rsplit(".", maxsplit=1)[-1].lower()
    if key in FORBIDDEN_TASK_WORKFLOW_METADATA_KEYS:
        return True
    if isinstance(value, dict):
        module_name = value.get("object_module")
        return isinstance(module_name, str) and module_name.startswith(
            ("google.adk", "adk_adapter", "runtime_container")
        )
    if value is None or isinstance(value, (str, int, float, bool, list, tuple, dict)):
        return False
    return type(value).__module__.startswith(
        ("google.adk", "adk_adapter", "runtime_container")
    )
