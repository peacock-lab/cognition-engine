#!/usr/bin/env python3
"""ADK workflow 最小正式入口测试。"""

from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from engine.analyzer.run_adk_workflow_minimal_execution import (  # noqa: E402
    ENTRY_ID,
    ENTRY_TYPE,
    OUTPUTS_DIR,
    PROBE_REFERENCE,
    WORKFLOW_NAME,
    build_failure_payload,
    build_success_payload,
    resolve_output_path,
)


def test_resolve_output_path_defaults_to_workflow_directory() -> None:
    output_path = resolve_output_path(None)

    assert output_path.parent == OUTPUTS_DIR
    assert output_path.name.startswith(f"{ENTRY_ID}-")
    assert output_path.suffix == ".json"


def test_resolve_output_path_accepts_project_relative_path() -> None:
    output_path = resolve_output_path("outputs/workflow/manual-run.json")

    assert output_path == project_root / "outputs" / "workflow" / "manual-run.json"


def test_build_success_payload_marks_formal_entry_boundary() -> None:
    output_path = project_root / "outputs" / "workflow" / "formal-entry.json"

    payload = build_success_payload(
        started_at="2026-04-17T05:00:00Z",
        completed_at="2026-04-17T05:00:01Z",
        duration_seconds=1.23456,
        input_text="hello-adk-workflow",
        output_path=output_path,
        event_records=[
            {
                "author": "NodeA",
                "node_name": "NodeA",
                "is_child_node_event": True,
                "output": "node-a:hello-adk-workflow",
            },
            {
                "author": "NodeB",
                "node_name": "NodeB",
                "is_child_node_event": True,
                "output": "node-b:node-a:hello-adk-workflow",
            },
        ],
        workflow_graph_built=True,
        formal_output_written=True,
    )

    assert payload["result"] == "success"
    assert payload["entry_type"] == ENTRY_TYPE
    assert payload["probe_reference"] == PROBE_REFERENCE
    assert payload["workflow_name"] == WORKFLOW_NAME
    assert payload["workflow_node_count"] == 2
    assert payload["workflow_execution_order"] == ["NodeA", "NodeB"]
    assert payload["final_output_text"] == "node-b:node-a:hello-adk-workflow"
    assert payload["workflow_graph_built"] is True
    assert payload["workflow_serial_execution_completed"] is True
    assert payload["formal_output_written"] is True
    assert payload["output_file"] == "outputs/workflow/formal-entry.json"
    assert payload["duration_seconds"] == 1.2346
    assert "正式结果文件" in payload["boundary_judgement"]


def test_build_failure_payload_keeps_formal_entry_warning() -> None:
    output_path = project_root / "outputs" / "workflow" / "failed-entry.json"

    payload = build_failure_payload(
        started_at="2026-04-17T05:00:00Z",
        completed_at="2026-04-17T05:00:01Z",
        duration_seconds=0.25,
        input_text="hello-adk-workflow",
        output_path=output_path,
        exc=RuntimeError("workflow execution failed"),
    )

    assert payload["result"] == "failed"
    assert payload["entry_type"] == ENTRY_TYPE
    assert payload["probe_reference"] == PROBE_REFERENCE
    assert payload["workflow_name"] == WORKFLOW_NAME
    assert payload["output_file"] == "outputs/workflow/failed-entry.json"
    assert payload["error_type"] == "RuntimeError"
    assert "probe 级验证结论" in payload["boundary_judgement"]
