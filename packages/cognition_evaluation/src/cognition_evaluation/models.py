"""Product-level evaluation contracts for Cognition System."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


EvaluationStatus = Literal["passed", "failed", "warning", "not_applicable", "unknown"]
EvaluationSeverity = Literal["info", "warning", "error", "blocking"]
EvaluationSubjectKind = Literal[
    "answer",
    "architecture_boundary",
    "configuration_boundary",
    "contract_boundary",
    "evidence_summary_answer",
    "answer_scoped_transformation",
    "model_output",
    "product_experience",
]


class EvaluationBaseModel(BaseModel):
    """Base model for evaluation public contracts."""

    model_config = ConfigDict(extra="forbid")


class EvaluationRef(EvaluationBaseModel):
    """Safe reference used by evaluation contracts."""

    ref: str = Field(..., min_length=1)
    kind: str = Field(..., min_length=1)
    purpose: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationProfileRef(EvaluationBaseModel):
    """Stable profile reference for an evaluation policy."""

    ref: str = Field(..., min_length=1)
    name: str | None = None
    version: str | None = None


class EvaluationCriterion(EvaluationBaseModel):
    """Single criterion requested for an evaluation run."""

    name: str = Field(..., min_length=1)
    threshold: float | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationSubject(EvaluationBaseModel):
    """Subject being evaluated without raw provider payloads."""

    kind: EvaluationSubjectKind
    subject_ref: str | None = None
    answer_preview: str | None = None
    question_preview: str | None = None
    evidence_refs: list[EvaluationRef] = Field(default_factory=list)
    additional_refs: list[EvaluationRef] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_safe_preview(self) -> "EvaluationSubject":
        for value in (self.answer_preview, self.question_preview):
            if value and _contains_forbidden_marker(value):
                raise ValueError("evaluation subject preview contains forbidden marker.")
        return self


class EvaluationInput(EvaluationBaseModel):
    """Input to an evaluation run."""

    evaluation_id: str = Field(..., min_length=1)
    subject: EvaluationSubject
    criteria: list[EvaluationCriterion] = Field(default_factory=list)
    profile_ref: EvaluationProfileRef | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationFinding(EvaluationBaseModel):
    """Single evaluation finding."""

    criterion: str = Field(..., min_length=1)
    status: EvaluationStatus
    severity: EvaluationSeverity = "info"
    message: str = Field(..., min_length=1)
    score: float | None = Field(default=None, ge=0)
    refs: list[EvaluationRef] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationResult(EvaluationBaseModel):
    """Result of a product-level evaluation run."""

    evaluation_id: str = Field(..., min_length=1)
    status: EvaluationStatus
    findings: list[EvaluationFinding] = Field(default_factory=list)
    profile_ref: EvaluationProfileRef | None = None
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_status_and_findings(self) -> "EvaluationResult":
        if self.status == "failed" and not self.findings:
            raise ValueError("failed evaluation results require findings.")
        return self

    @property
    def passed(self) -> bool:
        """Return whether the evaluation passed."""

        return self.status == "passed"


class EvaluationSummary(EvaluationBaseModel):
    """Safe summary for ProductGateway, observability or CLI surfaces."""

    evaluation_ref: str | None = None
    status: EvaluationStatus
    finding_count: int = Field(..., ge=0)
    blocking_finding_count: int = Field(..., ge=0)
    warning_finding_count: int = Field(..., ge=0)
    profile_ref: str | None = None
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdkNativeEvaluationCapability(EvaluationBaseModel):
    """Safe ADK native evaluation capability snapshot."""

    module_available: bool
    agent_evaluator_available: bool
    eval_config_available: bool
    eval_metric_available: bool
    eval_status_values: list[str] = Field(default_factory=list)
    optional_dependency_warnings: list[str] = Field(default_factory=list)
    raw_object_exported: bool = False


def evaluation_summary_from_result(
    result: EvaluationResult,
    *,
    evaluation_ref: str | None = None,
) -> EvaluationSummary:
    """Build a safe summary from an evaluation result."""

    blocking_count = sum(
        1 for finding in result.findings if finding.severity == "blocking"
    )
    warning_count = sum(
        1 for finding in result.findings if finding.severity == "warning"
    )
    return EvaluationSummary(
        evaluation_ref=evaluation_ref,
        status=result.status,
        finding_count=len(result.findings),
        blocking_finding_count=blocking_count,
        warning_finding_count=warning_count,
        profile_ref=result.profile_ref.ref if result.profile_ref else None,
        summary=result.summary,
    )


def _contains_forbidden_marker(value: str) -> bool:
    lowered = value.lower()
    return any(
        marker in lowered
        for marker in (
            "raw_provider_response",
            "system_prompt",
            "api_key",
            "credential",
            "secret",
            "token",
        )
    )
