from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from schemas.product_gateway_response_summary import (
    PRODUCT_GATEWAY_RESPONSE_SUMMARY_VERSION,
    ProductGatewayResponseSummarySchema,
    validate_product_gateway_response_summary,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_SOURCE_ROOT = REPO_ROOT / "packages" / "schemas" / "src" / "schemas"


def test_product_gateway_response_summary_accepts_minimal_public_shape() -> None:
    summary = validate_product_gateway_response_summary(_summary())

    assert isinstance(summary, ProductGatewayResponseSummarySchema)
    assert summary.product == "product_gateway"
    assert summary.payload_type == "product_gateway_response_summary"
    assert summary.payload_version == PRODUCT_GATEWAY_RESPONSE_SUMMARY_VERSION
    assert summary.request_id == "request-1"
    assert summary.entry_kind == "agent_shell"
    assert summary.status == "success"
    assert summary.evidence_refs[0].ref == "evidence://request-1"
    assert summary.additional_refs[0].ref == (
        "external-readonly-evidence-observation://observation-1"
    )
    assert summary.readonly is True
    assert summary.summary_only is True
    assert summary.refs_only is True
    assert summary.candidate_only is True
    assert summary.execution_enabled is False
    assert summary.follow_up is False
    assert summary.temporary_follow_up is True
    assert summary.durable_session is False
    assert summary.memory_enabled is False


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
        "external_readonly_refs",
        "external_readonly_ask",
    ],
)
def test_product_gateway_response_summary_accepts_frozen_entry_kinds(
    entry_kind: str,
) -> None:
    summary = validate_product_gateway_response_summary(_summary(entry_kind=entry_kind))

    assert summary.entry_kind == entry_kind


@pytest.mark.parametrize("status", ["success", "blocked", "failed", "skipped"])
def test_product_gateway_response_summary_accepts_frozen_statuses(status: str) -> None:
    summary = validate_product_gateway_response_summary(_summary(status=status))

    assert summary.status == status


def test_product_gateway_response_summary_rejects_blocked_without_reasons() -> None:
    summary = _summary(status="blocked")
    summary["blocking_reasons"] = []

    with pytest.raises(ValidationError):
        validate_product_gateway_response_summary(summary)


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
def test_product_gateway_response_summary_rejects_invalid_header(
    field: str,
    value: str,
) -> None:
    summary = _summary()
    summary[field] = value

    with pytest.raises(ValidationError):
        validate_product_gateway_response_summary(summary)


def test_product_gateway_response_summary_rejects_raw_and_runtime_payloads() -> None:
    metadata_summary = _summary()
    metadata_summary["metadata"] = {"raw_response": "must not cross boundary"}
    with pytest.raises(ValidationError):
        validate_product_gateway_response_summary(metadata_summary)

    ref_summary = _summary()
    ref_summary["evidence_refs"] = [
        {
            "ref": "evidence://raw",
            "kind": "evidence",
            "metadata": {"response_text": "raw provider output"},
        }
    ]
    with pytest.raises(ValidationError):
        validate_product_gateway_response_summary(ref_summary)

    additional_ref_summary = _summary()
    additional_ref_summary["additional_refs"] = [
        {
            "ref": "external-readonly-evidence-observation://raw",
            "kind": "external_readonly_evidence_observation",
            "metadata": {"config_context": {"token": "config-secret"}},
        }
    ]
    with pytest.raises(ValidationError):
        validate_product_gateway_response_summary(additional_ref_summary)

    runtime_summary = _summary()
    runtime_summary["metadata"] = {"object_module": "runtime_container.registry"}
    with pytest.raises(ValidationError):
        validate_product_gateway_response_summary(runtime_summary)


def test_product_gateway_response_summary_rejects_execution_flags() -> None:
    summary = _summary()
    summary["execution_enabled"] = True

    with pytest.raises(ValidationError):
        validate_product_gateway_response_summary(summary)


def test_product_gateway_response_summary_rejects_durable_follow_up_state() -> None:
    summary = _summary(entry_kind="external_readonly_ask")
    summary["follow_up"] = True
    summary["follow_up_turn_index"] = 1
    summary["follow_up_seed_ref"] = "evidence-summary-answer-follow-up://seed-681"
    summary["durable_session"] = True

    with pytest.raises(ValidationError):
        validate_product_gateway_response_summary(summary)


def test_product_gateway_response_summary_schema_has_no_execution_layer_imports() -> None:
    source = (SCHEMA_SOURCE_ROOT / "product_gateway_response_summary.py").read_text(
        encoding="utf-8"
    )
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:product_gateway|cognition_agent|cognition_governance|config_contexts|"
        r"runtime_container|composition|adk_adapter|google\.adk|litellm)\b",
        re.MULTILINE,
    )

    assert forbidden_imports.search(source) is None
    assert "ProductGatewayResponse(" not in source


def _summary(
    *,
    entry_kind: str = "agent_shell",
    status: str = "success",
) -> dict[str, object]:
    return {
        "product": "product_gateway",
        "payload_type": "product_gateway_response_summary",
        "payload_version": PRODUCT_GATEWAY_RESPONSE_SUMMARY_VERSION,
        "request_id": "request-1",
        "entry_kind": entry_kind,
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
        "warnings": ["product_gateway_warning"] if status == "skipped" else [],
        "metadata": {"source": "product_gateway.agent_shell"},
    }
