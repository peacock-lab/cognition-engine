"""Candidate-only Skill metadata views.

These models describe possible ADK Skills metadata shapes without loading
Skill files, creating SkillToolset instances, or depending on google.adk.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from config_contexts.governance_candidate import GovernanceCandidateConfigBaseModel


class SkillCandidateFlags(BaseModel):
    """Non-executing boundary flags for Skill metadata candidates."""

    model_config = ConfigDict(extra="forbid")

    candidate_only: bool = True
    observation_only: bool = True
    runtime_dependency_enabled: bool = False
    skill_toolset_runtime_enabled: bool = False
    skill_registry_runtime_enabled: bool = False
    github_main_runtime_dependency_enabled: bool = False
    public_contract_enabled: bool = False
    policy_execution_enabled: bool = False
    live_call_enabled: bool = False
    raw_adk_object_included: bool = False
    script_execution_enabled: bool = False
    external_resource_loading_enabled: bool = False

    @model_validator(mode="after")
    def validate_candidate_flags(self) -> "SkillCandidateFlags":
        if not self.candidate_only:
            raise ValueError("candidate_only must remain true.")
        if not self.observation_only:
            raise ValueError("observation_only must remain true.")
        false_flags = {
            "runtime_dependency_enabled": self.runtime_dependency_enabled,
            "skill_toolset_runtime_enabled": self.skill_toolset_runtime_enabled,
            "skill_registry_runtime_enabled": self.skill_registry_runtime_enabled,
            "github_main_runtime_dependency_enabled": (
                self.github_main_runtime_dependency_enabled
            ),
            "public_contract_enabled": self.public_contract_enabled,
            "policy_execution_enabled": self.policy_execution_enabled,
            "live_call_enabled": self.live_call_enabled,
            "raw_adk_object_included": self.raw_adk_object_included,
            "script_execution_enabled": self.script_execution_enabled,
            "external_resource_loading_enabled": self.external_resource_loading_enabled,
        }
        enabled = [name for name, value in false_flags.items() if value]
        if enabled:
            raise ValueError(
                "Skill candidate flags must remain disabled: " + ", ".join(enabled)
            )
        return self


class SkillL1MetadataCandidate(BaseModel):
    """Low-cost discovery metadata for a Skill candidate."""

    model_config = ConfigDict(extra="forbid")

    skill_id: str
    name: str
    description: str
    license: str | None = None
    compatibility: str | None = None
    allowed_tools: tuple[str, ...] = Field(default_factory=tuple)
    tags: tuple[str, ...] = Field(default_factory=tuple)
    domains: tuple[str, ...] = Field(default_factory=tuple)
    capabilities: tuple[str, ...] = Field(default_factory=tuple)
    source_ref: str | None = None
    skill_dir_ref: str | None = None
    skill_file_ref: str | None = None
    adk_frontmatter_projection: dict[str, str] = Field(default_factory=dict)


class SkillL2InstructionsCandidate(BaseModel):
    """Instruction summary and references for a Skill candidate."""

    model_config = ConfigDict(extra="forbid")

    instructions_summary: str | None = None
    instructions_ref: str | None = None
    instruction_format: Literal[
        "markdown",
        "text",
        "structured_markdown",
        "unknown",
    ] = "unknown"
    intended_use: str | None = None
    constraints: tuple[str, ...] = Field(default_factory=tuple)
    prompt_or_instruction_packaging_notes: tuple[str, ...] = Field(
        default_factory=tuple
    )
    adk_skill_instructions_projection: str | None = None


class SkillResourceRefCandidate(BaseModel):
    """Reference-only resource entry for a Skill candidate."""

    model_config = ConfigDict(extra="forbid")

    ref: str
    description: str | None = None
    media_type: str | None = None
    digest: str | None = None
    safety_class: Literal[
        "none",
        "reference_only",
        "review_required",
        "unsafe_or_unknown",
    ] = "reference_only"


class SkillL3ResourcesCandidate(BaseModel):
    """Resource and script references for a Skill candidate."""

    model_config = ConfigDict(extra="forbid")

    references: tuple[SkillResourceRefCandidate, ...] = Field(default_factory=tuple)
    assets: tuple[SkillResourceRefCandidate, ...] = Field(default_factory=tuple)
    scripts: tuple[SkillResourceRefCandidate, ...] = Field(default_factory=tuple)
    resource_refs: tuple[str, ...] = Field(default_factory=tuple)
    asset_refs: tuple[str, ...] = Field(default_factory=tuple)
    script_refs: tuple[str, ...] = Field(default_factory=tuple)
    script_safety_notes: tuple[str, ...] = Field(default_factory=tuple)
    code_execution_required: bool = False
    adk_resources_projection: str | None = None
    adk_script_projection: str | None = None


class SkillAdkProjectionCandidate(BaseModel):
    """Future ADK object projection notes without raw ADK objects."""

    model_config = ConfigDict(extra="forbid")

    frontmatter_projection_notes: str | None = None
    instructions_projection_notes: str | None = None
    resources_projection_notes: str | None = None
    script_projection_notes: str | None = None


class SkillRegistryCompatibilityCandidate(BaseModel):
    """Future SkillRegistry compatibility notes without registry runtime use."""

    model_config = ConfigDict(extra="forbid")

    get_skill_mapping: str | None = None
    search_skills_mapping: str | None = None
    search_tool_description_mapping: str | None = None
    list_skills_mapping: str | None = None
    load_skill_mapping: str | None = None
    load_skill_resource_mapping: str | None = None
    registry_runtime_dependency_enabled: bool = False
    github_main_runtime_dependency_enabled: bool = False

    @model_validator(mode="after")
    def validate_registry_candidate(self) -> "SkillRegistryCompatibilityCandidate":
        if self.registry_runtime_dependency_enabled:
            raise ValueError("registry_runtime_dependency_enabled must remain false.")
        if self.github_main_runtime_dependency_enabled:
            raise ValueError(
                "github_main_runtime_dependency_enabled must remain false."
            )
        return self


class SkillMetadataViewCandidate(GovernanceCandidateConfigBaseModel):
    """Candidate-only metadata view for ADK Skills alignment."""

    candidate_flags: SkillCandidateFlags = Field(default_factory=SkillCandidateFlags)
    l1_metadata: SkillL1MetadataCandidate
    l2_instructions: SkillL2InstructionsCandidate = Field(
        default_factory=SkillL2InstructionsCandidate
    )
    l3_resources: SkillL3ResourcesCandidate = Field(
        default_factory=SkillL3ResourcesCandidate
    )
    adk_projection: SkillAdkProjectionCandidate = Field(
        default_factory=SkillAdkProjectionCandidate
    )
    registry_compatibility: SkillRegistryCompatibilityCandidate = Field(
        default_factory=SkillRegistryCompatibilityCandidate
    )
    trigger_sources: tuple[
        Literal[
            "workflow_dynamic_workflows",
            "runner_event_artifact",
            "agent_teams_multi_agent",
            "product_gateway_read_only",
            "cognition_agent_read_only",
            "cognition_governance_review",
        ],
        ...,
    ] = Field(default_factory=tuple)
    safety_notes: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_skill_metadata_candidate(self) -> "SkillMetadataViewCandidate":
        if self.policy_execution_enabled:
            raise ValueError("policy_execution_enabled must remain false.")
        return self
