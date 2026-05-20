from __future__ import annotations

import re
from pathlib import Path

from cognition_governance import (
    ADK_WORKFLOW_RUNNER_POLICY_SET_ID,
    ALLOWED_UNIFIED_DECISION_KINDS,
    POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER,
    POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE,
    POLICY_DOMAIN_RELEASE_GOVERNANCE,
    PRODUCT_AGENT_OUTPUT_GOVERNANCE_POLICY_SET_ID,
    RELEASE_GOVERNANCE_POLICY_SET_ID,
    GovernanceCase,
    GovernanceDecision,
    GovernanceEvidence,
    UnifiedGovernanceDecisionCandidateResult,
    UnifiedGovernancePolicySetCandidate,
    build_adk_workflow_runner_policy_set_candidate,
    build_product_agent_output_governance_policy_set_candidate,
    build_release_governance_policy_set_candidate,
    build_unified_policy_set_candidate,
    make_unified_governance_decision_candidate,
    map_agent_task_advice_payload_to_governance_evidence,
    map_product_agent_output_evidence_to_governance_case,
    map_product_gateway_response_summary_to_governance_evidence,
    map_release_check_output_to_governance_evidence,
    map_release_evidence_to_governance_case,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
GOVERNANCE_SOURCE_ROOT = REPO_ROOT / "packages" / "cognition_governance" / "src"


def _adk_evidence() -> GovernanceEvidence:
    return GovernanceEvidence(
        evidence_id="evidence-unified-adk2-001",
        evidence_type="adk_workflow_runner_execution",
        source="observability_hub.adk_workflow_runner_evidence",
        summary="ADK2 WorkflowRunner evidence for unified candidate tests.",
        metadata={
            "runtime_kind": "adk2_workflow_runner",
            "workflow_name": "unified-adk2-workflow",
            "status": "success",
            "run_config": {"mapped_fields": ["max_llm_calls"]},
            "service_bundle": {"source": "in_memory"},
            "artifact_summary": {"artifact_count": 1},
            "session_summary": {"session_id": "session-unified-adk2-001"},
            "event_summary": {"event_count": 2},
            "warnings": [],
        },
    )


def _adk_case() -> GovernanceCase:
    return GovernanceCase(
        case_id="case-unified-adk2-001",
        title="ADK2 unified governance review",
        case_type="adk_workflow_runner_governance_review",
        subject="unified-adk2-workflow",
        context={
            "workflow_name": "unified-adk2-workflow",
            "risk_level": "low",
        },
        evidence_refs=["evidence-unified-adk2-001"],
        policy_refs=[ADK_WORKFLOW_RUNNER_POLICY_SET_ID],
        metadata={
            "findings": [
                {
                    "code": "ADK2_WORKFLOW_RUNNER_CHAIN_OBSERVED",
                    "severity": "info",
                    "message": "ADK2 WorkflowRunner evidence candidate was observed.",
                }
            ],
            "required_followups": [],
        },
    )


def _release_evidence() -> list[GovernanceEvidence]:
    return [
        map_release_check_output_to_governance_evidence(
            {
                "script_name": "check_public_surface.py",
                "target_version": "0.6.0",
                "phase": "pre-release",
                "final_status": "PASS",
                "failure_codes": [],
            }
        ),
        map_release_check_output_to_governance_evidence(
            {
                "script_name": "check_public_workflow_template.py",
                "target_version": "0.6.0",
                "phase": "pre-release",
                "final_status": "PASS",
                "failure_codes": [],
            }
        ),
        map_release_check_output_to_governance_evidence(
            {
                "script_name": "check_pypi_version.py",
                "target_version": "0.6.0",
                "phase": "pre-release",
                "final_status": "BLOCK",
                "failure_codes": ["PYPI_VERSION_ALREADY_EXISTS"],
            }
        ),
        map_release_check_output_to_governance_evidence(
            {
                "script_name": "check_release_note_tag_github_release.py",
                "target_version": "0.6.0",
                "phase": "pre-release",
                "final_status": "PASS",
                "failure_codes": [],
            }
        ),
        map_release_check_output_to_governance_evidence(
            {
                "script_name": "check_release_tokens.py",
                "target_version": "0.6.0",
                "phase": "pre-release",
                "final_status": "PASS",
                "failure_codes": [],
            }
        ),
        map_release_check_output_to_governance_evidence(
            {
                "script_name": "check_trusted_publishing_config.py",
                "target_version": "0.6.0",
                "phase": "pre-release",
                "final_status": "PASS",
                "failure_codes": [],
            }
        ),
        map_release_check_output_to_governance_evidence(
            {
                "script_name": "release_safety_check.py",
                "target_version": "0.6.0",
                "phase": "pre-release",
                "final_status": "PASS",
                "failure_codes": [],
            }
        ),
        map_release_check_output_to_governance_evidence(
            {
                "script_name": "verify_pypi_release.py",
                "target_version": "0.6.0",
                "phase": "pre-release",
                "final_status": "PASS",
                "failure_codes": [],
            }
        ),
    ]


def _product_agent_output_evidence() -> list[GovernanceEvidence]:
    return [
        map_product_gateway_response_summary_to_governance_evidence(
            {
                "product": "product_gateway",
                "payload_type": "product_gateway_response_summary",
                "payload_version": "product_gateway_response_summary_v1",
                "request_id": "request-unified-product-agent-1",
                "entry_kind": "agent_shell",
                "status": "success",
                "exit_code": 0,
                "product_gateway_response_ref": (
                    "product-gateway-response://request-unified-product-agent-1"
                ),
                "governance_summary_ref": (
                    "governance-summary://request-unified-product-agent-1"
                ),
                "evidence_refs": [
                    {
                        "ref": "evidence://request-unified-product-agent-1",
                        "kind": "evidence",
                    }
                ],
                "audit_refs": [],
                "agent_advice_refs": [],
                "tool_audit_refs": [],
                "blocking_reasons": [],
                "warnings": [],
            }
        ),
        map_agent_task_advice_payload_to_governance_evidence(
            {
                "product": "cognition_agent",
                "payload_type": "agent_task_advice_consumption_payload",
                "payload_version": "agent_task_advice_consumption_payload_v1",
                "candidate_id": "agent-task-advice-unified-1",
                "task_context_candidate_id": "agent-task-context-unified-1",
                "task_candidate_id": "agent-task-unified-1",
                "product_gateway_request_id": "request-unified-product-agent-1",
                "product_gateway_entry_kind": "agent_shell",
                "product_gateway_status": "success",
                "product_gateway_exit_code": 0,
                "recommendation": "continue_with_product_gateway_review",
                "status": "ready_for_product_gateway_review",
                "readonly": True,
                "candidate_only": True,
                "execution_enabled": False,
            }
        ),
    ]


def test_builds_unified_policy_set_candidate_for_adk2_domain() -> None:
    candidate = build_unified_policy_set_candidate(
        policy_domain=POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER
    )

    assert isinstance(candidate, UnifiedGovernancePolicySetCandidate)
    assert candidate.policy_domain == POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER
    assert candidate.policy_set.policy_set_id == ADK_WORKFLOW_RUNNER_POLICY_SET_ID
    assert candidate.policy_status == "candidate_only"
    assert candidate.formal_decision_enabled is False
    assert candidate.policy_execution_enabled is False
    assert candidate.governance_outcome_enabled is False
    assert candidate.public_contract is False
    assert "run_config_mapping_completeness" in candidate.rule_candidates


def test_builds_release_governance_policy_set_candidate() -> None:
    candidate = build_release_governance_policy_set_candidate()

    assert isinstance(candidate, UnifiedGovernancePolicySetCandidate)
    assert candidate.policy_domain == POLICY_DOMAIN_RELEASE_GOVERNANCE
    assert candidate.policy_set.policy_set_id == RELEASE_GOVERNANCE_POLICY_SET_ID
    assert candidate.policy_set.metadata["policy_status"] == "candidate_only"
    assert candidate.policy_set.metadata["formal_decision_enabled"] is False
    assert candidate.policy_set.metadata["policy_execution_enabled"] is False
    assert candidate.policy_set.metadata["governance_outcome_enabled"] is False
    assert "release_provider_coverage" in candidate.rule_candidates


def test_builds_product_agent_output_policy_set_candidate() -> None:
    candidate = build_product_agent_output_governance_policy_set_candidate()

    assert isinstance(candidate, UnifiedGovernancePolicySetCandidate)
    assert candidate.policy_domain == POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE
    assert candidate.policy_set.policy_set_id == (
        PRODUCT_AGENT_OUTPUT_GOVERNANCE_POLICY_SET_ID
    )
    assert candidate.policy_set.metadata["policy_status"] == "candidate_only"
    assert candidate.formal_decision_enabled is False
    assert candidate.policy_execution_enabled is False
    assert candidate.governance_outcome_enabled is False
    assert candidate.public_contract is False
    assert "product_gateway_summary_header_guard" in candidate.rule_candidates
    assert "refs_only_guard" in candidate.rule_candidates


def test_makes_unified_decision_candidate_from_adk2_chain() -> None:
    result = make_unified_governance_decision_candidate(
        _adk_case(),
        _adk_evidence(),
        policy_set_candidate=build_adk_workflow_runner_policy_set_candidate(),
    )

    assert isinstance(result, UnifiedGovernanceDecisionCandidateResult)
    assert isinstance(result.decision_candidate, GovernanceDecision)
    decision = result.decision_candidate
    assert decision.decision == "continue"
    assert decision.decision in ALLOWED_UNIFIED_DECISION_KINDS
    assert decision.decision not in {"release", "block"}
    assert decision.policy_set_id == ADK_WORKFLOW_RUNNER_POLICY_SET_ID
    assert decision.metadata["policy_domain"] == POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER
    assert decision.metadata["decision_semantics"] == "candidate_only"
    assert decision.metadata["formal_decision_enabled"] is False
    assert decision.metadata["policy_execution_enabled"] is False
    assert decision.metadata["governance_outcome_enabled"] is False
    assert decision.metadata["human_review_required"] is False
    assert decision.metadata["missing_evidence"] == []
    assert "workflow_name" in decision.metadata["domain_metadata"]
    assert "not a pass" in decision.metadata["continue_semantics"]
    assert not hasattr(result, "governance_outcome")
    assert "can_publish" not in repr(result.model_dump(mode="python"))
    assert "can_release" not in repr(result.model_dump(mode="python"))


def test_makes_unified_decision_candidate_from_release_chain() -> None:
    evidence = _release_evidence()
    governance_case = map_release_evidence_to_governance_case(
        evidence,
        release_target="public_repo_and_pypi",
    )
    result = make_unified_governance_decision_candidate(
        governance_case,
        evidence,
        policy_set_candidate=build_release_governance_policy_set_candidate(),
    )

    decision = result.decision_candidate
    assert decision.decision == "fix"
    assert decision.decision in ALLOWED_UNIFIED_DECISION_KINDS
    assert decision.decision not in {"release", "block"}
    assert decision.policy_set_id == RELEASE_GOVERNANCE_POLICY_SET_ID
    assert decision.metadata["policy_domain"] == POLICY_DOMAIN_RELEASE_GOVERNANCE
    assert decision.metadata["decision_semantics"] == "candidate_only"
    assert decision.metadata["formal_decision_enabled"] is False
    assert decision.metadata["policy_execution_enabled"] is False
    assert decision.metadata["governance_outcome_enabled"] is False
    assert decision.metadata["human_review_required"] is True
    assert decision.metadata["missing_evidence"] == []
    assert decision.metadata["human_review_reasons"]
    assert "providers" in decision.metadata["domain_metadata"]
    assert "raw_output_digest" not in decision.metadata
    assert "checks_summary" not in decision.metadata
    assert not hasattr(result, "governance_outcome")
    assert "can_publish" not in repr(result.model_dump(mode="python"))
    assert "can_release" not in repr(result.model_dump(mode="python"))


def test_makes_unified_decision_candidate_from_product_agent_output_chain() -> None:
    evidence = _product_agent_output_evidence()
    governance_case = map_product_agent_output_evidence_to_governance_case(evidence)

    result = make_unified_governance_decision_candidate(
        governance_case,
        evidence,
        policy_set_candidate=build_product_agent_output_governance_policy_set_candidate(),
    )

    decision = result.decision_candidate
    assert decision.decision == "continue"
    assert decision.decision in ALLOWED_UNIFIED_DECISION_KINDS
    assert decision.decision not in {"release", "block"}
    assert decision.policy_set_id == PRODUCT_AGENT_OUTPUT_GOVERNANCE_POLICY_SET_ID
    assert decision.metadata["policy_domain"] == (
        POLICY_DOMAIN_PRODUCT_AGENT_OUTPUT_GOVERNANCE
    )
    assert decision.metadata["decision_semantics"] == "candidate_only"
    assert decision.metadata["formal_decision_enabled"] is False
    assert decision.metadata["policy_execution_enabled"] is False
    assert decision.metadata["governance_outcome_enabled"] is False
    assert decision.metadata["human_review_required"] is False
    assert decision.metadata["missing_evidence"] == []
    assert "product_gateway_request_id" in decision.metadata["domain_metadata"]
    assert "not a pass" in decision.metadata["continue_semantics"]
    serialized = repr(result.model_dump(mode="python"))
    assert "can_publish" not in serialized
    assert "can_release" not in serialized
    assert not hasattr(result, "governance_outcome")


def test_product_agent_output_missing_agent_payload_needs_evidence() -> None:
    evidence = [_product_agent_output_evidence()[0]]
    governance_case = map_product_agent_output_evidence_to_governance_case(evidence)

    result = make_unified_governance_decision_candidate(
        governance_case,
        evidence,
        policy_set_candidate=build_product_agent_output_governance_policy_set_candidate(),
    )

    decision = result.decision_candidate
    assert decision.decision == "need_evidence"
    assert decision.metadata["human_review_required"] is True
    assert "agent_task_advice_consumption_payload" in decision.metadata[
        "missing_evidence"
    ]


def test_missing_policy_set_defers_without_formal_decision() -> None:
    result = make_unified_governance_decision_candidate(
        _adk_case(),
        _adk_evidence(),
        policy_set_candidate=None,
        policy_domain=POLICY_DOMAIN_ADK2_WORKFLOW_RUNNER,
    )

    decision = result.decision_candidate
    assert decision.decision == "defer"
    assert decision.metadata["human_review_required"] is True
    assert decision.metadata["policy_set_candidate_id"] is None
    assert "PolicySet candidate was not provided." in decision.metadata[
        "human_review_reasons"
    ]
    assert "Decision output is candidate-only." in decision.metadata[
        "blocked_formal_decision_reasons"
    ]


def test_unified_decision_source_keeps_runtime_and_script_layers_out() -> None:
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:google\.adk|adk_adapter|runtime_container|composition|scripts|subprocess)\b",
        re.MULTILINE,
    )

    for source_path in GOVERNANCE_SOURCE_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_imports.search(source) is None, source_path
