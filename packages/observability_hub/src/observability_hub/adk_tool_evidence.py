"""ADK native Tool call evidence candidates."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import Field

from observability_hub.models import ObservabilityBaseModel


class AdkToolCallEvidence(ObservabilityBaseModel):
    """Candidate evidence from an ADK native FunctionTool call."""

    evidence_id: str
    source: str
    runtime_kind: str
    tool_name: str
    tool_kind: str
    status: str
    tool_call_allowed: bool
    tool_call_attempted: bool
    tool_runtime_call_performed: bool
    tool_confirmation_required: bool
    tool_confirmation_granted: bool
    adk_tool_confirmation_requested: bool = False
    tool_approval_ref: str | None = None
    tool_confirmation_decision_source: str | None = None
    tool_input_summary: dict[str, Any] = Field(default_factory=dict)
    tool_output_summary: dict[str, Any] = Field(default_factory=dict)
    tool_failure_type: str | None = None
    tool_evidence_ref: str
    tool_run_ref: str
    session_id: str | None = None
    artifact_delta_refs: list[str] = Field(default_factory=list)
    readonly_facts_embedded: bool = False
    does_not_store_raw_tool_input: bool = True
    does_not_store_raw_tool_output: bool = True
    raw_adk_object_included: bool = False
    metadata_keys: list[str] = Field(default_factory=list)
    contract_candidate_notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: str


def build_adk_tool_call_evidence(
    tool_call: Any,
    *,
    assembly_metadata: dict[str, Any] | None = None,
) -> AdkToolCallEvidence:
    """Build sanitized evidence for an ADK FunctionTool call."""

    call = _mapping(tool_call)
    metadata = _mapping(call.get("metadata"))
    assembly = _mapping(assembly_metadata)
    evidence_id = f"adk-tool-call-evidence-{uuid4()}"
    failure_type = _plain_str(call.get("tool_failure_type"))
    status = "failed" if failure_type else "success"
    warnings: list[str] = []
    if not call.get("does_not_store_raw_tool_input", False):
        warnings.append("raw_tool_input_boundary_not_declared")
    if not call.get("does_not_store_raw_tool_output", False):
        warnings.append("raw_tool_output_boundary_not_declared")
    if not assembly:
        warnings.append("assembly_metadata was not provided; assembly facts are partial.")

    return AdkToolCallEvidence(
        evidence_id=evidence_id,
        source="observability_hub.adk_tool_evidence",
        runtime_kind="adk_function_tool",
        tool_name=_required_str(call.get("tool_name"), "tool_name"),
        tool_kind=_required_str(call.get("tool_kind"), "tool_kind"),
        status=status,
        tool_call_allowed=bool(call.get("tool_call_allowed")),
        tool_call_attempted=bool(call.get("tool_call_attempted")),
        tool_runtime_call_performed=bool(
            call.get("tool_runtime_call_performed")
        ),
        tool_confirmation_required=bool(
            call.get("tool_confirmation_required")
        ),
        tool_confirmation_granted=bool(call.get("tool_confirmation_granted")),
        adk_tool_confirmation_requested=bool(
            call.get("adk_tool_confirmation_requested")
        ),
        tool_approval_ref=_plain_str(call.get("tool_approval_ref")),
        tool_confirmation_decision_source=_plain_str(
            call.get("tool_confirmation_decision_source")
        ),
        tool_input_summary=_mapping(call.get("tool_input_summary")),
        tool_output_summary=_mapping(call.get("tool_output_summary")),
        tool_failure_type=failure_type,
        tool_evidence_ref=f"adk-tool-call-evidence://{evidence_id}",
        tool_run_ref=_required_str(call.get("tool_run_ref"), "tool_run_ref"),
        session_id=_plain_str(call.get("session_id")),
        artifact_delta_refs=[
            str(item) for item in _list(call.get("artifact_delta_refs"))
        ],
        readonly_facts_embedded=bool(call.get("readonly_facts_embedded")),
        does_not_store_raw_tool_input=bool(
            call.get("does_not_store_raw_tool_input")
        ),
        does_not_store_raw_tool_output=bool(
            call.get("does_not_store_raw_tool_output")
        ),
        raw_adk_object_included=False,
        metadata_keys=sorted(
            key
            for source in (call, metadata, assembly)
            for key in source
            if isinstance(key, str)
        ),
        contract_candidate_notes=[
            "Candidate evidence only; not a public contract.",
            "ADK native Tool objects are summarized as plain metadata.",
            "Tool input and output are represented only by sanitized summaries.",
        ],
        warnings=warnings,
        created_at=datetime.now(UTC).isoformat(),
    )


def _mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return {
            str(key): _sanitize(item)
            for key, item in value.items()
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


def _required_str(value: Any, field_name: str) -> str:
    text = _plain_str(value)
    if not text:
        raise ValueError(f"{field_name} is required.")
    return text


def _plain_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)
