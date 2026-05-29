import pytest

from schemas.continuable_evidence_session import (
    ContinuableEvidenceSessionArtifactIndexSchema,
    ContinuableEvidenceSessionDeletePolicySchema,
    ContinuableEvidenceSessionExpirationPolicySchema,
    ContinuableEvidenceSessionExportPolicySchema,
    ContinuableEvidenceSessionIndexEntrySchema,
    ContinuableEvidenceSessionLocalStateRootPolicySchema,
    ContinuableEvidenceSessionResumePolicySchema,
    ContinuableEvidenceSessionRuntimeBindingSchema,
    ContinuableEvidenceSessionRuntimeVisibleSummarySchema,
    ContinuableEvidenceSessionRecordManifestSchema,
    ContinuableEvidenceSessionSchema,
    ContinuableEvidenceSessionSeedSchema,
    ContinuableEvidenceSessionStoragePolicySchema,
    ContinuableEvidenceSessionSummarySchema,
    ContinuableEvidenceSessionTrajectorySchema,
    ContinuableEvidenceSessionTurnSchema,
)


SESSION_REF = "continuable-evidence-session://session-1"
SEED_REF = "continuable-evidence-session-seed://seed-1"
TURN_REF = "continuable-evidence-session-turn://turn-1"
SUMMARY_REF = "continuable-evidence-session-summary://summary-1"
INDEX_REF = "continuable-evidence-session-artifact-index://index-1"
TRAJECTORY_REF = "continuable-evidence-session-trajectory://trajectory-1"
RUNTIME_BINDING_REF = "continuable-evidence-session-runtime-binding://binding-1"
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
EVALUATION_REF = "evaluation://continuable-evidence-session/runtime-binding"


def test_continuable_evidence_session_minimal_contracts_validate():
    session = ContinuableEvidenceSessionSchema(
        session_id="session-1",
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
        created_at="2026-05-27T00:00:00Z",
        updated_at="2026-05-27T00:00:00Z",
        resumable=True,
    )
    seed = ContinuableEvidenceSessionSeedSchema(
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
    )
    turn = ContinuableEvidenceSessionTurnSchema(
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
        created_at="2026-05-27T00:00:00Z",
    )
    summary = ContinuableEvidenceSessionSummarySchema(
        session_summary_ref=SUMMARY_REF,
        continuable_evidence_session_ref=SESSION_REF,
        summary_kind="resume",
        summary_text="这次会话围绕一份公开资料进行，最近状态为可恢复。",
        source_refs=[ANSWER_RUN_REF, DIGEST_REF],
        evidence_scope_summary="一份外部只读资料。",
        last_user_intent_summary="继续追问。",
        answer_state_boundary="evidence_follow_up",
    )
    index = ContinuableEvidenceSessionArtifactIndexSchema(
        session_artifact_index_ref=INDEX_REF,
        continuable_evidence_session_ref=SESSION_REF,
        answer_run_refs=[ANSWER_RUN_REF],
        answer_artifact_refs=[ANSWER_ARTIFACT_REF],
        trace_inspect_refs=[TRACE_INSPECT_REF],
        observability_summary_refs=[OBS_REF],
    )
    policy = ContinuableEvidenceSessionResumePolicySchema(
        policy_ref="policy://continuable-evidence-session/resume/default-v1",
        continuable_evidence_session_ref=SESSION_REF,
        resume_allowed=True,
        resume_status="requires_confirmation",
        retention_policy_ref="policy://continuable-evidence-session/retention/default-v1",
        export_allowed=True,
    )
    trajectory = ContinuableEvidenceSessionTrajectorySchema(
        session_trajectory_ref=TRAJECTORY_REF,
        continuable_evidence_session_ref=SESSION_REF,
        user_visible_turns=[
            {"turn_kind": "evidence_follow_up", "turn_status": "success"}
        ],
        developer_review_refs=[TRACE_INSPECT_REF],
        evidence_grounded_turn_count=1,
        latest_resume_summary_ref=SUMMARY_REF,
    )

    assert session.runtime_backed is False
    assert seed.requires_user_confirmation_on_resume is True
    assert turn.turn_kind == "evidence_follow_up"
    assert summary.source_refs == [ANSWER_RUN_REF, DIGEST_REF]
    assert index.artifact_service_binding_refs == []
    assert policy.resume_allowed is True
    assert trajectory.user_visible_turns


def test_continuable_evidence_session_rejects_invalid_ref_prefix():
    with pytest.raises(ValueError):
        ContinuableEvidenceSessionSchema(
            session_id="session-1",
            continuable_evidence_session_ref="adk-session://raw",
            session_status="created",
            source_answer_run_ref=ANSWER_RUN_REF,
            session_seed_ref=SEED_REF,
            created_at="2026-05-27T00:00:00Z",
            updated_at="2026-05-27T00:00:00Z",
        )


def test_continuable_evidence_session_rejects_runtime_claim():
    with pytest.raises(ValueError):
        ContinuableEvidenceSessionSchema(
            session_id="session-1",
            continuable_evidence_session_ref=SESSION_REF,
            session_status="created",
            source_answer_run_ref=ANSWER_RUN_REF,
            session_seed_ref=SEED_REF,
            created_at="2026-05-27T00:00:00Z",
            updated_at="2026-05-27T00:00:00Z",
            backed_by_adk_session=True,
        )


def test_continuable_evidence_summary_requires_source_refs():
    with pytest.raises(ValueError):
        ContinuableEvidenceSessionSummarySchema(
            session_summary_ref=SUMMARY_REF,
            continuable_evidence_session_ref=SESSION_REF,
            summary_kind="resume",
            summary_text="恢复摘要。",
            source_refs=[],
        )


def test_continuable_evidence_artifact_index_rejects_raw_body():
    with pytest.raises(ValueError):
        ContinuableEvidenceSessionArtifactIndexSchema(
            session_artifact_index_ref=INDEX_REF,
            continuable_evidence_session_ref=SESSION_REF,
            answer_run_refs=[ANSWER_RUN_REF],
            metadata={"artifact_body": "raw answer"},
        )


def test_continuable_evidence_storage_policy_contracts_validate():
    storage_policy = ContinuableEvidenceSessionStoragePolicySchema(
        storage_policy_ref=STORAGE_POLICY_REF,
        continuable_evidence_session_ref=SESSION_REF,
        local_state_root_policy_ref=STATE_ROOT_POLICY_REF,
        retention_policy_ref=RETENTION_POLICY_REF,
        delete_policy_ref=DELETE_POLICY_REF,
        export_policy_ref=EXPORT_POLICY_REF,
    )
    state_root_policy = ContinuableEvidenceSessionLocalStateRootPolicySchema(
        local_state_root_policy_ref=STATE_ROOT_POLICY_REF,
    )
    manifest = ContinuableEvidenceSessionRecordManifestSchema(
        record_manifest_ref=MANIFEST_REF,
        continuable_evidence_session_ref=SESSION_REF,
        logical_file_names=[
            "manifest.json",
            "session.json",
            "seed.json",
            "resume-policy.json",
            "artifact-index.json",
        ],
        storage_policy_ref=STORAGE_POLICY_REF,
        local_state_root_policy_ref=STATE_ROOT_POLICY_REF,
        retention_policy_ref=RETENTION_POLICY_REF,
        delete_policy_ref=DELETE_POLICY_REF,
        export_policy_ref=EXPORT_POLICY_REF,
        created_at="2026-05-27T00:00:00Z",
        updated_at="2026-05-27T00:00:00Z",
    )
    index_entry = ContinuableEvidenceSessionIndexEntrySchema(
        session_id="session-1",
        continuable_evidence_session_ref=SESSION_REF,
        session_status="resumable",
        created_at="2026-05-27T00:00:00Z",
        updated_at="2026-05-27T00:00:00Z",
        source_scope_summary="一份外部只读资料。",
        latest_resume_summary_preview="会话可恢复，需要用户确认。",
        turn_count=1,
        evidence_ref_count=1,
        digest_ref_count=1,
        resumable=True,
    )
    delete_policy = ContinuableEvidenceSessionDeletePolicySchema(
        delete_policy_ref=DELETE_POLICY_REF,
    )
    expiration_policy = ContinuableEvidenceSessionExpirationPolicySchema(
        retention_policy_ref=RETENTION_POLICY_REF,
    )
    export_policy = ContinuableEvidenceSessionExportPolicySchema(
        export_policy_ref=EXPORT_POLICY_REF,
    )

    assert storage_policy.auto_save_default is False
    assert state_root_policy.uses_repo_outputs is False
    assert manifest.io_performed is False
    assert index_entry.resumable is True
    assert delete_policy.deleted_session_resumable is False
    assert expiration_policy.default_retention_days == 30
    assert export_policy.export_package_kind == "refs_and_summaries"


def test_continuable_evidence_storage_policy_rejects_auto_save():
    with pytest.raises(ValueError):
        ContinuableEvidenceSessionStoragePolicySchema(
            storage_policy_ref=STORAGE_POLICY_REF,
            continuable_evidence_session_ref=SESSION_REF,
            local_state_root_policy_ref=STATE_ROOT_POLICY_REF,
            retention_policy_ref=RETENTION_POLICY_REF,
            delete_policy_ref=DELETE_POLICY_REF,
            export_policy_ref=EXPORT_POLICY_REF,
            auto_save_default=True,
        )


def test_continuable_evidence_local_state_root_rejects_repo_outputs():
    with pytest.raises(ValueError):
        ContinuableEvidenceSessionLocalStateRootPolicySchema(
            local_state_root_policy_ref=STATE_ROOT_POLICY_REF,
            uses_repo_outputs=True,
        )


def test_continuable_evidence_record_manifest_rejects_io_claim():
    with pytest.raises(ValueError):
        ContinuableEvidenceSessionRecordManifestSchema(
            record_manifest_ref=MANIFEST_REF,
            continuable_evidence_session_ref=SESSION_REF,
            logical_file_names=["manifest.json"],
            storage_policy_ref=STORAGE_POLICY_REF,
            local_state_root_policy_ref=STATE_ROOT_POLICY_REF,
            retention_policy_ref=RETENTION_POLICY_REF,
            delete_policy_ref=DELETE_POLICY_REF,
            export_policy_ref=EXPORT_POLICY_REF,
            created_at="2026-05-27T00:00:00Z",
            updated_at="2026-05-27T00:00:00Z",
            io_performed=True,
        )


def test_continuable_evidence_index_entry_rejects_full_answer():
    with pytest.raises(ValueError):
        ContinuableEvidenceSessionIndexEntrySchema(
            session_id="session-1",
            continuable_evidence_session_ref=SESSION_REF,
            session_status="resumable",
            created_at="2026-05-27T00:00:00Z",
            updated_at="2026-05-27T00:00:00Z",
            source_scope_summary="一份外部只读资料。",
            latest_resume_summary_preview="full_answer: raw",
            resumable=True,
        )


def test_continuable_evidence_export_policy_rejects_evidence_archive():
    with pytest.raises(ValueError):
        ContinuableEvidenceSessionExportPolicySchema(
            export_policy_ref=EXPORT_POLICY_REF,
            export_package_is_evidence_archive=True,
        )


def test_continuable_evidence_runtime_binding_contract_validates():
    binding = ContinuableEvidenceSessionRuntimeBindingSchema(
        runtime_binding_ref=RUNTIME_BINDING_REF,
        continuable_evidence_session_ref=SESSION_REF,
        runtime_binding_status="probed",
        runtime_binding_summary_ref=SUMMARY_REF,
        agent_binding_ref=RUNTIME_BINDING_REF,
        session_binding_ref=RUNTIME_BINDING_REF,
        event_review_refs=[TRACE_INSPECT_REF],
        artifact_binding_summary_refs=[ANSWER_ARTIFACT_REF],
        runtime_binding_evaluation_summary_ref=EVALUATION_REF,
    )

    assert binding.runtime_binding_scope == "agent_session_event_artifactservice"
    assert binding.raw_runtime_object_included is False
    assert binding.user_product_runtime_path_enabled is False


def test_continuable_evidence_runtime_binding_rejects_raw_runtime_claim():
    with pytest.raises(ValueError):
        ContinuableEvidenceSessionRuntimeBindingSchema(
            runtime_binding_ref=RUNTIME_BINDING_REF,
            continuable_evidence_session_ref=SESSION_REF,
            runtime_binding_status="bound",
            raw_runtime_object_included=True,
        )


def test_continuable_evidence_runtime_binding_rejects_user_path_claim():
    with pytest.raises(ValueError):
        ContinuableEvidenceSessionRuntimeBindingSchema(
            runtime_binding_ref=RUNTIME_BINDING_REF,
            continuable_evidence_session_ref=SESSION_REF,
            runtime_binding_status="bindable",
            user_product_runtime_path_enabled=True,
        )


def test_continuable_evidence_runtime_binding_rejects_raw_event_payload_key():
    with pytest.raises(ValueError):
        ContinuableEvidenceSessionRuntimeBindingSchema(
            runtime_binding_ref=RUNTIME_BINDING_REF,
            continuable_evidence_session_ref=SESSION_REF,
            metadata={"raw_event_payload": "raw"},
        )


def test_continuable_evidence_runtime_visible_summary_contract_validates():
    summary = ContinuableEvidenceSessionRuntimeVisibleSummarySchema(
        runtime_visible_summary_ref=SUMMARY_REF,
        continuable_evidence_session_ref=SESSION_REF,
        runtime_binding_ref=RUNTIME_BINDING_REF,
        runtime_binding_status="probed",
        runtime_availability_hint=(
            "已形成内部 runtime binding 安全摘要；用户 runtime 路径尚未打开。"
        ),
        trajectory_summary={
            "turn_count": 1,
            "latest_status": "success",
            "event_review_ref_count": 1,
        },
        artifact_index=[
            {
                "ref": ANSWER_ARTIFACT_REF,
                "kind": "answer_artifact",
                "purpose": "runtime_binding_user_visible_artifact_index",
            }
        ],
        evaluation_summary_ref=EVALUATION_REF,
        evaluation_status="passed",
        next_actions=["进入产品入口体验验收前，先让用户可见摘要稳定。"],
    )

    assert summary.runtime_binding_status == "probed"
    assert summary.user_product_runtime_path_enabled is False
    assert summary.artifact_index[0].ref == ANSWER_ARTIFACT_REF


def test_continuable_evidence_runtime_visible_summary_rejects_runtime_claims():
    with pytest.raises(ValueError):
        ContinuableEvidenceSessionRuntimeVisibleSummarySchema(
            runtime_visible_summary_ref=SUMMARY_REF,
            continuable_evidence_session_ref=SESSION_REF,
            runtime_availability_hint="runtime path opened",
            artifact_index=[{"ref": ANSWER_ARTIFACT_REF}],
            user_product_runtime_path_enabled=True,
        )


def test_continuable_evidence_runtime_visible_summary_rejects_raw_artifact_body():
    with pytest.raises(ValueError):
        ContinuableEvidenceSessionRuntimeVisibleSummarySchema(
            runtime_visible_summary_ref=SUMMARY_REF,
            continuable_evidence_session_ref=SESSION_REF,
            runtime_availability_hint="内部摘要可用。",
            artifact_index=[{"ref": ANSWER_ARTIFACT_REF}],
            metadata={"artifact_body": "raw"},
        )
