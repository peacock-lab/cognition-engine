"""Candidate registry for channel-neutral task workflow descriptors."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cognition_task_workflows._core.descriptors import TaskWorkflowDescriptorCandidate


class TaskWorkflowRegistryCandidate(BaseModel):
    """Read-only candidate registry for task workflow descriptors."""

    model_config = ConfigDict(extra="forbid")

    candidate_only: bool = True
    workflow_execution_enabled: bool = False
    descriptors: tuple[TaskWorkflowDescriptorCandidate, ...] = Field(
        default_factory=tuple
    )

    @model_validator(mode="after")
    def validate_registry_boundary(self) -> "TaskWorkflowRegistryCandidate":
        if self.candidate_only is not True:
            raise ValueError("candidate_only must remain true.")
        if self.workflow_execution_enabled:
            raise ValueError("workflow_execution_enabled must remain false.")
        workflow_ids = [descriptor.workflow_id for descriptor in self.descriptors]
        if len(workflow_ids) != len(set(workflow_ids)):
            raise ValueError("workflow_id values must be unique.")
        return self


def build_task_workflow_registry_candidate(
    descriptors: tuple[TaskWorkflowDescriptorCandidate, ...]
    | list[TaskWorkflowDescriptorCandidate],
) -> TaskWorkflowRegistryCandidate:
    """Build a read-only candidate registry."""

    return TaskWorkflowRegistryCandidate(descriptors=tuple(descriptors))


def resolve_task_workflow_descriptor_candidate(
    registry: TaskWorkflowRegistryCandidate,
    workflow_id: str,
) -> TaskWorkflowDescriptorCandidate | None:
    """Resolve a descriptor by id without executing a workflow."""

    for descriptor in registry.descriptors:
        if descriptor.workflow_id == workflow_id:
            return descriptor
    return None
