from __future__ import annotations

import re
from pathlib import Path

from cognition_governance import (
    AdkWorkflowRunnerGovernanceReview,
    review_adk_workflow_runner_evidence,
)
from observability_hub import AdkWorkflowRunnerEvidence


REPO_ROOT = Path(__file__).resolve().parents[3]
GOVERNANCE_SOURCE_ROOT = REPO_ROOT / "packages" / "cognition_governance" / "src"
OBSERVABILITY_BRIDGE = (
    GOVERNANCE_SOURCE_ROOT / "cognition_governance" / "observability_bridge.py"
)


def _normal_evidence() -> AdkWorkflowRunnerEvidence:
    return AdkWorkflowRunnerEvidence(
        evidence_id="evidence-adk2-review-001",
        source="observability_hub.adk_workflow_runner_evidence",
        runtime_kind="adk2_workflow_runner",
        runtime_id="runtime-adk2-review-001",
        workflow_id="workflow-adk2-review-001",
        workflow_name="adk2-review-workflow",
        status="success",
        app_name="adk2-review-app",
        user_id="adk2-review-user",
        assembly_options={
            "service_bundle_options": {"source": "in_memory"},
            "run_config_options": {
                "mapped_fields": ["max_llm_calls", "custom_metadata"],
                "unmapped_fields": ["tool_thread_pool_config"],
            },
        },
        service_bundle={
            "artifact_service": {"adk_service_type": "InMemoryArtifactService"},
            "session_service": {"adk_service_type": "InMemorySessionService"},
        },
        run_config={
            "mapped_fields": ["max_llm_calls", "custom_metadata"],
            "unmapped_fields": ["tool_thread_pool_config"],
            "custom_metadata_keys": ["source"],
            "max_llm_calls": 17,
        },
        artifact_summary={
            "artifact_count": 1,
            "artifact_ids": ["review-output.txt"],
            "versions": [0],
        },
        session_summary={
            "session_id": "session-adk2-review-001",
            "event_count": 2,
            "adk_invocation_id": "adk-inv-review-001",
        },
        event_summary={
            "event_count": 2,
            "node_paths": ["adk2_review_workflow@1/review_node@1"],
            "authors": ["review_node"],
            "has_error": False,
        },
        metadata_keys=["workflow_service", "run_config"],
        observability_candidate="observability_hub.adk_workflow_runner_intake",
        contract_candidate_notes=["Candidate evidence only; not a public contract."],
        created_at="2026-05-07T00:00:00Z",
    )


def test_review_adk_workflow_runner_evidence_accepts_observability_candidate() -> None:
    review = review_adk_workflow_runner_evidence(_normal_evidence())

    assert isinstance(review, AdkWorkflowRunnerGovernanceReview)
    assert review.evidence_id == "evidence-adk2-review-001"
    assert review.workflow_name == "adk2-review-workflow"
    assert review.status == "success"
    assert review.risk_level == "low"
    assert {finding.code for finding in review.findings} == {
        "ADK2_WORKFLOW_RUNNER_CHAIN_OBSERVED",
        "RUN_CONFIG_UNMAPPED_FIELDS_PRESENT",
    }
    assert all(finding.severity == "info" for finding in review.findings)
    assert review.required_followups == []
    assert any("no formal GovernanceDecision" in note for note in review.policy_candidate_notes)

    dumped = review.model_dump(mode="python")
    assert "google.adk" not in repr(dumped)
    assert "Runner(" not in repr(dumped)
    assert "RunConfig(" not in repr(dumped)


def test_review_adk_workflow_runner_evidence_flags_missing_metadata_and_warnings() -> None:
    evidence = _normal_evidence().model_dump(mode="python")
    evidence["assembly_options"] = {}
    evidence["service_bundle"] = {}
    evidence["run_config"] = {}
    evidence["artifact_summary"] = {"artifact_count": 0}
    evidence["session_summary"] = {}
    evidence["event_summary"] = {"event_count": 0}
    evidence["warnings"] = ["assembly_metadata was not provided; assembly facts are partial."]

    review = review_adk_workflow_runner_evidence(evidence)
    finding_codes = {finding.code for finding in review.findings}

    assert review.risk_level == "medium"
    assert "RUN_CONFIG_SUMMARY_MISSING" in finding_codes
    assert "SERVICE_BUNDLE_SUMMARY_MISSING" in finding_codes
    assert "ARTIFACT_LIFECYCLE_NOT_OBSERVED" in finding_codes
    assert "SESSION_LIFECYCLE_NOT_OBSERVED" in finding_codes
    assert "EVENT_LIFECYCLE_NOT_OBSERVED" in finding_codes
    assert "EVIDENCE_WARNING_REPORTED" in finding_codes
    assert review.required_followups


def test_review_adk_workflow_runner_evidence_consumes_lifecycle_summary() -> None:
    evidence = _normal_evidence().model_dump(mode="python")
    evidence["lifecycle_summary"] = {
        "summary_id": "adk-lifecycle-summary-evidence-adk2-review-001",
        "source": "observability_hub.adk_workflow_runner_evidence.lifecycle_summary",
        "runtime_id": "runtime-adk2-review-001",
        "workflow_id": "workflow-adk2-review-001",
        "workflow_name": "adk2-review-workflow",
        "status": "success",
        "artifacts": [
            {
                "artifact_ref": {"artifact_id": "review-output.txt", "name": "review-output.txt"},
                "operation": "set",
                "service_type_name": "InMemoryArtifactService",
                "metadata_keys": ["raw_artifact_delta"],
                "metadata": {"sanitized": True},
            }
        ],
        "session": {
            "session_id": "session-adk2-review-001",
            "app_name": "adk2-review-app",
            "user_id": "adk2-review-user",
            "event_count": 2,
            "service_type_name": "InMemorySessionService",
            "metadata": {"sanitized": True},
        },
        "events": {
            "event_count": 2,
            "event_types": ["node_completed"],
            "authors": ["review_node"],
            "node_paths": ["adk2_review_workflow@1/review_node@1"],
            "has_error": False,
            "metadata": {"sanitized": True},
        },
        "context_state": {
            "state_delta_count": 1,
            "state_delta_keys": ["counter"],
            "state_delta_entity_mode": "state_delta_contract_summary",
            "raw_state_values_included": False,
            "sanitized": True,
            "metadata": {"sanitized": True},
        },
        "candidate_only": True,
        "formal_decision_enabled": False,
        "policy_execution_enabled": False,
        "governance_outcome_enabled": False,
        "metadata": {
            "candidate_contract": "schemas.runtime.AdkLifecycleFactsSummary",
            "sanitized": True,
        },
    }

    review = review_adk_workflow_runner_evidence(evidence)

    assert "ADK_LIFECYCLE_SUMMARY_OBSERVED" in {
        finding.code for finding in review.findings
    }
    assert "CONTEXT_STATE_LIFECYCLE_FACTS_OBSERVED" in {
        finding.code for finding in review.findings
    }
    assert review.risk_level == "low"
    assert "google.adk" not in repr(review.model_dump(mode="python"))


def test_review_adk_workflow_runner_evidence_consumes_run_config_service_bundle_summary() -> None:
    evidence = _normal_evidence().model_dump(mode="python")
    evidence["run_config_service_bundle_summary"] = {
        "summary_id": "adk-run-config-service-bundle-summary-evidence-adk2-review-001",
        "source": (
            "observability_hub.adk_workflow_runner_evidence."
            "run_config_service_bundle_summary"
        ),
        "runtime_id": "runtime-adk2-review-001",
        "workflow_id": "workflow-adk2-review-001",
        "workflow_name": "adk2-review-workflow",
        "status": "success",
        "run_config": {
            "source": "observability_hub.adk_workflow_runner_evidence.run_config",
            "run_config_source": "assembly_options + workflow_result.metadata",
            "mapped_fields": ["max_llm_calls", "custom_metadata"],
            "unmapped_fields": ["tool_thread_pool_config"],
            "deferred_fields": ["tool_thread_pool_config"],
            "custom_metadata_keys": ["source"],
            "max_llm_calls": 17,
            "streaming_mode": "none",
            "adk_run_config_type": "RunConfig",
            "live_call_enabled": False,
            "no_live_mode": True,
            "call_attempted": False,
            "candidate_only": True,
            "formal_decision_enabled": False,
            "policy_execution_enabled": False,
            "governance_outcome_enabled": False,
            "metadata": {"sanitized": True},
        },
        "service_bundle": {
            "source": "observability_hub.adk_workflow_runner_evidence.service_bundle",
            "service_bundle_source": "in_memory",
            "persistence_stage": "runtime_fact_only",
            "persistence_strategy": "in_memory_or_provided_service_reference",
            "external_persistence_enabled": False,
            "artifact_service_present": True,
            "session_service_present": True,
            "artifact_service_type_name": "InMemoryArtifactService",
            "session_service_type_name": "InMemorySessionService",
            "capability_flags": [
                "artifact_service_present",
                "session_service_present",
            ],
            "candidate_only": True,
            "formal_decision_enabled": False,
            "policy_execution_enabled": False,
            "governance_outcome_enabled": False,
            "metadata": {"sanitized": True},
        },
        "candidate_only": True,
        "formal_decision_enabled": False,
        "policy_execution_enabled": False,
        "governance_outcome_enabled": False,
        "metadata": {
            "candidate_contract": "schemas.runtime.AdkRunConfigServiceBundleSummary",
            "sanitized": True,
        },
    }

    review = review_adk_workflow_runner_evidence(evidence)

    assert "ADK_RUN_CONFIG_SERVICE_BUNDLE_SUMMARY_OBSERVED" in {
        finding.code for finding in review.findings
    }
    assert review.risk_level == "low"
    assert "google.adk" not in repr(review.model_dump(mode="python"))
    assert "adk_adapter" not in repr(review.model_dump(mode="python"))


def test_review_adk_workflow_runner_evidence_consumes_graph_and_trace_summaries() -> None:
    evidence = _normal_evidence().model_dump(mode="python")
    evidence["graph_summary"] = _graph_summary()
    evidence["trace_summary"] = _trace_summary()

    review = review_adk_workflow_runner_evidence(evidence)
    finding_codes = {finding.code for finding in review.findings}

    assert "ADK_WORKFLOW_GRAPH_SUMMARY_OBSERVED" in finding_codes
    assert "ADK_WORKFLOW_TRACE_SUMMARY_OBSERVED" in finding_codes
    assert "ADK_WORKFLOW_GRAPH_SUMMARY_BOUNDARY_OPEN" not in finding_codes
    assert "ADK_WORKFLOW_TRACE_SUMMARY_BOUNDARY_OPEN" not in finding_codes
    assert review.risk_level == "low"
    assert "google.adk" not in repr(review.model_dump(mode="python"))
    assert "raw_event" not in repr(review.model_dump(mode="python"))


def test_review_adk_workflow_runner_evidence_flags_graph_and_trace_boundaries() -> None:
    evidence = _normal_evidence().model_dump(mode="python")
    graph_summary = _graph_summary()
    graph_summary["summary_only"] = False
    graph_summary["raw_graph_object_included"] = True
    trace_summary = _trace_summary()
    trace_summary["refs_only"] = False
    trace_summary["raw_payload_included"] = True
    evidence["graph_summary"] = graph_summary
    evidence["trace_summary"] = trace_summary

    review = review_adk_workflow_runner_evidence(evidence)
    findings_by_code = {finding.code: finding for finding in review.findings}

    assert review.risk_level == "medium"
    assert "ADK_WORKFLOW_GRAPH_SUMMARY_BOUNDARY_OPEN" in findings_by_code
    assert "graph_summary.summary_only" in findings_by_code[
        "ADK_WORKFLOW_GRAPH_SUMMARY_BOUNDARY_OPEN"
    ].evidence_path
    assert "ADK_WORKFLOW_TRACE_SUMMARY_BOUNDARY_OPEN" in findings_by_code
    assert "trace_summary.refs_only" in findings_by_code[
        "ADK_WORKFLOW_TRACE_SUMMARY_BOUNDARY_OPEN"
    ].evidence_path


def test_cognition_governance_review_source_keeps_adk_and_assembly_layers_out() -> None:
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+(?:google\.adk|adk_adapter|runtime_container|composition)\b",
        re.MULTILINE,
    )

    for source_path in GOVERNANCE_SOURCE_ROOT.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert forbidden_imports.search(source) is None, source_path

    bridge_source = OBSERVABILITY_BRIDGE.read_text(encoding="utf-8")
    assert "AdkWorkflowRunnerEvidence" not in bridge_source
    assert "adk_workflow_runner" not in bridge_source


def _graph_summary() -> dict[str, object]:
    return {
        "summary_id": "graph-summary-evidence-adk2-review-001",
        "source": "observability_hub.adk_workflow_runner_evidence.graph_summary",
        "runtime_id": "runtime-adk2-review-001",
        "workflow_id": "workflow-adk2-review-001",
        "workflow_name": "adk2-review-workflow",
        "node_paths": ["adk2_review_workflow@1/review_node@1"],
        "node_path_count": 1,
        "branch_ids": [],
        "has_branching": False,
        "graph_inferred_from": "event_summary.node_paths",
        "candidate_only": True,
        "summary_only": True,
        "refs_only": True,
        "raw_adk_object_included": False,
        "raw_graph_object_included": False,
    }


def _trace_summary() -> dict[str, object]:
    return {
        "source": "observability_hub.adk_workflow_runner_evidence.trace_summary",
        "event_count": 2,
        "event_ids": ["event-review-001"],
        "event_types": ["node_completed"],
        "invocation_ids": ["adk-inv-review-001"],
        "state_delta_refs": ["state-delta://counter"],
        "artifact_delta_refs": ["artifact-delta://review-output.txt"],
        "has_error": False,
        "trace_inferred_from": "event_summary",
        "candidate_only": True,
        "summary_only": True,
        "refs_only": True,
        "raw_event_included": False,
        "raw_payload_included": False,
    }
