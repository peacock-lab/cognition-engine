"""Behavior guards for product gateway response summaries."""

from __future__ import annotations

from typing import Any, Mapping

from behavior_contracts.governance_candidate import CandidateGuardResult
from schemas.product_gateway_response_summary import (
    PRODUCT_GATEWAY_RESPONSE_SUMMARY_ENTRY_KINDS,
    PRODUCT_GATEWAY_RESPONSE_SUMMARY_PAYLOAD_TYPE,
    PRODUCT_GATEWAY_RESPONSE_SUMMARY_PRODUCT,
    PRODUCT_GATEWAY_RESPONSE_SUMMARY_STATUSES,
    PRODUCT_GATEWAY_RESPONSE_SUMMARY_VERSION,
)


SUMMARY_ONLY_FORBIDDEN_KEYS = frozenset(
    {
        "artifact_content",
        "completion",
        "content",
        "full_response",
        "message",
        "messages",
        "prompt",
        "response",
        "response_text",
        "system_prompt",
        "text",
        "user_message",
    }
)

RAW_PAYLOAD_KEYS = frozenset(
    {
        "api_key",
        "credential",
        "credentials",
        "payload",
        "provider_payload",
        "provider_response",
        "raw",
        "raw_adk_object",
        "raw_api_payload",
        "raw_input",
        "raw_output",
        "raw_payload",
        "raw_prompt",
        "raw_provider_payload",
        "raw_provider_response",
        "raw_response",
        "raw_tool_input",
        "raw_tool_output",
        "raw_user_message",
        "secret",
        "token",
        "tool_context",
        "tool_input",
        "tool_output",
    }
)

SENSITIVE_KEY_EXCEPTIONS = frozenset({"raw_output_digest"})

REF_FIELDS = frozenset(
    {
        "evidence_refs",
        "audit_refs",
        "agent_advice_refs",
        "additional_refs",
        "tool_audit_refs",
    }
)
REF_ITEM_KEYS = frozenset({"ref", "kind", "purpose", "metadata"})

NO_EXECUTION_FIELDS = frozenset(
    {
        "execution_enabled",
        "runtime_permission_granted",
        "agent_runtime_enabled",
        "llm_call_enabled",
        "action_execution_enabled",
        "chat_enabled",
        "durable_session",
        "gateway_enabled",
        "tool_execution_enabled",
        "memory_enabled",
    }
)

FORBIDDEN_OBJECT_MODULE_PREFIXES = (
    "google.adk",
    "adk_adapter",
    "runtime_container",
    "composition",
    "litellm",
)


class ProductGatewayResponseSummaryHeaderGuard:
    """Validate the frozen product gateway response summary header."""

    guard_name = "product_gateway_response_summary_header_guard"

    def validate(self, summary: Mapping[str, Any]) -> CandidateGuardResult:
        violations: list[str] = []
        expected = {
            "product": PRODUCT_GATEWAY_RESPONSE_SUMMARY_PRODUCT,
            "payload_type": PRODUCT_GATEWAY_RESPONSE_SUMMARY_PAYLOAD_TYPE,
            "payload_version": PRODUCT_GATEWAY_RESPONSE_SUMMARY_VERSION,
        }
        for key, expected_value in expected.items():
            if summary.get(key) != expected_value:
                violations.append(f"{key} must be {expected_value}.")
        for key in ("request_id", "entry_kind", "status"):
            if not isinstance(summary.get(key), str) or not summary.get(key):
                violations.append(f"{key} is required.")
        entry_kind = summary.get("entry_kind")
        if isinstance(entry_kind, str) and (
            entry_kind not in PRODUCT_GATEWAY_RESPONSE_SUMMARY_ENTRY_KINDS
        ):
            violations.append(f"unsupported product_gateway entry_kind: {entry_kind}.")
        status = summary.get("status")
        if isinstance(status, str) and status not in PRODUCT_GATEWAY_RESPONSE_SUMMARY_STATUSES:
            violations.append(f"unsupported product_gateway status: {status}.")
        return _result(violations)


class ProductGatewayResponseSummaryOnlyGuard:
    """Reject payloads that carry response bodies instead of summaries."""

    guard_name = "product_gateway_response_summary_only_guard"

    def validate(self, summary: Mapping[str, Any]) -> CandidateGuardResult:
        violations = [
            f"summary-only field is forbidden at {path}."
            for path, _value in _walk(summary)
            if _key_at_path(path) in SUMMARY_ONLY_FORBIDDEN_KEYS
        ]
        return _result(violations)


class ProductGatewayResponseRefsOnlyGuard:
    """Validate that refs are sanitized ref items only."""

    guard_name = "product_gateway_response_refs_only_guard"

    def validate(self, summary: Mapping[str, Any]) -> CandidateGuardResult:
        violations: list[str] = []
        for field_name in REF_FIELDS:
            values = summary.get(field_name, [])
            if not isinstance(values, (list, tuple)):
                violations.append(f"{field_name} must be a list.")
                continue
            for index, value in enumerate(values):
                item_path = f"$.{field_name}[{index}]"
                if not isinstance(value, Mapping):
                    violations.append(f"{item_path} must be a mapping.")
                    continue
                extra_keys = sorted(str(key) for key in set(value.keys()) - REF_ITEM_KEYS)
                for key in extra_keys:
                    violations.append(f"{item_path}.{key} is not allowed in refs.")
                if not isinstance(value.get("ref"), str) or not value.get("ref"):
                    violations.append(f"{item_path}.ref is required.")
                if not isinstance(value.get("kind"), str) or not value.get("kind"):
                    violations.append(f"{item_path}.kind is required.")
                metadata = value.get("metadata", {})
                if metadata is not None and not isinstance(metadata, Mapping):
                    violations.append(f"{item_path}.metadata must be a mapping.")
        return _result(violations)


class ProductGatewayResponseNoRawPayloadGuard:
    """Reject raw or sensitive payload fields."""

    guard_name = "product_gateway_response_no_raw_payload_guard"

    def validate(self, summary: Mapping[str, Any]) -> CandidateGuardResult:
        violations = [
            f"raw or sensitive payload is forbidden at {path}."
            for path, value in _walk(summary)
            if _is_raw_payload(path, value)
        ]
        return _result(violations)


class ProductGatewayResponseNoExecutionGuard:
    """Reject execution-enabling flags."""

    guard_name = "product_gateway_response_no_execution_guard"

    def validate(self, summary: Mapping[str, Any]) -> CandidateGuardResult:
        violations = [
            f"{path} must not be true."
            for path, value in _walk(summary)
            if _key_at_path(path) in NO_EXECUTION_FIELDS and value is True
        ]
        return _result(violations)


class ProductGatewayResponseNoRuntimeObjectLeakageGuard:
    """Reject runtime, ADK, composition, and provider object markers."""

    guard_name = "product_gateway_response_no_runtime_object_leakage_guard"

    def validate(self, summary: Mapping[str, Any]) -> CandidateGuardResult:
        violations = [
            f"runtime object leakage is forbidden at {path}."
            for path, value in _walk(summary)
            if _is_runtime_object(value)
        ]
        return _result(violations)


class ProductGatewayResponseBlockedRequiresReasonGuard:
    """Require blocked summaries to carry explicit blocking reasons."""

    guard_name = "product_gateway_response_blocked_requires_reason_guard"

    def validate(self, summary: Mapping[str, Any]) -> CandidateGuardResult:
        if summary.get("status") != "blocked":
            return _result([])
        reasons = summary.get("blocking_reasons")
        if isinstance(reasons, (list, tuple)) and any(
            isinstance(reason, str) and reason for reason in reasons
        ):
            return _result([])
        return _result(["blocked product gateway summaries require blocking_reasons."])


DEFAULT_PRODUCT_GATEWAY_RESPONSE_SUMMARY_GUARDS = (
    ProductGatewayResponseSummaryHeaderGuard(),
    ProductGatewayResponseSummaryOnlyGuard(),
    ProductGatewayResponseRefsOnlyGuard(),
    ProductGatewayResponseNoRawPayloadGuard(),
    ProductGatewayResponseNoExecutionGuard(),
    ProductGatewayResponseNoRuntimeObjectLeakageGuard(),
    ProductGatewayResponseBlockedRequiresReasonGuard(),
)


def validate_product_gateway_response_summary_guards(
    summary: Mapping[str, Any],
    guards: tuple[
        ProductGatewayResponseSummaryHeaderGuard
        | ProductGatewayResponseSummaryOnlyGuard
        | ProductGatewayResponseRefsOnlyGuard
        | ProductGatewayResponseNoRawPayloadGuard
        | ProductGatewayResponseNoExecutionGuard
        | ProductGatewayResponseNoRuntimeObjectLeakageGuard
        | ProductGatewayResponseBlockedRequiresReasonGuard,
        ...,
    ] = DEFAULT_PRODUCT_GATEWAY_RESPONSE_SUMMARY_GUARDS,
) -> CandidateGuardResult:
    """Run product gateway response summary guards without executing anything."""

    violations: list[str] = []
    for guard in guards:
        result = guard.validate(summary)
        violations.extend(f"{guard.guard_name}: {item}" for item in result.violations)
    return _result(violations)


def _result(violations: list[str]) -> CandidateGuardResult:
    return CandidateGuardResult(
        passed=not violations,
        violations=tuple(violations),
    )


def _walk(value: Any, path: str = "$") -> list[tuple[str, Any]]:
    items = [(path, value)]
    if isinstance(value, Mapping):
        for key, item in value.items():
            items.extend(_walk(item, f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            items.extend(_walk(item, f"{path}[{index}]"))
    return items


def _key_at_path(path: str) -> str:
    return path.rsplit(".", maxsplit=1)[-1].split("[", maxsplit=1)[0].lower()


def _is_raw_payload(path: str, value: Any) -> bool:
    key = _key_at_path(path)
    if key in SENSITIVE_KEY_EXCEPTIONS:
        return False
    if key in RAW_PAYLOAD_KEYS or key.endswith("_token") or key.endswith("_secret"):
        return True
    if isinstance(value, str):
        lowered = value.lower()
        return any(
            marker in lowered
            for marker in (
                "raw provider response",
                "raw_response",
                "response_text",
                "system_prompt",
                "raw_tool_input",
                "raw_tool_output",
            )
        )
    return False


def _is_runtime_object(value: Any) -> bool:
    if isinstance(value, Mapping):
        module_name = value.get("object_module")
        return isinstance(module_name, str) and module_name.startswith(
            FORBIDDEN_OBJECT_MODULE_PREFIXES
        )
    if value is None or isinstance(value, (str, int, float, bool, list, tuple, dict)):
        return False
    return type(value).__module__.startswith(FORBIDDEN_OBJECT_MODULE_PREFIXES)


__all__ = [
    "DEFAULT_PRODUCT_GATEWAY_RESPONSE_SUMMARY_GUARDS",
    "ProductGatewayResponseBlockedRequiresReasonGuard",
    "ProductGatewayResponseNoExecutionGuard",
    "ProductGatewayResponseNoRawPayloadGuard",
    "ProductGatewayResponseNoRuntimeObjectLeakageGuard",
    "ProductGatewayResponseRefsOnlyGuard",
    "ProductGatewayResponseSummaryHeaderGuard",
    "ProductGatewayResponseSummaryOnlyGuard",
    "validate_product_gateway_response_summary_guards",
]
