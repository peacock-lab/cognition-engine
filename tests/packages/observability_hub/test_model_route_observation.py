from __future__ import annotations

from observability_hub import ModelRouteObservation, build_model_route_observation
from schemas.model_routing import ModelRouteFacts


def test_observability_hub_builds_model_route_observation_from_public_facts() -> None:
    facts = ModelRouteFacts(
        model_name="ollama/gemma4-pro:latest",
        provider="litellm",
        adk_version="2.0.0b1",
        litellm_version="1.82.6",
        source="adk_adapter.models",
        metadata={
            "route": "ADK LiteLlm local route",
            "backend_provider": "ollama",
            "route_target": "ollama/gemma4-pro:latest",
            "route_kind": "adk_litellm",
        },
    )

    observation = build_model_route_observation(facts)

    assert isinstance(observation, ModelRouteObservation)
    assert observation.model_name == "ollama/gemma4-pro:latest"
    assert observation.provider == "litellm"
    assert observation.route_source == "adk_adapter.models"
    assert observation.runtime_call_performed is False
    assert observation.direct_litellm_completion is False
    assert observation.governance_direct_model_call is False
    assert observation.metadata["route_metadata"]["backend_provider"] == "ollama"
    assert observation.metadata["route_metadata"]["route_target"] == (
        "ollama/gemma4-pro:latest"
    )
    assert observation.metadata["route_metadata"]["route_kind"] == "adk_litellm"
    assert observation.metadata["does_not_call_model"] is True
    assert observation.metadata["does_not_store_prompt"] is True
    assert observation.metadata["does_not_store_completion"] is True
