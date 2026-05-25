from __future__ import annotations

import tomllib
from pathlib import Path

from external_readonly import (
    ExternalReadonlyHttpResponse,
    ExternalReadonlyNetworkGateView,
    ExternalReadonlyUrlFetchRequest,
    external_readonly_url_fetch_result_status_dict,
    run_external_readonly_url_fetch,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "packages" / "external_readonly"


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


def test_external_readonly_package_metadata_is_independent_candidate() -> None:
    pyproject = tomllib.loads(
        (PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )

    assert pyproject["project"]["name"] == "cognition-system-external-readonly"
    assert pyproject["project"]["dependencies"] == [
        "cognition-system-schemas==0.8.1"
    ]
    assert pyproject["tool"]["uv"]["sources"] == {
        "cognition-system-schemas": {"workspace": True}
    }
    assert pyproject["tool"]["external_readonly"]["provider_neutral"] is True
    assert pyproject["tool"]["external_readonly"]["network_default_closed"] is True
    assert pyproject["tool"]["external_readonly"]["uploads_content"] is False
    assert pyproject["tool"]["external_readonly"]["third_party_adapter_slot_reserved"] is True


def test_external_readonly_core_fetches_through_injected_transport_only() -> None:
    body = "<html><body><h1>Reference</h1><p>Visible facts.</p></body></html>"
    transport = FakeTransport(
        ExternalReadonlyHttpResponse(
            final_url="https://example.com/reference",
            status_code=200,
            body_text=body,
            bytes_read=len(body.encode("utf-8")),
            retrieved_at="2026-05-16T10:00:00+00:00",
            content_type="text/html",
            response_headers={"content-type": "text/html"},
            external_network_call_performed=False,
        )
    )

    result = run_external_readonly_url_fetch(
        gate=_gate(),
        request=_request(),
        transport=transport,
    )
    status = external_readonly_url_fetch_result_status_dict(result)

    assert result.status == "completed"
    assert result.runtime_fetch_performed is True
    assert result.external_network_call_performed is False
    assert len(transport.calls) == 1
    assert result.envelope is not None
    assert result.envelope.model_context_items[0]["sanitized_excerpt"] == (
        "Reference Visible facts."
    )
    assert status["metadata"]["runtime_service"] == "external_readonly.url_fetch"
    assert "runtime_container_external_readonly" not in str(status)


def test_external_readonly_core_source_has_no_channel_or_runtime_dependencies() -> None:
    source = (PACKAGE_ROOT / "src" / "external_readonly" / "url_fetch.py").read_text(
        encoding="utf-8"
    )

    assert "runtime_container" not in source
    assert "product_gateway" not in source
    assert "cognition_cli" not in source
    assert "cognition_operation_flows" not in source
    assert "google.adk" not in source
    assert "litellm" not in source
    assert "adk_adapter" not in source


def test_external_readonly_package_dependencies_stay_contract_only() -> None:
    pyproject = tomllib.loads(
        (PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    dependencies = " ".join(pyproject["project"]["dependencies"])

    assert dependencies == "cognition-system-schemas==0.8.1"
    assert "behavior-contracts" not in dependencies
    assert "contract-core" not in dependencies
    assert "runtime-container" not in dependencies
    assert "product-gateway" not in dependencies
    assert "composition" not in dependencies
    assert "observability-hub" not in dependencies
    assert "cli" not in dependencies


def _gate(**overrides: object) -> ExternalReadonlyNetworkGateView:
    kwargs = {
        "request_ref": "external-readonly-request://url-context/476",
        "status": "passed",
        "network_gate_open": True,
        "allowed_for_network_request": True,
        "operator_approval_satisfied": True,
        "controlled_output_satisfied": True,
        "tool_origin": "url_context",
        "operation_family": "fetch",
        "metadata": {
            "network_gate_ref_present": True,
            "approval_ref_present": True,
        },
    }
    kwargs.update(overrides)
    return ExternalReadonlyNetworkGateView(**kwargs)


def _request(**overrides: object) -> ExternalReadonlyUrlFetchRequest:
    kwargs = {
        "request_ref": "external-readonly-request://url-context/476",
        "source_url": "https://example.com/reference",
        "envelope_ref": "evidence://external-readonly/envelope/url-fetch-476",
        "evidence_ref": "evidence://external-readonly/item/url-fetch-476",
        "controlled_output_ref": "outputs/external-readonly/url-fetch-476.json",
    }
    kwargs.update(overrides)
    return ExternalReadonlyUrlFetchRequest(**kwargs)
