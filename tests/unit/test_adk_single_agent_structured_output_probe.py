#!/usr/bin/env python3
"""ADK 单 agent 结构化输出约束最小验证脚本测试。"""

from pathlib import Path
from types import SimpleNamespace
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from engine.analyzer.probe_adk_single_agent_structured_output import (  # noqa: E402
    AGENT_NAME,
    APP_NAME,
    EXPECTED_OUTPUT_JSON,
    EXPECTED_STRUCTURED_OUTPUT,
    OUTPUT_KEY,
    SELECTED_RUNTIME_PATH,
    build_failure_payload,
    build_success_payload,
    extract_node_name,
    serialize_event,
    serialize_llm_request,
)


def test_extract_node_name_strips_run_id() -> None:
    assert extract_node_name("single_agent_structured_output_node@1") == (
        "single_agent_structured_output_node"
    )
    assert extract_node_name(
        "wf@1/single_agent_structured_output_node@2"
    ) == "single_agent_structured_output_node"
    assert extract_node_name(None) is None


def test_serialize_event_extracts_text_and_state_delta() -> None:
    event = SimpleNamespace(
        author=AGENT_NAME,
        output=None,
        content=SimpleNamespace(
            role="model",
            parts=[SimpleNamespace(text=EXPECTED_OUTPUT_JSON)],
        ),
        actions=SimpleNamespace(state_delta={OUTPUT_KEY: EXPECTED_STRUCTURED_OUTPUT}),
        node_info=SimpleNamespace(path="single_agent_structured_output_node@1"),
    )

    record = serialize_event(event)

    assert record["author"] == AGENT_NAME
    assert record["node_name"] == "single_agent_structured_output_node"
    assert record["text_parts"] == [EXPECTED_OUTPUT_JSON]
    assert record["has_state_delta"] is True
    assert record["state_delta"] == {OUTPUT_KEY: EXPECTED_STRUCTURED_OUTPUT}


def test_serialize_llm_request_extracts_response_schema_metadata() -> None:
    llm_request = SimpleNamespace(
        contents=[
            SimpleNamespace(
                role="user",
                parts=[SimpleNamespace(text="Write a tiny story as structured output.")],
            )
        ],
        config=SimpleNamespace(
            response_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                },
            },
            response_mime_type="application/json",
        ),
    )

    record = serialize_llm_request(llm_request)

    assert record["content_count"] == 1
    assert record["request_roles"] == ["user"]
    assert record["has_response_schema"] is True
    assert record["response_schema_type"] == "dict"
    assert record["response_mime_type"] == "application/json"
    assert record["response_schema_properties"] == ["content", "title"]


def test_build_success_payload_marks_structured_output_acceptance() -> None:
    payload = build_success_payload(
        started_at="2026-04-16T06:00:00Z",
        completed_at="2026-04-16T06:00:01Z",
        duration_seconds=1.23456,
        input_text="Write a tiny story as structured output.",
        adk_module_path="/tmp/google-adk/src/google/adk/__init__.py",
        event_records=[
            {
                "author": AGENT_NAME,
                "node_path": "single_agent_structured_output_node@1",
                "node_name": "single_agent_structured_output_node",
                "output": None,
                "role": "model",
                "text_parts": [EXPECTED_OUTPUT_JSON],
                "has_state_delta": True,
                "state_delta": {OUTPUT_KEY: EXPECTED_STRUCTURED_OUTPUT},
            }
        ],
        request_records=[
            {
                "content_count": 1,
                "request_roles": ["user"],
                "request_texts": ["Write a tiny story as structured output."],
                "has_response_schema": True,
                "response_schema_type": "StoryOutput",
                "response_mime_type": "application/json",
                "response_schema_properties": ["content", "title"],
            }
        ],
        session_state={OUTPUT_KEY: EXPECTED_STRUCTURED_OUTPUT},
    )

    assert payload["result"] == "success"
    assert payload["accepted_as_minimal_single_agent_structured_output_constraint"] is True
    assert payload["runner_app_name"] == APP_NAME
    assert payload["agent_name"] == AGENT_NAME
    assert payload["output_key"] == OUTPUT_KEY
    assert payload["selected_runtime_path"] == SELECTED_RUNTIME_PATH
    assert payload["entered_structured_output_constraint_semantics"] is True
    assert payload["response_schema_request_count"] == 1
    assert payload["final_text_result"] == EXPECTED_OUTPUT_JSON
    assert payload["structured_output_payload"] == EXPECTED_STRUCTURED_OUTPUT
    assert payload["duration_seconds"] == 1.2346


def test_build_failure_payload_keeps_boundary_warning() -> None:
    payload = build_failure_payload(
        started_at="2026-04-16T06:00:00Z",
        completed_at="2026-04-16T06:00:01Z",
        duration_seconds=0.25,
        input_text="Write a tiny story as structured output.",
        exc=RuntimeError("response_schema is missing"),
    )

    assert payload["result"] == "failed"
    assert payload["accepted_as_minimal_single_agent_structured_output_constraint"] is False
    assert payload["error_type"] == "RuntimeError"
    assert payload["selected_runtime_path"] == SELECTED_RUNTIME_PATH
    assert "正式 output_schema 承接层" in payload["boundary_judgement"]
