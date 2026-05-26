import pytest
from pydantic import ValidationError

from config_contexts import (
    SkillCandidateFlags,
    SkillL1MetadataCandidate,
    SkillL2InstructionsCandidate,
    SkillL3ResourcesCandidate,
    SkillMetadataViewCandidate,
    SkillRegistryCompatibilityCandidate,
    SkillResourceRefCandidate,
)


def test_skill_metadata_view_candidate_expresses_l1_l2_l3_shape() -> None:
    view = SkillMetadataViewCandidate(
        l1_metadata=SkillL1MetadataCandidate(
            skill_id="skill.workflow.fragment.review",
            name="Workflow Fragment Review",
            description="Review reusable workflow fragments before implementation.",
            license="internal-candidate",
            compatibility="adk-2.0.0b1-observation",
            allowed_tools=("read_only_search",),
            tags=("workflow", "skill-candidate"),
            domains=("workflow_dynamic_workflows",),
            capabilities=("review", "fragment_selection"),
            source_ref="tasks/b1/302",
            skill_dir_ref="skills/workflow-fragment-review",
            skill_file_ref="skills/workflow-fragment-review/SKILL.md",
            adk_frontmatter_projection={"name": "Workflow Fragment Review"},
        ),
        l2_instructions=SkillL2InstructionsCandidate(
            instructions_summary="Explain how to review a reusable workflow fragment.",
            instructions_ref="skills/workflow-fragment-review/SKILL.md#instructions",
            instruction_format="markdown",
            intended_use="candidate review only",
            constraints=("do_not_execute", "do_not_load_runtime_tools"),
            prompt_or_instruction_packaging_notes=("future_agent_packaging",),
            adk_skill_instructions_projection="Skill.instructions candidate ref",
        ),
        l3_resources=SkillL3ResourcesCandidate(
            references=(
                SkillResourceRefCandidate(
                    ref="references/workflow-fragment.md",
                    media_type="text/markdown",
                    safety_class="reference_only",
                ),
            ),
            scripts=(
                SkillResourceRefCandidate(
                    ref="scripts/check_fragment.py",
                    safety_class="review_required",
                ),
            ),
            resource_refs=("references/workflow-fragment.md",),
            script_refs=("scripts/check_fragment.py",),
            script_safety_notes=("scripts are never executed in candidate view",),
            code_execution_required=True,
            adk_resources_projection="Resources.references/assets/scripts refs only",
            adk_script_projection="Script.src ref or digest only",
        ),
        trigger_sources=("workflow_dynamic_workflows", "cognition_governance_review"),
        safety_notes=("candidate view only",),
    )

    assert view.config_view_semantics == "candidate_only"
    assert view.l1_metadata.skill_id == "skill.workflow.fragment.review"
    assert view.l2_instructions.instruction_format == "markdown"
    assert view.l3_resources.code_execution_required is True
    assert view.candidate_flags.runtime_dependency_enabled is False
    assert view.candidate_flags.script_execution_enabled is False
    assert view.candidate_flags.raw_adk_object_included is False


@pytest.mark.parametrize(
    ("flag_name", "flag_value"),
    [
        ("candidate_only", False),
        ("observation_only", False),
        ("runtime_dependency_enabled", True),
        ("skill_toolset_runtime_enabled", True),
        ("skill_registry_runtime_enabled", True),
        ("github_main_runtime_dependency_enabled", True),
        ("public_contract_enabled", True),
        ("policy_execution_enabled", True),
        ("live_call_enabled", True),
        ("raw_adk_object_included", True),
        ("script_execution_enabled", True),
        ("external_resource_loading_enabled", True),
    ],
)
def test_skill_candidate_flags_reject_boundary_escalation(
    flag_name: str,
    flag_value: bool,
) -> None:
    with pytest.raises(ValidationError):
        SkillCandidateFlags(**{flag_name: flag_value})


def test_skill_registry_compatibility_keeps_runtime_dependencies_disabled() -> None:
    candidate = SkillRegistryCompatibilityCandidate(
        get_skill_mapping="skill_id may map to future get_skill",
        search_skills_mapping="L1 metadata may map to future search_skills",
        search_tool_description_mapping=(
            "description and instructions summary may map to future search"
        ),
    )

    assert candidate.registry_runtime_dependency_enabled is False
    assert candidate.github_main_runtime_dependency_enabled is False

    with pytest.raises(ValidationError):
        SkillRegistryCompatibilityCandidate(registry_runtime_dependency_enabled=True)

    with pytest.raises(ValidationError):
        SkillRegistryCompatibilityCandidate(
            github_main_runtime_dependency_enabled=True
        )


def test_skill_metadata_view_rejects_runtime_or_policy_execution() -> None:
    l1_metadata = SkillL1MetadataCandidate(
        skill_id="skill.agent.team.handoff",
        name="Agent Team Handoff",
        description="Candidate metadata for future agent handoff skills.",
    )

    with pytest.raises(ValidationError):
        SkillMetadataViewCandidate(
            l1_metadata=l1_metadata,
            runtime_execution_enabled=True,
        )

    with pytest.raises(ValidationError):
        SkillMetadataViewCandidate(
            l1_metadata=l1_metadata,
            policy_execution_enabled=True,
        )

    with pytest.raises(ValidationError):
        SkillMetadataViewCandidate(
            l1_metadata=l1_metadata,
            candidate_flags=SkillCandidateFlags(script_execution_enabled=True),
        )
