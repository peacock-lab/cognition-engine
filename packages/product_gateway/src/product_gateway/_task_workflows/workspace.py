"""Product gateway workspace operations for task workflow artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from cognition_task_workflows.product_entry_service import (
    build_twf_product_entry_run_workspace_policy,
    create_twf_product_entry_run_workspace,
    finalize_twf_product_entry_run_workspace,
    restore_twf_product_entry_run_workspace_snapshot,
    write_twf_product_entry_run_workspace_json,
    write_twf_product_entry_run_workspace_text,
)


def build_internal_twf_run_workspace_policy(
    *,
    workspace_root: str | Path,
    retention_policy: str,
    cleanup_policy: str,
    max_write_bytes: int,
) -> Any:
    """Build a governed task workflow run-workspace policy."""

    return build_twf_product_entry_run_workspace_policy(
        workspace_root=workspace_root,
        retention_policy=retention_policy,
        cleanup_policy=cleanup_policy,
        max_write_bytes=max_write_bytes,
    )


def create_internal_twf_run_workspace(
    *,
    policy: Any,
    workflow_name: str,
    run_id: str,
) -> Any:
    """Create a governed task workflow run workspace."""

    return create_twf_product_entry_run_workspace(
        policy=policy,
        workflow_name=workflow_name,
        run_id=run_id,
    )


def write_internal_twf_run_workspace_json(
    workspace: Any,
    *,
    relative_path: str,
    payload: Mapping[str, Any],
    kind: str,
    max_write_bytes: int,
) -> tuple[Any, Any]:
    """Write a governed JSON artifact to a task workflow run workspace."""

    return write_twf_product_entry_run_workspace_json(
        workspace,
        relative_path=relative_path,
        payload=payload,
        kind=kind,
        max_write_bytes=max_write_bytes,
    )


def write_internal_twf_run_workspace_text(
    workspace: Any,
    *,
    relative_path: str,
    text: str,
    kind: str,
    max_write_bytes: int | None = None,
) -> tuple[Any, Any]:
    """Write a governed text artifact to a task workflow run workspace."""

    return write_twf_product_entry_run_workspace_text(
        workspace,
        relative_path=relative_path,
        text=text,
        kind=kind,
        max_write_bytes=max_write_bytes,
    )


def finalize_internal_twf_run_workspace(
    workspace: Any,
    *,
    status: str,
    metadata: Mapping[str, Any] | None = None,
) -> Any:
    """Finalize a governed task workflow run workspace."""

    return finalize_twf_product_entry_run_workspace(
        workspace,
        status=status,
        metadata=metadata,
    )


def restore_internal_twf_run_workspace_snapshot(
    snapshot: Mapping[str, Any],
) -> Any:
    """Restore a governed task workflow workspace state from a snapshot."""

    return restore_twf_product_entry_run_workspace_snapshot(snapshot)


__all__ = [
    "build_internal_twf_run_workspace_policy",
    "create_internal_twf_run_workspace",
    "finalize_internal_twf_run_workspace",
    "restore_internal_twf_run_workspace_snapshot",
    "write_internal_twf_run_workspace_json",
    "write_internal_twf_run_workspace_text",
]
