"""Runtime fact bus candidate models for observability-hub."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import Field

from observability_hub.evidence_summary_answer import (
    EvidenceSummaryAnswerPolicyObservationCandidate,
)
from observability_hub.llm_invocation import LlmCallObservationCandidate
from observability_hub.models import ObservabilityBaseModel


RUNTIME_FACT_PHASES = (
    "request_received",
    "config_selected",
    "approval_recorded",
    "capability_snapshot_recorded",
    "preflight_completed",
    "governance_pre_run_decided",
    "runtime_started",
    "runtime_event_recorded",
    "runtime_completed",
    "evaluation_completed",
    "governance_post_run_decided",
    "answer_trace_finalized",
    "artifact_summary_recorded",
    "product_response_projected",
)

RUNTIME_FACT_STATUSES = (
    "success",
    "blocked",
    "failed",
    "skipped",
    "warning",
    "unavailable",
)

_FORBIDDEN_SAFE_PAYLOAD_KEYS = {
    "api_key",
    "completion",
    "config_context",
    "config_context_value",
    "cookie",
    "credential",
    "full_config_context",
    "messages",
    "prompt",
    "provider_raw_response",
    "raw_adk_object",
    "raw_external_body",
    "raw_html",
    "raw_payload",
    "raw_prompt",
    "raw_provider_response",
    "raw_response",
    "raw_tool_input",
    "raw_tool_output",
    "response",
    "response_headers",
    "secret",
    "system_prompt",
    "token",
    "traceback",
    "unredacted_traceback",
}


class RawBoundarySummary(ObservabilityBaseModel):
    """Summary of raw-boundary handling for a runtime fact."""

    raw_absent: bool = True
    raw_blocked: bool = False
    raw_unavailable_reason: str | None = None
    blocked_keys: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeFactEnvelope(ObservabilityBaseModel):
    """Internal runtime fact envelope candidate.

    This is not a public schema. It is a local observability candidate for
    correlating sanitized facts without storing raw payloads.
    """

    fact_id: str
    correlation_id: str
    request_id: str | None = None
    trace_ref: str | None = None
    source_component: str
    phase: str
    subject_ref: str | None = None
    status: str
    safe_payload: dict[str, Any] = Field(default_factory=dict)
    refs: list[str] = Field(default_factory=list)
    raw_boundary: RawBoundarySummary
    created_at: str


def build_runtime_fact_envelope(
    *,
    source_component: str,
    phase: str,
    status: str,
    safe_payload: Mapping[str, Any] | None = None,
    refs: Sequence[str] | None = None,
    request_id: str | None = None,
    trace_ref: str | None = None,
    subject_ref: str | None = None,
    correlation_id: str | None = None,
    fact_id: str | None = None,
    raw_boundary: RawBoundarySummary | Mapping[str, Any] | None = None,
) -> RuntimeFactEnvelope:
    """Build a sanitized runtime fact envelope."""

    _validate_choice("phase", phase, RUNTIME_FACT_PHASES)
    _validate_choice("status", status, RUNTIME_FACT_STATUSES)
    payload = _plain_mapping(safe_payload)
    blocked_keys = _blocked_payload_keys(payload)
    if blocked_keys:
        raise ValueError(
            "safe_payload contains forbidden raw-boundary keys: "
            + ", ".join(blocked_keys)
        )
    raw_summary = _raw_boundary_summary(raw_boundary, blocked_keys=blocked_keys)
    safe_refs = _safe_refs(refs)
    generated_fact_id = fact_id or f"runtime-fact://{uuid4()}"
    return RuntimeFactEnvelope(
        fact_id=generated_fact_id,
        correlation_id=(
            correlation_id
            or trace_ref
            or request_id
            or subject_ref
            or generated_fact_id
        ),
        request_id=_optional_str(request_id),
        trace_ref=_optional_str(trace_ref),
        source_component=_required_str(source_component, "source_component"),
        phase=phase,
        subject_ref=_optional_str(subject_ref),
        status=status,
        safe_payload=payload,
        refs=safe_refs,
        raw_boundary=raw_summary,
        created_at=datetime.now(UTC).isoformat(),
    )


def build_runtime_fact_from_llm_call_observation(
    observation: LlmCallObservationCandidate | Mapping[str, Any],
) -> RuntimeFactEnvelope:
    """Map an LLM call observation candidate into a runtime fact envelope."""

    candidate = (
        observation
        if isinstance(observation, LlmCallObservationCandidate)
        else LlmCallObservationCandidate.model_validate(observation)
    )
    safe_payload = {
        "observation_id": candidate.observation_id,
        "model_name": candidate.model_name,
        "provider": candidate.provider,
        "backend_provider": candidate.backend_provider,
        "route_kind": candidate.route_kind,
        "route_target": candidate.route_target,
        "call_attempted": candidate.call_attempted,
        "call_allowed": candidate.call_allowed,
        "runtime_call_performed": candidate.runtime_call_performed,
        "success": candidate.success,
        "response_non_empty": candidate.response_non_empty,
        "sanitized_response_length": candidate.sanitized_response_length,
        "latency_ms": candidate.latency_ms,
        "failure_type": candidate.failure_type,
        "governance_decision_ref": candidate.governance_decision_ref,
    }
    refs = _safe_refs(
        [
            candidate.governance_decision_ref,
            candidate.route_target,
        ]
    )
    return build_runtime_fact_envelope(
        source_component="observability_hub.llm_invocation",
        phase="runtime_completed",
        status=_status_from_llm_observation(candidate),
        request_id=candidate.request_id,
        subject_ref=candidate.observation_id,
        safe_payload=safe_payload,
        refs=refs,
        raw_boundary=RawBoundarySummary(
            raw_absent=True,
            metadata={
                "does_not_store_prompt": True,
                "does_not_store_completion": True,
                "does_not_store_raw_provider_response": True,
                "sanitized_response_preview_omitted": True,
            },
        ),
    )


def build_runtime_fact_from_evidence_summary_answer_observation(
    observation: EvidenceSummaryAnswerPolicyObservationCandidate | Mapping[str, Any],
) -> RuntimeFactEnvelope:
    """Map evidence-summary-answer observation into a runtime fact envelope."""

    candidate = (
        observation
        if isinstance(observation, EvidenceSummaryAnswerPolicyObservationCandidate)
        else EvidenceSummaryAnswerPolicyObservationCandidate.model_validate(
            observation
        )
    )
    safe_payload = {
        "observation_id": candidate.observation_id,
        "payload_type": candidate.payload_type,
        "payload_version": candidate.payload_version,
        "schema_validation_passed": candidate.schema_validation_passed,
        "schema_validation_error_count": candidate.schema_validation_error_count,
        "guard_validation_passed": candidate.guard_validation_passed,
        "guard_violation_count": candidate.guard_violation_count,
        "guard_names": candidate.guard_names,
        "policy_profile": candidate.policy_profile,
        "policy_ref": candidate.policy_ref,
        "config_source_ref": candidate.config_source_ref,
        "status": candidate.status,
        "answerability": candidate.answerability,
        "evidence_ref_count": candidate.evidence_ref_count,
        "digest_ref_count": candidate.digest_ref_count,
        "summary_fact_count": candidate.summary_fact_count,
        "summary_fact_total_chars": candidate.summary_fact_total_chars,
        "raw_boundary_violation_count": candidate.raw_boundary_violation_count,
        "sanitized_excerpt_preview_present": (
            candidate.sanitized_excerpt_preview_present
        ),
        "answer_present": candidate.answer_present,
        "answer_preview_present": candidate.answer_preview_present,
        "user_question_present": candidate.user_question_present,
        "blocking_reasons": candidate.blocking_reasons,
        "citation_failures": candidate.citation_failures,
    }
    refs = _safe_refs(
        [
            *candidate.evidence_refs,
            *candidate.digest_refs,
            candidate.policy_ref,
            candidate.config_source_ref,
        ]
    )
    return build_runtime_fact_envelope(
        source_component="observability_hub.evidence_summary_answer",
        phase=_phase_from_evidence_summary_answer(candidate),
        status=_status_from_evidence_summary_answer(candidate),
        request_id=candidate.request_id,
        subject_ref=candidate.observation_id,
        safe_payload=safe_payload,
        refs=refs,
        raw_boundary=RawBoundarySummary(
            raw_absent=candidate.raw_boundary_violation_count == 0,
            raw_blocked=candidate.raw_boundary_violation_count > 0,
            blocked_keys=(
                ["evidence_summary_answer_raw_boundary"]
                if candidate.raw_boundary_violation_count > 0
                else []
            ),
            metadata={
                "does_not_store_raw_payload": True,
                "does_not_store_summary_facts": True,
                "does_not_store_answer": True,
                "does_not_store_user_question": True,
                "does_not_store_config_context_value": True,
            },
        ),
    )


def _status_from_llm_observation(
    candidate: LlmCallObservationCandidate,
) -> str:
    if candidate.success:
        return "success"
    if candidate.failure_type == "governance_blocked" or not candidate.call_allowed:
        return "blocked"
    if candidate.call_attempted or candidate.failure_type:
        return "failed"
    return "skipped"


def _phase_from_evidence_summary_answer(
    candidate: EvidenceSummaryAnswerPolicyObservationCandidate,
) -> str:
    if candidate.payload_type == "evidence_summary_answer_result":
        return "answer_trace_finalized"
    return "preflight_completed"


def _status_from_evidence_summary_answer(
    candidate: EvidenceSummaryAnswerPolicyObservationCandidate,
) -> str:
    if not candidate.schema_validation_passed:
        return "failed"
    if candidate.guard_validation_passed is False:
        return "failed"
    if candidate.blocking_reasons:
        return "blocked"
    if candidate.status in {"success", "blocked", "failed", "skipped", "warning"}:
        return candidate.status
    return "success"


def _raw_boundary_summary(
    value: RawBoundarySummary | Mapping[str, Any] | None,
    *,
    blocked_keys: list[str],
) -> RawBoundarySummary:
    if isinstance(value, RawBoundarySummary):
        return value
    if value is not None:
        return RawBoundarySummary.model_validate(value)
    return RawBoundarySummary(
        raw_absent=not blocked_keys,
        raw_blocked=bool(blocked_keys),
        blocked_keys=blocked_keys,
    )


def _validate_choice(name: str, value: str, allowed: tuple[str, ...]) -> None:
    if value not in allowed:
        raise ValueError(f"{name} must be one of: {', '.join(allowed)}")


def _plain_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("safe_payload must be a mapping.")
    return {
        str(key): item
        for key, item in value.items()
        if isinstance(key, str)
    }


def _blocked_payload_keys(value: Any, *, path: str = "") -> list[str]:
    blocked: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            key_path = f"{path}.{key_text}" if path else key_text
            if key_text.lower() in _FORBIDDEN_SAFE_PAYLOAD_KEYS:
                blocked.append(key_path)
            blocked.extend(_blocked_payload_keys(item, path=key_path))
    elif is_dataclass(value) and not isinstance(value, type):
        blocked.extend(_blocked_payload_keys(asdict(value), path=path))
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for index, item in enumerate(value):
            item_path = f"{path}[{index}]" if path else f"[{index}]"
            blocked.extend(_blocked_payload_keys(item, path=item_path))
    return sorted(dict.fromkeys(blocked))


def _safe_refs(values: Sequence[str | None] | None) -> list[str]:
    if values is None:
        return []
    refs = [
        value.strip()
        for value in values
        if isinstance(value, str) and value.strip()
    ]
    return list(dict.fromkeys(refs))


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _required_str(value: Any, field_name: str) -> str:
    if isinstance(value, str) and value:
        return value
    raise ValueError(f"{field_name} must be a non-empty string.")
