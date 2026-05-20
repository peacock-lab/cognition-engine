"""Task workflow facade for governed LLM invocation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from contract_core.llm_invocation import (
    GovernedLlmInvocationService,
    LlmGovernancePrecondition,
    LlmInvocationRequest,
    LlmInvocationResult,
)
from contract_core.model_routing import ModelRouteFacts
from runtime.llm_invocation import (
    RuntimeLlmInvocationContext,
    build_runtime_llm_invocation_request,
    run_governed_llm_invocation,
)


@dataclass(frozen=True)
class TwfLlmInvocationFacade:
    """Thin task workflow facade over governed runtime LLM invocation."""

    service: GovernedLlmInvocationService
    metadata: dict[str, Any] = field(default_factory=dict)

    def run(self, request: LlmInvocationRequest) -> LlmInvocationResult:
        """Run a governed invocation for a task workflow."""

        return run_twf_llm_invocation(
            service=self.service,
            request=request,
            metadata=self.metadata,
        )

    def to_metadata(self) -> dict[str, Any]:
        """Return sanitized facade metadata."""

        return {
            "facade": "cognition_task_workflows._llm.invocation",
            "runtime_helper": "runtime.llm_invocation.run_governed_llm_invocation",
            "service_contract": (
                "contract_core.llm_invocation.GovernedLlmInvocationService"
            ),
            "metadata": dict(self.metadata),
            "does_not_configure_live": True,
        }


def build_twf_llm_invocation_request(
    *,
    request_id: str,
    route_facts: ModelRouteFacts,
    governance_precondition: LlmGovernancePrecondition,
    prompt_ref: str | None = None,
    prompt_preview_sanitized: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> LlmInvocationRequest:
    """Build public request facts for a task workflow LLM call."""

    return build_runtime_llm_invocation_request(
        request_id=request_id,
        route_facts=route_facts,
        governance_precondition=governance_precondition,
        prompt_ref=prompt_ref,
        prompt_preview_sanitized=prompt_preview_sanitized,
        metadata={
            "twf_llm_invocation_facade": "cognition_task_workflows._llm.invocation",
            **(metadata or {}),
        },
    )


def run_twf_llm_invocation(
    *,
    service: GovernedLlmInvocationService,
    request: LlmInvocationRequest,
    metadata: dict[str, Any] | None = None,
) -> LlmInvocationResult:
    """Run governed LLM invocation through runtime without owning execution."""

    return run_governed_llm_invocation(
        context=RuntimeLlmInvocationContext(
            service=service,
            metadata={
                "twf_llm_invocation_facade": "cognition_task_workflows._llm.invocation",
                **(metadata or {}),
            },
        ),
        request=request,
    )
