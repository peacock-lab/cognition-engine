"""Behavior guards for cognition agent carrier product contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from typing import Any

from behavior_contracts.governance_candidate import CandidateGuardResult
from schemas.cognition_agent_carrier import (
    COGNITION_AGENT_CARRIER_REF_PREFIX,
    COGNITION_AGENT_MATERIAL_CONSUMPTION_REF_PREFIX,
    COGNITION_AGENT_RESPONSE_REF_PREFIX,
    COGNITION_AGENT_RESUME_REQUEST_REF_PREFIX,
    FORBIDDEN_COGNITION_AGENT_CARRIER_KEYS,
    SAFE_REF_PREFIXES,
)


CANDIDATE_REQUIRED_TRUE_FIELDS = frozenset({"candidate_only", "readonly"})
CARRIER_FORBIDDEN_TRUE_FIELDS = frozenset(
    {"execution_enabled", "agent_runtime_enabled", "adk_raw_object_included"}
)
RESUME_REQUEST_FORBIDDEN_TRUE_FIELDS = frozenset(
    {
        "auto_resume_answer_enabled",
        "model_call_requested",
        "user_product_runtime_path_enabled",
        "workflow_replay_enabled",
        "task_runtime_implementation_enabled",
    }
)
RESPONSE_PROJECTION_FORBIDDEN_TRUE_FIELDS = frozenset(
    {
        "raw_provider_response_included",
        "full_answer_persistence_claim",
        "llm_call_performed",
        "product_gateway_user_visible",
    }
)
MATERIAL_CONSUMPTION_FORBIDDEN_TRUE_FIELDS = frozenset(
    {
        "implementation_object_included",
        "provider_implementation_included",
        "raw_evidence_included",
    }
)
RUNTIME_CLAIM_FIELDS = frozenset(
    {
        "adk_raw_object_included",
        "agent_runtime_enabled",
        "auto_resume_answer_enabled",
        "callbacks_enabled",
        "execution_enabled",
        "llm_call_performed",
        "memory_enabled",
        "model_call_requested",
        "plugins_enabled",
        "product_gateway_user_visible",
        "skills_loaded",
        "task_runtime_implementation_enabled",
        "tools_mcp_enabled",
        "user_product_runtime_path_enabled",
        "workflow_replay_enabled",
    }
)
SAFE_SCALAR_TYPES = (str, int, float, bool, type(None))
SENSITIVE_TEXT_MARKERS = (
    "api_key",
    "authorization:",
    "bearer ",
    "config_context",
    "cookie:",
    "credential",
    "full_answer",
    "google.adk",
    "provider_response",
    "raw prompt",
    "raw_prompt",
    "raw provider",
    "secret",
    "system_prompt",
    "token",
    "traceback",
)


def guard_cognition_agent_carrier_raw_boundary(payload: Any) -> CandidateGuardResult:
    """Block raw evidence, prompts, provider payloads, secrets, and raw objects."""

    violations = tuple(_raw_boundary_violations(_mapping(payload), path="$"))
    return CandidateGuardResult(passed=not violations, violations=violations)


def guard_cognition_agent_carrier_ref_prefixes(payload: Any) -> CandidateGuardResult:
    """Validate cognition agent carrier product ref prefixes."""

    data = _mapping(payload)
    violations: list[str] = []
    prefix_checks = {
        "agent_carrier_ref": COGNITION_AGENT_CARRIER_REF_PREFIX,
        "agent_resume_request_ref": COGNITION_AGENT_RESUME_REQUEST_REF_PREFIX,
        "agent_response_ref": COGNITION_AGENT_RESPONSE_REF_PREFIX,
        "material_consumption_ref": COGNITION_AGENT_MATERIAL_CONSUMPTION_REF_PREFIX,
        "continuable_evidence_session_ref": "continuable-evidence-session://",
    }
    for field_name, prefix in prefix_checks.items():
        value = data.get(field_name)
        if value is None:
            continue
        if not isinstance(value, str) or not value.startswith(prefix):
            violations.append(f"{field_name}:invalid_ref_prefix")
    for field_name in (
        "answer_run_ref",
        "answer_artifact_ref",
        "trace_inspect_ref",
        "observability_summary_ref",
        "evaluation_summary_ref",
    ):
        value = data.get(field_name)
        if value is not None and (
            not isinstance(value, str) or not _has_safe_ref_prefix(value)
        ):
            violations.append(f"{field_name}:unsupported_ref_prefix")
    for field_name in (
        "artifact_refs",
        "answer_context_refs",
        "answer_run_refs",
        "boundary_hints_refs",
        "digest_refs",
        "evidence_material_refs",
        "evidence_refs",
        "observability_summary_refs",
        "response_projection_refs",
        "runtime_binding_refs",
        "trace_inspect_refs",
    ):
        for value in _sequence(data.get(field_name)):
            if not isinstance(value, str) or not _has_safe_ref_prefix(value):
                violations.append(f"{field_name}:unsupported_ref_prefix")
    return CandidateGuardResult(passed=not violations, violations=tuple(violations))


def guard_cognition_agent_carrier_candidate_boundary(
    payload: Any,
) -> CandidateGuardResult:
    """Ensure carrier contracts remain candidate-only and read-only."""

    data = _mapping(payload)
    if not _is_payload(data, "cognition_agent_carrier"):
        return CandidateGuardResult(passed=True, violations=())
    violations: list[str] = []
    for field_name in CANDIDATE_REQUIRED_TRUE_FIELDS:
        if data.get(field_name) is not True:
            violations.append(f"{field_name}:must_be_true")
    for field_name in CARRIER_FORBIDDEN_TRUE_FIELDS:
        if data.get(field_name) is True:
            violations.append(f"{field_name}:must_be_false")
    return CandidateGuardResult(passed=not violations, violations=tuple(violations))


def guard_cognition_agent_resume_request_boundary(
    payload: Any,
) -> CandidateGuardResult:
    """Keep resume requests as authorization objects, not model calls."""

    data = _mapping(payload)
    if not _is_payload(data, "cognition_agent_resume_request"):
        return CandidateGuardResult(passed=True, violations=())
    violations: list[str] = []
    if data.get("requires_user_confirmation") is not True:
        violations.append("requires_user_confirmation:must_be_true")
    if data.get("requires_external_readonly_authorization") is not True:
        violations.append("requires_external_readonly_authorization:must_be_true")
    if data.get("resume_authorization_state") in {
        "blocked",
        "expired",
        "deleted",
        "unavailable",
    } and not _sequence(data.get("blocking_reasons")):
        violations.append("blocking_reasons:required_for_non_resumable_state")
    for field_name in RESUME_REQUEST_FORBIDDEN_TRUE_FIELDS:
        if data.get(field_name) is True:
            violations.append(f"{field_name}:must_be_false")
    violations.extend(_raw_boundary_violations(data, path="$"))
    return CandidateGuardResult(passed=not violations, violations=tuple(violations))


def guard_cognition_agent_response_projection_boundary(
    payload: Any,
) -> CandidateGuardResult:
    """Keep response projections refs-only and not user-visible execution."""

    data = _mapping(payload)
    if not _is_payload(data, "cognition_agent_response_projection"):
        return CandidateGuardResult(passed=True, violations=())
    violations: list[str] = []
    for field_name in RESPONSE_PROJECTION_FORBIDDEN_TRUE_FIELDS:
        if data.get(field_name) is True:
            violations.append(f"{field_name}:must_be_false")
    violations.extend(_raw_boundary_violations(data, path="$"))
    return CandidateGuardResult(passed=not violations, violations=tuple(violations))


def guard_cognition_agent_material_consumption_refs_only(
    payload: Any,
) -> CandidateGuardResult:
    """Ensure external-readonly material consumption is refs-only."""

    data = _mapping(payload)
    if not _is_payload(data, "cognition_agent_material_consumption"):
        return CandidateGuardResult(passed=True, violations=())
    violations: list[str] = []
    if data.get("source_layer") != "external_readonly":
        violations.append("source_layer:must_be_external_readonly")
    if data.get("refs_only") is not True:
        violations.append("refs_only:must_be_true")
    if not _sequence(data.get("evidence_refs")):
        violations.append("evidence_refs:required")
    if not _sequence(data.get("digest_refs")):
        violations.append("digest_refs:required")
    for field_name in MATERIAL_CONSUMPTION_FORBIDDEN_TRUE_FIELDS:
        if data.get(field_name) is True:
            violations.append(f"{field_name}:must_be_false")
    violations.extend(_raw_boundary_violations(data, path="$"))
    return CandidateGuardResult(passed=not violations, violations=tuple(violations))


def guard_cognition_agent_runtime_claims(payload: Any) -> CandidateGuardResult:
    """Block direct runtime, gateway, memory, tool, skill, callback, or plugin claims."""

    violations = tuple(_runtime_claim_violations(_mapping(payload), path="$"))
    return CandidateGuardResult(passed=not violations, violations=violations)


def validate_cognition_agent_carrier_guards(payload: Any) -> CandidateGuardResult:
    """Run the default non-executing cognition agent carrier guards."""

    violations: list[str] = []
    for guard in DEFAULT_COGNITION_AGENT_CARRIER_GUARDS:
        result = guard(payload)
        violations.extend(result.violations)
    unique_violations = tuple(dict.fromkeys(violations))
    return CandidateGuardResult(
        passed=not unique_violations,
        violations=unique_violations,
    )


DEFAULT_COGNITION_AGENT_CARRIER_GUARDS = (
    guard_cognition_agent_carrier_raw_boundary,
    guard_cognition_agent_carrier_ref_prefixes,
    guard_cognition_agent_carrier_candidate_boundary,
    guard_cognition_agent_resume_request_boundary,
    guard_cognition_agent_response_projection_boundary,
    guard_cognition_agent_material_consumption_refs_only,
    guard_cognition_agent_runtime_claims,
)


def _mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items() if isinstance(key, str)}
    if is_dataclass(value) and not isinstance(value, type):
        return _mapping(asdict(value))
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="python")
        if isinstance(dumped, Mapping):
            return _mapping(dumped)
    return {}


def _sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list | tuple):
        return list(value)
    return []


def _is_payload(data: Mapping[str, Any], payload_type: str) -> bool:
    return data.get("payload_type") == payload_type


def _has_safe_ref_prefix(value: str) -> bool:
    return any(value.startswith(prefix) for prefix in SAFE_REF_PREFIXES)


def _raw_boundary_violations(value: Any, *, path: str) -> list[str]:
    violations: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            normalized_key = key_text.lower()
            if normalized_key in FORBIDDEN_COGNITION_AGENT_CARRIER_KEYS:
                violations.append(f"{path}.{key_text}:forbidden_raw_boundary_key")
            violations.extend(
                _raw_boundary_violations(item, path=f"{path}.{key_text}")
            )
        return violations
    if isinstance(value, list | tuple):
        for index, item in enumerate(value):
            violations.extend(_raw_boundary_violations(item, path=f"{path}[{index}]"))
        return violations
    if isinstance(value, str):
        normalized = value.lower()
        for marker in SENSITIVE_TEXT_MARKERS:
            if marker in normalized:
                violations.append(f"{path}:forbidden_raw_boundary_marker:{marker}")
                break
    return violations


def _runtime_claim_violations(value: Any, *, path: str) -> list[str]:
    violations: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if key_text in RUNTIME_CLAIM_FIELDS and item is True:
                violations.append(f"{path}.{key_text}:runtime_claim_forbidden")
            violations.extend(_runtime_claim_violations(item, path=f"{path}.{key_text}"))
        return violations
    if isinstance(value, list | tuple):
        for index, item in enumerate(value):
            violations.extend(_runtime_claim_violations(item, path=f"{path}[{index}]"))
    return violations


__all__ = [
    "DEFAULT_COGNITION_AGENT_CARRIER_GUARDS",
    "guard_cognition_agent_carrier_candidate_boundary",
    "guard_cognition_agent_carrier_raw_boundary",
    "guard_cognition_agent_carrier_ref_prefixes",
    "guard_cognition_agent_material_consumption_refs_only",
    "guard_cognition_agent_response_projection_boundary",
    "guard_cognition_agent_resume_request_boundary",
    "guard_cognition_agent_runtime_claims",
    "validate_cognition_agent_carrier_guards",
]
