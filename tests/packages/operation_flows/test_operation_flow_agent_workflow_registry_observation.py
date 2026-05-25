from __future__ import annotations

from cognition_operation_flows._agents.workflow_admission import (
    AgentRoleDeclarationCandidate,
    build_agent_workflow_descriptor,
    evaluate_agent_team_admission,
    validate_agent_workflow_loading_gate,
)
from cognition_operation_flows._agents.workflow_registry_observation import (
    build_operation_flow_agent_workflow_candidate_descriptor_source,
    build_operation_flow_agent_workflow_registry_observation,
    operation_flow_agent_workflow_candidate_descriptor_source_status_dict,
    operation_flow_agent_workflow_registry_observation_status_dict,
)
from cognition_operation_flows._requests.registry import (
    OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
    OPERATION_FLOW_PLAN_WORKFLOW_NAME,
    OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
    OPERATION_FLOW_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
    build_default_operation_flow_registry,
    list_operation_flow_descriptors,
)


def test_passed_agent_gate_builds_candidate_visible_observation() -> None:
    gate = _passed_agent_gate()

    source = build_operation_flow_agent_workflow_candidate_descriptor_source(gate)
    observation = build_operation_flow_agent_workflow_registry_observation(
        gate,
        source=source,
    )
    source_status = operation_flow_agent_workflow_candidate_descriptor_source_status_dict(
        source
    )
    observation_status = operation_flow_agent_workflow_registry_observation_status_dict(
        observation
    )

    assert source.allowed_for_candidate_registration is True
    assert source.allowed_for_execution is False
    assert source.metadata["does_not_register_workflow"] is True
    assert source.metadata["does_not_route_workflow"] is True
    assert observation.status == "candidate_visible"
    assert observation.candidate_registration_allowed is True
    assert observation.execution_allowed is False
    assert observation.metadata["not_in_registry_descriptors"] is True
    assert observation.metadata["router_matched"] is False
    assert observation.metadata["route_reason"] is None
    assert source_status["allowed_for_execution"] is False
    assert observation_status["metadata"]["does_not_execute_workflow"] is True


def test_blocked_agent_gate_builds_blocked_observation() -> None:
    gate = _blocked_agent_gate()

    observation = build_operation_flow_agent_workflow_registry_observation(gate)

    assert observation.status == "blocked"
    assert observation.candidate_registration_allowed is False
    assert observation.execution_allowed is False
    assert "entry_agent_missing" in observation.blocking_reasons


def test_observation_does_not_modify_default_registry() -> None:
    gate = _passed_agent_gate()
    registry = build_default_operation_flow_registry()
    before = tuple(
        descriptor.workflow_name
        for descriptor in list_operation_flow_descriptors(registry)
    )

    observation = build_operation_flow_agent_workflow_registry_observation(gate)
    after = tuple(
        descriptor.workflow_name
        for descriptor in list_operation_flow_descriptors(registry)
    )

    assert before == (
        OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
        OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
        OPERATION_FLOW_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
        OPERATION_FLOW_PLAN_WORKFLOW_NAME,
    )
    assert after == before
    assert observation.agent_workflow_name not in after


def test_candidate_descriptor_source_refs_are_stable_and_candidate_only() -> None:
    gate = _passed_agent_gate()

    source = build_operation_flow_agent_workflow_candidate_descriptor_source(gate)

    assert source.source_name == (
        "operation-flow-research-agent-workflow-candidate-descriptor-source"
    )
    assert source.agent_workflow_descriptor_ref == (
        "agent-workflow-descriptor://operation-flow-research-agent-workflow"
    )
    assert source.agent_team_admission_ref == (
        "agent-team-admission://research-team"
    )
    assert source.evidence_projection_ref == (
        "agent-workflow-evidence-projection://"
        "operation-flow-research-agent-workflow/research-team"
    )
    assert source.metadata["candidate_only"] is True


def _passed_agent_gate():
    descriptor = build_agent_workflow_descriptor(
        workflow_name="operation_flow_research_agent_workflow",
        task_kind="research_assist",
        agent_team_name="research_team",
        agent_team_kind="single_agent_candidate",
        default_risk_level="low",
        live_gate_policy="no_live",
    )
    admission = evaluate_agent_team_admission(
        agent_team_name="research_team",
        agent_team_kind="single_agent_candidate",
        source_ref="agent-team-candidate://research-team",
        entry_agent_name="researcher",
        role_declarations=(_researcher_role(),),
        handoff_policy_declared=True,
        handoff_policy_kind="none",
        model_policy_ref="model-policy://no-live",
        input_schema_ref="schema://agent-workflows/research/input",
        output_boundary_ref="boundary://agent-workflows/research/sanitized-output",
        failure_policy_ref="failure-policy://agent-workflows/research/basic",
        risk_level="low",
        max_risk_level="medium",
        live_gate_policy="no_live",
    )
    return validate_agent_workflow_loading_gate(
        descriptor=descriptor,
        admission=admission,
    )


def _blocked_agent_gate():
    descriptor = build_agent_workflow_descriptor(
        workflow_name="operation_flow_research_agent_workflow",
        task_kind="research_assist",
        agent_team_name="research_team",
        agent_team_kind="single_agent_candidate",
        default_risk_level="low",
        live_gate_policy="no_live",
    )
    admission = evaluate_agent_team_admission(
        agent_team_name="research_team",
        agent_team_kind="single_agent_candidate",
        source_ref="agent-team-candidate://research-team",
        entry_agent_name="planner",
        role_declarations=(_researcher_role(),),
        handoff_policy_declared=True,
        handoff_policy_kind="none",
        model_policy_ref="model-policy://no-live",
        input_schema_ref="schema://agent-workflows/research/input",
        output_boundary_ref="boundary://agent-workflows/research/sanitized-output",
        failure_policy_ref="failure-policy://agent-workflows/research/basic",
        risk_level="low",
        max_risk_level="medium",
        live_gate_policy="no_live",
    )
    return validate_agent_workflow_loading_gate(
        descriptor=descriptor,
        admission=admission,
    )


def _researcher_role() -> AgentRoleDeclarationCandidate:
    return AgentRoleDeclarationCandidate(
        agent_name="researcher",
        agent_kind="llm_agent_candidate",
        role_label="researcher",
        responsibility_summary="Collect sanitized research notes.",
        input_boundary_ref="schema://agent-role/researcher/input",
        output_boundary_ref="boundary://agent-role/researcher/output",
        model_policy_ref="model-policy://no-live",
        handoff_allowed=False,
        handoff_targets_declared=False,
        risk_level="low",
    )
