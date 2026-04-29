#!/usr/bin/env python3
"""ADK 单 agent 最小 tool 调用接入验证脚本测试。"""

from pathlib import Path
from types import SimpleNamespace
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from engine.analyzer.probe_adk_single_agent_tool_call import (  # noqa: E402
    AGENT_NAME,
    APP_NAME,
    DEFAULT_FINAL_TEXT,
    SELECTED_RUNTIME_PATH,
    TOOL_NAME,
    build_failure_payload,
    build_success_payload,
    extract_node_name,
    serialize_event,
    serialize_llm_request,
)


def test_extract_node_name_strips_run_id() -> None:
    assert extract_node_name("single_agent_tool_node@1") == "single_agent_tool_node"
    assert extract_node_name("wf@1/single_agent_tool_node@2") == "single_agent_tool_node"
    assert extract_node_name(None) is None


def test_serialize_event_extracts_tool_call_and_response() -> None:
    event = SimpleNamespace(
        author=AGENT_NAME,
        output=None,
        content=SimpleNamespace(
            role="model",
            parts=[
                SimpleNamespace(
                    text=None,
                    function_call=SimpleNamespace(id="fc-1", name=TOOL_NAME, args={"x": 1, "y": 2}),
                    function_response=None,
                ),
                SimpleNamespace(
                    text=None,
                    function_call=None,
                    function_response=SimpleNamespace(id="fc-1", name=TOOL_NAME, response={"result": 3}),
                ),
                SimpleNamespace(
                    text=DEFAULT_FINAL_TEXT,
                    function_call=None,
                    function_response=None,
                ),
            ],
        ),
        actions=SimpleNamespace(state_delta={}),
        node_info=SimpleNamespace(path="single_agent_tool_node@1"),
    )

    record = serialize_event(event)

    assert record["author"] == AGENT_NAME
    assert record["node_name"] == "single_agent_tool_node"
    assert record["function_calls"] == [{"id": "fc-1", "name": TOOL_NAME, "args": {"x": 1, "y": 2}}]
    assert record["function_responses"] == [
        {"id": "fc-1", "name": TOOL_NAME, "response": {"result": 3}}
    ]
    assert record["text_parts"] == [DEFAULT_FINAL_TEXT]


def test_serialize_llm_request_extracts_roles_and_tool_metadata() -> None:
    llm_request = SimpleNamespace(
        contents=[
            SimpleNamespace(
                role="user",
                parts=[SimpleNamespace(text="Please add 1 and 2.", function_response=None)],
            ),
            SimpleNamespace(
                role="tool",
                parts=[
                    SimpleNamespace(
                        text=None,
                        function_response=SimpleNamespace(name=TOOL_NAME, response={"result": 3}),
                    )
                ],
            ),
        ],
        tools=[SimpleNamespace(), SimpleNamespace()],
    )

    record = serialize_llm_request(llm_request)

    assert record["content_count"] == 2
    assert record["request_roles"] == ["user", "tool"]
    assert "Please add 1 and 2." in record["request_texts"]
    assert record["tool_declaration_count"] == 2
    assert record["function_response_names"] == [TOOL_NAME]


def test_build_success_payload_marks_single_agent_tool_call_acceptance() -> None:
    payload = build_success_payload(
        started_at="2026-04-16T05:00:00Z",
        completed_at="2026-04-16T05:00:01Z",
        duration_seconds=1.23456,
        input_text="Please add 1 and 2.",
        adk_module_path="/tmp/google-adk/src/google/adk/__init__.py",
        event_records=[
            {
                "author": AGENT_NAME,
                "node_path": "single_agent_tool_node@1",
                "node_name": "single_agent_tool_node",
                "output": None,
                "role": "model",
                "text_parts": [],
                "function_calls": [{"id": "fc-1", "name": TOOL_NAME, "args": {"x": 1, "y": 2}}],
                "function_responses": [],
                "has_state_delta": False,
                "state_delta": {},
            },
            {
                "author": AGENT_NAME,
                "node_path": "single_agent_tool_node@1",
                "node_name": "single_agent_tool_node",
                "output": None,
                "role": "tool",
                "text_parts": [],
                "function_calls": [],
                "function_responses": [{"id": "fc-1", "name": TOOL_NAME, "response": {"result": 3}}],
                "has_state_delta": False,
                "state_delta": {},
            },
            {
                "author": AGENT_NAME,
                "node_path": "single_agent_tool_node@1",
                "node_name": "single_agent_tool_node",
                "output": None,
                "role": "model",
                "text_parts": [DEFAULT_FINAL_TEXT],
                "function_calls": [],
                "function_responses": [],
                "has_state_delta": False,
                "state_delta": {},
            },
        ],
        request_records=[
            {"content_count": 1, "request_roles": ["user"], "request_texts": ["Please add 1 and 2."], "tool_declaration_count": 1, "function_response_names": []},
            {"content_count": 2, "request_roles": ["user", "tool"], "request_texts": ["Please add 1 and 2."], "tool_declaration_count": 1, "function_response_names": [TOOL_NAME]},
        ],
        session_state={},
    )

    assert payload["result"] == "success"
    assert payload["accepted_as_minimal_single_agent_tool_call"] is True
    assert payload["runner_app_name"] == APP_NAME
    assert payload["agent_name"] == AGENT_NAME
    assert payload["tool_name"] == TOOL_NAME
    assert payload["selected_runtime_path"] == SELECTED_RUNTIME_PATH
    assert payload["entered_tool_call_semantics"] is True
    assert payload["model_request_count"] == 2
    assert payload["tool_call_count"] == 1
    assert payload["tool_response_count"] == 1
    assert payload["tool_call_observed"] is True
    assert payload["tool_response_observed"] is True
    assert payload["tool_call_args"] == {"x": 1, "y": 2}
    assert payload["tool_response_payload"] == {"result": 3}
    assert payload["tool_result_value"] == 3
    assert payload["final_text_result"] == DEFAULT_FINAL_TEXT
    assert payload["duration_seconds"] == 1.2346


def test_build_failure_payload_keeps_boundary_warning() -> None:
    payload = build_failure_payload(
        started_at="2026-04-16T05:00:00Z",
        completed_at="2026-04-16T05:00:01Z",
        duration_seconds=0.25,
        input_text="Please add 1 and 2.",
        exc=RuntimeError("tool call path is rejected"),
    )

    assert payload["result"] == "failed"
    assert payload["accepted_as_minimal_single_agent_tool_call"] is False
    assert payload["error_type"] == "RuntimeError"
    assert payload["selected_runtime_path"] == SELECTED_RUNTIME_PATH
    assert "正式 agent/tool 承接层" in payload["boundary_judgement"]
