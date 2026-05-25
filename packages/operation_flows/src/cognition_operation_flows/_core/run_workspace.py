"""Governed run workspace helpers for operation flows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
import json
from pathlib import Path
import re
import shutil
from typing import Any


OPERATION_FLOW_RUN_WORKSPACE_SCHEMA_VERSION = "operation_flow-run-workspace.v1"
OPERATION_FLOW_RUN_WORKSPACE_SUBDIRS = (
    "inputs",
    "references",
    "evidence",
    "artifacts",
    "results",
)
OPERATION_FLOW_RUN_WORKSPACE_RETENTION_POLICIES = frozenset(
    {"keep", "ephemeral", "delete_on_success"}
)
OPERATION_FLOW_RUN_WORKSPACE_CLEANUP_POLICIES = frozenset(
    {"manual", "delete_on_success", "delete_always"}
)
OPERATION_FLOW_RUN_WORKSPACE_FORBIDDEN_PATH_MARKERS = (
    ".env",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "api_key",
    "credential",
    "id_dsa",
    "id_ed25519",
    "id_rsa",
    "password",
    "private_key",
    "secret",
    "service_account",
    "token",
)


@dataclass(frozen=True)
class OperationFlowRunWorkspacePolicyCandidate:
    """Policy for creating and writing one governed run workspace."""

    workspace_root: str
    retention_policy: str = "keep"
    cleanup_policy: str = "manual"
    max_write_bytes: int = 65536
    allowed_subdirs: tuple[str, ...] = OPERATION_FLOW_RUN_WORKSPACE_SUBDIRS
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationFlowRunWorkspaceStateCandidate:
    """Created run workspace state and refs."""

    workspace_ref: str
    workspace_path: str
    workflow_name: str
    run_id: str
    workspace_created: bool
    retention_policy: str
    cleanup_policy: str
    manifest_path: str
    subdirs: tuple[str, ...]
    artifact_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    result_refs: tuple[str, ...] = ()
    cleanup_performed: bool = False
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationFlowRunWorkspaceWriteCandidate:
    """One workspace write result."""

    ref: str
    path: str
    relative_path: str
    kind: str
    bytes_written: int
    status: str
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationFlowRunWorkspaceCleanupCandidate:
    """Cleanup result for one workspace."""

    workspace_ref: str
    workspace_path: str
    cleanup_performed: bool
    status: str
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


def build_operation_flow_run_workspace_policy(
    *,
    workspace_root: str | Path,
    retention_policy: str = "keep",
    cleanup_policy: str = "manual",
    max_write_bytes: int = 65536,
) -> OperationFlowRunWorkspacePolicyCandidate:
    """Build a run workspace policy without creating files."""

    return OperationFlowRunWorkspacePolicyCandidate(
        workspace_root=str(Path(workspace_root).expanduser().resolve()),
        retention_policy=retention_policy,
        cleanup_policy=cleanup_policy,
        max_write_bytes=max_write_bytes,
        metadata={
            "candidate_only": False,
            "does_not_access_network": True,
            "workspace_schema_version": OPERATION_FLOW_RUN_WORKSPACE_SCHEMA_VERSION,
        },
    )


def create_operation_flow_run_workspace(
    *,
    policy: OperationFlowRunWorkspacePolicyCandidate,
    workflow_name: str,
    run_id: str,
) -> OperationFlowRunWorkspaceStateCandidate:
    """Create one governed run workspace with standard subdirectories."""

    blocking = _validate_policy(policy)
    workflow_slug = _slug_or_default(workflow_name, "workflow")
    run_slug = _slug_or_default(run_id, "run")
    root = Path(policy.workspace_root).expanduser().resolve()
    workspace_path = (root / workflow_slug / run_slug).resolve()
    if root not in workspace_path.parents and root != workspace_path:
        blocking.append("workspace_path_outside_root")
    if blocking:
        return OperationFlowRunWorkspaceStateCandidate(
            workspace_ref=f"run-workspace://{workflow_slug}/{run_slug}",
            workspace_path=str(workspace_path),
            workflow_name=workflow_slug,
            run_id=run_slug,
            workspace_created=False,
            retention_policy=policy.retention_policy,
            cleanup_policy=policy.cleanup_policy,
            manifest_path=str(workspace_path / "manifest.json"),
            subdirs=tuple(policy.allowed_subdirs),
            blocking_reasons=tuple(_ordered_unique(blocking)),
            metadata={"workspace_schema_version": OPERATION_FLOW_RUN_WORKSPACE_SCHEMA_VERSION},
        )

    workspace_path.mkdir(parents=True, exist_ok=True)
    for subdir in policy.allowed_subdirs:
        (workspace_path / subdir).mkdir(exist_ok=True)
    manifest_path = workspace_path / "manifest.json"
    state = OperationFlowRunWorkspaceStateCandidate(
        workspace_ref=f"run-workspace://{workflow_slug}/{run_slug}",
        workspace_path=str(workspace_path),
        workflow_name=workflow_slug,
        run_id=run_slug,
        workspace_created=True,
        retention_policy=policy.retention_policy,
        cleanup_policy=policy.cleanup_policy,
        manifest_path=str(manifest_path),
        subdirs=tuple(policy.allowed_subdirs),
        metadata={
            "workspace_schema_version": OPERATION_FLOW_RUN_WORKSPACE_SCHEMA_VERSION,
            "workspace_root": str(root),
            "max_write_bytes": policy.max_write_bytes,
        },
    )
    _write_manifest(state, status="created", extra={"writes": []})
    return state


def write_operation_flow_run_workspace_json(
    workspace: OperationFlowRunWorkspaceStateCandidate,
    *,
    relative_path: str,
    payload: Mapping[str, Any],
    kind: str,
    max_write_bytes: int = 65536,
) -> tuple[OperationFlowRunWorkspaceStateCandidate, OperationFlowRunWorkspaceWriteCandidate]:
    """Write bounded JSON into a workspace and attach the produced ref."""

    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return write_operation_flow_run_workspace_text(
        workspace,
        relative_path=relative_path,
        text=text,
        kind=kind,
        max_write_bytes=max_write_bytes,
    )


def write_operation_flow_run_workspace_text(
    workspace: OperationFlowRunWorkspaceStateCandidate,
    *,
    relative_path: str,
    text: str,
    kind: str,
    max_write_bytes: int = 65536,
) -> tuple[OperationFlowRunWorkspaceStateCandidate, OperationFlowRunWorkspaceWriteCandidate]:
    """Write bounded text into a workspace and attach the produced ref."""

    blocking = list(workspace.blocking_reasons)
    warnings: list[str] = []
    if not workspace.workspace_created:
        blocking.append("workspace_not_created")
    resolved = _resolve_workspace_relative_path(workspace, relative_path)
    if resolved is None:
        blocking.append("workspace_relative_path_invalid")
        resolved = Path(workspace.workspace_path) / "blocked"
    encoded = text.encode("utf-8")
    if len(encoded) > max_write_bytes:
        warnings.append("workspace_write_truncated")
        encoded = encoded[:max_write_bytes]
        text = encoded.decode("utf-8", errors="ignore")

    if blocking:
        write_result = OperationFlowRunWorkspaceWriteCandidate(
            ref=_workspace_ref_for(workspace, kind, relative_path),
            path=str(resolved),
            relative_path=relative_path,
            kind=kind,
            bytes_written=0,
            status="blocked",
            blocking_reasons=tuple(_ordered_unique(blocking)),
            warnings=tuple(_ordered_unique(warnings)),
        )
        return workspace, write_result

    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(text, encoding="utf-8")
    ref = _workspace_ref_for(workspace, kind, relative_path)
    workspace = _attach_ref(workspace, kind, ref)
    write_result = OperationFlowRunWorkspaceWriteCandidate(
        ref=ref,
        path=str(resolved),
        relative_path=relative_path,
        kind=kind,
        bytes_written=len(encoded),
        status="succeeded",
        warnings=tuple(_ordered_unique(warnings)),
        metadata={"workspace_schema_version": OPERATION_FLOW_RUN_WORKSPACE_SCHEMA_VERSION},
    )
    return workspace, write_result


def finalize_operation_flow_run_workspace(
    workspace: OperationFlowRunWorkspaceStateCandidate,
    *,
    status: str,
    metadata: Mapping[str, Any] | None = None,
) -> OperationFlowRunWorkspaceStateCandidate:
    """Write the final manifest and return the updated workspace state."""

    finalized = replace(
        workspace,
        metadata={
            **workspace.metadata,
            "final_status": status,
            **dict(metadata or {}),
        },
    )
    if finalized.workspace_created and not finalized.cleanup_performed:
        _write_manifest(finalized, status=status, extra=dict(metadata or {}))
    return finalized


def cleanup_operation_flow_run_workspace(
    workspace: OperationFlowRunWorkspaceStateCandidate,
    *,
    status: str,
) -> tuple[OperationFlowRunWorkspaceStateCandidate, OperationFlowRunWorkspaceCleanupCandidate]:
    """Apply cleanup policy, deleting only the workspace directory when allowed."""

    should_delete = workspace.cleanup_policy == "delete_always" or (
        workspace.cleanup_policy == "delete_on_success" and status == "succeeded"
    )
    if not should_delete:
        cleanup = OperationFlowRunWorkspaceCleanupCandidate(
            workspace_ref=workspace.workspace_ref,
            workspace_path=workspace.workspace_path,
            cleanup_performed=False,
            status="skipped",
            metadata={"cleanup_policy": workspace.cleanup_policy},
        )
        return workspace, cleanup
    if not workspace.workspace_created:
        cleanup = OperationFlowRunWorkspaceCleanupCandidate(
            workspace_ref=workspace.workspace_ref,
            workspace_path=workspace.workspace_path,
            cleanup_performed=False,
            status="blocked",
            blocking_reasons=("workspace_not_created",),
        )
        return workspace, cleanup
    shutil.rmtree(workspace.workspace_path)
    cleaned = replace(workspace, cleanup_performed=True)
    cleanup = OperationFlowRunWorkspaceCleanupCandidate(
        workspace_ref=workspace.workspace_ref,
        workspace_path=workspace.workspace_path,
        cleanup_performed=True,
        status="succeeded",
        metadata={"cleanup_policy": workspace.cleanup_policy},
    )
    return cleaned, cleanup


def operation_flow_run_workspace_status_dict(
    workspace: OperationFlowRunWorkspaceStateCandidate | None,
) -> dict[str, Any] | None:
    """Return a sanitized workspace status dict."""

    if workspace is None:
        return None
    return {
        "workspace_ref": workspace.workspace_ref,
        "workspace_path": workspace.workspace_path,
        "workspace_created": workspace.workspace_created,
        "retention_policy": workspace.retention_policy,
        "cleanup_policy": workspace.cleanup_policy,
        "cleanup_performed": workspace.cleanup_performed,
        "manifest_path": workspace.manifest_path,
        "artifact_refs": list(workspace.artifact_refs),
        "evidence_refs": list(workspace.evidence_refs),
        "result_refs": list(workspace.result_refs),
        "blocking_reasons": list(workspace.blocking_reasons),
        "warnings": list(workspace.warnings),
        "metadata": dict(workspace.metadata),
    }


def _validate_policy(policy: OperationFlowRunWorkspacePolicyCandidate) -> list[str]:
    blocking: list[str] = []
    if policy.retention_policy not in OPERATION_FLOW_RUN_WORKSPACE_RETENTION_POLICIES:
        blocking.append("workspace_retention_policy_invalid")
    if policy.cleanup_policy not in OPERATION_FLOW_RUN_WORKSPACE_CLEANUP_POLICIES:
        blocking.append("workspace_cleanup_policy_invalid")
    if policy.max_write_bytes <= 0:
        blocking.append("workspace_max_write_bytes_invalid")
    if not policy.allowed_subdirs:
        blocking.append("workspace_allowed_subdirs_missing")
    for subdir in policy.allowed_subdirs:
        if "/" in subdir or "\\" in subdir or subdir.startswith("."):
            blocking.append("workspace_allowed_subdir_invalid")
    return blocking


def _resolve_workspace_relative_path(
    workspace: OperationFlowRunWorkspaceStateCandidate,
    relative_path: str,
) -> Path | None:
    path = Path(relative_path)
    parts = path.parts
    if path.is_absolute() or not parts or ".." in parts:
        return None
    if parts[0] not in set(workspace.subdirs):
        return None
    path_text = str(path).lower()
    if any(marker in path_text for marker in OPERATION_FLOW_RUN_WORKSPACE_FORBIDDEN_PATH_MARKERS):
        return None
    root = Path(workspace.workspace_path).resolve()
    resolved = (root / path).resolve()
    if root not in resolved.parents and root != resolved:
        return None
    return resolved


def _write_manifest(
    workspace: OperationFlowRunWorkspaceStateCandidate,
    *,
    status: str,
    extra: Mapping[str, Any],
) -> None:
    payload = {
        "schema_version": OPERATION_FLOW_RUN_WORKSPACE_SCHEMA_VERSION,
        "workspace_ref": workspace.workspace_ref,
        "workspace_path": workspace.workspace_path,
        "workflow_name": workspace.workflow_name,
        "run_id": workspace.run_id,
        "status": status,
        "retention_policy": workspace.retention_policy,
        "cleanup_policy": workspace.cleanup_policy,
        "subdirs": list(workspace.subdirs),
        "artifact_refs": list(workspace.artifact_refs),
        "evidence_refs": list(workspace.evidence_refs),
        "result_refs": list(workspace.result_refs),
        "metadata": dict(workspace.metadata),
        **dict(extra),
    }
    Path(workspace.manifest_path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _attach_ref(
    workspace: OperationFlowRunWorkspaceStateCandidate,
    kind: str,
    ref: str,
) -> OperationFlowRunWorkspaceStateCandidate:
    if kind == "artifact":
        return replace(
            workspace,
            artifact_refs=tuple(_ordered_unique((*workspace.artifact_refs, ref))),
        )
    if kind in {"evidence", "reference"}:
        return replace(
            workspace,
            evidence_refs=tuple(_ordered_unique((*workspace.evidence_refs, ref))),
        )
    if kind == "result":
        return replace(
            workspace,
            result_refs=tuple(_ordered_unique((*workspace.result_refs, ref))),
        )
    return workspace


def _workspace_ref_for(
    workspace: OperationFlowRunWorkspaceStateCandidate,
    kind: str,
    relative_path: str,
) -> str:
    ref_kind = "evidence" if kind == "reference" else kind
    return (
        f"{ref_kind}://run-workspace/{workspace.workflow_name}/"
        f"{workspace.run_id}/{relative_path}"
    )


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
