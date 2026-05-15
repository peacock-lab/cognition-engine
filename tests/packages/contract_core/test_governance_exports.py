from __future__ import annotations

from config_contexts.governance import GovernanceConfigContext
from contract_core import governance


def test_governance_facade_reexports_config_context() -> None:
    assert governance.GovernanceConfigContext is GovernanceConfigContext


def test_governance_facade_exports_are_explicit() -> None:
    assert "GovernanceConfigContext" in governance.__all__


def test_governance_facade_does_not_export_governance_decision_or_actions() -> None:
    forbidden_exports = {
        "GovernanceDecision",
        "GovernanceOutcome",
        "GovernanceOutcomeCandidate",
        "ActionCandidate",
        "RuntimeActionCandidate",
    }

    assert forbidden_exports.isdisjoint(set(governance.__all__))
