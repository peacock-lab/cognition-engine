"""Helpers for root-direct insight formal-entry records."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List

ROOT_FORMAL_FIELDS = (
    "id",
    "framework_id",
    "type",
    "category",
    "title",
    "description",
    "confidence",
    "impact",
    "tags",
    "evidence",
    "connections",
)

EVIDENCE_FORMAL_FIELDS = (
    "type",
    "source_file",
    "source_section",
)

CONNECTION_FORMAL_FIELDS = (
    "insight_id",
    "type",
    "strength",
    "description",
)


def _missing_fields(payload: Dict[str, Any], required_fields: Iterable[str]) -> List[str]:
    missing: List[str] = []
    for field in required_fields:
        if field not in payload:
            missing.append(field)
    return missing


def _ordered_payload(payload: Dict[str, Any], formal_fields: Iterable[str]) -> Dict[str, Any]:
    ordered: Dict[str, Any] = {}
    formal_field_set = set(formal_fields)

    for field in formal_fields:
        if field in payload:
            ordered[field] = deepcopy(payload[field])

    for field, value in payload.items():
        if field in formal_field_set:
            continue
        ordered[field] = deepcopy(value)

    return ordered


def inspect_insight_formal_entry(record: Dict[str, Any]) -> Dict[str, bool]:
    """Return boolean checks for the current insight formal-entry contract."""
    evidence = record.get("evidence")
    connections = record.get("connections")

    return {
        "has_id": isinstance(record.get("id"), str) and bool(record.get("id")),
        "has_framework_id": isinstance(record.get("framework_id"), str) and bool(record.get("framework_id")),
        "has_type": isinstance(record.get("type"), str) and bool(record.get("type")),
        "has_category": isinstance(record.get("category"), str) and bool(record.get("category")),
        "has_title": isinstance(record.get("title"), str) and bool(record.get("title")),
        "has_description": isinstance(record.get("description"), str) and bool(record.get("description")),
        "has_confidence": isinstance(record.get("confidence"), (int, float)),
        "has_impact": isinstance(record.get("impact"), dict),
        "has_tags": isinstance(record.get("tags"), list),
        "has_evidence": isinstance(evidence, list) and len(evidence) > 0,
        "has_connections": isinstance(connections, list),
        "evidence_formal_fields_complete": isinstance(evidence, list)
        and len(evidence) > 0
        and all(not _missing_fields(item, EVIDENCE_FORMAL_FIELDS) for item in evidence),
        "connections_formal_fields_complete": isinstance(connections, list)
        and all(not _missing_fields(item, CONNECTION_FORMAL_FIELDS) for item in connections),
    }


def build_insight_formal_entry_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize an insight record to the root-direct formal-entry layout."""
    checks = inspect_insight_formal_entry(record)
    failed_checks = [name for name, passed in checks.items() if not passed]
    if failed_checks:
        insight_id = record.get("id", "<unknown>")
        raise ValueError(
            f"Insight formal entry is incomplete for {insight_id}: {', '.join(failed_checks)}"
        )

    normalized = _ordered_payload(record, ROOT_FORMAL_FIELDS)
    normalized["evidence"] = [
        _ordered_payload(item, EVIDENCE_FORMAL_FIELDS)
        for item in record.get("evidence", [])
    ]
    normalized["connections"] = [
        _ordered_payload(item, CONNECTION_FORMAL_FIELDS)
        for item in record.get("connections", [])
    ]
    return normalized
