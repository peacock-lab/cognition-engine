from __future__ import annotations

import pytest
from pydantic import ValidationError

import product_gateway.contracts as contracts_module
from product_gateway.contracts import (
    ProductGatewayEntryKind,
    ProductGatewayExecutionMode,
    ProductGatewayInputRefs,
    ProductGatewayLiveOptions,
    ProductGatewayOperatorApprovalRef,
    ProductGatewayOutputRefs,
    ProductGatewayRef,
    ProductGatewayRequest,
    ProductGatewayResponse,
    ProductGatewayStatus,
)
from schemas.product_gateway_response_summary import (
    PRODUCT_GATEWAY_RESPONSE_SUMMARY_ENTRY_KINDS,
)


def test_product_gateway_contracts_public_surface_is_explicit() -> None:
    assert tuple(contracts_module.__all__) == (
        "ProductGatewayEntryKind",
        "ProductGatewayExecutionMode",
        "ProductGatewayInputRefs",
        "ProductGatewayLiveOptions",
        "ProductGatewayOperatorApprovalRef",
        "ProductGatewayOutputRefs",
        "ProductGatewayRef",
        "ProductGatewayRequest",
        "ProductGatewayResponse",
        "ProductGatewayStatus",
    )
    assert "_raise_if_raw_payload_found" not in contracts_module.__all__
    assert "_walk" not in contracts_module.__all__
    assert "_is_raw_payload" not in contracts_module.__all__
    assert "ProductGatewayContractBase" not in contracts_module.__all__
    assert "FORBIDDEN_PRODUCT_GATEWAY_KEYS" not in contracts_module.__all__
    assert "FORBIDDEN_PRODUCT_GATEWAY_MODULE_PREFIXES" not in contracts_module.__all__


def test_product_gateway_response_summary_entry_kinds_cover_product_entries() -> None:
    assert PRODUCT_GATEWAY_RESPONSE_SUMMARY_ENTRY_KINDS == frozenset(
        item.value for item in ProductGatewayEntryKind
    )


def test_product_gateway_request_accepts_sanitized_product_input() -> None:
    request = ProductGatewayRequest(
        request_id="request-1",
        entry_kind=ProductGatewayEntryKind.COGNITION_RUN,
        execution_mode=ProductGatewayExecutionMode.NO_LIVE,
        input_payload={
            "input_summary": "用户请求摘要",
            "input_kind": "task_review",
        },
        input_refs=ProductGatewayInputRefs(
            operator_approval_ref="operator-approval://request-1",
            audit_ref="audit://request-1",
        ),
        operator_approval=ProductGatewayOperatorApprovalRef(
            approved=True,
            approval_ref="operator-approval://request-1",
            decision_source="explicit_cli",
        ),
    )

    assert request.input_payload["input_kind"] == "task_review"
    assert request.operator_approval.approved is True


@pytest.mark.parametrize(
    "raw_payload",
    [
        {"prompt": "raw prompt"},
        {"messages": [{"role": "user", "content": "raw"}]},
        {"raw_user_message": "raw"},
        {"user_message": "raw"},
        {"raw_api_payload": {"message": "raw"}},
        {"raw_tool_input": {"argument": "raw"}},
        {"nested": {"object_module": "google.adk.tools.tool_context"}},
    ],
)
def test_product_gateway_request_rejects_raw_input_payloads(
    raw_payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        ProductGatewayRequest(
            request_id="request-raw",
            entry_kind=ProductGatewayEntryKind.TOOL_SMOKE,
            execution_mode=ProductGatewayExecutionMode.SMOKE,
            input_payload=raw_payload,
        )


def test_product_gateway_live_options_require_explicit_identity() -> None:
    with pytest.raises(ValidationError):
        ProductGatewayLiveOptions(request_live_llm=True)

    with pytest.raises(ValidationError):
        ProductGatewayLiveOptions(
            request_live_llm=True,
            allow_live_llm=True,
            override_source="explicit_smoke",
        )

    live_options = ProductGatewayLiveOptions(
        request_live_llm=True,
        allow_live_llm=True,
        live_llm_approval_ref="operator-approval://live-1",
        override_source="explicit_smoke",
    )

    assert live_options.allow_live_llm is True


def test_product_gateway_response_accepts_sanitized_refs() -> None:
    response = ProductGatewayResponse(
        request_id="request-1",
        entry_kind=ProductGatewayEntryKind.TOOL_SMOKE,
        status=ProductGatewayStatus.SUCCESS,
        output_refs=ProductGatewayOutputRefs(
            output_ref="product-output://request-1",
            evidence_refs=[
                ProductGatewayRef(
                    ref="evidence://request-1",
                    kind="sanitized_evidence",
                    purpose="tool_smoke",
                )
            ],
        ),
        governance_summary_ref="governance-summary://request-1",
        tool_audit_refs=[
            ProductGatewayRef(
                ref="tool-audit://request-1",
                kind="tool_audit",
            )
        ],
    )

    assert response.status is ProductGatewayStatus.SUCCESS
    assert response.output_refs.evidence_refs[0].kind == "sanitized_evidence"


def test_product_gateway_response_rejects_raw_metadata_and_blocked_without_reason() -> None:
    with pytest.raises(ValidationError):
        ProductGatewayResponse(
            request_id="response-raw",
            entry_kind=ProductGatewayEntryKind.AGENT_SHELL,
            status=ProductGatewayStatus.FAILED,
            metadata={"raw_response": "raw"},
        )

    with pytest.raises(ValidationError):
        ProductGatewayResponse(
            request_id="response-blocked",
            entry_kind=ProductGatewayEntryKind.CONTROLLED_LIVE,
            status=ProductGatewayStatus.BLOCKED,
        )


def test_product_gateway_refs_reject_raw_payload_metadata() -> None:
    with pytest.raises(ValidationError):
        ProductGatewayRef(
            ref="bad-ref://1",
            kind="bad",
            metadata={"raw_provider_response": {"content": "raw"}},
        )
