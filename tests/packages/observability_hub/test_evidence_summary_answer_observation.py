from __future__ import annotations

import copy

import pytest

from observability_hub import (
    EvidenceSummaryAnswerPolicyObservationCandidate,
    build_evidence_summary_answer_policy_observation_candidate,
)
from schemas.evidence_summary_answer import (
    EVIDENCE_SUMMARY_ANSWER_CONTEXT_VERSION,
    EVIDENCE_SUMMARY_ANSWER_PRODUCT,
    EVIDENCE_SUMMARY_ANSWER_RESULT_VERSION,
    GOVERNED_EVIDENCE_DIGEST_VERSION,
)


_FACT_TEXT = "Governed fact text must stay out of observability."
_QUESTION_TEXT = "What does the governed evidence say?"
_ANSWER_TEXT = "The governed evidence supports a contract-first answer."
_ANSWER_PREVIEW_TEXT = "The governed evidence supports a contract-first answer."
_PREVIEW_TEXT = "Preview text must stay out of observability."
_RAW_TEXT = "Provider payload value must stay out."
_PROVIDER_RAW_TEXT = "Provider response value must stay out."
_CONFIG_VALUE = "Configuration value must stay out."


def test_builds_digest_observation_with_policy_and_guard_outcome() -> None:
    observation = build_evidence_summary_answer_policy_observation_candidate(
        _digest(),
        guard_outcome=_guard_outcome(),
        policy_summary=_policy_summary(),
    )

    assert isinstance(observation, EvidenceSummaryAnswerPolicyObservationCandidate)
    assert observation.source == "observability_hub.evidence_summary_answer"
    assert observation.payload_type == "governed_evidence_digest"
    assert observation.schema_validation_passed is True
    assert observation.schema_validation_error_count == 0
    assert observation.guard_validation_passed is True
    assert observation.guard_violation_count == 0
    assert observation.guard_names == [
        "evidence_summary_answer_header_guard",
        "evidence_summary_answer_no_raw_boundary_guard",
    ]
    assert observation.policy_profile == "smoke_only"
    assert observation.policy_ref == "policy://evidence-summary-answer/smoke-only"
    assert observation.config_source_ref == "config://runtime/evidence-summary-answer"
    assert observation.exposure_enabled is True
    assert observation.allow_model_context is True
    assert observation.citation_required is True
    assert observation.insufficient_evidence_required is True
    assert observation.enabled_by_default is False
    assert observation.raw_boundary_allowed is False
    assert observation.sanitized_excerpt_preview_allowed is False
    assert observation.observability_candidate_body_allowed is False
    assert observation.citation_exception_allowed is False
    assert observation.evidence_refs == [
        "evidence://external-readonly/request-1/fetch-1"
    ]
    assert observation.digest_refs == [
        "governed-evidence-digest://request-1/digest-1"
    ]
    assert observation.summary_fact_count == 1
    assert observation.summary_fact_total_chars == len(_FACT_TEXT)
    assert observation.metadata["does_not_store_raw_payload"] is True
    assert observation.metadata["does_not_store_summary_facts"] is True
    assert observation.metadata["does_not_store_answer"] is True
    assert observation.metadata["does_not_store_user_question"] is True
    assert observation.metadata["does_not_store_config_context_value"] is True
    assert observation.metadata["does_not_call_model"] is True
    assert observation.metadata["does_not_fetch_or_search"] is True

    serialized = observation.model_dump_json()
    assert _FACT_TEXT not in serialized
    assert _CONFIG_VALUE not in serialized


def test_builds_context_observation_without_storing_question_or_facts() -> None:
    observation = build_evidence_summary_answer_policy_observation_candidate(
        _context(),
        policy_summary=_policy_summary(),
    )

    assert observation.request_id == "request-1"
    assert observation.payload_type == "evidence_summary_answer_context"
    assert observation.schema_validation_passed is True
    assert observation.user_question_present is True
    assert observation.evidence_ref_count == 1
    assert observation.digest_ref_count == 1
    assert observation.summary_fact_count == 1
    assert observation.policy_ref == "policy://evidence-summary-answer/smoke-only"

    serialized = observation.model_dump_json()
    assert _QUESTION_TEXT not in serialized
    assert _FACT_TEXT not in serialized


def test_builds_result_observation_without_storing_answer_text() -> None:
    observation = build_evidence_summary_answer_policy_observation_candidate(
        _result()
    )

    assert observation.request_id == "request-1"
    assert observation.payload_type == "evidence_summary_answer_result"
    assert observation.status == "success"
    assert observation.schema_validation_passed is True
    assert observation.answer_present is True
    assert observation.answer_preview_present is True
    assert observation.evidence_refs == [
        "evidence://external-readonly/request-1/fetch-1"
    ]
    assert observation.digest_refs == [
        "governed-evidence-digest://request-1/digest-1"
    ]

    serialized = observation.model_dump_json()
    assert _ANSWER_TEXT not in serialized
    assert _ANSWER_PREVIEW_TEXT not in serialized


def test_records_invalid_schema_and_raw_boundary_presence_without_storing_values() -> None:
    payload = _digest()
    payload["sanitized_excerpt_preview"] = _PREVIEW_TEXT
    payload["raw_payload"] = _RAW_TEXT
    payload["raw_provider_response"] = _PROVIDER_RAW_TEXT
    payload["metadata"] = {"config_context_value": _CONFIG_VALUE}
    payload["raw_boundary_flags"] = {
        "sanitized_excerpt_preview_included": True,
        "raw_payload_included": True,
        "raw_provider_response_included": True,
    }

    observation = build_evidence_summary_answer_policy_observation_candidate(
        payload,
        guard_outcome={
            "passed": False,
            "violations": [
                "evidence_summary_answer_no_raw_boundary_guard: boundary violation"
            ],
        },
    )

    assert observation.schema_validation_passed is False
    assert observation.schema_validation_error_count == 1
    assert observation.guard_validation_passed is False
    assert observation.guard_violation_count == 1
    assert observation.guard_names == ["evidence_summary_answer_no_raw_boundary_guard"]
    assert observation.raw_boundary_violation_count >= 4
    assert observation.sanitized_excerpt_preview_present is True
    assert "sanitized_excerpt_preview" not in observation.model_dump()

    serialized = observation.model_dump_json()
    assert _PREVIEW_TEXT not in serialized
    assert _RAW_TEXT not in serialized
    assert _PROVIDER_RAW_TEXT not in serialized
    assert _CONFIG_VALUE not in serialized


def test_rejects_non_mapping_payload() -> None:
    with pytest.raises(ValueError, match="must be a mapping"):
        build_evidence_summary_answer_policy_observation_candidate(42)


def test_root_public_surface_exports_evidence_summary_answer_observation() -> None:
    assert EvidenceSummaryAnswerPolicyObservationCandidate.__name__ == (
        "EvidenceSummaryAnswerPolicyObservationCandidate"
    )
    assert callable(build_evidence_summary_answer_policy_observation_candidate)


def _digest() -> dict[str, object]:
    return {
        "product": EVIDENCE_SUMMARY_ANSWER_PRODUCT,
        "payload_type": "governed_evidence_digest",
        "payload_version": GOVERNED_EVIDENCE_DIGEST_VERSION,
        "digest_id": "digest-1",
        "digest_ref": "governed-evidence-digest://request-1/digest-1",
        "evidence_ref": "evidence://external-readonly/request-1/fetch-1",
        "evidence_output_ref": "external-readonly-output://request-1/fetch-1",
        "source_url_host": "example.com",
        "source_url_scheme": "https",
        "runtime_status": "success",
        "status": "ready",
        "reference_review_ready": True,
        "allowed_for_model_context": True,
        "evidence_written": True,
        "content_hash": "sha256:abc123",
        "total_excerpt_chars": len(_FACT_TEXT),
        "raw_boundary_flags": {},
        "blocking_reasons": [],
        "warnings": [],
        "summary_facts": [_FACT_TEXT],
        "topic_labels": ["contracts"],
        "risk_labels": [],
        "answerability": "answerable",
        "digest_generation_policy_ref": (
            "policy://evidence-summary-answer/digest-generation-v1"
        ),
        "digest_budget": 4000,
        "metadata": {"source": "observability-hub.test"},
    }


def _context() -> dict[str, object]:
    return {
        "product": EVIDENCE_SUMMARY_ANSWER_PRODUCT,
        "payload_type": "evidence_summary_answer_context",
        "payload_version": EVIDENCE_SUMMARY_ANSWER_CONTEXT_VERSION,
        "request_id": "request-1",
        "user_question": _QUESTION_TEXT,
        "digests": [copy.deepcopy(_digest())],
        "evidence_refs": [
            {
                "ref": "evidence://external-readonly/request-1/fetch-1",
                "kind": "external_readonly_evidence",
                "purpose": "answer_context",
            }
        ],
        "additional_refs": [
            {
                "ref": "governed-evidence-digest://request-1/digest-1",
                "kind": "governed_evidence_digest",
                "purpose": "digest_context",
            }
        ],
        "answer_policy_ref": "policy://evidence-summary-answer/answer-v1",
        "citation_policy_ref": "policy://evidence-summary-answer/citation-v1",
        "model_context_budget": 4000,
        "metadata": {"source": "observability-hub.test"},
    }


def _result() -> dict[str, object]:
    return {
        "product": EVIDENCE_SUMMARY_ANSWER_PRODUCT,
        "payload_type": "evidence_summary_answer_result",
        "payload_version": EVIDENCE_SUMMARY_ANSWER_RESULT_VERSION,
        "request_id": "request-1",
        "status": "success",
        "answer": _ANSWER_TEXT,
        "answer_preview": _ANSWER_PREVIEW_TEXT,
        "evidence_refs_used": [
            {
                "ref": "evidence://external-readonly/request-1/fetch-1",
                "kind": "external_readonly_evidence",
                "purpose": "citation",
            }
        ],
        "digest_refs_used": ["governed-evidence-digest://request-1/digest-1"],
        "additional_refs_used": [],
        "insufficient_evidence_reason": None,
        "citation_failures": [],
        "blocking_reasons": [],
        "warnings": [],
        "llm_call_allowed": True,
        "llm_call_attempted": True,
        "llm_runtime_call_performed": True,
        "raw_boundary_flags": {},
        "metadata": {"source": "observability-hub.test"},
    }


def _guard_outcome() -> dict[str, object]:
    return {
        "passed": True,
        "violations": [],
        "guard_names": [
            "evidence_summary_answer_header_guard",
            "evidence_summary_answer_no_raw_boundary_guard",
        ],
    }


def _policy_summary() -> dict[str, object]:
    return {
        "profile": "smoke_only",
        "policy_ref": "policy://evidence-summary-answer/smoke-only",
        "config_source_ref": "config://runtime/evidence-summary-answer",
        "exposure_enabled": True,
        "allow_model_context": True,
        "citation_required": True,
        "insufficient_evidence_required": True,
        "enabled_by_default": False,
        "allow_raw_boundary": False,
        "allow_sanitized_excerpt_preview": False,
        "allow_observability_candidate_body": False,
        "allow_citation_exception": False,
        "metadata": {"source": "config/base/runtime.yaml", "value": _CONFIG_VALUE},
    }
