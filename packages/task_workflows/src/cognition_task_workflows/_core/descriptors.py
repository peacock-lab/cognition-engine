"""Candidate descriptors for channel-neutral task workflows."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cognition_task_workflows._core.boundaries import (
    validate_task_workflow_metadata_boundary,
)


TaskWorkflowKindCandidate = Literal[
    "plan",
    "reference_review",
    "config_profile_explain",
    "run_workspace_evidence_audit",
    "custom_candidate",
]
TaskWorkflowExecutionBoundaryCandidate = Literal[
    "no_execution",
    "runtime_facade",
    "backend_task_service",
]


class TaskWorkflowDescriptorCandidate(BaseModel):
    """Channel-neutral descriptor for a candidate task workflow."""

    model_config = ConfigDict(extra="forbid")

    workflow_id: str = Field(..., min_length=1)
    workflow_name: str = Field(..., min_length=1)
    workflow_kind: TaskWorkflowKindCandidate
    version: str = "0.7.0"
    candidate_only: bool = True
    channel_neutral: bool = True
    owner_package: str = "cognition_task_workflows"
    product_gateway_entry_required: bool = True
    channel_private_workflow: bool = False
    product_gateway_owns_workflow: bool = False
    runtime_container_internal_workflow: bool = False
    workflow_execution_enabled: bool = False
    public_contract_enabled: bool = False
    execution_boundary: TaskWorkflowExecutionBoundaryCandidate = "no_execution"
    request_contract_ref: str | None = None
    result_contract_ref: str | None = None
    read_context_contract_ref: str | None = None
    evidence_summary_contract_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_descriptor_boundary(self) -> "TaskWorkflowDescriptorCandidate":
        if self.candidate_only is not True:
            raise ValueError("candidate_only must remain true.")
        if self.channel_neutral is not True:
            raise ValueError("channel_neutral must remain true.")
        if self.owner_package != "cognition_task_workflows":
            raise ValueError("owner_package must be cognition_task_workflows.")
        if self.product_gateway_entry_required is not True:
            raise ValueError("product_gateway_entry_required must remain true.")
        if self.channel_private_workflow:
            raise ValueError("task workflow must not be channel-private.")
        if self.product_gateway_owns_workflow:
            raise ValueError("product_gateway must not own workflow body.")
        if self.runtime_container_internal_workflow:
            raise ValueError("runtime_container must not own workflow body.")
        if self.workflow_execution_enabled:
            raise ValueError("workflow_execution_enabled must remain false.")
        if self.public_contract_enabled and not (
            self.request_contract_ref and self.result_contract_ref
        ):
            raise ValueError(
                "public_contract_enabled requires request_contract_ref and result_contract_ref."
            )
        if self.execution_boundary != "no_execution" and not self.workflow_execution_enabled:
            raise ValueError("execution boundary must stay no_execution while execution is disabled.")
        validate_task_workflow_metadata_boundary(self.metadata)
        return self


def build_task_workflow_descriptor_candidate(
    *,
    workflow_id: str,
    workflow_name: str,
    workflow_kind: TaskWorkflowKindCandidate,
    metadata: dict[str, Any] | None = None,
) -> TaskWorkflowDescriptorCandidate:
    """Build a minimal candidate descriptor without enabling execution."""

    return TaskWorkflowDescriptorCandidate(
        workflow_id=workflow_id,
        workflow_name=workflow_name,
        workflow_kind=workflow_kind,
        metadata=dict(metadata or {}),
    )
