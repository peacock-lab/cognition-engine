"""Build governance control-plane records from workflow results."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, Optional

from cognition_engine.events import build_event_trace_governance
from cognition_engine.invocation import build_invocation_binding_summary
from cognition_engine.runtime import runtime_path_for_event_trace
from cognition_engine.sessions import (
    build_adk_session_binding,
    build_project_context_binding,
)
from cognition_engine.control_plane.records import (
    ARTIFACT_MANIFEST_TYPE,
    ARTIFACT_MANIFEST_VERSION,
    BUNDLE_TYPE,
    BUNDLE_VERSION,
    CONTEXT_RECORD_TYPE,
    CONTEXT_RECORD_VERSION,
    EVENT_TRACE_TYPE,
    EVENT_TRACE_VERSION,
    RUN_RECORD_TYPE,
    RUN_RECORD_VERSION,
    now_utc_iso,
    shared_run_identity,
)


def build_control_plane_bundle(workflow_result: Dict[str, Any]) -> Dict[str, Any]:
    """Build the minimal control-plane four-record bundle for a workflow result."""

    created_at = now_utc_iso()
    execution_id = workflow_result.get("execution_id")
    context_record = build_context_record(workflow_result, created_at=created_at)
    run_record = build_run_record(workflow_result, created_at=created_at)
    event_trace = build_event_trace(workflow_result, created_at=created_at)
    artifact_manifest = build_artifact_manifest(workflow_result, created_at=created_at)

    return {
        "bundle_type": BUNDLE_TYPE,
        "bundle_version": BUNDLE_VERSION,
        "execution_id": execution_id,
        "context_record": context_record,
        "run_record": run_record,
        "event_trace": event_trace,
        "artifact_manifest": artifact_manifest,
        "created_at": created_at,
    }


def build_context_record(
    workflow_result: Dict[str, Any],
    *,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    identity = shared_run_identity(workflow_result)
    session_id = identity["session_id"]
    context_id = identity["context_id"]
    invocation_binding = _invocation_binding(workflow_result)
    event_governance = _event_governance(workflow_result)

    return {
        "record_type": CONTEXT_RECORD_TYPE,
        "record_version": CONTEXT_RECORD_VERSION,
        "insight_id": workflow_result.get("insight_id"),
        "workflow_name": workflow_result.get("workflow_name"),
        **identity,
        "adk_session_binding": build_adk_session_binding(session_id),
        "project_context_binding": build_project_context_binding(
            execution_id=identity["execution_id"],
            context_id=context_id,
            invocation_id=identity["invocation_id"],
        ),
        "adk_invocation_binding": invocation_binding,
        "adk_event_trace_binding": {
            "adk_event_records_bound": bool(event_governance["adk_event_records"]),
            "adk_event_fields_bound": event_governance["adk_event_fields_bound"],
            "adk_event_coverage_available": event_governance[
                "adk_event_coverage_available"
            ],
            "adk_event_total_count": event_governance["adk_event_total_count"],
            "adk_event_error_count": event_governance["adk_event_error_count"],
            "adk_event_interrupted_count": event_governance[
                "adk_event_interrupted_count"
            ],
        },
        "input_summary": {
            "input_type": "insight_id",
            "insight_id": workflow_result.get("insight_id"),
            "command": workflow_result.get("command"),
        },
        "run_goal": f"execute {workflow_result.get('workflow_name') or 'workflow'}",
        "constraints": [
            "ADK is the only runtime foundation",
            "cognition engine builds governance control plane only",
            "control plane consumes workflow result without replacing business steps",
        ],
        "created_at": created_at or now_utc_iso(),
    }


def build_run_record(
    workflow_result: Dict[str, Any],
    *,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    identity = shared_run_identity(workflow_result)
    execution_id = identity["execution_id"]
    invocation_binding = _invocation_binding(workflow_result)
    event_governance = _event_governance(workflow_result)

    return {
        "record_type": RUN_RECORD_TYPE,
        "record_version": RUN_RECORD_VERSION,
        **identity,
        "workflow_name": workflow_result.get("workflow_name"),
        "insight_id": workflow_result.get("insight_id"),
        "status": workflow_result.get("status"),
        "adk_runtime": workflow_result.get("adk_runtime"),
        "adk_backed": bool(workflow_result.get("adk_backed")),
        "legacy_fallback_used": bool(workflow_result.get("legacy_fallback_used")),
        "project_invocation_id": invocation_binding["project_invocation_id"],
        "adk_invocation_id": invocation_binding["adk_invocation_id"],
        "adk_invocation_ids": invocation_binding["adk_invocation_ids"],
        "adk_invocation_bound": invocation_binding["adk_invocation_bound"],
        "adk_invocation_event_count": invocation_binding[
            "adk_invocation_event_count"
        ],
        "adk_invocation_mismatch": invocation_binding["adk_invocation_mismatch"],
        "adk_event_total_count": event_governance["adk_event_total_count"],
        "adk_event_error_count": event_governance["adk_event_error_count"],
        "adk_event_interrupted_count": event_governance[
            "adk_event_interrupted_count"
        ],
        "adk_event_partial_count": event_governance["adk_event_partial_count"],
        "adk_event_turn_complete_count": event_governance[
            "adk_event_turn_complete_count"
        ],
        "adk_event_field_coverage": event_governance["adk_event_field_coverage"],
        "validation": deepcopy(workflow_result.get("validation", {})),
        "step_results": deepcopy(workflow_result.get("step_results", [])),
        "context_record_ref": f"context_record:{execution_id}",
        "event_trace_ref": f"event_trace:{execution_id}",
        "artifact_manifest_ref": f"artifact_manifest:{execution_id}",
        "created_at": created_at or now_utc_iso(),
    }


def build_event_trace(
    workflow_result: Dict[str, Any],
    *,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    identity = shared_run_identity(workflow_result)
    event_summary = workflow_result.get("event_summary") or {}
    adk_events = deepcopy(event_summary.get("adk_events", []))
    business_events = deepcopy(event_summary.get("step_events", []))
    invocation_binding = _invocation_binding(workflow_result)
    event_governance = _event_governance(workflow_result)

    return {
        "record_type": EVENT_TRACE_TYPE,
        "record_version": EVENT_TRACE_VERSION,
        **identity,
        "source": event_summary.get("source"),
        "adk_runtime_path": runtime_path_for_event_trace(
            event_summary=event_summary,
            workflow_result=workflow_result,
        ),
        "adk_event_count": _count_or_len(event_summary.get("adk_event_count"), adk_events),
        "business_event_count": _count_or_len(
            event_summary.get("business_event_count"),
            business_events,
        ),
        "project_invocation_id": invocation_binding["project_invocation_id"],
        "adk_invocation_ids": invocation_binding["adk_invocation_ids"],
        "adk_invocation_event_count": invocation_binding[
            "adk_invocation_event_count"
        ],
        "adk_invocation_bound": invocation_binding["adk_invocation_bound"],
        "adk_invocation_mismatch": invocation_binding["adk_invocation_mismatch"],
        "adk_invocation_missing_count": invocation_binding[
            "adk_invocation_missing_count"
        ],
        "adk_event_records": event_governance["adk_event_records"],
        "adk_event_field_coverage": event_governance["adk_event_field_coverage"],
        "adk_event_fields_bound": event_governance["adk_event_fields_bound"],
        "adk_event_coverage_available": event_governance[
            "adk_event_coverage_available"
        ],
        "adk_event_total_count": event_governance["adk_event_total_count"],
        "adk_event_error_count": event_governance["adk_event_error_count"],
        "adk_event_interrupted_count": event_governance[
            "adk_event_interrupted_count"
        ],
        "adk_event_partial_count": event_governance["adk_event_partial_count"],
        "adk_event_turn_complete_count": event_governance[
            "adk_event_turn_complete_count"
        ],
        "adk_event_finish_reasons": event_governance["adk_event_finish_reasons"],
        "adk_event_author_summary": event_governance["adk_event_author_summary"],
        "adk_event_node_summary": event_governance["adk_event_node_summary"],
        "adk_event_branch_summary": event_governance["adk_event_branch_summary"],
        "adk_events_layer": adk_events,
        "business_step_events_layer": business_events,
        "created_at": created_at or now_utc_iso(),
    }


def build_artifact_manifest(
    workflow_result: Dict[str, Any],
    *,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    identity = shared_run_identity(workflow_result)
    artifacts = deepcopy(workflow_result.get("artifact_refs", []))

    return {
        "record_type": ARTIFACT_MANIFEST_TYPE,
        "record_version": ARTIFACT_MANIFEST_VERSION,
        **identity,
        "mapping_status": _mapping_status(artifacts),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "output_files": _compact(ref.get("path") for ref in artifacts),
        "metadata_files": _compact(ref.get("metadata_file") for ref in artifacts),
        "adk_artifact_bindings": _adk_artifact_bindings(artifacts),
        "adk_artifact_bound_count": sum(
            1 for ref in artifacts if ref.get("adk_artifact_bound") is True
        ),
        "adk_artifact_binding_error_count": sum(
            1 for ref in artifacts if ref.get("adk_artifact_error")
        ),
        "created_at": created_at or now_utc_iso(),
    }


def _count_or_len(value: Any, items: list[Any]) -> int:
    if isinstance(value, int):
        return value
    return len(items)


def _mapping_status(artifacts: list[Dict[str, Any]]) -> str:
    statuses = sorted(
        {
            status
            for status in (artifact.get("mapping_status") for artifact in artifacts)
            if status
        }
    )
    if not statuses:
        return "unmapped"
    if len(statuses) == 1:
        return statuses[0]
    return "mixed_artifact_mapping"


def _compact(values: Iterable[Any]) -> list[Any]:
    return [value for value in values if value]


def _invocation_binding(workflow_result: Dict[str, Any]) -> Dict[str, Any]:
    event_summary = workflow_result.get("event_summary") or {}
    return build_invocation_binding_summary(
        project_invocation_id=workflow_result.get("invocation_id"),
        adk_events=event_summary.get("adk_events", []),
    )


def _event_governance(workflow_result: Dict[str, Any]) -> Dict[str, Any]:
    event_summary = workflow_result.get("event_summary") or {}
    return build_event_trace_governance(event_summary.get("adk_events", []))


def _adk_artifact_bindings(artifacts: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    return [
        {
            "artifact_id": artifact.get("artifact_id"),
            "step_name": artifact.get("step_name"),
            "adk_artifact_service": artifact.get("adk_artifact_service"),
            "adk_artifact_key": artifact.get("adk_artifact_key"),
            "adk_artifact_version": artifact.get("adk_artifact_version"),
            "adk_artifact_uri": artifact.get("adk_artifact_uri"),
            "adk_artifact_bound": artifact.get("adk_artifact_bound"),
            "adk_artifact_error": artifact.get("adk_artifact_error"),
            "adk_artifact_metadata": artifact.get("adk_artifact_metadata"),
        }
        for artifact in artifacts
        if any(key.startswith("adk_artifact_") for key in artifact)
    ]
