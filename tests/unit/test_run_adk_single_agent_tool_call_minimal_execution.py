from __future__ import annotations

from pathlib import Path

from engine.analyzer.run_adk_single_agent_tool_call_minimal_execution import (
    AGENT_MODE,
    DEFAULT_TOOL_ARGS,
    ENTRY_ID,
    ENTRY_TYPE,
    OUTPUTS_DIR,
    PROBE_REFERENCE,
    PROJECT_ROOT,
    TOOL_NAME,
    build_parser,
    build_failure_payload,
    build_success_payload,
    resolve_output_path,
)


def test_resolve_output_path_defaults_to_single_agent_tool_call_directory() -> None:
    output_path = resolve_output_path(None)

    assert output_path.parent == OUTPUTS_DIR
    assert output_path.name.startswith(f"{ENTRY_ID}-")
    assert output_path.suffix == ".json"


def test_resolve_output_path_accepts_relative_path() -> None:
    output_path = resolve_output_path("outputs/single_agent_tool_call/manual.json")

    assert output_path == PROJECT_ROOT / "outputs" / "single_agent_tool_call" / "manual.json"


def test_build_parser_accepts_output_file_argument() -> None:
    parser = build_parser()

    args = parser.parse_args(["--output-file", "outputs/single_agent_tool_call/manual.json"])

    assert args.output_file == "outputs/single_agent_tool_call/manual.json"


def test_build_success_payload_marks_tool_call_formal_entry_boundary() -> None:
    output_path = PROJECT_ROOT / "outputs" / "single_agent_tool_call" / "formal-entry.json"
    payload = build_success_payload(
        started_at="2026-04-17T08:00:00Z",
        completed_at="2026-04-17T08:00:01Z",
        duration_seconds=1.23456,
        input_text="Please add 1 and 2.",
        output_path=output_path,
        event_records=[
            {
                "author": "single_agent_tool_formal_entry",
                "node_path": "single_agent_tool_formal_entry@1",
                "node_name": "single_agent_tool_formal_entry",
                "output": None,
                "role": "model",
                "text_parts": [],
                "function_calls": [{"id": "fc-1", "name": TOOL_NAME, "args": DEFAULT_TOOL_ARGS}],
                "function_responses": [],
                "has_state_delta": False,
                "state_delta": {},
            },
            {
                "author": "single_agent_tool_formal_entry",
                "node_path": "single_agent_tool_formal_entry@1",
                "node_name": "single_agent_tool_formal_entry",
                "output": None,
                "role": "tool",
                "text_parts": [],
                "function_calls": [],
                "function_responses": [{"id": "fc-1", "name": TOOL_NAME, "response": {"result": 3}}],
                "has_state_delta": False,
                "state_delta": {},
            },
            {
                "author": "single_agent_tool_formal_entry",
                "node_path": "single_agent_tool_formal_entry@1",
                "node_name": "single_agent_tool_formal_entry",
                "output": None,
                "role": "model",
                "text_parts": ["Result is 3."],
                "function_calls": [],
                "function_responses": [],
                "has_state_delta": False,
                "state_delta": {},
            },
        ],
        session_state={},
        formal_output_written=False,
    )

    assert payload["result"] == "success"
    assert payload["entry_type"] == ENTRY_TYPE
    assert payload["probe_reference"] == PROBE_REFERENCE
    assert payload["output_file"] == "outputs/single_agent_tool_call/formal-entry.json"
    assert payload["agent_mode"] == AGENT_MODE
    assert payload["tool_name"] == TOOL_NAME
    assert payload["tool_call_args"] == DEFAULT_TOOL_ARGS
    assert payload["tool_response_payload"] == {"result": 3}
    assert payload["tool_result_value"] == 3
    assert payload["final_text_result"] == "Result is 3."
    assert payload["internal_observation"] == {
        "observed_node_names": ["single_agent_tool_formal_entry"],
        "semantic_observation": {
            "entered_semantics": ["tool_call"],
            "observed_results": ["tool_call", "tool_response"],
        },
        "event_records": [
            {
                "author": "single_agent_tool_formal_entry",
                "role": "model",
                "output": None,
                "node_name": "single_agent_tool_formal_entry",
                "has_state_delta": False,
                "state_delta": {},
            },
            {
                "author": "single_agent_tool_formal_entry",
                "role": "tool",
                "output": None,
                "node_name": "single_agent_tool_formal_entry",
                "has_state_delta": False,
                "state_delta": {},
            },
            {
                "author": "single_agent_tool_formal_entry",
                "role": "model",
                "output": None,
                "node_name": "single_agent_tool_formal_entry",
                "has_state_delta": False,
                "state_delta": {},
            },
        ],
    }
    assert payload["context_access"] == {
        "state_delta": {},
        "session_state": {},
    }
    assert payload["runner_execution"] == {
        "Runner": "Runner",
        "request_acceptance": True,
        "event_consumption": True,
        "append_progression": True,
        "response_return": True,
    }
    assert payload["state_delta"] == {}
    assert payload["session_state"] == {}
    assert payload["duration_seconds"] == 1.2346
    assert payload["entered_tool_call_semantics"] is True
    assert payload["tool_call_observed"] is True
    assert payload["tool_response_observed"] is True
    assert payload["formal_output_written"] is False
    assert "LlmAgent(mode='chat', tools=[add])" in payload["boundary_judgement"]


def test_build_failure_payload_preserves_formal_entry_boundary() -> None:
    output_path = Path("/tmp/single-agent-tool-call-failed.json")
    payload = build_failure_payload(
        started_at="2026-04-17T08:00:00Z",
        completed_at="2026-04-17T08:00:01Z",
        duration_seconds=0.12345,
        input_text="Please add 1 and 2.",
        output_path=output_path,
        exc=RuntimeError("tool response missing"),
    )

    assert payload["result"] == "failed"
    assert payload["entry_type"] == ENTRY_TYPE
    assert payload["tool_name"] == TOOL_NAME
    assert payload["error_type"] == "RuntimeError"
    assert payload["error_message"] == "tool response missing"
    assert payload["output_file"] == str(output_path)
    assert payload["duration_seconds"] == 0.1235
    assert "不能把 probe 级最小承接结论一并推翻" in payload["boundary_judgement"]
