from __future__ import annotations

import sys
from pathlib import Path

PACKAGE_SRC = (
    Path(__file__).resolve().parents[3] / "packages" / "cognition_agent" / "src"
)
sys.path.insert(0, str(PACKAGE_SRC))

from cognition_agent.governance_view import (
    AgentGovernanceViewCandidate,
    build_agent_governance_view_from_precondition_summary,
)


def test_agent_governance_boundary_remains_readonly_candidate_view() -> None:
    view = AgentGovernanceViewCandidate(
        candidate_id="agent-governance-view-001",
        source="composition.governance_precondition",
        summary="Read-only governance summary for agent shell.",
        governance_refs=["decision:config"],
        metadata={"preferred_source": "composition metadata.governance_precondition"},
    )

    assert view.readonly is True
    assert view.candidate_only is True
    assert view.execution_enabled is False
    assert view.action_execution_enabled is False
    assert view.runtime_action_enabled is False


def test_agent_consumes_composition_precondition_summary_as_readonly_view() -> None:
    view = build_agent_governance_view_from_precondition_summary(
        candidate_id="agent-governance-view-002",
        precondition_summary={
            "allowed": True,
            "reason": "governance_decision_allowed",
            "decision": "continue",
            "metadata": {
                "policy_refs": ["policy:runtime"],
                "composition_precondition_allowed": True,
            },
        },
    )

    assert view.precondition_allowed is True
    assert view.precondition_decision == "continue"
    assert view.policy_refs == ["policy:runtime"]
    assert view.metadata["does_not_call_runtime"] is True
    assert view.metadata["does_not_call_llm"] is True
    assert view.action_candidate_refs == []
