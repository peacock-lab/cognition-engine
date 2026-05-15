"""Governance candidate configuration views.

These views express candidate configuration boundaries only. They do not load
configuration files, consume config payloads, or execute release/runtime actions.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


FORBIDDEN_RELEASE_ACTIONS = frozenset(
    {
        "release",
        "block",
        "pass",
        "publish",
        "upload",
        "twine_upload",
        "git_tag",
        "git_push",
        "github_release",
        "trusted_publishing",
    }
)

FORBIDDEN_RUNTIME_ACTIONS = frozenset(
    {
        "runtime_fix",
        "run_config_update",
        "service_bundle_update",
        "execute_workflow",
    }
)

DEFAULT_RELEASE_CONFIRMATIONS = (
    "human_review_record_candidate",
    "governance_outcome_candidate",
    "operator_confirmation",
    "release_workflow_or_cli_confirmation",
)

DEFAULT_RUNTIME_CONFIRMATIONS = (
    "human_review_record_candidate",
    "governance_outcome_candidate",
    "runtime_operator_confirmation",
)


class GovernanceCandidateConfigBaseModel(BaseModel):
    """Base model for non-executing governance candidate config views."""

    model_config = ConfigDict(extra="forbid")

    config_view_semantics: Literal["candidate_only"] = "candidate_only"
    formal_decision_enabled: bool = False
    formal_outcome_enabled: bool = False
    policy_execution_enabled: bool = False
    execution_enabled: bool = False
    release_action_enabled: bool = False
    runtime_execution_enabled: bool = False
    requires_operator_confirmation: bool = True
    forbidden_release_actions: tuple[str, ...] = Field(
        default_factory=lambda: tuple(sorted(FORBIDDEN_RELEASE_ACTIONS))
    )
    forbidden_runtime_actions: tuple[str, ...] = Field(
        default_factory=lambda: tuple(sorted(FORBIDDEN_RUNTIME_ACTIONS))
    )

    @model_validator(mode="after")
    def validate_candidate_invariants(self) -> "GovernanceCandidateConfigBaseModel":
        if self.formal_decision_enabled:
            raise ValueError("formal_decision_enabled must remain false.")
        if self.formal_outcome_enabled:
            raise ValueError("formal_outcome_enabled must remain false.")
        if self.policy_execution_enabled:
            raise ValueError("policy_execution_enabled must remain false.")
        if self.execution_enabled:
            raise ValueError("execution_enabled must remain false.")
        if self.release_action_enabled:
            raise ValueError("release_action_enabled must remain false.")
        if self.runtime_execution_enabled:
            raise ValueError("runtime_execution_enabled must remain false.")
        if not self.requires_operator_confirmation:
            raise ValueError("requires_operator_confirmation must remain true.")
        return self


class AdkRunConfigViewCandidate(GovernanceCandidateConfigBaseModel):
    """Candidate view for ADK RunConfig options."""

    max_llm_calls: int | None = Field(default=None, gt=0)
    response_modalities: tuple[str, ...] | None = None
    save_input_blobs_as_artifacts: bool | None = None
    support_cfc: bool | None = None
    streaming_mode: Literal["none", "sse", "bidi"] | None = None
    get_session_num_recent_events: int | None = Field(default=None, ge=0)
    get_session_after_timestamp: float | None = None
    custom_metadata_keys: tuple[str, ...] = Field(default_factory=tuple)


class ServiceBundleViewCandidate(GovernanceCandidateConfigBaseModel):
    """Candidate view for ADK service bundle source policy."""

    source: Literal["in_memory", "provided_services", "safe_context_ref"] = "in_memory"
    app_name: str = "cognition_engine_adk_adapter"
    user_id: str = "cognition-engine-adk-user"
    workflow_name: str | None = None
    artifact_service_source: str | None = None
    session_service_source: str | None = None
    event_service_source: str | None = None
    service_lifecycle_policy: str = "candidate_review_only"
    external_service_instance_allowed: bool = False

    @model_validator(mode="after")
    def validate_service_bundle_candidate(self) -> "ServiceBundleViewCandidate":
        if self.external_service_instance_allowed:
            raise ValueError("external_service_instance_allowed must remain false.")
        return self


class ReleaseGovernanceConfigViewCandidate(GovernanceCandidateConfigBaseModel):
    """Candidate view for release governance configuration policy."""

    release_target: str | None = None
    target_version: str | None = None
    phase: str | None = None
    provider_allowlist: tuple[str, ...] = Field(default_factory=tuple)
    token_presence_check_mode: str = "presence_only"
    trusted_publishing_check_mode: str = "configuration_check_only"
    required_evidence_providers: tuple[str, ...] = Field(default_factory=tuple)
    reviewer_role_ref: str | None = None
    operator_role_ref: str | None = None
    executor_role_ref: str | None = None
    required_confirmations: tuple[str, ...] = DEFAULT_RELEASE_CONFIRMATIONS
    credential_value_allowed: bool = False

    @model_validator(mode="after")
    def validate_release_config_candidate(self) -> "ReleaseGovernanceConfigViewCandidate":
        if self.credential_value_allowed:
            raise ValueError("credential_value_allowed must remain false.")
        return self


class ActionCandidateConfigViewCandidate(GovernanceCandidateConfigBaseModel):
    """Candidate view for action candidate policy."""

    allowed_action_domains: tuple[str, ...] = (
        "adk2_workflow_runner",
        "release_governance",
    )
    allowed_action_kinds: tuple[str, ...] = Field(default_factory=tuple)
    required_confirmations_by_domain: dict[str, tuple[str, ...]] = Field(
        default_factory=lambda: {
            "release_governance": DEFAULT_RELEASE_CONFIRMATIONS,
            "adk2_workflow_runner": DEFAULT_RUNTIME_CONFIRMATIONS,
        }
    )
    reviewer_executor_separation_required: bool = True
    requires_decision_candidate_ref: bool = True
    requires_human_review_ref: bool = True
    requires_outcome_candidate_ref: bool = True

    @model_validator(mode="after")
    def validate_action_candidate_config(self) -> "ActionCandidateConfigViewCandidate":
        if not self.reviewer_executor_separation_required:
            raise ValueError("reviewer_executor_separation_required must remain true.")
        if not self.requires_decision_candidate_ref:
            raise ValueError("requires_decision_candidate_ref must remain true.")
        if not self.requires_human_review_ref:
            raise ValueError("requires_human_review_ref must remain true.")
        if not self.requires_outcome_candidate_ref:
            raise ValueError("requires_outcome_candidate_ref must remain true.")
        forbidden = set(self.allowed_action_kinds) & (
            FORBIDDEN_RELEASE_ACTIONS | FORBIDDEN_RUNTIME_ACTIONS
        )
        if forbidden:
            raise ValueError(
                "allowed_action_kinds must not include forbidden actions: "
                + ", ".join(sorted(forbidden))
            )
        return self
