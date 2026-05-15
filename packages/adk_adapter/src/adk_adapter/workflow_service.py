"""Workflow service adapter for ADK 2 Workflow/BaseNode main chain."""

from __future__ import annotations

from typing import Any

from adk_adapter.run_config import AdkRunConfigOptions
from adk_adapter.runner_service import AdkRunnerServiceAdapter, AdkRunnerServiceBundle


class AdkWorkflowServiceAdapter:
    """Adapt an ADK Workflow/BaseNode into a runner-backed service entry."""

    def __init__(
        self,
        *,
        workflow: Any,
        runner_service: AdkRunnerServiceAdapter | None = None,
        app_name: str = "cognition_engine_adk_adapter",
        user_id: str = "cognition-engine-adk-user",
        service_bundle: AdkRunnerServiceBundle | None = None,
        run_config: Any | None = None,
        run_config_options: AdkRunConfigOptions | None = None,
    ) -> None:
        self.workflow = workflow
        self.app_name = app_name
        self.user_id = user_id
        self.runner_service = runner_service or AdkRunnerServiceAdapter(
            workflow=workflow,
            app_name=app_name,
            user_id=user_id,
            service_bundle=service_bundle,
            run_config=run_config,
            run_config_options=run_config_options,
        )

    @property
    def service_bundle(self) -> AdkRunnerServiceBundle:
        """Return services injected into the workflow runner chain."""

        return self.runner_service.service_bundle

    def create_runner(self) -> Any:
        """Create a real ADK Runner for this workflow service."""

        return self.runner_service.create_runner()

    def metadata(self) -> dict[str, Any]:
        """Return workflow adapter metadata without leaking ADK objects."""

        return {
            "adapter": "adk_adapter.workflow_service",
            "workflow_type": type(self.workflow).__name__,
            "workflow_name": getattr(self.workflow, "name", None),
            "app_name": self.app_name,
            "user_id": self.user_id,
            "runner_service": self.runner_service.metadata(),
        }
