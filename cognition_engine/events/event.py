"""ADK Event normalization helpers."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional


def serialize_adk_event(event: object) -> Dict[str, Any]:
    """Convert an ADK Event into the project event summary contract."""

    node_info = getattr(event, "node_info", None)
    node_info_record = jsonable(node_info)
    node_path = _node_info_path(node_info, node_info_record)
    return {
        "event_id": getattr(event, "id", None),
        "id": getattr(event, "id", None),
        "author": getattr(event, "author", None),
        "adk_invocation_id": getattr(event, "invocation_id", None),
        "invocation_id": getattr(event, "invocation_id", None),
        "node_info": node_info_record,
        "node_name": extract_node_name(node_path),
        "node_path": node_path,
        "branch": getattr(event, "branch", None),
        "timestamp": jsonable(getattr(event, "timestamp", None)),
        "partial": getattr(event, "partial", None),
        "turn_complete": getattr(event, "turn_complete", None),
        "interrupted": getattr(event, "interrupted", None),
        "error_code": getattr(event, "error_code", None),
        "error_message": getattr(event, "error_message", None),
        "finish_reason": getattr(event, "finish_reason", None),
        "actions": jsonable(getattr(event, "actions", None)),
        "custom_metadata": jsonable(getattr(event, "custom_metadata", None)),
        "long_running_tool_ids": jsonable(
            getattr(event, "long_running_tool_ids", None)
        ),
        "model_version": getattr(event, "model_version", None),
        "usage_metadata": jsonable(getattr(event, "usage_metadata", None)),
        "cache_metadata": jsonable(getattr(event, "cache_metadata", None)),
        "citation_metadata": jsonable(getattr(event, "citation_metadata", None)),
        "grounding_metadata": jsonable(getattr(event, "grounding_metadata", None)),
        "content": jsonable(getattr(event, "content", None)),
        "output": jsonable(getattr(event, "output", None)),
    }


def jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (list, tuple, set)):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return model_dump(mode="json", by_alias=False)
        except TypeError:
            return model_dump()
    if hasattr(value, "__dict__"):
        return {
            key: jsonable(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return str(value)


def extract_node_name(node_path: Optional[str]) -> Optional[str]:
    if not node_path:
        return None
    node_name = node_path.rsplit("/", 1)[-1]
    if "@" in node_name:
        node_name = node_name.rsplit("@", 1)[0]
    return node_name


def _node_info_path(node_info: Any, node_info_record: Any) -> Optional[str]:
    node_path = getattr(node_info, "path", None)
    if node_path:
        return node_path
    if isinstance(node_info_record, dict):
        path = node_info_record.get("path")
        return str(path) if path else None
    return None
