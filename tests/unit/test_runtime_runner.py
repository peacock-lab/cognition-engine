from __future__ import annotations

from cognition_engine.runtime import ADK_RUNTIME_PATH, runtime_path_for_event_trace


def test_runtime_path_for_event_trace_prefers_event_summary_path() -> None:
    assert runtime_path_for_event_trace(
        event_summary={"adk_runtime_path": "summary-runtime-path"},
        workflow_result={"adk_runtime": ADK_RUNTIME_PATH},
    ) == "summary-runtime-path"


def test_runtime_path_for_event_trace_falls_back_to_workflow_result() -> None:
    assert runtime_path_for_event_trace(
        event_summary={},
        workflow_result={"adk_runtime": ADK_RUNTIME_PATH},
    ) == ADK_RUNTIME_PATH


def test_runtime_readme_is_module_boundary_not_task_log() -> None:
    readme = open("cognition_engine/runtime/README.md", encoding="utf-8").read()

    assert "Module Position" in readme
    assert "ADK Correspondence" in readme
    assert "adk_workflow_adapter.py Consumption" in readme
    assert "任务" not in readme
    assert "结果包" not in readme
