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
    GovernanceEvidence,
    GovernanceOutcome,
    GovernancePolicySet,
)


def test_invocation_session_and_workflow_context_can_be_modeled_in_governance_case() -> None:
    case = GovernanceCase(
        case_id="context-mapping-001",
        title="Review invocation context before governance decision",
        case_type="context_mapping_review",
        subject="Invocation and session context to GovernanceCase.context",
        context={
            "producer_chain": [
                "adk_adapter",
                "runtime_container",
                "observability_hub",
            ],
            "source_objects": [
                "InvocationBindingRecord",
                "InvocationRef.metadata",
                "session",
                "workflow metadata",
                "runtime context",
            ],
            "invocation": {
                "invocation_id": "invocation-001",
                "adapter": "adk_adapter",
                "target": "workflow-runner",
            },
            "session": {
                "session_id": "session-001",
                "scope": "governance-sample",
            },
            "workflow": {
                "workflow_id": "workflow-001",
                "phase": "v0.7.0",
            },
            "runtime": {
                "run_id": "run-001",
                "environment": "local",
            },
        },
        evidence_refs=["evidence-context-binding-summary"],
        policy_refs=["policy-context-mapping"],
        metadata={
            "tracking_source": "cognition_governance roadmap",
            "follow_up": "context mapping and public contract promotion",
        },
    )

    evidence = GovernanceEvidence(
        evidence_id="evidence-context-binding-summary",
        evidence_type="context_binding_summary",
        source="InvocationRef.metadata",
        summary=(
            "Invocation, session, workflow, and runtime context can be used as "
            "GovernanceCase.context; only evidence-relevant binding details are "
            "copied into GovernanceEvidence.metadata."
        ),
        content_ref="runtime_context:context-mapping-001",
        metadata={
            "invocation_id": "invocation-001",
            "session_id": "session-001",
            "workflow_id": "workflow-001",
            "run_id": "run-001",
            "is_original_context_object": False,
        },
    )

    policy_set = GovernancePolicySet(
        policy_set_id="policy-context-mapping",
        name="Context to governance case mapping policy",
        policies=[
            "Invocation and session objects must not be migrated into cognition_governance.",
            "Context summaries may be represented in GovernanceCase.context.",
            "Only evidence-relevant binding details should enter GovernanceEvidence.metadata.",
        ],
    )

    decision = GovernanceDecision(
        decision_id="decision-context-mapping-001",
        case_id=case.case_id,
        decision="continue",
        rationale=(
            "The context can be represented as a governance case context summary "
            "without importing runtime, session, invocation, or observability models."
        ),
        evidence_ids=[evidence.evidence_id],
        policy_set_id=policy_set.policy_set_id,
        metadata={
            "mapping_confirmed": True,
            "migrate_context_objects": False,
        },
    )

    outcome = GovernanceOutcome(
        outcome_id="outcome-context-mapping-001",
        decision_id=decision.decision_id,
        status="validated",
        summary=(
            "Context to GovernanceCase.context mapping was validated at sample level."
        ),
        metadata={"next_step": "keep mapping table updated"},
    )

    assert case.context["invocation"]["invocation_id"] == "invocation-001"
    assert case.context["session"]["session_id"] == "session-001"
    assert case.context["workflow"]["phase"] == "v0.7.0"
    assert evidence.metadata["is_original_context_object"] is False
    assert decision.decision == "continue"
    assert decision.metadata["migrate_context_objects"] is False
    assert outcome.status == "validated"


def test_context_mapping_sample_keeps_non_evidence_context_out_of_evidence_metadata() -> None:
    case = GovernanceCase(
        case_id="context-mapping-002",
        title="Keep governance context summary separate from evidence metadata",
        case_type="context_mapping_review",
        subject="Context summary boundary",
        context={
            "session": {
                "session_id": "session-002",
                "user_flow": "architecture review",
            },
            "workflow": {
                "workflow_id": "workflow-002",
                "step": "mapping design",
            },
            "non_evidence_context": {
                "conversation_phase": "design discussion",
                "internal_notes": "kept in GovernanceCase.context only",
            },
        },
    )

    evidence = GovernanceEvidence(
        evidence_id="evidence-context-mapping-002",
        evidence_type="context_binding_summary",
        source="workflow metadata",
        summary="Only workflow identity is needed as evidence metadata.",
        metadata={
            "workflow_id": "workflow-002",
        },
    )

    assert "non_evidence_context" in case.context
    assert "internal_notes" not in evidence.metadata
    assert evidence.metadata == {"workflow_id": "workflow-002"}


def test_context_mapping_sample_round_trips_case_context() -> None:
    case = GovernanceCase(
        case_id="context-mapping-003",
        title="Round-trip context mapping sample",
        case_type="context_mapping_review",
        context={
            "invocation_ref_metadata": {
                "invocation_id": "invocation-003",
                "adapter": "adk_adapter",
            },
            "runtime_context": {
                "run_id": "run-003",
                "status": "completed",
            },
        },
    )

    dumped = case.model_dump()
    restored = GovernanceCase.model_validate(dumped)

    assert restored == case
    assert restored.context["invocation_ref_metadata"]["adapter"] == "adk_adapter"
    assert restored.context["runtime_context"]["status"] == "completed"
