from __future__ import annotations

import sys
from pathlib import Path

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
    GovernanceOutcome,
    build_governance_decision_from_config,
    create_action_candidate,
    create_runtime_action_candidate,
)


def test_config_decision_chain_reuses_decision_and_does_not_make_outcome() -> None:
    case = GovernanceCase(
        case_id="case-config-chain",
        title="Review config decision chain",
        case_type="runtime_governance",
    )

    decision = build_governance_decision_from_config(
        config_context={"governance_profile": "runtime"},
        case=case,
    )

    assert isinstance(decision, GovernanceDecision)
    assert not isinstance(decision, GovernanceOutcome)
    assert decision.metadata["governance_outcome_enabled"] is False


def test_action_candidate_remains_candidate_only_for_config_decision() -> None:
    decision = build_governance_decision_from_config(
        config_context={"governance_profile": "runtime"},
        case=GovernanceCase(
            case_id="case-config-action",
            title="Review config action boundary",
            case_type="runtime_governance",
        ),
    )

    action_result = create_action_candidate(
        decision_candidate=decision,
        action_domain="adk2_workflow_runner",
        action_kind="continue_runtime_governance_review",
    )

    assert action_result.action_candidate.execution_enabled is False
    assert action_result.action_candidate.action_semantics == "candidate_only"
    assert action_result.action_candidate.metadata["does_not_execute_action"] is True
    assert any(
        "Execution is disabled inside cognition_governance" in reason
        for reason in action_result.action_candidate.blocked_execution_reasons
    )


def test_runtime_action_candidate_remains_non_executing_for_config_decision() -> None:
    decision = build_governance_decision_from_config(
        config_context={"governance_profile": "runtime"},
        case=GovernanceCase(
            case_id="case-config-runtime-action",
            title="Review runtime action boundary",
            case_type="runtime_governance",
        ),
    )

    result = create_runtime_action_candidate(
        decision_candidate=decision,
        action_kind="continue_runtime_governance_review",
    )

    assert result.runtime_action_candidate.runtime_execution_enabled is False
    assert result.action_candidate.metadata["does_not_call_runtime_container"] is True
    assert result.action_candidate.metadata["does_not_call_composition"] is True
    assert result.action_candidate.metadata["does_not_call_adk_adapter"] is True
