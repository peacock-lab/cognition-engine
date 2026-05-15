"""Internal platform-chain debug summaries for ADK adapter handoff.

This module is not the formal observability path. ADK facts must flow through
the capability modules and observability_hub before cognition_governance uses
them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import metadata as importlib_metadata
from typing import Any

from schemas.runtime import WorkflowResult


@dataclass(frozen=True)
class AdkPlatformChainFacts:
    """Debug summary facts emitted by the ADK adapter platform skeleton."""

    workflow_id: str
    status: str
    requested_invocation_id: str | None
    adk_invocation_id: str | None
    session_id: str | None
    app_name: str | None
    user_id: str | None
    event_count: int
    artifact_delta_count: int
    error_count: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_metadata(self) -> dict[str, Any]:
        """Return plain metadata suitable for observability handoff."""

        return {
            "adapter": "adk_adapter",
            "workflow_id": self.workflow_id,
            "status": self.status,
            "requested_invocation_id": self.requested_invocation_id,
            "adk_invocation_id": self.adk_invocation_id,
            "session_id": self.session_id,
            "app_name": self.app_name,
            "user_id": self.user_id,
            "event_count": self.event_count,
            "artifact_delta_count": self.artifact_delta_count,
            "error_count": self.error_count,
            **self.metadata,
        }


@dataclass(frozen=True)
class AdkLocalModelBoundary:
    """Local model boundary facts without performing model calls."""

    route: str
    local_model: str
    adk_version: str | None
    litellm_version: str | None
    runtime_call_performed: bool
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        """Return the boundary as plain metadata."""

        return {
            "route": self.route,
            "local_model": self.local_model,
            "adk_version": self.adk_version,
            "litellm_version": self.litellm_version,
            "runtime_call_performed": self.runtime_call_performed,
            "notes": list(self.notes),
        }


def build_adk_platform_chain_facts(workflow_result: WorkflowResult) -> AdkPlatformChainFacts:
    """Summarize an ADK-backed WorkflowResult for downstream evidence intake."""

    binding = workflow_result.metadata.get("adk_invocation_binding", {})
    return AdkPlatformChainFacts(
        workflow_id=workflow_result.workflow_ref.workflow_id,
        status=workflow_result.status.value,
        requested_invocation_id=workflow_result.metadata.get("requested_invocation_id")
        or binding.get("requested_invocation_id"),
        adk_invocation_id=workflow_result.metadata.get("adk_invocation_id")
        or binding.get("adk_invocation_id"),
        session_id=workflow_result.metadata.get("session_id") or binding.get("session_id"),
        app_name=workflow_result.metadata.get("app_name") or binding.get("app_name"),
        user_id=workflow_result.metadata.get("user_id") or binding.get("user_id"),
        event_count=len(workflow_result.events),
        artifact_delta_count=len(workflow_result.artifact_deltas),
        error_count=len(workflow_result.errors),
        metadata={
            "producer": "adk_adapter",
            "handoff_target": "observability_hub",
            "skeleton_stage": "v0.6.0-adk-adapter-second-batch",
        },
    )


def describe_litellm_ollama_boundary(local_model: str = "gemma4") -> AdkLocalModelBoundary:
    """Describe the local model route without invoking LiteLLM, Ollama, or ADK."""

    adk_version = _installed_version("google-adk")
    litellm_version = _installed_version("litellm")
    notes = [
        "Ollama local models should enter through ADK ecosystem LiteLLM routing.",
        "cognition_governance must consume model facts as evidence, not call models directly.",
    ]
    if litellm_version is None:
        notes.append("litellm is not installed in this workspace; runtime model call is deferred.")

    return AdkLocalModelBoundary(
        route="adk_adapter.litellm_ollama",
        local_model=local_model,
        adk_version=adk_version,
        litellm_version=litellm_version,
        runtime_call_performed=False,
        notes=notes,
    )


def _installed_version(distribution_name: str) -> str | None:
    try:
        return importlib_metadata.version(distribution_name)
    except importlib_metadata.PackageNotFoundError:
        return None
