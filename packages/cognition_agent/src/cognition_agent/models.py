"""Candidate-only cognition agent data shells."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


AgentCandidateStatus = Literal["candidate_only", "recorded", "deferred", "blocked"]

FORBIDDEN_RUNTIME_OBJECT_MODULE_PREFIXES = (
    "google.adk",
    "adk_adapter",
    "composition",
    "runtime_container",
    "cognition_governance",
    "observability_hub",
)

SENSITIVE_AGENT_KEYS = frozenset(
    {
        "credential",
        "credentials",
        "env",
        "raw",
        "raw_output",
        "secret",
        "stderr",
        "stdout",
        "token",
        "tool_state",
    }
)

SENSITIVE_KEY_EXCEPTIONS = frozenset(
    {
        "raw_output_digest",
        "sensitive_fields_omitted",
        "token_presence_check_mode",
    }
)


class AgentBaseCandidate(BaseModel):
    """Base model for non-executing agent candidates."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(..., min_length=1)
    candidate_type: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)
    status: AgentCandidateStatus = "candidate_only"
    governance_refs: list[str] = Field(default_factory=list)
    config_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    domain_metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_candidate_boundary(self) -> "AgentBaseCandidate":
        """Keep agent candidates non-executing and safe to expose."""

        violations = _candidate_boundary_violations(self.model_dump(mode="python"))
        if violations:
            raise ValueError("; ".join(violations))
        return self


class AgentTaskCandidate(AgentBaseCandidate):
    """Candidate task seen by the cognition agent shell; it is not executed."""

    candidate_type: Literal["agent_task_candidate"] = "agent_task_candidate"
    task_intent: str | None = None
    execution_enabled: bool = False
    requires_governance_view: bool = True

    @model_validator(mode="after")
    def validate_task_candidate(self) -> "AgentTaskCandidate":
        if self.execution_enabled:
            raise ValueError("execution_enabled must remain false.")
        if not self.requires_governance_view:
            raise ValueError("requires_governance_view must remain true.")
        return self


class AgentInteractionCandidate(AgentBaseCandidate):
    """Candidate interaction record; it is not a chat session."""

    candidate_type: Literal["agent_interaction_candidate"] = (
        "agent_interaction_candidate"
    )
    interaction_kind: str = "candidate_note"
    chat_enabled: bool = False
    llm_call_enabled: bool = False

    @model_validator(mode="after")
    def validate_interaction_candidate(self) -> "AgentInteractionCandidate":
        if self.chat_enabled:
            raise ValueError("chat_enabled must remain false.")
        if self.llm_call_enabled:
            raise ValueError("llm_call_enabled must remain false.")
        return self


class AgentContextCandidate(AgentBaseCandidate):
    """Read-only context candidate for the cognition agent shell."""

    candidate_type: Literal["agent_context_candidate"] = "agent_context_candidate"
    context_refs: list[str] = Field(default_factory=list)
    readonly: bool = True
    secret_context_allowed: bool = False

    @model_validator(mode="after")
    def validate_context_candidate(self) -> "AgentContextCandidate":
        if not self.readonly:
            raise ValueError("readonly must remain true.")
        if self.secret_context_allowed:
            raise ValueError("secret_context_allowed must remain false.")
        return self


class AgentCapabilityViewCandidate(AgentBaseCandidate):
    """Candidate capability view; it does not expose executable tools."""

    candidate_type: Literal["agent_capability_view_candidate"] = (
        "agent_capability_view_candidate"
    )
    capability_refs: list[str] = Field(default_factory=list)
    tool_execution_enabled: bool = False
    agent_runtime_enabled: bool = False
    gateway_enabled: bool = False

    @model_validator(mode="after")
    def validate_capability_view_candidate(self) -> "AgentCapabilityViewCandidate":
        if self.tool_execution_enabled:
            raise ValueError("tool_execution_enabled must remain false.")
        if self.agent_runtime_enabled:
            raise ValueError("agent_runtime_enabled must remain false.")
        if self.gateway_enabled:
            raise ValueError("gateway_enabled must remain false.")
        return self


def _candidate_boundary_violations(value: Any, path: str = "$") -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_path = f"{path}.{key}"
            if _is_sensitive_key(str(key)):
                violations.append(f"sensitive field is forbidden at {key_path}")
            if key == "object_module" and isinstance(item, str) and _is_forbidden_module(
                item
            ):
                violations.append(f"forbidden object module at {key_path}")
            violations.extend(_candidate_boundary_violations(item, key_path))
        return violations
    if isinstance(value, list):
        for index, item in enumerate(value):
            violations.extend(_candidate_boundary_violations(item, f"{path}[{index}]"))
        return violations
    if _is_forbidden_runtime_object(value):
        violations.append(f"forbidden runtime object at {path}")
    return violations


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    if lowered in SENSITIVE_KEY_EXCEPTIONS:
        return False
    return (
        lowered in SENSITIVE_AGENT_KEYS
        or lowered.endswith("_token")
        or lowered.endswith("_credential")
        or lowered.endswith("_secret")
    )


def _is_forbidden_runtime_object(value: Any) -> bool:
    if value is None or isinstance(value, (str, int, float, bool, dict, list, tuple)):
        return False
    return _is_forbidden_module(type(value).__module__)


def _is_forbidden_module(module_name: str) -> bool:
    return module_name.startswith(FORBIDDEN_RUNTIME_OBJECT_MODULE_PREFIXES)
