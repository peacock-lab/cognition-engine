from __future__ import annotations

from observability_hub.adk_intake import (
    AdkObservabilityFactPackage,
    build_adk_evidence_bundle,
    build_adk_evidence_bundle_from_workflow_result,
    build_adk_fact_package,
)
from schemas.runtime import (
    ArtifactDelta,
    ArtifactRef,
    DeltaOperation,
    InvocationRef,
    RuntimeEvent,
    RuntimeEventType,
    RuntimeResult,
    RuntimeStatus,
    WorkflowRef,
    WorkflowResult,
)


def _adk_workflow_result() -> WorkflowResult:
    invocation_ref = InvocationRef(
        invocation_id="requested-adk-001",
        runtime_id="runtime-adk-001",
        workflow_id="workflow-adk-001",
        metadata={
            "adk_invocation_binding": {
                "requested_invocation_id": "requested-adk-001",
                "adk_invocation_id": "actual-adk-001",
                "session_id": "session-adk-001",
                "app_name": "app-adk",
                "user_id": "user-adk",
                "workflow_id": "workflow-adk-001",
            }
        },
    )
    workflow_ref = WorkflowRef(workflow_id="workflow-adk-001", name="adk-intake")
    runtime_event = RuntimeEvent(
        event_id="event-adk-001",
        event_type=RuntimeEventType.NODE_COMPLETED,
        invocation_ref=invocation_ref,
        workflow_ref=workflow_ref,
        payload={"output": {"ok": True}},
        metadata={
            "adapter_name": "adk_adapter",
            "requested_invocation_id": "requested-adk-001",
            "adk_invocation_id": "actual-adk-001",
            "session_id": "session-adk-001",
            "app_name": "app-adk",
            "user_id": "user-adk",
            "node_path": "workflow/node",
        },
    )
    artifact_delta = ArtifactDelta(
        delta_id="artifact-delta-adk-001",
        invocation_ref=invocation_ref,
        artifact_ref=ArtifactRef(
            artifact_id="adk-artifact.json",
            name="adk-artifact.json",
        ),
        operation=DeltaOperation.UPDATE,
        metadata={"source": "adk_adapter.artifacts"},
    )
    return WorkflowResult(
        workflow_ref=workflow_ref,
        status=RuntimeStatus.SUCCESS,
        invocation_ref=invocation_ref,
        events=[runtime_event],
        artifact_deltas=[artifact_delta],
        metadata={
            "adapter_name": "adk_adapter",
            "requested_invocation_id": "requested-adk-001",
            "adk_invocation_id": "actual-adk-001",
            "session_id": "session-adk-001",
        },
    )


def test_observability_hub_builds_adk_evidence_bundle_from_runtime_result() -> None:
    workflow_result = _adk_workflow_result()
    runtime_result = RuntimeResult(
        runtime_id="runtime-adk-001",
        status=RuntimeStatus.SUCCESS,
        invocation_ref=workflow_result.invocation_ref,
        workflow_result=workflow_result,
        events=workflow_result.events,
        artifact_deltas=workflow_result.artifact_deltas,
        metadata={"runtime_name": "adk-runtime"},
    )

    bundle = build_adk_evidence_bundle(runtime_result)
    package = build_adk_fact_package(runtime_result)

    assert bundle.metadata["runtime_metadata"]["observability_hub_intake"] == "adk_adapter"
    assert bundle.run_record.adapter_name == "adk_adapter"
    assert bundle.event_trace.event_count == 1
    assert bundle.artifact_manifest.artifact_count == 1
    assert bundle.invocation is not None
    assert bundle.invocation.adk_invocation_id == "actual-adk-001"
    assert isinstance(package, AdkObservabilityFactPackage)
    assert package.to_governance_input().bundle_id == package.evidence_bundle.bundle_id


def test_observability_hub_builds_adk_evidence_bundle_from_workflow_result() -> None:
    bundle = build_adk_evidence_bundle_from_workflow_result(
        _adk_workflow_result(),
        runtime_id="runtime-from-workflow-001",
        metadata={"adapter_name": "adk_adapter"},
    )

    assert bundle.runtime_id == "runtime-from-workflow-001"
    assert bundle.workflow_id == "workflow-adk-001"
    assert bundle.artifact_manifest.artifacts[0]["artifact_id"] == "adk-artifact.json"
    assert bundle.metadata["runtime_metadata"]["governance_input_owner"] == (
        "observability_hub"
    )
