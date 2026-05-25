from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from cognition_evaluation import (
    ArchitectureBoundarySnapshot,
    evaluate_architecture_boundary,
    evaluate_cli_duty_whitelist_source_boundary,
    evaluate_cli_source_architecture_boundary,
    evaluate_product_entry_source_boundary,
    evaluation_summary_from_result,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_architecture_boundary_passes_clean_snapshot() -> None:
    result = evaluate_architecture_boundary(
        ArchitectureBoundarySnapshot(
            component_ref="packages/cognition_evaluation",
            changed_paths=["packages/cognition_evaluation/src/cognition_evaluation"],
            task_api_semantic_mapping="task evaluation finding",
            workflow_runtime_semantic_mapping="workflow step output finding",
        )
    )

    assert result.status == "passed"
    assert result.profile_ref is not None
    assert result.profile_ref.ref == "evaluation-profile://architecture-boundary/v1"
    assert result.metadata["governance_decision"] is False

    summary = evaluation_summary_from_result(result)
    assert summary.status == "passed"
    assert summary.finding_count == 0


def test_architecture_boundary_flags_cli_and_product_gateway_candidate_consumption() -> None:
    result = evaluate_architecture_boundary(
        ArchitectureBoundarySnapshot(
            component_ref="packages/cli",
            direct_internal_imports=["observability_hub.RuntimeFactEnvelope"],
            cli_internal_candidate_consumption=["RuntimeFactEnvelope"],
            product_gateway_internal_candidate_consumption=[
                "RuntimeFactSummaryProjection"
            ],
            task_api_semantic_mapping="task trace summary",
            workflow_runtime_semantic_mapping="workflow run summary",
        )
    )

    assert result.status == "failed"
    criteria = {finding.criterion for finding in result.findings}
    assert "dependency_direction_boundary" in criteria
    assert "cli_channel_boundary" in criteria
    assert "product_gateway_boundary" in criteria
    assert any(finding.severity == "blocking" for finding in result.findings)


def test_cli_source_architecture_boundary_flags_product_fact_assembly() -> None:
    result = evaluate_cli_source_architecture_boundary(
        component_ref="packages/cli",
        source_path="packages/cli/src/cognition_cli/external_readonly/ask.py",
        source_text="""
from product_application_assembly import build_evidence_summary_answer_trace
from product_gateway.external_readonly_ask import execute_external_readonly_ask_gateway_request

def _product_response_summary():
    execute_external_readonly_ask_gateway_request({})
    build_evidence_summary_answer_trace(None, {})
""",
    )

    assert result.status == "failed"
    assert result.metadata["source_text_retained"] is False
    criteria = {finding.criterion for finding in result.findings}
    assert "cli_channel_boundary" in criteria


def test_cli_source_architecture_boundary_allows_summary_consumption() -> None:
    result = evaluate_cli_source_architecture_boundary(
        component_ref="packages/cli",
        source_path="packages/cli/src/cognition_cli/external_readonly/ask.py",
        source_text="""
from product_application_assembly import assemble_evidence_summary_answer_product_output

def render(summary):
    return summary["answer_trace_ref"]
""",
    )

    assert result.status == "passed"


def test_cli_source_architecture_boundary_allows_answer_run_ref_display() -> None:
    result = evaluate_cli_source_architecture_boundary(
        component_ref="packages/cli",
        source_path="packages/cli/src/cognition_cli/external_readonly/ask.py",
        source_text='''
def render(summary):
    output = {"answer_run_ref": summary.get("answer_run_ref")}
    return f"answer_run_ref: {output['answer_run_ref']}"
''',
    )

    assert result.status == "passed"


def test_cli_source_architecture_boundary_flags_answer_run_ref_generation() -> None:
    result = evaluate_cli_source_architecture_boundary(
        component_ref="packages/cli",
        source_path="packages/cli/src/cognition_cli/external_readonly/ask.py",
        source_text="""
def build_run_ref(run_id):
    answer_run_ref = f"evidence-summary-answer-run://{run_id}"
    return answer_run_ref
""",
    )

    assert result.status == "failed"


def test_cli_duty_whitelist_allows_channel_adapter_rendering() -> None:
    result = evaluate_cli_duty_whitelist_source_boundary(
        component_ref="packages/cli",
        source_path="packages/cli/src/cognition_cli/example.py",
        source_text="""
def render(output):
    print(output.get("status"))
    print(output.get("answer_run_ref") or "unavailable")
    return 0
""",
    )

    assert result.status == "passed"
    assert result.metadata["source_text_retained"] is False


def test_cli_duty_whitelist_flags_product_and_model_drift() -> None:
    result = evaluate_cli_duty_whitelist_source_boundary(
        component_ref="packages/cli",
        source_path="packages/cli/src/cognition_cli/external_readonly/ask.py",
        source_text="""
from config_contexts.runtime import RuntimeLiveLlmConfigView
from contract_core.llm_invocation import LlmGovernancePrecondition
from contract_core.model_routing import ModelRouteFacts
from product_application_assembly import build_evidence_summary_answer_context

def build(args):
    RuntimeLiveLlmConfigView()
    ModelRouteFacts(model_name="m", provider="p", source="s")
    LlmGovernancePrecondition(allowed=True, reason="r", decision="allow")
    build_evidence_summary_answer_context(None)
""",
    )

    assert result.status == "failed"
    criteria = {finding.criterion for finding in result.findings}
    assert "cli_product_answer_assembly_boundary" in criteria
    assert "cli_model_routing_boundary" in criteria
    assert "cli_governance_precondition_boundary" in criteria
    assert "cli_to_cli_product_path_coupling" not in criteria


def test_cli_duty_whitelist_flags_provider_key_backend_strategy() -> None:
    result = evaluate_cli_duty_whitelist_source_boundary(
        component_ref="packages/cli",
        source_path="packages/cli/src/cognition_cli/credentials/deepseek_keychain.py",
        source_text="""
DEEPSEEK_KEYCHAIN_SERVICE = "service"

class MacOSKeychainDeepSeekCredentialStore:
    pass

def build():
    return build_default_deepseek_credential_store()
""",
    )

    assert result.status == "failed"
    assert {
        finding.criterion for finding in result.findings
    } == {"cli_provider_key_strategy_boundary"}


def test_cli_duty_whitelist_flags_chat_bridge_ask_wrapper_import() -> None:
    result = evaluate_cli_duty_whitelist_source_boundary(
        component_ref="packages/cli",
        source_path=(
            "packages/cli/src/cognition_cli/chat/external_readonly_bridge.py"
        ),
        source_text="""
from cognition_cli.external_readonly.ask import (
    build_external_readonly_ask_initial_interaction,
    build_external_readonly_ask_follow_up_interaction,
)
""",
    )

    assert result.status == "failed"
    assert "cli_chat_bridge_ask_cli_wrapper_import" in {
        finding.criterion for finding in result.findings
    }


def test_cli_duty_whitelist_flags_private_answer_transform_execution() -> None:
    result = evaluate_cli_duty_whitelist_source_boundary(
        component_ref="packages/cli",
        source_path="packages/cli/src/cognition_cli/chat/external_readonly_bridge.py",
        source_text="""
from product_application_assembly import build_evidence_summary_answer_transform_llm_request

def transform():
    return build_evidence_summary_answer_transform_llm_request(None)
""",
    )

    assert result.status == "failed"
    assert "cli_answer_scoped_transform_private_boundary" in {
        finding.criterion for finding in result.findings
    }


def test_cli_duty_whitelist_flags_retired_external_readonly_answer_surface() -> None:
    result = evaluate_cli_duty_whitelist_source_boundary(
        component_ref="packages/cli",
        source_path="packages/cli/src/cognition_cli/application.py",
        source_text='''
if args.external_readonly_command == "answer":
    return external_readonly_answer_command(args)
''',
    )

    assert result.status == "failed"
    assert "cli_retired_external_readonly_answer_surface" in {
        finding.criterion for finding in result.findings
    }


def test_current_external_readonly_ask_cli_keeps_product_assembly_out_of_duty_findings() -> None:
    source_path = (
        REPO_ROOT
        / "packages"
        / "cli"
        / "src"
        / "cognition_cli"
        / "external_readonly"
        / "ask.py"
    )

    result = evaluate_cli_duty_whitelist_source_boundary(
        component_ref="packages/cli",
        source_path=str(source_path.relative_to(REPO_ROOT)),
        source_text=source_path.read_text(encoding="utf-8"),
    )

    assert result.status == "passed"
    criteria = {finding.criterion for finding in result.findings}
    assert "cli_product_answer_assembly_boundary" not in criteria
    assert "cli_model_routing_boundary" not in criteria
    assert "cli_governance_precondition_boundary" not in criteria
    assert "cli_provider_key_strategy_boundary" not in criteria
    assert "cli_evaluation_rule_boundary" not in criteria


def test_current_cli_sources_satisfy_duty_whitelist() -> None:
    cli_root = REPO_ROOT / "packages" / "cli" / "src" / "cognition_cli"
    for source_path in sorted(cli_root.rglob("*.py")):
        result = evaluate_cli_duty_whitelist_source_boundary(
            component_ref="packages/cli",
            source_path=str(source_path.relative_to(REPO_ROOT)),
            source_text=source_path.read_text(encoding="utf-8"),
        )
        assert result.status == "passed", (
            source_path.relative_to(REPO_ROOT),
            [finding.criterion for finding in result.findings],
        )


def test_current_chat_bridge_uses_product_ask_interaction_facade() -> None:
    source_path = (
        REPO_ROOT
        / "packages"
        / "cli"
        / "src"
        / "cognition_cli"
        / "chat"
        / "external_readonly_bridge.py"
    )

    result = evaluate_cli_duty_whitelist_source_boundary(
        component_ref="packages/cli",
        source_path=str(source_path.relative_to(REPO_ROOT)),
        source_text=source_path.read_text(encoding="utf-8"),
    )

    assert "cli_to_cli_product_path_coupling" not in {
        finding.criterion for finding in result.findings
    }


def test_current_external_readonly_ask_cli_keeps_product_fact_assembly_out() -> None:
    source_path = (
        REPO_ROOT
        / "packages"
        / "cli"
        / "src"
        / "cognition_cli"
        / "external_readonly"
        / "ask.py"
    )

    result = evaluate_cli_source_architecture_boundary(
        component_ref="packages/cli",
        source_path=str(source_path.relative_to(REPO_ROOT)),
        source_text=source_path.read_text(encoding="utf-8"),
    )

    assert result.status == "passed"


def test_product_entry_source_boundary_flags_cli_namespace_leakage() -> None:
    result = evaluate_product_entry_source_boundary(
        component_ref="packages/product_application_assembly",
        source_path=(
            "packages/product_application_assembly/src/product_application_assembly/"
            "evidence_summary_answer_ask_entry.py"
        ),
        source_text="""
from cognition_cli.parser import build_parser

def run(argv):
    args = build_parser().parse_args(argv)
    return args
""",
    )

    assert result.status == "failed"
    criteria = {finding.criterion for finding in result.findings}
    assert "product_entry_argparse_namespace_boundary" in criteria
    assert "product_entry_cli_import_boundary" in criteria


def test_current_product_ask_entry_has_no_cli_namespace_leakage() -> None:
    source_path = (
        REPO_ROOT
        / "packages"
        / "product_application_assembly"
        / "src"
        / "product_application_assembly"
        / "evidence_summary_answer_ask_entry.py"
    )

    result = evaluate_product_entry_source_boundary(
        component_ref="packages/product_application_assembly",
        source_path=str(source_path.relative_to(REPO_ROOT)),
        source_text=source_path.read_text(encoding="utf-8"),
    )

    assert result.status == "passed"


def test_architecture_boundary_flags_governance_and_axis_mapping_risks() -> None:
    result = evaluate_architecture_boundary(
        ArchitectureBoundarySnapshot(
            component_ref="packages/cognition_evaluation",
            governance_decision_outputs=["allow", "block"],
            observability_as_linear_step=True,
            legacy_terms=["TWF"],
            module_swallowing_risks=["evaluation writes observability events"],
        )
    )

    assert result.status == "failed"
    criteria = [finding.criterion for finding in result.findings]
    assert "evaluation_governance_boundary" in criteria
    assert "runtime_fact_bus_boundary" in criteria
    assert "legacy_route_pollution" in criteria
    assert "adk_axis_alignment" in criteria
    assert "module_swallowing_risk" in criteria


def test_architecture_boundary_rejects_raw_markers() -> None:
    with pytest.raises(ValidationError):
        ArchitectureBoundarySnapshot(
            component_ref="packages/cli",
            metadata={"bad_value": "raw_provider_response must not enter evaluation input"},
        )
