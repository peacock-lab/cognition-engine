"""Local store for continuable evidence session records.

The store only writes to an explicit caller-provided state root. It does not
resolve platform defaults, read environment variables, or open ADK runtime
storage.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from behavior_contracts.continuable_evidence_session import (
    validate_continuable_evidence_session_guards,
)
from schemas.continuable_evidence_session import (
    ContinuableEvidenceSessionArtifactIndexSchema,
    ContinuableEvidenceSessionDeletePolicySchema,
    ContinuableEvidenceSessionExpirationPolicySchema,
    ContinuableEvidenceSessionExportPolicySchema,
    ContinuableEvidenceSessionIndexEntrySchema,
    ContinuableEvidenceSessionLocalStateRootPolicySchema,
    ContinuableEvidenceSessionRecordManifestSchema,
    ContinuableEvidenceSessionResumePolicySchema,
    ContinuableEvidenceSessionRuntimeVisibleSummarySchema,
    ContinuableEvidenceSessionSchema,
    ContinuableEvidenceSessionSeedSchema,
    ContinuableEvidenceSessionStoragePolicySchema,
    ContinuableEvidenceSessionSummarySchema,
    ContinuableEvidenceSessionTrajectorySchema,
    ContinuableEvidenceSessionTurnSchema,
)


INDEX_PAYLOAD_TYPE = "continuable_evidence_session_index"
INDEX_PAYLOAD_VERSION = "continuable_evidence_session_index_v1"
DELETION_RECEIPT_PAYLOAD_TYPE = "continuable_evidence_session_deletion_receipt"
DELETION_RECEIPT_PAYLOAD_VERSION = "continuable_evidence_session_deletion_receipt_v1"


@dataclass(frozen=True)
class ContinuableEvidenceSessionLocalStorePaths:
    """Resolved paths under an explicit state root."""

    state_root: Path
    index_path: Path
    sessions_dir: Path
    deletion_receipts_dir: Path


@dataclass(frozen=True)
class ContinuableEvidenceSessionLocalStoreRecord:
    """Validated product-level payloads for one local session record."""

    storage_policy: ContinuableEvidenceSessionStoragePolicySchema | dict[str, Any]
    local_state_root_policy: (
        ContinuableEvidenceSessionLocalStateRootPolicySchema | dict[str, Any]
    )
    manifest: ContinuableEvidenceSessionRecordManifestSchema | dict[str, Any]
    index_entry: ContinuableEvidenceSessionIndexEntrySchema | dict[str, Any]
    session: ContinuableEvidenceSessionSchema | dict[str, Any]
    seed: ContinuableEvidenceSessionSeedSchema | dict[str, Any]
    resume_policy: ContinuableEvidenceSessionResumePolicySchema | dict[str, Any]
    artifact_index: ContinuableEvidenceSessionArtifactIndexSchema | dict[str, Any]
    trajectory: ContinuableEvidenceSessionTrajectorySchema | dict[str, Any]
    latest_summary: ContinuableEvidenceSessionSummarySchema | dict[str, Any]
    turns: tuple[ContinuableEvidenceSessionTurnSchema | dict[str, Any], ...]
    delete_policy: ContinuableEvidenceSessionDeletePolicySchema | dict[str, Any]
    expiration_policy: ContinuableEvidenceSessionExpirationPolicySchema | dict[str, Any]
    export_policy: ContinuableEvidenceSessionExportPolicySchema | dict[str, Any]
    runtime_visible_summary: (
        ContinuableEvidenceSessionRuntimeVisibleSummarySchema | dict[str, Any] | None
    ) = None


@dataclass(frozen=True)
class ContinuableEvidenceSessionLocalStoreResult:
    """Result of saving one local session record."""

    session_id: str
    session_dir: Path
    written_relative_paths: tuple[str, ...]
    index_entry: ContinuableEvidenceSessionIndexEntrySchema
    manifest: ContinuableEvidenceSessionRecordManifestSchema


@dataclass(frozen=True)
class ContinuableEvidenceSessionLocalStoreLoadResult:
    """Result of loading one local session manifest."""

    session_id: str
    manifest: ContinuableEvidenceSessionRecordManifestSchema
    manifest_path: Path


@dataclass(frozen=True)
class ContinuableEvidenceSessionLocalStoreDeleteResult:
    """Result of deleting one local session record."""

    session_id: str
    deleted: bool
    receipt_path: Path | None
    remaining_index_count: int


@dataclass(frozen=True)
class ContinuableEvidenceSessionLocalStoreExpireResult:
    """Result of marking expired sessions in the local index."""

    expired_session_ids: tuple[str, ...]
    index_entries: tuple[ContinuableEvidenceSessionIndexEntrySchema, ...]


def resolve_continuable_evidence_session_store_paths(
    state_root: str | Path,
) -> ContinuableEvidenceSessionLocalStorePaths:
    """Resolve local store paths under an explicit state root."""

    root = Path(state_root)
    _validate_state_root(root)
    return ContinuableEvidenceSessionLocalStorePaths(
        state_root=root,
        index_path=root / "index.json",
        sessions_dir=root / "sessions",
        deletion_receipts_dir=root / "receipts" / "deletion",
    )


def save_continuable_evidence_session_record(
    *,
    state_root: str | Path,
    record: ContinuableEvidenceSessionLocalStoreRecord,
) -> ContinuableEvidenceSessionLocalStoreResult:
    """Save one validated continuable evidence session record."""

    paths = resolve_continuable_evidence_session_store_paths(state_root)
    validated = _validate_record(record)
    session_id = _safe_session_id(validated.index_entry.session_id)
    if session_id != validated.session.session_id:
        raise ValueError("index entry and session must share session_id.")
    _assert_same_session_ref(validated)
    session_dir = paths.sessions_dir / session_id
    summaries_dir = session_dir / "summaries"
    turns_dir = session_dir / "turns"
    paths.sessions_dir.mkdir(parents=True, exist_ok=True)
    paths.deletion_receipts_dir.mkdir(parents=True, exist_ok=True)
    summaries_dir.mkdir(parents=True, exist_ok=True)
    turns_dir.mkdir(parents=True, exist_ok=True)

    turn_files = tuple(
        (
            turns_dir / f"{turn.turn_index:04d}-{_safe_file_stem(turn.turn_kind)}.json",
            turn,
        )
        for turn in validated.turns
    )
    runtime_visible_summary_payloads: tuple[tuple[Path, Any], ...] = (
        (
            (summaries_dir / "runtime-visible.json", validated.runtime_visible_summary),
        )
        if validated.runtime_visible_summary is not None
        else ()
    )
    payloads: tuple[tuple[Path, Any], ...] = (
        (session_dir / "manifest.json", validated.manifest),
        (session_dir / "session.json", validated.session),
        (session_dir / "seed.json", validated.seed),
        (session_dir / "resume-policy.json", validated.resume_policy),
        (session_dir / "artifact-index.json", validated.artifact_index),
        (session_dir / "trajectory.json", validated.trajectory),
        (summaries_dir / "latest.json", validated.latest_summary),
        *runtime_visible_summary_payloads,
        *turn_files,
    )
    for path, payload in payloads:
        _atomic_write_json(path, _to_json_payload(payload))

    entries = [
        item
        for item in _read_index_entries(paths.index_path)
        if item.session_id != session_id
    ]
    entries.append(validated.index_entry)
    _write_index(paths.index_path, entries)
    return ContinuableEvidenceSessionLocalStoreResult(
        session_id=session_id,
        session_dir=session_dir,
        written_relative_paths=tuple(
            str(path.relative_to(paths.state_root)) for path, _ in payloads
        ),
        index_entry=validated.index_entry,
        manifest=validated.manifest,
    )


def list_continuable_evidence_session_index_entries(
    *,
    state_root: str | Path,
) -> tuple[ContinuableEvidenceSessionIndexEntrySchema, ...]:
    """List validated safe index entries from the explicit state root."""

    paths = resolve_continuable_evidence_session_store_paths(state_root)
    return tuple(_read_index_entries(paths.index_path))


def load_continuable_evidence_session_record_manifest(
    *,
    state_root: str | Path,
    session_id: str,
) -> ContinuableEvidenceSessionLocalStoreLoadResult:
    """Load and validate one local session record manifest."""

    paths = resolve_continuable_evidence_session_store_paths(state_root)
    safe_session_id = _safe_session_id(session_id)
    manifest_path = paths.sessions_dir / safe_session_id / "manifest.json"
    manifest = ContinuableEvidenceSessionRecordManifestSchema.model_validate(
        _read_json(manifest_path)
    )
    result = validate_continuable_evidence_session_guards(
        manifest.model_dump(mode="python")
    )
    if not result.passed:
        raise ValueError(f"guard violations: {', '.join(result.violations)}")
    return ContinuableEvidenceSessionLocalStoreLoadResult(
        session_id=safe_session_id,
        manifest=manifest,
        manifest_path=manifest_path,
    )


def delete_continuable_evidence_session_record(
    *,
    state_root: str | Path,
    session_id: str,
    delete_policy: ContinuableEvidenceSessionDeletePolicySchema | dict[str, Any],
    deleted_at: str,
    reason_category: str = "user_requested",
) -> ContinuableEvidenceSessionLocalStoreDeleteResult:
    """Delete one session directory and remove it from the resumable index."""

    paths = resolve_continuable_evidence_session_store_paths(state_root)
    policy = _validate_payload(
        delete_policy,
        ContinuableEvidenceSessionDeletePolicySchema,
    )
    if not policy.delete_allowed:
        raise ValueError("delete policy does not allow deletion.")
    _validate_timestamp(deleted_at, field_name="deleted_at")
    _validate_safe_scalar(reason_category, field_name="reason_category")
    safe_session_id = _safe_session_id(session_id)
    session_dir = paths.sessions_dir / safe_session_id
    deleted = session_dir.exists()
    if deleted:
        shutil.rmtree(session_dir)
    entries = [
        item
        for item in _read_index_entries(paths.index_path)
        if item.session_id != safe_session_id
    ]
    _write_index(paths.index_path, entries)
    receipt_path: Path | None = None
    if policy.deletion_receipt_allowed:
        paths.deletion_receipts_dir.mkdir(parents=True, exist_ok=True)
        receipt_path = paths.deletion_receipts_dir / f"{safe_session_id}.json"
        _atomic_write_json(
            receipt_path,
            {
                "payload_type": DELETION_RECEIPT_PAYLOAD_TYPE,
                "payload_version": DELETION_RECEIPT_PAYLOAD_VERSION,
                "session_id": safe_session_id,
                "deleted_at": deleted_at,
                "delete_policy_ref": policy.delete_policy_ref,
                "reason_category": reason_category,
            },
        )
    return ContinuableEvidenceSessionLocalStoreDeleteResult(
        session_id=safe_session_id,
        deleted=deleted,
        receipt_path=receipt_path,
        remaining_index_count=len(entries),
    )


def expire_continuable_evidence_session_records(
    *,
    state_root: str | Path,
    expiration_policy: ContinuableEvidenceSessionExpirationPolicySchema | dict[str, Any],
    now: str,
) -> ContinuableEvidenceSessionLocalStoreExpireResult:
    """Mark expired sessions as non-resumable without deleting local records."""

    paths = resolve_continuable_evidence_session_store_paths(state_root)
    _validate_payload(
        expiration_policy,
        ContinuableEvidenceSessionExpirationPolicySchema,
    )
    now_dt = _validate_timestamp(now, field_name="now")
    expired_ids: list[str] = []
    updated_entries: list[ContinuableEvidenceSessionIndexEntrySchema] = []
    for entry in _read_index_entries(paths.index_path):
        expires_at = _parse_optional_timestamp(entry.expires_at)
        if expires_at and expires_at <= now_dt and entry.session_status != "deleted":
            expired_entry = entry.model_copy(
                update={
                    "session_status": "expired",
                    "resumable": False,
                    "updated_at": now,
                }
            )
            expired_entry = ContinuableEvidenceSessionIndexEntrySchema.model_validate(
                expired_entry.model_dump(mode="python")
            )
            expired_ids.append(entry.session_id)
            _mark_manifest_expired(paths, entry.session_id, now)
            updated_entries.append(expired_entry)
        else:
            updated_entries.append(entry)
    _write_index(paths.index_path, updated_entries)
    return ContinuableEvidenceSessionLocalStoreExpireResult(
        expired_session_ids=tuple(expired_ids),
        index_entries=tuple(updated_entries),
    )


@dataclass(frozen=True)
class _ValidatedRecord:
    storage_policy: ContinuableEvidenceSessionStoragePolicySchema
    local_state_root_policy: ContinuableEvidenceSessionLocalStateRootPolicySchema
    manifest: ContinuableEvidenceSessionRecordManifestSchema
    index_entry: ContinuableEvidenceSessionIndexEntrySchema
    session: ContinuableEvidenceSessionSchema
    seed: ContinuableEvidenceSessionSeedSchema
    resume_policy: ContinuableEvidenceSessionResumePolicySchema
    artifact_index: ContinuableEvidenceSessionArtifactIndexSchema
    trajectory: ContinuableEvidenceSessionTrajectorySchema
    latest_summary: ContinuableEvidenceSessionSummarySchema
    turns: tuple[ContinuableEvidenceSessionTurnSchema, ...]
    delete_policy: ContinuableEvidenceSessionDeletePolicySchema
    expiration_policy: ContinuableEvidenceSessionExpirationPolicySchema
    export_policy: ContinuableEvidenceSessionExportPolicySchema
    runtime_visible_summary: ContinuableEvidenceSessionRuntimeVisibleSummarySchema | None


def _validate_record(
    record: ContinuableEvidenceSessionLocalStoreRecord,
) -> _ValidatedRecord:
    validated = _ValidatedRecord(
        storage_policy=_validate_payload(
            record.storage_policy,
            ContinuableEvidenceSessionStoragePolicySchema,
        ),
        local_state_root_policy=_validate_payload(
            record.local_state_root_policy,
            ContinuableEvidenceSessionLocalStateRootPolicySchema,
        ),
        manifest=_validate_payload(
            record.manifest,
            ContinuableEvidenceSessionRecordManifestSchema,
        ),
        index_entry=_validate_payload(
            record.index_entry,
            ContinuableEvidenceSessionIndexEntrySchema,
        ),
        session=_validate_payload(record.session, ContinuableEvidenceSessionSchema),
        seed=_validate_payload(record.seed, ContinuableEvidenceSessionSeedSchema),
        resume_policy=_validate_payload(
            record.resume_policy,
            ContinuableEvidenceSessionResumePolicySchema,
        ),
        artifact_index=_validate_payload(
            record.artifact_index,
            ContinuableEvidenceSessionArtifactIndexSchema,
        ),
        trajectory=_validate_payload(
            record.trajectory,
            ContinuableEvidenceSessionTrajectorySchema,
        ),
        latest_summary=_validate_payload(
            record.latest_summary,
            ContinuableEvidenceSessionSummarySchema,
        ),
        turns=tuple(
            _validate_payload(turn, ContinuableEvidenceSessionTurnSchema)
            for turn in record.turns
        ),
        delete_policy=_validate_payload(
            record.delete_policy,
            ContinuableEvidenceSessionDeletePolicySchema,
        ),
        expiration_policy=_validate_payload(
            record.expiration_policy,
            ContinuableEvidenceSessionExpirationPolicySchema,
        ),
        export_policy=_validate_payload(
            record.export_policy,
            ContinuableEvidenceSessionExportPolicySchema,
        ),
        runtime_visible_summary=(
            _validate_payload(
                record.runtime_visible_summary,
                ContinuableEvidenceSessionRuntimeVisibleSummarySchema,
            )
            if record.runtime_visible_summary is not None
            else None
        ),
    )
    if not validated.storage_policy.local_store_allowed:
        raise ValueError("storage policy does not allow local store.")
    if not validated.turns:
        raise ValueError("local store record requires turns.")
    return validated


def _validate_payload(value: Any, model_type: type[Any]) -> Any:
    model = model_type.model_validate(value)
    result = validate_continuable_evidence_session_guards(model.model_dump(mode="python"))
    if not result.passed:
        raise ValueError(f"guard violations: {', '.join(result.violations)}")
    return model


def _assert_same_session_ref(record: _ValidatedRecord) -> None:
    session_ref = record.session.continuable_evidence_session_ref
    for field_name, value in (
        ("storage_policy", record.storage_policy.continuable_evidence_session_ref),
        ("manifest", record.manifest.continuable_evidence_session_ref),
        ("index_entry", record.index_entry.continuable_evidence_session_ref),
        ("seed", record.seed.continuable_evidence_session_ref),
        ("resume_policy", record.resume_policy.continuable_evidence_session_ref),
        ("artifact_index", record.artifact_index.continuable_evidence_session_ref),
        ("trajectory", record.trajectory.continuable_evidence_session_ref),
        ("latest_summary", record.latest_summary.continuable_evidence_session_ref),
        (
            "runtime_visible_summary",
            (
                record.runtime_visible_summary.continuable_evidence_session_ref
                if record.runtime_visible_summary is not None
                else session_ref
            ),
        ),
    ):
        if value != session_ref:
            raise ValueError(f"{field_name} has a mismatched session ref.")
    for turn in record.turns:
        if turn.continuable_evidence_session_ref != session_ref:
            raise ValueError("turn has a mismatched session ref.")


def _read_index_entries(
    index_path: Path,
) -> list[ContinuableEvidenceSessionIndexEntrySchema]:
    if not index_path.exists():
        return []
    payload = _read_json(index_path)
    if payload.get("payload_type") != INDEX_PAYLOAD_TYPE:
        raise ValueError("invalid session index payload_type.")
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError("session index entries must be a list.")
    return [
        ContinuableEvidenceSessionIndexEntrySchema.model_validate(entry)
        for entry in entries
    ]


def _write_index(
    index_path: Path,
    entries: list[ContinuableEvidenceSessionIndexEntrySchema],
) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    validated_entries = [
        ContinuableEvidenceSessionIndexEntrySchema.model_validate(
            entry.model_dump(mode="python")
        )
        for entry in entries
    ]
    _atomic_write_json(
        index_path,
        {
            "payload_type": INDEX_PAYLOAD_TYPE,
            "payload_version": INDEX_PAYLOAD_VERSION,
            "entries": [
                entry.model_dump(mode="json", exclude_none=True)
                for entry in validated_entries
            ],
        },
    )


def _mark_manifest_expired(
    paths: ContinuableEvidenceSessionLocalStorePaths,
    session_id: str,
    now: str,
) -> None:
    manifest_path = paths.sessions_dir / _safe_session_id(session_id) / "manifest.json"
    if not manifest_path.exists():
        return
    manifest = ContinuableEvidenceSessionRecordManifestSchema.model_validate(
        _read_json(manifest_path)
    )
    expired_manifest = manifest.model_copy(
        update={"record_status": "expired", "updated_at": now}
    )
    expired_manifest = ContinuableEvidenceSessionRecordManifestSchema.model_validate(
        expired_manifest.model_dump(mode="python")
    )
    _atomic_write_json(manifest_path, _to_json_payload(expired_manifest))


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object.")
    return payload


def _to_json_payload(value: Any) -> dict[str, Any]:
    payload = value.model_dump(mode="json", exclude_none=True)
    if not isinstance(payload, dict):
        raise ValueError("payload must serialize to a JSON object.")
    return payload


def _validate_state_root(root: Path) -> None:
    if not str(root):
        raise ValueError("state_root is required.")
    if any(part in {"", ".", ".."} for part in root.parts):
        raise ValueError("state_root must not contain empty or parent parts.")
    if any(part == "outputs" for part in root.parts):
        raise ValueError("state_root must not use repo outputs.")


def _safe_session_id(value: str) -> str:
    _validate_safe_scalar(value, field_name="session_id")
    if "/" in value or "\\" in value or value in {"", ".", ".."} or ".." in value:
        raise ValueError("session_id must be a safe local directory name.")
    return value


def _safe_file_stem(value: str) -> str:
    _validate_safe_scalar(value, field_name="file_stem")
    return value.replace(" ", "_").replace("/", "_").replace("\\", "_")


def _validate_safe_scalar(value: str, *, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank.")
    normalized = value.lower()
    for marker in (
        "api_key",
        "authorization:",
        "bearer ",
        "cookie:",
        "full_answer",
        "provider_response",
        "raw_prompt",
        "raw provider",
        "secret",
        "system_prompt",
        "token",
        "traceback",
    ):
        if marker in normalized:
            raise ValueError(f"{field_name} contains forbidden marker.")


def _validate_timestamp(value: str, *, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO timestamp.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _parse_optional_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None
    return _validate_timestamp(value, field_name="expires_at")


__all__ = (
    "ContinuableEvidenceSessionLocalStoreDeleteResult",
    "ContinuableEvidenceSessionLocalStoreExpireResult",
    "ContinuableEvidenceSessionLocalStoreLoadResult",
    "ContinuableEvidenceSessionLocalStorePaths",
    "ContinuableEvidenceSessionLocalStoreRecord",
    "ContinuableEvidenceSessionLocalStoreResult",
    "delete_continuable_evidence_session_record",
    "expire_continuable_evidence_session_records",
    "list_continuable_evidence_session_index_entries",
    "load_continuable_evidence_session_record_manifest",
    "resolve_continuable_evidence_session_store_paths",
    "save_continuable_evidence_session_record",
)
