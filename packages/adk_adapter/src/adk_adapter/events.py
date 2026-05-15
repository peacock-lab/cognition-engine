"""Event capability skeletons for ADK adapter observability handoff."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from adk_adapter.event_mapper import AdkEventMapper
from adk_adapter.invocation_mapper import AdkInvocationBinding
from schemas.runtime import InvocationRef, RuntimeErrorRecord, RuntimeEvent, WorkflowRef


@dataclass(frozen=True)
class AdkEventFacts:
    """Runtime event facts produced from ADK events."""

    runtime_events: list[RuntimeEvent]
    error_records: list[RuntimeErrorRecord]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_observability_input(self) -> dict[str, Any]:
        """Return an observability-hub friendly event fact payload."""

        return {
            "events": self.runtime_events,
            "errors": self.error_records,
            "event_count": len(self.runtime_events),
            "error_count": len(self.error_records),
            "source": "adk_adapter.events",
            **self.metadata,
        }


class AdkEventFactsBuilder:
    """Build event trace facts with the first-batch event mapper."""

    def __init__(self, mapper: AdkEventMapper | None = None) -> None:
        self._mapper = mapper or AdkEventMapper()

    def build_from_events(
        self,
        events: Iterable[Any],
        *,
        invocation_ref: InvocationRef,
        workflow_ref: WorkflowRef | None = None,
        invocation_binding: AdkInvocationBinding | None = None,
    ) -> AdkEventFacts:
        """Map ADK events into RuntimeEvent and RuntimeErrorRecord facts."""

        runtime_events: list[RuntimeEvent] = []
        error_records: list[RuntimeErrorRecord] = []
        for event in events:
            runtime_events.append(
                self._mapper.map_event(
                    event,
                    invocation_ref=invocation_ref,
                    workflow_ref=workflow_ref,
                    invocation_binding=invocation_binding,
                )
            )
            error_record = self._mapper.map_error_record(
                event,
                invocation_ref=invocation_ref,
                workflow_ref=workflow_ref,
                invocation_binding=invocation_binding,
            )
            if error_record is not None:
                error_records.append(error_record)

        return AdkEventFacts(
            runtime_events=runtime_events,
            error_records=error_records,
            metadata={
                "candidate_target": "observability_hub.EventTrace",
                "complete_event_stream_service": False,
            },
        )
