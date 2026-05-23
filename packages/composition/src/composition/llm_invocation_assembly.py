"""Composition boundary for governed LLM invocation service assembly."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any

from adk_adapter import (
    ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_NO_OUTPUT_SCHEMA,
    ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_OUTPUT_SCHEMA,
    AdkEvidenceSummaryAnswerOutputGovernanceOptions,
    AdkEvidenceSummaryAnswerOutputGovernanceProbe,
    AdkGovernedLlmInvocationOptions,
    AdkGovernedLlmInvocationService,
)
from adk_adapter.models import (
    build_litellm_deepseek_model_route,
    build_litellm_ollama_model_route,
)
from behavior_contracts.llm_invocation import GovernedLlmInvocationService
from config_assembly.runtime import assemble_runtime_config_payload
from config_contexts.runtime import (
    RuntimeConfigContextBundle,
    RuntimeLiveLlmConfigView,
    RuntimeLlmModelProfileConfigView,
    RuntimeLlmOutputGovernanceProfileConfigView,
    RuntimeLlmProviderProfileConfigView,
)
from config_contexts.runtime_builder import build_runtime_config_contexts
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


@dataclass(frozen=True)
class _LiveLlmProfileSelection:
    provider_profile_ref: str
    model_profile_ref: str
    output_governance_profile_ref: str
    provider_profile: RuntimeLlmProviderProfileConfigView
    model_profile: RuntimeLlmModelProfileConfigView
    output_governance_profile: RuntimeLlmOutputGovernanceProfileConfigView


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
    response_preview_limit: int | None = None,
    provider_profile_ref: str | None = None,
    model_profile_ref: str | None = None,
    output_governance_profile_ref: str | None = None,
    network_gate_open: bool = False,
    operator_approved: bool = False,
    approval_ref: str | None = None,
    audit_ref: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> LlmInvocationServiceAssembly:
    """Assemble a controlled-live LLM service from runtime configuration."""

    live_llm = config_context.live_llm
    selection = _resolve_live_llm_profile_selection(
        live_llm,
        provider_profile_ref=provider_profile_ref,
        model_profile_ref=model_profile_ref,
        output_governance_profile_ref=output_governance_profile_ref,
    )
    if selection.provider_profile.backend_provider == "deepseek":
        return _build_deepseek_output_governance_assembly(
            selection,
            timeout_seconds=timeout_seconds,
            temperature=temperature,
            max_tokens=max_tokens,
            response_preview_limit=response_preview_limit,
            network_gate_open=network_gate_open,
            operator_approved=operator_approved,
            approval_ref=approval_ref,
            audit_ref=audit_ref,
            metadata=metadata,
        )
    if (
        selection.provider_profile.backend_provider == "ollama"
        and selection.output_governance_profile.mode
        in {"adk_no_output_schema", "adk_output_schema"}
    ):
        return _build_ollama_output_governance_assembly(
            selection,
            ollama_api_base=ollama_api_base,
            timeout_seconds=timeout_seconds,
            temperature=temperature,
            max_tokens=max_tokens,
            response_preview_limit=response_preview_limit,
            metadata=metadata,
        )
    if selection.output_governance_profile.mode != "direct_controlled_live":
        raise ValueError(
            "non-default output governance profile requires a supported "
            "provider-specific assembly."
        )
    resolved_ollama_api_base = (
        ollama_api_base
        if ollama_api_base is not None
        else selection.provider_profile.api_base or live_llm.ollama_api_base
    )
    resolved_timeout_seconds = (
        timeout_seconds
        if timeout_seconds is not None
        else (
            live_llm.timeout_seconds
            if model_profile_ref is None
            else selection.model_profile.timeout_seconds
        )
    )
    resolved_temperature = (
        temperature
        if temperature is not None
        else (
            live_llm.temperature
            if model_profile_ref is None
            else selection.model_profile.temperature
        )
    )
    resolved_max_tokens = (
        max_tokens
        if max_tokens is not None
        else (
            live_llm.max_tokens
            if model_profile_ref is None
            else selection.model_profile.max_tokens
        )
    )
    live_metadata = {
        "live_options_source": (
            "config_contexts.runtime.RuntimeLiveLlmConfigView"
        ),
        "live_service_profile": live_llm.profile,
        "configured_model_name": selection.model_profile.model_name,
        "provider_profile_ref": selection.provider_profile_ref,
        "model_profile_ref": selection.model_profile_ref,
        "output_governance_profile_ref": selection.output_governance_profile_ref,
        "backend_provider": selection.provider_profile.backend_provider,
        "route_kind": selection.provider_profile.route_kind,
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


def build_controlled_live_llm_invocation_service_assembly_from_config_root(
    *,
    config_root: str | Path | None = None,
    environment: str = "local",
    ollama_api_base: str | None = None,
    timeout_seconds: int | None = None,
    temperature: float | None = None,
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
) -> LlmInvocationServiceAssembly:
    """Assemble a controlled-live LLM service from the config root."""

    config_payload = assemble_runtime_config_payload(
        config_root=Path(config_root or "config"),
        environment=environment,
    )
    config_context = build_runtime_config_contexts(config_payload)
    return build_controlled_live_llm_invocation_service_assembly_from_runtime_config(
        config_context=config_context,
        ollama_api_base=ollama_api_base,
        timeout_seconds=timeout_seconds,
        temperature=temperature,
        max_tokens=max_tokens,
        response_preview_limit=response_preview_limit,
        provider_profile_ref=provider_profile_ref,
        model_profile_ref=model_profile_ref,
        output_governance_profile_ref=output_governance_profile_ref,
        network_gate_open=network_gate_open,
        operator_approved=operator_approved,
        approval_ref=approval_ref,
        audit_ref=audit_ref,
        metadata=metadata,
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
    response_preview_limit: int | None = None,
    provider_profile_ref: str | None = None,
    model_profile_ref: str | None = None,
    output_governance_profile_ref: str | None = None,
    network_gate_open: bool = False,
    operator_approved: bool = False,
    approval_ref: str | None = None,
    audit_ref: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> GovernedLlmInvocationService:
    """Return a config-driven controlled-live service through the contract."""

    return build_controlled_live_llm_invocation_service_assembly_from_runtime_config(
        config_context=config_context,
        ollama_api_base=ollama_api_base,
        timeout_seconds=timeout_seconds,
        temperature=temperature,
        max_tokens=max_tokens,
        response_preview_limit=response_preview_limit,
        provider_profile_ref=provider_profile_ref,
        model_profile_ref=model_profile_ref,
        output_governance_profile_ref=output_governance_profile_ref,
        network_gate_open=network_gate_open,
        operator_approved=operator_approved,
        approval_ref=approval_ref,
        audit_ref=audit_ref,
        metadata=metadata,
    ).service


def build_controlled_live_adk_governed_llm_invocation_service_from_config_root(
    *,
    config_root: str | Path | None = None,
    environment: str = "local",
    ollama_api_base: str | None = None,
    timeout_seconds: int | None = None,
    temperature: float | None = None,
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
) -> GovernedLlmInvocationService:
    """Return a config-root controlled-live service through the contract."""

    return build_controlled_live_llm_invocation_service_assembly_from_config_root(
        config_root=config_root,
        environment=environment,
        ollama_api_base=ollama_api_base,
        timeout_seconds=timeout_seconds,
        temperature=temperature,
        max_tokens=max_tokens,
        response_preview_limit=response_preview_limit,
        provider_profile_ref=provider_profile_ref,
        model_profile_ref=model_profile_ref,
        output_governance_profile_ref=output_governance_profile_ref,
        network_gate_open=network_gate_open,
        operator_approved=operator_approved,
        approval_ref=approval_ref,
        audit_ref=audit_ref,
        metadata=metadata,
    ).service


def _resolve_live_llm_profile_selection(
    live_llm: RuntimeLiveLlmConfigView,
    *,
    provider_profile_ref: str | None,
    model_profile_ref: str | None,
    output_governance_profile_ref: str | None,
) -> _LiveLlmProfileSelection:
    resolved_model_ref = model_profile_ref or live_llm.default_model_profile_ref
    model_profile = live_llm.model_profiles.get(resolved_model_ref)
    if model_profile is None:
        raise ValueError("selected model profile does not exist.")

    resolved_provider_ref = provider_profile_ref or model_profile.provider_profile_ref
    if resolved_provider_ref != model_profile.provider_profile_ref:
        raise ValueError("selected provider profile must match model profile.")
    provider_profile = live_llm.provider_profiles.get(resolved_provider_ref)
    if provider_profile is None:
        raise ValueError("selected provider profile does not exist.")

    resolved_output_ref = (
        output_governance_profile_ref
        or live_llm.default_output_governance_profile_ref
    )
    output_governance_profile = live_llm.output_governance_profiles.get(
        resolved_output_ref
    )
    if output_governance_profile is None:
        raise ValueError("selected output governance profile does not exist.")

    return _LiveLlmProfileSelection(
        provider_profile_ref=resolved_provider_ref,
        model_profile_ref=resolved_model_ref,
        output_governance_profile_ref=resolved_output_ref,
        provider_profile=provider_profile,
        model_profile=model_profile,
        output_governance_profile=output_governance_profile,
    )


def _build_deepseek_output_governance_assembly(
    selection: _LiveLlmProfileSelection,
    *,
    timeout_seconds: int | None,
    temperature: float | None,
    max_tokens: int | None,
    response_preview_limit: int | None,
    network_gate_open: bool,
    operator_approved: bool,
    approval_ref: str | None,
    audit_ref: str | None,
    metadata: dict[str, Any] | None,
) -> LlmInvocationServiceAssembly:
    _validate_external_provider_controls(
        selection.provider_profile,
        network_gate_open=network_gate_open,
        operator_approved=operator_approved,
        approval_ref=approval_ref,
        audit_ref=audit_ref,
    )
    if (
        selection.output_governance_profile.mode
        != "adk_no_output_schema"
    ):
        raise ValueError("DeepSeek product path requires adk_no_output_schema.")

    resolved_timeout_seconds = (
        timeout_seconds
        if timeout_seconds is not None
        else selection.model_profile.timeout_seconds
    )
    resolved_temperature = (
        temperature if temperature is not None else selection.model_profile.temperature
    )
    resolved_max_tokens = (
        max_tokens if max_tokens is not None else selection.model_profile.max_tokens
    )
    api_base = _provider_api_base(selection.provider_profile)
    model, route_facts = build_litellm_deepseek_model_route(
        model_name=selection.model_profile.model_name,
        api_base=api_base,
        secret_ref=selection.provider_profile.secret_ref or "",
        network_gate_open=network_gate_open,
        operator_approved=operator_approved,
        approval_ref=approval_ref,
        audit_ref=audit_ref,
        timeout=resolved_timeout_seconds,
        temperature=resolved_temperature,
        max_tokens=resolved_max_tokens,
        thinking_mode=str(
            selection.model_profile.metadata.get("thinking_mode") or "disabled"
        ),
    )
    public_route_facts = route_facts.to_public_model_route_facts()
    live_metadata = {
        "live_options_source": "config_contexts.runtime.RuntimeLiveLlmConfigView",
        "live_service_profile": "adk_litellm_deepseek_v4",
        "configured_model_name": selection.model_profile.model_name,
        "provider_profile_ref": selection.provider_profile_ref,
        "model_profile_ref": selection.model_profile_ref,
        "output_governance_profile_ref": selection.output_governance_profile_ref,
        "backend_provider": selection.provider_profile.backend_provider,
        "route_kind": selection.provider_profile.route_kind,
        "api_base_host": _url_host(api_base),
        "timeout_seconds": resolved_timeout_seconds,
        "temperature": resolved_temperature,
        "max_tokens": resolved_max_tokens,
        "network_gate_open": network_gate_open,
        "operator_approved": operator_approved,
        "approval_ref_present": bool(approval_ref),
        "audit_ref_present": bool(audit_ref),
        "secret_ref_present": bool(selection.provider_profile.secret_ref),
        "thinking_mode": public_route_facts.metadata.get("thinking_mode"),
        "product_optional_provider": True,
        **(metadata or {}),
    }
    service: GovernedLlmInvocationService = (
        AdkEvidenceSummaryAnswerOutputGovernanceProbe(
            options=AdkEvidenceSummaryAnswerOutputGovernanceOptions(
                model=model,
                model_name=selection.model_profile.model_name,
                app_name="cognition_engine_external_readonly_ask_deepseek",
                output_governance_mode=(
                    ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_NO_OUTPUT_SCHEMA
                ),
                route_facts=public_route_facts,
                max_repair_attempts=(
                    selection.output_governance_profile.max_repair_attempts
                ),
                response_preview_limit=response_preview_limit or 600,
                metadata=live_metadata,
            )
        )
    )
    assembly_options = LlmInvocationServiceAssemblyOptions(
        route_facts=public_route_facts,
        metadata=live_metadata,
    )
    return LlmInvocationServiceAssembly(
        service=service,
        assembly_options=assembly_options,
        metadata={
            "assembly": "composition.llm_invocation_assembly",
            "service_contract": (
                "behavior_contracts.llm_invocation.GovernedLlmInvocationService"
            ),
            "service_implementation": (
                "adk_adapter.evidence_summary_answer_output_governance."
                "AdkEvidenceSummaryAnswerOutputGovernanceProbe"
            ),
            "does_not_invoke_service": True,
            "runtime_connected": False,
            "runtime_container_connected": False,
            "observability_candidate_created": False,
            "profile_selection": _profile_selection_metadata(selection),
            "assembly_options": assembly_options.to_metadata(),
        },
    )


def _build_ollama_output_governance_assembly(
    selection: _LiveLlmProfileSelection,
    *,
    ollama_api_base: str | None,
    timeout_seconds: int | None,
    temperature: float | None,
    max_tokens: int | None,
    response_preview_limit: int | None,
    metadata: dict[str, Any] | None,
) -> LlmInvocationServiceAssembly:
    output_governance_mode = _adk_output_governance_mode(
        selection.output_governance_profile
    )

    resolved_ollama_api_base = (
        ollama_api_base
        if ollama_api_base is not None
        else _provider_api_base(selection.provider_profile)
    )
    resolved_timeout_seconds = (
        timeout_seconds
        if timeout_seconds is not None
        else selection.model_profile.timeout_seconds
    )
    resolved_temperature = (
        temperature if temperature is not None else selection.model_profile.temperature
    )
    resolved_max_tokens = (
        max_tokens if max_tokens is not None else selection.model_profile.max_tokens
    )
    model, route_facts = build_litellm_ollama_model_route(
        model_name=selection.model_profile.model_name,
        api_base=resolved_ollama_api_base,
        timeout=resolved_timeout_seconds,
        temperature=resolved_temperature,
        max_tokens=resolved_max_tokens,
    )
    public_route_facts = route_facts.to_public_model_route_facts()
    live_metadata = {
        "live_options_source": "config_contexts.runtime.RuntimeLiveLlmConfigView",
        "live_service_profile": "adk_litellm_ollama_output_governance",
        "configured_model_name": selection.model_profile.model_name,
        "provider_profile_ref": selection.provider_profile_ref,
        "model_profile_ref": selection.model_profile_ref,
        "output_governance_profile_ref": selection.output_governance_profile_ref,
        "backend_provider": selection.provider_profile.backend_provider,
        "route_kind": selection.provider_profile.route_kind,
        "output_governance_mode": output_governance_mode,
        "ollama_api_base": resolved_ollama_api_base,
        "timeout_seconds": resolved_timeout_seconds,
        "temperature": resolved_temperature,
        "max_tokens": resolved_max_tokens,
        "local_only_provider": True,
        **(metadata or {}),
    }
    service: GovernedLlmInvocationService = (
        AdkEvidenceSummaryAnswerOutputGovernanceProbe(
            options=AdkEvidenceSummaryAnswerOutputGovernanceOptions(
                model=model,
                model_name=selection.model_profile.model_name,
                app_name="cognition_engine_external_readonly_ask_ollama",
                output_governance_mode=output_governance_mode,
                route_facts=public_route_facts,
                max_repair_attempts=(
                    selection.output_governance_profile.max_repair_attempts
                ),
                response_preview_limit=response_preview_limit or 600,
                metadata=live_metadata,
            )
        )
    )
    assembly_options = LlmInvocationServiceAssemblyOptions(
        route_facts=public_route_facts,
        metadata=live_metadata,
    )
    return LlmInvocationServiceAssembly(
        service=service,
        assembly_options=assembly_options,
        metadata={
            "assembly": "composition.llm_invocation_assembly",
            "service_contract": (
                "behavior_contracts.llm_invocation.GovernedLlmInvocationService"
            ),
            "service_implementation": (
                "adk_adapter.evidence_summary_answer_output_governance."
                "AdkEvidenceSummaryAnswerOutputGovernanceProbe"
            ),
            "does_not_invoke_service": True,
            "runtime_connected": False,
            "runtime_container_connected": False,
            "observability_candidate_created": False,
            "profile_selection": _profile_selection_metadata(selection),
            "assembly_options": assembly_options.to_metadata(),
        },
    )


def _adk_output_governance_mode(
    output_governance_profile: RuntimeLlmOutputGovernanceProfileConfigView,
) -> str:
    if output_governance_profile.mode == "adk_no_output_schema":
        return ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_NO_OUTPUT_SCHEMA
    if output_governance_profile.mode == "adk_output_schema":
        return ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_OUTPUT_SCHEMA
    raise ValueError("Ollama ADK product path requires an ADK output governance mode.")


def _validate_external_provider_controls(
    provider_profile: RuntimeLlmProviderProfileConfigView,
    *,
    network_gate_open: bool,
    operator_approved: bool,
    approval_ref: str | None,
    audit_ref: str | None,
) -> None:
    if provider_profile.requires_network_gate and not network_gate_open:
        raise ValueError("external provider network gate is required.")
    if provider_profile.requires_operator_approval and not operator_approved:
        raise ValueError("external provider operator approval is required.")
    if provider_profile.requires_operator_approval and not approval_ref:
        raise ValueError("external provider approval ref is required.")
    if provider_profile.requires_audit_ref and not audit_ref:
        raise ValueError("external provider audit ref is required.")


def _provider_api_base(
    provider_profile: RuntimeLlmProviderProfileConfigView,
) -> str | None:
    if provider_profile.api_base_env_var:
        value = os.getenv(provider_profile.api_base_env_var)
        if value:
            return value
    return provider_profile.api_base


def _profile_selection_metadata(
    selection: _LiveLlmProfileSelection,
) -> dict[str, Any]:
    return {
        "provider_profile_ref": selection.provider_profile_ref,
        "model_profile_ref": selection.model_profile_ref,
        "output_governance_profile_ref": selection.output_governance_profile_ref,
        "backend_provider": selection.provider_profile.backend_provider,
        "route_kind": selection.provider_profile.route_kind,
        "model_name": selection.model_profile.model_name,
        "output_governance_mode": selection.output_governance_profile.mode,
    }


def _url_host(value: str | None) -> str | None:
    if not value:
        return None
    from urllib.parse import urlparse

    return urlparse(value).hostname


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
