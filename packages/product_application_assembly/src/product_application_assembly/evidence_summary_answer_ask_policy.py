"""Product-level policy helpers for evidence-summary-answer ask actions."""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Mapping
from dataclasses import dataclass, field
import os
from typing import Any

from config_contexts.runtime import (
    RuntimeConfigSelectionContext,
    RuntimeLiveLlmConfigView,
    RuntimeLiveLlmInvocationOptionsContext,
)
from schemas.llm_invocation import LlmGovernancePrecondition
from schemas.model_routing import ModelRouteFacts


PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ASK_POLICY_SOURCE = (
    "product_application_assembly.evidence_summary_answer_ask_policy"
)


@dataclass(frozen=True)
class EvidenceSummaryAnswerAskRoutePolicyInput:
    """Product-level route policy input.

    Channel adapters may collect option values, but route facts must be built in
    product-level policy helpers so later TUI / GUI surfaces do not copy CLI
    route construction.
    """

    model_name: str
    provider_profile_ref: str | None = None
    model_profile_ref: str | None = None
    output_governance_profile_ref: str | None = None
    source: str = PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ASK_POLICY_SOURCE
    product_path: str = "external_readonly_ask_product_path"
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceSummaryAnswerAskModelSelectionInput:
    """Product-level model selection input collected by a channel adapter."""

    model_name: str | None = None
    model_alias: str | None = None
    provider_profile_ref: str | None = None
    model_profile_ref: str | None = None
    output_governance_profile_ref: str | None = None


@dataclass(frozen=True)
class EvidenceSummaryAnswerAskModelSelectionResult:
    """Resolved ask model route selection facts."""

    model_name: str
    model_alias: str | None
    provider_profile_ref: str | None
    model_profile_ref: str | None
    output_governance_profile_ref: str | None
    backend_provider: str
    route_kind: str
    external_provider_selected: bool
    local_ollama_selected: bool
    blocking_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidenceSummaryAnswerAskLlmServiceResolutionInput:
    """Product-level input for resolving an ask LLM service."""

    config_root: str | None
    environment: str | None
    profile: str | None
    request_id: str
    surface: str
    product_path: str
    source: str
    ollama_api_base: str | None
    timeout_seconds: float | None
    max_tokens: int | None
    response_preview_limit: int
    network_gate_open: bool
    operator_approved: bool
    approval_ref: str | None
    audit_ref: str | None
    model_selection: EvidenceSummaryAnswerAskModelSelectionResult
    provider_key: str | None = None
    provider_key_metadata: Mapping[str, Any] = field(default_factory=dict)


def resolve_evidence_summary_answer_ask_model_selection(
    selection_input: EvidenceSummaryAnswerAskModelSelectionInput,
    *,
    alias_conflict_reason: str = "model_alias_conflicts_with_explicit_model_options",
    alias_unknown_reason_prefix: str = "model_alias_unknown",
) -> EvidenceSummaryAnswerAskModelSelectionResult:
    """Resolve product-level ask model alias, profile refs and route kind."""

    explicit_model_name = _normalized_optional_text(selection_input.model_name)
    alias = _normalized_optional_text(selection_input.model_alias)
    provider_profile_ref = _normalized_optional_text(
        selection_input.provider_profile_ref
    )
    model_profile_ref = _normalized_optional_text(selection_input.model_profile_ref)
    output_governance_profile_ref = _normalized_optional_text(
        selection_input.output_governance_profile_ref
    )
    blocking_reasons: tuple[str, ...] = ()

    if alias is not None:
        if any(
            value is not None
            for value in (
                explicit_model_name,
                provider_profile_ref,
                model_profile_ref,
                output_governance_profile_ref,
            )
        ):
            blocking_reasons = (alias_conflict_reason,)
        else:
            runtime_view = RuntimeLiveLlmConfigView()
            alias_config = runtime_view.model_aliases.get(alias)
            if alias_config is None:
                blocking_reasons = (f"{alias_unknown_reason_prefix}:{alias}",)
            else:
                model_profile = runtime_view.model_profiles[
                    alias_config.model_profile_ref
                ]
                explicit_model_name = alias_config.model_name or model_profile.model_name
                provider_profile_ref = alias_config.provider_profile_ref
                model_profile_ref = alias_config.model_profile_ref
                output_governance_profile_ref = (
                    alias_config.output_governance_profile_ref
                )

    model_name = explicit_model_name or RuntimeLiveLlmConfigView().model_name
    backend_provider = evidence_summary_answer_ask_route_backend_provider(
        model_name=model_name,
        provider_profile_ref=provider_profile_ref,
    )
    external_provider_selected = (
        evidence_summary_answer_ask_external_provider_selected(
            model_name=model_name,
            provider_profile_ref=provider_profile_ref,
            model_profile_ref=model_profile_ref,
            output_governance_profile_ref=output_governance_profile_ref,
        )
    )
    return EvidenceSummaryAnswerAskModelSelectionResult(
        model_name=model_name,
        model_alias=alias,
        provider_profile_ref=provider_profile_ref,
        model_profile_ref=model_profile_ref,
        output_governance_profile_ref=output_governance_profile_ref,
        backend_provider=backend_provider,
        route_kind=evidence_summary_answer_ask_route_kind(backend_provider),
        external_provider_selected=external_provider_selected,
        local_ollama_selected=not external_provider_selected,
        blocking_reasons=blocking_reasons,
    )


def resolve_evidence_summary_answer_ask_llm_service(
    factory: Any,
    resolution_input: EvidenceSummaryAnswerAskLlmServiceResolutionInput,
    *,
    provider_key_env_name: str = "DEEPSEEK_API_KEY",
    provider_resolution_failed_reason: str = (
        "external_readonly_ask_llm_provider_resolution_failed"
    ),
    provider_exception_warning: str = "external_readonly_ask_llm_provider_exception",
) -> dict[str, Any]:
    """Resolve an ask LLM service without making the channel adapter own routing."""

    selection = resolution_input.model_selection
    try:
        with _temporary_provider_key_env(
            provider_key_env_name,
            resolution_input.provider_key,
        ):
            resolution = factory.resolve(
                config_context=None,
                config_selection=RuntimeConfigSelectionContext(
                    config_root=resolution_input.config_root,
                    environment=resolution_input.environment,
                    profile=resolution_input.profile,
                    selection_source=resolution_input.source,
                    metadata={
                        "request_id": resolution_input.request_id,
                        "surface": resolution_input.surface,
                        "product_path": resolution_input.product_path,
                    },
                ),
                live_llm_options=RuntimeLiveLlmInvocationOptionsContext(
                    ollama_api_base=resolution_input.ollama_api_base,
                    timeout_seconds=resolution_input.timeout_seconds,
                    max_tokens=resolution_input.max_tokens,
                    response_preview_limit=resolution_input.response_preview_limit,
                    provider_profile_ref=selection.provider_profile_ref,
                    model_profile_ref=selection.model_profile_ref,
                    output_governance_profile_ref=(
                        selection.output_governance_profile_ref
                    ),
                    network_gate_open=resolution_input.network_gate_open,
                    operator_approved=resolution_input.operator_approved,
                    approval_ref=resolution_input.approval_ref,
                    audit_ref=resolution_input.audit_ref,
                    selection_source=resolution_input.source,
                    metadata={
                        "request_id": resolution_input.request_id,
                        "surface": resolution_input.surface,
                        "model_name": selection.model_name,
                        "provider_profile_ref": selection.provider_profile_ref,
                        "model_profile_ref": selection.model_profile_ref,
                        "output_governance_profile_ref": (
                            selection.output_governance_profile_ref
                        ),
                        "provider_key_supplied_by_prompt": False,
                        "provider_key_persistent_save": False,
                        **dict(resolution_input.provider_key_metadata),
                        "product_path": resolution_input.product_path,
                    },
                ),
            )
    except Exception:
        return {
            "service": None,
            "blocking_reasons": (provider_resolution_failed_reason,),
            "warnings": (provider_exception_warning,),
        }
    blocking_reasons = tuple(str(item) for item in resolution.blocking_reasons)
    service = resolution.service
    invoker = _llm_invoker(service)
    if blocking_reasons or service is None:
        return {
            "service": None,
            "llm_invoker": None,
            "blocking_reasons": blocking_reasons
            or (provider_resolution_failed_reason,),
            "warnings": tuple(str(item) for item in resolution.warnings),
        }
    if invoker is None:
        return {
            "service": None,
            "llm_invoker": None,
            "blocking_reasons": (provider_resolution_failed_reason,),
            "warnings": tuple(str(item) for item in resolution.warnings),
        }
    return {
        "service": service,
        "llm_invoker": invoker,
        "blocking_reasons": (),
        "warnings": tuple(str(item) for item in resolution.warnings),
    }


def _llm_invoker(service: Any) -> Any | None:
    invoker = getattr(service, "invoke", None)
    return invoker if callable(invoker) else None


def resolve_evidence_summary_answer_ask_model_selection_from_channel_options(
    options: Any,
    *,
    alias_conflict_reason: str = "model_alias_conflicts_with_explicit_model_options",
    alias_unknown_reason_prefix: str = "model_alias_unknown",
) -> EvidenceSummaryAnswerAskModelSelectionResult:
    """Resolve model selection from a channel options object without CLI logic."""

    return resolve_evidence_summary_answer_ask_model_selection(
        EvidenceSummaryAnswerAskModelSelectionInput(
            model_name=getattr(options, "model_name", None),
            model_alias=getattr(options, "model_alias", None),
            provider_profile_ref=getattr(options, "llm_provider_profile_ref", None),
            model_profile_ref=getattr(options, "llm_model_profile_ref", None),
            output_governance_profile_ref=getattr(
                options,
                "llm_output_governance_profile_ref",
                None,
            ),
        ),
        alias_conflict_reason=alias_conflict_reason,
        alias_unknown_reason_prefix=alias_unknown_reason_prefix,
    )


def apply_evidence_summary_answer_ask_model_selection_to_channel_options(
    options: Any,
    selection: EvidenceSummaryAnswerAskModelSelectionResult,
) -> None:
    """Apply resolved model selection facts back to a channel options object."""

    setattr(options, "model_name", selection.model_name)
    setattr(options, "llm_provider_profile_ref", selection.provider_profile_ref)
    setattr(options, "llm_model_profile_ref", selection.model_profile_ref)
    setattr(
        options,
        "llm_output_governance_profile_ref",
        selection.output_governance_profile_ref,
    )


def build_evidence_summary_answer_ask_route_facts(
    route_input: EvidenceSummaryAnswerAskRoutePolicyInput,
) -> ModelRouteFacts:
    """Build product-level model route facts for an ask action."""

    model_name = route_input.model_name.strip()
    backend_provider = evidence_summary_answer_ask_route_backend_provider(
        model_name=model_name,
        provider_profile_ref=route_input.provider_profile_ref,
    )
    return ModelRouteFacts(
        model_name=model_name,
        provider="litellm",
        source=route_input.source,
        metadata={
            "backend_provider": backend_provider,
            "route_kind": evidence_summary_answer_ask_route_kind(backend_provider),
            "route_target": model_name,
            "route_fact_contract": "schemas.model_routing.ModelRouteFacts",
            "provider_profile_ref": route_input.provider_profile_ref,
            "model_profile_ref": route_input.model_profile_ref,
            "output_governance_profile_ref": (
                route_input.output_governance_profile_ref
            ),
            "product_path": route_input.product_path,
            **dict(route_input.metadata),
        },
    )


def build_evidence_summary_answer_ask_governance_precondition(
    *,
    approval_ref: str | None,
    command: str,
    product_path: str,
    source: str = PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ASK_POLICY_SOURCE,
    metadata: Mapping[str, Any] | None = None,
) -> LlmGovernancePrecondition:
    """Build product-level governance precondition for ask model invocation."""

    return LlmGovernancePrecondition(
        allowed=True,
        reason="external_readonly_ask_explicit_controlled_product_generation",
        decision="allow",
        governance_decision_ref=approval_ref,
        metadata={
            "source": source,
            "surface": command,
            "product_path": product_path,
            **dict(metadata or {}),
        },
    )


def evidence_summary_answer_ask_external_provider_selected(
    *,
    model_name: str | None,
    provider_profile_ref: str | None,
    model_profile_ref: str | None,
    output_governance_profile_ref: str | None,
) -> bool:
    """Return whether the selected route points to an external provider."""

    if isinstance(provider_profile_ref, str) and provider_profile_ref:
        return provider_profile_ref != "local_ollama"
    if any(
        isinstance(value, str) and value
        for value in (model_profile_ref, output_governance_profile_ref)
    ):
        return True
    return bool(model_name and not model_name.startswith("ollama/"))


def evidence_summary_answer_ask_route_backend_provider(
    *,
    model_name: str,
    provider_profile_ref: str | None,
) -> str:
    """Resolve the product-level backend provider label for route facts."""

    if isinstance(provider_profile_ref, str) and provider_profile_ref:
        if provider_profile_ref == "local_ollama":
            return "ollama"
        return provider_profile_ref.removesuffix("_gated")
    if model_name.startswith("ollama/"):
        return "ollama"
    return model_name.split("/", 1)[0]


def evidence_summary_answer_ask_route_kind(backend_provider: str) -> str:
    """Return the safe route kind label for product route facts."""

    if backend_provider == "ollama":
        return "adk_litellm"
    return "adk_litellm_openai_compatible"


def _normalized_optional_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


@contextmanager
def _temporary_provider_key_env(env_name: str, provider_key: str | None) -> Any:
    if not provider_key:
        yield
        return
    sentinel = object()
    previous = os.environ.get(env_name, sentinel)
    os.environ[env_name] = provider_key
    try:
        yield
    finally:
        if previous is sentinel:
            os.environ.pop(env_name, None)
        else:
            os.environ[env_name] = str(previous)
