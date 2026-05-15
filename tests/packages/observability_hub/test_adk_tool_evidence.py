from __future__ import annotations

from observability_hub import AdkToolCallEvidence, build_adk_tool_call_evidence


def test_builds_adk_tool_call_evidence_from_sanitized_tool_result() -> None:
    evidence = build_adk_tool_call_evidence(
        {
            "tool_name": "review_task_context",
            "tool_kind": "deterministic_no_live_task_review",
            "tool_call_allowed": True,
            "tool_call_attempted": True,
            "tool_runtime_call_performed": True,
            "tool_confirmation_required": False,
            "tool_confirmation_granted": True,
            "adk_tool_confirmation_requested": False,
            "tool_approval_ref": "approval://tool-214",
            "tool_confirmation_decision_source": "test.operator_approval",
            "tool_input_summary": {
                "argument_keys": ["task_ref"],
                "argument_count": 1,
                "input_digest": "abc",
            },
            "tool_output_summary": {
                "result_kind": "deterministic_no_live_task_review",
                "recommendation": "review_ready",
                "output_digest": "def",
            },
            "tool_failure_type": None,
            "tool_run_ref": "adk-function-tool-run://tool-run-001",
            "session_id": "session://tool-test",
            "artifact_delta_refs": [],
            "readonly_facts_embedded": False,
            "does_not_store_raw_tool_input": True,
            "does_not_store_raw_tool_output": True,
            "metadata": {"source": "test"},
        },
        assembly_metadata={
            "assembly": "composition.adk_tool_assembly",
            "tool_name": "review_task_context",
        },
    )

    assert isinstance(evidence, AdkToolCallEvidence)
    assert evidence.runtime_kind == "adk_function_tool"
    assert evidence.tool_name == "review_task_context"
    assert evidence.tool_kind == "deterministic_no_live_task_review"
    assert evidence.status == "success"
    assert evidence.tool_evidence_ref.startswith(
        "adk-tool-call-evidence://adk-tool-call-evidence-"
    )
    assert evidence.tool_run_ref == "adk-function-tool-run://tool-run-001"
    assert evidence.tool_input_summary["argument_keys"] == ["task_ref"]
    assert evidence.tool_output_summary["recommendation"] == "review_ready"
    assert evidence.adk_tool_confirmation_requested is False
    assert evidence.tool_approval_ref == "approval://tool-214"
    assert evidence.tool_confirmation_decision_source == "test.operator_approval"
    assert evidence.does_not_store_raw_tool_input is True
    assert evidence.does_not_store_raw_tool_output is True
    assert evidence.raw_adk_object_included is False
    assert evidence.warnings == []


def test_adk_tool_call_evidence_marks_failed_tool_call() -> None:
    evidence = build_adk_tool_call_evidence(
        {
            "tool_name": "review_task_context",
            "tool_kind": "deterministic_no_live_task_review",
            "tool_call_allowed": False,
            "tool_call_attempted": False,
            "tool_runtime_call_performed": False,
            "tool_confirmation_required": False,
            "tool_confirmation_granted": False,
            "tool_input_summary": {},
            "tool_output_summary": {},
            "tool_failure_type": "tool_call_not_allowed",
            "tool_run_ref": "adk-function-tool-run://tool-run-002",
            "does_not_store_raw_tool_input": True,
            "does_not_store_raw_tool_output": True,
            "metadata": {},
        }
    )

    assert evidence.status == "failed"
    assert evidence.tool_failure_type == "tool_call_not_allowed"
    assert evidence.tool_call_attempted is False
    assert evidence.tool_runtime_call_performed is False
    assert evidence.warnings == [
        "assembly_metadata was not provided; assembly facts are partial."
    ]
