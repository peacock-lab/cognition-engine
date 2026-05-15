"""Governance-facing configuration contexts for Cognition Engine."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


GovernanceMode = Literal["advisory", "review_required", "blocking"]
GovernanceDecisionLevel = Literal["candidate", "human_review"]


class GovernanceConfigContext(BaseModel):
    """Configuration view consumed by cognition governance boundaries."""

    model_config = ConfigDict(extra="forbid")

    config_context_kind: Literal["governance_config"] = "governance_config"
    governance_profile: str = Field(default="default", min_length=1)
    enabled: bool = True
    mode: GovernanceMode = "advisory"
    decision_level: GovernanceDecisionLevel = "candidate"
    policy_refs: tuple[str, ...] = Field(default_factory=tuple)
    required_evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    block_on_violation: bool = False
    audit_required: bool = True
    custom_metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_governance_context(self) -> "GovernanceConfigContext":
        """Keep review/blocking semantics explicit."""

        if self.block_on_violation and self.mode != "blocking":
            raise ValueError("block_on_violation requires mode='blocking'.")
        if self.mode == "blocking" and self.decision_level != "human_review":
            raise ValueError("blocking mode requires decision_level='human_review'.")
        return self
