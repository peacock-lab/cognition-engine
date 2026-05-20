from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from cognition_governance import (
    ALLOWED_HUMAN_REVIEW_RESULTS,
    GovernanceDecision,
    GovernanceOutcomeCandidate,
    GovernanceOutcomeCandidateResult,
    HumanReviewRecordCandidate,
    POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE,
    PRODUCT_AGENT_OUTPUT_GOVERNANCE_DECISION_CANDIDATE_SCOPE,
    build_adk_workflow_runner_policy_set_candidate,
    build_product_agent_output_governance_policy_set_candidate,
    build_release_governance_policy_set_candidate,
    create_governance_outcome_candidate,
    create_human_review_record_candidate,
    make_unified_governance_decision_candidate,
    map_agent_task_advice_payload_to_governance_evidence,
    map_product_agent_output_evidence_to_governance_case,
    map_product_gateway_response_summary_to_governance_evidence,
    map_release_check_output_to_governance_evidence,
    map_release_evidence_to_governance_case,
)
from cognition_governance.models import GovernanceCase, GovernanceEvidence


REPO_ROOT = Path(__file__).resolve().parents[3]
GOVERNANCE_SOURCE_ROOT = REPO_ROOT / "packages" / "cognition_governance" / "src"


def _adk_decision_candidate() -> GovernanceDecision:
    evidence = GovernanceEvidence(
        evidence_id="evidence-human-review-adk2-001",
        evidence_type="adk_workflow_runner_execution",
        source="observability_hub.adk_workflow_runner_evidence",
        summary="ADK2 WorkflowRunner evidence for human review tests.",
        metadata={
            "runtime_kind": "adk2_workflow_runner",
            "workflow_name": "human-review-adk2-workflow",
            "run_config": {"mapped_fields": ["max_llm_calls"]},
            "service_bundle": {"source": "in_memory"},
            "artifact_summary": {"artifact_count": 1},
            "session_summary": {"session_id": "session-human-review-adk2-001"},
            "event_summary": {"event_count": 2},
        },
    )
    case = GovernanceCase(
        case_id="case-human-review-adk2-001",
        title="ADK2 human review candidate",
        case_type="adk_workflow_runner_governance_review",
        context={"workflow_name": "human-review-adk2-workflow", "risk_level": "low"},
        evidence_refs=[evidence.evidence_id],
        policy_refs=["policy-adk2-workflow-runner-governance"],
        metadata={"findings": [], "required_followups": []},
    )
    result = make_unified_governance_decision_candidate(
        case,
        evidence,
        policy_set_candidate=build_adk_workflow_runner_policy_set_candidate(),
        domain_metadata={"workflow_name": "human-review-adk2-workflow"},
    )
    return result.decision_candidate


def _release_decision_candidate() -> GovernanceDecision:
    evidence = [
        map_release_check_output_to_governance_evidence(
            {
                "script_name": "check_public_surface.py",
                "target_version": "0.6.0",
                "phase": "pre-release",
                "final_status": "PASS",
                "failure_codes": [],
            }
        )
    ]
    case = map_release_evidence_to_governance_case(
        evidence,
        release_target="public_repo_and_pypi",
    )
    result = make_unified_governance_decision_candidate(
        case,
        evidence,
        policy_set_candidate=build_release_governance_policy_set_candidate(),
        domain_metadata={
            "target_version": "0.6.0",
            "phase": "pre-release",
            "release_target": "public_repo_and_pypi",
        },
    )
    return result.decision_candidate


def _product_agent_output_decision_candidate() -> GovernanceDecision:
    evidence = [
        map_product_gateway_response_summary_to_governance_evidence(
            _product_gateway_summary()
        ),
        map_agent_task_advice_payload_to_governance_evidence(_agent_task_advice_payload()),
    ]
    case = map_product_agent_output_evidence_to_governance_case(evidence)
    result = make_unified_governance_decision_candidate(
        case,
        evidence,
        policy_set_candidate=build_product_agent_output_governance_policy_set_candidate(),
    )
    return result.decision_candidate


def _product_gateway_summary() -> dict[str, object]:
    return {
        "product": "product_gateway",
        "payload_type": "product_gateway_response_summary",
        "payload_version": "product_gateway_response_summary_v1",
        "request_id": "request-human-review-product-agent-001",
        "entry_kind": "agent_shell",
        "status": "success",
        "exit_code": 0,
        "product_gateway_response_ref": (
            "product-gateway-response://request-human-review-product-agent-001"
        ),
        "governance_summary_ref": (
            "governance-summary://request-human-review-product-agent-001"
        ),
        "evidence_refs": [
            {
                "ref": "evidence://request-human-review-product-agent-001",
                "kind": "evidence",
            }
        ],
        "audit_refs": [],
        "agent_advice_refs": [],
        "tool_audit_refs": [],
        "blocking_reasons": [],
        "warnings": [],
    }


def _agent_task_advice_payload() -> dict[str, object]:
    return {
        "product": "cognition_agent",
        "payload_type": "agent_task_advice_consumption_payload",
        "payload_version": "agent_task_advice_consumption_payload_v1",
        "candidate_id": "agent-task-advice-human-review-001",
        "task_context_candidate_id": "agent-task-context-human-review-001",
        "task_candidate_id": "agent-task-human-review-001",
        "product_gateway_request_id": "request-human-review-product-agent-001",
        "product_gateway_entry_kind": "agent_shell",
        "product_gateway_status": "success",
        "product_gateway_exit_code": 0,
        "recommendation": "continue_with_product_gateway_review",
        "status": "ready_for_product_gateway_review",
        "readonly": True,
        "candidate_only": True,
        "execution_enabled": False,
    }


def test_creates_human_review_record_from_decision_candidate_without_mutation() -> None:
    decision = _adk_decision_candidate()
    before = decision.model_dump(mode="python")

    review = create_human_review_record_candidate(
        decision,
        reviewer="release-governance-reviewer",
        review_result="accept_candidate",
        review_reasons=["Candidate can move to the next governance review step."],
        reviewed_at="2026-05-07T10:00:00+00:00",
    )

    assert isinstance(review, HumanReviewRecordCandidate)
    assert review.decision_candidate_id == decision.decision_id
    assert review.case_id == decision.case_id
    assert review.review_result == "accept_candidate"
    assert review.review_result in ALLOWED_HUMAN_REVIEW_RESULTS
    assert review.metadata["review_semantics"] == "candidate_only"
    assert review.metadata["formal_decision_enabled"] is False
    assert review.metadata["formal_outcome_enabled"] is False
    assert review.metadata["release_action_enabled"] is False
    assert review.metadata["does_not_mutate_decision_candidate"] is True
    assert decision.model_dump(mode="python") == before


def test_reject_candidate_review_does_not_create_block_or_action() -> None:
    decision = _release_decision_candidate()
    review = create_human_review_record_candidate(
        decision,
        reviewer="release-governance-reviewer",
        review_result="reject_candidate",
        review_reasons=["Evidence needs another pass before later review."],
        required_followups=["Refresh release evidence."],
        reviewed_at="2026-05-07T10:05:00+00:00",
    )

    assert review.review_result == "reject_candidate"
    assert review.metadata["release_action_enabled"] is False
    assert "can_publish" not in repr(review.model_dump(mode="python"))
    assert "can_release" not in repr(review.model_dump(mode="python"))


def test_creates_governance_outcome_candidate_from_decision_and_review() -> None:
    decision = _adk_decision_candidate()
    review = create_human_review_record_candidate(
        decision,
        reviewer="architecture-reviewer",
        review_result="request_fix",
        required_followups=["Record service bundle follow-up."],
        reviewed_at="2026-05-07T10:10:00+00:00",
    )

    result = create_governance_outcome_candidate(
        decision,
        review,
        domain_metadata={"service_bundle_followup": "Record source and lifecycle."},
    )

    assert isinstance(result, GovernanceOutcomeCandidateResult)
    assert result.human_review_record == review
    outcome = result.outcome_candidate
    assert isinstance(outcome, GovernanceOutcomeCandidate)
    assert outcome.decision_candidate_id == decision.decision_id
    assert outcome.human_review_id == review.review_id
    assert outcome.status_candidate == "deferred"
    assert outcome.outcome_semantics == "candidate_only"
    assert outcome.formal_decision_required is True
    assert outcome.formal_outcome_enabled is False
    assert outcome.release_action_enabled is False
    assert outcome.metadata["outcome_semantics"] == "candidate_only"
    assert outcome.metadata["formal_decision_required"] is True
    assert outcome.metadata["formal_outcome_enabled"] is False
    assert outcome.metadata["release_action_enabled"] is False
    assert outcome.blocked_formal_outcome_reasons
    assert "service_bundle_followup" in outcome.domain_metadata["extra"]
    assert not hasattr(result, "formal_decision")
    assert not hasattr(result, "governance_outcome")


def test_release_outcome_candidate_does_not_record_real_action_result() -> None:
    decision = _release_decision_candidate()
    review = create_human_review_record_candidate(
        decision,
        reviewer="release-governance-reviewer",
        review_result="defer",
        required_followups=["Wait for release action boundary review."],
        reviewed_at="2026-05-07T10:15:00+00:00",
    )

    result = create_governance_outcome_candidate(
        decision,
        review,
        domain_metadata={
            "target_version": "0.6.0",
            "release_target": "public_repo_and_pypi",
        },
    )

    outcome = result.outcome_candidate
    assert outcome.status_candidate == "deferred"
    assert outcome.policy_domain == "release_governance"
    assert outcome.release_action_enabled is False
    assert outcome.metadata["does_not_record_real_action_result"] is True
    assert "target_version" in outcome.domain_metadata["extra"]
    serialized = repr(result.model_dump(mode="python"))
    assert "can_publish" not in serialized
    assert "can_release" not in serialized
    assert "tag_release_and_publish" not in serialized


def test_product_agent_output_review_preserves_policy_domain() -> None:
    decision = _product_agent_output_decision_candidate()
    before = decision.model_dump(mode="python")

    review = create_human_review_record_candidate(
        decision,
        reviewer="product-agent-governance-reviewer",
        review_result="accept_candidate",
        review_reasons=["Product-agent output can continue to candidate review."],
        reviewed_at="2026-05-13T10:30:00+00:00",
    )

    assert review.policy_domain == POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE
    assert review.candidate_scope == (
        PRODUCT_AGENT_OUTPUT_GOVERNANCE_DECISION_CANDIDATE_SCOPE
    )
    assert review.metadata["review_semantics"] == "candidate_only"
    assert review.metadata["formal_decision_enabled"] is False
    assert review.metadata["policy_execution_enabled"] is False
    assert review.metadata["formal_outcome_enabled"] is False
    assert review.metadata["release_action_enabled"] is False
    assert review.metadata["does_not_mutate_decision_candidate"] is True
    assert decision.model_dump(mode="python") == before


def test_product_agent_output_outcome_candidate_preserves_domain_metadata() -> None:
    decision = _product_agent_output_decision_candidate()
    review = create_human_review_record_candidate(
        decision,
        reviewer="product-agent-governance-reviewer",
        review_result="request_fix",
        required_followups=["Record product-agent output follow-up."],
        reviewed_at="2026-05-13T10:35:00+00:00",
    )

    result = create_governance_outcome_candidate(decision, review)

    outcome = result.outcome_candidate
    assert outcome.policy_domain == POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE
    assert outcome.status_candidate == "deferred"
    assert outcome.outcome_semantics == "candidate_only"
    assert outcome.formal_outcome_enabled is False
    assert outcome.release_action_enabled is False
    assert outcome.metadata["does_not_record_real_action_result"] is True
    assert outcome.domain_metadata["product_gateway_request_id"] == (
        "request-human-review-product-agent-001"
    )
    assert outcome.domain_metadata["agent_advice_candidate_id"] == (
        "agent-task-advice-human-review-001"
    )
    assert outcome.domain_metadata["summary_only"] is True
    assert outcome.domain_metadata["refs_only"] is True
    assert outcome.domain_metadata["candidate_only"] is True
    assert "Release action boundary review is pending." not in (
        outcome.blocked_formal_outcome_reasons
    )
    assert "Product-agent output action boundary review is pending." in (
        outcome.blocked_formal_outcome_reasons
    )
    assert "Product / agent execution remains disabled." in (
        outcome.blocked_formal_outcome_reasons
    )
    serialized = repr(result.model_dump(mode="python"))
    assert "can_publish" not in serialized
    assert "can_release" not in serialized
    assert "tag_release_and_publish" not in serialized
    assert not hasattr(result, "formal_decision")
    assert not hasattr(result, "governance_outcome")


def test_invalid_review_result_is_rejected() -> None:
    decision = _adk_decision_candidate()

    with pytest.raises(ValidationError):
        create_human_review_record_candidate(
            decision,
            reviewer="architecture-reviewer",
            review_result="approve",  # type: ignore[arg-type]
            reviewed_at="2026-05-07T10:20:00+00:00",
        )


def test_outcome_candidate_requires_matching_human_review_record() -> None:
    decision = _adk_decision_candidate()
    other_decision = _release_decision_candidate()
    review = create_human_review_record_candidate(
        other_decision,
        reviewer="release-governance-reviewer",
        review_result="defer",
        reviewed_at="2026-05-07T10:25:00+00:00",
    )

    with pytest.raises(ValueError):
        create_governance_outcome_candidate(decision, review)


def test_unknown_policy_domain_does_not_fallback_to_release_governance() -> None:
    decision = GovernanceDecision(
        decision_id="decision-unknown-policy-domain-001",
        case_id="case-unknown-policy-domain-001",
        decision="continue",
        rationale="Unknown policy domain should not be silently remapped.",
        metadata={
            "policy_domain": "unknown_governance_domain",
            "decision_semantics": "candidate_only",
            "formal_decision_enabled": False,
        },
    )

    with pytest.raises(ValueError, match="Unsupported policy_domain"):
        create_human_review_record_candidate(
            decision,
            reviewer="governance-reviewer",
            review_result="defer",
            reviewed_at="2026-05-13T10:40:00+00:00",
        )


def test_human_review_outcome_source_keeps_runtime_and_script_layers_out() -> None:
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:google\.adk|adk_adapter|runtime_container|composition|scripts|subprocess)\b",
        re.MULTILINE,
    )

    for source_path in GOVERNANCE_SOURCE_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_imports.search(source) is None, source_path
