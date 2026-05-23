"""Shared task-control candidates for governed task workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
import re
from typing import Any


TWF_CONTROL_STAGES = (
    "preflight",
    "staging",
    "plan",
    "execute",
    "observe",
    "summarize",
    "cleanup/result",
)
TWF_CONFIG_PRECEDENCE = (
    "entrypoint_explicit_args",
    "session_args",
    "profile_config",
    "default_values",
)
MANAGED_GOVERNANCE_PARAMETERS = frozenset(
    {
        "approval_ref",
        "audit_ref",
        "risk_level",
        "output_budget",
        "live_gate",
        "allow_live_llm",
        "allow_ollama",
        "live_llm_approval_ref",
        "sanitized_evidence_ref",
        "governance_summary_output_ref",
    }
)
KNOWN_RISK_LEVELS = frozenset({"none", "low", "medium", "high", "unknown"})


@dataclass(frozen=True)
class TwfPreflightCandidate:
    """Preflight facts for a governed task workflow."""

    allowed: bool
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    managed_parameters: tuple[str, ...] = ()
    passthrough_parameter_keys: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfWorkspaceCandidate:
    """Run workspace candidate without creating filesystem state yet."""

    workspace_ref: str
    workspace_created: bool = False
    retention_policy: str = "candidate_only_not_created"
    cleanup_policy: str = "no_cleanup_required_until_workspace_created"
    artifact_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TwfRunContextCandidate:
    """Task-control context shared by task workflows."""

    workflow_name: str
    task_kind: str
    run_id: str
    stages: tuple[str, ...]
    preflight: TwfPreflightCandidate
    workspace: TwfWorkspaceCandidate
    config_precedence: tuple[str, ...]
    status: str
    evidence_summary: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


def build_twf_run_id(
    workflow_name: str,
    *,
    session_id: str | None = None,
    turn_index: int | None = None,
) -> str:
    """Build a stable, display-safe run id for task contexts."""

    workflow_slug = _slug_or_default(workflow_name, "workflow")
    session_slug = _slug_or_default(session_id or "", "session")
    turn_slug = f"turn-{turn_index:03d}" if isinstance(turn_index, int) else "turn-000"
    return f"{workflow_slug}-{session_slug}-{turn_slug}"


def evaluate_twf_preflight(
    *,
    live_model_allowed: bool,
    approval_ref: str | None = None,
    audit_ref: str | None = None,
    sanitized_evidence_ref: str | None = None,
    risk_level: str = "unknown",
    output_budget: int | None = None,
    live_gate: str | None = None,
    user_passthrough_parameters: Mapping[str, Any] | None = None,
) -> TwfPreflightCandidate:
    """Evaluate generic task preflight without calling external services."""

    passthrough_keys = tuple(sorted((user_passthrough_parameters or {}).keys()))
    managed_keys = tuple(sorted(MANAGED_GOVERNANCE_PARAMETERS))
    conflicts = tuple(
        key for key in passthrough_keys if key in MANAGED_GOVERNANCE_PARAMETERS
    )
    blocking_reasons = tuple(
        f"user_passthrough_overrides_{key}" for key in conflicts
    )
    warnings: list[str] = []
    normalized_risk = (risk_level or "unknown").strip().lower()
    if normalized_risk not in KNOWN_RISK_LEVELS:
        warnings.append("risk_level_unrecognized")
    if output_budget is None:
        warnings.append("output_budget_not_set")
    elif output_budget <= 0:
        blocking_reasons = (*blocking_reasons, "output_budget_invalid")
    if not live_gate:
        warnings.append("live_gate_inferred")
    if live_model_allowed:
        if not approval_ref:
            warnings.append("approval_ref_missing_observed")
        if not audit_ref:
            warnings.append("audit_ref_missing_observed")
        if not sanitized_evidence_ref:
            warnings.append("sanitized_evidence_ref_missing_observed")
    else:
        warnings.append("live_model_disabled")
    return TwfPreflightCandidate(
        allowed=not blocking_reasons,
        blocking_reasons=blocking_reasons,
        warnings=tuple(_ordered_unique(warnings)),
        managed_parameters=managed_keys,
        passthrough_parameter_keys=passthrough_keys,
        metadata={
            "stage": "preflight",
            "live_model_allowed": live_model_allowed,
            "managed_parameter_conflicts": conflicts,
            "risk_level": normalized_risk,
            "output_budget": output_budget,
        },
    )


def build_twf_workspace_candidate(
    *,
    workflow_name: str,
    run_id: str,
    artifact_refs: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    retention_policy: str = "candidate_only_not_created",
    cleanup_policy: str = "no_cleanup_required_until_workspace_created",
) -> TwfWorkspaceCandidate:
    """Build a run workspace candidate without touching the filesystem."""

    return TwfWorkspaceCandidate(
        workspace_ref=f"run-workspace://{_slug_or_default(workflow_name, 'workflow')}/{run_id}",
        workspace_created=False,
        retention_policy=retention_policy,
        cleanup_policy=cleanup_policy,
        artifact_refs=tuple(_ordered_unique(artifact_refs)),
        evidence_refs=tuple(_ordered_unique(evidence_refs)),
        metadata={
            "stage": "staging",
            "workspace_mode": "candidate_only",
        },
    )


def build_twf_run_context(
    *,
    workflow_name: str,
    task_kind: str,
    session_id: str | None = None,
    turn_index: int | None = None,
    live_model_allowed: bool = False,
    approval_ref: str | None = None,
    audit_ref: str | None = None,
    sanitized_evidence_ref: str | None = None,
    risk_level: str = "unknown",
    output_budget: int | None = None,
    live_gate: str | None = None,
    user_passthrough_parameters: Mapping[str, Any] | None = None,
    artifact_refs: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    metadata: Mapping[str, Any] | None = None,
) -> TwfRunContextCandidate:
    """Build the shared task-control context for a workflow run."""

    resolved_live_gate = live_gate or (
        "controlled_live" if live_model_allowed else "no_live"
    )
    run_id = build_twf_run_id(
        workflow_name,
        session_id=session_id,
        turn_index=turn_index,
    )
    preflight = evaluate_twf_preflight(
        live_model_allowed=live_model_allowed,
        approval_ref=approval_ref,
        audit_ref=audit_ref,
        sanitized_evidence_ref=sanitized_evidence_ref,
        risk_level=risk_level,
        output_budget=output_budget,
        live_gate=resolved_live_gate,
        user_passthrough_parameters=user_passthrough_parameters,
    )
    workspace = build_twf_workspace_candidate(
        workflow_name=workflow_name,
        run_id=run_id,
        artifact_refs=artifact_refs,
        evidence_refs=tuple(
            ref
            for ref in (audit_ref, sanitized_evidence_ref, *tuple(evidence_refs))
            if ref
        ),
    )
    status = "preflight_allowed" if preflight.allowed else "blocked"
    evidence_summary = {
        "approval_ref_present": bool(approval_ref),
        "audit_ref_present": bool(audit_ref),
        "sanitized_evidence_ref_present": bool(sanitized_evidence_ref),
        "risk_level": (risk_level or "unknown").strip().lower(),
        "output_budget": output_budget,
        "live_gate": resolved_live_gate,
    }
    return TwfRunContextCandidate(
        workflow_name=workflow_name,
        task_kind=task_kind,
        run_id=run_id,
        stages=TWF_CONTROL_STAGES,
        preflight=preflight,
        workspace=workspace,
        config_precedence=TWF_CONFIG_PRECEDENCE,
        status=status,
        evidence_summary=evidence_summary,
        metadata={
            "control_structure": "preflight->staging->plan->execute->observe->summarize->cleanup/result",
            "entrypoint_boundary": "entrypoint_handles_args_trigger_display_only",
            **dict(metadata or {}),
        },
    )


def finalize_twf_run_context(
    context: TwfRunContextCandidate,
    *,
    status: str,
    artifact_refs: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    workspace_ref: str | None = None,
    workspace_created: bool | None = None,
    retention_policy: str | None = None,
    cleanup_policy: str | None = None,
    workspace_metadata: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> TwfRunContextCandidate:
    """Return a finalized context with result refs and status attached."""

    workspace = replace(
        context.workspace,
        workspace_ref=workspace_ref or context.workspace.workspace_ref,
        workspace_created=(
            workspace_created
            if workspace_created is not None
            else context.workspace.workspace_created
        ),
        retention_policy=retention_policy or context.workspace.retention_policy,
        cleanup_policy=cleanup_policy or context.workspace.cleanup_policy,
        artifact_refs=tuple(
            _ordered_unique((*context.workspace.artifact_refs, *artifact_refs))
        ),
        evidence_refs=tuple(
            _ordered_unique((*context.workspace.evidence_refs, *evidence_refs))
        ),
        metadata={
            **context.workspace.metadata,
            **dict(workspace_metadata or {}),
        },
    )
    return replace(
        context,
        status=status,
        workspace=workspace,
        metadata={
            **context.metadata,
            "finalized": True,
            **dict(metadata or {}),
        },
    )


def twf_run_context_status_dict(
    context: TwfRunContextCandidate,
) -> dict[str, Any]:
    """Build a sanitized status/evidence dict for result metadata."""

    return {
        "workflow_name": context.workflow_name,
        "task_kind": context.task_kind,
        "run_id": context.run_id,
        "status": context.status,
        "stages": list(context.stages),
        "preflight": {
            "allowed": context.preflight.allowed,
            "blocking_reasons": list(context.preflight.blocking_reasons),
            "warnings": list(context.preflight.warnings),
            "managed_parameters": list(context.preflight.managed_parameters),
            "passthrough_parameter_keys": list(
                context.preflight.passthrough_parameter_keys
            ),
        },
        "workspace": {
            "workspace_ref": context.workspace.workspace_ref,
            "workspace_created": context.workspace.workspace_created,
            "retention_policy": context.workspace.retention_policy,
            "cleanup_policy": context.workspace.cleanup_policy,
            "artifact_refs": list(context.workspace.artifact_refs),
            "evidence_refs": list(context.workspace.evidence_refs),
        },
        "config_precedence": list(context.config_precedence),
        "evidence_summary": dict(context.evidence_summary),
        "metadata": dict(context.metadata),
    }


def _slug_or_default(value: str, default: str) -> str:
    lowered = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or default


def _ordered_unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique
