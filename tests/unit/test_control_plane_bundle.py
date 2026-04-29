from __future__ import annotations

from copy import deepcopy

from cognition_engine.control_plane import build_control_plane_bundle


def test_build_control_plane_bundle_contains_four_records() -> None:
    workflow_result = sample_workflow_result()

    bundle = build_control_plane_bundle(workflow_result)

    assert bundle["bundle_type"] == "control_plane_bundle"
    assert bundle["bundle_version"] == "ce-control-plane-bundle/v1"
    assert bundle["execution_id"] == "ce-adk-workflow-sample"
    assert bundle["context_record"]["record_type"] == "context_record"
    assert bundle["run_record"]["record_type"] == "run_record"
    assert bundle["event_trace"]["record_type"] == "event_trace"
    assert bundle["artifact_manifest"]["record_type"] == "artifact_manifest"


def test_control_plane_records_share_execution_id() -> None:
    bundle = build_control_plane_bundle(sample_workflow_result())

    assert {
        bundle["context_record"]["execution_id"],
        bundle["run_record"]["execution_id"],
        bundle["event_trace"]["execution_id"],
        bundle["artifact_manifest"]["execution_id"],
    } == {"ce-adk-workflow-sample"}


def test_context_record_contains_session_context_and_invocation_bindings() -> None:
    context_record = build_control_plane_bundle(sample_workflow_result())["context_record"]

    assert context_record["session_id"] == "adk-session-sample"
    assert context_record["context_id"] == "adk-session:adk-session-sample"
    assert context_record["invocation_id"] == "ce-adk-invocation-sample"
    assert context_record["adk_session_binding"] == {
        "session_service": "InMemorySessionService",
        "session_id": "adk-session-sample",
        "binding_status": "adk_session_mapped",
    }
    assert context_record["project_context_binding"]["binding_status"] == (
        "project_context_id_over_adk_session"
    )
    assert context_record["adk_invocation_binding"] == {
        "project_invocation_id": "ce-adk-invocation-sample",
        "adk_invocation_id": "ce-adk-invocation-sample",
        "adk_invocation_ids": ["ce-adk-invocation-sample"],
        "adk_invocation_event_count": 2,
        "adk_invocation_missing_count": 0,
        "adk_invocation_bound": True,
        "adk_invocation_mismatch": False,
    }
    assert context_record["adk_event_trace_binding"] == {
        "adk_event_records_bound": True,
        "adk_event_fields_bound": True,
        "adk_event_coverage_available": True,
        "adk_event_total_count": 2,
        "adk_event_error_count": 0,
        "adk_event_interrupted_count": 0,
    }
    assert context_record["input_summary"]["insight_id"] == "insight-adk-runner-centrality"


def test_run_record_preserves_status_adk_runtime_validation_and_steps() -> None:
    run_record = build_control_plane_bundle(sample_workflow_result())["run_record"]

    assert run_record["status"] == "success"
    assert run_record["adk_runtime"] == "Runner -> Workflow -> BaseNode business steps"
    assert run_record["adk_backed"] is True
    assert run_record["legacy_fallback_used"] is False
    assert run_record["project_invocation_id"] == "ce-adk-invocation-sample"
    assert run_record["adk_invocation_id"] == "ce-adk-invocation-sample"
    assert run_record["adk_invocation_bound"] is True
    assert run_record["adk_invocation_event_count"] == 2
    assert run_record["adk_invocation_mismatch"] is False
    assert run_record["adk_event_total_count"] == 2
    assert run_record["adk_event_error_count"] == 0
    assert run_record["adk_event_interrupted_count"] == 0
    assert run_record["adk_event_partial_count"] == 1
    assert run_record["adk_event_turn_complete_count"] == 1
    assert run_record["adk_event_field_coverage"][
        "adk_event_with_invocation_id_count"
    ] == 2
    assert run_record["validation"]["adk_backed_workflow"] is True
    assert [step["name"] for step in run_record["step_results"]] == [
        "product_brief",
        "decision_pack",
        "model_enhancement",
    ]


def test_event_trace_keeps_adk_and_business_event_layers() -> None:
    event_trace = build_control_plane_bundle(sample_workflow_result())["event_trace"]

    assert event_trace["source"] == "ADK Runner events plus business step event mapping"
    assert event_trace["adk_runtime_path"] == "Runner -> Workflow -> BaseNode business steps"
    assert event_trace["adk_event_count"] == 2
    assert event_trace["business_event_count"] == 2
    assert event_trace["project_invocation_id"] == "ce-adk-invocation-sample"
    assert event_trace["adk_invocation_ids"] == ["ce-adk-invocation-sample"]
    assert event_trace["adk_invocation_event_count"] == 2
    assert event_trace["adk_invocation_bound"] is True
    assert event_trace["adk_invocation_mismatch"] is False
    assert event_trace["adk_invocation_missing_count"] == 0
    assert event_trace["adk_event_total_count"] == 2
    assert event_trace["adk_event_records"] == [
        {
            "event_id": "event-product",
            "adk_invocation_id": "ce-adk-invocation-sample",
            "author": "workflow",
            "node_info": {"path": "workflow/product_brief@1"},
            "node_name": "product_brief",
            "node_path": "workflow/product_brief@1",
            "branch": "main",
            "timestamp": "2026-04-29T12:00:00Z",
            "partial": True,
            "turn_complete": False,
            "interrupted": False,
            "error_code": None,
            "error_message": None,
            "finish_reason": None,
            "actions_present": True,
            "custom_metadata_present": True,
            "long_running_tool_ids": [],
            "long_running_tool_id_count": 0,
            "model_version": "gemini-sample",
            "usage_metadata_present": True,
            "cache_metadata_present": False,
            "citation_metadata_present": False,
            "grounding_metadata_present": False,
        },
        {
            "event_id": "event-decision",
            "adk_invocation_id": "ce-adk-invocation-sample",
            "author": "workflow",
            "node_info": {"path": "workflow/decision_pack@1"},
            "node_name": "decision_pack",
            "node_path": "workflow/decision_pack@1",
            "branch": "main",
            "timestamp": "2026-04-29T12:00:01Z",
            "partial": False,
            "turn_complete": True,
            "interrupted": False,
            "error_code": None,
            "error_message": None,
            "finish_reason": "stop",
            "actions_present": False,
            "custom_metadata_present": False,
            "long_running_tool_ids": [],
            "long_running_tool_id_count": 0,
            "model_version": None,
            "usage_metadata_present": False,
            "cache_metadata_present": False,
            "citation_metadata_present": False,
            "grounding_metadata_present": False,
        },
    ]
    assert event_trace["adk_event_field_coverage"] == {
        "adk_event_total_count": 2,
        "adk_event_with_id_count": 2,
        "adk_event_with_invocation_id_count": 2,
        "adk_event_with_author_count": 2,
        "adk_event_with_node_info_count": 2,
        "adk_event_with_timestamp_count": 2,
        "adk_event_with_actions_count": 1,
        "adk_event_with_usage_metadata_count": 1,
    }
    assert event_trace["adk_event_fields_bound"] is True
    assert event_trace["adk_event_coverage_available"] is True
    assert event_trace["adk_event_error_count"] == 0
    assert event_trace["adk_event_interrupted_count"] == 0
    assert event_trace["adk_event_partial_count"] == 1
    assert event_trace["adk_event_turn_complete_count"] == 1
    assert event_trace["adk_event_finish_reasons"] == {"stop": 1}
    assert event_trace["adk_event_author_summary"] == {"workflow": 2}
    assert event_trace["adk_event_node_summary"] == {
        "decision_pack": 1,
        "product_brief": 1,
    }
    assert event_trace["adk_event_branch_summary"] == {"main": 2}
    assert [event["node_name"] for event in event_trace["adk_events_layer"]] == [
        "product_brief",
        "decision_pack",
    ]
    assert [event["step_name"] for event in event_trace["business_step_events_layer"]] == [
        "product_brief",
        "product_brief",
    ]


def test_event_trace_records_missing_adk_invocation_without_failure() -> None:
    workflow_result = sample_workflow_result()
    workflow_result["event_summary"]["adk_events"][0]["adk_invocation_id"] = None

    event_trace = build_control_plane_bundle(workflow_result)["event_trace"]

    assert event_trace["adk_invocation_ids"] == ["ce-adk-invocation-sample"]
    assert event_trace["adk_invocation_event_count"] == 1
    assert event_trace["adk_invocation_missing_count"] == 1
    assert event_trace["adk_invocation_bound"] is False
    assert event_trace["adk_invocation_mismatch"] is False


def test_event_trace_records_native_event_field_gaps_without_failure() -> None:
    workflow_result = sample_workflow_result()
    event = workflow_result["event_summary"]["adk_events"][0]
    event["event_id"] = None
    event["id"] = None
    event["timestamp"] = None
    event["node_info"] = None
    event["actions"] = None

    event_trace = build_control_plane_bundle(workflow_result)["event_trace"]

    assert event_trace["adk_event_field_coverage"] == {
        "adk_event_total_count": 2,
        "adk_event_with_id_count": 1,
        "adk_event_with_invocation_id_count": 2,
        "adk_event_with_author_count": 2,
        "adk_event_with_node_info_count": 1,
        "adk_event_with_timestamp_count": 1,
        "adk_event_with_actions_count": 0,
        "adk_event_with_usage_metadata_count": 1,
    }
    assert event_trace["adk_event_fields_bound"] is False
    assert event_trace["adk_event_coverage_available"] is True
    assert event_trace["adk_event_records"][0]["event_id"] is None


def test_event_trace_records_error_interrupted_state_without_failure() -> None:
    workflow_result = sample_workflow_result()
    event = workflow_result["event_summary"]["adk_events"][1]
    event["interrupted"] = True
    event["error_code"] = "decision_failed"
    event["error_message"] = "decision failed"

    bundle = build_control_plane_bundle(workflow_result)

    assert bundle["event_trace"]["adk_event_error_count"] == 1
    assert bundle["event_trace"]["adk_event_interrupted_count"] == 1
    assert bundle["run_record"]["adk_event_error_count"] == 1
    assert bundle["context_record"]["adk_event_trace_binding"][
        "adk_event_interrupted_count"
    ] == 1


def test_run_record_records_adk_invocation_mismatch_without_failure() -> None:
    workflow_result = sample_workflow_result()
    workflow_result["event_summary"]["adk_events"][1][
        "adk_invocation_id"
    ] = "unexpected-adk-invocation"

    run_record = build_control_plane_bundle(workflow_result)["run_record"]

    assert run_record["project_invocation_id"] == "ce-adk-invocation-sample"
    assert run_record["adk_invocation_id"] is None
    assert run_record["adk_invocation_ids"] == [
        "ce-adk-invocation-sample",
        "unexpected-adk-invocation",
    ]
    assert run_record["adk_invocation_event_count"] == 2
    assert run_record["adk_invocation_bound"] is False
    assert run_record["adk_invocation_mismatch"] is True


def test_artifact_manifest_preserves_artifacts_outputs_and_metadata() -> None:
    artifact_manifest = build_control_plane_bundle(sample_workflow_result())[
        "artifact_manifest"
    ]

    assert artifact_manifest["mapping_status"] == "business_artifact_mapping"
    assert artifact_manifest["artifact_count"] == 4
    assert [artifact["kind"] for artifact in artifact_manifest["artifacts"]] == [
        "business_output",
        "business_output",
        "business_output",
        "workflow_summary",
    ]
    assert artifact_manifest["output_files"] == [
        "outputs/product-briefs/sample.md",
        "outputs/decision-packs/sample.md",
        "outputs/model-enhancements/sample.md",
        "outputs/workflows/sample.md",
    ]
    assert artifact_manifest["metadata_files"] == [
        "outputs/.metadata/product.json",
        "outputs/.metadata/decision.json",
        "outputs/.metadata/enhancement.json",
        "outputs/.metadata/workflow.json",
    ]
    assert artifact_manifest["adk_artifact_bound_count"] == 4
    assert artifact_manifest["adk_artifact_binding_error_count"] == 0
    assert [binding["adk_artifact_bound"] for binding in artifact_manifest["adk_artifact_bindings"]] == [
        True,
        True,
        True,
        True,
    ]
    assert artifact_manifest["adk_artifact_bindings"][0]["adk_artifact_metadata"][
        "metadata_id"
    ] == "output-product_brief"


def test_control_plane_builder_does_not_mutate_workflow_result() -> None:
    workflow_result = sample_workflow_result()
    original = deepcopy(workflow_result)

    build_control_plane_bundle(workflow_result)

    assert workflow_result == original


def sample_workflow_result() -> dict:
    return {
        "command": (
            "python -m cognition_engine.workflow "
            "--insight insight-adk-runner-centrality"
        ),
        "contract_version": "ce-insight-to-decision-workflow-result/v1",
        "workflow_name": "insight-to-decision workflow",
        "output_type": "insight-to-decision-workflow",
        "insight_id": "insight-adk-runner-centrality",
        "status": "success",
        "execution_id": "ce-adk-workflow-sample",
        "session_id": "adk-session-sample",
        "context_id": "adk-session:adk-session-sample",
        "invocation_id": "ce-adk-invocation-sample",
        "adk_runtime": "Runner -> Workflow -> BaseNode business steps",
        "adk_backed": True,
        "legacy_fallback_used": False,
        "step_results": [
            child_step("product_brief", "product-brief"),
            child_step("decision_pack", "decision-pack"),
            child_step("model_enhancement", "model-enhancement"),
        ],
        "event_summary": {
            "source": "ADK Runner events plus business step event mapping",
            "adk_runtime_path": "Runner -> Workflow -> BaseNode business steps",
            "adk_event_count": 2,
            "business_event_count": 2,
            "adk_events": [
                {
                    "event_id": "event-product",
                    "id": "event-product",
                    "author": "workflow",
                    "adk_invocation_id": "ce-adk-invocation-sample",
                    "invocation_id": "ce-adk-invocation-sample",
                    "node_info": {"path": "workflow/product_brief@1"},
                    "node_name": "product_brief",
                    "node_path": "workflow/product_brief@1",
                    "branch": "main",
                    "timestamp": "2026-04-29T12:00:00Z",
                    "partial": True,
                    "turn_complete": False,
                    "interrupted": False,
                    "error_code": None,
                    "error_message": None,
                    "finish_reason": None,
                    "actions": {"state_delta": {"step": "product_brief"}},
                    "custom_metadata": {"source": "sample"},
                    "long_running_tool_ids": [],
                    "model_version": "gemini-sample",
                    "usage_metadata": {"total_token_count": 42},
                    "cache_metadata": None,
                    "citation_metadata": None,
                    "grounding_metadata": None,
                },
                {
                    "event_id": "event-decision",
                    "id": "event-decision",
                    "author": "workflow",
                    "adk_invocation_id": "ce-adk-invocation-sample",
                    "invocation_id": "ce-adk-invocation-sample",
                    "node_info": {"path": "workflow/decision_pack@1"},
                    "node_name": "decision_pack",
                    "node_path": "workflow/decision_pack@1",
                    "branch": "main",
                    "timestamp": "2026-04-29T12:00:01Z",
                    "partial": False,
                    "turn_complete": True,
                    "interrupted": False,
                    "error_code": None,
                    "error_message": None,
                    "finish_reason": "stop",
                    "actions": None,
                    "custom_metadata": None,
                    "long_running_tool_ids": [],
                    "model_version": None,
                    "usage_metadata": None,
                    "cache_metadata": None,
                    "citation_metadata": None,
                    "grounding_metadata": None,
                },
            ],
            "step_events": [
                {"step_name": "product_brief", "status": "started"},
                {"step_name": "product_brief", "status": "success"},
            ],
        },
        "artifact_refs": [
            artifact_ref(
                "product_brief",
                "business_output",
                "outputs/product-briefs/sample.md",
                "outputs/.metadata/product.json",
            ),
            artifact_ref(
                "decision_pack",
                "business_output",
                "outputs/decision-packs/sample.md",
                "outputs/.metadata/decision.json",
            ),
            artifact_ref(
                "model_enhancement",
                "business_output",
                "outputs/model-enhancements/sample.md",
                "outputs/.metadata/enhancement.json",
            ),
            artifact_ref(
                "workflow",
                "workflow_summary",
                "outputs/workflows/sample.md",
                "outputs/.metadata/workflow.json",
            ),
        ],
        "validation": {
            "adk_backed_workflow": True,
            "adk_session_mapped": True,
            "adk_events_mapped": True,
            "business_step_events_mapped": True,
            "business_artifact_refs_mapped": True,
            "workflow_summary_artifact_mapped": True,
        },
    }


def child_step(name: str, output_type: str) -> dict:
    return {
        "name": name,
        "status": "success",
        "output_type": output_type,
        "output_file": f"outputs/{output_type}/sample.md",
        "metadata_file": f"outputs/.metadata/{name}.json",
        "error_code": None,
        "error_message": None,
    }


def artifact_ref(
    step_name: str,
    kind: str,
    output_file: str,
    metadata_file: str,
) -> dict:
    return {
        "artifact_id": f"ce-adk-workflow-sample:{step_name}:output",
        "step_name": step_name,
        "kind": kind,
        "mapping_status": "business_artifact_mapping",
        "path": output_file,
        "metadata_file": metadata_file,
        "metadata_id": f"output-{step_name}",
        "adk_artifact_service": "FileArtifactService",
        "adk_artifact_key": f"{step_name}-{kind}-sample.md",
        "adk_artifact_version": 0,
        "adk_artifact_uri": (
            "adk-file-artifact://cognition_engine_adk_backed_workflow/"
            f"cognition-engine-workflow-user/sessions/adk-session-sample/"
            f"artifacts/{step_name}-{kind}-sample.md/versions/0"
        ),
        "adk_artifact_bound": True,
        "adk_artifact_error": None,
        "adk_artifact_metadata": {
            "execution_id": "ce-adk-workflow-sample",
            "session_id": "adk-session-sample",
            "context_id": "adk-session:adk-session-sample",
            "invocation_id": "ce-adk-invocation-sample",
            "artifact_id": f"ce-adk-workflow-sample:{step_name}:output",
            "step_name": step_name,
            "kind": kind,
            "output_type": "insight-to-decision-workflow"
            if step_name == "workflow"
            else output_file.split("/")[1].removesuffix("s"),
            "metadata_id": f"output-{step_name}",
            "metadata_file": metadata_file,
            "mapping_status": "business_artifact_mapping",
            "source_path": output_file,
            "source_file_exists": True,
        },
    }
