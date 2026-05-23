"""Candidate-only Skills capability projections for task workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from cognition_operation_flows._skills.projection_context import (
    TWF_SKILL_CAPABILITY_ALLOWED_SLOT_USES,
    TWF_SKILL_CAPABILITY_FORBIDDEN_SLOT_USES,
    TWF_SKILL_CAPABILITY_REFERENCEABLE_SLOT_STATUSES,
)
from config_contexts import SkillL1MetadataCandidate, SkillMetadataViewCandidate
from cognition_operation_flows._tools.reference_reader import REFERENCE_READER_TOOL_NAME
from cognition_operation_flows._skills.registry_admission import (
    TWF_SKILL_FORBIDDEN_RAW_KEYS,
    TWF_SKILL_RESOURCE_POLICIES,
    TWF_SKILL_RISK_LEVEL_ORDER,
    TWF_SKILL_SCRIPT_POLICIES,
    TWF_SKILL_SECRET_KEY_MARKERS,
    TwfProjectSkillCapabilityDeclarationCandidate,
    TwfProjectSkillLoadingValidationCandidate,
    TwfProjectSkillRegistryLoadingGateCandidate,
    TwfProjectSkillRegistryRecordCandidate,
    build_twf_project_skill_registry_source,
    validate_twf_project_skill_registry_loading_gate,
)
from cognition_operation_flows._requests.registry import (
    TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
    TWF_PLAN_WORKFLOW_NAME,
    TWF_REFERENCE_REVIEW_WORKFLOW_NAME,
    TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
    TwfDescriptorCandidate,
    TwfRegistryCandidate,
    build_default_twf_registry,
)
from cognition_operation_flows._tools.loading_validation import TwfToolLoadingGateCandidate


TWF_SKILL_CAPABILITY_PROJECTION_STAGES = (
    "registry_gate_review",
    "capability_declaration_review",
    "tool_dependency_boundary_review",
    "workflow_reference_review",
    "raw_material_boundary_review",
    "projection_boundary_review",
)


@dataclass(frozen=True)
class TwfSkillCapabilityReviewCandidate:
    """Candidate-only review for projecting one Skill capability."""

    review_id: str
    registry_name: str
    skill_id: str
    capability_id: str
    capability_name: str
    source_ref: str | None
    source_gate_status: str
    source_validation_status: str
    domains: tuple[str, ...] = ()
    task_kinds: tuple[str, ...] = ()
    workflow_refs: tuple[str, ...] = ()
    agent_role_refs: tuple[str, ...] = ()
    required_tool_names: tuple[str, ...] = ()
    optional_tool_names: tuple[str, ...] = ()
    input_boundary_ref: str | None = None
    output_boundary_ref: str | None = None
    risk_level: str = "unknown"
    script_policy: str = "blocked"
    resource_policy: str = "blocked"
    review_status_candidate: str = "blocked_candidate"
    allowed_for_projection: bool = False
    allowed_for_workflow_reference: bool = False
    allowed_workflow_names: tuple[str, ...] = ()
    denied_workflow_names: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    approval_ref: str | None = None
    audit_ref: str | None = None
    candidate_only: bool = True
    runtime_enabled: bool = False
    skill_file_loading_enabled: bool = False
    resources_loading_enabled: bool = False
    scripts_execution_enabled: bool = False
    tool_exposure_enabled: bool = False
    agent_runtime_enabled: bool = False
    workflow_registration_enabled: bool = False
    public_schema_enabled: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfSkillCapabilityProjectionCandidate:
    """Sanitized Skill capability projection for workflow-side reference."""

    projection_id: str
    source_review_id: str
    registry_name: str
    skill_id: str
    capability_id: str
    capability_name: str
    projection_status_candidate: str
    display_summary: str
    use_boundary: str
    domains: tuple[str, ...] = ()
    task_kinds: tuple[str, ...] = ()
    input_boundary_ref: str | None = None
    output_boundary_ref: str | None = None
    risk_level: str = "unknown"
    script_policy: str = "blocked"
    resource_policy: str = "blocked"
    tool_dependency_summary: tuple[str, ...] = ()
    workflow_ref_summary: tuple[str, ...] = ()
    allowed_workflow_names: tuple[str, ...] = ()
    denied_workflow_names: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    approval_ref: str | None = None
    audit_ref: str | None = None
    visibility: str = "workflow_visible"
    sensitivity: str = "low"
    confidence: str = "medium"
    candidate_only: bool = True
    runtime_enabled: bool = False
    skill_file_loading_enabled: bool = False
    resources_loading_enabled: bool = False
    scripts_execution_enabled: bool = False
    tool_exposure_enabled: bool = False
    agent_runtime_enabled: bool = False
    prompt_context_enabled: bool = False
    workflow_registration_enabled: bool = False
    public_schema_enabled: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfWorkflowSkillSlotReferenceCandidate:
    """Candidate-only workflow slot reference to a Skill capability projection."""

    slot_ref: str
    workflow_name: str
    workflow_version: str
    task_kind: str
    projection_id: str
    skill_id: str
    capability_id: str
    reference_mode: str = "projection_summary_only"
    allowed_use: tuple[str, ...] = ("workflow_planning_hint",)
    forbidden_use: tuple[str, ...] = TWF_SKILL_CAPABILITY_FORBIDDEN_SLOT_USES
    slot_status_candidate: str = "blocked_candidate"
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    candidate_only: bool = True
    runtime_enabled: bool = False
    skill_file_loading_enabled: bool = False
    resources_loading_enabled: bool = False
    scripts_execution_enabled: bool = False
    tool_exposure_enabled: bool = False
    agent_runtime_enabled: bool = False
    prompt_context_enabled: bool = False
    public_schema_enabled: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


def review_twf_skill_capability_for_projection(
    *,
    gate: TwfProjectSkillRegistryLoadingGateCandidate,
    records: Sequence[TwfProjectSkillRegistryRecordCandidate],
    skill_id: str,
    capability_id: str,
    workflow_registry: TwfRegistryCandidate | None = None,
    approval_ref: str | None = None,
    audit_ref: str | None = None,
    evidence_refs: Sequence[str] = (),
    max_risk_level: str = "medium",
) -> TwfSkillCapabilityReviewCandidate:
    """Review one Skill capability for sanitized projection without loading it."""

    registry = workflow_registry or build_default_twf_registry()
    descriptor_names = {
        descriptor.workflow_name for descriptor in registry.descriptors
    }
    blocking: list[str] = []
    warnings: list[str] = []

    if gate.status != "passed":
        blocking.append("source_gate_blocked")
    if not gate.allowed_for_candidate_reference:
        blocking.append("source_gate_not_referenceable")
    _collect_flag_blocks("source_gate", gate.metadata, blocking)

    record = _find_record(records, skill_id)
    validation = _find_validation(gate.validations, skill_id)
    capability = _find_capability(record, capability_id) if record else None

    if record is None:
        blocking.append("skill_record_missing")
    else:
        _collect_flag_blocks("record", record.metadata, blocking)
        warnings.extend(record.warnings)
        blocking.extend(f"record:{reason}" for reason in record.blocking_reasons)

    if validation is None:
        blocking.append("source_validation_missing")
        source_validation_status = "missing"
    else:
        source_validation_status = validation.status
        if not validation.allowed_for_candidate_reference:
            blocking.append("source_validation_not_referenceable")
        if not validation.dependencies_satisfied:
            blocking.append("tool_dependency_gate_failed")
        warnings.extend(validation.warnings)
        blocking.extend(
            f"source_validation:{reason}"
            for reason in validation.blocking_reasons
        )
        _collect_flag_blocks("source_validation", validation.metadata, blocking)

    if capability is None:
        blocking.append("capability_declaration_missing")
        capability = _empty_capability(skill_id=skill_id, capability_id=capability_id)
    else:
        _collect_flag_blocks("capability", capability.metadata, blocking)

    normalized_risk = _normalize_risk(capability.risk_level)
    script_policy = _normalize_policy(
        capability.script_policy,
        TWF_SKILL_SCRIPT_POLICIES,
        default="blocked",
    )
    resource_policy = _normalize_policy(
        capability.resource_policy,
        TWF_SKILL_RESOURCE_POLICIES,
        default="blocked",
    )
    if not capability.skill_id.strip():
        blocking.append("skill_id_missing")
    if capability.skill_id and capability.skill_id != skill_id:
        blocking.append("skill_id_mismatch")
    if not capability.capability_id.strip():
        blocking.append("capability_id_missing")
    if not capability.capability_name.strip():
        blocking.append("capability_name_missing")
    if not capability.input_boundary_ref:
        blocking.append("input_boundary_missing")
    if not capability.output_boundary_ref:
        blocking.append("output_boundary_missing")
    if normalized_risk == "unknown":
        blocking.append("risk_level_missing")
    if normalized_risk == "blocked":
        blocking.append("risk_blocked")
    if not _risk_at_or_below(normalized_risk, max_risk_level):
        blocking.append("risk_exceeds_policy")
    if script_policy == "blocked":
        blocking.append("script_policy_blocked")
    if script_policy == "review_required":
        blocking.append("script_policy_review_required")
    if resource_policy == "blocked":
        blocking.append("resource_policy_blocked")
    if resource_policy == "review_required":
        blocking.append("resource_policy_review_required")
    if not capability.workflow_refs:
        blocking.append("workflow_refs_missing")

    workflow_names = tuple(
        _ordered_unique(_workflow_name_from_ref(ref) for ref in capability.workflow_refs)
    )
    unknown_workflow_names = tuple(
        name for name in workflow_names if name and name not in descriptor_names
    )
    if unknown_workflow_names:
        blocking.extend(
            f"workflow_ref_unknown:{name}" for name in unknown_workflow_names
        )
    allowed_workflow_names = tuple(
        name for name in workflow_names if name and name in descriptor_names
    )
    tool_dependencies = tuple(
        _ordered_unique(
            (
                *capability.required_tool_names,
                *capability.optional_tool_names,
                *capability.allowed_tool_names,
            )
        )
    )
    if capability.required_tool_names and (
        validation is None
        or validation.tools_dependency_gate_status != "passed"
        or not validation.dependencies_satisfied
    ):
        blocking.append("required_tool_dependency_not_satisfied")

    status = "approved_candidate" if not blocking else "blocked_candidate"
    return TwfSkillCapabilityReviewCandidate(
        review_id=f"skill-capability-review://{skill_id}/{capability_id}",
        registry_name=gate.registry_name,
        skill_id=skill_id,
        capability_id=capability_id,
        capability_name=capability.capability_name,
        source_ref=record.source_ref if record else None,
        source_gate_status=gate.status,
        source_validation_status=source_validation_status,
        domains=capability.domains,
        task_kinds=capability.task_kinds,
        workflow_refs=capability.workflow_refs,
        agent_role_refs=capability.agent_role_refs,
        required_tool_names=capability.required_tool_names,
        optional_tool_names=capability.optional_tool_names,
        input_boundary_ref=capability.input_boundary_ref,
        output_boundary_ref=capability.output_boundary_ref,
        risk_level=normalized_risk,
        script_policy=script_policy,
        resource_policy=resource_policy,
        review_status_candidate=status,
        allowed_for_projection=not blocking,
        allowed_for_workflow_reference=not blocking,
        allowed_workflow_names=allowed_workflow_names if not blocking else (),
        denied_workflow_names=unknown_workflow_names,
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        evidence_refs=tuple(_ordered_unique(evidence_refs)),
        approval_ref=approval_ref,
        audit_ref=audit_ref,
        metadata={
            "stages": list(TWF_SKILL_CAPABILITY_PROJECTION_STAGES),
            "candidate_only": True,
            "tool_dependency_summary": list(tool_dependencies),
            "workflow_registry_version": registry.registry_version,
            "does_not_load_skill_file": True,
            "does_not_read_resources": True,
            "does_not_execute_scripts": True,
            "does_not_create_skill_toolset": True,
            "does_not_call_adk_skill_registry": True,
            "does_not_expose_tool": True,
            "does_not_register_workflow": True,
            "does_not_call_agent_runtime": True,
        },
    )


def build_twf_skill_capability_projection(
    review: TwfSkillCapabilityReviewCandidate,
    *,
    projection_id: str | None = None,
    display_summary: str | None = None,
    use_boundary: str | None = None,
    visibility: str = "workflow_visible",
    sensitivity: str = "low",
    confidence: str = "medium",
) -> TwfSkillCapabilityProjectionCandidate:
    """Build a sanitized capability projection from a candidate-only review."""

    status = (
        "approved_candidate"
        if review.allowed_for_projection
        and review.review_status_candidate == "approved_candidate"
        else "blocked_candidate"
    )
    resolved_projection_id = (
        projection_id
        or f"skill-capability-projection://{review.skill_id}/{review.capability_id}"
    )
    return TwfSkillCapabilityProjectionCandidate(
        projection_id=resolved_projection_id,
        source_review_id=review.review_id,
        registry_name=review.registry_name,
        skill_id=review.skill_id,
        capability_id=review.capability_id,
        capability_name=review.capability_name,
        projection_status_candidate=status,
        display_summary=display_summary
        or _default_projection_summary(
            capability_name=review.capability_name,
            task_kinds=review.task_kinds,
        ),
        use_boundary=use_boundary
        or (
            "Use this projection only as a workflow planning/status hint; "
            "do not load or execute the Skill."
        ),
        domains=review.domains,
        task_kinds=review.task_kinds,
        input_boundary_ref=review.input_boundary_ref,
        output_boundary_ref=review.output_boundary_ref,
        risk_level=review.risk_level,
        script_policy=review.script_policy,
        resource_policy=review.resource_policy,
        tool_dependency_summary=tuple(
            _ordered_unique(
                (
                    *review.required_tool_names,
                    *review.optional_tool_names,
                )
            )
        ),
        workflow_ref_summary=review.workflow_refs,
        allowed_workflow_names=review.allowed_workflow_names
        if status == "approved_candidate"
        else (),
        denied_workflow_names=review.denied_workflow_names,
        evidence_refs=review.evidence_refs,
        approval_ref=review.approval_ref,
        audit_ref=review.audit_ref,
        visibility=visibility,
        sensitivity=sensitivity,
        confidence=confidence,
        metadata={
            "candidate_only": True,
            "sanitized_projection": True,
            "review_status_candidate": review.review_status_candidate,
            "blocking_reasons": list(review.blocking_reasons),
            "does_not_include_skill_file_body": True,
            "does_not_include_raw_instructions": True,
            "does_not_include_raw_resource_content": True,
            "does_not_include_raw_script_body": True,
            "does_not_include_secret": True,
            "does_not_include_raw_adk_object": True,
            "does_not_include_model_response": True,
            "does_not_include_external_call_result": True,
            "runtime_enabled": False,
            "skill_file_loading_enabled": False,
            "resources_loading_enabled": False,
            "scripts_execution_enabled": False,
            "tool_exposure_enabled": False,
            "agent_runtime_enabled": False,
            "public_schema_enabled": False,
        },
    )


def build_twf_workflow_skill_slot_reference(
    *,
    descriptor: TwfDescriptorCandidate,
    projection: TwfSkillCapabilityProjectionCandidate,
    slot_ref: str | None = None,
    allowed_use: Sequence[str] = ("workflow_planning_hint",),
) -> TwfWorkflowSkillSlotReferenceCandidate:
    """Build a read-only workflow slot reference to a capability projection."""

    blocking: list[str] = []
    warnings: list[str] = []
    if descriptor.skills_slot_status not in TWF_SKILL_CAPABILITY_REFERENCEABLE_SLOT_STATUSES:
        blocking.append("workflow_skills_slot_not_reference_only")
    if projection.projection_status_candidate != "approved_candidate":
        blocking.append("projection_not_approved")
    if descriptor.workflow_name not in projection.allowed_workflow_names:
        blocking.append("workflow_not_allowed_for_projection")
    if descriptor.workflow_name in projection.denied_workflow_names:
        blocking.append("workflow_denied_for_projection")
    normalized_allowed_use = tuple(
        use for use in _ordered_unique(allowed_use) if use in TWF_SKILL_CAPABILITY_ALLOWED_SLOT_USES
    )
    if len(normalized_allowed_use) != len(tuple(_ordered_unique(allowed_use))):
        warnings.append("unsupported_allowed_use_ignored")
    if not normalized_allowed_use:
        blocking.append("allowed_use_missing")
    status = "active_candidate" if not blocking else "blocked_candidate"
    return TwfWorkflowSkillSlotReferenceCandidate(
        slot_ref=slot_ref
        or f"workflow-skill-slot://{descriptor.workflow_name}/{projection.projection_id}",
        workflow_name=descriptor.workflow_name,
        workflow_version=descriptor.workflow_version,
        task_kind=descriptor.task_kind,
        projection_id=projection.projection_id,
        skill_id=projection.skill_id,
        capability_id=projection.capability_id,
        reference_mode="projection_summary_only",
        allowed_use=normalized_allowed_use,
        forbidden_use=TWF_SKILL_CAPABILITY_FORBIDDEN_SLOT_USES,
        slot_status_candidate=status,
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "candidate_only": True,
            "does_not_load_skill_file": True,
            "does_not_read_resources": True,
            "does_not_execute_scripts": True,
            "does_not_create_skill_toolset": True,
            "does_not_expose_tool": True,
            "does_not_call_agent_runtime": True,
            "reference_mode": "projection_summary_only",
        },
    )


def build_twf_skill_projection_read_context(
    *,
    descriptor: TwfDescriptorCandidate,
    projections: Sequence[TwfSkillCapabilityProjectionCandidate | Mapping[str, Any]],
    slot_references: Sequence[
        TwfWorkflowSkillSlotReferenceCandidate | Mapping[str, Any]
    ],
    allowed_use_stage: str,
    tool_loading_gate: TwfToolLoadingGateCandidate | Mapping[str, Any] | None = None,
) -> TwfSkillProjectionReadContextCandidate:
    """Build sanitized read-only Skill projection context for one workflow."""

    projection_statuses = {
        str(status.get("projection_id") or ""): status
        for status in (_projection_status_dict(projection) for projection in projections)
        if status.get("projection_id")
    }
    slot_statuses = tuple(_slot_status_dict(slot) for slot in slot_references)
    relevant_slots = tuple(
        status
        for status in slot_statuses
        if status.get("workflow_name") == descriptor.workflow_name
    )
    blocking: list[str] = []
    warnings: list[str] = []
    if allowed_use_stage not in TWF_SKILL_CAPABILITY_ALLOWED_SLOT_USES:
        blocking.append("allowed_use_stage_unsupported")
    if descriptor.skills_slot_status not in TWF_SKILL_CAPABILITY_REFERENCEABLE_SLOT_STATUSES:
        blocking.append("workflow_skills_slot_not_reference_only")
    if not projection_statuses:
        return _unavailable_read_context(
            descriptor=descriptor,
            allowed_use_stage=allowed_use_stage,
            blocking_reasons=("projection_missing",),
        )
    if not relevant_slots:
        return _unavailable_read_context(
            descriptor=descriptor,
            allowed_use_stage=allowed_use_stage,
            blocking_reasons=("workflow_slot_reference_missing",),
        )

    selected_projections: list[dict[str, Any]] = []
    selected_slots: list[dict[str, Any]] = []
    tool_gate_status = _tool_gate_status_dict(tool_loading_gate)
    allowed_tool_names = set(tool_gate_status.get("allowed_tool_names") or ())
    tool_gate_passed = tool_gate_status.get("status") == "passed"
    for slot in relevant_slots:
        selected_slots.append(slot)
        projection_id = str(slot.get("projection_id") or "")
        projection = projection_statuses.get(projection_id)
        if projection is None:
            blocking.append(f"projection_missing_for_slot:{projection_id}")
            continue
        selected_projections.append(projection)
        if slot.get("slot_status_candidate") != "active_candidate":
            blocking.append("slot_not_active_candidate")
        if slot.get("reference_mode") != "projection_summary_only":
            blocking.append("reference_mode_not_projection_summary_only")
        if allowed_use_stage not in tuple(slot.get("allowed_use") or ()):
            blocking.append("allowed_use_stage_not_allowed")
        if allowed_use_stage in tuple(slot.get("forbidden_use") or ()):
            blocking.append("allowed_use_stage_forbidden")
        if projection.get("projection_status_candidate") != "approved_candidate":
            blocking.append("projection_not_approved")
        if descriptor.workflow_name not in tuple(
            projection.get("allowed_workflow_names") or ()
        ):
            blocking.append("workflow_not_allowed_for_projection")
        if descriptor.workflow_name in tuple(
            projection.get("denied_workflow_names") or ()
        ):
            blocking.append("workflow_denied_for_projection")
        for tool_name in tuple(projection.get("tool_dependency_summary") or ()):
            if not tool_gate_passed:
                blocking.append(f"tool_dependency_gate_missing:{tool_name}")
            elif tool_name not in allowed_tool_names:
                blocking.append(f"tool_dependency_not_allowed:{tool_name}")
        _collect_status_flag_blocks("projection", projection, blocking)
        _collect_status_flag_blocks("slot", slot, blocking)
        _collect_status_raw_material_blocks("projection", projection, blocking)
        _collect_status_raw_material_blocks("slot", slot, blocking)
        warnings.extend(str(warning) for warning in slot.get("warnings") or ())
        warnings.extend(str(warning) for warning in projection.get("warnings") or ())

    combined_statuses = (*selected_projections, *selected_slots)
    runtime_enabled = any(
        _status_flag_enabled(status, "runtime_enabled")
        for status in combined_statuses
    )
    skill_file_loading_enabled = any(
        _status_flag_enabled(status, "skill_file_loading_enabled")
        for status in combined_statuses
    )
    resources_loading_enabled = any(
        _status_flag_enabled(status, "resources_loading_enabled")
        for status in combined_statuses
    )
    scripts_execution_enabled = any(
        _status_flag_enabled(status, "scripts_execution_enabled")
        for status in combined_statuses
    )
    tool_exposure_enabled = any(
        _status_flag_enabled(status, "tool_exposure_enabled")
        for status in combined_statuses
    )
    agent_runtime_enabled = any(
        _status_flag_enabled(status, "agent_runtime_enabled")
        for status in combined_statuses
    )
    prompt_context_enabled = any(
        _status_flag_enabled(status, "prompt_context_enabled")
        for status in combined_statuses
    )
    workflow_registration_enabled = any(
        _status_flag_enabled(status, "workflow_registration_enabled")
        for status in combined_statuses
    )
    public_schema_enabled = any(
        _status_flag_enabled(status, "public_schema_enabled")
        for status in combined_statuses
    )
    status = "available_candidate" if not blocking else "blocked_candidate"
    return TwfSkillProjectionReadContextCandidate(
        status=status,
        workflow_name=descriptor.workflow_name,
        workflow_version=descriptor.workflow_version,
        task_kind=descriptor.task_kind,
        allowed_use_stage=allowed_use_stage,
        projection_refs=tuple(
            _ordered_unique(
                str(projection.get("projection_id") or "")
                for projection in selected_projections
            )
        ),
        skill_ids=tuple(
            _ordered_unique(
                str(projection.get("skill_id") or "")
                for projection in selected_projections
            )
        ),
        capability_ids=tuple(
            _ordered_unique(
                str(projection.get("capability_id") or "")
                for projection in selected_projections
            )
        ),
        capability_names=tuple(
            _ordered_unique(
                str(projection.get("capability_name") or "")
                for projection in selected_projections
            )
        ),
        display_summaries=tuple(
            _ordered_unique(
                str(projection.get("display_summary") or "")
                for projection in selected_projections
            )
        ),
        use_boundaries=tuple(
            _ordered_unique(
                str(projection.get("use_boundary") or "")
                for projection in selected_projections
            )
        ),
        slot_refs=tuple(
            _ordered_unique(str(slot.get("slot_ref") or "") for slot in selected_slots)
        ),
        reference_modes=tuple(
            _ordered_unique(
                str(slot.get("reference_mode") or "") for slot in selected_slots
            )
        ),
        allowed_use=tuple(
            _ordered_unique(
                allowed_use
                for slot in selected_slots
                for allowed_use in tuple(slot.get("allowed_use") or ())
            )
        ),
        evidence_refs=tuple(
            _ordered_unique(
                evidence_ref
                for projection in selected_projections
                for evidence_ref in tuple(projection.get("evidence_refs") or ())
            )
        ),
        risk_levels=tuple(
            _ordered_unique(
                str(projection.get("risk_level") or "")
                for projection in selected_projections
            )
        ),
        sensitivities=tuple(
            _ordered_unique(
                str(projection.get("sensitivity") or "")
                for projection in selected_projections
            )
        ),
        confidences=tuple(
            _ordered_unique(
                str(projection.get("confidence") or "")
                for projection in selected_projections
            )
        ),
        tool_dependency_summary=tuple(
            _ordered_unique(
                tool_name
                for projection in selected_projections
                for tool_name in tuple(projection.get("tool_dependency_summary") or ())
            )
        ),
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        runtime_enabled=runtime_enabled,
        skill_file_loading_enabled=skill_file_loading_enabled,
        resources_loading_enabled=resources_loading_enabled,
        scripts_execution_enabled=scripts_execution_enabled,
        tool_exposure_enabled=tool_exposure_enabled,
        agent_runtime_enabled=agent_runtime_enabled,
        prompt_context_enabled=prompt_context_enabled,
        workflow_registration_enabled=workflow_registration_enabled,
        public_schema_enabled=public_schema_enabled,
        metadata={
            "candidate_only": True,
            "reference_only": True,
            "sanitized_summary": True,
            "read_context_only": True,
            "does_not_load_skill_file": True,
            "does_not_read_resources": True,
            "does_not_execute_scripts": True,
            "does_not_create_skill_toolset": True,
            "does_not_call_adk_skill_registry": True,
            "does_not_expose_tool": True,
            "does_not_call_agent_runtime": True,
            "does_not_register_workflow": True,
            "does_not_inject_prompt_context": True,
            "does_not_dispatch_runtime": True,
            "tool_gate_status": tool_gate_status.get("status"),
        },
    )


def twf_skill_capability_review_status_dict(
    review: TwfSkillCapabilityReviewCandidate,
) -> dict[str, Any]:
    """Return a JSON-ready capability review summary."""

    return {
        "review_id": review.review_id,
        "registry_name": review.registry_name,
        "skill_id": review.skill_id,
        "capability_id": review.capability_id,
        "capability_name": review.capability_name,
        "source_ref": review.source_ref,
        "source_gate_status": review.source_gate_status,
        "source_validation_status": review.source_validation_status,
        "domains": list(review.domains),
        "task_kinds": list(review.task_kinds),
        "workflow_refs": list(review.workflow_refs),
        "agent_role_refs": list(review.agent_role_refs),
        "required_tool_names": list(review.required_tool_names),
        "optional_tool_names": list(review.optional_tool_names),
        "input_boundary_ref": review.input_boundary_ref,
        "output_boundary_ref": review.output_boundary_ref,
        "risk_level": review.risk_level,
        "script_policy": review.script_policy,
        "resource_policy": review.resource_policy,
        "review_status_candidate": review.review_status_candidate,
        "allowed_for_projection": review.allowed_for_projection,
        "allowed_for_workflow_reference": review.allowed_for_workflow_reference,
        "allowed_workflow_names": list(review.allowed_workflow_names),
        "denied_workflow_names": list(review.denied_workflow_names),
        "blocking_reasons": list(review.blocking_reasons),
        "warnings": list(review.warnings),
        "evidence_refs": list(review.evidence_refs),
        "approval_ref": review.approval_ref,
        "audit_ref": review.audit_ref,
        "candidate_only": review.candidate_only,
        "runtime_enabled": review.runtime_enabled,
        "skill_file_loading_enabled": review.skill_file_loading_enabled,
        "resources_loading_enabled": review.resources_loading_enabled,
        "scripts_execution_enabled": review.scripts_execution_enabled,
        "tool_exposure_enabled": review.tool_exposure_enabled,
        "agent_runtime_enabled": review.agent_runtime_enabled,
        "workflow_registration_enabled": review.workflow_registration_enabled,
        "public_schema_enabled": review.public_schema_enabled,
        "metadata": dict(review.metadata),
    }


def twf_skill_capability_projection_status_dict(
    projection: TwfSkillCapabilityProjectionCandidate,
) -> dict[str, Any]:
    """Return a JSON-ready sanitized capability projection."""

    return {
        "projection_id": projection.projection_id,
        "source_review_id": projection.source_review_id,
        "registry_name": projection.registry_name,
        "skill_id": projection.skill_id,
        "capability_id": projection.capability_id,
        "capability_name": projection.capability_name,
        "projection_status_candidate": projection.projection_status_candidate,
        "display_summary": projection.display_summary,
        "use_boundary": projection.use_boundary,
        "domains": list(projection.domains),
        "task_kinds": list(projection.task_kinds),
        "input_boundary_ref": projection.input_boundary_ref,
        "output_boundary_ref": projection.output_boundary_ref,
        "risk_level": projection.risk_level,
        "script_policy": projection.script_policy,
        "resource_policy": projection.resource_policy,
        "tool_dependency_summary": list(projection.tool_dependency_summary),
        "workflow_ref_summary": list(projection.workflow_ref_summary),
        "allowed_workflow_names": list(projection.allowed_workflow_names),
        "denied_workflow_names": list(projection.denied_workflow_names),
        "evidence_refs": list(projection.evidence_refs),
        "approval_ref": projection.approval_ref,
        "audit_ref": projection.audit_ref,
        "visibility": projection.visibility,
        "sensitivity": projection.sensitivity,
        "confidence": projection.confidence,
        "candidate_only": projection.candidate_only,
        "runtime_enabled": projection.runtime_enabled,
        "skill_file_loading_enabled": projection.skill_file_loading_enabled,
        "resources_loading_enabled": projection.resources_loading_enabled,
        "scripts_execution_enabled": projection.scripts_execution_enabled,
        "tool_exposure_enabled": projection.tool_exposure_enabled,
        "agent_runtime_enabled": projection.agent_runtime_enabled,
        "prompt_context_enabled": projection.prompt_context_enabled,
        "workflow_registration_enabled": projection.workflow_registration_enabled,
        "public_schema_enabled": projection.public_schema_enabled,
        "metadata": dict(projection.metadata),
    }


def twf_workflow_skill_slot_reference_status_dict(
    reference: TwfWorkflowSkillSlotReferenceCandidate,
) -> dict[str, Any]:
    """Return a JSON-ready workflow Skill slot reference summary."""

    return {
        "slot_ref": reference.slot_ref,
        "workflow_name": reference.workflow_name,
        "workflow_version": reference.workflow_version,
        "task_kind": reference.task_kind,
        "projection_id": reference.projection_id,
        "skill_id": reference.skill_id,
        "capability_id": reference.capability_id,
        "reference_mode": reference.reference_mode,
        "allowed_use": list(reference.allowed_use),
        "forbidden_use": list(reference.forbidden_use),
        "slot_status_candidate": reference.slot_status_candidate,
        "blocking_reasons": list(reference.blocking_reasons),
        "warnings": list(reference.warnings),
        "candidate_only": reference.candidate_only,
        "runtime_enabled": reference.runtime_enabled,
        "skill_file_loading_enabled": reference.skill_file_loading_enabled,
        "resources_loading_enabled": reference.resources_loading_enabled,
        "scripts_execution_enabled": reference.scripts_execution_enabled,
        "tool_exposure_enabled": reference.tool_exposure_enabled,
        "agent_runtime_enabled": reference.agent_runtime_enabled,
        "prompt_context_enabled": reference.prompt_context_enabled,
        "public_schema_enabled": reference.public_schema_enabled,
        "metadata": dict(reference.metadata),
    }


def twf_skill_projection_read_context_status_dict(
    read_context: TwfSkillProjectionReadContextCandidate,
) -> dict[str, Any]:
    """Return a JSON-ready workflow Skill projection read context."""

    return {
        "status": read_context.status,
        "workflow_name": read_context.workflow_name,
        "workflow_version": read_context.workflow_version,
        "task_kind": read_context.task_kind,
        "allowed_use_stage": read_context.allowed_use_stage,
        "projection_refs": list(read_context.projection_refs),
        "skill_ids": list(read_context.skill_ids),
        "capability_ids": list(read_context.capability_ids),
        "capability_names": list(read_context.capability_names),
        "display_summaries": list(read_context.display_summaries),
        "use_boundaries": list(read_context.use_boundaries),
        "slot_refs": list(read_context.slot_refs),
        "reference_modes": list(read_context.reference_modes),
        "allowed_use": list(read_context.allowed_use),
        "evidence_refs": list(read_context.evidence_refs),
        "risk_levels": list(read_context.risk_levels),
        "sensitivities": list(read_context.sensitivities),
        "confidences": list(read_context.confidences),
        "tool_dependency_summary": list(read_context.tool_dependency_summary),
        "blocking_reasons": list(read_context.blocking_reasons),
        "warnings": list(read_context.warnings),
        "candidate_only": read_context.candidate_only,
        "reference_only": read_context.reference_only,
        "runtime_enabled": read_context.runtime_enabled,
        "skill_file_loading_enabled": read_context.skill_file_loading_enabled,
        "resources_loading_enabled": read_context.resources_loading_enabled,
        "scripts_execution_enabled": read_context.scripts_execution_enabled,
        "tool_exposure_enabled": read_context.tool_exposure_enabled,
        "agent_runtime_enabled": read_context.agent_runtime_enabled,
        "prompt_context_enabled": read_context.prompt_context_enabled,
        "workflow_registration_enabled": (
            read_context.workflow_registration_enabled
        ),
        "public_schema_enabled": read_context.public_schema_enabled,
        "metadata": dict(read_context.metadata),
    }


def build_twf_skill_projection_status_summary(
    *,
    projections: Sequence[TwfSkillCapabilityProjectionCandidate | Mapping[str, Any]],
    slot_references: Sequence[
        TwfWorkflowSkillSlotReferenceCandidate | Mapping[str, Any]
    ],
    source: str = "cognition_operation_flows._skills.capability_projection",
) -> TwfSkillProjectionStatusSummaryCandidate:
    """Build a sanitized aggregate status summary for Skill projection refs."""

    projection_statuses = tuple(_projection_status_dict(projection) for projection in projections)
    slot_statuses = tuple(_slot_status_dict(slot) for slot in slot_references)
    active_slots = tuple(
        slot
        for slot in slot_statuses
        if slot.get("slot_status_candidate") == "active_candidate"
    )
    blocked_slots = tuple(
        slot
        for slot in slot_statuses
        if slot.get("slot_status_candidate") != "active_candidate"
    )
    runtime_enabled = any(
        _status_flag_enabled(status, "runtime_enabled")
        for status in (*projection_statuses, *slot_statuses)
    )
    skill_file_loading_enabled = any(
        _status_flag_enabled(status, "skill_file_loading_enabled")
        for status in (*projection_statuses, *slot_statuses)
    )
    resources_loading_enabled = any(
        _status_flag_enabled(status, "resources_loading_enabled")
        for status in (*projection_statuses, *slot_statuses)
    )
    scripts_execution_enabled = any(
        _status_flag_enabled(status, "scripts_execution_enabled")
        for status in (*projection_statuses, *slot_statuses)
    )
    tool_exposure_enabled = any(
        _status_flag_enabled(status, "tool_exposure_enabled")
        for status in (*projection_statuses, *slot_statuses)
    )
    agent_runtime_enabled = any(
        _status_flag_enabled(status, "agent_runtime_enabled")
        for status in (*projection_statuses, *slot_statuses)
    )
    prompt_context_enabled = any(
        _status_flag_enabled(status, "prompt_context_enabled")
        for status in (*projection_statuses, *slot_statuses)
    )
    public_schema_enabled = any(
        _status_flag_enabled(status, "public_schema_enabled")
        for status in (*projection_statuses, *slot_statuses)
    )
    has_runtime_escalation = any(
        (
            runtime_enabled,
            skill_file_loading_enabled,
            resources_loading_enabled,
            scripts_execution_enabled,
            tool_exposure_enabled,
            agent_runtime_enabled,
            prompt_context_enabled,
            public_schema_enabled,
        )
    )
    status = "not_configured"
    if projection_statuses or slot_statuses:
        status = (
            "blocked"
            if blocked_slots or has_runtime_escalation
            else "candidate_only_referenceable"
        )
    return TwfSkillProjectionStatusSummaryCandidate(
        status=status,
        source=source,
        projection_count=len(projection_statuses),
        workflow_slot_reference_count=len(slot_statuses),
        active_slot_reference_count=len(active_slots),
        blocked_slot_reference_count=len(blocked_slots),
        projection_refs=tuple(
            _ordered_unique(
                str(status.get("projection_id") or "")
                for status in projection_statuses
            )
        ),
        workflow_slot_refs=tuple(
            _ordered_unique(str(status.get("slot_ref") or "") for status in slot_statuses)
        ),
        workflow_names=tuple(
            _ordered_unique(
                str(status.get("workflow_name") or "")
                for status in slot_statuses
            )
        ),
        skill_ids=tuple(
            _ordered_unique(
                str(status.get("skill_id") or "")
                for status in (*projection_statuses, *slot_statuses)
            )
        ),
        capability_ids=tuple(
            _ordered_unique(
                str(status.get("capability_id") or "")
                for status in (*projection_statuses, *slot_statuses)
            )
        ),
        reference_modes=tuple(
            _ordered_unique(
                str(status.get("reference_mode") or "")
                for status in slot_statuses
            )
        ),
        allowed_use_summary={
            str(status["workflow_name"]): tuple(status.get("allowed_use") or ())
            for status in slot_statuses
            if status.get("workflow_name")
        },
        forbidden_use_summary={
            str(status["workflow_name"]): tuple(status.get("forbidden_use") or ())
            for status in slot_statuses
            if status.get("workflow_name")
        },
        evidence_refs=tuple(
            _ordered_unique(
                evidence_ref
                for status in projection_statuses
                for evidence_ref in status.get("evidence_refs", ())
            )
        ),
        runtime_enabled=runtime_enabled,
        skill_file_loading_enabled=skill_file_loading_enabled,
        resources_loading_enabled=resources_loading_enabled,
        scripts_execution_enabled=scripts_execution_enabled,
        tool_exposure_enabled=tool_exposure_enabled,
        agent_runtime_enabled=agent_runtime_enabled,
        prompt_context_enabled=prompt_context_enabled,
        public_schema_enabled=public_schema_enabled,
        metadata={
            "candidate_only": True,
            "reference_only": True,
            "does_not_load_skill_file": True,
            "does_not_read_resources": True,
            "does_not_execute_scripts": True,
            "does_not_create_skill_toolset": True,
            "does_not_call_adk_skill_registry": True,
            "does_not_expose_tool": True,
            "does_not_call_agent_runtime": True,
            "does_not_register_workflow": True,
            "does_not_inject_prompt_context": True,
            "sanitized_summary": True,
        },
    )


def build_default_twf_skill_capability_projection_status_summary() -> (
    TwfSkillProjectionStatusSummaryCandidate
):
    """Build the default four-workflow candidate-only Skill projection summary."""

    registry = build_default_twf_registry()
    records = _default_skill_capability_records()
    source = build_twf_project_skill_registry_source(
        registry_name="project_skills",
        source_ref="config://skills/project-skills",
        declared_skill_ids=tuple(record.skill_id for record in records),
    )
    gate = validate_twf_project_skill_registry_loading_gate(
        source=source,
        records=records,
        tool_loading_gate=_default_reference_tool_gate(),
    )
    descriptors = {
        descriptor.workflow_name: descriptor for descriptor in registry.descriptors
    }
    projections: list[TwfSkillCapabilityProjectionCandidate] = []
    slots: list[TwfWorkflowSkillSlotReferenceCandidate] = []
    for sample in _default_skill_capability_samples():
        review = review_twf_skill_capability_for_projection(
            gate=gate,
            records=records,
            skill_id=sample["skill_id"],
            capability_id=sample["capability_id"],
            workflow_registry=registry,
            evidence_refs=(sample["evidence_ref"],),
        )
        projection = build_twf_skill_capability_projection(
            review,
            display_summary=sample["display_summary"],
            use_boundary=sample["use_boundary"],
        )
        projections.append(projection)
        slots.append(
            build_twf_workflow_skill_slot_reference(
                descriptor=descriptors[sample["workflow_name"]],
                projection=projection,
                allowed_use=sample["allowed_use"],
            )
        )
    return build_twf_skill_projection_status_summary(
        projections=projections,
        slot_references=slots,
    )


def twf_skill_projection_status_summary_status_dict(
    summary: TwfSkillProjectionStatusSummaryCandidate,
) -> dict[str, Any]:
    """Return a JSON-ready Skills projection status summary."""

    return {
        "status": summary.status,
        "source": summary.source,
        "projection_count": summary.projection_count,
        "workflow_slot_reference_count": summary.workflow_slot_reference_count,
        "active_slot_reference_count": summary.active_slot_reference_count,
        "blocked_slot_reference_count": summary.blocked_slot_reference_count,
        "projection_refs": list(summary.projection_refs),
        "workflow_slot_refs": list(summary.workflow_slot_refs),
        "workflow_names": list(summary.workflow_names),
        "skill_ids": list(summary.skill_ids),
        "capability_ids": list(summary.capability_ids),
        "reference_modes": list(summary.reference_modes),
        "allowed_use_summary": {
            key: list(values)
            for key, values in summary.allowed_use_summary.items()
        },
        "forbidden_use_summary": {
            key: list(values)
            for key, values in summary.forbidden_use_summary.items()
        },
        "evidence_refs": list(summary.evidence_refs),
        "runtime_enabled": summary.runtime_enabled,
        "skill_file_loading_enabled": summary.skill_file_loading_enabled,
        "resources_loading_enabled": summary.resources_loading_enabled,
        "scripts_execution_enabled": summary.scripts_execution_enabled,
        "tool_exposure_enabled": summary.tool_exposure_enabled,
        "agent_runtime_enabled": summary.agent_runtime_enabled,
        "prompt_context_enabled": summary.prompt_context_enabled,
        "public_schema_enabled": summary.public_schema_enabled,
        "metadata": dict(summary.metadata),
    }


def _find_record(
    records: Sequence[TwfProjectSkillRegistryRecordCandidate],
    skill_id: str,
) -> TwfProjectSkillRegistryRecordCandidate | None:
    return next((record for record in records if record.skill_id == skill_id), None)


def _find_validation(
    validations: Sequence[TwfProjectSkillLoadingValidationCandidate],
    skill_id: str,
) -> TwfProjectSkillLoadingValidationCandidate | None:
    return next(
        (validation for validation in validations if validation.skill_id == skill_id),
        None,
    )


def _find_capability(
    record: TwfProjectSkillRegistryRecordCandidate | None,
    capability_id: str,
) -> TwfProjectSkillCapabilityDeclarationCandidate | None:
    if record is None:
        return None
    return next(
        (
            capability
            for capability in record.capability_declarations
            if capability.capability_id == capability_id
        ),
        None,
    )


def _empty_capability(
    *,
    skill_id: str,
    capability_id: str,
) -> TwfProjectSkillCapabilityDeclarationCandidate:
    return TwfProjectSkillCapabilityDeclarationCandidate(
        skill_id=skill_id,
        capability_id=capability_id,
        capability_name="",
        description="",
        risk_level="unknown",
        script_policy="blocked",
        resource_policy="blocked",
    )


def _workflow_name_from_ref(ref: str) -> str:
    if "://" in ref:
        return ref.rsplit("://", 1)[-1].strip()
    return ref.strip()


def _collect_flag_blocks(
    prefix: str,
    metadata: Mapping[str, Any],
    blocking: list[str],
) -> None:
    for raw_key in _forbidden_raw_keys(metadata):
        blocking.append(f"{prefix}:raw_skill_material_forbidden:{raw_key}")
    for secret_key in _raw_secret_keys(metadata):
        blocking.append(f"{prefix}:raw_secret_material_forbidden:{secret_key}")


def _forbidden_raw_keys(metadata: Mapping[str, Any]) -> tuple[str, ...]:
    keys: list[str] = []
    for key, value in metadata.items():
        key_text = str(key)
        if key_text in TWF_SKILL_FORBIDDEN_RAW_KEYS:
            keys.append(key_text)
        if isinstance(value, Mapping):
            keys.extend(_forbidden_raw_keys(value))
    return tuple(_ordered_unique(keys))


def _raw_secret_keys(metadata: Mapping[str, Any]) -> tuple[str, ...]:
    keys: list[str] = []
    for key, value in metadata.items():
        key_text = str(key).lower()
        is_negative_boundary_flag = key_text.startswith("does_not_include_")
        if (
            value
            and not is_negative_boundary_flag
            and any(marker in key_text for marker in TWF_SKILL_SECRET_KEY_MARKERS)
        ):
            keys.append(str(key))
        if isinstance(value, Mapping):
            keys.extend(_raw_secret_keys(value))
    return tuple(_ordered_unique(keys))


def _default_projection_summary(
    *,
    capability_name: str,
    task_kinds: Sequence[str],
) -> str:
    task_text = ", ".join(task_kinds) if task_kinds else "declared workflow tasks"
    return f"{capability_name or 'Skill capability'} supports {task_text}."


def _projection_status_dict(
    projection: TwfSkillCapabilityProjectionCandidate | Mapping[str, Any],
) -> dict[str, Any]:
    if isinstance(projection, TwfSkillCapabilityProjectionCandidate):
        return twf_skill_capability_projection_status_dict(projection)
    return dict(projection)


def _slot_status_dict(
    slot: TwfWorkflowSkillSlotReferenceCandidate | Mapping[str, Any],
) -> dict[str, Any]:
    if isinstance(slot, TwfWorkflowSkillSlotReferenceCandidate):
        return twf_workflow_skill_slot_reference_status_dict(slot)
    return dict(slot)


def _unavailable_read_context(
    *,
    descriptor: TwfDescriptorCandidate,
    allowed_use_stage: str,
    blocking_reasons: Sequence[str],
) -> TwfSkillProjectionReadContextCandidate:
    return TwfSkillProjectionReadContextCandidate(
        status="unavailable",
        workflow_name=descriptor.workflow_name,
        workflow_version=descriptor.workflow_version,
        task_kind=descriptor.task_kind,
        allowed_use_stage=allowed_use_stage,
        blocking_reasons=tuple(_ordered_unique(blocking_reasons)),
        metadata={
            "candidate_only": True,
            "reference_only": True,
            "sanitized_summary": True,
            "read_context_only": True,
            "does_not_load_skill_file": True,
            "does_not_read_resources": True,
            "does_not_execute_scripts": True,
            "does_not_create_skill_toolset": True,
            "does_not_call_adk_skill_registry": True,
            "does_not_expose_tool": True,
            "does_not_call_agent_runtime": True,
            "does_not_register_workflow": True,
            "does_not_inject_prompt_context": True,
            "does_not_dispatch_runtime": True,
        },
    )


def _tool_gate_status_dict(
    tool_loading_gate: TwfToolLoadingGateCandidate | Mapping[str, Any] | None,
) -> dict[str, Any]:
    if tool_loading_gate is None:
        return {"status": "unavailable", "allowed_tool_names": ()}
    if isinstance(tool_loading_gate, TwfToolLoadingGateCandidate):
        return {
            "status": tool_loading_gate.status,
            "risk_gate_status": tool_loading_gate.risk_gate_status,
            "allowed_tool_names": tuple(tool_loading_gate.allowed_tool_names),
            "blocked_tool_names": tuple(tool_loading_gate.blocked_tool_names),
            "blocking_reasons": tuple(tool_loading_gate.blocking_reasons),
            "warnings": tuple(tool_loading_gate.warnings),
        }
    return dict(tool_loading_gate)


def _collect_status_flag_blocks(
    prefix: str,
    status: Mapping[str, Any],
    blocking: list[str],
) -> None:
    for key in (
        "runtime_enabled",
        "skill_file_loading_enabled",
        "resources_loading_enabled",
        "scripts_execution_enabled",
        "tool_exposure_enabled",
        "agent_runtime_enabled",
        "prompt_context_enabled",
        "workflow_registration_enabled",
        "public_schema_enabled",
    ):
        if status.get(key):
            blocking.append(f"{prefix}_{key}")


def _collect_status_raw_material_blocks(
    prefix: str,
    status: Mapping[str, Any],
    blocking: list[str],
) -> None:
    for raw_key in _forbidden_raw_keys(status):
        blocking.append(f"{prefix}:raw_skill_material_forbidden:{raw_key}")
    for secret_key in _raw_secret_keys(status):
        blocking.append(f"{prefix}:raw_secret_material_forbidden:{secret_key}")


def _status_flag_enabled(status: Mapping[str, Any], key: str) -> bool:
    return bool(status.get(key))


def _default_skill_capability_samples() -> tuple[dict[str, Any], ...]:
    return (
        {
            "skill_id": "skill.plan.design",
            "capability_id": "capability.plan.design",
            "workflow_name": TWF_PLAN_WORKFLOW_NAME,
            "task_kind": "plan_design",
            "display_summary": "方案设计能力投影，用于稳定输出结构、约束和预算项。",
            "use_boundary": "仅作为 plan workflow 的结构化规划提示，不加载 Skill。",
            "allowed_use": ("workflow_planning_hint",),
            "evidence_ref": "evidence://skills/plan-design",
        },
        {
            "skill_id": "skill.reference.review",
            "capability_id": "capability.reference.review",
            "workflow_name": TWF_REFERENCE_REVIEW_WORKFLOW_NAME,
            "task_kind": "reference_review",
            "display_summary": "资料审查能力投影，用于稳定输出符合性、风险和建议。",
            "use_boundary": "仅作为 reference review workflow 的审查结构提示，不执行工具。",
            "allowed_use": ("workflow_planning_hint", "status_evidence_summary"),
            "evidence_ref": "evidence://skills/reference-review",
        },
        {
            "skill_id": "skill.config.profile.explain",
            "capability_id": "capability.config.profile.explain",
            "workflow_name": TWF_CONFIG_PROFILE_EXPLAIN_WORKFLOW_NAME,
            "task_kind": "config_profile_explain",
            "display_summary": "配置解释能力投影，用于稳定解释配置优先级和覆盖关系。",
            "use_boundary": "仅作为 config profile explain workflow 的解释结构提示。",
            "allowed_use": ("status_evidence_summary",),
            "evidence_ref": "evidence://skills/config-profile-explain",
        },
        {
            "skill_id": "skill.evidence.audit",
            "capability_id": "capability.evidence.audit",
            "workflow_name": TWF_RUN_WORKSPACE_EVIDENCE_AUDIT_WORKFLOW_NAME,
            "task_kind": "run_workspace_evidence_audit",
            "display_summary": "证据审计能力投影，用于稳定审查 run workspace 证据完整性。",
            "use_boundary": "仅作为 evidence audit workflow 的证据摘要提示。",
            "allowed_use": ("status_evidence_summary",),
            "evidence_ref": "evidence://skills/evidence-audit",
        },
    )


def _default_skill_capability_records() -> tuple[
    TwfProjectSkillRegistryRecordCandidate, ...
]:
    records: list[TwfProjectSkillRegistryRecordCandidate] = []
    for sample in _default_skill_capability_samples():
        required_tools = (
            (REFERENCE_READER_TOOL_NAME,)
            if sample["workflow_name"] == TWF_REFERENCE_REVIEW_WORKFLOW_NAME
            else ()
        )
        capability = TwfProjectSkillCapabilityDeclarationCandidate(
            skill_id=sample["skill_id"],
            capability_id=sample["capability_id"],
            capability_name=str(sample["display_summary"]).split("，", 1)[0],
            description=sample["display_summary"],
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
            TwfProjectSkillRegistryRecordCandidate(
                skill_id=sample["skill_id"],
                metadata_view=SkillMetadataViewCandidate(
                    l1_metadata=SkillL1MetadataCandidate(
                        skill_id=sample["skill_id"],
                        name=sample["skill_id"],
                        description=sample["display_summary"],
                        capabilities=(sample["capability_id"],),
                        source_ref="candidate://runtime-container/default-skills",
                        skill_file_ref=f"skills/{sample['skill_id']}/SKILL.md",
                    )
                ),
                capability_declarations=(capability,),
                source_ref=f"skill-candidate://{sample['skill_id']}",
            )
        )
    return tuple(records)


def _default_reference_tool_gate() -> TwfToolLoadingGateCandidate:
    return TwfToolLoadingGateCandidate(
        status="passed",
        risk_gate_status="passed",
        validations=(),
        allowed_tool_names=(REFERENCE_READER_TOOL_NAME,),
        blocked_tool_names=(),
        blocking_reasons=(),
        warnings=(),
        metadata={
            "candidate_only": True,
            "does_not_execute_tools": True,
        },
    )


def _normalize_risk(risk_level: str) -> str:
    normalized = (risk_level or "unknown").strip().lower()
    return normalized if normalized in TWF_SKILL_RISK_LEVEL_ORDER else "unknown"


def _risk_at_or_below(risk_level: str, max_risk_level: str) -> bool:
    return TWF_SKILL_RISK_LEVEL_ORDER.get(
        _normalize_risk(risk_level),
        TWF_SKILL_RISK_LEVEL_ORDER["unknown"],
    ) <= TWF_SKILL_RISK_LEVEL_ORDER.get(
        _normalize_risk(max_risk_level),
        TWF_SKILL_RISK_LEVEL_ORDER["medium"],
    )


def _normalize_policy(
    policy: str,
    allowed_values: frozenset[str],
    *,
    default: str,
) -> str:
    normalized = (policy or default).strip().lower()
    return normalized if normalized in allowed_values else default


def _ordered_unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


# Canonical read-context/status-summary implementation lives in task_workflows.
from cognition_operation_flows._skills.projection_context import (  # noqa: E402
    TwfSkillProjectionStatusSummaryCandidate,
    TwfSkillProjectionReadContextCandidate,
    build_twf_skill_projection_status_summary,
    build_twf_skill_projection_read_context,
    twf_skill_projection_status_summary_status_dict,
    twf_skill_projection_read_context_status_dict,
)
