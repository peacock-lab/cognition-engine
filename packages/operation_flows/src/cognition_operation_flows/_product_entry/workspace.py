"""Private product-entry run workspace implementation."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from cognition_operation_flows._core.run_workspace import (
    TwfRunWorkspaceStateCandidate,
    build_twf_run_workspace_policy,
    create_twf_run_workspace,
    finalize_twf_run_workspace,
    write_twf_run_workspace_json,
    write_twf_run_workspace_text,
)


def build_twf_product_entry_run_workspace_policy(
    *,
    workspace_root: str | Path,
    retention_policy: str,
    cleanup_policy: str,
    max_write_bytes: int,
) -> Any:
    """Build a governed TWF run workspace policy."""

    return build_twf_run_workspace_policy(
        workspace_root=workspace_root,
        retention_policy=retention_policy,
        cleanup_policy=cleanup_policy,
        max_write_bytes=max_write_bytes,
    )


def create_twf_product_entry_run_workspace(
    *,
    policy: Any,
    workflow_name: str,
    run_id: str,
) -> Any:
    """Create a governed TWF run workspace."""

    return create_twf_run_workspace(
        policy=policy,
        workflow_name=workflow_name,
        run_id=run_id,
    )


def write_twf_product_entry_run_workspace_json(
    workspace: Any,
    *,
    relative_path: str,
    payload: Mapping[str, Any],
    kind: str,
    max_write_bytes: int,
) -> tuple[Any, Any]:
    """Write a governed JSON artifact to a TWF run workspace."""

    return write_twf_run_workspace_json(
        workspace,
        relative_path=relative_path,
        payload=payload,
        kind=kind,
        max_write_bytes=max_write_bytes,
    )


def write_twf_product_entry_run_workspace_text(
    workspace: Any,
    *,
    relative_path: str,
    text: str,
    kind: str,
    max_write_bytes: int | None = None,
) -> tuple[Any, Any]:
    """Write a governed text artifact to a TWF run workspace."""

    return write_twf_run_workspace_text(
        workspace,
        relative_path=relative_path,
        text=text,
        kind=kind,
        max_write_bytes=max_write_bytes,
    )


def finalize_twf_product_entry_run_workspace(
    workspace: Any,
    *,
    status: str,
    metadata: Mapping[str, Any] | None = None,
) -> Any:
    """Finalize a governed TWF run workspace."""

    return finalize_twf_run_workspace(
        workspace,
        status=status,
        metadata=metadata,
    )


def restore_twf_product_entry_run_workspace_snapshot(
    snapshot: Mapping[str, Any],
) -> Any:
    """Restore a governed TWF run workspace state from a snapshot."""

    return TwfRunWorkspaceStateCandidate(
        workspace_ref=str(snapshot.get("workspace_ref") or ""),
        workspace_path=str(snapshot.get("workspace_path") or ""),
        workflow_name=str(snapshot.get("workflow_name") or ""),
        run_id=str(snapshot.get("run_id") or ""),
        workspace_created=bool(snapshot.get("workspace_created")),
        retention_policy=str(snapshot.get("retention_policy") or "keep"),
        cleanup_policy=str(snapshot.get("cleanup_policy") or "manual"),
        manifest_path=str(snapshot.get("manifest_path") or ""),
        subdirs=tuple(str(item) for item in snapshot.get("subdirs") or ()),
        artifact_refs=tuple(
            str(item) for item in snapshot.get("artifact_refs") or ()
        ),
        evidence_refs=tuple(
            str(item) for item in snapshot.get("evidence_refs") or ()
        ),
        result_refs=tuple(str(item) for item in snapshot.get("result_refs") or ()),
        cleanup_performed=bool(snapshot.get("cleanup_performed")),
        blocking_reasons=tuple(
            str(item) for item in snapshot.get("blocking_reasons") or ()
        ),
        warnings=tuple(str(item) for item in snapshot.get("warnings") or ()),
        metadata=dict(snapshot.get("metadata") or {}),
    )


__all__ = [
    "build_twf_product_entry_run_workspace_policy",
    "create_twf_product_entry_run_workspace",
    "finalize_twf_product_entry_run_workspace",
    "restore_twf_product_entry_run_workspace_snapshot",
    "write_twf_product_entry_run_workspace_json",
    "write_twf_product_entry_run_workspace_text",
]
