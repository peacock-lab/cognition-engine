from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError


PACKAGE_SRC = Path(__file__).resolve().parents[3] / "packages" / "cognition_agent" / "src"
sys.path.insert(0, str(PACKAGE_SRC))

from cognition_agent.governance_view import (  # noqa: E402
    GOVERNANCE_PRECONDITION_SUMMARY_SOURCE,
    GOVERNANCE_PRECONDITION_SUMMARY_VERSION,
    AgentGovernanceViewCandidate,
    build_agent_governance_view_from_precondition_summary,
    build_agent_governance_view_candidate,
)
from contract_core.governance_candidate import (  # noqa: E402
    ActionCandidateConfigViewCandidate,
    ActionCandidateSchema,
    GovernanceCaseSchemaCandidate,
    GovernanceDecisionCandidateSchema,
    GovernanceEvidenceSchemaCandidate,
    ReleaseGovernanceConfigViewCandidate,
)


def test_agent_governance_view_candidate_is_readonly_candidate_only() -> None:
    view = AgentGovernanceViewCandidate(
        candidate_id="agent-governance-view-1",
        source="unit-test",
        summary="Read-only governance view.",
        governance_refs=["ev-1", "case-1"],
    )

    assert view.candidate_type == "agent_governance_view_candidate"
    assert view.readonly is True
    assert view.candidate_only is True
    assert view.execution_enabled is False
    assert view.formal_decision_enabled is False
    assert view.action_execution_enabled is False


def test_build_agent_governance_view_candidate_collects_public_candidate_refs() -> None:
    evidence = GovernanceEvidenceSchemaCandidate(
        evidence_id="ev-1",
        evidence_type="release_check_output",
        source="release_governance.script_output",
        summary="Evidence summary.",
    )
    case = GovernanceCaseSchemaCandidate(
        case_id="case-1",
        title="Release governance case",
        case_type="release_governance",
        evidence_refs=[evidence.evidence_id],
    )
    decision = GovernanceDecisionCandidateSchema(
        decision_id="decision-1",
        case_id=case.case_id,
        decision="continue",
        rationale="Candidate can continue to later review.",
        evidence_ids=[evidence.evidence_id],
        policy_domain="release_governance",
    )
    action = ActionCandidateSchema(
        action_candidate_id="action-1",
        action_domain="release_governance",
        action_kind="prepare_release",
        decision_candidate_id=decision.decision_id,
        reviewer="reviewer-a",
        executor="executor-b",
    )
    action_config = ActionCandidateConfigViewCandidate(
        allowed_action_kinds=("prepare_release",),
    )
    release_config = ReleaseGovernanceConfigViewCandidate(
        release_target="cognition-engine",
        phase="candidate-review",
    )

    view = build_agent_governance_view_candidate(
        candidate_id="agent-governance-view-2",
        source="unit-test",
        summary="Read-only view over public candidate contracts.",
        evidence_candidates=[evidence],
        case_candidates=[case],
        decision_candidates=[decision],
        action_candidates=[action],
        action_config_view=action_config,
        release_config_view=release_config,
    )

    assert view.evidence_candidate_refs == ["ev-1"]
    assert view.case_candidate_refs == ["case-1"]
    assert view.decision_candidate_refs == ["decision-1"]
    assert view.action_candidate_refs == ["action-1"]
    assert set(view.governance_refs) == {"ev-1", "case-1", "decision-1", "action-1"}
    assert view.config_view_refs == [
        "action_candidate_config_view",
        "release_governance_config_view",
    ]
    assert view.metadata["does_not_call_llm"] is True
    assert view.metadata["does_not_call_runtime"] is True
    assert view.metadata["does_not_call_release"] is True


def test_build_agent_governance_view_from_precondition_summary_is_readonly() -> None:
    view = build_agent_governance_view_from_precondition_summary(
        candidate_id="agent-governance-view-precondition-1",
        precondition_summary={
            "allowed": False,
            "reason": "governance_decision_precondition_denied",
            "decision": "need_evidence",
            "metadata": {
                "policy_refs": ["policy:runtime"],
                "candidate_scope": "governance_config_decision_candidate",
                "composition_precondition_allowed": False,
            },
        },
    )

    assert view.source == GOVERNANCE_PRECONDITION_SUMMARY_SOURCE
    assert view.summary_version == GOVERNANCE_PRECONDITION_SUMMARY_VERSION
    assert view.governance_summary_source == GOVERNANCE_PRECONDITION_SUMMARY_SOURCE
    assert view.precondition_allowed is False
    assert view.precondition_reason == "governance_decision_precondition_denied"
    assert view.precondition_decision == "need_evidence"
    assert view.policy_refs == ["policy:runtime"]
    assert set(view.governance_refs) == {
        "policy:runtime",
        "governance_decision:need_evidence",
        "governance_candidate_scope:governance_config_decision_candidate",
    }
    assert view.metadata["does_not_import_cognition_governance"] is True
    assert view.metadata["does_not_consume_action_candidate"] is True
    assert view.metadata["does_not_consume_runtime_action_candidate"] is True
    assert view.execution_enabled is False
    assert view.action_execution_enabled is False


def test_agent_governance_view_rejects_execution_or_formal_flags() -> None:
    with pytest.raises(ValidationError):
        AgentGovernanceViewCandidate(
            candidate_id="agent-governance-view-3",
            source="unit-test",
            summary="Invalid execution view.",
            execution_enabled=True,
        )

    with pytest.raises(ValidationError):
        AgentGovernanceViewCandidate(
            candidate_id="agent-governance-view-4",
            source="unit-test",
            summary="Invalid formal view.",
            formal_decision_enabled=True,
        )
