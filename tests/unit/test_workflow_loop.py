from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from cognition_engine import workflow
from cognition_engine.rendering import generate_outputs


project_root = Path(__file__).parent.parent.parent


def install_real_repo_data(tmp_path: Path, *insight_ids: str) -> None:
    insights_dir = tmp_path / "data" / "insights" / "adk-2.0.0a3"
    frameworks_dir = tmp_path / "data" / "frameworks" / "adk-2.0.0a3"
    insights_dir.mkdir(parents=True, exist_ok=True)
    frameworks_dir.mkdir(parents=True, exist_ok=True)

    source_framework = project_root / "data" / "frameworks" / "adk-2.0.0a3" / "metadata.json"
    frameworks_dir.joinpath("metadata.json").write_text(
        source_framework.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    for insight_id in insight_ids:
        source_insight = project_root / "data" / "insights" / "adk-2.0.0a3" / f"{insight_id}.json"
        insights_dir.joinpath(f"{insight_id}.json").write_text(
            source_insight.read_text(encoding="utf-8"),
            encoding="utf-8",
        )


def with_project_path(tmp_path: Path):
    class ProjectPathContext:
        def __enter__(self):
            self.original_project_path = generate_outputs.NEW_PROJECT_PATH
            generate_outputs.NEW_PROJECT_PATH = tmp_path
            return self

        def __exit__(self, exc_type, exc, tb):
            generate_outputs.NEW_PROJECT_PATH = self.original_project_path

    return ProjectPathContext()


def test_run_workflow_loop_returns_json_error_when_insight_missing(
    capsys,
    tmp_path: Path,
) -> None:
    install_real_repo_data(tmp_path, "insight-adk-runner-centrality")

    with with_project_path(tmp_path):
        exit_code = workflow.run_workflow_loop(None, json_only=True)

    result = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert result["status"] == "error"
    assert result["contract_version"] == "ce-insight-to-decision-workflow-result/v1"
    assert result["workflow_name"] == "insight-to-decision workflow"
    assert result["error_code"] == "missing_insight"
    assert result["steps"] == []
    assert "insight-adk-runner-centrality" in result["available_insight_ids"]


def test_build_workflow_result_returns_error_when_insight_not_found(
    tmp_path: Path,
) -> None:
    install_real_repo_data(tmp_path, "insight-adk-runner-centrality")

    with with_project_path(tmp_path):
        result = workflow.build_workflow_result("insight-does-not-exist")

    assert result["status"] == "error"
    assert result["error_code"] == "insight_not_found"
    assert result["product_brief"]["output_type"] == "product-brief"
    assert result["decision_pack"] is None
    assert result["model_enhancement"] is None
    assert len(result["steps"]) == 1


def test_workflow_success_executes_three_child_loops(tmp_path: Path) -> None:
    install_real_repo_data(tmp_path, "insight-adk-runner-centrality")

    with with_project_path(tmp_path):
        result = workflow.build_workflow_result("insight-adk-runner-centrality")

    assert result["status"] == "success"
    assert result["contract_version"] == "ce-insight-to-decision-workflow-result/v1"
    assert result["output_type"] == "insight-to-decision-workflow"
    assert [step["name"] for step in result["steps"]] == [
        "product_brief",
        "decision_pack",
        "model_enhancement",
    ]
    assert result["product_brief"]["contract_version"] == "ce-brief-result/v1"
    assert result["decision_pack"]["contract_version"] == "ce-decision-pack-result/v1"
    assert result["model_enhancement"]["contract_version"] == "ce-model-enhancement-result/v1"
    assert result["model_enhancement"]["output_type"] == "model-enhancement"
    assert result["output_file"].startswith("outputs/workflows/")
    assert result["metadata_file"].startswith("outputs/.metadata/")
    assert result["metadata_id"].startswith("output-")
    assert result["error_code"] is None
    assert result["adk_backed"] is True
    assert result["legacy_fallback_used"] is False
    assert result["execution_id"].startswith("ce-adk-workflow-")
    assert result["session_id"]
    assert result["context_id"].startswith("adk-session:")
    assert result["invocation_id"].startswith("ce-adk-invocation-")
    assert result["adk_runtime"] == "Runner -> Workflow -> BaseNode business steps"
    assert len(result["artifact_refs"]) == 4
    assert {ref["kind"] for ref in result["artifact_refs"]} == {
        "business_output",
        "workflow_summary",
    }
    assert {ref["mapping_status"] for ref in result["artifact_refs"]} == {
        "business_artifact_mapping"
    }
    assert result["event_summary"]["adk_event_count"] >= 3
    assert result["event_summary"]["business_event_count"] >= 6
    assert {
        event["adk_invocation_id"] for event in result["event_summary"]["adk_events"]
    } == {result["invocation_id"]}
    assert all(ref["adk_artifact_bound"] is True for ref in result["artifact_refs"])
    assert {
        ref["adk_artifact_service"] for ref in result["artifact_refs"]
    } == {"FileArtifactService"}
    assert all(ref["adk_artifact_key"] for ref in result["artifact_refs"])
    assert all(ref["adk_artifact_version"] == 0 for ref in result["artifact_refs"])
    assert all(ref["adk_artifact_uri"] for ref in result["artifact_refs"])
    assert all(ref["adk_artifact_metadata"]["execution_id"] == result["execution_id"] for ref in result["artifact_refs"])
    control_plane = result["control_plane"]
    assert control_plane["bundle_type"] == "control_plane_bundle"
    assert control_plane["execution_id"] == result["execution_id"]
    assert control_plane["context_record"]["execution_id"] == result["execution_id"]
    assert control_plane["run_record"]["execution_id"] == result["execution_id"]
    assert control_plane["event_trace"]["execution_id"] == result["execution_id"]
    assert control_plane["artifact_manifest"]["execution_id"] == result["execution_id"]
    assert control_plane["artifact_manifest"]["artifact_count"] == 4
    assert control_plane["artifact_manifest"]["adk_artifact_bound_count"] == 4
    assert control_plane["artifact_manifest"]["adk_artifact_binding_error_count"] == 0
    assert len(control_plane["artifact_manifest"]["adk_artifact_bindings"]) == 4
    assert control_plane["event_trace"]["adk_event_count"] >= 3
    assert control_plane["event_trace"]["business_event_count"] >= 6
    assert control_plane["event_trace"]["project_invocation_id"] == result["invocation_id"]
    assert control_plane["event_trace"]["adk_invocation_ids"] == [result["invocation_id"]]
    assert control_plane["event_trace"]["adk_invocation_bound"] is True
    assert control_plane["event_trace"]["adk_invocation_mismatch"] is False
    assert control_plane["event_trace"]["adk_event_records"]
    assert control_plane["event_trace"]["adk_event_total_count"] >= 3
    assert control_plane["event_trace"]["adk_event_field_coverage"][
        "adk_event_with_invocation_id_count"
    ] >= 3
    assert control_plane["event_trace"]["adk_event_fields_bound"] is True
    assert control_plane["event_trace"]["adk_event_coverage_available"] is True
    assert control_plane["event_trace"]["adk_event_error_count"] == 0
    assert control_plane["event_trace"]["adk_event_interrupted_count"] == 0
    assert control_plane["event_trace"]["adk_event_author_summary"]
    assert control_plane["event_trace"]["adk_event_node_summary"]
    assert control_plane["run_record"]["adk_invocation_id"] == result["invocation_id"]
    assert control_plane["run_record"]["adk_invocation_bound"] is True
    assert control_plane["run_record"]["adk_event_total_count"] >= 3
    assert control_plane["run_record"]["adk_event_field_coverage"][
        "adk_event_with_id_count"
    ] >= 3


def test_workflow_validation_records_all_child_files(tmp_path: Path) -> None:
    install_real_repo_data(tmp_path, "insight-adk-runner-centrality")

    with with_project_path(tmp_path):
        result = workflow.build_workflow_result("insight-adk-runner-centrality")

    assert result["validation"] == {
        "workflow_output_file_exists": True,
        "workflow_metadata_file_exists": True,
        "product_brief_output_file_exists": True,
        "product_brief_metadata_file_exists": True,
        "decision_pack_output_file_exists": True,
        "decision_pack_metadata_file_exists": True,
        "model_enhancement_output_file_exists": True,
        "model_enhancement_metadata_file_exists": True,
        "adk_backed_workflow": True,
        "adk_session_mapped": True,
        "adk_session_id_mapped": True,
        "adk_invocation_mapped": True,
        "adk_invocation_bound": True,
        "adk_invocation_id_mapped": True,
        "adk_invocation_event_count": result["validation"]["adk_invocation_event_count"],
        "adk_invocation_mismatch": False,
        "adk_event_fields_bound": True,
        "adk_event_coverage_available": True,
        "adk_event_error_count": 0,
        "adk_event_interrupted_count": 0,
        "project_execution_id_mapped": True,
        "project_context_id_mapped": True,
        "project_invocation_id_mapped": True,
        "adk_events_mapped": True,
        "adk_runner_events_mapped": True,
        "business_step_events_mapped": True,
        "adk_artifacts_mapped": True,
        "business_artifact_refs_mapped": True,
        "workflow_summary_artifact_mapped": True,
        "output_files_mapped": True,
        "metadata_files_mapped": True,
        "legacy_fallback_used": False,
        "adk_file_artifacts_bound": True,
        "adk_file_artifact_binding_attempted": True,
        "adk_file_artifact_binding_errors": False,
    }
    assert (tmp_path / result["output_file"]).exists()
    assert (tmp_path / result["metadata_file"]).exists()
    for child_key in ("product_brief", "decision_pack", "model_enhancement"):
        assert (tmp_path / result[child_key]["output_file"]).exists()
        assert (tmp_path / result[child_key]["metadata_file"]).exists()


def test_workflow_output_markdown_and_metadata_are_saved(tmp_path: Path) -> None:
    install_real_repo_data(tmp_path, "insight-adk-runner-centrality")

    with with_project_path(tmp_path):
        result = workflow.build_workflow_result("insight-adk-runner-centrality")

    workflow_output_path = tmp_path / result["output_file"]
    workflow_metadata_path = tmp_path / result["metadata_file"]
    workflow_text = workflow_output_path.read_text(encoding="utf-8")
    workflow_metadata = json.loads(workflow_metadata_path.read_text(encoding="utf-8"))

    assert workflow_output_path.parent == tmp_path / "outputs" / "workflows"
    assert workflow_metadata["type"] == "workflow"
    assert workflow_metadata["file_path"] == result["output_file"]
    assert workflow_metadata["insight_id"] == "insight-adk-runner-centrality"
    assert workflow_metadata["framework_id"] == "adk-2.0.0a3"
    assert "Workflow 汇总: insight-to-decision workflow" in workflow_text
    assert "ce-insight-to-decision-workflow-result/v1" in workflow_text
    assert result["product_brief"]["output_file"] in workflow_text
    assert result["decision_pack"]["metadata_file"] in workflow_text
    assert result["model_enhancement"]["output_file"] in workflow_text
    assert result["execution_id"] in workflow_text
    assert "ADK-backed 承接映射" in workflow_text
    assert "artifact_mapping_status: `business_artifact_mapping`" in workflow_text
    assert "artifact_boundary: `business artifact mapping over cognition-engine outputs / metadata`" in workflow_text
    assert "## 一页结论" not in workflow_text
    assert "## 模型增强内容" not in workflow_text
    assert not (tmp_path / "outputs" / "workflow").exists()


def test_product_brief_failure_stops_following_steps() -> None:
    calls: list[str] = []

    def product_failure(insight_id: str) -> dict:
        calls.append(f"product:{insight_id}")
        return {
            "status": "error",
            "contract_version": "ce-brief-result/v1",
            "output_type": "product-brief",
            "output_file": None,
            "metadata_file": None,
            "metadata_id": None,
            "error_code": "product_failed",
            "error_message": "product failed",
            "validation": {
                "output_file_exists": False,
                "metadata_file_exists": False,
            },
        }

    def unexpected_step(insight_id: str) -> dict:
        calls.append(f"unexpected:{insight_id}")
        raise AssertionError("step should not run")

    result = workflow.build_workflow_result(
        "insight-adk-runner-centrality",
        product_brief_builder=product_failure,
        decision_pack_builder=unexpected_step,
        model_enhancement_builder=unexpected_step,
    )

    assert result["status"] == "error"
    assert result["error_code"] == "product_failed"
    assert result["output_file"] is None
    assert result["metadata_file"] is None
    assert result["validation"]["workflow_output_file_exists"] is False
    assert result["decision_pack"] is None
    assert result["model_enhancement"] is None
    assert calls == ["product:insight-adk-runner-centrality"]


def test_decision_pack_failure_stops_model_enhancement() -> None:
    calls: list[str] = []

    def product_success(insight_id: str) -> dict:
        calls.append(f"product:{insight_id}")
        return child_result("success", "ce-brief-result/v1", "product-brief")

    def decision_failure(insight_id: str) -> dict:
        calls.append(f"decision:{insight_id}")
        return {
            **child_result("error", "ce-decision-pack-result/v1", "decision-pack"),
            "error_code": "decision_failed",
            "error_message": "decision failed",
        }

    def unexpected_enhancement(insight_id: str) -> dict:
        calls.append(f"enhancement:{insight_id}")
        raise AssertionError("model enhancement should not run")

    result = workflow.build_workflow_result(
        "insight-adk-runner-centrality",
        product_brief_builder=product_success,
        decision_pack_builder=decision_failure,
        model_enhancement_builder=unexpected_enhancement,
    )

    assert result["status"] == "error"
    assert result["error_code"] == "decision_failed"
    assert result["output_file"] is None
    assert result["metadata_file"] is None
    assert result["product_brief"]["status"] == "success"
    assert result["model_enhancement"] is None
    assert calls == [
        "product:insight-adk-runner-centrality",
        "decision:insight-adk-runner-centrality",
    ]


def test_workflow_passes_mock_provider_to_model_enhancement_by_default(
    tmp_path: Path,
) -> None:
    install_real_repo_data(tmp_path, "insight-adk-runner-centrality")

    with with_project_path(tmp_path):
        result = workflow.build_workflow_result("insight-adk-runner-centrality")

    output_text = (tmp_path / result["model_enhancement"]["output_file"]).read_text(
        encoding="utf-8",
    )

    assert result["model_enhancement"]["status"] == "success"
    assert "provider: `mock`" in output_text


def test_module_entry_outputs_json_with_mock_provider(tmp_path: Path) -> None:
    install_real_repo_data(tmp_path, "insight-adk-runner-centrality")
    script = (
        "import json, sys; "
        "from pathlib import Path; "
        "from cognition_engine.rendering import generate_outputs; "
        "generate_outputs.NEW_PROJECT_PATH = Path(sys.argv[1]); "
        "from cognition_engine.workflow import main; "
        "raise SystemExit(main(['--insight', 'insight-adk-runner-centrality', '--json']))"
    )

    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    payload = json.loads(result.stdout)

    assert payload["status"] == "success"
    assert payload["workflow_name"] == "insight-to-decision workflow"
    assert payload["output_file"].startswith("outputs/workflows/")
    assert payload["model_enhancement"]["output_type"] == "model-enhancement"


def child_result(status: str, contract_version: str, output_type: str) -> dict:
    return {
        "status": status,
        "contract_version": contract_version,
        "output_type": output_type,
        "output_file": f"outputs/{output_type}/sample.md",
        "metadata_file": "outputs/.metadata/sample.json",
        "metadata_id": "output-sample",
        "error_code": None,
        "error_message": None,
        "validation": {
            "output_file_exists": status == "success",
            "metadata_file_exists": status == "success",
        },
    }
