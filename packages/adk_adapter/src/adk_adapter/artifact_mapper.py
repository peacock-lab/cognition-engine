"""Artifact delta boundary mapping for Google ADK event actions."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from adk_adapter.invocation_mapper import AdkInvocationBinding
from schemas.runtime import ArtifactDelta, ArtifactRef, DeltaOperation, InvocationRef


class AdkArtifactMapper:
    """Map EventActions.artifact_delta into ArtifactDelta candidates."""

    def map_event_artifact_deltas(
        self,
        event: Any,
        *,
        invocation_ref: InvocationRef,
        invocation_binding: AdkInvocationBinding | None = None,
    ) -> list[ArtifactDelta]:
        """Extract artifact delta candidates from one ADK event."""

        actions = getattr(event, "actions", None)
        artifact_delta = getattr(actions, "artifact_delta", None)
        if not artifact_delta:
            return []

        if isinstance(artifact_delta, dict):
            items = artifact_delta.items()
        else:
            items = [("artifact_delta", artifact_delta)]

        deltas: list[ArtifactDelta] = []
        for name, value in items:
            artifact_id = str(name)
            metadata = {
                "adk_event_id": getattr(event, "id", None),
                "adk_invocation_id": getattr(event, "invocation_id", None),
                "raw_artifact_delta": self._plain(value),
            }
            if invocation_binding is not None:
                metadata["adk_invocation_binding"] = invocation_binding.to_metadata()

            deltas.append(
                ArtifactDelta(
                    delta_id=f"adk-artifact-delta-{uuid4().hex}",
                    invocation_ref=invocation_ref,
                    artifact_ref=ArtifactRef(
                        artifact_id=artifact_id,
                        name=artifact_id,
                        metadata={"source": "adk_event_actions"},
                    ),
                    operation=DeltaOperation.UPDATE,
                    metadata=metadata,
                )
            )
        return deltas

    def _plain(self, value: Any) -> Any:
        if isinstance(value, (str, int, float, bool, list, tuple, dict)) or value is None:
            return value
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        return repr(value)
