from __future__ import annotations

from config_contexts import SkillL1MetadataCandidate, SkillMetadataViewCandidate
from cognition_operation_flows._skills.capability_projection import (
    build_operation_flow_skill_capability_projection,
    build_operation_flow_skill_projection_read_context,
    build_operation_flow_workflow_skill_slot_reference,
    operation_flow_skill_capability_projection_status_dict,
    operation_flow_skill_capability_review_status_dict,
    operation_flow_skill_projection_read_context_status_dict,
    operation_flow_workflow_skill_slot_reference_status_dict,
    review_operation_flow_skill_capability_for_projection,
)
from cognition_operation_flows._skills.registry_admission import (
    OperationFlowProjectSkillCapabilityDeclarationCandidate,
    OperationFlowProjectSkillRegistryRecordCandidate,
    build_operation_flow_project_skill_registry_source,
    validate_operation_flow_project_skill_registry_loading_gate,
)
from cognition_operation_flows._requests.registry import (
    OPERATION_FLOW_PLAN_WORKFLOW_NAME,
    build_operation_flow_plan_workflow_descriptor,
)
from cognition_operation_flows._tools.loading_validation import OperationFlowToolLoadingGateCandidate


def test_skill_capability_projection_passes_without_runtime_loading() -> None:
    source, record, gate = _passed_skill_gate()

    review = review_operation_flow_skill_capability_for_projection(
        gate=gate,
        records=(record,),
        skill_id="skill.plan.formatting",
        capability_id="capability.plan.formatting",
        evidence_refs=("evidence://skill-plan-formatting",),
    )
    projection = build_operation_flow_skill_capability_projection(review)
    slot = build_operation_flow_workflow_skill_slot_reference(
        descriptor=build_operation_flow_plan_workflow_descriptor(),
        projection=projection,
    )
    review_status = operation_flow_skill_capability_review_status_dict(review)
    projection_status = operation_flow_skill_capability_projection_status_dict(projection)
    slot_status = operation_flow_workflow_skill_slot_reference_status_dict(slot)

    assert source.registry_name == "project_skills"
    assert gate.status == "passed"
    assert review.review_status_candidate == "approved_candidate"
    assert review.allowed_for_projection is True
    assert review.allowed_for_workflow_reference is True
    assert review.allowed_workflow_names == (OPERATION_FLOW_PLAN_WORKFLOW_NAME,)
    assert review.runtime_enabled is False
    assert review.skill_file_loading_enabled is False
    assert review.resources_loading_enabled is False
    assert review.scripts_execution_enabled is False
    assert review.tool_exposure_enabled is False
    assert review.agent_runtime_enabled is False
    assert review.public_schema_enabled is False
    assert projection.projection_status_candidate == "approved_candidate"
    assert projection.allowed_workflow_names == (OPERATION_FLOW_PLAN_WORKFLOW_NAME,)
    assert projection.metadata["does_not_include_raw_instructions"] is True
    assert projection.metadata["does_not_include_raw_resource_content"] is True
    assert projection.metadata["does_not_include_raw_script_body"] is True
    assert projection.metadata["runtime_enabled"] is False
    assert projection.metadata["tool_exposure_enabled"] is False
    assert slot.slot_status_candidate == "active_candidate"
    assert slot.reference_mode == "projection_summary_only"
    assert "skill_runtime_loading" in slot.forbidden_use
    assert "script_execution" in slot.forbidden_use
    assert "tool_exposure" in slot.forbidden_use
    assert "agent_runtime" in slot.forbidden_use
    assert "public_schema" in slot.forbidden_use
    assert review_status["candidate_only"] is True
    assert projection_status["candidate_only"] is True
    assert projection_status["metadata"]["does_not_include_secret"] is True
    assert slot_status["runtime_enabled"] is False
    assert slot_status["public_schema_enabled"] is False


def test_workflow_skill_projection_read_context_passes_as_read_only_hint() -> None:
    _, record, gate = _passed_skill_gate()
    descriptor = build_operation_flow_plan_workflow_descriptor()
    review = review_operation_flow_skill_capability_for_projection(
        gate=gate,
        records=(record,),
        skill_id="skill.plan.formatting",
        capability_id="capability.plan.formatting",
    )
    projection = build_operation_flow_skill_capability_projection(
        review,
        display_summary="方案排版能力投影。",
        use_boundary="仅作为 workflow planning hint，不加载 Skill。",
    )
    slot = build_operation_flow_workflow_skill_slot_reference(
        descriptor=descriptor,
        projection=projection,
    )

    read_context = build_operation_flow_skill_projection_read_context(
        descriptor=descriptor,
        projections=(projection,),
        slot_references=(slot,),
        allowed_use_stage="workflow_planning_hint",
    )
    status = operation_flow_skill_projection_read_context_status_dict(read_context)

    assert read_context.status == "available_candidate"
    assert read_context.workflow_name == OPERATION_FLOW_PLAN_WORKFLOW_NAME
    assert read_context.allowed_use_stage == "workflow_planning_hint"
    assert read_context.projection_refs == (projection.projection_id,)
    assert read_context.display_summaries == ("方案排版能力投影。",)
    assert read_context.use_boundaries == (
        "仅作为 workflow planning hint，不加载 Skill。",
    )
    assert read_context.reference_modes == ("projection_summary_only",)
    assert read_context.runtime_enabled is False
    assert read_context.prompt_context_enabled is False
    assert read_context.public_schema_enabled is False
    assert status["metadata"]["read_context_only"] is True
    assert status["metadata"]["does_not_inject_prompt_context"] is True
    assert status["metadata"]["does_not_dispatch_runtime"] is True


def test_workflow_skill_projection_read_context_blocks_allowed_use_mismatch() -> None:
    _, record, gate = _passed_skill_gate()
    descriptor = build_operation_flow_plan_workflow_descriptor()
    review = review_operation_flow_skill_capability_for_projection(
        gate=gate,
        records=(record,),
        skill_id="skill.plan.formatting",
        capability_id="capability.plan.formatting",
    )
    projection = build_operation_flow_skill_capability_projection(review)
    slot = build_operation_flow_workflow_skill_slot_reference(
        descriptor=descriptor,
        projection=projection,
        allowed_use=("workflow_planning_hint",),
    )

    read_context = build_operation_flow_skill_projection_read_context(
        descriptor=descriptor,
        projections=(projection,),
        slot_references=(slot,),
        allowed_use_stage="status_evidence_summary",
    )

    assert read_context.status == "blocked_candidate"
    assert "allowed_use_stage_not_allowed" in read_context.blocking_reasons
    assert read_context.runtime_enabled is False
    assert read_context.prompt_context_enabled is False
    assert read_context.public_schema_enabled is False


def test_workflow_skill_projection_read_context_blocks_runtime_escalation() -> None:
    _, record, gate = _passed_skill_gate()
    descriptor = build_operation_flow_plan_workflow_descriptor()
    review = review_operation_flow_skill_capability_for_projection(
        gate=gate,
        records=(record,),
        skill_id="skill.plan.formatting",
        capability_id="capability.plan.formatting",
    )
    projection = build_operation_flow_skill_capability_projection(review)
    escalated_projection = projection.__class__(
        **{
            **projection.__dict__,
            "runtime_enabled": True,
        }
    )
    slot = build_operation_flow_workflow_skill_slot_reference(
        descriptor=descriptor,
        projection=escalated_projection,
    )

    read_context = build_operation_flow_skill_projection_read_context(
        descriptor=descriptor,
        projections=(escalated_projection,),
        slot_references=(slot,),
        allowed_use_stage="workflow_planning_hint",
    )

    assert read_context.status == "blocked_candidate"
    assert read_context.runtime_enabled is True
    assert "projection_runtime_enabled" in read_context.blocking_reasons


def test_workflow_skill_projection_read_context_unavailable_without_slot() -> None:
    _, record, gate = _passed_skill_gate()
    descriptor = build_operation_flow_plan_workflow_descriptor()
    review = review_operation_flow_skill_capability_for_projection(
        gate=gate,
        records=(record,),
        skill_id="skill.plan.formatting",
        capability_id="capability.plan.formatting",
    )
    projection = build_operation_flow_skill_capability_projection(review)

    read_context = build_operation_flow_skill_projection_read_context(
        descriptor=descriptor,
        projections=(projection,),
        slot_references=(),
        allowed_use_stage="workflow_planning_hint",
    )

    assert read_context.status == "unavailable"
    assert "workflow_slot_reference_missing" in read_context.blocking_reasons
    assert read_context.runtime_enabled is False
    assert read_context.prompt_context_enabled is False
    assert read_context.public_schema_enabled is False


def test_source_gate_blocked_prevents_approved_projection() -> None:
    source = build_operation_flow_project_skill_registry_source(
        registry_name="project_skills",
        source_ref="config://skills/project-skills",
        declared_skill_ids=("skill.plan.formatting",),
    )
    record = _skill_record(
        capability=_capability(
            input_boundary_ref=None,
            output_boundary_ref=None,
        )
    )
    gate = validate_operation_flow_project_skill_registry_loading_gate(
        source=source,
        records=(record,),
    )

    review = review_operation_flow_skill_capability_for_projection(
        gate=gate,
        records=(record,),
        skill_id="skill.plan.formatting",
        capability_id="capability.plan.formatting",
    )
    projection = build_operation_flow_skill_capability_projection(review)

    assert gate.status == "blocked"
    assert review.review_status_candidate == "blocked_candidate"
    assert review.allowed_for_projection is False
    assert "source_gate_blocked" in review.blocking_reasons
    assert "input_boundary_missing" in review.blocking_reasons
    assert "output_boundary_missing" in review.blocking_reasons
    assert projection.projection_status_candidate == "blocked_candidate"
    assert projection.allowed_workflow_names == ()


def test_unknown_workflow_ref_blocks_workflow_reference() -> None:
    source = build_operation_flow_project_skill_registry_source(
        registry_name="project_skills",
        source_ref="config://skills/project-skills",
        declared_skill_ids=("skill.plan.formatting",),
    )
    record = _skill_record(
        capability=_capability(
            workflow_refs=("workflow-candidate://unknown_workflow",),
        )
    )
    gate = validate_operation_flow_project_skill_registry_loading_gate(
        source=source,
        records=(record,),
    )

    review = review_operation_flow_skill_capability_for_projection(
        gate=gate,
        records=(record,),
        skill_id="skill.plan.formatting",
        capability_id="capability.plan.formatting",
    )

    assert gate.status == "passed"
    assert review.review_status_candidate == "blocked_candidate"
    assert "workflow_ref_unknown:unknown_workflow" in review.blocking_reasons
    assert review.allowed_workflow_names == ()
    assert review.denied_workflow_names == ("unknown_workflow",)


def test_required_tools_must_still_pass_tools_gate() -> None:
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
    blocked_gate = validate_operation_flow_project_skill_registry_loading_gate(
        source=source,
        records=(record,),
    )
    allowed_gate = validate_operation_flow_project_skill_registry_loading_gate(
        source=source,
        records=(record,),
        tool_loading_gate=_passed_tool_gate("local_reference_reader"),
    )

    blocked_review = review_operation_flow_skill_capability_for_projection(
        gate=blocked_gate,
        records=(record,),
        skill_id="skill.reference.review",
        capability_id="capability.reference.review",
    )
    allowed_review = review_operation_flow_skill_capability_for_projection(
        gate=allowed_gate,
        records=(record,),
        skill_id="skill.reference.review",
        capability_id="capability.reference.review",
    )

    assert blocked_gate.status == "blocked"
    assert blocked_review.review_status_candidate == "blocked_candidate"
    assert "required_tool_dependency_not_satisfied" in (
        blocked_review.blocking_reasons
    )
    assert allowed_gate.status == "passed"
    assert allowed_review.review_status_candidate == "approved_candidate"


def test_raw_skill_material_and_secret_are_blocked() -> None:
    source = build_operation_flow_project_skill_registry_source(
        registry_name="project_skills",
        source_ref="config://skills/project-skills",
        declared_skill_ids=("skill.plan.formatting",),
    )
    record = _skill_record(
        capability=_capability(
            metadata={
                "raw_skill_instructions": "do not project this",
                "api_key": "secret",
            }
        )
    )
    gate = validate_operation_flow_project_skill_registry_loading_gate(
        source=source,
        records=(record,),
    )

    review = review_operation_flow_skill_capability_for_projection(
        gate=gate,
        records=(record,),
        skill_id="skill.plan.formatting",
        capability_id="capability.plan.formatting",
    )

    assert gate.status == "blocked"
    assert review.review_status_candidate == "blocked_candidate"
    assert "capability:raw_skill_material_forbidden:raw_skill_instructions" in (
        review.blocking_reasons
    )
    assert "capability:raw_secret_material_forbidden:api_key" in (
        review.blocking_reasons
    )


def test_workflow_slot_blocks_projection_not_allowed_for_workflow() -> None:
    _, record, gate = _passed_skill_gate()
    review = review_operation_flow_skill_capability_for_projection(
        gate=gate,
        records=(record,),
        skill_id="skill.plan.formatting",
        capability_id="capability.plan.formatting",
    )
    projection = build_operation_flow_skill_capability_projection(review)
    descriptor = build_operation_flow_plan_workflow_descriptor()
    denied_projection = build_operation_flow_skill_capability_projection(
        review,
        projection_id="skill-capability-projection://denied",
    )
    denied_projection = denied_projection.__class__(
        **{
            **denied_projection.__dict__,
            "allowed_workflow_names": (),
            "denied_workflow_names": (descriptor.workflow_name,),
        }
    )

    slot = build_operation_flow_workflow_skill_slot_reference(
        descriptor=descriptor,
        projection=denied_projection,
    )

    assert projection.projection_status_candidate == "approved_candidate"
    assert slot.slot_status_candidate == "blocked_candidate"
    assert "workflow_not_allowed_for_projection" in slot.blocking_reasons
    assert "workflow_denied_for_projection" in slot.blocking_reasons


def _passed_skill_gate():
    source = build_operation_flow_project_skill_registry_source(
        registry_name="project_skills",
        source_ref="config://skills/project-skills",
        declared_skill_ids=("skill.plan.formatting",),
    )
    record = _skill_record(capability=_capability())
    gate = validate_operation_flow_project_skill_registry_loading_gate(
        source=source,
        records=(record,),
    )
    return source, record, gate


def _skill_record(
    *,
    skill_id: str = "skill.plan.formatting",
    capability: OperationFlowProjectSkillCapabilityDeclarationCandidate,
    metadata: dict[str, object] | None = None,
) -> OperationFlowProjectSkillRegistryRecordCandidate:
    return OperationFlowProjectSkillRegistryRecordCandidate(
        skill_id=skill_id,
        metadata_view=SkillMetadataViewCandidate(
            l1_metadata=SkillL1MetadataCandidate(
                skill_id=skill_id,
                name="Plan Formatting",
                description="Candidate-only plan formatting skill.",
                capabilities=(capability.capability_id,),
                source_ref="tasks/b1/397",
                skill_file_ref="skills/plan-formatting/SKILL.md",
            )
        ),
        capability_declarations=(capability,),
        source_ref=f"skill-candidate://{skill_id}",
        metadata=dict(metadata or {}),
    )


def _capability(
    *,
    skill_id: str = "skill.plan.formatting",
    capability_id: str = "capability.plan.formatting",
    input_boundary_ref: str | None = "schema://skills/plan-formatting/input",
    output_boundary_ref: str | None = "boundary://skills/plan-formatting/output",
    workflow_refs: tuple[str, ...] = ("workflow-candidate://operation_flow_plan_workflow",),
    required_tool_names: tuple[str, ...] = (),
    metadata: dict[str, object] | None = None,
) -> OperationFlowProjectSkillCapabilityDeclarationCandidate:
    return OperationFlowProjectSkillCapabilityDeclarationCandidate(
        skill_id=skill_id,
        capability_id=capability_id,
        capability_name="Plan Formatting",
        description="Format structured plan output as a candidate capability.",
        domains=("operation_flow_plan_workflow",),
        task_kinds=("plan_formatting",),
        required_tool_names=required_tool_names,
        workflow_refs=workflow_refs,
        input_boundary_ref=input_boundary_ref,
        output_boundary_ref=output_boundary_ref,
        risk_level="low",
        script_policy="no_scripts",
        resource_policy="refs_only",
        metadata=dict(metadata or {}),
    )


def _passed_tool_gate(tool_name: str) -> OperationFlowToolLoadingGateCandidate:
    return OperationFlowToolLoadingGateCandidate(
        status="passed",
        risk_gate_status="passed",
        validations=(),
        allowed_tool_names=(tool_name,),
        blocked_tool_names=(),
        blocking_reasons=(),
        warnings=(),
        metadata={"test_gate": True},
    )
