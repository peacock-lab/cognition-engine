from __future__ import annotations

import pytest
from pydantic import ValidationError

from cognition_evaluation import (
    ContractBoundarySnapshot,
    evaluate_contract_boundary,
    evaluation_summary_from_result,
)


def test_contract_boundary_passes_clean_snapshot() -> None:
    result = evaluate_contract_boundary(
        ContractBoundarySnapshot(
            contract_ref="evaluation://contract/architecture-boundary",
            contract_home="cognition_evaluation",
            expected_contract_home="cognition_evaluation",
        )
    )

    assert result.status == "passed"
    assert result.profile_ref is not None
    assert result.profile_ref.ref == "evaluation-profile://contract-boundary/v1"
    assert result.metadata["governance_decision"] is False

    summary = evaluation_summary_from_result(result)
    assert summary.status == "passed"
    assert summary.finding_count == 0


def test_contract_boundary_flags_wrong_home_and_helper_bypass() -> None:
    result = evaluate_contract_boundary(
        ContractBoundarySnapshot(
            contract_ref="product-gateway://response/internal-candidate",
            contract_home="packages/cli",
            expected_contract_home="schemas",
            implementation_helper_contracts=["ProductGatewayResponseDraft"],
            internal_candidates_publicized=["RuntimeFactEnvelope"],
        )
    )

    assert result.status == "failed"
    criteria = {finding.criterion for finding in result.findings}
    assert "contract_home_boundary" in criteria
    assert "anti_bypass_contract_review" in criteria
    assert "public_schema_threshold" in criteria


def test_contract_boundary_flags_missing_task_workflow_mapping() -> None:
    result = evaluate_contract_boundary(
        ContractBoundarySnapshot(
            contract_ref="product-level://answer-status",
            fields_without_task_api_mapping=["answer_trace_status", "opaque_state"],
            fields_without_workflow_runtime_mapping=["opaque_state"],
        )
    )

    assert result.status == "failed"
    failed_findings = [
        finding
        for finding in result.findings
        if finding.criterion == "task_workflow_semantic_mapping"
        and finding.status == "failed"
    ]
    assert failed_findings
    assert failed_findings[0].metadata["fields"] == ["opaque_state"]


def test_contract_boundary_flags_config_and_exit_mechanism_risks() -> None:
    result = evaluate_contract_boundary(
        ContractBoundarySnapshot(
            contract_ref="config://provider-profile",
            config_facts_without_context_contract=["gemma4_pro_local.max_tokens"],
            public_schema_without_stable_consumers=["RuntimeFactEnvelopeSchema"],
            legacy_aliases_without_exit=["task_workflows"],
        )
    )

    assert result.status == "failed"
    criteria = {finding.criterion for finding in result.findings}
    assert "config_context_ownership" in criteria
    assert "public_schema_threshold" in criteria
    assert "exit_mechanism_boundary" in criteria


def test_contract_boundary_rejects_raw_markers() -> None:
    with pytest.raises(ValidationError):
        ContractBoundarySnapshot(
            contract_ref="contract://bad",
            metadata={"bad_value": "system_prompt must not enter evaluation input"},
        )
