"""Public product gateway response summary contract."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


PRODUCT_GATEWAY_RESPONSE_SUMMARY_PRODUCT = "product_gateway"
PRODUCT_GATEWAY_RESPONSE_SUMMARY_PAYLOAD_TYPE = "product_gateway_response_summary"
PRODUCT_GATEWAY_RESPONSE_SUMMARY_VERSION = "product_gateway_response_summary_v1"

ProductGatewayResponseSummaryEntryKind = Literal[
    "cognition_run",
    "controlled_live",
    "agent_shell",
    "tool_smoke",
]
ProductGatewayResponseSummaryStatus = Literal[
    "success",
    "blocked",
    "failed",
    "skipped",
]

PRODUCT_GATEWAY_RESPONSE_SUMMARY_ENTRY_KINDS = frozenset(
    {
        "cognition_run",
        "controlled_live",
        "agent_shell",
        "tool_smoke",
    }
)
PRODUCT_GATEWAY_RESPONSE_SUMMARY_STATUSES = frozenset(
    {"success", "blocked", "failed", "skipped"}
)

FORBIDDEN_PRODUCT_GATEWAY_RESPONSE_SUMMARY_KEYS = frozenset(
    {
        "api_key",
        "artifact_content",
        "completion",
        "content",
        "credential",
        "credentials",
        "full_response",
        "message",
        "messages",
        "payload",
        "prompt",
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
        "response",
        "response_text",
        "secret",
        "system_prompt",
        "text",
        "token",
        "tool_context",
        "tool_input",
        "tool_output",
        "user_message",
    }
)

SENSITIVE_KEY_EXCEPTIONS = frozenset({"raw_output_digest"})

FORBIDDEN_OBJECT_MODULE_PREFIXES = (
    "google.adk",
    "adk_adapter",
    "runtime_container",
    "composition",
    "litellm",
)


class ProductGatewayResponseSummaryBaseModel(BaseModel):
    """Base model for product gateway response summary public contracts."""

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_summary_public_boundary(
        self,
    ) -> "ProductGatewayResponseSummaryBaseModel":
        violations = _summary_boundary_violations(self.model_dump(mode="python"))
        if violations:
            raise ValueError("; ".join(violations))
        return self


class ProductGatewayResponseSummaryRefSchema(ProductGatewayResponseSummaryBaseModel):
    """Sanitized reference carried by a product gateway response summary."""

    ref: str = Field(..., min_length=1)
    kind: str = Field(..., min_length=1)
    purpose: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProductGatewayResponseSummarySchema(ProductGatewayResponseSummaryBaseModel):
    """Public summary-only response shape consumed across package boundaries."""

    product: Literal["product_gateway"] = PRODUCT_GATEWAY_RESPONSE_SUMMARY_PRODUCT
    payload_type: Literal["product_gateway_response_summary"] = (
        PRODUCT_GATEWAY_RESPONSE_SUMMARY_PAYLOAD_TYPE
    )
    payload_version: Literal["product_gateway_response_summary_v1"] = (
        PRODUCT_GATEWAY_RESPONSE_SUMMARY_VERSION
    )
    request_id: str = Field(..., min_length=1)
    entry_kind: ProductGatewayResponseSummaryEntryKind
    status: ProductGatewayResponseSummaryStatus
    exit_code: int | None = None
    product_gateway_response_ref: str | None = None
    governance_summary_ref: str | None = None
    evidence_refs: list[ProductGatewayResponseSummaryRefSchema] = Field(
        default_factory=list
    )
    audit_refs: list[ProductGatewayResponseSummaryRefSchema] = Field(
        default_factory=list
    )
    agent_advice_refs: list[ProductGatewayResponseSummaryRefSchema] = Field(
        default_factory=list
    )
    tool_audit_refs: list[ProductGatewayResponseSummaryRefSchema] = Field(
        default_factory=list
    )
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    readonly: bool = True
    summary_only: bool = True
    refs_only: bool = True
    candidate_only: bool = True
    execution_enabled: bool = False
    runtime_permission_granted: bool = False
    llm_call_enabled: bool = False
    tool_execution_enabled: bool = False
    action_execution_enabled: bool = False
    gateway_enabled: bool = False

    @model_validator(mode="after")
    def validate_response_summary(self) -> "ProductGatewayResponseSummarySchema":
        if self.status == "blocked" and not self.blocking_reasons:
            raise ValueError("blocked product gateway summaries require blocking_reasons.")
        _validate_summary_invariant_flags(self)
        return self


def validate_product_gateway_response_summary(
    summary: dict[str, Any],
) -> ProductGatewayResponseSummarySchema:
    """Validate a plain dict response summary as a public contract."""

    return ProductGatewayResponseSummarySchema.model_validate(summary)


def _validate_summary_invariant_flags(
    summary: ProductGatewayResponseSummarySchema,
) -> None:
    if not summary.readonly:
        raise ValueError("readonly must remain true.")
    if not summary.summary_only:
        raise ValueError("summary_only must remain true.")
    if not summary.refs_only:
        raise ValueError("refs_only must remain true.")
    if not summary.candidate_only:
        raise ValueError("candidate_only must remain true.")
    if summary.execution_enabled:
        raise ValueError("execution_enabled must remain false.")
    if summary.runtime_permission_granted:
        raise ValueError("runtime_permission_granted must remain false.")
    if summary.llm_call_enabled:
        raise ValueError("llm_call_enabled must remain false.")
    if summary.tool_execution_enabled:
        raise ValueError("tool_execution_enabled must remain false.")
    if summary.action_execution_enabled:
        raise ValueError("action_execution_enabled must remain false.")
    if summary.gateway_enabled:
        raise ValueError("gateway_enabled must remain false.")


def _summary_boundary_violations(value: Any, path: str = "$") -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_path = f"{path}.{key}"
            if _is_forbidden_summary_key(str(key)):
                violations.append(f"raw or sensitive field is forbidden at {key_path}")
            if key == "object_module" and isinstance(item, str) and _is_runtime_module(
                item
            ):
                violations.append(f"runtime object module is forbidden at {key_path}")
            violations.extend(_summary_boundary_violations(item, key_path))
        return violations
    if isinstance(value, list):
        for index, item in enumerate(value):
            violations.extend(_summary_boundary_violations(item, f"{path}[{index}]"))
        return violations
    if _is_runtime_object(value):
        violations.append(f"runtime object is forbidden at {path}")
    if isinstance(value, str) and _looks_like_raw_payload(value):
        violations.append(f"raw payload marker is forbidden at {path}")
    return violations


def _is_forbidden_summary_key(key: str) -> bool:
    lowered = key.lower()
    if lowered in SENSITIVE_KEY_EXCEPTIONS:
        return False
    return (
        lowered in FORBIDDEN_PRODUCT_GATEWAY_RESPONSE_SUMMARY_KEYS
        or lowered.endswith("_token")
        or lowered.endswith("_credential")
        or lowered.endswith("_secret")
    )


def _is_runtime_object(value: Any) -> bool:
    if value is None or isinstance(value, (str, int, float, bool, dict, list, tuple)):
        return False
    return _is_runtime_module(type(value).__module__)


def _is_runtime_module(module_name: str) -> bool:
    return module_name.startswith(FORBIDDEN_OBJECT_MODULE_PREFIXES)


def _looks_like_raw_payload(value: str) -> bool:
    lowered = value.lower()
    return any(
        marker in lowered
        for marker in (
            "raw provider response",
            "raw_response",
            "response_text",
            "system_prompt",
            "api_key",
            "raw_tool_input",
            "raw_tool_output",
        )
    )


__all__ = [
    "FORBIDDEN_OBJECT_MODULE_PREFIXES",
    "FORBIDDEN_PRODUCT_GATEWAY_RESPONSE_SUMMARY_KEYS",
    "PRODUCT_GATEWAY_RESPONSE_SUMMARY_ENTRY_KINDS",
    "PRODUCT_GATEWAY_RESPONSE_SUMMARY_PAYLOAD_TYPE",
    "PRODUCT_GATEWAY_RESPONSE_SUMMARY_PRODUCT",
    "PRODUCT_GATEWAY_RESPONSE_SUMMARY_STATUSES",
    "PRODUCT_GATEWAY_RESPONSE_SUMMARY_VERSION",
    "ProductGatewayResponseSummaryEntryKind",
    "ProductGatewayResponseSummaryRefSchema",
    "ProductGatewayResponseSummarySchema",
    "ProductGatewayResponseSummaryStatus",
    "validate_product_gateway_response_summary",
]
