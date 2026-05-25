"""Summary projections for runtime fact bus candidates."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import Field

from observability_hub.models import ObservabilityBaseModel
from observability_hub.runtime_fact_bus import (
    RawBoundarySummary,
    RuntimeFactEnvelope,
)


class RuntimeFactSummaryProjection(ObservabilityBaseModel):
    """Internal user-readable summary projection for a runtime fact."""

    projection_ref: str
    correlation_id: str
    request_id: str | None = None
    source_component: str
    phase: str
    status: str
    summary: str
    reason: str
    user_explanation: str
    recovery_hints: list[str] = Field(default_factory=list)
    refs: list[str] = Field(default_factory=list)
    raw_boundary_summary: dict[str, Any] = Field(default_factory=dict)
    runtime_backed: bool = False
    public_schema: bool = False
    created_at: str


def build_runtime_fact_summary_projection(
    fact: RuntimeFactEnvelope | Mapping[str, Any],
    *,
    projection_ref: str | None = None,
) -> RuntimeFactSummaryProjection:
    """Project an internal runtime fact into a safe readable summary."""

    runtime_fact = (
        fact if isinstance(fact, RuntimeFactEnvelope) else RuntimeFactEnvelope.model_validate(fact)
    )
    reason = _reason(runtime_fact)
    return RuntimeFactSummaryProjection(
        projection_ref=projection_ref or f"runtime-fact-summary://{uuid4()}",
        correlation_id=runtime_fact.correlation_id,
        request_id=runtime_fact.request_id,
        source_component=runtime_fact.source_component,
        phase=runtime_fact.phase,
        status=runtime_fact.status,
        summary=_summary(reason),
        reason=reason,
        user_explanation=_user_explanation(reason),
        recovery_hints=_recovery_hints(reason),
        refs=_safe_refs(runtime_fact.refs),
        raw_boundary_summary=_raw_boundary_summary(runtime_fact.raw_boundary),
        runtime_backed=False,
        public_schema=False,
        created_at=datetime.now(UTC).isoformat(),
    )


def runtime_fact_summary_projection_dict(
    projection: RuntimeFactSummaryProjection | Mapping[str, Any],
) -> dict[str, Any]:
    """Return a JSON-ready dict for a runtime fact summary projection."""

    model = (
        projection
        if isinstance(projection, RuntimeFactSummaryProjection)
        else RuntimeFactSummaryProjection.model_validate(projection)
    )
    return model.model_dump(mode="json")


def _reason(fact: RuntimeFactEnvelope) -> str:
    payload = fact.safe_payload
    if (
        fact.raw_boundary.raw_blocked
        or _int_value(payload.get("raw_boundary_violation_count")) > 0
    ):
        return "raw_boundary_blocked"

    if fact.phase == "runtime_completed":
        return _runtime_completed_reason(fact)
    if fact.phase == "preflight_completed":
        return _preflight_reason(fact)
    if fact.phase == "answer_trace_finalized":
        return _answer_trace_reason(fact)
    if fact.status == "blocked":
        return "runtime_fact_blocked"
    if fact.status == "failed":
        return "runtime_fact_failed"
    if fact.status == "success":
        return "runtime_fact_success"
    return "runtime_fact_status_summary"


def _runtime_completed_reason(fact: RuntimeFactEnvelope) -> str:
    payload = fact.safe_payload
    failure_type = _text(payload.get("failure_type"))
    if fact.status == "success":
        return "runtime_completed_success"
    if (
        fact.status == "blocked"
        or failure_type == "governance_blocked"
        or payload.get("call_allowed") is False
    ):
        return "governance_blocked"
    if failure_type == "output_schema_validation_failure":
        return "output_schema_validation_failed"
    if fact.status == "failed":
        return "runtime_failed"
    if fact.status == "skipped":
        return "runtime_skipped"
    return "runtime_completed_status_summary"


def _preflight_reason(fact: RuntimeFactEnvelope) -> str:
    if fact.status in {"blocked", "failed", "skipped"}:
        return "answerability_preflight_blocked"
    if fact.status == "success":
        return "preflight_passed"
    return "preflight_status_summary"


def _answer_trace_reason(fact: RuntimeFactEnvelope) -> str:
    payload = fact.safe_payload
    if payload.get("schema_validation_passed") is False:
        return "output_schema_validation_failed"
    if _int_value(payload.get("schema_validation_error_count")) > 0:
        return "output_schema_validation_failed"
    if (
        payload.get("guard_validation_passed") is False
        or _contains_text(
            _string_list(payload.get("blocking_reasons")),
            "llm_answer_quality_contract_violation",
        )
    ):
        return "answer_quality_contract_failed"
    if fact.status == "success":
        return "answer_trace_success"
    if fact.status == "blocked":
        return "answer_trace_blocked"
    if fact.status == "failed":
        return "answer_trace_failed"
    return "answer_trace_status_summary"


def _summary(reason: str) -> str:
    return {
        "runtime_completed_success": "Runtime completed successfully.",
        "governance_blocked": "Request was blocked by governance before runtime execution.",
        "output_schema_validation_failed": "Model output failed structured validation.",
        "runtime_failed": "Runtime execution failed after the request was allowed.",
        "runtime_skipped": "Runtime execution was skipped.",
        "answerability_preflight_blocked": "Request was limited before model invocation by answerability preflight.",
        "preflight_passed": "Answerability preflight passed.",
        "answer_quality_contract_failed": "Answer failed the quality contract.",
        "answer_trace_success": "Answer trace completed successfully.",
        "answer_trace_blocked": "Answer trace was blocked.",
        "answer_trace_failed": "Answer trace failed.",
        "raw_boundary_blocked": "Raw-boundary content was blocked from the runtime fact.",
        "runtime_fact_blocked": "Runtime fact reports a blocked state.",
        "runtime_fact_failed": "Runtime fact reports a failed state.",
        "runtime_fact_success": "Runtime fact reports a successful state.",
    }.get(reason, "Runtime fact has a summarized status.")


def _user_explanation(reason: str) -> str:
    return {
        "runtime_completed_success": (
            "The controlled runtime path completed and produced sanitized facts "
            "that can be reviewed through the attached refs."
        ),
        "governance_blocked": (
            "The request did not proceed to model or provider execution because "
            "a governance precondition was not satisfied."
        ),
        "output_schema_validation_failed": (
            "The model response did not match the expected structured output, so "
            "it was not accepted as a successful answer."
        ),
        "runtime_failed": (
            "The request reached runtime execution, but the runtime reported a "
            "failure before a successful answer could be formed."
        ),
        "runtime_skipped": (
            "The runtime path was intentionally skipped, so no provider execution "
            "should be inferred from this fact."
        ),
        "answerability_preflight_blocked": (
            "The request was stopped before model invocation because the available "
            "evidence or requested output scope did not support the answer safely."
        ),
        "preflight_passed": (
            "The request passed the answerability preflight and may continue to "
            "the controlled runtime path."
        ),
        "answer_quality_contract_failed": (
            "A candidate answer was formed but failed the answer quality contract, "
            "so it should not be treated as a successful answer."
        ),
        "answer_trace_success": (
            "The answer trace reached a successful finalized state with reviewable refs."
        ),
        "answer_trace_blocked": (
            "The answer trace reached a blocked state before a successful answer "
            "could be finalized."
        ),
        "answer_trace_failed": (
            "The answer trace reached a failed state and should be reviewed through "
            "its refs and status."
        ),
        "raw_boundary_blocked": (
            "A raw-boundary field was detected and blocked; only safe summary facts "
            "and refs should be used."
        ),
    }.get(
        reason,
        "This runtime fact is summarized for review without exposing raw payloads.",
    )


def _recovery_hints(reason: str) -> list[str]:
    return {
        "runtime_completed_success": [
            "Review refs if you need to audit the related decision or evidence.",
        ],
        "governance_blocked": [
            "Review governance refs and required approvals.",
            "Retry only after the missing gate is satisfied.",
        ],
        "output_schema_validation_failed": [
            "Retry with a shorter or clearer request.",
            "Switch to a more stable provider profile if the failure repeats.",
        ],
        "runtime_failed": [
            "Check runtime/provider health and sanitized failure facts.",
            "Retry after confirming the runtime path is available.",
        ],
        "runtime_skipped": [
            "Confirm whether runtime execution was intentionally disabled.",
        ],
        "answerability_preflight_blocked": [
            "Ask a narrower question supported by the evidence.",
            "Provide richer evidence before requesting long-form output.",
        ],
        "preflight_passed": [
            "Continue through the controlled runtime path if authorized.",
        ],
        "answer_quality_contract_failed": [
            "Ask a clearer evidence-grounded question.",
            "Retry or switch provider profile if this repeats.",
        ],
        "answer_trace_success": [
            "Use refs to review the answer trace and evidence.",
        ],
        "answer_trace_blocked": [
            "Review blocking reasons and related refs before retrying.",
        ],
        "answer_trace_failed": [
            "Review failure refs and retry with a narrower request.",
        ],
        "raw_boundary_blocked": [
            "Remove raw payload fields.",
            "Pass only safe counts, status, summaries, and refs.",
        ],
    }.get(reason, ["Review refs and status before retrying."])


def _raw_boundary_summary(raw_boundary: RawBoundarySummary) -> dict[str, Any]:
    blocked_count = len(raw_boundary.blocked_keys)
    if raw_boundary.raw_blocked:
        message = "Raw content was blocked and is not exposed."
    elif raw_boundary.raw_unavailable_reason:
        message = "Raw content is unavailable for this projection."
    elif raw_boundary.raw_absent:
        message = "No raw content is present in this runtime fact."
    else:
        message = "Raw content is not exposed in this projection."
    return {
        "raw_absent": raw_boundary.raw_absent,
        "raw_blocked": raw_boundary.raw_blocked,
        "raw_unavailable_reason": _safe_optional_text(
            raw_boundary.raw_unavailable_reason
        ),
        "blocked_key_count": blocked_count,
        "message": message,
    }


def _safe_optional_text(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    lowered = text.lower()
    forbidden_markers = (
        "api_key",
        "completion",
        "config_context",
        "credential",
        "messages",
        "prompt",
        "raw_provider_response",
        "raw_response",
        "secret",
        "token",
        "traceback",
    )
    if any(marker in lowered for marker in forbidden_markers):
        return "unavailable"
    return text[:160]


def _int_value(value: Any) -> int:
    return value if isinstance(value, int) and value >= 0 else 0


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        return []
    return [item for item in value if isinstance(item, str)]


def _contains_text(values: Sequence[str], target: str) -> bool:
    return any(value == target for value in values)


def _safe_refs(values: Sequence[str]) -> list[str]:
    refs = [
        value.strip()
        for value in values
        if isinstance(value, str) and value.strip()
    ]
    return list(dict.fromkeys(refs))
