from __future__ import annotations

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
    assert [step["name"] for step in result["step_results"]] == [
        "product_brief",
        "decision_pack",
        "model_enhancement",
    ]
    assert len(result["artifact_refs"]) == 3
    assert result["validation"]["adk_backed_workflow"] is True
    assert result["validation"]["adk_session_mapped"] is True
    assert result["validation"]["adk_events_mapped"] is True
    assert result["event_summary"]["adk_event_count"] >= 3
    assert result["event_summary"]["business_event_count"] == 6
    assert calls == [
        "product-brief:insight-adk-runner-centrality",
        "decision-pack:insight-adk-runner-centrality",
        "model-enhancement:insight-adk-runner-centrality",
    ]


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
