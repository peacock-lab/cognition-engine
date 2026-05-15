from __future__ import annotations

import re
from pathlib import Path

from contract_core.llm_invocation import (
    GovernedLlmInvocationService,
    LlmGovernancePrecondition,
    LlmInvocationFailureType,
    LlmInvocationRequest,
    LlmInvocationResult,
)
from contract_core.model_routing import ModelRouteFacts
from runtime_container import llm_invocation_facade
from runtime_container.llm_invocation_facade import (
    RuntimeContainerLlmInvocationFacade,
    build_runtime_container_llm_invocation_request,
    run_runtime_container_llm_invocation,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_CONTAINER_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "runtime_container" / "src" / "runtime_container"
)


class NoLiveGovernedLlmInvocationService:
    def __init__(self) -> None:
        self.requests: list[LlmInvocationRequest] = []

    def invoke(self, request: LlmInvocationRequest) -> LlmInvocationResult:
        self.requests.append(request)
        return LlmInvocationResult(
            request_id=request.request_id,
            route_facts=request.route_facts,
            governance_precondition=request.governance_precondition,
            call_attempted=False,
            call_allowed=True,
            runtime_call_performed=False,
            success=False,
            response_non_empty=False,
            failure_type=LlmInvocationFailureType.LIVE_DISABLED,
            error_message_sanitized="live invocation remains disabled",
            metadata={"facade_test": "no-live"},
        )


def test_runtime_container_builds_llm_invocation_request_through_runtime_helper() -> None:
    request = build_runtime_container_llm_invocation_request(
        request_id="runtime-container-llm-request-1",
        route_facts=_route_facts(),
        governance_precondition=_governance_precondition(),
        prompt_ref="prompt-ref-1",
        prompt_preview_sanitized="sanitized prompt preview",
        metadata={"source": "runtime-container-test"},
    )

    assert isinstance(request, LlmInvocationRequest)
    assert request.metadata["runtime_boundary"] == "runtime.llm_invocation"
    assert (
        request.metadata["runtime_container_facade"]
        == "runtime_container.llm_invocation_facade"
    )
    assert request.metadata["source"] == "runtime-container-test"


def test_runtime_container_facade_returns_no_live_llm_invocation_result() -> None:
    service: GovernedLlmInvocationService = NoLiveGovernedLlmInvocationService()
    request = build_runtime_container_llm_invocation_request(
        request_id="runtime-container-llm-request-1",
        route_facts=_route_facts(),
        governance_precondition=_governance_precondition(),
    )

    result = run_runtime_container_llm_invocation(
        service=service,
        request=request,
        metadata={"source": "runtime-container-test"},
    )

    assert result.failure_type == LlmInvocationFailureType.LIVE_DISABLED
    assert result.call_attempted is False
    assert result.call_allowed is True
    assert result.runtime_call_performed is False
    assert result.success is False
    assert len(service.requests) == 1
    assert service.requests[0] is request


def test_runtime_container_llm_invocation_facade_holder_runs_through_runtime() -> None:
    service: GovernedLlmInvocationService = NoLiveGovernedLlmInvocationService()
    facade = RuntimeContainerLlmInvocationFacade(
        service=service,
        metadata={"source": "facade-holder-test"},
    )
    request = build_runtime_container_llm_invocation_request(
        request_id="runtime-container-llm-request-1",
        route_facts=_route_facts(),
        governance_precondition=_governance_precondition(),
    )

    result = facade.run(request)

    assert result.failure_type == LlmInvocationFailureType.LIVE_DISABLED
    assert facade.to_metadata()["does_not_configure_live"] is True
    assert facade.to_metadata()["metadata"] == {"source": "facade-holder-test"}


def test_runtime_container_llm_invocation_public_module_is_exported() -> None:
    assert llm_invocation_facade.RuntimeContainerLlmInvocationFacade is (
        RuntimeContainerLlmInvocationFacade
    )
    assert llm_invocation_facade.build_runtime_container_llm_invocation_request is (
        build_runtime_container_llm_invocation_request
    )
    assert llm_invocation_facade.run_runtime_container_llm_invocation is (
        run_runtime_container_llm_invocation
    )


def test_runtime_container_llm_invocation_source_has_no_adapter_or_live_dependencies() -> None:
    source = (RUNTIME_CONTAINER_SOURCE_ROOT / "llm_invocation_facade.py").read_text(
        encoding="utf-8"
    )
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:adk_adapter|litellm|google\.adk|composition|cognition_agent)\b",
        re.MULTILINE,
    )
    forbidden_calls = re.compile(
        r"\b(?:completion|acompletion|runner\.run|run_async)\s*\("
    )

    assert forbidden_imports.search(source) is None
    assert forbidden_calls.search(source) is None
    assert "live_enabled=True" not in source
    assert "AdkGovernedLlmInvocationService" not in source
    assert "LLMClient" not in source
    assert "ModelExecutor" not in source
    assert "AgentModelRuntime" not in source
    assert "Chat" not in source
    assert "Gateway" not in source
    assert "ToolExecutor" not in source


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


def _governance_precondition() -> LlmGovernancePrecondition:
    return LlmGovernancePrecondition(
        allowed=True,
        reason="runtime_container_precondition_allowed",
        decision="continue",
        governance_decision_ref="governance-decision-1",
    )
