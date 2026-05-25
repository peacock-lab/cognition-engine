"""Product-level request and response contracts for product gateway entries."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


FORBIDDEN_PRODUCT_GATEWAY_KEYS = frozenset(
    {
        "adk_object",
        "artifact_content",
        "credential",
        "function_tool",
        "live_model_payload",
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
        "token",
        "tool_context",
        "tool_input",
        "tool_output",
        "user_message",
    }
)

FORBIDDEN_PRODUCT_GATEWAY_MODULE_PREFIXES = (
    "google.adk",
    "adk_adapter",
    "litellm",
)


class ProductGatewayEntryKind(str, Enum):
    """Product entry kinds normalized by the product gateway."""

    COGNITION_RUN = "cognition_run"
    CONTROLLED_LIVE = "controlled_live"
    AGENT_SHELL = "agent_shell"
    TOOL_SMOKE = "tool_smoke"
    TASK_WORKFLOW_ROUTE = "operation_flow_route"
    TASK_WORKFLOW_EXECUTION = "operation_flow_execution"
    EXTERNAL_READONLY_FETCH = "external_readonly_fetch"
    EXTERNAL_READONLY_REFS = "external_readonly_refs"
    EXTERNAL_READONLY_ASK = "external_readonly_ask"


class ProductGatewayExecutionMode(str, Enum):
    """Execution modes requested at the product entry boundary."""

    NO_LIVE = "no_live"
    CONTROLLED_LIVE = "controlled_live"
    SMOKE = "smoke"
    PREFLIGHT_ONLY = "preflight_only"


class ProductGatewayStatus(str, Enum):
    """Product gateway response status."""

    SUCCESS = "success"
    BLOCKED = "blocked"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProductGatewayContractBase(BaseModel):
    """Base class for product gateway contracts."""

    model_config = ConfigDict(extra="forbid")


class ProductGatewayRef(ProductGatewayContractBase):
    """Sanitized reference exposed at the product entry boundary."""

    ref: str = Field(..., min_length=1)
    kind: str = Field(..., min_length=1)
    purpose: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_ref_boundary(self) -> "ProductGatewayRef":
        _raise_if_raw_payload_found(
            self.metadata,
            field_name="metadata",
        )
        return self


class ProductGatewayInputRefs(ProductGatewayContractBase):
    """Input references accepted by the product gateway."""

    operator_approval_ref: str | None = None
    audit_ref: str | None = None
    sanitized_evidence_ref: str | None = None
    governance_summary_ref: str | None = None
    additional_refs: list[ProductGatewayRef] = Field(default_factory=list)


class ProductGatewayOutputRefs(ProductGatewayContractBase):
    """Output references returned by the product gateway."""

    output_ref: str | None = None
    governance_summary_ref: str | None = None
    evidence_refs: list[ProductGatewayRef] = Field(default_factory=list)
    audit_refs: list[ProductGatewayRef] = Field(default_factory=list)
    agent_advice_refs: list[ProductGatewayRef] = Field(default_factory=list)
    tool_audit_refs: list[ProductGatewayRef] = Field(default_factory=list)
    additional_refs: list[ProductGatewayRef] = Field(default_factory=list)


class ProductGatewayOperatorApprovalRef(ProductGatewayContractBase):
    """Operator approval facts expressed as product entry refs."""

    approved: bool = False
    approval_ref: str | None = None
    audit_ref: str | None = None
    decision_source: str | None = None

    @model_validator(mode="after")
    def validate_approval_ref(self) -> "ProductGatewayOperatorApprovalRef":
        if self.approved and not self.approval_ref:
            raise ValueError("approved product requests require approval_ref.")
        return self


class ProductGatewayLiveOptions(ProductGatewayContractBase):
    """Explicit live options carried by product entry requests."""

    request_live_llm: bool = False
    request_ollama: bool = False
    allow_live_llm: bool = False
    allow_ollama: bool = False
    live_llm_approval_ref: str | None = None
    override_source: str | None = None

    @model_validator(mode="after")
    def validate_live_options(self) -> "ProductGatewayLiveOptions":
        if self.allow_live_llm and not self.live_llm_approval_ref:
            raise ValueError("allow_live_llm requires live_llm_approval_ref.")
        if self.allow_ollama and not self.live_llm_approval_ref:
            raise ValueError("allow_ollama requires live_llm_approval_ref.")
        if (self.request_live_llm or self.request_ollama) and not self.override_source:
            raise ValueError("live requests require override_source.")
        return self


class ProductGatewayRequest(ProductGatewayContractBase):
    """Product-level request object normalized by product gateway entries."""

    request_id: str = Field(..., min_length=1)
    entry_kind: ProductGatewayEntryKind
    execution_mode: ProductGatewayExecutionMode
    input_payload: dict[str, Any] = Field(default_factory=dict)
    input_refs: ProductGatewayInputRefs = Field(default_factory=ProductGatewayInputRefs)
    operator_approval: ProductGatewayOperatorApprovalRef = Field(
        default_factory=ProductGatewayOperatorApprovalRef
    )
    live_options: ProductGatewayLiveOptions = Field(default_factory=ProductGatewayLiveOptions)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_request_boundary(self) -> "ProductGatewayRequest":
        _raise_if_raw_payload_found(
            self.input_payload,
            field_name="input_payload",
        )
        _raise_if_raw_payload_found(
            self.metadata,
            field_name="metadata",
        )
        return self


class ProductGatewayResponse(ProductGatewayContractBase):
    """Product-level response object returned by product gateway entries."""

    request_id: str = Field(..., min_length=1)
    entry_kind: ProductGatewayEntryKind
    status: ProductGatewayStatus
    exit_code: int | None = None
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    output_refs: ProductGatewayOutputRefs = Field(default_factory=ProductGatewayOutputRefs)
    governance_summary_ref: str | None = None
    evidence_refs: list[ProductGatewayRef] = Field(default_factory=list)
    audit_refs: list[ProductGatewayRef] = Field(default_factory=list)
    agent_advice_refs: list[ProductGatewayRef] = Field(default_factory=list)
    tool_audit_refs: list[ProductGatewayRef] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_response_boundary(self) -> "ProductGatewayResponse":
        _raise_if_raw_payload_found(
            self.metadata,
            field_name="metadata",
        )
        if self.status is ProductGatewayStatus.BLOCKED and not self.blocking_reasons:
            raise ValueError("blocked product gateway responses require blocking_reasons.")
        return self


def _raise_if_raw_payload_found(value: Any, *, field_name: str) -> None:
    violations = [
        f"{field_name} contains forbidden raw payload at {path}."
        for path, item in _walk(value)
        if _is_raw_payload(path, item)
    ]
    if violations:
        raise ValueError("; ".join(violations))


def _walk(value: Any, path: str = "$") -> list[tuple[str, Any]]:
    items = [(path, value)]
    if isinstance(value, dict):
        for key, item in value.items():
            items.extend(_walk(item, f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            items.extend(_walk(item, f"{path}[{index}]"))
    return items


def _is_raw_payload(path: str, value: Any) -> bool:
    key = path.rsplit(".", maxsplit=1)[-1].lower()
    if key in FORBIDDEN_PRODUCT_GATEWAY_KEYS:
        return True
    if isinstance(value, dict):
        module_name = value.get("object_module")
        return isinstance(module_name, str) and module_name.startswith(
            FORBIDDEN_PRODUCT_GATEWAY_MODULE_PREFIXES
        )
    if value is None or isinstance(value, (str, int, float, bool, list, tuple, dict)):
        return False
    return type(value).__module__.startswith(FORBIDDEN_PRODUCT_GATEWAY_MODULE_PREFIXES)


__all__ = [
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
]
