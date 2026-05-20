"""Behavior guards for CLI-facing product gateway contracts."""

from __future__ import annotations

from typing import Any, Mapping

from behavior_contracts.governance_candidate import CandidateGuardResult
from schemas.product_gateway_cli import (
    PRODUCT_GATEWAY_CLI_TWF_WORKFLOW_NAMES,
    product_gateway_cli_surface_boundary_violations,
)


class ProductGatewayCliSurfaceNoRawPayloadGuard:
    """Reject raw or sensitive fields in CLI-facing product gateway shapes."""

    guard_name = "product_gateway_cli_surface_no_raw_payload_guard"

    def validate(self, value: Mapping[str, Any]) -> CandidateGuardResult:
        violations = [
            item
            for item in product_gateway_cli_surface_boundary_violations(dict(value))
            if "raw or sensitive" in item
        ]
        return _result(violations)


class ProductGatewayCliSurfaceNoRuntimeLeakageGuard:
    """Reject runtime, ADK, composition, task-workflow, and provider objects."""

    guard_name = "product_gateway_cli_surface_no_runtime_leakage_guard"

    def validate(self, value: Mapping[str, Any]) -> CandidateGuardResult:
        violations = [
            item
            for item in product_gateway_cli_surface_boundary_violations(dict(value))
            if "runtime object" in item
        ]
        return _result(violations)


class ProductGatewayCliTaskWorkflowHeaderGuard:
    """Validate stable task workflow names in CLI-facing request contracts."""

    guard_name = "product_gateway_cli_task_workflow_header_guard"

    def validate(self, value: Mapping[str, Any]) -> CandidateGuardResult:
        workflow_name = value.get("workflow_name")
        if workflow_name is None:
            draft_input = value.get("request_draft_input")
            if isinstance(draft_input, Mapping):
                workflow_name = draft_input.get("workflow_name")
        if workflow_name is None:
            return _result([])
        if workflow_name not in PRODUCT_GATEWAY_CLI_TWF_WORKFLOW_NAMES:
            return _result([f"unsupported task workflow name: {workflow_name}."])
        return _result([])


DEFAULT_PRODUCT_GATEWAY_CLI_SURFACE_GUARDS = (
    ProductGatewayCliSurfaceNoRawPayloadGuard(),
    ProductGatewayCliSurfaceNoRuntimeLeakageGuard(),
    ProductGatewayCliTaskWorkflowHeaderGuard(),
)


def validate_product_gateway_cli_surface_guards(
    value: Mapping[str, Any],
    guards: tuple[
        ProductGatewayCliSurfaceNoRawPayloadGuard
        | ProductGatewayCliSurfaceNoRuntimeLeakageGuard
        | ProductGatewayCliTaskWorkflowHeaderGuard,
        ...,
    ] = DEFAULT_PRODUCT_GATEWAY_CLI_SURFACE_GUARDS,
) -> CandidateGuardResult:
    """Run CLI-facing product gateway guards without executing anything."""

    violations: list[str] = []
    for guard in guards:
        result = guard.validate(value)
        violations.extend(f"{guard.guard_name}: {item}" for item in result.violations)
    return _result(violations)


def _result(violations: list[str]) -> CandidateGuardResult:
    return CandidateGuardResult(passed=not violations, violations=tuple(violations))


__all__ = [
    "DEFAULT_PRODUCT_GATEWAY_CLI_SURFACE_GUARDS",
    "ProductGatewayCliSurfaceNoRawPayloadGuard",
    "ProductGatewayCliSurfaceNoRuntimeLeakageGuard",
    "ProductGatewayCliTaskWorkflowHeaderGuard",
    "validate_product_gateway_cli_surface_guards",
]
