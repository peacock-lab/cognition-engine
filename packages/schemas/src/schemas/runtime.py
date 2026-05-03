"""Runtime-facing public data contracts for Cognition Engine."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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
