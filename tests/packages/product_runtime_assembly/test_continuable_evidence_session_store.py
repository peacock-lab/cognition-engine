from __future__ import annotations

import json

import pytest

from product_runtime_assembly.continuable_evidence_session_store import (
    ContinuableEvidenceSessionLocalStoreRecord,
    delete_continuable_evidence_session_record,
    expire_continuable_evidence_session_records,
    list_continuable_evidence_session_index_entries,
    load_continuable_evidence_session_record_manifest,
    resolve_continuable_evidence_session_store_paths,
    save_continuable_evidence_session_record,
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
    ContinuableEvidenceSessionSchema,
    ContinuableEvidenceSessionSeedSchema,
    ContinuableEvidenceSessionStoragePolicySchema,
    ContinuableEvidenceSessionSummarySchema,
    ContinuableEvidenceSessionTrajectorySchema,
    ContinuableEvidenceSessionTurnSchema,
)


SESSION_ID = "session-1"
SESSION_REF = "continuable-evidence-session://session-1"
SEED_REF = "continuable-evidence-session-seed://seed-1"
TURN_REF = "continuable-evidence-session-turn://turn-1"
SUMMARY_REF = "continuable-evidence-session-summary://summary-1"
INDEX_REF = "continuable-evidence-session-artifact-index://index-1"
TRAJECTORY_REF = "continuable-evidence-session-trajectory://trajectory-1"
ANSWER_RUN_REF = "evidence-summary-answer-run://run-1"
ANSWER_ARTIFACT_REF = "evidence-summary-answer-artifact://artifact-1"
TRACE_INSPECT_REF = "evidence-summary-answer-trace-inspect://inspect-1"
OBS_REF = "evidence-summary-answer-observability-summary://obs-1"
DIGEST_REF = "governed-evidence-digest://digest-1"
EVIDENCE_REF = "evidence://external-readonly/source-1"
STORAGE_POLICY_REF = "policy://continuable-evidence-session/storage/default-v1"
STATE_ROOT_POLICY_REF = "policy://continuable-evidence-session/state-root/default-v1"
RETENTION_POLICY_REF = "policy://continuable-evidence-session/retention/default-v1"
DELETE_POLICY_REF = "policy://continuable-evidence-session/delete/default-v1"
EXPORT_POLICY_REF = "policy://continuable-evidence-session/export/default-v1"
MANIFEST_REF = "policy://continuable-evidence-session/record-manifest/session-1"
CREATED_AT = "2026-05-27T00:00:00Z"
EXPIRES_AT = "2026-05-28T00:00:00Z"


def test_continuable_evidence_session_store_saves_lists_and_loads_manifest(tmp_path):
    state_root = tmp_path / "session-state"
    result = save_continuable_evidence_session_record(
        state_root=state_root,
        record=_record(),
    )

    assert result.session_id == SESSION_ID
    assert (state_root / "index.json").exists()
    assert (state_root / "sessions" / SESSION_ID / "manifest.json").exists()
    assert (state_root / "sessions" / SESSION_ID / "summaries" / "latest.json").exists()
    assert (
        state_root
        / "sessions"
        / SESSION_ID
        / "turns"
        / "0001-evidence_follow_up.json"
    ).exists()
    assert "sessions/session-1/session.json" in result.written_relative_paths

    entries = list_continuable_evidence_session_index_entries(state_root=state_root)
    loaded = load_continuable_evidence_session_record_manifest(
        state_root=state_root,
        session_id=SESSION_ID,
    )

    assert len(entries) == 1
    assert entries[0].continuable_evidence_session_ref == SESSION_REF
    assert entries[0].latest_resume_summary_preview == "会话可恢复，需要用户确认。"
    assert loaded.manifest.record_manifest_ref == MANIFEST_REF


def test_continuable_evidence_session_store_delete_removes_record_and_receipts(tmp_path):
    state_root = tmp_path / "session-state"
    save_continuable_evidence_session_record(state_root=state_root, record=_record())

    result = delete_continuable_evidence_session_record(
        state_root=state_root,
        session_id=SESSION_ID,
        delete_policy=ContinuableEvidenceSessionDeletePolicySchema(
            delete_policy_ref=DELETE_POLICY_REF,
        ),
        deleted_at="2026-05-27T01:00:00Z",
    )

    assert result.deleted is True
    assert result.remaining_index_count == 0
    assert not (state_root / "sessions" / SESSION_ID).exists()
    assert result.receipt_path is not None
    receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
    assert receipt["payload_type"] == "continuable_evidence_session_deletion_receipt"
    assert "continuable_evidence_session_ref" not in receipt


def test_continuable_evidence_session_store_expire_marks_index_and_manifest(tmp_path):
    state_root = tmp_path / "session-state"
    save_continuable_evidence_session_record(state_root=state_root, record=_record())

    result = expire_continuable_evidence_session_records(
        state_root=state_root,
        expiration_policy=ContinuableEvidenceSessionExpirationPolicySchema(
            retention_policy_ref=RETENTION_POLICY_REF,
        ),
        now="2026-05-29T00:00:00Z",
    )
    loaded = load_continuable_evidence_session_record_manifest(
        state_root=state_root,
        session_id=SESSION_ID,
    )

    assert result.expired_session_ids == (SESSION_ID,)
    assert result.index_entries[0].session_status == "expired"
    assert result.index_entries[0].resumable is False
    assert loaded.manifest.record_status == "expired"


def test_continuable_evidence_session_store_rejects_outputs_state_root(tmp_path):
    with pytest.raises(ValueError, match="outputs"):
        resolve_continuable_evidence_session_store_paths(tmp_path / "outputs")


def test_continuable_evidence_session_store_rejects_auto_save_policy(tmp_path):
    record = _record(
        storage_policy=ContinuableEvidenceSessionStoragePolicySchema.model_construct(
            storage_policy_ref=STORAGE_POLICY_REF,
            continuable_evidence_session_ref=SESSION_REF,
            local_state_root_policy_ref=STATE_ROOT_POLICY_REF,
            retention_policy_ref=RETENTION_POLICY_REF,
            delete_policy_ref=DELETE_POLICY_REF,
            export_policy_ref=EXPORT_POLICY_REF,
            auto_save_default=True,
        )
    )

    with pytest.raises(ValueError):
        save_continuable_evidence_session_record(
            state_root=tmp_path / "session-state",
            record=record,
        )


def test_continuable_evidence_session_store_rejects_raw_index_payload(tmp_path):
    record = _record(
        index_entry={
            "session_id": SESSION_ID,
            "continuable_evidence_session_ref": SESSION_REF,
            "session_status": "resumable",
            "created_at": CREATED_AT,
            "updated_at": CREATED_AT,
            "source_scope_summary": "一份外部只读资料。",
            "latest_resume_summary_preview": "full_answer: raw",
            "resumable": True,
        }
    )

    with pytest.raises(ValueError):
        save_continuable_evidence_session_record(
            state_root=tmp_path / "session-state",
            record=record,
        )


def test_continuable_evidence_session_store_does_not_expand_root_surface():
    import product_runtime_assembly

    assert "save_continuable_evidence_session_record" not in product_runtime_assembly.__all__
    assert not hasattr(product_runtime_assembly, "save_continuable_evidence_session_record")


def _record(**overrides):
    values = {
        "storage_policy": ContinuableEvidenceSessionStoragePolicySchema(
            storage_policy_ref=STORAGE_POLICY_REF,
            continuable_evidence_session_ref=SESSION_REF,
            local_state_root_policy_ref=STATE_ROOT_POLICY_REF,
            retention_policy_ref=RETENTION_POLICY_REF,
            delete_policy_ref=DELETE_POLICY_REF,
            export_policy_ref=EXPORT_POLICY_REF,
        ),
        "local_state_root_policy": ContinuableEvidenceSessionLocalStateRootPolicySchema(
            local_state_root_policy_ref=STATE_ROOT_POLICY_REF,
        ),
        "manifest": ContinuableEvidenceSessionRecordManifestSchema(
            record_manifest_ref=MANIFEST_REF,
            continuable_evidence_session_ref=SESSION_REF,
            logical_file_names=[
                "manifest.json",
                "session.json",
                "seed.json",
                "resume-policy.json",
                "artifact-index.json",
                "trajectory.json",
                "summaries/latest.json",
                "turns/0001-evidence_follow_up.json",
            ],
            storage_policy_ref=STORAGE_POLICY_REF,
            local_state_root_policy_ref=STATE_ROOT_POLICY_REF,
            retention_policy_ref=RETENTION_POLICY_REF,
            delete_policy_ref=DELETE_POLICY_REF,
            export_policy_ref=EXPORT_POLICY_REF,
            created_at=CREATED_AT,
            updated_at=CREATED_AT,
            expires_at=EXPIRES_AT,
        ),
        "index_entry": ContinuableEvidenceSessionIndexEntrySchema(
            session_id=SESSION_ID,
            continuable_evidence_session_ref=SESSION_REF,
            session_status="resumable",
            created_at=CREATED_AT,
            updated_at=CREATED_AT,
            expires_at=EXPIRES_AT,
            source_scope_summary="一份外部只读资料。",
            latest_resume_summary_preview="会话可恢复，需要用户确认。",
            turn_count=1,
            evidence_ref_count=1,
            digest_ref_count=1,
            resumable=True,
        ),
        "session": ContinuableEvidenceSessionSchema(
            session_id=SESSION_ID,
            continuable_evidence_session_ref=SESSION_REF,
            session_status="resumable",
            source_answer_run_ref=ANSWER_RUN_REF,
            latest_answer_run_ref=ANSWER_RUN_REF,
            session_seed_ref=SEED_REF,
            session_summary_ref=SUMMARY_REF,
            session_artifact_index_ref=INDEX_REF,
            session_trajectory_ref=TRAJECTORY_REF,
            turn_count=1,
            evidence_ref_count=1,
            digest_ref_count=1,
            created_at=CREATED_AT,
            updated_at=CREATED_AT,
            expires_at=EXPIRES_AT,
            resumable=True,
        ),
        "seed": ContinuableEvidenceSessionSeedSchema(
            seed_id="seed-1",
            session_seed_ref=SEED_REF,
            continuable_evidence_session_ref=SESSION_REF,
            source_request_id="request-1",
            source_answer_run_ref=ANSWER_RUN_REF,
            source_answer_status="success",
            evidence_refs=[{"ref": EVIDENCE_REF, "kind": "evidence"}],
            digest_refs=[DIGEST_REF],
            answer_artifact_ref=ANSWER_ARTIFACT_REF,
            trace_inspect_ref=TRACE_INSPECT_REF,
            observability_summary_ref=OBS_REF,
            resume_summary_ref=SUMMARY_REF,
            seed_source="initial_answer_run",
        ),
        "resume_policy": ContinuableEvidenceSessionResumePolicySchema(
            policy_ref="policy://continuable-evidence-session/resume/default-v1",
            continuable_evidence_session_ref=SESSION_REF,
            resume_allowed=True,
            resume_status="requires_confirmation",
            retention_policy_ref=RETENTION_POLICY_REF,
            export_allowed=True,
        ),
        "artifact_index": ContinuableEvidenceSessionArtifactIndexSchema(
            session_artifact_index_ref=INDEX_REF,
            continuable_evidence_session_ref=SESSION_REF,
            answer_run_refs=[ANSWER_RUN_REF],
            answer_artifact_refs=[ANSWER_ARTIFACT_REF],
            trace_inspect_refs=[TRACE_INSPECT_REF],
            observability_summary_refs=[OBS_REF],
        ),
        "trajectory": ContinuableEvidenceSessionTrajectorySchema(
            session_trajectory_ref=TRAJECTORY_REF,
            continuable_evidence_session_ref=SESSION_REF,
            user_visible_turns=[
                {"turn_kind": "evidence_follow_up", "turn_status": "success"}
            ],
            developer_review_refs=[TRACE_INSPECT_REF],
            evidence_grounded_turn_count=1,
            latest_resume_summary_ref=SUMMARY_REF,
        ),
        "latest_summary": ContinuableEvidenceSessionSummarySchema(
            session_summary_ref=SUMMARY_REF,
            continuable_evidence_session_ref=SESSION_REF,
            summary_kind="resume",
            summary_text="这次会话围绕一份公开资料进行，最近状态为可恢复。",
            source_refs=[ANSWER_RUN_REF, DIGEST_REF],
            evidence_scope_summary="一份外部只读资料。",
            last_user_intent_summary="继续追问。",
            answer_state_boundary="evidence_follow_up",
        ),
        "turns": (
            ContinuableEvidenceSessionTurnSchema(
                turn_id="turn-1",
                session_turn_ref=TURN_REF,
                continuable_evidence_session_ref=SESSION_REF,
                turn_index=1,
                turn_kind="evidence_follow_up",
                turn_status="success",
                input_summary="继续基于同一资料追问。",
                output_summary="返回安全摘要。",
                answer_run_ref=ANSWER_RUN_REF,
                answer_artifact_ref=ANSWER_ARTIFACT_REF,
                trace_inspect_ref=TRACE_INSPECT_REF,
                observability_summary_ref=OBS_REF,
                requires_reauthorization=True,
                created_at=CREATED_AT,
            ),
        ),
        "delete_policy": ContinuableEvidenceSessionDeletePolicySchema(
            delete_policy_ref=DELETE_POLICY_REF,
        ),
        "expiration_policy": ContinuableEvidenceSessionExpirationPolicySchema(
            retention_policy_ref=RETENTION_POLICY_REF,
        ),
        "export_policy": ContinuableEvidenceSessionExportPolicySchema(
            export_policy_ref=EXPORT_POLICY_REF,
        ),
    }
    values.update(overrides)
    return ContinuableEvidenceSessionLocalStoreRecord(**values)
