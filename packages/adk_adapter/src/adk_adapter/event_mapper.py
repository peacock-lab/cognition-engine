"""Map Google ADK events to Cognition Engine runtime events."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from adk_adapter.invocation_mapper import AdkInvocationBinding
from schemas.runtime import (
    InvocationRef,
    NodeRef,
    RuntimeErrorRecord,
    RuntimeEvent,
    RuntimeEventType,
    WorkflowRef,
)


class AdkEventMapper:
    """Convert ADK event-like objects into public RuntimeEvent schemas."""

    def map_event(
        self,
        event: Any,
        *,
        invocation_ref: InvocationRef,
        workflow_ref: WorkflowRef | None = None,
        invocation_binding: AdkInvocationBinding | None = None,
    ) -> RuntimeEvent:
        """Map one ADK Event into a RuntimeEvent."""

        event_id = str(getattr(event, "id", None) or f"adk-event-{uuid4().hex}")
        node_path = self._node_path(event)
        error_code = getattr(event, "error_code", None)
        error_message = getattr(event, "error_message", None)
        actions = getattr(event, "actions", None)

        payload = {
            "content": self._plain(getattr(event, "content", None)),
            "output": self._plain(getattr(event, "output", None)),
            "state_delta": self._plain(getattr(actions, "state_delta", None)),
            "artifact_delta": self._plain(getattr(actions, "artifact_delta", None)),
            "agent_state": self._plain(getattr(actions, "agent_state", None)),
            "route": self._plain(getattr(actions, "route", None)),
        }

        metadata = {
            "adk_event_id": event_id,
            "adk_invocation_id": getattr(event, "invocation_id", None),
            "author": getattr(event, "author", None),
            "node_path": node_path,
            "error_code": error_code,
            "error_message": error_message,
        }
        if invocation_binding is not None:
            metadata["adk_invocation_binding"] = invocation_binding.to_metadata()

        return RuntimeEvent(
            event_id=event_id,
            event_type=self._event_type(event, node_path=node_path),
            invocation_ref=invocation_ref,
            workflow_ref=workflow_ref,
            node_ref=self._node_ref(node_path),
            timestamp=self._timestamp(getattr(event, "timestamp", None)),
            payload=payload,
            metadata=metadata,
        )

    def map_error_record(
        self,
        event: Any,
        *,
        invocation_ref: InvocationRef,
        workflow_ref: WorkflowRef | None = None,
        invocation_binding: AdkInvocationBinding | None = None,
    ) -> RuntimeErrorRecord | None:
        """Return a RuntimeErrorRecord when an ADK Event carries error fields."""

        error_code = getattr(event, "error_code", None)
        error_message = getattr(event, "error_message", None)
        if not error_code and not error_message:
            return None

        metadata: dict[str, Any] = {
            "adk_event_id": getattr(event, "id", None),
            "adk_invocation_id": getattr(event, "invocation_id", None),
            "author": getattr(event, "author", None),
            "node_path": self._node_path(event),
        }
        if invocation_binding is not None:
            metadata["adk_invocation_binding"] = invocation_binding.to_metadata()

        return RuntimeErrorRecord(
            error_id=f"adk-event-error-{getattr(event, 'id', None) or uuid4().hex}",
            error_type=str(error_code or "adk_event_error"),
            message=str(error_message or error_code or "ADK event error"),
            recoverable=False,
            invocation_ref=invocation_ref,
            workflow_ref=workflow_ref,
            node_ref=self._node_ref(self._node_path(event)),
            metadata=metadata,
        )

    def _event_type(self, event: Any, *, node_path: str | None) -> RuntimeEventType:
        if getattr(event, "error_code", None) or getattr(event, "error_message", None):
            return RuntimeEventType.NODE_FAILED if node_path else RuntimeEventType.RUNTIME_FAILED
        if node_path:
            return RuntimeEventType.NODE_COMPLETED
        return RuntimeEventType.WORKFLOW_STARTED

    def _node_path(self, event: Any) -> str | None:
        node_info = getattr(event, "node_info", None)
        path = getattr(node_info, "path", None)
        if path:
            return str(path)
        return None

    def _node_ref(self, node_path: str | None) -> NodeRef | None:
        if not node_path:
            return None
        node_id = node_path.split("/")[-1] or node_path
        return NodeRef(node_id=node_id, name=node_id, source="adk", metadata={"path": node_path})

    def _timestamp(self, value: Any) -> str | None:
        if value is None:
            return None
        if hasattr(value, "isoformat"):
            return value.isoformat().replace("+00:00", "Z")
        return str(value)

    def _plain(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool, list, tuple, dict)):
            return value
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if hasattr(value, "dict"):
            return value.dict()
        return repr(value)
