"""RuntimeResult intake for observability-hub."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from schemas.runtime import ArtifactDelta, InvocationRef, RuntimeErrorRecord, RuntimeEvent, RuntimeResult

from observability_hub.errors import ObservabilityHubInputError
from observability_hub.models import (
    ArtifactManifest,
    EvidenceBundle,
    EventTrace,
    InvocationBindingRecord,
    RunRecord,
)


def _as_runtime_result(runtime_result: RuntimeResult | dict[str, Any]) -> RuntimeResult:
    if isinstance(runtime_result, RuntimeResult):
        return runtime_result
    if isinstance(runtime_result, dict):
        return RuntimeResult.model_validate(runtime_result)
    raise ObservabilityHubInputError(
        "build_evidence_bundle expects a RuntimeResult or RuntimeResult-compatible mapping."
    )


def _collect_metadata_sources(runtime_result: RuntimeResult) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = [runtime_result.metadata]

    workflow_result = runtime_result.workflow_result
    if workflow_result is not None:
        sources.append(workflow_result.metadata)

    for event in _select_event_source(runtime_result):
        sources.append(event.metadata)

    sources.append(runtime_result.invocation_ref.metadata)
    return sources


def _first_non_empty(mapping_sources: list[dict[str, Any]], *keys: str) -> Any:
    for source in mapping_sources:
        for key in keys:
            value = source.get(key)
            if value not in (None, "", [], {}):
                return value
    return None


def _select_event_source(runtime_result: RuntimeResult) -> list[RuntimeEvent]:
    if runtime_result.events:
        return runtime_result.events
    workflow_result = runtime_result.workflow_result
    if workflow_result is not None and workflow_result.events:
        return workflow_result.events
    return []


def _select_artifact_source(runtime_result: RuntimeResult) -> list[ArtifactDelta]:
    if runtime_result.artifact_deltas:
        return runtime_result.artifact_deltas
    workflow_result = runtime_result.workflow_result
    if workflow_result is not None and workflow_result.artifact_deltas:
        return workflow_result.artifact_deltas
    return []


def _serialize_event(event: RuntimeEvent) -> dict[str, Any]:
    event_dict = {
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "timestamp": event.timestamp,
        "invocation_id": event.invocation_ref.invocation_id,
        "runtime_id": event.invocation_ref.runtime_id,
        "workflow_id": event.workflow_ref.workflow_id if event.workflow_ref else None,
        "node_id": event.node_ref.node_id if event.node_ref else None,
        "node_name": event.node_ref.name if event.node_ref else None,
        "payload": event.payload,
        "artifact_delta_refs": list(event.artifact_delta_refs),
        "metadata": event.metadata,
    }
    return event_dict


def _build_event_trace(runtime_result: RuntimeResult, warnings: list[str]) -> EventTrace:
    events = _select_event_source(runtime_result)
    if not events:
        warnings.append("No runtime events were available; EventTrace was built empty.")

    serialized_events = [_serialize_event(event) for event in events]
    node_paths = sorted(
        {
            node_path
            for event in events
            for node_path in (
                event.metadata.get("node_path"),
                event.metadata.get("node_name"),
                event.node_ref.node_id if event.node_ref else None,
            )
            if node_path
        }
    )
    authors = sorted(
        {
            author
            for event in events
            for author in (
                event.metadata.get("author"),
                event.payload.get("author"),
            )
            if author
        }
    )
    has_error = any(
        event.metadata.get("error_code")
        or event.metadata.get("error_message")
        or event.payload.get("error_code")
        or event.payload.get("error_message")
        for event in events
    )

    return EventTrace(
        events=serialized_events,
        event_count=len(serialized_events),
        node_paths=node_paths,
        authors=authors,
        has_error=has_error,
        metadata={"source": "runtime_result.events" if runtime_result.events else "workflow_result.events"},
    )


def _serialize_artifact_delta(artifact_delta: ArtifactDelta) -> dict[str, Any]:
    return {
        "delta_id": artifact_delta.delta_id,
        "operation": artifact_delta.operation.value,
        "artifact_id": artifact_delta.artifact_ref.artifact_id,
        "name": artifact_delta.artifact_ref.name,
        "path": artifact_delta.artifact_ref.path,
        "version": artifact_delta.artifact_ref.version,
        "invocation_id": artifact_delta.invocation_ref.invocation_id,
        "metadata": artifact_delta.metadata,
    }


def _build_artifact_manifest(runtime_result: RuntimeResult, warnings: list[str]) -> ArtifactManifest:
    artifacts = _select_artifact_source(runtime_result)
    if not artifacts:
        warnings.append("No artifact deltas were available; ArtifactManifest was built empty.")

    serialized_artifacts = [_serialize_artifact_delta(artifact) for artifact in artifacts]
    return ArtifactManifest(
        artifacts=serialized_artifacts,
        artifact_count=len(serialized_artifacts),
        metadata={
            "source": (
                "runtime_result.artifact_deltas"
                if runtime_result.artifact_deltas
                else "workflow_result.artifact_deltas"
            )
        },
    )


def _build_invocation_binding(runtime_result: RuntimeResult) -> InvocationBindingRecord:
    metadata_sources = _collect_metadata_sources(runtime_result)
    invocation_ref: InvocationRef = runtime_result.invocation_ref
    workflow_id = (
        runtime_result.workflow_result.workflow_ref.workflow_id
        if runtime_result.workflow_result is not None
        else invocation_ref.workflow_id
    )

    return InvocationBindingRecord(
        requested_invocation_id=_first_non_empty(
            metadata_sources,
            "requested_invocation_id",
            "requestedInvocationId",
        ),
        actual_invocation_id=_first_non_empty(
            metadata_sources,
            "actual_invocation_id",
            "actualInvocationId",
        )
        or invocation_ref.invocation_id,
        adk_invocation_id=_first_non_empty(
            metadata_sources,
            "adk_invocation_id",
            "adkInvocationId",
        ),
        session_id=_first_non_empty(metadata_sources, "session_id", "sessionId"),
        app_name=_first_non_empty(metadata_sources, "app_name", "appName"),
        user_id=_first_non_empty(metadata_sources, "user_id", "userId"),
        workflow_id=workflow_id,
        metadata={
            "invocation_ref": invocation_ref.model_dump(mode="python"),
        },
    )


def _serialize_error(error: RuntimeErrorRecord) -> dict[str, Any]:
    return {
        "error_id": error.error_id,
        "error_type": error.error_type,
        "message": error.message,
        "recoverable": error.recoverable,
        "invocation_id": error.invocation_ref.invocation_id if error.invocation_ref else None,
        "workflow_id": error.workflow_ref.workflow_id if error.workflow_ref else None,
        "node_id": error.node_ref.node_id if error.node_ref else None,
        "metadata": error.metadata,
    }


def _build_run_record(
    runtime_result: RuntimeResult,
    event_trace: EventTrace,
    artifact_manifest: ArtifactManifest,
) -> RunRecord:
    metadata_sources = _collect_metadata_sources(runtime_result)
    workflow_id = (
        runtime_result.workflow_result.workflow_ref.workflow_id
        if runtime_result.workflow_result is not None
        else runtime_result.invocation_ref.workflow_id
    )

    return RunRecord(
        runtime_id=runtime_result.runtime_id,
        status=runtime_result.status.value,
        workflow_id=workflow_id,
        adapter_name=_first_non_empty(metadata_sources, "adapter_name", "adapter"),
        started_at=_first_non_empty(metadata_sources, "started_at", "startedAt"),
        finished_at=_first_non_empty(metadata_sources, "finished_at", "finishedAt"),
        event_count=event_trace.event_count,
        error_count=len(runtime_result.errors),
        artifact_count=artifact_manifest.artifact_count,
        metadata={
            "runtime_metadata": runtime_result.metadata,
            "workflow_metadata": (
                runtime_result.workflow_result.metadata if runtime_result.workflow_result is not None else {}
            ),
        },
    )


def build_evidence_bundle(runtime_result: RuntimeResult | dict[str, Any]) -> EvidenceBundle:
    """Build the first-batch EvidenceBundle from a standard RuntimeResult."""

    parsed_runtime_result = _as_runtime_result(runtime_result)
    warnings: list[str] = []
    event_trace = _build_event_trace(parsed_runtime_result, warnings)
    artifact_manifest = _build_artifact_manifest(parsed_runtime_result, warnings)
    invocation = _build_invocation_binding(parsed_runtime_result)
    run_record = _build_run_record(parsed_runtime_result, event_trace, artifact_manifest)
    serialized_errors = [_serialize_error(error) for error in parsed_runtime_result.errors]

    if invocation.requested_invocation_id is None:
        warnings.append("requested_invocation_id was not available in metadata sources.")
    if invocation.adk_invocation_id is None:
        warnings.append("adk_invocation_id was not available in metadata sources.")
    if run_record.started_at is None or run_record.finished_at is None:
        warnings.append("Runtime timing fields were incomplete; missing values were kept as null.")

    workflow_id = invocation.workflow_id
    if workflow_id is None:
        warnings.append("workflow_id was not available; EvidenceBundle.workflow_id was kept null.")

    return EvidenceBundle(
        bundle_id=f"bundle-{uuid4()}",
        source_type="runtime_result",
        runtime_id=parsed_runtime_result.runtime_id,
        workflow_id=workflow_id,
        invocation=invocation,
        run_record=run_record,
        event_trace=event_trace,
        artifact_manifest=artifact_manifest,
        errors=serialized_errors,
        warnings=warnings,
        metadata={
            "runtime_metadata": parsed_runtime_result.metadata,
            "workflow_metadata": (
                parsed_runtime_result.workflow_result.metadata
                if parsed_runtime_result.workflow_result is not None
                else {}
            ),
            "evidence_contract": {
                "input_type": "schemas.runtime.RuntimeResult",
                "missing_facts_kept_in": ["warnings", "metadata"],
            },
        },
        created_at=datetime.now(UTC).isoformat(),
    )
