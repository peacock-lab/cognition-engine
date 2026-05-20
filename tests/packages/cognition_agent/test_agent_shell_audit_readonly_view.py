from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from cognition_agent import (
    AGENT_SHELL_AUDIT_READONLY_VIEW_SOURCE,
    AGENT_SHELL_AUDIT_READONLY_VIEW_VERSION,
    AgentShellAuditReadonlyViewCandidate,
    build_agent_governance_evidence_summary_view,
    build_agent_governed_run_evidence_context_candidate,
    build_agent_shell_audit_readonly_view,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
COGNITION_AGENT_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "cognition_agent" / "src" / "cognition_agent"
)


def test_agent_shell_audit_readonly_view_consumes_success_contract() -> None:
    view = build_agent_shell_audit_readonly_view(
        candidate_id="agent-shell-audit-view-success-1",
        agent_shell_audit=_agent_shell_audit(status="success", failure_type=None),
    )

    assert isinstance(view, AgentShellAuditReadonlyViewCandidate)
    assert view.candidate_type == "agent_shell_audit_readonly_view_candidate"
    assert view.view_version == AGENT_SHELL_AUDIT_READONLY_VIEW_VERSION
    assert view.source == AGENT_SHELL_AUDIT_READONLY_VIEW_SOURCE
    assert view.agent_shell_evidence_ref == (
        "adk-agent-shell-evidence://adk-agent-shell-evidence-1"
    )
    assert view.agent_shell_run_ref == "adk-agent-shell-run://agent-shell-live-1"
    assert view.status == "success"
    assert view.event_count == 2
    assert view.controlled_live is True
    assert view.controlled_live_smoke is True
    assert view.controlled_live_smoke_enabled is True
    assert view.runtime_call_performed is True
    assert view.call_attempted is True
    assert view.failure_type is None
    assert view.live_profile == {
        "live_options_source": "config_contexts.runtime.RuntimeLiveLlmConfigView",
        "live_service_profile": "adk_litellm_ollama",
        "configured_model_name": "ollama/gemma4-pro:latest",
        "timeout_seconds": 45,
        "temperature": 0,
        "max_tokens": 64,
        "enabled_by_default": False,
    }
    assert view.ready_for_agent_review is True
    assert view.warnings == []
    assert view.readonly is True
    assert view.candidate_only is True
    assert view.execution_enabled is False
    assert view.runtime_permission_granted is False
    assert view.runtime_container_call_enabled is False
    assert view.llm_call_enabled is False
    assert view.metadata["does_not_call_runtime_container"] is True
    assert view.metadata["does_not_import_adk_adapter"] is True
    assert view.metadata["does_not_read_configuration_center"] is True
    assert "adk-agent-shell-run://agent-shell-live-1" in view.governance_refs
    assert view.config_refs == ["config:runtime:live_llm"]


def test_agent_shell_audit_readonly_view_consumes_failure_and_skipped() -> None:
    failure_view = build_agent_shell_audit_readonly_view(
        candidate_id="agent-shell-audit-view-failure-1",
        agent_shell_audit=_agent_shell_audit(
            status="failure",
            failure_type="provider_unavailable",
            runtime_call_performed=True,
            call_attempted=True,
        ),
    )
    skipped_view = build_agent_shell_audit_readonly_view(
        candidate_id="agent-shell-audit-view-skipped-1",
        agent_shell_audit=_agent_shell_audit(
            status="skipped",
            failure_type="live_disabled",
            runtime_call_performed=False,
            call_attempted=False,
        ),
    )

    assert failure_view.ready_for_agent_review is True
    assert failure_view.failure_type == "provider_unavailable"
    assert "agent_shell_failure:provider_unavailable" in failure_view.warnings
    assert skipped_view.ready_for_agent_review is True
    assert skipped_view.failure_type == "live_disabled"
    assert "controlled_live_agent_shell_live_disabled" in skipped_view.warnings
    assert "agent_shell_runtime_call_not_performed" in skipped_view.warnings
    assert "agent_shell_skipped" in skipped_view.warnings


def test_agent_shell_audit_view_can_feed_governed_run_context_readonly() -> None:
    view = build_agent_shell_audit_readonly_view(
        candidate_id="agent-shell-audit-view-context-1",
        agent_shell_audit=_agent_shell_audit(status="success", failure_type=None),
    )
    context = build_agent_governed_run_evidence_context_candidate(
        candidate_id="governed-context-agent-shell-1",
        governance_summary_view=_governance_summary_view(),
        agent_shell_audit_view=view,
    )

    assert context.agent_shell_audit_candidate_id == (
        "agent-shell-audit-view-context-1"
    )
    assert context.agent_shell_evidence_ref == (
        "adk-agent-shell-evidence://adk-agent-shell-evidence-1"
    )
    assert context.agent_shell_run_ref == "adk-agent-shell-run://agent-shell-live-1"
    assert context.agent_shell_status == "success"
    assert context.agent_shell_failure_type is None
    assert context.agent_shell_controlled_live is True
    assert context.agent_shell_runtime_call_performed is True
    assert context.agent_shell_call_attempted is True
    assert context.agent_shell_live_profile == view.live_profile
    assert context.execution_enabled is False
    assert context.runtime_container_call_enabled is False


def test_agent_shell_audit_readonly_view_rejects_raw_and_execution_payloads() -> None:
    with pytest.raises(ValueError):
        build_agent_shell_audit_readonly_view(
            candidate_id="agent-shell-audit-view-raw-1",
            agent_shell_audit={
                **_agent_shell_audit(status="success", failure_type=None),
                "raw_response": "must not be consumed",
            },
        )

    with pytest.raises(ValueError):
        build_agent_shell_audit_readonly_view(
            candidate_id="agent-shell-audit-view-raw-live-profile-1",
            agent_shell_audit={
                **_agent_shell_audit(status="success", failure_type=None),
                "live_profile": {
                    "live_service_profile": "adk_litellm_ollama",
                    "raw_provider_response": "must not be consumed",
                },
            },
        )

    with pytest.raises(ValidationError):
        AgentShellAuditReadonlyViewCandidate(
            candidate_id="agent-shell-audit-view-invalid-1",
            source=AGENT_SHELL_AUDIT_READONLY_VIEW_SOURCE,
            summary="Invalid Agent shell audit view.",
            status="success",
            execution_enabled=True,
        )


def test_agent_shell_audit_readonly_view_source_has_no_execution_dependencies() -> None:
    source = (COGNITION_AGENT_SOURCE_ROOT / "agent_shell_audit_view.py").read_text(
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


def _agent_shell_audit(
    *,
    status: str,
    failure_type: str | None,
    runtime_call_performed: bool = True,
    call_attempted: bool = True,
) -> dict[str, object]:
    return {
        "agent_shell_evidence_ref": (
            "adk-agent-shell-evidence://adk-agent-shell-evidence-1"
        ),
        "agent_shell_run_ref": "adk-agent-shell-run://agent-shell-live-1",
        "agent_name": "cognition_agent_shell",
        "agent_type": "LlmAgent",
        "app_name": "cognition_agent_shell_controlled_live_smoke",
        "status": status,
        "event_count": 2 if status == "success" else 0,
        "controlled_live": True,
        "controlled_live_smoke": True,
        "controlled_live_smoke_enabled": True,
        "runtime_call_performed": runtime_call_performed,
        "call_attempted": call_attempted,
        "failure_type": failure_type,
        "error_message_sanitized": failure_type,
        "live_profile": {
            "live_options_source": "config_contexts.runtime.RuntimeLiveLlmConfigView",
            "live_service_profile": "adk_litellm_ollama",
            "configured_model_name": "ollama/gemma4-pro:latest",
            "ollama_api_base": "http://127.0.0.1:11434",
            "timeout_seconds": 45,
            "temperature": 0,
            "max_tokens": 64,
            "enabled_by_default": False,
        },
        "does_not_store_prompt": True,
        "does_not_store_raw_response": True,
        "raw_adk_object_included": False,
        "raw_adk_event_included": False,
        "raw_adk_session_included": False,
    }


def _governance_summary_view():
    return build_agent_governance_evidence_summary_view(
        candidate_id="agent-governance-summary-view-agent-shell-1",
        governance_evidence_metadata={
            "lifecycle_summary": {
                "summary_id": "adk-lifecycle-summary-agent-shell-1",
                "runtime_id": "runtime-agent-shell-1",
                "workflow_id": "workflow-agent-shell-1",
                "workflow_name": "agent-shell-workflow",
                "status": "success",
                "session": {"session_id": "session-agent-shell-1", "event_count": 2},
                "events": {"event_count": 2, "event_types": ["node_completed"]},
                "context_state": {
                    "state_delta_count": 0,
                    "state_delta_entity_mode": "event_payload_summary_only",
                },
            },
            "run_config_service_bundle_summary": {
                "summary_id": "adk-run-config-service-bundle-summary-agent-shell-1",
                "runtime_id": "runtime-agent-shell-1",
                "workflow_id": "workflow-agent-shell-1",
                "workflow_name": "agent-shell-workflow",
                "status": "success",
                "run_config": {
                    "mapped_fields": ["max_llm_calls"],
                    "unmapped_fields": [],
                    "deferred_fields": [],
                    "no_live_mode": True,
                    "call_attempted": False,
                },
                "service_bundle": {
                    "service_bundle_source": "in_memory",
                    "artifact_service_present": True,
                    "session_service_present": True,
                },
            },
        },
    )
