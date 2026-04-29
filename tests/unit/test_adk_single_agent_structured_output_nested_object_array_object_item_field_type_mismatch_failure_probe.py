#!/usr/bin/env python3
"""ADK 单 agent 结构化输出嵌套对象中的数组对象项字段类型不匹配失败路径最小验证脚本测试。"""

from pathlib import Path
from types import SimpleNamespace
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from engine.analyzer.probe_adk_single_agent_structured_output_nested_object_array_object_item_field_type_mismatch_failure import (  # noqa: E402
    AGENT_NAME,
    APP_NAME,
    EXPECTED_ERROR_FIELD,
    EXPECTED_ERROR_FRAGMENT,
    EXPECTED_ERROR_TYPE,
    INVALID_OUTPUT_JSON,
    INVALID_STRUCTURED_OUTPUT,
    OUTPUT_KEY,
    SELECTED_RUNTIME_PATH,
    build_failure_payload,
    build_success_payload,
    extract_node_name,
    serialize_event,
    serialize_llm_request,
)


def test_extract_node_name_strips_run_id() -> None:
    assert extract_node_name(
        "single_agent_structured_output_nested_object_array_object_item_field_type_mismatch_failure_node@1"
    ) == "single_agent_structured_output_nested_object_array_object_item_field_type_mismatch_failure_node"
    assert extract_node_name(
        "wf@1/single_agent_structured_output_nested_object_array_object_item_field_type_mismatch_failure_node@2"
    ) == "single_agent_structured_output_nested_object_array_object_item_field_type_mismatch_failure_node"
    assert extract_node_name(None) is None


def test_serialize_event_extracts_text_without_state_delta() -> None:
    event = SimpleNamespace(
        author=AGENT_NAME,
        output=None,
        content=SimpleNamespace(
            role="model",
            parts=[SimpleNamespace(text=INVALID_OUTPUT_JSON)],
        ),
        actions=SimpleNamespace(state_delta={}),
        node_info=SimpleNamespace(
            path="single_agent_structured_output_nested_object_array_object_item_field_type_mismatch_failure_node@1"
        ),
    )

    record = serialize_event(event)

    assert record["author"] == AGENT_NAME
    assert (
        record["node_name"]
        == "single_agent_structured_output_nested_object_array_object_item_field_type_mismatch_failure_node"
    )
    assert record["text_parts"] == [INVALID_OUTPUT_JSON]
    assert record["has_state_delta"] is False
    assert record["state_delta"] == {}


def test_serialize_llm_request_extracts_response_schema_metadata() -> None:
    llm_request = SimpleNamespace(
        contents=[
            SimpleNamespace(
                role="user",
                parts=[
                    SimpleNamespace(
                        text="Write a tiny story outline with metadata characters as structured output."
                    )
                ],
            )
        ],
        config=SimpleNamespace(
            response_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "tone": {"type": "string"},
                            "characters": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "role": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
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
    assert record["response_schema_properties"] == ["metadata", "title"]


def test_build_success_payload_marks_nested_object_array_object_item_failure_path_acceptance() -> None:
    payload = build_success_payload(
        started_at="2026-04-17T01:00:00Z",
        completed_at="2026-04-17T01:00:01Z",
        duration_seconds=1.23456,
        input_text="Write a tiny story outline with metadata characters as structured output.",
        adk_module_path="/tmp/google-adk/src/google/adk/__init__.py",
        error_type=EXPECTED_ERROR_TYPE,
        error_message=(
            "1 validation error for StoryWithMetadataCharactersOutput\n"
            "metadata.characters.1.name\n"
            "  Input should be a valid string [type=string_type, input_value=123, input_type=int]"
        ),
        event_records=[
            {
                "author": AGENT_NAME,
                "node_path": "single_agent_structured_output_nested_object_array_object_item_field_type_mismatch_failure_node@1",
                "node_name": "single_agent_structured_output_nested_object_array_object_item_field_type_mismatch_failure_node",
                "output": None,
                "role": "model",
                "text_parts": [INVALID_OUTPUT_JSON],
                "has_state_delta": False,
                "state_delta": {},
            }
        ],
        request_records=[
            {
                "content_count": 1,
                "request_roles": ["user"],
                "request_texts": [
                    "Write a tiny story outline with metadata characters as structured output."
                ],
                "has_response_schema": True,
                "response_schema_type": "StoryWithMetadataCharactersOutput",
                "response_mime_type": "application/json",
                "response_schema_properties": ["metadata", "title"],
            }
        ],
        session_state={},
    )

    assert payload["result"] == "success"
    assert (
        payload[
            "accepted_as_minimal_single_agent_structured_output_nested_object_array_object_item_field_type_mismatch_failure_path"
        ]
        is True
    )
    assert payload["runner_app_name"] == APP_NAME
    assert payload["agent_name"] == AGENT_NAME
    assert payload["output_key"] == OUTPUT_KEY
    assert payload["selected_runtime_path"] == SELECTED_RUNTIME_PATH
    assert payload["expected_error_type"] == EXPECTED_ERROR_TYPE
    assert payload["expected_error_field"] == EXPECTED_ERROR_FIELD
    assert payload["expected_error_fragment"] == EXPECTED_ERROR_FRAGMENT
    assert payload["invalid_structured_output_payload"] == INVALID_STRUCTURED_OUTPUT
    assert payload[
        "entered_schema_nested_object_array_object_item_field_type_mismatch_failure_semantics"
    ] is True
    assert payload["nested_object_array_object_item_field_type_mismatch_failure_observed"] is True
    assert payload["response_schema_request_count"] == 1
    assert payload["state_delta_write_observed"] is False
    assert payload["session_state_write_observed"] is False
    assert payload["duration_seconds"] == 1.2346


def test_build_failure_payload_keeps_boundary_warning() -> None:
    payload = build_failure_payload(
        started_at="2026-04-17T01:00:00Z",
        completed_at="2026-04-17T01:00:01Z",
        duration_seconds=0.25,
        input_text="Write a tiny story outline with metadata characters as structured output.",
        exc=RuntimeError(
            "schema nested object array object item field type mismatch validation was not observed"
        ),
    )

    assert payload["result"] == "failed"
    assert (
        payload[
            "accepted_as_minimal_single_agent_structured_output_nested_object_array_object_item_field_type_mismatch_failure_path"
        ]
        is False
    )
    assert payload["error_type"] == "RuntimeError"
    assert payload["selected_runtime_path"] == SELECTED_RUNTIME_PATH
    assert "schema 嵌套对象中的数组对象项字段类型不匹配失败承接层" in payload["boundary_judgement"]
