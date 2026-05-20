"""Governed HTTPS GET runner for external read-only URL references."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import html
import ipaddress
import re
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


EXTERNAL_READONLY_EVIDENCE_REF_PREFIX = "evidence://external-readonly/"
EXTERNAL_READONLY_CONTROLLED_OUTPUT_ROOT = "outputs/external-readonly"
EXTERNAL_READONLY_ALLOWED_OPERATIONS = frozenset({"fetch", "read"})
EXTERNAL_READONLY_ALLOWED_CONTENT_TYPES = frozenset(
    {
        "application/json",
        "application/xhtml+xml",
        "application/xml",
        "text/html",
        "text/plain",
        "text/xml",
    }
)
EXTERNAL_READONLY_MAX_BYTES = 50_000
EXTERNAL_READONLY_MAX_EXCERPT_CHARS = 2_000
EXTERNAL_READONLY_MAX_TIMEOUT_SECONDS = 30
EXTERNAL_READONLY_MAX_REDIRECT_LIMIT = 3
EXTERNAL_READONLY_SECRET_KEY_MARKERS = (
    "access_token",
    "api_key",
    "authorization",
    "cookie",
    "credential",
    "password",
    "private_key",
    "secret",
    "service_account_json",
    "session",
    "token",
)
EXTERNAL_READONLY_EXCERPT_FORBIDDEN_MARKERS = (
    "api_key=",
    "authorization:",
    "begin private key",
    "password=",
    "private_key=",
    "secret=",
    "service_account_json",
)
EXTERNAL_READONLY_FORBIDDEN_RESPONSE_HEADERS = frozenset(
    {
        "set-cookie",
        "set-cookie2",
        "www-authenticate",
        "proxy-authenticate",
    }
)


@dataclass(frozen=True)
class ExternalReadonlyNetworkGateView:
    """Minimal gate view consumed by the runtime fetch runner."""

    request_ref: str
    status: str
    network_gate_open: bool
    allowed_for_network_request: bool
    operator_approval_satisfied: bool
    controlled_output_satisfied: bool
    tool_origin: str = "url_context"
    operation_family: str = "fetch"
    external_network_call_performed: bool = False
    tool_execution_performed: bool = False
    blocking_reasons: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExternalReadonlyUrlFetchRequest:
    """Runtime request for one approved external-readonly HTTPS GET."""

    request_ref: str
    source_url: str
    envelope_ref: str
    evidence_ref: str
    citation_index: int = 1
    source_title: str | None = None
    controlled_output_ref: str | None = None
    retrieved_at: str | None = None
    item_type: str = "fetched_excerpt"
    max_bytes: int = 20_000
    max_excerpt_chars: int = EXTERNAL_READONLY_MAX_EXCERPT_CHARS
    timeout_seconds: int = 10
    redirect_limit: int = 0
    raw_url_context_included: bool = False
    writes_files: bool = False
    uploads_content: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExternalReadonlyHttpResponse:
    """Transport response kept at the runtime boundary before sanitization."""

    final_url: str
    status_code: int
    body_text: str
    bytes_read: int
    retrieved_at: str
    content_type: str | None = None
    redirect_count: int = 0
    response_headers: Mapping[str, str] = field(default_factory=dict)
    external_network_call_performed: bool = False
    transport_error_sanitized: str | None = None


class ExternalReadonlyHttpTransport(Protocol):
    """Callable HTTPS GET transport used by the governed runner."""

    def __call__(
        self,
        request: ExternalReadonlyUrlFetchRequest,
    ) -> ExternalReadonlyHttpResponse:
        """Fetch a URL and return raw text to the runtime sanitizer."""


@dataclass(frozen=True)
class ExternalReadonlyEvidenceEnvelope:
    """Sanitized evidence envelope produced by the external-readonly core."""

    envelope_ref: str
    request_ref: str
    status: str
    allowed_for_model_context: bool
    model_context_items: tuple[dict[str, Any], ...]
    evidence_refs: tuple[str, ...]
    source_urls: tuple[str, ...]
    total_excerpt_chars: int
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExternalReadonlyUrlFetchResult:
    """Sanitized URL fetch result without raw network payloads."""

    status: str
    request_ref: str
    source_url: str
    envelope_ref: str
    allowed_for_model_context: bool
    envelope: ExternalReadonlyEvidenceEnvelope | None
    transport_called: bool = False
    runtime_fetch_performed: bool = False
    external_network_call_performed: bool = False
    tool_execution_performed: bool = False
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


def coerce_external_readonly_network_gate_view(
    gate: ExternalReadonlyNetworkGateView | Mapping[str, Any] | object,
) -> ExternalReadonlyNetworkGateView:
    """Coerce a sanitized gate mapping or object into the runtime gate view."""

    if isinstance(gate, ExternalReadonlyNetworkGateView):
        return gate

    def get_value(name: str, default: Any = None) -> Any:
        if isinstance(gate, Mapping):
            return gate.get(name, default)
        return getattr(gate, name, default)

    return ExternalReadonlyNetworkGateView(
        request_ref=str(get_value("request_ref", "")),
        status=str(get_value("status", "")),
        network_gate_open=bool(get_value("network_gate_open", False)),
        allowed_for_network_request=bool(
            get_value("allowed_for_network_request", False)
        ),
        operator_approval_satisfied=bool(
            get_value("operator_approval_satisfied", False)
        ),
        controlled_output_satisfied=bool(
            get_value("controlled_output_satisfied", False)
        ),
        tool_origin=_normalize_token(str(get_value("tool_origin", "url_context"))),
        operation_family=_normalize_token(
            str(get_value("operation_family", "fetch"))
        ),
        external_network_call_performed=bool(
            get_value("external_network_call_performed", False)
        ),
        tool_execution_performed=bool(
            get_value("tool_execution_performed", False)
        ),
        blocking_reasons=tuple(
            str(item) for item in get_value("blocking_reasons", ()) or ()
        ),
        metadata=_coerce_mapping(get_value("metadata", {})),
    )


def run_external_readonly_url_fetch(
    *,
    gate: ExternalReadonlyNetworkGateView | Mapping[str, Any] | object,
    request: ExternalReadonlyUrlFetchRequest,
    transport: ExternalReadonlyHttpTransport | None = None,
) -> ExternalReadonlyUrlFetchResult:
    """Run one gated HTTPS GET and return only sanitized evidence."""

    transport = transport or urllib_external_readonly_https_get_transport
    gate_view = coerce_external_readonly_network_gate_view(gate)
    blocking: list[str] = []
    warnings: list[str] = []
    blocking.extend(_gate_blocking_reasons(gate_view))
    blocking.extend(_request_blocking_reasons(request))
    if gate_view.request_ref != request.request_ref:
        blocking.append("request_ref_mismatch")
    if gate_view.blocking_reasons:
        warnings.append("gate_had_prior_blocking_reasons")

    if blocking:
        return _blocked_result(
            gate=gate_view,
            request=request,
            blocking=blocking,
            warnings=warnings,
            transport_called=False,
            runtime_fetch_performed=False,
            external_network_call_performed=False,
        )

    transport_called = False
    response: ExternalReadonlyHttpResponse | None = None
    try:
        transport_called = True
        response = transport(request)
    except Exception as exc:  # pragma: no cover - exercised through status only
        return _blocked_result(
            gate=gate_view,
            request=request,
            blocking=("transport_error",),
            warnings=warnings,
            transport_called=transport_called,
            runtime_fetch_performed=True,
            external_network_call_performed=False,
            metadata={"transport_error_type": type(exc).__name__},
        )

    response_blocking, response_warnings = _response_review_reasons(
        request=request,
        response=response,
    )
    blocking.extend(response_blocking)
    warnings.extend(response_warnings)
    if blocking:
        return _blocked_result(
            gate=gate_view,
            request=request,
            blocking=blocking,
            warnings=warnings,
            transport_called=transport_called,
            runtime_fetch_performed=True,
            external_network_call_performed=response.external_network_call_performed,
            metadata=_response_presence_metadata(response),
        )

    sanitized_excerpt, excerpt_warnings = _sanitized_excerpt(
        response.body_text,
        content_type=response.content_type,
        max_chars=request.max_excerpt_chars,
    )
    warnings.extend(excerpt_warnings)
    if not sanitized_excerpt:
        return _blocked_result(
            gate=gate_view,
            request=request,
            blocking=("sanitized_excerpt_required",),
            warnings=warnings,
            transport_called=transport_called,
            runtime_fetch_performed=True,
            external_network_call_performed=response.external_network_call_performed,
            metadata=_response_presence_metadata(response),
        )
    if _excerpt_contains_forbidden_marker(sanitized_excerpt):
        return _blocked_result(
            gate=gate_view,
            request=request,
            blocking=("sanitized_excerpt_contains_secret_marker",),
            warnings=warnings,
            transport_called=transport_called,
            runtime_fetch_performed=True,
            external_network_call_performed=response.external_network_call_performed,
            metadata=_response_presence_metadata(response),
        )

    source_url = response.final_url.strip() or request.source_url
    content_hash = _sha256_text(sanitized_excerpt)
    model_context_item = {
        "citation_index": request.citation_index,
        "evidence_ref": request.evidence_ref,
        "source_url": source_url,
        "source_title": request.source_title,
        "retrieved_at": response.retrieved_at,
        "item_type": request.item_type,
        "sanitized_excerpt": sanitized_excerpt,
        "content_hash": content_hash,
    }
    envelope = ExternalReadonlyEvidenceEnvelope(
        envelope_ref=request.envelope_ref,
        request_ref=request.request_ref,
        status="valid",
        allowed_for_model_context=True,
        model_context_items=(model_context_item,),
        evidence_refs=(request.evidence_ref,),
        source_urls=(source_url,),
        total_excerpt_chars=len(sanitized_excerpt),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "external_readonly_core": True,
            "runtime_service": "external_readonly.url_fetch",
            "network_gate_status": gate_view.status,
            "network_gate_open": gate_view.network_gate_open,
            "controlled_output_ref_present": bool(request.controlled_output_ref),
            "external_network_call_performed": (
                response.external_network_call_performed
            ),
            "runtime_fetch_performed": True,
            "tool_execution_performed": False,
            "writes_files": False,
            "uploads_content": False,
            "raw_response_included": False,
            "raw_html_included": False,
            "full_page_content_included": False,
            "cookies_included": False,
            "auth_headers_included": False,
            "response_headers_included": False,
            "max_bytes": request.max_bytes,
            "max_excerpt_chars": request.max_excerpt_chars,
        },
    )
    return ExternalReadonlyUrlFetchResult(
        status="completed",
        request_ref=request.request_ref,
        source_url=request.source_url,
        envelope_ref=request.envelope_ref,
        allowed_for_model_context=True,
        envelope=envelope,
        transport_called=transport_called,
        runtime_fetch_performed=True,
        external_network_call_performed=response.external_network_call_performed,
        tool_execution_performed=False,
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "external_readonly_core": True,
            "runtime_service": "external_readonly.url_fetch",
            "transport_called": transport_called,
            "external_network_call_performed": (
                response.external_network_call_performed
            ),
            "raw_response_included": False,
            "response_headers_included": False,
            "writes_files": False,
            "uploads_content": False,
        },
    )


def urllib_external_readonly_https_get_transport(
    request: ExternalReadonlyUrlFetchRequest,
) -> ExternalReadonlyHttpResponse:
    """Perform a bounded public HTTPS GET using the Python standard library."""

    request_obj = Request(
        request.source_url,
        method="GET",
        headers={
            "Accept": "text/plain,text/html,application/xhtml+xml,application/json",
            "User-Agent": "cognition-system-external-readonly/0.8.0",
        },
    )
    opener = build_opener(_NoRedirectHandler)
    retrieved_at = _now_iso()
    try:
        with opener.open(request_obj, timeout=request.timeout_seconds) as response:
            raw = response.read(request.max_bytes + 1)
            content_type = response.headers.get("content-type")
            charset = response.headers.get_content_charset() or "utf-8"
            body_text = raw.decode(charset, errors="replace")
            return ExternalReadonlyHttpResponse(
                final_url=response.geturl(),
                status_code=int(getattr(response, "status", response.getcode())),
                content_type=content_type,
                body_text=body_text,
                bytes_read=len(raw),
                retrieved_at=retrieved_at,
                redirect_count=0,
                response_headers=_normalized_headers(dict(response.headers.items())),
                external_network_call_performed=True,
            )
    except HTTPError as exc:
        return ExternalReadonlyHttpResponse(
            final_url=exc.geturl() or request.source_url,
            status_code=int(exc.code),
            content_type=exc.headers.get("content-type") if exc.headers else None,
            body_text="",
            bytes_read=0,
            retrieved_at=retrieved_at,
            redirect_count=0,
            response_headers=(
                _normalized_headers(dict(exc.headers.items()))
                if exc.headers is not None
                else {}
            ),
            external_network_call_performed=True,
            transport_error_sanitized="http_error",
        )
    except URLError:
        return ExternalReadonlyHttpResponse(
            final_url=request.source_url,
            status_code=0,
            content_type=None,
            body_text="",
            bytes_read=0,
            retrieved_at=retrieved_at,
            external_network_call_performed=True,
            transport_error_sanitized="url_error",
        )


def external_readonly_url_fetch_result_status_dict(
    result: ExternalReadonlyUrlFetchResult,
) -> dict[str, Any]:
    """Return a JSON-ready sanitized URL fetch result."""

    return {
        "status": result.status,
        "request_ref": result.request_ref,
        "source_url": result.source_url,
        "envelope_ref": result.envelope_ref,
        "allowed_for_model_context": result.allowed_for_model_context,
        "transport_called": result.transport_called,
        "runtime_fetch_performed": result.runtime_fetch_performed,
        "external_network_call_performed": result.external_network_call_performed,
        "tool_execution_performed": result.tool_execution_performed,
        "blocking_reasons": list(result.blocking_reasons),
        "warnings": list(result.warnings),
        "envelope": (
            external_readonly_evidence_envelope_status_dict(result.envelope)
            if result.envelope is not None
            else None
        ),
        "metadata": dict(result.metadata),
    }


def external_readonly_evidence_envelope_status_dict(
    envelope: ExternalReadonlyEvidenceEnvelope,
) -> dict[str, Any]:
    """Return a JSON-ready sanitized runtime evidence envelope."""

    return {
        "envelope_ref": envelope.envelope_ref,
        "request_ref": envelope.request_ref,
        "status": envelope.status,
        "allowed_for_model_context": envelope.allowed_for_model_context,
        "evidence_refs": list(envelope.evidence_refs),
        "source_urls": list(envelope.source_urls),
        "total_excerpt_chars": envelope.total_excerpt_chars,
        "blocking_reasons": list(envelope.blocking_reasons),
        "warnings": list(envelope.warnings),
        "model_context_items": [
            dict(item) for item in envelope.model_context_items
        ],
        "metadata": dict(envelope.metadata),
    }


def _gate_blocking_reasons(gate: ExternalReadonlyNetworkGateView) -> list[str]:
    blocking: list[str] = []
    if gate.status != "passed":
        blocking.append("network_gate_not_passed")
    if not gate.network_gate_open or not gate.allowed_for_network_request:
        blocking.append("network_gate_not_open")
    if not gate.operator_approval_satisfied:
        blocking.append("operator_approval_not_satisfied")
    if not gate.controlled_output_satisfied:
        blocking.append("controlled_output_not_satisfied")
    if gate.tool_origin != "url_context":
        blocking.append("tool_origin_not_url_context")
    if gate.operation_family not in EXTERNAL_READONLY_ALLOWED_OPERATIONS:
        blocking.append("operation_family_not_fetch_or_read")
    if gate.external_network_call_performed:
        blocking.append("network_gate_has_execution_fact")
    if gate.tool_execution_performed:
        blocking.append("network_gate_has_tool_execution_fact")
    if _raw_secret_keys(gate.metadata):
        blocking.append("raw_credential_material_forbidden")
    return blocking


def _request_blocking_reasons(
    request: ExternalReadonlyUrlFetchRequest,
) -> list[str]:
    blocking: list[str] = []
    if not _present(request.request_ref):
        blocking.append("request_ref_required")
    if not _external_https_url_allowed(request.source_url):
        blocking.append("source_url_not_external_https")
    if not _evidence_ref_allowed(request.envelope_ref):
        blocking.append("envelope_ref_not_external_readonly")
    if not _evidence_ref_allowed(request.evidence_ref):
        blocking.append("evidence_ref_not_external_readonly")
    if not isinstance(request.citation_index, int) or request.citation_index <= 0:
        blocking.append("citation_index_invalid")
    if _normalize_token(request.item_type) not in {
        "fetched_excerpt",
        "url_context_excerpt",
    }:
        blocking.append("item_type_not_allowed")
    if not _bounded_int(
        request.max_bytes,
        minimum=1,
        maximum=EXTERNAL_READONLY_MAX_BYTES,
    ):
        blocking.append("max_bytes_out_of_bounds")
    if not _bounded_int(
        request.max_excerpt_chars,
        minimum=1,
        maximum=EXTERNAL_READONLY_MAX_EXCERPT_CHARS,
    ):
        blocking.append("max_excerpt_chars_out_of_bounds")
    if not _bounded_int(
        request.timeout_seconds,
        minimum=1,
        maximum=EXTERNAL_READONLY_MAX_TIMEOUT_SECONDS,
    ):
        blocking.append("timeout_seconds_out_of_bounds")
    if not _bounded_int(
        request.redirect_limit,
        minimum=0,
        maximum=EXTERNAL_READONLY_MAX_REDIRECT_LIMIT,
    ):
        blocking.append("redirect_limit_out_of_bounds")
    if request.raw_url_context_included:
        blocking.append("raw_url_context_forbidden")
    if request.writes_files:
        blocking.append("writes_files_forbidden")
    if request.uploads_content:
        blocking.append("upload_forbidden")
    if request.controlled_output_ref and not _controlled_output_ref_allowed(
        request.controlled_output_ref
    ):
        blocking.append("controlled_output_ref_not_allowed")
    if _raw_secret_keys(request.metadata):
        blocking.append("raw_credential_material_forbidden")
    return blocking


def _response_review_reasons(
    *,
    request: ExternalReadonlyUrlFetchRequest,
    response: ExternalReadonlyHttpResponse,
) -> tuple[list[str], list[str]]:
    blocking: list[str] = []
    warnings: list[str] = []
    if response.transport_error_sanitized:
        blocking.append("transport_error")
    if not _external_https_url_allowed(response.final_url):
        blocking.append("final_url_not_external_https")
    if not (200 <= response.status_code <= 299):
        blocking.append("http_status_not_success")
    if response.bytes_read > request.max_bytes:
        blocking.append("response_bytes_exceeds_limit")
    if response.redirect_count > request.redirect_limit:
        blocking.append("redirect_count_exceeds_limit")
    if not _valid_retrieved_at(response.retrieved_at):
        blocking.append("retrieved_at_invalid")
    if _forbidden_response_header_names(response.response_headers):
        blocking.append("response_headers_forbidden")
    if not response.body_text.strip():
        blocking.append("response_body_empty")

    content_type = _content_type_token(response.content_type)
    if content_type is None:
        warnings.append("content_type_missing")
    elif content_type not in EXTERNAL_READONLY_ALLOWED_CONTENT_TYPES:
        blocking.append("content_type_not_allowed")
    return blocking, warnings


def _blocked_result(
    *,
    gate: ExternalReadonlyNetworkGateView,
    request: ExternalReadonlyUrlFetchRequest,
    blocking: Sequence[str],
    warnings: Sequence[str],
    transport_called: bool,
    runtime_fetch_performed: bool,
    external_network_call_performed: bool,
    metadata: Mapping[str, Any] | None = None,
) -> ExternalReadonlyUrlFetchResult:
    return ExternalReadonlyUrlFetchResult(
        status="blocked",
        request_ref=request.request_ref,
        source_url=request.source_url,
        envelope_ref=request.envelope_ref,
        allowed_for_model_context=False,
        envelope=None,
        transport_called=transport_called,
        runtime_fetch_performed=runtime_fetch_performed,
        external_network_call_performed=external_network_call_performed,
        tool_execution_performed=False,
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "external_readonly_core": True,
            "runtime_service": "external_readonly.url_fetch",
            "network_gate_status": gate.status,
            "network_gate_open": gate.network_gate_open,
            "transport_called": transport_called,
            "runtime_fetch_performed": runtime_fetch_performed,
            "external_network_call_performed": external_network_call_performed,
            "raw_response_included": False,
            "response_headers_included": False,
            "writes_files": False,
            "uploads_content": False,
            **dict(metadata or {}),
        },
    )


def _sanitized_excerpt(
    value: str,
    *,
    content_type: str | None,
    max_chars: int,
) -> tuple[str, list[str]]:
    warnings: list[str] = []
    text = value
    if _looks_like_html(value, content_type):
        text = _strip_html(value)
    else:
        text = _strip_script_blocks(value)
    text = html.unescape(text)
    text = _normalize_text(text)
    if len(text) > max_chars:
        text = text[:max_chars].rstrip()
        warnings.append("sanitized_excerpt_truncated")
    return text, warnings


def _strip_html(value: str) -> str:
    text = _strip_script_blocks(value)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return text


def _strip_script_blocks(value: str) -> str:
    return re.sub(
        r"<(script|style|noscript)\b[^>]*>.*?</\1>",
        " ",
        value,
        flags=re.IGNORECASE | re.DOTALL,
    )


def _looks_like_html(value: str, content_type: str | None) -> bool:
    token = _content_type_token(content_type)
    if token in {"text/html", "application/xhtml+xml"}:
        return True
    lower = value[:500].lower()
    return "<html" in lower or "<body" in lower or "</" in lower


def _response_presence_metadata(
    response: ExternalReadonlyHttpResponse,
) -> dict[str, Any]:
    return {
        "http_status_code": response.status_code,
        "content_type_present": bool(response.content_type),
        "response_headers_present": bool(response.response_headers),
        "response_cookie_header_present": bool(
            _forbidden_response_header_names(response.response_headers)
        ),
        "body_bytes_read": response.bytes_read,
        "redirect_count": response.redirect_count,
        "transport_error_present": bool(response.transport_error_sanitized),
    }


def _normalized_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {str(key).lower(): str(value) for key, value in headers.items()}


def _forbidden_response_header_names(headers: Mapping[str, str]) -> tuple[str, ...]:
    names = []
    for key in headers:
        normalized = str(key).strip().lower()
        if normalized in EXTERNAL_READONLY_FORBIDDEN_RESPONSE_HEADERS:
            names.append(normalized)
    return tuple(_ordered_unique(names))


def _external_https_url_allowed(value: str) -> bool:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    if parsed.username or parsed.password:
        return False
    host = parsed.hostname.lower()
    if (
        host in {"localhost"}
        or host.endswith(".localhost")
        or host.endswith(".local")
        or host.endswith(".internal")
    ):
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return True
    return not (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _controlled_output_ref_allowed(value: str | None) -> bool:
    if not _present(value):
        return False
    ref = str(value).strip()
    if ref.startswith(EXTERNAL_READONLY_EVIDENCE_REF_PREFIX):
        return len(ref) > len(EXTERNAL_READONLY_EVIDENCE_REF_PREFIX)
    if not ref.startswith(f"{EXTERNAL_READONLY_CONTROLLED_OUTPUT_ROOT}/"):
        return False
    if not ref.endswith(".json"):
        return False
    return not any(part in {"", ".", ".."} for part in ref.split("/"))


def _evidence_ref_allowed(value: str | None) -> bool:
    return _present(value) and str(value).strip().startswith(
        EXTERNAL_READONLY_EVIDENCE_REF_PREFIX
    ) and len(str(value).strip()) > len(EXTERNAL_READONLY_EVIDENCE_REF_PREFIX)


def _valid_retrieved_at(value: str) -> bool:
    text = value.strip()
    if "T" not in text:
        return False
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _content_type_token(value: str | None) -> str | None:
    if not value:
        return None
    return value.split(";", 1)[0].strip().lower() or None


def _bounded_int(value: int, *, minimum: int, maximum: int) -> bool:
    return isinstance(value, int) and minimum <= value <= maximum


def _raw_secret_keys(raw_config: Mapping[str, Any]) -> tuple[str, ...]:
    keys: list[str] = []
    for key, value in raw_config.items():
        key_text = str(key).lower()
        if any(marker in key_text for marker in EXTERNAL_READONLY_SECRET_KEY_MARKERS):
            if value:
                keys.append(str(key))
        if isinstance(value, Mapping):
            nested = _raw_secret_keys(value)
            keys.extend(f"{key}.{item}" for item in nested)
    return tuple(_ordered_unique(keys))


def _excerpt_contains_forbidden_marker(value: str) -> bool:
    lower = value.lower()
    return any(
        marker in lower for marker in EXTERNAL_READONLY_EXCERPT_FORBIDDEN_MARKERS
    )


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_token(value: str) -> str:
    return value.strip().replace("-", "_").replace(" ", "_").lower()


def _coerce_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _present(value: str | None) -> bool:
    return value is not None and bool(value.strip())


def _ordered_unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None
