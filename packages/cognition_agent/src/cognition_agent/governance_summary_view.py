"""Read-only governance evidence summary views for the cognition agent shell."""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from cognition_agent.models import AgentBaseCandidate


GOVERNANCE_EVIDENCE_SUMMARY_VIEW_VERSION = (
    "agent_governance_evidence_summary_view_v1"
)
GOVERNANCE_EVIDENCE_SUMMARY_VIEW_SOURCE = (
    "schemas.runtime.AdkLifecycleFactsSummary+"
    "schemas.runtime.AdkRunConfigServiceBundleSummary+"
    "observability_hub.AdkWorkflowRunnerEvidence.graph_trace_summary_shape"
)

FORBIDDEN_GOVERNANCE_SUMMARY_KEYS = frozenset(
    {
        "api_key",
        "blob",
        "bytes",
        "completion",
        "credential",
        "credentials",
        "file_content",
        "full_response",
        "message",
        "messages",
        "prompt",
        "raw",
        "raw_provider_response",
        "raw_response",
        "response",
        "response_text",
        "secret",
        "system_prompt",
        "text",
        "token",
    }
)

FORBIDDEN_GOVERNANCE_SUMMARY_MODULE_PREFIXES = (
    "google.adk",
    "adk_adapter",
    "runtime",
    "runtime_container",
    "observability_hub",
    "cognition_governance",
)


class AgentGovernanceEvidenceSummaryViewCandidate(AgentBaseCandidate):
    """Agent-facing read-only view over sanitized governance evidence summaries."""

    candidate_type: str = "agent_governance_evidence_summary_view_candidate"
    summary_version: str = GOVERNANCE_EVIDENCE_SUMMARY_VIEW_VERSION
    summary_source: str = GOVERNANCE_EVIDENCE_SUMMARY_VIEW_SOURCE
    lifecycle_summary_id: str | None = None
    run_config_service_bundle_summary_id: str | None = None
    runtime_id: str | None = None
    workflow_id: str | None = None
    workflow_name: str | None = None
    runtime_status: str | None = None
    artifact_count: int = Field(default=0, ge=0)
    session_observed: bool = False
    event_count: int = Field(default=0, ge=0)
    event_types: list[str] = Field(default_factory=list)
    state_delta_count: int = Field(default=0, ge=0)
    state_delta_entity_mode: str | None = None
    graph_summary_id: str | None = None
    graph_node_path_count: int = Field(default=0, ge=0)
    graph_node_paths: list[str] = Field(default_factory=list)
    graph_has_branching: bool = False
    trace_event_count: int = Field(default=0, ge=0)
    trace_event_types: list[str] = Field(default_factory=list)
    trace_has_error: bool = False
    artifact_service_type_name: str | None = None
    session_service_type_name: str | None = None
    run_config_mapped_fields: list[str] = Field(default_factory=list)
    run_config_unmapped_fields: list[str] = Field(default_factory=list)
    run_config_deferred_fields: list[str] = Field(default_factory=list)
    run_config_no_live_mode: bool = True
    run_config_call_attempted: bool = False
    service_bundle_source: str | None = None
    service_persistence_stage: str | None = None
    service_persistence_strategy: str | None = None
    artifact_service_present: bool = False
    session_service_present: bool = False
    readonly: bool = True
    candidate_only: bool = True
    execution_enabled: bool = False
    agent_runtime_enabled: bool = False
    runtime_call_enabled: bool = False
    runtime_container_call_enabled: bool = False
    runtime_helper_call_enabled: bool = False
    service_invoke_enabled: bool = False
    llm_call_enabled: bool = False
    action_execution_enabled: bool = False
    runtime_action_enabled: bool = False
    cli_enabled: bool = False
    chat_enabled: bool = False
    gateway_enabled: bool = False
    tool_execution_enabled: bool = False

    @model_validator(mode="after")
    def validate_readonly_governance_summary(
        self,
    ) -> "AgentGovernanceEvidenceSummaryViewCandidate":
        if not self.readonly:
            raise ValueError("readonly must remain true.")
        if not self.candidate_only:
            raise ValueError("candidate_only must remain true.")
        if self.execution_enabled:
            raise ValueError("execution_enabled must remain false.")
        if self.agent_runtime_enabled:
            raise ValueError("agent_runtime_enabled must remain false.")
        if self.runtime_call_enabled:
            raise ValueError("runtime_call_enabled must remain false.")
        if self.runtime_container_call_enabled:
            raise ValueError("runtime_container_call_enabled must remain false.")
        if self.runtime_helper_call_enabled:
            raise ValueError("runtime_helper_call_enabled must remain false.")
        if self.service_invoke_enabled:
            raise ValueError("service_invoke_enabled must remain false.")
        if self.llm_call_enabled:
            raise ValueError("llm_call_enabled must remain false.")
        if self.action_execution_enabled:
            raise ValueError("action_execution_enabled must remain false.")
        if self.runtime_action_enabled:
            raise ValueError("runtime_action_enabled must remain false.")
        if self.cli_enabled:
            raise ValueError("cli_enabled must remain false.")
        if self.chat_enabled:
            raise ValueError("chat_enabled must remain false.")
        if self.gateway_enabled:
            raise ValueError("gateway_enabled must remain false.")
        if self.tool_execution_enabled:
            raise ValueError("tool_execution_enabled must remain false.")
        if self.run_config_call_attempted:
            raise ValueError("run_config_call_attempted must remain false.")
        if not self.run_config_no_live_mode:
            raise ValueError("run_config_no_live_mode must remain true.")
        return self


def build_agent_governance_evidence_summary_view(
    *,
    candidate_id: str,
    governance_evidence_metadata: Any | None = None,
    lifecycle_summary: Any | None = None,
    run_config_service_bundle_summary: Any | None = None,
    metadata: dict[str, Any] | None = None,
    domain_metadata: dict[str, Any] | None = None,
) -> AgentGovernanceEvidenceSummaryViewCandidate:
    """Build a read-only agent view from public governance summary shapes."""

    evidence_metadata = _evidence_metadata_mapping(governance_evidence_metadata)
    llm_invocation_audit = _mapping(evidence_metadata.get("llm_invocation_audit"))
    lifecycle = _public_mapping(
        lifecycle_summary
        if lifecycle_summary is not None
        else evidence_metadata.get("lifecycle_summary")
    )
    run_config_bundle = _public_mapping(
        run_config_service_bundle_summary
        if run_config_service_bundle_summary is not None
        else evidence_metadata.get("run_config_service_bundle_summary")
    )
    graph_summary = _public_mapping(evidence_metadata.get("graph_summary"))
    trace_summary = _public_mapping(evidence_metadata.get("trace_summary"))
    if not lifecycle and not run_config_bundle and not graph_summary and not trace_summary:
        raise ValueError("At least one governance summary shape is required.")

    _raise_if_summary_boundary_violated(lifecycle)
    _raise_if_summary_boundary_violated(run_config_bundle)
    _raise_if_summary_boundary_violated(graph_summary)
    _raise_if_summary_boundary_violated(trace_summary)
    _raise_if_summary_boundary_violated(llm_invocation_audit)
    _raise_if_summary_boundary_violated(metadata or {})
    _raise_if_summary_boundary_violated(domain_metadata or {})

    lifecycle_values = _normalize_lifecycle_summary(lifecycle)
    run_config_values = _normalize_run_config_service_bundle_summary(run_config_bundle)
    graph_values = _normalize_graph_summary(graph_summary)
    trace_values = _normalize_trace_summary(trace_summary)
    merged = _merge_summary_values(
        lifecycle_values,
        run_config_values,
        graph_values,
        trace_values,
    )
    summary_ids = _summary_refs(
        lifecycle,
        run_config_bundle,
        graph_summary,
        trace_summary,
    )

    return AgentGovernanceEvidenceSummaryViewCandidate(
        candidate_id=candidate_id,
        source=GOVERNANCE_EVIDENCE_SUMMARY_VIEW_SOURCE,
        summary=_summary_text(merged),
        governance_refs=summary_ids,
        metadata={
            "view_semantics": "agent_readonly_governance_evidence_summary",
            "readonly": True,
            "candidate_only": True,
            "summary_version": GOVERNANCE_EVIDENCE_SUMMARY_VIEW_VERSION,
            "summary_source": GOVERNANCE_EVIDENCE_SUMMARY_VIEW_SOURCE,
            "consumed_lifecycle_summary": bool(lifecycle),
            "consumed_run_config_service_bundle_summary": bool(run_config_bundle),
            "consumed_graph_summary": bool(graph_summary),
            "consumed_trace_summary": bool(trace_summary),
            "does_not_import_cognition_governance": True,
            "does_not_import_observability_hub": True,
            "does_not_import_runtime": True,
            "does_not_import_runtime_container": True,
            "does_not_import_adk_adapter": True,
            "does_not_import_google_adk": True,
            "does_not_call_runtime": True,
            "does_not_call_runtime_container": True,
            "does_not_call_service_invoke": True,
            "does_not_call_llm": True,
            "does_not_execute_action": True,
            "does_not_execute_runtime_action": True,
            "does_not_enable_cli": True,
            "does_not_enable_chat": True,
            "does_not_enable_gateway": True,
            "does_not_enable_tool_executor": True,
            **(metadata or {}),
        },
        domain_metadata=domain_metadata or {},
        **merged,
    )


def _evidence_metadata_mapping(value: Any | None) -> dict[str, Any]:
    data = _public_mapping(value)
    metadata = _mapping(data.get("metadata"))
    return metadata if metadata else data


def _public_mapping(value: Any | None) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="python")
        if isinstance(dumped, dict):
            return dumped
    raise TypeError("Governance evidence summary input must be a dict-like public shape.")


def _normalize_lifecycle_summary(data: dict[str, Any]) -> dict[str, Any]:
    if not data:
        return {}
    session = _mapping(data.get("session"))
    events = _mapping(data.get("events"))
    context_state = _mapping(data.get("context_state"))
    artifacts = _list(data.get("artifacts"))
    return {
        "lifecycle_summary_id": _optional_string(data.get("summary_id")),
        "runtime_id": _optional_string(data.get("runtime_id")),
        "workflow_id": _optional_string(data.get("workflow_id")),
        "workflow_name": _optional_string(data.get("workflow_name")),
        "runtime_status": _optional_string(data.get("status")),
        "artifact_count": len(artifacts),
        "session_observed": bool(session.get("session_id")),
        "event_count": _non_negative_int(events.get("event_count")),
        "event_types": _string_list(events.get("event_types")),
        "state_delta_count": _non_negative_int(
            context_state.get("state_delta_count")
        ),
        "state_delta_entity_mode": _optional_string(
            context_state.get("state_delta_entity_mode")
        ),
        "artifact_service_type_name": _service_type_from_artifacts(artifacts),
        "session_service_type_name": _optional_string(session.get("service_type_name")),
    }


def _normalize_run_config_service_bundle_summary(data: dict[str, Any]) -> dict[str, Any]:
    if not data:
        return {}
    run_config = _mapping(data.get("run_config"))
    service_bundle = _mapping(data.get("service_bundle"))
    return {
        "run_config_service_bundle_summary_id": _optional_string(data.get("summary_id")),
        "runtime_id": _optional_string(data.get("runtime_id")),
        "workflow_id": _optional_string(data.get("workflow_id")),
        "workflow_name": _optional_string(data.get("workflow_name")),
        "runtime_status": _optional_string(data.get("status")),
        "run_config_mapped_fields": _string_list(run_config.get("mapped_fields")),
        "run_config_unmapped_fields": _string_list(run_config.get("unmapped_fields")),
        "run_config_deferred_fields": _string_list(run_config.get("deferred_fields")),
        "run_config_no_live_mode": _bool(run_config.get("no_live_mode"), default=True),
        "run_config_call_attempted": _bool(run_config.get("call_attempted")),
        "service_bundle_source": _optional_string(
            service_bundle.get("service_bundle_source")
        ),
        "service_persistence_stage": _optional_string(
            service_bundle.get("persistence_stage")
        ),
        "service_persistence_strategy": _optional_string(
            service_bundle.get("persistence_strategy")
        ),
        "artifact_service_present": _bool(
            service_bundle.get("artifact_service_present")
        ),
        "session_service_present": _bool(service_bundle.get("session_service_present")),
        "artifact_service_type_name": _optional_string(
            service_bundle.get("artifact_service_type_name")
        ),
        "session_service_type_name": _optional_string(
            service_bundle.get("session_service_type_name")
        ),
    }


def _normalize_graph_summary(data: dict[str, Any]) -> dict[str, Any]:
    if not data:
        return {}
    return {
        "graph_summary_id": _optional_string(data.get("summary_id")),
        "runtime_id": _optional_string(data.get("runtime_id")),
        "workflow_id": _optional_string(data.get("workflow_id")),
        "workflow_name": _optional_string(data.get("workflow_name")),
        "graph_node_path_count": _non_negative_int(data.get("node_path_count")),
        "graph_node_paths": _string_list(data.get("node_paths")),
        "graph_has_branching": _bool(data.get("has_branching")),
    }


def _normalize_trace_summary(data: dict[str, Any]) -> dict[str, Any]:
    if not data:
        return {}
    return {
        "trace_event_count": _non_negative_int(data.get("event_count")),
        "trace_event_types": _string_list(data.get("event_types")),
        "trace_has_error": _bool(data.get("has_error")),
    }


def _merge_summary_values(
    *summary_values: dict[str, Any],
) -> dict[str, Any]:
    values = {
        "lifecycle_summary_id": None,
        "run_config_service_bundle_summary_id": None,
        "runtime_id": None,
        "workflow_id": None,
        "workflow_name": None,
        "runtime_status": None,
        "artifact_count": 0,
        "session_observed": False,
        "event_count": 0,
        "event_types": [],
        "state_delta_count": 0,
        "state_delta_entity_mode": None,
        "graph_summary_id": None,
        "graph_node_path_count": 0,
        "graph_node_paths": [],
        "graph_has_branching": False,
        "trace_event_count": 0,
        "trace_event_types": [],
        "trace_has_error": False,
        "artifact_service_type_name": None,
        "session_service_type_name": None,
        "run_config_mapped_fields": [],
        "run_config_unmapped_fields": [],
        "run_config_deferred_fields": [],
        "run_config_no_live_mode": True,
        "run_config_call_attempted": False,
        "service_bundle_source": None,
        "service_persistence_stage": None,
        "service_persistence_strategy": None,
        "artifact_service_present": False,
        "session_service_present": False,
    }
    for source in summary_values:
        for key, item in source.items():
            if item not in (None, [], {}):
                values[key] = item
    return values


def _summary_refs(
    lifecycle_summary: dict[str, Any],
    run_config_service_bundle_summary: dict[str, Any],
    graph_summary: dict[str, Any],
    trace_summary: dict[str, Any],
) -> list[str]:
    refs: list[str] = []
    lifecycle_id = _optional_string(lifecycle_summary.get("summary_id"))
    run_config_id = _optional_string(
        run_config_service_bundle_summary.get("summary_id")
    )
    graph_id = _optional_string(graph_summary.get("summary_id"))
    trace_source = _optional_string(trace_summary.get("source"))
    if lifecycle_id:
        refs.append(f"lifecycle_summary:{lifecycle_id}")
    if run_config_id:
        refs.append(f"run_config_service_bundle_summary:{run_config_id}")
    if graph_id:
        refs.append(f"graph_summary:{graph_id}")
    if trace_summary:
        refs.append(f"trace_summary:{trace_source or 'present'}")
    return refs


def _summary_text(values: dict[str, Any]) -> str:
    workflow = values["workflow_name"] or values["workflow_id"] or "unknown_workflow"
    status = values["runtime_status"] or "unknown_status"
    return (
        "Read-only governance evidence summary: "
        f"workflow={workflow}, status={status}, "
        f"artifacts={values['artifact_count']}, events={values['event_count']}, "
        f"state_deltas={values['state_delta_count']}, "
        f"graph_nodes={values['graph_node_path_count']}, "
        f"trace_events={values['trace_event_count']}, "
        f"mapped_run_config_fields={len(values['run_config_mapped_fields'])}, "
        f"service_bundle_source={values['service_bundle_source'] or 'unknown'}. "
        "This view is not execution permission."
    )


def _raise_if_summary_boundary_violated(value: Any) -> None:
    violations = _summary_boundary_violations(value)
    if violations:
        raise ValueError("; ".join(violations))


def _summary_boundary_violations(value: Any, path: str = "$") -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            key_path = f"{path}.{key_text}"
            if key_text.lower() in FORBIDDEN_GOVERNANCE_SUMMARY_KEYS:
                violations.append(
                    f"governance summary payload key is forbidden at {key_path}"
                )
            if key_text == "object_module" and isinstance(item, str):
                if item.startswith(FORBIDDEN_GOVERNANCE_SUMMARY_MODULE_PREFIXES):
                    violations.append(f"forbidden object module at {key_path}")
            violations.extend(_summary_boundary_violations(item, key_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            violations.extend(_summary_boundary_violations(item, f"{path}[{index}]"))
    return violations


def _service_type_from_artifacts(artifacts: list[Any]) -> str | None:
    for artifact in artifacts:
        artifact_mapping = _mapping(artifact)
        service_type = _optional_string(artifact_mapping.get("service_type_name"))
        if service_type:
            return service_type
    return None


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in _list(value) if item not in (None, "")]


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _non_negative_int(value: Any) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


def _bool(value: Any, *, default: bool = False) -> bool:
    return value if isinstance(value, bool) else default
