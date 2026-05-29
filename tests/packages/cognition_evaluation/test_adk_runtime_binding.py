from __future__ import annotations

from cognition_evaluation import evaluate_adk_runtime_binding_safe_projection


def _safe_projection() -> dict[str, object]:
    return {
        "probe_ref": "adk-runtime-binding-probe://unit-test",
        "agent_ref": "adk-agent://runtime_binding_probe_agent",
        "agent_type": "LlmAgent",
        "app_name": "test_runtime_binding_probe",
        "session_binding_ref": (
            "adk-session-binding://test_runtime_binding_probe/session-001"
        ),
        "invocation_ref": "invocation-001",
        "adk_invocation_ref_present": True,
        "event_count": 2,
        "event_summaries": [
            {
                "event_ref": "adk-event://event-001",
                "event_type": "workflow_started",
                "author": "runtime_binding_probe_agent",
                "payload_keys": ["artifact_delta", "content", "output"],
                "has_error": False,
            }
        ],
        "artifact_summary": {
            "artifact_ref": "adk-artifact-binding://session-001/probe-summary.txt",
            "filename": "probe-summary.txt",
            "version": 0,
            "body_included": False,
            "deleted_after_probe": True,
        },
        "service_summary": {
            "session_service_type": "InMemorySessionService",
            "artifact_service_type": "InMemoryArtifactService",
            "session_event_count": 2,
            "in_memory_services": True,
        },
        "raw_object_included": False,
        "user_product_path_enabled": False,
        "default_local_state_dir_enabled": False,
        "auto_resume_enabled": False,
        "skills_loaded": False,
        "memory_enabled": False,
    }


def test_adk_runtime_binding_safe_projection_passes() -> None:
    result = evaluate_adk_runtime_binding_safe_projection(projection=_safe_projection())

    assert result.status == "passed"
    assert result.profile_ref is not None
    assert result.profile_ref.ref.endswith("safe-projection-v1")


def test_adk_runtime_binding_safe_projection_blocks_raw_object_and_user_path() -> None:
    projection = _safe_projection()
    projection["raw_object_included"] = True
    projection["user_product_path_enabled"] = True

    result = evaluate_adk_runtime_binding_safe_projection(projection=projection)

    assert result.status == "failed"
    assert {finding.criterion for finding in result.findings} >= {
        "runtime_binding_raw_object_boundary",
        "runtime_binding_scope_boundary",
    }


def test_adk_runtime_binding_safe_projection_blocks_artifact_body() -> None:
    projection = _safe_projection()
    artifact_summary = dict(projection["artifact_summary"])  # type: ignore[arg-type]
    artifact_summary["body_included"] = True
    projection["artifact_summary"] = artifact_summary

    result = evaluate_adk_runtime_binding_safe_projection(projection=projection)

    assert result.status == "failed"
    assert result.findings[0].criterion == "runtime_binding_artifact_body_boundary"
