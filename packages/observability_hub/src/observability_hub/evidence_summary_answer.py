"""Evidence summary answer observation candidates for observability-hub."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import Field
from schemas.evidence_summary_answer import (
    EVIDENCE_SUMMARY_ANSWER_CONTEXT_PAYLOAD_TYPE,
    EVIDENCE_SUMMARY_ANSWER_RESULT_PAYLOAD_TYPE,
    EXTERNAL_READONLY_EVIDENCE_REF_PREFIX,
    FORBIDDEN_EVIDENCE_SUMMARY_ANSWER_KEYS,
    GOVERNED_EVIDENCE_DIGEST_PAYLOAD_TYPE,
    GOVERNED_EVIDENCE_DIGEST_REF_PREFIX,
    validate_evidence_summary_answer_context,
    validate_evidence_summary_answer_result,
    validate_governed_evidence_digest,
)

from observability_hub.models import ObservabilityBaseModel


class EvidenceSummaryAnswerPolicyObservationCandidate(ObservabilityBaseModel):
    """Internal outcome-only observation candidate for evidence summary answer."""

    observation_id: str
    source: str
    request_id: str | None = None
    payload_type: str | None = None
    payload_version: str | None = None
    schema_validation_passed: bool = False
    schema_validation_error_count: int = 0
    guard_validation_passed: bool | None = None
    guard_violation_count: int = 0
    guard_names: list[str] = Field(default_factory=list)
    policy_profile: str | None = None
    policy_ref: str | None = None
    config_source_ref: str | None = None
    exposure_enabled: bool | None = None
    allow_model_context: bool | None = None
    citation_required: bool | None = None
    insufficient_evidence_required: bool | None = None
    enabled_by_default: bool | None = None
    raw_boundary_allowed: bool | None = None
    sanitized_excerpt_preview_allowed: bool | None = None
    observability_candidate_body_allowed: bool | None = None
    citation_exception_allowed: bool | None = None
    status: str | None = None
    answerability: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    digest_refs: list[str] = Field(default_factory=list)
    evidence_ref_count: int = 0
    digest_ref_count: int = 0
    summary_fact_count: int = 0
    summary_fact_total_chars: int = 0
    raw_boundary_violation_count: int = 0
    sanitized_excerpt_preview_present: bool = False
    answer_present: bool = False
    answer_preview_present: bool = False
    user_question_present: bool = False
    blocking_reasons: list[str] = Field(default_factory=list)
    citation_failures: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str


def build_evidence_summary_answer_policy_observation_candidate(
    payload: Any,
    *,
    guard_outcome: Any | None = None,
    policy_summary: Any | None = None,
    schema_validation_passed: bool | None = None,
    schema_validation_error_count: int | None = None,
) -> EvidenceSummaryAnswerPolicyObservationCandidate:
    """Build an outcome-only observation candidate without storing context text."""

    data = _mapping_or_raise(payload, "evidence-summary-answer payload")
    guard_data = _mapping(guard_outcome)
    policy_data = _mapping(policy_summary)
    computed_schema_passed, computed_schema_error_count = _schema_outcome(data)
    schema_passed = (
        schema_validation_passed
        if schema_validation_passed is not None
        else computed_schema_passed
    )
    schema_errors = (
        _non_negative_int(schema_validation_error_count)
        if schema_validation_error_count is not None
        else computed_schema_error_count
    )
    evidence_refs = _evidence_refs(data)
    digest_refs = _digest_refs(data)
    summary_fact_count, summary_fact_total_chars = _summary_fact_counts(data)

    return EvidenceSummaryAnswerPolicyObservationCandidate(
        observation_id=f"evidence-summary-answer-policy-observation-{uuid4()}",
        source="observability_hub.evidence_summary_answer",
        request_id=_plain_str(data.get("request_id")),
        payload_type=_plain_str(data.get("payload_type")),
        payload_version=_plain_str(data.get("payload_version")),
        schema_validation_passed=schema_passed,
        schema_validation_error_count=schema_errors,
        guard_validation_passed=_guard_passed(guard_data),
        guard_violation_count=_guard_violation_count(guard_data),
        guard_names=_guard_names(guard_data),
        policy_profile=_plain_str(
            policy_data.get("policy_profile", policy_data.get("profile"))
        ),
        policy_ref=_policy_ref(data, policy_data),
        config_source_ref=_config_source_ref(policy_data),
        exposure_enabled=_optional_bool(policy_data.get("exposure_enabled")),
        allow_model_context=_optional_bool(policy_data.get("allow_model_context")),
        citation_required=_optional_bool(policy_data.get("citation_required")),
        insufficient_evidence_required=_optional_bool(
            policy_data.get("insufficient_evidence_required")
        ),
        enabled_by_default=_optional_bool(policy_data.get("enabled_by_default")),
        raw_boundary_allowed=_optional_bool(policy_data.get("allow_raw_boundary")),
        sanitized_excerpt_preview_allowed=_optional_bool(
            policy_data.get("allow_sanitized_excerpt_preview")
        ),
        observability_candidate_body_allowed=_optional_bool(
            policy_data.get("allow_observability_candidate_body")
        ),
        citation_exception_allowed=_optional_bool(
            policy_data.get("allow_citation_exception")
        ),
        status=_plain_str(data.get("status")),
        answerability=_plain_str(data.get("answerability")),
        evidence_refs=evidence_refs,
        digest_refs=digest_refs,
        evidence_ref_count=len(evidence_refs),
        digest_ref_count=len(digest_refs),
        summary_fact_count=summary_fact_count,
        summary_fact_total_chars=summary_fact_total_chars,
        raw_boundary_violation_count=_raw_boundary_violation_count(data),
        sanitized_excerpt_preview_present=_contains_key(
            data,
            "sanitized_excerpt_preview",
        )
        or _raw_boundary_flag_true(data, "sanitized_excerpt_preview_included"),
        answer_present=_has_nonempty_str(data.get("answer")),
        answer_preview_present=_has_nonempty_str(data.get("answer_preview")),
        user_question_present=_has_nonempty_str(data.get("user_question")),
        blocking_reasons=_safe_string_list(data.get("blocking_reasons")),
        citation_failures=_safe_string_list(data.get("citation_failures")),
        metadata={
            "observation_semantics": (
                "evidence_summary_answer_policy_outcome_candidate"
            ),
            "does_not_store_raw_payload": True,
            "does_not_store_provider_raw_response": True,
            "does_not_store_sanitized_excerpt_preview": True,
            "does_not_store_summary_facts": True,
            "does_not_store_answer": True,
            "does_not_store_user_question": True,
            "does_not_store_config_context_value": True,
            "does_not_call_model": True,
            "does_not_fetch_or_search": True,
            "payload_metadata_keys": sorted(_mapping(data.get("metadata"))),
            "guard_outcome_keys": sorted(guard_data),
            "policy_summary_keys": sorted(policy_data),
        },
        created_at=datetime.now(UTC).isoformat(),
    )


def _mapping_or_raise(value: Any, input_name: str) -> dict[str, Any]:
    data = _mapping(value)
    if data:
        return data
    if value is None or value == {}:
        return {}
    raise ValueError(f"{input_name} must be a mapping or dataclass-like object.")


def _mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return {
            str(key): item
            for key, item in value.items()
            if isinstance(key, str)
        }
    if is_dataclass(value) and not isinstance(value, type):
        return _mapping(asdict(value))
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="python")
        if isinstance(dumped, Mapping):
            return _mapping(dumped)
    return {}


def _schema_outcome(payload: dict[str, Any]) -> tuple[bool, int]:
    payload_type = payload.get("payload_type")
    try:
        if payload_type == GOVERNED_EVIDENCE_DIGEST_PAYLOAD_TYPE:
            validate_governed_evidence_digest(payload)
        elif payload_type == EVIDENCE_SUMMARY_ANSWER_CONTEXT_PAYLOAD_TYPE:
            validate_evidence_summary_answer_context(payload)
        elif payload_type == EVIDENCE_SUMMARY_ANSWER_RESULT_PAYLOAD_TYPE:
            validate_evidence_summary_answer_result(payload)
        else:
            return False, 1
    except Exception:
        return False, 1
    return True, 0


def _guard_passed(guard_data: dict[str, Any]) -> bool | None:
    if "passed" not in guard_data:
        violations = _sequence(guard_data.get("violations"))
        return not violations if violations else None
    value = guard_data.get("passed")
    return value if isinstance(value, bool) else None


def _guard_violation_count(guard_data: dict[str, Any]) -> int:
    if "violation_count" in guard_data:
        return _non_negative_int(guard_data.get("violation_count"))
    return len(_sequence(guard_data.get("violations")))


def _guard_names(guard_data: dict[str, Any]) -> list[str]:
    values = _sequence(guard_data.get("guard_names", guard_data.get("guards")))
    names = [_safe_short_str(item) for item in values]
    names = [name for name in names if name]
    if names:
        return sorted(dict.fromkeys(names))
    inferred: list[str] = []
    for violation in _sequence(guard_data.get("violations")):
        text = str(violation)
        if ":" in text:
            inferred.append(text.split(":", maxsplit=1)[0].strip())
    return sorted(dict.fromkeys(item for item in inferred if item))


def _policy_ref(data: dict[str, Any], policy_data: dict[str, Any]) -> str | None:
    return _plain_str(
        policy_data.get(
            "policy_ref",
            data.get(
                "answer_policy_ref",
                data.get(
                    "citation_policy_ref",
                    data.get("digest_generation_policy_ref"),
                ),
            ),
        )
    )


def _config_source_ref(policy_data: dict[str, Any]) -> str | None:
    metadata = _mapping(policy_data.get("metadata"))
    return _plain_str(
        policy_data.get(
            "config_source_ref",
            policy_data.get("source", metadata.get("source")),
        )
    )


def _evidence_refs(data: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    refs.extend(
        _refs_with_prefix(
            _plain_str_list(data.get("evidence_ref")),
            EXTERNAL_READONLY_EVIDENCE_REF_PREFIX,
        )
    )
    refs.extend(
        _refs_from_ref_items(
            data.get("evidence_refs"),
            prefix=EXTERNAL_READONLY_EVIDENCE_REF_PREFIX,
        )
    )
    refs.extend(
        _refs_from_ref_items(
            data.get("evidence_refs_used"),
            prefix=EXTERNAL_READONLY_EVIDENCE_REF_PREFIX,
        )
    )
    refs.extend(
        _refs_from_ref_items(
            data.get("additional_refs"),
            prefix=EXTERNAL_READONLY_EVIDENCE_REF_PREFIX,
        )
    )
    refs.extend(
        _refs_from_ref_items(
            data.get("additional_refs_used"),
            prefix=EXTERNAL_READONLY_EVIDENCE_REF_PREFIX,
        )
    )
    for digest in _sequence(data.get("digests")):
        digest_data = _mapping(digest)
        refs.extend(
            _refs_with_prefix(
                _plain_str_list(digest_data.get("evidence_ref")),
                EXTERNAL_READONLY_EVIDENCE_REF_PREFIX,
            )
        )
    return _dedupe(refs)


def _digest_refs(data: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    refs.extend(
        _refs_with_prefix(
            _plain_str_list(data.get("digest_ref")),
            GOVERNED_EVIDENCE_DIGEST_REF_PREFIX,
        )
    )
    refs.extend(
        _refs_with_prefix(
            _plain_str_list(data.get("digest_refs_used")),
            GOVERNED_EVIDENCE_DIGEST_REF_PREFIX,
        )
    )
    refs.extend(
        _refs_from_ref_items(
            data.get("additional_refs"),
            prefix=GOVERNED_EVIDENCE_DIGEST_REF_PREFIX,
        )
    )
    refs.extend(
        _refs_from_ref_items(
            data.get("additional_refs_used"),
            prefix=GOVERNED_EVIDENCE_DIGEST_REF_PREFIX,
        )
    )
    for digest in _sequence(data.get("digests")):
        digest_data = _mapping(digest)
        refs.extend(
            _refs_with_prefix(
                _plain_str_list(digest_data.get("digest_ref")),
                GOVERNED_EVIDENCE_DIGEST_REF_PREFIX,
            )
        )
    return _dedupe(refs)


def _refs_from_ref_items(value: Any, *, prefix: str | None = None) -> list[str]:
    refs: list[str] = []
    for item in _sequence(value):
        item_data = _mapping(item)
        if item_data:
            refs.extend(_plain_str_list(item_data.get("ref")))
        else:
            refs.extend(_plain_str_list(item))
    return _refs_with_prefix(refs, prefix)


def _refs_with_prefix(refs: list[str], prefix: str | None) -> list[str]:
    if prefix is None:
        return refs
    return [ref for ref in refs if ref.startswith(prefix)]


def _summary_fact_counts(data: dict[str, Any]) -> tuple[int, int]:
    facts = _string_items(data.get("summary_facts"))
    for digest in _sequence(data.get("digests")):
        digest_data = _mapping(digest)
        facts.extend(_string_items(digest_data.get("summary_facts")))
    return len(facts), sum(len(fact) for fact in facts)


def _raw_boundary_violation_count(data: dict[str, Any]) -> int:
    count = _raw_boundary_flag_count(data)
    count += _forbidden_key_count(data)
    return count


def _raw_boundary_flag_count(data: dict[str, Any]) -> int:
    flags = _mapping(data.get("raw_boundary_flags"))
    return sum(1 for value in flags.values() if value is True)


def _raw_boundary_flag_true(data: dict[str, Any], flag_name: str) -> bool:
    flags = _mapping(data.get("raw_boundary_flags"))
    return flags.get(flag_name) is True


def _forbidden_key_count(value: Any) -> int:
    if isinstance(value, Mapping):
        count = 0
        for key, item in value.items():
            if _is_forbidden_key(str(key)):
                count += 1
            count += _forbidden_key_count(item)
        return count
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return sum(_forbidden_key_count(item) for item in value)
    return 0


def _contains_key(value: Any, key_name: str) -> bool:
    if isinstance(value, Mapping):
        return any(
            str(key) == key_name or _contains_key(item, key_name)
            for key, item in value.items()
        )
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return any(_contains_key(item, key_name) for item in value)
    return False


def _safe_string_list(value: Any) -> list[str]:
    return [
        _safe_short_str(item)
        for item in _sequence(value)
        if _safe_short_str(item)
    ][:20]


def _safe_short_str(value: Any) -> str:
    text = str(value).strip()
    if not text:
        return ""
    if _looks_like_forbidden_marker(text):
        return "[redacted-boundary-marker]"
    return text[:200]


def _plain_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _plain_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, Sequence) and not isinstance(value, bytes):
        return [str(item) for item in value if item is not None and str(item)]
    return [str(value)]


def _string_items(value: Any) -> list[str]:
    if value is None or isinstance(value, bytes):
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, Sequence):
        return [str(item) for item in value if isinstance(item, str)]
    return []


def _sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, str | bytes):
        return [value]
    if isinstance(value, Sequence):
        return list(value)
    return [value]


def _optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y"}:
            return True
        if normalized in {"0", "false", "no", "n"}:
            return False
    return None


def _has_nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _non_negative_int(value: Any) -> int:
    if isinstance(value, bool) or value is None:
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _is_forbidden_key(key: str) -> bool:
    lowered = key.lower()
    return (
        lowered in FORBIDDEN_EVIDENCE_SUMMARY_ANSWER_KEYS
        or lowered.endswith("_token")
        or lowered.endswith("_secret")
        or lowered.endswith("_credential")
    )


def _looks_like_forbidden_marker(value: str) -> bool:
    lowered = value.lower()
    return any(
        marker in lowered
        for marker in (
            "api_key",
            "config_context",
            "full productgatewayresponse",
            "observability_candidate_body",
            "prompt_or_messages",
            "raw html",
            "raw payload",
            "raw provider response",
            "raw_payload",
            "raw_provider_response",
            "response_headers",
            "response_text",
            "sanitized_excerpt_preview",
            "secret",
            "system_prompt",
            "token",
        )
    )


__all__ = [
    "EvidenceSummaryAnswerPolicyObservationCandidate",
    "build_evidence_summary_answer_policy_observation_candidate",
]
