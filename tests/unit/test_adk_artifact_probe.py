#!/usr/bin/env python3
"""ADK artifact 最小接入验证脚本测试。"""

from pathlib import Path
from types import SimpleNamespace
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from engine.analyzer.probe_adk_artifact import (  # noqa: E402
    APP_NAME,
    ARTIFACT_NAME,
    DEFAULT_ARTIFACT_TEXT,
    NODE_NAME,
    SELECTED_RUNTIME_PATH,
    build_failure_payload,
    build_success_payload,
    extract_node_name,
    merge_artifact_deltas,
    serialize_event,
)


def test_extract_node_name_strips_run_id() -> None:
    assert extract_node_name("artifact_probe@1") == "artifact_probe"
    assert extract_node_name("wf@1/artifact_probe@2") == "artifact_probe"
    assert extract_node_name(None) is None


def test_serialize_event_extracts_artifact_delta() -> None:
    event = SimpleNamespace(
        author=NODE_NAME,
        output="artifact:hello-artifact",
        content=SimpleNamespace(
            role="model",
            parts=[SimpleNamespace(text="artifact:hello-artifact")],
        ),
        actions=SimpleNamespace(
            state_delta={"artifact_loaded_text": DEFAULT_ARTIFACT_TEXT},
            artifact_delta={ARTIFACT_NAME: 0},
        ),
        node_info=SimpleNamespace(path="artifact_probe@1"),
    )

    record = serialize_event(event)

    assert record["author"] == NODE_NAME
    assert record["node_name"] == "artifact_probe"
    assert record["text_parts"] == ["artifact:hello-artifact"]
    assert record["has_state_delta"] is True
    assert record["state_delta"] == {"artifact_loaded_text": DEFAULT_ARTIFACT_TEXT}
    assert record["has_artifact_delta"] is True
    assert record["artifact_delta"] == {ARTIFACT_NAME: 0}


def test_merge_artifact_deltas_collects_latest_versions() -> None:
    merged = merge_artifact_deltas(
        [
            {"artifact_delta": {"artifact-a.txt": 0}},
            {"artifact_delta": {"artifact-a.txt": 1, ARTIFACT_NAME: 0}},
        ]
    )

    assert merged == {"artifact-a.txt": 1, ARTIFACT_NAME: 0}


def test_build_success_payload_marks_artifact_access_acceptance() -> None:
    payload = build_success_payload(
        started_at="2026-04-17T01:00:00Z",
        completed_at="2026-04-17T01:00:01Z",
        duration_seconds=1.23456,
        input_text="hello-adk-artifact",
        adk_module_path="/tmp/google-adk/src/google/adk/__init__.py",
        event_records=[
            {
                "author": NODE_NAME,
                "node_path": "artifact_probe@1",
                "node_name": NODE_NAME,
                "output": "artifact:hello-artifact",
                "role": "model",
                "text_parts": ["artifact:hello-artifact"],
                "has_state_delta": True,
                "state_delta": {
                    "artifact_saved_version": 0,
                    "artifact_loaded_text": DEFAULT_ARTIFACT_TEXT,
                    "artifact_keys": [ARTIFACT_NAME],
                },
                "has_artifact_delta": True,
                "artifact_delta": {ARTIFACT_NAME: 0},
            }
        ],
        session_state={
            "artifact_saved_version": 0,
            "artifact_loaded_text": DEFAULT_ARTIFACT_TEXT,
            "artifact_keys": [ARTIFACT_NAME],
        },
        artifact_keys=[ARTIFACT_NAME],
        loaded_artifact_text=DEFAULT_ARTIFACT_TEXT,
    )

    assert payload["result"] == "success"
    assert payload["accepted_as_minimal_artifact_access"] is True
    assert payload["runner_app_name"] == APP_NAME
    assert payload["node_name"] == NODE_NAME
    assert payload["artifact_name"] == ARTIFACT_NAME
    assert payload["selected_runtime_path"] == SELECTED_RUNTIME_PATH
    assert payload["artifact_saved"] is True
    assert payload["artifact_loaded"] is True
    assert payload["artifact_listed"] is True
    assert payload["artifact_version"] == 0
    assert payload["artifact_keys"] == [ARTIFACT_NAME]
    assert payload["loaded_artifact_text"] == DEFAULT_ARTIFACT_TEXT
    assert payload["artifact_delta_observed"] is True
    assert payload["artifact_delta"] == {ARTIFACT_NAME: 0}
    assert payload["duration_seconds"] == 1.2346


def test_build_failure_payload_keeps_boundary_warning() -> None:
    payload = build_failure_payload(
        started_at="2026-04-17T01:00:00Z",
        completed_at="2026-04-17T01:00:01Z",
        duration_seconds=0.25,
        input_text="hello-adk-artifact",
        exc=RuntimeError("artifact service unavailable"),
    )

    assert payload["result"] == "failed"
    assert payload["accepted_as_minimal_artifact_access"] is False
    assert payload["artifact_name"] == ARTIFACT_NAME
    assert payload["selected_runtime_path"] == SELECTED_RUNTIME_PATH
    assert payload["error_type"] == "RuntimeError"
    assert "正式 artifact 接入" in payload["boundary_judgement"]
