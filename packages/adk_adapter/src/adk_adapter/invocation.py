"""Invocation and context capability skeletons for ADK adapter handoff."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from adk_adapter.invocation_mapper import AdkInvocationBinding, AdkInvocationMapper
from schemas.runtime import InvocationRef, WorkflowRef


@dataclass(frozen=True)
class AdkInvocationContextFacts:
    """Invocation and workflow context facts from an ADK run."""

    invocation_ref: InvocationRef
    invocation_binding: AdkInvocationBinding
    workflow_ref: WorkflowRef | None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_observability_input(self) -> dict[str, Any]:
        """Return context facts intended for observability_hub intake."""

        return {
            "invocation_ref": self.invocation_ref,
            "workflow_ref": self.workflow_ref,
            "adk_invocation_binding": self.invocation_binding.to_metadata(),
            "source": "adk_adapter.invocation",
            **self.metadata,
        }


class AdkInvocationContextBuilder:
    """Build invocation context facts with the first-batch invocation mapper."""

    def __init__(self, mapper: AdkInvocationMapper | None = None) -> None:
        self._mapper = mapper or AdkInvocationMapper()

    def build_from_events(
        self,
        *,
        requested_invocation_ref: InvocationRef,
        events: Iterable[Any],
        workflow_ref: WorkflowRef | None = None,
        session_id: str | None = None,
        app_name: str | None = None,
        user_id: str | None = None,
    ) -> AdkInvocationContextFacts:
        """Build invocation context facts without bypassing observability_hub."""

        binding = self._mapper.bind_from_events(
            requested_invocation_id=requested_invocation_ref.invocation_id,
            events=events,
            session_id=session_id,
            app_name=app_name,
            user_id=user_id,
            workflow_id=workflow_ref.workflow_id if workflow_ref is not None else None,
        )
        invocation_ref = self._mapper.merge_into_invocation_ref(
            requested_invocation_ref,
            binding,
        )
        return AdkInvocationContextFacts(
            invocation_ref=invocation_ref,
            invocation_binding=binding,
            workflow_ref=workflow_ref,
            metadata={
                "candidate_target": "observability_hub.InvocationBindingRecord",
                "governance_context_source": "EvidenceBundle.invocation",
            },
        )
