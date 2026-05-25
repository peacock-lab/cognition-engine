"""Candidate descriptors for channel-neutral operation flows."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cognition_operation_flows._core.boundaries import (
    validate_operation_flow_metadata_boundary,
)


OperationFlowKindCandidate = Literal[
    "plan",
    "reference_review",
    "config_profile_explain",
    "run_workspace_evidence_audit",
    "custom_candidate",
]
OperationFlowExecutionBoundaryCandidate = Literal[
    "no_execution",
    "runtime_facade",
    "backend_task_service",
]


class OperationFlowDescriptorCandidate(BaseModel):
    """Channel-neutral descriptor for a candidate operation flow."""

    model_config = ConfigDict(extra="forbid")

    workflow_id: str = Field(..., min_length=1)
    workflow_name: str = Field(..., min_length=1)
    workflow_kind: OperationFlowKindCandidate
    version: str = "0.7.0"
    candidate_only: bool = True
    channel_neutral: bool = True
    owner_package: str = "cognition_operation_flows"
    product_gateway_entry_required: bool = True
    channel_private_workflow: bool = False
    product_gateway_owns_workflow: bool = False
    runtime_container_internal_workflow: bool = False
    workflow_execution_enabled: bool = False
    public_contract_enabled: bool = False
    execution_boundary: OperationFlowExecutionBoundaryCandidate = "no_execution"
    request_contract_ref: str | None = None
    result_contract_ref: str | None = None
    read_context_contract_ref: str | None = None
    evidence_summary_contract_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_descriptor_boundary(self) -> "OperationFlowDescriptorCandidate":
        if self.candidate_only is not True:
            raise ValueError("candidate_only must remain true.")
        if self.channel_neutral is not True:
            raise ValueError("channel_neutral must remain true.")
        if self.owner_package != "cognition_operation_flows":
            raise ValueError("owner_package must be cognition_operation_flows.")
        if self.product_gateway_entry_required is not True:
            raise ValueError("product_gateway_entry_required must remain true.")
        if self.channel_private_workflow:
            raise ValueError("operation flow must not be channel-private.")
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
        validate_operation_flow_metadata_boundary(self.metadata)
        return self


def build_operation_flow_descriptor_candidate(
    *,
    workflow_id: str,
    workflow_name: str,
    workflow_kind: OperationFlowKindCandidate,
    metadata: dict[str, Any] | None = None,
) -> OperationFlowDescriptorCandidate:
    """Build a minimal candidate descriptor without enabling execution."""

    return OperationFlowDescriptorCandidate(
        workflow_id=workflow_id,
        workflow_name=workflow_name,
        workflow_kind=workflow_kind,
        metadata=dict(metadata or {}),
    )
