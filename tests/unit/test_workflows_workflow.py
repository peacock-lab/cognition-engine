from __future__ import annotations

import subprocess
import sys

import pytest

from cognition_engine import workflow as top_level_workflow
from cognition_engine.workflows import workflow as workflows_workflow


def test_workflows_module_and_top_level_facade_share_public_entrypoints() -> None:
    assert top_level_workflow.run_workflow_loop is workflows_workflow.run_workflow_loop
    assert top_level_workflow.build_workflow_result is workflows_workflow.build_workflow_result
    assert top_level_workflow.WorkflowError is workflows_workflow.WorkflowError
    assert top_level_workflow.COMMAND_NAME == "python -m cognition_engine.workflow"


def test_workflow_request_validation_and_error_contract_stay_in_workflows_module() -> None:
    assert workflows_workflow.validate_workflow_request(" insight-sample ") == (
        "insight-sample"
    )
    with pytest.raises(workflows_workflow.WorkflowError) as exc_info:
        workflows_workflow.validate_workflow_request("insight one")

    assert exc_info.value.error_code == "invalid_insight_id"
    error_result = workflows_workflow.build_error_result(
        exc_info.value.error_code,
        exc_info.value.error_message,
        insight_id=exc_info.value.insight_id,
    )
    assert error_result["status"] == "error"
    assert error_result["contract_version"] == (
        "ce-insight-to-decision-workflow-result/v1"
    )
    assert error_result["workflow_name"] == "insight-to-decision workflow"
    assert error_result["event_summary"]["adk_event_count"] == 0


def test_top_level_module_entrypoint_still_uses_workflow_facade() -> None:
    script = (
        "from cognition_engine.workflow import main, run_workflow_loop; "
        "import cognition_engine.workflows.workflow as wf; "
        "print(main is wf.main); "
        "print(run_workflow_loop is wf.run_workflow_loop)"
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.splitlines() == ["True", "True"]


def test_workflows_readme_is_module_boundary_not_task_log() -> None:
    readme = open("cognition_engine/workflows/README.md", encoding="utf-8").read()

    assert "Module Position" in readme
    assert "ADK Correspondence" in readme
    assert "Top-Level Consumption" in readme
    assert "任务" not in readme
    assert "结果包" not in readme
