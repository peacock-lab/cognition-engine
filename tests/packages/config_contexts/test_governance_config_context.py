from __future__ import annotations

import pytest
from pydantic import ValidationError

from config_assembly.runtime import RuntimeConfigPayload
from config_contexts.governance import GovernanceConfigContext
from config_contexts.runtime_builder import build_runtime_config_contexts


def test_governance_config_context_defaults_to_advisory_candidate_view() -> None:
    context = GovernanceConfigContext()

    assert context.config_context_kind == "governance_config"
    assert context.governance_profile == "default"
    assert context.enabled is True
    assert context.mode == "advisory"
    assert context.decision_level == "candidate"
    assert context.policy_refs == ()
    assert context.block_on_violation is False


def test_governance_config_context_allows_explicit_blocking_review() -> None:
    context = GovernanceConfigContext(
        governance_profile="adk-runtime",
        mode="blocking",
        decision_level="human_review",
        policy_refs=("policy:runtime-run-config",),
        required_evidence_refs=("evidence:run-config",),
        block_on_violation=True,
        custom_metadata={"source": "test"},
    )

    assert context.policy_refs == ("policy:runtime-run-config",)
    assert context.required_evidence_refs == ("evidence:run-config",)
    assert context.custom_metadata == {"source": "test"}


def test_governance_config_context_rejects_implicit_blocking_semantics() -> None:
    with pytest.raises(ValidationError):
        GovernanceConfigContext(block_on_violation=True)

    with pytest.raises(ValidationError):
        GovernanceConfigContext(mode="blocking")


def test_runtime_config_context_builder_maps_optional_governance_section() -> None:
    payload = RuntimeConfigPayload(
        source_root="config",
        environment="test",
        base_file="config/base/runtime.yaml",
        payload={
            "runtime": {"runtime_name": "test-runtime"},
            "workflow_execution": {"workflow_name": "test-workflow"},
            "node_execution": {},
            "resume_policy": {},
            "event_policy": {},
            "artifact_policy": {},
            "adapter_selection": {},
            "governance": {
                "governance_profile": "runtime-governance",
                "mode": "review_required",
                "decision_level": "human_review",
                "policy_refs": ["policy:runtime"],
            },
        },
    )

    bundle = build_runtime_config_contexts(payload)

    assert bundle.governance.governance_profile == "runtime-governance"
    assert bundle.governance.mode == "review_required"
    assert bundle.governance.policy_refs == ("policy:runtime",)
