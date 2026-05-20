from __future__ import annotations

from behavior_contracts.adk_tool import (
    assert_controlled_live_tool_requires_explicit_confirmation,
    assert_low_risk_tool_requires_no_external_side_effects,
    assert_no_raw_adk_or_tool_payload,
    assert_tool_audit_is_sanitized,
    assert_tool_consumer_is_candidate_only,
)
from schemas.adk_tool import (
    AdkFunctionToolAuditStatus,
    AdkFunctionToolFailureType,
    ToolRiskLevel,
)


def test_tool_audit_sanitized_guard_accepts_project_side_contract() -> None:
    result = assert_tool_audit_is_sanitized(_successful_tool_audit())

    assert result.passed is True
    assert result.violations == ()


def test_tool_audit_sanitized_guard_rejects_raw_payload() -> None:
    audit = _successful_tool_audit()
    audit["tool_input_summary"] = {"raw_tool_input": "secret"}

    result = assert_tool_audit_is_sanitized(audit)

    assert result.passed is False
    assert "raw_tool_input" in result.violations[0]


def test_low_risk_tool_guard_accepts_no_side_effect_profile() -> None:
    result = assert_low_risk_tool_requires_no_external_side_effects(
        {
            "tool_name": "deterministic_external_echo",
            "risk_level": ToolRiskLevel.LOW,
            "external_side_effects": False,
            "requires_confirmation": True,
        }
    )

    assert result.passed is True


def test_low_risk_tool_guard_rejects_external_side_effects() -> None:
    result = assert_low_risk_tool_requires_no_external_side_effects(
        {
            "tool_name": "deterministic_external_echo",
            "risk_level": ToolRiskLevel.LOW,
            "external_side_effects": True,
            "requires_confirmation": True,
        }
    )

    assert result.passed is False
    assert "external_side_effects" in result.violations[0]


def test_controlled_live_guard_requires_confirmation_for_runtime_call() -> None:
    audit = _successful_tool_audit()
    audit["tool_confirmation_decision_source"] = None

    result = assert_controlled_live_tool_requires_explicit_confirmation(audit)

    assert result.passed is False
    assert "tool_confirmation_decision_source" in result.violations[0]


def test_candidate_only_consumer_guard_rejects_execution_flags() -> None:
    result = assert_tool_consumer_is_candidate_only(
        {
            "candidate_only": True,
            "tool_execution_enabled": True,
        }
    )

    assert result.passed is False
    assert "tool_execution_enabled" in result.violations[0]


def test_raw_adk_payload_guard_rejects_tool_context_marker() -> None:
    result = assert_no_raw_adk_or_tool_payload(
        {
            "tool_context": {
                "object_module": "google.adk.tools.tool_context",
            }
        }
    )

    assert result.passed is False
    assert "tool_context" in result.violations[0]


def test_blocked_tool_audit_can_use_failure_type_contract() -> None:
    audit = _successful_tool_audit()
    audit.update(
        {
            "status": AdkFunctionToolAuditStatus.FAILED,
            "tool_call_allowed": False,
            "tool_call_attempted": False,
            "tool_runtime_call_performed": False,
            "tool_confirmation_granted": False,
            "tool_confirmation_decision_source": None,
            "tool_failure_type": AdkFunctionToolFailureType.TOOL_SMOKE_DISABLED,
        }
    )

    result = assert_tool_audit_is_sanitized(audit)

    assert result.passed is True


def _successful_tool_audit() -> dict[str, object]:
    return {
        "tool_name": "deterministic_external_echo",
        "tool_kind": "deterministic_low_risk_external_smoke",
        "status": AdkFunctionToolAuditStatus.SUCCESS,
        "tool_call_allowed": True,
        "tool_call_attempted": True,
        "tool_runtime_call_performed": True,
        "tool_confirmation_required": True,
        "tool_confirmation_granted": True,
        "adk_tool_confirmation_requested": True,
        "tool_approval_ref": "operator-approval://tool/1",
        "tool_confirmation_decision_source": "explicit_smoke_fixture",
        "tool_input_summary": {
            "argument_keys": ["echo_label", "message_kind", "message_ref"],
            "argument_count": 3,
        },
        "tool_output_summary": {
            "result_keys": ["recommendation", "external_side_effects"],
            "external_side_effects": False,
        },
        "tool_failure_type": None,
        "does_not_store_raw_tool_input": True,
        "does_not_store_raw_tool_output": True,
        "raw_adk_object_included": False,
    }
