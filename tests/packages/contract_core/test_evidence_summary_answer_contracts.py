from __future__ import annotations

import re
from pathlib import Path

from behavior_contracts.evidence_summary_answer import (
    EvidenceSummaryAnswerFollowUpSeedGuard,
    EvidenceSummaryAnswerRunGuard,
    build_evidence_summary_answer_outcome_observation_readonly_facts,
    build_evidence_summary_answer_outcome_observation_readonly_public_refs,
    evidence_summary_answer_outcome_observation_readonly_public_refs_status_dict,
    validate_evidence_summary_answer_outcome_observation_readonly_public_refs,
)
from contract_core import evidence_summary_answer
from schemas.evidence_summary_answer import (
    EvidenceSummaryAnswerFollowUpSeedSchema,
    EvidenceSummaryAnswerRunSchema,
    validate_evidence_summary_answer_follow_up_seed,
    validate_evidence_summary_answer_run,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_CORE_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "contract_core" / "src" / "contract_core"
)
_OBSERVATION_REF = "evidence-summary-answer-outcome-observation://obs-1"
_EVIDENCE_REF = "evidence://external-readonly/request-1/fetch-1"
_DIGEST_REF = "governed-evidence-digest://request-1/digest-1"


def test_contract_core_reexports_evidence_summary_answer_contracts() -> None:
    assert (
        evidence_summary_answer.build_evidence_summary_answer_outcome_observation_readonly_facts
        is build_evidence_summary_answer_outcome_observation_readonly_facts
    )
    assert (
        evidence_summary_answer.build_evidence_summary_answer_outcome_observation_readonly_public_refs
        is build_evidence_summary_answer_outcome_observation_readonly_public_refs
    )
    assert (
        evidence_summary_answer.evidence_summary_answer_outcome_observation_readonly_public_refs_status_dict
        is evidence_summary_answer_outcome_observation_readonly_public_refs_status_dict
    )
    assert (
        evidence_summary_answer.validate_evidence_summary_answer_outcome_observation_readonly_public_refs
        is validate_evidence_summary_answer_outcome_observation_readonly_public_refs
    )
    assert (
        evidence_summary_answer.EvidenceSummaryAnswerFollowUpSeedGuard
        is EvidenceSummaryAnswerFollowUpSeedGuard
    )
    assert (
        evidence_summary_answer.EvidenceSummaryAnswerFollowUpSeedSchema
        is EvidenceSummaryAnswerFollowUpSeedSchema
    )
    assert evidence_summary_answer.EvidenceSummaryAnswerRunGuard is EvidenceSummaryAnswerRunGuard
    assert evidence_summary_answer.EvidenceSummaryAnswerRunSchema is EvidenceSummaryAnswerRunSchema
    assert (
        evidence_summary_answer.validate_evidence_summary_answer_run
        is validate_evidence_summary_answer_run
    )
    assert (
        evidence_summary_answer.validate_evidence_summary_answer_follow_up_seed
        is validate_evidence_summary_answer_follow_up_seed
    )


def test_contract_core_facade_builds_status_dict() -> None:
    facts = (
        evidence_summary_answer.build_evidence_summary_answer_outcome_observation_readonly_facts(
            observation_candidate_ids=("obs-1",),
            request_ids=("request-1",),
            result_statuses=("success",),
            external_readonly_evidence_refs=(_EVIDENCE_REF,),
            governed_evidence_digest_refs=(_DIGEST_REF,),
            schema_validation_passed=True,
            guard_validation_passed=True,
        )
    )
    public_refs = (
        evidence_summary_answer.build_evidence_summary_answer_outcome_observation_readonly_public_refs(
            evidence_summary_answer_outcome_observation_refs=(_OBSERVATION_REF,),
            external_readonly_evidence_refs=(_EVIDENCE_REF,),
            governed_evidence_digest_refs=(_DIGEST_REF,),
            facts=facts,
        )
    )
    status = (
        evidence_summary_answer.evidence_summary_answer_outcome_observation_readonly_public_refs_status_dict(
            public_refs
        )
    )

    assert status["payload_type"] == (
        "evidence_summary_answer_outcome_observation_readonly_public_refs"
    )
    assert status["readonly"] is True


def test_contract_core_evidence_summary_answer_facade_is_thin() -> None:
    source = (CONTRACT_CORE_SOURCE_ROOT / "evidence_summary_answer.py").read_text(
        encoding="utf-8"
    )
    init_source = (CONTRACT_CORE_SOURCE_ROOT / "__init__.py").read_text(
        encoding="utf-8"
    )
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:observability_hub|composition|product_gateway|"
        r"cognition_operation_flows|cognition_cli|runtime_container|"
        r"external_readonly|google\.adk|litellm|urllib\.request|requests|httpx)\b",
        re.MULTILINE,
    )

    assert "from behavior_contracts.evidence_summary_answer import" in source
    assert "evidence_summary_answer" in init_source
    assert "dataclass" not in source
    assert "def " not in source
    assert "read_text" not in source
    assert "write_text" not in source
    assert "mkdir" not in source
    assert forbidden_imports.search(source) is None
