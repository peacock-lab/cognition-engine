#!/usr/bin/env python3
"""ADK workflow execution 最小接入验证脚本测试。"""

from pathlib import Path
from types import SimpleNamespace
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from engine.analyzer.probe_adk_workflow import (  # noqa: E402
    APP_NAME,
    WORKFLOW_NAME,
    build_failure_payload,
    build_success_payload,
    extract_node_name,
    serialize_event,
)


def test_extract_node_name_strips_run_id() -> None:
    assert extract_node_name("minimal_workflow_probe@1/NodeA@1") == "NodeA"
    assert extract_node_name("minimal_workflow_probe@1") == "minimal_workflow_probe"
    assert extract_node_name(None) is None


def test_serialize_event_extracts_workflow_path_and_state_delta() -> None:
    event = SimpleNamespace(
        author="NodeA",
        output="node-a:hello-adk-workflow",
        content=SimpleNamespace(role="model"),
        actions=SimpleNamespace(state_delta={"workflow_probe_stage": "prepare"}),
        node_info=SimpleNamespace(path="minimal_workflow_probe@1/NodeA@1"),
    )

    record = serialize_event(event)

    assert record["author"] == "NodeA"
    assert record["node_path"] == "minimal_workflow_probe@1/NodeA@1"
    assert record["node_name"] == "NodeA"
    assert record["is_child_node_event"] is True
    assert record["output"] == "node-a:hello-adk-workflow"
    assert record["has_state_delta"] is True
    assert record["state_delta"] == {"workflow_probe_stage": "prepare"}


def test_build_success_payload_marks_minimal_workflow_acceptance() -> None:
    payload = build_success_payload(
        started_at="2026-04-16T03:00:00Z",
        completed_at="2026-04-16T03:00:01Z",
        duration_seconds=1.23456,
        input_text="hello-adk-workflow",
        adk_module_path="/tmp/google-adk/src/google/adk/__init__.py",
        event_records=[
            {
                "author": "NodeA",
                "node_path": "minimal_workflow_probe@1/NodeA@1",
                "node_name": "NodeA",
                "is_child_node_event": True,
                "output": "node-a:hello-adk-workflow",
                "role": "model",
                "has_state_delta": True,
                "state_delta": {"workflow_probe_stage": "prepare"},
            },
            {
                "author": "NodeB",
                "node_path": "minimal_workflow_probe@1/NodeB@1",
                "node_name": "NodeB",
                "is_child_node_event": True,
                "output": "node-b:node-a:hello-adk-workflow",
                "role": "model",
                "has_state_delta": True,
                "state_delta": {"workflow_probe_stage": "finalize"},
            },
        ],
        persisted_outputs=[
            "node-a:hello-adk-workflow",
            "node-b:node-a:hello-adk-workflow",
        ],
    )

    assert payload["result"] == "success"
    assert payload["accepted_as_minimal_workflow"] is True
    assert payload["runner_app_name"] == APP_NAME
    assert payload["workflow_name"] == WORKFLOW_NAME
    assert payload["workflow_nodes_observed"] == ["NodeA", "NodeB"]
    assert payload["workflow_execution_order"] == ["NodeA", "NodeB"]
    assert payload["workflow_node_count"] == 2
    assert payload["final_output_text"] == "node-b:node-a:hello-adk-workflow"
    assert payload["state_delta_observed"] is True
    assert payload["duration_seconds"] == 1.2346


def test_build_failure_payload_keeps_boundary_warning() -> None:
    payload = build_failure_payload(
        started_at="2026-04-16T03:00:00Z",
        completed_at="2026-04-16T03:00:01Z",
        duration_seconds=0.25,
        input_text="hello-adk-workflow",
        exc=RuntimeError("workflow import failed"),
    )

    assert payload["result"] == "failed"
    assert payload["accepted_as_minimal_workflow"] is False
    assert payload["error_type"] == "RuntimeError"
    assert "正式 workflow 接入层" in payload["boundary_judgement"]
