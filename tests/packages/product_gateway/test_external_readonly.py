from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from product_gateway.contracts import (
    ProductGatewayEntryKind,
    ProductGatewayExecutionMode,
    ProductGatewayResponse,
    ProductGatewayStatus,
)
from product_gateway.external_readonly import (
    ExternalReadonlyFetchGatewayInput,
    build_external_readonly_fetch_gateway_projection,
    build_external_readonly_fetch_gateway_request,
    execute_external_readonly_fetch_gateway_request,
    run_external_readonly_fetch_gateway_request,
)
from product_gateway.response_summary_projection import (
    project_product_gateway_response_summary,
)
from schemas.product_gateway_response_summary import (
    validate_product_gateway_response_summary,
)
from external_readonly import (
    ExternalReadonlyHttpResponse,
    ExternalReadonlyUrlFetchRequest,
)


PRODUCT_GATEWAY_ROOT = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "product_gateway"
    / "src"
    / "product_gateway"
)


class FakeTransport:
    def __init__(self, response: ExternalReadonlyHttpResponse) -> None:
        self.response = response
        self.calls: list[ExternalReadonlyUrlFetchRequest] = []

    def __call__(
        self,
        request: ExternalReadonlyUrlFetchRequest,
    ) -> ExternalReadonlyHttpResponse:
        self.calls.append(request)
        return self.response


def test_external_readonly_fetch_gateway_request_defaults_to_preflight() -> None:
    gateway_input = _gateway_input(allow_runtime_fetch=False)

    request = build_external_readonly_fetch_gateway_request(gateway_input)
    response = run_external_readonly_fetch_gateway_request(gateway_input)

    assert request.entry_kind is ProductGatewayEntryKind.EXTERNAL_READONLY_FETCH
    assert request.execution_mode is ProductGatewayExecutionMode.PREFLIGHT_ONLY
    assert request.input_payload["source_url"] == "https://example.com/reference"
    assert request.input_payload["network_gate_present"] is True
    assert request.metadata["backend_api"] == "external_readonly"
    assert response.status is ProductGatewayStatus.BLOCKED
    assert response.exit_code == 2
    assert "external_readonly_runtime_fetch_not_allowed" in response.blocking_reasons
    assert response.metadata["runtime_fetch_performed"] is False
    assert response.metadata["external_network_call_performed"] is False


def test_external_readonly_fetch_gateway_executes_fake_transport() -> None:
    transport = FakeTransport(
        _response(
            body_text=(
                "<html><script>RAW_EXTERNAL_READONLY_467()</script>"
                "<body>Visible source facts.</body></html>"
            ),
            content_type="text/html",
        )
    )

    execution = execute_external_readonly_fetch_gateway_request(
        _gateway_input(allow_runtime_fetch=True),
        transport=transport,
    )
    response = execution.product_response

    assert isinstance(response, ProductGatewayResponse)
    assert response.status is ProductGatewayStatus.SUCCESS
    assert response.exit_code == 0
    assert response.entry_kind is ProductGatewayEntryKind.EXTERNAL_READONLY_FETCH
    assert execution.runtime_result is not None
    assert execution.runtime_result.status == "completed"
    assert execution.runtime_result.external_network_call_performed is False
    assert len(transport.calls) == 1
    assert [(ref.ref, ref.kind, ref.purpose) for ref in response.evidence_refs] == [
        (
            "evidence://external-readonly/item/product-gateway-467",
            "external_readonly_evidence",
            "external_readonly_fetch",
        )
    ]
    assert response.output_refs.evidence_refs == response.evidence_refs
    assert response.metadata["runtime_fetch_performed"] is True
    assert response.metadata["transport_called"] is True
    assert response.metadata["external_network_call_performed"] is False
    assert "RAW_EXTERNAL_READONLY_467" not in str(response.model_dump())

    summary = _assert_projected_response_summary(response)
    assert summary["entry_kind"] == "external_readonly_fetch"
    assert summary["status"] == "success"
    assert [ref["ref"] for ref in summary["evidence_refs"]] == [
        "evidence://external-readonly/item/product-gateway-467"
    ]
    assert summary["blocking_reasons"] == []


def test_external_readonly_fetch_requires_transport_unless_live_transport_requested() -> None:
    execution = execute_external_readonly_fetch_gateway_request(
        _gateway_input(allow_runtime_fetch=True)
    )

    assert execution.runtime_result is None
    assert execution.product_response.status is ProductGatewayStatus.BLOCKED
    assert "external_readonly_transport_required" in (
        execution.product_response.blocking_reasons
    )
    assert execution.product_response.metadata["transport_called"] is False

    summary = _assert_projected_response_summary(execution.product_response)
    assert summary["entry_kind"] == "external_readonly_fetch"
    assert summary["status"] == "blocked"
    assert "external_readonly_transport_required" in summary["blocking_reasons"]
    assert summary["evidence_refs"] == []


def test_external_readonly_fetch_closed_gate_blocks_before_transport_call() -> None:
    transport = FakeTransport(_response())

    execution = execute_external_readonly_fetch_gateway_request(
        _gateway_input(
            allow_runtime_fetch=True,
            network_gate={
                **_passed_gate(),
                "status": "blocked",
                "network_gate_open": False,
            },
        ),
        transport=transport,
    )

    assert execution.runtime_result is not None
    assert execution.runtime_result.status == "blocked"
    assert execution.product_response.status is ProductGatewayStatus.BLOCKED
    assert "network_gate_not_passed" in execution.product_response.blocking_reasons
    assert "network_gate_not_open" in execution.product_response.blocking_reasons
    assert transport.calls == []


def test_external_readonly_fetch_live_transport_remains_explicit() -> None:
    projection = build_external_readonly_fetch_gateway_projection(
        _gateway_input(allow_runtime_fetch=True, use_live_transport=True)
    )
    blocked = run_external_readonly_fetch_gateway_request(
        _gateway_input(allow_runtime_fetch=False, use_live_transport=True)
    )

    assert projection.execution_mode == "smoke"
    assert projection.use_live_transport is True
    assert projection.transport_required is False
    assert blocked.status is ProductGatewayStatus.BLOCKED
    assert "external_readonly_runtime_fetch_not_allowed" in blocked.blocking_reasons
    assert "live_transport_requires_runtime_fetch_allowance" in blocked.blocking_reasons
    assert blocked.metadata["external_network_call_performed"] is False


@pytest.mark.parametrize(
    "raw_payload",
    [
        {"metadata": {"raw_response": "must not pass"}},
        {"metadata": {"response_headers": {"set-cookie": "secret"}}},
        {"network_gate": {"metadata": {"token": "secret"}}},
        {"metadata": {"object_module": "google.adk.tools"}},
    ],
)
def test_external_readonly_fetch_rejects_raw_payloads(
    raw_payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        build_external_readonly_fetch_gateway_request(
            _gateway_input(**raw_payload)
        )


def test_external_readonly_module_exports_run_request() -> None:
    from product_gateway.external_readonly import __all__ as exported_names

    assert "run_external_readonly_fetch_gateway_request" in exported_names
    assert (
        run_external_readonly_fetch_gateway_request.__module__
        == "product_gateway.external_readonly"
    )


def test_external_readonly_source_keeps_product_gateway_boundary() -> None:
    source = (PRODUCT_GATEWAY_ROOT / "external_readonly.py").read_text(
        encoding="utf-8"
    )

    assert "from external_readonly import" in source
    assert "from runtime_container" not in source
    assert "runtime_container.external_readonly" not in source
    assert "cognition_operation_flows" not in source
    assert "product_gateway.cli" not in source
    assert "from google.adk" not in source
    assert "import google.adk" not in source
    assert "from litellm" not in source
    assert "import litellm" not in source
    assert "from adk_adapter" not in source
    assert "import adk_adapter" not in source
    assert "raw_response_included" in source


def _assert_projected_response_summary(
    response: ProductGatewayResponse,
) -> dict[str, object]:
    summary = project_product_gateway_response_summary(response)
    validated = validate_product_gateway_response_summary(summary)

    assert validated.model_dump(mode="python") == summary
    assert summary["payload_type"] == "product_gateway_response_summary"
    assert summary["payload_version"] == "product_gateway_response_summary_v1"
    assert summary["status"] == response.status.value
    assert summary["exit_code"] == response.exit_code
    assert summary["product_gateway_response_ref"] is None
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
        "product_gateway_response_source": response.metadata["source"],
    }
    summary_text = repr(summary)
    assert "RAW_EXTERNAL_READONLY_467" not in summary_text
    assert "raw_response" not in summary_text
    assert "config_context" not in summary_text
    return summary


def _gateway_input(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "request_id": "external-readonly-request://product-gateway/467",
        "source_url": "https://example.com/reference",
        "envelope_ref": "evidence://external-readonly/envelope/product-gateway-467",
        "evidence_ref": "evidence://external-readonly/item/product-gateway-467",
        "network_gate": _passed_gate(),
        "source_title": "Example Reference",
        "controlled_output_ref": "outputs/external-readonly/product-gateway-467.json",
        "operator_approved": True,
        "approval_ref": "approval://external-readonly/product-gateway-467",
        "audit_ref": "audit://external-readonly/product-gateway-467",
        "sanitized_evidence_ref": "evidence://external-readonly/product-gateway-467",
        "governance_summary_ref": "summary://external-readonly/product-gateway-467",
        "runtime_fetch_approval_ref": (
            "approval://external-readonly/runtime-fetch/product-gateway-467"
        ),
    }
    kwargs.update(overrides)
    return kwargs


def _passed_gate() -> dict[str, object]:
    return {
        "request_ref": "external-readonly-request://product-gateway/467",
        "status": "passed",
        "network_gate_open": True,
        "allowed_for_network_request": True,
        "operator_approval_satisfied": True,
        "controlled_output_satisfied": True,
        "tool_origin": "url_context",
        "operation_family": "fetch",
        "external_network_call_performed": False,
        "tool_execution_performed": False,
        "metadata": {
            "network_gate_ref_present": True,
            "approval_ref_present": True,
            "audit_ref_present": True,
        },
    }


def _response(**overrides: object) -> ExternalReadonlyHttpResponse:
    kwargs = {
        "final_url": "https://example.com/reference",
        "status_code": 200,
        "body_text": "Visible source facts.",
        "bytes_read": len("Visible source facts.".encode("utf-8")),
        "retrieved_at": "2026-05-16T10:00:00+00:00",
        "content_type": "text/plain",
        "response_headers": {"content-type": "text/plain"},
        "external_network_call_performed": False,
    }
    kwargs.update(overrides)
    return ExternalReadonlyHttpResponse(**kwargs)
