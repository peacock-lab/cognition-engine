"""Internal mapping from ADK2 WorkflowRunner review candidates to governance cases."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from cognition_governance.adk_workflow_runner_review import (
    review_adk_workflow_runner_evidence,
)
from cognition_governance.models import GovernanceCase, GovernanceEvidence


ADK_WORKFLOW_RUNNER_EVIDENCE_TYPE = "adk_workflow_runner_execution"
ADK_WORKFLOW_RUNNER_CASE_TYPE = "adk_workflow_runner_governance_review"
ADK_WORKFLOW_RUNNER_REVIEW_SOURCE = (
    "cognition_governance.adk_workflow_runner_case_mapping"
)

_FORBIDDEN_OBJECT_MODULE_PREFIXES = (
    "google.adk",
    "adk_adapter",
    "runtime_container",
    "composition",
)


class AdkWorkflowRunnerGovernanceMappingResult(BaseModel):
    """Internal mapping result; this is not a governance decision."""

    model_config = ConfigDict(extra="forbid")

    governance_evidence: GovernanceEvidence
    governance_case: GovernanceCase
    notes: list[str] = Field(default_factory=list)


def map_adk_workflow_runner_evidence_to_governance_evidence(
    evidence: Any,
) -> GovernanceEvidence:
    """Map an ADK2 WorkflowRunner evidence candidate to internal GovernanceEvidence."""

    evidence_mapping = _as_mapping(evidence)
    evidence_id = _required_str(evidence_mapping.get("evidence_id"), "evidence_id")
    source = _required_str(evidence_mapping.get("source"), "source")

    return GovernanceEvidence(
        evidence_id=evidence_id,
        evidence_type=ADK_WORKFLOW_RUNNER_EVIDENCE_TYPE,
        source=source,
        summary=_evidence_summary(evidence_mapping),
        content_ref=None,
        metadata={
            "runtime_kind": _plain_str(evidence_mapping.get("runtime_kind")),
            "runtime_id": _plain_str(evidence_mapping.get("runtime_id")),
            "workflow_id": _plain_str(evidence_mapping.get("workflow_id")),
            "workflow_name": _plain_str(evidence_mapping.get("workflow_name")),
            "status": _plain_str(evidence_mapping.get("status")),
            "app_name": _plain_str(evidence_mapping.get("app_name")),
            "user_id": _plain_str(evidence_mapping.get("user_id")),
            "run_config": _mapping(evidence_mapping.get("run_config")),
            "service_bundle": _service_bundle_summary(evidence_mapping),
            "artifact_summary": _mapping(evidence_mapping.get("artifact_summary")),
            "session_summary": _mapping(evidence_mapping.get("session_summary")),
            "event_summary": _mapping(evidence_mapping.get("event_summary")),
            "lifecycle_summary": _mapping(evidence_mapping.get("lifecycle_summary")),
            "run_config_service_bundle_summary": _mapping(
                evidence_mapping.get("run_config_service_bundle_summary")
            ),
            "graph_summary": _mapping(evidence_mapping.get("graph_summary")),
            "trace_summary": _mapping(evidence_mapping.get("trace_summary")),
            "warnings": _list(evidence_mapping.get("warnings")),
            "contract_candidate_notes": _list(
                evidence_mapping.get("contract_candidate_notes")
            ),
            "observability_candidate": _plain_str(
                evidence_mapping.get("observability_candidate")
            ),
            "created_at": _plain_str(evidence_mapping.get("created_at")),
        },
    )


def map_adk_workflow_runner_review_to_governance_case(
    review: Any,
    *,
    evidence_ref: str | GovernanceEvidence | None = None,
) -> GovernanceCase:
    """Map an ADK2 WorkflowRunner governance review candidate to GovernanceCase."""

    review_mapping = _as_mapping(review)
    review_id = _required_str(review_mapping.get("review_id"), "review_id")
    evidence_id = _evidence_ref_id(evidence_ref) or _plain_str(
        review_mapping.get("evidence_id")
    )
    workflow_name = _plain_str(review_mapping.get("workflow_name"))
    status = _plain_str(review_mapping.get("status"))
    risk_level = _plain_str(review_mapping.get("risk_level"))

    return GovernanceCase(
        case_id=review_id,
        title="ADK2 WorkflowRunner governance review",
        case_type=ADK_WORKFLOW_RUNNER_CASE_TYPE,
        subject=workflow_name or evidence_id,
        context={
            "workflow_name": workflow_name,
            "status": status,
            "risk_level": risk_level,
            "evidence_id": evidence_id,
            "review_source": _plain_str(review_mapping.get("source")),
        },
        evidence_refs=[evidence_id] if evidence_id else [],
        policy_refs=[],
        metadata={
            "review_id": review_id,
            "findings": _findings_summary(review_mapping.get("findings")),
            "required_followups": _list(review_mapping.get("required_followups")),
            "policy_candidate_notes": _list(
                review_mapping.get("policy_candidate_notes")
            ),
            "contract_candidate_notes": _list(
                review_mapping.get("contract_candidate_notes")
            ),
            "config_context_candidate_notes": _list(
                review_mapping.get("config_context_candidate_notes")
            ),
            "created_at": _plain_str(review_mapping.get("created_at")),
            "mapping_boundary": [
                "No GovernanceDecision is produced.",
                "No formal publishing outcome is produced.",
                "Findings remain governance case metadata candidates.",
            ],
        },
    )


def map_adk_workflow_runner_governance_package(
    evidence: Any,
    *,
    review: Any | None = None,
) -> AdkWorkflowRunnerGovernanceMappingResult:
    """Map evidence and review candidates into an internal governance package."""

    governance_evidence = map_adk_workflow_runner_evidence_to_governance_evidence(
        evidence
    )
    review_candidate = review
    if review_candidate is None:
        review_candidate = review_adk_workflow_runner_evidence(evidence)

    governance_case = map_adk_workflow_runner_review_to_governance_case(
        review_candidate,
        evidence_ref=governance_evidence,
    )

    return AdkWorkflowRunnerGovernanceMappingResult(
        governance_evidence=governance_evidence,
        governance_case=governance_case,
        notes=[
            "Internal ADK2 WorkflowRunner governance mapping only.",
            "GovernanceDecision and GovernanceOutcome remain out of scope.",
            "Policy execution and formal publishing outcomes remain out of scope.",
        ],
    )


def _evidence_summary(evidence: dict[str, Any]) -> str:
    workflow_name = _plain_str(evidence.get("workflow_name")) or "unknown workflow"
    status = _plain_str(evidence.get("status")) or "unknown status"
    runtime_kind = _plain_str(evidence.get("runtime_kind")) or "unknown runtime"
    artifact_summary = _mapping(evidence.get("artifact_summary"))
    event_summary = _mapping(evidence.get("event_summary"))
    service_bundle = _service_bundle_summary(evidence)
    run_config = _mapping(evidence.get("run_config"))
    return (
        f"ADK2 WorkflowRunner evidence for {workflow_name}: "
        f"status={status}, runtime_kind={runtime_kind}, "
        f"mapped_run_config_fields={len(_list(run_config.get('mapped_fields')))}, "
        f"service_bundle_source={service_bundle.get('source') or 'unknown'}, "
        f"artifacts={artifact_summary.get('artifact_count', 0)}, "
        f"events={event_summary.get('event_count', 0)}."
    )


def _service_bundle_summary(evidence: dict[str, Any]) -> dict[str, Any]:
    service_bundle = _mapping(evidence.get("service_bundle"))
    assembly_options = _mapping(evidence.get("assembly_options"))
    service_bundle_options = _mapping(assembly_options.get("service_bundle_options"))
    summary = dict(service_bundle)
    if "source" not in summary and service_bundle_options.get("source") is not None:
        summary["source"] = service_bundle_options.get("source")
    return summary


def _findings_summary(value: Any) -> list[dict[str, Any]]:
    findings = _list(value)
    return [
        {
            "code": _plain_str(finding.get("code")),
            "severity": _plain_str(finding.get("severity")),
            "message": _plain_str(finding.get("message")),
            "evidence_path": _plain_str(finding.get("evidence_path")),
            "recommendation": _plain_str(finding.get("recommendation")),
        }
        for finding in (_as_mapping(item) for item in findings)
    ]


def _as_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return _sanitize_mapping(value)
    if hasattr(value, "model_dump"):
        return _sanitize_mapping(value.model_dump(mode="python"))
    raise TypeError(
        "ADK2 WorkflowRunner governance mapping expects a mapping-like input."
    )


def _mapping(value: Any) -> dict[str, Any]:
    return _sanitize_mapping(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return [_sanitize(item) for item in value] if isinstance(value, (list, tuple)) else []


def _plain_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _required_str(value: Any, field_name: str) -> str:
    if isinstance(value, str) and value:
        return value
    raise ValueError(f"{field_name} is required for ADK2 WorkflowRunner mapping.")


def _evidence_ref_id(value: str | GovernanceEvidence | None) -> str | None:
    if isinstance(value, GovernanceEvidence):
        return value.evidence_id
    return value if isinstance(value, str) and value else None


def _sanitize_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    return {str(key): _sanitize(value, key=str(key)) for key, value in mapping.items()}


def _sanitize(value: Any, *, key: str | None = None) -> Any:
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        return _sanitize_string(value, key=key)
    if isinstance(value, dict):
        return _sanitize_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    return {
        "object_type": type(value).__name__,
        "object_module": _sanitize_module(type(value).__module__),
    }


def _sanitize_string(value: str, *, key: str | None = None) -> str:
    if key == "object_module":
        return _sanitize_module(value)
    return value


def _sanitize_module(module_name: str) -> str:
    if module_name.startswith(_FORBIDDEN_OBJECT_MODULE_PREFIXES):
        return "external_runtime_object"
    return module_name
