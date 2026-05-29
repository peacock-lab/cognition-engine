from behavior_contracts.continuable_evidence_session import (
    guard_continuable_evidence_session_artifact_index,
    guard_continuable_evidence_session_delete_policy,
    guard_continuable_evidence_session_export_policy,
    guard_continuable_evidence_session_local_state_root_policy,
    guard_continuable_evidence_session_raw_boundary,
    guard_continuable_evidence_session_record_manifest,
    guard_continuable_evidence_session_resume_policy,
    guard_continuable_evidence_session_runtime_binding,
    guard_continuable_evidence_session_runtime_claims,
    guard_continuable_evidence_session_runtime_visible_summary,
    guard_continuable_evidence_session_storage_policy,
    validate_continuable_evidence_session_guards,
)


SESSION_REF = "continuable-evidence-session://session-1"
RUNTIME_BINDING_REF = "continuable-evidence-session-runtime-binding://binding-1"
ANSWER_RUN_REF = "evidence-summary-answer-run://run-1"
ANSWER_ARTIFACT_REF = "evidence-summary-answer-artifact://artifact-1"
TRACE_INSPECT_REF = "evidence-summary-answer-trace-inspect://inspect-1"
EVALUATION_REF = "evaluation://continuable-evidence-session/runtime-binding"
STORAGE_POLICY_REF = "policy://continuable-evidence-session/storage/default-v1"
STATE_ROOT_POLICY_REF = "policy://continuable-evidence-session/state-root/default-v1"
RETENTION_POLICY_REF = "policy://continuable-evidence-session/retention/default-v1"
DELETE_POLICY_REF = "policy://continuable-evidence-session/delete/default-v1"
EXPORT_POLICY_REF = "policy://continuable-evidence-session/export/default-v1"


def test_continuable_evidence_session_guards_allow_safe_payload():
    payload = {
        "continuable_evidence_session_ref": SESSION_REF,
        "source_answer_run_ref": ANSWER_RUN_REF,
        "session_status": "resumable",
        "resume_allowed": True,
        "resume_status": "requires_confirmation",
        "requires_user_confirmation": True,
        "requires_external_readonly_authorization": True,
        "requires_model_authorization": True,
        "metadata": {"source": "unit-test"},
    }

    result = validate_continuable_evidence_session_guards(payload)

    assert result.passed is True
    assert result.violations == ()


def test_continuable_evidence_session_raw_boundary_blocks_sensitive_payload():
    result = guard_continuable_evidence_session_raw_boundary(
        {
            "continuable_evidence_session_ref": SESSION_REF,
            "raw_prompt": "do not store",
            "metadata": {"secret": "value"},
        }
    )

    assert result.passed is False
    assert any("forbidden_raw_boundary_key" in item for item in result.violations)


def test_continuable_evidence_session_runtime_claims_block_adk_session():
    result = guard_continuable_evidence_session_runtime_claims(
        {
            "continuable_evidence_session_ref": SESSION_REF,
            "backed_by_adk_session": True,
        }
    )

    assert result.passed is False
    assert result.violations == ("$.backed_by_adk_session:runtime_claim_forbidden",)


def test_continuable_evidence_session_resume_policy_requires_blockers():
    result = guard_continuable_evidence_session_resume_policy(
        {
            "continuable_evidence_session_ref": SESSION_REF,
            "resume_allowed": False,
            "resume_status": "deleted",
            "requires_user_confirmation": True,
            "requires_external_readonly_authorization": True,
            "requires_model_authorization": True,
            "blocking_reasons": [],
        }
    )

    assert result.passed is False
    assert "deleted:requires_blocking_reasons" in result.violations


def test_continuable_evidence_session_artifact_index_is_refs_only():
    result = guard_continuable_evidence_session_artifact_index(
        {
            "continuable_evidence_session_ref": SESSION_REF,
            "answer_run_refs": [ANSWER_RUN_REF],
            "artifact_service_binding_refs": ["adk-artifact://raw"],
            "artifact_body": "raw content",
        }
    )

    assert result.passed is False
    assert "artifact_service_binding_refs:must_be_empty" in result.violations
    assert any("forbidden_raw_boundary_key" in item for item in result.violations)


def test_continuable_evidence_session_storage_guards_allow_safe_policy():
    result = validate_continuable_evidence_session_guards(
        {
            "payload_type": "continuable_evidence_session_storage_policy",
            "storage_policy_ref": STORAGE_POLICY_REF,
            "continuable_evidence_session_ref": SESSION_REF,
            "save_policy": "explicit_user_opt_in",
            "auto_save_default": False,
            "requires_user_confirmation_on_save": True,
            "requires_user_confirmation_on_resume": True,
            "local_state_root_policy_ref": STATE_ROOT_POLICY_REF,
            "retention_policy_ref": RETENTION_POLICY_REF,
            "delete_policy_ref": DELETE_POLICY_REF,
            "export_policy_ref": EXPORT_POLICY_REF,
            "config_backed": False,
            "runtime_backed": False,
            "memory_enabled": False,
        }
    )

    assert result.passed is True
    assert result.violations == ()


def test_continuable_evidence_session_storage_guard_blocks_auto_save():
    result = guard_continuable_evidence_session_storage_policy(
        {
            "payload_type": "continuable_evidence_session_storage_policy",
            "save_policy": "explicit_user_opt_in",
            "auto_save_default": True,
            "requires_user_confirmation_on_save": True,
            "requires_user_confirmation_on_resume": True,
        }
    )

    assert result.passed is False
    assert "auto_save_default:must_be_false" in result.violations


def test_continuable_evidence_session_local_state_root_guard_blocks_outputs():
    result = guard_continuable_evidence_session_local_state_root_policy(
        {
            "payload_type": "continuable_evidence_session_local_state_root_policy",
            "local_state_root_policy_ref": STATE_ROOT_POLICY_REF,
            "uses_repo_outputs": True,
        }
    )

    assert result.passed is False
    assert "uses_repo_outputs:must_be_false" in result.violations


def test_continuable_evidence_session_record_manifest_guard_blocks_io():
    result = guard_continuable_evidence_session_record_manifest(
        {
            "payload_type": "continuable_evidence_session_record_manifest",
            "contains_raw_payload": False,
            "io_performed": True,
        }
    )

    assert result.passed is False
    assert "io_performed:must_be_false" in result.violations


def test_continuable_evidence_session_delete_guard_blocks_resumable_deleted():
    result = guard_continuable_evidence_session_delete_policy(
        {
            "payload_type": "continuable_evidence_session_delete_policy",
            "requires_user_confirmation": True,
            "removes_local_record": True,
            "removes_from_resumable_index": True,
            "deleted_session_resumable": True,
        }
    )

    assert result.passed is False
    assert "deleted_session_resumable:must_be_false" in result.violations


def test_continuable_evidence_session_export_guard_blocks_evidence_archive():
    result = guard_continuable_evidence_session_export_policy(
        {
            "payload_type": "continuable_evidence_session_export_policy",
            "export_package_kind": "refs_and_summaries",
            "export_package_is_evidence_archive": True,
        }
    )

    assert result.passed is False
    assert "export_package_is_evidence_archive:must_be_false" in result.violations


def test_continuable_evidence_session_runtime_binding_guard_allows_safe_payload():
    result = validate_continuable_evidence_session_guards(
        {
            "payload_type": "continuable_evidence_session_runtime_binding",
            "runtime_binding_ref": RUNTIME_BINDING_REF,
            "continuable_evidence_session_ref": SESSION_REF,
            "runtime_binding_status": "probed",
            "runtime_binding_scope": "agent_session_event_artifactservice",
            "event_review_refs": [TRACE_INSPECT_REF],
            "artifact_binding_summary_refs": [ANSWER_ARTIFACT_REF],
            "runtime_binding_evaluation_summary_ref": EVALUATION_REF,
            "raw_runtime_object_included": False,
            "raw_event_payload_included": False,
            "artifact_body_included": False,
            "adk_eval_raw_data_included": False,
            "user_product_runtime_path_enabled": False,
            "default_local_state_dir_enabled": False,
            "auto_resume_answer_enabled": False,
            "skills_loaded": False,
            "memory_enabled": False,
            "tools_mcp_enabled": False,
            "callbacks_enabled": False,
            "plugins_enabled": False,
        }
    )

    assert result.passed is True
    assert result.violations == ()


def test_continuable_evidence_session_runtime_binding_guard_blocks_runtime_claims():
    result = guard_continuable_evidence_session_runtime_binding(
        {
            "payload_type": "continuable_evidence_session_runtime_binding",
            "runtime_binding_ref": RUNTIME_BINDING_REF,
            "continuable_evidence_session_ref": SESSION_REF,
            "runtime_binding_status": "bound",
            "runtime_binding_scope": "agent_session_event_artifactservice",
            "raw_runtime_object_included": True,
            "user_product_runtime_path_enabled": True,
            "skills_loaded": True,
            "raw_event_payload": {"content": "raw"},
        }
    )

    assert result.passed is False
    assert "raw_runtime_object_included:must_be_false" in result.violations
    assert "user_product_runtime_path_enabled:must_be_false" in result.violations
    assert "skills_loaded:must_be_false" in result.violations
    assert any("forbidden_raw_boundary_key" in item for item in result.violations)


def test_continuable_evidence_session_runtime_binding_guard_blocks_bad_refs():
    result = guard_continuable_evidence_session_runtime_binding(
        {
            "payload_type": "continuable_evidence_session_runtime_binding",
            "runtime_binding_ref": "adk-session://raw",
            "continuable_evidence_session_ref": SESSION_REF,
            "runtime_binding_status": "probed",
            "runtime_binding_scope": "agent_session_event_artifactservice",
            "event_review_refs": ["adk-event://raw"],
        }
    )

    assert result.passed is False
    assert "runtime_binding_ref:invalid_ref_prefix" in result.violations
    assert "event_review_refs:unsupported_ref_prefix" in result.violations


def test_continuable_evidence_session_runtime_visible_summary_guard_allows_safe_payload():
    result = validate_continuable_evidence_session_guards(
        {
            "payload_type": "continuable_evidence_session_runtime_visible_summary",
            "runtime_visible_summary_ref": (
                "continuable-evidence-session-summary://runtime-visible-1"
            ),
            "continuable_evidence_session_ref": SESSION_REF,
            "runtime_binding_ref": RUNTIME_BINDING_REF,
            "runtime_binding_status": "probed",
            "runtime_availability_hint": (
                "内部 runtime binding safe projection 可用于复查。"
            ),
            "trajectory_summary": {"turn_count": 1},
            "artifact_index": [
                {
                    "ref": ANSWER_ARTIFACT_REF,
                    "kind": "answer_artifact",
                    "purpose": "runtime_binding_user_visible_artifact_index",
                }
            ],
            "evaluation_summary_ref": EVALUATION_REF,
            "evaluation_status": "passed",
            "user_product_runtime_path_enabled": False,
            "default_local_state_dir_enabled": False,
            "auto_resume_answer_enabled": False,
            "workflow_replay_enabled": False,
            "llm_call_enabled": False,
            "task_runtime_implementation_enabled": False,
            "raw_runtime_object_included": False,
            "raw_event_payload_included": False,
            "artifact_body_included": False,
            "adk_eval_raw_data_included": False,
        }
    )

    assert result.passed is True
    assert result.violations == ()


def test_continuable_evidence_session_runtime_visible_summary_guard_blocks_claims():
    result = guard_continuable_evidence_session_runtime_visible_summary(
        {
            "payload_type": "continuable_evidence_session_runtime_visible_summary",
            "runtime_visible_summary_ref": (
                "continuable-evidence-session-summary://runtime-visible-1"
            ),
            "continuable_evidence_session_ref": SESSION_REF,
            "runtime_binding_status": "probed",
            "artifact_index": [{"ref": ANSWER_ARTIFACT_REF}],
            "user_product_runtime_path_enabled": True,
            "auto_resume_answer_enabled": True,
            "raw_event_payload": {"content": "raw"},
        }
    )

    assert result.passed is False
    assert "user_product_runtime_path_enabled:must_be_false" in result.violations
    assert "auto_resume_answer_enabled:must_be_false" in result.violations
    assert any("forbidden_raw_boundary_key" in item for item in result.violations)
