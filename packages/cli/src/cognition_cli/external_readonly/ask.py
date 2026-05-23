"""External-readonly controlled question-answering product channel."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass, replace
import getpass
import json
import os
import re
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from cognition_cli.constants import (
    EXIT_BLOCKING,
    EXIT_OUTPUT_BOUNDARY_FAILURE,
    EXIT_RUNTIME_FAILURE,
    EXIT_OK,
    PRODUCT_NAME,
)
from cognition_cli.external_readonly.fetch import (
    REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION,
)
from cognition_cli.external_readonly.refs import (
    ExternalReadonlyRefsApplicationExecutor,
    build_external_readonly_refs_cli_output,
)
from config_contexts.runtime import (
    RuntimeConfigSelectionContext,
    RuntimeLiveLlmConfigView,
    RuntimeLiveLlmInvocationOptionsContext,
)
from contract_core.external_readonly_archive import (
    external_readonly_fetch_output_boundary_violated,
)
from contract_core.external_readonly_evidence import (
    validate_external_readonly_evidence_path,
)
from contract_core.llm_invocation import (
    GovernedLlmInvocationServiceFactory,
    LlmGovernancePrecondition,
    LlmInvocationRequest,
)
from contract_core.model_routing import ModelRouteFacts
from external_readonly.governed_summary_facts import (
    build_external_readonly_governed_summary_facts,
)
from product_application_assembly import (
    EVIDENCE_SUMMARY_ANSWER_GENERATION_INTERACTION_MODE,
    EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_INTERACTION_MODE,
    build_evidence_summary_answer_artifact,
    build_evidence_summary_answer_answerability_preflight_result,
    build_evidence_summary_answer_context,
    build_evidence_summary_answer_follow_up_context,
    build_evidence_summary_answer_follow_up_seed,
    build_evidence_summary_answer_llm_invocation_request,
    build_evidence_summary_answer_result_from_llm_invocation_result,
    build_evidence_summary_answer_trace,
    build_governed_evidence_digest_from_external_readonly_facts,
    build_no_model_evidence_summary_answer_result,
    evidence_summary_answer_follow_up_seed_status_dict,
    evidence_summary_answer_artifact_status_dict,
    evidence_summary_answer_artifact_summary_dict,
    evidence_summary_answer_result_status_dict,
    evidence_summary_answer_trace_status_dict,
    evidence_summary_answer_trace_summary_dict,
)
from product_gateway.external_readonly import (
    execute_external_readonly_fetch_gateway_request,
)
from product_gateway.external_readonly_ask import (
    execute_external_readonly_ask_gateway_request,
)


EXTERNAL_READONLY_ASK_COMMAND = "cognition external-readonly ask"
EXTERNAL_READONLY_ASK_SOURCE = "cognition_cli.external_readonly.ask"
EXTERNAL_READONLY_ASK_REQUEST_ID = "external-readonly-ask-request://cli/ask"
EXTERNAL_READONLY_ASK_INTERACTION_MODE = (
    EVIDENCE_SUMMARY_ANSWER_GENERATION_INTERACTION_MODE
)
EXTERNAL_READONLY_ASK_FAILURE = "external_readonly_ask_cli_failure"
EXTERNAL_READONLY_ASK_PROVIDER_NOT_INJECTED = (
    "external_readonly_ask_llm_provider_not_injected"
)
EXTERNAL_READONLY_ASK_PROVIDER_RESOLUTION_FAILED = (
    "external_readonly_ask_llm_provider_resolution_failed"
)
EXTERNAL_READONLY_ASK_PRODUCT_PATH = "external_readonly_ask_product_path"
EXTERNAL_READONLY_ASK_QUALITY_CONTRACT_VIOLATION = (
    "llm_answer_quality_contract_violation"
)
EXTERNAL_READONLY_ASK_MODEL_ALIAS_CONFLICT = (
    "model_alias_conflicts_with_explicit_model_options"
)
EXTERNAL_READONLY_ASK_MODEL_ALIAS_UNKNOWN = "model_alias_unknown"
EXTERNAL_READONLY_ASK_GUIDED_UNAVAILABLE_FOR_JSON_OUTPUT = (
    "external_readonly_ask_guided_unavailable_for_json_output"
)
EXTERNAL_READONLY_ASK_GUIDED_REQUIRES_INTERACTIVE_TERMINAL = (
    "external_readonly_ask_guided_requires_interactive_terminal"
)
EXTERNAL_READONLY_ASK_GUIDED_CANCELLED = "external_readonly_ask_guided_cancelled"
EXTERNAL_READONLY_ASK_GUIDED_EXTERNAL_FETCH_DECLINED = (
    "external_readonly_ask_guided_external_fetch_declined"
)
EXTERNAL_READONLY_ASK_GUIDED_LIVE_LLM_DECLINED = (
    "external_readonly_ask_guided_live_llm_declined"
)
EXTERNAL_READONLY_ASK_GUIDED_EXTERNAL_PROVIDER_DECLINED = (
    "external_readonly_ask_guided_external_provider_declined"
)
EXTERNAL_READONLY_ASK_GUIDED_QUESTION_REQUIRED = (
    "external_readonly_ask_guided_question_required"
)
EXTERNAL_READONLY_ASK_GUIDED_INPUT_REQUIRED = (
    "external_readonly_ask_guided_input_required"
)
EXTERNAL_READONLY_ASK_GUIDED_FOLLOW_UP_QUESTION_REQUIRED = (
    "external_readonly_ask_guided_follow_up_question_required"
)
DEEPSEEK_API_KEY_ENV = "DEEPSEEK_API_KEY"
DEEPSEEK_PROVIDER_KEY_REQUIRED = "deepseek_provider_key_required"
PROVIDER_KEY_PROMPT_UNAVAILABLE_FOR_JSON_OUTPUT = (
    "provider_key_prompt_unavailable_for_json_output"
)
PROVIDER_KEY_PROMPT_REQUIRES_INTERACTIVE_TERMINAL = (
    "provider_key_prompt_requires_interactive_terminal"
)
PROVIDER_KEY_INPUT_REQUIRED = "provider_key_input_required"
PROVIDER_KEY_PROMPT_CANCELLED = "provider_key_prompt_cancelled"
PROVIDER_KEY_STORE_UNAVAILABLE = "provider_key_store_unavailable"
PROVIDER_KEY_STORED_CREDENTIAL_NOT_FOUND = (
    "provider_key_stored_credential_not_found"
)
PROVIDER_KEY_STORED_CREDENTIAL_LOAD_FAILED = (
    "provider_key_stored_credential_load_failed"
)
PROVIDER_KEY_PERSISTENT_SAVE_FAILED = "provider_key_persistent_save_failed"
EXTERNAL_READONLY_ASK_MODEL_ALIAS_EXPLICIT_OPTION_FIELDS = (
    "model_name",
    "llm_provider_profile_ref",
    "llm_model_profile_ref",
    "llm_output_governance_profile_ref",
)

ExternalReadonlyAskLlmInvocationServiceFactory = GovernedLlmInvocationServiceFactory
ExternalReadonlyAskFetchExecutor = Callable[[Mapping[str, Any]], Any]


@dataclass(frozen=True)
class ExternalReadonlyAskCliSessionState:
    """CLI-local temporary state for same-process external-readonly follow-up."""

    request_id: str
    source_url: str | None
    evidence_paths: tuple[str, ...]
    evidence_bridge: Mapping[str, Any]
    follow_up_seed: Any | None
    service: Any | None
    args: argparse.Namespace
    follow_up_turn_index: int = 0


def external_readonly_ask_command(
    args: argparse.Namespace,
    *,
    refs_executor: ExternalReadonlyRefsApplicationExecutor | None = None,
    fetch_executor: ExternalReadonlyAskFetchExecutor | None = None,
    llm_invocation_service_factory: (
        ExternalReadonlyAskLlmInvocationServiceFactory | None
    ) = None,
) -> int:
    """Run an explicit controlled external-readonly QA product path."""

    try:
        exit_code, output = build_external_readonly_ask_cli_output(
            args,
            refs_executor=refs_executor,
            fetch_executor=fetch_executor,
            llm_invocation_service_factory=llm_invocation_service_factory,
        )
    except Exception as exc:  # pragma: no cover - defensive product boundary.
        print(f"{EXTERNAL_READONLY_ASK_COMMAND} error: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_FAILURE
    return _emit_external_readonly_ask_output(args, output, exit_code=exit_code)


def build_external_readonly_ask_cli_output(
    args: argparse.Namespace,
    *,
    refs_executor: ExternalReadonlyRefsApplicationExecutor | None = None,
    fetch_executor: ExternalReadonlyAskFetchExecutor | None = None,
    llm_invocation_service_factory: (
        ExternalReadonlyAskLlmInvocationServiceFactory | None
    ) = None,
    session_state_collector: (
        Callable[[ExternalReadonlyAskCliSessionState], None] | None
    ) = None,
) -> tuple[int, dict[str, Any]]:
    """Build the external-readonly QA product output without printing it."""

    request_id = str(args.request_id or EXTERNAL_READONLY_ASK_REQUEST_ID)
    guided_reasons = _apply_guided_onboarding(args)
    evidence_paths = tuple(getattr(args, "evidence_paths", ()) or ())
    source_url = _normalized_optional_text(getattr(args, "source_url", None))
    question = _normalized_question(getattr(args, "question", None))
    follow_up_questions = _normalized_follow_up_questions(
        getattr(args, "follow_up_questions", ()) or ()
    )
    provider_key: str | None = None
    provider_key_metadata: dict[str, Any] = {}
    preflight_reasons = guided_reasons or _apply_model_alias(args)
    if not preflight_reasons:
        preflight_reasons = _preflight_blocking_reasons(
            args,
            evidence_paths=evidence_paths,
            source_url=source_url,
            question=question,
        )
        if llm_invocation_service_factory is None:
            preflight_reasons = (
                *preflight_reasons,
                EXTERNAL_READONLY_ASK_PROVIDER_NOT_INJECTED,
            )
    if not preflight_reasons:
        provider_key_result = _provider_key_onboarding(args)
        provider_key = provider_key_result["provider_key"]
        provider_key_metadata = dict(provider_key_result["metadata"])
        preflight_reasons = tuple(provider_key_result["blocking_reasons"])
    if preflight_reasons:
        return (
            EXIT_BLOCKING,
            _blocked_output(
                request_id,
                evidence_paths=evidence_paths,
                source_url=source_url,
                question=question,
                blocking_reasons=preflight_reasons,
                warnings=(),
                product_response_summary=_product_response_summary(
                    request_id=request_id,
                    answer_status="blocked",
                    evidence_refs=(),
                    additional_refs=(),
                    blocking_reasons=preflight_reasons,
                    warnings=(),
                    readonly_refs_status="blocked",
                    source_url_present=bool(source_url),
                    evidence_path_count=len(evidence_paths),
                    model_name=None,
                    llm_call_allowed=False,
                    llm_call_attempted=False,
                    llm_runtime_call_performed=False,
                    external_readonly_fetch_performed=False,
                    external_readonly_network_call_performed=False,
                    external_network_call_performed=False,
                ),
                fetch_request_id=None,
            ),
        )

    evidence_bridge = _build_evidence_bridge(
        args,
        request_id=request_id,
        evidence_paths=evidence_paths,
        source_url=source_url,
        question=question,
        refs_executor=refs_executor,
        fetch_executor=fetch_executor,
    )
    if evidence_bridge["blocking_reasons"]:
        blocking_reasons = tuple(evidence_bridge["blocking_reasons"])
        return (
            EXIT_BLOCKING,
            _blocked_output(
                request_id,
                evidence_paths=evidence_paths,
                source_url=source_url,
                question=question,
                blocking_reasons=blocking_reasons,
                warnings=tuple(evidence_bridge["warnings"]),
                product_response_summary=_product_response_summary(
                    request_id=request_id,
                    answer_status="blocked",
                    evidence_refs=tuple(evidence_bridge["evidence_refs"]),
                    additional_refs=tuple(evidence_bridge["additional_refs"]),
                    blocking_reasons=blocking_reasons,
                    warnings=tuple(evidence_bridge["warnings"]),
                    readonly_refs_status=str(evidence_bridge["readonly_refs_status"]),
                    source_url_present=bool(source_url),
                    evidence_path_count=len(evidence_paths),
                    model_name=None,
                    llm_call_allowed=False,
                    llm_call_attempted=False,
                    llm_runtime_call_performed=False,
                    external_readonly_fetch_performed=bool(
                        evidence_bridge["external_readonly_fetch_performed"]
                    ),
                    external_readonly_network_call_performed=bool(
                        evidence_bridge[
                            "external_readonly_network_call_performed"
                        ]
                    ),
                    external_network_call_performed=bool(
                        evidence_bridge["external_network_call_performed"]
                    ),
                ),
                fetch_request_id=_optional_string(evidence_bridge["fetch_request_id"]),
            ),
        )

    context = evidence_bridge["context"]
    generation_policy_facts = _generation_policy_facts(context)
    preflight_result_model = build_evidence_summary_answer_answerability_preflight_result(
        context,
        metadata={
            "source": EXTERNAL_READONLY_ASK_SOURCE,
            "product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH,
        },
    )
    if preflight_result_model is not None:
        answer_result = evidence_summary_answer_result_status_dict(preflight_result_model)
        follow_up_seed = build_evidence_summary_answer_follow_up_seed(
            preflight_result_model,
            metadata={"product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH},
        )
        output = _output_from_answer_result(
            request_id,
            evidence_paths=evidence_paths,
            source_url=source_url,
            question=question,
            answer_result=answer_result,
            llm_request=None,
            evidence_bridge=evidence_bridge,
            resolution_warnings=(),
            follow_up_seed=follow_up_seed,
        )
        _collect_session_state(
            session_state_collector,
            request_id=request_id,
            source_url=source_url,
            evidence_paths=evidence_paths,
            evidence_bridge=evidence_bridge,
            follow_up_seed=follow_up_seed,
            service=None,
            args=args,
        )
        return _exit_code_from_output(output), output

    try:
        llm_request = build_evidence_summary_answer_llm_invocation_request(
            context,
            route_facts=_route_facts(args),
            governance_precondition=_governance_precondition(args),
            request_id=f"{request_id}/llm",
            generation_policy_facts=generation_policy_facts,
            metadata={"product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH},
        )
    except ValueError as exc:
        result = build_no_model_evidence_summary_answer_result(
            context,
            metadata={
                "source": EXTERNAL_READONLY_ASK_SOURCE,
                "bridge_reason": str(exc),
                "product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH,
            },
        )
        answer_result = evidence_summary_answer_result_status_dict(result)
        output = _output_from_answer_result(
            request_id,
            evidence_paths=evidence_paths,
            source_url=source_url,
            question=question,
            answer_result=answer_result,
            llm_request=None,
            evidence_bridge=evidence_bridge,
            resolution_warnings=(),
        )
        return _exit_code_from_output(output), output

    resolution = _resolve_llm_service(
        args,
        llm_invocation_service_factory,
        request_id=request_id,
        provider_key=provider_key,
        provider_key_metadata=provider_key_metadata,
    )
    if resolution["blocking_reasons"]:
        blocking_reasons = tuple(resolution["blocking_reasons"])
        return (
            EXIT_BLOCKING,
            _blocked_output(
                request_id,
                evidence_paths=evidence_paths,
                source_url=source_url,
                question=question,
                blocking_reasons=blocking_reasons,
                warnings=tuple(resolution["warnings"]),
                product_response_summary=_product_response_summary(
                    request_id=request_id,
                    answer_status="blocked",
                    evidence_refs=tuple(evidence_bridge["evidence_refs"]),
                    additional_refs=tuple(evidence_bridge["additional_refs"]),
                    blocking_reasons=blocking_reasons,
                    warnings=tuple(resolution["warnings"]),
                    readonly_refs_status=str(evidence_bridge["readonly_refs_status"]),
                    source_url_present=bool(source_url),
                    evidence_path_count=len(evidence_paths),
                    model_name=None,
                    llm_call_allowed=False,
                    llm_call_attempted=False,
                    llm_runtime_call_performed=False,
                    external_readonly_fetch_performed=bool(
                        evidence_bridge["external_readonly_fetch_performed"]
                    ),
                    external_readonly_network_call_performed=bool(
                        evidence_bridge[
                            "external_readonly_network_call_performed"
                        ]
                    ),
                    external_network_call_performed=bool(
                        evidence_bridge["external_network_call_performed"]
                    ),
                ),
                fetch_request_id=_optional_string(evidence_bridge["fetch_request_id"]),
            ),
        )

    service = resolution["service"]
    llm_result = service.invoke(llm_request)
    answer_result_model = build_evidence_summary_answer_result_from_llm_invocation_result(
        context,
        llm_result,
        generation_policy_facts=generation_policy_facts,
        metadata={"product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH},
    )
    answer_result = evidence_summary_answer_result_status_dict(answer_result_model)
    follow_up_seed = None
    if answer_result_model.status == "success":
        follow_up_seed = build_evidence_summary_answer_follow_up_seed(
            answer_result_model,
            metadata={"product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH},
        )
    output = _output_from_answer_result(
        request_id,
        evidence_paths=evidence_paths,
        source_url=source_url,
        question=question,
        answer_result=answer_result,
        llm_request=llm_request,
        evidence_bridge=evidence_bridge,
        resolution_warnings=tuple(resolution["warnings"]),
        follow_up_seed=follow_up_seed,
    )
    _collect_session_state(
        session_state_collector,
        request_id=request_id,
        source_url=source_url,
        evidence_paths=evidence_paths,
        evidence_bridge=evidence_bridge,
        follow_up_seed=follow_up_seed,
        service=service,
        args=args,
    )
    guided_follow_up = (
        getattr(args, "guided", False) is True
        and not follow_up_questions
        and _guided_follow_up_prompt_available()
    )
    if follow_up_questions or guided_follow_up:
        output = _output_with_follow_up_turns(
            output,
            follow_up_questions=follow_up_questions,
            source_url=source_url,
            evidence_paths=evidence_paths,
            evidence_bridge=evidence_bridge,
            service=service,
            args=args,
            request_id=request_id,
            source_seed=follow_up_seed,
            guided_follow_up=guided_follow_up,
        )
    return _exit_code_from_output(output), output


def build_external_readonly_ask_follow_up_cli_output(
    session_state: ExternalReadonlyAskCliSessionState,
    follow_up_question: str,
) -> tuple[int, dict[str, Any], ExternalReadonlyAskCliSessionState]:
    """Run one same-process follow-up over an existing ask session state."""

    question = _normalized_question(follow_up_question)
    if not question:
        output = _blocked_output(
            session_state.request_id,
            evidence_paths=session_state.evidence_paths,
            source_url=session_state.source_url,
            question=follow_up_question,
            blocking_reasons=(EXTERNAL_READONLY_ASK_GUIDED_FOLLOW_UP_QUESTION_REQUIRED,),
            warnings=(),
            product_response_summary=_product_response_summary(
                request_id=session_state.request_id,
                answer_status="blocked",
                evidence_refs=(),
                additional_refs=(),
                blocking_reasons=(
                    EXTERNAL_READONLY_ASK_GUIDED_FOLLOW_UP_QUESTION_REQUIRED,
                ),
                warnings=(),
                readonly_refs_status="blocked",
                source_url_present=bool(session_state.source_url),
                evidence_path_count=len(session_state.evidence_paths),
                model_name=None,
                llm_call_allowed=False,
                llm_call_attempted=False,
                llm_runtime_call_performed=False,
                external_readonly_fetch_performed=False,
                external_readonly_network_call_performed=False,
                external_network_call_performed=False,
            ),
            fetch_request_id=None,
        )
        return _exit_code_from_output(output), output, session_state
    if session_state.follow_up_seed is None or session_state.service is None:
        blocking_reasons = ("external_readonly_ask_follow_up_state_unavailable",)
        output = _blocked_output(
            session_state.request_id,
            evidence_paths=session_state.evidence_paths,
            source_url=session_state.source_url,
            question=question,
            blocking_reasons=blocking_reasons,
            warnings=(),
            product_response_summary=_product_response_summary(
                request_id=session_state.request_id,
                answer_status="blocked",
                evidence_refs=(),
                additional_refs=(),
                blocking_reasons=blocking_reasons,
                warnings=(),
                readonly_refs_status="blocked",
                source_url_present=bool(session_state.source_url),
                evidence_path_count=len(session_state.evidence_paths),
                model_name=None,
                llm_call_allowed=False,
                llm_call_attempted=False,
                llm_runtime_call_performed=False,
                external_readonly_fetch_performed=False,
                external_readonly_network_call_performed=False,
                external_network_call_performed=False,
            ),
            fetch_request_id=None,
        )
        return _exit_code_from_output(output), output, session_state

    follow_up_index = session_state.follow_up_turn_index + 1
    output, next_seed = _run_follow_up_turn(
        question,
        follow_up_index=follow_up_index,
        source_url=session_state.source_url,
        evidence_paths=session_state.evidence_paths,
        evidence_bridge=session_state.evidence_bridge,
        service=session_state.service,
        args=session_state.args,
        request_id=session_state.request_id,
        seed=session_state.follow_up_seed,
    )
    next_state = replace(
        session_state,
        follow_up_seed=next_seed,
        follow_up_turn_index=follow_up_index,
    )
    return _exit_code_from_output(output), output, next_state


def _collect_session_state(
    collector: Callable[[ExternalReadonlyAskCliSessionState], None] | None,
    *,
    request_id: str,
    source_url: str | None,
    evidence_paths: tuple[str, ...],
    evidence_bridge: Mapping[str, Any],
    follow_up_seed: Any | None,
    service: Any | None,
    args: argparse.Namespace,
) -> None:
    if collector is None:
        return
    collector(
        ExternalReadonlyAskCliSessionState(
            request_id=request_id,
            source_url=source_url,
            evidence_paths=evidence_paths,
            evidence_bridge=evidence_bridge,
            follow_up_seed=follow_up_seed,
            service=service,
            args=args,
        )
    )


def _build_evidence_bridge(
    args: argparse.Namespace,
    *,
    request_id: str,
    evidence_paths: tuple[str, ...],
    source_url: str | None,
    question: str,
    refs_executor: ExternalReadonlyRefsApplicationExecutor | None,
    fetch_executor: ExternalReadonlyAskFetchExecutor | None,
) -> dict[str, Any]:
    if source_url:
        return _evidence_bridge_from_source_url(
            args,
            request_id=request_id,
            source_url=source_url,
            question=question,
            fetch_executor=fetch_executor,
        )
    return _evidence_bridge_from_archives(
        request_id=request_id,
        evidence_paths=evidence_paths,
        question=question,
        refs_executor=refs_executor,
    )


def _evidence_bridge_from_source_url(
    args: argparse.Namespace,
    *,
    request_id: str,
    source_url: str,
    question: str,
    fetch_executor: ExternalReadonlyAskFetchExecutor | None,
) -> dict[str, Any]:
    fetch_request_id = f"{request_id}/fetch"
    execution = (fetch_executor or execute_external_readonly_fetch_gateway_request)(
        _fetch_gateway_input_from_args(
            args,
            request_id=fetch_request_id,
            source_url=source_url,
        )
    )
    product_response = execution.product_response
    runtime_result = getattr(execution, "runtime_result", None)
    fetch_metadata = dict(getattr(product_response, "metadata", {}) or {})
    fetch_status = getattr(getattr(product_response, "status", None), "value", None)
    fetch_blocking = tuple(str(item) for item in product_response.blocking_reasons)
    fetch_warnings = tuple(str(item) for item in product_response.warnings)
    external_fetch_performed = bool(
        fetch_metadata.get("runtime_fetch_performed", False)
    )
    external_network_call_performed = bool(
        fetch_metadata.get("external_network_call_performed", False)
    )
    if fetch_status != "success" or runtime_result is None:
        return _empty_bridge(
            blocking_reasons=fetch_blocking or ("external_readonly_ask_fetch_failed",),
            warnings=fetch_warnings,
            readonly_refs_status="blocked",
            fetch_request_id=fetch_request_id,
            external_readonly_fetch_performed=external_fetch_performed,
            external_readonly_network_call_performed=external_network_call_performed,
            external_network_call_performed=external_network_call_performed,
        )

    facts = build_external_readonly_governed_summary_facts(
        getattr(runtime_result, "envelope", None),
        evidence_output_path=None,
        evidence_written=getattr(runtime_result, "status", None) == "completed",
        reference_review_ready=(
            getattr(runtime_result, "status", None) == "completed"
            and getattr(runtime_result, "allowed_for_model_context", False) is True
        ),
    )
    return _bridge_from_facts(
        (facts.model_dump(mode="python"),),
        request_id=request_id,
        question=question,
        fetch_request_id=fetch_request_id,
        readonly_refs_status=facts.status,
        warnings=fetch_warnings,
        external_readonly_fetch_performed=external_fetch_performed,
        external_readonly_network_call_performed=external_network_call_performed,
        external_network_call_performed=external_network_call_performed,
    )


def _evidence_bridge_from_archives(
    *,
    request_id: str,
    evidence_paths: tuple[str, ...],
    question: str,
    refs_executor: ExternalReadonlyRefsApplicationExecutor | None,
) -> dict[str, Any]:
    refs_exit_code, refs_output = build_external_readonly_refs_cli_output(
        evidence_paths,
        request_id=f"{request_id}/refs",
        executor=refs_executor,
        metadata={
            "source": EXTERNAL_READONLY_ASK_SOURCE,
            "ask_product_path": True,
            "permanent_product_path": True,
        },
    )
    refs_summary = _mapping(refs_output.get("product_response_summary"))
    evidence_refs = tuple(_allowed_refs(refs_summary.get("evidence_refs")))
    additional_refs = tuple(_allowed_refs(refs_summary.get("additional_refs")))
    if refs_exit_code != EXIT_OK or refs_output.get("status") != "success":
        blocking_reasons = _string_tuple(refs_output.get("blocking_reasons"))
        return _empty_bridge(
            blocking_reasons=blocking_reasons
            or ("external_readonly_refs_not_success",),
            warnings=_string_tuple(refs_output.get("warnings")),
            evidence_refs=evidence_refs,
            additional_refs=additional_refs,
            readonly_refs_status=str(refs_output.get("readonly_refs_status") or "blocked"),
            fetch_request_id=None,
            external_readonly_fetch_performed=False,
            external_readonly_network_call_performed=False,
            external_network_call_performed=False,
        )

    facts_payloads, blocking_reasons = _archived_governed_summary_facts(
        evidence_paths,
        repo_root=Path.cwd(),
    )
    if blocking_reasons:
        return _empty_bridge(
            blocking_reasons=blocking_reasons,
            warnings=(),
            evidence_refs=evidence_refs,
            additional_refs=additional_refs,
            readonly_refs_status=str(refs_output.get("readonly_refs_status") or "blocked"),
            fetch_request_id=None,
            external_readonly_fetch_performed=False,
            external_readonly_network_call_performed=False,
            external_network_call_performed=False,
        )
    return _bridge_from_facts(
        tuple(facts_payloads),
        request_id=request_id,
        question=question,
        fetch_request_id=None,
        readonly_refs_status=str(refs_output.get("readonly_refs_status") or "ready"),
        evidence_refs=evidence_refs,
        additional_refs=additional_refs,
        warnings=_string_tuple(refs_output.get("warnings")),
        external_readonly_fetch_performed=False,
        external_readonly_network_call_performed=False,
        external_network_call_performed=False,
    )


def _bridge_from_facts(
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
    try:
        digests = [
            build_governed_evidence_digest_from_external_readonly_facts(
                facts,
                metadata={
                    "source": EXTERNAL_READONLY_ASK_SOURCE,
                    "product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH,
                },
            )
            for facts in facts_payloads
        ]
        context = build_evidence_summary_answer_context(
            request_id=f"{request_id}/context",
            user_question=question,
            digests=digests,
            metadata={
                "source": EXTERNAL_READONLY_ASK_SOURCE,
                "product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH,
            },
        )
    except Exception:
        return _empty_bridge(
            blocking_reasons=("evidence_summary_answer_context_bridge_failed",),
            warnings=warnings,
            evidence_refs=evidence_refs,
            additional_refs=additional_refs,
            readonly_refs_status="blocked",
            fetch_request_id=fetch_request_id,
            external_readonly_fetch_performed=external_readonly_fetch_performed,
            external_readonly_network_call_performed=(
                external_readonly_network_call_performed
            ),
            external_network_call_performed=external_network_call_performed,
        )
    return {
        "context": context,
        "facts_payloads": facts_payloads,
        "blocking_reasons": (),
        "warnings": warnings,
        "evidence_refs": evidence_refs or tuple(
            ref.model_dump(mode="python") for ref in context.evidence_refs
        ),
        "additional_refs": additional_refs or tuple(
            ref.model_dump(mode="python") for ref in context.additional_refs
        ),
        "readonly_refs_status": readonly_refs_status,
        "fetch_request_id": fetch_request_id,
        "external_readonly_fetch_performed": external_readonly_fetch_performed,
        "external_readonly_network_call_performed": (
            external_readonly_network_call_performed
        ),
        "external_network_call_performed": external_network_call_performed,
    }


def _generation_policy_facts(context: Any) -> dict[str, Any]:
    return {
        "profile": "controlled_live_answer_generation",
        "allow_answer_generation_success": True,
        "answer_generation_service_ref": (
            "service://cognition-cli/external-readonly-ask/generation"
        ),
        "answer_policy_ref": context.answer_policy_ref,
        "citation_policy_ref": context.citation_policy_ref,
    }


def _apply_guided_onboarding(args: argparse.Namespace) -> tuple[str, ...]:
    if getattr(args, "guided", False) is not True:
        return ()
    if args.format == "json" or args.json:
        return (EXTERNAL_READONLY_ASK_GUIDED_UNAVAILABLE_FOR_JSON_OUTPUT,)
    if not _guided_prompt_available():
        return (EXTERNAL_READONLY_ASK_GUIDED_REQUIRES_INTERACTIVE_TERMINAL,)
    try:
        return _fill_guided_first_use_args(args)
    except (EOFError, KeyboardInterrupt):
        return (EXTERNAL_READONLY_ASK_GUIDED_CANCELLED,)


def _fill_guided_first_use_args(args: argparse.Namespace) -> tuple[str, ...]:
    if not _normalized_optional_text(getattr(args, "source_url", None)) and not tuple(
        getattr(args, "evidence_paths", ()) or ()
    ):
        source = _read_guided_source()
        if source is None:
            return (EXTERNAL_READONLY_ASK_GUIDED_CANCELLED,)
        source = _normalize_guided_source_input(source)
        if not source:
            return (EXTERNAL_READONLY_ASK_GUIDED_INPUT_REQUIRED,)
        if source.startswith(("http://", "https://")):
            args.source_url = source
        else:
            args.evidence_paths = [source]

    if not _normalized_question(getattr(args, "question", None)):
        question = _read_guided_question()
        if question is None:
            return (EXTERNAL_READONLY_ASK_GUIDED_CANCELLED,)
        question = _normalize_guided_question_input(question)
        if not question:
            return (EXTERNAL_READONLY_ASK_GUIDED_QUESTION_REQUIRED,)
        args.question = question

    if not _model_alias(args) and not _explicit_model_name(args):
        model_alias = _read_guided_model_alias()
        if model_alias is None:
            return (EXTERNAL_READONLY_ASK_GUIDED_CANCELLED,)
        if model_alias not in {"deepseek", "gemma4"}:
            return (EXTERNAL_READONLY_ASK_GUIDED_INPUT_REQUIRED,)
        args.model_alias = model_alias

    source_url = _normalized_optional_text(getattr(args, "source_url", None))
    if source_url:
        if not _guided_confirm("允许本次外部只读抓取该 URL？"):
            return (EXTERNAL_READONLY_ASK_GUIDED_EXTERNAL_FETCH_DECLINED,)
        _apply_guided_external_readonly_fetch_confirmation(args)

    if not _guided_confirm("允许本次受控大模型回答？"):
        return (EXTERNAL_READONLY_ASK_GUIDED_LIVE_LLM_DECLINED,)
    _apply_guided_live_llm_confirmation(args)

    if _guided_local_ollama_selected(args):
        _apply_guided_ollama_confirmation(args)
        return ()

    if _guided_external_provider_selected(args):
        if not _guided_confirm("允许本次外部模型 provider 调用？"):
            return (EXTERNAL_READONLY_ASK_GUIDED_EXTERNAL_PROVIDER_DECLINED,)
        _apply_guided_external_provider_confirmation(args)
        if (
            not os.getenv(DEEPSEEK_API_KEY_ENV)
            and not getattr(args, "prompt_provider_key", False)
            and not getattr(args, "use_stored_provider_key", False)
        ):
            key_mode = _read_guided_provider_key_mode()
            if key_mode is None:
                return (EXTERNAL_READONLY_ASK_GUIDED_CANCELLED,)
            if key_mode == "stored":
                args.use_stored_provider_key = True
            elif key_mode == "prompt":
                args.prompt_provider_key = True
            else:
                return (EXTERNAL_READONLY_ASK_GUIDED_INPUT_REQUIRED,)
    return ()


def _guided_prompt_available() -> bool:
    if os.getenv("CI"):
        return False
    return sys.stdin.isatty() and sys.stderr.isatty()


def _guided_follow_up_prompt_available() -> bool:
    if os.getenv("CI"):
        return False
    return sys.stdin.isatty() and sys.stderr.isatty()


def _read_guided_source() -> str | None:
    return _read_guided_line("请输入 URL 或 evidence path: ")


def _read_guided_question() -> str | None:
    return _read_guided_line("请输入问题: ")


def _read_guided_follow_up_question() -> str | None:
    return _read_guided_line("请输入追问问题: ")


def _read_guided_follow_up_decision() -> tuple[str, str | None]:
    choice = _read_guided_line(
        "继续围绕同一证据追问？ 输入 yes/no，或直接输入追问问题: "
    )
    if choice is None:
        return ("cancel", None)
    normalized = " ".join(str(choice or "").strip().lower().split())
    if normalized in {"y", "yes", "true", "1", "同意", "确认", "允许", "继续"}:
        return ("continue", None)
    if normalized in {"n", "no", "false", "0", "不同意", "取消", "否", "不", "不用"}:
        return ("decline", None)
    question = _normalize_guided_question_input(choice)
    if question:
        return ("question", question)
    return ("decline", None)


def _read_guided_model_alias() -> str | None:
    print("请选择模型：1) deepseek  2) gemma4", file=sys.stderr)
    choice = _read_guided_line("请输入 1、2、deepseek 或 gemma4: ")
    normalized = _normalize_guided_choice_input(
        choice,
        labels=("model", "model alias", "模型", "选择模型"),
    )
    if normalized in {"1", "deepseek"}:
        return "deepseek"
    if normalized in {"2", "gemma4"}:
        return "gemma4"
    if not normalized:
        return None
    return normalized


def _read_guided_provider_key_mode() -> str | None:
    print("请选择 DeepSeek key 使用方式：1) 使用已保存  2) 输入 key  3) 取消", file=sys.stderr)
    choice = _read_guided_line("请输入 1、2 或 3: ")
    normalized = _normalize_guided_choice_input(
        choice,
        labels=("key", "key mode", "provider key", "deepseek key", "方式", "key 方式"),
    )
    if normalized in {"1", "stored", "saved", "use-stored", "使用已保存"}:
        return "stored"
    if normalized in {"2", "prompt", "input", "输入", "输入key", "输入 key"}:
        return "prompt"
    if normalized in {"3", "cancel", "取消"}:
        return None
    return normalized or None


def _guided_confirm(prompt: str) -> bool:
    choice = _read_guided_line(f"{prompt} 输入 yes/no: ")
    normalized = " ".join(str(choice or "").strip().lower().split())
    return normalized in {"y", "yes", "true", "1", "同意", "确认", "允许"}


def _read_guided_line(prompt: str) -> str | None:
    print(prompt, end="", file=sys.stderr, flush=True)
    try:
        raw_value = sys.stdin.readline()
    except KeyboardInterrupt:
        print("", file=sys.stderr)
        return None
    if raw_value == "":
        return None
    return raw_value.strip()


def _strip_guided_field_label(value: str, labels: tuple[str, ...]) -> str:
    text = str(value or "").strip()
    lowered = text.lower()
    for label in labels:
        normalized_label = label.lower()
        for separator in (":", "："):
            prefix = f"{normalized_label}{separator}"
            if lowered.startswith(prefix):
                return text[len(prefix) :].strip()
    return text


def _normalize_guided_source_input(value: str | None) -> str:
    text = str(value or "").strip()
    match = re.search(r"https?://\S+", text)
    if match:
        return match.group(0).rstrip(".,;，；。)")
    return _strip_guided_field_label(
        text,
        (
            "url/evidence",
            "url",
            "source url",
            "source",
            "evidence path",
            "evidence",
            "来源",
            "地址",
            "路径",
        ),
    )


def _normalize_guided_question_input(value: str | None) -> str:
    return _strip_guided_field_label(
        str(value or ""),
        ("question", "q", "问题", "提问"),
    )


def _normalize_guided_choice_input(
    value: str | None,
    *,
    labels: tuple[str, ...],
) -> str:
    stripped = _strip_guided_field_label(str(value or ""), labels)
    return " ".join(stripped.strip().lower().split())


def _apply_guided_external_readonly_fetch_confirmation(args: argparse.Namespace) -> None:
    args.confirm_external_readonly_fetch = REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION
    args.operator_approved = True
    args.network_gate_open = True
    args.allow_runtime_fetch = True
    args.use_live_transport = True
    args.approval_ref = args.approval_ref or "approval://external-readonly-ask/guided"
    args.runtime_fetch_approval_ref = (
        args.runtime_fetch_approval_ref
        or "approval://external-readonly-ask/guided-runtime-fetch"
    )
    args.audit_ref = args.audit_ref or "audit://external-readonly-ask/guided"


def _apply_guided_live_llm_confirmation(args: argparse.Namespace) -> None:
    args.request_live_llm = True
    args.allow_live_llm = True
    args.live_llm_approval_ref = (
        args.live_llm_approval_ref
        or "approval://external-readonly-ask/guided-live-llm"
    )


def _apply_guided_ollama_confirmation(args: argparse.Namespace) -> None:
    args.request_ollama = True
    args.allow_ollama = True


def _apply_guided_external_provider_confirmation(args: argparse.Namespace) -> None:
    args.operator_approved = True
    args.network_gate_open = True
    args.audit_ref = args.audit_ref or "audit://external-readonly-ask/guided"


def _guided_local_ollama_selected(args: argparse.Namespace) -> bool:
    alias = _model_alias(args)
    if alias == "gemma4":
        return True
    if alias == "deepseek":
        return False
    return not _guided_external_provider_selected(args)


def _guided_external_provider_selected(args: argparse.Namespace) -> bool:
    alias = _model_alias(args)
    if alias == "deepseek":
        return True
    if alias == "gemma4":
        return False
    return _external_llm_provider_selected(args)


def _provider_key_onboarding(args: argparse.Namespace) -> dict[str, Any]:
    if not _deepseek_provider_selected(args):
        return _provider_key_onboarding_result()
    if os.getenv(DEEPSEEK_API_KEY_ENV):
        return _provider_key_onboarding_result(
            metadata={
                "provider_key_source": "environment",
                "provider_key_store_used": False,
                "provider_key_persistent_save": False,
            },
        )
    if getattr(args, "use_stored_provider_key", False):
        stored_result = _load_stored_provider_key()
        if stored_result["provider_key"]:
            return stored_result
        if getattr(args, "prompt_provider_key", False) is not True:
            return stored_result
    if getattr(args, "prompt_provider_key", False) is not True:
        return _provider_key_onboarding_result(
            blocking_reasons=(DEEPSEEK_PROVIDER_KEY_REQUIRED,),
        )
    if args.format == "json" or args.json:
        return _provider_key_onboarding_result(
            blocking_reasons=(PROVIDER_KEY_PROMPT_UNAVAILABLE_FOR_JSON_OUTPUT,),
        )
    if not _provider_key_prompt_available():
        return _provider_key_onboarding_result(
            blocking_reasons=(PROVIDER_KEY_PROMPT_REQUIRES_INTERACTIVE_TERMINAL,),
        )
    provider_key = _read_provider_key_secret()
    if provider_key is None:
        return _provider_key_onboarding_result(
            blocking_reasons=(PROVIDER_KEY_PROMPT_CANCELLED,),
        )
    provider_key = provider_key.strip()
    if not provider_key:
        return _provider_key_onboarding_result(
            blocking_reasons=(PROVIDER_KEY_INPUT_REQUIRED,),
        )
    choice = _read_provider_key_persistence_choice()
    if choice == "once":
        return _provider_key_onboarding_result(
            provider_key=provider_key,
            metadata={
                "provider_key_source": "prompt_once",
                "provider_key_supplied_by_prompt": True,
                "provider_key_store_used": False,
                "provider_key_persistent_save": False,
            },
        )
    if choice == "store":
        stored_result = _save_provider_key(provider_key)
        if stored_result["blocking_reasons"]:
            return stored_result
        return _provider_key_onboarding_result(
            provider_key=provider_key,
            metadata={
                **stored_result["metadata"],
                "provider_key_source": "prompt_store",
                "provider_key_supplied_by_prompt": True,
                "provider_key_store_used": False,
                "provider_key_persistent_save": True,
            },
        )
    return _provider_key_onboarding_result(
        blocking_reasons=(PROVIDER_KEY_PROMPT_CANCELLED,),
    )


def _provider_key_onboarding_result(
    *,
    provider_key: str | None = None,
    blocking_reasons: tuple[str, ...] = (),
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "provider_key": provider_key,
        "blocking_reasons": tuple(blocking_reasons),
        "metadata": dict(metadata or {}),
    }


def _load_stored_provider_key() -> dict[str, Any]:
    try:
        store = _deepseek_credential_store()
        load_result = store.load_api_key()
    except Exception:
        return _provider_key_onboarding_result(
            blocking_reasons=(PROVIDER_KEY_STORED_CREDENTIAL_LOAD_FAILED,),
            metadata={"provider_key_store_backend": "unknown"},
        )
    metadata = {"provider_key_store_backend": str(load_result.backend)}
    if load_result.status == "success" and load_result.secret_value:
        return _provider_key_onboarding_result(
            provider_key=load_result.secret_value,
            metadata={
                **metadata,
                "provider_key_source": "stored_keychain",
                "provider_key_loaded_from_store": True,
                "provider_key_store_used": True,
                "provider_key_persistent_save": True,
            },
        )
    blocking_reason = load_result.blocking_reason or (
        PROVIDER_KEY_STORED_CREDENTIAL_NOT_FOUND
    )
    return _provider_key_onboarding_result(
        blocking_reasons=(str(blocking_reason),),
        metadata=metadata,
    )


def _save_provider_key(provider_key: str) -> dict[str, Any]:
    try:
        store = _deepseek_credential_store()
        save_result = store.save_api_key(provider_key)
    except Exception:
        return _provider_key_onboarding_result(
            blocking_reasons=(PROVIDER_KEY_PERSISTENT_SAVE_FAILED,),
            metadata={"provider_key_store_backend": "unknown"},
        )
    metadata = {"provider_key_store_backend": str(save_result.backend)}
    if save_result.status == "success":
        return _provider_key_onboarding_result(metadata=metadata)
    blocking_reason = save_result.blocking_reason or PROVIDER_KEY_PERSISTENT_SAVE_FAILED
    return _provider_key_onboarding_result(
        blocking_reasons=(str(blocking_reason),),
        metadata=metadata,
    )


def _deepseek_credential_store() -> Any:
    from cognition_cli.credentials.deepseek_keychain import (
        build_default_deepseek_credential_store,
    )

    return build_default_deepseek_credential_store()


def _deepseek_provider_selected(args: argparse.Namespace) -> bool:
    return _route_backend_provider(args, _model_name(args)) == "deepseek"


def _provider_key_prompt_available() -> bool:
    if os.getenv("CI"):
        return False
    return sys.stdin.isatty() and sys.stderr.isatty()


def _read_provider_key_secret() -> str | None:
    try:
        return getpass.getpass("请输入 DeepSeek API key: ", stream=sys.stderr)
    except (EOFError, KeyboardInterrupt):
        return None


def _read_provider_key_persistence_choice() -> str:
    print(
        "请选择 DeepSeek key 使用方式：1) 仅本次使用  2) 长期保存  3) 取消",
        file=sys.stderr,
    )
    print("请输入 1、2 或 3：", end="", file=sys.stderr, flush=True)
    try:
        raw_choice = sys.stdin.readline()
    except KeyboardInterrupt:
        return "cancel"
    normalized = _normalize_guided_choice_input(
        raw_choice,
        labels=("key", "key mode", "provider key", "deepseek key", "方式", "key 方式"),
    )
    if normalized in {"1", "once", "one-time", "本次", "仅本次", "仅本次使用"}:
        return "once"
    if normalized in {"2", "store", "save", "persist", "长期", "长期保存"}:
        return "store"
    return "cancel"


@contextmanager
def _temporary_provider_key_env(provider_key: str | None) -> Any:
    if not provider_key:
        yield
        return
    sentinel = object()
    previous = os.environ.get(DEEPSEEK_API_KEY_ENV, sentinel)
    os.environ[DEEPSEEK_API_KEY_ENV] = provider_key
    try:
        yield
    finally:
        if previous is sentinel:
            os.environ.pop(DEEPSEEK_API_KEY_ENV, None)
        else:
            os.environ[DEEPSEEK_API_KEY_ENV] = str(previous)


def _resolve_llm_service(
    args: argparse.Namespace,
    factory: ExternalReadonlyAskLlmInvocationServiceFactory,
    *,
    request_id: str,
    provider_key: str | None,
    provider_key_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        with _temporary_provider_key_env(provider_key):
            resolution = factory.resolve(
                config_context=None,
                config_selection=RuntimeConfigSelectionContext(
                    config_root=str(args.config_root) if args.config_root else None,
                    environment=args.environment,
                    profile=args.profile,
                    selection_source=EXTERNAL_READONLY_ASK_SOURCE,
                    metadata={
                        "request_id": request_id,
                        "surface": EXTERNAL_READONLY_ASK_COMMAND,
                        "product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH,
                    },
                ),
                live_llm_options=RuntimeLiveLlmInvocationOptionsContext(
                    ollama_api_base=args.ollama_api_base,
                    timeout_seconds=args.live_llm_timeout_seconds,
                    max_tokens=args.live_llm_max_tokens,
                    response_preview_limit=args.answer_preview_limit,
                    provider_profile_ref=getattr(
                        args,
                        "llm_provider_profile_ref",
                        None,
                    ),
                    model_profile_ref=getattr(args, "llm_model_profile_ref", None),
                    output_governance_profile_ref=getattr(
                        args,
                        "llm_output_governance_profile_ref",
                        None,
                    ),
                    network_gate_open=bool(getattr(args, "network_gate_open", False)),
                    operator_approved=bool(getattr(args, "operator_approved", False)),
                    approval_ref=args.live_llm_approval_ref,
                    audit_ref=getattr(args, "audit_ref", None),
                    selection_source=EXTERNAL_READONLY_ASK_SOURCE,
                    metadata={
                        "request_id": request_id,
                        "surface": EXTERNAL_READONLY_ASK_COMMAND,
                        "model_name": _model_name(args),
                        "provider_profile_ref": getattr(
                            args,
                            "llm_provider_profile_ref",
                            None,
                        ),
                        "model_profile_ref": getattr(
                            args,
                            "llm_model_profile_ref",
                            None,
                        ),
                        "output_governance_profile_ref": getattr(
                            args,
                            "llm_output_governance_profile_ref",
                            None,
                        ),
                        "provider_key_supplied_by_prompt": False,
                        "provider_key_persistent_save": False,
                        **dict(provider_key_metadata),
                        "product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH,
                    },
                ),
            )
    except Exception:
        return {
            "service": None,
            "blocking_reasons": (EXTERNAL_READONLY_ASK_PROVIDER_RESOLUTION_FAILED,),
            "warnings": ("external_readonly_ask_llm_provider_exception",),
        }
    blocking_reasons = tuple(str(item) for item in resolution.blocking_reasons)
    service = resolution.service
    if blocking_reasons or service is None:
        return {
            "service": None,
            "blocking_reasons": blocking_reasons
            or (EXTERNAL_READONLY_ASK_PROVIDER_RESOLUTION_FAILED,),
            "warnings": tuple(str(item) for item in resolution.warnings),
        }
    return {
        "service": service,
        "blocking_reasons": (),
        "warnings": tuple(str(item) for item in resolution.warnings),
    }


def _fetch_gateway_input_from_args(
    args: argparse.Namespace,
    *,
    request_id: str,
    source_url: str,
) -> dict[str, Any]:
    operator_approval_satisfied = bool(
        args.operator_approved
        and args.approval_ref
        and args.runtime_fetch_approval_ref
    )
    controlled_output_satisfied = bool(
        args.controlled_output_ref and args.audit_ref and args.sanitized_evidence_ref
    )
    gate_passed = bool(
        args.network_gate_open
        and operator_approval_satisfied
        and controlled_output_satisfied
    )
    return {
        "request_id": request_id,
        "source_url": source_url,
        "envelope_ref": args.envelope_ref,
        "evidence_ref": args.evidence_ref,
        "network_gate": {
            "request_ref": request_id,
            "status": "passed" if gate_passed else "blocked",
            "network_gate_open": args.network_gate_open,
            "allowed_for_network_request": args.network_gate_open,
            "operator_approval_satisfied": operator_approval_satisfied,
            "controlled_output_satisfied": controlled_output_satisfied,
            "tool_origin": "url_context",
            "operation_family": "fetch",
            "external_network_call_performed": False,
            "tool_execution_performed": False,
            "metadata": {
                "source": EXTERNAL_READONLY_ASK_SOURCE,
                "network_gate_ref_present": args.network_gate_open,
                "approval_ref_present": bool(args.approval_ref),
                "audit_ref_present": bool(args.audit_ref),
                "sanitized_evidence_ref_present": bool(args.sanitized_evidence_ref),
            },
        },
        "source_title": args.source_title,
        "controlled_output_ref": args.controlled_output_ref,
        "operator_approved": args.operator_approved,
        "approval_ref": args.approval_ref,
        "audit_ref": args.audit_ref,
        "sanitized_evidence_ref": args.sanitized_evidence_ref,
        "governance_summary_ref": args.governance_summary_ref,
        "allow_runtime_fetch": args.allow_runtime_fetch,
        "runtime_fetch_approval_ref": args.runtime_fetch_approval_ref,
        "use_live_transport": args.use_live_transport,
        "max_bytes": args.max_bytes,
        "max_excerpt_chars": args.max_excerpt_chars,
        "timeout_seconds": args.timeout_seconds,
        "redirect_limit": args.redirect_limit,
        "metadata": {
            "source": EXTERNAL_READONLY_ASK_SOURCE,
            "cli_command": EXTERNAL_READONLY_ASK_COMMAND,
            "product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH,
            "raw_response_included": False,
            "response_headers_included": False,
            "uploads_content": False,
            "writes_files": False,
        },
    }


def _archived_governed_summary_facts(
    evidence_paths: tuple[str, ...],
    *,
    repo_root: Path,
) -> tuple[list[Mapping[str, Any]], tuple[str, ...]]:
    payloads: list[Mapping[str, Any]] = []
    blocking_reasons: list[str] = []
    for evidence_path in evidence_paths:
        issue = validate_external_readonly_evidence_path(
            evidence_path=evidence_path,
            repo_root=repo_root,
        )
        if issue:
            blocking_reasons.append(f"{evidence_path}:{issue}")
            continue
        target = (repo_root / evidence_path).resolve()
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            blocking_reasons.append(
                f"{evidence_path}:external_readonly_evidence_archive_unreadable"
            )
            continue
        if not isinstance(payload, Mapping):
            blocking_reasons.append(
                f"{evidence_path}:external_readonly_evidence_archive_not_object"
            )
            continue

        facts = _mapping(payload.get("governed_summary_facts"))
        if facts:
            payloads.append(facts)
            continue
        payloads.append(
            _blocked_governed_summary_facts_payload(
                payload,
                evidence_path=evidence_path,
                reason="external_readonly_governed_summary_facts_required",
            )
        )
    return payloads, tuple(blocking_reasons)


def _blocked_governed_summary_facts_payload(
    archive_payload: Mapping[str, Any],
    *,
    evidence_path: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "payload_type": "external_readonly_governed_summary_facts",
        "payload_version": "external_readonly_governed_summary_facts_v1",
        "status": "blocked",
        "evidence_ref": _archive_evidence_ref(archive_payload, evidence_path),
        "evidence_output_path": evidence_path,
        "reference_review_ready": False,
        "allowed_for_model_context": False,
        "evidence_written": archive_payload.get("evidence_written") is True,
        "facts": [],
        "fact_count": 0,
        "total_fact_chars": 0,
        "blocking_reasons": [reason],
        "warnings": [],
        "metadata": {
            "source": EXTERNAL_READONLY_ASK_SOURCE,
            "archive_bridge": True,
            "product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH,
        },
    }


def _archive_evidence_ref(
    archive_payload: Mapping[str, Any],
    evidence_path: str,
) -> str:
    value = archive_payload.get("evidence_ref")
    if isinstance(value, str) and value.startswith("evidence://external-readonly/"):
        return value
    try:
        relative = Path(evidence_path).relative_to("outputs/external-readonly")
    except ValueError:
        return "evidence://external-readonly/governed-summary-facts/unavailable"
    return f"evidence://external-readonly/{relative.as_posix()}"


def _route_facts(args: argparse.Namespace) -> ModelRouteFacts:
    model_name = _model_name(args)
    backend_provider = _route_backend_provider(args, model_name)
    return ModelRouteFacts(
        model_name=model_name,
        provider="litellm",
        source=EXTERNAL_READONLY_ASK_SOURCE,
        metadata={
            "backend_provider": backend_provider,
            "route_kind": _route_kind(backend_provider),
            "route_target": model_name,
            "route_fact_contract": "schemas.model_routing.ModelRouteFacts",
            "provider_profile_ref": getattr(args, "llm_provider_profile_ref", None),
            "model_profile_ref": getattr(args, "llm_model_profile_ref", None),
            "output_governance_profile_ref": getattr(
                args,
                "llm_output_governance_profile_ref",
                None,
            ),
            "product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH,
        },
    )


def _governance_precondition(args: argparse.Namespace) -> LlmGovernancePrecondition:
    return LlmGovernancePrecondition(
        allowed=True,
        reason="external_readonly_ask_explicit_controlled_product_generation",
        decision="allow",
        governance_decision_ref=args.live_llm_approval_ref,
        metadata={
            "surface": EXTERNAL_READONLY_ASK_COMMAND,
            "product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH,
        },
    )


def _output_from_answer_result(
    request_id: str,
    *,
    evidence_paths: tuple[str, ...],
    source_url: str | None,
    question: str,
    answer_result: Mapping[str, Any],
    llm_request: LlmInvocationRequest | None,
    evidence_bridge: Mapping[str, Any],
    resolution_warnings: tuple[str, ...],
    follow_up_seed: Any | None = None,
    follow_up_turn_index: int | None = None,
    source_follow_up_seed_ref: str | None = None,
) -> dict[str, Any]:
    context = evidence_bridge["context"]
    product_summary_refs = _product_refs(answer_result, context)
    status = str(answer_result.get("status") or "failed")
    answer = answer_result.get("answer")
    answer_text = answer if isinstance(answer, str) and answer else None
    answer_preview = answer_result.get("answer_preview")
    answer_preview_text = (
        answer_preview if isinstance(answer_preview, str) and answer_preview else None
    )
    warnings = [
        *tuple(str(item) for item in evidence_bridge.get("warnings") or ()),
        *_string_tuple(answer_result.get("warnings")),
        *resolution_warnings,
    ]
    follow_up_seed_payload = (
        evidence_summary_answer_follow_up_seed_status_dict(follow_up_seed)
        if follow_up_seed is not None
        else None
    )
    trace_seed_ref = source_follow_up_seed_ref or _optional_string(
        _mapping(follow_up_seed_payload).get("seed_ref")
    )
    answer_trace_model = build_evidence_summary_answer_trace(
        context,
        answer_result,
        readonly_refs_status=str(evidence_bridge.get("readonly_refs_status") or status),
        evidence_refs=product_summary_refs["evidence_refs"],
        additional_refs=product_summary_refs["additional_refs"],
        follow_up=follow_up_turn_index is not None,
        follow_up_turn_index=follow_up_turn_index,
        follow_up_seed_ref=trace_seed_ref,
        metadata={
            "product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH,
            **_llm_request_trace_metadata(llm_request),
        },
    )
    answer_trace = evidence_summary_answer_trace_status_dict(answer_trace_model)
    answer_trace_summary = evidence_summary_answer_trace_summary_dict(answer_trace_model)
    answer_artifact_model = build_evidence_summary_answer_artifact(
        context,
        answer_result,
        answer_trace_model,
        metadata={"product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH},
    )
    answer_artifact = evidence_summary_answer_artifact_status_dict(
        answer_artifact_model
    )
    answer_artifact_summary = evidence_summary_answer_artifact_summary_dict(
        answer_artifact_model
    )
    product_response_summary = _product_response_summary(
        request_id=request_id,
        answer_status=status,
        evidence_refs=product_summary_refs["evidence_refs"],
        additional_refs=product_summary_refs["additional_refs"],
        blocking_reasons=_string_tuple(answer_result.get("blocking_reasons")),
        warnings=tuple(warnings),
        readonly_refs_status=str(evidence_bridge.get("readonly_refs_status") or status),
        source_url_present=bool(source_url),
        evidence_path_count=len(evidence_paths),
        model_name=_answer_result_model_name(answer_result, llm_request),
        llm_call_allowed=answer_result.get("llm_call_allowed") is True,
        llm_call_attempted=answer_result.get("llm_call_attempted") is True,
        llm_runtime_call_performed=(
            answer_result.get("llm_runtime_call_performed") is True
        ),
        external_readonly_fetch_performed=bool(
            evidence_bridge.get("external_readonly_fetch_performed", False)
        ),
        external_readonly_network_call_performed=bool(
            evidence_bridge.get("external_readonly_network_call_performed", False)
        ),
        external_network_call_performed=bool(
            evidence_bridge.get("external_network_call_performed", False)
        ),
        follow_up=follow_up_turn_index is not None,
        follow_up_turn_index=follow_up_turn_index,
        follow_up_seed_ref=source_follow_up_seed_ref,
        answer_trace_ref=answer_trace["trace_ref"],
        answer_trace_status=answer_trace["answer_status"],
        answer_trace_summary=answer_trace_summary,
        answer_artifact_ref=answer_artifact["artifact_ref"],
        answer_artifact_status=answer_artifact["artifact_status"],
        answer_artifact_summary=answer_artifact_summary,
    )
    blocking_reasons = _string_tuple(answer_result.get("blocking_reasons"))
    citation_failures = _string_tuple(answer_result.get("citation_failures"))
    evidence_refs = _public_ref_details(product_summary_refs["evidence_refs"])
    additional_refs = _public_ref_details(product_summary_refs["additional_refs"])
    failure_explanation = _failure_explanation(
        status=status,
        blocking_reasons=blocking_reasons,
        citation_failures=citation_failures,
    )
    recovery_hints = _recovery_hints(
        status=status,
        blocking_reasons=blocking_reasons,
        citation_failures=citation_failures,
    )
    return {
        "product": PRODUCT_NAME,
        "command": EXTERNAL_READONLY_ASK_COMMAND,
        "interaction_mode": (
            EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_INTERACTION_MODE
            if follow_up_turn_index is not None
            else EXTERNAL_READONLY_ASK_INTERACTION_MODE
        ),
        "product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH,
        "status": status,
        "success": status == "success",
        "failure_type": None if status == "success" else EXTERNAL_READONLY_ASK_FAILURE,
        "request_id": request_id,
        "fetch_request_id": evidence_bridge.get("fetch_request_id"),
        "llm_request_id": llm_request.request_id if llm_request is not None else None,
        "model_name": _answer_result_model_name(answer_result, llm_request),
        "source_url_present": bool(source_url),
        "source_url": source_url,
        "evidence_path_count": len(evidence_paths),
        "evidence_ref_count": len(product_summary_refs["evidence_refs"]),
        "additional_ref_count": len(product_summary_refs["additional_refs"]),
        "evidence_refs": evidence_refs,
        "additional_refs": additional_refs,
        "readonly_refs_status": evidence_bridge.get("readonly_refs_status"),
        "answer_trace_ref": answer_trace["trace_ref"],
        "answer_trace_status": answer_trace["answer_status"],
        "answer_trace_summary": answer_trace_summary,
        "answer_artifact_ref": answer_artifact["artifact_ref"],
        "answer_artifact_status": answer_artifact["artifact_status"],
        "answer_artifact_summary": answer_artifact_summary,
        "evidence_summary_answer_trace": answer_trace,
        "evidence_summary_answer_artifact": answer_artifact,
        "product_response_summary": product_response_summary,
        "question_preview": _preview(question, limit=120),
        "answer": answer_text,
        "answer_preview": answer_preview_text,
        "answer_length": len(answer_text) if answer_text else None,
        "evidence_summary_answer_result": dict(answer_result),
        "llm_call_allowed": answer_result.get("llm_call_allowed") is True,
        "llm_call_attempted": answer_result.get("llm_call_attempted") is True,
        "llm_runtime_call_performed": (
            answer_result.get("llm_runtime_call_performed") is True
        ),
        "external_readonly_fetch_performed": bool(
            evidence_bridge.get("external_readonly_fetch_performed", False)
        ),
        "external_readonly_network_call_performed": bool(
            evidence_bridge.get("external_readonly_network_call_performed", False)
        ),
        "external_network_call_performed": bool(
            evidence_bridge.get("external_network_call_performed", False)
        ),
        "raw_response_included": False,
        "raw_html_included": False,
        "response_headers_included": False,
        "uploads_content": False,
        "writes_files": False,
        "failure_explanation": failure_explanation,
        "recovery_hints": recovery_hints,
        "blocking_reasons": blocking_reasons,
        "citation_failures": citation_failures,
        "warnings": warnings,
        "exit_code": _exit_code_from_status(status),
        "follow_up": follow_up_turn_index is not None,
        "follow_up_turn_index": follow_up_turn_index,
        "follow_up_seed_ref": source_follow_up_seed_ref,
        "follow_up_available": bool(
            follow_up_seed_payload
            and follow_up_seed_payload.get("follow_up_allowed") is True
        ),
        "follow_up_seed": follow_up_seed_payload,
        "temporary_follow_up": True,
        "durable_session": False,
        "memory_enabled": False,
    }


def _output_with_follow_up_turns(
    initial_output: dict[str, Any],
    *,
    follow_up_questions: tuple[str, ...],
    source_url: str | None,
    evidence_paths: tuple[str, ...],
    evidence_bridge: Mapping[str, Any],
    service: Any,
    args: argparse.Namespace,
    request_id: str,
    source_seed: Any | None,
    guided_follow_up: bool = False,
) -> dict[str, Any]:
    turns = [_turn_summary(initial_output, turn_index=1)]
    if initial_output.get("status") != "success" or source_seed is None:
        initial_output["turn_count"] = len(turns)
        initial_output["turns"] = turns
        initial_output["follow_up_requested"] = bool(follow_up_questions)
        initial_output["follow_up_blocking_reasons"] = (
            ["source_turn_not_success_or_seed_missing"]
            if follow_up_questions
            else []
        )
        return initial_output

    current_seed = source_seed
    final_output = initial_output
    planned_questions = list(follow_up_questions)
    follow_up_index = 0
    guided_prompted = False
    follow_up_declined = False
    follow_up_cancelled = False
    while planned_questions or guided_follow_up:
        if planned_questions:
            follow_up_question = planned_questions.pop(0)
        else:
            guided_prompted = True
            _print_guided_follow_up_turn_preview(final_output)
            try:
                decision, inline_question = _read_guided_follow_up_decision()
            except (EOFError, KeyboardInterrupt):
                follow_up_cancelled = True
                break
            if decision == "cancel":
                follow_up_cancelled = True
                break
            if decision == "decline":
                follow_up_declined = True
                break
            raw_question = inline_question
            if raw_question is None:
                try:
                    raw_question = _read_guided_follow_up_question()
                except (EOFError, KeyboardInterrupt):
                    follow_up_cancelled = True
                    break
                if raw_question is None:
                    follow_up_cancelled = True
                    break
            follow_up_question = _normalize_guided_question_input(raw_question)
            if not follow_up_question:
                warnings = list(final_output.get("warnings") or [])
                warnings.append(
                    EXTERNAL_READONLY_ASK_GUIDED_FOLLOW_UP_QUESTION_REQUIRED
                )
                final_output["warnings"] = warnings
                final_output["follow_up_blocking_reasons"] = [
                    EXTERNAL_READONLY_ASK_GUIDED_FOLLOW_UP_QUESTION_REQUIRED
                ]
                break
        follow_up_index += 1
        final_output, current_seed = _run_follow_up_turn(
            follow_up_question,
            follow_up_index=follow_up_index,
            source_url=source_url,
            evidence_paths=evidence_paths,
            evidence_bridge=evidence_bridge,
            service=service,
            args=args,
            request_id=request_id,
            seed=current_seed,
        )
        turns.append(_turn_summary(final_output, turn_index=follow_up_index + 1))
        if final_output.get("status") != "success" or current_seed is None:
            break

    final_output["initial_request_id"] = initial_output.get("request_id")
    final_output["turn_count"] = len(turns)
    final_output["turns"] = turns
    final_output["follow_up_requested"] = (
        bool(follow_up_questions)
        or follow_up_index > 0
        or (guided_prompted and not follow_up_declined)
    )
    final_output["guided_follow_up_prompted"] = guided_prompted
    final_output["follow_up_declined"] = follow_up_declined
    final_output["follow_up_cancelled"] = follow_up_cancelled
    final_output.setdefault("follow_up_blocking_reasons", [])
    return final_output


def _print_guided_follow_up_turn_preview(output: Mapping[str, Any]) -> None:
    answer = _optional_string(output.get("answer")) or _optional_string(
        output.get("answer_preview")
    )
    if answer:
        print("", file=sys.stderr)
        print("本轮答案:", file=sys.stderr)
        print(answer, file=sys.stderr)
    print(
        "提示：追问仅在当前进程内围绕同一受治理证据继续；"
        "不启用长期 Memory 或持久会话。",
        file=sys.stderr,
    )


def _run_follow_up_turn(
    follow_up_question: str,
    *,
    follow_up_index: int,
    source_url: str | None,
    evidence_paths: tuple[str, ...],
    evidence_bridge: Mapping[str, Any],
    service: Any,
    args: argparse.Namespace,
    request_id: str,
    seed: Any,
) -> tuple[dict[str, Any], Any | None]:
    context = build_evidence_summary_answer_follow_up_context(
        seed,
        request_id=f"{request_id}/follow-up-{follow_up_index}/context",
        follow_up_question=follow_up_question,
        digests=evidence_bridge["context"].digests,
        metadata={"product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH},
    )
    generation_policy_facts = _generation_policy_facts(context)
    preflight_result_model = build_evidence_summary_answer_answerability_preflight_result(
        context,
        metadata={
            "source": EXTERNAL_READONLY_ASK_SOURCE,
            "product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH,
        },
    )
    if preflight_result_model is not None:
        answer_result = evidence_summary_answer_result_status_dict(preflight_result_model)
        next_seed = build_evidence_summary_answer_follow_up_seed(
            preflight_result_model,
            metadata={"product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH},
        )
        follow_up_bridge = dict(evidence_bridge)
        follow_up_bridge["context"] = context
        output = _output_from_answer_result(
            f"{request_id}/follow-up-{follow_up_index}",
            evidence_paths=evidence_paths,
            source_url=source_url,
            question=follow_up_question,
            answer_result=answer_result,
            llm_request=None,
            evidence_bridge=follow_up_bridge,
            resolution_warnings=(),
            follow_up_seed=next_seed,
            follow_up_turn_index=follow_up_index,
            source_follow_up_seed_ref=seed.seed_ref,
        )
        return output, next_seed

    llm_request = build_evidence_summary_answer_llm_invocation_request(
        context,
        route_facts=_route_facts(args),
        governance_precondition=_governance_precondition(args),
        request_id=f"{request_id}/follow-up-{follow_up_index}/llm",
        generation_policy_facts=generation_policy_facts,
        metadata={"product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH},
    )
    llm_result = service.invoke(llm_request)
    answer_result_model = build_evidence_summary_answer_result_from_llm_invocation_result(
        context,
        llm_result,
        generation_policy_facts=generation_policy_facts,
        metadata={"product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH},
    )
    answer_result = evidence_summary_answer_result_status_dict(answer_result_model)
    next_seed = (
        build_evidence_summary_answer_follow_up_seed(
            answer_result_model,
            metadata={"product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH},
        )
        if answer_result_model.status == "success"
        else None
    )
    follow_up_bridge = dict(evidence_bridge)
    follow_up_bridge["context"] = context
    output = _output_from_answer_result(
        f"{request_id}/follow-up-{follow_up_index}",
        evidence_paths=evidence_paths,
        source_url=source_url,
        question=follow_up_question,
        answer_result=answer_result,
        llm_request=llm_request,
        evidence_bridge=follow_up_bridge,
        resolution_warnings=(),
        follow_up_seed=next_seed,
        follow_up_turn_index=follow_up_index,
        source_follow_up_seed_ref=seed.seed_ref,
    )
    return output, next_seed


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


def _llm_request_trace_metadata(
    llm_request: LlmInvocationRequest | None,
) -> dict[str, str]:
    if llm_request is None:
        return {}
    route_facts = getattr(llm_request, "route_facts", None)
    metadata = _mapping(getattr(route_facts, "metadata", None))
    profile_refs = {
        "provider_profile_ref": metadata.get("provider_profile_ref"),
        "model_profile_ref": metadata.get("model_profile_ref"),
        "output_governance_profile_ref": metadata.get(
            "output_governance_profile_ref"
        ),
        "llm_route_provider": getattr(route_facts, "provider", None),
        "llm_route_model": getattr(route_facts, "model_name", None),
    }
    return {
        key: value
        for key, value in profile_refs.items()
        if isinstance(value, str) and value
    }


def _blocked_output(
    request_id: str,
    *,
    evidence_paths: tuple[str, ...],
    source_url: str | None,
    question: str,
    blocking_reasons: tuple[str, ...],
    warnings: tuple[str, ...],
    product_response_summary: Mapping[str, Any],
    fetch_request_id: str | None,
) -> dict[str, Any]:
    evidence_refs = _allowed_refs(product_response_summary.get("evidence_refs"))
    additional_refs = _allowed_refs(product_response_summary.get("additional_refs"))
    public_evidence_refs = _public_ref_details(evidence_refs)
    public_additional_refs = _public_ref_details(additional_refs)
    answer_trace_ref = _optional_string(product_response_summary.get("answer_trace_ref"))
    answer_trace_status = _optional_string(
        product_response_summary.get("answer_trace_status")
    )
    answer_trace_summary = _mapping(product_response_summary.get("answer_trace_summary"))
    answer_artifact_ref = _optional_string(
        product_response_summary.get("answer_artifact_ref")
    )
    answer_artifact_status = _optional_string(
        product_response_summary.get("answer_artifact_status")
    )
    answer_artifact_summary = _mapping(
        product_response_summary.get("answer_artifact_summary")
    )
    citation_failures: tuple[str, ...] = ()
    failure_explanation = _failure_explanation(
        status="blocked",
        blocking_reasons=blocking_reasons,
        citation_failures=citation_failures,
    )
    recovery_hints = _recovery_hints(
        status="blocked",
        blocking_reasons=blocking_reasons,
        citation_failures=citation_failures,
    )
    return {
        "product": PRODUCT_NAME,
        "command": EXTERNAL_READONLY_ASK_COMMAND,
        "interaction_mode": EXTERNAL_READONLY_ASK_INTERACTION_MODE,
        "product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH,
        "status": "blocked",
        "success": False,
        "failure_type": EXTERNAL_READONLY_ASK_FAILURE,
        "request_id": request_id,
        "fetch_request_id": fetch_request_id,
        "llm_request_id": None,
        "model_name": None,
        "source_url_present": bool(source_url),
        "source_url": source_url,
        "evidence_path_count": len(evidence_paths),
        "evidence_ref_count": len(evidence_refs),
        "additional_ref_count": len(additional_refs),
        "evidence_refs": public_evidence_refs,
        "additional_refs": public_additional_refs,
        "readonly_refs_status": "blocked",
        "answer_trace_ref": answer_trace_ref,
        "answer_trace_status": answer_trace_status,
        "answer_trace_summary": dict(answer_trace_summary),
        "answer_trace_unavailable_reason": (
            None if answer_trace_ref else "answer_trace_requires_answer_context"
        ),
        "answer_artifact_ref": answer_artifact_ref,
        "answer_artifact_status": answer_artifact_status,
        "answer_artifact_summary": dict(answer_artifact_summary),
        "answer_artifact_unavailable_reason": (
            None if answer_artifact_ref else "answer_artifact_requires_answer_context"
        ),
        "product_response_summary": dict(product_response_summary),
        "question_preview": _preview(question, limit=120) if question else None,
        "answer": None,
        "answer_preview": None,
        "answer_length": None,
        "llm_call_allowed": False,
        "llm_call_attempted": False,
        "llm_runtime_call_performed": False,
        "external_readonly_fetch_performed": bool(
            product_response_summary.get("metadata", {}).get(
                "external_readonly_fetch_performed",
                False,
            )
        ),
        "external_readonly_network_call_performed": False,
        "external_network_call_performed": False,
        "raw_response_included": False,
        "raw_html_included": False,
        "response_headers_included": False,
        "uploads_content": False,
        "writes_files": False,
        "failure_explanation": failure_explanation,
        "recovery_hints": recovery_hints,
        "blocking_reasons": list(blocking_reasons),
        "citation_failures": list(citation_failures),
        "warnings": list(warnings),
        "exit_code": EXIT_BLOCKING,
    }


def _product_refs(
    answer_result: Mapping[str, Any],
    context: Any,
) -> dict[str, tuple[Mapping[str, Any], ...]]:
    evidence_refs = tuple(_allowed_refs(answer_result.get("evidence_refs_used")))
    additional_refs = tuple(_allowed_refs(answer_result.get("additional_refs_used")))
    if not evidence_refs:
        evidence_refs = tuple(ref.model_dump(mode="python") for ref in context.evidence_refs)
    if not additional_refs:
        additional_refs = tuple(
            ref.model_dump(mode="python") for ref in context.additional_refs
        )
    return {"evidence_refs": evidence_refs, "additional_refs": additional_refs}


def _answer_result_model_name(
    answer_result: Mapping[str, Any],
    llm_request: LlmInvocationRequest | None,
) -> str | None:
    metadata = _mapping(answer_result.get("metadata"))
    routed_model = metadata.get("llm_route_model")
    if isinstance(routed_model, str) and routed_model:
        return routed_model
    return llm_request.route_facts.model_name if llm_request is not None else None


def _product_response_summary(
    *,
    request_id: str,
    answer_status: str,
    evidence_refs: tuple[Mapping[str, Any], ...],
    additional_refs: tuple[Mapping[str, Any], ...],
    blocking_reasons: tuple[str, ...],
    warnings: tuple[str, ...],
    readonly_refs_status: str,
    source_url_present: bool,
    evidence_path_count: int,
    model_name: str | None,
    llm_call_allowed: bool,
    llm_call_attempted: bool,
    llm_runtime_call_performed: bool,
    external_readonly_fetch_performed: bool,
    external_readonly_network_call_performed: bool,
    external_network_call_performed: bool,
    follow_up: bool = False,
    follow_up_turn_index: int | None = None,
    follow_up_seed_ref: str | None = None,
    answer_trace_ref: str | None = None,
    answer_trace_status: str | None = None,
    answer_trace_summary: Mapping[str, Any] | None = None,
    answer_artifact_ref: str | None = None,
    answer_artifact_status: str | None = None,
    answer_artifact_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result = execute_external_readonly_ask_gateway_request(
        {
            "request_id": f"{request_id}/product",
            "answer_status": answer_status,
            "evidence_refs": [dict(ref) for ref in evidence_refs],
            "additional_refs": [dict(ref) for ref in additional_refs],
            "blocking_reasons": list(blocking_reasons),
            "warnings": list(warnings),
            "readonly_refs_status": readonly_refs_status,
            "source_url_present": source_url_present,
            "evidence_path_count": evidence_path_count,
            "model_name": model_name,
            "llm_call_allowed": llm_call_allowed,
            "llm_call_attempted": llm_call_attempted,
            "llm_runtime_call_performed": llm_runtime_call_performed,
            "external_readonly_fetch_performed": external_readonly_fetch_performed,
            "external_readonly_network_call_performed": (
                external_readonly_network_call_performed
            ),
            "external_network_call_performed": external_network_call_performed,
            "follow_up": follow_up,
            "follow_up_turn_index": follow_up_turn_index,
            "follow_up_seed_ref": follow_up_seed_ref,
            "answer_trace_ref": answer_trace_ref,
            "answer_trace_status": answer_trace_status,
            "answer_trace_summary": dict(answer_trace_summary or {}),
            "answer_artifact_ref": answer_artifact_ref,
            "answer_artifact_status": answer_artifact_status,
            "answer_artifact_summary": dict(answer_artifact_summary or {}),
            "temporary_follow_up": True,
            "durable_session": False,
            "memory_enabled": False,
            "metadata": {
                "source": EXTERNAL_READONLY_ASK_SOURCE,
                "product_path": EXTERNAL_READONLY_ASK_PRODUCT_PATH,
            },
        }
    )
    return dict(result.product_response_summary)


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


def _preflight_blocking_reasons(
    args: argparse.Namespace,
    *,
    evidence_paths: tuple[str, ...],
    source_url: str | None,
    question: str,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not source_url and not evidence_paths:
        reasons.append("source_url_or_evidence_output_path_required")
    if source_url and evidence_paths:
        reasons.append("source_url_and_evidence_path_mutually_exclusive")
    if source_url and not _natural_language_confirmation_satisfied(args):
        reasons.append("external_readonly_natural_language_confirmation_required")
    if not question:
        reasons.append("question_required")
    if args.request_live_llm is not True:
        reasons.append("request_live_llm_required")
    external_provider_selected = _external_llm_provider_selected(args)
    if not external_provider_selected and args.request_ollama is not True:
        reasons.append("request_ollama_required")
    if args.allow_live_llm is not True:
        reasons.append("allow_live_llm_required")
    if not external_provider_selected and args.allow_ollama is not True:
        reasons.append("allow_ollama_required")
    if not args.live_llm_approval_ref:
        reasons.append("live_llm_approval_ref_required")
    if external_provider_selected:
        if not getattr(args, "llm_provider_profile_ref", None):
            reasons.append("llm_provider_profile_ref_required")
        if not getattr(args, "llm_model_profile_ref", None):
            reasons.append("llm_model_profile_ref_required")
        if not getattr(args, "llm_output_governance_profile_ref", None):
            reasons.append("llm_output_governance_profile_ref_required")
        if not _explicit_model_name(args):
            reasons.append("external_llm_model_name_required")
        if not getattr(args, "network_gate_open", False):
            reasons.append("external_llm_network_gate_open_required")
        if not getattr(args, "operator_approved", False):
            reasons.append("external_llm_operator_approved_required")
        if not getattr(args, "audit_ref", None):
            reasons.append("external_llm_audit_ref_required")
    if (
        args.live_llm_timeout_seconds is not None
        and args.live_llm_timeout_seconds <= 0
    ):
        reasons.append("live_llm_timeout_seconds_must_be_positive")
    if args.live_llm_max_tokens is not None and args.live_llm_max_tokens <= 0:
        reasons.append("live_llm_max_tokens_must_be_positive")
    if args.answer_preview_limit is not None and args.answer_preview_limit <= 0:
        reasons.append("answer_preview_limit_must_be_positive")
    if not _model_name(args):
        reasons.append("model_name_required")
    if (
        not external_provider_selected
        and args.ollama_api_base
        and not _local_ollama_api_base(args.ollama_api_base)
    ):
        reasons.append("ollama_api_base_must_be_local")
    return tuple(reasons)


def _emit_external_readonly_ask_output(
    args: argparse.Namespace,
    output: Mapping[str, Any],
    *,
    exit_code: int,
) -> int:
    if external_readonly_fetch_output_boundary_violated(output):
        print(
            f"{EXTERNAL_READONLY_ASK_COMMAND} output boundary violation",
            file=sys.stderr,
        )
        return EXIT_OUTPUT_BOUNDARY_FAILURE

    if args.format == "json" or args.json:
        print(json.dumps(dict(output), ensure_ascii=False, sort_keys=True))
    else:
        print(_text_output(output))
    return exit_code


def _text_output(output: Mapping[str, Any]) -> str:
    lines = [
        str(output["product"]),
        f"command: {output['command']}",
        f"status: {output['status']}",
        f"request_id: {output['request_id']}",
        f"answer_trace_ref: {output.get('answer_trace_ref') or 'unavailable'}",
        f"answer_artifact_ref: {output.get('answer_artifact_ref') or 'unavailable'}",
        f"evidence_ref_count: {output['evidence_ref_count']}",
        f"additional_ref_count: {output['additional_ref_count']}",
        f"readonly_refs_status: {output['readonly_refs_status']}",
        f"llm_call_attempted: {str(output['llm_call_attempted']).lower()}",
        f"llm_runtime_call_performed: {str(output['llm_runtime_call_performed']).lower()}",
    ]
    if output.get("turn_count"):
        lines.append(f"turn_count: {output['turn_count']}")
    if output.get("answer_trace_status"):
        lines.append(f"answer_trace_status: {output.get('answer_trace_status')}")
    if output.get("answer_trace_unavailable_reason"):
        lines.append(
            "answer_trace_unavailable_reason: "
            f"{output.get('answer_trace_unavailable_reason')}"
        )
    if output.get("answer_artifact_status"):
        lines.append(
            f"answer_artifact_status: {output.get('answer_artifact_status')}"
        )
    if output.get("answer_artifact_unavailable_reason"):
        lines.append(
            "answer_artifact_unavailable_reason: "
            f"{output.get('answer_artifact_unavailable_reason')}"
        )
    if output.get("follow_up"):
        lines.append(f"follow_up_turn_index: {output.get('follow_up_turn_index')}")
    if (
        output.get("follow_up_available")
        or output.get("follow_up")
        or output.get("turn_count")
        or output.get("guided_follow_up_prompted")
    ):
        lines.append(
            "follow_up_scope: temporary_only; "
            "durable_session=false; memory_enabled=false"
        )
    if output.get("guided_follow_up_prompted"):
        lines.append(
            "guided_follow_up_prompted: "
            f"{str(output.get('guided_follow_up_prompted')).lower()}"
        )
    if output.get("follow_up_declined"):
        lines.append("follow_up_declined: true")
    if output.get("follow_up_cancelled"):
        lines.append("follow_up_cancelled: true")
    if output.get("follow_up_available"):
        seed_ref = _mapping(output.get("follow_up_seed")).get("seed_ref")
        suffix = f" ({seed_ref})" if seed_ref else ""
        lines.append(f"follow_up_available: true{suffix}")
    blocking = output.get("blocking_reasons") or []
    warnings = output.get("warnings") or []
    if blocking:
        lines.append("blocking_reasons: " + ", ".join(map(str, blocking)))
    failure_explanation = output.get("failure_explanation")
    if failure_explanation:
        lines.append("failure_explanation: " + str(failure_explanation))
    recovery_hints = _list_value(output.get("recovery_hints"))
    if recovery_hints:
        lines.append("recovery_hints:")
        lines.extend(f"- {hint}" for hint in recovery_hints)
    evidence_refs = _list_value(output.get("evidence_refs"))
    if evidence_refs:
        lines.append("evidence_refs:")
        lines.extend(_text_ref_lines(evidence_refs))
    additional_refs = _list_value(output.get("additional_refs"))
    if additional_refs:
        lines.append("additional_refs:")
        lines.extend(_text_ref_lines(additional_refs))
    if warnings:
        lines.append("warnings: " + ", ".join(map(str, warnings)))
    answer = output.get("answer")
    if answer:
        lines.append("answer:")
        lines.append(str(answer))
    turns = _list_value(output.get("turns"))
    if turns:
        lines.append("turns:")
        for turn in turns:
            mapping = _mapping(turn)
            lines.append(
                "- "
                f"{mapping.get('turn_index')}: "
                f"{mapping.get('status')} "
                f"{mapping.get('question_preview')}"
            )
    return "\n".join(lines)


def _exit_code_from_output(output: Mapping[str, Any]) -> int:
    return _exit_code_from_status(output.get("status"))


def _exit_code_from_status(status: Any) -> int:
    if status == "success":
        return EXIT_OK
    if status in {"blocked", "insufficient_evidence"}:
        return EXIT_BLOCKING
    return EXIT_RUNTIME_FAILURE


def _natural_language_confirmation_satisfied(args: argparse.Namespace) -> bool:
    return (
        str(args.confirm_external_readonly_fetch or "").strip()
        == REQUIRED_EXTERNAL_READONLY_FETCH_CONFIRMATION
    )


def _model_name(args: argparse.Namespace) -> str:
    model_name = _explicit_model_name(args)
    if isinstance(model_name, str) and model_name.strip():
        return model_name.strip()
    return RuntimeLiveLlmConfigView().model_name


def _apply_model_alias(args: argparse.Namespace) -> tuple[str, ...]:
    alias = _model_alias(args)
    if alias is None:
        return ()
    if any(
        getattr(args, name, None)
        for name in EXTERNAL_READONLY_ASK_MODEL_ALIAS_EXPLICIT_OPTION_FIELDS
    ):
        return (EXTERNAL_READONLY_ASK_MODEL_ALIAS_CONFLICT,)
    runtime_view = RuntimeLiveLlmConfigView()
    alias_config = runtime_view.model_aliases.get(alias)
    if alias_config is None:
        return (f"{EXTERNAL_READONLY_ASK_MODEL_ALIAS_UNKNOWN}:{alias}",)
    model_profile = runtime_view.model_profiles[alias_config.model_profile_ref]
    args.model_name = alias_config.model_name or model_profile.model_name
    args.llm_provider_profile_ref = alias_config.provider_profile_ref
    args.llm_model_profile_ref = alias_config.model_profile_ref
    args.llm_output_governance_profile_ref = (
        alias_config.output_governance_profile_ref
    )
    return ()


def _explicit_model_name(args: argparse.Namespace) -> str | None:
    model_name = getattr(args, "model_name", None)
    return model_name.strip() if isinstance(model_name, str) and model_name.strip() else None


def _model_alias(args: argparse.Namespace) -> str | None:
    alias = getattr(args, "model_alias", None)
    return alias.strip() if isinstance(alias, str) and alias.strip() else None


def _external_llm_provider_selected(args: argparse.Namespace) -> bool:
    provider_ref = getattr(args, "llm_provider_profile_ref", None)
    if isinstance(provider_ref, str) and provider_ref:
        return provider_ref != "local_ollama"
    if any(
        getattr(args, name, None)
        for name in (
            "llm_model_profile_ref",
            "llm_output_governance_profile_ref",
        )
    ):
        return True
    model_name = _explicit_model_name(args)
    return bool(model_name and not model_name.startswith("ollama/"))


def _route_backend_provider(args: argparse.Namespace, model_name: str) -> str:
    provider_ref = getattr(args, "llm_provider_profile_ref", None)
    if isinstance(provider_ref, str) and provider_ref:
        if provider_ref == "local_ollama":
            return "ollama"
        return provider_ref.removesuffix("_gated")
    if model_name.startswith("ollama/"):
        return "ollama"
    return model_name.split("/", 1)[0]


def _route_kind(backend_provider: str) -> str:
    if backend_provider == "ollama":
        return "adk_litellm"
    return "adk_litellm_openai_compatible"


def _normalized_question(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _normalized_follow_up_questions(values: Any) -> tuple[str, ...]:
    questions = []
    for value in _list_value(values):
        question = _normalized_question(value)
        if question:
            questions.append(question)
    return tuple(questions)


def _normalized_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def _preview(value: str, *, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[:limit].rstrip()


def _local_ollama_api_base(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "http" and parsed.hostname in {
        "127.0.0.1",
        "localhost",
        "::1",
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


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


def _public_ref_details(value: Any) -> list[dict[str, Any]]:
    refs = value if isinstance(value, tuple) else _allowed_refs(value)
    public_refs: list[dict[str, Any]] = []
    for item in refs:
        mapping = _mapping(item)
        ref = str(mapping.get("ref") or "")
        if not ref:
            continue
        detail: dict[str, Any] = {
            "ref": ref,
            "kind": str(mapping.get("kind") or "unknown"),
        }
        purpose = mapping.get("purpose")
        if isinstance(purpose, str) and purpose:
            detail["purpose"] = purpose
        public_refs.append(detail)
    return public_refs


def _failure_explanation(
    *,
    status: str,
    blocking_reasons: tuple[str, ...],
    citation_failures: tuple[str, ...],
) -> str | None:
    if status == "success":
        return None
    if EXTERNAL_READONLY_ASK_QUALITY_CONTRACT_VIOLATION in blocking_reasons:
        return (
            "模型输出未通过回答质量检查，因此没有作为成功答案返回。"
        )
    if _has_model_alias_reason(blocking_reasons):
        return "模型别名参数未通过预检，尚未进入模型回答。"
    if EXTERNAL_READONLY_ASK_GUIDED_EXTERNAL_FETCH_DECLINED in blocking_reasons:
        return "用户未授权本次外部只读抓取，已停止在模型回答之前。"
    if EXTERNAL_READONLY_ASK_GUIDED_LIVE_LLM_DECLINED in blocking_reasons:
        return "用户未授权本次受控大模型回答，已停止进入模型调用。"
    if EXTERNAL_READONLY_ASK_GUIDED_EXTERNAL_PROVIDER_DECLINED in blocking_reasons:
        return "用户未授权本次外部模型 provider 调用，已停止进入模型调用。"
    if EXTERNAL_READONLY_ASK_GUIDED_QUESTION_REQUIRED in blocking_reasons:
        return "用户未输入问题，已停止在证据抓取和模型回答之前。"
    if _has_guided_reason(blocking_reasons):
        return "首用引导未完成或当前场景不可交互，尚未进入模型回答。"
    if _has_provider_key_reason(blocking_reasons):
        return "DeepSeek key 尚未通过安全输入或凭据检查，未进入模型回答。"
    if status == "insufficient_evidence":
        return "当前证据事实不足，无法形成受控问答答案。"
    if citation_failures:
        return "模型输出缺少可用引用，无法作为受控问答答案返回。"
    if _has_missing_gate_reason(blocking_reasons):
        return "当前请求缺少必要输入或显式授权，尚未进入模型回答。"
    if EXTERNAL_READONLY_ASK_PROVIDER_NOT_INJECTED in blocking_reasons:
        return "当前产品入口没有可用的模型调用服务。"
    if EXTERNAL_READONLY_ASK_PROVIDER_RESOLUTION_FAILED in blocking_reasons:
        return "模型调用服务解析失败，尚未形成回答。"
    if _has_output_schema_validation_failure_reason(blocking_reasons):
        return "模型输出未通过结构化输出校验，未形成可返回答案。"
    if any(reason.startswith("llm_invocation_failure:") for reason in blocking_reasons):
        return "模型调用失败，未形成可返回答案。"
    if blocking_reasons:
        return "本次请求被治理条件拦截，未形成可返回答案。"
    return "本次未形成可返回的成功答案。"


def _recovery_hints(
    *,
    status: str,
    blocking_reasons: tuple[str, ...],
    citation_failures: tuple[str, ...],
) -> list[str]:
    if status == "success":
        return []
    if EXTERNAL_READONLY_ASK_QUALITY_CONTRACT_VIOLATION in blocking_reasons:
        return [
            "请重试一次，或换用更稳定的本地模型。",
            "请缩短问题，并明确要求只基于证据给出最终答案。",
            "若持续失败，请保留 request_id 供后续 prompt/profile 修补。",
        ]
    if _has_model_alias_reason(blocking_reasons):
        return [
            "请使用 --model gemma4 或 --model deepseek。",
            "若需要高级参数，请改用 --model-name 与完整 profile refs，且不要同时传入 --model。",
        ]
    if _has_guided_reason(blocking_reasons):
        if EXTERNAL_READONLY_ASK_GUIDED_UNAVAILABLE_FOR_JSON_OUTPUT in blocking_reasons:
            return [
                "JSON 输出用于自动化场景，不会启动交互式首用引导。",
                "请改用文本终端运行 --guided，或显式提供所有 ask 参数。",
            ]
        if EXTERNAL_READONLY_ASK_GUIDED_REQUIRES_INTERACTIVE_TERMINAL in blocking_reasons:
            return [
                "当前不是可交互终端，已避免阻塞等待首用输入。",
                "请在终端中重试 --guided，或显式提供所有 ask 参数。",
            ]
        if EXTERNAL_READONLY_ASK_GUIDED_EXTERNAL_FETCH_DECLINED in blocking_reasons:
            return [
                "如需让系统读取该 URL，请重新运行 --guided 并在外部只读抓取确认处输入 yes。",
                "若不希望联网，请先使用受控 fetch 生成 evidence archive，再用 evidence path 提问。",
            ]
        if EXTERNAL_READONLY_ASK_GUIDED_LIVE_LLM_DECLINED in blocking_reasons:
            return [
                "如需形成模型答案，请重新运行 --guided 并在受控大模型回答确认处输入 yes。",
                "若只想检查证据抓取，请使用 external-readonly refs/fetch 路径，不进入 ask 模型回答。",
            ]
        if EXTERNAL_READONLY_ASK_GUIDED_EXTERNAL_PROVIDER_DECLINED in blocking_reasons:
            return [
                "如需使用 DeepSeek，请重新运行 --guided 并在外部 provider 调用确认处输入 yes。",
                "若不希望调用外部 provider，请选择 gemma4 本地模型。",
            ]
        if EXTERNAL_READONLY_ASK_GUIDED_QUESTION_REQUIRED in blocking_reasons:
            return [
                "请重新运行 --guided，并在“请输入问题”处输入要基于证据回答的问题。",
                "问题可以很短，例如：这份资料主要说明了什么？",
            ]
        return [
            "请重新运行 --guided，并按提示输入 URL/evidence、问题、模型与授权确认。",
            "若用于自动化，请显式提供 source/evidence、question、model 和治理 gate 参数。",
        ]
    if _has_provider_key_reason(blocking_reasons):
        if PROVIDER_KEY_STORE_UNAVAILABLE in blocking_reasons:
            return [
                "当前系统没有可用的 OS keychain 凭据存储后端。",
                "请重新运行并选择“仅本次使用”，或在当前进程环境中临时提供 DeepSeek key。",
            ]
        if PROVIDER_KEY_STORED_CREDENTIAL_NOT_FOUND in blocking_reasons:
            return [
                "未找到已保存的 DeepSeek key。",
                "请在交互式终端中使用 --prompt-provider-key 并选择“长期保存”，或选择“仅本次使用”。",
            ]
        if PROVIDER_KEY_STORED_CREDENTIAL_LOAD_FAILED in blocking_reasons:
            return [
                "读取已保存 DeepSeek key 失败，已停止进入模型调用。",
                "请检查系统钥匙串授权，或重新运行 --prompt-provider-key。",
            ]
        if PROVIDER_KEY_PERSISTENT_SAVE_FAILED in blocking_reasons:
            return [
                "DeepSeek key 未能写入系统钥匙串，已停止进入模型调用。",
                "请检查系统钥匙串授权，或重新运行并选择“仅本次使用”。",
            ]
        if PROVIDER_KEY_PROMPT_UNAVAILABLE_FOR_JSON_OUTPUT in blocking_reasons:
            return [
                "JSON 输出用于自动化场景，不会交互式读取 key。",
                "请在交互式文本模式下使用 --prompt-provider-key，使用 --use-stored-provider-key，或在当前进程环境中临时提供 DeepSeek key。",
            ]
        if PROVIDER_KEY_PROMPT_REQUIRES_INTERACTIVE_TERMINAL in blocking_reasons:
            return [
                "当前不是可交互终端，已避免阻塞等待 key 输入。",
                "请在终端中重试 --prompt-provider-key，或由调用方在当前进程环境中临时提供 DeepSeek key。",
            ]
        return [
            "请在交互式终端中使用 --prompt-provider-key，并选择“仅本次使用”或“长期保存”。",
            "不要把 DeepSeek key 写入命令、仓库、配置文件、任务包或 evidence archive。",
        ]
    if status == "insufficient_evidence":
        return [
            "请补充可回答该问题的 external-readonly evidence。",
            "请确认 evidence archive 中存在 governed_summary_facts。",
        ]
    if citation_failures:
        return [
            "请确认 evidence refs 可见且与 governed summary facts 对齐。",
            "请重试一次，要求回答中引用可见 evidence ref。",
        ]
    if _has_external_provider_gate_reason(blocking_reasons):
        return [
            "请补齐外部 provider 的 profile ref、model name、network gate、operator approval 和 audit ref。",
            "请确认密钥只通过当前进程环境变量或显式 OS keychain 读取提供，不要写入命令、配置或证据文件。",
        ]
    if _has_live_call_failure_reason(blocking_reasons):
        return [
            "请检查所选 provider 的环境变量密钥、网络可达性、模型名称和服务额度。",
            "若使用外部 provider，请确认失败详情只保留在本地调试环境，不进入产品响应。",
        ]
    if _has_output_schema_validation_failure_reason(blocking_reasons):
        return [
            "请缩短追问或降低摘要字数，并明确要求只基于证据给出最终答案。",
            "可重试一次，或切换到 deepseek 路径验证是否为本地结构化输出约束导致。",
            "若持续失败，请保留 request_id 供后续 output governance profile 修补。",
        ]
    if _has_missing_gate_reason(blocking_reasons):
        return [
            "请补齐 source URL 或 evidence path。",
            "请显式提供 live LLM 与 Ollama 的请求、允许和 approval ref。",
        ]
    if EXTERNAL_READONLY_ASK_PROVIDER_NOT_INJECTED in blocking_reasons:
        return ["请通过产品运行装配入口调用，以注入受治理的模型调用服务。"]
    if EXTERNAL_READONLY_ASK_PROVIDER_RESOLUTION_FAILED in blocking_reasons:
        return ["请检查本地 Ollama 地址、模型名称和运行配置。"]
    return ["请查看 blocking_reasons，并按缺失的受控条件补齐后重试。"]


def _has_missing_gate_reason(blocking_reasons: tuple[str, ...]) -> bool:
    missing_gate_reasons = {
        "source_url_or_evidence_output_path_required",
        "external_readonly_natural_language_confirmation_required",
        "question_required",
        "request_live_llm_required",
        "request_ollama_required",
        "allow_live_llm_required",
        "allow_ollama_required",
        "live_llm_approval_ref_required",
        "model_name_required",
        "live_llm_timeout_seconds_must_be_positive",
        "live_llm_max_tokens_must_be_positive",
        "answer_preview_limit_must_be_positive",
        "ollama_api_base_must_be_local",
    }
    return any(
        reason in missing_gate_reasons
        for reason in blocking_reasons
    )


def _has_model_alias_reason(blocking_reasons: tuple[str, ...]) -> bool:
    return any(
        reason == EXTERNAL_READONLY_ASK_MODEL_ALIAS_CONFLICT
        or reason.startswith(f"{EXTERNAL_READONLY_ASK_MODEL_ALIAS_UNKNOWN}:")
        for reason in blocking_reasons
    )


def _has_guided_reason(blocking_reasons: tuple[str, ...]) -> bool:
    guided_reasons = {
        EXTERNAL_READONLY_ASK_GUIDED_UNAVAILABLE_FOR_JSON_OUTPUT,
        EXTERNAL_READONLY_ASK_GUIDED_REQUIRES_INTERACTIVE_TERMINAL,
        EXTERNAL_READONLY_ASK_GUIDED_CANCELLED,
        EXTERNAL_READONLY_ASK_GUIDED_EXTERNAL_FETCH_DECLINED,
        EXTERNAL_READONLY_ASK_GUIDED_LIVE_LLM_DECLINED,
        EXTERNAL_READONLY_ASK_GUIDED_EXTERNAL_PROVIDER_DECLINED,
        EXTERNAL_READONLY_ASK_GUIDED_QUESTION_REQUIRED,
        EXTERNAL_READONLY_ASK_GUIDED_INPUT_REQUIRED,
    }
    return any(reason in guided_reasons for reason in blocking_reasons)


def _has_provider_key_reason(blocking_reasons: tuple[str, ...]) -> bool:
    provider_key_reasons = {
        DEEPSEEK_PROVIDER_KEY_REQUIRED,
        PROVIDER_KEY_PROMPT_UNAVAILABLE_FOR_JSON_OUTPUT,
        PROVIDER_KEY_PROMPT_REQUIRES_INTERACTIVE_TERMINAL,
        PROVIDER_KEY_INPUT_REQUIRED,
        PROVIDER_KEY_PROMPT_CANCELLED,
        PROVIDER_KEY_STORE_UNAVAILABLE,
        PROVIDER_KEY_STORED_CREDENTIAL_NOT_FOUND,
        PROVIDER_KEY_STORED_CREDENTIAL_LOAD_FAILED,
        PROVIDER_KEY_PERSISTENT_SAVE_FAILED,
    }
    return any(reason in provider_key_reasons for reason in blocking_reasons)


def _has_external_provider_gate_reason(blocking_reasons: tuple[str, ...]) -> bool:
    external_provider_reasons = {
        "llm_provider_profile_ref_required",
        "llm_model_profile_ref_required",
        "llm_output_governance_profile_ref_required",
        "external_llm_model_name_required",
        "external_llm_network_gate_open_required",
        "external_llm_operator_approved_required",
        "external_llm_audit_ref_required",
    }
    return any(reason in external_provider_reasons for reason in blocking_reasons)


def _has_live_call_failure_reason(blocking_reasons: tuple[str, ...]) -> bool:
    return any(
        reason == "llm_invocation_failure:live_call_failure"
        for reason in blocking_reasons
    )


def _has_output_schema_validation_failure_reason(
    blocking_reasons: tuple[str, ...],
) -> bool:
    return any(
        reason == "llm_invocation_failure:output_schema_validation_failure"
        for reason in blocking_reasons
    )


def _text_ref_lines(value: list[Any]) -> list[str]:
    lines: list[str] = []
    for item in value:
        mapping = _mapping(item)
        ref = mapping.get("ref")
        if not ref:
            continue
        kind = mapping.get("kind") or "unknown"
        purpose = mapping.get("purpose")
        suffix = f" ({purpose})" if purpose else ""
        lines.append(f"- {kind}: {ref}{suffix}")
    return lines


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


__all__ = [
    "EXTERNAL_READONLY_ASK_COMMAND",
    "EXTERNAL_READONLY_ASK_INTERACTION_MODE",
    "EXTERNAL_READONLY_ASK_REQUEST_ID",
    "ExternalReadonlyAskCliSessionState",
    "ExternalReadonlyAskFetchExecutor",
    "ExternalReadonlyAskLlmInvocationServiceFactory",
    "build_external_readonly_ask_cli_output",
    "build_external_readonly_ask_follow_up_cli_output",
    "external_readonly_ask_command",
]
