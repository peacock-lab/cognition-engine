from __future__ import annotations

import re
from pathlib import Path

import pytest
from schemas.model_routing import ModelRouteFacts

from adk_adapter.models import AdkModelRouteFacts, build_litellm_ollama_model_route


REPO_ROOT = Path(__file__).resolve().parents[3]
ADK_ADAPTER_SOURCE_ROOT = REPO_ROOT / "packages" / "adk_adapter" / "src" / "adk_adapter"


def test_adk_model_route_facts_convert_to_public_model_route_facts() -> None:
    _, facts = build_litellm_ollama_model_route(
        model_name="ollama/gemma4-pro:latest"
    )

    public_facts = facts.to_public_model_route_facts()
    observability_input = facts.to_observability_input()

    assert isinstance(public_facts, ModelRouteFacts)
    assert public_facts.model_name == "ollama/gemma4-pro:latest"
    assert public_facts.provider == "litellm"
    assert public_facts.metadata["backend_provider"] == "ollama"
    assert public_facts.metadata["route_target"] == "ollama/gemma4-pro:latest"
    assert public_facts.metadata["route_kind"] == "adk_litellm"
    assert public_facts.runtime_call_performed is False
    assert public_facts.direct_litellm_completion is False
    assert public_facts.governance_direct_model_call is False
    assert observability_input["candidate_target"] == (
        "observability_hub.ModelRouteObservation"
    )
    assert observability_input["runtime_call_performed"] is False
    assert observability_input["direct_litellm_completion"] is False
    assert observability_input["governance_direct_model_call"] is False


@pytest.mark.parametrize(
    "kwargs",
    [
        {"runtime_call_performed": True},
        {"direct_litellm_completion": True},
        {"governance_direct_model_call": True},
    ],
)
def test_adk_model_route_facts_reject_execution_flags(kwargs: dict[str, bool]) -> None:
    with pytest.raises(ValueError):
        AdkModelRouteFacts(
            model_name="ollama/gemma4-pro:latest",
            provider="litellm",
            adk_version=None,
            litellm_version=None,
            pydantic_version=None,
            pydantic_core_version=None,
            metadata={
                "backend_provider": "ollama",
                "route_target": "ollama/gemma4-pro:latest",
            },
            **kwargs,
        )


def test_adk_adapter_model_routing_source_does_not_call_completion_or_runner() -> None:
    source = (ADK_ADAPTER_SOURCE_ROOT / "models.py").read_text(encoding="utf-8")
    forbidden_calls = re.compile(
        r"\b(?:completion|acompletion|runner\.run|run_async)\s*\("
    )

    assert forbidden_calls.search(source) is None
