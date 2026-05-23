"""Read-only Skill projection context helpers for task workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


TWF_SKILL_CAPABILITY_ALLOWED_SLOT_USES = frozenset(
    {"workflow_planning_hint", "status_evidence_summary"}
)
TWF_SKILL_CAPABILITY_FORBIDDEN_SLOT_USES = (
    "skill_runtime_loading",
    "script_execution",
    "tool_exposure",
    "agent_runtime",
    "public_schema",
)
TWF_SKILL_CAPABILITY_REFERENCEABLE_SLOT_STATUSES = frozenset(
    {"candidate_only_frozen", "reference_only_candidate"}
)
TWF_SKILL_PROJECTION_FORBIDDEN_RAW_KEYS = (
    "raw_skill_instructions",
    "skill_instructions",
    "raw_instructions",
    "raw_resource_content",
    "resource_content",
    "raw_script_body",
    "script_body",
)
TWF_SKILL_PROJECTION_SECRET_KEY_MARKERS = (
    "access_token",
    "api_key",
    "credential",
    "password",
    "private_key",
    "secret",
    "service_account_json",
    "token",
)


@dataclass(frozen=True)
class TwfSkillProjectionStatusSummaryCandidate:
    """Sanitized status summary for candidate-only Skill projections."""

    status: str
    source: str
    projection_count: int
    workflow_slot_reference_count: int
    active_slot_reference_count: int
    blocked_slot_reference_count: int
    projection_refs: tuple[str, ...] = ()
    workflow_slot_refs: tuple[str, ...] = ()
    workflow_names: tuple[str, ...] = ()
    skill_ids: tuple[str, ...] = ()
    capability_ids: tuple[str, ...] = ()
    reference_modes: tuple[str, ...] = ()
    allowed_use_summary: dict[str, tuple[str, ...]] = field(default_factory=dict)
    forbidden_use_summary: dict[str, tuple[str, ...]] = field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()
    runtime_enabled: bool = False
    skill_file_loading_enabled: bool = False
    resources_loading_enabled: bool = False
    scripts_execution_enabled: bool = False
    tool_exposure_enabled: bool = False
    agent_runtime_enabled: bool = False
    prompt_context_enabled: bool = False
    public_schema_enabled: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfSkillProjectionReadContextCandidate:
    """Candidate-only read context for workflow-side Skill projection hints."""

    status: str
    workflow_name: str
    workflow_version: str
    task_kind: str
    allowed_use_stage: str
    projection_refs: tuple[str, ...] = ()
    skill_ids: tuple[str, ...] = ()
    capability_ids: tuple[str, ...] = ()
    capability_names: tuple[str, ...] = ()
    display_summaries: tuple[str, ...] = ()
    use_boundaries: tuple[str, ...] = ()
    slot_refs: tuple[str, ...] = ()
    reference_modes: tuple[str, ...] = ()
    allowed_use: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    risk_levels: tuple[str, ...] = ()
    sensitivities: tuple[str, ...] = ()
    confidences: tuple[str, ...] = ()
    tool_dependency_summary: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    candidate_only: bool = True
    reference_only: bool = True
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


def build_twf_skill_projection_read_context(
    *,
    descriptor: Any | Mapping[str, Any],
    projections: Sequence[Mapping[str, Any] | Any],
    slot_references: Sequence[Mapping[str, Any] | Any],
    allowed_use_stage: str,
    tool_loading_gate: Mapping[str, Any] | Any | None = None,
) -> TwfSkillProjectionReadContextCandidate:
    """Build sanitized read-only Skill projection context for one workflow."""

    projection_statuses = {
        str(status.get("projection_id") or ""): status
        for status in (_projection_status_dict(projection) for projection in projections)
        if status.get("projection_id")
    }
    slot_statuses = tuple(_slot_status_dict(slot) for slot in slot_references)
    workflow_name = _descriptor_value(descriptor, "workflow_name")
    workflow_version = _descriptor_value(descriptor, "workflow_version")
    task_kind = _descriptor_value(descriptor, "task_kind")
    skills_slot_status = _descriptor_value(descriptor, "skills_slot_status")
    relevant_slots = tuple(
        status for status in slot_statuses if status.get("workflow_name") == workflow_name
    )
    blocking: list[str] = []
    warnings: list[str] = []
    if allowed_use_stage not in TWF_SKILL_CAPABILITY_ALLOWED_SLOT_USES:
        blocking.append("allowed_use_stage_unsupported")
    if skills_slot_status not in TWF_SKILL_CAPABILITY_REFERENCEABLE_SLOT_STATUSES:
        blocking.append("workflow_skills_slot_not_reference_only")
    if not projection_statuses:
        return _unavailable_read_context(
            workflow_name=workflow_name,
            workflow_version=workflow_version,
            task_kind=task_kind,
            allowed_use_stage=allowed_use_stage,
            blocking_reasons=("projection_missing",),
        )
    if not relevant_slots:
        return _unavailable_read_context(
            workflow_name=workflow_name,
            workflow_version=workflow_version,
            task_kind=task_kind,
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
        if workflow_name not in tuple(projection.get("allowed_workflow_names") or ()):
            blocking.append("workflow_not_allowed_for_projection")
        if workflow_name in tuple(projection.get("denied_workflow_names") or ()):
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
        _status_flag_enabled(status, "runtime_enabled") for status in combined_statuses
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
        workflow_name=workflow_name,
        workflow_version=workflow_version,
        task_kind=task_kind,
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
        "workflow_registration_enabled": read_context.workflow_registration_enabled,
        "public_schema_enabled": read_context.public_schema_enabled,
        "metadata": dict(read_context.metadata),
    }


def build_twf_skill_projection_status_summary(
    *,
    projections: Sequence[Mapping[str, Any] | Any],
    slot_references: Sequence[Mapping[str, Any] | Any],
    source: str = "cognition_operation_flows._skills.projection_context",
) -> TwfSkillProjectionStatusSummaryCandidate:
    """Build a sanitized aggregate status summary for Skill projection refs."""

    projection_statuses = tuple(
        _projection_status_dict(projection) for projection in projections
    )
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
                str(status.get("workflow_name") or "") for status in slot_statuses
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
                str(status.get("reference_mode") or "") for status in slot_statuses
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


def _projection_status_dict(projection: Mapping[str, Any] | Any) -> dict[str, Any]:
    if isinstance(projection, Mapping):
        return dict(projection)
    return {
        "projection_id": getattr(projection, "projection_id", None),
        "source_review_id": getattr(projection, "source_review_id", None),
        "registry_name": getattr(projection, "registry_name", None),
        "skill_id": getattr(projection, "skill_id", None),
        "capability_id": getattr(projection, "capability_id", None),
        "capability_name": getattr(projection, "capability_name", None),
        "projection_status_candidate": getattr(
            projection, "projection_status_candidate", None
        ),
        "display_summary": getattr(projection, "display_summary", None),
        "use_boundary": getattr(projection, "use_boundary", None),
        "domains": tuple(getattr(projection, "domains", ())),
        "task_kinds": tuple(getattr(projection, "task_kinds", ())),
        "input_boundary_ref": getattr(projection, "input_boundary_ref", None),
        "output_boundary_ref": getattr(projection, "output_boundary_ref", None),
        "risk_level": getattr(projection, "risk_level", None),
        "script_policy": getattr(projection, "script_policy", None),
        "resource_policy": getattr(projection, "resource_policy", None),
        "tool_dependency_summary": tuple(
            getattr(projection, "tool_dependency_summary", ())
        ),
        "workflow_ref_summary": tuple(getattr(projection, "workflow_ref_summary", ())),
        "allowed_workflow_names": tuple(
            getattr(projection, "allowed_workflow_names", ())
        ),
        "denied_workflow_names": tuple(getattr(projection, "denied_workflow_names", ())),
        "evidence_refs": tuple(getattr(projection, "evidence_refs", ())),
        "approval_ref": getattr(projection, "approval_ref", None),
        "audit_ref": getattr(projection, "audit_ref", None),
        "visibility": getattr(projection, "visibility", None),
        "sensitivity": getattr(projection, "sensitivity", None),
        "confidence": getattr(projection, "confidence", None),
        "candidate_only": getattr(projection, "candidate_only", True),
        "runtime_enabled": getattr(projection, "runtime_enabled", False),
        "skill_file_loading_enabled": getattr(
            projection, "skill_file_loading_enabled", False
        ),
        "resources_loading_enabled": getattr(
            projection, "resources_loading_enabled", False
        ),
        "scripts_execution_enabled": getattr(
            projection, "scripts_execution_enabled", False
        ),
        "tool_exposure_enabled": getattr(projection, "tool_exposure_enabled", False),
        "agent_runtime_enabled": getattr(projection, "agent_runtime_enabled", False),
        "prompt_context_enabled": getattr(projection, "prompt_context_enabled", False),
        "workflow_registration_enabled": getattr(
            projection, "workflow_registration_enabled", False
        ),
        "public_schema_enabled": getattr(projection, "public_schema_enabled", False),
        "metadata": dict(getattr(projection, "metadata", {})),
    }


def _slot_status_dict(slot: Mapping[str, Any] | Any) -> dict[str, Any]:
    if isinstance(slot, Mapping):
        return dict(slot)
    return {
        "slot_ref": getattr(slot, "slot_ref", None),
        "workflow_name": getattr(slot, "workflow_name", None),
        "workflow_version": getattr(slot, "workflow_version", None),
        "task_kind": getattr(slot, "task_kind", None),
        "projection_id": getattr(slot, "projection_id", None),
        "skill_id": getattr(slot, "skill_id", None),
        "capability_id": getattr(slot, "capability_id", None),
        "reference_mode": getattr(slot, "reference_mode", None),
        "allowed_use": tuple(getattr(slot, "allowed_use", ())),
        "forbidden_use": tuple(getattr(slot, "forbidden_use", ())),
        "slot_status_candidate": getattr(slot, "slot_status_candidate", None),
        "blocking_reasons": tuple(getattr(slot, "blocking_reasons", ())),
        "warnings": tuple(getattr(slot, "warnings", ())),
        "candidate_only": getattr(slot, "candidate_only", True),
        "runtime_enabled": getattr(slot, "runtime_enabled", False),
        "skill_file_loading_enabled": getattr(slot, "skill_file_loading_enabled", False),
        "resources_loading_enabled": getattr(slot, "resources_loading_enabled", False),
        "scripts_execution_enabled": getattr(slot, "scripts_execution_enabled", False),
        "tool_exposure_enabled": getattr(slot, "tool_exposure_enabled", False),
        "agent_runtime_enabled": getattr(slot, "agent_runtime_enabled", False),
        "prompt_context_enabled": getattr(slot, "prompt_context_enabled", False),
        "public_schema_enabled": getattr(slot, "public_schema_enabled", False),
        "metadata": dict(getattr(slot, "metadata", {})),
    }


def _unavailable_read_context(
    *,
    workflow_name: str,
    workflow_version: str,
    task_kind: str,
    allowed_use_stage: str,
    blocking_reasons: Sequence[str],
) -> TwfSkillProjectionReadContextCandidate:
    return TwfSkillProjectionReadContextCandidate(
        status="unavailable",
        workflow_name=workflow_name,
        workflow_version=workflow_version,
        task_kind=task_kind,
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


def _descriptor_value(descriptor: Any | Mapping[str, Any], key: str) -> str:
    if isinstance(descriptor, Mapping):
        return str(descriptor.get(key) or "")
    return str(getattr(descriptor, key, "") or "")


def _tool_gate_status_dict(tool_loading_gate: Mapping[str, Any] | Any | None) -> dict[str, Any]:
    if tool_loading_gate is None:
        return {"status": "unavailable", "allowed_tool_names": ()}
    if isinstance(tool_loading_gate, Mapping):
        return dict(tool_loading_gate)
    return {
        "status": getattr(tool_loading_gate, "status", None),
        "risk_gate_status": getattr(tool_loading_gate, "risk_gate_status", None),
        "allowed_tool_names": tuple(getattr(tool_loading_gate, "allowed_tool_names", ())),
        "blocked_tool_names": tuple(getattr(tool_loading_gate, "blocked_tool_names", ())),
        "blocking_reasons": tuple(getattr(tool_loading_gate, "blocking_reasons", ())),
        "warnings": tuple(getattr(tool_loading_gate, "warnings", ())),
    }


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


def _forbidden_raw_keys(metadata: Mapping[str, Any]) -> tuple[str, ...]:
    keys: list[str] = []
    for key, value in metadata.items():
        key_text = str(key)
        if key_text in TWF_SKILL_PROJECTION_FORBIDDEN_RAW_KEYS:
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
            and any(marker in key_text for marker in TWF_SKILL_PROJECTION_SECRET_KEY_MARKERS)
        ):
            keys.append(str(key))
        if isinstance(value, Mapping):
            keys.extend(_raw_secret_keys(value))
    return tuple(_ordered_unique(keys))


def _status_flag_enabled(status: Mapping[str, Any], key: str) -> bool:
    return bool(status.get(key))


def _ordered_unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique
