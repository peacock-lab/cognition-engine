from __future__ import annotations

from datetime import UTC, datetime

from product_runtime_assembly.continuable_evidence_session_entry import (
    build_product_console_session_action_handler,
    build_product_console_session_save_handler,
)
from product_runtime_assembly.continuable_evidence_session_state_root import (
    ContinuableEvidenceSessionStateRootResolution,
)


NOW = datetime(2026, 5, 27, 0, 0, 0, tzinfo=UTC)


def test_product_console_session_entry_saves_lists_previews_expires_and_deletes(
    tmp_path,
) -> None:
    state_root = tmp_path / "session-state"
    save_handler = build_product_console_session_save_handler(now_factory=lambda: NOW)
    action_handler = build_product_console_session_action_handler(
        now_factory=lambda: NOW
    )

    save_result = save_handler(
        {
            "action": "save",
            "state_root": str(state_root),
            "output": {
                "request_id": "external-readonly-ask-request://product-console/ask",
                "status": "success",
                "question_preview": "这份资料主要说明什么？",
                "answer_preview": "这是安全摘要。",
                "answer_run_ref": "evidence-summary-answer-run://run-test",
                "answer_trace_ref": "evidence-summary-answer-trace://trace-test",
                "answer_artifact_ref": (
                    "evidence-summary-answer-artifact://artifact-test"
                ),
                "observability_summary_ref": (
                    "evidence-summary-answer-observability-summary://summary-test"
                ),
                "trace_inspect_ref": (
                    "evidence-summary-answer-trace-inspect://inspect-test"
                ),
                "evidence_refs": [
                    {"ref": "evidence://external-readonly/source-test"}
                ],
                "additional_refs": [
                    {"ref": "governed-evidence-digest://digest-test"}
                ],
                "runtime_visible_summary": {
                    "runtime_summary_ref": (
                        "continuable-evidence-session-summary://runtime-visible-test"
                    ),
                    "runtime_availability_hint": {
                        "runtime_binding_status": "probed",
                        "hint": "内部 runtime binding safe projection 可用于复查。",
                    },
                    "runtime_artifact_index": [
                        {
                            "ref": "evidence-summary-answer-artifact://artifact-test",
                            "kind": "answer_artifact",
                        }
                    ],
                    "runtime_evaluation_summary": {
                        "evaluation_summary_ref": (
                            "evaluation://continuable-evidence-session/runtime-binding"
                        ),
                        "evaluation_status": "passed",
                    },
                },
            },
            "turns": (
                {
                    "turn_index": 1,
                    "request_id": "external-readonly-ask-request://product-console/ask",
                    "status": "success",
                    "question_preview": "这份资料主要说明什么？",
                    "answer_preview": "这是安全摘要。",
                    "answer_run_ref": "evidence-summary-answer-run://run-test",
                    "answer_artifact_ref": (
                        "evidence-summary-answer-artifact://artifact-test"
                    ),
                    "trace_inspect_ref": (
                        "evidence-summary-answer-trace-inspect://inspect-test"
                    ),
                    "observability_summary_ref": (
                        "evidence-summary-answer-observability-summary://summary-test"
                    ),
                    "evidence_refs": [
                        {"ref": "evidence://external-readonly/source-test"}
                    ],
                    "additional_refs": [
                        {"ref": "governed-evidence-digest://digest-test"}
                    ],
                },
                {
                    "turn_index": 2,
                    "request_id": (
                        "external-readonly-ask-request://product-console/ask/"
                        "answer-transform-1"
                    ),
                    "status": "success",
                    "answer_scoped_transformation": True,
                    "question_preview": "请做三点摘要。",
                    "answer_preview": "三点安全摘要。",
                },
            ),
        }
    )

    assert save_result["status"] == "success"
    session_id = save_result["session_id"]
    assert (state_root / "index.json").exists()
    assert (state_root / "sessions" / session_id / "manifest.json").exists()
    assert "sessions/" + session_id + "/turns/0001-initial_question.json" in (
        save_result["written_relative_paths"]
    )
    assert "sessions/" + session_id + "/turns/0002-answer_transformation.json" in (
        save_result["written_relative_paths"]
    )
    assert "sessions/" + session_id + "/summaries/runtime-visible.json" in (
        save_result["written_relative_paths"]
    )

    list_result = action_handler({"action": "list", "state_root": str(state_root)})
    preview_result = action_handler(
        {
            "action": "resume-preview",
            "state_root": str(state_root),
            "session_id": session_id,
        }
    )
    expire_result = action_handler(
        {
            "action": "expire",
            "state_root": str(state_root),
            "now": "2026-06-27T00:00:00Z",
        }
    )
    delete_result = action_handler(
        {
            "action": "delete",
            "state_root": str(state_root),
            "session_id": session_id,
            "confirmed": True,
        }
    )

    assert list_result["status"] == "success"
    assert list_result["entries"][0]["session_id"] == session_id
    assert preview_result["status"] == "success"
    assert preview_result["resume_preview"]["record_status"] == "resumable"
    assert preview_result["resume_preview"][
        "requires_external_readonly_authorization"
    ] is True
    runtime_summary = preview_result["resume_preview"]["runtime_summary"]
    assert runtime_summary["has_runtime_visible_summary"] is True
    assert runtime_summary["runtime_binding_status"] == "probed"
    assert runtime_summary["artifact_refs"] == (
        "evidence-summary-answer-artifact://artifact-test",
    )
    assert runtime_summary["evaluation_status"] == "passed"
    assert runtime_summary["auto_resume_answer_enabled"] is False
    assert expire_result["expired_session_ids"] == (session_id,)
    assert delete_result["status"] == "success"
    assert delete_result["deleted"] is True
    assert not (state_root / "sessions" / session_id).exists()
    deleted_preview_result = action_handler(
        {
            "action": "resume-preview",
            "state_root": str(state_root),
            "session_id": session_id,
        }
    )
    assert deleted_preview_result["status"] == "unavailable"
    assert deleted_preview_result["reason"] == "session_not_found"
    assert (
        "不会重新读取资料、调用模型或重放 Workflow。"
        in deleted_preview_result["recovery_hints"][0]
    )


def test_product_console_session_entry_uses_default_state_root_resolver(tmp_path) -> None:
    state_root = tmp_path / "default-session-state"

    def resolver(_request):
        return ContinuableEvidenceSessionStateRootResolution(
            state_root=str(state_root),
            state_root_source="platform_default",
        )

    save_handler = build_product_console_session_save_handler(
        now_factory=lambda: NOW,
        state_root_resolver=resolver,
    )
    action_handler = build_product_console_session_action_handler(
        now_factory=lambda: NOW,
        state_root_resolver=resolver,
    )
    save_result = save_handler(
        {
            "action": "save",
            "output": {
                "request_id": "external-readonly-ask-request://product-console/ask",
                "status": "success",
                "question_preview": "这份资料主要说明什么？",
                "answer_preview": "这是安全摘要。",
                "answer_run_ref": "evidence-summary-answer-run://run-default",
                "evidence_refs": [
                    {"ref": "evidence://external-readonly/source-test"}
                ],
                "additional_refs": [
                    {"ref": "governed-evidence-digest://digest-test"}
                ],
            },
            "turns": (
                {
                    "turn_index": 1,
                    "status": "success",
                    "question_preview": "这份资料主要说明什么？",
                    "answer_preview": "这是安全摘要。",
                    "answer_run_ref": "evidence-summary-answer-run://run-default",
                    "evidence_refs": [
                        {"ref": "evidence://external-readonly/source-test"}
                    ],
                    "additional_refs": [
                        {"ref": "governed-evidence-digest://digest-test"}
                    ],
                },
            ),
        }
    )

    assert save_result["status"] == "success"
    assert save_result["state_root"] == str(state_root)
    assert save_result["state_root_source"] == "platform_default"
    list_result = action_handler({"action": "list"})
    assert list_result["status"] == "success"
    assert list_result["state_root_source"] == "platform_default"
    assert list_result["entries"][0]["session_id"] == save_result["session_id"]


def test_product_console_session_save_handler_requires_digest_refs(tmp_path) -> None:
    save_handler = build_product_console_session_save_handler(now_factory=lambda: NOW)

    result = save_handler(
        {
            "action": "save",
            "state_root": str(tmp_path / "session-state"),
            "output": {
                "status": "success",
                "answer_run_ref": "evidence-summary-answer-run://run-test",
                "evidence_refs": [
                    {"ref": "evidence://external-readonly/source-test"}
                ],
            },
            "turns": (
                {
                    "turn_index": 1,
                    "status": "success",
                    "answer_run_ref": "evidence-summary-answer-run://run-test",
                    "evidence_refs": [
                        {"ref": "evidence://external-readonly/source-test"}
                    ],
                },
            ),
        }
    )

    assert result["status"] == "unavailable"
    assert result["reason"] == "session_save_requires_digest_refs"


def test_session_save_ignores_review_runtime_display_shape(tmp_path) -> None:
    state_root = tmp_path / "session-state"
    save_handler = build_product_console_session_save_handler(now_factory=lambda: NOW)

    result = save_handler(
        {
            "action": "save",
            "state_root": str(state_root),
            "output": {
                "status": "success",
                "answer_run_ref": "evidence-summary-answer-run://run-test",
                "evidence_refs": [
                    {"ref": "evidence://external-readonly/source-test"}
                ],
                "additional_refs": [
                    {"ref": "governed-evidence-digest://digest-test"}
                ],
                "review": {
                    "runtime": {
                        "runtime_summary_ref": "runtime-summary://display-only",
                        "artifact_index": [
                            {"ref": "artifact://display-only", "kind": "answer"}
                        ],
                    }
                },
            },
            "turns": (
                {
                    "turn_index": 1,
                    "status": "success",
                    "answer_run_ref": "evidence-summary-answer-run://run-test",
                    "evidence_refs": [
                        {"ref": "evidence://external-readonly/source-test"}
                    ],
                    "additional_refs": [
                        {"ref": "governed-evidence-digest://digest-test"}
                    ],
                },
            ),
        }
    )

    assert result["status"] == "success"
    assert not any(
        path.endswith("summaries/runtime-visible.json")
        for path in result["written_relative_paths"]
    )
