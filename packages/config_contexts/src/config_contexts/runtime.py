"""Runtime-facing configuration contexts for Cognition Engine."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExecutionMode(str, Enum):
    """Runtime execution mode."""

    LOCAL = "local"
    REMOTE = "remote"
    HYBRID = "hybrid"
    TEST = "test"


class RuntimeConfigBaseModel(BaseModel):
    """Base model for runtime configuration views."""

    model_config = ConfigDict(extra="forbid")


class RuntimeConfigView(RuntimeConfigBaseModel):
    """Runtime execution configuration view."""

    runtime_name: str
    execution_mode: ExecutionMode = ExecutionMode.LOCAL
    default_workflow_name: str | None = None
    enable_event_capture: bool = True
    enable_state_delta_capture: bool = True
    enable_artifact_delta_capture: bool = True
    default_adapter: str = "local"
    timeout_seconds: int = Field(default=300, gt=0)
    retry_policy_ref: str | None = None


class WorkflowExecutionConfigView(RuntimeConfigBaseModel):
    """Workflow execution policy configuration view."""

    workflow_name: str
    graph_mode: bool = True
    allow_dynamic_nodes: bool = True
    allow_collaborative_agents: bool = False
    max_node_count: int = Field(default=100, gt=0)
    max_execution_depth: int = Field(default=20, gt=0)
    timeout_seconds: int = Field(default=300, gt=0)


class NodeExecutionConfigView(RuntimeConfigBaseModel):
    """Node execution policy configuration view."""

    node_execution_mode: str = "isolated"
    enable_node_isolation: bool = True
    timeout_seconds: int = Field(default=120, gt=0)
    max_retries: int = Field(default=0, ge=0)
    allow_parallel_execution: bool = False


class ResumePolicyConfigView(RuntimeConfigBaseModel):
    """Resume and HITL policy configuration view."""

    enable_resume: bool = True
    enable_hitl: bool = False
    resume_storage_policy: str = "local"
    resume_token_ttl_seconds: int = Field(default=3600, gt=0)
    require_human_confirmation: bool = False

    @model_validator(mode="after")
    def validate_hitl_requires_resume(self) -> "ResumePolicyConfigView":
        """HITL requires resume support."""
        if self.enable_hitl and not self.enable_resume:
            raise ValueError("enable_hitl requires enable_resume")
        return self


class EventPolicyConfigView(RuntimeConfigBaseModel):
    """Event capture and output policy configuration view."""

    enable_event_stream: bool = True
    capture_node_events: bool = True
    capture_state_deltas: bool = True
    capture_artifact_deltas: bool = True
    event_sink_name: str = "local"


class ArtifactPolicyConfigView(RuntimeConfigBaseModel):
    """Artifact capture and publishing policy configuration view."""

    enable_artifact_capture: bool = True
    artifact_sink_name: str = "local"
    artifact_name_prefix: str = "ce-runtime"
    artifact_version_policy: str = "timestamp"


class AdapterSelectionConfigView(RuntimeConfigBaseModel):
    """Runtime adapter selection configuration view."""

    default_runtime_adapter: str = "local"
    adk_adapter_enabled: bool = False
    litellm_adapter_enabled: bool = False
    hermes_adapter_enabled: bool = False
    openclaw_adapter_enabled: bool = False
    fallback_adapter: str | None = "local"


class RuntimeConfigContextBundle(RuntimeConfigBaseModel):
    """Runtime-facing configuration context bundle."""

    runtime: RuntimeConfigView
    workflow_execution: WorkflowExecutionConfigView
    node_execution: NodeExecutionConfigView
    resume_policy: ResumePolicyConfigView
    event_policy: EventPolicyConfigView
    artifact_policy: ArtifactPolicyConfigView
    adapter_selection: AdapterSelectionConfigView
