from __future__ import annotations

import re
from pathlib import Path

from behavior_contracts.product_gateway_response_summary import (
    ProductGatewayResponseBlockedRequiresReasonGuard,
    ProductGatewayResponseNoExecutionGuard,
    ProductGatewayResponseNoRawPayloadGuard,
    ProductGatewayResponseNoRuntimeObjectLeakageGuard,
    ProductGatewayResponseRefsOnlyGuard,
    ProductGatewayResponseSummaryHeaderGuard,
    ProductGatewayResponseSummaryOnlyGuard,
    validate_product_gateway_response_summary_guards,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
BEHAVIOR_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "behavior_contracts" / "src" / "behavior_contracts"
)


def test_product_gateway_response_summary_guards_accept_safe_summary() -> None:
    result = validate_product_gateway_response_summary_guards(_summary())

    assert result.passed is True
    assert result.violations == ()


def test_product_gateway_response_summary_header_guard_rejects_invalid_header() -> None:
    summary = _summary()
    summary["payload_version"] = "other"

    result = ProductGatewayResponseSummaryHeaderGuard().validate(summary)

    assert result.passed is False
    assert "payload_version" in result.violations[0]


def test_product_gateway_response_summary_only_guard_rejects_body_fields() -> None:
    summary = _summary()
    summary["metadata"] = {"response_text": "raw body"}

    result = ProductGatewayResponseSummaryOnlyGuard().validate(summary)

    assert result.passed is False
    assert "summary-only" in result.violations[0]


def test_product_gateway_response_refs_only_guard_rejects_non_ref_item() -> None:
    summary = _summary()
    summary["evidence_refs"] = [
        {
            "ref": "evidence://request-1",
            "kind": "evidence",
            "payload": {"raw": "not allowed"},
        }
    ]

    result = ProductGatewayResponseRefsOnlyGuard().validate(summary)

    assert result.passed is False
    assert "payload" in result.violations[0]


def test_product_gateway_response_refs_only_guard_checks_additional_refs() -> None:
    summary = _summary()
    summary["additional_refs"] = [
        {
            "ref": "external-readonly-evidence-observation://observation-1",
            "kind": "external_readonly_evidence_observation",
            "candidate": {"raw": "not allowed"},
        }
    ]

    result = ProductGatewayResponseRefsOnlyGuard().validate(summary)

    assert result.passed is False
    assert "additional_refs" in result.violations[0]
    assert "candidate" in result.violations[0]


def test_product_gateway_response_no_raw_payload_guard_rejects_raw_fields() -> None:
    summary = _summary()
    summary["metadata"] = {"raw_provider_response": {"content": "raw"}}

    result = ProductGatewayResponseNoRawPayloadGuard().validate(summary)

    assert result.passed is False
    assert "raw or sensitive" in result.violations[0]


def test_product_gateway_response_no_execution_guard_rejects_enabled_flags() -> None:
    summary = _summary()
    summary["execution_enabled"] = True

    result = ProductGatewayResponseNoExecutionGuard().validate(summary)

    assert result.passed is False
    assert "execution_enabled" in result.violations[0]


def test_product_gateway_response_no_runtime_object_guard_rejects_markers() -> None:
    summary = _summary()
    summary["metadata"] = {"object_module": "google.adk.runners"}

    result = ProductGatewayResponseNoRuntimeObjectLeakageGuard().validate(summary)

    assert result.passed is False
    assert "runtime object leakage" in result.violations[0]


def test_product_gateway_response_blocked_guard_requires_reason() -> None:
    summary = _summary(status="blocked")
    summary["blocking_reasons"] = []

    result = ProductGatewayResponseBlockedRequiresReasonGuard().validate(summary)

    assert result.passed is False
    assert "blocking_reasons" in result.violations[0]


def test_product_gateway_response_summary_guards_have_no_execution_layer_imports() -> None:
    source = (
        BEHAVIOR_SOURCE_ROOT / "product_gateway_response_summary.py"
    ).read_text(encoding="utf-8")
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:product_gateway|cognition_agent|cognition_governance|config_contexts|"
        r"runtime_container|composition|adk_adapter|google\.adk|litellm)\b",
        re.MULTILINE,
    )

    assert forbidden_imports.search(source) is None


def _summary(status: str = "success") -> dict[str, object]:
    return {
        "product": "product_gateway",
        "payload_type": "product_gateway_response_summary",
        "payload_version": "product_gateway_response_summary_v1",
        "request_id": "request-1",
        "entry_kind": "agent_shell",
        "status": status,
        "exit_code": 0 if status in {"success", "skipped"} else 1,
        "product_gateway_response_ref": "product-gateway-response://request-1",
        "governance_summary_ref": "governance-summary://request-1",
        "evidence_refs": [
            {
                "ref": "evidence://request-1",
                "kind": "evidence",
                "purpose": "review",
                "metadata": {"source": "product_gateway.agent_shell"},
            }
        ],
        "audit_refs": [{"ref": "audit://request-1", "kind": "audit"}],
        "agent_advice_refs": [
            {"ref": "agent-advice://agent-task-advice-1", "kind": "agent_advice"}
        ],
        "tool_audit_refs": [
            {"ref": "tool-audit://tool-smoke-1", "kind": "tool_audit"}
        ],
        "additional_refs": [
            {
                "ref": "external-readonly-evidence-observation://observation-1",
                "kind": "external_readonly_evidence_observation",
                "purpose": "external_readonly_readonly_public_refs",
                "metadata": {"source": "product_gateway.external_readonly_refs"},
            }
        ],
        "blocking_reasons": ["product_gateway_blocked"]
        if status == "blocked"
        else [],
        "warnings": [],
        "metadata": {"source": "product_gateway.agent_shell"},
    }
