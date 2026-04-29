#!/usr/bin/env python3
"""ADK runtime 最小接入验证脚本测试。"""

from pathlib import Path
from types import SimpleNamespace
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from engine.analyzer.probe_adk_runtime import (  # noqa: E402
    APP_NAME,
    build_failure_payload,
    build_success_payload,
    serialize_event,
)


def test_serialize_event_extracts_output_and_state_delta() -> None:
    event = SimpleNamespace(
        author="echo_probe",
        output="Echo: hello-adk",
        content=SimpleNamespace(role="model"),
        actions=SimpleNamespace(state_delta={"probe": "ok"}),
    )

    record = serialize_event(event)

    assert record["author"] == "echo_probe"
    assert record["output"] == "Echo: hello-adk"
    assert record["role"] == "model"
    assert record["has_state_delta"] is True
    assert record["state_delta"] == {"probe": "ok"}


def test_build_success_payload_marks_minimal_acceptance() -> None:
    payload = build_success_payload(
        started_at="2026-04-16T02:00:00Z",
        completed_at="2026-04-16T02:00:01Z",
        duration_seconds=1.23456,
        input_text="hello-adk",
        adk_module_path="/tmp/google-adk/src/google/adk/__init__.py",
        event_records=[
            {
                "author": "echo_probe",
                "output": "Echo: hello-adk",
                "role": "model",
                "has_state_delta": True,
                "state_delta": {"probe": "ok"},
            }
        ],
        persisted_outputs=["Echo: hello-adk"],
    )

    assert payload["result"] == "success"
    assert payload["accepted_as_minimal_base"] is True
    assert payload["runner_app_name"] == APP_NAME
    assert payload["output_text"] == "Echo: hello-adk"
    assert payload["state_delta_observed"] is True
    assert payload["state_delta"] == {"probe": "ok"}
    assert payload["persisted_outputs"] == ["Echo: hello-adk"]
    assert payload["duration_seconds"] == 1.2346


def test_build_failure_payload_keeps_boundary_warning() -> None:
    payload = build_failure_payload(
        started_at="2026-04-16T02:00:00Z",
        completed_at="2026-04-16T02:00:01Z",
        duration_seconds=0.25,
        input_text="hello-adk",
        exc=RuntimeError("google.adk import failed"),
    )

    assert payload["result"] == "failed"
    assert payload["accepted_as_minimal_base"] is False
    assert payload["error_type"] == "RuntimeError"
    assert "不能把邻仓依赖调用误写成认知引擎正式底座接入" in payload["boundary_judgement"]
