"""Model capability skeletons for ADK LiteLlm local model routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import metadata as importlib_metadata
from typing import Any

from schemas.model_routing import ModelRouteFacts


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


def _installed_version(distribution_name: str) -> str | None:
    try:
        return importlib_metadata.version(distribution_name)
    except importlib_metadata.PackageNotFoundError:
        return None
