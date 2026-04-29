"""ADK invocation context binding and summary helpers."""

from __future__ import annotations

from typing import Any, Dict, Optional

from google.adk.plugins.base_plugin import BasePlugin


class ProjectInvocationBindingPlugin(BasePlugin):
    """Bind the project invocation id onto ADK invocation context and events."""

    def __init__(self, *, invocation_id: str) -> None:
        super().__init__(name="ce_project_invocation_binding")
        self.invocation_id = invocation_id

    async def before_run_callback(self, *, invocation_context):
        invocation_context.invocation_id = self.invocation_id
        return None

    async def on_event_callback(self, *, invocation_context, event):
        del invocation_context
        if getattr(event, "invocation_id", None) == self.invocation_id:
            return None
        return event.model_copy(update={"invocation_id": self.invocation_id})


def build_invocation_binding_summary(
    *,
    project_invocation_id: Optional[str],
    adk_events: list[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build the control-plane invocation binding summary."""

    invocation_ids = adk_invocation_ids(adk_events)
    event_count = adk_invocation_event_count(adk_events)
    return {
        "project_invocation_id": project_invocation_id,
        "adk_invocation_id": invocation_ids[0] if len(invocation_ids) == 1 else None,
        "adk_invocation_ids": invocation_ids,
        "adk_invocation_event_count": event_count,
        "adk_invocation_missing_count": len(adk_events) - event_count,
        "adk_invocation_bound": adk_invocation_bound(
            project_invocation_id,
            adk_events,
        ),
        "adk_invocation_mismatch": adk_invocation_mismatch(
            project_invocation_id,
            adk_events,
        ),
    }


def adk_invocation_ids(adk_events: list[Dict[str, Any]]) -> list[str]:
    return sorted(
        {
            invocation_id
            for invocation_id in (
                event.get("adk_invocation_id") for event in adk_events
            )
            if invocation_id
        }
    )


def adk_invocation_event_count(adk_events: list[Dict[str, Any]]) -> int:
    return sum(1 for event in adk_events if event.get("adk_invocation_id"))


def adk_invocation_bound(
    project_invocation_id: Optional[str],
    adk_events: list[Dict[str, Any]],
) -> bool:
    return bool(
        project_invocation_id
        and adk_events
        and all(
            event.get("adk_invocation_id") == project_invocation_id
            for event in adk_events
        )
    )


def adk_invocation_mismatch(
    project_invocation_id: Optional[str],
    adk_events: list[Dict[str, Any]],
) -> bool:
    invocation_ids = adk_invocation_ids(adk_events)
    if not project_invocation_id or not invocation_ids:
        return False
    return any(invocation_id != project_invocation_id for invocation_id in invocation_ids)
