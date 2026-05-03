from __future__ import annotations

from pathlib import Path
from typing import Any

from adk_adapter import AdkWorkflowRunner
from runtime_container import runtime as runtime_facade
from schemas.runtime import InvocationRef, RuntimeInput, RuntimeStatus, WorkflowRef


def test_runtime_container_facade_runs_real_adk_workflow_through_adk_adapter() -> None:
    from google.adk.agents.context import Context
    from google.adk.events import Event
    from google.adk.events.event import NodeInfo
    from google.adk.workflow import START, BaseNode, Workflow

    class MinimalNode(BaseNode):
        async def _run_impl(self, *, ctx: Context, node_input: Any):
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                node_info=NodeInfo(path=ctx.node_path),
                output={"ok": True, "node": self.name, "echo": "hello from adk"},
            )

    workflow = Workflow(
        name="minimal_runtime_container_workflow",
        edges=[(START, MinimalNode(name="minimal_node"))],
    )
    adk_workflow_runner = AdkWorkflowRunner(
        workflow=workflow,
        app_name="test_runtime_container_adk",
        user_id="runtime-container-test-user",
    )

    runtime_runner = runtime_facade.build_standard_runtime_runner(
        options=runtime_facade.RuntimeCompositionOptions(
            config_root=Path("config"),
            environment="local",
        ),
        workflow_runner=adk_workflow_runner,
    )

    runtime_result = runtime_runner.run(
        RuntimeInput(
            runtime_id="runtime-adk-001",
            workflow_ref=WorkflowRef(
                workflow_id="workflow-adk-001",
                name="minimal_runtime_container_workflow",
            ),
            invocation_ref=InvocationRef(invocation_id="requested-rt-001"),
            input_payload={"message": "hello from runtime container"},
            metadata={"requested_invocation_id": "requested-rt-001"},
        )
    )

    assert isinstance(runtime_runner, runtime_facade.StandardRuntimeRunner)
    assert runtime_result.status == RuntimeStatus.SUCCESS
    assert runtime_result.runtime_id == "runtime-adk-001"
    assert runtime_result.workflow_result is not None
    assert runtime_result.workflow_result.status == RuntimeStatus.SUCCESS
    assert runtime_result.metadata["runtime_name"] == "local-runtime"
    assert runtime_result.metadata["default_adapter"] == "local"

    workflow_result = runtime_result.workflow_result
    assert workflow_result.metadata["adapter"] == "adk_adapter"
    assert workflow_result.metadata["requested_invocation_id"] == "requested-rt-001"
    assert workflow_result.metadata["adk_invocation_id"]
    assert workflow_result.metadata["session_id"]
    assert workflow_result.metadata["event_count"] >= 2

    assert runtime_result.events
    assert len(runtime_result.events) >= 2
    assert any(event.metadata["adk_invocation_id"] for event in runtime_result.events)
    assert any(event.metadata["author"] == "minimal_runtime_container_workflow" for event in runtime_result.events)
    assert any(event.metadata["node_path"] == "minimal_runtime_container_workflow@1/minimal_node@1" for event in runtime_result.events)
    assert any(
        event.payload["output"] == {"ok": True, "node": "minimal_node", "echo": "hello from adk"}
        for event in runtime_result.events
    )

    binding_metadata = workflow_result.metadata["adk_invocation_binding"]
    assert binding_metadata["requested_invocation_id"] == "requested-rt-001"
    assert binding_metadata["adk_invocation_id"]
    assert workflow_result.invocation_ref.metadata["adk_invocation_binding"]["adk_invocation_id"]
