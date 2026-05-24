"""Contract boundary evaluation helpers."""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from cognition_evaluation.models import (
    EvaluationBaseModel,
    EvaluationFinding,
    EvaluationProfileRef,
    EvaluationResult,
)


CONTRACT_BOUNDARY_EVALUATION_PROFILE = EvaluationProfileRef(
    ref="evaluation-profile://contract-boundary/v1",
    name="contract_boundary_evaluation",
    version="v1",
)


class ContractBoundarySnapshot(EvaluationBaseModel):
    """Safe contract snapshot for deterministic boundary evaluation."""

    contract_ref: str = Field(..., min_length=1)
    contract_home: str | None = None
    expected_contract_home: str | None = None
    implementation_helper_contracts: list[str] = Field(default_factory=list)
    fields_without_task_api_mapping: list[str] = Field(default_factory=list)
    fields_without_workflow_runtime_mapping: list[str] = Field(default_factory=list)
    config_facts_without_context_contract: list[str] = Field(default_factory=list)
    public_schema_without_stable_consumers: list[str] = Field(default_factory=list)
    internal_candidates_publicized: list[str] = Field(default_factory=list)
    legacy_aliases_without_exit: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_safe_snapshot(self) -> "ContractBoundarySnapshot":
        _reject_forbidden_values(self.model_dump())
        return self


def evaluate_contract_boundary(
    snapshot: ContractBoundarySnapshot,
    *,
    evaluation_id: str = "evaluation://contract-boundary",
) -> EvaluationResult:
    """Evaluate contract boundaries without deciding governance outcomes."""

    findings: list[EvaluationFinding] = []
    if (
        snapshot.contract_home
        and snapshot.expected_contract_home
        and snapshot.contract_home != snapshot.expected_contract_home
    ):
        findings.append(
            _finding(
                "contract_home_boundary",
                "failed",
                "error",
                "Contract is placed outside its expected contract home.",
                {
                    "contract_home": snapshot.contract_home,
                    "expected_contract_home": snapshot.expected_contract_home,
                },
            )
        )
    if snapshot.implementation_helper_contracts:
        findings.append(
            _finding(
                "anti_bypass_contract_review",
                "failed",
                "blocking",
                "Stable contract objects are implemented in helper or entry packages.",
                {"contracts": snapshot.implementation_helper_contracts},
            )
        )
    missing_task = set(snapshot.fields_without_task_api_mapping)
    missing_workflow = set(snapshot.fields_without_workflow_runtime_mapping)
    missing_both = sorted(missing_task & missing_workflow)
    missing_any = sorted((missing_task | missing_workflow) - set(missing_both))
    if missing_both:
        findings.append(
            _finding(
                "task_workflow_semantic_mapping",
                "failed",
                "error",
                "Product-level fields lack both Task API and Workflow Runtime semantic mapping.",
                {"fields": missing_both},
            )
        )
    if missing_any:
        findings.append(
            _finding(
                "task_workflow_semantic_mapping",
                "warning",
                "warning",
                "Product-level fields have incomplete Task API or Workflow Runtime mapping.",
                {"fields": missing_any},
            )
        )
    if snapshot.config_facts_without_context_contract:
        findings.append(
            _finding(
                "config_context_ownership",
                "failed",
                "error",
                "Stable configuration facts bypass config_contexts contract review.",
                {"config_facts": snapshot.config_facts_without_context_contract},
            )
        )
    if snapshot.public_schema_without_stable_consumers:
        findings.append(
            _finding(
                "public_schema_threshold",
                "warning",
                "warning",
                "Public schema candidates do not yet have stable consumers.",
                {"schemas": snapshot.public_schema_without_stable_consumers},
            )
        )
    if snapshot.internal_candidates_publicized:
        findings.append(
            _finding(
                "public_schema_threshold",
                "failed",
                "error",
                "Internal candidates are being publicized as stable contracts.",
                {"candidates": snapshot.internal_candidates_publicized},
            )
        )
    if snapshot.legacy_aliases_without_exit:
        findings.append(
            _finding(
                "exit_mechanism_boundary",
                "warning",
                "warning",
                "Legacy aliases or compatibility shims do not have an exit mechanism.",
                {"aliases": snapshot.legacy_aliases_without_exit},
            )
        )

    status = _result_status(findings)
    return EvaluationResult(
        evaluation_id=evaluation_id,
        status=status,
        findings=findings,
        profile_ref=CONTRACT_BOUNDARY_EVALUATION_PROFILE,
        summary=(
            "Contract boundary evaluation passed."
            if status == "passed"
            else "Contract boundary evaluation produced findings."
        ),
        metadata={
            "contract_ref": snapshot.contract_ref,
            "evaluation_scope": "contract_boundary",
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
            raise ValueError("contract boundary snapshot contains forbidden marker.")
    elif isinstance(value, dict):
        for item in value.values():
            _reject_forbidden_values(item)
    elif isinstance(value, list | tuple | set):
        for item in value:
            _reject_forbidden_values(item)
