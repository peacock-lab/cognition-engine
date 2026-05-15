"""Behavior contracts for ADK native FunctionTool product boundaries."""

from __future__ import annotations

from typing import Any, Mapping

from behavior_contracts.governance_candidate import CandidateGuardResult
from schemas.adk_tool import (
    AdkFunctionToolAuditContract,
    AdkFunctionToolAuditStatus,
    AdkFunctionToolRiskProfile,
    ToolRiskLevel,
)


def assert_tool_audit_is_sanitized(
    audit: AdkFunctionToolAuditContract | Mapping[str, Any],
) -> CandidateGuardResult:
    """Validate that public Tool audit facts do not expose raw runtime payloads."""

    try:
        AdkFunctionToolAuditContract.model_validate(audit)
    except ValueError as exc:
        return CandidateGuardResult(False, (str(exc),))
    return CandidateGuardResult(True)


def assert_low_risk_tool_requires_no_external_side_effects(
    risk_profile: AdkFunctionToolRiskProfile | Mapping[str, Any],
) -> CandidateGuardResult:
    """Validate the low-risk Tool profile boundary."""

    try:
        profile = AdkFunctionToolRiskProfile.model_validate(risk_profile)
    except ValueError as exc:
        return CandidateGuardResult(False, (str(exc),))
    if profile.risk_level is not ToolRiskLevel.LOW:
        return CandidateGuardResult(False, ("risk_level must be low.",))
    return CandidateGuardResult(True)


def assert_controlled_live_tool_requires_explicit_confirmation(
    audit: AdkFunctionToolAuditContract | Mapping[str, Any],
) -> CandidateGuardResult:
    """Require explicit confirmation before controlled-live Tool execution."""

    try:
        contract = AdkFunctionToolAuditContract.model_validate(audit)
    except ValueError as exc:
        return CandidateGuardResult(False, (str(exc),))
    violations: list[str] = []
    if contract.tool_runtime_call_performed:
        if not contract.tool_confirmation_required:
            violations.append("tool_confirmation_required must be true.")
        if not contract.tool_confirmation_granted:
            violations.append("tool_confirmation_granted must be true.")
        if not contract.tool_confirmation_decision_source:
            violations.append("tool_confirmation_decision_source is required.")
    return CandidateGuardResult(not violations, tuple(violations))


def assert_tool_consumer_is_candidate_only(
    consumer_facts: Mapping[str, Any],
) -> CandidateGuardResult:
    """Require Tool consumers to remain read-only candidate consumers."""

    violations: list[str] = []
    if consumer_facts.get("candidate_only") is not True:
        violations.append("candidate_only must be true.")
    for field_name in (
        "tool_execution_enabled",
        "tool_control_plane_enabled",
        "runtime_execution_enabled",
        "formal_governance_decision_enabled",
    ):
        if consumer_facts.get(field_name) is True:
            violations.append(f"{field_name} must not be true.")
    return CandidateGuardResult(not violations, tuple(violations))


def assert_no_raw_adk_or_tool_payload(
    value: Mapping[str, Any],
) -> CandidateGuardResult:
    """Reject raw ADK, ToolContext, ToolConfirmation, input, and output payloads."""

    violations = [
        f"raw ADK or tool payload is forbidden at {path}."
        for path, item in _walk(value)
        if _is_raw_tool_payload(path, item)
    ]
    return CandidateGuardResult(not violations, tuple(violations))


def _walk(value: Any, path: str = "$") -> list[tuple[str, Any]]:
    items = [(path, value)]
    if isinstance(value, Mapping):
        for key, item in value.items():
            items.extend(_walk(item, f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            items.extend(_walk(item, f"{path}[{index}]"))
    return items


def _is_raw_tool_payload(path: str, value: Any) -> bool:
    key = path.rsplit(".", maxsplit=1)[-1].lower()
    if key in {
        "adk_object",
        "function_tool",
        "raw",
        "raw_adk_object",
        "raw_input",
        "raw_output",
        "raw_tool_input",
        "raw_tool_output",
        "tool_confirmation",
        "tool_context",
        "tool_input",
        "tool_output",
    }:
        return True
    if isinstance(value, Mapping):
        module_name = value.get("object_module")
        return isinstance(module_name, str) and module_name.startswith("google.adk")
    if value is None or isinstance(value, (str, int, float, bool, list, tuple, dict)):
        return False
    return type(value).__module__.startswith("google.adk")
