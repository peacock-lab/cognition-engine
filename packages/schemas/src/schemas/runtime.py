"""Runtime-facing public data contracts for Cognition Engine."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RuntimeStatus(str, Enum):
    """Standard runtime execution status."""

    SUCCESS = "success"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    RESUMABLE = "resumable"


class RuntimeEventType(str, Enum):
    """Standard runtime event type."""

    RUNTIME_STARTED = "runtime_started"
    RUNTIME_COMPLETED = "runtime_completed"
    RUNTIME_FAILED = "runtime_failed"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"
    STATE_DELTA = "state_delta"
    ARTIFACT_DELTA = "artifact_delta"
    RESUME_REQUESTED = "resume_requested"
    HUMAN_INPUT_REQUESTED = "human_input_requested"


class DeltaOperation(str, Enum):
    """Standard delta operation."""

    SET = "set"
    UPDATE = "update"
    DELETE = "delete"
    APPEND = "append"


class RuntimeBaseModel(BaseModel):
    """Base model for runtime schemas."""

    model_config = ConfigDict(extra="forbid")


FORBIDDEN_LIFECYCLE_METADATA_KEYS = frozenset(
    {
        "api_key",
        "blob",
        "bytes",
        "completion",
        "file_content",
        "full_response",
        "message",
        "messages",
        "prompt",
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

FORBIDDEN_LIFECYCLE_MODULE_PREFIXES = (
    "google.adk",
    "adk_adapter",
    "runtime_container",
    "composition",
    "litellm",
)


class InvocationRef(RuntimeBaseModel):
    """Stable reference for one runtime invocation."""

    invocation_id: str
    runtime_id: str | None = None
    workflow_id: str | None = None
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowRef(RuntimeBaseModel):
    """Stable reference for a workflow."""

    workflow_id: str
    name: str | None = None
    version: str | None = None
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NodeRef(RuntimeBaseModel):
    """Stable reference for a workflow node."""

    node_id: str
    name: str | None = None
    version: str | None = None
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactRef(RuntimeBaseModel):
    """Stable reference for an artifact."""

    artifact_id: str
    name: str | None = None
    path: str | None = None
    version: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StateDelta(RuntimeBaseModel):
    """Runtime state delta."""

    delta_id: str
    invocation_ref: InvocationRef
    scope: str
    key: str
    value: Any = None
    operation: DeltaOperation
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactDelta(RuntimeBaseModel):
    """Runtime artifact delta."""

    delta_id: str
    invocation_ref: InvocationRef
    artifact_ref: ArtifactRef
    operation: DeltaOperation
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeEvent(RuntimeBaseModel):
    """Standard runtime event."""

    event_id: str
    event_type: RuntimeEventType
    invocation_ref: InvocationRef
    workflow_ref: WorkflowRef | None = None
    node_ref: NodeRef | None = None
    timestamp: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    state_delta_refs: list[str] = Field(default_factory=list)
    artifact_delta_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeErrorRecord(RuntimeBaseModel):
    """Standard runtime error record."""

    error_id: str
    error_type: str
    message: str
    recoverable: bool = False
    invocation_ref: InvocationRef | None = None
    workflow_ref: WorkflowRef | None = None
    node_ref: NodeRef | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResumePoint(RuntimeBaseModel):
    """Runtime resume point."""

    resume_id: str
    invocation_ref: InvocationRef
    workflow_ref: WorkflowRef | None = None
    node_ref: NodeRef | None = None
    reason: str
    required_input: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class HumanInputRequest(RuntimeBaseModel):
    """Human-in-the-loop input request."""

    request_id: str
    invocation_ref: InvocationRef
    prompt: str
    expected_response_schema: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class HumanInputResponse(RuntimeBaseModel):
    """Human-in-the-loop input response."""

    request_id: str
    invocation_ref: InvocationRef
    response_payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class NodeExecutionInput(RuntimeBaseModel):
    """Standard node execution input."""

    node_ref: NodeRef
    workflow_ref: WorkflowRef | None = None
    invocation_ref: InvocationRef
    input_payload: dict[str, Any] = Field(default_factory=dict)
    config_context_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NodeExecutionResult(RuntimeBaseModel):
    """Standard node execution result."""

    node_ref: NodeRef
    status: RuntimeStatus
    invocation_ref: InvocationRef
    output_payload: dict[str, Any] = Field(default_factory=dict)
    events: list[RuntimeEvent] = Field(default_factory=list)
    state_deltas: list[StateDelta] = Field(default_factory=list)
    artifact_deltas: list[ArtifactDelta] = Field(default_factory=list)
    errors: list[RuntimeErrorRecord] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowInput(RuntimeBaseModel):
    """Standard workflow input."""

    workflow_ref: WorkflowRef
    invocation_ref: InvocationRef
    input_payload: dict[str, Any] = Field(default_factory=dict)
    node_graph_ref: str | None = None
    config_context_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowResult(RuntimeBaseModel):
    """Standard workflow result."""

    workflow_ref: WorkflowRef
    status: RuntimeStatus
    invocation_ref: InvocationRef
    node_results: list[NodeExecutionResult] = Field(default_factory=list)
    events: list[RuntimeEvent] = Field(default_factory=list)
    state_deltas: list[StateDelta] = Field(default_factory=list)
    artifact_deltas: list[ArtifactDelta] = Field(default_factory=list)
    errors: list[RuntimeErrorRecord] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeInput(RuntimeBaseModel):
    """Standard runtime input."""

    runtime_id: str
    workflow_ref: WorkflowRef
    invocation_ref: InvocationRef
    input_payload: dict[str, Any] = Field(default_factory=dict)
    config_context_ref: str | None = None
    adapter_selection: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeResult(RuntimeBaseModel):
    """Standard runtime result."""

    runtime_id: str
    status: RuntimeStatus
    invocation_ref: InvocationRef
    workflow_result: WorkflowResult | None = None
    events: list[RuntimeEvent] = Field(default_factory=list)
    state_deltas: list[StateDelta] = Field(default_factory=list)
    artifact_deltas: list[ArtifactDelta] = Field(default_factory=list)
    errors: list[RuntimeErrorRecord] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactLifecycleFacts(RuntimeBaseModel):
    """Sanitized artifact lifecycle facts derived from runtime artifact deltas."""

    artifact_ref: ArtifactRef
    invocation_ref: InvocationRef | None = None
    operation: DeltaOperation | None = None
    version: str | None = None
    artifact_source: str | None = None
    artifact_sink: str | None = None
    name_prefix: str | None = None
    service_type_name: str | None = None
    source: str = "schemas.runtime.ArtifactLifecycleFacts"
    metadata_keys: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_sanitized_lifecycle_metadata(self) -> "ArtifactLifecycleFacts":
        _raise_if_lifecycle_metadata_violates_boundary(self.metadata)
        _raise_if_lifecycle_metadata_violates_boundary(self.artifact_ref.metadata)
        return self


class SessionLifecycleFacts(RuntimeBaseModel):
    """Sanitized session lifecycle facts derived from runtime metadata."""

    session_id: str | None = None
    app_name: str | None = None
    user_id: str | None = None
    invocation_ref: InvocationRef | None = None
    event_count: int = Field(default=0, ge=0)
    has_state: bool = False
    state_keys: list[str] = Field(default_factory=list)
    state_key_count: int = Field(default=0, ge=0)
    service_type_name: str | None = None
    source: str = "schemas.runtime.SessionLifecycleFacts"
    metadata_keys: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_sanitized_lifecycle_metadata(self) -> "SessionLifecycleFacts":
        _raise_if_lifecycle_metadata_violates_boundary(self.metadata)
        if self.invocation_ref is not None:
            _raise_if_lifecycle_metadata_violates_boundary(self.invocation_ref.metadata)
        return self


class EventLifecycleFacts(RuntimeBaseModel):
    """Sanitized event lifecycle facts derived from runtime event summaries."""

    event_count: int = Field(default=0, ge=0)
    event_ids: list[str] = Field(default_factory=list)
    event_types: list[str] = Field(default_factory=list)
    authors: list[str] = Field(default_factory=list)
    branch_ids: list[str] = Field(default_factory=list)
    node_paths: list[str] = Field(default_factory=list)
    state_delta_refs: list[str] = Field(default_factory=list)
    artifact_delta_refs: list[str] = Field(default_factory=list)
    invocation_ids: list[str] = Field(default_factory=list)
    state_delta_count: int = Field(default=0, ge=0)
    state_delta_keys: list[str] = Field(default_factory=list)
    error_count: int = Field(default=0, ge=0)
    error_codes: list[str] = Field(default_factory=list)
    has_error: bool = False
    source: str = "schemas.runtime.EventLifecycleFacts"
    metadata_keys: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_sanitized_lifecycle_metadata(self) -> "EventLifecycleFacts":
        _raise_if_lifecycle_metadata_violates_boundary(self.metadata)
        return self


class ContextStateLifecycleFacts(RuntimeBaseModel):
    """Sanitized context/state facts derived from session, events, and RunConfig."""

    source: str = "schemas.runtime.ContextStateLifecycleFacts"
    has_session_state: bool = False
    session_state_keys: list[str] = Field(default_factory=list)
    session_state_key_count: int = Field(default=0, ge=0)
    state_delta_refs: list[str] = Field(default_factory=list)
    state_delta_scopes: list[str] = Field(default_factory=list)
    state_delta_operations: list[str] = Field(default_factory=list)
    state_delta_count: int = Field(default=0, ge=0)
    state_delta_keys: list[str] = Field(default_factory=list)
    state_delta_entity_mode: str = "summary_only"
    raw_state_values_included: bool = False
    custom_metadata_keys: list[str] = Field(default_factory=list)
    runtime_metadata_keys: list[str] = Field(default_factory=list)
    sanitized: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_sanitized_context_state_facts(self) -> "ContextStateLifecycleFacts":
        violations = _lifecycle_metadata_boundary_violations(self.metadata)
        if not self.sanitized:
            violations.append("sanitized must remain true.")
        if self.raw_state_values_included:
            violations.append("raw_state_values_included must remain false.")
        if violations:
            raise ValueError("; ".join(violations))
        return self


class AdkLifecycleFactsSummary(RuntimeBaseModel):
    """Candidate public summary for ADK artifact/session/event lifecycle facts."""

    summary_id: str
    source: str = "schemas.runtime.AdkLifecycleFactsSummary"
    runtime_id: str | None = None
    workflow_id: str | None = None
    workflow_name: str | None = None
    status: str | None = None
    invocation_ref: InvocationRef | None = None
    artifacts: list[ArtifactLifecycleFacts] = Field(default_factory=list)
    session: SessionLifecycleFacts | None = None
    events: EventLifecycleFacts = Field(default_factory=EventLifecycleFacts)
    context_state: ContextStateLifecycleFacts = Field(
        default_factory=ContextStateLifecycleFacts
    )
    candidate_only: bool = True
    formal_decision_enabled: bool = False
    policy_execution_enabled: bool = False
    governance_outcome_enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_candidate_and_sanitized_boundary(self) -> "AdkLifecycleFactsSummary":
        violations: list[str] = []
        if not self.candidate_only:
            violations.append("candidate_only must remain true.")
        if self.formal_decision_enabled:
            violations.append("formal_decision_enabled must remain false.")
        if self.policy_execution_enabled:
            violations.append("policy_execution_enabled must remain false.")
        if self.governance_outcome_enabled:
            violations.append("governance_outcome_enabled must remain false.")
        violations.extend(_lifecycle_metadata_boundary_violations(self.metadata))
        if self.invocation_ref is not None:
            violations.extend(
                _lifecycle_metadata_boundary_violations(self.invocation_ref.metadata)
            )
        if violations:
            raise ValueError("; ".join(violations))
        return self


class RunConfigGovernanceView(RuntimeBaseModel):
    """Candidate sanitized governance view for mapped ADK RunConfig facts."""

    source: str = "schemas.runtime.RunConfigGovernanceView"
    run_config_source: str | None = None
    adk_run_config_version: str | None = None
    official_fields: list[str] = Field(default_factory=list)
    mapper_supported_fields: list[str] = Field(default_factory=list)
    field_policies: dict[str, dict[str, str]] = Field(default_factory=dict)
    deprecated_fields: list[str] = Field(default_factory=list)
    live_media_fields: list[str] = Field(default_factory=list)
    declared_fields: list[str] = Field(default_factory=list)
    mapped_fields: list[str] = Field(default_factory=list)
    unmapped_fields: list[str] = Field(default_factory=list)
    deferred_fields: list[str] = Field(default_factory=list)
    custom_metadata_keys: list[str] = Field(default_factory=list)
    max_llm_calls: int | None = None
    streaming_mode: str | None = None
    adk_run_config_type: str | None = None
    live_blob_save_requested: bool = False
    live_audio_save_requested: bool = False
    live_call_enabled: bool = False
    no_live_mode: bool = True
    call_attempted: bool = False
    candidate_only: bool = True
    formal_decision_enabled: bool = False
    policy_execution_enabled: bool = False
    governance_outcome_enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_candidate_and_sanitized_boundary(self) -> "RunConfigGovernanceView":
        violations = _candidate_boundary_violations(
            candidate_only=self.candidate_only,
            formal_decision_enabled=self.formal_decision_enabled,
            policy_execution_enabled=self.policy_execution_enabled,
            governance_outcome_enabled=self.governance_outcome_enabled,
        )
        if self.live_call_enabled:
            violations.append("live_call_enabled must remain false.")
        if not self.no_live_mode:
            violations.append("no_live_mode must remain true.")
        if self.call_attempted:
            violations.append("call_attempted must remain false.")
        violations.extend(_lifecycle_metadata_boundary_violations(self.metadata))
        if violations:
            raise ValueError("; ".join(violations))
        return self


class ServiceBundleGovernanceView(RuntimeBaseModel):
    """Candidate sanitized governance view for ADK service bundle facts."""

    source: str = "schemas.runtime.ServiceBundleGovernanceView"
    service_bundle_source: str | None = None
    persistence_stage: str = "runtime_fact_only"
    persistence_strategy: str = "not_configured"
    external_persistence_enabled: bool = False
    artifact_service_present: bool = False
    session_service_present: bool = False
    artifact_service_type_name: str | None = None
    session_service_type_name: str | None = None
    artifact_service_source: str | None = None
    session_service_source: str | None = None
    capability_flags: list[str] = Field(default_factory=list)
    candidate_only: bool = True
    formal_decision_enabled: bool = False
    policy_execution_enabled: bool = False
    governance_outcome_enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_candidate_and_sanitized_boundary(
        self,
    ) -> "ServiceBundleGovernanceView":
        violations = _candidate_boundary_violations(
            candidate_only=self.candidate_only,
            formal_decision_enabled=self.formal_decision_enabled,
            policy_execution_enabled=self.policy_execution_enabled,
            governance_outcome_enabled=self.governance_outcome_enabled,
        )
        violations.extend(_lifecycle_metadata_boundary_violations(self.metadata))
        if self.external_persistence_enabled:
            violations.append("external_persistence_enabled must remain false.")
        if violations:
            raise ValueError("; ".join(violations))
        return self


class AdkRunConfigServiceBundleSummary(RuntimeBaseModel):
    """Candidate public summary for ADK RunConfig and ServiceBundle governance facts."""

    summary_id: str
    source: str = "schemas.runtime.AdkRunConfigServiceBundleSummary"
    runtime_id: str | None = None
    workflow_id: str | None = None
    workflow_name: str | None = None
    status: str | None = None
    run_config: RunConfigGovernanceView = Field(default_factory=RunConfigGovernanceView)
    service_bundle: ServiceBundleGovernanceView = Field(
        default_factory=ServiceBundleGovernanceView
    )
    candidate_only: bool = True
    formal_decision_enabled: bool = False
    policy_execution_enabled: bool = False
    governance_outcome_enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_candidate_and_sanitized_boundary(
        self,
    ) -> "AdkRunConfigServiceBundleSummary":
        violations = _candidate_boundary_violations(
            candidate_only=self.candidate_only,
            formal_decision_enabled=self.formal_decision_enabled,
            policy_execution_enabled=self.policy_execution_enabled,
            governance_outcome_enabled=self.governance_outcome_enabled,
        )
        violations.extend(_lifecycle_metadata_boundary_violations(self.metadata))
        if violations:
            raise ValueError("; ".join(violations))
        return self


class AdkServiceFactsSummaryInput(RuntimeBaseModel):
    """Public input contract for ADK service facts used by governance summaries."""

    evidence_id: str | None = None
    source: str = "schemas.runtime.AdkServiceFactsSummaryInput"
    lifecycle_summary: AdkLifecycleFactsSummary
    run_config_service_bundle_summary: AdkRunConfigServiceBundleSummary
    sanitized: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_sanitized_service_facts(self) -> "AdkServiceFactsSummaryInput":
        violations = _lifecycle_metadata_boundary_violations(self.metadata)
        if not self.sanitized:
            violations.append("sanitized must remain true.")
        if violations:
            raise ValueError("; ".join(violations))
        return self


class RecordedRunEvidenceInput(RuntimeBaseModel):
    """Public input contract for recorded-run evidence and ADK service facts.

    evidence_bundle_ref is a stable reference identifier for an upstream
    EvidenceBundle. It links recorded-run evidence to an observability intake
    product without embedding the bundle body or raw provider content.
    """

    recorded_run_id: str | None = None
    evidence_id: str | None = None
    source: str = "schemas.runtime.RecordedRunEvidenceInput"
    adk_service_facts: AdkServiceFactsSummaryInput
    evidence_bundle_ref: str | None = Field(
        default=None,
        description=(
            "Stable reference id for an upstream EvidenceBundle; reference only, "
            "not EvidenceBundle content."
        ),
    )
    adk_workflow_runner_evidence_ref: str | None = None
    evidence_bundle_observed: bool = Field(
        default=False,
        description="True when evidence_bundle_ref points to an observed EvidenceBundle.",
    )
    adk_workflow_runner_evidence_observed: bool = False
    does_not_execute_recorded_run: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_recorded_run_contract(self) -> "RecordedRunEvidenceInput":
        violations = _lifecycle_metadata_boundary_violations(self.metadata)
        if not self.does_not_execute_recorded_run:
            violations.append("does_not_execute_recorded_run must remain true.")
        if violations:
            raise ValueError("; ".join(violations))
        return self


class RuntimeProductizationGateEvaluationFacts(RuntimeBaseModel):
    """Public facts emitted after evaluating runtime productization gating."""

    gate_id: str
    runtime_execution_ready: bool = False
    adk_run_allowed: bool = False
    live_llm_allowed: bool = False
    ollama_allowed: bool = False
    default_no_live: bool = True
    default_no_adk_run: bool = True
    default_no_ollama: bool = True
    execution_performed: bool = False
    adk_run_performed: bool = False
    live_llm_call_performed: bool = False
    ollama_call_performed: bool = False
    missing_conditions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_no_execution_performed(self) -> "RuntimeProductizationGateEvaluationFacts":
        violations = _lifecycle_metadata_boundary_violations(self.metadata)
        if self.execution_performed:
            violations.append("execution_performed must remain false.")
        if self.adk_run_performed:
            violations.append("adk_run_performed must remain false.")
        if self.live_llm_call_performed:
            violations.append("live_llm_call_performed must remain false.")
        if self.ollama_call_performed:
            violations.append("ollama_call_performed must remain false.")
        if violations:
            raise ValueError("; ".join(violations))
        return self


def _candidate_boundary_violations(
    *,
    candidate_only: bool,
    formal_decision_enabled: bool,
    policy_execution_enabled: bool,
    governance_outcome_enabled: bool,
) -> list[str]:
    violations: list[str] = []
    if not candidate_only:
        violations.append("candidate_only must remain true.")
    if formal_decision_enabled:
        violations.append("formal_decision_enabled must remain false.")
    if policy_execution_enabled:
        violations.append("policy_execution_enabled must remain false.")
    if governance_outcome_enabled:
        violations.append("governance_outcome_enabled must remain false.")
    return violations


def _raise_if_lifecycle_metadata_violates_boundary(value: Any) -> None:
    violations = _lifecycle_metadata_boundary_violations(value)
    if violations:
        raise ValueError("; ".join(violations))


def _lifecycle_metadata_boundary_violations(
    value: Any,
    path: str = "$.metadata",
) -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            key_path = f"{path}.{key_text}"
            if key_text.lower() in FORBIDDEN_LIFECYCLE_METADATA_KEYS:
                violations.append(f"runtime lifecycle payload key is forbidden at {key_path}")
            if key_text == "object_module" and isinstance(item, str):
                if item.startswith(FORBIDDEN_LIFECYCLE_MODULE_PREFIXES):
                    violations.append(f"runtime object module is forbidden at {key_path}")
            violations.extend(_lifecycle_metadata_boundary_violations(item, key_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            violations.extend(
                _lifecycle_metadata_boundary_violations(item, f"{path}[{index}]")
            )
    return violations
