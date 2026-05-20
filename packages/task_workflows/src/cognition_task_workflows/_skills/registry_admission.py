"""Candidate-only project-side Skills registry admission for the task workflow channel."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from config_contexts import SkillMetadataViewCandidate

from cognition_task_workflows._tools.loading_validation import TwfToolLoadingGateCandidate


TWF_SKILL_REGISTRY_LOADING_VALIDATION_STAGES = (
    "registry_source_resolution",
    "skill_metadata_view_validation",
    "candidate_flags_validation",
    "capability_declaration_validation",
    "input_boundary_validation",
    "output_boundary_validation",
    "tools_dependency_validation",
    "resource_boundary_validation",
    "script_policy_validation",
    "risk_level_validation",
    "evidence_projection_validation",
)
TWF_SKILL_REGISTRY_SOURCE_KINDS = frozenset(
    {
        "inline_candidate",
        "config_profile",
        "project_manifest",
        "generated_summary",
        "unknown",
    }
)
TWF_SKILL_RISK_LEVEL_ORDER = {
    "none": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "unknown": 4,
    "blocked": 5,
}
TWF_SKILL_SCRIPT_POLICIES = frozenset(
    {"no_scripts", "reference_only", "review_required", "blocked"}
)
TWF_SKILL_RESOURCE_POLICIES = frozenset(
    {"refs_only", "digest_required", "review_required", "blocked"}
)
TWF_SKILL_FORBIDDEN_RUNTIME_FLAGS = (
    "skill_registry_runtime_requested",
    "skill_toolset_runtime_requested",
    "real_skill_loading_requested",
    "skill_file_loading_requested",
    "skill_directory_read_requested",
    "script_execution_requested",
    "runtime_execution_enabled",
    "policy_execution_enabled",
    "live_call_enabled",
    "raw_adk_object_included",
)
TWF_SKILL_FORBIDDEN_RAW_KEYS = (
    "raw_skill_instructions",
    "skill_instructions",
    "raw_instructions",
    "raw_resource_content",
    "resource_content",
    "raw_script_body",
    "script_body",
)
TWF_SKILL_SECRET_KEY_MARKERS = (
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
class TwfProjectSkillRegistrySourceCandidate:
    """Project-side Skills registry source summary before runtime integration."""

    registry_name: str
    registry_version: str
    source_kind: str
    source_ref: str | None = None
    profile_ref: str | None = None
    declared_skill_ids: tuple[str, ...] = ()
    candidate_only: bool = True
    observation_only: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfProjectSkillCapabilityDeclarationCandidate:
    """Capability declaration for one project-side Skill candidate."""

    skill_id: str
    capability_id: str
    capability_name: str
    description: str
    domains: tuple[str, ...] = ()
    task_kinds: tuple[str, ...] = ()
    allowed_tool_names: tuple[str, ...] = ()
    required_tool_names: tuple[str, ...] = ()
    optional_tool_names: tuple[str, ...] = ()
    agent_role_refs: tuple[str, ...] = ()
    workflow_refs: tuple[str, ...] = ()
    input_boundary_ref: str | None = None
    output_boundary_ref: str | None = None
    risk_level: str = "unknown"
    script_policy: str = "no_scripts"
    resource_policy: str = "refs_only"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfProjectSkillRegistryRecordCandidate:
    """Registry record connecting existing Skill metadata to capabilities."""

    skill_id: str
    metadata_view: SkillMetadataViewCandidate
    capability_declarations: tuple[
        TwfProjectSkillCapabilityDeclarationCandidate, ...
    ] = ()
    source_ref: str | None = None
    declared_status: str = "candidate_declared"
    warnings: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfProjectSkillLoadingValidationCandidate:
    """Validation result for one project-side Skill candidate."""

    skill_id: str
    status: str
    capability_ids: tuple[str, ...]
    loadable: bool
    dependencies_satisfied: bool
    candidate_flags_satisfied: bool
    capability_declarations_satisfied: bool
    input_boundary_declared: bool
    output_boundary_declared: bool
    tools_dependency_gate_status: str
    risk_level: str
    risk_gate_status: str
    allowed_for_candidate_reference: bool
    allowed_for_runtime_loading: bool = False
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfProjectSkillRegistryLoadingGateCandidate:
    """Aggregate gate for project-side Skills registry declarations."""

    registry_name: str
    status: str
    risk_gate_status: str
    source: TwfProjectSkillRegistrySourceCandidate
    validations: tuple[TwfProjectSkillLoadingValidationCandidate, ...]
    validated_skill_ids: tuple[str, ...]
    blocked_skill_ids: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    allowed_for_candidate_reference: bool = False
    allowed_for_runtime_loading: bool = False
    allowed_for_tool_exposure: bool = False
    allowed_for_workflow_registration: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfProjectSkillRegistryEvidenceProjectionCandidate:
    """Sanitized evidence projection for a project-side Skills registry gate."""

    registry_name: str
    skill_count: int
    capability_count: int
    validated_skill_ids: tuple[str, ...]
    blocked_skill_ids: tuple[str, ...]
    risk_levels: dict[str, str]
    tool_dependency_summary: dict[str, tuple[str, ...]]
    agent_role_ref_summary: dict[str, tuple[str, ...]]
    workflow_ref_summary: dict[str, tuple[str, ...]]
    warnings: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


def build_twf_project_skill_registry_source(
    *,
    registry_name: str,
    registry_version: str = "v0.7.0-candidate",
    source_kind: str = "inline_candidate",
    source_ref: str | None = None,
    profile_ref: str | None = None,
    declared_skill_ids: Sequence[str] = (),
    metadata: Mapping[str, Any] | None = None,
) -> TwfProjectSkillRegistrySourceCandidate:
    """Build a project-side registry source without reading Skill files."""

    normalized_kind = _normalize_source_kind(source_kind)
    return TwfProjectSkillRegistrySourceCandidate(
        registry_name=registry_name,
        registry_version=registry_version,
        source_kind=normalized_kind,
        source_ref=source_ref,
        profile_ref=profile_ref,
        declared_skill_ids=tuple(_ordered_unique(declared_skill_ids)),
        candidate_only=True,
        observation_only=True,
        metadata={
            **dict(metadata or {}),
            "candidate_only": True,
            "observation_only": True,
            "does_not_load_skill_file": True,
            "does_not_read_skill_directory": True,
            "does_not_create_skill_toolset": True,
            "does_not_call_skill_registry": True,
            "does_not_execute_script": True,
            "does_not_register_workflow": True,
            "does_not_expose_tool": True,
        },
    )


def validate_twf_project_skill_registry_loading_gate(
    *,
    source: TwfProjectSkillRegistrySourceCandidate,
    records: Sequence[TwfProjectSkillRegistryRecordCandidate],
    tool_loading_gate: TwfToolLoadingGateCandidate | None = None,
    max_risk_level: str = "medium",
) -> TwfProjectSkillRegistryLoadingGateCandidate:
    """Validate project-side Skills declarations without runtime loading."""

    blocking: list[str] = []
    warnings: list[str] = []
    if not source.registry_name.strip():
        blocking.append("registry_name_missing")
    if not source.registry_version.strip():
        warnings.append("registry_version_missing")
    if source.source_kind not in TWF_SKILL_REGISTRY_SOURCE_KINDS:
        blocking.append("registry_source_kind_unsupported")
    if not source.source_ref:
        blocking.append("registry_source_ref_missing")
    if not source.candidate_only or not source.observation_only:
        blocking.append("registry_source_candidate_flags_escalated")
    blocking.extend(_metadata_runtime_blocking_reasons(source.metadata))
    raw_keys = _forbidden_raw_keys(source.metadata)
    secret_keys = _raw_secret_keys(source.metadata)
    if raw_keys:
        blocking.append("registry_source_raw_skill_material_forbidden")
    if secret_keys:
        blocking.append("registry_source_raw_secret_material_forbidden")

    registry_records = tuple(records)
    if not registry_records:
        blocking.append("skill_registry_empty")
    declared_ids = set(source.declared_skill_ids)
    validations: list[TwfProjectSkillLoadingValidationCandidate] = []
    for record in registry_records:
        if declared_ids and record.skill_id not in declared_ids:
            blocking.append(f"skill_not_declared_in_source:{record.skill_id}")
        validation = validate_twf_project_skill_loading(
            record=record,
            tool_loading_gate=tool_loading_gate,
            max_risk_level=max_risk_level,
        )
        validations.append(validation)
        warnings.extend(validation.warnings)
        blocking.extend(
            f"{validation.skill_id}:{reason}"
            for reason in validation.blocking_reasons
        )

    validated_skill_ids = tuple(
        validation.skill_id
        for validation in validations
        if validation.allowed_for_candidate_reference
    )
    blocked_skill_ids = tuple(
        validation.skill_id
        for validation in validations
        if not validation.allowed_for_candidate_reference
    )
    status = "passed" if not blocking else "blocked"
    return TwfProjectSkillRegistryLoadingGateCandidate(
        registry_name=source.registry_name,
        status=status,
        risk_gate_status=status,
        source=source,
        validations=tuple(validations),
        validated_skill_ids=tuple(_ordered_unique(validated_skill_ids)),
        blocked_skill_ids=tuple(_ordered_unique(blocked_skill_ids)),
        warnings=tuple(_ordered_unique(warnings)),
        blocking_reasons=tuple(_ordered_unique(blocking)),
        allowed_for_candidate_reference=not blocking,
        allowed_for_runtime_loading=False,
        allowed_for_tool_exposure=False,
        allowed_for_workflow_registration=False,
        metadata={
            "stages": list(TWF_SKILL_REGISTRY_LOADING_VALIDATION_STAGES),
            "candidate_only": True,
            "observation_only": True,
            "does_not_load_skill_file": True,
            "does_not_read_skill_directory": True,
            "does_not_create_skill_toolset": True,
            "does_not_call_skill_registry": True,
            "does_not_execute_script": True,
            "does_not_register_workflow": True,
            "does_not_expose_tool": True,
            "tool_loading_gate_status": (
                tool_loading_gate.status if tool_loading_gate else "not_declared"
            ),
            "policy_max_risk_level": _normalize_risk(max_risk_level),
            "validation_count": len(validations),
        },
    )


def validate_twf_project_skill_loading(
    *,
    record: TwfProjectSkillRegistryRecordCandidate,
    tool_loading_gate: TwfToolLoadingGateCandidate | None = None,
    max_risk_level: str = "medium",
) -> TwfProjectSkillLoadingValidationCandidate:
    """Validate one Skill registry record without loading the Skill itself."""

    blocking: list[str] = list(record.blocking_reasons)
    warnings: list[str] = list(record.warnings)
    metadata_view = record.metadata_view
    l1_metadata = metadata_view.l1_metadata
    flags = metadata_view.candidate_flags
    if not record.skill_id.strip():
        blocking.append("skill_id_missing")
    if record.skill_id != l1_metadata.skill_id:
        blocking.append("skill_metadata_skill_id_mismatch")
    if not l1_metadata.description.strip():
        blocking.append("skill_description_missing")
    if not record.source_ref:
        warnings.append("source_ref_not_stable")
    if not _candidate_flags_satisfied(metadata_view):
        blocking.append("candidate_flags_escalated")
    blocking.extend(_metadata_runtime_blocking_reasons(record.metadata))
    raw_keys = _forbidden_raw_keys(record.metadata)
    secret_keys = _raw_secret_keys(record.metadata)
    if raw_keys:
        blocking.append("raw_skill_material_forbidden")
    if secret_keys:
        blocking.append("raw_secret_material_forbidden")

    capabilities = tuple(record.capability_declarations)
    if not capabilities:
        blocking.append("capability_declaration_missing")
    capability_ids: list[str] = []
    declared_risk_levels: list[str] = []
    input_boundary_declared = bool(capabilities)
    output_boundary_declared = bool(capabilities)
    tool_dependencies: list[str] = []
    for capability in capabilities:
        capability_key = capability.capability_id or "<missing>"
        capability_ids.append(capability.capability_id)
        declared_risk_levels.append(_normalize_risk(capability.risk_level))
        _validate_capability(
            capability=capability,
            record_skill_id=record.skill_id,
            tool_loading_gate=tool_loading_gate,
            max_risk_level=max_risk_level,
            blocking=blocking,
            warnings=warnings,
        )
        input_boundary_declared = (
            input_boundary_declared and bool(capability.input_boundary_ref)
        )
        output_boundary_declared = (
            output_boundary_declared and bool(capability.output_boundary_ref)
        )
        tool_dependencies.extend(_capability_tool_dependencies(capability))
        if not capability.capability_id.strip():
            blocking.append(f"capability:{capability_key}:capability_id_missing")

    normalized_risk = _max_risk_level(declared_risk_levels)
    dependencies_satisfied = _tool_dependencies_satisfied(
        tool_dependencies=tool_dependencies,
        tool_loading_gate=tool_loading_gate,
    )
    if tool_dependencies and not dependencies_satisfied:
        blocking.append("tool_dependency_bypasses_tools_gate")
    status = "passed" if not blocking else "blocked"
    return TwfProjectSkillLoadingValidationCandidate(
        skill_id=record.skill_id,
        status=status,
        capability_ids=tuple(_ordered_unique(capability_ids)),
        loadable=bool(record.source_ref) and not blocking,
        dependencies_satisfied=dependencies_satisfied,
        candidate_flags_satisfied=_candidate_flags_satisfied(metadata_view),
        capability_declarations_satisfied=bool(capabilities) and not blocking,
        input_boundary_declared=input_boundary_declared,
        output_boundary_declared=output_boundary_declared,
        tools_dependency_gate_status=(
            tool_loading_gate.status if tool_loading_gate else "not_declared"
        ),
        risk_level=normalized_risk,
        risk_gate_status=status,
        allowed_for_candidate_reference=not blocking,
        allowed_for_runtime_loading=False,
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "stages": list(TWF_SKILL_REGISTRY_LOADING_VALIDATION_STAGES),
            "candidate_only": True,
            "observation_only": True,
            "does_not_load_skill_file": True,
            "does_not_read_skill_directory": True,
            "does_not_execute_script": True,
            "does_not_create_skill_toolset": True,
            "does_not_call_skill_registry": True,
            "tool_dependency_names": list(_ordered_unique(tool_dependencies)),
            "tool_loading_gate_status": (
                tool_loading_gate.status if tool_loading_gate else "not_declared"
            ),
            "policy_max_risk_level": _normalize_risk(max_risk_level),
            "forbidden_raw_key_count": len(raw_keys),
            "raw_secret_key_count": len(secret_keys),
        },
    )


def build_twf_project_skill_registry_evidence_projection(
    gate: TwfProjectSkillRegistryLoadingGateCandidate,
    *,
    records: Sequence[TwfProjectSkillRegistryRecordCandidate],
) -> TwfProjectSkillRegistryEvidenceProjectionCandidate:
    """Build a sanitized evidence projection for a Skills registry gate."""

    record_by_skill_id = {record.skill_id: record for record in records}
    risk_levels = {
        validation.skill_id: validation.risk_level for validation in gate.validations
    }
    tool_dependency_summary: dict[str, tuple[str, ...]] = {}
    agent_role_ref_summary: dict[str, tuple[str, ...]] = {}
    workflow_ref_summary: dict[str, tuple[str, ...]] = {}
    capability_count = 0
    for validation in gate.validations:
        record = record_by_skill_id.get(validation.skill_id)
        if record is None:
            continue
        capability_count += len(record.capability_declarations)
        tool_dependency_summary[validation.skill_id] = tuple(
            _ordered_unique(
                tool_name
                for capability in record.capability_declarations
                for tool_name in _capability_tool_dependencies(capability)
            )
        )
        agent_role_ref_summary[validation.skill_id] = tuple(
            _ordered_unique(
                role_ref
                for capability in record.capability_declarations
                for role_ref in capability.agent_role_refs
            )
        )
        workflow_ref_summary[validation.skill_id] = tuple(
            _ordered_unique(
                workflow_ref
                for capability in record.capability_declarations
                for workflow_ref in capability.workflow_refs
            )
        )
    return TwfProjectSkillRegistryEvidenceProjectionCandidate(
        registry_name=gate.registry_name,
        skill_count=len(gate.validations),
        capability_count=capability_count,
        validated_skill_ids=gate.validated_skill_ids,
        blocked_skill_ids=gate.blocked_skill_ids,
        risk_levels=risk_levels,
        tool_dependency_summary=tool_dependency_summary,
        agent_role_ref_summary=agent_role_ref_summary,
        workflow_ref_summary=workflow_ref_summary,
        warnings=gate.warnings,
        blocking_reasons=gate.blocking_reasons,
        metadata={
            "candidate_only": True,
            "sanitized_projection": True,
            "does_not_include_skill_file_body": True,
            "does_not_include_raw_instructions": True,
            "does_not_include_raw_resource_content": True,
            "does_not_include_raw_script_body": True,
            "does_not_include_secret": True,
            "does_not_include_raw_adk_object": True,
            "does_not_include_model_response": True,
            "does_not_include_external_call_result": True,
        },
    )


def twf_project_skill_registry_source_status_dict(
    source: TwfProjectSkillRegistrySourceCandidate,
) -> dict[str, Any]:
    """Return a sanitized JSON-ready registry source summary."""

    return {
        "registry_name": source.registry_name,
        "registry_version": source.registry_version,
        "source_kind": source.source_kind,
        "source_ref": source.source_ref,
        "profile_ref": source.profile_ref,
        "declared_skill_ids": list(source.declared_skill_ids),
        "candidate_only": source.candidate_only,
        "observation_only": source.observation_only,
        "metadata": dict(source.metadata),
    }


def twf_project_skill_capability_declaration_status_dict(
    capability: TwfProjectSkillCapabilityDeclarationCandidate,
) -> dict[str, Any]:
    """Return a sanitized JSON-ready capability declaration summary."""

    return {
        "skill_id": capability.skill_id,
        "capability_id": capability.capability_id,
        "capability_name": capability.capability_name,
        "description": capability.description,
        "domains": list(capability.domains),
        "task_kinds": list(capability.task_kinds),
        "allowed_tool_names": list(capability.allowed_tool_names),
        "required_tool_names": list(capability.required_tool_names),
        "optional_tool_names": list(capability.optional_tool_names),
        "agent_role_refs": list(capability.agent_role_refs),
        "workflow_refs": list(capability.workflow_refs),
        "input_boundary_ref": capability.input_boundary_ref,
        "output_boundary_ref": capability.output_boundary_ref,
        "risk_level": _normalize_risk(capability.risk_level),
        "script_policy": _normalize_policy(
            capability.script_policy,
            TWF_SKILL_SCRIPT_POLICIES,
            default="blocked",
        ),
        "resource_policy": _normalize_policy(
            capability.resource_policy,
            TWF_SKILL_RESOURCE_POLICIES,
            default="blocked",
        ),
        "metadata": dict(capability.metadata),
    }


def twf_project_skill_loading_validation_status_dict(
    validation: TwfProjectSkillLoadingValidationCandidate,
) -> dict[str, Any]:
    """Return a sanitized JSON-ready loading validation summary."""

    return {
        "skill_id": validation.skill_id,
        "status": validation.status,
        "capability_ids": list(validation.capability_ids),
        "loadable": validation.loadable,
        "dependencies_satisfied": validation.dependencies_satisfied,
        "candidate_flags_satisfied": validation.candidate_flags_satisfied,
        "capability_declarations_satisfied": (
            validation.capability_declarations_satisfied
        ),
        "input_boundary_declared": validation.input_boundary_declared,
        "output_boundary_declared": validation.output_boundary_declared,
        "tools_dependency_gate_status": validation.tools_dependency_gate_status,
        "risk_level": validation.risk_level,
        "risk_gate_status": validation.risk_gate_status,
        "allowed_for_candidate_reference": validation.allowed_for_candidate_reference,
        "allowed_for_runtime_loading": validation.allowed_for_runtime_loading,
        "blocking_reasons": list(validation.blocking_reasons),
        "warnings": list(validation.warnings),
        "metadata": dict(validation.metadata),
    }


def twf_project_skill_registry_loading_gate_status_dict(
    gate: TwfProjectSkillRegistryLoadingGateCandidate,
) -> dict[str, Any]:
    """Return a sanitized JSON-ready registry loading gate summary."""

    return {
        "registry_name": gate.registry_name,
        "status": gate.status,
        "risk_gate_status": gate.risk_gate_status,
        "source": twf_project_skill_registry_source_status_dict(gate.source),
        "validations": [
            twf_project_skill_loading_validation_status_dict(validation)
            for validation in gate.validations
        ],
        "validated_skill_ids": list(gate.validated_skill_ids),
        "blocked_skill_ids": list(gate.blocked_skill_ids),
        "warnings": list(gate.warnings),
        "blocking_reasons": list(gate.blocking_reasons),
        "allowed_for_candidate_reference": gate.allowed_for_candidate_reference,
        "allowed_for_runtime_loading": gate.allowed_for_runtime_loading,
        "allowed_for_tool_exposure": gate.allowed_for_tool_exposure,
        "allowed_for_workflow_registration": (
            gate.allowed_for_workflow_registration
        ),
        "metadata": dict(gate.metadata),
    }


def twf_project_skill_registry_evidence_projection_status_dict(
    projection: TwfProjectSkillRegistryEvidenceProjectionCandidate,
) -> dict[str, Any]:
    """Return a sanitized JSON-ready Skills registry evidence projection."""

    return {
        "registry_name": projection.registry_name,
        "skill_count": projection.skill_count,
        "capability_count": projection.capability_count,
        "validated_skill_ids": list(projection.validated_skill_ids),
        "blocked_skill_ids": list(projection.blocked_skill_ids),
        "risk_levels": dict(projection.risk_levels),
        "tool_dependency_summary": {
            skill_id: list(tool_names)
            for skill_id, tool_names in projection.tool_dependency_summary.items()
        },
        "agent_role_ref_summary": {
            skill_id: list(role_refs)
            for skill_id, role_refs in projection.agent_role_ref_summary.items()
        },
        "workflow_ref_summary": {
            skill_id: list(workflow_refs)
            for skill_id, workflow_refs in projection.workflow_ref_summary.items()
        },
        "warnings": list(projection.warnings),
        "blocking_reasons": list(projection.blocking_reasons),
        "metadata": dict(projection.metadata),
    }


def _validate_capability(
    *,
    capability: TwfProjectSkillCapabilityDeclarationCandidate,
    record_skill_id: str,
    tool_loading_gate: TwfToolLoadingGateCandidate | None,
    max_risk_level: str,
    blocking: list[str],
    warnings: list[str],
) -> None:
    capability_key = capability.capability_id or "<missing>"
    prefix = f"capability:{capability_key}:"
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
    if capability.skill_id != record_skill_id:
        blocking.append(f"{prefix}skill_id_mismatch")
    if not capability.capability_name.strip():
        blocking.append(f"{prefix}capability_name_missing")
    if not capability.description.strip():
        blocking.append(f"{prefix}capability_description_missing")
    if not capability.task_kinds:
        blocking.append(f"{prefix}task_kind_missing")
    if not capability.input_boundary_ref:
        blocking.append(f"{prefix}input_boundary_missing")
    if not capability.output_boundary_ref:
        blocking.append(f"{prefix}output_boundary_missing")
    if normalized_risk == "unknown":
        blocking.append(f"{prefix}risk_level_missing")
    if normalized_risk == "blocked":
        blocking.append(f"{prefix}risk_blocked")
    if not _risk_at_or_below(normalized_risk, max_risk_level):
        blocking.append(f"{prefix}risk_exceeds_policy")
    if script_policy == "blocked":
        blocking.append(f"{prefix}script_policy_blocked")
    elif script_policy == "review_required":
        warnings.append(f"{prefix}script_refs_present_review_required")
    if resource_policy == "blocked":
        blocking.append(f"{prefix}resource_policy_blocked")
    elif resource_policy == "review_required":
        warnings.append(f"{prefix}resource_refs_review_required")
    if not capability.required_tool_names:
        warnings.append(f"{prefix}no_required_tools_declared")
    if not capability.agent_role_refs:
        warnings.append(f"{prefix}no_agent_role_refs_declared")
    if not capability.workflow_refs:
        warnings.append(f"{prefix}no_workflow_refs_declared")
    if len(capability.domains) > 5:
        warnings.append(f"{prefix}capability_domain_too_broad")

    tool_dependencies = _capability_tool_dependencies(capability)
    if tool_dependencies:
        if tool_loading_gate is None or tool_loading_gate.status != "passed":
            blocking.append(f"{prefix}tool_dependency_gate_failed")
        else:
            allowed_tools = set(tool_loading_gate.allowed_tool_names)
            for tool_name in tool_dependencies:
                if tool_name not in allowed_tools:
                    blocking.append(f"{prefix}tool_not_allowed:{tool_name}")

    blocking.extend(
        f"{prefix}{reason}"
        for reason in _metadata_runtime_blocking_reasons(capability.metadata)
    )
    if _forbidden_raw_keys(capability.metadata):
        blocking.append(f"{prefix}raw_skill_material_forbidden")
    if _raw_secret_keys(capability.metadata):
        blocking.append(f"{prefix}raw_secret_material_forbidden")


def _candidate_flags_satisfied(metadata_view: SkillMetadataViewCandidate) -> bool:
    flags = metadata_view.candidate_flags
    return (
        metadata_view.config_view_semantics == "candidate_only"
        and metadata_view.formal_decision_enabled is False
        and metadata_view.formal_outcome_enabled is False
        and metadata_view.policy_execution_enabled is False
        and metadata_view.execution_enabled is False
        and metadata_view.runtime_execution_enabled is False
        and flags.candidate_only is True
        and flags.observation_only is True
        and flags.runtime_dependency_enabled is False
        and flags.skill_toolset_runtime_enabled is False
        and flags.skill_registry_runtime_enabled is False
        and flags.github_main_runtime_dependency_enabled is False
        and flags.policy_execution_enabled is False
        and flags.live_call_enabled is False
        and flags.raw_adk_object_included is False
        and flags.script_execution_enabled is False
        and flags.external_resource_loading_enabled is False
    )


def _metadata_runtime_blocking_reasons(metadata: Mapping[str, Any]) -> list[str]:
    blocking: list[str] = []
    for key, value in metadata.items():
        key_text = str(key)
        if key_text in TWF_SKILL_FORBIDDEN_RUNTIME_FLAGS and bool(value):
            blocking.append(key_text)
        if isinstance(value, Mapping):
            blocking.extend(_metadata_runtime_blocking_reasons(value))
    return _ordered_unique(blocking)


def _forbidden_raw_keys(metadata: Mapping[str, Any]) -> tuple[str, ...]:
    keys: list[str] = []
    for key, value in metadata.items():
        key_text = str(key)
        if key_text in TWF_SKILL_FORBIDDEN_RAW_KEYS:
            keys.append(key_text)
        if isinstance(value, Mapping):
            keys.extend(_forbidden_raw_keys(value))
    return tuple(_ordered_unique(keys))


def _raw_secret_keys(raw_config: Mapping[str, Any]) -> tuple[str, ...]:
    keys: list[str] = []
    for key, value in raw_config.items():
        key_text = str(key).lower()
        if any(marker in key_text for marker in TWF_SKILL_SECRET_KEY_MARKERS):
            keys.append(str(key))
        if isinstance(value, Mapping):
            keys.extend(_raw_secret_keys(value))
    return tuple(_ordered_unique(keys))


def _capability_tool_dependencies(
    capability: TwfProjectSkillCapabilityDeclarationCandidate,
) -> list[str]:
    return _ordered_unique(
        (
            *capability.allowed_tool_names,
            *capability.required_tool_names,
            *capability.optional_tool_names,
        )
    )


def _tool_dependencies_satisfied(
    *,
    tool_dependencies: Sequence[str],
    tool_loading_gate: TwfToolLoadingGateCandidate | None,
) -> bool:
    if not tool_dependencies:
        return True
    if tool_loading_gate is None or tool_loading_gate.status != "passed":
        return False
    allowed_tools = set(tool_loading_gate.allowed_tool_names)
    return all(tool_name in allowed_tools for tool_name in tool_dependencies)


def _normalize_source_kind(source_kind: str) -> str:
    normalized = source_kind.strip().lower()
    return normalized if normalized in TWF_SKILL_REGISTRY_SOURCE_KINDS else "unknown"


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


def _max_risk_level(risk_levels: Sequence[str]) -> str:
    if not risk_levels:
        return "unknown"
    return max(
        (_normalize_risk(risk_level) for risk_level in risk_levels),
        key=lambda risk: TWF_SKILL_RISK_LEVEL_ORDER[risk],
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
