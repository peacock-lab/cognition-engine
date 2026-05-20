"""Behavior contract for controlled execution runtime services."""

from __future__ import annotations

from typing import Protocol

from config_contexts.runtime import (
    RuntimeConfigSelectionContext,
    RuntimeLiveLlmInvocationOptionsContext,
)
from schemas.controlled_execution import (
    ControlledExecutionRequestSchema,
    ControlledExecutionRuntimeSummarySchema,
)


class ControlledExecutionRuntimeService(Protocol):
    """Protocol for a governed controlled execution runtime service."""

    def __call__(
        self,
        request: ControlledExecutionRequestSchema,
        *,
        config_selection: RuntimeConfigSelectionContext,
        live_llm_options: RuntimeLiveLlmInvocationOptionsContext | None = None,
    ) -> ControlledExecutionRuntimeSummarySchema:
        """Run controlled execution and return a sanitized runtime summary."""


__all__ = ["ControlledExecutionRuntimeService"]
