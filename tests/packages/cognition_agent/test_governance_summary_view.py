from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

PACKAGE_SRC = Path(__file__).resolve().parents[3] / "packages" / "cognition_agent" / "src"
sys.path.insert(0, str(PACKAGE_SRC))

from cognition_agent import (  # noqa: E402
    GOVERNANCE_EVIDENCE_SUMMARY_VIEW_SOURCE,
    GOVERNANCE_EVIDENCE_SUMMARY_VIEW_VERSION,
    AgentGovernanceEvidenceSummaryViewCandidate,
    build_agent_governance_evidence_summary_view,
)
from schemas.runtime import (  # noqa: E402
    AdkLifecycleFactsSummary,
    AdkRunConfigServiceBundleSummary,
    ContextStateLifecycleFacts,
    EventLifecycleFacts,
    RunConfigGovernanceView,
    ServiceBundleGovernanceView,
    SessionLifecycleFacts,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
COGNITION_AGENT_SOURCE_ROOT = (
    REPO_ROOT / "packages" / "cognition_agent" / "src" / "cognition_agent"
)


def test_agent_governance_summary_view_consumes_public_summaries_readonly() -> None:
    view = build_agent_governance_evidence_summary_view(
        candidate_id="agent-governance-summary-view-1",
        governance_evidence_metadata={
            "evidence_id": "governance-evidence-1",
            "lifecycle_summary": _lifecycle_summary().model_dump(mode="python"),
            "run_config_service_bundle_summary": (
                _run_config_service_bundle_summary().model_dump(mode="python")
            ),
            "graph_summary": _graph_summary(),
            "trace_summary": _trace_summary(),
        },
    )

    assert isinstance(view, AgentGovernanceEvidenceSummaryViewCandidate)
    assert view.candidate_type == "agent_governance_evidence_summary_view_candidate"
    assert view.summary_version == GOVERNANCE_EVIDENCE_SUMMARY_VIEW_VERSION
    assert view.summary_source == GOVERNANCE_EVIDENCE_SUMMARY_VIEW_SOURCE
    assert view.lifecycle_summary_id == "adk-lifecycle-summary-agent-1"
    assert view.run_config_service_bundle_summary_id == (
        "adk-run-config-service-bundle-summary-agent-1"
    )
    assert view.runtime_id == "runtime-agent-summary-1"
    assert view.workflow_name == "agent-summary-workflow"
    assert view.artifact_count == 0
    assert view.session_observed is True
    assert view.event_count == 2
    assert view.event_types == ["node_completed"]
    assert view.state_delta_count == 1
    assert view.state_delta_entity_mode == "state_delta_contract_summary"
    assert view.graph_summary_id == "graph-summary-agent-1"
    assert view.graph_node_path_count == 1
    assert view.graph_node_paths == ["agent_summary_workflow@1/review_node@1"]
    assert view.graph_has_branching is False
    assert view.trace_event_count == 2
    assert view.trace_event_types == ["node_completed"]
    assert view.trace_has_error is False
    assert view.run_config_mapped_fields == ["max_llm_calls", "custom_metadata"]
    assert view.run_config_unmapped_fields == ["tool_thread_pool_config"]
    assert view.run_config_deferred_fields == ["tool_thread_pool_config"]
    assert view.run_config_no_live_mode is True
    assert view.run_config_call_attempted is False
    assert view.service_bundle_source == "in_memory"
    assert view.service_persistence_stage == "runtime_fact_only"
    assert view.service_persistence_strategy == (
        "in_memory_or_provided_service_reference"
    )
    assert view.artifact_service_present is True
    assert view.session_service_present is True
    assert view.readonly is True
    assert view.candidate_only is True
    assert view.execution_enabled is False
    assert view.runtime_container_call_enabled is False
    assert view.service_invoke_enabled is False
    assert view.llm_call_enabled is False
    assert view.action_execution_enabled is False
    assert view.runtime_action_enabled is False
    assert view.metadata["does_not_import_cognition_governance"] is True
    assert view.metadata["does_not_import_observability_hub"] is True
    assert view.metadata["does_not_import_runtime"] is True
    assert view.metadata["does_not_call_runtime_container"] is True
    assert view.metadata["does_not_execute_runtime_action"] is True
    assert view.metadata["consumed_graph_summary"] is True
    assert view.metadata["consumed_trace_summary"] is True
    assert "graph_summary:graph-summary-agent-1" in view.governance_refs
    assert "trace_summary:observability_hub.adk_workflow_runner_evidence.trace_summary" in (
        view.governance_refs
    )
    assert "This view is not execution permission." in view.summary
    assert "graph_nodes=1" in view.summary
    assert "trace_events=2" in view.summary


def test_agent_governance_summary_view_accepts_explicit_public_schema_objects() -> None:
    view = build_agent_governance_evidence_summary_view(
        candidate_id="agent-governance-summary-view-2",
        lifecycle_summary=_lifecycle_summary(),
        run_config_service_bundle_summary=_run_config_service_bundle_summary(),
    )

    assert set(view.governance_refs) == {
        "lifecycle_summary:adk-lifecycle-summary-agent-1",
        (
            "run_config_service_bundle_summary:"
            "adk-run-config-service-bundle-summary-agent-1"
        ),
    }
    assert view.metadata["consumed_lifecycle_summary"] is True
    assert view.metadata["consumed_run_config_service_bundle_summary"] is True


def test_agent_governance_summary_view_accepts_safe_llm_invocation_audit() -> None:
    view = build_agent_governance_evidence_summary_view(
        candidate_id="agent-governance-summary-view-audit-1",
        governance_evidence_metadata={
            "evidence_id": "governance-evidence-audit-1",
            "lifecycle_summary": _lifecycle_summary().model_dump(mode="python"),
            "run_config_service_bundle_summary": (
                _run_config_service_bundle_summary().model_dump(mode="python")
            ),
            "llm_invocation_audit": _llm_invocation_audit(),
        },
    )

    assert view.lifecycle_summary_id == "adk-lifecycle-summary-agent-1"
    assert view.run_config_service_bundle_summary_id == (
        "adk-run-config-service-bundle-summary-agent-1"
    )
    assert not hasattr(view, "llm_invocation_audit")
    assert view.metadata["consumed_lifecycle_summary"] is True
    assert view.metadata["consumed_run_config_service_bundle_summary"] is True


def test_agent_governance_summary_view_rejects_raw_or_runtime_payloads() -> None:
    with pytest.raises(ValueError):
        build_agent_governance_evidence_summary_view(
            candidate_id="agent-governance-summary-view-raw-1",
            governance_evidence_metadata={
                "lifecycle_summary": {
                    **_lifecycle_summary().model_dump(mode="python"),
                    "metadata": {"prompt": "raw prompt"},
                },
            },
        )

    with pytest.raises(ValueError):
        build_agent_governance_evidence_summary_view(
            candidate_id="agent-governance-summary-view-raw-2",
            governance_evidence_metadata={
                "run_config_service_bundle_summary": {
                    **_run_config_service_bundle_summary().model_dump(mode="python"),
                    "metadata": {"object_module": "google.adk.runners"},
                },
            },
        )

    with pytest.raises(ValueError):
        build_agent_governance_evidence_summary_view(
            candidate_id="agent-governance-summary-view-raw-audit-1",
            governance_evidence_metadata={
                "lifecycle_summary": _lifecycle_summary().model_dump(mode="python"),
                "run_config_service_bundle_summary": (
                    _run_config_service_bundle_summary().model_dump(mode="python")
                ),
                "llm_invocation_audit": {
                    **_llm_invocation_audit(),
                    "raw_provider_response": {"content": "raw"},
                },
            },
        )

    with pytest.raises(ValueError):
        build_agent_governance_evidence_summary_view(
            candidate_id="agent-governance-summary-view-raw-graph-1",
            governance_evidence_metadata={
                "graph_summary": {
                    **_graph_summary(),
                    "raw": {"object_module": "google.adk.workflow"},
                },
            },
        )

    with pytest.raises(ValueError):
        build_agent_governance_evidence_summary_view(
            candidate_id="agent-governance-summary-view-raw-trace-1",
            governance_evidence_metadata={
                "trace_summary": {
                    **_trace_summary(),
                    "prompt": "raw prompt must not enter agent view",
                },
            },
        )


def test_agent_governance_summary_view_rejects_execution_flags() -> None:
    with pytest.raises(ValidationError):
        AgentGovernanceEvidenceSummaryViewCandidate(
            candidate_id="agent-governance-summary-view-invalid-1",
            source=GOVERNANCE_EVIDENCE_SUMMARY_VIEW_SOURCE,
            summary="Invalid governance evidence summary view.",
            runtime_container_call_enabled=True,
        )

    with pytest.raises(ValidationError):
        AgentGovernanceEvidenceSummaryViewCandidate(
            candidate_id="agent-governance-summary-view-invalid-2",
            source=GOVERNANCE_EVIDENCE_SUMMARY_VIEW_SOURCE,
            summary="Invalid governance evidence summary view.",
            run_config_call_attempted=True,
        )


def test_cognition_agent_governance_summary_source_has_no_execution_dependencies() -> None:
    source = (COGNITION_AGENT_SOURCE_ROOT / "governance_summary_view.py").read_text(
        encoding="utf-8"
    )
    forbidden_imports = re.compile(
        r"^\s*(?:from|import)\s+"
        r"(?:cognition_governance|observability_hub|runtime|runtime_container|"
        r"adk_adapter|google\.adk|litellm)\b",
        re.MULTILINE,
    )
    forbidden_calls = re.compile(
        r"\b(?:completion|acompletion|service\.invoke|run_async|runner\.run)\s*\("
    )

    assert forbidden_imports.search(source) is None
    assert forbidden_calls.search(source) is None
    assert "live_enabled=True" not in source
    assert "ActionCandidate" not in source
    assert "RuntimeActionCandidate" not in source
    assert "AgentRuntime" not in source
    assert "ToolExecutor" not in source
    assert "Chat" not in source
    assert "Gateway" not in source


def _lifecycle_summary() -> AdkLifecycleFactsSummary:
    return AdkLifecycleFactsSummary(
        summary_id="adk-lifecycle-summary-agent-1",
        runtime_id="runtime-agent-summary-1",
        workflow_id="workflow-agent-summary-1",
        workflow_name="agent-summary-workflow",
        status="success",
        session=SessionLifecycleFacts(
            session_id="session-agent-summary-1",
            event_count=2,
            service_type_name="InMemorySessionService",
            metadata={"sanitized": True},
        ),
        events=EventLifecycleFacts(
            event_count=2,
            event_types=["node_completed"],
            metadata={"sanitized": True},
        ),
        context_state=ContextStateLifecycleFacts(
            state_delta_count=1,
            state_delta_keys=["counter"],
            state_delta_entity_mode="state_delta_contract_summary",
            raw_state_values_included=False,
            metadata={"sanitized": True},
        ),
        metadata={"sanitized": True},
    )


def _run_config_service_bundle_summary() -> AdkRunConfigServiceBundleSummary:
    return AdkRunConfigServiceBundleSummary(
        summary_id="adk-run-config-service-bundle-summary-agent-1",
        runtime_id="runtime-agent-summary-1",
        workflow_id="workflow-agent-summary-1",
        workflow_name="agent-summary-workflow",
        status="success",
        run_config=RunConfigGovernanceView(
            run_config_source="assembly_options + workflow_result.metadata",
            mapped_fields=["max_llm_calls", "custom_metadata"],
            unmapped_fields=["tool_thread_pool_config"],
            deferred_fields=["tool_thread_pool_config"],
            custom_metadata_keys=["source"],
            max_llm_calls=17,
            streaming_mode="none",
            adk_run_config_type="RunConfig",
            metadata={"sanitized": True},
        ),
        service_bundle=ServiceBundleGovernanceView(
            service_bundle_source="in_memory",
            persistence_stage="runtime_fact_only",
            persistence_strategy="in_memory_or_provided_service_reference",
            artifact_service_present=True,
            session_service_present=True,
            artifact_service_type_name="InMemoryArtifactService",
            session_service_type_name="InMemorySessionService",
            capability_flags=[
                "artifact_service_present",
                "session_service_present",
            ],
            metadata={"sanitized": True},
        ),
        metadata={"sanitized": True},
    )


def _graph_summary() -> dict[str, object]:
    return {
        "summary_id": "graph-summary-agent-1",
        "source": "observability_hub.adk_workflow_runner_evidence.graph_summary",
        "runtime_id": "runtime-agent-summary-1",
        "workflow_id": "workflow-agent-summary-1",
        "workflow_name": "agent-summary-workflow",
        "node_paths": ["agent_summary_workflow@1/review_node@1"],
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
        "event_ids": ["event-agent-001"],
        "event_types": ["node_completed"],
        "invocation_ids": ["adk-inv-agent-001"],
        "state_delta_refs": ["state-delta://counter"],
        "artifact_delta_refs": [],
        "has_error": False,
        "trace_inferred_from": "event_summary",
        "candidate_only": True,
        "summary_only": True,
        "refs_only": True,
        "raw_event_included": False,
        "raw_payload_included": False,
    }


def _llm_invocation_audit() -> dict[str, object]:
    return {
        "llm_invocation_result_ref": "llm-invocation-result://llm-request-agent-1",
        "llm_invocation_observation_ref": (
            "llm-call-observation://llm-request-agent-1"
        ),
        "llm_invocation_summary_ref": (
            "agent-llm-invocation-summary://llm-request-agent-1"
        ),
        "call_allowed": True,
        "call_attempted": True,
        "runtime_call_performed": True,
        "failure_type": None,
        "controlled_live": True,
        "live_llm_call_performed": True,
        "ollama_call_performed": True,
        "live_profile": {
            "controlled_live": True,
            "live_options_source": "config_contexts.runtime.RuntimeLiveLlmConfigView",
            "live_service_profile": "adk_litellm_ollama",
            "configured_model_name": "ollama/gemma4-pro:latest",
            "timeout_seconds": 45,
            "temperature": 0,
            "max_tokens": 64,
            "local_no_proxy_applied": True,
        },
        "readonly_facts_embedded": False,
        "does_not_store_prompt": True,
        "does_not_store_raw_provider_response": True,
    }
