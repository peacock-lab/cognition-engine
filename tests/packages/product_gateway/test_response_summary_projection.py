from __future__ import annotations

import re
from pathlib import Path

from product_gateway.contracts import (
    ProductGatewayEntryKind,
    ProductGatewayOutputRefs,
    ProductGatewayRef,
    ProductGatewayResponse,
    ProductGatewayStatus,
)
from product_gateway.response_summary_projection import (
    project_product_gateway_response_summary,
)
from schemas.product_gateway_response_summary import (
    PRODUCT_GATEWAY_RESPONSE_SUMMARY_VERSION,
    validate_product_gateway_response_summary,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
PRODUCT_GATEWAY_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "product_gateway" / "src" / "product_gateway"
)


def test_response_summary_projection_builds_external_readonly_summary() -> None:
    response = ProductGatewayResponse(
        request_id="external-readonly/request-1",
        entry_kind=ProductGatewayEntryKind.EXTERNAL_READONLY_FETCH,
        status=ProductGatewayStatus.SUCCESS,
        output_refs=ProductGatewayOutputRefs(
            evidence_refs=[
                ProductGatewayRef(
                    ref="evidence://external-readonly/request-1",
                    kind="sanitized_evidence",
                    purpose="external_readonly_fetch",
                    metadata={"source": "product_gateway.external_readonly"},
                )
            ],
        ),
        metadata={
            "source": "product_gateway.external_readonly",
            "config_context": {"profile": "dev"},
            "config_profile": "dev",
        },
    )

    summary = project_product_gateway_response_summary(
        response,
        product_gateway_response_ref=(
            "product-gateway-response://external-readonly/request-1"
        ),
    )
    validated = validate_product_gateway_response_summary(summary)

    assert validated.payload_version == PRODUCT_GATEWAY_RESPONSE_SUMMARY_VERSION
    assert summary["payload_type"] == "product_gateway_response_summary"
    assert summary["entry_kind"] == "external_readonly_fetch"
    assert summary["status"] == "success"
    assert summary["product_gateway_response_ref"] == (
        "product-gateway-response://external-readonly/request-1"
    )
    assert summary["evidence_refs"][0]["ref"] == (
        "evidence://external-readonly/request-1"
    )
    assert summary["readonly"] is True
    assert summary["summary_only"] is True
    assert summary["refs_only"] is True
    assert summary["candidate_only"] is True
    assert summary["execution_enabled"] is False
    assert summary["runtime_permission_granted"] is False
    assert summary["llm_call_enabled"] is False
    assert summary["tool_execution_enabled"] is False
    assert summary["action_execution_enabled"] is False
    assert summary["gateway_enabled"] is False
    assert summary["metadata"] == {
        "source": "product_gateway.response_summary_projection",
        "product_gateway_response_source": "product_gateway.external_readonly",
    }


def test_response_summary_projection_merges_refs_and_preserves_order() -> None:
    shared_evidence_ref = ProductGatewayRef(
        ref="evidence://shared",
        kind="sanitized_evidence",
        purpose="task_workflow_execution",
        metadata={"source": "output_refs"},
    )
    response = ProductGatewayResponse(
        request_id="twf/request-1",
        entry_kind=ProductGatewayEntryKind.TASK_WORKFLOW_EXECUTION,
        status=ProductGatewayStatus.SUCCESS,
        output_refs=ProductGatewayOutputRefs(
            governance_summary_ref="governance-summary://output",
            evidence_refs=[shared_evidence_ref],
            audit_refs=[
                ProductGatewayRef(ref="audit://output", kind="audit"),
            ],
            agent_advice_refs=[
                ProductGatewayRef(ref="agent-advice://shared", kind="agent_advice"),
            ],
            tool_audit_refs=[
                ProductGatewayRef(ref="tool-audit://output", kind="tool_audit"),
            ],
            additional_refs=[
                ProductGatewayRef(
                    ref="external-readonly-evidence-observation://output",
                    kind="external_readonly_evidence_observation",
                    purpose="external_readonly_readonly_public_refs",
                    metadata={
                        "source": "product_gateway.external_readonly_refs_projection"
                    },
                )
            ],
        ),
        evidence_refs=[
            shared_evidence_ref,
            ProductGatewayRef(
                ref="evidence://top-level",
                kind="sanitized_evidence",
                purpose="task_workflow_execution",
            ),
        ],
        audit_refs=[
            ProductGatewayRef(ref="audit://top-level", kind="audit"),
        ],
        agent_advice_refs=[
            ProductGatewayRef(ref="agent-advice://shared", kind="agent_advice"),
            ProductGatewayRef(ref="agent-advice://top-level", kind="agent_advice"),
        ],
        tool_audit_refs=[
            ProductGatewayRef(ref="tool-audit://top-level", kind="tool_audit"),
        ],
        metadata={"source": "product_gateway.cli_surface"},
    )

    summary = project_product_gateway_response_summary(response)

    assert summary["governance_summary_ref"] == "governance-summary://output"
    assert [ref["ref"] for ref in summary["evidence_refs"]] == [
        "evidence://shared",
        "evidence://top-level",
    ]
    assert [ref["ref"] for ref in summary["audit_refs"]] == [
        "audit://output",
        "audit://top-level",
    ]
    assert [ref["ref"] for ref in summary["agent_advice_refs"]] == [
        "agent-advice://shared",
        "agent-advice://top-level",
    ]
    assert [ref["ref"] for ref in summary["tool_audit_refs"]] == [
        "tool-audit://output",
        "tool-audit://top-level",
    ]
    assert [ref["ref"] for ref in summary["additional_refs"]] == [
        "external-readonly-evidence-observation://output"
    ]
    assert summary["additional_refs"][0]["kind"] == (
        "external_readonly_evidence_observation"
    )
    validate_product_gateway_response_summary(summary)


def test_response_summary_projection_prefers_response_governance_ref() -> None:
    response = ProductGatewayResponse(
        request_id="twf/request-2",
        entry_kind=ProductGatewayEntryKind.TASK_WORKFLOW_EXECUTION,
        status=ProductGatewayStatus.SUCCESS,
        output_refs=ProductGatewayOutputRefs(
            governance_summary_ref="governance-summary://output"
        ),
        governance_summary_ref="governance-summary://response",
    )

    summary = project_product_gateway_response_summary(response)

    assert summary["governance_summary_ref"] == "governance-summary://response"


def test_response_summary_projection_source_has_no_execution_imports() -> None:
    source = (
        PRODUCT_GATEWAY_SOURCE_ROOT / "response_summary_projection.py"
    ).read_text(encoding="utf-8")
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:runtime_container|composition|adk_adapter|google\.adk|litellm)\b",
        re.MULTILINE,
    )

    assert forbidden_imports.search(source) is None
    assert "open(" not in source
    assert "requests" not in source
    assert "httpx" not in source
