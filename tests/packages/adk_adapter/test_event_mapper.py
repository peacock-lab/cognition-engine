from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from adk_adapter.event_mapper import AdkEventMapper
from adk_adapter.invocation_mapper import AdkInvocationBinding
from schemas.runtime import InvocationRef, RuntimeEventType, WorkflowRef


def test_event_mapper_maps_adk_event_fields_to_runtime_event() -> None:
    mapper = AdkEventMapper()
    event = SimpleNamespace(
        id="event-001",
        invocation_id="adk-actual-001",
        author="minimal_node",
        branch="main",
        node_info=SimpleNamespace(path="workflow@1/minimal_node@1"),
        timestamp=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
        content={"parts": [{"text": "hello"}]},
        output={"ok": True},
        actions=SimpleNamespace(
            state_delta={"stage": "done"},
            artifact_delta={"artifact.md": 1},
            agent_state={"status": "ready"},
            route="next",
        ),
        error_code=None,
        error_message=None,
    )

    runtime_event = mapper.map_event(
        event,
        invocation_ref=InvocationRef(invocation_id="requested-001"),
        workflow_ref=WorkflowRef(workflow_id="workflow-001"),
        invocation_binding=AdkInvocationBinding(
            requested_invocation_id="requested-001",
            adk_invocation_id="adk-actual-001",
        ),
    )

    assert runtime_event.event_id == "event-001"
    assert runtime_event.event_type == RuntimeEventType.NODE_COMPLETED
    assert runtime_event.invocation_ref.invocation_id == "requested-001"
    assert runtime_event.node_ref is not None
    assert runtime_event.node_ref.metadata["path"] == "workflow@1/minimal_node@1"
    assert runtime_event.timestamp == "2026-05-01T12:00:00Z"
    assert runtime_event.payload["output"] == {"ok": True}
    assert runtime_event.payload["state_delta"] == {"stage": "done"}
    assert runtime_event.payload["artifact_delta"] == {"artifact.md": 1}
    assert runtime_event.metadata["author"] == "minimal_node"
    assert runtime_event.metadata["branch"] == "main"
    assert runtime_event.metadata["adk_invocation_id"] == "adk-actual-001"


def test_event_mapper_maps_error_event_to_error_record() -> None:
    mapper = AdkEventMapper()
    event = SimpleNamespace(
        id="event-error-001",
        invocation_id="adk-actual-001",
        author="minimal_node",
        node_info=SimpleNamespace(path="workflow@1/minimal_node@1"),
        timestamp=None,
        content=None,
        output=None,
        actions=SimpleNamespace(state_delta={}, artifact_delta={}),
        error_code="sample_error",
        error_message="sample failed",
    )

    runtime_event = mapper.map_event(
        event,
        invocation_ref=InvocationRef(invocation_id="requested-001"),
        workflow_ref=WorkflowRef(workflow_id="workflow-001"),
    )
    error_record = mapper.map_error_record(
        event,
        invocation_ref=InvocationRef(invocation_id="requested-001"),
        workflow_ref=WorkflowRef(workflow_id="workflow-001"),
    )

    assert runtime_event.event_type == RuntimeEventType.NODE_FAILED
    assert runtime_event.metadata["error_code"] == "sample_error"
    assert error_record is not None
    assert error_record.error_type == "sample_error"
    assert error_record.message == "sample failed"
