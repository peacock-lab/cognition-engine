from __future__ import annotations

from runtime_container.cli_agent_workflow_admission import (
    AgentRoleDeclarationCandidate,
    agent_workflow_evidence_projection_status_dict,
    agent_workflow_loading_gate_status_dict,
    build_agent_workflow_descriptor,
    build_agent_workflow_evidence_projection,
    evaluate_agent_team_admission,
    validate_agent_workflow_loading_gate,
)
from runtime_container.cli_tool_loading_validation import CliToolLoadingGateCandidate


def test_low_risk_single_agent_candidate_passes_without_execution() -> None:
    descriptor = build_agent_workflow_descriptor(
        workflow_name="cli_research_agent_workflow",
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

    gate = validate_agent_workflow_loading_gate(
        descriptor=descriptor,
        admission=admission,
    )
    status = agent_workflow_loading_gate_status_dict(gate)
    projection = build_agent_workflow_evidence_projection(gate)
    projection_status = agent_workflow_evidence_projection_status_dict(projection)

    assert admission.admitted is True
    assert gate.status == "passed"
    assert gate.allowed_for_candidate_registration is True
    assert gate.allowed_for_execution is False
    assert gate.metadata["does_not_load_agent"] is True
    assert gate.metadata["does_not_execute_agent"] is True
    assert gate.metadata["does_not_call_model"] is True
    assert gate.metadata["agent_gate_reuses_tools_gate"] is False
    assert status["descriptor"]["agent_slot_status"] == (
        "candidate_descriptor_available"
    )
    assert projection_status["role_count"] == 1
    assert projection_status["metadata"]["does_not_include_topology_graph"] is True


def test_entry_agent_must_match_declared_role() -> None:
    admission = evaluate_agent_team_admission(
        agent_team_name="research_team",
        agent_team_kind="single_agent_candidate",
        source_ref="agent-team-candidate://research-team",
        entry_agent_name="planner",
        role_declarations=(_researcher_role(),),
        handoff_policy_declared=True,
        model_policy_ref="model-policy://no-live",
        input_schema_ref="schema://agent-workflows/research/input",
        output_boundary_ref="boundary://agent-workflows/research/sanitized-output",
        failure_policy_ref="failure-policy://agent-workflows/research/basic",
        risk_level="low",
    )

    assert admission.admitted is False
    assert "entry_agent_missing" in admission.blocking_reasons


def test_role_boundaries_are_required() -> None:
    role = AgentRoleDeclarationCandidate(
        agent_name="researcher",
        agent_kind="llm_agent_candidate",
        role_label="researcher",
        responsibility_summary="Collect sanitized research notes.",
        input_boundary_ref="schema://agent-role/researcher/input",
        output_boundary_ref="",
        model_policy_ref="model-policy://no-live",
        risk_level="low",
    )

    admission = evaluate_agent_team_admission(
        agent_team_name="research_team",
        agent_team_kind="single_agent_candidate",
        source_ref="agent-team-candidate://research-team",
        entry_agent_name="researcher",
        role_declarations=(role,),
        handoff_policy_declared=True,
        model_policy_ref="model-policy://no-live",
        input_schema_ref="schema://agent-workflows/research/input",
        output_boundary_ref="boundary://agent-workflows/research/sanitized-output",
        failure_policy_ref="failure-policy://agent-workflows/research/basic",
        risk_level="low",
    )

    assert admission.admitted is False
    assert (
        "role:researcher:role_output_boundary_missing"
        in admission.blocking_reasons
    )


def test_tool_dependencies_must_pass_tools_gate() -> None:
    role = _researcher_role(allowed_tool_names=("local_reference_reader",))

    blocked = evaluate_agent_team_admission(
        agent_team_name="research_team",
        agent_team_kind="single_agent_candidate",
        source_ref="agent-team-candidate://research-team",
        entry_agent_name="researcher",
        role_declarations=(role,),
        handoff_policy_declared=True,
        model_policy_ref="model-policy://no-live",
        input_schema_ref="schema://agent-workflows/research/input",
        output_boundary_ref="boundary://agent-workflows/research/sanitized-output",
        failure_policy_ref="failure-policy://agent-workflows/research/basic",
        risk_level="low",
    )
    allowed = evaluate_agent_team_admission(
        agent_team_name="research_team",
        agent_team_kind="single_agent_candidate",
        source_ref="agent-team-candidate://research-team",
        entry_agent_name="researcher",
        role_declarations=(role,),
        handoff_policy_declared=True,
        model_policy_ref="model-policy://no-live",
        tool_loading_gate=_passed_tool_gate(),
        input_schema_ref="schema://agent-workflows/research/input",
        output_boundary_ref="boundary://agent-workflows/research/sanitized-output",
        failure_policy_ref="failure-policy://agent-workflows/research/basic",
        risk_level="low",
        operator_approved=True,
        approval_ref="approval://agent-tools",
    )

    assert blocked.admitted is False
    assert "tool_dependency_gate_failed" in blocked.blocking_reasons
    assert "role:researcher:role_tool_not_allowed:local_reference_reader" in (
        blocked.blocking_reasons
    )
    assert allowed.admitted is True
    assert allowed.metadata["tool_loading_gate_status"] == "passed"


def test_medium_or_live_agent_candidate_requires_operator_confirmation() -> None:
    kwargs = dict(
        agent_team_name="research_team",
        agent_team_kind="collaborative_agent_candidate",
        source_ref="agent-team-candidate://research-team",
        entry_agent_name="researcher",
        role_declarations=(_researcher_role(),),
        handoff_policy_declared=True,
        handoff_policy_kind="declared_internal_boundary",
        model_policy_ref="model-policy://controlled-live",
        input_schema_ref="schema://agent-workflows/research/input",
        output_boundary_ref="boundary://agent-workflows/research/sanitized-output",
        failure_policy_ref="failure-policy://agent-workflows/research/basic",
        risk_level="medium",
        max_risk_level="medium",
        live_gate_policy="controlled_live",
    )

    blocked = evaluate_agent_team_admission(**kwargs)
    allowed = evaluate_agent_team_admission(
        **kwargs,
        operator_approved=True,
        approval_ref="approval://agent-team",
    )

    assert blocked.admitted is False
    assert "operator_confirmation_required" in blocked.blocking_reasons
    assert allowed.admitted is True
    assert allowed.confirmation_required is True
    assert allowed.confirmation_satisfied is True


def test_managed_governance_parameters_and_raw_secrets_are_blocked() -> None:
    admission = evaluate_agent_team_admission(
        agent_team_name="research_team",
        agent_team_kind="single_agent_candidate",
        source_ref="agent-team-candidate://research-team",
        entry_agent_name="researcher",
        role_declarations=(_researcher_role(),),
        handoff_policy_declared=True,
        model_policy_ref="model-policy://no-live",
        input_schema_ref="schema://agent-workflows/research/input",
        output_boundary_ref="boundary://agent-workflows/research/sanitized-output",
        failure_policy_ref="failure-policy://agent-workflows/research/basic",
        risk_level="low",
        user_passthrough_parameters={"approval_ref": "user-overrides"},
        raw_config={"api_key": "secret-value"},
    )

    assert admission.admitted is False
    assert "managed_governance_parameter_override:approval_ref" in (
        admission.blocking_reasons
    )
    assert "raw_credential_material_forbidden" in admission.blocking_reasons


def test_descriptor_and_admission_must_match() -> None:
    descriptor = build_agent_workflow_descriptor(
        workflow_name="cli_research_agent_workflow",
        task_kind="research_assist",
        agent_team_name="other_team",
    )
    admission = evaluate_agent_team_admission(
        agent_team_name="research_team",
        agent_team_kind="single_agent_candidate",
        source_ref="agent-team-candidate://research-team",
        entry_agent_name="researcher",
        role_declarations=(_researcher_role(),),
        handoff_policy_declared=True,
        model_policy_ref="model-policy://no-live",
        input_schema_ref="schema://agent-workflows/research/input",
        output_boundary_ref="boundary://agent-workflows/research/sanitized-output",
        failure_policy_ref="failure-policy://agent-workflows/research/basic",
        risk_level="low",
    )

    gate = validate_agent_workflow_loading_gate(
        descriptor=descriptor,
        admission=admission,
    )

    assert gate.status == "blocked"
    assert "agent_team_ref_mismatch" in gate.blocking_reasons


def _researcher_role(
    *,
    allowed_tool_names: tuple[str, ...] = (),
) -> AgentRoleDeclarationCandidate:
    return AgentRoleDeclarationCandidate(
        agent_name="researcher",
        agent_kind="llm_agent_candidate",
        role_label="researcher",
        responsibility_summary="Collect sanitized research notes.",
        input_boundary_ref="schema://agent-role/researcher/input",
        output_boundary_ref="boundary://agent-role/researcher/output",
        allowed_tool_names=allowed_tool_names,
        model_policy_ref="model-policy://no-live",
        handoff_allowed=False,
        handoff_targets_declared=False,
        risk_level="low",
    )


def _passed_tool_gate() -> CliToolLoadingGateCandidate:
    return CliToolLoadingGateCandidate(
        status="passed",
        risk_gate_status="passed",
        validations=(),
        allowed_tool_names=("local_reference_reader",),
        blocked_tool_names=(),
        metadata={
            "does_not_execute_tools": True,
            "does_not_call_model": True,
        },
    )
