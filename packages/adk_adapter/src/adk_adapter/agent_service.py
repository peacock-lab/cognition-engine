"""Agent service adapter for ADK 2 native Agent shells."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Any
from urllib.parse import urlparse

from google.adk.models.base_llm import BaseLlm

from adk_adapter.event_mapper import AdkEventMapper
from adk_adapter.invocation_mapper import AdkInvocationBinding, AdkInvocationMapper
from adk_adapter.run_config import AdkRunConfigMapper, AdkRunConfigOptions
from adk_adapter.runner_service import AdkRunnerServiceBundle
from schemas.runtime import InvocationRef, RuntimeErrorRecord, RuntimeEvent


@dataclass(frozen=True)
class AdkAgentShellOptions:
    """Local options for constructing an ADK native LlmAgent shell."""

    name: str
    model: str
    instruction: str
    description: str = ""
    mode: str | None = "chat"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_metadata(self) -> dict[str, Any]:
        """Return safe option metadata without exposing full instructions."""

        return {
            "options_type": "adk_adapter.agent_service.AdkAgentShellOptions",
            "name": self.name,
            "model": self.model,
            "description": self.description,
            "mode": self.mode,
            "instruction_length": len(self.instruction),
            "metadata_keys": sorted(self.metadata),
        }


@dataclass(frozen=True)
class AdkAgentControlledLiveOptions:
    """Controlled-live model options for an ADK native Agent shell."""

    model: str = "ollama/gemma4-pro:latest"
    ollama_api_base: str = "http://127.0.0.1:11434"
    timeout_seconds: int = 45
    temperature: float = 0
    max_tokens: int = 64
    llm_client: Any | None = field(default=None, repr=False, compare=False)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_metadata(self) -> dict[str, Any]:
        """Return sanitized controlled-live option metadata."""

        return {
            "options_type": "adk_adapter.agent_service."
            "AdkAgentControlledLiveOptions",
            "model": self.model,
            "ollama_api_base": self.ollama_api_base,
            "timeout_seconds": self.timeout_seconds,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "live_service_profile": self.metadata.get(
                "live_service_profile",
                "adk_litellm_ollama",
            ),
            "live_options_source": self.metadata.get("live_options_source"),
            "metadata_keys": sorted(self.metadata),
            "custom_client_injected": self.llm_client is not None,
        }


@dataclass(frozen=True)
class AdkAgentRunResult:
    """Internal result for one ADK Agent shell run."""

    agent_name: str | None
    agent_type: str
    app_name: str
    user_id: str
    session_id: str
    requested_invocation_id: str
    invocation_ref: InvocationRef
    invocation_binding: AdkInvocationBinding
    events: list[Any]
    runtime_events: list[RuntimeEvent]
    errors: list[RuntimeErrorRecord]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def adk_invocation_id(self) -> str | None:
        """Return the first invocation id emitted by ADK events."""

        return self.invocation_binding.adk_invocation_id

    def to_observability_input(self) -> dict[str, Any]:
        """Return a sanitized plain shape for observability-hub intake."""

        return {
            "source": "adk_adapter.agent_service",
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "app_name": self.app_name,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "requested_invocation_id": self.requested_invocation_id,
            "adk_invocation_id": self.adk_invocation_id,
            "invocation_ref": self.invocation_ref.model_dump(mode="python"),
            "invocation_binding": self.invocation_binding.to_metadata(),
            "events": [
                event.model_dump(mode="python") for event in self.runtime_events
            ],
            "errors": [error.model_dump(mode="python") for error in self.errors],
            "event_count": len(self.runtime_events),
            "error_count": len(self.errors),
            "metadata": dict(self.metadata),
        }


class AdkAgentServiceAdapter:
    """Adapt an ADK native Agent into a runner-backed service entry."""

    def __init__(
        self,
        *,
        agent: Any,
        app_name: str = "cognition_engine_adk_adapter",
        user_id: str = "cognition-engine-adk-user",
        service_bundle: AdkRunnerServiceBundle | None = None,
        run_config: Any | None = None,
        run_config_options: AdkRunConfigOptions | None = None,
        event_mapper: AdkEventMapper | None = None,
        invocation_mapper: AdkInvocationMapper | None = None,
    ) -> None:
        self.agent = agent
        self.app_name = app_name
        self.user_id = user_id
        self.service_bundle = service_bundle or AdkRunnerServiceBundle.in_memory(
            app_name=app_name,
            user_id=user_id,
        )
        self.run_config = run_config or AdkRunConfigMapper().build(run_config_options)
        self._event_mapper = event_mapper or AdkEventMapper()
        self._invocation_mapper = invocation_mapper or AdkInvocationMapper()

    def create_runner(self) -> Any:
        """Create a real ADK Runner over the configured native Agent."""

        from google.adk.runners import Runner

        return Runner(
            agent=self.agent,
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
        """Run the ADK Agent and collect emitted events."""

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

    async def run_text_async(
        self,
        *,
        text: str,
        invocation_id: str,
        session_id: str | None = None,
        state: dict[str, Any] | None = None,
        yield_user_message: bool = True,
    ) -> AdkAgentRunResult:
        """Run the ADK Agent with a text message and map emitted facts."""

        from google.genai import types

        session = await self.create_session(state=state, session_id=session_id)
        message = types.Content(
            role="user",
            parts=[types.Part(text=text)],
        )
        events = await self.run_async(
            user_id=self.user_id,
            session_id=session.id,
            invocation_id=invocation_id,
            new_message=message,
            yield_user_message=yield_user_message,
        )
        binding = self._invocation_mapper.bind_from_events(
            requested_invocation_id=invocation_id,
            events=events,
            session_id=session.id,
            app_name=self.app_name,
            user_id=self.user_id,
            metadata={
                "runner_entry": "agent",
                "agent_name": getattr(self.agent, "name", None),
            },
        )
        invocation_ref = self._invocation_mapper.merge_into_invocation_ref(
            InvocationRef(invocation_id=invocation_id, source="adk_agent_shell"),
            binding,
        )
        runtime_events = [
            self._event_mapper.map_event(
                event,
                invocation_ref=invocation_ref,
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
                    invocation_binding=binding,
                )
            )
            is not None
        ]
        return AdkAgentRunResult(
            agent_name=getattr(self.agent, "name", None),
            agent_type=type(self.agent).__name__,
            app_name=self.app_name,
            user_id=self.user_id,
            session_id=session.id,
            requested_invocation_id=invocation_id,
            invocation_ref=invocation_ref,
            invocation_binding=binding,
            events=events,
            runtime_events=runtime_events,
            errors=errors,
            metadata={
                **self.metadata(),
                "event_count": len(events),
                "error_count": len(errors),
                "no_live_execution_observed": _is_no_live_model(self.agent),
            },
        )

    def metadata(self) -> dict[str, Any]:
        """Return adapter metadata without leaking ADK objects."""

        return {
            "adapter": "adk_adapter.agent_service",
            "adk_runner_type": "Runner",
            "runner_entry": "agent",
            "agent_type": type(self.agent).__name__,
            "agent_name": getattr(self.agent, "name", None),
            "agent_model": _safe_text(getattr(self.agent, "model", None)),
            "agent_mode": getattr(self.agent, "mode", None),
            "app_name": self.app_name,
            "user_id": self.user_id,
            "service_bundle": self.service_bundle.metadata(),
            "run_config": AdkRunConfigMapper().metadata(self.run_config),
        }


def create_adk_llm_agent(options: AdkAgentShellOptions) -> Any:
    """Create an ADK native LlmAgent from local shell options."""

    from google.adk.agents import Agent

    return Agent(
        name=options.name,
        model=options.model,
        instruction=options.instruction,
        description=options.description,
        mode=options.mode,
    )


def create_no_live_adk_llm_agent(
    options: AdkAgentShellOptions,
    *,
    response_text: str = "No-live ADK Agent shell response.",
) -> Any:
    """Create an ADK native LlmAgent backed by a deterministic no-live model."""

    from google.adk.agents import Agent

    return Agent(
        name=options.name,
        model=AdkNoLiveLlm(model=options.model, response_text=response_text),
        instruction=options.instruction,
        description=options.description,
        mode=options.mode,
    )


def create_controlled_live_adk_llm_agent(
    options: AdkAgentShellOptions,
    *,
    live_options: AdkAgentControlledLiveOptions,
) -> Any:
    """Create an ADK native Agent backed by ADK LiteLlm provider routing."""

    from google.adk.agents import Agent
    from google.adk.models.lite_llm import LiteLlm

    _ensure_local_no_proxy(live_options.ollama_api_base)
    lite_llm_kwargs: dict[str, Any] = {
        "api_base": live_options.ollama_api_base,
        "timeout": live_options.timeout_seconds,
        "temperature": live_options.temperature,
        "max_tokens": live_options.max_tokens,
    }
    if live_options.llm_client is not None:
        lite_llm_kwargs["llm_client"] = live_options.llm_client

    return Agent(
        name=options.name,
        model=LiteLlm(model=live_options.model, **lite_llm_kwargs),
        instruction=options.instruction,
        description=options.description,
        mode=options.mode,
    )


class AdkNoLiveLlm(BaseLlm):
    """Deterministic ADK BaseLlm used for no-live Agent shell tests."""

    response_text: str = "No-live ADK Agent shell response."

    @classmethod
    def supported_models(cls) -> list[str]:
        """Return the explicit no-live model namespace."""

        return [r"adk-no-live/.+"]

    async def generate_content_async(self, llm_request: Any, stream: bool = False):
        """Yield one deterministic response without calling a provider."""

        from google.adk.models.llm_response import LlmResponse
        from google.genai import types

        yield LlmResponse(
            model_version=self.model,
            content=types.Content(
                role="model",
                parts=[types.Part(text=self.response_text)],
            ),
            partial=False,
            turn_complete=True,
            custom_metadata={
                "no_live_execution": True,
                "source": "adk_adapter.agent_service.AdkNoLiveLlm",
            },
        )


def _is_no_live_model(agent: Any) -> bool:
    if isinstance(getattr(agent, "model", None), AdkNoLiveLlm):
        return True
    return any(
        _is_no_live_model(sub_agent)
        for sub_agent in getattr(agent, "sub_agents", ())
    )


def _safe_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return type(value).__name__


def _ensure_local_no_proxy(api_base: str) -> bool:
    host = urlparse(api_base).hostname
    if host not in {"127.0.0.1", "localhost"}:
        return False
    for key in ("NO_PROXY", "no_proxy"):
        existing = [
            item.strip()
            for item in os.environ.get(key, "").split(",")
            if item.strip()
        ]
        merged = existing + [
            item for item in ("127.0.0.1", "localhost") if item not in existing
        ]
        os.environ[key] = ",".join(merged)
    return True
