"""Governance review candidates for ADK2 WorkflowRunner evidence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


FindingSeverity = Literal["info", "warning", "error"]
ReviewRiskLevel = Literal["low", "medium", "high"]


class AdkWorkflowRunnerGovernanceFinding(BaseModel):
    """One governance finding from an ADK2 WorkflowRunner evidence candidate."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=1)
    severity: FindingSeverity
    message: str = Field(..., min_length=1)
    evidence_path: str = Field(..., min_length=1)
    recommendation: str = Field(..., min_length=1)


class AdkWorkflowRunnerGovernanceReview(BaseModel):
    """Governance review candidate, not a formal GovernanceDecision."""

    model_config = ConfigDict(extra="forbid")

    review_id: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    evidence_id: str | None = None
    workflow_name: str | None = None
    status: str | None = None
    risk_level: ReviewRiskLevel
    findings: list[AdkWorkflowRunnerGovernanceFinding] = Field(default_factory=list)
    required_followups: list[str] = Field(default_factory=list)
    policy_candidate_notes: list[str] = Field(default_factory=list)
    contract_candidate_notes: list[str] = Field(default_factory=list)
    config_context_candidate_notes: list[str] = Field(default_factory=list)
    created_at: str


def review_adk_workflow_runner_evidence(evidence: Any) -> AdkWorkflowRunnerGovernanceReview:
    """Review an ADK2 WorkflowRunner evidence candidate as plain governance input."""

    evidence_mapping = _as_mapping(evidence)
    findings: list[AdkWorkflowRunnerGovernanceFinding] = []

    _check_main_chain(evidence_mapping, findings)
    _check_run_config(evidence_mapping, findings)
    _check_service_bundle(evidence_mapping, findings)
    _check_lifecycle(evidence_mapping, findings)
    _check_lifecycle_summary(evidence_mapping, findings)
    _check_run_config_service_bundle_summary(evidence_mapping, findings)
    _check_graph_summary(evidence_mapping, findings)
    _check_trace_summary(evidence_mapping, findings)
    _check_evidence_warnings(evidence_mapping, findings)

    return AdkWorkflowRunnerGovernanceReview(
        review_id=f"adk-workflow-runner-review-{uuid4()}",
        source="cognition_governance.adk_workflow_runner_review",
        evidence_id=_plain_str(evidence_mapping.get("evidence_id")),
        workflow_name=_plain_str(evidence_mapping.get("workflow_name")),
        status=_plain_str(evidence_mapping.get("status")),
        risk_level=_risk_level(findings),
        findings=findings,
        required_followups=_required_followups(findings),
        policy_candidate_notes=[
            "Review candidate only; no formal GovernanceDecision is produced.",
            "Governance consumes observability evidence summaries, not ADK native objects.",
        ],
        contract_candidate_notes=[
            "AdkWorkflowRunnerGovernanceReview is internal to cognition_governance.",
            "Promotion to public contract requires a separate decision.",
        ],
        config_context_candidate_notes=[
            "RunConfig and ServiceBundle options remain candidate config-context inputs.",
            "No config_assembly or config_contexts integration is performed in this review.",
        ],
        created_at=datetime.now(UTC).isoformat(),
    )


def _check_main_chain(
    evidence: dict[str, Any],
    findings: list[AdkWorkflowRunnerGovernanceFinding],
) -> None:
    if evidence.get("runtime_kind") == "adk2_workflow_runner":
        findings.append(
            _finding(
                code="ADK2_WORKFLOW_RUNNER_CHAIN_OBSERVED",
                severity="info",
                message="ADK2 WorkflowRunner evidence candidate was observed.",
                evidence_path="runtime_kind",
                recommendation="Keep this evidence as a candidate governance input.",
            )
        )
    else:
        findings.append(
            _finding(
                code="ADK2_WORKFLOW_RUNNER_CHAIN_MISSING",
                severity="warning",
                message="Evidence does not identify an ADK2 WorkflowRunner runtime kind.",
                evidence_path="runtime_kind",
                recommendation="Provide evidence produced by the ADK2 WorkflowRunner evidence entry.",
            )
        )

    if evidence.get("status") not in {"success", "SUCCESS", "RuntimeStatus.SUCCESS"}:
        findings.append(
            _finding(
                code="ADK2_WORKFLOW_RUNNER_STATUS_NOT_SUCCESS",
                severity="warning",
                message="Evidence status is not success.",
                evidence_path="status",
                recommendation="Review runtime errors before promoting this evidence.",
            )
        )


def _check_run_config(
    evidence: dict[str, Any],
    findings: list[AdkWorkflowRunnerGovernanceFinding],
) -> None:
    run_config = _mapping(evidence.get("run_config"))
    mapped_fields = _list(run_config.get("mapped_fields"))
    unmapped_fields = _list(run_config.get("unmapped_fields"))

    if not run_config:
        findings.append(
            _finding(
                code="RUN_CONFIG_SUMMARY_MISSING",
                severity="warning",
                message="RunConfig summary is missing from evidence.",
                evidence_path="run_config",
                recommendation="Include RunConfig summary from WorkflowResult metadata.",
            )
        )
        return

    if not mapped_fields:
        findings.append(
            _finding(
                code="RUN_CONFIG_MAPPED_FIELDS_MISSING",
                severity="warning",
                message="RunConfig mapped_fields is empty.",
                evidence_path="run_config.mapped_fields",
                recommendation="Verify ADK RunConfig options were mapped before execution.",
            )
        )
    if unmapped_fields:
        findings.append(
            _finding(
                code="RUN_CONFIG_UNMAPPED_FIELDS_PRESENT",
                severity="info",
                message="RunConfig has fields that are intentionally not mapped yet.",
                evidence_path="run_config.unmapped_fields",
                recommendation="Track unmapped fields as follow-up mapping candidates.",
            )
        )


def _check_service_bundle(
    evidence: dict[str, Any],
    findings: list[AdkWorkflowRunnerGovernanceFinding],
) -> None:
    service_bundle = _mapping(evidence.get("service_bundle"))
    assembly_options = _mapping(evidence.get("assembly_options"))
    bundle_options = _mapping(assembly_options.get("service_bundle_options"))
    source = bundle_options.get("source")

    if not service_bundle:
        findings.append(
            _finding(
                code="SERVICE_BUNDLE_SUMMARY_MISSING",
                severity="warning",
                message="ServiceBundle summary is missing from evidence.",
                evidence_path="service_bundle",
                recommendation="Include ServiceBundle metadata from assembly evidence.",
            )
        )
        return

    if not source:
        findings.append(
            _finding(
                code="SERVICE_BUNDLE_SOURCE_MISSING",
                severity="warning",
                message="ServiceBundle source is not explicit in assembly options.",
                evidence_path="assembly_options.service_bundle_options.source",
                recommendation="Record whether the bundle source is in_memory or provided_services.",
            )
        )
    for service_name in ("artifact_service", "session_service"):
        service = _mapping(service_bundle.get(service_name))
        if not service.get("adk_service_type"):
            findings.append(
                _finding(
                    code=f"{service_name.upper()}_TYPE_MISSING",
                    severity="warning",
                    message=f"{service_name} type summary is missing.",
                    evidence_path=f"service_bundle.{service_name}.adk_service_type",
                    recommendation="Record ADK service type names as plain metadata.",
                )
            )


def _check_lifecycle(
    evidence: dict[str, Any],
    findings: list[AdkWorkflowRunnerGovernanceFinding],
) -> None:
    artifact_summary = _mapping(evidence.get("artifact_summary"))
    session_summary = _mapping(evidence.get("session_summary"))
    event_summary = _mapping(evidence.get("event_summary"))

    if int(artifact_summary.get("artifact_count") or 0) <= 0:
        findings.append(
            _finding(
                code="ARTIFACT_LIFECYCLE_NOT_OBSERVED",
                severity="warning",
                message="No artifact lifecycle evidence was observed.",
                evidence_path="artifact_summary.artifact_count",
                recommendation="Run a workflow that writes artifacts through injected ArtifactService.",
            )
        )
    if not session_summary.get("session_id"):
        findings.append(
            _finding(
                code="SESSION_LIFECYCLE_NOT_OBSERVED",
                severity="warning",
                message="No session_id was observed in evidence.",
                evidence_path="session_summary.session_id",
                recommendation="Include session metadata from WorkflowResult invocation binding.",
            )
        )
    if int(event_summary.get("event_count") or 0) <= 0:
        findings.append(
            _finding(
                code="EVENT_LIFECYCLE_NOT_OBSERVED",
                severity="warning",
                message="No execution events were observed.",
                evidence_path="event_summary.event_count",
                recommendation="Include RuntimeResult or WorkflowResult events.",
            )
        )


def _check_lifecycle_summary(
    evidence: dict[str, Any],
    findings: list[AdkWorkflowRunnerGovernanceFinding],
) -> None:
    lifecycle_summary = _mapping(evidence.get("lifecycle_summary"))
    if not lifecycle_summary:
        return

    findings.append(
        _finding(
            code="ADK_LIFECYCLE_SUMMARY_OBSERVED",
            severity="info",
            message="Sanitized ADK artifact/session/event lifecycle summary was observed.",
            evidence_path="lifecycle_summary",
            recommendation="Keep lifecycle summary candidate-only until public contract promotion is reviewed.",
        )
    )

    if lifecycle_summary.get("candidate_only") is not True:
        findings.append(
            _finding(
                code="ADK_LIFECYCLE_SUMMARY_CANDIDATE_BOUNDARY_MISSING",
                severity="warning",
                message="Lifecycle summary does not declare candidate_only=true.",
                evidence_path="lifecycle_summary.candidate_only",
                recommendation="Mark lifecycle summary as candidate-only.",
            )
        )
    for field_name in (
        "formal_decision_enabled",
        "policy_execution_enabled",
        "governance_outcome_enabled",
    ):
        if lifecycle_summary.get(field_name) is not False:
            findings.append(
                _finding(
                    code="ADK_LIFECYCLE_SUMMARY_FORMAL_BOUNDARY_OPEN",
                    severity="warning",
                    message=f"Lifecycle summary has {field_name} not explicitly false.",
                    evidence_path=f"lifecycle_summary.{field_name}",
                    recommendation="Keep lifecycle summary out of formal governance execution.",
                )
            )

    if _contains_forbidden_runtime_module_text(lifecycle_summary):
        findings.append(
            _finding(
                code="ADK_LIFECYCLE_SUMMARY_RUNTIME_OBJECT_LEAKAGE",
                severity="warning",
                message="Lifecycle summary may contain unsanitized runtime object module names.",
                evidence_path="lifecycle_summary",
                recommendation="Remove ADK, adapter, runtime_container, or composition object modules from lifecycle summary.",
            )
        )
    context_state = _mapping(lifecycle_summary.get("context_state"))
    if context_state:
        findings.append(
            _finding(
                code="CONTEXT_STATE_LIFECYCLE_FACTS_OBSERVED",
                severity="info",
                message="Sanitized context/state lifecycle facts were observed.",
                evidence_path="lifecycle_summary.context_state",
                recommendation="Keep state facts key-only unless a later policy allows value review.",
            )
        )
        if context_state.get("raw_state_values_included") is not False:
            findings.append(
                _finding(
                    code="CONTEXT_STATE_RAW_VALUES_BOUNDARY_OPEN",
                    severity="warning",
                    message="Context/state facts do not explicitly exclude raw state values.",
                    evidence_path="lifecycle_summary.context_state.raw_state_values_included",
                    recommendation="Keep raw state values out of governance evidence.",
                )
            )


def _check_run_config_service_bundle_summary(
    evidence: dict[str, Any],
    findings: list[AdkWorkflowRunnerGovernanceFinding],
) -> None:
    summary = _mapping(evidence.get("run_config_service_bundle_summary"))
    if not summary:
        return

    findings.append(
        _finding(
            code="ADK_RUN_CONFIG_SERVICE_BUNDLE_SUMMARY_OBSERVED",
            severity="info",
            message="Sanitized ADK RunConfig and ServiceBundle governance summary was observed.",
            evidence_path="run_config_service_bundle_summary",
            recommendation="Keep the summary candidate-only until public contract promotion is reviewed.",
        )
    )

    if summary.get("candidate_only") is not True:
        findings.append(
            _finding(
                code="ADK_RUN_CONFIG_SERVICE_BUNDLE_CANDIDATE_BOUNDARY_MISSING",
                severity="warning",
                message="RunConfig/ServiceBundle summary does not declare candidate_only=true.",
                evidence_path="run_config_service_bundle_summary.candidate_only",
                recommendation="Mark RunConfig/ServiceBundle summary as candidate-only.",
            )
        )
    for field_name in (
        "formal_decision_enabled",
        "policy_execution_enabled",
        "governance_outcome_enabled",
    ):
        if summary.get(field_name) is not False:
            findings.append(
                _finding(
                    code="ADK_RUN_CONFIG_SERVICE_BUNDLE_FORMAL_BOUNDARY_OPEN",
                    severity="warning",
                    message=(
                        "RunConfig/ServiceBundle summary has "
                        f"{field_name} not explicitly false."
                    ),
                    evidence_path=f"run_config_service_bundle_summary.{field_name}",
                    recommendation="Keep RunConfig/ServiceBundle summary out of formal governance execution.",
                )
            )

    run_config = _mapping(summary.get("run_config"))
    service_bundle = _mapping(summary.get("service_bundle"))
    if run_config.get("live_call_enabled") is not False:
        findings.append(
            _finding(
                code="RUN_CONFIG_GOVERNANCE_VIEW_LIVE_BOUNDARY_OPEN",
                severity="warning",
                message="RunConfig governance view does not explicitly keep live_call_enabled=false.",
                evidence_path="run_config_service_bundle_summary.run_config.live_call_enabled",
                recommendation="Keep RunConfig governance view no-live in this candidate contract.",
            )
        )
    if run_config.get("call_attempted") is not False:
        findings.append(
            _finding(
                code="RUN_CONFIG_GOVERNANCE_VIEW_CALL_ATTEMPTED",
                severity="warning",
                message="RunConfig governance view indicates a call was attempted.",
                evidence_path="run_config_service_bundle_summary.run_config.call_attempted",
                recommendation="Do not use this summary as a live model or ADK run execution trigger.",
            )
        )
    if not _list(run_config.get("mapped_fields")):
        findings.append(
            _finding(
                code="RUN_CONFIG_GOVERNANCE_VIEW_MAPPED_FIELDS_MISSING",
                severity="warning",
                message="RunConfig governance view mapped_fields is empty.",
                evidence_path="run_config_service_bundle_summary.run_config.mapped_fields",
                recommendation="Preserve mapped RunConfig fields in the sanitized summary.",
            )
        )
    if not service_bundle.get("service_bundle_source"):
        findings.append(
            _finding(
                code="SERVICE_BUNDLE_GOVERNANCE_VIEW_SOURCE_MISSING",
                severity="warning",
                message="ServiceBundle governance view source is missing.",
                evidence_path=(
                    "run_config_service_bundle_summary.service_bundle."
                    "service_bundle_source"
                ),
                recommendation="Record service_bundle_source as sanitized metadata.",
            )
        )
    if service_bundle.get("external_persistence_enabled") is not False:
        findings.append(
            _finding(
                code="SERVICE_BUNDLE_EXTERNAL_PERSISTENCE_BOUNDARY_OPEN",
                severity="warning",
                message="ServiceBundle summary does not explicitly keep external persistence disabled.",
                evidence_path=(
                    "run_config_service_bundle_summary.service_bundle."
                    "external_persistence_enabled"
                ),
                recommendation="Keep external persistence behind a separate productization task.",
            )
        )

    if _contains_forbidden_runtime_module_text(summary):
        findings.append(
            _finding(
                code="ADK_RUN_CONFIG_SERVICE_BUNDLE_RUNTIME_OBJECT_LEAKAGE",
                severity="warning",
                message="RunConfig/ServiceBundle summary may contain unsanitized runtime object module names.",
                evidence_path="run_config_service_bundle_summary",
                recommendation="Remove ADK, adapter, runtime_container, or composition object modules from the summary.",
            )
        )


def _check_graph_summary(
    evidence: dict[str, Any],
    findings: list[AdkWorkflowRunnerGovernanceFinding],
) -> None:
    graph_summary = _mapping(evidence.get("graph_summary"))
    if not graph_summary:
        return

    findings.append(
        _finding(
            code="ADK_WORKFLOW_GRAPH_SUMMARY_OBSERVED",
            severity="info",
            message="Sanitized ADK Workflow graph summary was observed.",
            evidence_path="graph_summary",
            recommendation="Keep graph summary candidate-only until public contract promotion is reviewed.",
        )
    )

    boundary_paths = []
    for field_name in ("candidate_only", "summary_only", "refs_only"):
        if graph_summary.get(field_name) is not True:
            boundary_paths.append(f"graph_summary.{field_name}")
    for field_name in ("raw_adk_object_included", "raw_graph_object_included"):
        if graph_summary.get(field_name) is not False:
            boundary_paths.append(f"graph_summary.{field_name}")

    if boundary_paths:
        findings.append(
            _finding(
                code="ADK_WORKFLOW_GRAPH_SUMMARY_BOUNDARY_OPEN",
                severity="warning",
                message="Graph summary candidate boundary is not fully closed.",
                evidence_path=", ".join(boundary_paths),
                recommendation=(
                    "Keep graph summary candidate-only, summary-only, refs-only, "
                    "and exclude raw ADK or graph objects."
                ),
            )
        )

    if _contains_forbidden_runtime_module_text(graph_summary):
        findings.append(
            _finding(
                code="ADK_WORKFLOW_GRAPH_SUMMARY_RUNTIME_OBJECT_LEAKAGE",
                severity="warning",
                message="Graph summary may contain unsanitized runtime object module names.",
                evidence_path="graph_summary",
                recommendation="Remove ADK, adapter, runtime_container, or composition object modules from graph summary.",
            )
        )


def _check_trace_summary(
    evidence: dict[str, Any],
    findings: list[AdkWorkflowRunnerGovernanceFinding],
) -> None:
    trace_summary = _mapping(evidence.get("trace_summary"))
    if not trace_summary:
        return

    findings.append(
        _finding(
            code="ADK_WORKFLOW_TRACE_SUMMARY_OBSERVED",
            severity="info",
            message="Sanitized ADK Workflow trace summary was observed.",
            evidence_path="trace_summary",
            recommendation="Keep trace summary candidate-only until public contract promotion is reviewed.",
        )
    )

    boundary_paths = []
    for field_name in ("candidate_only", "summary_only", "refs_only"):
        if trace_summary.get(field_name) is not True:
            boundary_paths.append(f"trace_summary.{field_name}")
    for field_name in ("raw_event_included", "raw_payload_included"):
        if trace_summary.get(field_name) is not False:
            boundary_paths.append(f"trace_summary.{field_name}")

    if boundary_paths:
        findings.append(
            _finding(
                code="ADK_WORKFLOW_TRACE_SUMMARY_BOUNDARY_OPEN",
                severity="warning",
                message="Trace summary candidate boundary is not fully closed.",
                evidence_path=", ".join(boundary_paths),
                recommendation=(
                    "Keep trace summary candidate-only, summary-only, refs-only, "
                    "and exclude raw events or payloads."
                ),
            )
        )

    if _contains_forbidden_runtime_module_text(trace_summary):
        findings.append(
            _finding(
                code="ADK_WORKFLOW_TRACE_SUMMARY_RUNTIME_OBJECT_LEAKAGE",
                severity="warning",
                message="Trace summary may contain unsanitized runtime object module names.",
                evidence_path="trace_summary",
                recommendation="Remove ADK, adapter, runtime_container, or composition object modules from trace summary.",
            )
        )


def _check_evidence_warnings(
    evidence: dict[str, Any],
    findings: list[AdkWorkflowRunnerGovernanceFinding],
) -> None:
    warnings = _list(evidence.get("warnings"))
    for index, warning in enumerate(warnings):
        findings.append(
            _finding(
                code="EVIDENCE_WARNING_REPORTED",
                severity="warning",
                message=str(warning),
                evidence_path=f"warnings[{index}]",
                recommendation="Resolve or explicitly accept the evidence warning.",
            )
        )


def _risk_level(findings: list[AdkWorkflowRunnerGovernanceFinding]) -> ReviewRiskLevel:
    if any(finding.severity == "error" for finding in findings):
        return "high"
    if any(finding.severity == "warning" for finding in findings):
        return "medium"
    return "low"


def _required_followups(findings: list[AdkWorkflowRunnerGovernanceFinding]) -> list[str]:
    return [
        finding.recommendation
        for finding in findings
        if finding.severity in {"warning", "error"}
    ]


def _finding(
    *,
    code: str,
    severity: FindingSeverity,
    message: str,
    evidence_path: str,
    recommendation: str,
) -> AdkWorkflowRunnerGovernanceFinding:
    return AdkWorkflowRunnerGovernanceFinding(
        code=code,
        severity=severity,
        message=message,
        evidence_path=evidence_path,
        recommendation=recommendation,
    )


def _as_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return _sanitize_mapping(value)
    if hasattr(value, "model_dump"):
        return _sanitize_mapping(value.model_dump(mode="python"))
    raise TypeError(
        "review_adk_workflow_runner_evidence expects mapping-like evidence input."
    )


def _mapping(value: Any) -> dict[str, Any]:
    return _sanitize_mapping(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _plain_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _sanitize_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    return {str(key): _sanitize(value) for key, value in mapping.items()}


def _sanitize(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return _sanitize_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    return {"object_type": type(value).__name__, "object_module": type(value).__module__}


def _contains_forbidden_runtime_module_text(value: Any) -> bool:
    text = repr(value)
    return any(
        forbidden in text
        for forbidden in (
            "google.adk",
            "adk_adapter",
            "runtime_container",
            "composition",
        )
    )
