"""Channel-neutral product entry service for external-readonly ask."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any
from urllib.parse import urlparse

from schemas.llm_invocation import LlmInvocationRequest

from product_application_assembly.evidence_summary_answer_ask_action import (
    EvidenceSummaryAnswerAskActionInput,
    EvidenceSummaryAnswerAskActionResult,
    build_evidence_summary_answer_ask_blocked_output,
    build_evidence_summary_answer_ask_evidence_bridge_from_facts,
    run_evidence_summary_answer_ask_follow_up_action,
    run_evidence_summary_answer_ask_initial_action,
)
from product_application_assembly.evidence_summary_answer_ask_interaction import (
    EvidenceSummaryAnswerAskInteractionState,
)
from product_application_assembly.evidence_summary_answer_ask_policy import (
    EvidenceSummaryAnswerAskLlmServiceResolutionInput,
    EvidenceSummaryAnswerAskModelSelectionInput,
    EvidenceSummaryAnswerAskModelSelectionResult,
    EvidenceSummaryAnswerAskRoutePolicyInput,
    build_evidence_summary_answer_ask_governance_precondition,
    build_evidence_summary_answer_ask_route_facts,
    resolve_evidence_summary_answer_ask_llm_service,
    resolve_evidence_summary_answer_ask_model_selection,
)
from product_application_assembly.evidence_summary_answer_follow_up import (
    evidence_summary_answer_follow_up_seed_status_dict,
)
from product_application_assembly.evidence_summary_answer_product_output import (
    assemble_evidence_summary_answer_product_summary,
)
from product_application_assembly.evidence_summary_answer_transform import (
    build_evidence_summary_answer_transform_llm_request,
    build_evidence_summary_answer_transform_output,
    evidence_summary_answer_transform_quality_passed,
    evidence_summary_answer_transform_question_matches,
    evidence_summary_answer_transform_text_from_llm_result,
    local_evidence_summary_answer_transform_text,
)
from product_gateway.external_readonly_ask_bridge import (
    ExternalReadonlyAskEvidenceBridgeResult,
    build_external_readonly_ask_bridge_from_archives,
    build_external_readonly_ask_bridge_from_source_url,
)


PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ASK_ENTRY_SOURCE = (
    "product_application_assembly.evidence_summary_answer_ask_entry"
)
EVIDENCE_SUMMARY_ANSWER_ASK_ENTRY_PRODUCT_PATH = "external_readonly_ask_product_path"
EVIDENCE_SUMMARY_ANSWER_ASK_ENTRY_COMMAND = "cognition external-readonly ask"
EVIDENCE_SUMMARY_ANSWER_ASK_ENTRY_INTERACTION_MODE = (
    "evidence_summary_answer_generation"
)
EVIDENCE_SUMMARY_ANSWER_ASK_ENTRY_FAILURE = (
    "external_readonly_ask_product_entry_failure"
)
EVIDENCE_SUMMARY_ANSWER_ASK_PROVIDER_NOT_INJECTED = (
    "external_readonly_ask_llm_provider_not_injected"
)
EVIDENCE_SUMMARY_ANSWER_ASK_PROVIDER_RESOLUTION_FAILED = (
    "external_readonly_ask_llm_provider_resolution_failed"
)
EVIDENCE_SUMMARY_ANSWER_ASK_QUALITY_CONTRACT_VIOLATION = (
    "llm_answer_quality_contract_violation"
)
EVIDENCE_SUMMARY_ANSWER_ASK_ANSWER_TRANSFORMATION_WARNING = (
    "external_readonly_ask_answer_scoped_transformation"
)
EVIDENCE_SUMMARY_ANSWER_ASK_ANSWER_TRANSFORMATION_FAILURE = (
    "external_readonly_ask_answer_scoped_transformation_failed"
)
EVIDENCE_SUMMARY_ANSWER_ASK_SESSION_OPERATION_SUMMARY_WARNING = (
    "external_readonly_ask_session_operation_summary"
)
EVIDENCE_SUMMARY_ANSWER_ASK_MODEL_ALIAS_CONFLICT = (
    "model_alias_conflicts_with_explicit_model_options"
)
EVIDENCE_SUMMARY_ANSWER_ASK_MODEL_ALIAS_UNKNOWN = "model_alias_unknown"
REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION = "同意外部只读抓取"
EVIDENCE_SUMMARY_ANSWER_ASK_EXTERNAL_FETCH_DECLINED = (
    "external_readonly_ask_guided_external_fetch_declined"
)
EVIDENCE_SUMMARY_ANSWER_ASK_LIVE_LLM_DECLINED = (
    "external_readonly_ask_guided_live_llm_declined"
)
EVIDENCE_SUMMARY_ANSWER_ASK_QUESTION_REQUIRED = (
    "external_readonly_ask_guided_question_required"
)

ASK_ENTRY_EXIT_OK = 0
ASK_ENTRY_EXIT_RUNTIME_FAILURE = 1
ASK_ENTRY_EXIT_BLOCKING = 3


@dataclass(frozen=True)
class EvidenceSummaryAnswerAskEntryRequest:
    """Channel-neutral ask entry request.

    This object is not an argparse namespace and does not carry terminal prompt
    state. CLI, chat, TUI and future GUI adapters may collect values, then pass
    this structured request to the product entry service.
    """

    request_id: str
    source_url: str | None
    evidence_paths: tuple[str, ...]
    question: str
    follow_up_questions: tuple[str, ...] = ()
    repo_root: str | None = None
    product_name: str = "Cognition System / 认知系统"
    command: str = EVIDENCE_SUMMARY_ANSWER_ASK_ENTRY_COMMAND
    product_path: str = EVIDENCE_SUMMARY_ANSWER_ASK_ENTRY_PRODUCT_PATH
    input_channel: str = "unknown"
    source: str = PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ASK_ENTRY_SOURCE
    model_name: str | None = None
    model_alias: str | None = None
    provider_profile_ref: str | None = None
    model_profile_ref: str | None = None
    output_governance_profile_ref: str | None = None
    request_live_llm: bool = False
    allow_live_llm: bool = False
    request_ollama: bool = False
    allow_ollama: bool = False
    live_llm_approval_ref: str | None = None
    config_root: str | None = None
    environment: str | None = "local"
    profile: str | None = None
    ollama_api_base: str | None = None
    live_llm_timeout_seconds: float | None = None
    live_llm_max_tokens: int | None = None
    answer_preview_limit: int = 400
    network_gate_open: bool = False
    operator_approved: bool = False
    approval_ref: str | None = None
    runtime_fetch_approval_ref: str | None = None
    audit_ref: str | None = None
    envelope_ref: str | None = None
    evidence_ref: str | None = None
    controlled_output_ref: str | None = None
    sanitized_evidence_ref: str | None = None
    governance_summary_ref: str | None = None
    source_title: str | None = None
    allow_runtime_fetch: bool = False
    use_live_transport: bool = False
    max_bytes: int = 20_000
    max_excerpt_chars: int = 2_000
    timeout_seconds: int = 10
    redirect_limit: int = 0
    confirm_external_readonly_fetch: str | None = None
    provider_key: str | None = None
    provider_key_metadata: Mapping[str, Any] = field(default_factory=dict)
    channel_blocking_reasons: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceSummaryAnswerAskEntryServices:
    """Runtime dependencies injected into the product ask entry service."""

    refs_executor: Any | None = None
    fetch_executor: Any | None = None
    llm_invocation_service_factory: Any | None = None


def normalize_evidence_summary_answer_ask_entry_request(
    request: EvidenceSummaryAnswerAskEntryRequest,
) -> EvidenceSummaryAnswerAskEntryRequest:
    """Normalize shared ask entry request fields for every channel.

    CLI, product console and future third-party adapters may collect channel
    inputs, but product_application_assembly owns shared request defaults used
    by the external-readonly fetch gateway. This keeps channel adapters from
    copying CLI-private default refs.
    """

    slug = _entry_ref_slug(request)
    updates: dict[str, Any] = {}
    if not request.envelope_ref:
        updates["envelope_ref"] = f"evidence://external-readonly/envelope/{slug}"
    if not request.evidence_ref:
        updates["evidence_ref"] = f"evidence://external-readonly/item/{slug}"
    if not request.controlled_output_ref:
        updates["controlled_output_ref"] = f"outputs/external-readonly/{slug}.json"
    if not request.sanitized_evidence_ref:
        updates["sanitized_evidence_ref"] = f"evidence://external-readonly/{slug}"
    if not request.governance_summary_ref:
        updates["governance_summary_ref"] = f"summary://external-readonly/{slug}"
    return replace(request, **updates) if updates else request


def run_evidence_summary_answer_ask_entry(
    request: EvidenceSummaryAnswerAskEntryRequest,
    *,
    services: EvidenceSummaryAnswerAskEntryServices | None = None,
) -> EvidenceSummaryAnswerAskActionResult:
    """Run an initial ask entry and optional planned follow-up turns."""

    request = normalize_evidence_summary_answer_ask_entry_request(request)
    service_bundle = services or EvidenceSummaryAnswerAskEntryServices()
    model_selection = _model_selection(request)
    channel_reasons = tuple(str(reason) for reason in request.channel_blocking_reasons)
    if channel_reasons or model_selection.blocking_reasons:
        preflight_reasons = channel_reasons
    else:
        preflight_reasons = (
            _preflight_blocking_reasons(
                request,
                model_selection=model_selection,
            )
        )
    if model_selection.blocking_reasons:
        preflight_reasons = (*preflight_reasons, *model_selection.blocking_reasons)
    if (
        not model_selection.blocking_reasons
        and service_bundle.llm_invocation_service_factory is None
    ):
        preflight_reasons = (
            *preflight_reasons,
            EVIDENCE_SUMMARY_ANSWER_ASK_PROVIDER_NOT_INJECTED,
        )

    action_input = _action_input_from_request(
        request,
        model_selection=model_selection,
    )
    if preflight_reasons:
        summary = assemble_evidence_summary_answer_product_summary(
            request_id=request.request_id,
            answer_status="blocked",
            evidence_refs=(),
            additional_refs=(),
            blocking_reasons=preflight_reasons,
            warnings=(),
            readonly_refs_status="blocked",
            source_url_present=bool(request.source_url),
            evidence_path_count=len(request.evidence_paths),
            model_name=None,
            llm_call_allowed=False,
            llm_call_attempted=False,
            llm_runtime_call_performed=False,
            external_readonly_fetch_performed=False,
            external_readonly_network_call_performed=False,
            external_network_call_performed=False,
            product_path=request.product_path,
            metadata={"input_channel": request.input_channel},
        ).product_response_summary
        output = build_evidence_summary_answer_ask_blocked_output(
            action_input,
            blocking_reasons=preflight_reasons,
            warnings=(),
            product_response_summary=summary,
            fetch_request_id=None,
        )
        return EvidenceSummaryAnswerAskActionResult(
            exit_code=ASK_ENTRY_EXIT_BLOCKING,
            output=output,
            next_state=None,
        )

    action_result = run_evidence_summary_answer_ask_initial_action(
        action_input,
        evidence_bridge_builder=lambda product_input: _build_evidence_bridge(
            request,
            request_id=product_input.request_id,
            evidence_paths=product_input.evidence_paths,
            source_url=product_input.source_url,
            question=product_input.question,
            services=service_bundle,
        ),
        llm_service_resolver=(
            lambda product_input: _resolve_llm_service(
                request,
                service_bundle.llm_invocation_service_factory,
                request_id=product_input.request_id,
                model_selection=model_selection,
            )
        ),
    )
    output = action_result.output
    next_state = action_result.next_state
    if next_state is not None and request.follow_up_questions:
        output, next_state = run_evidence_summary_answer_ask_follow_up_sequence(
            output,
            session_state=next_state,
            follow_up_questions=request.follow_up_questions,
            request_id=request.request_id,
        )
    return EvidenceSummaryAnswerAskActionResult(
        exit_code=_exit_code_from_output(output),
        output=output,
        next_state=next_state,
    )


def run_evidence_summary_answer_ask_follow_up_entry(
    session_state: EvidenceSummaryAnswerAskInteractionState,
    follow_up_question: str,
    *,
    previous_output: Mapping[str, Any] | None = None,
    turns: tuple[Mapping[str, Any], ...] = (),
    request_id: str | None = None,
    follow_up_index: int | None = None,
) -> EvidenceSummaryAnswerAskActionResult:
    """Run one follow-up or answer-scoped action over an existing ask state."""

    effective_request_id = request_id or session_state.request_id
    effective_follow_up_index = follow_up_index or (
        session_state.follow_up_turn_index + 1
    )
    previous = previous_output or {}
    seed = session_state.follow_up_seed
    if _looks_like_guided_session_operation_summary_question(follow_up_question):
        output, _ = _run_guided_session_operation_summary_turn(
            follow_up_question,
            follow_up_index=effective_follow_up_index,
            previous_output=previous,
            turns=turns,
            request_id=effective_request_id,
            seed=seed,
        )
        return EvidenceSummaryAnswerAskActionResult(
            exit_code=_exit_code_from_output(output),
            output=output,
            next_state=session_state,
        )
    if previous and _looks_like_answer_scoped_transformation_question(
        follow_up_question
    ):
        output, next_seed = _run_answer_scoped_transformation_turn(
            follow_up_question,
            follow_up_index=effective_follow_up_index,
            previous_output=previous,
            service=session_state.service,
            session_state=session_state,
            request_id=effective_request_id,
            seed=seed,
        )
        next_state = (
            session_state
            if next_seed is seed
            else EvidenceSummaryAnswerAskInteractionState(
                request_id=session_state.request_id,
                source_url=session_state.source_url,
                evidence_paths=session_state.evidence_paths,
                evidence_bridge=session_state.evidence_bridge,
                follow_up_seed=next_seed,
                service=session_state.service,
                route_facts_factory=session_state.route_facts_factory,
                governance_precondition_factory=(
                    session_state.governance_precondition_factory
                ),
                follow_up_turn_index=session_state.follow_up_turn_index,
                metadata=session_state.metadata,
            )
        )
        return EvidenceSummaryAnswerAskActionResult(
            exit_code=_exit_code_from_output(output),
            output=output,
            next_state=next_state,
        )

    return run_evidence_summary_answer_ask_follow_up_action(
        session_state,
        follow_up_question,
    )


def run_evidence_summary_answer_ask_follow_up_sequence(
    initial_output: dict[str, Any],
    *,
    session_state: EvidenceSummaryAnswerAskInteractionState,
    follow_up_questions: tuple[str, ...],
    request_id: str,
) -> tuple[dict[str, Any], EvidenceSummaryAnswerAskInteractionState]:
    """Run planned same-process follow-up turns over one ask state."""

    turns = [_turn_summary(initial_output, turn_index=1)]
    current_seed = session_state.follow_up_seed
    if initial_output.get("status") != "success" or current_seed is None:
        initial_output["turn_count"] = len(turns)
        initial_output["turns"] = turns
        initial_output["follow_up_requested"] = bool(follow_up_questions)
        initial_output["follow_up_blocking_reasons"] = (
            ["source_turn_not_success_or_seed_missing"]
            if follow_up_questions
            else []
        )
        return initial_output, session_state

    current_state = session_state
    final_output = initial_output
    follow_up_index = 0
    for follow_up_question in follow_up_questions:
        follow_up_index += 1
        action_result = run_evidence_summary_answer_ask_follow_up_entry(
            current_state,
            follow_up_question,
            previous_output=final_output,
            turns=tuple(turns),
            request_id=request_id,
            follow_up_index=follow_up_index,
        )
        final_output = action_result.output
        if action_result.next_state is not None:
            current_state = action_result.next_state
        current_seed = current_state.follow_up_seed
        turns.append(_turn_summary(final_output, turn_index=follow_up_index + 1))
        if final_output.get("status") != "success" or current_seed is None:
            break

    final_output["initial_request_id"] = initial_output.get("request_id")
    final_output["turn_count"] = len(turns)
    final_output["turns"] = turns
    final_output["follow_up_requested"] = bool(follow_up_questions)
    final_output.setdefault("follow_up_blocking_reasons", [])
    return final_output, current_state


def _action_input_from_request(
    request: EvidenceSummaryAnswerAskEntryRequest,
    *,
    model_selection: EvidenceSummaryAnswerAskModelSelectionResult,
) -> EvidenceSummaryAnswerAskActionInput:
    return EvidenceSummaryAnswerAskActionInput(
        request_id=request.request_id,
        source_url=request.source_url,
        evidence_paths=request.evidence_paths,
        question=request.question,
        route_facts=_route_facts(request, model_selection=model_selection),
        governance_precondition=_ask_governance_precondition_from_request(request),
        model_name=model_selection.model_name,
        product_name=request.product_name,
        command=request.command,
        product_path=request.product_path,
        input_channel=request.input_channel,
        source=request.source,
        metadata=request.metadata,
    )


def _build_evidence_bridge(
    request: EvidenceSummaryAnswerAskEntryRequest,
    *,
    request_id: str,
    evidence_paths: tuple[str, ...],
    source_url: str | None,
    question: str,
    services: EvidenceSummaryAnswerAskEntryServices,
) -> dict[str, Any]:
    if source_url:
        return _evidence_bridge_from_source_url(
            request,
            request_id=request_id,
            source_url=source_url,
            question=question,
            fetch_executor=services.fetch_executor,
        )
    return _evidence_bridge_from_archives(
        request,
        request_id=request_id,
        evidence_paths=evidence_paths,
        question=question,
        refs_executor=services.refs_executor,
    )


def _evidence_bridge_from_source_url(
    request: EvidenceSummaryAnswerAskEntryRequest,
    *,
    request_id: str,
    source_url: str,
    question: str,
    fetch_executor: Any | None,
) -> dict[str, Any]:
    fetch_request_id = f"{request_id}/fetch"
    bridge_result = build_external_readonly_ask_bridge_from_source_url(
        fetch_gateway_input=_fetch_gateway_input_from_request(
            request,
            request_id=fetch_request_id,
            source_url=source_url,
        ),
        fetch_request_id=fetch_request_id,
        fetch_executor=fetch_executor,
    )
    return _evidence_bridge_from_gateway_bridge_result(
        request,
        bridge_result,
        request_id=request_id,
        question=question,
    )


def _evidence_bridge_from_archives(
    request: EvidenceSummaryAnswerAskEntryRequest,
    *,
    request_id: str,
    evidence_paths: tuple[str, ...],
    question: str,
    refs_executor: Any | None,
) -> dict[str, Any]:
    _ = refs_executor
    bridge_result = build_external_readonly_ask_bridge_from_archives(
        evidence_paths=evidence_paths,
        repo_root=request.repo_root,
        source=request.source,
        product_path=request.product_path,
    )
    return _evidence_bridge_from_gateway_bridge_result(
        request,
        bridge_result,
        request_id=request_id,
        question=question,
    )


def _evidence_bridge_from_gateway_bridge_result(
    request: EvidenceSummaryAnswerAskEntryRequest,
    bridge_result: ExternalReadonlyAskEvidenceBridgeResult,
    *,
    request_id: str,
    question: str,
) -> dict[str, Any]:
    if bridge_result.blocking_reasons and not bridge_result.facts_payloads:
        return _empty_bridge(
            blocking_reasons=bridge_result.blocking_reasons,
            warnings=bridge_result.warnings,
            evidence_refs=bridge_result.evidence_refs,
            additional_refs=bridge_result.additional_refs,
            readonly_refs_status=bridge_result.readonly_refs_status,
            fetch_request_id=bridge_result.fetch_request_id,
            external_readonly_fetch_performed=(
                bridge_result.external_readonly_fetch_performed
            ),
            external_readonly_network_call_performed=(
                bridge_result.external_readonly_network_call_performed
            ),
            external_network_call_performed=(
                bridge_result.external_network_call_performed
            ),
        )
    return _bridge_from_facts(
        request,
        bridge_result.facts_payloads,
        request_id=request_id,
        question=question,
        fetch_request_id=bridge_result.fetch_request_id,
        readonly_refs_status=bridge_result.readonly_refs_status,
        evidence_refs=bridge_result.evidence_refs,
        additional_refs=bridge_result.additional_refs,
        warnings=bridge_result.warnings,
        external_readonly_fetch_performed=(
            bridge_result.external_readonly_fetch_performed
        ),
        external_readonly_network_call_performed=(
            bridge_result.external_readonly_network_call_performed
        ),
        external_network_call_performed=bridge_result.external_network_call_performed,
    )


def _bridge_from_facts(
    request: EvidenceSummaryAnswerAskEntryRequest,
    facts_payloads: tuple[Mapping[str, Any], ...],
    *,
    request_id: str,
    question: str,
    fetch_request_id: str | None,
    readonly_refs_status: str,
    evidence_refs: tuple[Mapping[str, Any], ...] = (),
    additional_refs: tuple[Mapping[str, Any], ...] = (),
    warnings: tuple[str, ...] = (),
    external_readonly_fetch_performed: bool,
    external_readonly_network_call_performed: bool,
    external_network_call_performed: bool,
) -> dict[str, Any]:
    return build_evidence_summary_answer_ask_evidence_bridge_from_facts(
        facts_payloads,
        request_id=request_id,
        question=question,
        fetch_request_id=fetch_request_id,
        readonly_refs_status=readonly_refs_status,
        evidence_refs=evidence_refs,
        additional_refs=additional_refs,
        warnings=warnings,
        external_readonly_fetch_performed=external_readonly_fetch_performed,
        external_readonly_network_call_performed=(
            external_readonly_network_call_performed
        ),
        external_network_call_performed=external_network_call_performed,
        source=request.source,
        product_path=request.product_path,
    )


def _resolve_llm_service(
    request: EvidenceSummaryAnswerAskEntryRequest,
    factory: Any,
    *,
    request_id: str,
    model_selection: EvidenceSummaryAnswerAskModelSelectionResult,
) -> dict[str, Any]:
    return resolve_evidence_summary_answer_ask_llm_service(
        factory,
        EvidenceSummaryAnswerAskLlmServiceResolutionInput(
            config_root=request.config_root,
            environment=request.environment,
            profile=request.profile,
            request_id=request_id,
            surface=request.command,
            product_path=request.product_path,
            source=request.source,
            ollama_api_base=request.ollama_api_base,
            timeout_seconds=request.live_llm_timeout_seconds,
            max_tokens=request.live_llm_max_tokens,
            response_preview_limit=request.answer_preview_limit,
            network_gate_open=request.network_gate_open,
            operator_approved=request.operator_approved,
            approval_ref=request.live_llm_approval_ref,
            audit_ref=request.audit_ref,
            model_selection=model_selection,
            provider_key=request.provider_key,
            provider_key_metadata=request.provider_key_metadata,
        ),
        provider_key_env_name="DEEPSEEK_API_KEY",
        provider_resolution_failed_reason=(
            EVIDENCE_SUMMARY_ANSWER_ASK_PROVIDER_RESOLUTION_FAILED
        ),
        provider_exception_warning="external_readonly_ask_llm_provider_exception",
    )


def _fetch_gateway_input_from_request(
    request: EvidenceSummaryAnswerAskEntryRequest,
    *,
    request_id: str,
    source_url: str,
) -> dict[str, Any]:
    operator_approval_satisfied = bool(
        request.operator_approved
        and request.approval_ref
        and request.runtime_fetch_approval_ref
    )
    controlled_output_satisfied = bool(
        request.controlled_output_ref
        and request.audit_ref
        and request.sanitized_evidence_ref
    )
    gate_passed = bool(
        request.network_gate_open
        and operator_approval_satisfied
        and controlled_output_satisfied
    )
    return {
        "request_id": request_id,
        "source_url": source_url,
        "envelope_ref": request.envelope_ref,
        "evidence_ref": request.evidence_ref,
        "network_gate": {
            "request_ref": request_id,
            "status": "passed" if gate_passed else "blocked",
            "network_gate_open": request.network_gate_open,
            "allowed_for_network_request": request.network_gate_open,
            "operator_approval_satisfied": operator_approval_satisfied,
            "controlled_output_satisfied": controlled_output_satisfied,
            "tool_origin": "url_context",
            "operation_family": "fetch",
            "external_network_call_performed": False,
            "tool_execution_performed": False,
            "metadata": {
                "source": request.source,
                "network_gate_ref_present": request.network_gate_open,
                "approval_ref_present": bool(request.approval_ref),
                "audit_ref_present": bool(request.audit_ref),
                "sanitized_evidence_ref_present": bool(
                    request.sanitized_evidence_ref
                ),
            },
        },
        "source_title": request.source_title,
        "controlled_output_ref": request.controlled_output_ref,
        "operator_approved": request.operator_approved,
        "approval_ref": request.approval_ref,
        "audit_ref": request.audit_ref,
        "sanitized_evidence_ref": request.sanitized_evidence_ref,
        "governance_summary_ref": request.governance_summary_ref,
        "allow_runtime_fetch": request.allow_runtime_fetch,
        "runtime_fetch_approval_ref": request.runtime_fetch_approval_ref,
        "use_live_transport": request.use_live_transport,
        "max_bytes": request.max_bytes,
        "max_excerpt_chars": request.max_excerpt_chars,
        "timeout_seconds": request.timeout_seconds,
        "redirect_limit": request.redirect_limit,
        "metadata": {
            "source": request.source,
            "product_path": request.product_path,
            "input_channel": request.input_channel,
            "raw_response_included": False,
            "response_headers_included": False,
            "uploads_content": False,
            "writes_files": False,
        },
    }


def _route_facts(
    request: EvidenceSummaryAnswerAskEntryRequest,
    *,
    model_selection: EvidenceSummaryAnswerAskModelSelectionResult,
) -> Any:
    return build_evidence_summary_answer_ask_route_facts(
        EvidenceSummaryAnswerAskRoutePolicyInput(
            model_name=model_selection.model_name,
            provider_profile_ref=model_selection.provider_profile_ref,
            model_profile_ref=model_selection.model_profile_ref,
            output_governance_profile_ref=(
                model_selection.output_governance_profile_ref
            ),
            source=request.source,
            product_path=request.product_path,
        )
    )


def _ask_governance_precondition_from_request(
    request: EvidenceSummaryAnswerAskEntryRequest,
) -> Any:
    return build_evidence_summary_answer_ask_governance_precondition(
        approval_ref=request.live_llm_approval_ref,
        command=request.command,
        product_path=request.product_path,
        source=request.source,
    )


def _model_selection(
    request: EvidenceSummaryAnswerAskEntryRequest,
) -> EvidenceSummaryAnswerAskModelSelectionResult:
    return resolve_evidence_summary_answer_ask_model_selection(
        EvidenceSummaryAnswerAskModelSelectionInput(
            model_name=request.model_name,
            model_alias=request.model_alias,
            provider_profile_ref=request.provider_profile_ref,
            model_profile_ref=request.model_profile_ref,
            output_governance_profile_ref=request.output_governance_profile_ref,
        ),
        alias_conflict_reason=EVIDENCE_SUMMARY_ANSWER_ASK_MODEL_ALIAS_CONFLICT,
        alias_unknown_reason_prefix=EVIDENCE_SUMMARY_ANSWER_ASK_MODEL_ALIAS_UNKNOWN,
    )


def _preflight_blocking_reasons(
    request: EvidenceSummaryAnswerAskEntryRequest,
    *,
    model_selection: EvidenceSummaryAnswerAskModelSelectionResult,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not request.source_url and not request.evidence_paths:
        reasons.append("source_url_or_evidence_output_path_required")
    if request.source_url and request.evidence_paths:
        reasons.append("source_url_and_evidence_path_mutually_exclusive")
    if request.source_url and not _natural_language_confirmation_satisfied(request):
        reasons.append("external_readonly_natural_language_confirmation_required")
    if not request.question:
        reasons.append("question_required")
    if request.request_live_llm is not True:
        reasons.append("request_live_llm_required")
    external_provider_selected = model_selection.external_provider_selected
    if not external_provider_selected and request.request_ollama is not True:
        reasons.append("request_ollama_required")
    if request.allow_live_llm is not True:
        reasons.append("allow_live_llm_required")
    if not external_provider_selected and request.allow_ollama is not True:
        reasons.append("allow_ollama_required")
    if not request.live_llm_approval_ref:
        reasons.append("live_llm_approval_ref_required")
    if external_provider_selected:
        if not model_selection.provider_profile_ref:
            reasons.append("llm_provider_profile_ref_required")
        if not model_selection.model_profile_ref:
            reasons.append("llm_model_profile_ref_required")
        if not model_selection.output_governance_profile_ref:
            reasons.append("llm_output_governance_profile_ref_required")
        if not model_selection.model_name:
            reasons.append("external_llm_model_name_required")
        if not request.network_gate_open:
            reasons.append("external_llm_network_gate_open_required")
        if not request.operator_approved:
            reasons.append("external_llm_operator_approved_required")
        if not request.audit_ref:
            reasons.append("external_llm_audit_ref_required")
    if (
        request.live_llm_timeout_seconds is not None
        and request.live_llm_timeout_seconds <= 0
    ):
        reasons.append("live_llm_timeout_seconds_must_be_positive")
    if request.live_llm_max_tokens is not None and request.live_llm_max_tokens <= 0:
        reasons.append("live_llm_max_tokens_must_be_positive")
    if request.answer_preview_limit <= 0:
        reasons.append("answer_preview_limit_must_be_positive")
    if not model_selection.model_name:
        reasons.append("model_name_required")
    if (
        not external_provider_selected
        and request.ollama_api_base
        and not _local_ollama_api_base(request.ollama_api_base)
    ):
        reasons.append("ollama_api_base_must_be_local")
    return tuple(reasons)


def _run_answer_scoped_transformation_turn(
    follow_up_question: str,
    *,
    follow_up_index: int,
    previous_output: Mapping[str, Any],
    service: Any,
    session_state: EvidenceSummaryAnswerAskInteractionState,
    request_id: str,
    seed: Any,
) -> tuple[dict[str, Any], Any | None]:
    previous_answer = _normalized_optional_text(previous_output.get("answer"))
    if previous_answer is None:
        output = _answer_scoped_transformation_output(
            request_id=f"{request_id}/answer-transform-{follow_up_index}",
            question=follow_up_question,
            previous_output=previous_output,
            llm_request=None,
            llm_result=None,
            status="failed",
            answer=None,
            blocking_reasons=("answer_scoped_transformation_snapshot_missing",),
            seed=seed,
        )
        return output, seed

    local_answer = _local_answer_scoped_transformation_text(
        previous_answer=previous_answer,
        question=follow_up_question,
    )
    if local_answer is not None:
        output = _answer_scoped_transformation_output(
            request_id=f"{request_id}/answer-transform-{follow_up_index}",
            question=follow_up_question,
            previous_output=previous_output,
            llm_request=None,
            llm_result=None,
            status="success",
            answer=local_answer,
            blocking_reasons=(),
            seed=seed,
        )
        return output, seed

    answer_ref = (
        "answer-snapshot://external-readonly-ask/"
        f"{_safe_ref_part(request_id)}/turn-{follow_up_index:03d}"
    )
    llm_request = build_evidence_summary_answer_transform_llm_request(
        request_id=f"{request_id}/answer-transform-{follow_up_index}/llm",
        question=follow_up_question,
        previous_answer=previous_answer,
        route_facts=session_state.route_facts(),
        governance_precondition=session_state.governance_precondition(),
        answer_ref=answer_ref,
        evidence_refs=_ref_values(previous_output.get("evidence_refs")),
        source=PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ASK_ENTRY_SOURCE,
        product_path=EVIDENCE_SUMMARY_ANSWER_ASK_ENTRY_PRODUCT_PATH,
    )
    llm_invoker = _llm_invoker(service)
    if not callable(llm_invoker):
        output = _answer_scoped_transformation_output(
            request_id=f"{request_id}/answer-transform-{follow_up_index}",
            question=follow_up_question,
            previous_output=previous_output,
            llm_request=llm_request,
            llm_result=None,
            answer="",
            status="failed",
            blocking_reasons=(EVIDENCE_SUMMARY_ANSWER_ASK_PROVIDER_NOT_INJECTED,),
            seed=seed,
        )
        return output, seed
    llm_result = llm_invoker(llm_request)
    answer = evidence_summary_answer_transform_text_from_llm_result(llm_result)
    status = "success"
    blocking_reasons: tuple[str, ...] = ()
    if not llm_result.success:
        status = "failed"
        failure_type = (
            llm_result.failure_type.value
            if getattr(llm_result.failure_type, "value", None)
            else str(llm_result.failure_type or "llm_invocation_failed")
        )
        blocking_reasons = (f"llm_invocation_failure:{failure_type}",)
    elif not answer:
        status = "failed"
        blocking_reasons = ("llm_success_without_sanitized_answer",)
    elif not evidence_summary_answer_transform_quality_passed(
        answer,
        question=follow_up_question,
    ):
        status = "failed"
        blocking_reasons = ("answer_scoped_transformation_quality_violation",)

    output = _answer_scoped_transformation_output(
        request_id=f"{request_id}/answer-transform-{follow_up_index}",
        question=follow_up_question,
        previous_output=previous_output,
        llm_request=llm_request,
        llm_result=llm_result,
        status=status,
        answer=answer if status == "success" else None,
        blocking_reasons=blocking_reasons,
        seed=seed,
    )
    return output, seed if status == "success" else None


def _answer_scoped_transformation_output(
    *,
    request_id: str,
    question: str,
    previous_output: Mapping[str, Any],
    llm_request: LlmInvocationRequest | None,
    llm_result: Any | None,
    status: str,
    answer: str | None,
    blocking_reasons: tuple[str, ...],
    seed: Any,
) -> dict[str, Any]:
    return build_evidence_summary_answer_transform_output(
        request_id=request_id,
        command=EVIDENCE_SUMMARY_ANSWER_ASK_ENTRY_COMMAND,
        interaction_mode="external_readonly_ask_answer_scoped_transformation",
        product_path=EVIDENCE_SUMMARY_ANSWER_ASK_ENTRY_PRODUCT_PATH,
        question=question,
        previous_output=previous_output,
        llm_request=llm_request,
        llm_result=llm_result,
        status=status,
        answer=answer,
        blocking_reasons=blocking_reasons,
        seed=seed,
        follow_up_seed_status_dict=evidence_summary_answer_follow_up_seed_status_dict,
        warning_code=EVIDENCE_SUMMARY_ANSWER_ASK_ANSWER_TRANSFORMATION_WARNING,
        failure_type=EVIDENCE_SUMMARY_ANSWER_ASK_ANSWER_TRANSFORMATION_FAILURE,
    )


def _turn_summary(output: Mapping[str, Any], *, turn_index: int) -> dict[str, Any]:
    return {
        "turn_index": turn_index,
        "request_id": output.get("request_id"),
        "status": output.get("status"),
        "follow_up": output.get("follow_up") is True,
        "follow_up_turn_index": output.get("follow_up_turn_index"),
        "question_preview": output.get("question_preview"),
        "answer": output.get("answer"),
        "evidence_refs": output.get("evidence_refs") or [],
        "additional_refs": output.get("additional_refs") or [],
    }


def _run_guided_session_operation_summary_turn(
    follow_up_question: str,
    *,
    follow_up_index: int,
    previous_output: Mapping[str, Any],
    turns: tuple[Mapping[str, Any], ...],
    request_id: str,
    seed: Any,
) -> tuple[dict[str, Any], Any | None]:
    answer = _guided_session_operation_summary_text(turns)
    output = _local_guided_session_output(
        request_id=f"{request_id}/session-summary-{follow_up_index}",
        question=follow_up_question,
        previous_output=previous_output,
        status="success",
        answer=answer,
        blocking_reasons=(),
        seed=seed,
    )
    return output, seed


def _local_guided_session_output(
    *,
    request_id: str,
    question: str,
    previous_output: Mapping[str, Any],
    status: str,
    answer: str | None,
    blocking_reasons: tuple[str, ...],
    seed: Any,
) -> dict[str, Any]:
    evidence_refs = _list_value(previous_output.get("evidence_refs"))
    additional_refs = _list_value(previous_output.get("additional_refs"))
    follow_up_seed_payload = evidence_summary_answer_follow_up_seed_status_dict(seed)
    warnings = list(previous_output.get("warnings") or [])
    if status == "success":
        warnings.append(EVIDENCE_SUMMARY_ANSWER_ASK_SESSION_OPERATION_SUMMARY_WARNING)
    return {
        "product": "Cognition System / 认知系统",
        "command": EVIDENCE_SUMMARY_ANSWER_ASK_ENTRY_COMMAND,
        "interaction_mode": "external_readonly_ask_session_operation_summary",
        "product_path": EVIDENCE_SUMMARY_ANSWER_ASK_ENTRY_PRODUCT_PATH,
        "status": status,
        "success": status == "success",
        "failure_type": None if status == "success" else "session_operation_summary_failed",
        "request_id": request_id,
        "llm_request_id": None,
        "model_name": None,
        "source_url_present": previous_output.get("source_url_present") is True,
        "evidence_path_count": previous_output.get("evidence_path_count") or 0,
        "evidence_ref_count": len(evidence_refs),
        "additional_ref_count": len(additional_refs),
        "evidence_refs": evidence_refs,
        "additional_refs": additional_refs,
        "readonly_refs_status": previous_output.get("readonly_refs_status") or "ready",
        "answer_trace_ref": None,
        "answer_trace_status": None,
        "answer_trace_summary": {},
        "answer_trace_unavailable_reason": "session_operation_summary_current_process_only",
        "answer_artifact_ref": None,
        "answer_artifact_status": None,
        "answer_artifact_summary": {},
        "answer_artifact_unavailable_reason": "session_operation_summary_current_process_only",
        "trace_inspect_ref": None,
        "trace_inspect_status": "unavailable",
        "trace_inspect_summary": {},
        "trace_inspect_unavailable_reason": "session_operation_summary_current_process_only",
        "answer_run_ref": None,
        "answer_run_status": "unavailable",
        "answer_run_summary": {},
        "answer_run_unavailable_reason": "session_operation_summary_current_process_only",
        "question_preview": _preview(question, limit=120),
        "answer": answer,
        "answer_preview": _preview(answer, limit=120) if answer else None,
        "answer_length": len(answer) if answer else None,
        "guided_session_operation_summary": True,
        "summary_scope": "current_process_only; durable_session=false; memory_enabled=false",
        "llm_call_allowed": False,
        "llm_call_attempted": False,
        "llm_runtime_call_performed": False,
        "external_readonly_fetch_performed": False,
        "external_readonly_network_call_performed": False,
        "external_network_call_performed": False,
        "raw_response_included": False,
        "raw_html_included": False,
        "response_headers_included": False,
        "uploads_content": False,
        "writes_files": False,
        "failure_explanation": None,
        "recovery_hints": [],
        "blocking_reasons": blocking_reasons,
        "citation_failures": (),
        "warnings": warnings,
        "exit_code": 0 if status == "success" else 1,
        "follow_up": False,
        "follow_up_turn_index": None,
        "follow_up_available": follow_up_seed_payload.get("follow_up_allowed") is True,
        "follow_up_seed": follow_up_seed_payload,
        "temporary_follow_up": True,
        "durable_session": False,
        "memory_enabled": False,
        "product_response_summary": {
            "request_id": request_id,
            "status": status,
            "guided_session_operation_summary": True,
            "answer_run_ref": None,
            "answer_run_status": "unavailable",
            "answer_run_unavailable_reason": (
                "session_operation_summary_current_process_only"
            ),
            "readonly_refs_status": previous_output.get("readonly_refs_status")
            or "ready",
            "llm_call_attempted": False,
            "llm_runtime_call_performed": False,
        },
    }


def _looks_like_guided_session_operation_summary_question(question: str) -> bool:
    normalized = "".join(question.strip().split()).lower()
    if not normalized:
        return False
    if not any(keyword in normalized for keyword in ("总结", "小结", "回顾")):
        return False
    return any(
        keyword in normalized
        for keyword in (
            "今天的交流",
            "今天交流",
            "本次交流",
            "这次交流",
            "以上交流",
            "我们的交流",
            "我们今天",
            "当前交流",
            "刚才交流",
            "对话",
            "操作",
        )
    )


def _guided_session_operation_summary_text(
    turns: tuple[Mapping[str, Any], ...],
) -> str:
    lines = ["本次 --guided 进程内，你主要完成了这些交流："]
    for index, turn in enumerate(turns, start=1):
        question = _optional_string(turn.get("question_preview")) or "未记录问题"
        status = _optional_string(turn.get("status")) or "unknown"
        prefix = "首轮" if index == 1 else f"第 {index} 轮"
        lines.append(f"{index}. {prefix}：{question}（status: {status}）。")
    lines.append(
        "这个总结只基于当前进程内的 external-readonly ask turn 列表；"
        "不读取长期 Memory，不代表跨进程会话，也不重新抓取资料。"
    )
    return "\n".join(lines)


def _looks_like_answer_scoped_transformation_question(question: str) -> bool:
    return evidence_summary_answer_transform_question_matches(question)


def _local_answer_scoped_transformation_text(
    *,
    previous_answer: str,
    question: str,
) -> str | None:
    return local_evidence_summary_answer_transform_text(
        previous_answer=previous_answer,
        question=question,
    )


def _empty_bridge(
    *,
    blocking_reasons: tuple[str, ...],
    warnings: tuple[str, ...],
    readonly_refs_status: str,
    fetch_request_id: str | None,
    external_readonly_fetch_performed: bool,
    external_readonly_network_call_performed: bool,
    external_network_call_performed: bool,
    evidence_refs: tuple[Mapping[str, Any], ...] = (),
    additional_refs: tuple[Mapping[str, Any], ...] = (),
) -> dict[str, Any]:
    return {
        "context": None,
        "facts_payloads": (),
        "blocking_reasons": blocking_reasons,
        "warnings": warnings,
        "evidence_refs": evidence_refs,
        "additional_refs": additional_refs,
        "readonly_refs_status": readonly_refs_status,
        "fetch_request_id": fetch_request_id,
        "external_readonly_fetch_performed": external_readonly_fetch_performed,
        "external_readonly_network_call_performed": (
            external_readonly_network_call_performed
        ),
        "external_network_call_performed": external_network_call_performed,
    }


def _natural_language_confirmation_satisfied(
    request: EvidenceSummaryAnswerAskEntryRequest,
) -> bool:
    return (
        str(request.confirm_external_readonly_fetch or "").strip()
        == REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION
    )


def _explicit_model_name(request: EvidenceSummaryAnswerAskEntryRequest) -> str | None:
    model_name = request.model_name
    return model_name.strip() if isinstance(model_name, str) and model_name.strip() else None


def _local_ollama_api_base(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "http" and parsed.hostname in {
        "127.0.0.1",
        "localhost",
        "::1",
    }


def _ref_values(value: Any) -> tuple[str, ...]:
    refs: list[str] = []
    for item in _list_value(value):
        mapping = _mapping(item)
        ref = mapping.get("ref")
        if isinstance(ref, str) and ref:
            refs.append(ref)
    return tuple(dict.fromkeys(refs))


def _safe_ref_part(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-") or "ref"


def _entry_ref_slug(request: EvidenceSummaryAnswerAskEntryRequest) -> str:
    channel = _safe_ref_part(request.input_channel or "")
    if channel == "cli":
        return "cli-ask"
    if channel == "product_console":
        return "product-console-ask"
    if channel and channel != "unknown":
        return f"{channel}-ask"
    request_tail = str(request.request_id or "").rstrip("/").rsplit("/", 1)[-1]
    return _safe_ref_part(request_tail or "ask")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _llm_invoker(service: Any) -> Any | None:
    invoker = getattr(service, "invoke", None)
    return invoker if callable(invoker) else None


def _allowed_refs(value: Any) -> tuple[Mapping[str, Any], ...]:
    refs: list[Mapping[str, Any]] = []
    for item in _list_value(value):
        mapping = _mapping(item)
        if not mapping:
            continue
        refs.append(
            {
                "ref": str(mapping.get("ref") or ""),
                "kind": str(mapping.get("kind") or "unknown"),
                "purpose": mapping.get("purpose"),
                "metadata": dict(mapping.get("metadata") or {}),
            }
        )
    return tuple(refs)


def _list_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _string_tuple(value: Any) -> tuple[str, ...]:
    return tuple(str(item) for item in _list_value(value))


def _optional_string(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _normalized_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def _preview(value: str, *, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[:limit].rstrip()


def _exit_code_from_output(output: Mapping[str, Any]) -> int:
    status = output.get("status")
    if status == "success":
        return ASK_ENTRY_EXIT_OK
    if status in {"blocked", "insufficient_evidence"}:
        return ASK_ENTRY_EXIT_BLOCKING
    return ASK_ENTRY_EXIT_RUNTIME_FAILURE


__all__ = (
    "EVIDENCE_SUMMARY_ANSWER_ASK_ENTRY_COMMAND",
    "EVIDENCE_SUMMARY_ANSWER_ASK_ENTRY_PRODUCT_PATH",
    "EVIDENCE_SUMMARY_ANSWER_ASK_EXTERNAL_FETCH_DECLINED",
    "EVIDENCE_SUMMARY_ANSWER_ASK_LIVE_LLM_DECLINED",
    "EVIDENCE_SUMMARY_ANSWER_ASK_QUESTION_REQUIRED",
    "EvidenceSummaryAnswerAskEntryRequest",
    "EvidenceSummaryAnswerAskEntryServices",
    "normalize_evidence_summary_answer_ask_entry_request",
    "run_evidence_summary_answer_ask_entry",
    "run_evidence_summary_answer_ask_follow_up_entry",
    "run_evidence_summary_answer_ask_follow_up_sequence",
)
