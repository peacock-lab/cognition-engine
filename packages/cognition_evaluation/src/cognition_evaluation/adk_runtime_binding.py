"""Evaluation helpers for ADK isolated runtime binding projections."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from cognition_evaluation.models import (
    EvaluationFinding,
    EvaluationProfileRef,
    EvaluationResult,
)


ADK_RUNTIME_BINDING_EVALUATION_PROFILE = EvaluationProfileRef(
    ref="evaluation-profile://adk-runtime-binding/safe-projection-v1",
    name="adk_runtime_binding_safe_projection",
    version="v1",
)


def evaluate_adk_runtime_binding_safe_projection(
    *,
    projection: Mapping[str, Any],
    evaluation_id: str = "evaluation://adk-runtime-binding/safe-projection",
) -> EvaluationResult:
    """Evaluate whether an ADK runtime binding projection is product-safe."""

    findings: list[EvaluationFinding] = []
    required_fields = (
        "probe_ref",
        "agent_ref",
        "session_binding_ref",
        "invocation_ref",
        "event_count",
        "event_summaries",
        "artifact_summary",
        "service_summary",
    )
    for field_name in required_fields:
        if field_name not in projection or projection.get(field_name) in (None, ""):
            findings.append(
                _finding(
                    "runtime_binding_projection_required_fields",
                    "Runtime binding projection is missing required safe fields.",
                    metadata={"field": field_name},
                )
            )

    if projection.get("raw_object_included"):
        findings.append(
            _finding(
                "runtime_binding_raw_object_boundary",
                "Runtime binding projection must not include raw ADK objects.",
            )
        )
    for flag_name in (
        "user_product_path_enabled",
        "default_local_state_dir_enabled",
        "auto_resume_enabled",
        "skills_loaded",
        "memory_enabled",
    ):
        if projection.get(flag_name):
            findings.append(
                _finding(
                    "runtime_binding_scope_boundary",
                    "Runtime binding probe opened a disallowed capability.",
                    metadata={"flag": flag_name},
                )
            )

    if int(projection.get("event_count") or 0) <= 0:
        findings.append(
            _finding(
                "runtime_binding_event_summary",
                "Runtime binding projection must include at least one safe event summary.",
            )
        )
    event_summaries = projection.get("event_summaries") or []
    if not isinstance(event_summaries, Sequence) or isinstance(event_summaries, (str, bytes)):
        findings.append(
            _finding(
                "runtime_binding_event_summary",
                "Runtime binding event summaries must be a sequence.",
            )
        )
    else:
        for index, event in enumerate(event_summaries):
            if not isinstance(event, Mapping):
                findings.append(
                    _finding(
                        "runtime_binding_event_summary",
                        "Runtime binding event summary must be a mapping.",
                        metadata={"event_index": index},
                    )
                )
                continue
            for forbidden_key in ("raw_event", "content", "output", "raw_payload"):
                if forbidden_key in event:
                    findings.append(
                        _finding(
                            "runtime_binding_event_raw_boundary",
                            "Runtime binding event summary contains raw payload fields.",
                            metadata={"event_index": index, "field": forbidden_key},
                        )
                    )

    artifact_summary = projection.get("artifact_summary") or {}
    if isinstance(artifact_summary, Mapping):
        if artifact_summary.get("body_included"):
            findings.append(
                _finding(
                    "runtime_binding_artifact_body_boundary",
                    "Artifact projection must not include artifact body.",
                )
            )
        if not artifact_summary.get("deleted_after_probe"):
            findings.append(
                _finding(
                    "runtime_binding_artifact_lifecycle",
                    "Isolated probe artifact should be deleted after lifecycle check.",
                    severity="warning",
                )
            )
    else:
        findings.append(
            _finding(
                "runtime_binding_artifact_summary",
                "Artifact summary must be a safe mapping.",
            )
        )

    service_summary = projection.get("service_summary") or {}
    if isinstance(service_summary, Mapping):
        if not service_summary.get("in_memory_services"):
            findings.append(
                _finding(
                    "runtime_binding_service_boundary",
                    "Runtime binding probe must use in-memory services.",
                )
            )
    else:
        findings.append(
            _finding(
                "runtime_binding_service_summary",
                "Service summary must be a safe mapping.",
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
        profile_ref=ADK_RUNTIME_BINDING_EVALUATION_PROFILE,
        summary=(
            "ADK runtime binding safe projection passed."
            if not findings
            else "ADK runtime binding safe projection produced findings."
        ),
        metadata={
            "evaluation_scope": "adk_runtime_binding_safe_projection",
            "adk_evaluation_utility_influence": (
                "trajectory/tool-use/multi-turn/final-response evaluation ideas"
            ),
        },
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
