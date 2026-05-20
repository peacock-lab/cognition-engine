from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPO_ROOT / "packages" / "task_workflows" / "src"

sys.path.insert(0, str(SOURCE_ROOT))

from cognition_task_workflows._requests.registry import (  # noqa: E402
    TWF_PLAN_WORKFLOW_NAME,
    build_twf_plan_workflow_descriptor,
)
from cognition_task_workflows._skills.projection_context import (  # noqa: E402
    build_twf_skill_projection_status_summary,
    build_twf_skill_projection_read_context,
    twf_skill_projection_status_summary_status_dict,
    twf_skill_projection_read_context_status_dict,
)


def test_skill_projection_read_context_accepts_sanitized_dicts() -> None:
    descriptor = build_twf_plan_workflow_descriptor()
    projection = _projection()
    slot = _slot()

    read_context = build_twf_skill_projection_read_context(
        descriptor=descriptor,
        projections=(projection,),
        slot_references=(slot,),
        allowed_use_stage="workflow_planning_hint",
    )
    status = twf_skill_projection_read_context_status_dict(read_context)

    assert read_context.status == "available_candidate"
    assert read_context.workflow_name == TWF_PLAN_WORKFLOW_NAME
    assert read_context.projection_refs == (projection["projection_id"],)
    assert read_context.display_summaries == ("方案排版能力投影。",)
    assert read_context.runtime_enabled is False
    assert read_context.prompt_context_enabled is False
    assert read_context.public_schema_enabled is False
    assert status["metadata"]["read_context_only"] is True
    assert status["metadata"]["does_not_dispatch_runtime"] is True


def test_skill_projection_read_context_blocks_runtime_escalation() -> None:
    descriptor = build_twf_plan_workflow_descriptor()
    projection = {
        **_projection(),
        "runtime_enabled": True,
    }

    read_context = build_twf_skill_projection_read_context(
        descriptor=descriptor,
        projections=(projection,),
        slot_references=(_slot(),),
        allowed_use_stage="workflow_planning_hint",
    )

    assert read_context.status == "blocked_candidate"
    assert read_context.runtime_enabled is True
    assert "projection_runtime_enabled" in read_context.blocking_reasons


def test_skill_projection_read_context_blocks_raw_material_and_secret() -> None:
    descriptor = build_twf_plan_workflow_descriptor()
    projection = {
        **_projection(),
        "metadata": {"raw_skill_instructions": "do not expose", "api_key": "secret"},
    }

    read_context = build_twf_skill_projection_read_context(
        descriptor=descriptor,
        projections=(projection,),
        slot_references=(_slot(),),
        allowed_use_stage="workflow_planning_hint",
    )

    assert read_context.status == "blocked_candidate"
    assert (
        "projection:raw_skill_material_forbidden:raw_skill_instructions"
        in read_context.blocking_reasons
    )
    assert "projection:raw_secret_material_forbidden:api_key" in (
        read_context.blocking_reasons
    )


def test_skill_projection_status_summary_blocks_escalated_context() -> None:
    summary = build_twf_skill_projection_status_summary(
        projections=({**_projection(), "prompt_context_enabled": True},),
        slot_references=(_slot(),),
    )
    status = twf_skill_projection_status_summary_status_dict(summary)

    assert summary.status == "blocked"
    assert summary.prompt_context_enabled is True
    assert status["source"] == "cognition_task_workflows._skills.projection_context"
    assert status["metadata"]["does_not_inject_prompt_context"] is True


def _projection() -> dict[str, object]:
    return {
        "projection_id": "skill-capability-projection://skill.plan.formatting/capability.plan.formatting",
        "source_review_id": "skill-capability-review://skill.plan.formatting/capability.plan.formatting",
        "registry_name": "project_skills",
        "skill_id": "skill.plan.formatting",
        "capability_id": "capability.plan.formatting",
        "capability_name": "Plan Formatting",
        "projection_status_candidate": "approved_candidate",
        "display_summary": "方案排版能力投影。",
        "use_boundary": "仅作为 workflow planning hint，不加载 Skill。",
        "risk_level": "low",
        "tool_dependency_summary": (),
        "allowed_workflow_names": (TWF_PLAN_WORKFLOW_NAME,),
        "denied_workflow_names": (),
        "evidence_refs": ("evidence://skill-plan-formatting",),
        "sensitivity": "low",
        "confidence": "medium",
        "candidate_only": True,
        "runtime_enabled": False,
        "skill_file_loading_enabled": False,
        "resources_loading_enabled": False,
        "scripts_execution_enabled": False,
        "tool_exposure_enabled": False,
        "agent_runtime_enabled": False,
        "prompt_context_enabled": False,
        "workflow_registration_enabled": False,
        "public_schema_enabled": False,
        "metadata": {"sanitized_projection": True},
    }


def _slot() -> dict[str, object]:
    return {
        "slot_ref": "workflow-skill-slot://twf_plan_workflow/skill.plan.formatting",
        "workflow_name": TWF_PLAN_WORKFLOW_NAME,
        "workflow_version": "v0.7.0-candidate",
        "task_kind": "plan_design",
        "projection_id": _projection()["projection_id"],
        "skill_id": "skill.plan.formatting",
        "capability_id": "capability.plan.formatting",
        "reference_mode": "projection_summary_only",
        "allowed_use": ("workflow_planning_hint",),
        "forbidden_use": (
            "skill_runtime_loading",
            "script_execution",
            "tool_exposure",
            "agent_runtime",
            "public_schema",
        ),
        "slot_status_candidate": "active_candidate",
        "candidate_only": True,
        "runtime_enabled": False,
        "skill_file_loading_enabled": False,
        "resources_loading_enabled": False,
        "scripts_execution_enabled": False,
        "tool_exposure_enabled": False,
        "agent_runtime_enabled": False,
        "prompt_context_enabled": False,
        "public_schema_enabled": False,
        "metadata": {"reference_mode": "projection_summary_only"},
    }
