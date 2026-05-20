"""Model capability skeletons for ADK LiteLlm model routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import metadata as importlib_metadata
import os
from typing import Any
from urllib.parse import urlparse

from schemas.model_routing import ModelRouteFacts


DEFAULT_LITELLM_DEEPSEEK_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_DEEPSEEK_SECRET_REF = "secret-ref://env/DEEPSEEK_API_KEY"
SUPPORTED_LITELLM_DEEPSEEK_V4_MODELS = frozenset(
    {
        "deepseek/deepseek-v4-flash",
        "deepseek/deepseek-v4-pro",
    }
)


@dataclass(frozen=True)
class AdkModelRouteFacts:
    """Facts for an ADK LiteLlm model route without declaring a new adapter."""

    model_name: str
    provider: str
    adk_version: str | None
    litellm_version: str | None
    pydantic_version: str | None
    pydantic_core_version: str | None
    runtime_call_performed: bool = False
    direct_litellm_completion: bool = False
    governance_direct_model_call: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Keep adapter-local model route facts non-executing."""

        if self.runtime_call_performed:
            raise ValueError("runtime_call_performed must remain false.")
        if self.direct_litellm_completion:
            raise ValueError("direct_litellm_completion must remain false.")
        if self.governance_direct_model_call:
            raise ValueError("governance_direct_model_call must remain false.")

    def to_public_model_route_facts(self) -> ModelRouteFacts:
        """Return public model route facts without ADK/LiteLLM objects."""

        return ModelRouteFacts(
            model_name=self.model_name,
            provider=self.provider,
            adk_version=self.adk_version,
            litellm_version=self.litellm_version,
            pydantic_version=self.pydantic_version,
            pydantic_core_version=self.pydantic_core_version,
            runtime_call_performed=self.runtime_call_performed,
            direct_litellm_completion=self.direct_litellm_completion,
            governance_direct_model_call=self.governance_direct_model_call,
            source="adk_adapter.models",
            metadata=dict(self.metadata),
        )

    def to_observability_input(self) -> dict[str, Any]:
        """Return model route facts intended for observability_hub."""

        payload = self.to_public_model_route_facts().to_observability_input()
        return {
            **payload,
            **payload["metadata"],
        }


def build_litellm_ollama_model_route(
    *,
    model_name: str = "ollama/gemma4-pro:latest",
) -> tuple[Any, AdkModelRouteFacts]:
    """Construct an ADK LiteLlm model route and return boundary facts."""

    from google.adk.models.lite_llm import LiteLlm

    model = LiteLlm(model=model_name)
    facts = AdkModelRouteFacts(
        model_name=model_name,
        provider="litellm",
        adk_version=_installed_version("google-adk"),
        litellm_version=_installed_version("litellm"),
        pydantic_version=_installed_version("pydantic"),
        pydantic_core_version=_installed_version("pydantic-core"),
        runtime_call_performed=False,
        direct_litellm_completion=False,
        governance_direct_model_call=False,
        metadata={
            "route": "ADK LiteLlm -> LlmAgent -> InMemoryRunner -> Ollama/Gemma4 -> ADK Event",
            "backend_provider": "ollama",
            "route_target": model_name,
            "route_kind": "adk_litellm",
            "route_fact_contract": "schemas.model_routing.ModelRouteFacts",
        },
    )
    return model, facts


def build_litellm_deepseek_model_route(
    *,
    model_name: str = DEFAULT_LITELLM_DEEPSEEK_MODEL,
    api_base: str | None = None,
    api_key: str | None = None,
    secret_ref: str = DEFAULT_DEEPSEEK_SECRET_REF,
    network_gate_open: bool = False,
    operator_approved: bool = False,
    approval_ref: str | None = None,
    audit_ref: str | None = None,
    timeout: int | None = None,
    temperature: float | None = 0,
    max_tokens: int | None = None,
    thinking_mode: str | None = "disabled",
) -> tuple[Any, AdkModelRouteFacts]:
    """Construct an ADK LiteLlm DeepSeek route and return boundary facts."""

    if model_name not in SUPPORTED_LITELLM_DEEPSEEK_V4_MODELS:
        raise ValueError("DeepSeek route currently supports DeepSeek V4 models only.")
    if not secret_ref:
        raise ValueError("secret_ref is required for DeepSeek route facts.")

    from google.adk.models.lite_llm import LiteLlm

    model_kwargs: dict[str, Any] = {}
    if api_base:
        model_kwargs["api_base"] = api_base
    resolved_api_key = api_key or _api_key_from_secret_ref(secret_ref)
    if resolved_api_key:
        model_kwargs["api_key"] = resolved_api_key
    if timeout is not None:
        model_kwargs["timeout"] = timeout
    if temperature is not None:
        model_kwargs["temperature"] = temperature
    if max_tokens is not None:
        model_kwargs["max_tokens"] = max_tokens
    if thinking_mode is not None:
        if thinking_mode not in {"disabled", "enabled"}:
            raise ValueError("DeepSeek thinking_mode must be disabled or enabled.")
        model_kwargs["extra_body"] = {"thinking": {"type": thinking_mode}}

    model = LiteLlm(model=model_name, **model_kwargs)
    facts = AdkModelRouteFacts(
        model_name=model_name,
        provider="litellm",
        adk_version=_installed_version("google-adk"),
        litellm_version=_installed_version("litellm"),
        pydantic_version=_installed_version("pydantic"),
        pydantic_core_version=_installed_version("pydantic-core"),
        runtime_call_performed=False,
        direct_litellm_completion=False,
        governance_direct_model_call=False,
        metadata={
            "route": (
                "ADK LiteLlm -> LlmAgent -> InMemoryRunner -> "
                "DeepSeek V4 -> ADK Event"
            ),
            "backend_provider": "deepseek",
            "route_target": model_name,
            "route_kind": "adk_litellm_openai_compatible",
            "route_fact_contract": "schemas.model_routing.ModelRouteFacts",
            "api_base_host": _url_host(api_base),
            "secret_ref": secret_ref,
            "secret_ref_present": bool(secret_ref),
            "model_family": "deepseek_v4",
            "model_release": "v4",
            "thinking_mode": thinking_mode,
            "legacy_alias": False,
            "network_access": "external_gated",
            "requires_network_gate": True,
            "network_gate_open": network_gate_open,
            "operator_approved": operator_approved,
            "approval_ref_present": bool(approval_ref),
            "audit_ref_present": bool(audit_ref),
            "candidate_only": True,
            "enabled_by_default": False,
        },
    )
    return model, facts


def _installed_version(distribution_name: str) -> str | None:
    try:
        return importlib_metadata.version(distribution_name)
    except importlib_metadata.PackageNotFoundError:
        return None


def _url_host(value: str | None) -> str | None:
    if not value:
        return None
    return urlparse(value).hostname


def _api_key_from_secret_ref(secret_ref: str) -> str | None:
    prefix = "secret-ref://env/"
    if not secret_ref.startswith(prefix):
        return None
    env_var = secret_ref.removeprefix(prefix)
    if not env_var or not env_var.replace("_", "").isalnum():
        return None
    value = os.getenv(env_var)
    return value or None
