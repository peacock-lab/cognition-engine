from __future__ import annotations

from cognition_evaluation import evaluate_adk_workflow_no_live_safe_projection


def test_evaluate_adk_workflow_no_live_safe_projection_passes() -> None:
    result = evaluate_adk_workflow_no_live_safe_projection(
        projection=_projection(),
    )

    assert result.status == "passed"
    assert result.passed is True
    assert result.findings == []
    assert result.profile_ref
    assert result.profile_ref.ref == (
        "evaluation-profile://adk-workflow-no-live/safe-projection-v1"
    )
    assert result.metadata["adk_evaluation_utility_module_available"] is True
    assert result.metadata["runtime_execution_enabled"] is False
    assert result.metadata["governance_decision_enabled"] is False


def test_evaluate_adk_workflow_no_live_safe_projection_blocks_raw_claims() -> None:
    projection = _projection()
    projection["raw_object_included"] = True
    projection["artifact_body_included"] = True
    projection["user_product_path_enabled"] = True

    result = evaluate_adk_workflow_no_live_safe_projection(projection=projection)

    assert result.status == "failed"
    assert {finding.metadata.get("flag") for finding in result.findings} >= {
        "raw_object_included",
        "artifact_body_included",
        "user_product_path_enabled",
    }


def test_evaluate_adk_workflow_no_live_safe_projection_warns_without_artifact_refs() -> None:
    projection = _projection()
    projection["artifact_binding_summary_refs"] = []

    result = evaluate_adk_workflow_no_live_safe_projection(projection=projection)

    assert result.status == "warning"
    assert any(
        finding.criterion == "workflow_no_live_artifact_refs"
        and finding.severity == "warning"
        for finding in result.findings
    )


def _projection() -> dict[str, object]:
    return {
        "probe_ref": "adk-workflow-no-live-probe://unit-test",
        "workflow_ref": "adk-workflow://workflow-no-live-unit-test",
        "workflow_name": "workflow_no_live_unit_test",
        "invocation_ref": "workflow-no-live-invocation-test",
        "adk_invocation_ref_present": True,
        "session_binding_ref": "adk-workflow-session-binding://app/session-001",
        "workflow_status": "success",
        "event_count": 2,
        "node_paths": ["workflow_no_live_fact_node"],
        "event_review_refs": [
            "continuable-evidence-session-workflow-binding://workflow/event-review/1"
        ],
        "artifact_binding_summary_refs": [
            "continuable-evidence-session-workflow-binding://workflow/artifact-summary/1"
        ],
        "evaluation_summary_ref": "evaluation://adk-workflow-no-live/unit-test",
        "service_summary": {
            "workflow_runner": "AdkWorkflowRunner",
            "session_service_type": "InMemorySessionService",
            "artifact_service_type": "InMemoryArtifactService",
            "in_memory_services": True,
        },
        "raw_object_included": False,
        "raw_event_payload_included": False,
        "artifact_body_included": False,
        "adk_eval_raw_data_included": False,
        "user_product_path_enabled": False,
        "default_local_state_dir_enabled": False,
        "auto_resume_enabled": False,
        "skills_loaded": False,
        "memory_enabled": False,
        "tools_mcp_enabled": False,
        "callbacks_enabled": False,
        "plugins_enabled": False,
        "metadata": {"probe_type": "workflow_runtime_no_live"},
    }
