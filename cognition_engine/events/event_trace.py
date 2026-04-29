"""ADK Event Trace projection helpers for control-plane records."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable


def build_event_trace_governance(adk_events: list[Dict[str, Any]]) -> Dict[str, Any]:
    records = [adk_event_record(event) for event in adk_events]
    total_count = len(adk_events)
    field_coverage = {
        "adk_event_total_count": total_count,
        "adk_event_with_id_count": count_with(adk_events, "event_id"),
        "adk_event_with_invocation_id_count": count_with(
            adk_events,
            "adk_invocation_id",
        ),
        "adk_event_with_author_count": count_with(adk_events, "author"),
        "adk_event_with_node_info_count": count_with(adk_events, "node_info"),
        "adk_event_with_timestamp_count": count_with(adk_events, "timestamp"),
        "adk_event_with_actions_count": count_with(adk_events, "actions"),
        "adk_event_with_usage_metadata_count": count_with(
            adk_events,
            "usage_metadata",
        ),
    }
    return {
        "adk_event_records": records,
        "adk_event_field_coverage": field_coverage,
        "adk_event_fields_bound": adk_event_fields_bound(
            total_count,
            field_coverage,
        ),
        "adk_event_coverage_available": bool(total_count),
        "adk_event_total_count": total_count,
        "adk_event_error_count": adk_event_error_count(adk_events),
        "adk_event_interrupted_count": adk_event_interrupted_count(adk_events),
        "adk_event_partial_count": sum(
            1 for event in adk_events if event.get("partial") is True
        ),
        "adk_event_turn_complete_count": sum(
            1 for event in adk_events if event.get("turn_complete") is True
        ),
        "adk_event_finish_reasons": value_counts(
            event.get("finish_reason") for event in adk_events
        ),
        "adk_event_author_summary": value_counts(
            event.get("author") for event in adk_events
        ),
        "adk_event_node_summary": value_counts(
            event.get("node_name") or event.get("node_path")
            for event in adk_events
        ),
        "adk_event_branch_summary": value_counts(
            event.get("branch") for event in adk_events
        ),
    }


def adk_event_record(event: Dict[str, Any]) -> Dict[str, Any]:
    long_running_tool_ids = event.get("long_running_tool_ids") or []
    if not isinstance(long_running_tool_ids, list):
        long_running_tool_ids = [long_running_tool_ids]
    return {
        "event_id": event.get("event_id") or event.get("id"),
        "adk_invocation_id": event.get("adk_invocation_id")
        or event.get("invocation_id"),
        "author": event.get("author"),
        "node_info": deepcopy(event.get("node_info")),
        "node_name": event.get("node_name"),
        "node_path": event.get("node_path"),
        "branch": event.get("branch"),
        "timestamp": event.get("timestamp"),
        "partial": event.get("partial"),
        "turn_complete": event.get("turn_complete"),
        "interrupted": event.get("interrupted"),
        "error_code": event.get("error_code"),
        "error_message": event.get("error_message"),
        "finish_reason": event.get("finish_reason"),
        "actions_present": has_value(event.get("actions")),
        "custom_metadata_present": has_value(event.get("custom_metadata")),
        "long_running_tool_ids": deepcopy(long_running_tool_ids),
        "long_running_tool_id_count": len(long_running_tool_ids),
        "model_version": event.get("model_version"),
        "usage_metadata_present": has_value(event.get("usage_metadata")),
        "cache_metadata_present": has_value(event.get("cache_metadata")),
        "citation_metadata_present": has_value(event.get("citation_metadata")),
        "grounding_metadata_present": has_value(event.get("grounding_metadata")),
    }


def adk_event_fields_bound(
    total_count: int,
    field_coverage: Dict[str, int],
) -> bool:
    return bool(
        total_count
        and field_coverage["adk_event_with_id_count"] == total_count
        and field_coverage["adk_event_with_invocation_id_count"] == total_count
        and field_coverage["adk_event_with_author_count"] == total_count
    )


def adk_event_error_count(adk_events: list[Dict[str, Any]]) -> int:
    return sum(
        1
        for event in adk_events
        if event.get("error_code") or event.get("error_message")
    )


def adk_event_interrupted_count(adk_events: list[Dict[str, Any]]) -> int:
    return sum(1 for event in adk_events if event.get("interrupted") is True)


def count_with(events: list[Dict[str, Any]], key: str) -> int:
    return sum(1 for event in events if has_value(event.get(key)))


def has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (str, list, tuple, set, dict)):
        return bool(value)
    return True


def value_counts(values: Iterable[Any]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for value in values:
        if not has_value(value):
            continue
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))
