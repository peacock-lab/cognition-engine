"""Controlled-live LLM service builder owned by runtime_container."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config_contexts.runtime import (
    RuntimeConfigContextBundle,
    RuntimeConfigSelectionContext,
    RuntimeLiveLlmInvocationOptionsContext,
)
from contract_core.llm_invocation import (
    GovernedLlmInvocationServiceFactory,
    GovernedLlmInvocationServiceResolution,
)

RUNTIME_CONTAINER_LIVE_LLM_PROVIDER_RESOLUTION_FAILED = (
    "runtime_container_live_llm_provider_resolution_failed"
)
RUNTIME_CONTAINER_LIVE_LLM_PROVIDER_RESOLUTION_EXCEPTION = (
    "runtime_container_live_llm_provider_resolution_exception"
)


@dataclass(frozen=True)
class RuntimeContainerGovernedLlmInvocationServiceFactory:
    """Runtime-container implementation of governed LLM service factory."""

    metadata: Mapping[str, Any] = field(default_factory=dict)

    def resolve(
        self,
        *,
        config_context: RuntimeConfigContextBundle | None = None,
        config_selection: RuntimeConfigSelectionContext,
        live_llm_options: RuntimeLiveLlmInvocationOptionsContext,
    ) -> GovernedLlmInvocationServiceResolution:
        """Resolve a controlled-live LLM service through runtime_container."""

        try:
            service = build_runtime_container_controlled_live_llm_invocation_service(
                config_context=config_context,
                config_root=config_selection.config_root,
                environment=config_selection.environment,
                ollama_api_base=live_llm_options.ollama_api_base,
                timeout_seconds=live_llm_options.timeout_seconds,
                max_tokens=live_llm_options.max_tokens,
                response_preview_limit=live_llm_options.response_preview_limit,
                provider_profile_ref=live_llm_options.provider_profile_ref,
                model_profile_ref=live_llm_options.model_profile_ref,
                output_governance_profile_ref=(
                    live_llm_options.output_governance_profile_ref
                ),
                network_gate_open=live_llm_options.network_gate_open,
                operator_approved=live_llm_options.operator_approved,
                approval_ref=live_llm_options.approval_ref,
                audit_ref=live_llm_options.audit_ref,
                metadata=_factory_service_metadata(
                    factory_metadata=self.metadata,
                    config_selection=config_selection,
                    live_llm_options=live_llm_options,
                ),
            )
        except Exception:
            return GovernedLlmInvocationServiceResolution(
                blocking_reasons=(
                    RUNTIME_CONTAINER_LIVE_LLM_PROVIDER_RESOLUTION_FAILED,
                ),
                warnings=(
                    RUNTIME_CONTAINER_LIVE_LLM_PROVIDER_RESOLUTION_EXCEPTION,
                ),
                metadata={
                    "failure_type": (
                        RUNTIME_CONTAINER_LIVE_LLM_PROVIDER_RESOLUTION_EXCEPTION
                    ),
                    "runtime_container_live_llm_factory": True,
                },
            )

        return GovernedLlmInvocationServiceResolution(
            service=service,
            metadata=_factory_resolution_metadata(
                factory_metadata=self.metadata,
                config_selection=config_selection,
                live_llm_options=live_llm_options,
            ),
        )


def build_runtime_container_governed_llm_invocation_service_factory(
    *,
    metadata: Mapping[str, Any] | None = None,
) -> GovernedLlmInvocationServiceFactory:
    """Build a runtime-container governed LLM invocation service factory."""

    return RuntimeContainerGovernedLlmInvocationServiceFactory(
        metadata=dict(metadata or {})
    )


def build_runtime_container_controlled_live_llm_invocation_service(
    *,
    config_context: Any | None = None,
    config_root: str | Path | None = None,
    environment: str = "local",
    ollama_api_base: str | None = None,
    timeout_seconds: int | None = None,
    max_tokens: int | None = None,
    response_preview_limit: int | None = None,
    provider_profile_ref: str | None = None,
    model_profile_ref: str | None = None,
    output_governance_profile_ref: str | None = None,
    network_gate_open: bool = False,
    operator_approved: bool = False,
    approval_ref: str | None = None,
    audit_ref: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Any:
    """Build a controlled-live LLM service from a config context or root."""

    from composition.llm_invocation_assembly import (
        build_controlled_live_adk_governed_llm_invocation_service_from_config_root,
        build_controlled_live_adk_governed_llm_invocation_service_from_runtime_config,
    )

    live_metadata = {
        "source": "runtime_container.controlled_live_llm_service",
        "runtime_container_controlled_live_service": True,
        "cli_controlled_live": bool(
            metadata and str(metadata.get("source", "")).startswith("cognition_cli")
        ),
        "cli_ollama_api_base_override": ollama_api_base is not None,
        "cli_timeout_seconds_override": timeout_seconds is not None,
        "provider_profile_ref": provider_profile_ref,
        "model_profile_ref": model_profile_ref,
        "output_governance_profile_ref": output_governance_profile_ref,
        "network_gate_open": network_gate_open,
        "operator_approved": operator_approved,
        "approval_ref_present": bool(approval_ref),
        "audit_ref_present": bool(audit_ref),
        **(metadata or {}),
    }
    if response_preview_limit is not None:
        live_metadata["response_preview_limit"] = response_preview_limit
    if max_tokens is not None:
        live_metadata["cli_chat_controlled_live"] = True

    if config_context is not None:
        return (
            build_controlled_live_adk_governed_llm_invocation_service_from_runtime_config(
                config_context=config_context,
                ollama_api_base=ollama_api_base,
                timeout_seconds=timeout_seconds,
                max_tokens=max_tokens,
                response_preview_limit=response_preview_limit,
                provider_profile_ref=provider_profile_ref,
                model_profile_ref=model_profile_ref,
                output_governance_profile_ref=output_governance_profile_ref,
                network_gate_open=network_gate_open,
                operator_approved=operator_approved,
                approval_ref=approval_ref,
                audit_ref=audit_ref,
                metadata=live_metadata,
            )
        )

    return build_controlled_live_adk_governed_llm_invocation_service_from_config_root(
        config_root=config_root,
        environment=environment,
        ollama_api_base=ollama_api_base,
        timeout_seconds=timeout_seconds,
        max_tokens=max_tokens,
        response_preview_limit=response_preview_limit,
        provider_profile_ref=provider_profile_ref,
        model_profile_ref=model_profile_ref,
        output_governance_profile_ref=output_governance_profile_ref,
        network_gate_open=network_gate_open,
        operator_approved=operator_approved,
        approval_ref=approval_ref,
        audit_ref=audit_ref,
        metadata=live_metadata,
    )


def _factory_service_metadata(
    *,
    factory_metadata: Mapping[str, Any],
    config_selection: RuntimeConfigSelectionContext,
    live_llm_options: RuntimeLiveLlmInvocationOptionsContext,
) -> dict[str, Any]:
    return {
        "source": (
            live_llm_options.selection_source
            or "runtime_container.controlled_live_llm_service.factory"
        ),
        "runtime_container_live_llm_factory": True,
        "config_selection_source": config_selection.selection_source,
        "config_profile": config_selection.profile,
        "factory_metadata_keys": _metadata_keys(factory_metadata),
        "config_metadata_keys": _metadata_keys(config_selection.metadata),
        "live_llm_options_source": live_llm_options.selection_source,
        "live_llm_options_metadata_keys": _metadata_keys(
            live_llm_options.metadata
        ),
    }


def _factory_resolution_metadata(
    *,
    factory_metadata: Mapping[str, Any],
    config_selection: RuntimeConfigSelectionContext,
    live_llm_options: RuntimeLiveLlmInvocationOptionsContext,
) -> dict[str, Any]:
    return {
        "resolution_source": (
            "runtime_container.controlled_live_llm_service.factory"
        ),
        "runtime_container_live_llm_factory": True,
        "config_selection_source": config_selection.selection_source,
        "config_profile": config_selection.profile,
        "config_metadata_keys": _metadata_keys(config_selection.metadata),
        "factory_metadata_keys": _metadata_keys(factory_metadata),
        "live_llm_options_source": live_llm_options.selection_source,
        "live_llm_options_metadata_keys": _metadata_keys(
            live_llm_options.metadata
        ),
    }


def _metadata_keys(metadata: Mapping[str, Any]) -> list[str]:
    return sorted(str(key) for key in metadata)


__all__ = [
    "RuntimeContainerGovernedLlmInvocationServiceFactory",
    "build_runtime_container_controlled_live_llm_invocation_service",
    "build_runtime_container_governed_llm_invocation_service_factory",
]
