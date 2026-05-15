from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from schemas.adk_tool import (
    ADK_TOOL_MIN_VERSION,
    AdkFunctionToolAuditContract,
    AdkFunctionToolAuditStatus,
    AdkFunctionToolCapabilityOrigin,
    AdkFunctionToolCapabilityProfile,
    AdkFunctionToolFailureType,
    AdkFunctionToolRiskProfile,
    ToolRiskLevel,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
ADK_TOOL_SCHEMA_ROOT = REPO_ROOT / "packages" / "schemas" / "src" / "schemas" / "adk_tool"


def test_adk_function_tool_audit_contract_accepts_sanitized_success() -> None:
    audit = AdkFunctionToolAuditContract(
        tool_name="deterministic_external_echo",
        tool_kind="deterministic_low_risk_external_smoke",
        status=AdkFunctionToolAuditStatus.SUCCESS,
        tool_call_allowed=True,
        tool_call_attempted=True,
        tool_runtime_call_performed=True,
        tool_confirmation_required=True,
        tool_confirmation_granted=True,
        adk_tool_confirmation_requested=True,
        tool_approval_ref="operator-approval://tool/1",
        tool_confirmation_decision_source="explicit_smoke_fixture",
        tool_input_summary={
            "argument_keys": ["echo_label", "message_kind", "message_ref"],
            "argument_count": 3,
        },
        tool_output_summary={
            "result_keys": [
                "does_not_store_raw_input",
                "external_side_effects",
                "recommendation",
            ],
            "external_side_effects": False,
        },
        tool_evidence_ref="adk-tool-call-evidence://evidence-1",
        tool_run_ref="adk-tool-run://run-1",
    )

    assert audit.tool_failure_type is None
    assert audit.raw_adk_object_included is False
    assert audit.does_not_store_raw_tool_input is True
    assert audit.does_not_store_raw_tool_output is True


def test_adk_function_tool_audit_contract_accepts_blocked_failure() -> None:
    audit = AdkFunctionToolAuditContract(
        tool_name="deterministic_external_echo",
        tool_kind="deterministic_low_risk_external_smoke",
        status=AdkFunctionToolAuditStatus.FAILED,
        tool_call_allowed=False,
        tool_call_attempted=False,
        tool_runtime_call_performed=False,
        tool_confirmation_required=True,
        tool_confirmation_granted=False,
        tool_failure_type=AdkFunctionToolFailureType.TOOL_CONFIRMATION_REQUIRED,
    )

    assert audit.tool_failure_type == AdkFunctionToolFailureType.TOOL_CONFIRMATION_REQUIRED


@pytest.mark.parametrize(
    "raw_boundary",
    [
        {"raw_adk_object_included": True},
        {"does_not_store_raw_tool_input": False},
        {"does_not_store_raw_tool_output": False},
        {"tool_input_summary": {"raw_tool_input": {"message": "raw"}}},
        {"tool_output_summary": {"object_module": "google.adk.tools.tool_context"}},
    ],
)
def test_adk_function_tool_audit_contract_rejects_raw_boundaries(
    raw_boundary: dict[str, object],
) -> None:
    values = {
        "tool_name": "deterministic_external_echo",
        "tool_kind": "deterministic_low_risk_external_smoke",
        "status": AdkFunctionToolAuditStatus.SUCCESS,
        "tool_call_allowed": True,
        "tool_call_attempted": True,
        "tool_runtime_call_performed": True,
        "tool_confirmation_required": True,
        "tool_confirmation_granted": True,
    }
    values.update(raw_boundary)

    with pytest.raises(ValidationError):
        AdkFunctionToolAuditContract(**values)


def test_adk_function_tool_capability_profile_freezes_low_risk_boundary() -> None:
    risk_profile = AdkFunctionToolRiskProfile(
        tool_name="deterministic_external_echo",
        risk_level=ToolRiskLevel.LOW,
        external_side_effects=False,
        requires_confirmation=True,
    )
    capability = AdkFunctionToolCapabilityProfile(
        tool_name="deterministic_external_echo",
        tool_kind="deterministic_low_risk_external_smoke",
        capability_origin=AdkFunctionToolCapabilityOrigin.ADK_NATIVE_FUNCTION_TOOL,
        risk_profile=risk_profile,
    )

    assert capability.adk_min_version == ADK_TOOL_MIN_VERSION
    assert capability.require_confirmation_supported is True
    assert capability.low_risk_allowlist_required is True
    assert capability.raw_adk_object_included is False


@pytest.mark.parametrize(
    "risk_profile",
    [
        {"external_side_effects": True},
        {"reads_files": True},
        {"writes_files": True},
        {"accesses_network": True},
        {"executes_shell": True},
        {"calls_llm": True},
        {"creates_external_resources": True},
        {"requires_confirmation": False},
        {"candidate_only": False},
    ],
)
def test_low_risk_profile_rejects_side_effects_and_execution_flags(
    risk_profile: dict[str, object],
) -> None:
    values = {
        "tool_name": "deterministic_external_echo",
        "risk_level": ToolRiskLevel.LOW,
        "external_side_effects": False,
        "requires_confirmation": True,
    }
    values.update(risk_profile)

    with pytest.raises(ValidationError):
        AdkFunctionToolRiskProfile(**values)


def test_adk_tool_schemas_do_not_import_adapter_or_adk_libraries() -> None:
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+(?:adk_adapter|google\.adk|litellm)\b",
        re.MULTILINE,
    )

    for source_path in ADK_TOOL_SCHEMA_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_imports.search(source) is None, source_path
