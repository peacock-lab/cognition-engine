from __future__ import annotations

from pathlib import Path

from engine.analyzer.run_adk_agent_runtime_result_minimal_capture import (
    DEFAULT_MOCK_RESPONSE_TEXT,
    ENTRY_ID,
    ENTRY_TYPE,
    OUTPUT_KEY,
    OUTPUTS_DIR,
    PROBE_REFERENCE,
    PROJECT_ROOT,
    build_parser,
    build_failure_payload,
    build_success_payload,
    resolve_output_path,
)


def test_resolve_output_path_defaults_to_agent_runtime_result_directory() -> None:
    output_path = resolve_output_path(None)

    assert output_path.parent == OUTPUTS_DIR
    assert output_path.name.startswith(f"{ENTRY_ID}-")
    assert output_path.suffix == ".json"


def test_resolve_output_path_accepts_relative_path() -> None:
    output_path = resolve_output_path("outputs/agent_runtime_result/manual.json")

    assert output_path == PROJECT_ROOT / "outputs" / "agent_runtime_result" / "manual.json"


def test_build_parser_accepts_mock_response_text_argument() -> None:
    parser = build_parser()

    args = parser.parse_args(["--mock-response-text", "unexpected-runtime-result"])

    assert args.mock_response_text == "unexpected-runtime-result"
    assert DEFAULT_MOCK_RESPONSE_TEXT == "hello-agent-runtime-result"


def test_build_parser_accepts_omit_agent_output_key_flag() -> None:
    parser = build_parser()

    args = parser.parse_args(["--omit-agent-output-key"])

    assert args.omit_agent_output_key is True


def test_build_success_payload_marks_formal_entry_boundary() -> None:
    output_path = PROJECT_ROOT / "outputs" / "agent_runtime_result" / "formal-entry.json"
    payload = build_success_payload(
        started_at="2026-04-17T03:00:00Z",
        completed_at="2026-04-17T03:00:01Z",
        duration_seconds=1.23456,
        input_text="hello-adk-agent-runtime-result",
        output_path=output_path,
        event_records=[
            {
                "author": "user",
                "node_path": None,
                "node_name": None,
                "output": None,
                "role": "user",
                "text_parts": ["hello-adk-agent-runtime-result"],
                "has_state_delta": False,
                "state_delta": {},
            },
            {
                "author": "agent_runtime_formal_entry",
                "node_path": "agent_runtime_formal_entry@1",
                "node_name": "agent_runtime_formal_entry",
                "output": None,
                "role": "model",
                "text_parts": ["hello-agent-runtime-result"],
                "has_state_delta": True,
                "state_delta": {OUTPUT_KEY: "hello-agent-runtime-result"},
            },
        ],
        session_state={OUTPUT_KEY: "hello-agent-runtime-result"},
        formal_output_written=False,
    )

    assert payload["result"] == "success"
    assert payload["entry_type"] == ENTRY_TYPE
    assert payload["probe_reference"] == PROBE_REFERENCE
    assert payload["output_file"] == "outputs/agent_runtime_result/formal-entry.json"
    assert payload["content_text_result"] == "hello-agent-runtime-result"
    assert payload["runtime_result_text"] == "hello-agent-runtime-result"
    assert payload["internal_observation"] == {
        "observed_node_names": ["agent_runtime_formal_entry"],
        "semantic_observation": {
            "entered_semantics": ["agent_runtime_result"],
            "observed_results": [],
        },
        "event_records": [
            {
                "author": "user",
                "role": "user",
                "output": None,
                "node_name": None,
                "has_state_delta": False,
                "state_delta": {},
            },
            {
                "author": "agent_runtime_formal_entry",
                "role": "model",
                "output": None,
                "node_name": "agent_runtime_formal_entry",
                "has_state_delta": True,
                "state_delta": {OUTPUT_KEY: "hello-agent-runtime-result"},
            },
        ],
    }
    assert payload["context_access"] == {
        "state_delta": {OUTPUT_KEY: "hello-agent-runtime-result"},
        "session_state": {OUTPUT_KEY: "hello-agent-runtime-result"},
    }
    assert payload["runner_execution"] == {
        "Runner": "Runner",
        "request_acceptance": True,
        "event_consumption": True,
        "append_progression": True,
        "response_return": True,
    }
    assert payload["state_delta"] == {OUTPUT_KEY: "hello-agent-runtime-result"}
    assert payload["session_state"] == {OUTPUT_KEY: "hello-agent-runtime-result"}
    assert payload["duration_seconds"] == 1.2346
    assert payload["entered_agent_runtime_semantics"] is True
    assert payload["runtime_result_captured"] is True
    assert payload["output_key_state_observed"] is True
    assert payload["formal_output_written"] is False
    assert "LlmAgent(single_turn) runtime result 捕获" in payload["boundary_judgement"]


def test_build_failure_payload_preserves_runtime_result_boundary() -> None:
    output_path = Path("/tmp/agent-runtime-result-failed.json")
    payload = build_failure_payload(
        started_at="2026-04-17T03:00:00Z",
        completed_at="2026-04-17T03:00:01Z",
        duration_seconds=0.12345,
        input_text="hello-adk-agent-runtime-result",
        output_path=output_path,
        exc=RuntimeError("missing output key"),
    )

    assert payload["result"] == "failed"
    assert payload["entry_type"] == ENTRY_TYPE
    assert payload["output_key"] == OUTPUT_KEY
    assert payload["error_type"] == "RuntimeError"
    assert payload["error_message"] == "missing output key"
    assert payload["output_file"] == str(output_path)
    assert payload["duration_seconds"] == 0.1235
    assert "不能把 probe 级最小承接结论一并推翻" in payload["boundary_judgement"]
