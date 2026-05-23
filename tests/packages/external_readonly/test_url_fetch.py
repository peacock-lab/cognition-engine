from __future__ import annotations

import hashlib
from pathlib import Path

from external_readonly import (
    ExternalReadonlyHttpResponse,
    ExternalReadonlyNetworkGateView,
    ExternalReadonlyUrlFetchRequest,
    external_readonly_url_fetch_result_status_dict,
    run_external_readonly_url_fetch,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
EXTERNAL_READONLY_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "external_readonly" / "src" / "external_readonly"
)
RUNTIME_CONTAINER_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "runtime_container" / "src" / "runtime_container"
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


def test_url_fetch_builds_sanitized_evidence_with_fake_transport() -> None:
    body = (
        "<html><head><script>RAW_JS_MARKER_466()</script></head>"
        "<body><h1>Example Reference</h1>"
        "<p>Visible reference text for the model.</p></body></html>"
    )
    transport = FakeTransport(
        _response(
            body_text=body,
            bytes_read=len(body.encode("utf-8")),
            content_type="text/html; charset=utf-8",
        )
    )

    result = run_external_readonly_url_fetch(
        gate=_gate(),
        request=_request(source_title="Example Reference"),
        transport=transport,
    )
    status = external_readonly_url_fetch_result_status_dict(result)

    assert result.status == "completed"
    assert result.allowed_for_model_context is True
    assert result.transport_called is True
    assert result.runtime_fetch_performed is True
    assert result.external_network_call_performed is False
    assert len(transport.calls) == 1
    assert result.envelope is not None
    item = result.envelope.model_context_items[0]
    assert item["sanitized_excerpt"] == (
        "Example Reference Visible reference text for the model."
    )
    assert item["content_hash"] == _hash(item["sanitized_excerpt"])
    assert status["envelope"]["model_context_items"][0] == item
    assert "RAW_JS_MARKER_466" not in str(status)
    assert "<html>" not in str(status)
    assert "set-cookie" not in str(status).lower()


def test_url_fetch_blocks_without_open_gate_before_transport() -> None:
    transport = FakeTransport(_response())

    result = run_external_readonly_url_fetch(
        gate=_gate(status="blocked", network_gate_open=False),
        request=_request(),
        transport=transport,
    )

    assert result.status == "blocked"
    assert result.transport_called is False
    assert result.runtime_fetch_performed is False
    assert result.envelope is None
    assert transport.calls == []
    assert "network_gate_not_passed" in result.blocking_reasons
    assert "network_gate_not_open" in result.blocking_reasons


def test_url_fetch_blocks_private_url_before_transport() -> None:
    transport = FakeTransport(_response())

    result = run_external_readonly_url_fetch(
        gate=_gate(),
        request=_request(source_url="https://127.0.0.1/admin"),
        transport=transport,
    )

    assert result.status == "blocked"
    assert result.transport_called is False
    assert result.envelope is None
    assert transport.calls == []
    assert "source_url_not_external_https" in result.blocking_reasons


def test_url_fetch_blocks_response_cookie_header_without_leaking_header_value() -> None:
    transport = FakeTransport(
        _response(
            response_headers={
                "content-type": "text/html",
                "set-cookie": "session=RAW_COOKIE_MARKER_466",
            }
        )
    )

    result = run_external_readonly_url_fetch(
        gate=_gate(),
        request=_request(),
        transport=transport,
    )
    status = external_readonly_url_fetch_result_status_dict(result)

    assert result.status == "blocked"
    assert result.transport_called is True
    assert result.envelope is None
    assert "response_headers_forbidden" in result.blocking_reasons
    assert "RAW_COOKIE_MARKER_466" not in str(status)
    assert status["metadata"]["response_headers_included"] is False
    assert status["metadata"]["response_cookie_header_present"] is True


def test_url_fetch_blocks_non_success_and_too_large_response() -> None:
    transport = FakeTransport(
        _response(
            status_code=500,
            body_text="A" * 6,
            bytes_read=6,
            content_type="text/plain",
        )
    )

    result = run_external_readonly_url_fetch(
        gate=_gate(),
        request=_request(max_bytes=5),
        transport=transport,
    )

    assert result.status == "blocked"
    assert result.transport_called is True
    assert result.envelope is None
    assert "http_status_not_success" in result.blocking_reasons
    assert "response_bytes_exceeds_limit" in result.blocking_reasons


def test_url_fetch_source_keeps_external_readonly_boundary_and_no_live_dependencies() -> None:
    source = (
        EXTERNAL_READONLY_SOURCE_ROOT / "url_fetch.py"
    ).read_text(encoding="utf-8")

    assert "method=\"GET\"" in source
    assert "build_opener(_NoRedirectHandler)" in source
    assert "method=\"POST\"" not in source
    assert "runtime_container" not in source
    assert "cognition_operation_flows" not in source
    assert "product_gateway" not in source
    assert "cognition_cli" not in source
    assert "google.adk" not in source
    assert "litellm" not in source
    assert "adk_adapter" not in source


def test_runtime_container_external_readonly_facade_is_removed() -> None:
    assert not (RUNTIME_CONTAINER_SOURCE_ROOT / "external_readonly").exists()


def _gate(**overrides: object) -> ExternalReadonlyNetworkGateView:
    kwargs = {
        "request_ref": "external-readonly-request://url-context/466",
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
        "request_ref": "external-readonly-request://url-context/466",
        "source_url": "https://example.com/reference",
        "envelope_ref": "evidence://external-readonly/envelope/url-fetch-466",
        "evidence_ref": "evidence://external-readonly/item/url-fetch-466",
        "controlled_output_ref": "outputs/external-readonly/url-fetch-466.json",
    }
    kwargs.update(overrides)
    return ExternalReadonlyUrlFetchRequest(**kwargs)


def _response(**overrides: object) -> ExternalReadonlyHttpResponse:
    kwargs = {
        "final_url": "https://example.com/reference",
        "status_code": 200,
        "body_text": "Visible reference text for the model.",
        "bytes_read": len("Visible reference text for the model.".encode("utf-8")),
        "retrieved_at": "2026-05-16T10:00:00+00:00",
        "content_type": "text/plain",
        "response_headers": {"content-type": "text/plain"},
        "external_network_call_performed": False,
    }
    kwargs.update(overrides)
    return ExternalReadonlyHttpResponse(**kwargs)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
