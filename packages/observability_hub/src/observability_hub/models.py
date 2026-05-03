"""Local observability-hub models for first-batch intake."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ObservabilityBaseModel(BaseModel):
    """Base model for observability-hub local schemas."""

    model_config = ConfigDict(extra="forbid")


class InvocationBindingRecord(ObservabilityBaseModel):
    """Invocation binding facts preserved from runtime metadata."""

    requested_invocation_id: str | None = None
    actual_invocation_id: str | None = None
    adk_invocation_id: str | None = None
    session_id: str | None = None
    app_name: str | None = None
    user_id: str | None = None
    workflow_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunRecord(ObservabilityBaseModel):
    """Summary facts for one runtime execution."""

    runtime_id: str
    status: str
    workflow_id: str | None = None
    adapter_name: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    event_count: int = 0
    error_count: int = 0
    artifact_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class EventTrace(ObservabilityBaseModel):
    """Best-effort event chain extracted from standard runtime facts."""

    events: list[dict[str, Any]] = Field(default_factory=list)
    event_count: int = 0
    node_paths: list[str] = Field(default_factory=list)
    authors: list[str] = Field(default_factory=list)
    has_error: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactManifest(ObservabilityBaseModel):
    """Best-effort artifact summary extracted from runtime facts."""

    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    artifact_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceBundle(ObservabilityBaseModel):
    """Candidate observation bundle built from one runtime result."""

    bundle_id: str
    source_type: str
    runtime_id: str
    workflow_id: str | None = None
    invocation: InvocationBindingRecord | None = None
    run_record: RunRecord
    event_trace: EventTrace
    artifact_manifest: ArtifactManifest
    errors: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
