from __future__ import annotations

from typing import Any

from adk_adapter import (
    AdkRunnerServiceAdapter,
    AdkRunnerServiceBundle,
    AdkRunnerServiceBundleOptions,
    AdkWorkflowRunner,
    AdkWorkflowServiceAdapter,
)
from schemas.runtime import InvocationRef, RuntimeStatus, WorkflowInput, WorkflowRef


def test_runner_and_workflow_services_inject_artifact_session_services() -> None:
    from google.adk.agents.context import Context
    from google.adk.events import Event
    from google.adk.events.event import NodeInfo
    from google.adk.workflow import START, BaseNode, Workflow
    from google.genai import types

    class ArtifactWritingNode(BaseNode):
        async def _run_impl(self, *, ctx: Context, node_input: Any):
            version = await ctx.save_artifact(
                "workflow-output.txt",
                types.Part(text="written by workflow node"),
                custom_metadata={"source": "runner-workflow-service-test"},
            )
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                node_info=NodeInfo(path=ctx.node_path),
                output={
                    "version": version,
                    "artifact_keys": await ctx.list_artifacts(),
                },
            )

    service_bundle = AdkRunnerServiceBundle.in_memory(
        app_name="test_adk_adapter",
        user_id="test-user",
    )
    workflow = Workflow(
        name="artifact_session_injection_workflow",
        edges=[(START, ArtifactWritingNode(name="artifact_writer"))],
    )
    runner_service = AdkRunnerServiceAdapter(
        workflow=workflow,
        app_name="test_adk_adapter",
        user_id="test-user",
        service_bundle=service_bundle,
    )
    workflow_service = AdkWorkflowServiceAdapter(
        workflow=workflow,
        runner_service=runner_service,
        app_name="test_adk_adapter",
        user_id="test-user",
    )

    adk_runner = workflow_service.create_runner()

    assert adk_runner.agent is workflow
    assert adk_runner.artifact_service is service_bundle.adk_artifact_service
    assert adk_runner.session_service is service_bundle.adk_session_service

    result = AdkWorkflowRunner(
        workflow=workflow,
        app_name="test_adk_adapter",
        user_id="test-user",
        workflow_service=workflow_service,
    ).run_workflow(
        WorkflowInput(
            workflow_ref=WorkflowRef(
                workflow_id="workflow-001",
                name="artifact-session-injection",
            ),
            invocation_ref=InvocationRef(invocation_id="requested-001"),
            input_payload={"message": "hello"},
        )
    )

    session_id = result.metadata["session_id"]
    loaded_session = service_bundle.session_service.get_session_sync(session_id=session_id)
    loaded_artifact = service_bundle.artifact_service.load_artifact_sync(
        filename="workflow-output.txt",
        session_id=session_id,
    )

    assert result.status == RuntimeStatus.SUCCESS
    assert result.metadata["workflow_service"]["adapter"] == "adk_adapter.workflow_service"
    assert result.artifact_deltas[0].artifact_ref.artifact_id == "workflow-output.txt"
    assert loaded_session.id == session_id
    assert len(loaded_session.events) >= 2
    assert loaded_artifact.text == "written by workflow node"


def test_service_bundle_options_wrap_provided_adk_services() -> None:
    from google.adk.artifacts import InMemoryArtifactService
    from google.adk.sessions import InMemorySessionService

    artifact_service = InMemoryArtifactService()
    session_service = InMemorySessionService()

    bundle = AdkRunnerServiceBundleOptions(
        source="provided_services",
        artifact_service=artifact_service,
        session_service=session_service,
        artifact_service_label="provided-artifacts",
        session_service_label="provided-sessions",
    ).build_service_bundle(app_name="provided-app", user_id="provided-user")

    assert bundle.adk_artifact_service is artifact_service
    assert bundle.adk_session_service is session_service
    assert bundle.metadata()["artifact_service"]["adk_service_type"] == (
        "InMemoryArtifactService"
    )
