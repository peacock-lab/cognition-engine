from __future__ import annotations

import re
from pathlib import Path

from cognition_agent import AgentLlmInvocationSummaryCandidate
from composition import (
    LlmInvocationReadonlyProductBundle,
    build_llm_invocation_readonly_product_bundle,
)
from observability_hub import LlmCallObservationCandidate
from schemas.llm_invocation import (
    LlmGovernancePrecondition,
    LlmInvocationFailureType,
    LlmInvocationResult,
)
from schemas.model_routing import ModelRouteFacts


REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSITION_SOURCE_ROOT = REPO_ROOT / "packages" / "composition" / "src" / "composition"


def test_builds_readonly_observation_and_agent_summary_bundle() -> None:
    bundle = build_llm_invocation_readonly_product_bundle(
        _invocation_result(),
        metadata={"test_case": "readonly-bundle"},
    )

    assert isinstance(bundle, LlmInvocationReadonlyProductBundle)
    assert isinstance(bundle.observation_candidate, LlmCallObservationCandidate)
    assert isinstance(
        bundle.agent_summary_candidate,
        AgentLlmInvocationSummaryCandidate,
    )
    assert bundle.observation_candidate.request_id == "llm-request-readonly-1"
    assert bundle.observation_candidate.failure_type == "live_disabled"
    assert bundle.agent_summary_candidate.request_id == "llm-request-readonly-1"
    assert bundle.agent_summary_candidate.readonly is True
    assert bundle.agent_summary_candidate.candidate_only is True
    assert bundle.agent_summary_candidate.llm_call_enabled is False
    assert bundle.agent_summary_candidate.service_invoke_enabled is False


def test_readonly_bundle_public_refs_are_compact_and_sanitized() -> None:
    bundle = build_llm_invocation_readonly_product_bundle(_invocation_result())
    refs = bundle.to_public_refs()
    facts = refs["llm_invocation_readonly_facts"]

    assert refs["llm_invocation_observation_ref"] == (
        "llm-call-observation://llm-request-readonly-1"
    )
    assert refs["llm_invocation_summary_ref"] == (
        "agent-llm-invocation-summary://llm-request-readonly-1"
    )
    assert facts["request_id"] == "llm-request-readonly-1"
    assert facts["call_allowed"] is True
    assert facts["call_attempted"] is False
    assert facts["runtime_call_performed"] is False
    assert facts["failure_type"] == "live_disabled"
    assert facts["sanitized_response_length"] is None
    assert facts["sanitized_response_preview"] is None
    assert facts["live_profile"] is None
    assert facts["readonly"] is True
    assert facts["candidate_only"] is True
    assert facts["does_not_call_model"] is True
    assert facts["does_not_store_prompt"] is True
    assert facts["does_not_store_raw_provider_response"] is True
    assert "prompt" not in facts
    assert "messages" not in facts
    assert "raw_provider_response" not in facts
    assert "response_text" not in facts


def test_readonly_bundle_public_refs_include_compact_live_profile() -> None:
    bundle = build_llm_invocation_readonly_product_bundle(
        _invocation_result(
            request_id="llm-request-live-profile-1",
            call_attempted=True,
            runtime_call_performed=True,
            success=True,
            failure_type=None,
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
    )

    facts = bundle.to_public_refs()["llm_invocation_readonly_facts"]

    assert facts["success"] is True
    assert facts["sanitized_response_length"] == 2
    assert facts["sanitized_response_preview"] == "ok"
    assert facts["live_profile"] == {
        "controlled_live": True,
        "live_options_source": "config_contexts.runtime.RuntimeLiveLlmConfigView",
        "live_service_profile": "adk_litellm_ollama",
        "configured_model_name": "ollama/gemma4-pro:latest",
        "timeout_seconds": 45,
        "temperature": 0,
        "max_tokens": 64,
        "local_no_proxy_applied": True,
    }
    assert "ollama_api_base" not in facts["live_profile"]


def test_readonly_assembly_source_does_not_execute_or_import_runtime_container() -> None:
    source = (
        COMPOSITION_SOURCE_ROOT / "llm_invocation_readonly_assembly.py"
    ).read_text(encoding="utf-8")
    forbidden_calls = re.compile(
        r"\b(?:completion|acompletion|runner\.run|run_async)\s*\("
    )

    assert ".invoke(" not in source
    assert "service.invoke" not in source
    assert "from runtime_container" not in source
    assert "import runtime_container" not in source
    assert "from adk_adapter" not in source
    assert "import adk_adapter" not in source
    assert forbidden_calls.search(source) is None


def _invocation_result(
    *,
    request_id: str = "llm-request-readonly-1",
    call_attempted: bool = False,
    runtime_call_performed: bool = False,
    success: bool = False,
    failure_type: LlmInvocationFailureType | None = LlmInvocationFailureType.LIVE_DISABLED,
    metadata: dict[str, object] | None = None,
) -> LlmInvocationResult:
    return LlmInvocationResult(
        request_id=request_id,
        route_facts=ModelRouteFacts(
            model_name="ollama/gemma4-pro:latest",
            provider="litellm",
            source="test",
            metadata={
                "backend_provider": "ollama",
                "route_kind": "adk_litellm",
                "route_target": "ollama/gemma4-pro:latest",
            },
        ),
        governance_precondition=LlmGovernancePrecondition(
            allowed=True,
            reason="no-live boundary allowed",
            decision="continue_no_live",
            governance_decision_ref="governance-decision-readonly-1",
        ),
        call_attempted=call_attempted,
        call_allowed=True,
        runtime_call_performed=runtime_call_performed,
        success=success,
        response_non_empty=success,
        sanitized_response_length=2 if success else None,
        sanitized_response_preview="ok" if success else None,
        failure_type=failure_type,
        error_message_sanitized=(
            None if success else "live invocation remains disabled"
        ),
        metadata=metadata or {},
    )
