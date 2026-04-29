from __future__ import annotations

from cognition_engine.sessions import (
    ADK_SESSION_SERVICE_NAME,
    build_adk_session_binding,
    build_project_context_binding,
    context_id_from_session_id,
    shared_run_identity,
)


def test_context_id_from_session_id_preserves_project_projection_contract() -> None:
    assert context_id_from_session_id("session-sample") == "adk-session:session-sample"
    assert context_id_from_session_id(None) is None


def test_session_bindings_match_context_record_contract() -> None:
    assert build_adk_session_binding("session-sample") == {
        "session_service": ADK_SESSION_SERVICE_NAME,
        "session_id": "session-sample",
        "binding_status": "adk_session_mapped",
    }
    assert build_adk_session_binding(None) == {
        "session_service": None,
        "session_id": None,
        "binding_status": "missing_adk_session",
    }
    assert build_project_context_binding(
        execution_id="ce-adk-workflow-sample",
        context_id="adk-session:session-sample",
        invocation_id="ce-adk-invocation-sample",
    ) == {
        "execution_id": "ce-adk-workflow-sample",
        "context_id": "adk-session:session-sample",
        "invocation_id": "ce-adk-invocation-sample",
        "binding_status": "project_context_id_over_adk_session",
    }


def test_shared_run_identity_preserves_control_plane_identity_shape() -> None:
    assert shared_run_identity(
        {
            "execution_id": "ce-adk-workflow-sample",
            "session_id": "session-sample",
            "context_id": "adk-session:session-sample",
            "invocation_id": "ce-adk-invocation-sample",
        }
    ) == {
        "execution_id": "ce-adk-workflow-sample",
        "session_id": "session-sample",
        "context_id": "adk-session:session-sample",
        "invocation_id": "ce-adk-invocation-sample",
    }


def test_sessions_readme_is_module_boundary_not_task_log() -> None:
    readme = open("cognition_engine/sessions/README.md", encoding="utf-8").read()

    assert "Module Position" in readme
    assert "ADK Correspondence" in readme
    assert "control_plane Consumption" in readme
    assert "任务" not in readme
    assert "结果包" not in readme
