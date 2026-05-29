"""Evaluation helpers for ADK Workflow no-live safe projections."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from cognition_evaluation.adk_native import detect_adk_native_evaluation_capability
from cognition_evaluation.models import (
    EvaluationFinding,
    EvaluationProfileRef,
    EvaluationResult,
)


ADK_WORKFLOW_NO_LIVE_EVALUATION_PROFILE = EvaluationProfileRef(
    ref="evaluation-profile://adk-workflow-no-live/safe-projection-v1",
    name="adk_workflow_no_live_safe_projection",
    version="v1",
)


def evaluate_adk_workflow_no_live_safe_projection(
    *,
    projection: Mapping[str, Any],
    evaluation_id: str = "evaluation://adk-workflow-no-live/safe-projection",
) -> EvaluationResult:
    """Evaluate whether a Workflow no-live projection is product-safe."""

    findings: list[EvaluationFinding] = []
    required_fields = (
        "probe_ref",
        "workflow_ref",
        "invocation_ref",
        "workflow_status",
        "event_count",
        "event_review_refs",
        "artifact_binding_summary_refs",
        "evaluation_summary_ref",
        "service_summary",
    )
    for field_name in required_fields:
        if field_name not in projection or projection.get(field_name) in (None, ""):
            findings.append(
                _finding(
                    "workflow_no_live_required_fields",
                    "Workflow no-live projection is missing required safe fields.",
                    metadata={"field": field_name},
                )
            )

    for flag_name in (
        "raw_object_included",
        "raw_event_payload_included",
        "artifact_body_included",
        "adk_eval_raw_data_included",
        "user_product_path_enabled",
        "default_local_state_dir_enabled",
        "auto_resume_enabled",
        "skills_loaded",
        "memory_enabled",
        "tools_mcp_enabled",
        "callbacks_enabled",
        "plugins_enabled",
    ):
        if projection.get(flag_name):
            findings.append(
                _finding(
                    "workflow_no_live_scope_boundary",
                    "Workflow no-live projection opened a disallowed capability.",
                    metadata={"flag": flag_name},
                )
            )

    if int(projection.get("event_count") or 0) <= 0:
        findings.append(
            _finding(
                "workflow_no_live_event_summary",
                "Workflow no-live projection must include safe event facts.",
            )
        )
    event_review_refs = projection.get("event_review_refs") or []
    if not _is_sequence_of_strings(event_review_refs):
        findings.append(
            _finding(
                "workflow_no_live_event_review_refs",
                "Workflow no-live event review refs must be a string sequence.",
            )
        )
    artifact_refs = projection.get("artifact_binding_summary_refs") or []
    if not _is_sequence_of_strings(artifact_refs):
        findings.append(
            _finding(
                "workflow_no_live_artifact_refs",
                "Workflow no-live artifact binding refs must be a string sequence.",
            )
        )
    elif not artifact_refs:
        findings.append(
            _finding(
                "workflow_no_live_artifact_refs",
                "Workflow no-live projection should include artifact refs.",
                severity="warning",
            )
        )

    service_summary = projection.get("service_summary") or {}
    if isinstance(service_summary, Mapping):
        if not service_summary.get("in_memory_services"):
            findings.append(
                _finding(
                    "workflow_no_live_service_boundary",
                    "Workflow no-live probe must use in-memory services.",
                )
            )
    else:
        findings.append(
            _finding(
                "workflow_no_live_service_summary",
                "Workflow no-live service summary must be a safe mapping.",
            )
        )

    capability = detect_adk_native_evaluation_capability()
    if not capability.module_available:
        findings.append(
            _finding(
                "workflow_no_live_adk_evaluation_capability",
                "ADK evaluation utility module is unavailable.",
                severity="warning",
            )
        )

    status = (
        "failed"
        if any(f.severity == "blocking" for f in findings)
        else "warning"
        if findings
        else "passed"
    )
    return EvaluationResult(
        evaluation_id=evaluation_id,
        status=status,
        findings=findings,
        profile_ref=ADK_WORKFLOW_NO_LIVE_EVALUATION_PROFILE,
        summary=(
            "ADK Workflow no-live safe projection passed."
            if not findings
            else "ADK Workflow no-live safe projection produced findings."
        ),
        metadata={
            "evaluation_scope": "adk_workflow_no_live_safe_projection",
            "adk_evaluation_utility_module_available": capability.module_available,
            "adk_evaluation_utility_agent_evaluator_available": (
                capability.agent_evaluator_available
            ),
            "adk_evaluation_utility_influence": (
                "trajectory/tool-use/multi-turn/final-response evaluation ideas"
            ),
            "runtime_execution_enabled": False,
            "governance_decision_enabled": False,
        },
    )


def _is_sequence_of_strings(value: Any) -> bool:
    return (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
        and all(isinstance(item, str) and item for item in value)
    )


def _finding(
    criterion: str,
    message: str,
    *,
    severity: str = "blocking",
    metadata: dict[str, Any] | None = None,
) -> EvaluationFinding:
    return EvaluationFinding(
        criterion=criterion,
        status="failed",
        severity=severity,  # type: ignore[arg-type]
        message=message,
        metadata=metadata or {},
    )
