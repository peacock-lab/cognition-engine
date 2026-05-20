from __future__ import annotations

from behavior_contracts.llm_invocation import (
    GovernedLlmInvocationService,
    GovernedLlmInvocationServiceFactory,
    GovernedLlmInvocationServiceResolution,
)
from schemas.llm_invocation import (
    LlmGovernancePrecondition,
    LlmInvocationFailureType,
    LlmInvocationRequest,
    LlmInvocationResult,
)

from contract_core import llm_invocation


def test_llm_invocation_facade_reexports_contracts() -> None:
    assert llm_invocation.GovernedLlmInvocationService is GovernedLlmInvocationService
    assert (
        llm_invocation.GovernedLlmInvocationServiceFactory
        is GovernedLlmInvocationServiceFactory
    )
    assert (
        llm_invocation.GovernedLlmInvocationServiceResolution
        is GovernedLlmInvocationServiceResolution
    )
    assert llm_invocation.LlmGovernancePrecondition is LlmGovernancePrecondition
    assert llm_invocation.LlmInvocationFailureType is LlmInvocationFailureType
    assert llm_invocation.LlmInvocationRequest is LlmInvocationRequest
    assert llm_invocation.LlmInvocationResult is LlmInvocationResult


def test_llm_invocation_facade_exports_are_explicit() -> None:
    assert llm_invocation.__all__ == [
        "GovernedLlmInvocationService",
        "GovernedLlmInvocationServiceFactory",
        "GovernedLlmInvocationServiceResolution",
        "LlmGovernancePrecondition",
        "LlmInvocationFailureType",
        "LlmInvocationRequest",
        "LlmInvocationResult",
    ]
