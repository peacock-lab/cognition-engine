"""Read-only Agent shell audit view for cognition agent consumers."""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from cognition_agent.models import AgentBaseCandidate


AGENT_SHELL_AUDIT_READONLY_VIEW_VERSION = "agent_shell_audit_readonly_view_v1"
AGENT_SHELL_AUDIT_READONLY_VIEW_SOURCE = "cognition_agent.agent_shell_audit_view"

FORBIDDEN_AGENT_SHELL_AUDIT_KEYS = frozenset(
    {
        "api_key",
        "artifact_content",
        "completion",
        "credential",
        "credentials",
        "full_response",
        "message",
        "messages",
        "prompt",
        "raw_adk_event",
        "raw_adk_object",
        "raw_adk_session",
        "raw_provider_payload",
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


class AgentShellAuditReadonlyViewCandidate(AgentBaseCandidate):
    """Agent-facing read-only view over sanitized Agent shell audit facts."""

    candidate_type: str = "agent_shell_audit_readonly_view_candidate"
    view_version: str = AGENT_SHELL_AUDIT_READONLY_VIEW_VERSION
    agent_shell_evidence_ref: str | None = None
    agent_shell_run_ref: str | None = None
    agent_name: str | None = None
    agent_type: str | None = None
    app_name: str | None = None
    status: str
    event_count: int = 0
    controlled_live: bool = False
    controlled_live_smoke: bool = False
    controlled_live_smoke_enabled: bool = False
    runtime_call_performed: bool = False
    call_attempted: bool = False
    failure_type: str | None = None
    error_message_sanitized: str | None = None
    live_profile: dict[str, Any] | None = None
    ready_for_agent_review: bool = False
    warnings: list[str] = Field(default_factory=list)
    readonly: bool = True
    candidate_only: bool = True
    execution_enabled: bool = False
    runtime_permission_granted: bool = False
    agent_runtime_enabled: bool = False
    runtime_container_call_enabled: bool = False
    runtime_helper_call_enabled: bool = False
    service_invoke_enabled: bool = False
    llm_call_enabled: bool = False
    action_execution_enabled: bool = False
    cli_enabled: bool = False
    chat_enabled: bool = False
    gateway_enabled: bool = False
    tool_execution_enabled: bool = False

    @model_validator(mode="after")
    def validate_agent_shell_audit_view(
        self,
    ) -> "AgentShellAuditReadonlyViewCandidate":
        if not self.readonly:
            raise ValueError("readonly must remain true.")
        if not self.candidate_only:
            raise ValueError("candidate_only must remain true.")
        if self.execution_enabled:
            raise ValueError("execution_enabled must remain false.")
        if self.runtime_permission_granted:
            raise ValueError("runtime_permission_granted must remain false.")
        if self.agent_runtime_enabled:
            raise ValueError("agent_runtime_enabled must remain false.")
        if self.runtime_container_call_enabled:
            raise ValueError("runtime_container_call_enabled must remain false.")
        if self.runtime_helper_call_enabled:
            raise ValueError("runtime_helper_call_enabled must remain false.")
        if self.service_invoke_enabled:
            raise ValueError("service_invoke_enabled must remain false.")
        if self.llm_call_enabled:
            raise ValueError("llm_call_enabled must remain false.")
        if self.action_execution_enabled:
            raise ValueError("action_execution_enabled must remain false.")
        if self.cli_enabled:
            raise ValueError("cli_enabled must remain false.")
        if self.chat_enabled:
            raise ValueError("chat_enabled must remain false.")
        if self.gateway_enabled:
            raise ValueError("gateway_enabled must remain false.")
        if self.tool_execution_enabled:
            raise ValueError("tool_execution_enabled must remain false.")
        violations = _forbidden_agent_shell_audit_key_violations(
            self.model_dump(mode="python")
        )
        if violations:
            raise ValueError("; ".join(violations))
        return self


def build_agent_shell_audit_readonly_view(
    *,
    candidate_id: str,
    agent_shell_audit: Any,
    metadata: dict[str, Any] | None = None,
    domain_metadata: dict[str, Any] | None = None,
) -> AgentShellAuditReadonlyViewCandidate:
    """Build a non-executing view from sanitized Agent shell audit facts."""

    audit = _safe_audit(_public_mapping(agent_shell_audit))
    live_profile = _compact_live_profile(audit.get("live_profile"))
    values = _agent_shell_values(audit=audit, live_profile=live_profile)
    warnings = _warnings(values)
    ready_for_agent_review = not _review_blocking_warnings(warnings)
    return AgentShellAuditReadonlyViewCandidate(
        candidate_id=candidate_id,
        source=AGENT_SHELL_AUDIT_READONLY_VIEW_SOURCE,
        summary=_summary_text(
            values=values,
            ready_for_agent_review=ready_for_agent_review,
        ),
        warnings=warnings,
        ready_for_agent_review=ready_for_agent_review,
        governance_refs=_governance_refs(values),
        config_refs=["config:runtime:live_llm"] if live_profile is not None else [],
        metadata={
            "view_semantics": "agent_shell_audit_readonly_view",
            "readonly": True,
            "candidate_only": True,
            "view_version": AGENT_SHELL_AUDIT_READONLY_VIEW_VERSION,
            "readiness_is_execution_permission": False,
            "runtime_permission_granted": False,
            "does_not_call_runtime": True,
            "does_not_call_runtime_container": True,
            "does_not_call_runtime_helper": True,
            "does_not_call_service_invoke": True,
            "does_not_call_llm": True,
            "does_not_execute_action": True,
            "does_not_enable_cli": True,
            "does_not_enable_chat": True,
            "does_not_enable_gateway": True,
            "does_not_enable_tool_executor": True,
            "does_not_import_runtime_container": True,
            "does_not_import_composition": True,
            "does_not_import_adk_adapter": True,
            "does_not_import_google_adk": True,
            "does_not_import_litellm": True,
            "does_not_read_configuration_center": True,
            "does_not_store_prompt": True,
            "does_not_store_messages": True,
            "does_not_store_raw_response": True,
            **_safe_mapping(metadata or {}, path="$.metadata"),
        },
        domain_metadata=_safe_mapping(domain_metadata or {}, path="$.domain_metadata"),
        **values,
    )


def _agent_shell_values(
    *,
    audit: dict[str, Any],
    live_profile: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "agent_shell_evidence_ref": _optional_string(
            audit.get("agent_shell_evidence_ref")
        ),
        "agent_shell_run_ref": _optional_string(audit.get("agent_shell_run_ref")),
        "agent_name": _optional_string(audit.get("agent_name")),
        "agent_type": _optional_string(audit.get("agent_type")),
        "app_name": _optional_string(audit.get("app_name")),
        "status": _status(audit.get("status")),
        "event_count": _non_negative_int(audit.get("event_count")),
        "controlled_live": _bool(audit.get("controlled_live")),
        "controlled_live_smoke": _bool(audit.get("controlled_live_smoke")),
        "controlled_live_smoke_enabled": _bool(
            audit.get("controlled_live_smoke_enabled")
        ),
        "runtime_call_performed": _bool(audit.get("runtime_call_performed")),
        "call_attempted": _bool(audit.get("call_attempted")),
        "failure_type": _optional_string(audit.get("failure_type")),
        "error_message_sanitized": _optional_string(
            audit.get("error_message_sanitized")
        ),
        "live_profile": live_profile,
    }


def _warnings(values: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if not values["controlled_live"]:
        warnings.append("agent_shell_not_controlled_live")
    if values["controlled_live"] and values["live_profile"] is None:
        warnings.append("controlled_live_agent_shell_profile_missing")
    if values["failure_type"] == "live_disabled":
        warnings.append("controlled_live_agent_shell_live_disabled")
    if values["failure_type"]:
        warnings.append(f"agent_shell_failure:{values['failure_type']}")
    if not values["runtime_call_performed"]:
        warnings.append("agent_shell_runtime_call_not_performed")
    if values["status"] in {"skipped", "not_run"}:
        warnings.append(f"agent_shell_{values['status']}")
    return warnings


def _review_blocking_warnings(warnings: list[str]) -> list[str]:
    return [
        warning
        for warning in warnings
        if warning
        in {
            "agent_shell_not_controlled_live",
            "controlled_live_agent_shell_profile_missing",
        }
    ]


def _summary_text(
    *,
    values: dict[str, Any],
    ready_for_agent_review: bool,
) -> str:
    readiness = "ready" if ready_for_agent_review else "incomplete"
    mode = "controlled_live" if values["controlled_live"] else "not_controlled_live"
    return (
        "Read-only Agent shell audit view: "
        f"review={readiness}, status={values['status']}, "
        f"mode={mode}, failure_type={values['failure_type'] or 'none'}. "
        "Audit view is not execution permission."
    )


def _governance_refs(values: dict[str, Any]) -> list[str]:
    refs = [
        values["agent_shell_evidence_ref"],
        values["agent_shell_run_ref"],
    ]
    return [ref for ref in refs if isinstance(ref, str) and ref]


def _public_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="python")
        if isinstance(dumped, dict):
            return dumped
    raise TypeError("Agent shell audit input must be a dict-like public shape.")


def _safe_audit(value: dict[str, Any]) -> dict[str, Any]:
    violations = _forbidden_agent_shell_audit_key_violations(
        value,
        path="$.agent_shell_audit",
    )
    if violations:
        raise ValueError("; ".join(violations))
    return dict(value)


def _safe_mapping(value: dict[str, Any], *, path: str) -> dict[str, Any]:
    violations = _forbidden_agent_shell_audit_key_violations(value, path=path)
    if violations:
        raise ValueError("; ".join(violations))
    return dict(value)


def _compact_live_profile(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    allowed_keys = (
        "live_options_source",
        "live_service_profile",
        "configured_model_name",
        "timeout_seconds",
        "temperature",
        "max_tokens",
        "enabled_by_default",
    )
    profile = {
        key: item
        for key in allowed_keys
        if (item := value.get(key)) is not None
        and isinstance(item, bool | int | float | str)
    }
    violations = _forbidden_agent_shell_audit_key_violations(
        profile,
        path="$.live_profile",
    )
    if violations:
        raise ValueError("; ".join(violations))
    return profile or None


def _forbidden_agent_shell_audit_key_violations(
    value: Any,
    path: str = "$",
) -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            key_path = f"{path}.{key_text}"
            if key_text.lower() in FORBIDDEN_AGENT_SHELL_AUDIT_KEYS:
                violations.append(f"agent shell audit key is forbidden at {key_path}")
            violations.extend(
                _forbidden_agent_shell_audit_key_violations(item, key_path)
            )
    elif isinstance(value, list):
        for index, item in enumerate(value):
            violations.extend(
                _forbidden_agent_shell_audit_key_violations(item, f"{path}[{index}]")
            )
    return violations


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _status(value: Any) -> str:
    return value if isinstance(value, str) and value else "unknown"


def _non_negative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int) and value >= 0:
        return value
    return 0


def _bool(value: Any) -> bool:
    return value if isinstance(value, bool) else False
