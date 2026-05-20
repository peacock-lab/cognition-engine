"""Workflow-local external-readonly evidence context helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def extract_twf_product_entry_external_readonly_evidence_context(
    workflow_result: Any,
) -> Mapping[str, Any] | None:
    """Extract workflow-local external-readonly evidence context."""

    return _external_readonly_context(workflow_result)


def _external_readonly_context(workflow_result: Any) -> Mapping[str, Any] | None:
    reference_context = getattr(workflow_result, "reference_context", None)
    metadata = getattr(reference_context, "metadata", None)
    if not isinstance(metadata, Mapping):
        return None
    context = metadata.get("external_readonly_evidence_context")
    return context if isinstance(context, Mapping) else None


__all__ = [
    "extract_twf_product_entry_external_readonly_evidence_context",
]
