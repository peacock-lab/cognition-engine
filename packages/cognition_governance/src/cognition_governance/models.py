"""Internal governance model candidates for cognition_governance.

These models are internal candidates for the cognition_governance package.
They are not public system-wide contracts yet. Cross-module consumption must
go through the public contract layer after a separate promotion decision.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


GovernanceDecisionKind = Literal[
    "continue",
    "fix",
    "close",
    "release",
    "defer",
    "block",
    "need_evidence",
]

GovernanceOutcomeStatus = Literal[
    "open",
    "validated",
    "failed",
    "superseded",
]


class GovernanceCase(BaseModel):
    """A governance matter that requires judgement."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    case_type: str = Field(..., min_length=1)
    subject: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    policy_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GovernanceEvidence(BaseModel):
    """Evidence used by a governance case or decision."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(..., min_length=1)
    evidence_type: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)
    content_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GovernancePolicySet(BaseModel):
    """A named set of governance policies used for judgement."""

    model_config = ConfigDict(extra="forbid")

    policy_set_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    policies: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GovernanceDecision(BaseModel):
    """A governance decision made for a governance case."""

    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(..., min_length=1)
    case_id: str = Field(..., min_length=1)
    decision: GovernanceDecisionKind
    rationale: str = Field(..., min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    policy_set_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GovernanceOutcome(BaseModel):
    """Follow-up outcome for a governance decision."""

    model_config = ConfigDict(extra="forbid")

    outcome_id: str = Field(..., min_length=1)
    decision_id: str = Field(..., min_length=1)
    status: GovernanceOutcomeStatus = "open"
    summary: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
