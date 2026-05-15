"""Read-only ADK Tool audit view for cognition agent consumers."""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from cognition_agent.models import AgentBaseCandidate


AGENT_TOOL_AUDIT_READONLY_VIEW_VERSION = "agent_tool_audit_readonly_view_v1"
AGENT_TOOL_AUDIT_READONLY_VIEW_SOURCE = "cognition_agent.agent_tool_audit_view"

FORBIDDEN_AGENT_TOOL_AUDIT_KEYS = frozenset(
    {
        "api_key",
        "artifact_content",
        "credential",
        "credentials",
        "full_output",
        "full_response",
        "message",
        "messages",
        "prompt",
        "raw_adk_object",
        "raw_provider_payload",
        "raw_provider_response",
        "raw_response",
        "raw_tool_input",
        "raw_tool_output",
        "secret",
        "system_prompt",
        "text",
        "token",
        "tool_input",
        "tool_output",
    }
)


class AgentToolAuditReadonlyViewCandidate(AgentBaseCandidate):
    """Agent-facing read-only view over sanitized ADK Tool audit facts."""

    candidate_type: str = "agent_tool_audit_readonly_view_candidate"
    view_version: str = AGENT_TOOL_AUDIT_READONLY_VIEW_VERSION
    tool_evidence_ref: str | None = None
    tool_run_ref: str | None = None
    tool_name: str | None = None
    tool_kind: str | None = None
    status: str
    tool_call_allowed: bool = False
    tool_call_attempted: bool = False
    tool_runtime_call_performed: bool = False
    tool_confirmation_required: bool = False
    tool_confirmation_granted: bool = False
    adk_tool_confirmation_requested: bool = False
    tool_approval_ref: str | None = None
    tool_confirmation_decision_source: str | None = None
    tool_failure_type: str | None = None
    tool_input_summary: dict[str, Any] = Field(default_factory=dict)
    tool_output_summary: dict[str, Any] = Field(default_factory=dict)
    ready_for_agent_review: bool = False
    warnings: list[str] = Field(default_factory=list)
    readonly: bool = True
    candidate_only: bool = True
    execution_enabled: bool = False
    runtime_permission_granted: bool = False
    tool_execution_enabled: bool = False
    action_execution_enabled: bool = False
    runtime_container_call_enabled: bool = False
    runtime_helper_call_enabled: bool = False
    service_invoke_enabled: bool = False
    llm_call_enabled: bool = False
    cli_enabled: bool = False
    chat_enabled: bool = False
    gateway_enabled: bool = False

    @model_validator(mode="after")
    def validate_agent_tool_audit_view(
        self,
    ) -> "AgentToolAuditReadonlyViewCandidate":
        if not self.readonly:
            raise ValueError("readonly must remain true.")
        if not self.candidate_only:
            raise ValueError("candidate_only must remain true.")
        if self.execution_enabled:
            raise ValueError("execution_enabled must remain false.")
        if self.runtime_permission_granted:
            raise ValueError("runtime_permission_granted must remain false.")
        if self.tool_execution_enabled:
            raise ValueError("tool_execution_enabled must remain false.")
        if self.action_execution_enabled:
            raise ValueError("action_execution_enabled must remain false.")
        if self.runtime_container_call_enabled:
            raise ValueError("runtime_container_call_enabled must remain false.")
        if self.runtime_helper_call_enabled:
            raise ValueError("runtime_helper_call_enabled must remain false.")
        if self.service_invoke_enabled:
            raise ValueError("service_invoke_enabled must remain false.")
        if self.llm_call_enabled:
            raise ValueError("llm_call_enabled must remain false.")
        if self.cli_enabled:
            raise ValueError("cli_enabled must remain false.")
        if self.chat_enabled:
            raise ValueError("chat_enabled must remain false.")
        if self.gateway_enabled:
            raise ValueError("gateway_enabled must remain false.")
        violations = _forbidden_agent_tool_audit_key_violations(
            self.model_dump(mode="python")
        )
        if violations:
            raise ValueError("; ".join(violations))
        return self


def build_agent_tool_audit_readonly_view(
    *,
    candidate_id: str,
    tool_audit: Any,
    metadata: dict[str, Any] | None = None,
    domain_metadata: dict[str, Any] | None = None,
) -> AgentToolAuditReadonlyViewCandidate:
    """Build a non-executing view from sanitized ADK Tool audit facts."""

    audit = _safe_audit(_public_mapping(tool_audit))
    values = _agent_tool_values(audit)
    warnings = _warnings(values)
    ready_for_agent_review = not _review_blocking_warnings(warnings)
    return AgentToolAuditReadonlyViewCandidate(
        candidate_id=candidate_id,
        source=AGENT_TOOL_AUDIT_READONLY_VIEW_SOURCE,
        summary=_summary_text(
            values=values,
            ready_for_agent_review=ready_for_agent_review,
        ),
        warnings=warnings,
        ready_for_agent_review=ready_for_agent_review,
        governance_refs=_governance_refs(values),
        metadata={
            "view_semantics": "agent_tool_audit_readonly_view",
            "readonly": True,
            "candidate_only": True,
            "view_version": AGENT_TOOL_AUDIT_READONLY_VIEW_VERSION,
            "readiness_is_execution_permission": False,
            "runtime_permission_granted": False,
            "does_not_call_runtime": True,
            "does_not_call_runtime_container": True,
            "does_not_call_runtime_helper": True,
            "does_not_call_service_invoke": True,
            "does_not_call_llm": True,
            "does_not_execute_action": True,
            "does_not_execute_tool": True,
            "does_not_enable_cli": True,
            "does_not_enable_chat": True,
            "does_not_enable_gateway": True,
            "does_not_enable_tool_execution": True,
            "does_not_import_runtime_container": True,
            "does_not_import_composition": True,
            "does_not_import_adk_adapter": True,
            "does_not_import_google_adk": True,
            "does_not_import_litellm": True,
            "does_not_read_configuration_center": True,
            "does_not_store_raw_tool_input": True,
            "does_not_store_raw_tool_output": True,
            **_safe_mapping(metadata or {}, path="$.metadata"),
        },
        domain_metadata=_safe_mapping(domain_metadata or {}, path="$.domain_metadata"),
        **values,
    )


def _agent_tool_values(audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "tool_evidence_ref": _optional_string(audit.get("tool_evidence_ref")),
        "tool_run_ref": _optional_string(audit.get("tool_run_ref")),
        "tool_name": _optional_string(audit.get("tool_name")),
        "tool_kind": _optional_string(audit.get("tool_kind")),
        "status": _status(audit.get("status")),
        "tool_call_allowed": _bool(audit.get("tool_call_allowed")),
        "tool_call_attempted": _bool(audit.get("tool_call_attempted")),
        "tool_runtime_call_performed": _bool(
            audit.get("tool_runtime_call_performed")
        ),
        "tool_confirmation_required": _bool(
            audit.get("tool_confirmation_required")
        ),
        "tool_confirmation_granted": _bool(
            audit.get("tool_confirmation_granted")
        ),
        "adk_tool_confirmation_requested": _bool(
            audit.get("adk_tool_confirmation_requested")
        ),
        "tool_approval_ref": _optional_string(audit.get("tool_approval_ref")),
        "tool_confirmation_decision_source": _optional_string(
            audit.get("tool_confirmation_decision_source")
        ),
        "tool_failure_type": _optional_string(audit.get("tool_failure_type")),
        "tool_input_summary": _safe_summary(
            audit.get("tool_input_summary"),
            path="$.tool_input_summary",
        ),
        "tool_output_summary": _safe_summary(
            audit.get("tool_output_summary"),
            path="$.tool_output_summary",
        ),
    }


def _warnings(values: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if not values["tool_call_allowed"]:
        warnings.append("tool_call_not_allowed")
    if values["tool_call_allowed"] and not values["tool_call_attempted"]:
        warnings.append("tool_call_not_attempted")
    if not values["tool_runtime_call_performed"]:
        warnings.append("tool_runtime_call_not_performed")
    if (
        values["tool_confirmation_required"]
        and not values["tool_confirmation_granted"]
    ):
        warnings.append("tool_confirmation_not_granted")
    if values["tool_failure_type"]:
        warnings.append(f"tool_failure:{values['tool_failure_type']}")
    if values["status"] in {"skipped", "not_run"}:
        warnings.append(f"tool_{values['status']}")
    return warnings


def _review_blocking_warnings(warnings: list[str]) -> list[str]:
    return [
        warning
        for warning in warnings
        if warning
        in {
            "tool_call_not_allowed",
            "tool_confirmation_not_granted",
        }
    ]


def _summary_text(
    *,
    values: dict[str, Any],
    ready_for_agent_review: bool,
) -> str:
    readiness = "ready" if ready_for_agent_review else "incomplete"
    return (
        "Read-only ADK Tool audit view: "
        f"review={readiness}, status={values['status']}, "
        f"tool={values['tool_name'] or 'unknown'}, "
        f"failure_type={values['tool_failure_type'] or 'none'}. "
        "Audit view is not execution permission."
    )


def _governance_refs(values: dict[str, Any]) -> list[str]:
    refs = [
        values["tool_evidence_ref"],
        values["tool_run_ref"],
        values["tool_approval_ref"],
    ]
    return [ref for ref in refs if isinstance(ref, str) and ref]


def _public_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="python")
        if isinstance(dumped, dict):
            return dumped
    raise TypeError("ADK Tool audit input must be a dict-like public shape.")


def _safe_audit(value: dict[str, Any]) -> dict[str, Any]:
    violations = _forbidden_agent_tool_audit_key_violations(
        value,
        path="$.tool_audit",
    )
    if violations:
        raise ValueError("; ".join(violations))
    return dict(value)


def _safe_mapping(value: dict[str, Any], *, path: str) -> dict[str, Any]:
    violations = _forbidden_agent_tool_audit_key_violations(value, path=path)
    if violations:
        raise ValueError("; ".join(violations))
    return dict(value)


def _safe_summary(value: Any, *, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    violations = _forbidden_agent_tool_audit_key_violations(value, path=path)
    if violations:
        raise ValueError("; ".join(violations))
    return dict(value)


def _forbidden_agent_tool_audit_key_violations(
    value: Any,
    path: str = "$",
) -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            key_path = f"{path}.{key_text}"
            if key_text.lower() in FORBIDDEN_AGENT_TOOL_AUDIT_KEYS:
                violations.append(f"forbidden tool audit field at {key_path}")
            violations.extend(
                _forbidden_agent_tool_audit_key_violations(item, key_path)
            )
        return violations
    if isinstance(value, list):
        for index, item in enumerate(value):
            violations.extend(
                _forbidden_agent_tool_audit_key_violations(
                    item,
                    f"{path}[{index}]",
                )
            )
    return violations


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _status(value: Any) -> str:
    if isinstance(value, str) and value:
        return value
    return "unknown"


def _bool(value: Any) -> bool:
    return bool(value)
