"""Output boundary helpers for the Cognition System CLI."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cognition_cli.constants import (
    ALLOWED_TOP_LEVEL_FIELDS,
    FORBIDDEN_TOP_LEVEL_FIELDS,
)


def whitelist_output(output: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: sanitize_value(value)
        for key, value in output.items()
        if key in ALLOWED_TOP_LEVEL_FIELDS and key not in FORBIDDEN_TOP_LEVEL_FIELDS
    }


def sanitize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): sanitize_value(nested)
            for key, nested in value.items()
            if str(key) not in FORBIDDEN_TOP_LEVEL_FIELDS
        }
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_value(item) for item in value]
    return value


def violates_output_boundary(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key) in FORBIDDEN_TOP_LEVEL_FIELDS:
                return True
            if violates_output_boundary(nested):
                return True
    elif isinstance(value, list | tuple):
        return any(violates_output_boundary(item) for item in value)
    return False


def safe_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}
