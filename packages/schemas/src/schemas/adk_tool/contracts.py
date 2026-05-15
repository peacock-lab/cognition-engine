"""Project-side contracts for ADK native FunctionTool facts."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


ADK_TOOL_MIN_VERSION = "2.0.0b1"

FORBIDDEN_TOOL_SUMMARY_KEYS = frozenset(
    {
        "adk_object",
        "completion",
        "function_tool",
        "message",
        "messages",
        "payload",
        "provider_response",
        "raw",
        "raw_adk_object",
        "raw_input",
        "raw_output",
        "raw_provider_response",
        "raw_response",
        "raw_tool_input",
        "raw_tool_output",
        "response",
        "response_text",
        "secret",
        "tool_confirmation",
        "tool_context",
        "tool_input",
        "tool_output",
        "token",
    }
)

FORBIDDEN_TOOL_MODULE_PREFIXES = (
    "google.adk",
    "adk_adapter",
    "composition",
    "runtime_container",
    "litellm",
)


class AdkFunctionToolAuditStatus(str, Enum):
    """Stable audit status for project-side ADK FunctionTool facts."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class AdkFunctionToolFailureType(str, Enum):
    """Stable failure categories for ADK FunctionTool product boundaries."""

    TOOL_CALL_NOT_ALLOWED = "tool_call_not_allowed"
    TOOL_CONFIRMATION_REQUIRED = "tool_confirmation_required"
    TOOL_CONFIRMATION_REJECTED = "tool_confirmation_rejected"
    TOOL_NOT_IN_LOW_RISK_ALLOWLIST = "tool_not_in_low_risk_allowlist"
    TOOL_RUNTIME_FAILURE = "tool_runtime_failure"
    TOOL_SMOKE_DISABLED = "tool_smoke_disabled"
    TOOL_SMOKE_OVERRIDE_SOURCE_MISSING = "tool_smoke_override_source_missing"
    UNKNOWN_FAILURE = "unknown_failure"


class AdkFunctionToolCapabilityOrigin(str, Enum):
    """Origin of a project-side Tool capability profile."""

    ADK_NATIVE_FUNCTION_TOOL = "adk_native_function_tool"


class ToolRiskLevel(str, Enum):
    """Project-side tool risk level."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AdkToolContractBase(BaseModel):
    """Base model for ADK Tool contract candidates."""

    model_config = ConfigDict(extra="forbid")


class AdkFunctionToolAuditContract(AdkToolContractBase):
    """Sanitized public audit facts for one ADK native FunctionTool call."""

    tool_name: str = Field(..., min_length=1)
    tool_kind: str = Field(..., min_length=1)
    status: AdkFunctionToolAuditStatus
    tool_call_allowed: bool
    tool_call_attempted: bool
    tool_runtime_call_performed: bool
    tool_confirmation_required: bool
    tool_confirmation_granted: bool
    adk_tool_confirmation_requested: bool = False
    tool_approval_ref: str | None = None
    tool_confirmation_decision_source: str | None = None
    tool_input_summary: dict[str, Any] = Field(default_factory=dict)
    tool_output_summary: dict[str, Any] = Field(default_factory=dict)
    tool_failure_type: AdkFunctionToolFailureType | None = None
    tool_evidence_ref: str | None = None
    tool_run_ref: str | None = None
    session_id: str | None = None
    artifact_delta_refs: list[str] = Field(default_factory=list)
    readonly_facts_embedded: bool = False
    does_not_store_raw_tool_input: bool = True
    does_not_store_raw_tool_output: bool = True
    raw_adk_object_included: bool = False
    metadata_keys: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_tool_audit_boundary(self) -> "AdkFunctionToolAuditContract":
        violations: list[str] = []
        if self.raw_adk_object_included:
            violations.append("raw_adk_object_included must be false.")
        if not self.does_not_store_raw_tool_input:
            violations.append("does_not_store_raw_tool_input must be true.")
        if not self.does_not_store_raw_tool_output:
            violations.append("does_not_store_raw_tool_output must be true.")
        if self.tool_runtime_call_performed and not self.tool_call_attempted:
            violations.append("tool_runtime_call_performed requires tool_call_attempted.")
        if self.tool_runtime_call_performed and not self.tool_call_allowed:
            violations.append("tool_runtime_call_performed requires tool_call_allowed.")
        if self.tool_confirmation_granted and not self.tool_confirmation_required:
            violations.append("tool_confirmation_granted requires tool_confirmation_required.")
        if self.tool_confirmation_required and self.tool_runtime_call_performed:
            if not self.tool_confirmation_granted:
                violations.append(
                    "confirmed runtime tool calls require tool_confirmation_granted."
                )
        if self.status is AdkFunctionToolAuditStatus.SUCCESS:
            if self.tool_failure_type is not None:
                violations.append("successful tool audits cannot include tool_failure_type.")
        elif self.tool_failure_type is None:
            violations.append("non-success tool audits require tool_failure_type.")
        violations.extend(
            _summary_boundary_violations(
                self.tool_input_summary,
                path="$.tool_input_summary",
            )
        )
        violations.extend(
            _summary_boundary_violations(
                self.tool_output_summary,
                path="$.tool_output_summary",
            )
        )
        if violations:
            raise ValueError("; ".join(violations))
        return self


class AdkFunctionToolRiskProfile(AdkToolContractBase):
    """Project-side risk profile for an ADK native FunctionTool capability."""

    tool_name: str = Field(..., min_length=1)
    risk_level: ToolRiskLevel
    external_side_effects: bool
    reads_files: bool = False
    writes_files: bool = False
    accesses_network: bool = False
    executes_shell: bool = False
    calls_llm: bool = False
    creates_external_resources: bool = False
    requires_confirmation: bool = True
    candidate_only: bool = True
    does_not_store_raw_tool_input: bool = True
    does_not_store_raw_tool_output: bool = True

    @model_validator(mode="after")
    def validate_low_risk_boundary(self) -> "AdkFunctionToolRiskProfile":
        violations: list[str] = []
        if self.risk_level is ToolRiskLevel.LOW:
            if self.external_side_effects:
                violations.append("low-risk tools must not have external_side_effects.")
            for field_name in (
                "reads_files",
                "writes_files",
                "accesses_network",
                "executes_shell",
                "calls_llm",
                "creates_external_resources",
            ):
                if getattr(self, field_name):
                    violations.append(f"low-risk tools must not set {field_name}.")
            if not self.requires_confirmation:
                violations.append("low-risk controlled tools require confirmation.")
            if not self.candidate_only:
                violations.append("tool risk profiles must remain candidate_only.")
            if not self.does_not_store_raw_tool_input:
                violations.append("does_not_store_raw_tool_input must be true.")
            if not self.does_not_store_raw_tool_output:
                violations.append("does_not_store_raw_tool_output must be true.")
        if violations:
            raise ValueError("; ".join(violations))
        return self


class AdkFunctionToolCapabilityProfile(AdkToolContractBase):
    """Project-side capability profile for an ADK native FunctionTool."""

    tool_name: str = Field(..., min_length=1)
    tool_kind: str = Field(..., min_length=1)
    capability_origin: AdkFunctionToolCapabilityOrigin
    adk_min_version: str = ADK_TOOL_MIN_VERSION
    require_confirmation_supported: bool = True
    low_risk_allowlist_required: bool = True
    controlled_live_supported: bool = True
    no_live_supported: bool = True
    risk_profile: AdkFunctionToolRiskProfile
    raw_adk_object_included: bool = False
    contract_candidate_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_capability_boundary(self) -> "AdkFunctionToolCapabilityProfile":
        violations: list[str] = []
        if self.adk_min_version != ADK_TOOL_MIN_VERSION:
            violations.append(f"adk_min_version must be {ADK_TOOL_MIN_VERSION}.")
        if self.raw_adk_object_included:
            violations.append("raw_adk_object_included must be false.")
        if self.capability_origin is not AdkFunctionToolCapabilityOrigin.ADK_NATIVE_FUNCTION_TOOL:
            violations.append("capability_origin must be adk_native_function_tool.")
        if self.tool_name != self.risk_profile.tool_name:
            violations.append("tool_name must match risk_profile.tool_name.")
        if self.controlled_live_supported and not self.require_confirmation_supported:
            violations.append(
                "controlled_live_supported requires require_confirmation_supported."
            )
        if violations:
            raise ValueError("; ".join(violations))
        return self


def _summary_boundary_violations(value: Any, path: str) -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            key_path = f"{path}.{key_text}"
            if key_text.lower() in FORBIDDEN_TOOL_SUMMARY_KEYS:
                violations.append(f"raw tool payload key is forbidden at {key_path}")
            if key_text == "object_module" and isinstance(item, str):
                if item.startswith(FORBIDDEN_TOOL_MODULE_PREFIXES):
                    violations.append(f"runtime object module is forbidden at {key_path}")
            violations.extend(_summary_boundary_violations(item, key_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            violations.extend(_summary_boundary_violations(item, f"{path}[{index}]"))
    elif _is_runtime_object(value):
        violations.append(f"runtime object is forbidden at {path}")
    return violations


def _is_runtime_object(value: Any) -> bool:
    if value is None or isinstance(value, (str, int, float, bool, list, tuple, dict)):
        return False
    return type(value).__module__.startswith(FORBIDDEN_TOOL_MODULE_PREFIXES)
