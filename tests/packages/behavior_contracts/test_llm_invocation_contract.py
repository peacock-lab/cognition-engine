from __future__ import annotations

import re
from pathlib import Path

from behavior_contracts.llm_invocation import (
    GovernedLlmInvocationService,
    GovernedLlmInvocationServiceFactory,
    GovernedLlmInvocationServiceResolution,
)
from config_contexts.runtime import (
    RuntimeConfigSelectionContext,
    RuntimeLiveLlmInvocationOptionsContext,
)
from schemas.llm_invocation import (
    LlmGovernancePrecondition,
    LlmInvocationFailureType,
    LlmInvocationRequest,
    LlmInvocationResult,
)
from schemas.model_routing import ModelRouteFacts


REPO_ROOT = Path(__file__).resolve().parents[3]
BEHAVIOR_CONTRACTS_ROOT = (
    REPO_ROOT / "packages" / "behavior_contracts" / "src" / "behavior_contracts"
)


class BlockingInvocationService:
    def invoke(self, request: LlmInvocationRequest) -> LlmInvocationResult:
        return LlmInvocationResult(
            request_id=request.request_id,
            route_facts=request.route_facts,
            governance_precondition=request.governance_precondition,
            call_attempted=False,
            call_allowed=False,
            runtime_call_performed=False,
            success=False,
            failure_type=LlmInvocationFailureType.GOVERNANCE_BLOCKED,
            error_message_sanitized="blocked before model call",
        )


class StaticInvocationServiceFactory:
    def __init__(self, service: GovernedLlmInvocationService) -> None:
        self.service = service

    def resolve(
        self,
        *,
        config_context=None,
        config_selection: RuntimeConfigSelectionContext,
        live_llm_options: RuntimeLiveLlmInvocationOptionsContext,
    ) -> GovernedLlmInvocationServiceResolution:
        return GovernedLlmInvocationServiceResolution(
            service=self.service,
            metadata={
                "environment": config_selection.environment,
                "timeout_seconds": live_llm_options.timeout_seconds,
            },
        )


def test_governed_llm_invocation_protocol_accepts_structural_service() -> None:
    service: GovernedLlmInvocationService = BlockingInvocationService()
    result = service.invoke(
        LlmInvocationRequest(
            request_id="llm-request-1",
            route_facts=_route_facts(),
            governance_precondition=LlmGovernancePrecondition(
                allowed=False,
                reason="governance_blocked",
                decision="block",
            ),
        )
    )

    assert result.failure_type == LlmInvocationFailureType.GOVERNANCE_BLOCKED
    assert result.runtime_call_performed is False


def test_governed_llm_invocation_factory_accepts_structural_factory() -> None:
    service = BlockingInvocationService()
    factory: GovernedLlmInvocationServiceFactory = StaticInvocationServiceFactory(
        service
    )

    resolution = factory.resolve(
        config_selection=RuntimeConfigSelectionContext(environment="local"),
        live_llm_options=RuntimeLiveLlmInvocationOptionsContext(
            timeout_seconds=11
        ),
    )

    assert resolution.service is service
    assert resolution.blocking_reasons == ()
    assert resolution.warnings == ()
    assert resolution.metadata == {
        "environment": "local",
        "timeout_seconds": 11,
    }


def test_governed_llm_invocation_resolution_can_block_without_service() -> None:
    resolution = GovernedLlmInvocationServiceResolution(
        blocking_reasons=("twf_live_llm_provider_not_injected",),
        warnings=("twf_live_llm_provider_required",),
    )

    assert resolution.service is None
    assert resolution.blocking_reasons == (
        "twf_live_llm_provider_not_injected",
    )
    assert resolution.warnings == ("twf_live_llm_provider_required",)


def test_llm_invocation_behavior_contract_does_not_call_model_libraries() -> None:
    forbidden_terms = re.compile(
        r"^\s*(?:from|import)\s+(?:adk_adapter|google\.adk|litellm)\b|"
        r"\b(?:completion|acompletion|run_async)\s*\(",
        re.MULTILINE,
    )

    source = (BEHAVIOR_CONTRACTS_ROOT / "llm_invocation.py").read_text(
        encoding="utf-8"
    )
    assert forbidden_terms.search(source) is None


def _route_facts() -> ModelRouteFacts:
    return ModelRouteFacts(
        model_name="ollama/gemma4-pro:latest",
        provider="litellm",
        metadata={
            "backend_provider": "ollama",
            "route_target": "ollama/gemma4-pro:latest",
            "route_kind": "adk_litellm",
        },
    )
