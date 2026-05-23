"""Candidate-only network gate for future external read-only references."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import ipaddress
import re
from typing import Any
from urllib.parse import urlparse

from cognition_operation_flows._external_readonly.tool_design import (
    TWF_EXTERNAL_READONLY_ORIGIN_OPERATIONS,
    TwfExternalReadonlyToolDesignCandidate,
    review_twf_external_readonly_tool_design,
)


TWF_EXTERNAL_READONLY_NETWORK_GATE_STAGES = (
    "design_review",
    "request_scope_review",
    "network_gate_review",
    "operator_approval_review",
    "source_boundary_review",
    "controlled_output_review",
    "runtime_closed_review",
    "sanitized_gate_summary",
)
TWF_EXTERNAL_READONLY_NETWORK_GATE_POLICIES = frozenset(
    {"external_readonly_manual_approval"}
)
TWF_EXTERNAL_READONLY_CONTROLLED_OUTPUT_ROOT = "outputs/external-readonly"
TWF_EXTERNAL_READONLY_MAX_RESULT_COUNT = 10
TWF_EXTERNAL_READONLY_MAX_BYTES = 50_000
TWF_EXTERNAL_READONLY_MAX_TIMEOUT_SECONDS = 30
TWF_EXTERNAL_READONLY_MAX_REDIRECT_LIMIT = 3
TWF_EXTERNAL_READONLY_SECRET_KEY_MARKERS = (
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


@dataclass(frozen=True)
class TwfExternalReadonlyNetworkRequestCandidate:
    """Future external read-only request facts, without making a network call."""

    request_ref: str
    tool_name: str
    tool_origin: str
    operation_family: str
    scope_ref: str | None = None
    query_ref: str | None = None
    source_url: str | None = None
    controlled_output_ref: str | None = None
    max_result_count: int = 5
    max_bytes: int = 20_000
    timeout_seconds: int = 10
    redirect_limit: int = 2
    network_enabled_for_request: bool = False
    raw_query_included: bool = False
    raw_url_context_included: bool = False
    raw_request_payload_included: bool = False
    raw_network_response_included: bool = False
    stores_raw_response: bool = False
    stores_full_page_content: bool = False
    uploads_content: bool = False
    allows_auth_headers: bool = False
    allows_cookies: bool = False
    allows_login: bool = False
    allows_form_submission: bool = False
    executes_javascript_action: bool = False
    follows_unbounded_redirects: bool = False
    writes_files: bool = False
    mutates_external_system: bool = False
    executes_code: bool = False
    executes_shell: bool = False
    calls_llm: bool = False
    tool_execution_performed: bool = False
    external_network_call_performed: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfExternalReadonlyNetworkApprovalCandidate:
    """Operator approval facts for opening a future external-readonly gate."""

    operator_approved: bool = False
    allow_external_network: bool = False
    approval_ref: str | None = None
    approved_by: str | None = None
    network_gate_ref: str | None = None
    network_gate_policy: str = "external_readonly_manual_approval"
    audit_ref: str | None = None
    sanitized_evidence_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfExternalReadonlyNetworkGateCandidate:
    """Sanitized gate result for one future external-readonly network request."""

    request_ref: str
    tool_name: str
    tool_origin: str
    operation_family: str
    status: str
    risk_level: str
    allowed_for_network_request: bool
    network_gate_open: bool
    operator_approval_satisfied: bool
    controlled_output_satisfied: bool
    external_network_call_performed: bool = False
    tool_execution_performed: bool = False
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfExternalReadonlyNetworkGateSummaryCandidate:
    """Aggregate sanitized summary for external-readonly network gates."""

    status: str
    allowed_request_refs: tuple[str, ...]
    blocked_request_refs: tuple[str, ...]
    gates: tuple[TwfExternalReadonlyNetworkGateCandidate, ...]
    external_network_call_performed: bool = False
    tool_execution_performed: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


def evaluate_twf_external_readonly_network_gate(
    *,
    design: TwfExternalReadonlyToolDesignCandidate,
    request: TwfExternalReadonlyNetworkRequestCandidate,
    approval: TwfExternalReadonlyNetworkApprovalCandidate,
) -> TwfExternalReadonlyNetworkGateCandidate:
    """Evaluate a future external-readonly network gate without network I/O."""

    design_review = review_twf_external_readonly_tool_design(design)
    request_origin = _normalize_token(request.tool_origin)
    request_operation = _normalize_operation_family(request.operation_family)
    blocking: list[str] = []
    warnings: list[str] = []

    if not design_review.allowed_for_design:
        blocking.append("design_review_not_allowed")
    if not _present(request.request_ref):
        blocking.append("request_ref_required")
    if not _present(request.scope_ref):
        blocking.append("scope_ref_required")
    if request.tool_name != design.tool_name:
        blocking.append("request_tool_identity_mismatch")
    if request_origin != design_review.tool_origin:
        blocking.append("request_tool_identity_mismatch")
    if request_operation != design_review.operation_family:
        blocking.append("request_tool_identity_mismatch")
    if request_operation not in TWF_EXTERNAL_READONLY_ORIGIN_OPERATIONS.get(
        request_origin,
        frozenset(),
    ):
        blocking.append("operation_family_not_allowed_for_tool_origin")

    if request_origin == "google_search" and not _present(request.query_ref):
        blocking.append("google_search_query_ref_required")
    if request_origin == "url_context":
        if not _present(request.source_url):
            blocking.append("url_context_source_url_required")
        elif not _external_https_url_allowed(request.source_url or ""):
            blocking.append("source_url_not_external_https")
    elif request.source_url and not _external_https_url_allowed(request.source_url):
        blocking.append("source_url_not_external_https")

    if not request.network_enabled_for_request:
        blocking.append("network_enabled_for_request_required")
    if request.external_network_call_performed:
        blocking.append("external_network_call_forbidden_in_gate")
    if request.tool_execution_performed:
        blocking.append("tool_execution_forbidden_in_gate")
    if not approval.operator_approved:
        blocking.append("operator_approval_not_true")
    if not approval.allow_external_network:
        blocking.append("operator_approval_external_network_not_true")
    if not _present(approval.approval_ref):
        blocking.append("approval_ref_required")
    if not _present(approval.approved_by):
        blocking.append("approved_by_required")
    if not _present(approval.network_gate_ref):
        blocking.append("network_gate_ref_required")
    if approval.network_gate_policy not in TWF_EXTERNAL_READONLY_NETWORK_GATE_POLICIES:
        blocking.append("network_gate_policy_not_allowed")
    if not _present(approval.audit_ref):
        blocking.append("audit_ref_required")
    if not _present(approval.sanitized_evidence_ref):
        blocking.append("sanitized_evidence_ref_required")

    if not _controlled_output_ref_allowed(request.controlled_output_ref):
        blocking.append("controlled_output_ref_required")
    if not _bounded_int(
        request.max_result_count,
        minimum=1,
        maximum=TWF_EXTERNAL_READONLY_MAX_RESULT_COUNT,
    ):
        blocking.append("max_result_count_out_of_bounds")
    if not _bounded_int(
        request.max_bytes,
        minimum=1,
        maximum=TWF_EXTERNAL_READONLY_MAX_BYTES,
    ):
        blocking.append("max_bytes_out_of_bounds")
    if not _bounded_int(
        request.timeout_seconds,
        minimum=1,
        maximum=TWF_EXTERNAL_READONLY_MAX_TIMEOUT_SECONDS,
    ):
        blocking.append("timeout_seconds_out_of_bounds")
    if not _bounded_int(
        request.redirect_limit,
        minimum=0,
        maximum=TWF_EXTERNAL_READONLY_MAX_REDIRECT_LIMIT,
    ):
        blocking.append("redirect_limit_out_of_bounds")

    if request.raw_query_included:
        blocking.append("raw_query_forbidden")
    if request.raw_url_context_included:
        blocking.append("raw_url_context_forbidden")
    if request.raw_request_payload_included:
        blocking.append("raw_request_payload_forbidden")
    if request.raw_network_response_included:
        blocking.append("raw_network_response_forbidden")
    if request.stores_raw_response:
        blocking.append("raw_response_storage_forbidden")
    if request.stores_full_page_content:
        blocking.append("full_page_content_storage_forbidden")
    if request.uploads_content:
        blocking.append("upload_forbidden")
    if request.allows_auth_headers:
        blocking.append("auth_headers_forbidden")
    if request.allows_cookies:
        blocking.append("cookies_forbidden")
    if request.allows_login:
        blocking.append("login_flow_forbidden")
    if request.allows_form_submission:
        blocking.append("form_submission_forbidden")
    if request.executes_javascript_action:
        blocking.append("javascript_action_forbidden")
    if request.follows_unbounded_redirects:
        blocking.append("unbounded_redirects_forbidden")
    if request.writes_files:
        blocking.append("writes_files_forbidden")
    if request.mutates_external_system:
        blocking.append("mutates_external_system_forbidden")
    if request.executes_code:
        blocking.append("executes_code_forbidden")
    if request.executes_shell:
        blocking.append("executes_shell_forbidden")
    if request.calls_llm:
        blocking.append("calls_llm_forbidden")
    if _raw_secret_keys(request.metadata) or _raw_secret_keys(approval.metadata):
        blocking.append("raw_credential_material_forbidden")

    operator_approval_satisfied = (
        approval.operator_approved
        and approval.allow_external_network
        and _present(approval.approval_ref)
        and _present(approval.approved_by)
        and _present(approval.network_gate_ref)
    )
    controlled_output_satisfied = (
        _controlled_output_ref_allowed(request.controlled_output_ref)
        and _present(approval.audit_ref)
        and _present(approval.sanitized_evidence_ref)
    )
    return TwfExternalReadonlyNetworkGateCandidate(
        request_ref=request.request_ref,
        tool_name=request.tool_name,
        tool_origin=request_origin,
        operation_family=request_operation,
        status="passed" if not blocking else "blocked",
        risk_level="medium" if not blocking else "blocked",
        allowed_for_network_request=not blocking,
        network_gate_open=not blocking,
        operator_approval_satisfied=operator_approval_satisfied,
        controlled_output_satisfied=controlled_output_satisfied,
        external_network_call_performed=False,
        tool_execution_performed=False,
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "candidate_only": True,
            "reference_only": True,
            "stages": list(TWF_EXTERNAL_READONLY_NETWORK_GATE_STAGES),
            "design_review_status": design_review.status,
            "network_gate_required": True,
            "network_enabled_for_request": request.network_enabled_for_request,
            "operator_approval_required": True,
            "approval_ref_present": bool(approval.approval_ref),
            "approved_by_present": bool(approval.approved_by),
            "network_gate_ref_present": bool(approval.network_gate_ref),
            "audit_ref_present": bool(approval.audit_ref),
            "sanitized_evidence_ref_present": bool(
                approval.sanitized_evidence_ref
            ),
            "query_ref_present": bool(request.query_ref),
            "source_url_present": bool(request.source_url),
            "controlled_output_ref": request.controlled_output_ref,
            "max_result_count": request.max_result_count,
            "max_bytes": request.max_bytes,
            "timeout_seconds": request.timeout_seconds,
            "redirect_limit": request.redirect_limit,
            "does_not_execute_tool": True,
            "does_not_perform_external_network_calls": True,
            "external_network_call_performed": False,
            "tool_execution_performed": False,
            "raw_metadata_included": False,
        },
    )


def build_twf_external_readonly_network_gate_summary(
    gates: Sequence[TwfExternalReadonlyNetworkGateCandidate],
) -> TwfExternalReadonlyNetworkGateSummaryCandidate:
    """Build an aggregate sanitized summary for external-readonly gates."""

    allowed = tuple(gate.request_ref for gate in gates if gate.network_gate_open)
    blocked = tuple(gate.request_ref for gate in gates if not gate.network_gate_open)
    return TwfExternalReadonlyNetworkGateSummaryCandidate(
        status="passed" if not blocked else "blocked",
        allowed_request_refs=tuple(_ordered_unique(allowed)),
        blocked_request_refs=tuple(_ordered_unique(blocked)),
        gates=tuple(gates),
        metadata={
            "candidate_only": True,
            "reference_only": True,
            "does_not_execute_tools": True,
            "does_not_perform_external_network_calls": True,
            "gate_count": len(gates),
        },
    )


def twf_external_readonly_network_gate_status_dict(
    gate: TwfExternalReadonlyNetworkGateCandidate,
) -> dict[str, Any]:
    """Return a JSON-ready sanitized network gate summary."""

    return {
        "request_ref": gate.request_ref,
        "tool_name": gate.tool_name,
        "tool_origin": gate.tool_origin,
        "operation_family": gate.operation_family,
        "status": gate.status,
        "risk_level": gate.risk_level,
        "allowed_for_network_request": gate.allowed_for_network_request,
        "network_gate_open": gate.network_gate_open,
        "operator_approval_satisfied": gate.operator_approval_satisfied,
        "controlled_output_satisfied": gate.controlled_output_satisfied,
        "external_network_call_performed": gate.external_network_call_performed,
        "tool_execution_performed": gate.tool_execution_performed,
        "blocking_reasons": list(gate.blocking_reasons),
        "warnings": list(gate.warnings),
        "metadata": dict(gate.metadata),
    }


def twf_external_readonly_network_gate_summary_status_dict(
    summary: TwfExternalReadonlyNetworkGateSummaryCandidate,
) -> dict[str, Any]:
    """Return a JSON-ready sanitized aggregate gate summary."""

    return {
        "status": summary.status,
        "allowed_request_refs": list(summary.allowed_request_refs),
        "blocked_request_refs": list(summary.blocked_request_refs),
        "external_network_call_performed": summary.external_network_call_performed,
        "tool_execution_performed": summary.tool_execution_performed,
        "gates": [
            twf_external_readonly_network_gate_status_dict(gate)
            for gate in summary.gates
        ],
        "metadata": dict(summary.metadata),
    }


def _normalize_operation_family(value: str) -> str:
    normalized = _normalize_token(value)
    for operations in TWF_EXTERNAL_READONLY_ORIGIN_OPERATIONS.values():
        if normalized in operations:
            return normalized
    tokens = _split_tokens(normalized)
    for token in tokens:
        if any(
            token in operations
            for operations in TWF_EXTERNAL_READONLY_ORIGIN_OPERATIONS.values()
        ):
            return token
    return normalized


def _controlled_output_ref_allowed(value: str | None) -> bool:
    if not _present(value):
        return False
    ref = str(value).strip()
    if ref.startswith("evidence://external-readonly/"):
        return len(ref) > len("evidence://external-readonly/")
    if not ref.startswith(f"{TWF_EXTERNAL_READONLY_CONTROLLED_OUTPUT_ROOT}/"):
        return False
    if not ref.endswith(".json"):
        return False
    parts = ref.split("/")
    return not any(part in {"", ".", ".."} for part in parts)


def _external_https_url_allowed(value: str) -> bool:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if host in {"localhost"} or host.endswith(".localhost") or host.endswith(".local"):
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


def _bounded_int(value: int, *, minimum: int, maximum: int) -> bool:
    return isinstance(value, int) and minimum <= value <= maximum


def _raw_secret_keys(raw_config: Mapping[str, Any]) -> tuple[str, ...]:
    keys: list[str] = []
    for key, value in raw_config.items():
        key_text = str(key).lower()
        if any(
            marker in key_text
            for marker in TWF_EXTERNAL_READONLY_SECRET_KEY_MARKERS
        ):
            if value:
                keys.append(str(key))
        if isinstance(value, Mapping):
            nested = _raw_secret_keys(value)
            keys.extend(f"{key}.{item}" for item in nested)
    return tuple(_ordered_unique(keys))


def _present(value: str | None) -> bool:
    return value is not None and bool(value.strip())


def _normalize_token(value: str) -> str:
    return (
        _camel_to_snake(value.strip())
        .replace("-", "_")
        .replace(" ", "_")
        .replace("/", "_")
        .lower()
    )


def _camel_to_snake(value: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value)


def _split_tokens(value: str) -> list[str]:
    return [token for token in value.split("_") if token]


def _ordered_unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique
