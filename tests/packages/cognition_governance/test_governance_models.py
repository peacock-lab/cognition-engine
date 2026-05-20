from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

PACKAGE_SRC = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "cognition_governance"
    / "src"
)
sys.path.insert(0, str(PACKAGE_SRC))

from cognition_governance import (  # noqa: E402
    GovernanceCase,
    GovernanceDecision,
    GovernanceEvidence,
    GovernanceOutcome,
    GovernancePolicySet,
)


def test_governance_models_can_be_instantiated_and_serialized() -> None:
    case = GovernanceCase(
        case_id="case-001",
        title="Review release candidate",
        case_type="release_review",
        subject="v0.6.0",
        evidence_refs=["evidence-001"],
        policy_refs=["policy-set-001"],
    )
    evidence = GovernanceEvidence(
        evidence_id="evidence-001",
        evidence_type="terminal_output",
        source="git status",
        summary="Working tree is clean.",
    )
    policy_set = GovernancePolicySet(
        policy_set_id="policy-set-001",
        name="Release gate policy",
        policies=["release note must match tag"],
    )
    decision = GovernanceDecision(
        decision_id="decision-001",
        case_id=case.case_id,
        decision="release",
        rationale="Release evidence satisfies the selected policy set.",
        evidence_ids=[evidence.evidence_id],
        policy_set_id=policy_set.policy_set_id,
    )
    outcome = GovernanceOutcome(
        outcome_id="outcome-001",
        decision_id=decision.decision_id,
        status="validated",
        summary="Release was completed and verified.",
    )

    assert case.model_dump()["case_id"] == "case-001"
    assert evidence.model_dump()["evidence_id"] == "evidence-001"
    assert policy_set.model_dump()["policy_set_id"] == "policy-set-001"
    assert decision.model_dump()["decision"] == "release"
    assert outcome.model_dump()["status"] == "validated"


def test_governance_models_reject_empty_required_fields() -> None:
    with pytest.raises(ValidationError):
        GovernanceCase(case_id="", title="x", case_type="task_review")


def test_governance_decision_rejects_unknown_decision_kind() -> None:
    with pytest.raises(ValidationError):
        GovernanceDecision(
            decision_id="decision-001",
            case_id="case-001",
            decision="unknown",
            rationale="invalid decision",
        )
