from __future__ import annotations

from pathlib import Path
from typing import Any

from adk_adapter import AdkRunConfigOptions, AdkRunnerServiceBundleOptions
from composition.adk_workflow_runner_assembly import (
    AdkWorkflowRunnerAssemblyOptions,
    AdkWorkflowRunnerRuntimeAssembly,
    build_adk_workflow_runner_runtime,
)
from composition.runtime import RuntimeCompositionOptions
from runtime.orchestrator import StandardRuntimeRunner
from schemas.runtime import InvocationRef, RuntimeInput, RuntimeStatus, WorkflowRef


def test_runtime_container_facade_builds_adk2_workflow_runner_runtime() -> None:
    from google.adk.agents.context import Context
    from google.adk.events import Event
    from google.adk.events.event import NodeInfo
    from google.adk.workflow import START, BaseNode, Workflow
    from google.genai import types

    class RuntimeContainerArtifactNode(BaseNode):
        async def _run_impl(self, *, ctx: Context, node_input: Any):
            version = await ctx.save_artifact(
                "runtime-container-output.txt",
                types.Part(text="runtime container artifact payload"),
                custom_metadata={"source": "runtime-container-provider-test"},
            )
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                node_info=NodeInfo(path=ctx.node_path),
                output={
                    "version": version,
                    "keys": await ctx.list_artifacts(),
                    "max_llm_calls": ctx.run_config.max_llm_calls,
                    "run_config_source": ctx.run_config.custom_metadata["source"],
                },
            )

    workflow = Workflow(
        name="runtime_container_adk2_workflow",
        edges=[(START, RuntimeContainerArtifactNode(name="runtime_container_node"))],
    )
    assembly_options = AdkWorkflowRunnerAssemblyOptions(
        app_name="test_runtime_container_adk2_options",
        user_id="runtime-container-options-user",
        workflow_name="runtime-container-options-workflow",
        service_bundle_options=AdkRunnerServiceBundleOptions(source="in_memory"),
        run_config_options=AdkRunConfigOptions(
            max_llm_calls=13,
            custom_metadata={"source": "runtime-container-options-test"},
            streaming_mode="none",
        ),
        metadata={"test_case": "runtime-container-options"},
    )
    assembly = build_adk_workflow_runner_runtime(
        options=RuntimeCompositionOptions(
            config_root=Path("config"),
            environment="local",
        ),
        workflow=workflow,
        assembly_options=assembly_options,
    )

    runtime_result = assembly.runtime_runner.run(
        RuntimeInput(
            runtime_id="runtime-container-adk2-001",
            workflow_ref=WorkflowRef(workflow_id="workflow-runtime-container-adk2-001"),
            invocation_ref=InvocationRef(invocation_id="inv-runtime-container-adk2-001"),
            input_payload={"message": "hello"},
        )
    )
    workflow_result = runtime_result.workflow_result
    session_id = workflow_result.metadata["session_id"]

    loaded_artifact = assembly.service_bundle.artifact_service.load_artifact_sync(
        filename="runtime-container-output.txt",
        session_id=session_id,
    )
    loaded_session = assembly.service_bundle.session_service.get_session_sync(
        session_id=session_id,
    )

    assert isinstance(assembly, AdkWorkflowRunnerRuntimeAssembly)
    assert isinstance(assembly.runtime_runner, StandardRuntimeRunner)
    assert runtime_result.status == RuntimeStatus.SUCCESS
    assert workflow_result.status == RuntimeStatus.SUCCESS
    assert workflow_result.metadata["workflow_service"]["runner_service"]["adk_runner_type"] == (
        "Runner"
    )
    assert workflow_result.metadata["workflow_service"]["runner_service"]["run_config"][
        "max_llm_calls"
    ] == 13
    assert workflow_result.metadata["run_config"]["custom_metadata_keys"] == ["source"]
    assert assembly.metadata["assembly_options"]["metadata_keys"] == ["test_case"]
    assert workflow_result.artifact_deltas[0].artifact_ref.artifact_id == (
        "runtime-container-output.txt"
    )
    assert any(
        event.payload["output"]
        and event.payload["output"].get("max_llm_calls") == 13
        and event.payload["output"].get("run_config_source")
        == "runtime-container-options-test"
        for event in workflow_result.events
    )
    assert loaded_artifact.text == "runtime container artifact payload"
    assert loaded_session.id == session_id
    assert len(loaded_session.events) >= 2
    assert "cognition_governance" not in repr(assembly.metadata)
