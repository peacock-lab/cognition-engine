"""Runtime organization for governed LLM invocation contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from behavior_contracts.llm_invocation import GovernedLlmInvocationService
from schemas.llm_invocation import (
    LlmGovernancePrecondition,
    LlmInvocationRequest,
    LlmInvocationResult,
)
from schemas.model_routing import ModelRouteFacts


@dataclass(frozen=True)
class RuntimeLlmInvocationContext:
    """Runtime-local holder for an injected governed LLM invocation service."""

    service: GovernedLlmInvocationService
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_metadata(self) -> dict[str, Any]:
        """Return sanitized runtime organization metadata."""

        return {
            "runtime_boundary": "runtime.llm_invocation",
            "service_contract": (
                "behavior_contracts.llm_invocation.GovernedLlmInvocationService"
            ),
            "metadata": dict(self.metadata),
            "does_not_configure_live": True,
        }


def build_runtime_llm_invocation_request(
    *,
    request_id: str,
    route_facts: ModelRouteFacts,
    governance_precondition: LlmGovernancePrecondition,
    prompt_ref: str | None = None,
    prompt_preview_sanitized: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> LlmInvocationRequest:
    """Build public request facts for a runtime-organized invocation."""

    return LlmInvocationRequest(
        request_id=request_id,
        route_facts=route_facts,
        governance_precondition=governance_precondition,
        prompt_ref=prompt_ref,
        prompt_preview_sanitized=prompt_preview_sanitized,
        metadata={
            "runtime_boundary": "runtime.llm_invocation",
            **(metadata or {}),
        },
    )


def run_governed_llm_invocation(
    *,
    context: RuntimeLlmInvocationContext,
    request: LlmInvocationRequest,
) -> LlmInvocationResult:
    """Invoke the injected governed LLM service through its public contract."""

    return context.service.invoke(request)
