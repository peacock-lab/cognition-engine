"""Runtime orchestration implementation for Cognition Engine."""

from __future__ import annotations

from dataclasses import dataclass

from behavior_contracts.runtime import (
    InvocationTracker,
    RuntimeEventPublisher,
    RuntimeRunner,
    WorkflowRunner,
)
from config_contexts.runtime import RuntimeConfigContextBundle
from schemas.runtime import (
    InvocationRef,
    RuntimeEvent,
    RuntimeEventType,
    RuntimeInput,
    RuntimeResult,
    RuntimeStatus,
    WorkflowInput,
)


@dataclass(frozen=True)
class RuntimeDependencies:
    """Injected runtime dependencies."""

    workflow_runner: WorkflowRunner
    invocation_tracker: InvocationTracker | None = None
    event_publisher: RuntimeEventPublisher | None = None


class StandardRuntimeRunner(RuntimeRunner):
    """Standard runtime runner that orchestrates execution by contracts."""

    def __init__(
        self,
        *,
        config_context: RuntimeConfigContextBundle,
        dependencies: RuntimeDependencies,
    ) -> None:
        self._config_context = config_context
        self._dependencies = dependencies

    def run(self, runtime_input: RuntimeInput) -> RuntimeResult:
        """Execute runtime input through injected workflow runner."""

        invocation_ref = self._resolve_invocation_ref(runtime_input)

        self._publish_runtime_event(
            RuntimeEvent(
                event_id=f"{invocation_ref.invocation_id}:runtime_started",
                event_type=RuntimeEventType.RUNTIME_STARTED,
                invocation_ref=invocation_ref,
                workflow_ref=runtime_input.workflow_ref,
                payload={
                    "runtime_id": runtime_input.runtime_id,
                    "runtime_name": self._config_context.runtime.runtime_name,
                },
            ),
        )

        workflow_result = self._dependencies.workflow_runner.run_workflow(
            WorkflowInput(
                workflow_ref=runtime_input.workflow_ref,
                invocation_ref=invocation_ref,
                input_payload=runtime_input.input_payload,
                config_context_ref=runtime_input.config_context_ref,
                metadata=runtime_input.metadata,
            ),
        )

        result_status = (
            RuntimeStatus.SUCCESS
            if workflow_result.status == RuntimeStatus.SUCCESS
            else workflow_result.status
        )

        self._publish_runtime_event(
            RuntimeEvent(
                event_id=f"{invocation_ref.invocation_id}:runtime_completed",
                event_type=RuntimeEventType.RUNTIME_COMPLETED,
                invocation_ref=invocation_ref,
                workflow_ref=runtime_input.workflow_ref,
                payload={
                    "runtime_id": runtime_input.runtime_id,
                    "status": result_status.value,
                },
            ),
        )

        return RuntimeResult(
            runtime_id=runtime_input.runtime_id,
            status=result_status,
            invocation_ref=invocation_ref,
            workflow_result=workflow_result,
            events=workflow_result.events,
            state_deltas=workflow_result.state_deltas,
            artifact_deltas=workflow_result.artifact_deltas,
            errors=workflow_result.errors,
            metadata={
                **runtime_input.metadata,
                "runtime_name": self._config_context.runtime.runtime_name,
                "execution_mode": self._config_context.runtime.execution_mode.value,
                "default_adapter": self._config_context.runtime.default_adapter,
            },
        )

    def _resolve_invocation_ref(self, runtime_input: RuntimeInput) -> InvocationRef:
        """Resolve invocation reference without mutating the input object."""

        if self._dependencies.invocation_tracker is None:
            return runtime_input.invocation_ref

        invocation_id = self._dependencies.invocation_tracker.next_invocation_id()

        return InvocationRef(
            invocation_id=invocation_id,
            runtime_id=runtime_input.runtime_id,
            workflow_id=runtime_input.workflow_ref.workflow_id,
            source="runtime",
            metadata=runtime_input.invocation_ref.metadata,
        )

    def _publish_runtime_event(self, event: RuntimeEvent) -> None:
        """Publish runtime event if an event publisher is injected."""

        if self._dependencies.event_publisher is not None:
            self._dependencies.event_publisher.publish_event(event)
