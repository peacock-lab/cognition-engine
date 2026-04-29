from __future__ import annotations

from cognition_engine.events.event_trace import build_event_trace_governance


def test_build_event_trace_governance_matches_event_trace_contract() -> None:
    governance = build_event_trace_governance(
        [
            {
                "event_id": "event-product",
                "adk_invocation_id": "ce-adk-invocation-sample",
                "author": "workflow",
                "node_info": {"path": "workflow/product_brief@1"},
                "node_name": "product_brief",
                "node_path": "workflow/product_brief@1",
                "branch": "main",
                "timestamp": "2026-04-30T10:00:00Z",
                "partial": True,
                "turn_complete": False,
                "interrupted": False,
                "error_code": None,
                "error_message": None,
                "finish_reason": None,
                "actions": {"state_delta": {"step": "product_brief"}},
                "custom_metadata": {"source": "unit"},
                "long_running_tool_ids": [],
                "model_version": "gemini-sample",
                "usage_metadata": {"total_token_count": 42},
                "cache_metadata": None,
                "citation_metadata": None,
                "grounding_metadata": None,
            },
            {
                "event_id": "event-decision",
                "adk_invocation_id": "ce-adk-invocation-sample",
                "author": "workflow",
                "node_info": {"path": "workflow/decision_pack@1"},
                "node_name": "decision_pack",
                "node_path": "workflow/decision_pack@1",
                "branch": "main",
                "timestamp": "2026-04-30T10:00:01Z",
                "partial": False,
                "turn_complete": True,
                "interrupted": True,
                "error_code": "decision_failed",
                "error_message": "decision failed",
                "finish_reason": "stop",
                "actions": None,
                "custom_metadata": None,
                "long_running_tool_ids": ["tool-1"],
                "model_version": None,
                "usage_metadata": None,
                "cache_metadata": None,
                "citation_metadata": None,
                "grounding_metadata": None,
            },
        ]
    )

    assert governance["adk_event_field_coverage"] == {
        "adk_event_total_count": 2,
        "adk_event_with_id_count": 2,
        "adk_event_with_invocation_id_count": 2,
        "adk_event_with_author_count": 2,
        "adk_event_with_node_info_count": 2,
        "adk_event_with_timestamp_count": 2,
        "adk_event_with_actions_count": 1,
        "adk_event_with_usage_metadata_count": 1,
    }
    assert governance["adk_event_fields_bound"] is True
    assert governance["adk_event_error_count"] == 1
    assert governance["adk_event_interrupted_count"] == 1
    assert governance["adk_event_partial_count"] == 1
    assert governance["adk_event_turn_complete_count"] == 1
    assert governance["adk_event_finish_reasons"] == {"stop": 1}
    assert governance["adk_event_author_summary"] == {"workflow": 2}
    assert governance["adk_event_node_summary"] == {
        "decision_pack": 1,
        "product_brief": 1,
    }
    assert governance["adk_event_branch_summary"] == {"main": 2}
    assert governance["adk_event_records"][1]["long_running_tool_id_count"] == 1


def test_events_readme_is_module_boundary_not_task_log() -> None:
    readme = open("cognition_engine/events/README.md", encoding="utf-8").read()

    assert "Module Position" in readme
    assert "ADK Correspondence" in readme
    assert "control_plane Consumption" in readme
    assert "任务" not in readme
    assert "结果包" not in readme
