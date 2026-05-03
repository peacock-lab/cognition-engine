from config_contexts.runtime import (
    AdapterSelectionConfigView,
    ArtifactPolicyConfigView,
    EventPolicyConfigView,
    NodeExecutionConfigView,
    ResumePolicyConfigView,
    RuntimeConfigContextBundle,
    RuntimeConfigView,
    WorkflowExecutionConfigView,
)
from runtime.orchestrator import RuntimeDependencies, StandardRuntimeRunner
from schemas.runtime import (
    InvocationRef,
    RuntimeEvent,
    RuntimeInput,
    RuntimeResult,
    RuntimeStatus,
    WorkflowRef,
    WorkflowResult,
)


class FakeWorkflowRunner:
    def run_workflow(self, workflow_input):
        return WorkflowResult(
            workflow_ref=workflow_input.workflow_ref,
            status=RuntimeStatus.SUCCESS,
            invocation_ref=workflow_input.invocation_ref,
            metadata={"workflow": "fake"},
        )


class FakeInvocationTracker:
    def next_invocation_id(self) -> str:
        return "generated-invocation"


class FakeEventPublisher:
    def __init__(self) -> None:
        self.events: list[RuntimeEvent] = []

    def publish_event(self, event: RuntimeEvent) -> None:
        self.events.append(event)


def build_config_context() -> RuntimeConfigContextBundle:
    return RuntimeConfigContextBundle(
        runtime=RuntimeConfigView(runtime_name="test-runtime"),
        workflow_execution=WorkflowExecutionConfigView(workflow_name="test-workflow"),
        node_execution=NodeExecutionConfigView(),
        resume_policy=ResumePolicyConfigView(),
        event_policy=EventPolicyConfigView(),
        artifact_policy=ArtifactPolicyConfigView(),
        adapter_selection=AdapterSelectionConfigView(),
    )


def test_standard_runtime_runner_returns_runtime_result() -> None:
    runner = StandardRuntimeRunner(
        config_context=build_config_context(),
        dependencies=RuntimeDependencies(workflow_runner=FakeWorkflowRunner()),
    )

    result = runner.run(
        RuntimeInput(
            runtime_id="rt-1",
            workflow_ref=WorkflowRef(workflow_id="wf-1"),
            invocation_ref=InvocationRef(invocation_id="inv-1"),
            input_payload={"hello": "world"},
        ),
    )

    assert isinstance(result, RuntimeResult)
    assert result.runtime_id == "rt-1"
    assert result.status == RuntimeStatus.SUCCESS
    assert result.workflow_result is not None
    assert result.metadata["runtime_name"] == "test-runtime"
    assert result.metadata["default_adapter"] == "local"


def test_standard_runtime_runner_uses_injected_invocation_tracker() -> None:
    runner = StandardRuntimeRunner(
        config_context=build_config_context(),
        dependencies=RuntimeDependencies(
            workflow_runner=FakeWorkflowRunner(),
            invocation_tracker=FakeInvocationTracker(),
        ),
    )

    result = runner.run(
        RuntimeInput(
            runtime_id="rt-1",
            workflow_ref=WorkflowRef(workflow_id="wf-1"),
            invocation_ref=InvocationRef(invocation_id="original-invocation"),
        ),
    )

    assert result.invocation_ref.invocation_id == "generated-invocation"


def test_standard_runtime_runner_publishes_runtime_events() -> None:
    publisher = FakeEventPublisher()
    runner = StandardRuntimeRunner(
        config_context=build_config_context(),
        dependencies=RuntimeDependencies(
            workflow_runner=FakeWorkflowRunner(),
            event_publisher=publisher,
        ),
    )

    runner.run(
        RuntimeInput(
            runtime_id="rt-1",
            workflow_ref=WorkflowRef(workflow_id="wf-1"),
            invocation_ref=InvocationRef(invocation_id="inv-1"),
        ),
    )

    assert [event.event_type.value for event in publisher.events] == [
        "runtime_started",
        "runtime_completed",
    ]
