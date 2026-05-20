"""Public controlled execution contracts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CONTROLLED_EXECUTION_REQUEST_PAYLOAD_TYPE = "controlled_execution_request"
CONTROLLED_EXECUTION_REQUEST_VERSION = "controlled_execution_request_v1"
CONTROLLED_EXECUTION_RUNTIME_SUMMARY_PAYLOAD_TYPE = (
    "controlled_execution_runtime_summary"
)
CONTROLLED_EXECUTION_RUNTIME_SUMMARY_VERSION = (
    "controlled_execution_runtime_summary_v1"
)

ControlledExecutionRuntimeSummaryStatus = Literal[
    "success",
    "blocked",
    "failed",
    "provider_failed",
]

CONTROLLED_EXECUTION_RUNTIME_SUMMARY_STATUSES = frozenset(
    {
        "success",
        "blocked",
        "failed",
        "provider_failed",
    }
)

FORBIDDEN_CONTROLLED_EXECUTION_PUBLIC_KEYS = frozenset(
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

FORBIDDEN_CONTROLLED_EXECUTION_REQUEST_KEYS = FORBIDDEN_CONTROLLED_EXECUTION_PUBLIC_KEYS
FORBIDDEN_CONTROLLED_EXECUTION_RUNTIME_SUMMARY_KEYS = (
    FORBIDDEN_CONTROLLED_EXECUTION_PUBLIC_KEYS
)

FORBIDDEN_CONTROLLED_EXECUTION_OBJECT_MODULE_PREFIXES = (
    "google.adk",
    "adk_adapter",
    "runtime_container",
    "composition",
    "litellm",
)


class ControlledExecutionRequestSchema(BaseModel):
    """Public sanitized request accepted by controlled execution services."""

    model_config = ConfigDict(extra="forbid")

    payload_type: Literal["controlled_execution_request"] = (
        CONTROLLED_EXECUTION_REQUEST_PAYLOAD_TYPE
    )
    payload_version: Literal["controlled_execution_request_v1"] = (
        CONTROLLED_EXECUTION_REQUEST_VERSION
    )
    runtime_id: str = Field(..., min_length=1)
    invocation_id: str | None = None
    workflow_id: str | None = None
    workflow_name: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    operator_approved: bool = False
    approval_ref: str | None = None
    audit_ref: str | None = None
    sanitized_evidence_ref: str | None = None
    governance_summary_output_ref: str | None = None
    request_live_llm: bool = False
    request_ollama: bool = False
    allow_live_llm: bool = False
    allow_ollama: bool = False
    live_llm_approval_ref: str | None = None
    allow_tool_confirmation: bool | None = None
    tool_confirmation_approval_ref: str | None = None
    tool_confirmation_decision_source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_public_boundary(self) -> "ControlledExecutionRequestSchema":
        violations = _request_boundary_violations(self.model_dump(mode="python"))
        if violations:
            raise ValueError("; ".join(violations))
        return self

    def to_runtime_mapping(self) -> dict[str, Any]:
        """Return the runtime-service request mapping shape."""

        return controlled_execution_request_to_mapping(self)


class ControlledExecutionRuntimeSummarySchema(BaseModel):
    """Public sanitized summary returned by controlled execution services."""

    model_config = ConfigDict(extra="forbid")

    payload_type: Literal["controlled_execution_runtime_summary"] = (
        CONTROLLED_EXECUTION_RUNTIME_SUMMARY_PAYLOAD_TYPE
    )
    payload_version: Literal["controlled_execution_runtime_summary_v1"] = (
        CONTROLLED_EXECUTION_RUNTIME_SUMMARY_VERSION
    )
    runtime_id: str | None = None
    invocation_id: str | None = None
    workflow_id: str | None = None
    execution_mode: str | None = None
    status: ControlledExecutionRuntimeSummaryStatus = "failed"
    controlled_run: bool = False
    productized_controlled_run: bool = False
    sanitized: bool = True
    adk_run_allowed: bool = False
    adk_run_performed: bool = False
    execution_performed: bool = False
    live_llm_allowed: bool = False
    live_llm_call_performed: bool = False
    ollama_allowed: bool = False
    ollama_call_performed: bool = False
    llm_invocation_call_allowed: bool | None = None
    llm_invocation_call_attempted: bool | None = None
    llm_invocation_runtime_call_performed: bool | None = None
    llm_invocation_failure_type: str | None = None
    tool_runtime_call_performed: bool | None = None
    tool_status: str | None = None
    tool_failure_type: str | None = None
    observability_source: str | None = None
    sanitized_evidence_ref: str | None = None
    audit_ref: str | None = None
    governance_summary_payload_ref: str | None = None
    governance_summary_output_ref: str | None = None
    tool_evidence_ref: str | None = None
    tool_run_ref: str | None = None
    llm_invocation_result_ref: str | None = None
    llm_invocation_observation_ref: str | None = None
    llm_invocation_summary_ref: str | None = None
    sanitized_response_display: str | None = None
    sanitized_response_preview: str | None = None
    final_preflight: dict[str, Any] | None = None
    controlled_live_llm_preflight: dict[str, Any] | None = None
    lifecycle_facts: dict[str, Any] | None = None
    run_config_service_bundle_facts: dict[str, Any] | None = None
    blocking_reasons: tuple[str, ...] = Field(default_factory=tuple)
    warnings: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_public_boundary(
        self,
    ) -> "ControlledExecutionRuntimeSummarySchema":
        if not self.sanitized:
            raise ValueError("sanitized must remain true.")
        if self.status == "blocked" and not self.blocking_reasons:
            raise ValueError("blocked runtime summaries require blocking_reasons.")
        violations = _summary_boundary_violations(self.model_dump(mode="python"))
        if violations:
            raise ValueError("; ".join(violations))
        return self

    def to_runtime_mapping(self) -> dict[str, Any]:
        """Return the CLI-compatible sanitized runtime mapping."""

        return controlled_execution_runtime_summary_to_mapping(self)


def validate_controlled_execution_request(
    request: ControlledExecutionRequestSchema | Mapping[str, Any],
) -> ControlledExecutionRequestSchema:
    """Validate a controlled execution request public contract."""

    if isinstance(request, ControlledExecutionRequestSchema):
        return request
    return ControlledExecutionRequestSchema.model_validate(dict(request))


def controlled_execution_request_to_mapping(
    request: ControlledExecutionRequestSchema | Mapping[str, Any],
) -> dict[str, Any]:
    """Return a JSON-ready controlled execution request mapping."""

    normalized_request = validate_controlled_execution_request(request)
    result: dict[str, Any] = {
        "runtime_id": normalized_request.runtime_id,
        "invocation_id": normalized_request.invocation_id,
        "workflow_id": normalized_request.workflow_id,
        "workflow_name": normalized_request.workflow_name,
        "input_payload": dict(normalized_request.input_payload),
        "operator_approved": normalized_request.operator_approved,
        "approval_ref": normalized_request.approval_ref,
        "audit_ref": normalized_request.audit_ref,
        "sanitized_evidence_ref": normalized_request.sanitized_evidence_ref,
        "governance_summary_output_ref": (
            normalized_request.governance_summary_output_ref
        ),
        "request_live_llm": normalized_request.request_live_llm,
        "request_ollama": normalized_request.request_ollama,
        "allow_live_llm": normalized_request.allow_live_llm,
        "allow_ollama": normalized_request.allow_ollama,
        "live_llm_approval_ref": normalized_request.live_llm_approval_ref,
        "allow_tool_confirmation": normalized_request.allow_tool_confirmation,
        "tool_confirmation_approval_ref": (
            normalized_request.tool_confirmation_approval_ref
        ),
        "tool_confirmation_decision_source": (
            normalized_request.tool_confirmation_decision_source
        ),
        "metadata": dict(normalized_request.metadata),
    }
    return {key: value for key, value in result.items() if value is not None}


def validate_controlled_execution_runtime_summary(
    summary: ControlledExecutionRuntimeSummarySchema | Mapping[str, Any],
) -> ControlledExecutionRuntimeSummarySchema:
    """Validate a controlled execution runtime summary public contract."""

    if isinstance(summary, ControlledExecutionRuntimeSummarySchema):
        return summary
    return ControlledExecutionRuntimeSummarySchema.model_validate(dict(summary))


def controlled_execution_runtime_summary_to_mapping(
    summary: ControlledExecutionRuntimeSummarySchema | Mapping[str, Any],
) -> dict[str, Any]:
    """Return a JSON-ready sanitized runtime summary mapping."""

    normalized_summary = validate_controlled_execution_runtime_summary(summary)
    result: dict[str, Any] = {
        "runtime_id": normalized_summary.runtime_id,
        "invocation_id": normalized_summary.invocation_id,
        "workflow_id": normalized_summary.workflow_id,
        "execution_mode": normalized_summary.execution_mode,
        "status": normalized_summary.status,
        "controlled_run": normalized_summary.controlled_run,
        "productized_controlled_run": (
            normalized_summary.productized_controlled_run
        ),
        "sanitized": normalized_summary.sanitized,
        "adk_run_allowed": normalized_summary.adk_run_allowed,
        "adk_run_performed": normalized_summary.adk_run_performed,
        "execution_performed": normalized_summary.execution_performed,
        "live_llm_allowed": normalized_summary.live_llm_allowed,
        "live_llm_call_performed": normalized_summary.live_llm_call_performed,
        "ollama_allowed": normalized_summary.ollama_allowed,
        "ollama_call_performed": normalized_summary.ollama_call_performed,
        "tool_status": normalized_summary.tool_status,
        "tool_failure_type": normalized_summary.tool_failure_type,
        "tool_runtime_call_performed": (
            normalized_summary.tool_runtime_call_performed
        ),
        "observability_source": normalized_summary.observability_source,
        "sanitized_evidence_ref": normalized_summary.sanitized_evidence_ref,
        "audit_ref": normalized_summary.audit_ref,
        "governance_summary_payload_ref": (
            normalized_summary.governance_summary_payload_ref
        ),
        "governance_summary_output_ref": (
            normalized_summary.governance_summary_output_ref
        ),
        "tool_evidence_ref": normalized_summary.tool_evidence_ref,
        "tool_run_ref": normalized_summary.tool_run_ref,
        "llm_invocation_result_ref": normalized_summary.llm_invocation_result_ref,
        "llm_invocation_observation_ref": (
            normalized_summary.llm_invocation_observation_ref
        ),
        "llm_invocation_summary_ref": normalized_summary.llm_invocation_summary_ref,
        "sanitized_response_display": normalized_summary.sanitized_response_display,
        "sanitized_response_preview": normalized_summary.sanitized_response_preview,
        "final_preflight": normalized_summary.final_preflight,
        "controlled_live_llm_preflight": (
            normalized_summary.controlled_live_llm_preflight
        ),
        "lifecycle_facts": normalized_summary.lifecycle_facts,
        "run_config_service_bundle_facts": (
            normalized_summary.run_config_service_bundle_facts
        ),
        "blocking_reasons": list(normalized_summary.blocking_reasons),
        "warnings": list(normalized_summary.warnings),
    }
    optional_fields = {
        "llm_invocation_call_allowed": (
            normalized_summary.llm_invocation_call_allowed
        ),
        "llm_invocation_call_attempted": (
            normalized_summary.llm_invocation_call_attempted
        ),
        "llm_invocation_runtime_call_performed": (
            normalized_summary.llm_invocation_runtime_call_performed
        ),
        "llm_invocation_failure_type": (
            normalized_summary.llm_invocation_failure_type
        ),
    }
    result.update(
        {key: value for key, value in optional_fields.items() if value is not None}
    )
    return {key: value for key, value in result.items() if value is not None}


def _summary_boundary_violations(value: Any) -> list[str]:
    return _controlled_execution_boundary_violations(
        value,
        contract_name="controlled execution runtime summary",
        forbidden_keys=FORBIDDEN_CONTROLLED_EXECUTION_RUNTIME_SUMMARY_KEYS,
    )


def _request_boundary_violations(value: Any) -> list[str]:
    return _controlled_execution_boundary_violations(
        value,
        contract_name="controlled execution request",
        forbidden_keys=FORBIDDEN_CONTROLLED_EXECUTION_REQUEST_KEYS,
    )


def _controlled_execution_boundary_violations(
    value: Any,
    *,
    contract_name: str,
    forbidden_keys: frozenset[str],
) -> list[str]:
    return [
        f"{contract_name} contains forbidden payload at {path}."
        for path, item in _walk(value)
        if _is_forbidden_controlled_execution_payload(
            path,
            item,
            forbidden_keys=forbidden_keys,
        )
    ]


def _walk(value: Any, path: str = "$") -> list[tuple[str, Any]]:
    items = [(path, value)]
    if isinstance(value, dict):
        for key, item in value.items():
            items.extend(_walk(item, f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            items.extend(_walk(item, f"{path}[{index}]"))
    return items


def _is_forbidden_runtime_summary_payload(path: str, value: Any) -> bool:
    return _is_forbidden_controlled_execution_payload(
        path,
        value,
        forbidden_keys=FORBIDDEN_CONTROLLED_EXECUTION_RUNTIME_SUMMARY_KEYS,
    )


def _is_forbidden_controlled_execution_payload(
    path: str,
    value: Any,
    *,
    forbidden_keys: frozenset[str],
) -> bool:
    key = path.rsplit(".", maxsplit=1)[-1].lower()
    if key in forbidden_keys:
        return True
    if isinstance(value, dict):
        module_name = value.get("object_module")
        return isinstance(module_name, str) and module_name.startswith(
            FORBIDDEN_CONTROLLED_EXECUTION_OBJECT_MODULE_PREFIXES
        )
    if value is None or isinstance(value, (str, int, float, bool, list, tuple, dict)):
        return False
    return type(value).__module__.startswith(
        FORBIDDEN_CONTROLLED_EXECUTION_OBJECT_MODULE_PREFIXES
    )


__all__ = [
    "CONTROLLED_EXECUTION_REQUEST_PAYLOAD_TYPE",
    "CONTROLLED_EXECUTION_REQUEST_VERSION",
    "CONTROLLED_EXECUTION_RUNTIME_SUMMARY_PAYLOAD_TYPE",
    "CONTROLLED_EXECUTION_RUNTIME_SUMMARY_STATUSES",
    "CONTROLLED_EXECUTION_RUNTIME_SUMMARY_VERSION",
    "ControlledExecutionRequestSchema",
    "ControlledExecutionRuntimeSummarySchema",
    "ControlledExecutionRuntimeSummaryStatus",
    "controlled_execution_request_to_mapping",
    "controlled_execution_runtime_summary_to_mapping",
    "validate_controlled_execution_request",
    "validate_controlled_execution_runtime_summary",
]
