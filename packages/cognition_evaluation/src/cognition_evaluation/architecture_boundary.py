"""Architecture boundary evaluation helpers."""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from cognition_evaluation.models import (
    EvaluationBaseModel,
    EvaluationFinding,
    EvaluationProfileRef,
    EvaluationResult,
)


ARCHITECTURE_BOUNDARY_EVALUATION_PROFILE = EvaluationProfileRef(
    ref="evaluation-profile://architecture-boundary/v1",
    name="architecture_boundary_evaluation",
    version="v1",
)


class ArchitectureBoundarySnapshot(EvaluationBaseModel):
    """Safe architecture snapshot for deterministic boundary evaluation."""

    component_ref: str = Field(..., min_length=1)
    changed_paths: list[str] = Field(default_factory=list)
    direct_internal_imports: list[str] = Field(default_factory=list)
    cli_internal_candidate_consumption: list[str] = Field(default_factory=list)
    product_gateway_internal_candidate_consumption: list[str] = Field(
        default_factory=list
    )
    governance_decision_outputs: list[str] = Field(default_factory=list)
    governance_owns_evaluation_rules: list[str] = Field(default_factory=list)
    observability_as_linear_step: bool = False
    legacy_terms: list[str] = Field(default_factory=list)
    task_api_semantic_mapping: str | None = None
    workflow_runtime_semantic_mapping: str | None = None
    module_swallowing_risks: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_safe_snapshot(self) -> "ArchitectureBoundarySnapshot":
        _reject_forbidden_values(self.model_dump())
        return self


def evaluate_architecture_boundary(
    snapshot: ArchitectureBoundarySnapshot,
    *,
    evaluation_id: str = "evaluation://architecture-boundary",
) -> EvaluationResult:
    """Evaluate architecture boundaries without making governance decisions."""

    findings: list[EvaluationFinding] = []
    if snapshot.direct_internal_imports:
        findings.append(
            _finding(
                "dependency_direction_boundary",
                "failed",
                "error",
                "Implementation directly imports internal or candidate objects.",
                {"imports": snapshot.direct_internal_imports},
            )
        )
    if snapshot.cli_internal_candidate_consumption:
        findings.append(
            _finding(
                "cli_channel_boundary",
                "failed",
                "blocking",
                "CLI consumes internal candidate objects instead of acting as a channel adapter.",
                {"consumers": snapshot.cli_internal_candidate_consumption},
            )
        )
    if snapshot.product_gateway_internal_candidate_consumption:
        findings.append(
            _finding(
                "product_gateway_boundary",
                "failed",
                "blocking",
                "ProductGateway consumes internal candidate bodies instead of safe summaries.",
                {
                    "consumers": (
                        snapshot.product_gateway_internal_candidate_consumption
                    )
                },
            )
        )
    if snapshot.governance_decision_outputs:
        findings.append(
            _finding(
                "evaluation_governance_boundary",
                "failed",
                "blocking",
                "Evaluation outputs governance decisions such as allow or block.",
                {"outputs": snapshot.governance_decision_outputs},
            )
        )
    if snapshot.governance_owns_evaluation_rules:
        findings.append(
            _finding(
                "governance_evaluation_boundary",
                "failed",
                "error",
                "Governance owns evaluation rules that should remain in evaluation.",
                {"rules": snapshot.governance_owns_evaluation_rules},
            )
        )
    if snapshot.observability_as_linear_step:
        findings.append(
            _finding(
                "runtime_fact_bus_boundary",
                "warning",
                "warning",
                "Observability is modeled as a linear post-step instead of a runtime fact bus.",
            )
        )
    if snapshot.legacy_terms:
        findings.append(
            _finding(
                "legacy_route_pollution",
                "warning",
                "warning",
                "Legacy terms remain in active architecture surfaces.",
                {"terms": snapshot.legacy_terms},
            )
        )
    missing_axis = []
    if not snapshot.task_api_semantic_mapping:
        missing_axis.append("task_api")
    if not snapshot.workflow_runtime_semantic_mapping:
        missing_axis.append("workflow_runtime")
    if missing_axis:
        findings.append(
            _finding(
                "adk_axis_alignment",
                "warning",
                "warning",
                "Implementation lacks explicit ADK2.x axis semantic mapping.",
                {"missing": missing_axis},
            )
        )
    if snapshot.module_swallowing_risks:
        findings.append(
            _finding(
                "module_swallowing_risk",
                "warning",
                "warning",
                "One module appears to absorb another module's responsibility.",
                {"risks": snapshot.module_swallowing_risks},
            )
        )

    status = _result_status(findings)
    return EvaluationResult(
        evaluation_id=evaluation_id,
        status=status,
        findings=findings,
        profile_ref=ARCHITECTURE_BOUNDARY_EVALUATION_PROFILE,
        summary=(
            "Architecture boundary evaluation passed."
            if status == "passed"
            else "Architecture boundary evaluation produced findings."
        ),
        metadata={
            "component_ref": snapshot.component_ref,
            "changed_path_count": len(snapshot.changed_paths),
            "evaluation_scope": "architecture_boundary",
            "governance_decision": False,
        },
    )


def _finding(
    criterion: str,
    status: str,
    severity: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> EvaluationFinding:
    return EvaluationFinding(
        criterion=criterion,
        status=status,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        message=message,
        metadata=metadata or {},
    )


def _result_status(findings: list[EvaluationFinding]) -> str:
    if not findings:
        return "passed"
    if any(finding.status == "failed" for finding in findings):
        return "failed"
    return "warning"


def _reject_forbidden_values(value: Any) -> None:
    if isinstance(value, str):
        lowered = value.lower()
        forbidden_markers = (
            " access_token",
            "api_key",
            "api_token",
            "auth_token",
            "credential",
            "provider_token",
            "raw_html",
            "raw_provider_response",
            "refresh_token",
            "secret",
            "system_prompt",
            "_token.",
            "_token/",
            "_token=",
            "_token:",
            "_token.yaml",
            "/token",
            "token=",
            "token:",
            "traceback",
        )
        if any(marker in lowered for marker in forbidden_markers):
            raise ValueError("architecture boundary snapshot contains forbidden marker.")
    elif isinstance(value, dict):
        for item in value.values():
            _reject_forbidden_values(item)
    elif isinstance(value, list | tuple | set):
        for item in value:
            _reject_forbidden_values(item)
