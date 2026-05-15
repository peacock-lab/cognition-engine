"""Governed LLM invocation data contracts."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from schemas.model_routing import ModelRouteFacts


FORBIDDEN_LLM_INVOCATION_METADATA_KEYS = frozenset(
    {
        "api_key",
        "completion",
        "message",
        "messages",
        "prompt",
        "raw_provider_response",
        "raw_response",
        "response",
        "response_text",
        "secret",
        "system_prompt",
        "text",
        "token",
    }
)

FORBIDDEN_LLM_INVOCATION_MODULE_PREFIXES = (
    "google.adk",
    "litellm",
    "adk_adapter",
    "runtime_container",
)


class LlmInvocationFailureType(str, Enum):
    """Stable failure categories for governed LLM invocation attempts."""

    GOVERNANCE_BLOCKED = "governance_blocked"
    GOVERNANCE_NEEDS_EVIDENCE = "governance_needs_evidence"
    ROUTE_FACTS_INVALID = "route_facts_invalid"
    LIVE_DISABLED = "live_disabled"
    DEPENDENCY_FAILURE = "dependency_failure"
    ROUTE_CONSTRUCTION_FAILURE = "route_construction_failure"
    LIVE_CALL_FAILURE = "live_call_failure"
    TIMEOUT_FAILURE = "timeout_failure"
    UNSUPPORTED_API_FAILURE = "unsupported_api_failure"
    ENVIRONMENT_FAILURE = "environment_failure"
    MODEL_MISSING = "model_missing"
    UNKNOWN_FAILURE = "unknown_failure"


class LlmGovernancePrecondition(BaseModel):
    """Governance precondition required before an LLM invocation."""

    model_config = ConfigDict(extra="forbid")

    allowed: bool
    reason: str = Field(..., min_length=1)
    decision: str | None = None
    governance_decision_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_no_runtime_payloads(self) -> "LlmGovernancePrecondition":
        violations = _metadata_boundary_violations(self.metadata)
        if violations:
            raise ValueError("; ".join(violations))
        return self


class LlmInvocationRequest(BaseModel):
    """Public request facts for a governed LLM invocation boundary."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=1)
    route_facts: ModelRouteFacts
    governance_precondition: LlmGovernancePrecondition
    prompt_ref: str | None = None
    prompt_preview_sanitized: str | None = Field(default=None, max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_request_boundary(self) -> "LlmInvocationRequest":
        violations = []
        if self.route_facts.runtime_call_performed:
            violations.append("route_facts must remain non-executing.")
        if self.route_facts.direct_litellm_completion:
            violations.append("route_facts must not represent direct LiteLLM completion.")
        if self.route_facts.governance_direct_model_call:
            violations.append("route_facts must not represent governance model calls.")
        violations.extend(_metadata_boundary_violations(self.metadata))
        if violations:
            raise ValueError("; ".join(violations))
        return self


class LlmInvocationResult(BaseModel):
    """Sanitized result facts for a governed LLM invocation attempt."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=1)
    route_facts: ModelRouteFacts
    governance_precondition: LlmGovernancePrecondition
    call_attempted: bool = False
    call_allowed: bool = False
    runtime_call_performed: bool = False
    success: bool = False
    response_non_empty: bool = False
    sanitized_response_length: int | None = Field(default=None, ge=0)
    sanitized_response_preview: str | None = Field(default=None, max_length=120)
    latency_ms: int | None = Field(default=None, ge=0)
    failure_type: LlmInvocationFailureType | None = None
    error_message_sanitized: str | None = Field(default=None, max_length=240)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_result_boundary(self) -> "LlmInvocationResult":
        violations: list[str] = []
        if self.success:
            if not self.call_attempted:
                violations.append("success requires call_attempted.")
            if not self.call_allowed:
                violations.append("success requires call_allowed.")
            if not self.runtime_call_performed:
                violations.append("success requires runtime_call_performed.")
            if self.failure_type is not None:
                violations.append("success cannot include failure_type.")
        else:
            if self.failure_type is None:
                violations.append("failed or blocked results require failure_type.")
        if self.runtime_call_performed and not self.call_attempted:
            violations.append("runtime_call_performed requires call_attempted.")
        if self.call_allowed and not self.governance_precondition.allowed:
            violations.append("call_allowed requires governance_precondition.allowed.")
        if not self.call_allowed and self.runtime_call_performed:
            violations.append("runtime_call_performed requires call_allowed.")
        if self.sanitized_response_preview is not None and self.sanitized_response_length is None:
            violations.append("sanitized_response_preview requires sanitized_response_length.")
        violations.extend(_metadata_boundary_violations(self.metadata))
        if violations:
            raise ValueError("; ".join(violations))
        return self


def _metadata_boundary_violations(value: Any, path: str = "$.metadata") -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            key_path = f"{path}.{key_text}"
            if key_text.lower() in FORBIDDEN_LLM_INVOCATION_METADATA_KEYS:
                violations.append(f"LLM invocation payload key is forbidden at {key_path}")
            if key_text == "object_module" and isinstance(item, str):
                if item.startswith(FORBIDDEN_LLM_INVOCATION_MODULE_PREFIXES):
                    violations.append(f"runtime object module is forbidden at {key_path}")
            violations.extend(_metadata_boundary_violations(item, key_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            violations.extend(_metadata_boundary_violations(item, f"{path}[{index}]"))
    return violations
