"""Governance candidate public data shells.

These models describe candidate data shapes only. They are not formal
GovernanceDecision, GovernanceOutcome, Action, ReleaseAction, or RuntimeAction
contracts.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


PolicyDomainCandidate = Literal[
    "adk2_workflow_runner",
    "release_governance",
    "product_agent_output_governance",
]
ActionDomainCandidate = Literal["adk2_workflow_runner", "release_governance"]

FORBIDDEN_RUNTIME_OBJECT_MODULE_PREFIXES = (
    "google.adk",
    "adk_adapter",
    "composition",
    "runtime_container",
)

SENSITIVE_SCHEMA_KEYS = frozenset(
    {
        "command",
        "command_output",
        "command_outputs",
        "credential",
        "credentials",
        "env",
        "fallback_token",
        "raw",
        "raw_output",
        "secret",
        "stderr",
        "stdout",
        "token",
    }
)

SENSITIVE_KEY_EXCEPTIONS = frozenset(
    {
        "raw_output_digest",
        "sensitive_fields_omitted",
        "token_presence_check_mode",
    }
)


class GovernanceCandidateBaseModel(BaseModel):
    """Base model for public governance candidate shells."""

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_public_candidate_boundary(self) -> "GovernanceCandidateBaseModel":
        """Reject sensitive raw fields and runtime object leakage."""

        violations = _candidate_boundary_violations(self.model_dump(mode="python"))
        if violations:
            raise ValueError("; ".join(violations))
        return self


class GovernanceEvidenceSchemaCandidate(GovernanceCandidateBaseModel):
    """Public candidate shell for governance evidence."""

    evidence_id: str = Field(..., min_length=1)
    evidence_type: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)
    content_ref: str | None = None
    domain_metadata: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GovernanceCaseSchemaCandidate(GovernanceCandidateBaseModel):
    """Public candidate shell for a governance case."""

    case_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    case_type: str = Field(..., min_length=1)
    subject: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    policy_refs: list[str] = Field(default_factory=list)
    domain_metadata: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GovernancePolicySetCandidateSchema(GovernanceCandidateBaseModel):
    """Public candidate shell for a policy set candidate."""

    policy_set_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    policies: list[str] = Field(default_factory=list)
    candidate_scope: str = "governance_policy_set_candidate"
    policy_domain: PolicyDomainCandidate | None = None
    policy_status: Literal["candidate_only"] = "candidate_only"
    policy_execution_enabled: bool = False
    public_contract: bool = False
    domain_metadata: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_policy_set_candidate(self) -> "GovernancePolicySetCandidateSchema":
        if self.policy_execution_enabled:
            raise ValueError("policy_execution_enabled must remain false.")
        return self


class GovernanceDecisionCandidateSchema(GovernanceCandidateBaseModel):
    """Public candidate shell for a governance decision candidate."""

    decision_id: str = Field(..., min_length=1)
    case_id: str = Field(..., min_length=1)
    decision: str = Field(..., min_length=1)
    rationale: str = Field(..., min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    policy_set_id: str | None = None
    candidate_scope: str = "governance_decision_candidate"
    policy_domain: PolicyDomainCandidate | None = None
    decision_semantics: Literal["candidate_only"] = "candidate_only"
    formal_decision_enabled: bool = False
    policy_execution_enabled: bool = False
    governance_outcome_enabled: bool = False
    blocked_formal_decision_reasons: list[str] = Field(default_factory=list)
    domain_metadata: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_decision_candidate(self) -> "GovernanceDecisionCandidateSchema":
        if self.formal_decision_enabled:
            raise ValueError("formal_decision_enabled must remain false.")
        if self.policy_execution_enabled:
            raise ValueError("policy_execution_enabled must remain false.")
        if self.governance_outcome_enabled:
            raise ValueError("governance_outcome_enabled must remain false.")
        return self


class HumanReviewRecordCandidateSchema(GovernanceCandidateBaseModel):
    """Public candidate shell for a human review record."""

    review_id: str = Field(..., min_length=1)
    decision_candidate_id: str = Field(..., min_length=1)
    case_id: str = Field(..., min_length=1)
    reviewer: str = Field(..., min_length=1)
    review_result: str = Field(..., min_length=1)
    review_reasons: list[str] = Field(default_factory=list)
    required_followups: list[str] = Field(default_factory=list)
    candidate_scope: str = "human_review_record_candidate"
    policy_domain: PolicyDomainCandidate | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GovernanceOutcomeCandidateSchema(GovernanceCandidateBaseModel):
    """Public candidate shell for a governance outcome candidate."""

    outcome_candidate_id: str = Field(..., min_length=1)
    decision_candidate_id: str = Field(..., min_length=1)
    human_review_id: str = Field(..., min_length=1)
    case_id: str = Field(..., min_length=1)
    policy_domain: PolicyDomainCandidate | None = None
    outcome_semantics: Literal["candidate_only"] = "candidate_only"
    formal_decision_required: bool = True
    formal_outcome_enabled: bool = False
    release_action_enabled: bool = False
    status_candidate: str = "open"
    summary: str = Field(..., min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    blocked_formal_outcome_reasons: list[str] = Field(default_factory=list)
    domain_metadata: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_outcome_candidate(self) -> "GovernanceOutcomeCandidateSchema":
        if not self.formal_decision_required:
            raise ValueError("formal_decision_required must remain true.")
        if self.formal_outcome_enabled:
            raise ValueError("formal_outcome_enabled must remain false.")
        if self.release_action_enabled:
            raise ValueError("release_action_enabled must remain false.")
        return self


class ActionCandidateSchema(GovernanceCandidateBaseModel):
    """Public candidate shell for a governance action candidate."""

    action_candidate_id: str = Field(..., min_length=1)
    decision_candidate_id: str | None = None
    human_review_id: str | None = None
    outcome_candidate_id: str | None = None
    case_id: str | None = None
    action_domain: ActionDomainCandidate
    action_kind: str = Field(..., min_length=1)
    action_semantics: Literal["candidate_only"] = "candidate_only"
    execution_enabled: bool = False
    requires_operator_confirmation: bool = True
    reviewer: str | None = None
    executor: str | None = None
    operator_notes: list[str] = Field(default_factory=list)
    blocked_execution_reasons: list[str] = Field(default_factory=list)
    required_confirmations: list[str] = Field(default_factory=list)
    source_decision_kind: str | None = None
    source_review_result: str | None = None
    source_outcome_status: str | None = None
    domain_metadata: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_action_candidate(self) -> "ActionCandidateSchema":
        if self.execution_enabled:
            raise ValueError("execution_enabled must remain false.")
        if not self.requires_operator_confirmation:
            raise ValueError("requires_operator_confirmation must remain true.")
        if self.reviewer and self.executor and self.reviewer == self.executor:
            raise ValueError("reviewer and executor must be separate.")
        return self


class ReleaseActionCandidateSchema(ActionCandidateSchema):
    """Public candidate shell for a release action candidate."""

    action_domain: Literal["release_governance"] = "release_governance"


class RuntimeActionCandidateSchema(ActionCandidateSchema):
    """Public candidate shell for a runtime action candidate."""

    action_domain: Literal["adk2_workflow_runner"] = "adk2_workflow_runner"
    runtime_action_domain: Literal["adk2_workflow_runner"] = "adk2_workflow_runner"
    runtime_action_kind: str | None = None
    runtime_execution_enabled: bool = False
    requires_runtime_operator_confirmation: bool = True

    @model_validator(mode="after")
    def validate_runtime_action_candidate(self) -> "RuntimeActionCandidateSchema":
        if self.runtime_execution_enabled:
            raise ValueError("runtime_execution_enabled must remain false.")
        if not self.requires_runtime_operator_confirmation:
            raise ValueError("requires_runtime_operator_confirmation must remain true.")
        return self


def _candidate_boundary_violations(value: Any, path: str = "$") -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_path = f"{path}.{key}"
            if _is_sensitive_key(str(key)):
                violations.append(f"sensitive field is forbidden at {key_path}")
            if key == "object_module" and isinstance(item, str) and _is_runtime_module(item):
                violations.append(f"runtime object module is forbidden at {key_path}")
            violations.extend(_candidate_boundary_violations(item, key_path))
        return violations
    if isinstance(value, list):
        for index, item in enumerate(value):
            violations.extend(_candidate_boundary_violations(item, f"{path}[{index}]"))
        return violations
    if _is_runtime_object(value):
        violations.append(f"runtime object is forbidden at {path}")
    return violations


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    if lowered in SENSITIVE_KEY_EXCEPTIONS:
        return False
    return (
        lowered in SENSITIVE_SCHEMA_KEYS
        or lowered.endswith("_token")
        or lowered.endswith("_credential")
        or lowered.endswith("_secret")
    )


def _is_runtime_object(value: Any) -> bool:
    if value is None or isinstance(value, (str, int, float, bool, dict, list, tuple)):
        return False
    return _is_runtime_module(type(value).__module__)


def _is_runtime_module(module_name: str) -> bool:
    return module_name.startswith(FORBIDDEN_RUNTIME_OBJECT_MODULE_PREFIXES)
