from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from cognition_agent.entrypoints import governance_summary
from scripts.dev_governance_summary_no_live_productization import (
    build_no_live_governance_summary_payload,
    write_no_live_governance_summary_payload,
)


def test_no_live_productization_loop_builds_cli_consumable_payload(
    tmp_path: Path,
    capsys,
) -> None:
    output_path = tmp_path / "ce-158-default-governance-summary-payload.json"
    output_ref = f"file://{output_path}"

    written_path = write_no_live_governance_summary_payload(
        output=output_path,
        overwrite=True,
    )

    assert written_path == output_path
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["evidence_id"] == "runtime-container-governance-summary-156-no-live"
    assert payload["recorded_run"]["evidence_bundle_ref"] == (
        "evidence-bundle://ce-156-no-live-productization"
    )
    assert payload["recorded_run"]["does_not_execute_recorded_run"] is True
    assert payload["configuration_chain"]["config_root"] == "config"
    assert payload["configuration_chain"]["environment"] == "local"
    assert payload["configuration_chain"]["adk_run_config"]["mapped"] is True
    assert payload["configuration_chain"]["adk_run_config"]["max_llm_calls"] == 1
    assert payload["configuration_chain"]["productization_gate"]["gate_id"] == (
        "gate-ce-156-no-live-productization"
    )
    assert payload["configuration_chain"]["governance"]["governance_profile"] == (
        "no-live-productization"
    )
    assert payload["summary_generation"][
        "uses_recorded_run_evidence_provider_contract"
    ] is True
    assert payload["productization_loop"]["recorded_run_evidence_provider_contract"] is True
    assert payload["productization_loop"]["adk_service_facts_provider_contract"] is True
    assert payload["productization_loop"]["config_chain_consumed"] is True
    assert payload["productization_loop"]["governance_summary_output_ref"] == output_ref
    assert payload["controlled_run_approval"]["approved"] is False
    assert payload["controlled_run_approval"]["request_adk_run"] is False
    assert payload["controlled_run_approval"]["allow_adk_run"] is False
    assert payload["controlled_run_approval"]["does_not_trigger_adk_run"] is True
    assert payload["controlled_run_gating"]["request_adk_run"] is False
    assert payload["controlled_run_gating"]["allow_adk_run"] is False
    assert payload["controlled_run_gating"]["runtime_execution_ready"] is False
    assert payload["controlled_run_gating"]["adk_run_allowed"] is False
    assert payload["controlled_run_gating"]["live_llm_allowed"] is False
    assert payload["controlled_run_gating"]["adk_run_performed"] is False
    assert payload["controlled_run_gating"]["execution_performed"] is False
    assert payload["controlled_run_gating"]["governance_summary_output_ref"] == output_ref
    assert payload["productization_gating"]["execution_performed"] is False
    assert payload["productization_gating"]["adk_run_performed"] is False
    assert payload["productization_gating"]["live_llm_call_performed"] is False
    assert payload["productization_gating"]["runtime_execution_ready"] is False
    assert payload["productization_gating"]["adk_run_allowed"] is False
    assert payload["productization_gating"]["live_llm_allowed"] is False
    assert payload["productization_gating"]["metadata"][
        "governance_summary_output_ref"
    ] == output_ref
    assert payload["run_config_service_bundle_summary"]["run_config"][
        "mapped_fields"
    ] == [
        "max_llm_calls",
        "custom_metadata",
        "response_modalities",
        "support_cfc",
        "streaming_mode",
        "get_session_config",
    ]
    assert payload["run_config_service_bundle_summary"]["run_config"][
        "live_call_enabled"
    ] is False
    assert payload["run_config_service_bundle_summary"]["run_config"][
        "call_attempted"
    ] is False

    assert governance_summary.main(["--input", str(output_path), "--json"]) == 0
    cli_json = json.loads(capsys.readouterr().out)
    assert cli_json["candidate_only"] is True
    assert cli_json["readonly"] is True
    assert cli_json["runtime_container_call_enabled"] is False
    assert cli_json["llm_call_enabled"] is False
    assert cli_json["workflow_name"] == "insight-to-decision"

    assert governance_summary.main(["--input", str(output_path), "--text"]) == 0
    text = capsys.readouterr().out
    assert "Read-only governance evidence summary" in text
    assert "This view is not execution permission." in text


def test_controlled_run_precheck_can_be_approved_without_execution(
    tmp_path: Path,
    capsys,
) -> None:
    output_path = tmp_path / "ce-158-controlled-run-precheck-payload.json"
    output_ref = f"file://{output_path}"
    approval_ref = "approval://test-controlled-run-precheck"

    write_no_live_governance_summary_payload(
        output=output_path,
        request_adk_run=True,
        allow_adk_run=True,
        operator_approved=True,
        operator_approval_ref=approval_ref,
        operator_ref="operator://test",
        overwrite=True,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    approval = payload["controlled_run_approval"]
    gating = payload["controlled_run_gating"]
    productization_gating = payload["productization_gating"]

    assert approval["approval_ref"] == approval_ref
    assert approval["approved"] is True
    assert approval["approved_by"] == "operator://test"
    assert approval["runtime_id"] == "local-runtime"
    assert approval["invocation_id"] == "inv-local-runtime"
    assert approval["gate_id"] == "gate-ce-156-no-live-productization"
    assert approval["request_adk_run"] is True
    assert approval["allow_adk_run"] is True
    assert approval["does_not_trigger_adk_run"] is True
    assert approval["does_not_trigger_live_llm"] is True

    assert gating["approval_ref"] == approval_ref
    assert gating["request_adk_run"] is True
    assert gating["allow_adk_run"] is True
    assert gating["explicit_operator_approval"] is True
    assert gating["runtime_execution_ready"] is True
    assert gating["adk_run_allowed"] is True
    assert gating["live_llm_allowed"] is False
    assert gating["adk_run_performed"] is False
    assert gating["execution_performed"] is False
    assert gating["missing_conditions"] == []
    assert gating["governance_summary_output_ref"] == output_ref
    assert gating["governance_decision_candidate"]["decision"] == "continue"
    assert gating["runtime_identity"]["invocation_id"] == "inv-local-runtime"

    assert productization_gating["runtime_execution_ready"] is True
    assert productization_gating["adk_run_allowed"] is True
    assert productization_gating["live_llm_allowed"] is False
    assert productization_gating["adk_run_performed"] is False
    assert productization_gating["execution_performed"] is False
    assert productization_gating["metadata"]["approval_ref"] == approval_ref
    assert productization_gating["metadata"][
        "governance_summary_output_ref"
    ] == output_ref

    assert governance_summary.main(["--input", str(output_path), "--json"]) == 0
    cli_json = json.loads(capsys.readouterr().out)
    assert cli_json["candidate_only"] is True
    assert cli_json["readonly"] is True
    assert cli_json["runtime_container_call_enabled"] is False
    assert cli_json["llm_call_enabled"] is False

    assert governance_summary.main(["--input", str(output_path), "--text"]) == 0
    text = capsys.readouterr().out
    assert "This view is not execution permission." in text


def test_no_live_productization_loop_module_can_run_with_python_m(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "ce-158-controlled-run-precheck-payload.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.dev_governance_summary_no_live_productization",
            "--config-root",
            "config",
            "--environment",
            "local",
            "--output",
            str(output_path),
            "--overwrite",
            "--pretty",
            "--request-adk-run",
            "--allow-adk-run",
            "--operator-approved",
            "--operator-approval-ref",
            "approval://test-module-controlled-run-precheck",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    stdout_payload = json.loads(completed.stdout)
    file_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert stdout_payload == file_payload
    assert file_payload["productization_loop"]["dev_only"] is True
    assert file_payload["productization_loop"]["product_cli"] is False
    assert file_payload["productization_loop"]["config_chain_consumed"] is True
    assert file_payload["configuration_chain"]["adk_run_config"]["mapped"] is True
    assert file_payload["controlled_run_gating"]["runtime_execution_ready"] is True
    assert file_payload["controlled_run_gating"]["adk_run_allowed"] is True
    assert file_payload["controlled_run_gating"]["execution_performed"] is False
    assert file_payload["productization_loop"]["does_not_trigger_live_llm"] is True
    assert file_payload["productization_loop"]["does_not_trigger_real_adk_run"] is True
    assert file_payload["productization_loop"]["does_not_trigger_ollama"] is True


def test_no_live_productization_loop_uses_productization_chain() -> None:
    payload = build_no_live_governance_summary_payload()

    assert payload["productization_loop"]["composition_provider_assembly"] == (
        "composition.adk_workflow_runner_assembly."
        "AdkWorkflowRunnerGovernanceSummaryProviderAssembly"
    )
    assert payload["productization_loop"]["composition_service_facts_assembly"] == (
        "composition.adk_workflow_runner_assembly."
        "AdkWorkflowRunnerServiceFactsProviderAssembly"
    )
    assert payload["summary_generation"]["generator"] == (
        "runtime-container-governance-summary-pipeline"
    )
    assert payload["configuration_chain"]["source"] == (
        "composition.runtime.build_runtime_config_context"
    )
