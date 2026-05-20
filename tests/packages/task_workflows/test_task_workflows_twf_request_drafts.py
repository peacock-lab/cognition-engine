from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "packages" / "task_workflows"
SOURCE_ROOT = PACKAGE_ROOT / "src"

sys.path.insert(0, str(SOURCE_ROOT))

from cognition_task_workflows._requests.drafts import (  # noqa: E402
    TWF_REQUEST_DRAFT_SCHEMA_VERSION,
    TwfGovernanceRefsCandidate,
    TwfReferenceWorkspaceControlsCandidate,
    TwfWorkflowRequestDraftCandidate,
    build_twf_config_profile_explain_request_draft,
    build_twf_plan_request_draft,
    build_twf_reference_review_request_draft,
    build_twf_run_workspace_evidence_audit_request_draft,
    twf_workflow_request_draft_status_dict,
)
from cognition_task_workflows._requests.registry import (  # noqa: E402
    TWF_PLAN_TASK_KIND,
    TWF_PLAN_WORKFLOW_NAME,
)


def test_plan_request_draft_is_channel_neutral_candidate_only() -> None:
    draft = build_twf_plan_request_draft(
        sanitized_user_text="我要建一个鱼塘，帮我设计建设方案",
        chat_session_id="session-1",
        turn_index=2,
        sanitized_history=({"user": "上一轮", "assistant": "已收到"},),
        sanitized_previous_display_text="上一轮方案摘要",
        governance_refs=TwfGovernanceRefsCandidate(
            approval_ref="approval://plan",
            audit_ref="audit://plan",
            sanitized_evidence_ref="evidence://plan",
            governance_summary_output_ref="artifact://plan",
        ),
        controls=TwfReferenceWorkspaceControlsCandidate(
            reference_paths=("docs/example.md",),
            external_readonly_evidence_paths=(
                "outputs/external-readonly/cli-fetch/example.json",
            ),
            tool_exposure_profile="readonly_reference",
            run_workspace_enabled=True,
            run_workspace_root="/tmp/cognition-run",
            run_workspace_retention_policy="keep_on_success",
            run_workspace_cleanup_policy="manual",
            run_workspace_max_write_bytes=4096,
        ),
        route_summary={
            "source": "product_gateway._task_workflows.route",
            "matched": True,
        },
        operator_approved=True,
        request_live_llm=True,
        allow_live_llm=True,
        live_llm_timeout_seconds=180,
        live_model_allowed=True,
    )

    assert draft.schema_version == TWF_REQUEST_DRAFT_SCHEMA_VERSION
    assert draft.workflow_name == TWF_PLAN_WORKFLOW_NAME
    assert draft.task_kind == TWF_PLAN_TASK_KIND
    assert draft.turn_input.sanitized_user_text.startswith("我要建一个鱼塘")
    assert draft.candidate_only is True
    assert draft.channel_neutral is True
    assert draft.product_gateway_entry_required is True
    assert draft.runtime_adapter_required is True
    assert draft.runtime_request_candidate_enabled is False
    assert draft.workflow_execution_enabled is False
    assert draft.public_schema_enabled is False
    assert draft.llm_invocation_service_embedded is False
    assert draft.argparse_namespace_embedded is False

    status = twf_workflow_request_draft_status_dict(draft)
    assert status["workflow_name"] == TWF_PLAN_WORKFLOW_NAME
    assert status["history_count"] == 1
    assert status["controls"]["reference_path_count"] == 1
    assert status["controls"]["external_readonly_evidence_path_count"] == 1
    assert status["governance_refs"]["approval_ref_present"] is True
    assert "sanitized_user_text" not in status


def test_four_request_draft_builders_cover_registered_workflows() -> None:
    builders = (
        build_twf_plan_request_draft,
        build_twf_reference_review_request_draft,
        build_twf_config_profile_explain_request_draft,
        build_twf_run_workspace_evidence_audit_request_draft,
    )

    drafts = tuple(
        builder(
            sanitized_user_text="请处理这个任务",
            chat_session_id="session-2",
            turn_index=index,
        )
        for index, builder in enumerate(builders, start=1)
    )

    assert [draft.workflow_name for draft in drafts] == [
        "twf_plan_workflow",
        "twf_reference_review_workflow",
        "twf_config_profile_explain_workflow",
        "twf_run_workspace_evidence_audit_workflow",
    ]
    assert all(draft.runtime_adapter_required for draft in drafts)
    assert all(not draft.workflow_execution_enabled for draft in drafts)


@pytest.mark.parametrize(
    "field_name, value",
    [
        ("candidate_only", False),
        ("channel_neutral", False),
        ("product_gateway_entry_required", False),
        ("runtime_adapter_required", False),
        ("runtime_request_candidate_enabled", True),
        ("workflow_execution_enabled", True),
        ("public_schema_enabled", True),
        ("llm_invocation_service_embedded", True),
        ("argparse_namespace_embedded", True),
    ],
)
def test_request_draft_rejects_boundary_drift(
    field_name: str,
    value: bool,
) -> None:
    payload = {
        "workflow_name": TWF_PLAN_WORKFLOW_NAME,
        "task_kind": TWF_PLAN_TASK_KIND,
        "turn_input": build_twf_plan_request_draft(
            sanitized_user_text="请给我方案"
        ).turn_input,
        field_name: value,
    }

    with pytest.raises(ValueError):
        TwfWorkflowRequestDraftCandidate(**payload)


def test_request_draft_rejects_managed_governance_passthrough() -> None:
    draft = build_twf_config_profile_explain_request_draft(
        sanitized_user_text="请解释当前配置",
        entrypoint_explicit_args={"allow_live_llm": True},
    )

    assert draft.entrypoint_explicit_args == {"allow_live_llm": True}

    with pytest.raises(ValueError, match="managed governance keys"):
        build_twf_plan_request_draft(
            sanitized_user_text="请给我方案",
            user_passthrough_parameters={"approval_ref": "user-controlled"},
        )


def test_request_draft_rejects_runtime_objects_and_raw_metadata() -> None:
    with pytest.raises(ValueError, match="forbidden runtime keys"):
        build_twf_plan_request_draft(
            sanitized_user_text="请给我方案",
            entrypoint_explicit_args={"argparse_namespace": "not allowed"},
        )

    with pytest.raises(ValueError):
        build_twf_plan_request_draft(
            sanitized_user_text="请给我方案",
            metadata={"raw_prompt": "不得进入 request draft"},
        )

    with pytest.raises(ValueError):
        build_twf_plan_request_draft(
            sanitized_user_text="请给我方案",
            route_summary={
                "runtime_object": {
                    "object_module": "runtime_container.controlled_adk_run_entry"
                }
            },
        )


def test_task_workflows_request_draft_has_no_runtime_or_channel_imports() -> None:
    source = (
        PACKAGE_ROOT
        / "src"
        / "cognition_task_workflows"
        / "_requests"
        / "drafts.py"
    ).read_text(encoding="utf-8")

    assert "from runtime_container" not in source
    assert "import runtime_container" not in source
    assert "from cognition_cli" not in source
    assert "import cognition_cli" not in source
    assert "from product_gateway" not in source
    assert "import product_gateway" not in source
    assert "import argparse" not in source


def test_task_workflows_package_flags_request_draft_candidate() -> None:
    pyproject = tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text())
    tool_config = pyproject["tool"]["cognition_task_workflows"]

    assert tool_config["request_draft_candidate_enabled"] is True
    assert tool_config["runtime_container_dependency_enabled"] is False
    assert tool_config["product_gateway_dependency_enabled"] is False
    assert tool_config["channel_adapter_dependency_enabled"] is False
