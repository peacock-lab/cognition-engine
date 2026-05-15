"""Legacy ADK adapter fact intake for observability-hub.

This module is retained as a 078-era observability candidate path. It consumes
standard runtime facts and builds observability-owned EvidenceBundle objects; it
is not an ADK service adapter, public contract layer, or governance decision
source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from schemas.runtime import RuntimeResult, WorkflowResult

from observability_hub.intake import build_evidence_bundle
from observability_hub.models import EvidenceBundle


@dataclass(frozen=True)
class AdkObservabilityFactPackage:
    """Observability-owned fact package for ADK adapter outputs."""

    evidence_bundle: EvidenceBundle
    source: str = "adk_adapter"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_governance_input(self) -> EvidenceBundle:
        """Return the only supported governance input for this package."""

        return self.evidence_bundle


def build_adk_evidence_bundle(
    runtime_result: RuntimeResult,
    *,
    metadata: dict[str, Any] | None = None,
) -> EvidenceBundle:
    """Build an EvidenceBundle from ADK-adapter runtime facts."""

    runtime_metadata = {
        **runtime_result.metadata,
        "observability_hub_intake": "adk_adapter",
        "governance_input_owner": "observability_hub",
        **(metadata or {}),
    }
    normalized_runtime_result = RuntimeResult(
        runtime_id=runtime_result.runtime_id,
        status=runtime_result.status,
        invocation_ref=runtime_result.invocation_ref,
        workflow_result=runtime_result.workflow_result,
        events=runtime_result.events,
        state_deltas=runtime_result.state_deltas,
        artifact_deltas=runtime_result.artifact_deltas,
        errors=runtime_result.errors,
        metadata=runtime_metadata,
    )
    return build_evidence_bundle(normalized_runtime_result)


def build_adk_fact_package(
    runtime_result: RuntimeResult,
    *,
    metadata: dict[str, Any] | None = None,
) -> AdkObservabilityFactPackage:
    """Build an observability-owned fact package from an ADK RuntimeResult."""

    evidence_bundle = build_adk_evidence_bundle(runtime_result, metadata=metadata)
    return AdkObservabilityFactPackage(
        evidence_bundle=evidence_bundle,
        metadata={
            "source_runtime_id": runtime_result.runtime_id,
            "source_workflow_id": (
                runtime_result.workflow_result.workflow_ref.workflow_id
                if runtime_result.workflow_result is not None
                else runtime_result.invocation_ref.workflow_id
            ),
            "adk_event_count": len(runtime_result.events),
            "adk_artifact_delta_count": len(runtime_result.artifact_deltas),
            "adk_error_count": len(runtime_result.errors),
        },
    )


def build_adk_evidence_bundle_from_workflow_result(
    workflow_result: WorkflowResult,
    *,
    runtime_id: str,
    metadata: dict[str, Any] | None = None,
) -> EvidenceBundle:
    """Build an EvidenceBundle when only an ADK-backed WorkflowResult is available."""

    runtime_result = RuntimeResult(
        runtime_id=runtime_id,
        status=workflow_result.status,
        invocation_ref=workflow_result.invocation_ref,
        workflow_result=workflow_result,
        events=workflow_result.events,
        state_deltas=workflow_result.state_deltas,
        artifact_deltas=workflow_result.artifact_deltas,
        errors=workflow_result.errors,
        metadata=metadata or {},
    )
    return build_adk_evidence_bundle(runtime_result)
