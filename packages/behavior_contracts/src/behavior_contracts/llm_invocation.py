"""Behavior contract for governed LLM invocation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from config_contexts.runtime import (
    RuntimeConfigContextBundle,
    RuntimeConfigSelectionContext,
    RuntimeLiveLlmInvocationOptionsContext,
)
from schemas.llm_invocation import LlmInvocationRequest, LlmInvocationResult


class GovernedLlmInvocationService(Protocol):
    """Protocol for a governed LLM invocation capability.

    Implementations may use ADK LiteLlm, LiteLLM provider routes, or an ADK
    WorkflowRunner chain. The protocol itself does not perform model calls.
    """

    def invoke(self, request: LlmInvocationRequest) -> LlmInvocationResult:
        """Run a governed invocation and return sanitized result facts."""


@dataclass(frozen=True)
class GovernedLlmInvocationServiceResolution:
    """Resolution result for a governed LLM invocation service factory."""

    service: GovernedLlmInvocationService | None = None
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


class GovernedLlmInvocationServiceFactory(Protocol):
    """Protocol for resolving a governed LLM invocation service."""

    def resolve(
        self,
        *,
        config_context: RuntimeConfigContextBundle | None = None,
        config_selection: RuntimeConfigSelectionContext,
        live_llm_options: RuntimeLiveLlmInvocationOptionsContext,
    ) -> GovernedLlmInvocationServiceResolution:
        """Resolve a governed LLM invocation service or blocking facts."""
