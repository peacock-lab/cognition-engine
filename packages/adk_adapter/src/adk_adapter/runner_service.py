"""Runner service adapter for ADK Workflow/BaseNode execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from adk_adapter.artifact_service import AdkArtifactServiceAdapter
from adk_adapter.run_config import AdkRunConfigMapper, AdkRunConfigOptions
from adk_adapter.session_service import AdkSessionServiceAdapter


@dataclass(frozen=True)
class AdkRunnerServiceBundleOptions:
    """Local options for choosing ADK service bundle sources."""

    source: str = "in_memory"
    artifact_service: Any | None = None
    session_service: Any | None = None
    artifact_service_label: str | None = None
    session_service_label: str | None = None

    def build_service_bundle(
        self,
        *,
        app_name: str = "cognition_engine_adk_adapter",
        user_id: str = "cognition-engine-adk-user",
    ) -> "AdkRunnerServiceBundle":
        """Build an ADK runner service bundle from local options."""

        if self.source == "in_memory":
            return AdkRunnerServiceBundle.in_memory(app_name=app_name, user_id=user_id)
        if self.source == "provided_services":
            if self.artifact_service is None or self.session_service is None:
                raise ValueError(
                    "provided_services requires artifact_service and session_service"
                )
            return AdkRunnerServiceBundle.from_services(
                artifact_service=self.artifact_service,
                session_service=self.session_service,
                app_name=app_name,
                user_id=user_id,
            )
        raise ValueError(f"Unsupported ADK service bundle source: {self.source}")

    def metadata(self) -> dict[str, Any]:
        """Return a safe service source summary."""

        return {
            "options_type": "adk_adapter.runner_service.AdkRunnerServiceBundleOptions",
            "source": self.source,
            "artifact_service_source": self.artifact_service_label
            or self._source_type(self.artifact_service),
            "session_service_source": self.session_service_label
            or self._source_type(self.session_service),
        }

    def _source_type(self, value: Any | None) -> str | None:
        if value is None:
            return None
        return type(value).__name__


@dataclass(frozen=True)
class AdkRunnerServiceBundle:
    """ADK services injected into the Runner main chain."""

    artifact_service: AdkArtifactServiceAdapter
    session_service: AdkSessionServiceAdapter
    app_name: str = "cognition_engine_adk_adapter"
    user_id: str = "cognition-engine-adk-user"

    @classmethod
    def in_memory(
        cls,
        *,
        app_name: str = "cognition_engine_adk_adapter",
        user_id: str = "cognition-engine-adk-user",
    ) -> "AdkRunnerServiceBundle":
        """Create an in-memory ADK service bundle."""

        return cls(
            artifact_service=AdkArtifactServiceAdapter(app_name=app_name, user_id=user_id),
            session_service=AdkSessionServiceAdapter(app_name=app_name, user_id=user_id),
            app_name=app_name,
            user_id=user_id,
        )

    @classmethod
    def from_services(
        cls,
        *,
        artifact_service: AdkArtifactServiceAdapter | Any,
        session_service: AdkSessionServiceAdapter | Any,
        app_name: str = "cognition_engine_adk_adapter",
        user_id: str = "cognition-engine-adk-user",
    ) -> "AdkRunnerServiceBundle":
        """Create a service bundle from prebuilt ADK services or adapters."""

        artifact_adapter = (
            artifact_service
            if isinstance(artifact_service, AdkArtifactServiceAdapter)
            else AdkArtifactServiceAdapter(
                service=artifact_service,
                app_name=app_name,
                user_id=user_id,
            )
        )
        session_adapter = (
            session_service
            if isinstance(session_service, AdkSessionServiceAdapter)
            else AdkSessionServiceAdapter(
                service=session_service,
                app_name=app_name,
                user_id=user_id,
            )
        )
        return cls(
            artifact_service=artifact_adapter,
            session_service=session_adapter,
            app_name=app_name,
            user_id=user_id,
        )

    @property
    def adk_artifact_service(self) -> Any:
        """Return the ADK artifact service for Runner injection."""

        return self.artifact_service.adk_service

    @property
    def adk_session_service(self) -> Any:
        """Return the ADK session service for Runner injection."""

        return self.session_service.adk_service

    def metadata(self) -> dict[str, Any]:
        """Return service bundle metadata without exposing ADK objects."""

        return {
            "adapter": "adk_adapter.runner_service_bundle",
            "app_name": self.app_name,
            "user_id": self.user_id,
            "artifact_service": self.artifact_service.metadata(),
            "session_service": self.session_service.metadata(),
        }


class AdkRunnerServiceAdapter:
    """Build and run ADK Runner with explicit service injection."""

    def __init__(
        self,
        *,
        workflow: Any,
        app_name: str = "cognition_engine_adk_adapter",
        user_id: str = "cognition-engine-adk-user",
        service_bundle: AdkRunnerServiceBundle | None = None,
        artifact_service: AdkArtifactServiceAdapter | Any | None = None,
        session_service: AdkSessionServiceAdapter | Any | None = None,
        run_config: Any | None = None,
        run_config_options: AdkRunConfigOptions | None = None,
    ) -> None:
        self.workflow = workflow
        self.app_name = app_name
        self.user_id = user_id
        self.service_bundle = service_bundle or self._build_bundle(
            artifact_service=artifact_service,
            session_service=session_service,
            app_name=app_name,
            user_id=user_id,
        )
        self.run_config = run_config or AdkRunConfigMapper().build(run_config_options)

    def create_runner(self) -> Any:
        """Create a real ADK Runner over the configured Workflow/BaseNode."""

        from google.adk.runners import Runner

        return Runner(
            node=self.workflow,
            app_name=self.app_name,
            artifact_service=self.service_bundle.adk_artifact_service,
            session_service=self.service_bundle.adk_session_service,
        )

    async def create_session(
        self,
        *,
        state: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> Any:
        """Create a session through the injected ADK SessionService."""

        return await self.service_bundle.session_service.create_session(
            state=state,
            session_id=session_id,
        )

    async def run_async(
        self,
        *,
        user_id: str,
        session_id: str,
        invocation_id: str | None = None,
        new_message: Any | None = None,
        run_config: Any | None = None,
        yield_user_message: bool = False,
    ) -> list[Any]:
        """Run the ADK Runner and collect emitted events."""

        runner = self.create_runner()
        events: list[Any] = []
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            invocation_id=invocation_id,
            new_message=new_message,
            run_config=run_config if run_config is not None else self.run_config,
            yield_user_message=yield_user_message,
        ):
            events.append(event)
        return events

    def metadata(self) -> dict[str, Any]:
        """Return adapter metadata without leaking the Runner instance."""

        return {
            "adapter": "adk_adapter.runner_service",
            "adk_runner_type": "Runner",
            "workflow_type": type(self.workflow).__name__,
            "app_name": self.app_name,
            "user_id": self.user_id,
            "service_bundle": self.service_bundle.metadata(),
            "run_config": AdkRunConfigMapper().metadata(self.run_config),
        }

    def _build_bundle(
        self,
        *,
        artifact_service: AdkArtifactServiceAdapter | Any | None,
        session_service: AdkSessionServiceAdapter | Any | None,
        app_name: str,
        user_id: str,
    ) -> AdkRunnerServiceBundle:
        return AdkRunnerServiceBundle.from_services(
            artifact_service=artifact_service
            if artifact_service is not None
            else AdkArtifactServiceAdapter(app_name=app_name, user_id=user_id),
            session_service=session_service
            if session_service is not None
            else AdkSessionServiceAdapter(app_name=app_name, user_id=user_id),
            app_name=app_name,
            user_id=user_id,
        )
