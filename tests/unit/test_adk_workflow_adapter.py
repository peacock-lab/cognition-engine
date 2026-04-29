from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from cognition_engine.events.event import serialize_adk_event
from cognition_engine.adk_workflow_adapter import (
    WorkflowStep,
    run_adk_backed_workflow,
)


def test_adk_backed_adapter_builds_execution_context_events_and_artifacts() -> None:
    calls: list[str] = []

    def build_step(output_type: str):
        def builder(insight_id: str) -> dict:
            calls.append(f"{output_type}:{insight_id}")
            return child_result("success", output_type)

        return builder

    result = run_adk_backed_workflow(
        insight_id="insight-adk-runner-centrality",
        result_base=result_base("insight-adk-runner-centrality"),
        steps=[
            WorkflowStep("product_brief", "product-brief", build_step("product-brief")),
            WorkflowStep("decision_pack", "decision-pack", build_step("decision-pack")),
            WorkflowStep(
                "model_enhancement",
                "model-enhancement",
                build_step("model-enhancement"),
            ),
        ],
    )

    assert result["status"] == "success"
    assert result["adk_backed"] is True
    assert result["legacy_fallback_used"] is False
    assert result["execution_id"].startswith("ce-adk-workflow-")
    assert result["session_id"]
    assert result["context_id"].startswith("adk-session:")
    assert result["invocation_id"].startswith("ce-adk-invocation-")
    assert {
        event["adk_invocation_id"] for event in result["event_summary"]["adk_events"]
    } == {result["invocation_id"]}
    assert all(
        event["event_id"] and event["author"]
        for event in result["event_summary"]["adk_events"]
    )
    assert all(
        "partial" in event
        and "turn_complete" in event
        and "interrupted" in event
        and "node_info" in event
        and "timestamp" in event
        for event in result["event_summary"]["adk_events"]
    )
    assert [step["name"] for step in result["step_results"]] == [
        "product_brief",
        "decision_pack",
        "model_enhancement",
    ]
    assert len(result["artifact_refs"]) == 3
    assert {ref["kind"] for ref in result["artifact_refs"]} == {"business_output"}
    assert {ref["mapping_status"] for ref in result["artifact_refs"]} == {
        "business_artifact_mapping"
    }
    assert result["validation"]["adk_backed_workflow"] is True
    assert result["validation"]["adk_session_mapped"] is True
    assert result["validation"]["adk_session_id_mapped"] is True
    assert result["validation"]["adk_invocation_mapped"] is True
    assert result["validation"]["adk_invocation_bound"] is True
    assert result["validation"]["adk_invocation_id_mapped"] is True
    assert result["validation"]["adk_invocation_event_count"] >= 3
    assert result["validation"]["adk_invocation_mismatch"] is False
    assert result["validation"]["adk_event_fields_bound"] is True
    assert result["validation"]["adk_event_coverage_available"] is True
    assert result["validation"]["adk_event_error_count"] == 0
    assert result["validation"]["adk_event_interrupted_count"] == 0
    assert result["validation"]["project_execution_id_mapped"] is True
    assert result["validation"]["project_context_id_mapped"] is True
    assert result["validation"]["project_invocation_id_mapped"] is True
    assert result["validation"]["adk_events_mapped"] is True
    assert result["validation"]["adk_runner_events_mapped"] is True
    assert result["validation"]["business_step_events_mapped"] is True
    assert result["validation"]["adk_artifacts_mapped"] is True
    assert result["validation"]["business_artifact_refs_mapped"] is True
    assert result["validation"]["workflow_summary_artifact_mapped"] is False
    assert result["validation"]["output_files_mapped"] is True
    assert result["validation"]["metadata_files_mapped"] is True
    assert result["event_summary"]["adk_event_count"] >= 3
    assert result["event_summary"]["business_event_count"] == 6
    assert calls == [
        "product-brief:insight-adk-runner-centrality",
        "decision-pack:insight-adk-runner-centrality",
        "model-enhancement:insight-adk-runner-centrality",
    ]


def test_serialize_adk_event_preserves_native_event_fields() -> None:
    event = SimpleNamespace(
        id="event-sample",
        invocation_id="ce-adk-invocation-sample",
        author="workflow",
        node_info=SimpleNamespace(path="workflow/product_brief@1"),
        branch="main",
        timestamp=datetime(2026, 4, 29, 12, 0, tzinfo=timezone.utc),
        partial=True,
        turn_complete=False,
        interrupted=True,
        error_code="sample_error",
        error_message="sample error",
        finish_reason="stop",
        actions=SimpleNamespace(state_delta={"step": "product_brief"}),
        custom_metadata={"source": "unit"},
        long_running_tool_ids=["tool-1"],
        model_version="gemini-sample",
        usage_metadata={"total_token_count": 42},
        cache_metadata={"hit": False},
        citation_metadata={"citations": []},
        grounding_metadata={"chunks": []},
        content={"parts": [{"text": "hello"}]},
        output="product_brief:success",
    )

    record = serialize_adk_event(event)

    assert record["event_id"] == "event-sample"
    assert record["id"] == "event-sample"
    assert record["adk_invocation_id"] == "ce-adk-invocation-sample"
    assert record["invocation_id"] == "ce-adk-invocation-sample"
    assert record["author"] == "workflow"
    assert record["node_name"] == "product_brief"
    assert record["node_path"] == "workflow/product_brief@1"
    assert record["branch"] == "main"
    assert record["timestamp"] == "2026-04-29T12:00:00Z"
    assert record["partial"] is True
    assert record["turn_complete"] is False
    assert record["interrupted"] is True
    assert record["error_code"] == "sample_error"
    assert record["error_message"] == "sample error"
    assert record["finish_reason"] == "stop"
    assert record["actions"] == {"state_delta": {"step": "product_brief"}}
    assert record["custom_metadata"] == {"source": "unit"}
    assert record["long_running_tool_ids"] == ["tool-1"]
    assert record["model_version"] == "gemini-sample"
    assert record["usage_metadata"] == {"total_token_count": 42}
    assert record["cache_metadata"] == {"hit": False}
    assert record["citation_metadata"] == {"citations": []}
    assert record["grounding_metadata"] == {"chunks": []}
    assert record["content"] == {"parts": [{"text": "hello"}]}
    assert record["output"] == "product_brief:success"


def test_adk_backed_adapter_halts_after_decision_pack_failure() -> None:
    calls: list[str] = []

    def product_builder(insight_id: str) -> dict:
        calls.append(f"product:{insight_id}")
        return child_result("success", "product-brief")

    def decision_builder(insight_id: str) -> dict:
        calls.append(f"decision:{insight_id}")
        return {
            **child_result("error", "decision-pack"),
            "error_code": "decision_failed",
            "error_message": "decision failed",
        }

    def unexpected_enhancement(insight_id: str) -> dict:
        calls.append(f"enhancement:{insight_id}")
        raise AssertionError("model enhancement should not run")

    result = run_adk_backed_workflow(
        insight_id="insight-adk-runner-centrality",
        result_base=result_base("insight-adk-runner-centrality"),
        steps=[
            WorkflowStep("product_brief", "product-brief", product_builder),
            WorkflowStep("decision_pack", "decision-pack", decision_builder),
            WorkflowStep("model_enhancement", "model-enhancement", unexpected_enhancement),
        ],
    )

    assert result["status"] == "error"
    assert result["error_code"] == "decision_failed"
    assert result["model_enhancement"] is None
    assert result["event_summary"]["step_events"][-1]["status"] == "skipped"
    assert calls == [
        "product:insight-adk-runner-centrality",
        "decision:insight-adk-runner-centrality",
    ]


def result_base(insight_id: str) -> dict:
    return {
        "command": f"python -m cognition_engine.workflow --insight {insight_id}",
        "command_name": "python -m cognition_engine.workflow",
        "usage": "python -m cognition_engine.workflow --insight <insight_id>",
        "contract_version": "ce-insight-to-decision-workflow-result/v1",
        "workflow_name": "insight-to-decision workflow",
        "output_type": "insight-to-decision-workflow",
        "insight_id": insight_id,
        "output_file": None,
        "metadata_file": None,
        "metadata_id": None,
    }


def child_result(status: str, output_type: str) -> dict:
    return {
        "status": status,
        "contract_version": f"ce-{output_type}-result/v1",
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
