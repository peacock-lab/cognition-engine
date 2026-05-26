from __future__ import annotations

from config_contexts import SkillL1MetadataCandidate, SkillMetadataViewCandidate
from cognition_operation_flows._tools.reference_reader import REFERENCE_READER_TOOL_NAME
from cognition_operation_flows._skills.capability_projection import (
    build_default_operation_flow_skill_capability_projection_status_summary,
    build_operation_flow_skill_capability_projection,
    build_operation_flow_skill_projection_read_context,
    build_operation_flow_workflow_skill_slot_reference,
    operation_flow_skill_capability_projection_status_dict,
    operation_flow_skill_projection_status_summary_status_dict,
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
    OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
    OPERATION_FLOW_PLAN_WORKFLOW_NAME,
    OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
    OPERATION_FLOW_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
    build_default_operation_flow_registry,
)
from cognition_operation_flows._tools.loading_validation import OperationFlowToolLoadingGateCandidate


def test_skill_capability_projection_real_samples_cover_four_workflows() -> None:
    registry = build_default_operation_flow_registry()
    records = _real_sample_records()
    source = build_operation_flow_project_skill_registry_source(
        registry_name="project_skills",
        source_ref="config://skills/project-skills",
        declared_skill_ids=tuple(record.skill_id for record in records),
    )
    gate = validate_operation_flow_project_skill_registry_loading_gate(
        source=source,
        records=records,
        tool_loading_gate=_passed_tool_gate(REFERENCE_READER_TOOL_NAME),
    )
    descriptors = {
        descriptor.workflow_name: descriptor for descriptor in registry.descriptors
    }

    assert gate.status == "passed"
    assert gate.allowed_for_candidate_reference is True
    assert gate.allowed_for_runtime_loading is False
    assert gate.allowed_for_tool_exposure is False
    assert gate.allowed_for_workflow_registration is False

    for sample in _real_samples():
        review = review_operation_flow_skill_capability_for_projection(
            gate=gate,
            records=records,
            skill_id=sample["skill_id"],
            capability_id=sample["capability_id"],
            workflow_registry=registry,
            evidence_refs=(sample["evidence_ref"],),
        )
        projection = build_operation_flow_skill_capability_projection(
            review,
            display_summary=sample["display_summary"],
            use_boundary=sample["use_boundary"],
        )
        slot = build_operation_flow_workflow_skill_slot_reference(
            descriptor=descriptors[sample["workflow_name"]],
            projection=projection,
            allowed_use=sample["allowed_use"],
        )
        projection_status = operation_flow_skill_capability_projection_status_dict(projection)
        slot_status = operation_flow_workflow_skill_slot_reference_status_dict(slot)

        assert review.review_status_candidate == "approved_candidate"
        assert review.allowed_workflow_names == (sample["workflow_name"],)
        assert projection.projection_status_candidate == "approved_candidate"
        assert projection.allowed_workflow_names == (sample["workflow_name"],)
        assert projection.runtime_enabled is False
        assert projection.skill_file_loading_enabled is False
        assert projection.resources_loading_enabled is False
        assert projection.scripts_execution_enabled is False
        assert projection.tool_exposure_enabled is False
        assert projection.agent_runtime_enabled is False
        assert projection.public_schema_enabled is False
        assert projection_status["metadata"]["does_not_include_raw_instructions"] is True
        assert projection_status["metadata"]["does_not_include_raw_resource_content"] is True
        assert projection_status["metadata"]["does_not_include_raw_script_body"] is True
        assert projection_status["metadata"]["does_not_include_secret"] is True
        assert slot.slot_status_candidate == "active_candidate"
        assert slot.reference_mode == "projection_summary_only"
        assert tuple(slot.allowed_use) == sample["allowed_use"]
        assert "skill_runtime_loading" in slot.forbidden_use
        assert "script_execution" in slot.forbidden_use
        assert "tool_exposure" in slot.forbidden_use
        assert "agent_runtime" in slot.forbidden_use
        assert "public_schema" in slot.forbidden_use
        assert slot_status["runtime_enabled"] is False
        assert slot_status["public_schema_enabled"] is False


def test_default_skill_capability_projection_status_summary_is_sanitized() -> None:
    summary = build_default_operation_flow_skill_capability_projection_status_summary()
    status = operation_flow_skill_projection_status_summary_status_dict(summary)

    assert status["status"] == "candidate_only_referenceable"
    assert status["projection_count"] == 4
    assert status["workflow_slot_reference_count"] == 4
    assert status["active_slot_reference_count"] == 4
    assert status["blocked_slot_reference_count"] == 0
    assert status["workflow_names"] == [
        OPERATION_FLOW_PLAN_WORKFLOW_NAME,
        OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
        OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
        OPERATION_FLOW_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
    ]
    assert status["reference_modes"] == ["projection_summary_only"]
    assert status["runtime_enabled"] is False
    assert status["skill_file_loading_enabled"] is False
    assert status["resources_loading_enabled"] is False
    assert status["scripts_execution_enabled"] is False
    assert status["tool_exposure_enabled"] is False
    assert status["agent_runtime_enabled"] is False
    assert status["prompt_context_enabled"] is False
    assert status["public_schema_enabled"] is False
    assert status["metadata"]["does_not_load_skill_file"] is True
    assert status["metadata"]["does_not_read_resources"] is True
    assert status["metadata"]["does_not_execute_scripts"] is True


def test_skill_projection_read_context_real_samples_cover_four_workflows() -> None:
    registry = build_default_operation_flow_registry()
    records = _real_sample_records()
    source = build_operation_flow_project_skill_registry_source(
        registry_name="project_skills",
        source_ref="config://skills/project-skills",
        declared_skill_ids=tuple(record.skill_id for record in records),
    )
    tool_gate = _passed_tool_gate(REFERENCE_READER_TOOL_NAME)
    gate = validate_operation_flow_project_skill_registry_loading_gate(
        source=source,
        records=records,
        tool_loading_gate=tool_gate,
    )
    descriptors = {
        descriptor.workflow_name: descriptor for descriptor in registry.descriptors
    }
    projections = []
    slots = []
    for sample in _real_samples():
        review = review_operation_flow_skill_capability_for_projection(
            gate=gate,
            records=records,
            skill_id=sample["skill_id"],
            capability_id=sample["capability_id"],
            workflow_registry=registry,
            evidence_refs=(sample["evidence_ref"],),
        )
        projection = build_operation_flow_skill_capability_projection(
            review,
            display_summary=sample["display_summary"],
            use_boundary=sample["use_boundary"],
        )
        projections.append(projection)
        slots.append(
            build_operation_flow_workflow_skill_slot_reference(
                descriptor=descriptors[sample["workflow_name"]],
                projection=projection,
                allowed_use=sample["allowed_use"],
            )
        )

    for sample in _real_samples():
        read_context = build_operation_flow_skill_projection_read_context(
            descriptor=descriptors[sample["workflow_name"]],
            projections=tuple(projections),
            slot_references=tuple(slots),
            allowed_use_stage=sample["allowed_use"][0],
            tool_loading_gate=tool_gate,
        )
        status = operation_flow_skill_projection_read_context_status_dict(
            read_context
        )

        assert read_context.status == "available_candidate"
        assert read_context.workflow_name == sample["workflow_name"]
        assert read_context.projection_refs == (
            f"skill-capability-projection://{sample['skill_id']}/{sample['capability_id']}",
        )
        assert read_context.capability_ids == (sample["capability_id"],)
        assert read_context.display_summaries == (sample["display_summary"],)
        assert read_context.use_boundaries == (sample["use_boundary"],)
        assert read_context.reference_modes == ("projection_summary_only",)
        assert read_context.runtime_enabled is False
        assert read_context.skill_file_loading_enabled is False
        assert read_context.resources_loading_enabled is False
        assert read_context.scripts_execution_enabled is False
        assert read_context.tool_exposure_enabled is False
        assert read_context.agent_runtime_enabled is False
        assert read_context.prompt_context_enabled is False
        assert read_context.public_schema_enabled is False
        assert status["metadata"]["read_context_only"] is True
        assert status["metadata"]["does_not_load_skill_file"] is True
        assert status["metadata"]["does_not_inject_prompt_context"] is True
        assert status["metadata"]["does_not_dispatch_runtime"] is True


def _real_samples() -> tuple[dict[str, object], ...]:
    return (
        {
            "skill_id": "skill.plan.design",
            "capability_id": "capability.plan.design",
            "workflow_name": OPERATION_FLOW_PLAN_WORKFLOW_NAME,
            "task_kind": "plan_design",
            "display_summary": "方案设计能力投影，用于稳定输出结构、约束和预算项。",
            "use_boundary": "仅作为 plan workflow 的结构化规划提示，不加载 Skill。",
            "allowed_use": ("workflow_planning_hint",),
            "evidence_ref": "evidence://skills/plan-design",
        },
        {
            "skill_id": "skill.reference.review",
            "capability_id": "capability.reference.review",
            "workflow_name": OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME,
            "task_kind": "reference_review",
            "display_summary": "资料审查能力投影，用于稳定输出符合性、风险和建议。",
            "use_boundary": "仅作为 reference review workflow 的审查结构提示，不执行工具。",
            "allowed_use": ("workflow_planning_hint", "status_evidence_summary"),
            "evidence_ref": "evidence://skills/reference-review",
        },
        {
            "skill_id": "skill.config.profile.explain",
            "capability_id": "capability.config.profile.explain",
            "workflow_name": OPERATION_FLOW_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
            "task_kind": "config_profile_explain",
            "display_summary": "配置解释能力投影，用于稳定解释配置优先级和覆盖关系。",
            "use_boundary": "仅作为 config profile explain workflow 的解释结构提示。",
            "allowed_use": ("status_evidence_summary",),
            "evidence_ref": "evidence://skills/config-profile-explain",
        },
        {
            "skill_id": "skill.evidence.audit",
            "capability_id": "capability.evidence.audit",
            "workflow_name": OPERATION_FLOW_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
            "task_kind": "run_workspace_evidence_audit",
            "display_summary": "证据审计能力投影，用于稳定审查 run workspace 证据完整性。",
            "use_boundary": "仅作为 evidence audit workflow 的证据摘要提示。",
            "allowed_use": ("status_evidence_summary",),
            "evidence_ref": "evidence://skills/evidence-audit",
        },
    )


def _real_sample_records() -> tuple[OperationFlowProjectSkillRegistryRecordCandidate, ...]:
    records: list[OperationFlowProjectSkillRegistryRecordCandidate] = []
    for sample in _real_samples():
        required_tools = (
            (REFERENCE_READER_TOOL_NAME,)
            if sample["workflow_name"] == OPERATION_FLOW_REFERENCE_REVIEW_WORKFLOW_NAME
            else ()
        )
        capability = OperationFlowProjectSkillCapabilityDeclarationCandidate(
            skill_id=sample["skill_id"],
            capability_id=sample["capability_id"],
            capability_name=str(sample["display_summary"]).split("，", 1)[0],
            description=str(sample["display_summary"]),
            domains=(sample["workflow_name"],),
            task_kinds=(sample["task_kind"],),
            required_tool_names=required_tools,
            workflow_refs=(f"workflow-candidate://{sample['workflow_name']}",),
            input_boundary_ref=f"schema://skills/{sample['skill_id']}/input",
            output_boundary_ref=f"boundary://skills/{sample['skill_id']}/output",
            risk_level="low",
            script_policy="no_scripts",
            resource_policy="refs_only",
        )
        records.append(
            OperationFlowProjectSkillRegistryRecordCandidate(
                skill_id=sample["skill_id"],
                metadata_view=SkillMetadataViewCandidate(
                    l1_metadata=SkillL1MetadataCandidate(
                        skill_id=sample["skill_id"],
                        name=str(sample["skill_id"]),
                        description=str(sample["display_summary"]),
                        capabilities=(sample["capability_id"],),
                        source_ref="tasks/b1/398",
                        skill_file_ref=f"skills/{sample['skill_id']}/SKILL.md",
                    )
                ),
                capability_declarations=(capability,),
                source_ref=f"skill-candidate://{sample['skill_id']}",
            )
        )
    return tuple(records)


def _passed_tool_gate(tool_name: str) -> OperationFlowToolLoadingGateCandidate:
    return OperationFlowToolLoadingGateCandidate(
        status="passed",
        risk_gate_status="passed",
        validations=(),
        allowed_tool_names=(tool_name,),
        blocked_tool_names=(),
        blocking_reasons=(),
        warnings=(),
        metadata={"real_sample_gate": True},
    )
