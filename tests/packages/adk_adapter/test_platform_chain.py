from __future__ import annotations

from pathlib import Path
from typing import Any

import contract_core.runtime as contract_runtime
from adk_adapter import AdkWorkflowRunner
from adk_adapter.platform_chain import (
    build_adk_platform_chain_facts,
    describe_litellm_ollama_boundary,
)
from composition.runtime import RuntimeCompositionOptions, build_standard_runtime_runner
from cognition_governance.models import GovernancePolicySet
from cognition_governance.observability_bridge import (
    build_governance_case_from_evidence_bundle,
    build_governance_decision_sample,
    build_governance_evidence_from_evidence_bundle,
)
from observability_hub import EvidenceBundle, build_evidence_bundle
from observability_hub.adk_intake import build_adk_fact_package
from runtime.orchestrator import StandardRuntimeRunner


def test_adk_platform_chain_reaches_observability_and_governance() -> None:
    from google.adk.agents.context import Context
    from google.adk.events import Event
    from google.adk.events.event import NodeInfo
    from google.adk.events.event_actions import EventActions
    from google.adk.workflow import START, BaseNode, Workflow

    class GovernanceEvidenceNode(BaseNode):
        async def _run_impl(self, *, ctx: Context, node_input: Any):
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                node_info=NodeInfo(path=ctx.node_path),
                output={
                    "governance_signal": "platform-chain-ready",
                    "node": self.name,
                },
                actions=EventActions(
                    state_delta={"platform_chain": "observability-ready"},
                    artifact_delta={"adk-platform-evidence.json": 1},
                    agent_state={"model_boundary": "no-runtime-model-call"},
                    route="observability_hub",
                ),
            )

    workflow = Workflow(
        name="adk_platform_chain_workflow",
        edges=[(START, GovernanceEvidenceNode(name="governance_evidence_node"))],
    )
    runtime_runner = build_standard_runtime_runner(
        options=RuntimeCompositionOptions(
            config_root=Path("config"),
            environment="local",
        ),
        workflow_runner=AdkWorkflowRunner(
            workflow=workflow,
            app_name="test_adk_platform_chain",
            user_id="test-governance-user",
        ),
    )
    runtime_input = contract_runtime.RuntimeInput(
        runtime_id="runtime-adk-platform-001",
        workflow_ref=contract_runtime.WorkflowRef(
            workflow_id="workflow-adk-platform-001",
            name="adk-platform-chain",
            source="adk_adapter",
        ),
        invocation_ref=contract_runtime.InvocationRef(
            invocation_id="requested-adk-platform-001",
            runtime_id="runtime-adk-platform-001",
            workflow_id="workflow-adk-platform-001",
        ),
        input_payload={"message": "build minimal ADK platform evidence chain"},
        metadata={"adapter_name": "adk_adapter", "task": "078"},
    )

    runtime_result = runtime_runner.run(runtime_input)
    adk_fact_package = build_adk_fact_package(runtime_result)
    evidence_bundle = adk_fact_package.to_governance_input()
    legacy_bundle = build_evidence_bundle(runtime_result)

    assert isinstance(runtime_runner, StandardRuntimeRunner)
    assert runtime_result.status == contract_runtime.RuntimeStatus.SUCCESS
    assert runtime_result.workflow_result is not None
    workflow_result = runtime_result.workflow_result
    platform_facts = build_adk_platform_chain_facts(workflow_result)

    assert platform_facts.status == "success"
    assert platform_facts.requested_invocation_id == "requested-adk-platform-001"
    assert platform_facts.adk_invocation_id
    assert platform_facts.session_id
    assert platform_facts.event_count >= 2
    assert platform_facts.artifact_delta_count == 1

    assert isinstance(evidence_bundle, EvidenceBundle)
    assert evidence_bundle.source_type == "runtime_result"
    assert evidence_bundle.metadata["runtime_metadata"]["observability_hub_intake"] == (
        "adk_adapter"
    )
    assert evidence_bundle.event_trace.event_count >= 2
    assert evidence_bundle.artifact_manifest.artifact_count == 1
    assert evidence_bundle.artifact_manifest.artifacts[0]["artifact_id"] == (
        "adk-platform-evidence.json"
    )
    assert evidence_bundle.invocation is not None
    assert evidence_bundle.invocation.requested_invocation_id == (
        "requested-adk-platform-001"
    )
    assert evidence_bundle.invocation.adk_invocation_id == platform_facts.adk_invocation_id
    assert legacy_bundle.event_trace.event_count == evidence_bundle.event_trace.event_count

    governance_evidence = build_governance_evidence_from_evidence_bundle(
        evidence_bundle,
        evidence_id="evidence-adk-platform-chain-001",
    )
    governance_case = build_governance_case_from_evidence_bundle(
        evidence_bundle,
        case_id="case-adk-platform-chain-001",
        title="Review ADK platform evidence chain",
        evidence_refs=[governance_evidence.evidence_id],
    )
    policy_set = GovernancePolicySet(
        policy_set_id="policy-adk-observability-bridge-candidate",
        name="ADK observability bridge candidate policy",
        policies=[
            "ADK adapter produces runtime facts.",
            "observability_hub owns EvidenceBundle formation.",
            "cognition_governance forms candidate-only decisions from case, evidence, and policy.",
        ],
    )
    governance_decision = build_governance_decision_sample(
        decision_id="decision-adk-platform-chain-001",
        case=governance_case,
        evidence=[governance_evidence],
        policy_set=policy_set,
    )

    assert governance_evidence.evidence_type == "adk_observability_evidence_bundle"
    assert governance_evidence.metadata["producer_chain"] == [
        "adk_adapter",
        "observability_hub",
        "cognition_governance",
    ]
    assert governance_evidence.metadata["artifact_count"] == 1
    assert governance_case.context["workflow"]["workflow_id"] == "workflow-adk-platform-001"
    assert governance_case.context["invocation"]["adk_invocation_id"] == (
        platform_facts.adk_invocation_id
    )
    assert governance_decision.decision == "continue"
    assert governance_decision.metadata["decision_semantics"] == "candidate_only"
    assert governance_decision.metadata["formal_decision_enabled"] is False
    assert governance_decision.metadata["policy_execution_enabled"] is False
    assert governance_decision.metadata["governance_outcome_enabled"] is False
    assert governance_decision.metadata["legacy_observability_bridge"] is True
    assert governance_decision.metadata["model_output_used_as_decision"] is False
    assert platform_facts.to_metadata()["handoff_target"] == "observability_hub"


def test_litellm_ollama_gemma4_boundary_is_described_without_model_call() -> None:
    boundary = describe_litellm_ollama_boundary(local_model="gemma4")
    metadata = boundary.to_metadata()

    assert metadata["route"] == "adk_adapter.litellm_ollama"
    assert metadata["local_model"] == "gemma4"
    assert metadata["adk_version"] == "2.0.0"
    assert metadata["runtime_call_performed"] is False
    assert any("cognition_governance" in note for note in metadata["notes"])
