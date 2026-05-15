"""Pre-execution loading validation and risk gate for CLI tools."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from runtime_container.cli_reference_reader import REFERENCE_READER_TOOL_NAME
from runtime_container.cli_tool_exposure_profile import (
    CliToolExposureResolutionCandidate,
    CliToolsetExposurePolicyCandidate,
)
from runtime_container.cli_toolset_admission import (
    CliToolCandidate,
    CliToolsetInventoryCandidate,
)


CLI_TOOL_LOADING_VALIDATION_STAGES = (
    "tool_exposure_resolution",
    "selected_tool_inventory",
    "loadability_validation",
    "dependency_validation",
    "risk_gate",
    "input_schema_validation",
    "output_boundary_validation",
)
RISK_LEVEL_ORDER = {
    "none": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "unknown": 4,
    "blocked": 5,
}
LOCAL_REFERENCE_READER_INPUT_SCHEMA_REF = (
    "schema://runtime-container/tools/local-reference-reader/read-request"
)
LOCAL_REFERENCE_READER_OUTPUT_BOUNDARY_REF = (
    "boundary://runtime-container/tools/local-reference-reader/sanitized-excerpt"
)


@dataclass(frozen=True)
class CliToolLoadingValidationCandidate:
    """Validation result for one selected CLI tool before execution."""

    tool_name: str
    toolset_name: str
    toolset_kind: str
    selected: bool
    exposed: bool
    status: str
    loadable: bool
    dependencies_satisfied: bool
    risk_level: str
    risk_gate_status: str
    input_schema_satisfied: bool
    output_boundary_declared: bool
    confirmation_required: bool
    confirmation_satisfied: bool
    allowed_for_execution: bool
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CliToolLoadingGateCandidate:
    """Aggregate loading-validation gate for a resolved CLI tool profile."""

    status: str
    risk_gate_status: str
    validations: tuple[CliToolLoadingValidationCandidate, ...]
    allowed_tool_names: tuple[str, ...]
    blocked_tool_names: tuple[str, ...]
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


def validate_cli_tool_loading_gate(
    resolution: CliToolExposureResolutionCandidate,
    *,
    operator_approved: bool = False,
    approval_ref: str | None = None,
) -> CliToolLoadingGateCandidate:
    """Validate selected tools before they are eligible for CLI execution."""

    policies = {
        policy.toolset_name: policy for policy in resolution.profile.toolsets
    }
    validations: list[CliToolLoadingValidationCandidate] = []
    blocking: list[str] = []
    warnings: list[str] = list(resolution.warnings)
    if resolution.status != "resolved":
        blocking.append("tool_exposure_resolution_blocked")
    for inventory in resolution.inventories:
        policy = policies.get(inventory.admission.toolset_name)
        for tool in inventory.tools:
            if not tool.selected:
                continue
            validation = validate_cli_tool_loading(
                inventory=inventory,
                tool=tool,
                policy=policy,
                operator_approved=operator_approved,
                approval_ref=approval_ref,
            )
            validations.append(validation)
            warnings.extend(validation.warnings)
            blocking.extend(
                f"{validation.tool_name}:{reason}"
                for reason in validation.blocking_reasons
            )
    allowed_tool_names = tuple(
        validation.tool_name
        for validation in validations
        if validation.allowed_for_execution
    )
    blocked_tool_names = tuple(
        validation.tool_name
        for validation in validations
        if not validation.allowed_for_execution
    )
    status = "passed" if not blocking else "blocked"
    return CliToolLoadingGateCandidate(
        status=status,
        risk_gate_status=status,
        validations=tuple(validations),
        allowed_tool_names=tuple(_ordered_unique(allowed_tool_names)),
        blocked_tool_names=tuple(_ordered_unique(blocked_tool_names)),
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "stages": list(CLI_TOOL_LOADING_VALIDATION_STAGES),
            "does_not_execute_tools": True,
            "does_not_call_model": True,
            "operator_approved": operator_approved,
            "approval_ref_present": bool(approval_ref),
            "validation_count": len(validations),
        },
    )


def validate_cli_tool_loading(
    *,
    inventory: CliToolsetInventoryCandidate,
    tool: CliToolCandidate,
    policy: CliToolsetExposurePolicyCandidate | None = None,
    operator_approved: bool = False,
    approval_ref: str | None = None,
) -> CliToolLoadingValidationCandidate:
    """Validate one selected tool before it can be used by CLI workflows."""

    operation = tool.operation_facts
    review = tool.risk_review
    blocking: list[str] = []
    warnings: list[str] = list(review.warnings)
    if not inventory.admission.admitted:
        blocking.append("toolset_not_admitted")
    if not tool.exposed:
        blocking.append("tool_not_exposed")
    if not review.allowed_for_readonly:
        blocking.append("tool_not_allowed_for_readonly")
    policy_max_risk = policy.max_risk_level if policy else "low"
    if not _risk_at_or_below(review.risk_level, policy_max_risk):
        blocking.append("tool_risk_exceeds_policy")
    dependencies_satisfied = _dependencies_satisfied(inventory, tool)
    if not dependencies_satisfied:
        blocking.append("tool_dependencies_not_satisfied")
    input_schema_ref = _input_schema_ref(tool)
    input_schema_satisfied = bool(input_schema_ref)
    if not input_schema_satisfied:
        blocking.append("tool_input_schema_missing")
    output_boundary_ref = _output_boundary_ref(tool)
    output_boundary_declared = bool(output_boundary_ref)
    if not output_boundary_declared:
        blocking.append("tool_output_boundary_missing")
    confirmation_satisfied = (
        not review.confirmation_required
        or (operator_approved and bool(approval_ref))
    )
    if review.confirmation_required and not confirmation_satisfied:
        blocking.append("operator_confirmation_required")
    risk_gate_status = "passed" if not blocking else "blocked"
    return CliToolLoadingValidationCandidate(
        tool_name=tool.tool_name,
        toolset_name=operation.toolset_name,
        toolset_kind=operation.toolset_kind,
        selected=tool.selected,
        exposed=tool.exposed,
        status="passed" if not blocking else "blocked",
        loadable=tool.exposed and inventory.admission.admitted,
        dependencies_satisfied=dependencies_satisfied,
        risk_level=review.risk_level,
        risk_gate_status=risk_gate_status,
        input_schema_satisfied=input_schema_satisfied,
        output_boundary_declared=output_boundary_declared,
        confirmation_required=review.confirmation_required,
        confirmation_satisfied=confirmation_satisfied,
        allowed_for_execution=not blocking,
        blocking_reasons=tuple(_ordered_unique(blocking)),
        warnings=tuple(_ordered_unique(warnings)),
        metadata={
            "policy_max_risk_level": policy_max_risk,
            "input_schema_ref": input_schema_ref,
            "output_boundary_ref": output_boundary_ref,
            "does_not_execute_tool": True,
        },
    )


def cli_tool_loading_gate_status_dict(
    gate: CliToolLoadingGateCandidate,
) -> dict[str, Any]:
    """Return a sanitized JSON-ready gate summary."""

    return {
        "status": gate.status,
        "risk_gate_status": gate.risk_gate_status,
        "allowed_tool_names": list(gate.allowed_tool_names),
        "blocked_tool_names": list(gate.blocked_tool_names),
        "blocking_reasons": list(gate.blocking_reasons),
        "warnings": list(gate.warnings),
        "validations": [
            cli_tool_loading_validation_status_dict(validation)
            for validation in gate.validations
        ],
        "metadata": dict(gate.metadata),
    }


def cli_tool_loading_validation_status_dict(
    validation: CliToolLoadingValidationCandidate,
) -> dict[str, Any]:
    """Return a sanitized JSON-ready validation summary."""

    return {
        "tool_name": validation.tool_name,
        "toolset_name": validation.toolset_name,
        "toolset_kind": validation.toolset_kind,
        "selected": validation.selected,
        "exposed": validation.exposed,
        "status": validation.status,
        "loadable": validation.loadable,
        "dependencies_satisfied": validation.dependencies_satisfied,
        "risk_level": validation.risk_level,
        "risk_gate_status": validation.risk_gate_status,
        "input_schema_satisfied": validation.input_schema_satisfied,
        "output_boundary_declared": validation.output_boundary_declared,
        "confirmation_required": validation.confirmation_required,
        "confirmation_satisfied": validation.confirmation_satisfied,
        "allowed_for_execution": validation.allowed_for_execution,
        "blocking_reasons": list(validation.blocking_reasons),
        "warnings": list(validation.warnings),
    }


def _dependencies_satisfied(
    inventory: CliToolsetInventoryCandidate,
    tool: CliToolCandidate,
) -> bool:
    if tool.tool_name == REFERENCE_READER_TOOL_NAME:
        return True
    if not inventory.admission.source_ref:
        return False
    if tool.operation_facts.requires_auth:
        return bool(
            inventory.admission.credential_boundary.get(
                "execution_credential_ref_present"
            )
        )
    return True


def _input_schema_ref(tool: CliToolCandidate) -> str | None:
    if tool.tool_name == REFERENCE_READER_TOOL_NAME:
        return LOCAL_REFERENCE_READER_INPUT_SCHEMA_REF
    return _metadata_ref(tool.operation_facts.metadata, "input_schema_ref")


def _output_boundary_ref(tool: CliToolCandidate) -> str | None:
    if tool.tool_name == REFERENCE_READER_TOOL_NAME:
        return LOCAL_REFERENCE_READER_OUTPUT_BOUNDARY_REF
    return _metadata_ref(tool.operation_facts.metadata, "output_boundary_ref")


def _metadata_ref(metadata: Mapping[str, Any], key: str) -> str | None:
    value = metadata.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _risk_at_or_below(risk_level: str, max_risk_level: str) -> bool:
    return RISK_LEVEL_ORDER.get(risk_level, RISK_LEVEL_ORDER["unknown"]) <= (
        RISK_LEVEL_ORDER.get(max_risk_level, RISK_LEVEL_ORDER["low"])
    )


def _ordered_unique(values: tuple[str, ...] | list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique
