from __future__ import annotations

import re
from pathlib import Path

from cognition_governance import (
    ADK_WORKFLOW_RUNNER_CASE_TYPE,
    ADK_WORKFLOW_RUNNER_EVIDENCE_TYPE,
    AdkWorkflowRunnerGovernanceMappingResult,
    GovernanceCase,
    GovernanceEvidence,
    map_adk_workflow_runner_evidence_to_governance_evidence,
    map_adk_workflow_runner_governance_package,
    map_adk_workflow_runner_review_to_governance_case,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
GOVERNANCE_SOURCE_ROOT = REPO_ROOT / "packages" / "cognition_governance" / "src"
OBSERVABILITY_BRIDGE = (
    GOVERNANCE_SOURCE_ROOT / "cognition_governance" / "observability_bridge.py"
)


def _evidence_candidate() -> dict[str, object]:
    return {
        "evidence_id": "evidence-adk2-mapping-001",
        "source": "observability_hub.adk_workflow_runner_evidence",
        "runtime_kind": "adk2_workflow_runner",
        "runtime_id": "runtime-adk2-mapping-001",
        "workflow_id": "workflow-adk2-mapping-001",
        "workflow_name": "adk2-mapping-workflow",
        "status": "success",
        "app_name": "adk2-mapping-app",
        "user_id": "adk2-mapping-user",
        "assembly_options": {
            "service_bundle_options": {"source": "in_memory"},
            "run_config_options": {
                "mapped_fields": ["max_llm_calls"],
                "unmapped_fields": ["tool_thread_pool_config"],
            },
            "raw_runtime_object": {
                "object_type": "Runner",
                "object_module": "google.adk.runners",
            },
        },
        "service_bundle": {
            "artifact_service": {
                "adk_service_type": "InMemoryArtifactService",
                "raw_service": {
                    "object_type": "ArtifactService",
                    "object_module": "google.adk.artifacts",
                },
            },
            "session_service": {"adk_service_type": "InMemorySessionService"},
        },
        "run_config": {
            "source": "assembly_options + workflow_result.metadata",
            "mapped_fields": ["max_llm_calls"],
            "unmapped_fields": ["tool_thread_pool_config"],
            "custom_metadata_keys": ["source"],
            "max_llm_calls": 17,
            "streaming_mode": "none",
            "adk_run_config_type": "RunConfig",
        },
        "artifact_summary": {
            "artifact_count": 1,
            "artifact_ids": ["artifact-001"],
            "artifact_names": ["output.txt"],
            "versions": [0],
            "has_artifacts": True,
        },
        "session_summary": {
            "session_id": "session-adk2-mapping-001",
            "app_name": "adk2-mapping-app",
            "user_id": "adk2-mapping-user",
            "event_count": 2,
        },
        "event_summary": {
            "event_count": 2,
            "node_paths": ["workflow@1/node@1"],
            "authors": ["node"],
            "has_error": False,
        },
        "lifecycle_summary": {
            "summary_id": "adk-lifecycle-summary-evidence-adk2-mapping-001",
            "source": "observability_hub.adk_workflow_runner_evidence.lifecycle_summary",
            "runtime_id": "runtime-adk2-mapping-001",
            "workflow_id": "workflow-adk2-mapping-001",
            "workflow_name": "adk2-mapping-workflow",
            "status": "success",
            "artifacts": [
                {
                    "artifact_ref": {"artifact_id": "artifact-001", "name": "output.txt"},
                    "operation": "set",
                    "service_type_name": "InMemoryArtifactService",
                    "metadata": {"sanitized": True},
                }
            ],
            "session": {
                "session_id": "session-adk2-mapping-001",
                "app_name": "adk2-mapping-app",
                "user_id": "adk2-mapping-user",
                "event_count": 2,
                "service_type_name": "InMemorySessionService",
                "metadata": {"sanitized": True},
            },
            "events": {
                "event_count": 2,
                "event_types": ["node_completed"],
                "node_paths": ["workflow@1/node@1"],
                "authors": ["node"],
                "has_error": False,
                "metadata": {"sanitized": True},
            },
            "candidate_only": True,
            "formal_decision_enabled": False,
            "policy_execution_enabled": False,
            "governance_outcome_enabled": False,
            "metadata": {"sanitized": True},
        },
        "run_config_service_bundle_summary": {
            "summary_id": "adk-run-config-service-bundle-summary-evidence-adk2-mapping-001",
            "source": (
                "observability_hub.adk_workflow_runner_evidence."
                "run_config_service_bundle_summary"
            ),
            "runtime_id": "runtime-adk2-mapping-001",
            "workflow_id": "workflow-adk2-mapping-001",
            "workflow_name": "adk2-mapping-workflow",
            "status": "success",
            "run_config": {
                "source": "observability_hub.adk_workflow_runner_evidence.run_config",
                "run_config_source": "assembly_options + workflow_result.metadata",
                "mapped_fields": ["max_llm_calls"],
                "unmapped_fields": ["tool_thread_pool_config"],
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
            "metadata": {"sanitized": True},
        },
        "graph_summary": {
            "summary_id": "graph-summary-evidence-adk2-mapping-001",
            "source": "observability_hub.adk_workflow_runner_evidence.graph_summary",
            "runtime_id": "runtime-adk2-mapping-001",
            "workflow_id": "workflow-adk2-mapping-001",
            "workflow_name": "adk2-mapping-workflow",
            "node_paths": ["workflow@1/node@1"],
            "node_path_count": 1,
            "branch_ids": [],
            "has_branching": False,
            "graph_inferred_from": "event_summary.node_paths",
            "candidate_only": True,
            "summary_only": True,
            "refs_only": True,
            "raw_adk_object_included": False,
            "raw_graph_object_included": False,
        },
        "trace_summary": {
            "source": "observability_hub.adk_workflow_runner_evidence.trace_summary",
            "event_count": 2,
            "event_ids": ["event-mapping-001"],
            "event_types": ["node_completed"],
            "invocation_ids": ["adk-inv-mapping-001"],
            "state_delta_refs": ["state-delta://mapping"],
            "artifact_delta_refs": ["artifact-delta://artifact-001"],
            "has_error": False,
            "trace_inferred_from": "event_summary",
            "candidate_only": True,
            "summary_only": True,
            "refs_only": True,
            "raw_event_included": False,
            "raw_payload_included": False,
        },
        "metadata_keys": ["workflow_service", "raw_runtime_object"],
        "observability_candidate": "observability_hub.adk_workflow_runner_intake",
        "contract_candidate_notes": [
            "Candidate evidence only; not a public contract.",
        ],
        "warnings": [],
        "created_at": "2026-05-07T00:00:00Z",
    }


def _review_candidate() -> dict[str, object]:
    return {
        "review_id": "review-adk2-mapping-001",
        "source": "cognition_governance.adk_workflow_runner_review",
        "evidence_id": "evidence-adk2-mapping-001",
        "workflow_name": "adk2-mapping-workflow",
        "status": "success",
        "risk_level": "low",
        "findings": [
            {
                "code": "ADK2_WORKFLOW_RUNNER_CHAIN_OBSERVED",
                "severity": "info",
                "message": "ADK2 WorkflowRunner evidence candidate was observed.",
                "evidence_path": "runtime_kind",
                "recommendation": "Keep this evidence as a candidate governance input.",
            }
        ],
        "required_followups": [],
        "policy_candidate_notes": [
            "Review candidate only; no formal GovernanceDecision is produced."
        ],
        "contract_candidate_notes": [
            "Promotion to public contract requires a separate decision."
        ],
        "config_context_candidate_notes": [
            "No config_assembly or config_contexts integration is performed."
        ],
        "created_at": "2026-05-07T00:00:00Z",
    }


def test_maps_evidence_candidate_dict_to_governance_evidence() -> None:
    governance_evidence = map_adk_workflow_runner_evidence_to_governance_evidence(
        _evidence_candidate()
    )

    assert isinstance(governance_evidence, GovernanceEvidence)
    assert governance_evidence.evidence_id == "evidence-adk2-mapping-001"
    assert governance_evidence.evidence_type == ADK_WORKFLOW_RUNNER_EVIDENCE_TYPE
    assert governance_evidence.content_ref is None
    assert "adk2-mapping-workflow" in governance_evidence.summary
    assert governance_evidence.metadata["run_config"]["mapped_fields"] == [
        "max_llm_calls"
    ]
    assert governance_evidence.metadata["service_bundle"]["source"] == "in_memory"
    assert governance_evidence.metadata["artifact_summary"]["artifact_count"] == 1
    assert governance_evidence.metadata["session_summary"]["session_id"] == (
        "session-adk2-mapping-001"
    )
    assert governance_evidence.metadata["event_summary"]["event_count"] == 2
    assert governance_evidence.metadata["lifecycle_summary"]["candidate_only"] is True
    assert governance_evidence.metadata["lifecycle_summary"]["artifacts"][0][
        "artifact_ref"
    ]["artifact_id"] == "artifact-001"
    assert governance_evidence.metadata["run_config_service_bundle_summary"][
        "run_config"
    ]["live_call_enabled"] is False
    assert governance_evidence.metadata["run_config_service_bundle_summary"][
        "service_bundle"
    ]["service_bundle_source"] == "in_memory"
    assert governance_evidence.metadata["graph_summary"]["node_path_count"] == 1
    assert governance_evidence.metadata["graph_summary"]["candidate_only"] is True
    assert governance_evidence.metadata["trace_summary"]["event_count"] == 2
    assert governance_evidence.metadata["trace_summary"]["raw_payload_included"] is False
    assert "assembly_options" not in governance_evidence.metadata
    assert "metadata_keys" not in governance_evidence.metadata
    assert "google.adk" not in repr(governance_evidence.model_dump(mode="python"))


def test_maps_review_candidate_dict_to_governance_case() -> None:
    governance_case = map_adk_workflow_runner_review_to_governance_case(
        _review_candidate(),
        evidence_ref="evidence-adk2-mapping-001",
    )

    assert isinstance(governance_case, GovernanceCase)
    assert governance_case.case_id == "review-adk2-mapping-001"
    assert governance_case.case_type == ADK_WORKFLOW_RUNNER_CASE_TYPE
    assert governance_case.subject == "adk2-mapping-workflow"
    assert governance_case.evidence_refs == ["evidence-adk2-mapping-001"]
    assert governance_case.policy_refs == []
    assert governance_case.context["status"] == "success"
    assert governance_case.context["risk_level"] == "low"
    assert governance_case.metadata["findings"][0]["code"] == (
        "ADK2_WORKFLOW_RUNNER_CHAIN_OBSERVED"
    )
    assert governance_case.metadata["required_followups"] == []
    assert governance_case.metadata["policy_candidate_notes"]
    assert governance_case.metadata["contract_candidate_notes"]
    assert governance_case.metadata["config_context_candidate_notes"]
    assert "No GovernanceDecision is produced." in governance_case.metadata[
        "mapping_boundary"
    ]


def test_mapping_package_links_evidence_and_review_without_decision() -> None:
    mapping_result = map_adk_workflow_runner_governance_package(
        _evidence_candidate(),
        review=_review_candidate(),
    )

    assert isinstance(mapping_result, AdkWorkflowRunnerGovernanceMappingResult)
    assert mapping_result.governance_evidence.evidence_id == (
        "evidence-adk2-mapping-001"
    )
    assert mapping_result.governance_case.evidence_refs == [
        "evidence-adk2-mapping-001"
    ]

    dumped = mapping_result.model_dump(mode="python")
    assert "governance_decision" not in dumped
    assert "governance_outcome" not in dumped
    assert "decision_id" not in repr(dumped)
    assert "release" not in repr(dumped)
    assert "block" not in repr(dumped)
    assert "pass" not in repr(dumped)


def test_mapping_source_keeps_adk_and_assembly_layers_out() -> None:
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
