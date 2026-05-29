"""Evaluation helpers for continuable evidence session product behavior."""

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


CONTINUABLE_EVIDENCE_SESSION_EVALUATION_PROFILE = EvaluationProfileRef(
    ref="evaluation-profile://continuable-evidence-session/product-boundary-v1",
    name="continuable_evidence_session_product_boundary",
    version="v1",
)

BOUNDARY_MARKERS = (
    "api_key",
    "authorization:",
    "bearer ",
    "config_context",
    "cookie:",
    "credential",
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


def evaluate_resume_summary_boundary(
    *,
    summary_text: str,
    evaluation_id: str = "evaluation://continuable-evidence-session/resume-boundary",
) -> EvaluationResult:
    """Evaluate whether a resume summary stays inside raw-boundary rules."""

    findings = [
        EvaluationFinding(
            criterion="resume_summary_raw_boundary",
            status="failed",
            severity="blocking",
            message="Resume summary contains forbidden raw-boundary markers.",
            metadata={"marker": marker},
        )
        for marker in _found_boundary_markers(summary_text)
    ]
    return _result(
        evaluation_id=evaluation_id,
        findings=findings,
        passed_summary="Resume summary boundary passed.",
        failed_summary="Resume summary boundary failed.",
        evaluation_scope="resume_summary_boundary",
    )


def evaluate_resume_summary_usefulness(
    *,
    summary_text: str,
    source_refs: list[str] | None = None,
    status: str | None = None,
    next_actions: list[str] | None = None,
    evaluation_id: str = "evaluation://continuable-evidence-session/resume-usefulness",
) -> EvaluationResult:
    """Evaluate whether a resume summary is useful enough for a user."""

    findings: list[EvaluationFinding] = []
    if not summary_text.strip():
        findings.append(
            _finding(
                "resume_summary_text",
                "Resume summary must not be blank.",
                severity="blocking",
            )
        )
    if not source_refs:
        findings.append(
            _finding(
                "resume_summary_source_refs",
                "Resume summary must carry source refs.",
                severity="blocking",
            )
        )
    if not status:
        findings.append(
            _finding(
                "resume_summary_status",
                "Resume summary should expose session status.",
                severity="warning",
            )
        )
    if not next_actions:
        findings.append(
            _finding(
                "resume_summary_next_actions",
                "Resume summary should expose user next actions.",
                severity="warning",
            )
        )
    return _result(
        evaluation_id=evaluation_id,
        findings=findings,
        passed_summary="Resume summary usefulness passed.",
        failed_summary="Resume summary usefulness needs attention.",
        evaluation_scope="resume_summary_usefulness",
    )


def evaluate_turn_kind_boundary(
    *,
    turn_kind: str,
    requires_reauthorization: bool,
    answer_state_boundary: str | None = None,
    evaluation_id: str = "evaluation://continuable-evidence-session/turn-kind",
) -> EvaluationResult:
    """Evaluate whether follow-up and answer transformation are distinct."""

    findings: list[EvaluationFinding] = []
    if turn_kind == "evidence_follow_up" and not requires_reauthorization:
        findings.append(
            _finding(
                "evidence_follow_up_authorization",
                "Evidence follow-up must require explicit authorization.",
                severity="blocking",
            )
        )
    if turn_kind == "answer_transformation" and requires_reauthorization:
        findings.append(
            _finding(
                "answer_transformation_authorization",
                "Answer transformation must not be modeled as evidence reload.",
                severity="blocking",
            )
        )
    if turn_kind == "answer_transformation" and answer_state_boundary == "evidence_grounded":
        findings.append(
            _finding(
                "answer_transformation_boundary",
                "Answer transformation must not be labeled evidence-grounded.",
                severity="blocking",
            )
        )
    return _result(
        evaluation_id=evaluation_id,
        findings=findings,
        passed_summary="Turn kind boundary passed.",
        failed_summary="Turn kind boundary failed.",
        evaluation_scope="turn_kind_boundary",
    )


def evaluate_trajectory_summary_quality(
    *,
    user_visible_turns: list[Mapping[str, Any]],
    developer_review_refs: list[str] | None = None,
    blocked_turn_count: int = 0,
    evaluation_id: str = "evaluation://continuable-evidence-session/trajectory",
) -> EvaluationResult:
    """Evaluate whether a trajectory summary carries useful safe review facts."""

    findings: list[EvaluationFinding] = []
    if not user_visible_turns:
        findings.append(
            _finding(
                "trajectory_user_visible_turns",
                "Trajectory summary must include user-visible turns.",
                severity="blocking",
            )
        )
    for index, turn in enumerate(user_visible_turns):
        missing = [
            field_name
            for field_name in ("turn_kind", "turn_status")
            if not turn.get(field_name)
        ]
        if missing:
            findings.append(
                _finding(
                    "trajectory_turn_fields",
                    "Trajectory turn is missing required safe summary fields.",
                    severity="blocking",
                    metadata={"turn_index": index, "missing": missing},
                )
            )
    if blocked_turn_count > 0 and not developer_review_refs:
        findings.append(
            _finding(
                "trajectory_blocked_review_refs",
                "Blocked trajectories should include safe developer review refs.",
                severity="warning",
            )
        )
    return _result(
        evaluation_id=evaluation_id,
        findings=findings,
        passed_summary="Trajectory summary quality passed.",
        failed_summary="Trajectory summary quality needs attention.",
        evaluation_scope="trajectory_summary_quality",
    )


def evaluate_storage_policy_boundary(
    *,
    save_policy: str,
    auto_save_default: bool,
    requires_user_confirmation_on_save: bool,
    requires_user_confirmation_on_resume: bool,
    uses_repo_outputs: bool = False,
    packaged_resource: bool = False,
    config_backed: bool = False,
    runtime_backed: bool = False,
    memory_enabled: bool = False,
    evaluation_id: str = "evaluation://continuable-evidence-session/storage-policy",
) -> EvaluationResult:
    """Evaluate whether storage policy keeps opt-in and product-level boundaries."""

    findings: list[EvaluationFinding] = []
    if save_policy != "explicit_user_opt_in":
        findings.append(
            _finding(
                "storage_policy_save_policy",
                "Storage policy must use explicit user opt-in.",
                severity="blocking",
            )
        )
    if auto_save_default:
        findings.append(
            _finding(
                "storage_policy_auto_save",
                "Storage policy must not enable auto-save by default.",
                severity="blocking",
            )
        )
    if not requires_user_confirmation_on_save:
        findings.append(
            _finding(
                "storage_policy_save_confirmation",
                "Storage policy must require confirmation before save.",
                severity="blocking",
            )
        )
    if not requires_user_confirmation_on_resume:
        findings.append(
            _finding(
                "storage_policy_resume_confirmation",
                "Storage policy must require confirmation before resume.",
                severity="blocking",
            )
        )
    for flag_name, value in (
        ("storage_policy_uses_repo_outputs", uses_repo_outputs),
        ("storage_policy_packaged_resource", packaged_resource),
        ("storage_policy_config_backed", config_backed),
        ("storage_policy_runtime_backed", runtime_backed),
        ("storage_policy_memory_enabled", memory_enabled),
    ):
        if value:
            findings.append(
                _finding(
                    flag_name,
                    "Storage policy must stay product-level and outside runtime/config.",
                    severity="blocking",
                )
            )
    return _result(
        evaluation_id=evaluation_id,
        findings=findings,
        passed_summary="Storage policy boundary passed.",
        failed_summary="Storage policy boundary failed.",
        evaluation_scope="storage_policy_boundary",
    )


def evaluate_session_record_manifest_boundary(
    *,
    logical_file_names: list[str] | None,
    contains_raw_payload: bool,
    io_performed: bool,
    evaluation_id: str = "evaluation://continuable-evidence-session/record-manifest",
) -> EvaluationResult:
    """Evaluate whether a record manifest is a safe logical contract only."""

    findings: list[EvaluationFinding] = []
    if not logical_file_names:
        findings.append(
            _finding(
                "record_manifest_logical_files",
                "Record manifest should declare logical record files.",
                severity="blocking",
            )
        )
    if contains_raw_payload:
        findings.append(
            _finding(
                "record_manifest_raw_payload",
                "Record manifest must not contain raw payload.",
                severity="blocking",
            )
        )
    if io_performed:
        findings.append(
            _finding(
                "record_manifest_io",
                "Record manifest contract must not claim local I/O.",
                severity="blocking",
            )
        )
    return _result(
        evaluation_id=evaluation_id,
        findings=findings,
        passed_summary="Record manifest boundary passed.",
        failed_summary="Record manifest boundary failed.",
        evaluation_scope="session_record_manifest_boundary",
    )


def evaluate_delete_expire_export_policy_boundary(
    *,
    delete_requires_confirmation: bool,
    deleted_session_resumable: bool,
    expired_session_resumable: bool,
    expired_equals_deleted: bool,
    export_package_kind: str,
    export_package_is_evidence_archive: bool,
    import_requires_confirmation: bool,
    import_requires_authorization: bool,
    evaluation_id: str = "evaluation://continuable-evidence-session/delete-expire-export",
) -> EvaluationResult:
    """Evaluate delete, expiration, and export policy user-facing boundaries."""

    findings: list[EvaluationFinding] = []
    if not delete_requires_confirmation:
        findings.append(
            _finding(
                "delete_policy_confirmation",
                "Delete policy must require user confirmation.",
                severity="blocking",
            )
        )
    if deleted_session_resumable:
        findings.append(
            _finding(
                "delete_policy_resumable",
                "Deleted sessions must not be resumable.",
                severity="blocking",
            )
        )
    if expired_session_resumable:
        findings.append(
            _finding(
                "expiration_policy_resumable",
                "Expired sessions must not be directly resumable.",
                severity="blocking",
            )
        )
    if expired_equals_deleted:
        findings.append(
            _finding(
                "expiration_policy_deleted_boundary",
                "Expired sessions must not be modeled as deleted sessions.",
                severity="blocking",
            )
        )
    if export_package_kind != "refs_and_summaries":
        findings.append(
            _finding(
                "export_policy_package_kind",
                "Export package must be refs-and-summaries.",
                severity="blocking",
            )
        )
    if export_package_is_evidence_archive:
        findings.append(
            _finding(
                "export_policy_evidence_archive",
                "Export package must not be an evidence archive.",
                severity="blocking",
            )
        )
    if not import_requires_confirmation:
        findings.append(
            _finding(
                "export_policy_import_confirmation",
                "Imported session resume must require confirmation.",
                severity="blocking",
            )
        )
    if not import_requires_authorization:
        findings.append(
            _finding(
                "export_policy_import_authorization",
                "Imported session resume must require authorization.",
                severity="blocking",
            )
        )
    return _result(
        evaluation_id=evaluation_id,
        findings=findings,
        passed_summary="Delete/expire/export policy boundary passed.",
        failed_summary="Delete/expire/export policy boundary failed.",
        evaluation_scope="delete_expire_export_policy_boundary",
    )


def evaluate_runtime_binding_product_contract(
    *,
    runtime_binding_ref: str | None,
    continuable_evidence_session_ref: str | None = None,
    runtime_binding_status: str = "unavailable",
    runtime_binding_scope: str = "agent_session_event_artifactservice",
    event_review_refs: list[str] | None = None,
    artifact_binding_summary_refs: list[str] | None = None,
    runtime_binding_evaluation_summary_ref: str | None = None,
    raw_runtime_object_included: bool = False,
    raw_event_payload_included: bool = False,
    artifact_body_included: bool = False,
    adk_eval_raw_data_included: bool = False,
    user_product_runtime_path_enabled: bool = False,
    default_local_state_dir_enabled: bool = False,
    auto_resume_answer_enabled: bool = False,
    skills_loaded: bool = False,
    memory_enabled: bool = False,
    tools_mcp_enabled: bool = False,
    callbacks_enabled: bool = False,
    plugins_enabled: bool = False,
    evaluation_id: str = "evaluation://continuable-evidence-session/runtime-binding",
) -> EvaluationResult:
    """Evaluate whether runtime binding remains a safe product-level contract."""

    findings: list[EvaluationFinding] = []
    if not runtime_binding_ref:
        findings.append(
            _finding(
                "runtime_binding_ref",
                "Runtime binding contract must carry a product-level binding ref.",
                severity="blocking",
            )
        )
    if continuable_evidence_session_ref is None:
        findings.append(
            _finding(
                "runtime_binding_session_ref",
                "Runtime binding contract should carry the product session ref.",
                severity="warning",
            )
        )
    if runtime_binding_status not in {
        "unavailable",
        "probed",
        "bindable",
        "bound",
        "failed",
    }:
        findings.append(
            _finding(
                "runtime_binding_status",
                "Runtime binding status is outside the approved product states.",
                severity="blocking",
            )
        )
    if runtime_binding_scope != "agent_session_event_artifactservice":
        findings.append(
            _finding(
                "runtime_binding_scope",
                "Runtime binding scope must remain the approved isolated scope.",
                severity="blocking",
            )
        )
    forbidden_flags = {
        "raw_runtime_object_included": raw_runtime_object_included,
        "raw_event_payload_included": raw_event_payload_included,
        "artifact_body_included": artifact_body_included,
        "adk_eval_raw_data_included": adk_eval_raw_data_included,
        "user_product_runtime_path_enabled": user_product_runtime_path_enabled,
        "default_local_state_dir_enabled": default_local_state_dir_enabled,
        "auto_resume_answer_enabled": auto_resume_answer_enabled,
        "skills_loaded": skills_loaded,
        "memory_enabled": memory_enabled,
        "tools_mcp_enabled": tools_mcp_enabled,
        "callbacks_enabled": callbacks_enabled,
        "plugins_enabled": plugins_enabled,
    }
    for flag_name, enabled in forbidden_flags.items():
        if enabled:
            findings.append(
                _finding(
                    f"runtime_binding_{flag_name}",
                    f"{flag_name} must remain false in product-level binding.",
                    severity="blocking",
                )
            )
    if runtime_binding_status in {"probed", "bindable", "bound"}:
        if not event_review_refs:
            findings.append(
                _finding(
                    "runtime_binding_event_review_refs",
                    "Bindable runtime projections should carry safe event review refs.",
                    severity="warning",
                )
            )
        if not artifact_binding_summary_refs:
            findings.append(
                _finding(
                    "runtime_binding_artifact_refs",
                    "Bindable runtime projections should carry artifact binding summary refs.",
                    severity="warning",
                )
            )
        if not runtime_binding_evaluation_summary_ref:
            findings.append(
                _finding(
                    "runtime_binding_evaluation_summary_ref",
                    "Bindable runtime projections should carry an evaluation summary ref.",
                    severity="warning",
                )
            )
    return _result(
        evaluation_id=evaluation_id,
        findings=findings,
        passed_summary="Runtime binding product contract passed.",
        failed_summary="Runtime binding product contract needs attention.",
        evaluation_scope="runtime_binding_product_contract",
    )


def evaluation_input_for_continuable_session(
    *,
    evaluation_id: str,
    session_ref: str,
    summary_preview: str | None = None,
    source_refs: list[str] | None = None,
) -> EvaluationInput:
    """Build a minimal safe evaluation input for a continuable session."""

    return EvaluationInput(
        evaluation_id=evaluation_id,
        subject=EvaluationSubject(
            kind="product_experience",
            subject_ref=session_ref,
            answer_preview=summary_preview,
            evidence_refs=[
                EvaluationRef(ref=ref, kind="product_ref", purpose="session_source")
                for ref in (source_refs or [])
            ],
        ),
        criteria=[
            EvaluationCriterion(name="resume_summary_boundary"),
            EvaluationCriterion(name="resume_summary_usefulness"),
            EvaluationCriterion(name="turn_kind_boundary"),
            EvaluationCriterion(name="trajectory_summary_quality"),
            EvaluationCriterion(name="storage_policy_boundary"),
            EvaluationCriterion(name="session_record_manifest_boundary"),
            EvaluationCriterion(name="delete_expire_export_policy_boundary"),
            EvaluationCriterion(name="runtime_binding_product_contract"),
        ],
        profile_ref=CONTINUABLE_EVIDENCE_SESSION_EVALUATION_PROFILE,
        metadata={"evaluation_scope": "continuable_evidence_session"},
    )


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
        profile_ref=CONTINUABLE_EVIDENCE_SESSION_EVALUATION_PROFILE,
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
    "CONTINUABLE_EVIDENCE_SESSION_EVALUATION_PROFILE",
    "evaluate_delete_expire_export_policy_boundary",
    "evaluate_resume_summary_boundary",
    "evaluate_resume_summary_usefulness",
    "evaluate_runtime_binding_product_contract",
    "evaluate_session_record_manifest_boundary",
    "evaluate_storage_policy_boundary",
    "evaluate_trajectory_summary_quality",
    "evaluate_turn_kind_boundary",
    "evaluation_input_for_continuable_session",
]
