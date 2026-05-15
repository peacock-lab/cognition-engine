"""Behavior contract for governed LLM invocation."""

from __future__ import annotations

from typing import Protocol

from schemas.llm_invocation import LlmInvocationRequest, LlmInvocationResult


class GovernedLlmInvocationService(Protocol):
    """Protocol for a governed LLM invocation capability.

    Implementations may use ADK LiteLlm, LiteLLM provider routes, or an ADK
    WorkflowRunner chain. The protocol itself does not perform model calls.
    """

    def invoke(self, request: LlmInvocationRequest) -> LlmInvocationResult:
        """Run a governed invocation and return sanitized result facts."""
