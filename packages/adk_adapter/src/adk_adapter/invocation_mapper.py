"""Invocation identity mapping for Google ADK workflow runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from schemas.runtime import InvocationRef


@dataclass(frozen=True)
class AdkInvocationBinding:
    """Internal binding between requested and ADK-emitted invocation ids."""

    requested_invocation_id: str
    adk_invocation_id: str | None = None
    session_id: str | None = None
    app_name: str | None = None
    user_id: str | None = None
    workflow_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_metadata(self) -> dict[str, Any]:
        """Return a plain metadata representation for schema payloads."""

        return {
            "requested_invocation_id": self.requested_invocation_id,
            "adk_invocation_id": self.adk_invocation_id,
            "session_id": self.session_id,
            "app_name": self.app_name,
            "user_id": self.user_id,
            "workflow_id": self.workflow_id,
            **self.metadata,
        }


class AdkInvocationMapper:
    """Build ADK invocation bindings without changing public schemas."""

    def create_binding(
        self,
        *,
        requested_invocation_id: str,
        adk_invocation_id: str | None = None,
        session_id: str | None = None,
        app_name: str | None = None,
        user_id: str | None = None,
        workflow_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AdkInvocationBinding:
        """Create an internal binding object."""

        return AdkInvocationBinding(
            requested_invocation_id=requested_invocation_id,
            adk_invocation_id=adk_invocation_id,
            session_id=session_id,
            app_name=app_name,
            user_id=user_id,
            workflow_id=workflow_id,
            metadata=metadata or {},
        )

    def bind_from_events(
        self,
        *,
        requested_invocation_id: str,
        events: Iterable[Any],
        session_id: str | None = None,
        app_name: str | None = None,
        user_id: str | None = None,
        workflow_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AdkInvocationBinding:
        """Create a binding from ADK events, preserving the first emitted id."""

        adk_invocation_id = None
        for event in events:
            value = getattr(event, "invocation_id", None)
            if value:
                adk_invocation_id = str(value)
                break

        return self.create_binding(
            requested_invocation_id=requested_invocation_id,
            adk_invocation_id=adk_invocation_id,
            session_id=session_id,
            app_name=app_name,
            user_id=user_id,
            workflow_id=workflow_id,
            metadata=metadata,
        )

    def merge_into_invocation_ref(
        self,
        invocation_ref: InvocationRef,
        binding: AdkInvocationBinding,
    ) -> InvocationRef:
        """Return an InvocationRef with ADK binding metadata attached."""

        return InvocationRef(
            invocation_id=invocation_ref.invocation_id,
            runtime_id=invocation_ref.runtime_id,
            workflow_id=invocation_ref.workflow_id,
            source=invocation_ref.source,
            metadata={
                **invocation_ref.metadata,
                "adk_invocation_binding": binding.to_metadata(),
            },
        )
