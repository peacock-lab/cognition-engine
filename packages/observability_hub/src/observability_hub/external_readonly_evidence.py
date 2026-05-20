"""External-readonly evidence summary observation candidates."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import Field

from observability_hub.models import ObservabilityBaseModel


class ExternalReadonlyEvidenceObservationCandidate(ObservabilityBaseModel):
    """Internal sanitized observation candidate for external-readonly evidence."""

    observation_id: str
    source: str
    status: str
    evidence_ref: str | None = None
    evidence_output_path: str
    source_url: str | None = None
    runtime_status: str | None = None
    reference_review_ready: bool = False
    allowed_for_model_context: bool = False
    evidence_written: bool = False
    runtime_fetch_performed: bool = False
    transport_called: bool = False
    external_network_call_performed: bool = False
    raw_response_included: bool = False
    raw_html_included: bool = False
    response_headers_included: bool = False
    uploads_content: bool = False
    writes_files: bool = False
    content_hash: str | None = None
    sanitized_excerpt_preview: str | None = None
    total_excerpt_chars: int = 0
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata_keys: list[str] = Field(default_factory=list)
    contract_candidate_notes: list[str] = Field(default_factory=list)
    created_at: str


def build_external_readonly_evidence_observation_candidate(
    summary: Any,
) -> ExternalReadonlyEvidenceObservationCandidate:
    """Build a sanitized observation candidate from an evidence summary."""

    data = _mapping_or_raise(summary, "external-readonly evidence summary")
    evidence_output_path = _required_str(
        data.get("evidence_output_path"),
        "evidence_output_path",
    )
    metadata = _mapping(data.get("metadata"))

    return ExternalReadonlyEvidenceObservationCandidate(
        observation_id=f"external-readonly-evidence-observation-{uuid4()}",
        source="observability_hub.external_readonly_evidence",
        status=_plain_str(data.get("status")) or "unknown",
        evidence_ref=_plain_str(data.get("evidence_ref")),
        evidence_output_path=evidence_output_path,
        source_url=_plain_str(data.get("source_url")),
        runtime_status=_plain_str(data.get("runtime_status")),
        reference_review_ready=_bool(data.get("reference_review_ready")),
        allowed_for_model_context=_bool(data.get("allowed_for_model_context")),
        evidence_written=_bool(data.get("evidence_written")),
        runtime_fetch_performed=_bool(data.get("runtime_fetch_performed")),
        transport_called=_bool(data.get("transport_called")),
        external_network_call_performed=_bool(
            data.get("external_network_call_performed")
        ),
        raw_response_included=_bool(data.get("raw_response_included")),
        raw_html_included=_bool(data.get("raw_html_included")),
        response_headers_included=_bool(data.get("response_headers_included")),
        uploads_content=_bool(data.get("uploads_content")),
        writes_files=_bool(data.get("writes_files")),
        content_hash=_plain_str(data.get("content_hash")),
        sanitized_excerpt_preview=_plain_str(
            data.get("sanitized_excerpt_preview")
        ),
        total_excerpt_chars=_non_negative_int(data.get("total_excerpt_chars")),
        blocking_reasons=_string_list(data.get("blocking_reasons")),
        warnings=_string_list(data.get("warnings")),
        metadata_keys=sorted(metadata),
        contract_candidate_notes=[
            "Candidate observation only; not a public contract.",
            "External-readonly provider implementation is not owned here.",
            "Only sanitized evidence summary fields are projected.",
            "Raw payload, header values, and config_context values are not stored.",
            "Does not read files, call network, write files, or call models.",
        ],
        created_at=datetime.now(UTC).isoformat(),
    )


def build_external_readonly_evidence_observation_candidates_from_read_context(
    context: Any,
) -> tuple[ExternalReadonlyEvidenceObservationCandidate, ...]:
    """Build observation candidates from a prepared-only read context."""

    data = _mapping_or_raise(
        context,
        "external-readonly evidence read context",
    )
    summaries = data.get("summaries")
    if summaries is None:
        return ()
    if isinstance(summaries, str | bytes) or isinstance(summaries, Mapping):
        raise ValueError("summaries must be a sequence of evidence summaries.")
    if not isinstance(summaries, Sequence):
        raise ValueError("summaries must be a sequence of evidence summaries.")
    return tuple(
        build_external_readonly_evidence_observation_candidate(summary)
        for summary in summaries
    )


def _mapping_or_raise(value: Any, input_name: str) -> dict[str, Any]:
    data = _mapping(value)
    if data:
        return data
    if value is None or value == {}:
        return {}
    raise ValueError(f"{input_name} must be a mapping or dataclass-like object.")


def _mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return {
            str(key): item
            for key, item in value.items()
            if isinstance(key, str)
        }
    if is_dataclass(value) and not isinstance(value, type):
        return _mapping(asdict(value))
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="python")
        if isinstance(dumped, Mapping):
            return _mapping(dumped)
    return {}


def _required_str(value: Any, field_name: str) -> str:
    text = _plain_str(value)
    if not text:
        raise ValueError(f"{field_name} is required.")
    return text


def _plain_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y"}:
            return True
        if normalized in {"", "0", "false", "no", "n"}:
            return False
    return bool(value)


def _non_negative_int(value: Any) -> int:
    if isinstance(value, bool) or value is None:
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence) and not isinstance(value, bytes):
        return [str(item) for item in value if item is not None]
    return []
