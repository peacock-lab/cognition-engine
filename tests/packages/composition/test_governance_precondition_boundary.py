from __future__ import annotations

from pathlib import Path

import pytest

from composition.adk_workflow_runner_assembly import (
    GOVERNANCE_DECISION_METADATA_BLOCK_FIELD,
    GOVERNANCE_DECISION_METADATA_PRECONDITION_FIELD,
    GOVERNANCE_DECISION_SHAPE_FIELDS,
    evaluate_governance_assembly_precondition,
)


def test_governance_assembly_precondition_allows_missing_decision() -> None:
    precondition = evaluate_governance_assembly_precondition(None)

    assert precondition.allowed is True
    assert precondition.reason == "governance_decision_not_provided"


def test_governance_assembly_precondition_declares_stable_shape_fields() -> None:
    assert GOVERNANCE_DECISION_SHAPE_FIELDS == ("decision", "metadata")
    assert (
        GOVERNANCE_DECISION_METADATA_PRECONDITION_FIELD
        == "composition_precondition_allowed"
    )
    assert GOVERNANCE_DECISION_METADATA_BLOCK_FIELD == "block_on_violation"


def test_governance_assembly_precondition_blocks_denied_candidate_decision() -> None:
    precondition = evaluate_governance_assembly_precondition(
        {
            "decision": "need_evidence",
            "metadata": {
                "composition_precondition_allowed": False,
                "block_on_violation": True,
            },
        }
    )

    assert precondition.allowed is False
    assert precondition.reason == "governance_decision_precondition_denied"


def test_composition_source_does_not_import_cognition_governance() -> None:
    source_path = (
        Path(__file__).resolve().parents[3]
        / "packages"
        / "composition"
        / "src"
        / "composition"
        / "adk_workflow_runner_assembly.py"
    )
    source = source_path.read_text(encoding="utf-8")

    assert "import cognition_governance" not in source
    assert "from cognition_governance" not in source


def test_governance_assembly_precondition_uses_existing_decision_shape() -> None:
    from cognition_governance import GovernanceDecision

    decision = GovernanceDecision(
        decision_id="decision-001",
        case_id="case-001",
        decision="continue",
        rationale="Config boundary allows assembly.",
        metadata={"composition_precondition_allowed": True},
    )

    precondition = evaluate_governance_assembly_precondition(decision)

    assert precondition.allowed is True
    assert precondition.decision == "continue"


def test_governance_precondition_denial_is_available_to_runtime_builder(
    tmp_path,
) -> None:
    from composition.adk_workflow_runner_assembly import build_adk_workflow_runner_runtime
    from composition.runtime import RuntimeCompositionOptions

    config_root = tmp_path / "config"
    (config_root / "base").mkdir(parents=True)
    (config_root / "env").mkdir()
    (config_root / "base" / "runtime.yaml").write_text(
        """
runtime:
  runtime_name: config-runtime
workflow_execution:
  workflow_name: config-workflow
node_execution: {}
resume_policy: {}
event_policy: {}
artifact_policy: {}
adapter_selection: {}
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        build_adk_workflow_runner_runtime(
            options=RuntimeCompositionOptions(
                config_root=config_root,
                environment="local",
            ),
            workflow=object(),
            governance_decision={
                "decision": "block",
                "metadata": {"composition_precondition_allowed": False},
            },
        )
