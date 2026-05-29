from __future__ import annotations

import pytest

from adk_adapter import (
    AdkRuntimeBindingSafeProjection,
    build_continuable_evidence_session_runtime_binding_from_adk_projection,
    validate_adk_runtime_binding_product_bridge,
)


def test_runtime_binding_bridge_builds_product_contract_from_safe_projection() -> None:
    projection = _projection()

    binding = build_continuable_evidence_session_runtime_binding_from_adk_projection(
        projection,
        continuable_evidence_session_ref="continuable-evidence-session://session-001",
    )
    result = validate_adk_runtime_binding_product_bridge(
        projection,
        continuable_evidence_session_ref="continuable-evidence-session://session-001",
    )

    assert binding.runtime_binding_ref.startswith(
        "continuable-evidence-session-runtime-binding://"
    )
    assert binding.continuable_evidence_session_ref == (
        "continuable-evidence-session://session-001"
    )
    assert binding.runtime_binding_status == "probed"
    assert binding.agent_binding_ref
    assert binding.agent_binding_ref.startswith(
        "continuable-evidence-session-runtime-binding://"
    )
    assert binding.session_binding_ref
    assert binding.event_review_refs
    assert all(
        ref.startswith("continuable-evidence-session-runtime-binding://")
        for ref in binding.event_review_refs
    )
    assert binding.artifact_binding_summary_refs
    assert binding.runtime_binding_evaluation_summary_ref
    assert binding.raw_runtime_object_included is False
    assert binding.user_product_runtime_path_enabled is False
    assert binding.default_local_state_dir_enabled is False
    assert binding.auto_resume_answer_enabled is False
    assert binding.skills_loaded is False
    assert binding.memory_enabled is False
    assert result.passed is True
    assert result.schema_validation_passed is True
    assert result.guard_result.passed is True
    assert result.runtime_binding is not None
    assert "adk-agent://" not in result.runtime_binding_payload["agent_binding_ref"]
    assert result.runtime_binding_payload["metadata"]["source_event_count"] == 2


def test_runtime_binding_bridge_rejects_forbidden_runtime_flags() -> None:
    projection = _projection(raw_object_included=True, user_product_path_enabled=True)

    with pytest.raises(ValueError, match="must be false"):
        build_continuable_evidence_session_runtime_binding_from_adk_projection(
            projection,
            continuable_evidence_session_ref="continuable-evidence-session://session-001",
        )

    result = validate_adk_runtime_binding_product_bridge(
        projection,
        continuable_evidence_session_ref="continuable-evidence-session://session-001",
    )

    assert result.passed is False
    assert result.runtime_binding is None
    assert result.schema_validation_passed is False
    assert result.schema_validation_error
    assert "raw_runtime_object_included:must_be_false" in result.guard_result.violations
    assert (
        "user_product_runtime_path_enabled:must_be_false"
        in result.guard_result.violations
    )


def test_runtime_binding_bridge_requires_product_session_ref() -> None:
    result = validate_adk_runtime_binding_product_bridge(
        _projection(),
        continuable_evidence_session_ref="adk-session://not-product-ref",
    )

    assert result.passed is False
    assert result.runtime_binding is None
    assert result.schema_validation_passed is False
    assert result.guard_result.passed is False
    assert "continuable_evidence_session_ref:invalid_ref_prefix" in (
        result.guard_result.violations
    )


def _projection(
    *,
    raw_object_included: bool = False,
    user_product_path_enabled: bool = False,
) -> AdkRuntimeBindingSafeProjection:
    return AdkRuntimeBindingSafeProjection(
        probe_ref="adk-runtime-binding-probe://unit-test",
        agent_ref="adk-agent://runtime_binding_probe_agent",
        agent_type="LlmAgent",
        app_name="test_runtime_binding_bridge",
        session_binding_ref="adk-session-binding://app/session-001",
        invocation_ref="invocation-runtime-binding-001",
        adk_invocation_ref="adk-invocation-001",
        event_count=2,
        event_summaries=[
            {
                "event_ref": "adk-event://event-001",
                "event_type": "model_request",
                "author": "runtime_binding_probe_agent",
                "branch": None,
                "has_error": False,
                "payload_keys": ["input"],
            },
            {
                "event_ref": "adk-event://event-002",
                "event_type": "model_response",
                "author": "runtime_binding_probe_agent",
                "branch": None,
                "has_error": False,
                "payload_keys": ["output"],
            },
        ],
        artifact_summary={
            "artifact_ref": "adk-artifact-binding://session-001/probe-summary.txt",
            "filename": "probe-summary.txt",
            "version": 0,
            "versions_before_delete": [0],
            "keys_before_delete": ["probe-summary.txt"],
            "keys_after_delete": [],
            "loaded_text_length": 21,
            "body_included": False,
            "deleted_after_probe": True,
        },
        service_summary={
            "session_service_type": "InMemorySessionService",
            "artifact_service_type": "InMemoryArtifactService",
            "session_event_count": 2,
            "in_memory_services": True,
        },
        raw_object_included=raw_object_included,
        user_product_path_enabled=user_product_path_enabled,
        default_local_state_dir_enabled=False,
        auto_resume_enabled=False,
        skills_loaded=False,
        memory_enabled=False,
        metadata={"probe_type": "agent_session_event_artifactservice"},
    )
