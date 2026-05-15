from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from cognition_agent import (
    LLM_CALL_OBSERVATION_SUMMARY_SOURCE,
    LLM_INVOCATION_RESULT_SUMMARY_SOURCE,
    LLM_INVOCATION_SUMMARY_VERSION,
    AgentLlmInvocationSummaryCandidate,
    build_agent_llm_invocation_summary_from_invocation_result,
    build_agent_llm_invocation_summary_from_observation_candidate,
)
from schemas.llm_invocation import (
    LlmGovernancePrecondition,
    LlmInvocationFailureType,
    LlmInvocationResult,
)
from schemas.model_routing import ModelRouteFacts


REPO_ROOT = Path(__file__).resolve().parents[3]
COGNITION_AGENT_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "cognition_agent" / "src" / "cognition_agent"
)


def test_agent_llm_invocation_summary_from_invocation_result_is_readonly() -> None:
    view = build_agent_llm_invocation_summary_from_invocation_result(
        candidate_id="agent-llm-summary-1",
        invocation_result=_invocation_result(),
    )

    assert isinstance(view, AgentLlmInvocationSummaryCandidate)
    assert view.candidate_type == "agent_llm_invocation_summary_candidate"
    assert view.summary_version == LLM_INVOCATION_SUMMARY_VERSION
    assert view.summary_source == LLM_INVOCATION_RESULT_SUMMARY_SOURCE
    assert view.request_id == "llm-request-1"
    assert view.model_name == "ollama/gemma4-pro:latest"
    assert view.provider == "litellm"
    assert view.backend_provider == "ollama"
    assert view.route_kind == "adk_litellm"
    assert view.call_allowed is True
    assert view.call_attempted is False
    assert view.runtime_call_performed is False
    assert view.success is False
    assert view.failure_type == "live_disabled"
    assert view.governance_decision_ref == "governance-decision-1"
    assert view.readonly is True
    assert view.candidate_only is True
    assert view.execution_enabled is False
    assert view.llm_call_enabled is False
    assert view.service_invoke_enabled is False
    assert view.metadata["does_not_call_runtime"] is True
    assert view.metadata["does_not_call_runtime_container"] is True
    assert view.metadata["does_not_call_service_invoke"] is True


def test_agent_llm_invocation_summary_from_observation_candidate_shape() -> None:
    view = build_agent_llm_invocation_summary_from_observation_candidate(
        candidate_id="agent-llm-summary-2",
        observation_candidate={
            "request_id": "llm-request-2",
            "model_name": "ollama/gemma4-pro:latest",
            "provider": "litellm",
            "backend_provider": "ollama",
            "route_kind": "adk_litellm",
            "route_target": "ollama/gemma4-pro:latest",
            "call_attempted": True,
            "call_allowed": True,
            "runtime_call_performed": True,
            "success": True,
            "response_non_empty": True,
            "sanitized_response_length": 2,
            "sanitized_response_preview": "ok",
            "governance_decision_ref": "governance-decision-2",
            "metadata": {
                "observation_semantics": "llm_invocation_sanitized_candidate",
                "does_not_store_prompt": True,
                "does_not_store_raw_provider_response": True,
                "llm_live_profile": {
                    "controlled_live": True,
                    "live_options_source": (
                        "config_contexts.runtime.RuntimeLiveLlmConfigView"
                    ),
                    "live_service_profile": "adk_litellm_ollama",
                    "configured_model_name": "ollama/gemma4-pro:latest",
                    "timeout_seconds": 45,
                    "temperature": 0,
                    "max_tokens": 64,
                    "local_no_proxy_applied": True,
                },
            },
        },
    )

    assert view.summary_source == LLM_CALL_OBSERVATION_SUMMARY_SOURCE
    assert view.success is True
    assert view.runtime_call_performed is True
    assert view.sanitized_response_preview == "ok"
    assert view.metadata["source_metadata"]["does_not_store_prompt"] is True
    assert view.metadata["source_metadata"]["llm_live_profile"][
        "live_service_profile"
    ] == "adk_litellm_ollama"
    assert view.metadata["source_metadata"]["llm_live_profile"][
        "local_no_proxy_applied"
    ] is True


def test_agent_llm_invocation_summary_rejects_raw_payload_metadata() -> None:
    with pytest.raises(ValueError):
        build_agent_llm_invocation_summary_from_invocation_result(
            candidate_id="agent-llm-summary-raw-1",
            invocation_result={
                **_invocation_result().model_dump(mode="python"),
                "metadata": {"raw_provider_response": {"content": "raw"}},
            },
        )


def test_agent_llm_invocation_summary_rejects_execution_flags() -> None:
    with pytest.raises(ValidationError):
        AgentLlmInvocationSummaryCandidate(
            candidate_id="agent-llm-summary-invalid-1",
            source=LLM_INVOCATION_RESULT_SUMMARY_SOURCE,
            summary="Invalid LLM invocation summary.",
            request_id="llm-request-1",
            model_name="ollama/gemma4-pro:latest",
            provider="litellm",
            execution_enabled=True,
        )


def test_cognition_agent_llm_invocation_source_has_no_execution_dependencies() -> None:
    source = (COGNITION_AGENT_SOURCE_ROOT / "llm_invocation_view.py").read_text(
        encoding="utf-8"
    )
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:adk_adapter|litellm|google\.adk|runtime_container|observability_hub)\b",
        re.MULTILINE,
    )
    forbidden_calls = re.compile(
        r"\b(?:completion|acompletion|service\.invoke|run_governed_llm_invocation)\s*\("
    )

    assert forbidden_imports.search(source) is None
    assert forbidden_calls.search(source) is None
    assert "live_enabled=True" not in source
    assert "ActionCandidate" not in source
    assert "RuntimeActionCandidate" not in source
    assert "AgentRuntime" not in source
    assert "ToolExecutor" not in source
    assert "Chat" not in source
    assert "Gateway" not in source


def _invocation_result() -> LlmInvocationResult:
    return LlmInvocationResult(
        request_id="llm-request-1",
        route_facts=ModelRouteFacts(
            model_name="ollama/gemma4-pro:latest",
            provider="litellm",
            source="adk_adapter.models",
            metadata={
                "backend_provider": "ollama",
                "route_target": "ollama/gemma4-pro:latest",
                "route_kind": "adk_litellm",
            },
        ),
        governance_precondition=LlmGovernancePrecondition(
            allowed=True,
            reason="governance_allowed",
            decision="continue",
            governance_decision_ref="governance-decision-1",
        ),
        call_attempted=False,
        call_allowed=True,
        runtime_call_performed=False,
        success=False,
        response_non_empty=False,
        failure_type=LlmInvocationFailureType.LIVE_DISABLED,
        error_message_sanitized="live invocation remains disabled",
        metadata={"runtime_container_facade": "runtime_container.llm_invocation_facade"},
    )
