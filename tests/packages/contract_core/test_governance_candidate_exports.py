from behavior_contracts.governance_candidate import (
    CandidateOnlyGuard,
    ProductAgentOutputGovernanceDomainGuard,
)
from config_contexts.governance_candidate import AdkRunConfigViewCandidate
from schemas.governance_candidate import GovernanceEvidenceSchemaCandidate

from contract_core import governance_candidate


def test_governance_candidate_facade_reexports_candidate_contracts() -> None:
    assert governance_candidate.CandidateOnlyGuard is CandidateOnlyGuard
    assert (
        governance_candidate.ProductAgentOutputGovernanceDomainGuard
        is ProductAgentOutputGovernanceDomainGuard
    )
    assert (
        governance_candidate.GovernanceEvidenceSchemaCandidate
        is GovernanceEvidenceSchemaCandidate
    )
    assert governance_candidate.AdkRunConfigViewCandidate is AdkRunConfigViewCandidate


def test_governance_candidate_facade_exports_are_explicit() -> None:
    expected_exports = {
        "CandidateOnlyGuard",
        "GovernanceEvidenceSchemaCandidate",
        "AdkRunConfigViewCandidate",
        "ActionCandidateConfigViewCandidate",
        "ProductAgentOutputGovernanceDomainGuard",
    }

    assert expected_exports <= set(governance_candidate.__all__)
