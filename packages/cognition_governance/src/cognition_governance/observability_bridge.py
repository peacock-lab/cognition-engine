"""Legacy internal bridge from observability evidence bundles to governance samples.

This module is retained as a 078-era bridge sample. It only accepts
observability-owned EvidenceBundle-like input and can produce candidate-only
governance samples; it is not a formal governance control plane or action path.
"""

from __future__ import annotations

from typing import Any, Iterable

from cognition_governance.models import (
    GovernanceCase,
    GovernanceDecision,
    GovernanceDecisionKind,
    GovernanceEvidence,
    GovernancePolicySet,
)


def build_governance_evidence_from_evidence_bundle(
    evidence_bundle: Any,
    *,
    evidence_id: str,
) -> GovernanceEvidence:
    """Summarize an EvidenceBundle-like object as GovernanceEvidence."""

    bundle = _as_evidence_bundle_mapping(evidence_bundle)
    bundle_id = str(bundle.get("bundle_id") or evidence_id)
    run_record = _as_mapping(bundle.get("run_record", {}))
    event_trace = _as_mapping(bundle.get("event_trace", {}))
    artifact_manifest = _as_mapping(bundle.get("artifact_manifest", {}))
    invocation = _as_mapping(bundle.get("invocation", {}))
    runtime_id = bundle.get("runtime_id")
    workflow_id = bundle.get("workflow_id")

    return GovernanceEvidence(
        evidence_id=evidence_id,
        evidence_type="adk_observability_evidence_bundle",
        source="observability_hub.EvidenceBundle",
        summary=(
            f"ADK adapter run {runtime_id or 'unknown-runtime'} for workflow "
            f"{workflow_id or 'unknown-workflow'} produced "
            f"{event_trace.get('event_count', 0)} events, "
            f"{artifact_manifest.get('artifact_count', 0)} artifacts, and "
            f"{len(bundle.get('errors', []))} errors."
        ),
        content_ref=f"observability_hub:{bundle_id}",
        metadata={
            "bundle_id": bundle_id,
            "runtime_id": runtime_id,
            "workflow_id": workflow_id,
            "status": run_record.get("status"),
            "event_count": event_trace.get("event_count", 0),
            "artifact_count": artifact_manifest.get("artifact_count", 0),
            "error_count": run_record.get("error_count", len(bundle.get("errors", []))),
            "requested_invocation_id": invocation.get("requested_invocation_id"),
            "actual_invocation_id": invocation.get("actual_invocation_id"),
            "adk_invocation_id": invocation.get("adk_invocation_id"),
            "session_id": invocation.get("session_id"),
            "app_name": invocation.get("app_name"),
            "user_id": invocation.get("user_id"),
            "producer_chain": [
                "adk_adapter",
                "observability_hub",
                "cognition_governance",
            ],
            "is_public_contract": False,
        },
    )


def build_governance_case_from_evidence_bundle(
    evidence_bundle: Any,
    *,
    case_id: str,
    title: str,
    evidence_refs: Iterable[str],
) -> GovernanceCase:
    """Build a governance case context from an EvidenceBundle-like object."""

    bundle = _as_evidence_bundle_mapping(evidence_bundle)
    invocation = _as_mapping(bundle.get("invocation", {}))
    run_record = _as_mapping(bundle.get("run_record", {}))
    event_trace = _as_mapping(bundle.get("event_trace", {}))
    artifact_manifest = _as_mapping(bundle.get("artifact_manifest", {}))
    workflow_id = bundle.get("workflow_id") or run_record.get("workflow_id")

    return GovernanceCase(
        case_id=case_id,
        title=title,
        case_type="adk_observability_bridge_review",
        subject=str(workflow_id or "adk-observability-bridge"),
        context={
            "producer_chain": [
                "adk_adapter",
                "runtime_container",
                "observability_hub",
                "cognition_governance",
            ],
            "runtime": {
                "runtime_id": bundle.get("runtime_id"),
                "status": run_record.get("status"),
            },
            "workflow": {
                "workflow_id": workflow_id,
                "adapter_name": run_record.get("adapter_name"),
            },
            "invocation": {
                "requested_invocation_id": invocation.get("requested_invocation_id"),
                "actual_invocation_id": invocation.get("actual_invocation_id"),
                "adk_invocation_id": invocation.get("adk_invocation_id"),
                "session_id": invocation.get("session_id"),
                "app_name": invocation.get("app_name"),
                "user_id": invocation.get("user_id"),
            },
            "observability": {
                "bundle_id": bundle.get("bundle_id"),
                "event_count": event_trace.get("event_count", 0),
                "artifact_count": artifact_manifest.get("artifact_count", 0),
                "error_count": len(bundle.get("errors", [])),
            },
        },
        evidence_refs=list(evidence_refs),
        policy_refs=["policy-adk-observability-bridge-candidate"],
        metadata={
            "producer": "cognition_governance",
            "source": "observability_hub.EvidenceBundle",
            "requires_observability_hub_output": True,
            "is_public_contract": False,
        },
    )


def build_governance_decision_sample(
    *,
    decision_id: str,
    case: GovernanceCase,
    evidence: Iterable[GovernanceEvidence],
    policy_set: GovernancePolicySet,
    decision: GovernanceDecisionKind = "continue",
    rationale: str = "Evidence supports continuing the ADK platform chain skeleton.",
) -> GovernanceDecision:
    """Create a candidate-only governance decision sample from observability evidence."""

    return GovernanceDecision(
        decision_id=decision_id,
        case_id=case.case_id,
        decision=decision,
        rationale=rationale,
        evidence_ids=[item.evidence_id for item in evidence],
        policy_set_id=policy_set.policy_set_id,
        metadata={
            "decision_source": "cognition_governance",
            "decision_semantics": "candidate_only",
            "formal_decision_enabled": False,
            "policy_execution_enabled": False,
            "governance_outcome_enabled": False,
            "legacy_observability_bridge": True,
            "model_output_used_as_decision": False,
        },
    )


def _as_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="python")
    raise TypeError(f"Expected mapping-like evidence object, got {type(value).__name__}.")


def _as_evidence_bundle_mapping(value: Any) -> dict[str, Any]:
    bundle = _as_mapping(value)
    required_keys = {"source_type", "run_record", "event_trace", "artifact_manifest"}
    missing_keys = sorted(required_keys - set(bundle))
    if missing_keys:
        raise ValueError(
            "cognition_governance observability bridge only accepts "
            f"observability_hub EvidenceBundle-like output; missing {missing_keys}."
        )
    if bundle.get("source_type") != "runtime_result":
        raise ValueError(
            "cognition_governance observability bridge only accepts EvidenceBundle "
            "objects produced from runtime_result facts."
        )
    return bundle
