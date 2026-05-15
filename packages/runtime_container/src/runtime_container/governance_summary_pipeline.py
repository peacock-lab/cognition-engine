"""Runtime-container gating and governance summary generation helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from contract_core.runtime import (
    AdkServiceFactsSummaryInput,
    RecordedRunEvidenceInput,
    RecordedRunEvidenceProvider,
    RuntimeProductizationGateConfigView,
    RuntimeProductizationGateEvaluationFacts,
    RuntimeResult,
)


RuntimeProductizationGating = RuntimeProductizationGateConfigView
RuntimeProductizationGateEvaluation = RuntimeProductizationGateEvaluationFacts


def evaluate_runtime_productization_gating(
    gating: RuntimeProductizationGateConfigView | None = None,
) -> RuntimeProductizationGateEvaluationFacts:
    """Evaluate explicit runtime/live gates without performing any runtime action."""

    gate = gating or RuntimeProductizationGateConfigView()
    missing_conditions = _missing_gate_conditions(gate)
    runtime_execution_ready = _runtime_execution_ready(gate, missing_conditions)
    adk_run_allowed = runtime_execution_ready and gate.request_adk_run
    live_llm_allowed = runtime_execution_ready and gate.request_live_llm
    ollama_allowed = runtime_execution_ready and gate.request_ollama

    return RuntimeProductizationGateEvaluationFacts(
        gate_id=gate.gate_id,
        runtime_execution_ready=runtime_execution_ready,
        adk_run_allowed=adk_run_allowed,
        live_llm_allowed=live_llm_allowed,
        ollama_allowed=ollama_allowed,
        default_no_live=not gate.request_live_llm,
        default_no_adk_run=not gate.request_adk_run,
        default_no_ollama=not gate.request_ollama,
        execution_performed=False,
        adk_run_performed=False,
        live_llm_call_performed=False,
        ollama_call_performed=False,
        missing_conditions=missing_conditions,
        metadata={
            "gating_semantics": "controlled_productization_gate",
            "safety_baseline": "no runtime action is performed by evaluation",
            "explicit_operator_approval": gate.explicit_operator_approval,
            "sanitized_evidence_ref": gate.sanitized_evidence_ref,
            "governance_summary_output_ref": gate.governance_summary_output_ref,
            "audit_ref": gate.audit_ref,
            "reason": gate.reason,
            **_safe_metadata(gate.metadata),
        },
    )


def build_runtime_container_governance_summary_payload(
    *,
    adk_service_facts: AdkServiceFactsSummaryInput,
    gating: RuntimeProductizationGateConfigView | None = None,
    evidence_id: str | None = None,
) -> dict[str, Any]:
    """Build CLI-consumable sanitized governance summary JSON from ADK service facts."""

    facts = _validate_adk_service_facts(adk_service_facts)
    lifecycle_summary = facts.lifecycle_summary
    run_config_service_bundle_summary = facts.run_config_service_bundle_summary
    gate_evaluation = evaluate_runtime_productization_gating(gating)
    payload_evidence_id = (
        evidence_id
        or _optional_string(facts.evidence_id)
        or f"runtime-productization-evidence-{uuid4()}"
    )

    return {
        "evidence_id": payload_evidence_id,
        "lifecycle_summary": lifecycle_summary.model_dump(mode="python"),
        "run_config_service_bundle_summary": (
            run_config_service_bundle_summary.model_dump(mode="python")
        ),
        "productization_gating": gate_evaluation.model_dump(mode="python"),
        "sanitized": True,
        "summary_generation": {
            "generator": "runtime-container-governance-summary-pipeline",
            "input_kind": facts.source,
            "does_not_execute_runtime": True,
            "does_not_call_runtime_helper": True,
            "does_not_call_adk_runner": True,
            "does_not_call_live_llm": True,
            "does_not_call_ollama": True,
            "output_is_compatible_with_agent_governance_summary_view": True,
        },
    }


def build_runtime_container_governance_summary_payload_from_recorded_run(
    *,
    recorded_run: RecordedRunEvidenceInput | None = None,
    runtime_result: RuntimeResult | None = None,
    recorded_run_evidence_provider: RecordedRunEvidenceProvider | None = None,
    gating: RuntimeProductizationGateConfigView | None = None,
    evidence_id: str | None = None,
) -> dict[str, Any]:
    """Build a governance summary payload from recorded run/evidence facts."""

    recorded = _resolve_recorded_run_evidence(
        recorded_run=recorded_run,
        runtime_result=runtime_result,
        recorded_run_evidence_provider=recorded_run_evidence_provider,
    )

    payload = build_runtime_container_governance_summary_payload(
        adk_service_facts=recorded.adk_service_facts,
        gating=gating,
        evidence_id=evidence_id or _optional_string(recorded.evidence_id),
    )
    payload["recorded_run"] = {
        "recorded_run_id": _optional_string(recorded.recorded_run_id),
        "source_kind": recorded.source,
        "evidence_bundle_ref": _optional_string(recorded.evidence_bundle_ref),
        "adk_workflow_runner_evidence_ref": _optional_string(
            recorded.adk_workflow_runner_evidence_ref
        ),
        "has_evidence_bundle": recorded.evidence_bundle_observed,
        "has_adk_workflow_runner_evidence": (
            recorded.adk_workflow_runner_evidence_observed
        ),
        "does_not_execute_recorded_run": recorded.does_not_execute_recorded_run,
    }
    payload["summary_generation"] = {
        **payload["summary_generation"],
        "input_kind": recorded.source,
        "accepts_recorded_run": True,
        "accepts_observability_evidence": True,
        "uses_recorded_run_evidence_provider_contract": (
            recorded_run_evidence_provider is not None
        ),
    }
    return payload


def write_runtime_container_governance_summary_payload(
    *,
    payload: dict[str, Any],
    output_path: str | Path,
    overwrite: bool = False,
) -> Path:
    """Write a sanitized governance summary payload as local JSON."""

    target = Path(output_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"governance summary payload already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def write_runtime_container_governance_summary_payload_from_recorded_run(
    *,
    recorded_run: RecordedRunEvidenceInput | None = None,
    runtime_result: RuntimeResult | None = None,
    recorded_run_evidence_provider: RecordedRunEvidenceProvider | None = None,
    output_path: str | Path,
    gating: RuntimeProductizationGateConfigView | None = None,
    evidence_id: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Build and write a governance summary payload from recorded run facts."""

    payload = build_runtime_container_governance_summary_payload_from_recorded_run(
        recorded_run=recorded_run,
        runtime_result=runtime_result,
        recorded_run_evidence_provider=recorded_run_evidence_provider,
        gating=gating,
        evidence_id=evidence_id,
    )
    return write_runtime_container_governance_summary_payload(
        payload=payload,
        output_path=output_path,
        overwrite=overwrite,
    )


def _missing_gate_conditions(gate: RuntimeProductizationGateConfigView) -> list[str]:
    requested = gate.request_adk_run or gate.request_live_llm or gate.request_ollama
    missing: list[str] = []
    if gate.request_adk_run and not gate.allow_adk_run:
        missing.append("allow_adk_run")
    if gate.request_live_llm and not gate.allow_live_llm:
        missing.append("allow_live_llm")
    if gate.request_ollama and not gate.allow_ollama:
        missing.append("allow_ollama")
    if gate.request_ollama and not gate.request_live_llm:
        missing.append("request_live_llm_for_ollama")
    if requested and not gate.explicit_operator_approval:
        missing.append("explicit_operator_approval")
    if requested and not gate.sanitized_evidence_ref:
        missing.append("sanitized_evidence_ref")
    if requested and not gate.governance_summary_output_ref:
        missing.append("governance_summary_output_ref")
    if requested and not gate.audit_ref:
        missing.append("audit_ref")
    return missing


def _runtime_execution_ready(
    gate: RuntimeProductizationGateConfigView,
    missing_conditions: list[str],
) -> bool:
    requested = gate.request_adk_run or gate.request_live_llm or gate.request_ollama
    return requested and not missing_conditions


def _resolve_recorded_run_evidence(
    *,
    recorded_run: RecordedRunEvidenceInput | None,
    runtime_result: RuntimeResult | None,
    recorded_run_evidence_provider: RecordedRunEvidenceProvider | None,
) -> RecordedRunEvidenceInput:
    if recorded_run is not None:
        return _validate_recorded_run_evidence(recorded_run)
    if runtime_result is not None and recorded_run_evidence_provider is not None:
        return _validate_recorded_run_evidence(
            recorded_run_evidence_provider.build_recorded_run_evidence(runtime_result)
        )
    raise ValueError(
        "recorded_run must be a RecordedRunEvidenceInput contract, or runtime_result "
        "must be provided with a RecordedRunEvidenceProvider contract."
    )


def _validate_recorded_run_evidence(
    value: RecordedRunEvidenceInput,
) -> RecordedRunEvidenceInput:
    if value is None:
        raise ValueError("recorded_run evidence contract is required.")
    return RecordedRunEvidenceInput.model_validate(value)


def _validate_adk_service_facts(
    value: AdkServiceFactsSummaryInput,
) -> AdkServiceFactsSummaryInput:
    if value is None:
        raise ValueError("adk_service_facts contract is required.")
    if isinstance(value, dict):
        if not value.get("lifecycle_summary"):
            raise ValueError("lifecycle_summary is required.")
        if not value.get("run_config_service_bundle_summary"):
            raise ValueError("run_config_service_bundle_summary is required.")
    return AdkServiceFactsSummaryInput.model_validate(value)


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _safe_metadata(value: dict[str, Any]) -> dict[str, Any]:
    return {
        str(key): item
        for key, item in value.items()
        if _metadata_value_is_safe(item)
    }


def _metadata_value_is_safe(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))
