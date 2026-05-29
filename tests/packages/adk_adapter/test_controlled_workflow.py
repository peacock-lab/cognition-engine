from __future__ import annotations

from adk_adapter import build_controlled_no_live_workflow


def test_build_controlled_no_live_workflow_returns_adk_workflow() -> None:
    workflow = build_controlled_no_live_workflow(
        workflow_name="controlled-adk-run",
        metadata={"source": "test"},
    )

    assert type(workflow).__name__ == "Workflow"
    assert workflow.name == "controlled_adk_run"
