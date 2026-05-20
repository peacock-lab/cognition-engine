from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from cognition_governance import (
    ALLOWED_ACTION_DOMAINS,
    ALLOWED_RUNTIME_ACTION_KINDS,
    ActionCandidate,
    ActionCandidateResult,
    FORBIDDEN_ACTION_KINDS,
    GovernanceCase,
    GovernanceDecision,
    GovernanceEvidence,
    RuntimeActionCandidate,
    RuntimeActionCandidateResult,
    build_adk_workflow_runner_policy_set_candidate,
    build_release_governance_policy_set_candidate,
    create_action_candidate,
    create_governance_outcome_candidate,
    create_human_review_record_candidate,
    create_release_action_candidate,
    create_runtime_action_candidate,
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
        )
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


def _runtime_decision_candidate() -> GovernanceDecision:
    evidence = GovernanceEvidence(
        evidence_id="evidence-action-adk2-001",
        evidence_type="adk_workflow_runner_execution",
        source="observability_hub.adk_workflow_runner_evidence",
        summary="ADK2 WorkflowRunner evidence for action candidate tests.",
        metadata={
            "runtime_kind": "adk2_workflow_runner",
            "runtime_id": "runtime-action-adk2-001",
            "workflow_id": "workflow-action-adk2-001",
            "workflow_name": "action-adk2-workflow",
            "run_config": {"mapped_fields": ["max_llm_calls"]},
            "service_bundle": {"source": "in_memory"},
            "artifact_summary": {"artifact_count": 1},
            "session_summary": {"session_id": "session-action-adk2-001"},
            "event_summary": {"event_count": 2},
        },
    )
    governance_case = GovernanceCase(
        case_id="case-action-adk2-001",
        title="ADK2 action candidate case",
        case_type="adk_workflow_runner_governance_review",
        context={
            "workflow_name": "action-adk2-workflow",
            "runtime_kind": "adk2_workflow_runner",
            "risk_level": "low",
        },
        evidence_refs=[evidence.evidence_id],
        policy_refs=["policy-adk2-workflow-runner-governance"],
        metadata={"findings": [], "required_followups": []},
    )
    result = make_unified_governance_decision_candidate(
        governance_case,
        evidence,
        policy_set_candidate=build_adk_workflow_runner_policy_set_candidate(),
        domain_metadata={
            "runtime_kind": "adk2_workflow_runner",
            "workflow_name": "action-adk2-workflow",
        },
    )
    return result.decision_candidate


def _review_and_outcome(decision: GovernanceDecision):
    review = create_human_review_record_candidate(
        decision,
        reviewer="governance-reviewer",
        review_result="accept_candidate",
        reviewed_at="2026-05-07T12:00:00+00:00",
    )
    outcome = create_governance_outcome_candidate(decision, review).outcome_candidate
    return review, outcome


def test_creates_unified_action_candidate_for_release_domain() -> None:
    decision = _release_decision_candidate()
    review, outcome = _review_and_outcome(decision)

    result = create_action_candidate(
        decision,
        review,
        outcome,
        action_domain="release_governance",
        action_kind="verify_release_readiness",
        executor="release-operator-candidate",
        created_at="2026-05-07T12:05:00+00:00",
    )

    assert isinstance(result, ActionCandidateResult)
    action = result.action_candidate
    assert isinstance(action, ActionCandidate)
    assert action.action_domain == "release_governance"
    assert action.action_domain in ALLOWED_ACTION_DOMAINS
    assert action.action_kind == "verify_release_readiness"
    assert action.action_semantics == "candidate_only"
    assert action.execution_enabled is False
    assert action.requires_operator_confirmation is True
    assert action.reviewer == "governance-reviewer"
    assert action.executor == "release-operator-candidate"
    assert "release_workflow_or_cli_confirmation" in action.required_confirmations
    assert action.metadata["does_not_execute_action"] is True
    assert action.metadata["does_not_modify_upstream_candidates"] is True


def test_creates_runtime_action_candidate_for_adk2_domain() -> None:
    decision = _runtime_decision_candidate()
    review, outcome = _review_and_outcome(decision)

    result = create_runtime_action_candidate(
        decision,
        review,
        outcome,
        action_kind="prepare_run_config_update",
        executor="runtime-operator-candidate",
        created_at="2026-05-07T12:10:00+00:00",
    )

    assert isinstance(result, RuntimeActionCandidateResult)
    runtime_action = result.runtime_action_candidate
    assert isinstance(runtime_action, RuntimeActionCandidate)
    action = result.action_candidate
    assert action.action_domain == "adk2_workflow_runner"
    assert action.action_kind == "prepare_run_config_update"
    assert action.action_kind in ALLOWED_RUNTIME_ACTION_KINDS
    assert action.action_semantics == "candidate_only"
    assert action.execution_enabled is False
    assert action.requires_operator_confirmation is True
    assert "runtime_operator_confirmation" in action.required_confirmations
    assert runtime_action.runtime_execution_enabled is False
    assert runtime_action.requires_runtime_operator_confirmation is True
    assert runtime_action.metadata["runtime_fix_executed"] is False
    assert runtime_action.metadata["run_config_updated"] is False
    assert runtime_action.metadata["service_bundle_updated"] is False


@pytest.mark.parametrize(
    "forbidden",
    ["runtime_fix", "run_config_update", "service_bundle_update"],
)
def test_runtime_true_action_kinds_are_rejected(forbidden: str) -> None:
    decision = _runtime_decision_candidate()
    review, outcome = _review_and_outcome(decision)

    with pytest.raises(ValidationError):
        create_runtime_action_candidate(
            decision,
            review,
            outcome,
            action_kind=forbidden,  # type: ignore[arg-type]
        )

    assert forbidden in FORBIDDEN_ACTION_KINDS


def test_missing_upstream_candidates_return_blocked_action_candidate() -> None:
    result = create_action_candidate(
        action_domain="adk2_workflow_runner",
        action_kind="request_runtime_evidence",
    )

    action = result.action_candidate
    assert action.decision_candidate_id is None
    assert action.human_review_id is None
    assert action.outcome_candidate_id is None
    assert action.execution_enabled is False
    assert "GovernanceDecision candidate is missing." in action.blocked_execution_reasons
    assert "HumanReviewRecord candidate is missing." in action.blocked_execution_reasons
    assert "GovernanceOutcome candidate is missing." in action.blocked_execution_reasons


def test_release_action_candidate_keeps_api_and_exposes_unified_candidate() -> None:
    decision = _release_decision_candidate()
    review, outcome = _review_and_outcome(decision)

    result = create_release_action_candidate(
        decision,
        review,
        outcome,
        action_kind="prepare_pypi_upload",
    )

    assert result.action_candidate.action_domain == "release_governance"
    assert result.action_candidate.action_semantics == "candidate_only"
    assert result.action_candidate.execution_enabled is False
    assert result.action_candidate.requires_operator_confirmation is True
    assert result.unified_action_candidate is not None
    assert result.unified_action_candidate.action_candidate_id == (
        result.action_candidate.action_candidate_id
    )
    assert result.unified_action_candidate.action_kind == "prepare_pypi_upload"


def test_action_candidate_source_keeps_execution_layers_out() -> None:
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:scripts|subprocess|requests|urllib|runtime_container|composition|adk_adapter|google\.adk)\b",
        re.MULTILINE,
    )
    forbidden_calls = re.compile(r"(?:subprocess\.|\.main\()")

    for source_path in GOVERNANCE_SOURCE_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_imports.search(source) is None, source_path
        assert forbidden_calls.search(source) is None, source_path
