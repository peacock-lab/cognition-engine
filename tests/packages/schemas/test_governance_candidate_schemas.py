import pytest
from pydantic import ValidationError

from schemas.governance_candidate import (
    ActionCandidateSchema,
    GovernanceCaseSchemaCandidate,
    GovernanceDecisionCandidateSchema,
    GovernanceEvidenceSchemaCandidate,
    GovernanceOutcomeCandidateSchema,
    GovernancePolicySetCandidateSchema,
    HumanReviewRecordCandidateSchema,
    ReleaseActionCandidateSchema,
    RuntimeActionCandidateSchema,
)


def test_governance_candidate_schemas_construct_minimal_shells() -> None:
    evidence = GovernanceEvidenceSchemaCandidate(
        evidence_id="ev-1",
        evidence_type="release_check_output",
        source="release_governance.script_output",
        summary="Release evidence summary.",
        metadata={"raw_output_digest": "sha256:abc"},
    )
    case = GovernanceCaseSchemaCandidate(
        case_id="case-1",
        title="Release governance review",
        case_type="release_governance",
        evidence_refs=[evidence.evidence_id],
    )
    policy = GovernancePolicySetCandidateSchema(
        policy_set_id="policy-1",
        name="Release policy candidate",
        policy_domain="release_governance",
    )
    decision = GovernanceDecisionCandidateSchema(
        decision_id="decision-1",
        case_id=case.case_id,
        decision="continue",
        rationale="Candidate can continue to later review.",
        evidence_ids=[evidence.evidence_id],
        policy_set_id=policy.policy_set_id,
        policy_domain="release_governance",
    )

    assert decision.decision_semantics == "candidate_only"
    assert decision.formal_decision_enabled is False
    assert decision.policy_execution_enabled is False


def test_review_outcome_and_action_candidate_schemas_keep_candidate_boundaries() -> None:
    review = HumanReviewRecordCandidateSchema(
        review_id="review-1",
        decision_candidate_id="decision-1",
        case_id="case-1",
        reviewer="reviewer-a",
        review_result="accept_candidate",
    )
    outcome = GovernanceOutcomeCandidateSchema(
        outcome_candidate_id="outcome-1",
        decision_candidate_id="decision-1",
        human_review_id=review.review_id,
        case_id="case-1",
        summary="Outcome candidate only.",
    )
    action = ActionCandidateSchema(
        action_candidate_id="action-1",
        action_domain="release_governance",
        action_kind="prepare_release",
        decision_candidate_id="decision-1",
        human_review_id=review.review_id,
        outcome_candidate_id=outcome.outcome_candidate_id,
        reviewer="reviewer-a",
        executor="executor-b",
    )

    assert outcome.outcome_semantics == "candidate_only"
    assert outcome.formal_outcome_enabled is False
    assert action.action_semantics == "candidate_only"
    assert action.execution_enabled is False
    assert action.requires_operator_confirmation is True


def test_action_candidate_schema_rejects_execution_and_actor_overlap() -> None:
    with pytest.raises(ValidationError):
        ActionCandidateSchema(
            action_candidate_id="action-1",
            action_domain="release_governance",
            action_kind="prepare_release",
            execution_enabled=True,
        )

    with pytest.raises(ValidationError):
        ActionCandidateSchema(
            action_candidate_id="action-2",
            action_domain="release_governance",
            action_kind="prepare_release",
            reviewer="same",
            executor="same",
        )


def test_schema_candidate_rejects_sensitive_raw_fields() -> None:
    with pytest.raises(ValidationError):
        GovernanceEvidenceSchemaCandidate(
            evidence_id="ev-1",
            evidence_type="release_check_output",
            source="release_governance.script_output",
            summary="Release evidence summary.",
            metadata={"stdout": "raw output", "token": "secret"},
        )


def test_schema_candidate_rejects_adk_native_object_marker() -> None:
    with pytest.raises(ValidationError):
        GovernanceEvidenceSchemaCandidate(
            evidence_id="ev-1",
            evidence_type="adk_workflow_runner_execution",
            source="observability_hub.adk_workflow_runner_evidence",
            summary="ADK evidence summary.",
            metadata={"run_config": {"object_module": "google.adk.runners"}},
        )


def test_release_and_runtime_action_wrappers_are_candidate_only() -> None:
    release_action = ReleaseActionCandidateSchema(
        action_candidate_id="release-action-1",
        action_kind="prepare_release",
    )
    runtime_action = RuntimeActionCandidateSchema(
        action_candidate_id="runtime-action-1",
        action_kind="prepare_run_config_update",
        runtime_action_kind="prepare_run_config_update",
    )

    assert release_action.action_domain == "release_governance"
    assert runtime_action.action_domain == "adk2_workflow_runner"
    assert runtime_action.runtime_execution_enabled is False


def test_product_agent_output_governance_policy_domain_is_candidate_only() -> None:
    policy = GovernancePolicySetCandidateSchema(
        policy_set_id="policy-product-agent-output-governance",
        name="Product-agent output governance policy candidate",
        candidate_scope="product_agent_output_governance_decision_candidate",
        policy_domain="product_agent_output_governance",
        domain_metadata={
            "summary_only": True,
            "refs_only": True,
            "candidate_only": True,
        },
    )
    decision = GovernanceDecisionCandidateSchema(
        decision_id="decision-product-agent-output-1",
        case_id="case-product-agent-output-1",
        decision="continue",
        rationale="Candidate can continue to product-agent output review.",
        candidate_scope="product_agent_output_governance_decision_candidate",
        policy_domain="product_agent_output_governance",
        policy_set_id=policy.policy_set_id,
        domain_metadata={
            "product_gateway_request_id": "request-product-agent-output-1",
            "summary_only": True,
            "refs_only": True,
            "candidate_only": True,
        },
    )
    review = HumanReviewRecordCandidateSchema(
        review_id="review-product-agent-output-1",
        decision_candidate_id=decision.decision_id,
        case_id=decision.case_id,
        reviewer="governance-reviewer",
        review_result="accept_candidate",
        candidate_scope="product_agent_output_governance_decision_candidate",
        policy_domain="product_agent_output_governance",
    )
    outcome = GovernanceOutcomeCandidateSchema(
        outcome_candidate_id="outcome-product-agent-output-1",
        decision_candidate_id=decision.decision_id,
        human_review_id=review.review_id,
        case_id=decision.case_id,
        policy_domain="product_agent_output_governance",
        summary="Product-agent output outcome candidate only.",
        domain_metadata={
            "agent_advice_candidate_id": "agent-advice-1",
            "summary_only": True,
            "refs_only": True,
            "candidate_only": True,
        },
    )

    assert policy.policy_status == "candidate_only"
    assert policy.policy_execution_enabled is False
    assert decision.decision_semantics == "candidate_only"
    assert decision.formal_decision_enabled is False
    assert decision.policy_execution_enabled is False
    assert decision.governance_outcome_enabled is False
    assert review.policy_domain == "product_agent_output_governance"
    assert outcome.outcome_semantics == "candidate_only"
    assert outcome.formal_outcome_enabled is False
    assert outcome.release_action_enabled is False


def test_product_agent_output_governance_is_not_an_action_domain() -> None:
    with pytest.raises(ValidationError):
        ActionCandidateSchema(
            action_candidate_id="action-product-agent-output-1",
            action_domain="product_agent_output_governance",
            action_kind="prepare_product_agent_output_action",
        )
