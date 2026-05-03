from pathlib import Path

from composition.runtime import (
    RuntimeCompositionOptions,
    build_runtime_config_context,
    build_standard_runtime_runner,
)
from schemas.runtime import (
    InvocationRef,
    RuntimeEvent,
    RuntimeInput,
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
            metadata={"source": "fake-workflow-runner"},
        )


class FakeEventPublisher:
    def __init__(self) -> None:
        self.events: list[RuntimeEvent] = []

    def publish_event(self, event: RuntimeEvent) -> None:
        self.events.append(event)


def test_build_runtime_config_context_from_project_config() -> None:
    bundle = build_runtime_config_context(
        RuntimeCompositionOptions(config_root=Path("config"), environment="local"),
    )

    assert bundle.runtime.runtime_name == "local-runtime"
    assert bundle.workflow_execution.workflow_name == "insight-to-decision"
    assert bundle.node_execution.max_retries == 1
    assert bundle.artifact_policy.artifact_name_prefix == "ce-runtime-local"


def test_build_standard_runtime_runner_composes_runtime_chain() -> None:
    runner = build_standard_runtime_runner(
        options=RuntimeCompositionOptions(config_root=Path("config"), environment="local"),
        workflow_runner=FakeWorkflowRunner(),
    )

    result = runner.run(
        RuntimeInput(
            runtime_id="rt-1",
            workflow_ref=WorkflowRef(workflow_id="wf-1"),
            invocation_ref=InvocationRef(invocation_id="inv-1"),
            input_payload={"message": "hello"},
        ),
    )

    assert result.status == RuntimeStatus.SUCCESS
    assert result.runtime_id == "rt-1"
    assert result.metadata["runtime_name"] == "local-runtime"
    assert result.workflow_result is not None
    assert result.workflow_result.metadata["source"] == "fake-workflow-runner"


def test_build_standard_runtime_runner_injects_event_publisher() -> None:
    publisher = FakeEventPublisher()
    runner = build_standard_runtime_runner(
        options=RuntimeCompositionOptions(config_root=Path("config"), environment="local"),
        workflow_runner=FakeWorkflowRunner(),
        event_publisher=publisher,
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
