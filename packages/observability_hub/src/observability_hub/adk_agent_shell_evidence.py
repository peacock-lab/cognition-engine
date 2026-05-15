"""ADK native Agent shell execution evidence candidates."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import Field

from observability_hub.models import ObservabilityBaseModel


class AdkAgentShellEvidence(ObservabilityBaseModel):
    """Candidate evidence from an ADK native Agent shell execution."""

    evidence_id: str
    source: str
    runtime_kind: str
    agent_name: str | None = None
    agent_type: str | None = None
    status: str
    app_name: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    requested_invocation_id: str | None = None
    adk_invocation_id: str | None = None
    invocation_summary: dict[str, Any] = Field(default_factory=dict)
    session_summary: dict[str, Any] = Field(default_factory=dict)
    event_summary: dict[str, Any] = Field(default_factory=dict)
    artifact_summary: dict[str, Any] = Field(default_factory=dict)
    service_bundle: dict[str, Any] = Field(default_factory=dict)
    run_config: dict[str, Any] = Field(default_factory=dict)
    assembly_options: dict[str, Any] = Field(default_factory=dict)
    no_live_execution_observed: bool = False
    metadata_keys: list[str] = Field(default_factory=list)
    contract_candidate_notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: str


def build_adk_agent_shell_evidence(
    agent_run: Any,
    *,
    assembly_metadata: dict[str, Any] | None = None,
) -> AdkAgentShellEvidence:
    """Build sanitized evidence for an ADK Agent shell run."""

    run = _mapping(agent_run)
    metadata = _mapping(run.get("metadata"))
    assembly = _mapping(assembly_metadata)
    service_bundle = _mapping(assembly.get("service_bundle")) or _mapping(
        metadata.get("service_bundle")
    )
    run_config = _mapping(metadata.get("run_config"))
    events = [_mapping(event) for event in _list(run.get("events"))]
    errors = [_mapping(error) for error in _list(run.get("errors"))]
    warnings: list[str] = []
    if not assembly:
        warnings.append("assembly_metadata was not provided; assembly facts are partial.")
    if not events:
        warnings.append("agent run did not include runtime event summaries.")

    evidence_id = f"adk-agent-shell-evidence-{uuid4()}"
    return AdkAgentShellEvidence(
        evidence_id=evidence_id,
        source="observability_hub.adk_agent_shell_evidence",
        runtime_kind="adk_agent_shell",
        agent_name=_plain_str(run.get("agent_name") or assembly.get("agent_name")),
        agent_type=_plain_str(run.get("agent_type") or assembly.get("agent_type")),
        status="failed" if errors else "success",
        app_name=_plain_str(run.get("app_name") or assembly.get("app_name")),
        user_id=_plain_str(run.get("user_id") or assembly.get("user_id")),
        session_id=_plain_str(run.get("session_id")),
        requested_invocation_id=_plain_str(run.get("requested_invocation_id")),
        adk_invocation_id=_plain_str(run.get("adk_invocation_id")),
        invocation_summary=_build_invocation_summary(run),
        session_summary=_build_session_summary(run),
        event_summary=_build_event_summary(events),
        artifact_summary=_build_artifact_summary(events),
        service_bundle=service_bundle,
        run_config=run_config,
        assembly_options=_mapping(assembly.get("assembly_options")),
        no_live_execution_observed=bool(
            metadata.get("no_live_execution_observed")
            or run.get("no_live_execution_observed")
        ),
        metadata_keys=sorted(
            key
            for source in (run, metadata, assembly)
            for key in source
            if isinstance(key, str)
        ),
        contract_candidate_notes=[
            "Candidate evidence only; not a public contract.",
            "ADK native objects are summarized as plain metadata.",
            "Multi-agent event facts are summary-only hints, not topology truth.",
            "Handoff event facts are ADK action hints, not handoff refs.",
            "No topology, handoff, or role refs are produced.",
            "No-live execution evidence does not imply production approval.",
        ],
        warnings=warnings,
        created_at=datetime.now(UTC).isoformat(),
    )


def _build_invocation_summary(run: dict[str, Any]) -> dict[str, Any]:
    invocation_binding = _mapping(run.get("invocation_binding"))
    return {
        "requested_invocation_id": _plain_str(run.get("requested_invocation_id")),
        "adk_invocation_id": _plain_str(run.get("adk_invocation_id")),
        "session_id": _plain_str(run.get("session_id")),
        "binding_keys": sorted(invocation_binding),
        "binding_present": bool(invocation_binding),
    }


def _build_session_summary(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": _plain_str(run.get("session_id")),
        "session_observed": bool(run.get("session_id")),
    }


def _build_event_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    authors = sorted(
        {
            _plain_str(_mapping(event.get("metadata")).get("author"))
            for event in events
            if _plain_str(_mapping(event.get("metadata")).get("author"))
        }
    )
    event_types = sorted(
        {
            _plain_str(event.get("event_type"))
            for event in events
            if _plain_str(event.get("event_type"))
        }
    )
    node_paths = sorted(
        {
            _plain_str(_mapping(event.get("metadata")).get("node_path"))
            for event in events
            if _plain_str(_mapping(event.get("metadata")).get("node_path"))
        }
    )
    branch_ids = sorted(
        {
            _plain_str(_mapping(event.get("metadata")).get("branch"))
            for event in events
            if _plain_str(_mapping(event.get("metadata")).get("branch"))
        }
    )
    invocation_ids = sorted(
        {
            _plain_str(_mapping(event.get("metadata")).get("adk_invocation_id"))
            for event in events
            if _plain_str(_mapping(event.get("metadata")).get("adk_invocation_id"))
        }
    )
    handoff_targets = sorted(
        {
            _plain_str(_mapping(event.get("metadata")).get("adk_transfer_to_agent"))
            for event in events
            if _plain_str(_mapping(event.get("metadata")).get("adk_transfer_to_agent"))
        }
    )
    handoff_event_count = sum(
        1
        for event in events
        if _plain_str(_mapping(event.get("metadata")).get("adk_transfer_to_agent"))
    )
    return {
        "event_count": len(events),
        "event_authors": authors,
        "branch_ids": branch_ids,
        "invocation_ids": invocation_ids,
        "handoff_targets": handoff_targets,
        "handoff_event_count": handoff_event_count,
        "event_types": event_types,
        "node_paths": node_paths,
        "has_error": any(_mapping(event.get("metadata")).get("error_code") for event in events),
        "content_observed": any(_mapping(event.get("payload")).get("content") for event in events),
        "output_observed": any(_mapping(event.get("payload")).get("output") for event in events),
    }


def _build_artifact_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    artifact_events = [
        event
        for event in events
        if _mapping(event.get("payload")).get("artifact_delta") is not None
    ]
    return {
        "artifact_count": len(artifact_events),
        "artifact_delta_observed": bool(artifact_events),
    }


def _mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return {
            str(key): _sanitize(value)
            for key, value in value.items()
            if isinstance(key, str)
        }
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="python")
        if isinstance(dumped, dict):
            return _mapping(dumped)
    return {}


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _sanitize(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _sanitize(item)
            for key, item in value.items()
            if isinstance(key, str)
        }
    if hasattr(value, "model_dump"):
        return _sanitize(value.model_dump(mode="python"))
    return repr(value)


def _plain_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)
