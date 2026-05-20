from __future__ import annotations

import sys
from pathlib import Path

PACKAGE_SRC = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "cognition_governance"
    / "src"
)
sys.path.insert(0, str(PACKAGE_SRC))

from cognition_governance import (  # noqa: E402
    GovernanceCase,
    GovernanceDecision,
    GovernanceEvidence,
    GovernanceOutcome,
    GovernancePolicySet,
)


def test_evidence_bundle_can_be_modeled_as_governance_evidence_source() -> None:
    case = GovernanceCase(
        case_id="observability-evidence-001",
        title="Review observability evidence bundle before governance decision",
        case_type="evidence_mapping_review",
        subject="EvidenceBundle to GovernanceEvidence mapping",
        context={
            "producer": "observability_hub",
            "source_objects": [
                "EvidenceBundle",
                "RunRecord",
                "EventTrace",
                "ArtifactManifest",
            ],
            "mapping_rule": (
                "observability_hub keeps runtime facts; cognition_governance "
                "summarizes them as GovernanceEvidence for judgement."
            ),
        },
        evidence_refs=["evidence-bundle-summary"],
        policy_refs=["policy-observability-evidence-mapping"],
        metadata={
            "tracking_source": "cognition_governance roadmap",
            "follow_up": "observability evidence mapping and public contract promotion",
        },
    )

    evidence = GovernanceEvidence(
        evidence_id="evidence-bundle-summary",
        evidence_type="observability_evidence_bundle",
        source="observability_hub.EvidenceBundle",
        summary=(
            "The evidence bundle contains a run record, event trace, and "
            "artifact manifest that can support a governance decision."
        ),
        content_ref="observability_hub:bundle-001",
        metadata={
            "bundle_id": "bundle-001",
            "run_record_id": "run-001",
            "event_trace_id": "trace-001",
            "artifact_manifest_id": "artifact-manifest-001",
            "producer": "observability_hub",
            "is_public_contract": False,
        },
    )

    policy_set = GovernancePolicySet(
        policy_set_id="policy-observability-evidence-mapping",
        name="Observability evidence mapping policy",
        policies=[
            "Observability facts remain owned by observability_hub.",
            "GovernanceEvidence may reference summarized observability facts.",
            "EvidenceBundle is not a public contract unless promoted separately.",
        ],
    )

    decision = GovernanceDecision(
        decision_id="decision-observability-evidence-001",
        case_id=case.case_id,
        decision="continue",
        rationale=(
            "The observability evidence bundle can be referenced as a "
            "GovernanceEvidence source without migrating observability_hub "
            "models into cognition_governance."
        ),
        evidence_ids=[evidence.evidence_id],
        policy_set_id=policy_set.policy_set_id,
        metadata={
            "mapping_confirmed": True,
            "migrate_observability_models": False,
        },
    )

    outcome = GovernanceOutcome(
        outcome_id="outcome-observability-evidence-001",
        decision_id=decision.decision_id,
        status="validated",
        summary=(
            "EvidenceBundle to GovernanceEvidence mapping was validated as "
            "a sample-level relationship."
        ),
        metadata={
            "next_step": (
                "keep observability evidence mapping tracked in the active roadmap"
            )
        },
    )

    assert case.context["producer"] == "observability_hub"
    assert evidence.evidence_type == "observability_evidence_bundle"
    assert evidence.metadata["is_public_contract"] is False
    assert evidence.metadata["run_record_id"] == "run-001"
    assert decision.decision == "continue"
    assert decision.metadata["migrate_observability_models"] is False
    assert outcome.status == "validated"


def test_run_record_event_trace_and_artifact_manifest_can_be_referenced_separately() -> None:
    run_record_evidence = GovernanceEvidence(
        evidence_id="evidence-run-record",
        evidence_type="observability_run_record",
        source="observability_hub.RunRecord",
        summary="RunRecord summarizes runtime execution facts.",
        content_ref="observability_hub:run-001",
        metadata={
            "run_id": "run-001",
            "status": "completed",
        },
    )

    event_trace_evidence = GovernanceEvidence(
        evidence_id="evidence-event-trace",
        evidence_type="observability_event_trace",
        source="observability_hub.EventTrace",
        summary="EventTrace summarizes ordered runtime events.",
        content_ref="observability_hub:trace-001",
        metadata={
            "trace_id": "trace-001",
            "event_count": 3,
        },
    )

    artifact_manifest_evidence = GovernanceEvidence(
        evidence_id="evidence-artifact-manifest",
        evidence_type="observability_artifact_manifest",
        source="observability_hub.ArtifactManifest",
        summary="ArtifactManifest summarizes generated artifacts.",
        content_ref="observability_hub:artifact-manifest-001",
        metadata={
            "artifact_manifest_id": "artifact-manifest-001",
            "artifact_count": 2,
        },
    )

    assert run_record_evidence.metadata["status"] == "completed"
    assert event_trace_evidence.metadata["event_count"] == 3
    assert artifact_manifest_evidence.metadata["artifact_count"] == 2


def test_observability_mapping_sample_round_trips_metadata() -> None:
    evidence = GovernanceEvidence(
        evidence_id="evidence-observability-roundtrip",
        evidence_type="observability_evidence_bundle",
        source="observability_hub.EvidenceBundle",
        summary="Round-trip sample for observability evidence metadata.",
        content_ref="observability_hub:bundle-002",
        metadata={
            "bundle_id": "bundle-002",
            "source_objects": [
                "RunRecord",
                "EventTrace",
                "ArtifactManifest",
            ],
        },
    )

    dumped = evidence.model_dump()
    restored = GovernanceEvidence.model_validate(dumped)

    assert restored == evidence
    assert restored.metadata["source_objects"] == [
        "RunRecord",
        "EventTrace",
        "ArtifactManifest",
    ]
