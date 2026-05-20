from __future__ import annotations

import pytest
from contract_core.external_readonly_evidence import (
    ExternalReadonlyEvidenceReadContext,
    ExternalReadonlyEvidenceSummary,
    external_readonly_evidence_read_context_status_dict,
    external_readonly_evidence_summary_status_dict,
)

from observability_hub import (
    ExternalReadonlyEvidenceObservationCandidate,
    build_external_readonly_evidence_observation_candidate,
    build_external_readonly_evidence_observation_candidates_from_read_context,
)


def test_builds_ready_external_readonly_evidence_observation() -> None:
    candidate = build_external_readonly_evidence_observation_candidate(
        _ready_summary()
    )

    assert isinstance(candidate, ExternalReadonlyEvidenceObservationCandidate)
    assert candidate.observation_id.startswith(
        "external-readonly-evidence-observation-"
    )
    assert candidate.source == "observability_hub.external_readonly_evidence"
    assert candidate.status == "ready"
    assert candidate.evidence_output_path == _EVIDENCE_OUTPUT_PATH
    assert candidate.evidence_ref == _EVIDENCE_REF
    assert candidate.source_url == "https://example.com/reference"
    assert candidate.runtime_status == "completed"
    assert candidate.reference_review_ready is True
    assert candidate.allowed_for_model_context is True
    assert candidate.evidence_written is True
    assert candidate.runtime_fetch_performed is True
    assert candidate.transport_called is True
    assert candidate.external_network_call_performed is True
    assert candidate.raw_response_included is False
    assert candidate.raw_html_included is False
    assert candidate.response_headers_included is False
    assert candidate.uploads_content is False
    assert candidate.writes_files is False
    assert candidate.content_hash == "sha256-safe"
    assert candidate.sanitized_excerpt_preview == "safe excerpt"
    assert candidate.total_excerpt_chars == len("safe excerpt")
    assert candidate.metadata_keys == [
        "config_context",
        "does_not_access_network",
        "does_not_call_model",
        "does_not_write_files",
    ]
    assert candidate.contract_candidate_notes


def test_builds_blocked_external_readonly_evidence_observation() -> None:
    candidate = build_external_readonly_evidence_observation_candidate(
        ExternalReadonlyEvidenceSummary(
            evidence_output_path=_EVIDENCE_OUTPUT_PATH,
            status="blocked",
            reference_review_ready=False,
            blocking_reasons=("evidence_file_missing",),
            warnings=("reference_review_unavailable",),
            metadata={"controlled_path_review": "passed"},
        )
    )

    assert candidate.status == "blocked"
    assert candidate.reference_review_ready is False
    assert candidate.blocking_reasons == ["evidence_file_missing"]
    assert candidate.warnings == ["reference_review_unavailable"]
    assert candidate.metadata_keys == ["controlled_path_review"]


def test_builds_observation_from_summary_status_dict() -> None:
    status = external_readonly_evidence_summary_status_dict(_ready_summary())

    candidate = build_external_readonly_evidence_observation_candidate(status)

    assert candidate.status == "ready"
    assert candidate.evidence_ref == _EVIDENCE_REF
    assert candidate.sanitized_excerpt_preview == "safe excerpt"


def test_builds_observations_from_read_context_dataclass() -> None:
    context = ExternalReadonlyEvidenceReadContext(
        status="ready",
        reference_review_ready=True,
        summaries=(
            _ready_summary("outputs/external-readonly/cli-fetch/one.json"),
            _ready_summary("outputs/external-readonly/cli-fetch/two.json"),
        ),
        evidence_output_paths=(
            "outputs/external-readonly/cli-fetch/one.json",
            "outputs/external-readonly/cli-fetch/two.json",
        ),
        evidence_refs=(
            "evidence://external-readonly/cli-fetch/one.json",
            "evidence://external-readonly/cli-fetch/two.json",
        ),
    )

    candidates = (
        build_external_readonly_evidence_observation_candidates_from_read_context(
            context
        )
    )

    assert len(candidates) == 2
    assert all(
        isinstance(
            candidate,
            ExternalReadonlyEvidenceObservationCandidate,
        )
        for candidate in candidates
    )
    assert [candidate.evidence_output_path for candidate in candidates] == [
        "outputs/external-readonly/cli-fetch/one.json",
        "outputs/external-readonly/cli-fetch/two.json",
    ]


def test_builds_observations_from_read_context_status_dict() -> None:
    context = ExternalReadonlyEvidenceReadContext(
        status="ready",
        reference_review_ready=True,
        summaries=(_ready_summary(),),
    )
    status = external_readonly_evidence_read_context_status_dict(context)

    candidates = (
        build_external_readonly_evidence_observation_candidates_from_read_context(
            status
        )
    )

    assert len(candidates) == 1
    assert candidates[0].evidence_output_path == _EVIDENCE_OUTPUT_PATH


def test_empty_read_context_returns_empty_tuple() -> None:
    context = ExternalReadonlyEvidenceReadContext(
        status="blocked",
        reference_review_ready=False,
    )

    assert (
        build_external_readonly_evidence_observation_candidates_from_read_context(
            context
        )
        == ()
    )


def test_rejects_invalid_observation_inputs() -> None:
    with pytest.raises(ValueError, match="mapping or dataclass-like"):
        build_external_readonly_evidence_observation_candidate(42)

    with pytest.raises(ValueError, match="evidence_output_path is required"):
        build_external_readonly_evidence_observation_candidate(
            {"status": "ready"}
        )

    with pytest.raises(ValueError, match="summaries must be a sequence"):
        build_external_readonly_evidence_observation_candidates_from_read_context(
            {"summaries": "outputs/external-readonly/cli-fetch/example.json"}
        )


def test_only_boundary_flags_and_metadata_keys_are_preserved() -> None:
    candidate = build_external_readonly_evidence_observation_candidate(
        {
            "evidence_output_path": _EVIDENCE_OUTPUT_PATH,
            "status": "ready",
            "reference_review_ready": True,
            "raw_response_included": True,
            "raw_html_included": True,
            "response_headers_included": True,
            "metadata": {
                "source": "test",
                "config_context": {
                    "token": "config-context-token-value",
                    "authorization": "authorization-header-value",
                },
            },
            "raw_response": "raw-response-secret-value",
            "raw_html": "<html>raw-html-secret-value</html>",
            "response_headers": {"set-cookie": "cookie-header-value"},
        }
    )

    serialized = candidate.model_dump_json()

    assert candidate.raw_response_included is True
    assert candidate.raw_html_included is True
    assert candidate.response_headers_included is True
    assert candidate.metadata_keys == ["config_context", "source"]
    assert "config-context-token-value" not in serialized
    assert "authorization-header-value" not in serialized
    assert "raw-response-secret-value" not in serialized
    assert "raw-html-secret-value" not in serialized
    assert "cookie-header-value" not in serialized


def test_root_public_surface_exports_external_readonly_bridge() -> None:
    assert ExternalReadonlyEvidenceObservationCandidate.__name__ == (
        "ExternalReadonlyEvidenceObservationCandidate"
    )
    assert callable(build_external_readonly_evidence_observation_candidate)
    assert callable(
        build_external_readonly_evidence_observation_candidates_from_read_context
    )


_EVIDENCE_OUTPUT_PATH = "outputs/external-readonly/cli-fetch/example.json"
_EVIDENCE_REF = "evidence://external-readonly/cli-fetch/example.json"


def _ready_summary(
    evidence_output_path: str = _EVIDENCE_OUTPUT_PATH,
) -> ExternalReadonlyEvidenceSummary:
    relative_name = evidence_output_path.rsplit("/", 1)[-1]
    return ExternalReadonlyEvidenceSummary(
        evidence_output_path=evidence_output_path,
        status="ready",
        reference_review_ready=True,
        evidence_ref=f"evidence://external-readonly/cli-fetch/{relative_name}",
        source_url="https://example.com/reference",
        runtime_status="completed",
        allowed_for_model_context=True,
        evidence_written=True,
        runtime_fetch_performed=True,
        transport_called=True,
        external_network_call_performed=True,
        raw_response_included=False,
        raw_html_included=False,
        response_headers_included=False,
        uploads_content=False,
        writes_files=False,
        content_hash="sha256-safe",
        sanitized_excerpt_preview="safe excerpt",
        total_excerpt_chars=len("safe excerpt"),
        metadata={
            "does_not_access_network": True,
            "does_not_write_files": True,
            "does_not_call_model": True,
            "config_context": {
                "token": "config-context-token-value",
            },
        },
    )
