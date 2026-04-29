#!/usr/bin/env python3
"""ADK agent runtime result 最小接入验证脚本测试。"""

from pathlib import Path
from types import SimpleNamespace
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from engine.analyzer.probe_adk_agent_runtime_result import (  # noqa: E402
    AGENT_NAME,
    APP_NAME,
    OUTPUT_KEY,
    SELECTED_RUNTIME_PATH,
    build_failure_payload,
    build_success_payload,
    extract_node_name,
    serialize_event,
)


def test_extract_node_name_strips_run_id() -> None:
    assert extract_node_name("agent_runtime_probe@1") == "agent_runtime_probe"
    assert extract_node_name("wf@1/agent_runtime_probe@2") == "agent_runtime_probe"
    assert extract_node_name(None) is None


def test_serialize_event_extracts_output_text_and_state_delta() -> None:
    event = SimpleNamespace(
        author=AGENT_NAME,
        output="hello-agent-runtime-result",
        content=SimpleNamespace(
            role="model",
            parts=[SimpleNamespace(text="hello-agent-runtime-result")],
        ),
        actions=SimpleNamespace(state_delta={OUTPUT_KEY: "hello-agent-runtime-result"}),
        node_info=SimpleNamespace(path="agent_runtime_probe@1"),
    )

    record = serialize_event(event)

    assert record["author"] == AGENT_NAME
    assert record["node_path"] == "agent_runtime_probe@1"
    assert record["node_name"] == "agent_runtime_probe"
    assert record["output"] == "hello-agent-runtime-result"
    assert record["role"] == "model"
    assert record["text_parts"] == ["hello-agent-runtime-result"]
    assert record["has_state_delta"] is True
    assert record["state_delta"] == {OUTPUT_KEY: "hello-agent-runtime-result"}


def test_build_success_payload_marks_agent_runtime_result_acceptance() -> None:
    payload = build_success_payload(
        started_at="2026-04-16T04:00:00Z",
        completed_at="2026-04-16T04:00:01Z",
        duration_seconds=1.23456,
        input_text="hello-adk-agent-runtime-result",
        adk_module_path="/tmp/google-adk/src/google/adk/__init__.py",
        wrapper_node_class="_V1LlmAgentWrapper",
        event_records=[
            {
                "author": AGENT_NAME,
                "node_path": "agent_runtime_probe@1",
                "node_name": "agent_runtime_probe",
                "output": None,
                "role": "model",
                "text_parts": ["hello-agent-runtime-result"],
                "has_state_delta": True,
                "state_delta": {OUTPUT_KEY: "hello-agent-runtime-result"},
            }
        ],
        persisted_outputs=["hello-agent-runtime-result"],
        session_state={OUTPUT_KEY: "hello-agent-runtime-result"},
    )

    assert payload["result"] == "success"
    assert payload["accepted_as_minimal_agent_runtime_result"] is True
    assert payload["runner_app_name"] == APP_NAME
    assert payload["agent_name"] == AGENT_NAME
    assert payload["agent_mode"] == "single_turn"
    assert payload["output_key"] == OUTPUT_KEY
    assert payload["selected_runtime_path"] == SELECTED_RUNTIME_PATH
    assert payload["wrapper_node_class"] == "_V1LlmAgentWrapper"
    assert payload["event_output_observed"] is False
    assert payload["event_output"] is None
    assert payload["content_text_result"] == "hello-agent-runtime-result"
    assert payload["runtime_result_text"] == "hello-agent-runtime-result"
    assert payload["state_delta_observed"] is True
    assert payload["state_delta"] == {OUTPUT_KEY: "hello-agent-runtime-result"}
    assert payload["session_state"] == {OUTPUT_KEY: "hello-agent-runtime-result"}
    assert payload["duration_seconds"] == 1.2346


def test_build_failure_payload_keeps_boundary_warning() -> None:
    payload = build_failure_payload(
        started_at="2026-04-16T04:00:00Z",
        completed_at="2026-04-16T04:00:01Z",
        duration_seconds=0.25,
        input_text="hello-adk-agent-runtime-result",
        exc=RuntimeError("root single_turn agent is rejected"),
    )

    assert payload["result"] == "failed"
    assert payload["accepted_as_minimal_agent_runtime_result"] is False
    assert payload["error_type"] == "RuntimeError"
    assert payload["selected_runtime_path"] == SELECTED_RUNTIME_PATH
    assert "正式 agent 承接层" in payload["boundary_judgement"]
