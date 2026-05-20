"""Behavior guards for external-readonly governed summary facts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from behavior_contracts.governance_candidate import CandidateGuardResult
from schemas.evidence_summary_answer import (
    EXTERNAL_READONLY_EVIDENCE_REF_PREFIX,
    FORBIDDEN_EVIDENCE_SUMMARY_ANSWER_KEYS,
    FORBIDDEN_EVIDENCE_SUMMARY_ANSWER_OBJECT_MODULE_PREFIXES,
    SUMMARY_FACT_ITEM_MAX_CHARS,
    SUMMARY_FACT_MAX_CHARS,
    SUMMARY_FACT_MAX_ITEMS,
)
from schemas.external_readonly_governed_summary_facts import (
    EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_PAYLOAD_TYPE,
    EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_STATUSES,
    EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_VERSION,
    EXTERNAL_READONLY_GOVERNED_SUMMARY_FACT_REF_PREFIX,
)


EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_EXTRA_FORBIDDEN_KEYS = frozenset(
    {
        "authorization",
        "auth_header",
        "auth_headers",
        "password",
        "sanitized_excerpt",
        "set_cookie",
    }
)


class ExternalReadonlyGovernedSummaryFactsHeaderGuard:
    """Validate frozen governed summary facts payload headers."""

    guard_name = "external_readonly_governed_summary_facts_header_guard"

    def validate(self, payload: Mapping[str, Any]) -> CandidateGuardResult:
        violations: list[str] = []
        if (
            payload.get("payload_type")
            != EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_PAYLOAD_TYPE
        ):
            violations.append(
                "payload_type must be "
                f"{EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_PAYLOAD_TYPE}."
            )
        if (
            payload.get("payload_version")
            != EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_VERSION
        ):
            violations.append(
                "payload_version must be "
                f"{EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_VERSION}."
            )
        status = payload.get("status")
        if status not in EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_STATUSES:
            violations.append(f"unsupported governed summary facts status: {status}.")
        if not _is_nonempty_string(payload.get("evidence_ref")):
            violations.append("evidence_ref is required.")
        return _result(violations)


class ExternalReadonlyGovernedSummaryFactsNoRawBoundaryGuard:
    """Reject raw, provider, config, prompt, and runtime boundary leakage."""

    guard_name = "external_readonly_governed_summary_facts_no_raw_boundary_guard"

    def validate(self, payload: Mapping[str, Any]) -> CandidateGuardResult:
        violations: list[str] = []
        for path, value in _walk(payload):
            if _is_runtime_boundary(path, value):
                violations.append(f"runtime object leakage is forbidden at {path}.")
            elif _is_raw_boundary(path, value):
                violations.append(f"raw boundary field is forbidden at {path}.")
        for path, value in _walk(payload):
            if _key_at_path(path) == "raw_boundary_flags" and isinstance(
                value, Mapping
            ):
                violations.extend(_raw_boundary_flag_violations(path, value))
        return _result(violations)


class ExternalReadonlyGovernedSummaryFactsContentGuard:
    """Validate content and cross-field constraints for governed facts."""

    guard_name = "external_readonly_governed_summary_facts_content_guard"

    def validate(self, payload: Mapping[str, Any]) -> CandidateGuardResult:
        violations: list[str] = []

        evidence_ref = payload.get("evidence_ref")
        if not isinstance(evidence_ref, str) or not evidence_ref.startswith(
            EXTERNAL_READONLY_EVIDENCE_REF_PREFIX
        ):
            violations.append(
                "evidence_ref must start with "
                f"{EXTERNAL_READONLY_EVIDENCE_REF_PREFIX}."
            )

        source_url_host = payload.get("source_url_host")
        if isinstance(source_url_host, str) and _host_has_path_or_query(
            source_url_host
        ):
            violations.append(
                "source_url_host must be a host without scheme, path, or query."
            )

        facts = payload.get("facts")
        if not isinstance(facts, (list, tuple)):
            violations.append("facts must be a list.")
            facts = ()
        if len(facts) > SUMMARY_FACT_MAX_ITEMS:
            violations.append(f"facts must contain at most {SUMMARY_FACT_MAX_ITEMS}.")

        fact_refs: set[str] = set()
        total_fact_chars = 0
        for index, fact in enumerate(facts, start=1):
            if not isinstance(fact, Mapping):
                violations.append(f"facts[{index - 1}] must be a mapping.")
                continue
            fact_ref = fact.get("fact_ref")
            if not isinstance(fact_ref, str) or not fact_ref.startswith(
                EXTERNAL_READONLY_GOVERNED_SUMMARY_FACT_REF_PREFIX
            ):
                violations.append(
                    f"facts[{index - 1}].fact_ref must start with "
                    f"{EXTERNAL_READONLY_GOVERNED_SUMMARY_FACT_REF_PREFIX}."
                )
            elif fact_ref in fact_refs:
                violations.append("fact_ref values must be unique.")
            else:
                fact_refs.add(fact_ref)

            fact_index = fact.get("fact_index")
            if fact_index != index:
                violations.append("fact_index values must be consecutive from 1.")

            fact_text = fact.get("fact_text")
            if not _is_nonempty_string(fact_text):
                violations.append(f"facts[{index - 1}].fact_text is required.")
            else:
                if len(fact_text) > SUMMARY_FACT_ITEM_MAX_CHARS:
                    violations.append(
                        f"facts[{index - 1}].fact_text exceeds "
                        f"{SUMMARY_FACT_ITEM_MAX_CHARS} characters."
                    )
                total_fact_chars += len(fact_text)

            fact_evidence_ref = fact.get("evidence_ref")
            if fact_evidence_ref != evidence_ref:
                violations.append("facts must use the bundle evidence_ref.")

        fact_count = payload.get("fact_count")
        if fact_count != len(facts):
            violations.append("fact_count must equal the number of facts.")

        declared_total_fact_chars = payload.get("total_fact_chars")
        if declared_total_fact_chars != total_fact_chars:
            violations.append("total_fact_chars must equal facts text length total.")
        if isinstance(declared_total_fact_chars, int) and (
            declared_total_fact_chars > SUMMARY_FACT_MAX_CHARS
        ):
            violations.append(
                f"total_fact_chars must not exceed {SUMMARY_FACT_MAX_CHARS}."
            )

        facts_budget = payload.get("facts_budget", SUMMARY_FACT_MAX_CHARS)
        if not isinstance(facts_budget, int) or not (
            1 <= facts_budget <= SUMMARY_FACT_MAX_CHARS
        ):
            violations.append(
                f"facts_budget must be between 1 and {SUMMARY_FACT_MAX_CHARS}."
            )
        elif isinstance(declared_total_fact_chars, int) and (
            declared_total_fact_chars > facts_budget
        ):
            violations.append("total_fact_chars must not exceed facts_budget.")

        status = payload.get("status")
        if status == "ready":
            if payload.get("reference_review_ready") is not True:
                violations.append("ready facts require reference_review_ready=true.")
            if payload.get("evidence_written") is not True:
                violations.append("ready facts require evidence_written=true.")
            if not facts:
                violations.append("ready facts require at least one fact.")
        elif status == "blocked":
            if not _has_nonempty_string_item(payload.get("blocking_reasons")):
                violations.append("blocked facts require blocking_reasons.")
            if payload.get("allowed_for_model_context") is True:
                violations.append("blocked facts cannot be allowed for model context.")
        elif status == "empty":
            if facts or payload.get("fact_count") or payload.get("total_fact_chars"):
                violations.append("empty facts must not carry fact content.")
            if payload.get("allowed_for_model_context") is True:
                violations.append("empty facts cannot be allowed for model context.")

        if payload.get("allowed_for_model_context") is True and status != "ready":
            violations.append("model context is only allowed for ready facts.")

        return _result(violations)


DEFAULT_EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_GUARDS = (
    ExternalReadonlyGovernedSummaryFactsHeaderGuard(),
    ExternalReadonlyGovernedSummaryFactsNoRawBoundaryGuard(),
    ExternalReadonlyGovernedSummaryFactsContentGuard(),
)


def validate_external_readonly_governed_summary_facts_guards(
    payload: Mapping[str, Any],
    guards: tuple[
        ExternalReadonlyGovernedSummaryFactsHeaderGuard
        | ExternalReadonlyGovernedSummaryFactsNoRawBoundaryGuard
        | ExternalReadonlyGovernedSummaryFactsContentGuard,
        ...,
    ] = DEFAULT_EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_GUARDS,
) -> CandidateGuardResult:
    """Run governed summary facts guards without executing anything."""

    violations: list[str] = []
    for guard in guards:
        result = guard.validate(payload)
        violations.extend(f"{guard.guard_name}: {item}" for item in result.violations)
    return _result(violations)


def _result(violations: list[str]) -> CandidateGuardResult:
    return CandidateGuardResult(
        passed=not violations,
        violations=tuple(violations),
    )


def _walk(value: Any, path: str = "$") -> list[tuple[str, Any]]:
    items = [(path, value)]
    if isinstance(value, Mapping):
        for key, item in value.items():
            items.extend(_walk(item, f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            items.extend(_walk(item, f"{path}[{index}]"))
    return items


def _key_at_path(path: str) -> str:
    return path.rsplit(".", maxsplit=1)[-1].split("[", maxsplit=1)[0].lower()


def _is_raw_boundary(path: str, value: Any) -> bool:
    key = _key_at_path(path)
    if (
        key in FORBIDDEN_EVIDENCE_SUMMARY_ANSWER_KEYS
        or key in EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_EXTRA_FORBIDDEN_KEYS
        or key.endswith("_token")
        or key.endswith("_secret")
        or key.endswith("_credential")
    ):
        return True
    return isinstance(value, str) and _looks_like_forbidden_marker(value)


def _is_runtime_boundary(path: str, value: Any) -> bool:
    key = _key_at_path(path)
    if key == "object_module" and isinstance(value, str) and _is_runtime_module(value):
        return True
    return _is_runtime_object(value)


def _raw_boundary_flag_violations(
    path: str,
    raw_boundary_flags: Mapping[str, Any],
) -> list[str]:
    return [
        f"{path}.{key} must not be true."
        for key, value in raw_boundary_flags.items()
        if value is True
    ]


def _host_has_path_or_query(value: str) -> bool:
    if not value.strip():
        return True
    return any(marker in value for marker in ("://", "/", "?", "#", "@", ":"))


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_nonempty_string_item(value: Any) -> bool:
    return isinstance(value, (list, tuple)) and any(
        isinstance(item, str) and bool(item.strip()) for item in value
    )


def _is_runtime_object(value: Any) -> bool:
    if value is None or isinstance(value, (str, int, float, bool, list, tuple, dict)):
        return False
    return _is_runtime_module(type(value).__module__)


def _is_runtime_module(module_name: str) -> bool:
    return module_name.startswith(
        FORBIDDEN_EVIDENCE_SUMMARY_ANSWER_OBJECT_MODULE_PREFIXES
    )


def _looks_like_forbidden_marker(value: str) -> bool:
    lowered = value.lower()
    return any(
        marker in lowered
        for marker in (
            "api_key",
            "authorization",
            "authorization:",
            "config_context",
            "config context value",
            "full productgatewayresponse",
            "full_product_gateway_response",
            "observability_candidate_body",
            "prompt_or_messages",
            "raw html",
            "raw payload",
            "raw provider response",
            "raw_payload",
            "raw_provider_response",
            "response_headers",
            "response_text",
            "sanitized_excerpt",
            "sanitized_excerpt_preview",
            "set-cookie",
            "system_prompt",
        )
    )


__all__ = [
    "DEFAULT_EXTERNAL_READONLY_GOVERNED_SUMMARY_FACTS_GUARDS",
    "ExternalReadonlyGovernedSummaryFactsContentGuard",
    "ExternalReadonlyGovernedSummaryFactsHeaderGuard",
    "ExternalReadonlyGovernedSummaryFactsNoRawBoundaryGuard",
    "validate_external_readonly_governed_summary_facts_guards",
]
