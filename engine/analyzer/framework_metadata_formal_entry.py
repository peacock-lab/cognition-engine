"""Helpers for root-direct framework metadata formal-entry records."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List

ROOT_FORMAL_FIELDS = (
    "id",
    "name",
    "version",
    "type",
    "repository",
    "status",
    "metadata",
    "timestamps",
)

METADATA_FORMAL_FIELDS = (
    "language",
    "architecture_style",
    "primary_entry_points",
    "core_modules",
    "analysis_depth",
    "source_documents",
    "input_channels",
)

SOURCE_DOCUMENT_FORMAL_FIELDS = (
    "source_id",
    "title",
    "kind",
    "path",
)

TIMESTAMP_FORMAL_FIELDS = (
    "first_analyzed",
    "last_updated",
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


def inspect_framework_metadata_formal_entry(record: Dict[str, Any]) -> Dict[str, bool]:
    """Return boolean checks for the current framework metadata formal-entry contract."""
    metadata = record.get("metadata")
    source_documents = metadata.get("source_documents") if isinstance(metadata, dict) else None
    input_channels = metadata.get("input_channels") if isinstance(metadata, dict) else None
    timestamps = record.get("timestamps")

    return {
        "has_id": isinstance(record.get("id"), str) and bool(record.get("id")),
        "has_name": isinstance(record.get("name"), str) and bool(record.get("name")),
        "has_version": isinstance(record.get("version"), str) and bool(record.get("version")),
        "has_type": isinstance(record.get("type"), str) and bool(record.get("type")),
        "has_repository": isinstance(record.get("repository"), str) and bool(record.get("repository")),
        "has_status": isinstance(record.get("status"), str) and bool(record.get("status")),
        "has_metadata": isinstance(metadata, dict),
        "has_timestamps": isinstance(timestamps, dict),
        "metadata_formal_fields_complete": isinstance(metadata, dict)
        and not _missing_fields(metadata, METADATA_FORMAL_FIELDS),
        "has_language": isinstance(metadata, dict)
        and isinstance(metadata.get("language"), str)
        and bool(metadata.get("language")),
        "has_architecture_style": isinstance(metadata, dict)
        and isinstance(metadata.get("architecture_style"), str)
        and bool(metadata.get("architecture_style")),
        "has_primary_entry_points": isinstance(metadata, dict)
        and isinstance(metadata.get("primary_entry_points"), list)
        and len(metadata.get("primary_entry_points", [])) > 0,
        "has_core_modules": isinstance(metadata, dict)
        and isinstance(metadata.get("core_modules"), list)
        and len(metadata.get("core_modules", [])) > 0,
        "has_analysis_depth": isinstance(metadata, dict)
        and isinstance(metadata.get("analysis_depth"), str)
        and bool(metadata.get("analysis_depth")),
        "has_source_documents": isinstance(source_documents, list) and len(source_documents) > 0,
        "source_documents_formal_fields_complete": isinstance(source_documents, list)
        and len(source_documents) > 0
        and all(not _missing_fields(item, SOURCE_DOCUMENT_FORMAL_FIELDS) for item in source_documents),
        "has_input_channels": isinstance(input_channels, list) and len(input_channels) > 0,
        "input_channels_formal_fields_complete": isinstance(input_channels, list)
        and len(input_channels) > 0
        and all(isinstance(item, str) and bool(item) for item in input_channels),
        "timestamps_formal_fields_complete": isinstance(timestamps, dict)
        and not _missing_fields(timestamps, TIMESTAMP_FORMAL_FIELDS),
    }


def build_framework_metadata_formal_entry_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a framework metadata record to the root-direct formal-entry layout."""
    checks = inspect_framework_metadata_formal_entry(record)
    failed_checks = [name for name, passed in checks.items() if not passed]
    if failed_checks:
        framework_id = record.get("id", "<unknown>")
        raise ValueError(
            "Framework metadata formal entry is incomplete for "
            f"{framework_id}: {', '.join(failed_checks)}"
        )

    normalized = _ordered_payload(record, ROOT_FORMAL_FIELDS)
    normalized["metadata"] = _ordered_payload(record["metadata"], METADATA_FORMAL_FIELDS)
    normalized["metadata"]["source_documents"] = [
        _ordered_payload(item, SOURCE_DOCUMENT_FORMAL_FIELDS)
        for item in record["metadata"].get("source_documents", [])
    ]
    normalized["timestamps"] = _ordered_payload(record["timestamps"], TIMESTAMP_FORMAL_FIELDS)
    return normalized
