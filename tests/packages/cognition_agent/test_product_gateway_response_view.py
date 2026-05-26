from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from cognition_agent import (
    AGENT_PRODUCT_GATEWAY_RESPONSE_VIEW_SOURCE,
    AGENT_PRODUCT_GATEWAY_RESPONSE_VIEW_VERSION,
    PRODUCT_GATEWAY_RESPONSE_SUMMARY_VERSION,
    AgentProductGatewayResponseViewCandidate,
    build_agent_product_gateway_response_view_candidate,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
COGNITION_AGENT_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "cognition_agent" / "src" / "cognition_agent"
)


def test_builds_product_gateway_response_view_from_minimal_summary() -> None:
    view = build_agent_product_gateway_response_view_candidate(
        candidate_id="agent-product-gateway-response-view-1",
        summary=_summary(),
    )

    assert isinstance(view, AgentProductGatewayResponseViewCandidate)
    assert view.candidate_type == "agent_product_gateway_response_view_candidate"
    assert view.view_version == AGENT_PRODUCT_GATEWAY_RESPONSE_VIEW_VERSION
    assert view.source == AGENT_PRODUCT_GATEWAY_RESPONSE_VIEW_SOURCE
    assert view.product_gateway_request_id == "product-gateway-request-1"
    assert view.product_gateway_entry_kind == "agent_shell"
    assert view.product_gateway_status == "success"
    assert view.product_gateway_exit_code == 0
    assert view.product_gateway_response_ref == (
        "product-gateway-response://product-gateway-request-1"
    )
    assert view.product_gateway_governance_summary_ref == (
        "governance-summary://product-gateway-request-1"
    )
    assert view.product_gateway_ready_for_review is True
    assert view.product_gateway_requires_review is False
    assert view.readonly is True
    assert view.candidate_only is True
    assert view.execution_enabled is False
    assert view.runtime_permission_granted is False
    assert view.agent_runtime_enabled is False
    assert view.llm_call_enabled is False
    assert view.action_execution_enabled is False
    assert view.chat_enabled is False
    assert view.gateway_enabled is False
    assert view.tool_execution_enabled is False
    assert view.metadata["does_not_call_product_gateway"] is True
    assert view.metadata["product_gateway_response_is_not_public_contract"] is True
    assert view.metadata["product_gateway_response_summary_version"] == (
        PRODUCT_GATEWAY_RESPONSE_SUMMARY_VERSION
    )


@pytest.mark.parametrize(
    "entry_kind",
    [
        "cognition_run",
        "controlled_live",
        "agent_shell",
        "tool_smoke",
        "operation_flow_route",
        "operation_flow_execution",
        "external_readonly_fetch",
    ],
)
def test_product_gateway_response_view_accepts_frozen_entry_kinds(
    entry_kind: str,
) -> None:
    view = build_agent_product_gateway_response_view_candidate(
        candidate_id=f"agent-product-gateway-response-view-{entry_kind}",
        summary=_summary(entry_kind=entry_kind),
    )

    assert view.product_gateway_entry_kind == entry_kind


@pytest.mark.parametrize(
    ("status", "expected_ready", "expected_requires_review"),
    [
        ("success", True, False),
        ("blocked", False, True),
        ("failed", False, True),
        ("skipped", True, False),
    ],
)
def test_product_gateway_response_view_statuses(
    status: str,
    expected_ready: bool,
    expected_requires_review: bool,
) -> None:
    view = build_agent_product_gateway_response_view_candidate(
        candidate_id=f"agent-product-gateway-response-view-{status}",
        summary=_summary(status=status),
    )

    assert view.product_gateway_status == status
    assert view.product_gateway_ready_for_review is expected_ready
    assert view.product_gateway_requires_review is expected_requires_review


def test_product_gateway_response_view_carries_refs() -> None:
    view = build_agent_product_gateway_response_view_candidate(
        candidate_id="agent-product-gateway-response-view-refs",
        summary=_summary(),
    )

    assert view.product_gateway_evidence_refs[0].ref == (
        "evidence://product-gateway-evidence-1"
    )
    assert view.product_gateway_evidence_refs[0].kind == "evidence"
    assert view.product_gateway_audit_refs[0].ref == "audit://product-gateway-audit-1"
    assert view.product_gateway_agent_advice_refs[0].ref == (
        "agent-advice://agent-task-advice-1"
    )
    assert view.product_gateway_tool_audit_refs[0].ref == (
        "tool-audit://tool-smoke-1"
    )
    assert "evidence://product-gateway-evidence-1" in view.governance_refs
    assert "tool-audit://tool-smoke-1" in view.governance_refs


def test_product_gateway_response_view_rejects_blocked_without_reasons() -> None:
    summary = _summary(status="blocked")
    summary["blocking_reasons"] = []

    with pytest.raises(ValueError):
        build_agent_product_gateway_response_view_candidate(
            candidate_id="agent-product-gateway-response-view-blocked-invalid",
            summary=summary,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("product", "other"),
        ("payload_type", "other"),
        ("payload_version", "other"),
        ("entry_kind", "other"),
        ("status", "other"),
    ],
)
def test_product_gateway_response_view_rejects_invalid_header(
    field: str,
    value: str,
) -> None:
    summary = _summary()
    summary[field] = value

    with pytest.raises(ValueError):
        build_agent_product_gateway_response_view_candidate(
            candidate_id=f"agent-product-gateway-response-view-invalid-{field}",
            summary=summary,
        )


def test_product_gateway_response_view_rejects_raw_payload_keys() -> None:
    summary = _summary()
    summary["metadata"] = {"raw_response": "must not be stored"}

    with pytest.raises(ValueError):
        build_agent_product_gateway_response_view_candidate(
            candidate_id="agent-product-gateway-response-view-raw-metadata",
            summary=summary,
        )

    ref_summary = _summary()
    ref_summary["evidence_refs"] = [
        {
            "ref": "evidence://raw",
            "kind": "evidence",
            "metadata": {"response_text": "raw provider output"},
        }
    ]
    with pytest.raises(ValueError):
        build_agent_product_gateway_response_view_candidate(
            candidate_id="agent-product-gateway-response-view-raw-ref",
            summary=ref_summary,
        )


def test_product_gateway_response_view_rejects_execution_flags() -> None:
    with pytest.raises(ValidationError):
        AgentProductGatewayResponseViewCandidate(
            candidate_id="agent-product-gateway-response-view-invalid-flags",
            source=AGENT_PRODUCT_GATEWAY_RESPONSE_VIEW_SOURCE,
            summary="Invalid product gateway response view.",
            product_gateway_request_id="product-gateway-request-1",
            product_gateway_entry_kind="agent_shell",
            product_gateway_status="success",
            execution_enabled=True,
        )


def test_product_gateway_response_view_source_has_no_execution_dependencies() -> None:
    source = (
        COGNITION_AGENT_SOURCE_ROOT / "product_gateway_response_view.py"
    ).read_text(encoding="utf-8")
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:product_gateway|adk_adapter|litellm|google\.adk|runtime_container|"
        r"runtime|observability_hub|composition|cognition_governance|subprocess)\b",
        re.MULTILINE,
    )
    forbidden_calls = re.compile(
        r"\b(?:completion|acompletion|service\.invoke|runner\.run|run_async)\s*\("
    )

    assert forbidden_imports.search(source) is None
    assert forbidden_calls.search(source) is None
    assert "import ProductGatewayResponse" not in source


def _summary(
    *,
    entry_kind: str = "agent_shell",
    status: str = "success",
) -> dict[str, object]:
    return {
        "product": "product_gateway",
        "payload_type": "product_gateway_response_summary",
        "payload_version": PRODUCT_GATEWAY_RESPONSE_SUMMARY_VERSION,
        "request_id": "product-gateway-request-1",
        "entry_kind": entry_kind,
        "status": status,
        "exit_code": 0 if status in {"success", "skipped"} else 1,
        "product_gateway_response_ref": (
            "product-gateway-response://product-gateway-request-1"
        ),
        "governance_summary_ref": "governance-summary://product-gateway-request-1",
        "evidence_refs": [
            {
                "ref": "evidence://product-gateway-evidence-1",
                "kind": "evidence",
                "purpose": "review",
                "metadata": {"source": "product_gateway.agent_shell"},
            }
        ],
        "audit_refs": [
            {
                "ref": "audit://product-gateway-audit-1",
                "kind": "audit",
                "purpose": "audit",
                "metadata": {},
            }
        ],
        "agent_advice_refs": [
            {
                "ref": "agent-advice://agent-task-advice-1",
                "kind": "agent_advice",
                "purpose": "review",
                "metadata": {},
            }
        ],
        "tool_audit_refs": [
            {
                "ref": "tool-audit://tool-smoke-1",
                "kind": "tool_audit",
                "purpose": "review",
                "metadata": {},
            }
        ],
        "blocking_reasons": (
            ["product_gateway_blocked"] if status == "blocked" else []
        ),
        "warnings": ["product_gateway_warning"] if status == "skipped" else [],
        "metadata": {"source": "product_gateway.agent_shell"},
    }
