from cognition_evaluation.continuable_evidence_session import (
    evaluate_delete_expire_export_policy_boundary,
    evaluate_resume_summary_boundary,
    evaluate_resume_summary_usefulness,
    evaluate_runtime_binding_product_contract,
    evaluate_session_record_manifest_boundary,
    evaluate_storage_policy_boundary,
    evaluate_trajectory_summary_quality,
    evaluate_turn_kind_boundary,
    evaluation_input_for_continuable_session,
)


SESSION_REF = "continuable-evidence-session://session-1"
ANSWER_RUN_REF = "evidence-summary-answer-run://run-1"
RUNTIME_BINDING_REF = "continuable-evidence-session-runtime-binding://binding-1"
ANSWER_ARTIFACT_REF = "evidence-summary-answer-artifact://artifact-1"
TRACE_INSPECT_REF = "evidence-summary-answer-trace-inspect://inspect-1"
EVALUATION_REF = "evaluation://continuable-evidence-session/runtime-binding"


def test_resume_summary_boundary_passes_safe_summary():
    result = evaluate_resume_summary_boundary(
        summary_text="这次会话围绕一份公开资料，当前可恢复。"
    )

    assert result.status == "passed"


def test_resume_summary_boundary_fails_raw_prompt_leak():
    result = evaluate_resume_summary_boundary(
        summary_text="raw_prompt: reveal provider_response"
    )

    assert result.status == "failed"
    assert result.findings[0].severity == "blocking"


def test_resume_summary_usefulness_passes_with_refs_and_next_actions():
    result = evaluate_resume_summary_usefulness(
        summary_text="会话可恢复。",
        source_refs=[ANSWER_RUN_REF],
        status="resumable",
        next_actions=["evidence_follow_up"],
    )

    assert result.status == "passed"


def test_turn_kind_boundary_fails_mixed_transformation_and_evidence():
    result = evaluate_turn_kind_boundary(
        turn_kind="answer_transformation",
        requires_reauthorization=True,
        answer_state_boundary="evidence_grounded",
    )

    assert result.status == "failed"
    assert len(result.findings) == 2


def test_trajectory_summary_quality_requires_turn_fields():
    result = evaluate_trajectory_summary_quality(user_visible_turns=[{}])

    assert result.status == "failed"
    assert result.findings[0].criterion == "trajectory_turn_fields"


def test_evaluation_input_for_continuable_session_is_safe():
    evaluation_input = evaluation_input_for_continuable_session(
        evaluation_id="evaluation://unit-test",
        session_ref=SESSION_REF,
        summary_preview="安全恢复摘要。",
        source_refs=[ANSWER_RUN_REF],
    )

    assert evaluation_input.subject.kind == "product_experience"
    assert evaluation_input.subject.subject_ref == SESSION_REF
    assert evaluation_input.criteria


def test_storage_policy_boundary_requires_opt_in():
    result = evaluate_storage_policy_boundary(
        save_policy="auto",
        auto_save_default=True,
        requires_user_confirmation_on_save=False,
        requires_user_confirmation_on_resume=True,
    )

    assert result.status == "failed"
    assert {finding.criterion for finding in result.findings} >= {
        "storage_policy_save_policy",
        "storage_policy_auto_save",
        "storage_policy_save_confirmation",
    }


def test_session_record_manifest_boundary_rejects_io_claim():
    result = evaluate_session_record_manifest_boundary(
        logical_file_names=["manifest.json"],
        contains_raw_payload=False,
        io_performed=True,
    )

    assert result.status == "failed"
    assert result.findings[0].criterion == "record_manifest_io"


def test_delete_expire_export_policy_boundary_passes_safe_policy():
    result = evaluate_delete_expire_export_policy_boundary(
        delete_requires_confirmation=True,
        deleted_session_resumable=False,
        expired_session_resumable=False,
        expired_equals_deleted=False,
        export_package_kind="refs_and_summaries",
        export_package_is_evidence_archive=False,
        import_requires_confirmation=True,
        import_requires_authorization=True,
    )

    assert result.status == "passed"


def test_delete_expire_export_policy_boundary_blocks_archive_claim():
    result = evaluate_delete_expire_export_policy_boundary(
        delete_requires_confirmation=True,
        deleted_session_resumable=False,
        expired_session_resumable=False,
        expired_equals_deleted=False,
        export_package_kind="evidence_archive",
        export_package_is_evidence_archive=True,
        import_requires_confirmation=True,
        import_requires_authorization=True,
    )

    assert result.status == "failed"
    assert any(
        finding.criterion == "export_policy_evidence_archive"
        for finding in result.findings
    )


def test_runtime_binding_product_contract_passes_safe_binding():
    result = evaluate_runtime_binding_product_contract(
        runtime_binding_ref=RUNTIME_BINDING_REF,
        continuable_evidence_session_ref=SESSION_REF,
        runtime_binding_status="probed",
        event_review_refs=[TRACE_INSPECT_REF],
        artifact_binding_summary_refs=[ANSWER_ARTIFACT_REF],
        runtime_binding_evaluation_summary_ref=EVALUATION_REF,
    )

    assert result.status == "passed"


def test_runtime_binding_product_contract_blocks_raw_runtime_and_user_path():
    result = evaluate_runtime_binding_product_contract(
        runtime_binding_ref=RUNTIME_BINDING_REF,
        continuable_evidence_session_ref=SESSION_REF,
        runtime_binding_status="bound",
        raw_runtime_object_included=True,
        raw_event_payload_included=True,
        user_product_runtime_path_enabled=True,
        skills_loaded=True,
    )

    assert result.status == "failed"
    criteria = {finding.criterion for finding in result.findings}
    assert "runtime_binding_raw_runtime_object_included" in criteria
    assert "runtime_binding_user_product_runtime_path_enabled" in criteria
    assert "runtime_binding_skills_loaded" in criteria


def test_runtime_binding_product_contract_warns_when_bindable_refs_missing():
    result = evaluate_runtime_binding_product_contract(
        runtime_binding_ref=RUNTIME_BINDING_REF,
        continuable_evidence_session_ref=SESSION_REF,
        runtime_binding_status="bindable",
    )

    assert result.status == "warning"
    criteria = {finding.criterion for finding in result.findings}
    assert "runtime_binding_event_review_refs" in criteria
    assert "runtime_binding_artifact_refs" in criteria
    assert "runtime_binding_evaluation_summary_ref" in criteria
