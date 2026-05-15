from __future__ import annotations

from observability_hub import build_adk_agent_shell_evidence


def test_builds_adk_agent_shell_evidence_from_sanitized_run_input() -> None:
    evidence = build_adk_agent_shell_evidence(
        {
            "agent_name": "task_quality_shell",
            "agent_type": "LlmAgent",
            "app_name": "agent-shell-app",
            "user_id": "test-user",
            "session_id": "session-001",
            "requested_invocation_id": "requested-001",
            "adk_invocation_id": "adk-001",
            "invocation_binding": {
                "requested_invocation_id": "requested-001",
                "adk_invocation_id": "adk-001",
                "session_id": "session-001",
            },
            "events": [
                {
                    "event_id": "event-001",
                    "event_type": "node_completed",
                    "payload": {"content": {"parts": [{"text": "hidden"}]}},
                    "metadata": {
                        "author": "task_quality_shell",
                        "branch": "parallel_root.task_quality_shell",
                        "adk_invocation_id": "adk-001",
                        "adk_transfer_to_agent": "handoff_target",
                        "node_path": "task_quality_shell",
                    },
                }
            ],
            "errors": [],
            "metadata": {
                "no_live_execution_observed": True,
                "run_config": {"max_llm_calls": 1},
                "service_bundle": {"source": "in_memory"},
            },
        },
        assembly_metadata={
            "agent_name": "task_quality_shell",
            "agent_type": "LlmAgent",
            "app_name": "agent-shell-app",
            "user_id": "test-user",
            "service_bundle": {"source": "in_memory"},
            "assembly_options": {"instruction_length": 42},
        },
    )

    assert evidence.runtime_kind == "adk_agent_shell"
    assert evidence.agent_name == "task_quality_shell"
    assert evidence.status == "success"
    assert evidence.session_summary["session_observed"] is True
    assert evidence.invocation_summary["binding_present"] is True
    assert evidence.event_summary["event_count"] == 1
    assert evidence.event_summary["event_authors"] == ["task_quality_shell"]
    assert evidence.event_summary["branch_ids"] == ["parallel_root.task_quality_shell"]
    assert evidence.event_summary["invocation_ids"] == ["adk-001"]
    assert evidence.event_summary["handoff_targets"] == ["handoff_target"]
    assert evidence.event_summary["handoff_event_count"] == 1
    assert evidence.event_summary["node_paths"] == ["task_quality_shell"]
    assert evidence.event_summary["content_observed"] is True
    assert evidence.artifact_summary["artifact_count"] == 0
    assert evidence.no_live_execution_observed is True
    assert evidence.service_bundle == {"source": "in_memory"}
    assert evidence.assembly_options == {"instruction_length": 42}
    assert "Multi-agent event facts are summary-only hints, not topology truth." in (
        evidence.contract_candidate_notes
    )
    assert "Handoff event facts are ADK action hints, not handoff refs." in (
        evidence.contract_candidate_notes
    )
    assert "No topology, handoff, or role refs are produced." in (
        evidence.contract_candidate_notes
    )


def test_agent_shell_evidence_does_not_require_adk_or_adapter_objects() -> None:
    evidence = build_adk_agent_shell_evidence(
        {
            "agent_name": "plain-agent",
            "agent_type": "LlmAgent",
            "events": [],
            "errors": [{"error_id": "err-1"}],
            "metadata": {},
        }
    )

    assert evidence.status == "failed"
    assert evidence.event_summary["handoff_targets"] == []
    assert evidence.event_summary["handoff_event_count"] == 0
    assert evidence.warnings == [
        "assembly_metadata was not provided; assembly facts are partial.",
        "agent run did not include runtime event summaries.",
    ]
    assert "ADK native objects are summarized as plain metadata." in (
        evidence.contract_candidate_notes
    )
