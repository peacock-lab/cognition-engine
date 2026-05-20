"""Runtime action candidates for ADK2 WorkflowRunner governance."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from cognition_governance.action_candidate import (
    ALLOWED_RUNTIME_ACTION_KINDS,
    ActionCandidate,
    RuntimeActionKindCandidate,
    create_action_candidate,
)
from cognition_governance.human_review_outcome_candidate import (
    GovernanceOutcomeCandidate,
    GovernanceOutcomeCandidateResult,
    HumanReviewRecordCandidate,
)
from cognition_governance.models import GovernanceDecision
from cognition_governance.unified_decision_candidate import (
    POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER,
    UnifiedGovernanceDecisionCandidateResult,
)


class RuntimeActionCandidate(BaseModel):
    """ADK2 WorkflowRunner runtime action candidate wrapper."""

    model_config = ConfigDict(extra="forbid")

    action_candidate: ActionCandidate
    runtime_action_domain: str = POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER
    runtime_action_kind: RuntimeActionKindCandidate
    runtime_execution_enabled: bool = False
    requires_runtime_operator_confirmation: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeActionCandidateResult(BaseModel):
    """Internal runtime action candidate result; no runtime action is executed."""

    model_config = ConfigDict(extra="forbid")

    action_candidate: ActionCandidate
    runtime_action_candidate: RuntimeActionCandidate
    notes: list[str] = Field(default_factory=list)


def create_runtime_action_candidate(
    decision_candidate: UnifiedGovernanceDecisionCandidateResult
    | GovernanceDecision
    | dict[str, Any]
    | None = None,
    human_review_record: HumanReviewRecordCandidate | dict[str, Any] | None = None,
    outcome_candidate: GovernanceOutcomeCandidateResult
    | GovernanceOutcomeCandidate
    | dict[str, Any]
    | None = None,
    *,
    action_kind: RuntimeActionKindCandidate,
    executor: str | None = None,
    operator_notes: list[str] | None = None,
    required_confirmations: list[str] | None = None,
    domain_metadata: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> RuntimeActionCandidateResult:
    """Create a runtime action candidate without calling runtime layers."""

    result = create_action_candidate(
        decision_candidate,
        human_review_record,
        outcome_candidate,
        action_domain=POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER,
        action_kind=action_kind,
        executor=executor,
        operator_notes=operator_notes,
        required_confirmations=required_confirmations,
        domain_metadata=domain_metadata,
        metadata={
            "runtime_action_candidate": True,
            "allowed_runtime_action_kinds": list(ALLOWED_RUNTIME_ACTION_KINDS),
            "runtime_execution_enabled": False,
            "does_not_call_runtime_container": True,
            "does_not_call_composition": True,
            "does_not_call_adk_adapter": True,
            **(metadata or {}),
        },
        created_at=created_at,
    )
    runtime_action = RuntimeActionCandidate(
        action_candidate=result.action_candidate,
        runtime_action_domain=POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER,
        runtime_action_kind=action_kind,
        runtime_execution_enabled=False,
        requires_runtime_operator_confirmation=True,
        metadata={
            "candidate_only": True,
            "runtime_fix_executed": False,
            "run_config_updated": False,
            "service_bundle_updated": False,
        },
    )
    return RuntimeActionCandidateResult(
        action_candidate=result.action_candidate,
        runtime_action_candidate=runtime_action,
        notes=[
            "Internal RuntimeActionCandidate only.",
            "No runtime fix, RunConfig update, ServiceBundle update, or workflow execution is performed.",
            "Runtime operator confirmation remains outside cognition_governance.",
        ],
    )
