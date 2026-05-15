"""Legacy artifact fact skeletons for ADK adapter observability handoff.

These objects are retained as 078-era observability candidates. They are not an
ADK ArtifactService adapter, not a runtime_container assembly entrypoint, and
not a source for public contract promotion by themselves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from adk_adapter.artifact_mapper import AdkArtifactMapper
from adk_adapter.invocation_mapper import AdkInvocationBinding
from schemas.runtime import ArtifactDelta, InvocationRef


@dataclass(frozen=True)
class AdkArtifactFacts:
    """Artifact facts produced from ADK event actions."""

    artifact_deltas: list[ArtifactDelta]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_observability_input(self) -> dict[str, Any]:
        """Return an observability-hub friendly artifact fact payload."""

        return {
            "artifact_deltas": self.artifact_deltas,
            "artifact_delta_count": len(self.artifact_deltas),
            "source": "adk_adapter.artifacts",
            **self.metadata,
        }


class AdkArtifactFactsBuilder:
    """Build legacy artifact facts with the first-batch artifact mapper."""

    def __init__(self, mapper: AdkArtifactMapper | None = None) -> None:
        self._mapper = mapper or AdkArtifactMapper()

    def build_from_events(
        self,
        events: Iterable[Any],
        *,
        invocation_ref: InvocationRef,
        invocation_binding: AdkInvocationBinding | None = None,
    ) -> AdkArtifactFacts:
        """Map ADK events into ArtifactDelta facts for observability_hub."""

        artifact_deltas = [
            artifact_delta
            for event in events
            for artifact_delta in self._mapper.map_event_artifact_deltas(
                event,
                invocation_ref=invocation_ref,
                invocation_binding=invocation_binding,
            )
        ]
        return AdkArtifactFacts(
            artifact_deltas=artifact_deltas,
            metadata={
                "candidate_target": "observability_hub.ArtifactManifest",
                "complete_artifact_service": False,
            },
        )
