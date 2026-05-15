"""Composition boundary for governed LLM invocation service assembly."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from adk_adapter import (
    AdkGovernedLlmInvocationOptions,
    AdkGovernedLlmInvocationService,
)
from behavior_contracts.llm_invocation import GovernedLlmInvocationService
from config_contexts.runtime import RuntimeConfigContextBundle
from schemas.llm_invocation import LlmGovernancePrecondition
from schemas.model_routing import ModelRouteFacts

DEFAULT_CONTROLLED_LIVE_OLLAMA_API_BASE = "http://127.0.0.1:11434"
DEFAULT_CONTROLLED_LIVE_TIMEOUT_SECONDS = 45
DEFAULT_CONTROLLED_LIVE_TEMPERATURE = 0
DEFAULT_CONTROLLED_LIVE_MAX_TOKENS = 64


@dataclass(frozen=True)
class LlmInvocationServiceAssemblyOptions:
    """Local composition options for governed LLM invocation assembly."""

    service_options: AdkGovernedLlmInvocationOptions = field(
        default_factory=AdkGovernedLlmInvocationOptions
    )
    route_facts: ModelRouteFacts | None = None
    governance_precondition: LlmGovernancePrecondition | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_metadata(self) -> dict[str, Any]:
        """Return serializable assembly options metadata."""

        return {
            "options_type": "composition.llm_invocation_assembly."
            "LlmInvocationServiceAssemblyOptions",
            "service_options": {
                "live_enabled": self.service_options.live_enabled,
                "metadata_keys": sorted(self.service_options.metadata),
            },
            "route_facts": _route_facts_metadata(self.route_facts),
            "governance_precondition": _governance_precondition_metadata(
                self.governance_precondition
            ),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class LlmInvocationServiceAssembly:
    """Holder for an assembled governed LLM invocation service."""

    service: GovernedLlmInvocationService
    assembly_options: LlmInvocationServiceAssemblyOptions
    metadata: dict[str, Any]


def build_llm_invocation_service_assembly(
    *,
    assembly_options: LlmInvocationServiceAssemblyOptions | None = None,
) -> LlmInvocationServiceAssembly:
    """Assemble the ADK governed LLM invocation service without invoking it."""

    options = assembly_options or LlmInvocationServiceAssemblyOptions()
    service: GovernedLlmInvocationService = AdkGovernedLlmInvocationService(
        options=options.service_options
    )
    return LlmInvocationServiceAssembly(
        service=service,
        assembly_options=options,
        metadata={
            "assembly": "composition.llm_invocation_assembly",
            "service_contract": (
                "behavior_contracts.llm_invocation.GovernedLlmInvocationService"
            ),
            "service_implementation": (
                "adk_adapter.llm_invocation.AdkGovernedLlmInvocationService"
            ),
            "does_not_invoke_service": True,
            "runtime_connected": False,
            "runtime_container_connected": False,
            "observability_candidate_created": False,
            "assembly_options": options.to_metadata(),
        },
    )


def build_adk_governed_llm_invocation_service(
    *,
    assembly_options: LlmInvocationServiceAssemblyOptions | None = None,
) -> GovernedLlmInvocationService:
    """Return the assembled service through the public behavior contract."""

    return build_llm_invocation_service_assembly(
        assembly_options=assembly_options
    ).service


def build_controlled_live_llm_invocation_service_assembly(
    *,
    ollama_api_base: str = DEFAULT_CONTROLLED_LIVE_OLLAMA_API_BASE,
    timeout_seconds: int = DEFAULT_CONTROLLED_LIVE_TIMEOUT_SECONDS,
    temperature: float = DEFAULT_CONTROLLED_LIVE_TEMPERATURE,
    max_tokens: int = DEFAULT_CONTROLLED_LIVE_MAX_TOKENS,
    metadata: dict[str, Any] | None = None,
) -> LlmInvocationServiceAssembly:
    """Assemble an explicitly live-enabled governed LLM service."""

    live_metadata = {
        "source": "composition.llm_invocation_assembly",
        "controlled_live": True,
        "live_service_profile": "adk_litellm_ollama",
        **(metadata or {}),
    }
    return build_llm_invocation_service_assembly(
        assembly_options=LlmInvocationServiceAssemblyOptions(
            service_options=AdkGovernedLlmInvocationOptions(
                live_enabled=True,
                ollama_api_base=ollama_api_base,
                timeout_seconds=timeout_seconds,
                temperature=temperature,
                max_tokens=max_tokens,
                metadata=live_metadata,
            ),
            metadata=live_metadata,
        )
    )


def build_controlled_live_llm_invocation_service_assembly_from_runtime_config(
    *,
    config_context: RuntimeConfigContextBundle,
    ollama_api_base: str | None = None,
    timeout_seconds: int | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> LlmInvocationServiceAssembly:
    """Assemble a controlled-live LLM service from runtime configuration."""

    live_llm = config_context.live_llm
    resolved_ollama_api_base = (
        ollama_api_base if ollama_api_base is not None else live_llm.ollama_api_base
    )
    resolved_timeout_seconds = (
        timeout_seconds if timeout_seconds is not None else live_llm.timeout_seconds
    )
    resolved_temperature = (
        temperature if temperature is not None else live_llm.temperature
    )
    resolved_max_tokens = max_tokens if max_tokens is not None else live_llm.max_tokens
    live_metadata = {
        "live_options_source": (
            "config_contexts.runtime.RuntimeLiveLlmConfigView"
        ),
        "live_service_profile": live_llm.profile,
        "configured_model_name": live_llm.model_name,
        "ollama_api_base": resolved_ollama_api_base,
        "timeout_seconds": resolved_timeout_seconds,
        "temperature": resolved_temperature,
        "max_tokens": resolved_max_tokens,
        "enabled_by_default": live_llm.enabled_by_default,
        "config_metadata_keys": sorted(live_llm.metadata),
        "config_metadata": dict(live_llm.metadata),
        **(metadata or {}),
    }
    return build_controlled_live_llm_invocation_service_assembly(
        ollama_api_base=resolved_ollama_api_base,
        timeout_seconds=resolved_timeout_seconds,
        temperature=resolved_temperature,
        max_tokens=resolved_max_tokens,
        metadata=live_metadata,
    )


def build_controlled_live_adk_governed_llm_invocation_service(
    *,
    ollama_api_base: str = DEFAULT_CONTROLLED_LIVE_OLLAMA_API_BASE,
    timeout_seconds: int = DEFAULT_CONTROLLED_LIVE_TIMEOUT_SECONDS,
    temperature: float = DEFAULT_CONTROLLED_LIVE_TEMPERATURE,
    max_tokens: int = DEFAULT_CONTROLLED_LIVE_MAX_TOKENS,
    metadata: dict[str, Any] | None = None,
) -> GovernedLlmInvocationService:
    """Return an explicitly live-enabled service through the public contract."""

    return build_controlled_live_llm_invocation_service_assembly(
        ollama_api_base=ollama_api_base,
        timeout_seconds=timeout_seconds,
        temperature=temperature,
        max_tokens=max_tokens,
        metadata=metadata,
    ).service


def build_controlled_live_adk_governed_llm_invocation_service_from_runtime_config(
    *,
    config_context: RuntimeConfigContextBundle,
    ollama_api_base: str | None = None,
    timeout_seconds: int | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> GovernedLlmInvocationService:
    """Return a config-driven controlled-live service through the contract."""

    return build_controlled_live_llm_invocation_service_assembly_from_runtime_config(
        config_context=config_context,
        ollama_api_base=ollama_api_base,
        timeout_seconds=timeout_seconds,
        temperature=temperature,
        max_tokens=max_tokens,
        metadata=metadata,
    ).service


def _route_facts_metadata(route_facts: ModelRouteFacts | None) -> dict[str, Any] | None:
    if route_facts is None:
        return None
    return {
        "model_name": route_facts.model_name,
        "provider": route_facts.provider,
        "runtime_call_performed": route_facts.runtime_call_performed,
        "direct_litellm_completion": route_facts.direct_litellm_completion,
        "governance_direct_model_call": route_facts.governance_direct_model_call,
        "source": route_facts.source,
        "metadata": dict(route_facts.metadata),
    }


def _governance_precondition_metadata(
    governance_precondition: LlmGovernancePrecondition | None,
) -> dict[str, Any] | None:
    if governance_precondition is None:
        return None
    return {
        "allowed": governance_precondition.allowed,
        "reason": governance_precondition.reason,
        "decision": governance_precondition.decision,
        "governance_decision_ref": governance_precondition.governance_decision_ref,
        "metadata": dict(governance_precondition.metadata),
    }
