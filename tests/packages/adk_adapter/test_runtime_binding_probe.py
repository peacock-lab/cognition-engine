from __future__ import annotations

from adk_adapter import (
    AdkRuntimeBindingProbeOptions,
    run_agent_session_event_artifactservice_probe,
)


def test_runtime_binding_probe_returns_safe_projection_without_user_path() -> None:
    projection = run_agent_session_event_artifactservice_probe(
        AdkRuntimeBindingProbeOptions(
            probe_ref="adk-runtime-binding-probe://unit-test",
            app_name="test_runtime_binding_probe",
            user_id="test-user",
            session_id="session-runtime-binding-001",
            invocation_id="invocation-runtime-binding-001",
            artifact_filename="probe-summary.txt",
            artifact_text="safe probe artifact",
        )
    )
    evaluation_projection = projection.to_evaluation_projection()

    assert projection.agent_ref == "adk-agent://runtime_binding_probe_agent"
    assert projection.agent_type == "LlmAgent"
    assert projection.session_binding_ref.endswith("/session-runtime-binding-001")
    assert projection.invocation_ref == "invocation-runtime-binding-001"
    assert projection.adk_invocation_ref
    assert projection.event_count >= 2
    assert projection.raw_object_included is False
    assert projection.user_product_path_enabled is False
    assert projection.default_local_state_dir_enabled is False
    assert projection.auto_resume_enabled is False
    assert projection.skills_loaded is False
    assert projection.memory_enabled is False
    assert projection.artifact_summary["filename"] == "probe-summary.txt"
    assert projection.artifact_summary["version"] == 0
    assert projection.artifact_summary["body_included"] is False
    assert projection.artifact_summary["deleted_after_probe"] is True
    assert projection.service_summary["in_memory_services"] is True
    assert evaluation_projection["event_summaries"]
    assert "raw_event" not in evaluation_projection["event_summaries"][0]
    assert "content" not in evaluation_projection["event_summaries"][0]
    assert "output" not in evaluation_projection["event_summaries"][0]
