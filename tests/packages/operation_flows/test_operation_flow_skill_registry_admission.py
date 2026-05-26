from __future__ import annotations

from config_contexts import SkillL1MetadataCandidate, SkillMetadataViewCandidate
from cognition_operation_flows._skills.registry_admission import (
    OperationFlowProjectSkillCapabilityDeclarationCandidate,
    OperationFlowProjectSkillRegistryRecordCandidate,
    build_operation_flow_project_skill_registry_evidence_projection,
    build_operation_flow_project_skill_registry_source,
    operation_flow_project_skill_registry_evidence_projection_status_dict,
    operation_flow_project_skill_registry_loading_gate_status_dict,
    validate_operation_flow_project_skill_registry_loading_gate,
)
from cognition_operation_flows._tools.loading_validation import OperationFlowToolLoadingGateCandidate


def test_project_skill_registry_candidate_passes_without_runtime_loading() -> None:
    source = build_operation_flow_project_skill_registry_source(
        registry_name="project_skills",
        source_ref="config://skills/project-skills",
        declared_skill_ids=("skill.plan.formatting",),
    )
    record = _skill_record(
        capability=_capability(
            skill_id="skill.plan.formatting",
            capability_id="capability.plan.formatting",
            required_tool_names=(),
        )
    )

    gate = validate_operation_flow_project_skill_registry_loading_gate(
        source=source,
        records=(record,),
    )
    projection = build_operation_flow_project_skill_registry_evidence_projection(
        gate,
        records=(record,),
    )
    status = operation_flow_project_skill_registry_loading_gate_status_dict(gate)
    projection_status = operation_flow_project_skill_registry_evidence_projection_status_dict(
        projection
    )

    assert gate.status == "passed"
    assert gate.allowed_for_candidate_reference is True
    assert gate.allowed_for_runtime_loading is False
    assert gate.allowed_for_tool_exposure is False
    assert gate.allowed_for_workflow_registration is False
    assert gate.metadata["does_not_load_skill_file"] is True
    assert gate.metadata["does_not_create_skill_toolset"] is True
    assert gate.metadata["does_not_call_skill_registry"] is True
    assert gate.metadata["does_not_execute_script"] is True
    assert status["validated_skill_ids"] == ["skill.plan.formatting"]
    assert projection_status["capability_count"] == 1
    assert projection_status["metadata"]["does_not_include_raw_instructions"] is True
    assert projection_status["metadata"]["does_not_include_raw_script_body"] is True


def test_skill_capability_boundaries_are_required() -> None:
    source = build_operation_flow_project_skill_registry_source(
        registry_name="project_skills",
        source_ref="config://skills/project-skills",
        declared_skill_ids=("skill.plan.formatting",),
    )
    record = _skill_record(
        capability=_capability(
            skill_id="skill.plan.formatting",
            capability_id="capability.plan.formatting",
            input_boundary_ref=None,
            output_boundary_ref=None,
        )
    )

    gate = validate_operation_flow_project_skill_registry_loading_gate(
        source=source,
        records=(record,),
    )

    assert gate.status == "blocked"
    assert "skill.plan.formatting:capability:capability.plan.formatting:input_boundary_missing" in (
        gate.blocking_reasons
    )
    assert "skill.plan.formatting:capability:capability.plan.formatting:output_boundary_missing" in (
        gate.blocking_reasons
    )
    assert gate.blocked_skill_ids == ("skill.plan.formatting",)


def test_tool_dependencies_must_pass_tools_gate() -> None:
    source = build_operation_flow_project_skill_registry_source(
        registry_name="project_skills",
        source_ref="config://skills/project-skills",
        declared_skill_ids=("skill.reference.review",),
    )
    record = _skill_record(
        skill_id="skill.reference.review",
        capability=_capability(
            skill_id="skill.reference.review",
            capability_id="capability.reference.review",
            required_tool_names=("local_reference_reader",),
        ),
    )

    blocked = validate_operation_flow_project_skill_registry_loading_gate(
        source=source,
        records=(record,),
    )
    allowed = validate_operation_flow_project_skill_registry_loading_gate(
        source=source,
        records=(record,),
        tool_loading_gate=_passed_tool_gate("local_reference_reader"),
    )

    assert blocked.status == "blocked"
    assert "skill.reference.review:capability:capability.reference.review:tool_dependency_gate_failed" in (
        blocked.blocking_reasons
    )
    assert "skill.reference.review:tool_dependency_bypasses_tools_gate" in (
        blocked.blocking_reasons
    )
    assert allowed.status == "passed"
    assert allowed.validated_skill_ids == ("skill.reference.review",)
    assert allowed.metadata["tool_loading_gate_status"] == "passed"


def test_runtime_loading_requests_and_raw_skill_material_are_blocked() -> None:
    source = build_operation_flow_project_skill_registry_source(
        registry_name="project_skills",
        source_ref="config://skills/project-skills",
        declared_skill_ids=("skill.plan.formatting",),
        metadata={"runtime_request": {"real_skill_loading_requested": True}},
    )
    record = _skill_record(
        capability=_capability(
            skill_id="skill.plan.formatting",
            capability_id="capability.plan.formatting",
        ),
        metadata={"raw_script_body": "print('do not execute')"},
    )

    gate = validate_operation_flow_project_skill_registry_loading_gate(
        source=source,
        records=(record,),
    )

    assert gate.status == "blocked"
    assert "real_skill_loading_requested" in gate.blocking_reasons
    assert "skill.plan.formatting:raw_skill_material_forbidden" in (
        gate.blocking_reasons
    )
    assert gate.allowed_for_runtime_loading is False


def test_skill_ids_must_match_source_and_metadata_view() -> None:
    source = build_operation_flow_project_skill_registry_source(
        registry_name="project_skills",
        source_ref="config://skills/project-skills",
        declared_skill_ids=("skill.expected",),
    )
    record = _skill_record(
        skill_id="skill.actual",
        metadata_skill_id="skill.metadata",
        capability=_capability(
            skill_id="skill.actual",
            capability_id="capability.actual",
        ),
    )

    gate = validate_operation_flow_project_skill_registry_loading_gate(
        source=source,
        records=(record,),
    )

    assert gate.status == "blocked"
    assert "skill_not_declared_in_source:skill.actual" in gate.blocking_reasons
    assert "skill.actual:skill_metadata_skill_id_mismatch" in gate.blocking_reasons


def test_risk_policy_blocks_high_risk_skill_capability() -> None:
    source = build_operation_flow_project_skill_registry_source(
        registry_name="project_skills",
        source_ref="config://skills/project-skills",
        declared_skill_ids=("skill.high.risk",),
    )
    record = _skill_record(
        skill_id="skill.high.risk",
        capability=_capability(
            skill_id="skill.high.risk",
            capability_id="capability.high.risk",
            risk_level="high",
        ),
    )

    gate = validate_operation_flow_project_skill_registry_loading_gate(
        source=source,
        records=(record,),
        max_risk_level="medium",
    )

    assert gate.status == "blocked"
    assert "skill.high.risk:capability:capability.high.risk:risk_exceeds_policy" in (
        gate.blocking_reasons
    )
    assert gate.validations[0].risk_level == "high"


def _skill_record(
    *,
    skill_id: str = "skill.plan.formatting",
    metadata_skill_id: str | None = None,
    capability: OperationFlowProjectSkillCapabilityDeclarationCandidate,
    metadata: dict[str, object] | None = None,
) -> OperationFlowProjectSkillRegistryRecordCandidate:
    resolved_metadata_skill_id = metadata_skill_id or skill_id
    return OperationFlowProjectSkillRegistryRecordCandidate(
        skill_id=skill_id,
        metadata_view=SkillMetadataViewCandidate(
            l1_metadata=SkillL1MetadataCandidate(
                skill_id=resolved_metadata_skill_id,
                name="Plan Formatting",
                description="Candidate-only plan formatting skill.",
                capabilities=(capability.capability_id,),
                source_ref="tasks/b1/355",
                skill_file_ref="skills/plan-formatting/SKILL.md",
            )
        ),
        capability_declarations=(capability,),
        source_ref="skill-candidate://plan-formatting",
        metadata=dict(metadata or {}),
    )


def _capability(
    *,
    skill_id: str,
    capability_id: str,
    input_boundary_ref: str | None = "schema://skills/plan-formatting/input",
    output_boundary_ref: str | None = "boundary://skills/plan-formatting/output",
    risk_level: str = "low",
    required_tool_names: tuple[str, ...] = (),
) -> OperationFlowProjectSkillCapabilityDeclarationCandidate:
    return OperationFlowProjectSkillCapabilityDeclarationCandidate(
        skill_id=skill_id,
        capability_id=capability_id,
        capability_name="Plan Formatting",
        description="Format structured plan output as a candidate capability.",
        domains=("operation_flow_plan_workflow",),
        task_kinds=("plan_formatting",),
        required_tool_names=required_tool_names,
        agent_role_refs=("agent-role-candidate://planner",),
        workflow_refs=("workflow-candidate://operation_flow_plan_workflow",),
        input_boundary_ref=input_boundary_ref,
        output_boundary_ref=output_boundary_ref,
        risk_level=risk_level,
        script_policy="no_scripts",
        resource_policy="refs_only",
    )


def _passed_tool_gate(tool_name: str) -> OperationFlowToolLoadingGateCandidate:
    return OperationFlowToolLoadingGateCandidate(
        status="passed",
        risk_gate_status="passed",
        validations=(),
        allowed_tool_names=(tool_name,),
        blocked_tool_names=(),
        metadata={"test_gate": True},
    )
