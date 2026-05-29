"""Evaluation helpers for cognition agent carrier product contracts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cognition_evaluation.models import (
    EvaluationCriterion,
    EvaluationFinding,
    EvaluationInput,
    EvaluationProfileRef,
    EvaluationRef,
    EvaluationResult,
    EvaluationSubject,
)


COGNITION_AGENT_CARRIER_EVALUATION_PROFILE = EvaluationProfileRef(
    ref="evaluation-profile://cognition-agent/carrier-contract-v1",
    name="cognition_agent_carrier_contract",
    version="v1",
)

BOUNDARY_MARKERS = (
    "api_key",
    "authorization:",
    "bearer ",
    "config_context",
    "cookie:",
    "credential",
    "full_answer",
    "google.adk",
    "provider_response",
    "raw evidence",
    "raw prompt",
    "raw_prompt",
    "raw_provider_response",
    "secret",
    "system_prompt",
    "token",
    "traceback",
)


def evaluate_agent_carrier_contract_boundary(
    *,
    agent_carrier_ref: str | None,
    product_intent_summary: str | None,
    candidate_only: bool,
    readonly: bool,
    execution_enabled: bool = False,
    agent_runtime_enabled: bool = False,
    adk_raw_object_included: bool = False,
    evidence_material_refs: list[str] | None = None,
    runtime_binding_refs: list[str] | None = None,
    evaluation_id: str = "evaluation://cognition-agent/carrier-contract",
) -> EvaluationResult:
    """Evaluate whether the carrier remains product-level and candidate-only."""

    findings: list[EvaluationFinding] = []
    if not agent_carrier_ref:
        findings.append(
            _finding(
                "agent_carrier_ref",
                "Agent carrier contract must carry a product-level carrier ref.",
                severity="blocking",
            )
        )
    if not product_intent_summary:
        findings.append(
            _finding(
                "agent_carrier_intent_summary",
                "Agent carrier contract must summarize product intent.",
                severity="blocking",
            )
        )
    else:
        for marker in _found_boundary_markers(product_intent_summary):
            findings.append(
                _finding(
                    "agent_carrier_intent_raw_boundary",
                    "Product intent summary contains forbidden raw-boundary markers.",
                    severity="blocking",
                    metadata={"marker": marker},
                )
            )
    if not candidate_only:
        findings.append(
            _finding(
                "agent_carrier_candidate_only",
                "Agent carrier must remain candidate-only.",
                severity="blocking",
            )
        )
    if not readonly:
        findings.append(
            _finding(
                "agent_carrier_readonly",
                "Agent carrier must remain read-only.",
                severity="blocking",
            )
        )
    forbidden_flags = {
        "execution_enabled": execution_enabled,
        "agent_runtime_enabled": agent_runtime_enabled,
        "adk_raw_object_included": adk_raw_object_included,
    }
    findings.extend(_forbidden_flag_findings("agent_carrier", forbidden_flags))
    if not evidence_material_refs:
        findings.append(
            _finding(
                "agent_carrier_material_refs",
                "Agent carrier should carry material refs for product consumption.",
                severity="warning",
            )
        )
    if runtime_binding_refs is None:
        findings.append(
            _finding(
                "agent_carrier_runtime_binding_refs",
                "Agent carrier should explicitly expose runtime binding refs list.",
                severity="warning",
            )
        )
    return _result(
        evaluation_id=evaluation_id,
        findings=findings,
        passed_summary="Agent carrier contract boundary passed.",
        failed_summary="Agent carrier contract boundary needs attention.",
        evaluation_scope="agent_carrier_contract_boundary",
    )


def evaluate_agent_resume_request_boundary(
    *,
    agent_resume_request_ref: str | None,
    agent_carrier_ref: str | None,
    continuable_evidence_session_ref: str | None,
    requires_user_confirmation: bool,
    requires_external_readonly_authorization: bool,
    auto_resume_answer_enabled: bool = False,
    model_call_requested: bool = False,
    user_product_runtime_path_enabled: bool = False,
    workflow_replay_enabled: bool = False,
    task_runtime_implementation_enabled: bool = False,
    blocking_reasons: list[str] | None = None,
    evaluation_id: str = "evaluation://cognition-agent/resume-request",
) -> EvaluationResult:
    """Evaluate whether a resume request is authorization-only."""

    findings: list[EvaluationFinding] = []
    for criterion, value, message in (
        (
            "agent_resume_request_ref",
            agent_resume_request_ref,
            "Resume request must carry a product-level request ref.",
        ),
        (
            "agent_resume_request_carrier_ref",
            agent_carrier_ref,
            "Resume request must carry its agent carrier ref.",
        ),
        (
            "agent_resume_request_session_ref",
            continuable_evidence_session_ref,
            "Resume request must carry the continuable evidence session ref.",
        ),
    ):
        if not value:
            findings.append(_finding(criterion, message, severity="blocking"))
    if not requires_user_confirmation:
        findings.append(
            _finding(
                "agent_resume_request_user_confirmation",
                "Resume request must require user confirmation.",
                severity="blocking",
            )
        )
    if not requires_external_readonly_authorization:
        findings.append(
            _finding(
                "agent_resume_request_material_authorization",
                "Resume request must require material authorization.",
                severity="blocking",
            )
        )
    forbidden_flags = {
        "auto_resume_answer_enabled": auto_resume_answer_enabled,
        "model_call_requested": model_call_requested,
        "user_product_runtime_path_enabled": user_product_runtime_path_enabled,
        "workflow_replay_enabled": workflow_replay_enabled,
        "task_runtime_implementation_enabled": task_runtime_implementation_enabled,
    }
    findings.extend(_forbidden_flag_findings("agent_resume_request", forbidden_flags))
    for reason in blocking_reasons or []:
        for marker in _found_boundary_markers(reason):
            findings.append(
                _finding(
                    "agent_resume_request_blocking_reason_raw_boundary",
                    "Blocking reason contains forbidden raw-boundary markers.",
                    severity="blocking",
                    metadata={"marker": marker},
                )
            )
    return _result(
        evaluation_id=evaluation_id,
        findings=findings,
        passed_summary="Agent resume request boundary passed.",
        failed_summary="Agent resume request boundary failed.",
        evaluation_scope="agent_resume_request_boundary",
    )


def evaluate_agent_response_projection_boundary(
    *,
    agent_response_ref: str | None,
    agent_carrier_ref: str | None,
    evaluation_summary_ref: str | None = None,
    observability_summary_ref: str | None = None,
    raw_provider_response_included: bool = False,
    full_answer_persistence_claim: bool = False,
    llm_call_performed: bool = False,
    product_gateway_user_visible: bool = False,
    recovery_hints: list[str] | None = None,
    boundary_hints: list[str] | None = None,
    evaluation_id: str = "evaluation://cognition-agent/response-projection",
) -> EvaluationResult:
    """Evaluate whether a response projection is safe and non-executing."""

    findings: list[EvaluationFinding] = []
    if not agent_response_ref:
        findings.append(
            _finding(
                "agent_response_ref",
                "Response projection must carry a product-level response ref.",
                severity="blocking",
            )
        )
    if not agent_carrier_ref:
        findings.append(
            _finding(
                "agent_response_carrier_ref",
                "Response projection must carry its agent carrier ref.",
                severity="blocking",
            )
        )
    if not evaluation_summary_ref:
        findings.append(
            _finding(
                "agent_response_evaluation_summary_ref",
                "Response projection should carry an evaluation summary ref.",
                severity="warning",
            )
        )
    if not observability_summary_ref:
        findings.append(
            _finding(
                "agent_response_observability_summary_ref",
                "Response projection should carry an observability summary ref.",
                severity="warning",
            )
        )
    forbidden_flags = {
        "raw_provider_response_included": raw_provider_response_included,
        "full_answer_persistence_claim": full_answer_persistence_claim,
        "llm_call_performed": llm_call_performed,
        "product_gateway_user_visible": product_gateway_user_visible,
    }
    findings.extend(_forbidden_flag_findings("agent_response_projection", forbidden_flags))
    for scope, values in (
        ("recovery_hints", recovery_hints or []),
        ("boundary_hints", boundary_hints or []),
    ):
        for value in values:
            for marker in _found_boundary_markers(value):
                findings.append(
                    _finding(
                        f"agent_response_{scope}_raw_boundary",
                        "Response projection hint contains forbidden raw-boundary markers.",
                        severity="blocking",
                        metadata={"marker": marker},
                    )
                )
    return _result(
        evaluation_id=evaluation_id,
        findings=findings,
        passed_summary="Agent response projection boundary passed.",
        failed_summary="Agent response projection boundary needs attention.",
        evaluation_scope="agent_response_projection_boundary",
    )


def evaluate_material_consumption_contract_boundary(
    *,
    material_consumption_ref: str | None,
    agent_carrier_ref: str | None,
    source_layer: str,
    evidence_refs: list[str] | None,
    digest_refs: list[str] | None,
    refs_only: bool,
    implementation_object_included: bool = False,
    provider_implementation_included: bool = False,
    raw_evidence_included: bool = False,
    metadata: Mapping[str, Any] | None = None,
    evaluation_id: str = "evaluation://cognition-agent/material-consumption",
) -> EvaluationResult:
    """Evaluate whether material consumption remains refs-only."""

    findings: list[EvaluationFinding] = []
    if not material_consumption_ref:
        findings.append(
            _finding(
                "material_consumption_ref",
                "Material consumption contract must carry a product-level ref.",
                severity="blocking",
            )
        )
    if not agent_carrier_ref:
        findings.append(
            _finding(
                "material_consumption_carrier_ref",
                "Material consumption contract must carry its agent carrier ref.",
                severity="blocking",
            )
        )
    if source_layer != "external_readonly":
        findings.append(
            _finding(
                "material_consumption_source_layer",
                "Material consumption source layer must be external_readonly.",
                severity="blocking",
            )
        )
    if not evidence_refs:
        findings.append(
            _finding(
                "material_consumption_evidence_refs",
                "Material consumption contract must carry evidence refs.",
                severity="blocking",
            )
        )
    if not digest_refs:
        findings.append(
            _finding(
                "material_consumption_digest_refs",
                "Material consumption contract must carry digest refs.",
                severity="blocking",
            )
        )
    if not refs_only:
        findings.append(
            _finding(
                "material_consumption_refs_only",
                "Material consumption contract must stay refs-only.",
                severity="blocking",
            )
        )
    forbidden_flags = {
        "implementation_object_included": implementation_object_included,
        "provider_implementation_included": provider_implementation_included,
        "raw_evidence_included": raw_evidence_included,
    }
    findings.extend(_forbidden_flag_findings("material_consumption", forbidden_flags))
    for key, value in (metadata or {}).items():
        if isinstance(value, str):
            for marker in _found_boundary_markers(value):
                findings.append(
                    _finding(
                        "material_consumption_metadata_raw_boundary",
                        "Material consumption metadata contains forbidden raw-boundary markers.",
                        severity="blocking",
                        metadata={"key": str(key), "marker": marker},
                    )
                )
    return _result(
        evaluation_id=evaluation_id,
        findings=findings,
        passed_summary="Material consumption contract boundary passed.",
        failed_summary="Material consumption contract boundary failed.",
        evaluation_scope="material_consumption_contract_boundary",
    )


def evaluation_input_for_cognition_agent_carrier(
    *,
    evaluation_id: str,
    agent_carrier_ref: str,
    material_refs: list[str] | None = None,
) -> EvaluationInput:
    """Build a minimal safe evaluation input for carrier contracts."""

    return EvaluationInput(
        evaluation_id=evaluation_id,
        subject=EvaluationSubject(
            kind="product_contract",
            subject_ref=agent_carrier_ref,
            evidence_refs=[
                EvaluationRef(ref=ref, kind="product_ref", purpose="agent_material")
                for ref in (material_refs or [])
            ],
        ),
        criteria=[
            EvaluationCriterion(name="agent_carrier_contract_boundary"),
            EvaluationCriterion(name="agent_resume_request_boundary"),
            EvaluationCriterion(name="agent_response_projection_boundary"),
            EvaluationCriterion(name="material_consumption_contract_boundary"),
        ],
        profile_ref=COGNITION_AGENT_CARRIER_EVALUATION_PROFILE,
        metadata={"evaluation_scope": "cognition_agent_carrier"},
    )


def _forbidden_flag_findings(
    scope: str,
    flags: Mapping[str, bool],
) -> list[EvaluationFinding]:
    findings: list[EvaluationFinding] = []
    for flag_name, enabled in flags.items():
        if enabled:
            findings.append(
                _finding(
                    f"{scope}_{flag_name}",
                    f"{flag_name} must remain false.",
                    severity="blocking",
                )
            )
    return findings


def _result(
    *,
    evaluation_id: str,
    findings: list[EvaluationFinding],
    passed_summary: str,
    failed_summary: str,
    evaluation_scope: str,
) -> EvaluationResult:
    return EvaluationResult(
        evaluation_id=evaluation_id,
        status="failed" if any(item.severity == "blocking" for item in findings) else (
            "warning" if findings else "passed"
        ),
        findings=findings,
        profile_ref=COGNITION_AGENT_CARRIER_EVALUATION_PROFILE,
        summary=failed_summary if findings else passed_summary,
        metadata={"evaluation_scope": evaluation_scope},
    )


def _finding(
    criterion: str,
    message: str,
    *,
    severity: str,
    metadata: dict[str, Any] | None = None,
) -> EvaluationFinding:
    return EvaluationFinding(
        criterion=criterion,
        status="failed" if severity == "blocking" else "warning",
        severity=severity,  # type: ignore[arg-type]
        message=message,
        metadata=dict(metadata or {}),
    )


def _found_boundary_markers(value: str) -> list[str]:
    normalized = value.lower()
    return [marker for marker in BOUNDARY_MARKERS if marker in normalized]


__all__ = [
    "COGNITION_AGENT_CARRIER_EVALUATION_PROFILE",
    "evaluate_agent_carrier_contract_boundary",
    "evaluate_agent_response_projection_boundary",
    "evaluate_agent_resume_request_boundary",
    "evaluate_material_consumption_contract_boundary",
    "evaluation_input_for_cognition_agent_carrier",
]
