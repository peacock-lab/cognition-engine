from __future__ import annotations

import re
from pathlib import Path

import pytest
from schemas.model_routing import ModelRouteFacts

from adk_adapter.models import (
    AdkModelRouteFacts,
    build_litellm_deepseek_model_route,
    build_litellm_ollama_model_route,
)


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


def test_litellm_deepseek_route_facts_are_gated_and_non_executing() -> None:
    model, facts = build_litellm_deepseek_model_route(
        model_name="deepseek/deepseek-v4-flash",
        api_base="https://api.deepseek.com",
        secret_ref="secret-ref://env/DEEPSEEK_API_KEY",
        network_gate_open=True,
        operator_approved=True,
        approval_ref="approval://manual/deepseek-smoke",
        audit_ref="audit://manual/deepseek-smoke",
        timeout=180,
        max_tokens=256,
    )

    public_facts = facts.to_public_model_route_facts()
    metadata = public_facts.metadata

    assert model.model == "deepseek/deepseek-v4-flash"
    assert model._additional_args["api_base"] == "https://api.deepseek.com"
    assert "custom_llm_provider" not in model._additional_args
    assert model._additional_args["extra_body"] == {
        "thinking": {"type": "disabled"}
    }
    assert public_facts.model_name == "deepseek/deepseek-v4-flash"
    assert public_facts.provider == "litellm"
    assert public_facts.runtime_call_performed is False
    assert public_facts.direct_litellm_completion is False
    assert public_facts.governance_direct_model_call is False
    assert metadata["backend_provider"] == "deepseek"
    assert metadata["route_target"] == "deepseek/deepseek-v4-flash"
    assert metadata["route_kind"] == "adk_litellm_openai_compatible"
    assert metadata["api_base_host"] == "api.deepseek.com"
    assert metadata["secret_ref"] == "secret-ref://env/DEEPSEEK_API_KEY"
    assert metadata["secret_ref_present"] is True
    assert metadata["model_family"] == "deepseek_v4"
    assert metadata["model_release"] == "v4"
    assert metadata["thinking_mode"] == "disabled"
    assert metadata["legacy_alias"] is False
    assert metadata["network_access"] == "external_gated"
    assert metadata["requires_network_gate"] is True
    assert metadata["network_gate_open"] is True
    assert metadata["operator_approved"] is True
    assert metadata["approval_ref_present"] is True
    assert metadata["audit_ref_present"] is True
    assert metadata["candidate_only"] is True
    assert metadata["enabled_by_default"] is False
    assert "api_key" not in metadata
    assert "authorization" not in {key.lower() for key in metadata}


def test_litellm_deepseek_route_accepts_v4_pro_candidate() -> None:
    model, facts = build_litellm_deepseek_model_route(
        model_name="deepseek/deepseek-v4-pro"
    )

    assert model.model == "deepseek/deepseek-v4-pro"
    assert facts.to_public_model_route_facts().metadata["route_target"] == (
        "deepseek/deepseek-v4-pro"
    )


def test_litellm_deepseek_route_rejects_unknown_thinking_mode() -> None:
    with pytest.raises(ValueError, match="thinking_mode"):
        build_litellm_deepseek_model_route(thinking_mode="auto")


@pytest.mark.parametrize(
    "model_name",
    ("deepseek-chat", "deepseek/deepseek-chat", "deepseek-v4-flash"),
)
def test_litellm_deepseek_route_rejects_legacy_or_unprefixed_model_names(
    model_name: str,
) -> None:
    with pytest.raises(ValueError, match="DeepSeek V4"):
        build_litellm_deepseek_model_route(model_name=model_name)


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
