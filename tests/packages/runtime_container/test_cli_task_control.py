from __future__ import annotations

from runtime_container.cli_task_control import (
    CLI_TASK_CONFIG_PRECEDENCE,
    CLI_TASK_CONTROL_STAGES,
    build_cli_task_run_context,
    cli_task_run_context_status_dict,
    evaluate_cli_task_preflight,
    finalize_cli_task_run_context,
)


def test_cli_task_run_context_records_control_structure_and_refs() -> None:
    context = build_cli_task_run_context(
        workflow_name="cli_plan_workflow",
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

    assert context.run_id == "cli-plan-workflow-cli-plan-test-turn-003"
    assert context.stages == CLI_TASK_CONTROL_STAGES
    assert context.config_precedence == CLI_TASK_CONFIG_PRECEDENCE
    assert context.status == "preflight_allowed"
    assert context.preflight.allowed is True
    assert context.preflight.passthrough_parameter_keys == ("domain",)
    assert context.workspace.workspace_created is False
    assert context.workspace.workspace_ref.startswith(
        "run-workspace://cli-plan-workflow/"
    )
    assert context.evidence_summary["approval_ref_present"] is True
    assert context.evidence_summary["risk_level"] == "medium"


def test_cli_task_preflight_blocks_user_passthrough_governance_override() -> None:
    preflight = evaluate_cli_task_preflight(
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


def test_cli_task_status_dict_is_sanitized_and_finalizable() -> None:
    context = build_cli_task_run_context(
        workflow_name="cli_plan_workflow",
        task_kind="new_plan",
        session_id="session with spaces",
        turn_index=1,
        live_model_allowed=False,
        risk_level="low",
        output_budget=512,
    )

    finalized = finalize_cli_task_run_context(
        context,
        status="succeeded",
        artifact_refs=("candidate-artifact://run/result",),
        evidence_refs=("evidence://extra",),
    )
    status = cli_task_run_context_status_dict(finalized)

    assert status["status"] == "succeeded"
    assert status["run_id"] == "cli-plan-workflow-session-with-spaces-turn-001"
    assert status["preflight"]["allowed"] is True
    assert status["workspace"]["workspace_created"] is False
    assert status["workspace"]["artifact_refs"] == [
        "candidate-artifact://run/result"
    ]
    assert "evidence://extra" in status["workspace"]["evidence_refs"]
    assert status["config_precedence"] == list(CLI_TASK_CONFIG_PRECEDENCE)
