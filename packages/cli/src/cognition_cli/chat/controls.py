"""Chat control and config-resolution helpers for the Cognition System CLI."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any


def _chat_plan_manual_controls_requested(args: argparse.Namespace) -> bool:
    return bool(
        args.reference_paths
        or getattr(args, "external_readonly_evidence_paths", ())
        or args.tool_exposure_profile
        or _chat_plan_workspace_args_requested(args)
        or _chat_audit_workspace_args_requested(args)
    )


def _chat_plan_config_dependent_controls_requested(
    args: argparse.Namespace,
) -> bool:
    return bool(
        args.reference_paths
        or args.tool_exposure_profile
        or _chat_plan_workspace_args_requested(args)
        or _chat_audit_workspace_args_requested(args)
    )


def _chat_audit_workspace_args_requested(args: argparse.Namespace) -> bool:
    return bool(
        getattr(args, "audit_run_workspace_path", None) is not None
        or getattr(args, "audit_run_workspace_ref", None)
        or getattr(args, "audit_run_workspace_root", None) is not None
        or getattr(args, "audit_focus", ())
    )


def _chat_plan_workspace_args_requested(args: argparse.Namespace) -> bool:
    return bool(
        args.enable_run_workspace
        or args.run_workspace_root is not None
        or args.run_workspace_retention_policy is not None
        or args.run_workspace_cleanup_policy is not None
        or args.run_workspace_max_write_bytes is not None
    )


def _chat_plan_manual_control_missing_governance(
    args: argparse.Namespace,
) -> list[str]:
    missing: list[str] = []
    if args.operator_approved is not True:
        missing.append("--operator-approved")
    if not args.approval_ref:
        missing.append("--approval-ref")
    if not args.audit_ref:
        missing.append("--audit-ref")
    if not args.sanitized_evidence_ref:
        missing.append("--sanitized-evidence-ref")
    if not args.governance_summary_output_ref:
        missing.append("--governance-summary-output-ref")
    return missing


def _chat_plan_control_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    config_context = _chat_plan_runtime_config_context(args)
    tool_exposure = getattr(config_context, "tool_exposure", None)
    run_workspace = getattr(config_context, "run_workspace", None)

    profile_name = (
        args.tool_exposure_profile
        or getattr(tool_exposure, "default_profile", None)
        or "readonly_reference"
    )
    profile_config = (
        tool_exposure.to_profile_config() if tool_exposure is not None else None
    )
    workspace_config_kwargs = (
        run_workspace.to_policy_kwargs() if run_workspace is not None else {}
    )
    workspace_enabled = bool(
        _chat_plan_workspace_args_requested(args)
        or getattr(run_workspace, "enabled_by_default", False)
    )
    workspace_root = _chat_plan_workspace_root(
        args,
        configured_root=workspace_config_kwargs.get("workspace_root"),
    )
    if not workspace_enabled:
        workspace_root = None

    entrypoint_explicit_args: dict[str, Any] = {}
    if args.tool_exposure_profile:
        entrypoint_explicit_args["profile_name"] = args.tool_exposure_profile

    return {
        "reference_paths": tuple(args.reference_paths),
        "reference_repo_root": str(_chat_plan_repo_root(args.config_root)),
        "external_readonly_evidence_paths": tuple(
            getattr(args, "external_readonly_evidence_paths", ())
        ),
        "external_readonly_evidence_repo_root": str(
            _chat_plan_repo_root(args.config_root)
        ),
        "reference_profile_name": profile_name,
        "reference_profile_config": profile_config,
        "reference_entrypoint_explicit_args": entrypoint_explicit_args,
        "run_workspace_root": workspace_root,
        "run_workspace_enabled": workspace_enabled,
        "run_workspace_retention_policy": (
            args.run_workspace_retention_policy
            or str(workspace_config_kwargs.get("retention_policy") or "keep")
        ),
        "run_workspace_cleanup_policy": (
            args.run_workspace_cleanup_policy
            or str(workspace_config_kwargs.get("cleanup_policy") or "manual")
        ),
        "run_workspace_max_write_bytes": (
            args.run_workspace_max_write_bytes
            or int(workspace_config_kwargs.get("max_write_bytes") or 65536)
        ),
        "metadata": {
            "manual_reference_paths_requested": bool(args.reference_paths),
            "manual_external_readonly_evidence_paths_requested": bool(
                getattr(args, "external_readonly_evidence_paths", ())
            ),
            "manual_run_workspace_requested": _chat_plan_workspace_args_requested(
                args
            ),
            "tool_exposure_profile_source": (
                "entrypoint_explicit_args"
                if args.tool_exposure_profile
                else (
                    "profile_config"
                    if tool_exposure is not None
                    else "default_values"
                )
            ),
            "run_workspace_config_source": (
                "entrypoint_explicit_args"
                if _chat_plan_workspace_args_requested(args)
                else (
                    "profile_config"
                    if getattr(run_workspace, "enabled_by_default", False)
                    else "default_values"
                )
            ),
        },
    }


def _chat_plan_runtime_config_context(args: argparse.Namespace) -> Any | None:
    if getattr(args, "_chat_plan_runtime_config_context_resolved", False):
        return getattr(args, "_chat_plan_runtime_config_context", None)
    try:
        from config_assembly.runtime import assemble_runtime_config_payload
        from config_contexts.runtime_builder import build_runtime_config_contexts

        config_payload = assemble_runtime_config_payload(
            config_root=args.config_root,
            environment=args.environment,
        )
        config_context = build_runtime_config_contexts(config_payload)
        args._chat_plan_runtime_config_context = config_context
        args._chat_plan_runtime_config_context_resolved = True
        return config_context
    except Exception:
        if _chat_plan_config_dependent_controls_requested(args):
            raise
        args._chat_plan_runtime_config_context = None
        args._chat_plan_runtime_config_context_resolved = True
        return None


def _chat_plan_workspace_root(
    args: argparse.Namespace,
    *,
    configured_root: Any,
) -> str | None:
    if args.run_workspace_root is not None:
        return str(args.run_workspace_root)
    if configured_root:
        root = Path(str(configured_root)).expanduser()
        if not root.is_absolute():
            root = _chat_plan_repo_root(args.config_root) / root
        return str(root)
    return None


def _chat_plan_repo_root(config_root: Path) -> Path:
    root = Path(config_root).expanduser()
    if root.name == "config":
        return root.parent.resolve()
    return Path.cwd().resolve()
