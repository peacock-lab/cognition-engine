from __future__ import annotations

import json

import pytest

from behavior_contracts import (
    EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_PUBLIC_REFS_PAYLOAD_TYPE
    as ROOT_PAYLOAD_TYPE,
    EvidenceSummaryAnswerOutcomeObservationReadonlyPublicRefs
    as RootReadonlyPublicRefs,
    build_evidence_summary_answer_outcome_observation_readonly_facts
    as root_build_facts,
    validate_evidence_summary_answer_outcome_observation_readonly_public_refs
    as root_validate_public_refs,
)
from behavior_contracts.evidence_summary_answer import (
    EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_PUBLIC_REFS_PAYLOAD_TYPE,
    EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_PUBLIC_REFS_VERSION,
    EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_REF_PREFIX,
    EvidenceSummaryAnswerOutcomeObservationReadonlyPublicRefs,
    build_evidence_summary_answer_outcome_observation_readonly_facts,
    build_evidence_summary_answer_outcome_observation_readonly_facts_from_candidates,
    build_evidence_summary_answer_outcome_observation_readonly_public_refs,
    evidence_summary_answer_outcome_observation_readonly_public_refs_status_dict,
    validate_evidence_summary_answer_outcome_observation_readonly_public_refs,
)


_OBSERVATION_REF = f"{EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_REF_PREFIX}obs-1"
_EVIDENCE_REF = "evidence://external-readonly/request-1/fetch-1"
_DIGEST_REF = "governed-evidence-digest://request-1/digest-1"
_ANSWER_TEXT = "The governed answer text must not leak."
_QUESTION_TEXT = "What does the governed evidence say?"
_SUMMARY_FACT_TEXT = "A governed fact must not leak."
_PREVIEW_TEXT = "Preview text must not leak."


def test_builds_sanitized_outcome_observation_readonly_public_refs() -> None:
    facts = build_evidence_summary_answer_outcome_observation_readonly_facts(
        observation_candidate_ids=("obs-1", "obs-1"),
        request_ids=("request-1",),
        result_statuses=("success",),
        external_readonly_evidence_refs=(_EVIDENCE_REF,),
        governed_evidence_digest_refs=(_DIGEST_REF,),
        summary_fact_count=1,
        schema_validation_passed=True,
        schema_validation_error_count=0,
        guard_validation_passed=True,
        guard_violation_count=0,
        guard_names=("evidence_summary_answer_result_mapping_guard",),
        answer_present=True,
        answer_preview_present=True,
        raw_boundary_violation_count=0,
        policy_profile="controlled_live_answer_generation",
        policy_ref="policy://evidence-summary-answer/answer-v1",
        config_source_ref="config://runtime/evidence-summary-answer",
        metadata={
            "source": "unit-test",
            "answer": _ANSWER_TEXT,
            "user_question": _QUESTION_TEXT,
            "summary_facts": _SUMMARY_FACT_TEXT,
            "sanitized_excerpt_preview": _PREVIEW_TEXT,
            "object_module": "observability_hub.internal",
            "nested": {"ignored": "not compact"},
        },
    )
    public_refs = build_evidence_summary_answer_outcome_observation_readonly_public_refs(
        evidence_summary_answer_outcome_observation_refs=(_OBSERVATION_REF,),
        external_readonly_evidence_refs=(_EVIDENCE_REF,),
        governed_evidence_digest_refs=(_DIGEST_REF,),
        facts=facts,
        metadata={
            "source": "unit-test",
            "raw_payload": "must-not-leak",
            "object_module": "product_gateway.internal",
        },
    )
    status = evidence_summary_answer_outcome_observation_readonly_public_refs_status_dict(
        public_refs
    )
    serialized = json.dumps(status, ensure_ascii=False, sort_keys=True)
    status_facts = status[
        "evidence_summary_answer_outcome_observation_readonly_facts"
    ]

    assert isinstance(public_refs, EvidenceSummaryAnswerOutcomeObservationReadonlyPublicRefs)
    assert status["payload_type"] == (
        EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_PUBLIC_REFS_PAYLOAD_TYPE
    )
    assert status["payload_version"] == (
        EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_PUBLIC_REFS_VERSION
    )
    assert status["evidence_summary_answer_outcome_observation_refs"] == [
        _OBSERVATION_REF
    ]
    assert status_facts["observation_candidate_ids"] == ["obs-1"]
    assert status_facts["status"] == "success"
    assert status_facts["candidate_count"] == 1
    assert status_facts["answer_present"] is True
    assert status_facts["answer_preview_present"] is True
    assert status_facts["does_not_store_answer"] is True
    assert status_facts["does_not_store_user_question"] is True
    assert status_facts["does_not_store_summary_facts"] is True
    assert status_facts["metadata"] == {"source": "unit-test"}
    assert status["metadata"] == {"source": "unit-test"}
    assert _ANSWER_TEXT not in serialized
    assert _QUESTION_TEXT not in serialized
    assert _SUMMARY_FACT_TEXT not in serialized
    assert _PREVIEW_TEXT not in serialized
    assert "observability_hub.internal" not in serialized
    assert "product_gateway.internal" not in serialized


def test_outcome_observation_readonly_facts_aggregate_empty_and_mixed_status() -> None:
    empty_facts = build_evidence_summary_answer_outcome_observation_readonly_facts()
    empty_refs = build_evidence_summary_answer_outcome_observation_readonly_public_refs(
        facts=empty_facts
    )
    empty_status = (
        evidence_summary_answer_outcome_observation_readonly_public_refs_status_dict(
            empty_refs
        )
    )

    assert empty_status[
        "evidence_summary_answer_outcome_observation_readonly_facts"
    ]["status"] == "empty"

    mixed_facts = build_evidence_summary_answer_outcome_observation_readonly_facts(
        observation_candidate_ids=("obs-1", "obs-2"),
        request_ids=("request-1", "request-2"),
        result_statuses=("success", "blocked"),
        external_readonly_evidence_refs=(_EVIDENCE_REF,),
        governed_evidence_digest_refs=(_DIGEST_REF,),
    )

    assert mixed_facts.status == "mixed"
    assert mixed_facts.candidate_count == 2
    assert mixed_facts.request_count == 2


def test_builds_facts_from_candidate_like_mappings_without_candidate_body() -> None:
    facts = build_evidence_summary_answer_outcome_observation_readonly_facts_from_candidates(
        (
            {
                "observation_id": "obs-1",
                "request_id": "request-1",
                "status": "success",
                "evidence_refs": [_EVIDENCE_REF],
                "digest_refs": [_DIGEST_REF],
                "schema_validation_passed": True,
                "schema_validation_error_count": 0,
                "guard_validation_passed": True,
                "guard_violation_count": 0,
                "guard_names": ["evidence_summary_answer_result_mapping_guard"],
                "summary_fact_count": 1,
                "answer_present": True,
                "answer_preview_present": True,
                "raw_boundary_violation_count": 0,
                "policy_profile": "controlled_live_answer_generation",
                "policy_ref": "policy://evidence-summary-answer/answer-v1",
                "config_source_ref": "config://runtime/evidence-summary-answer",
                "answer": _ANSWER_TEXT,
                "summary_facts": [_SUMMARY_FACT_TEXT],
            },
        )
    )

    assert facts.status == "success"
    assert facts.observation_candidate_ids == ("obs-1",)
    assert facts.external_readonly_evidence_refs == (_EVIDENCE_REF,)
    assert facts.governed_evidence_digest_refs == (_DIGEST_REF,)
    assert facts.answer_present is True
    assert facts.metadata == {}


def test_validate_rejects_bad_refs_and_mismatched_facts() -> None:
    status = evidence_summary_answer_outcome_observation_readonly_public_refs_status_dict(
        _public_refs_contract()
    )
    status["external_readonly_evidence_refs"] = ["file://raw.json"]

    with pytest.raises(ValueError, match="external_readonly_evidence_refs"):
        validate_evidence_summary_answer_outcome_observation_readonly_public_refs(
            status
        )

    status = evidence_summary_answer_outcome_observation_readonly_public_refs_status_dict(
        _public_refs_contract()
    )
    status["governed_evidence_digest_refs"] = [
        "governed-evidence-digest://request-1/other"
    ]

    with pytest.raises(ValueError, match="governed_evidence_digest_refs"):
        validate_evidence_summary_answer_outcome_observation_readonly_public_refs(
            status
        )


def test_validate_rejects_leaked_answer_fields_and_disabled_boundary_flags() -> None:
    status = evidence_summary_answer_outcome_observation_readonly_public_refs_status_dict(
        _public_refs_contract()
    )
    facts = status["evidence_summary_answer_outcome_observation_readonly_facts"]
    facts["answer"] = _ANSWER_TEXT

    with pytest.raises(ValueError, match="answer"):
        validate_evidence_summary_answer_outcome_observation_readonly_public_refs(
            status
        )

    status = evidence_summary_answer_outcome_observation_readonly_public_refs_status_dict(
        _public_refs_contract()
    )
    status["evidence_summary_answer_outcome_observation_readonly_facts"][
        "does_not_store_answer"
    ] = False

    with pytest.raises(ValueError, match="does_not_store_answer"):
        validate_evidence_summary_answer_outcome_observation_readonly_public_refs(
            status
        )


def test_behavior_contracts_root_exports_outcome_observation_contract() -> None:
    assert ROOT_PAYLOAD_TYPE == (
        EVIDENCE_SUMMARY_ANSWER_OUTCOME_OBSERVATION_READONLY_PUBLIC_REFS_PAYLOAD_TYPE
    )
    assert RootReadonlyPublicRefs is EvidenceSummaryAnswerOutcomeObservationReadonlyPublicRefs
    assert callable(root_build_facts)
    assert callable(root_validate_public_refs)


def _public_refs_contract() -> EvidenceSummaryAnswerOutcomeObservationReadonlyPublicRefs:
    facts = build_evidence_summary_answer_outcome_observation_readonly_facts(
        observation_candidate_ids=("obs-1",),
        request_ids=("request-1",),
        result_statuses=("success",),
        external_readonly_evidence_refs=(_EVIDENCE_REF,),
        governed_evidence_digest_refs=(_DIGEST_REF,),
        schema_validation_passed=True,
        guard_validation_passed=True,
        guard_names=("evidence_summary_answer_result_mapping_guard",),
        answer_present=True,
        answer_preview_present=True,
    )
    return build_evidence_summary_answer_outcome_observation_readonly_public_refs(
        evidence_summary_answer_outcome_observation_refs=(_OBSERVATION_REF,),
        external_readonly_evidence_refs=(_EVIDENCE_REF,),
        governed_evidence_digest_refs=(_DIGEST_REF,),
        facts=facts,
    )
