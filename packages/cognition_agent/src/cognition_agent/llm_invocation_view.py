"""Read-only LLM invocation summary views for the cognition agent shell."""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from cognition_agent.models import AgentBaseCandidate


LLM_INVOCATION_SUMMARY_VERSION = "llm_invocation_summary_v1"
LLM_INVOCATION_RESULT_SUMMARY_SOURCE = "schemas.llm_invocation.LlmInvocationResult"
LLM_CALL_OBSERVATION_SUMMARY_SOURCE = (
    "observability_hub.llm_invocation.LlmCallObservationCandidate"
)

FORBIDDEN_LLM_SUMMARY_KEYS = frozenset(
    {
        "api_key",
        "completion",
        "full_response",
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


class AgentLlmInvocationSummaryCandidate(AgentBaseCandidate):
    """Agent-facing read-only view over sanitized LLM invocation facts."""

    candidate_type: str = "agent_llm_invocation_summary_candidate"
    summary_version: str = LLM_INVOCATION_SUMMARY_VERSION
    summary_source: str
    request_id: str
    model_name: str
    provider: str
    backend_provider: str | None = None
    route_kind: str | None = None
    route_target: str | None = None
    call_attempted: bool = False
    call_allowed: bool = False
    runtime_call_performed: bool = False
    success: bool = False
    response_non_empty: bool = False
    sanitized_response_length: int | None = None
    sanitized_response_preview: str | None = None
    failure_type: str | None = None
    error_message_sanitized: str | None = None
    governance_decision_ref: str | None = None
    readonly: bool = True
    candidate_only: bool = True
    execution_enabled: bool = False
    agent_runtime_enabled: bool = False
    llm_call_enabled: bool = False
    runtime_helper_enabled: bool = False
    service_invoke_enabled: bool = False

    @model_validator(mode="after")
    def validate_llm_invocation_summary(
        self,
    ) -> "AgentLlmInvocationSummaryCandidate":
        if not self.readonly:
            raise ValueError("readonly must remain true.")
        if not self.candidate_only:
            raise ValueError("candidate_only must remain true.")
        if self.execution_enabled:
            raise ValueError("execution_enabled must remain false.")
        if self.agent_runtime_enabled:
            raise ValueError("agent_runtime_enabled must remain false.")
        if self.llm_call_enabled:
            raise ValueError("llm_call_enabled must remain false.")
        if self.runtime_helper_enabled:
            raise ValueError("runtime_helper_enabled must remain false.")
        if self.service_invoke_enabled:
            raise ValueError("service_invoke_enabled must remain false.")
        violations = _forbidden_summary_key_violations(self.model_dump(mode="python"))
        if violations:
            raise ValueError("; ".join(violations))
        return self


def build_agent_llm_invocation_summary_from_public_shape(
    *,
    candidate_id: str,
    invocation_summary: Any,
    metadata: dict[str, Any] | None = None,
    domain_metadata: dict[str, Any] | None = None,
) -> AgentLlmInvocationSummaryCandidate:
    """Build a read-only agent summary from public sanitized LLM facts."""

    data = _public_mapping(invocation_summary)
    normalized = (
        _normalize_invocation_result(data)
        if "route_facts" in data
        else _normalize_observation_candidate(data)
    )
    safe_metadata = _safe_metadata(normalized.pop("metadata", {}))
    summary = _summary_text(normalized)

    return AgentLlmInvocationSummaryCandidate(
        candidate_id=candidate_id,
        source=normalized["summary_source"],
        summary=summary,
        metadata={
            "view_semantics": "agent_readonly_llm_invocation_summary",
            "readonly": True,
            "summary_version": LLM_INVOCATION_SUMMARY_VERSION,
            "summary_source": normalized["summary_source"],
            "does_not_store_prompt": True,
            "does_not_store_full_response": True,
            "does_not_store_raw_provider_response": True,
            "does_not_call_runtime": True,
            "does_not_call_runtime_container": True,
            "does_not_call_llm": True,
            "does_not_call_service_invoke": True,
            "does_not_import_observability_hub": True,
            "source_metadata": safe_metadata,
            **_safe_metadata(metadata or {}),
        },
        domain_metadata=_safe_metadata(domain_metadata or {}),
        **normalized,
    )


def build_agent_llm_invocation_summary_from_invocation_result(
    *,
    candidate_id: str,
    invocation_result: Any,
    metadata: dict[str, Any] | None = None,
    domain_metadata: dict[str, Any] | None = None,
) -> AgentLlmInvocationSummaryCandidate:
    """Build an agent summary from a sanitized invocation result shape."""

    return build_agent_llm_invocation_summary_from_public_shape(
        candidate_id=candidate_id,
        invocation_summary=invocation_result,
        metadata=metadata,
        domain_metadata=domain_metadata,
    )


def build_agent_llm_invocation_summary_from_observation_candidate(
    *,
    candidate_id: str,
    observation_candidate: Any,
    metadata: dict[str, Any] | None = None,
    domain_metadata: dict[str, Any] | None = None,
) -> AgentLlmInvocationSummaryCandidate:
    """Build an agent summary from a sanitized observation candidate shape."""

    return build_agent_llm_invocation_summary_from_public_shape(
        candidate_id=candidate_id,
        invocation_summary=observation_candidate,
        metadata=metadata,
        domain_metadata=domain_metadata,
    )


def _normalize_invocation_result(data: dict[str, Any]) -> dict[str, Any]:
    route_facts = _mapping(data.get("route_facts"))
    route_metadata = _mapping(route_facts.get("metadata"))
    governance_precondition = _mapping(data.get("governance_precondition"))
    return {
        "summary_source": LLM_INVOCATION_RESULT_SUMMARY_SOURCE,
        "request_id": _required_string(data.get("request_id"), "request_id"),
        "model_name": _required_string(route_facts.get("model_name"), "model_name"),
        "provider": _required_string(route_facts.get("provider"), "provider"),
        "backend_provider": _optional_string(route_metadata.get("backend_provider")),
        "route_kind": _optional_string(route_metadata.get("route_kind")),
        "route_target": _optional_string(route_metadata.get("route_target")),
        "call_attempted": _bool(data.get("call_attempted")),
        "call_allowed": _bool(data.get("call_allowed")),
        "runtime_call_performed": _bool(data.get("runtime_call_performed")),
        "success": _bool(data.get("success")),
        "response_non_empty": _bool(data.get("response_non_empty")),
        "sanitized_response_length": _optional_int(
            data.get("sanitized_response_length")
        ),
        "sanitized_response_preview": _optional_string(
            data.get("sanitized_response_preview")
        ),
        "failure_type": _enum_string(data.get("failure_type")),
        "error_message_sanitized": _optional_string(
            data.get("error_message_sanitized")
        ),
        "governance_decision_ref": _optional_string(
            governance_precondition.get("governance_decision_ref")
        ),
        "metadata": _mapping(data.get("metadata")),
    }


def _normalize_observation_candidate(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary_source": LLM_CALL_OBSERVATION_SUMMARY_SOURCE,
        "request_id": _required_string(data.get("request_id"), "request_id"),
        "model_name": _required_string(data.get("model_name"), "model_name"),
        "provider": _required_string(data.get("provider"), "provider"),
        "backend_provider": _optional_string(data.get("backend_provider")),
        "route_kind": _optional_string(data.get("route_kind")),
        "route_target": _optional_string(data.get("route_target")),
        "call_attempted": _bool(data.get("call_attempted")),
        "call_allowed": _bool(data.get("call_allowed")),
        "runtime_call_performed": _bool(data.get("runtime_call_performed")),
        "success": _bool(data.get("success")),
        "response_non_empty": _bool(data.get("response_non_empty")),
        "sanitized_response_length": _optional_int(
            data.get("sanitized_response_length")
        ),
        "sanitized_response_preview": _optional_string(
            data.get("sanitized_response_preview")
        ),
        "failure_type": _optional_string(data.get("failure_type")),
        "error_message_sanitized": _optional_string(
            data.get("error_message_sanitized")
        ),
        "governance_decision_ref": _optional_string(
            data.get("governance_decision_ref")
        ),
        "metadata": _mapping(data.get("metadata")),
    }


def _public_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="python")
        if isinstance(dumped, dict):
            return dumped
    raise TypeError("LLM invocation summary input must be a dict-like public shape.")


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_metadata(value: dict[str, Any]) -> dict[str, Any]:
    violations = _forbidden_summary_key_violations(value, path="$.metadata")
    if violations:
        raise ValueError("; ".join(violations))
    return dict(value)


def _required_string(value: Any, field_name: str) -> str:
    if isinstance(value, str) and value:
        return value
    raise ValueError(f"{field_name} is required.")


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _enum_string(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    enum_value = getattr(value, "value", None)
    return enum_value if isinstance(enum_value, str) else None


def _bool(value: Any) -> bool:
    return value if isinstance(value, bool) else False


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _summary_text(values: dict[str, Any]) -> str:
    status = "success" if values["success"] else (values["failure_type"] or "unknown")
    call_state = (
        "performed" if values["runtime_call_performed"] else "not_performed"
    )
    return (
        "Read-only LLM invocation summary: "
        f"request_id={values['request_id']}, provider={values['provider']}, "
        f"model={values['model_name']}, status={status}, call={call_state}."
    )


def _forbidden_summary_key_violations(value: Any, path: str = "$") -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            key_path = f"{path}.{key_text}"
            if key_text.lower() in FORBIDDEN_LLM_SUMMARY_KEYS:
                violations.append(f"LLM summary payload key is forbidden at {key_path}")
            violations.extend(_forbidden_summary_key_violations(item, key_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            violations.extend(_forbidden_summary_key_violations(item, f"{path}[{index}]"))
    return violations
