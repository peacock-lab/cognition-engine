from __future__ import annotations

import pytest
from cognition_governance.models import GovernancePolicySet
from cognition_governance.observability_bridge import (
    build_governance_case_from_evidence_bundle,
    build_governance_decision_sample,
    build_governance_evidence_from_evidence_bundle,
)
from observability_hub.adk_intake import build_adk_evidence_bundle_from_workflow_result
from schemas.runtime import InvocationRef, RuntimeEvent, RuntimeEventType, RuntimeStatus, WorkflowRef, WorkflowResult


def _evidence_bundle():
    invocation_ref = InvocationRef(
        invocation_id="requested-governance-001",
        runtime_id="runtime-governance-001",
        workflow_id="workflow-governance-001",
        metadata={"session_id": "session-governance-001"},
    )
    workflow_ref = WorkflowRef(workflow_id="workflow-governance-001")
    event = RuntimeEvent(
        event_id="event-governance-001",
        event_type=RuntimeEventType.NODE_COMPLETED,
        invocation_ref=invocation_ref,
        workflow_ref=workflow_ref,
        payload={"model_fact": "candidate-evidence"},
        metadata={
            "adapter_name": "adk_adapter",
            "requested_invocation_id": "requested-governance-001",
            "adk_invocation_id": "actual-governance-001",
        },
    )
    workflow_result = WorkflowResult(
        workflow_ref=workflow_ref,
        status=RuntimeStatus.SUCCESS,
        invocation_ref=invocation_ref,
        events=[event],
        metadata={
            "adapter_name": "adk_adapter",
            "requested_invocation_id": "requested-governance-001",
            "adk_invocation_id": "actual-governance-001",
        },
    )
    return build_adk_evidence_bundle_from_workflow_result(
        workflow_result,
        runtime_id="runtime-governance-001",
    )


def test_governance_bridge_consumes_observability_hub_output_only() -> None:
    evidence_bundle = _evidence_bundle()
    evidence = build_governance_evidence_from_evidence_bundle(
        evidence_bundle,
        evidence_id="evidence-governance-001",
    )
    case = build_governance_case_from_evidence_bundle(
        evidence_bundle,
        case_id="case-governance-001",
        title="Review observability-owned ADK facts",
        evidence_refs=[evidence.evidence_id],
    )
    policy_set = GovernancePolicySet(
        policy_set_id="policy-governance-001",
        name="Observability-owned governance evidence policy",
        policies=["Governance consumes EvidenceBundle output, not ADK adapter internals."],
    )
    decision = build_governance_decision_sample(
        decision_id="decision-governance-001",
        case=case,
        evidence=[evidence],
        policy_set=policy_set,
    )

    assert evidence.source == "observability_hub.EvidenceBundle"
    assert evidence.metadata["producer_chain"] == [
        "adk_adapter",
        "observability_hub",
        "cognition_governance",
    ]
    assert case.metadata["requires_observability_hub_output"] is True
    assert case.context["workflow"]["workflow_id"] == "workflow-governance-001"
    assert decision.metadata["decision_semantics"] == "candidate_only"
    assert decision.metadata["formal_decision_enabled"] is False
    assert decision.metadata["policy_execution_enabled"] is False
    assert decision.metadata["governance_outcome_enabled"] is False
    assert decision.metadata["legacy_observability_bridge"] is True
    assert decision.metadata["model_output_used_as_decision"] is False


def test_governance_bridge_rejects_adk_adapter_summary_as_formal_input() -> None:
    adk_adapter_summary = {
        "adapter": "adk_adapter",
        "workflow_id": "workflow-platform-summary",
        "event_count": 1,
        "artifact_delta_count": 0,
    }

    with pytest.raises(ValueError, match="observability_hub EvidenceBundle-like output"):
        build_governance_evidence_from_evidence_bundle(
            adk_adapter_summary,
            evidence_id="evidence-invalid-platform-summary",
        )
