"""WorkflowRunner implementation backed by Google ADK."""

from __future__ import annotations

from typing import Any

from adk_adapter.artifact_mapper import AdkArtifactMapper
from adk_adapter.async_utils import run_sync
from adk_adapter.errors import error_record_from_exception
from adk_adapter.event_mapper import AdkEventMapper
from adk_adapter.invocation_mapper import AdkInvocationMapper
from adk_adapter.run_config import AdkRunConfigMapper, AdkRunConfigOptions
from adk_adapter.runner_service import AdkRunnerServiceAdapter, AdkRunnerServiceBundle
from adk_adapter.workflow_service import AdkWorkflowServiceAdapter
from behavior_contracts.runtime import WorkflowRunner
from schemas.runtime import (
    RuntimeStatus,
    WorkflowInput,
    WorkflowResult,
)

class AdkWorkflowRunner(WorkflowRunner):
    """Run an ADK workflow and return a standard WorkflowResult."""

    def __init__(
        self,
        *,
        workflow: Any,
        app_name: str = "cognition_engine_adk_adapter",
        user_id: str = "cognition-engine-adk-user",
        event_mapper: AdkEventMapper | None = None,
        invocation_mapper: AdkInvocationMapper | None = None,
        artifact_mapper: AdkArtifactMapper | None = None,
        workflow_service: AdkWorkflowServiceAdapter | None = None,
        runner_service: AdkRunnerServiceAdapter | None = None,
        service_bundle: AdkRunnerServiceBundle | None = None,
        artifact_service: Any | None = None,
        session_service: Any | None = None,
        run_config: Any | None = None,
        run_config_options: AdkRunConfigOptions | None = None,
    ) -> None:
        self._workflow = workflow
        self._app_name = app_name
        self._user_id = user_id
        self._event_mapper = event_mapper or AdkEventMapper()
        self._invocation_mapper = invocation_mapper or AdkInvocationMapper()
        self._artifact_mapper = artifact_mapper or AdkArtifactMapper()
        self._workflow_service = workflow_service or AdkWorkflowServiceAdapter(
            workflow=workflow,
            runner_service=runner_service,
            app_name=app_name,
            user_id=user_id,
            service_bundle=service_bundle
            or self._service_bundle_from_services(
                artifact_service=artifact_service,
                session_service=session_service,
            ),
            run_config=run_config,
            run_config_options=run_config_options,
        )
        self._run_config = run_config or self._workflow_service.runner_service.run_config

    def run_workflow(self, workflow_input: WorkflowInput) -> WorkflowResult:
        """Execute the configured ADK workflow through a sync contract method."""

        return run_sync(self._run_workflow_async(workflow_input))

    async def _run_workflow_async(self, workflow_input: WorkflowInput) -> WorkflowResult:
        from google.genai import types

        runner = self._workflow_service.create_runner()
        session = await self._workflow_service.runner_service.create_session()
        message = types.Content(
            role="user",
            parts=[types.Part(text=self._message_text(workflow_input))],
        )

        events: list[Any] = []
        try:
            async for event in runner.run_async(
                user_id=self._user_id,
                session_id=session.id,
                invocation_id=workflow_input.invocation_ref.invocation_id,
                new_message=message,
                run_config=self._run_config,
                yield_user_message=True,
            ):
                events.append(event)
        except Exception as exc:  # noqa: BLE001
            return WorkflowResult(
                workflow_ref=workflow_input.workflow_ref,
                status=RuntimeStatus.FAILED,
                invocation_ref=workflow_input.invocation_ref,
                errors=[
                    error_record_from_exception(
                        exc,
                        invocation_ref=workflow_input.invocation_ref,
                        workflow_ref=workflow_input.workflow_ref,
                        metadata={"adapter": "adk_adapter"},
                    )
                ],
                metadata={
                    **workflow_input.metadata,
                    "adapter": "adk_adapter",
                    "workflow_service": self._workflow_service.metadata(),
                    "app_name": self._app_name,
                    "user_id": self._user_id,
                    "session_id": session.id,
                    "run_config": AdkRunConfigMapper().metadata(self._run_config),
                    "requested_invocation_id": workflow_input.invocation_ref.invocation_id,
                },
            )

        binding = self._invocation_mapper.bind_from_events(
            requested_invocation_id=workflow_input.invocation_ref.invocation_id,
            events=events,
            session_id=session.id,
            app_name=self._app_name,
            user_id=self._user_id,
            workflow_id=workflow_input.workflow_ref.workflow_id,
        )
        invocation_ref = self._invocation_mapper.merge_into_invocation_ref(
            workflow_input.invocation_ref,
            binding,
        )
        runtime_events = [
            self._event_mapper.map_event(
                event,
                invocation_ref=invocation_ref,
                workflow_ref=workflow_input.workflow_ref,
                invocation_binding=binding,
            )
            for event in events
        ]
        errors = [
            error
            for event in events
            if (
                error := self._event_mapper.map_error_record(
                    event,
                    invocation_ref=invocation_ref,
                    workflow_ref=workflow_input.workflow_ref,
                    invocation_binding=binding,
                )
            )
            is not None
        ]
        artifact_deltas = [
            artifact_delta
            for event in events
            for artifact_delta in self._artifact_mapper.map_event_artifact_deltas(
                event,
                invocation_ref=invocation_ref,
                invocation_binding=binding,
            )
        ]

        return WorkflowResult(
            workflow_ref=workflow_input.workflow_ref,
            status=RuntimeStatus.FAILED if errors else RuntimeStatus.SUCCESS,
            invocation_ref=invocation_ref,
            events=runtime_events,
            artifact_deltas=artifact_deltas,
            errors=errors,
            metadata={
                **workflow_input.metadata,
                "adapter": "adk_adapter",
                "workflow_service": self._workflow_service.metadata(),
                "app_name": self._app_name,
                "user_id": self._user_id,
                "session_id": session.id,
                "run_config": AdkRunConfigMapper().metadata(self._run_config),
                "event_count": len(events),
                "requested_invocation_id": binding.requested_invocation_id,
                "adk_invocation_id": binding.adk_invocation_id,
                "adk_invocation_binding": binding.to_metadata(),
            },
        )

    def _message_text(self, workflow_input: WorkflowInput) -> str:
        payload = workflow_input.input_payload
        for key in ("message", "text", "prompt"):
            value = payload.get(key)
            if isinstance(value, str):
                return value
        return str(payload or "")

    def _service_bundle_from_services(
        self,
        *,
        artifact_service: Any | None,
        session_service: Any | None,
    ) -> AdkRunnerServiceBundle | None:
        if artifact_service is None and session_service is None:
            return None
        return AdkRunnerServiceAdapter(
            workflow=self._workflow,
            app_name=self._app_name,
            user_id=self._user_id,
            artifact_service=artifact_service,
            session_service=session_service,
        ).service_bundle
