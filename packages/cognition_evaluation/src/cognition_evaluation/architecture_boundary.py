"""Architecture boundary evaluation helpers."""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from cognition_evaluation.models import (
    EvaluationBaseModel,
    EvaluationFinding,
    EvaluationProfileRef,
    EvaluationResult,
)


ARCHITECTURE_BOUNDARY_EVALUATION_PROFILE = EvaluationProfileRef(
    ref="evaluation-profile://architecture-boundary/v1",
    name="architecture_boundary_evaluation",
    version="v1",
)

_CLI_PRODUCT_FACT_BUILDER_MARKERS = (
    "build_evidence_summary_answer_trace(",
    "build_evidence_summary_answer_artifact(",
    "build_evidence_summary_answer_observability_summary(",
    "build_evidence_summary_answer_trace_inspect(",
    "build_evidence_summary_answer_run(",
)
_CLI_PRODUCT_GATEWAY_ASSEMBLY_MARKERS = (
    "execute_external_readonly_ask_gateway_request(",
    "def _product_response_summary(",
)
_CLI_PRODUCT_RUN_REF_MARKERS = (
    "EVIDENCE_SUMMARY_ANSWER_RUN_REF_PREFIX",
    "evidence-summary-answer-run://",
    "operation://",
)
_CLI_DUTY_WHITELIST_MARKER_GROUPS = (
    {
        "criterion": "cli_product_answer_assembly_boundary",
        "status": "failed",
        "severity": "blocking",
        "message": (
            "CLI contains evidence-answer product assembly markers that should "
            "belong to product-level assembly or gateway boundaries."
        ),
        "recommended_action": "migrate_or_absorb",
        "markers": (
            "build_governed_evidence_digest_from_external_readonly_facts(",
            "build_evidence_summary_answer_context(",
            "build_evidence_summary_answer_follow_up_context(",
            "build_evidence_summary_answer_answerability_preflight_result(",
            "build_evidence_summary_answer_llm_invocation_request(",
            "build_evidence_summary_answer_result_from_llm_invocation_result(",
            "build_no_model_evidence_summary_answer_result(",
            "build_evidence_summary_answer_follow_up_seed(",
        ),
    },
    {
        "criterion": "cli_model_routing_boundary",
        "status": "failed",
        "severity": "blocking",
        "message": (
            "CLI contains model alias, provider profile, or route fact markers "
            "that should be owned by config/runtime/product routing boundaries."
        ),
        "recommended_action": "migrate_or_absorb",
        "markers": (
            "RuntimeLiveLlmConfigView()",
            "RuntimeLiveLlmConfigView",
            "ModelRouteFacts(",
            "def _apply_model_alias(",
            "def _external_llm_provider_selected(",
            "def _route_backend_provider(",
            "def _route_kind(",
        ),
    },
    {
        "criterion": "cli_provider_key_strategy_boundary",
        "status": "failed",
        "severity": "error",
        "message": (
            "CLI contains provider key storage or backend strategy markers; "
            "terminal prompting is allowed, credential backend policy is not."
        ),
        "recommended_action": "migrate_or_absorb",
        "markers": (
            "build_default_deepseek_credential_store(",
            "MacOSKeychainDeepSeekCredentialStore",
            "SecKeychain",
            "DEEPSEEK_KEYCHAIN_SERVICE",
            "def _provider_key_onboarding(",
            "def _load_stored_provider_key(",
            "def _save_provider_key(",
        ),
    },
    {
        "criterion": "cli_governance_precondition_boundary",
        "status": "failed",
        "severity": "error",
        "message": (
            "CLI contains governance precondition construction markers; CLI may "
            "collect approval facts but should not construct governance policy."
        ),
        "recommended_action": "migrate_or_absorb",
        "markers": (
            "LlmGovernancePrecondition(",
            "def _governance_precondition(",
            'decision="allow"',
        ),
    },
    {
        "criterion": "cli_evaluation_rule_boundary",
        "status": "warning",
        "severity": "warning",
        "message": (
            "CLI imports evaluation rules. This may be acceptable as temporary "
            "output checking, but should be reviewed before TUI/GUI reuse."
        ),
        "recommended_action": "classify",
        "markers": (
            "from cognition_evaluation.",
            "evaluate_requested_output_constraints(",
            "answer_matches_requested_output_",
        ),
    },
    {
        "criterion": "cli_answer_scoped_transform_private_boundary",
        "status": "failed",
        "severity": "blocking",
        "message": (
            "CLI contains answer-scoped transformation product execution "
            "markers. Answer transformations must run through the ask product "
            "entry service, not a CLI-private LLM path."
        ),
        "recommended_action": "migrate_or_absorb",
        "markers": (
            "build_evidence_summary_answer_transform_llm_request(",
            "build_evidence_summary_answer_transform_output(",
            "evidence_summary_answer_transform_quality_passed(",
            "evidence_summary_answer_transform_text_from_llm_result(",
            "local_evidence_summary_answer_transform_text(",
        ),
    },
    {
        "criterion": "cli_to_cli_product_path_coupling",
        "status": "warning",
        "severity": "warning",
        "message": (
            "A CLI channel calls another CLI product-path builder. If the state "
            "machine grows, extract a product entry service before implementing TUI."
        ),
        "recommended_action": "defer_to_follow_up_if_large",
        "markers": (
            "build_external_readonly_ask_cli_output(",
            "build_external_readonly_ask_follow_up_cli_output(",
            "ExternalReadonlyAskCliSessionState",
        ),
    },
    {
        "criterion": "cli_chat_bridge_ask_cli_wrapper_import",
        "status": "failed",
        "severity": "blocking",
        "message": (
            "Chat external-readonly bridge imports ask CLI wrappers directly. "
            "The bridge must consume an injected or product-level ask runner."
        ),
        "recommended_action": "migrate_or_absorb",
        "source_path_contains": "chat/external_readonly_bridge.py",
        "markers": (
            "from cognition_cli.external_readonly.ask import",
            "build_external_readonly_ask_initial_interaction",
            "build_external_readonly_ask_follow_up_interaction",
        ),
    },
    {
        "criterion": "cli_retired_external_readonly_answer_surface",
        "status": "failed",
        "severity": "blocking",
        "message": (
            "CLI still exposes the retired external-readonly answer smoke "
            "surface. Remove parser, dispatch, module and tests or formally "
            "re-home the capability."
        ),
        "recommended_action": "delete_or_rehome",
        "markers": (
            'external_readonly_command == "answer"',
            "external-readonly answer",
            "EXTERNAL_READONLY_ANSWER_COMMAND",
            "def external_readonly_answer_command(",
        ),
    },
)
_PRODUCT_ENTRY_BOUNDARY_MARKER_GROUPS = (
    {
        "criterion": "product_entry_argparse_namespace_boundary",
        "status": "failed",
        "severity": "blocking",
        "message": (
            "Product entry source contains CLI argparse namespace markers. "
            "Product entry services must receive structured product requests."
        ),
        "recommended_action": "migrate_or_absorb",
        "markers": (
            "argparse.Namespace",
            "from argparse import",
            "build_parser().parse_args(",
            "parse_args(argv)",
        ),
    },
    {
        "criterion": "product_entry_cli_import_boundary",
        "status": "failed",
        "severity": "blocking",
        "message": (
            "Product entry source imports CLI code. Dependency direction must "
            "remain CLI -> product entry, never product entry -> CLI."
        ),
        "recommended_action": "migrate_or_absorb",
        "markers": (
            "from cognition_cli.",
            "import cognition_cli",
        ),
    },
    {
        "criterion": "product_entry_terminal_io_boundary",
        "status": "failed",
        "severity": "blocking",
        "message": (
            "Product entry source contains terminal IO markers. Prompting and "
            "printing belong to channel adapters such as CLI or TUI."
        ),
        "recommended_action": "migrate_or_absorb",
        "markers": (
            "sys.stdin",
            "sys.stderr",
            "getpass.getpass(",
        ),
    },
)


class ArchitectureBoundarySnapshot(EvaluationBaseModel):
    """Safe architecture snapshot for deterministic boundary evaluation."""

    component_ref: str = Field(..., min_length=1)
    changed_paths: list[str] = Field(default_factory=list)
    direct_internal_imports: list[str] = Field(default_factory=list)
    cli_internal_candidate_consumption: list[str] = Field(default_factory=list)
    product_gateway_internal_candidate_consumption: list[str] = Field(
        default_factory=list
    )
    governance_decision_outputs: list[str] = Field(default_factory=list)
    governance_owns_evaluation_rules: list[str] = Field(default_factory=list)
    observability_as_linear_step: bool = False
    legacy_terms: list[str] = Field(default_factory=list)
    task_api_semantic_mapping: str | None = None
    workflow_runtime_semantic_mapping: str | None = None
    module_swallowing_risks: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_safe_snapshot(self) -> "ArchitectureBoundarySnapshot":
        _reject_forbidden_values(self.model_dump())
        return self


def evaluate_architecture_boundary(
    snapshot: ArchitectureBoundarySnapshot,
    *,
    evaluation_id: str = "evaluation://architecture-boundary",
) -> EvaluationResult:
    """Evaluate architecture boundaries without making governance decisions."""

    findings: list[EvaluationFinding] = []
    if snapshot.direct_internal_imports:
        findings.append(
            _finding(
                "dependency_direction_boundary",
                "failed",
                "error",
                "Implementation directly imports internal or candidate objects.",
                {"imports": snapshot.direct_internal_imports},
            )
        )
    if snapshot.cli_internal_candidate_consumption:
        findings.append(
            _finding(
                "cli_channel_boundary",
                "failed",
                "blocking",
                "CLI consumes internal candidate objects instead of acting as a channel adapter.",
                {"consumers": snapshot.cli_internal_candidate_consumption},
            )
        )
    if snapshot.product_gateway_internal_candidate_consumption:
        findings.append(
            _finding(
                "product_gateway_boundary",
                "failed",
                "blocking",
                "ProductGateway consumes internal candidate bodies instead of safe summaries.",
                {
                    "consumers": (
                        snapshot.product_gateway_internal_candidate_consumption
                    )
                },
            )
        )
    if snapshot.governance_decision_outputs:
        findings.append(
            _finding(
                "evaluation_governance_boundary",
                "failed",
                "blocking",
                "Evaluation outputs governance decisions such as allow or block.",
                {"outputs": snapshot.governance_decision_outputs},
            )
        )
    if snapshot.governance_owns_evaluation_rules:
        findings.append(
            _finding(
                "governance_evaluation_boundary",
                "failed",
                "error",
                "Governance owns evaluation rules that should remain in evaluation.",
                {"rules": snapshot.governance_owns_evaluation_rules},
            )
        )
    if snapshot.observability_as_linear_step:
        findings.append(
            _finding(
                "runtime_fact_bus_boundary",
                "warning",
                "warning",
                "Observability is modeled as a linear post-step instead of a runtime fact bus.",
            )
        )
    if snapshot.legacy_terms:
        findings.append(
            _finding(
                "legacy_route_pollution",
                "warning",
                "warning",
                "Legacy terms remain in active architecture surfaces.",
                {"terms": snapshot.legacy_terms},
            )
        )
    missing_axis = []
    if not snapshot.task_api_semantic_mapping:
        missing_axis.append("task_api")
    if not snapshot.workflow_runtime_semantic_mapping:
        missing_axis.append("workflow_runtime")
    if missing_axis:
        findings.append(
            _finding(
                "adk_axis_alignment",
                "warning",
                "warning",
                "Implementation lacks explicit ADK2.x axis semantic mapping.",
                {"missing": missing_axis},
            )
        )
    if snapshot.module_swallowing_risks:
        findings.append(
            _finding(
                "module_swallowing_risk",
                "warning",
                "warning",
                "One module appears to absorb another module's responsibility.",
                {"risks": snapshot.module_swallowing_risks},
            )
        )

    status = _result_status(findings)
    return EvaluationResult(
        evaluation_id=evaluation_id,
        status=status,
        findings=findings,
        profile_ref=ARCHITECTURE_BOUNDARY_EVALUATION_PROFILE,
        summary=(
            "Architecture boundary evaluation passed."
            if status == "passed"
            else "Architecture boundary evaluation produced findings."
        ),
        metadata={
            "component_ref": snapshot.component_ref,
            "changed_path_count": len(snapshot.changed_paths),
            "evaluation_scope": "architecture_boundary",
            "governance_decision": False,
        },
    )


def evaluate_cli_source_architecture_boundary(
    *,
    component_ref: str,
    source_text: str,
    source_path: str | None = None,
    evaluation_id: str = "evaluation://architecture-boundary/cli-source",
) -> EvaluationResult:
    """Evaluate CLI source text for product fact assembly responsibility drift."""

    consumers: list[str] = []
    for marker in _CLI_PRODUCT_FACT_BUILDER_MARKERS:
        if marker in source_text:
            consumers.append(marker.rstrip("("))
    for marker in _CLI_PRODUCT_GATEWAY_ASSEMBLY_MARKERS:
        if marker in source_text:
            consumers.append(marker.rstrip("("))
    for marker in _CLI_PRODUCT_RUN_REF_MARKERS:
        if marker in source_text:
            consumers.append(marker.strip("\"' ="))

    direct_internal_imports: list[str] = []
    if "product_gateway.response_summary_projection" in source_text:
        direct_internal_imports.append("product_gateway.response_summary_projection")
    if "observability_hub." in source_text or "from observability_hub" in source_text:
        direct_internal_imports.append("observability_hub")

    snapshot = ArchitectureBoundarySnapshot(
        component_ref=component_ref,
        changed_paths=[source_path] if source_path else [],
        direct_internal_imports=direct_internal_imports,
        cli_internal_candidate_consumption=sorted(set(consumers)),
        task_api_semantic_mapping="CLI renders task result summaries only.",
        workflow_runtime_semantic_mapping=(
            "CLI renders workflow-compatible product summaries only."
        ),
    )
    result = evaluate_architecture_boundary(snapshot, evaluation_id=evaluation_id)
    metadata = dict(result.metadata)
    metadata.update(
        {
            "evaluation_scope": "cli_source_architecture_boundary",
            "source_path": source_path,
            "source_text_retained": False,
        }
    )
    return result.model_copy(update={"metadata": metadata})


def evaluate_cli_duty_whitelist_source_boundary(
    *,
    component_ref: str,
    source_text: str,
    source_path: str | None = None,
    evaluation_id: str = "evaluation://architecture-boundary/cli-duty-whitelist",
) -> EvaluationResult:
    """Evaluate CLI source text against the allowed CLI duty whitelist.

    The helper is intentionally deterministic and source-text only: it reports
    duty drift markers without retaining source text or making governance
    decisions. Findings are meant to drive keep / migrate / absorb / delete
    classification in chain tasks.
    """

    findings: list[EvaluationFinding] = []
    for marker_group in _CLI_DUTY_WHITELIST_MARKER_GROUPS:
        criterion = str(marker_group["criterion"])
        source_path_contains = marker_group.get("source_path_contains")
        if source_path_contains and str(source_path_contains) not in (
            source_path or ""
        ):
            continue
        if (
            criterion == "cli_to_cli_product_path_coupling"
            and "from cognition_cli.external_readonly.ask import" not in source_text
        ):
            continue
        markers = tuple(str(marker) for marker in marker_group["markers"])
        matched_markers = sorted({marker for marker in markers if marker in source_text})
        if not matched_markers:
            continue
        findings.append(
            _finding(
                criterion,
                str(marker_group["status"]),
                str(marker_group["severity"]),
                str(marker_group["message"]),
                {
                    "matched_markers": matched_markers,
                    "matched_marker_count": len(matched_markers),
                    "recommended_action": str(marker_group["recommended_action"]),
                    "source_path": source_path,
                },
            )
        )

    status = _result_status(findings)
    return EvaluationResult(
        evaluation_id=evaluation_id,
        status=status,
        findings=findings,
        profile_ref=ARCHITECTURE_BOUNDARY_EVALUATION_PROFILE,
        summary=(
            "CLI duty whitelist evaluation passed."
            if status == "passed"
            else "CLI duty whitelist evaluation produced findings."
        ),
        metadata={
            "component_ref": component_ref,
            "evaluation_scope": "cli_duty_whitelist_source_boundary",
            "source_path": source_path,
            "source_text_retained": False,
            "governance_decision": False,
        },
    )


def evaluate_product_entry_source_boundary(
    *,
    component_ref: str,
    source_text: str,
    source_path: str | None = None,
    evaluation_id: str = "evaluation://architecture-boundary/product-entry",
) -> EvaluationResult:
    """Evaluate product entry source text for channel or CLI leakage."""

    findings: list[EvaluationFinding] = []
    for marker_group in _PRODUCT_ENTRY_BOUNDARY_MARKER_GROUPS:
        markers = tuple(str(marker) for marker in marker_group["markers"])
        matched_markers = sorted({marker for marker in markers if marker in source_text})
        if not matched_markers:
            continue
        findings.append(
            _finding(
                str(marker_group["criterion"]),
                str(marker_group["status"]),
                str(marker_group["severity"]),
                str(marker_group["message"]),
                {
                    "matched_markers": matched_markers,
                    "matched_marker_count": len(matched_markers),
                    "recommended_action": str(marker_group["recommended_action"]),
                    "source_path": source_path,
                },
            )
        )

    status = _result_status(findings)
    return EvaluationResult(
        evaluation_id=evaluation_id,
        status=status,
        findings=findings,
        profile_ref=ARCHITECTURE_BOUNDARY_EVALUATION_PROFILE,
        summary=(
            "Product entry boundary evaluation passed."
            if status == "passed"
            else "Product entry boundary evaluation produced findings."
        ),
        metadata={
            "component_ref": component_ref,
            "evaluation_scope": "product_entry_source_boundary",
            "source_path": source_path,
            "source_text_retained": False,
            "governance_decision": False,
        },
    )


def _finding(
    criterion: str,
    status: str,
    severity: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> EvaluationFinding:
    return EvaluationFinding(
        criterion=criterion,
        status=status,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        message=message,
        metadata=metadata or {},
    )


def _result_status(findings: list[EvaluationFinding]) -> str:
    if not findings:
        return "passed"
    if any(finding.status == "failed" for finding in findings):
        return "failed"
    return "warning"


def _reject_forbidden_values(value: Any) -> None:
    if isinstance(value, str):
        lowered = value.lower()
        forbidden_markers = (
            " access_token",
            "api_key",
            "api_token",
            "auth_token",
            "credential",
            "provider_token",
            "raw_html",
            "raw_provider_response",
            "refresh_token",
            "secret",
            "system_prompt",
            "_token.",
            "_token/",
            "_token=",
            "_token:",
            "_token.yaml",
            "/token",
            "token=",
            "token:",
            "traceback",
        )
        if any(marker in lowered for marker in forbidden_markers):
            raise ValueError("architecture boundary snapshot contains forbidden marker.")
    elif isinstance(value, dict):
        for item in value.values():
            _reject_forbidden_values(item)
    elif isinstance(value, list | tuple | set):
        for item in value:
            _reject_forbidden_values(item)
