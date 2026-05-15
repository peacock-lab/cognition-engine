from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from schemas.model_routing import ModelRouteFacts


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMAS_MODEL_ROUTING_ROOT = (
    REPO_ROOT / "packages" / "schemas" / "src" / "schemas" / "model_routing"
)


def test_model_route_facts_are_non_executing_public_facts() -> None:
    facts = ModelRouteFacts(
        model_name="ollama/gemma4-pro:latest",
        provider="litellm",
        adk_version="2.0.0b1",
        litellm_version="1.82.6",
        pydantic_version="2.13.3",
        pydantic_core_version="2.46.3",
        source="adk_adapter.models",
        metadata={
            "route": "ADK LiteLlm local route",
            "backend_provider": "ollama",
            "route_target": "ollama/gemma4-pro:latest",
            "route_kind": "adk_litellm",
        },
    )

    assert facts.provider == "litellm"
    assert facts.metadata["backend_provider"] == "ollama"
    assert facts.metadata["route_target"] == "ollama/gemma4-pro:latest"
    assert facts.metadata["route_kind"] == "adk_litellm"
    assert facts.runtime_call_performed is False
    assert facts.direct_litellm_completion is False
    assert facts.governance_direct_model_call is False
    assert facts.to_observability_input()["candidate_target"] == (
        "observability_hub.ModelRouteObservation"
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "runtime_call_performed",
        "direct_litellm_completion",
        "governance_direct_model_call",
    ],
)
def test_model_route_facts_reject_execution_flags(field_name: str) -> None:
    with pytest.raises(ValidationError):
        ModelRouteFacts(
            model_name="ollama/gemma4-pro:latest",
            provider="litellm",
            **{field_name: True},
        )


def test_model_route_facts_reject_prompt_or_response_payloads() -> None:
    with pytest.raises(ValidationError):
        ModelRouteFacts(
            model_name="ollama/gemma4-pro:latest",
            provider="litellm",
            metadata={"prompt": "hello"},
        )


def test_model_routing_schemas_do_not_import_adapter_or_model_libraries() -> None:
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+(?:adk_adapter|google\.adk|litellm)\b",
        re.MULTILINE,
    )

    for source_path in SCHEMAS_MODEL_ROUTING_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_imports.search(source) is None, source_path
