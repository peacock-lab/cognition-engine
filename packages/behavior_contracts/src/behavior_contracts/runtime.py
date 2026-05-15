"""Runtime-facing behavior contracts for Cognition Engine."""

from __future__ import annotations

from typing import Protocol

from schemas.runtime import (
    AdkServiceFactsSummaryInput,
    ArtifactDelta,
    NodeExecutionInput,
    NodeExecutionResult,
    RecordedRunEvidenceInput,
    ResumePoint,
    RuntimeEvent,
    RuntimeInput,
    RuntimeResult,
    StateDelta,
    WorkflowInput,
    WorkflowResult,
)


class RuntimeRunner(Protocol):
    """Contract for executing one runtime task."""

    def run(self, runtime_input: RuntimeInput) -> RuntimeResult:
        """Execute a runtime task."""


class WorkflowRunner(Protocol):
    """Contract for executing a workflow."""

    def run_workflow(self, workflow_input: WorkflowInput) -> WorkflowResult:
        """Execute a workflow."""


class NodeRunner(Protocol):
    """Contract for executing one node."""

    def run_node(self, node_input: NodeExecutionInput) -> NodeExecutionResult:
        """Execute a node."""


class NodeScheduler(Protocol):
    """Contract for scheduling node execution."""

    def schedule_nodes(
        self,
        workflow_input: WorkflowInput,
    ) -> list[NodeExecutionInput]:
        """Schedule nodes for a workflow input."""


class ResumeController(Protocol):
    """Contract for resuming runtime execution."""

    def resume(self, resume_point: ResumePoint) -> RuntimeResult:
        """Resume execution from a resume point."""


class RuntimeEventPublisher(Protocol):
    """Contract for publishing runtime events."""

    def publish_event(self, event: RuntimeEvent) -> None:
        """Publish a runtime event."""


class RuntimeArtifactPublisher(Protocol):
    """Contract for publishing runtime artifact deltas."""

    def publish_artifact_delta(self, artifact_delta: ArtifactDelta) -> None:
        """Publish an artifact delta."""


class RuntimeStatePublisher(Protocol):
    """Contract for publishing runtime state deltas."""

    def publish_state_delta(self, state_delta: StateDelta) -> None:
        """Publish a state delta."""


class InvocationTracker(Protocol):
    """Contract for tracking invocation identity."""

    def next_invocation_id(self) -> str:
        """Return the next invocation id."""


class RecordedRunEvidenceProvider(Protocol):
    """Contract for converting recorded runtime facts into recorded-run evidence."""

    def build_recorded_run_evidence(
        self,
        runtime_result: RuntimeResult,
    ) -> RecordedRunEvidenceInput:
        """Build recorded-run evidence facts from a runtime result."""


class AdkServiceFactsProvider(Protocol):
    """Contract for converting recorded runtime facts into ADK service facts."""

    def build_adk_service_facts(
        self,
        runtime_result: RuntimeResult,
    ) -> AdkServiceFactsSummaryInput:
        """Build ADK service facts from a runtime result."""
