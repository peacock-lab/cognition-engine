from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPO_ROOT / "packages" / "operation_flows" / "src"

sys.path.insert(0, str(SOURCE_ROOT))

from cognition_operation_flows._core.control import (  # noqa: E402
    TWF_CONFIG_PRECEDENCE,
    TWF_CONTROL_STAGES,
    build_twf_run_context,
    twf_run_context_status_dict,
    evaluate_twf_preflight,
    finalize_twf_run_context,
)


def test_task_run_context_records_control_structure_and_refs() -> None:
    context = build_twf_run_context(
        workflow_name="twf_plan_workflow",
        task_kind="new_plan",
        session_id="cli-plan-test",
        turn_index=3,
        live_model_allowed=True,
        approval_ref="approval://task-control",
        audit_ref="audit://task-control",
        sanitized_evidence_ref="evidence://task-control",
        risk_level="medium",
        output_budget=2048,
        user_passthrough_parameters={"domain": "fishpond"},
    )

    assert context.run_id == "twf-plan-workflow-cli-plan-test-turn-003"
    assert context.stages == TWF_CONTROL_STAGES
    assert context.config_precedence == TWF_CONFIG_PRECEDENCE
    assert context.status == "preflight_allowed"
    assert context.preflight.allowed is True
    assert context.preflight.passthrough_parameter_keys == ("domain",)
    assert context.workspace.workspace_created is False
    assert context.workspace.workspace_ref.startswith(
        "run-workspace://twf-plan-workflow/"
    )
    assert context.evidence_summary["approval_ref_present"] is True
    assert context.evidence_summary["risk_level"] == "medium"


def test_task_preflight_blocks_user_passthrough_governance_override() -> None:
    preflight = evaluate_twf_preflight(
        live_model_allowed=True,
        approval_ref="approval://task-control",
        audit_ref="audit://task-control",
        sanitized_evidence_ref="evidence://task-control",
        risk_level="low",
        output_budget=1024,
        live_gate="controlled_live",
        user_passthrough_parameters={
            "approval_ref": "approval://user-override",
            "domain": "fishpond",
        },
    )

    assert preflight.allowed is False
    assert "user_passthrough_overrides_approval_ref" in preflight.blocking_reasons
    assert "approval_ref" in preflight.managed_parameters
    assert preflight.passthrough_parameter_keys == ("approval_ref", "domain")


def test_task_status_dict_is_sanitized_and_finalizable() -> None:
    context = build_twf_run_context(
        workflow_name="twf_plan_workflow",
        task_kind="new_plan",
        session_id="session with spaces",
        turn_index=1,
        live_model_allowed=False,
        risk_level="low",
        output_budget=512,
    )

    finalized = finalize_twf_run_context(
        context,
        status="succeeded",
        artifact_refs=("candidate-artifact://run/result",),
        evidence_refs=("evidence://extra",),
    )
    status = twf_run_context_status_dict(finalized)

    assert status["status"] == "succeeded"
    assert status["run_id"] == "twf-plan-workflow-session-with-spaces-turn-001"
    assert status["preflight"]["allowed"] is True
    assert status["workspace"]["workspace_created"] is False
    assert status["workspace"]["artifact_refs"] == [
        "candidate-artifact://run/result"
    ]
    assert "evidence://extra" in status["workspace"]["evidence_refs"]
    assert status["config_precedence"] == list(TWF_CONFIG_PRECEDENCE)
