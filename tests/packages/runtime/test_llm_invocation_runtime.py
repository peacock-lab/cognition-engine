from __future__ import annotations

import re
from pathlib import Path

from behavior_contracts.llm_invocation import GovernedLlmInvocationService
from runtime.llm_invocation import (
    RuntimeLlmInvocationContext,
    build_runtime_llm_invocation_request,
    run_governed_llm_invocation,
)
from runtime.orchestrator import RuntimeDependencies
from schemas.llm_invocation import (
    LlmGovernancePrecondition,
    LlmInvocationFailureType,
    LlmInvocationRequest,
    LlmInvocationResult,
)
from schemas.model_routing import ModelRouteFacts


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_SOURCE_ROOT = REPO_ROOT / "packages" / "runtime" / "src" / "runtime"


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
            metadata={"runtime_test": "no-live"},
        )


class UnusedWorkflowRunner:
    def run_workflow(self, workflow_input):
        raise AssertionError("workflow runner should not be used in this test")


def test_runtime_builds_public_llm_invocation_request() -> None:
    request = build_runtime_llm_invocation_request(
        request_id="runtime-llm-request-1",
        route_facts=_route_facts(),
        governance_precondition=_governance_precondition(),
        prompt_ref="prompt-ref-1",
        prompt_preview_sanitized="sanitized prompt preview",
        metadata={"source": "runtime-test"},
    )

    assert isinstance(request, LlmInvocationRequest)
    assert request.request_id == "runtime-llm-request-1"
    assert request.route_facts.provider == "litellm"
    assert request.governance_precondition.allowed is True
    assert request.metadata["runtime_boundary"] == "runtime.llm_invocation"
    assert request.metadata["source"] == "runtime-test"


def test_runtime_invokes_governed_llm_service_through_contract_no_live() -> None:
    service: GovernedLlmInvocationService = NoLiveGovernedLlmInvocationService()
    request = build_runtime_llm_invocation_request(
        request_id="runtime-llm-request-1",
        route_facts=_route_facts(),
        governance_precondition=_governance_precondition(),
    )

    result = run_governed_llm_invocation(
        context=RuntimeLlmInvocationContext(
            service=service,
            metadata={"source": "runtime-test"},
        ),
        request=request,
    )

    assert result.failure_type == LlmInvocationFailureType.LIVE_DISABLED
    assert result.call_attempted is False
    assert result.call_allowed is True
    assert result.runtime_call_performed is False
    assert result.success is False
    assert len(service.requests) == 1
    assert service.requests[0] is request


def test_runtime_dependencies_can_hold_llm_invocation_service_contract() -> None:
    service: GovernedLlmInvocationService = NoLiveGovernedLlmInvocationService()

    dependencies = RuntimeDependencies(
        workflow_runner=UnusedWorkflowRunner(),
        llm_invocation_service=service,
    )

    assert dependencies.llm_invocation_service is service


def test_runtime_llm_invocation_context_exposes_sanitized_metadata() -> None:
    context = RuntimeLlmInvocationContext(
        service=NoLiveGovernedLlmInvocationService(),
        metadata={"source": "runtime-test"},
    )

    assert context.to_metadata() == {
        "runtime_boundary": "runtime.llm_invocation",
        "service_contract": (
            "behavior_contracts.llm_invocation.GovernedLlmInvocationService"
        ),
        "metadata": {"source": "runtime-test"},
        "does_not_configure_live": True,
    }


def test_runtime_llm_invocation_source_has_no_adapter_or_live_dependencies() -> None:
    source = (RUNTIME_SOURCE_ROOT / "llm_invocation.py").read_text(encoding="utf-8")
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+(?:adk_adapter|litellm|google\.adk|runtime_container)\b",
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
        reason="runtime_precondition_allowed",
        decision="continue",
        governance_decision_ref="governance-decision-1",
    )
