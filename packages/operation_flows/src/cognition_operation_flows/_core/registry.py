"""Candidate registry for channel-neutral operation flow descriptors."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cognition_operation_flows._core.descriptors import OperationFlowDescriptorCandidate


class OperationFlowRegistryCandidate(BaseModel):
    """Read-only candidate registry for operation flow descriptors."""

    model_config = ConfigDict(extra="forbid")

    candidate_only: bool = True
    workflow_execution_enabled: bool = False
    descriptors: tuple[OperationFlowDescriptorCandidate, ...] = Field(
        default_factory=tuple
    )

    @model_validator(mode="after")
    def validate_registry_boundary(self) -> "OperationFlowRegistryCandidate":
        if self.candidate_only is not True:
            raise ValueError("candidate_only must remain true.")
        if self.workflow_execution_enabled:
            raise ValueError("workflow_execution_enabled must remain false.")
        workflow_ids = [descriptor.workflow_id for descriptor in self.descriptors]
        if len(workflow_ids) != len(set(workflow_ids)):
            raise ValueError("workflow_id values must be unique.")
        return self


def build_operation_flow_registry_candidate(
    descriptors: tuple[OperationFlowDescriptorCandidate, ...]
    | list[OperationFlowDescriptorCandidate],
) -> OperationFlowRegistryCandidate:
    """Build a read-only candidate registry."""

    return OperationFlowRegistryCandidate(descriptors=tuple(descriptors))


def resolve_operation_flow_descriptor_candidate(
    registry: OperationFlowRegistryCandidate,
    workflow_id: str,
) -> OperationFlowDescriptorCandidate | None:
    """Resolve a descriptor by id without executing a workflow."""

    for descriptor in registry.descriptors:
        if descriptor.workflow_id == workflow_id:
            return descriptor
    return None
