from __future__ import annotations

from observability_hub import (
    LlmCallObservationCandidate,
    build_llm_call_observation_candidate,
    build_llm_call_observation_from_invocation_result,
)
from schemas.llm_invocation import (
    LlmGovernancePrecondition,
    LlmInvocationFailureType,
    LlmInvocationResult,
)
from schemas.model_routing import ModelRouteFacts


def test_builds_llm_call_observation_candidate_from_blocked_result() -> None:
    result = LlmInvocationResult(
        request_id="llm-request-1",
        route_facts=_route_facts(),
        governance_precondition=LlmGovernancePrecondition(
            allowed=False,
            reason="governance_blocked",
            decision="block",
            governance_decision_ref="governance-decision-1",
        ),
        call_attempted=False,
        call_allowed=False,
        runtime_call_performed=False,
        success=False,
        failure_type=LlmInvocationFailureType.GOVERNANCE_BLOCKED,
        error_message_sanitized="blocked before model call",
    )

    observation = build_llm_call_observation_candidate(result)

    assert isinstance(observation, LlmCallObservationCandidate)
    assert observation.request_id == "llm-request-1"
    assert observation.provider == "litellm"
    assert observation.backend_provider == "ollama"
    assert observation.route_kind == "adk_litellm"
    assert observation.runtime_call_performed is False
    assert observation.success is False
    assert observation.failure_type == "governance_blocked"
    assert observation.governance_decision_ref == "governance-decision-1"
    assert observation.metadata["does_not_call_model"] is True
    assert observation.metadata["does_not_store_prompt"] is True
    assert observation.metadata["does_not_store_completion"] is True
    assert observation.metadata["does_not_store_raw_provider_response"] is True


def test_builds_llm_call_observation_candidate_from_sanitized_success() -> None:
    result = LlmInvocationResult(
        request_id="llm-request-2",
        route_facts=_route_facts(),
        governance_precondition=LlmGovernancePrecondition(
            allowed=True,
            reason="governance_allowed",
            decision="continue",
            governance_decision_ref="governance-decision-2",
        ),
        call_attempted=True,
        call_allowed=True,
        runtime_call_performed=True,
        success=True,
        response_non_empty=True,
        sanitized_response_length=2,
        sanitized_response_preview="你好",
        latency_ms=42,
    )

    observation = build_llm_call_observation_candidate(result)

    assert observation.success is True
    assert observation.runtime_call_performed is True
    assert observation.sanitized_response_length == 2
    assert observation.sanitized_response_preview == "你好"
    assert observation.metadata["route_metadata"]["backend_provider"] == "ollama"


def test_builds_llm_call_observation_candidate_with_live_profile() -> None:
    result = LlmInvocationResult(
        request_id="llm-request-live-profile-1",
        route_facts=_route_facts(),
        governance_precondition=LlmGovernancePrecondition(
            allowed=True,
            reason="controlled_live_allowed",
            decision="continue_controlled_live",
            governance_decision_ref="governance-decision-live-profile-1",
        ),
        call_attempted=True,
        call_allowed=True,
        runtime_call_performed=True,
        success=True,
        response_non_empty=True,
        sanitized_response_length=2,
        sanitized_response_preview="你好",
        latency_ms=42,
        metadata={
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
            "options": {
                "ollama_api_base": "http://127.0.0.1:11434",
            },
        },
    )

    observation = build_llm_call_observation_candidate(result)

    assert observation.metadata["llm_live_profile"] == {
        "controlled_live": True,
        "live_options_source": "config_contexts.runtime.RuntimeLiveLlmConfigView",
        "live_service_profile": "adk_litellm_ollama",
        "configured_model_name": "ollama/gemma4-pro:latest",
        "timeout_seconds": 45,
        "temperature": 0,
        "max_tokens": 64,
        "local_no_proxy_applied": True,
    }
    assert "ollama_api_base" not in observation.metadata["llm_live_profile"]


def test_builds_llm_call_observation_from_runtime_container_result_dict() -> None:
    result = LlmInvocationResult(
        request_id="runtime-container-llm-request-1",
        route_facts=_route_facts(),
        governance_precondition=LlmGovernancePrecondition(
            allowed=True,
            reason="runtime_container_precondition_allowed",
            decision="continue",
            governance_decision_ref="governance-decision-3",
        ),
        call_attempted=False,
        call_allowed=True,
        runtime_call_performed=False,
        success=False,
        response_non_empty=False,
        failure_type=LlmInvocationFailureType.LIVE_DISABLED,
        error_message_sanitized="live invocation remains disabled",
        metadata={
            "runtime_container_facade": "runtime_container.llm_invocation_facade",
        },
    )

    observation = build_llm_call_observation_from_invocation_result(result.model_dump())

    assert isinstance(observation, LlmCallObservationCandidate)
    assert observation.request_id == "runtime-container-llm-request-1"
    assert observation.failure_type == "live_disabled"
    assert observation.call_allowed is True
    assert observation.call_attempted is False
    assert observation.runtime_call_performed is False
    assert observation.governance_decision_ref == "governance-decision-3"
    assert observation.metadata["result_metadata"] == {
        "runtime_container_facade": "runtime_container.llm_invocation_facade",
    }


def test_llm_call_observation_candidate_does_not_expose_raw_payload_fields() -> None:
    result = LlmInvocationResult(
        request_id="llm-request-3",
        route_facts=_route_facts(),
        governance_precondition=LlmGovernancePrecondition(
            allowed=False,
            reason="governance_blocked",
            decision="block",
        ),
        call_attempted=False,
        call_allowed=False,
        runtime_call_performed=False,
        success=False,
        failure_type=LlmInvocationFailureType.GOVERNANCE_BLOCKED,
        error_message_sanitized="blocked before model call",
    )

    observation = build_llm_call_observation_from_invocation_result(result)
    dumped = observation.model_dump()

    assert "prompt_ref" not in dumped
    assert "prompt_preview_sanitized" not in dumped
    assert "full_response" not in dumped
    assert "raw_provider_response" not in dumped
    assert "raw_response" not in dumped
    assert "prompt" not in observation.metadata["result_metadata"]
    assert "response" not in observation.metadata["result_metadata"]
    assert "raw_provider_response" not in observation.metadata["result_metadata"]
    assert observation.metadata["does_not_store_prompt"] is True
    assert observation.metadata["does_not_store_completion"] is True
    assert observation.metadata["does_not_store_raw_provider_response"] is True


def _route_facts() -> ModelRouteFacts:
    return ModelRouteFacts(
        model_name="ollama/gemma4-pro:latest",
        provider="litellm",
        source="adk_adapter.models",
        metadata={
            "backend_provider": "ollama",
            "route_target": "ollama/gemma4-pro:latest",
            "route_kind": "adk_litellm",
        },
    )
