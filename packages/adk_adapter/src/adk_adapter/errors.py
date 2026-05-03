"""Internal errors and error conversion helpers for adk_adapter."""

from __future__ import annotations

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
