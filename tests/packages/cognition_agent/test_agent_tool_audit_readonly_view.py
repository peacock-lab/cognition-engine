from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from cognition_agent import (
    AGENT_TOOL_AUDIT_READONLY_VIEW_SOURCE,
    AGENT_TOOL_AUDIT_READONLY_VIEW_VERSION,
    AgentToolAuditReadonlyViewCandidate,
    build_agent_tool_audit_readonly_view,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
COGNITION_AGENT_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "cognition_agent" / "src" / "cognition_agent"
)


def test_agent_tool_audit_readonly_view_consumes_success_contract() -> None:
    view = build_agent_tool_audit_readonly_view(
        candidate_id="agent-tool-audit-view-success-1",
        tool_audit=_tool_audit(status="success", failure_type=None),
    )

    assert isinstance(view, AgentToolAuditReadonlyViewCandidate)
    assert view.candidate_type == "agent_tool_audit_readonly_view_candidate"
    assert view.view_version == AGENT_TOOL_AUDIT_READONLY_VIEW_VERSION
    assert view.source == AGENT_TOOL_AUDIT_READONLY_VIEW_SOURCE
    assert view.tool_evidence_ref == (
        "adk-tool-call-evidence://adk-tool-call-evidence-1"
    )
    assert view.tool_run_ref == "adk-function-tool-run://tool-run-1"
    assert view.tool_name == "review_task_context"
    assert view.tool_kind == "deterministic_no_live_task_review"
    assert view.status == "success"
    assert view.tool_call_allowed is True
    assert view.tool_call_attempted is True
    assert view.tool_runtime_call_performed is True
    assert view.tool_confirmation_required is False
    assert view.tool_confirmation_granted is True
    assert view.adk_tool_confirmation_requested is False
    assert view.tool_approval_ref == "approval://tool-1"
    assert view.tool_confirmation_decision_source == "test.operator_approval"
    assert view.tool_failure_type is None
    assert view.tool_input_summary["argument_keys"] == ["task_ref"]
    assert view.tool_output_summary["recommendation"] == "review_ready"
    assert view.ready_for_agent_review is True
    assert view.warnings == []
    assert view.readonly is True
    assert view.candidate_only is True
    assert view.execution_enabled is False
    assert view.tool_execution_enabled is False
    assert view.metadata["does_not_call_runtime_container"] is True
    assert view.metadata["does_not_import_adk_adapter"] is True
    assert view.metadata["does_not_store_raw_tool_input"] is True
    assert view.metadata["does_not_store_raw_tool_output"] is True
    assert "adk-function-tool-run://tool-run-1" in view.governance_refs
    assert "approval://tool-1" in view.governance_refs


def test_agent_tool_audit_readonly_view_consumes_blocked_and_failure() -> None:
    blocked_view = build_agent_tool_audit_readonly_view(
        candidate_id="agent-tool-audit-view-blocked-1",
        tool_audit=_tool_audit(
            status="failed",
            failure_type="tool_call_not_allowed",
            tool_call_allowed=False,
            tool_call_attempted=False,
            tool_runtime_call_performed=False,
        ),
    )
    failure_view = build_agent_tool_audit_readonly_view(
        candidate_id="agent-tool-audit-view-failure-1",
        tool_audit=_tool_audit(
            status="failed",
            failure_type="tool_runtime_failure",
            tool_call_allowed=True,
            tool_call_attempted=True,
            tool_runtime_call_performed=True,
        ),
    )

    assert blocked_view.ready_for_agent_review is False
    assert "tool_call_not_allowed" in blocked_view.warnings
    assert "tool_failure:tool_call_not_allowed" in blocked_view.warnings
    assert failure_view.ready_for_agent_review is True
    assert "tool_failure:tool_runtime_failure" in failure_view.warnings


def test_agent_tool_audit_readonly_view_rejects_raw_and_execution_payloads() -> None:
    with pytest.raises(ValueError):
        build_agent_tool_audit_readonly_view(
            candidate_id="agent-tool-audit-view-raw-1",
            tool_audit={
                **_tool_audit(status="success", failure_type=None),
                "raw_tool_output": "must not be consumed",
            },
        )

    with pytest.raises(ValueError):
        build_agent_tool_audit_readonly_view(
            candidate_id="agent-tool-audit-view-raw-summary-1",
            tool_audit={
                **_tool_audit(status="success", failure_type=None),
                "tool_output_summary": {
                    "raw_tool_output": "must not be consumed",
                },
            },
        )

    with pytest.raises(ValidationError):
        AgentToolAuditReadonlyViewCandidate(
            candidate_id="agent-tool-audit-view-invalid-1",
            source=AGENT_TOOL_AUDIT_READONLY_VIEW_SOURCE,
            summary="Invalid ADK Tool audit view.",
            status="success",
            tool_execution_enabled=True,
        )


def test_agent_tool_audit_readonly_view_source_has_no_execution_dependencies() -> None:
    source = (COGNITION_AGENT_SOURCE_ROOT / "agent_tool_audit_view.py").read_text(
        encoding="utf-8"
    )
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:adk_adapter|litellm|google\.adk|runtime_container|runtime|"
        r"observability_hub|composition|config_contexts|config_assembly|"
        r"cognition_governance|subprocess)\b",
        re.MULTILINE,
    )
    forbidden_calls = re.compile(
        r"\b(?:completion|acompletion|service\.invoke|runner\.run|run_async)\s*\("
    )

    assert forbidden_imports.search(source) is None
    assert forbidden_calls.search(source) is None
    assert "live_enabled=True" not in source
    assert "RuntimeCompositionOptions" not in source
    assert "ToolExecutor" not in source
    assert "Chat" not in source
    assert "Gateway" not in source


def _tool_audit(
    *,
    status: str,
    failure_type: str | None,
    tool_call_allowed: bool = True,
    tool_call_attempted: bool = True,
    tool_runtime_call_performed: bool = True,
) -> dict[str, object]:
    return {
        "tool_evidence_ref": "adk-tool-call-evidence://adk-tool-call-evidence-1",
        "tool_run_ref": "adk-function-tool-run://tool-run-1",
        "tool_name": "review_task_context",
        "tool_kind": "deterministic_no_live_task_review",
        "status": status,
        "tool_call_allowed": tool_call_allowed,
        "tool_call_attempted": tool_call_attempted,
        "tool_runtime_call_performed": tool_runtime_call_performed,
        "tool_confirmation_required": False,
        "tool_confirmation_granted": True,
        "adk_tool_confirmation_requested": False,
        "tool_approval_ref": "approval://tool-1",
        "tool_confirmation_decision_source": "test.operator_approval",
        "tool_failure_type": failure_type,
        "tool_input_summary": {
            "argument_keys": ["task_ref"],
            "argument_count": 1,
            "input_digest": "abc",
        },
        "tool_output_summary": {
            "result_kind": "deterministic_no_live_task_review",
            "recommendation": "review_ready",
            "output_digest": "def",
        },
        "does_not_store_raw_tool_input": True,
        "does_not_store_raw_tool_output": True,
        "raw_adk_object_included": False,
    }
