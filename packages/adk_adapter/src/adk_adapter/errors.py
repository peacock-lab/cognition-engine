"""Internal errors and error conversion helpers for adk_adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from schemas.runtime import InvocationRef, RuntimeErrorRecord, WorkflowRef


class AdkAdapterError(RuntimeError):
    """Base error raised by adk_adapter internals."""


def error_record_from_exception(
    exc: BaseException,
    *,
    invocation_ref: InvocationRef | None = None,
    workflow_ref: WorkflowRef | None = None,
    metadata: dict[str, Any] | None = None,
) -> RuntimeErrorRecord:
    """Convert an exception into a standard runtime error record."""

    return RuntimeErrorRecord(
        error_id=f"adk-error-{uuid4().hex}",
        error_type=type(exc).__name__,
        message=str(exc),
        recoverable=False,
        invocation_ref=invocation_ref,
        workflow_ref=workflow_ref,
        metadata=metadata or {},
    )


@dataclass(frozen=True)
class AdkErrorFacts:
    """Error facts produced by ADK adapter boundaries."""

    error_records: list[RuntimeErrorRecord]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_observability_input(self) -> dict[str, Any]:
        """Return an observability-hub friendly error fact payload."""

        return {
            "errors": self.error_records,
            "error_count": len(self.error_records),
            "source": "adk_adapter.errors",
            **self.metadata,
        }


class AdkErrorFactsBuilder:
    """Build RuntimeErrorRecord facts for observability_hub intake."""

    def build_from_exception(
        self,
        exc: BaseException,
        *,
        invocation_ref: InvocationRef | None = None,
        workflow_ref: WorkflowRef | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AdkErrorFacts:
        """Convert one adapter exception into error facts."""

        error_record = error_record_from_exception(
            exc,
            invocation_ref=invocation_ref,
            workflow_ref=workflow_ref,
            metadata=metadata,
        )
        return AdkErrorFacts(
            error_records=[error_record],
            metadata={
                "candidate_target": "observability_hub.EvidenceBundle.errors",
                "complete_error_service": False,
            },
        )
