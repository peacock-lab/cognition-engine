from __future__ import annotations

from observability_hub import (
    ArtifactManifest,
    EvidenceBundle,
    EventTrace,
    InvocationBindingRecord,
    RunRecord,
    build_evidence_bundle,
)
from schemas.runtime import (
    ArtifactDelta,
    ArtifactRef,
    DeltaOperation,
    InvocationRef,
    RuntimeErrorRecord,
    RuntimeEvent,
    RuntimeEventType,
    RuntimeResult,
    RuntimeStatus,
    WorkflowRef,
    WorkflowResult,
)


def test_build_evidence_bundle_from_minimal_runtime_result() -> None:
    invocation_ref = InvocationRef(
        invocation_id="inv-actual-001",
        runtime_id="runtime-001",
        workflow_id="workflow-001",
        metadata={"session_id": "session-001"},
    )
    workflow_ref = WorkflowRef(workflow_id="workflow-001", name="demo-workflow")
    runtime_event = RuntimeEvent(
        event_id="event-001",
        event_type=RuntimeEventType.NODE_COMPLETED,
        invocation_ref=invocation_ref,
        workflow_ref=workflow_ref,
        timestamp="2026-05-02T10:00:00Z",
        payload={"author": "runner"},
        metadata={
            "node_path": "workflow/demo/node-1",
            "requested_invocation_id": "inv-requested-001",
            "adk_invocation_id": "adk-001",
            "app_name": "demo-app",
            "user_id": "user-001",
            "adapter_name": "demo-adapter",
            "started_at": "2026-05-02T09:59:00Z",
            "finished_at": "2026-05-02T10:00:00Z",
        },
    )
    artifact_delta = ArtifactDelta(
        delta_id="artifact-delta-001",
        invocation_ref=invocation_ref,
        artifact_ref=ArtifactRef(
            artifact_id="artifact-001",
            name="report.json",
            path="outputs/report.json",
        ),
        operation=DeltaOperation.SET,
        metadata={"kind": "report"},
    )
    workflow_result = WorkflowResult(
        workflow_ref=workflow_ref,
        status=RuntimeStatus.SUCCESS,
        invocation_ref=invocation_ref,
        events=[runtime_event],
        artifact_deltas=[artifact_delta],
        metadata={"requested_invocation_id": "inv-requested-001"},
    )
    runtime_result = RuntimeResult(
        runtime_id="runtime-001",
        status=RuntimeStatus.SUCCESS,
        invocation_ref=invocation_ref,
        workflow_result=workflow_result,
        events=[runtime_event],
        artifact_deltas=[artifact_delta],
        metadata={"actual_invocation_id": "inv-actual-001"},
    )

    bundle = build_evidence_bundle(runtime_result)

    assert isinstance(bundle, EvidenceBundle)
    assert bundle.source_type == "runtime_result"
    assert bundle.runtime_id == "runtime-001"
    assert bundle.workflow_id == "workflow-001"
    assert isinstance(bundle.run_record, RunRecord)
    assert bundle.run_record.event_count == 1
    assert bundle.run_record.artifact_count == 1
    assert isinstance(bundle.event_trace, EventTrace)
    assert bundle.event_trace.event_count == 1
    assert bundle.event_trace.node_paths == ["workflow/demo/node-1"]
    assert bundle.event_trace.authors == ["runner"]
    assert isinstance(bundle.artifact_manifest, ArtifactManifest)
    assert bundle.artifact_manifest.artifact_count == 1
    assert isinstance(bundle.invocation, InvocationBindingRecord)
    assert bundle.invocation.requested_invocation_id == "inv-requested-001"
    assert bundle.invocation.actual_invocation_id == "inv-actual-001"
    assert bundle.invocation.adk_invocation_id == "adk-001"
    assert bundle.invocation.app_name == "demo-app"
    assert bundle.invocation.user_id == "user-001"
    assert bundle.invocation.session_id == "session-001"
    assert bundle.warnings == []


def test_build_evidence_bundle_tolerates_missing_events_artifacts_and_binding_fields() -> None:
    runtime_result = RuntimeResult(
        runtime_id="runtime-empty-001",
        status=RuntimeStatus.SUCCESS,
        invocation_ref=InvocationRef(invocation_id="inv-empty-001"),
        metadata={},
    )

    bundle = build_evidence_bundle(runtime_result)

    assert bundle.runtime_id == "runtime-empty-001"
    assert bundle.event_trace.event_count == 0
    assert bundle.event_trace.events == []
    assert bundle.artifact_manifest.artifact_count == 0
    assert bundle.artifact_manifest.artifacts == []
    assert bundle.invocation is not None
    assert bundle.invocation.actual_invocation_id == "inv-empty-001"
    assert bundle.invocation.requested_invocation_id is None
    assert bundle.invocation.adk_invocation_id is None
    assert bundle.run_record.workflow_id is None
    assert any("EventTrace was built empty" in warning for warning in bundle.warnings)
    assert any("ArtifactManifest was built empty" in warning for warning in bundle.warnings)
    assert any("requested_invocation_id" in warning for warning in bundle.warnings)
    assert any("adk_invocation_id" in warning for warning in bundle.warnings)


def test_build_evidence_bundle_preserves_runtime_errors() -> None:
    invocation_ref = InvocationRef(invocation_id="inv-error-001", workflow_id="workflow-error-001")
    runtime_result = RuntimeResult(
        runtime_id="runtime-error-001",
        status=RuntimeStatus.FAILED,
        invocation_ref=invocation_ref,
        errors=[
            RuntimeErrorRecord(
                error_id="error-001",
                error_type="runtime_failure",
                message="boom",
                recoverable=False,
                invocation_ref=invocation_ref,
                metadata={"severity": "high"},
            )
        ],
    )

    bundle = build_evidence_bundle(runtime_result)

    assert len(bundle.errors) == 1
    assert bundle.errors[0]["error_id"] == "error-001"
    assert bundle.errors[0]["message"] == "boom"
    assert bundle.run_record.error_count == 1
