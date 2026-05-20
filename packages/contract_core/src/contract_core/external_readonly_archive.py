"""Thin facade for external-readonly archive behavior contracts."""

from behavior_contracts.external_readonly_archive import (
    EXTERNAL_READONLY_FETCH_ARCHIVE_CONTROLLED_ROOT,
    EXTERNAL_READONLY_FETCH_ARCHIVE_FORBIDDEN_OUTPUT_KEYS,
    EXTERNAL_READONLY_FETCH_ARCHIVE_REF_PREFIX,
    build_external_readonly_fetch_evidence_archive,
    external_readonly_fetch_evidence_output_blocked_payload,
    external_readonly_fetch_evidence_ref_for_output,
    external_readonly_fetch_output_boundary_violated,
    preview_external_readonly_text,
    sanitize_external_readonly_fetch_output,
    validate_external_readonly_fetch_evidence_output_path,
)

__all__ = [
    "EXTERNAL_READONLY_FETCH_ARCHIVE_CONTROLLED_ROOT",
    "EXTERNAL_READONLY_FETCH_ARCHIVE_FORBIDDEN_OUTPUT_KEYS",
    "EXTERNAL_READONLY_FETCH_ARCHIVE_REF_PREFIX",
    "build_external_readonly_fetch_evidence_archive",
    "external_readonly_fetch_evidence_output_blocked_payload",
    "external_readonly_fetch_evidence_ref_for_output",
    "external_readonly_fetch_output_boundary_violated",
    "preview_external_readonly_text",
    "sanitize_external_readonly_fetch_output",
    "validate_external_readonly_fetch_evidence_output_path",
]
