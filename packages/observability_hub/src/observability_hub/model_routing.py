"""Model-route fact intake for observability-hub."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from schemas.model_routing import ModelRouteFacts


class ModelRouteObservation(BaseModel):
    """Internal observation record for a model route; no model output is stored."""

    model_config = ConfigDict(extra="forbid")

    observation_id: str
    model_name: str
    provider: str
    route_source: str
    runtime_call_performed: bool = False
    direct_litellm_completion: bool = False
    governance_direct_model_call: bool = False
    route_versions: dict[str, str | None] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str


def build_model_route_observation(
    route_facts: ModelRouteFacts | dict[str, Any],
) -> ModelRouteObservation:
    """Build an internal observation from public model route facts."""

    facts = (
        route_facts
        if isinstance(route_facts, ModelRouteFacts)
        else ModelRouteFacts.model_validate(route_facts)
    )
    return ModelRouteObservation(
        observation_id=f"model-route-observation-{uuid4()}",
        model_name=facts.model_name,
        provider=facts.provider,
        route_source=facts.source,
        runtime_call_performed=facts.runtime_call_performed,
        direct_litellm_completion=facts.direct_litellm_completion,
        governance_direct_model_call=facts.governance_direct_model_call,
        route_versions={
            "adk_version": facts.adk_version,
            "litellm_version": facts.litellm_version,
            "pydantic_version": facts.pydantic_version,
            "pydantic_core_version": facts.pydantic_core_version,
        },
        metadata={
            "observation_semantics": "route_facts_only",
            "does_not_store_prompt": True,
            "does_not_store_completion": True,
            "does_not_call_model": True,
            "route_metadata": dict(facts.metadata),
        },
        created_at=datetime.now(UTC).isoformat(),
    )
