from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from cognition_governance import (
    ALLOWED_RELEASE_ACTION_KINDS,
    FORBIDDEN_RELEASE_ACTION_KINDS,
    GovernanceDecision,
    ReleaseActionCandidate,
    ReleaseActionCandidateResult,
    build_release_governance_policy_set_candidate,
    create_governance_outcome_candidate,
    create_human_review_record_candidate,
    create_release_action_candidate,
    make_unified_governance_decision_candidate,
    map_release_check_output_to_governance_evidence,
    map_release_evidence_to_governance_case,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
GOVERNANCE_SOURCE_ROOT = REPO_ROOT / "packages" / "cognition_governance" / "src"


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
        ),
        map_release_check_output_to_governance_evidence(
            {
                "script_name": "release_safety_check.py",
                "target_version": "0.6.0",
                "phase": "pre-release",
                "final_status": "PASS",
                "failure_codes": [],
            }
        ),
    ]
    governance_case = map_release_evidence_to_governance_case(
        evidence,
        release_target="public_repo_and_pypi",
    )
    result = make_unified_governance_decision_candidate(
        governance_case,
        evidence,
        policy_set_candidate=build_release_governance_policy_set_candidate(),
        domain_metadata={
            "target_version": "0.6.0",
            "phase": "pre-release",
            "release_target": "public_repo_and_pypi",
        },
    )
    return result.decision_candidate


def _release_review_and_outcome(decision: GovernanceDecision):
    review = create_human_review_record_candidate(
        decision,
        reviewer="release-governance-reviewer",
        review_result="accept_candidate",
        review_reasons=["Candidate can move to release action candidate review."],
        reviewed_at="2026-05-07T11:00:00+00:00",
    )
    outcome_result = create_governance_outcome_candidate(
        decision,
        review,
        domain_metadata={
            "target_version": "0.6.0",
            "release_target": "public_repo_and_pypi",
        },
    )
    return review, outcome_result.outcome_candidate


def test_creates_release_action_candidate_from_candidate_chain() -> None:
    decision = _release_decision_candidate()
    review, outcome = _release_review_and_outcome(decision)

    result = create_release_action_candidate(
        decision,
        review,
        outcome,
        action_kind="verify_release_readiness",
        executor="release-operator-candidate",
        operator_notes=["Operator must confirm outside cognition_governance."],
        created_at="2026-05-07T11:05:00+00:00",
    )

    assert isinstance(result, ReleaseActionCandidateResult)
    action = result.action_candidate
    assert isinstance(action, ReleaseActionCandidate)
    assert action.decision_candidate_id == decision.decision_id
    assert action.human_review_id == review.review_id
    assert action.outcome_candidate_id == outcome.outcome_candidate_id
    assert action.case_id == decision.case_id
    assert action.action_kind == "verify_release_readiness"
    assert action.action_kind in ALLOWED_RELEASE_ACTION_KINDS
    assert action.action_domain == "release_governance"
    assert action.action_semantics == "candidate_only"
    assert action.execution_enabled is False
    assert action.requires_operator_confirmation is True
    assert action.reviewer == "release-governance-reviewer"
    assert action.executor == "release-operator-candidate"
    assert action.source_decision_kind == decision.decision
    assert action.source_review_result == "accept_candidate"
    assert action.source_outcome_status == "open"
    assert action.blocked_execution_reasons
    assert "operator_confirmation" in action.required_confirmations
    assert action.metadata["does_not_execute_release_action"] is True
    assert action.metadata["does_not_call_scripts"] is True
    assert not hasattr(result, "release_action")
    assert not hasattr(result, "formal_decision")
    assert not hasattr(result, "governance_outcome")


def test_missing_human_review_returns_blocked_candidate() -> None:
    decision = _release_decision_candidate()
    _, outcome = _release_review_and_outcome(decision)

    result = create_release_action_candidate(
        decision,
        outcome_candidate=outcome,
        action_kind="request_release_evidence",
    )

    action = result.action_candidate
    assert action.human_review_id is None
    assert action.reviewer is None
    assert action.execution_enabled is False
    assert "HumanReviewRecord candidate is missing." in action.blocked_execution_reasons


def test_missing_outcome_returns_blocked_candidate() -> None:
    decision = _release_decision_candidate()
    review, _ = _release_review_and_outcome(decision)

    result = create_release_action_candidate(
        decision,
        human_review_record=review,
        action_kind="request_release_fix",
    )

    action = result.action_candidate
    assert action.outcome_candidate_id is None
    assert action.execution_enabled is False
    assert "GovernanceOutcome candidate is missing." in action.blocked_execution_reasons


@pytest.mark.parametrize(
    "forbidden",
    ["release", "block", "pass", "publish", "upload", "twine_upload"],
)
def test_forbidden_action_kind_is_rejected(forbidden: str) -> None:
    decision = _release_decision_candidate()
    review, outcome = _release_review_and_outcome(decision)

    with pytest.raises(ValidationError):
        create_release_action_candidate(
            decision,
            review,
            outcome,
            action_kind=forbidden,  # type: ignore[arg-type]
        )

    assert forbidden in FORBIDDEN_RELEASE_ACTION_KINDS


def test_release_action_candidate_does_not_expose_release_block_pass_execution() -> None:
    decision = _release_decision_candidate()
    review, outcome = _release_review_and_outcome(decision)

    result = create_release_action_candidate(
        decision,
        review,
        outcome,
        action_kind="prepare_pypi_upload",
    )

    serialized = repr(result.model_dump(mode="python"))
    assert "can_publish" not in serialized
    assert "can_release" not in serialized
    assert "tag_release_and_publish" not in serialized
    assert "twine upload" not in serialized
    assert result.action_candidate.execution_enabled is False
    assert result.action_candidate.requires_operator_confirmation is True


def test_release_action_candidate_accepts_dict_inputs() -> None:
    decision = _release_decision_candidate()
    review, outcome = _release_review_and_outcome(decision)

    result = create_release_action_candidate(
        decision.model_dump(mode="python"),
        review.model_dump(mode="python"),
        outcome.model_dump(mode="python"),
        action_kind="record_release_followup",
    )

    action = result.action_candidate
    assert action.decision_candidate_id == decision.decision_id
    assert action.human_review_id == review.review_id
    assert action.outcome_candidate_id == outcome.outcome_candidate_id
    assert action.action_semantics == "candidate_only"


def test_release_action_source_keeps_scripts_and_execution_layers_out() -> None:
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:scripts|subprocess|requests|urllib|google\.adk|adk_adapter|runtime_container|composition)\b",
        re.MULTILINE,
    )
    forbidden_calls = re.compile(r"(?:subprocess\.|\.main\()")

    for source_path in GOVERNANCE_SOURCE_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_imports.search(source) is None, source_path
        assert forbidden_calls.search(source) is None, source_path
