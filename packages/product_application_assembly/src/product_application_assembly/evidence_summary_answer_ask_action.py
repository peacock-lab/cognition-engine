"""Product-level action service for evidence-summary-answer ask."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any, Protocol

from schemas.llm_invocation import LlmInvocationRequest

from product_application_assembly.evidence_summary_answer_context import (
    build_evidence_summary_answer_context,
)
from product_application_assembly.evidence_summary_answer_follow_up import (
    EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_INTERACTION_MODE,
    build_evidence_summary_answer_follow_up_context,
    build_evidence_summary_answer_follow_up_seed,
    evidence_summary_answer_follow_up_seed_status_dict,
)
from product_application_assembly.evidence_summary_answer_generation import (
    EVIDENCE_SUMMARY_ANSWER_GENERATION_INTERACTION_MODE,
    build_evidence_summary_answer_llm_invocation_request,
    build_evidence_summary_answer_result_from_llm_invocation_result,
)
from product_application_assembly.evidence_summary_answer_product_output import (
    assemble_evidence_summary_answer_product_output,
    assemble_evidence_summary_answer_product_summary,
)
from product_application_assembly.evidence_summary_answer_result import (
    build_evidence_summary_answer_answerability_preflight_result,
    build_no_model_evidence_summary_answer_result,
    evidence_summary_answer_result_status_dict,
)
from product_application_assembly.evidence_summary_answer_ask_interaction import (
    EvidenceSummaryAnswerAskInteractionState,
)
from product_application_assembly.governed_evidence_digest import (
    build_governed_evidence_digest_from_external_readonly_facts,
)


PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ASK_ACTION_SOURCE = (
    "product_application_assembly.evidence_summary_answer_ask_action"
)
EVIDENCE_SUMMARY_ANSWER_ASK_PRODUCT_PATH = "external_readonly_ask_product_path"
EVIDENCE_SUMMARY_ANSWER_ASK_ACTION_SERVICE_REF = (
    "service://product-application-assembly/external-readonly-ask/action"
)

ASK_ACTION_EXIT_OK = 0
ASK_ACTION_EXIT_RUNTIME_FAILURE = 1
ASK_ACTION_EXIT_BLOCKING = 3

ASK_ACTION_FAILURE = "external_readonly_ask_product_action_failure"
ASK_ACTION_QUALITY_CONTRACT_VIOLATION = "llm_answer_quality_contract_violation"
ASK_ACTION_PROVIDER_RESOLUTION_FAILED = (
    "external_readonly_ask_llm_provider_resolution_failed"
)
ASK_ACTION_PROVIDER_NOT_INJECTED = "external_readonly_ask_llm_provider_not_injected"
ASK_ACTION_CONTEXT_BRIDGE_FAILED = "evidence_summary_answer_context_bridge_failed"


@dataclass(frozen=True)
class EvidenceSummaryAnswerAskActionInput:
    """Channel-neutral ask action input.

    This object is not a CLI argparse namespace, not terminal state, and not an
    ADK runtime object. Channel adapters may collect values, but the product
    action service owns the ask run composition.
    """

    request_id: str
    source_url: str | None
    evidence_paths: tuple[str, ...]
    question: str
    route_facts: Any | None
    governance_precondition: Any | None
    model_name: str | None = None
    product_name: str = "Cognition System / 认知系统"
    command: str = "cognition external-readonly ask"
    product_path: str = EVIDENCE_SUMMARY_ANSWER_ASK_PRODUCT_PATH
    input_channel: str = "unknown"
    answer_generation_service_ref: str = EVIDENCE_SUMMARY_ANSWER_ASK_ACTION_SERVICE_REF
    source: str = PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ASK_ACTION_SOURCE
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceSummaryAnswerAskActionResult:
    """Product-level ask action result."""

    exit_code: int
    output: dict[str, Any]
    next_state: EvidenceSummaryAnswerAskInteractionState | None = None


class EvidenceSummaryAnswerEvidenceBridgeBuilder(Protocol):
    def __call__(
        self,
        action_input: EvidenceSummaryAnswerAskActionInput,
    ) -> Mapping[str, Any]:
        """Build evidence bridge facts for the ask action."""


class EvidenceSummaryAnswerLlmServiceResolver(Protocol):
    def __call__(
        self,
        action_input: EvidenceSummaryAnswerAskActionInput,
    ) -> Mapping[str, Any]:
        """Resolve the governed LLM service for the ask action."""


def build_evidence_summary_answer_ask_evidence_bridge_from_facts(
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
    source: str = PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ASK_ACTION_SOURCE,
    product_path: str = EVIDENCE_SUMMARY_ANSWER_ASK_PRODUCT_PATH,
) -> dict[str, Any]:
    """Build a product evidence bridge from governed summary fact payloads."""

    try:
        digests = [
            build_governed_evidence_digest_from_external_readonly_facts(
                facts,
                metadata={"source": source, "product_path": product_path},
            )
            for facts in facts_payloads
        ]
        context = build_evidence_summary_answer_context(
            request_id=f"{request_id}/context",
            user_question=question,
            digests=digests,
            metadata={"source": source, "product_path": product_path},
        )
    except Exception:
        return build_evidence_summary_answer_empty_ask_evidence_bridge(
            blocking_reasons=(ASK_ACTION_CONTEXT_BRIDGE_FAILED,),
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
        "evidence_refs": evidence_refs
        or tuple(ref.model_dump(mode="python") for ref in context.evidence_refs),
        "additional_refs": additional_refs
        or tuple(ref.model_dump(mode="python") for ref in context.additional_refs),
        "readonly_refs_status": readonly_refs_status,
        "fetch_request_id": fetch_request_id,
        "external_readonly_fetch_performed": external_readonly_fetch_performed,
        "external_readonly_network_call_performed": (
            external_readonly_network_call_performed
        ),
        "external_network_call_performed": external_network_call_performed,
    }


def build_evidence_summary_answer_empty_ask_evidence_bridge(
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
    """Build an empty bridge for blocked evidence intake."""

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


def build_evidence_summary_answer_ask_blocked_output(
    action_input: EvidenceSummaryAnswerAskActionInput,
    *,
    blocking_reasons: tuple[str, ...],
    warnings: tuple[str, ...],
    product_response_summary: Mapping[str, Any],
    fetch_request_id: str | None,
) -> dict[str, Any]:
    """Build a product-level blocked output for an ask action."""

    evidence_refs = _allowed_refs(product_response_summary.get("evidence_refs"))
    additional_refs = _allowed_refs(product_response_summary.get("additional_refs"))
    public_evidence_refs = _public_ref_details(evidence_refs)
    public_additional_refs = _public_ref_details(additional_refs)
    answer_trace_ref = _optional_string(product_response_summary.get("answer_trace_ref"))
    answer_artifact_ref = _optional_string(
        product_response_summary.get("answer_artifact_ref")
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
        "product": action_input.product_name,
        "command": action_input.command,
        "interaction_mode": EVIDENCE_SUMMARY_ANSWER_GENERATION_INTERACTION_MODE,
        "product_path": action_input.product_path,
        "status": "blocked",
        "success": False,
        "failure_type": ASK_ACTION_FAILURE,
        "request_id": action_input.request_id,
        "fetch_request_id": fetch_request_id,
        "llm_request_id": None,
        "model_name": None,
        "source_url_present": bool(action_input.source_url),
        "source_url": action_input.source_url,
        "evidence_path_count": len(action_input.evidence_paths),
        "evidence_ref_count": len(evidence_refs),
        "additional_ref_count": len(additional_refs),
        "evidence_refs": public_evidence_refs,
        "additional_refs": public_additional_refs,
        "readonly_refs_status": "blocked",
        "answer_trace_ref": answer_trace_ref,
        "answer_trace_status": _optional_string(
            product_response_summary.get("answer_trace_status")
        ),
        "answer_trace_summary": dict(
            _mapping(product_response_summary.get("answer_trace_summary"))
        ),
        "answer_trace_unavailable_reason": (
            None if answer_trace_ref else "answer_trace_requires_answer_context"
        ),
        "answer_artifact_ref": answer_artifact_ref,
        "answer_artifact_status": _optional_string(
            product_response_summary.get("answer_artifact_status")
        ),
        "answer_artifact_summary": dict(
            _mapping(product_response_summary.get("answer_artifact_summary"))
        ),
        "answer_artifact_unavailable_reason": (
            None if answer_artifact_ref else "answer_artifact_requires_answer_context"
        ),
        "observability_summary_ref": _optional_string(
            product_response_summary.get("observability_summary_ref")
        ),
        "observability_summary_status": _optional_string(
            product_response_summary.get("observability_summary_status")
        ),
        "safe_observability_summary": dict(
            _mapping(product_response_summary.get("safe_observability_summary"))
        ),
        "trace_inspect_ref": _optional_string(
            product_response_summary.get("trace_inspect_ref")
        ),
        "trace_inspect_status": _optional_string(
            product_response_summary.get("trace_inspect_status")
        ),
        "trace_inspect_summary": dict(
            _mapping(product_response_summary.get("trace_inspect_summary"))
        ),
        "trace_inspect_unavailable_reason": _optional_string(
            product_response_summary.get("trace_inspect_unavailable_reason")
        ),
        "answer_run_ref": _optional_string(
            product_response_summary.get("answer_run_ref")
        ),
        "answer_run_status": _optional_string(
            product_response_summary.get("answer_run_status")
        ),
        "answer_run_summary": dict(
            _mapping(product_response_summary.get("answer_run_summary"))
        ),
        "answer_run_unavailable_reason": _optional_string(
            product_response_summary.get("answer_run_unavailable_reason")
        ),
        "product_response_summary": dict(product_response_summary),
        "question_preview": (
            _preview(action_input.question, limit=120) if action_input.question else None
        ),
        "answer": None,
        "answer_preview": None,
        "answer_length": None,
        "llm_call_allowed": False,
        "llm_call_attempted": False,
        "llm_runtime_call_performed": False,
        "external_readonly_fetch_performed": bool(
            _mapping(product_response_summary.get("metadata")).get(
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
        "exit_code": ASK_ACTION_EXIT_BLOCKING,
    }


def run_evidence_summary_answer_ask_initial_action(
    action_input: EvidenceSummaryAnswerAskActionInput,
    *,
    evidence_bridge_builder: EvidenceSummaryAnswerEvidenceBridgeBuilder,
    llm_service_resolver: EvidenceSummaryAnswerLlmServiceResolver | None,
) -> EvidenceSummaryAnswerAskActionResult:
    """Run an initial evidence-summary-answer ask action."""

    evidence_bridge = evidence_bridge_builder(action_input)
    bridge_reasons = _string_tuple(evidence_bridge.get("blocking_reasons"))
    if bridge_reasons:
        output = build_evidence_summary_answer_ask_blocked_output(
            action_input,
            blocking_reasons=bridge_reasons,
            warnings=_string_tuple(evidence_bridge.get("warnings")),
            product_response_summary=assemble_evidence_summary_answer_product_summary(
                request_id=action_input.request_id,
                answer_status="blocked",
                evidence_refs=tuple(_allowed_refs(evidence_bridge.get("evidence_refs"))),
                additional_refs=tuple(
                    _allowed_refs(evidence_bridge.get("additional_refs"))
                ),
                blocking_reasons=bridge_reasons,
                warnings=_string_tuple(evidence_bridge.get("warnings")),
                readonly_refs_status=str(
                    evidence_bridge.get("readonly_refs_status") or "blocked"
                ),
                source_url_present=bool(action_input.source_url),
                evidence_path_count=len(action_input.evidence_paths),
                model_name=None,
                llm_call_allowed=False,
                llm_call_attempted=False,
                llm_runtime_call_performed=False,
                external_readonly_fetch_performed=bool(
                    evidence_bridge.get("external_readonly_fetch_performed")
                ),
                external_readonly_network_call_performed=bool(
                    evidence_bridge.get("external_readonly_network_call_performed")
                ),
                external_network_call_performed=bool(
                    evidence_bridge.get("external_network_call_performed")
                ),
                product_path=action_input.product_path,
                metadata={"input_channel": action_input.input_channel},
            ).product_response_summary,
            fetch_request_id=_optional_string(evidence_bridge.get("fetch_request_id")),
        )
        return EvidenceSummaryAnswerAskActionResult(
            exit_code=_exit_code_from_output(output),
            output=output,
        )

    context = evidence_bridge["context"]
    generation_policy_facts = _generation_policy_facts(action_input, context)
    preflight_result_model = build_evidence_summary_answer_answerability_preflight_result(
        context,
        metadata={"source": action_input.source, "product_path": action_input.product_path},
    )
    if preflight_result_model is not None:
        answer_result = evidence_summary_answer_result_status_dict(
            preflight_result_model
        )
        follow_up_seed = build_evidence_summary_answer_follow_up_seed(
            preflight_result_model,
            metadata={"product_path": action_input.product_path},
        )
        output = _output_from_answer_result(
            action_input,
            answer_result=answer_result,
            llm_request=None,
            evidence_bridge=evidence_bridge,
            resolution_warnings=(),
            follow_up_seed=follow_up_seed,
        )
        return EvidenceSummaryAnswerAskActionResult(
            exit_code=_exit_code_from_output(output),
            output=output,
            next_state=_state_from_action(
                action_input,
                evidence_bridge=evidence_bridge,
                follow_up_seed=follow_up_seed,
                service=None,
            ),
        )

    try:
        llm_request = build_evidence_summary_answer_llm_invocation_request(
            context,
            route_facts=action_input.route_facts,
            governance_precondition=action_input.governance_precondition,
            request_id=f"{action_input.request_id}/llm",
            generation_policy_facts=generation_policy_facts,
            metadata={"product_path": action_input.product_path},
        )
    except ValueError as exc:
        result = build_no_model_evidence_summary_answer_result(
            context,
            metadata={
                "source": action_input.source,
                "bridge_reason": str(exc),
                "product_path": action_input.product_path,
            },
        )
        answer_result = evidence_summary_answer_result_status_dict(result)
        output = _output_from_answer_result(
            action_input,
            answer_result=answer_result,
            llm_request=None,
            evidence_bridge=evidence_bridge,
            resolution_warnings=(),
        )
        return EvidenceSummaryAnswerAskActionResult(
            exit_code=_exit_code_from_output(output),
            output=output,
        )

    resolution = (
        llm_service_resolver(action_input)
        if llm_service_resolver is not None
        else {
            "service": None,
            "llm_invoker": None,
            "blocking_reasons": (ASK_ACTION_PROVIDER_NOT_INJECTED,),
            "warnings": (),
        }
    )
    resolution_reasons = _string_tuple(resolution.get("blocking_reasons"))
    if resolution_reasons:
        output = build_evidence_summary_answer_ask_blocked_output(
            action_input,
            blocking_reasons=resolution_reasons,
            warnings=_string_tuple(resolution.get("warnings")),
            product_response_summary=assemble_evidence_summary_answer_product_summary(
                request_id=action_input.request_id,
                answer_status="blocked",
                evidence_refs=tuple(_allowed_refs(evidence_bridge.get("evidence_refs"))),
                additional_refs=tuple(
                    _allowed_refs(evidence_bridge.get("additional_refs"))
                ),
                blocking_reasons=resolution_reasons,
                warnings=_string_tuple(resolution.get("warnings")),
                readonly_refs_status=str(evidence_bridge.get("readonly_refs_status")),
                source_url_present=bool(action_input.source_url),
                evidence_path_count=len(action_input.evidence_paths),
                model_name=None,
                llm_call_allowed=False,
                llm_call_attempted=False,
                llm_runtime_call_performed=False,
                external_readonly_fetch_performed=bool(
                    evidence_bridge.get("external_readonly_fetch_performed")
                ),
                external_readonly_network_call_performed=bool(
                    evidence_bridge.get("external_readonly_network_call_performed")
                ),
                external_network_call_performed=bool(
                    evidence_bridge.get("external_network_call_performed")
                ),
                product_path=action_input.product_path,
                metadata={"input_channel": action_input.input_channel},
            ).product_response_summary,
            fetch_request_id=_optional_string(evidence_bridge.get("fetch_request_id")),
        )
        return EvidenceSummaryAnswerAskActionResult(
            exit_code=_exit_code_from_output(output),
            output=output,
        )

    service = resolution.get("service")
    llm_invoker = resolution.get("llm_invoker") or _llm_invoker(service)
    if not callable(llm_invoker):
        output = build_evidence_summary_answer_ask_blocked_output(
            action_input,
            blocking_reasons=(ASK_ACTION_PROVIDER_RESOLUTION_FAILED,),
            warnings=_string_tuple(resolution.get("warnings")),
            product_response_summary=assemble_evidence_summary_answer_product_summary(
                request_id=action_input.request_id,
                answer_status="blocked",
                evidence_refs=tuple(_allowed_refs(evidence_bridge.get("evidence_refs"))),
                additional_refs=tuple(
                    _allowed_refs(evidence_bridge.get("additional_refs"))
                ),
                blocking_reasons=(ASK_ACTION_PROVIDER_RESOLUTION_FAILED,),
                warnings=_string_tuple(resolution.get("warnings")),
                readonly_refs_status=str(evidence_bridge.get("readonly_refs_status")),
                source_url_present=bool(action_input.source_url),
                evidence_path_count=len(action_input.evidence_paths),
                model_name=None,
                llm_call_allowed=False,
                llm_call_attempted=False,
                llm_runtime_call_performed=False,
                external_readonly_fetch_performed=bool(
                    evidence_bridge.get("external_readonly_fetch_performed")
                ),
                external_readonly_network_call_performed=bool(
                    evidence_bridge.get("external_readonly_network_call_performed")
                ),
                external_network_call_performed=bool(
                    evidence_bridge.get("external_network_call_performed")
                ),
                product_path=action_input.product_path,
                metadata={"input_channel": action_input.input_channel},
            ).product_response_summary,
            fetch_request_id=_optional_string(evidence_bridge.get("fetch_request_id")),
        )
        return EvidenceSummaryAnswerAskActionResult(
            exit_code=_exit_code_from_output(output),
            output=output,
        )
    llm_result = llm_invoker(llm_request)
    answer_result_model = build_evidence_summary_answer_result_from_llm_invocation_result(
        context,
        llm_result,
        generation_policy_facts=generation_policy_facts,
        metadata={"product_path": action_input.product_path},
    )
    answer_result = evidence_summary_answer_result_status_dict(answer_result_model)
    follow_up_seed = None
    if answer_result_model.status == "success":
        follow_up_seed = build_evidence_summary_answer_follow_up_seed(
            answer_result_model,
            metadata={"product_path": action_input.product_path},
        )
    output = _output_from_answer_result(
        action_input,
        answer_result=answer_result,
        llm_request=llm_request,
        evidence_bridge=evidence_bridge,
        resolution_warnings=_string_tuple(resolution.get("warnings")),
        follow_up_seed=follow_up_seed,
    )
    return EvidenceSummaryAnswerAskActionResult(
        exit_code=_exit_code_from_output(output),
        output=output,
        next_state=_state_from_action(
            action_input,
            evidence_bridge=evidence_bridge,
            follow_up_seed=follow_up_seed,
            service=service,
        ),
    )


def run_evidence_summary_answer_ask_follow_up_action(
    session_state: EvidenceSummaryAnswerAskInteractionState,
    follow_up_question: str,
) -> EvidenceSummaryAnswerAskActionResult:
    """Run one same-process follow-up over an existing ask action state."""

    question = " ".join(str(follow_up_question or "").strip().split())
    if not question:
        blocking_reasons = ("external_readonly_ask_guided_follow_up_question_required",)
        action_input = _action_input_from_state(session_state, question=follow_up_question)
        output = build_evidence_summary_answer_ask_blocked_output(
            action_input,
            blocking_reasons=blocking_reasons,
            warnings=(),
            product_response_summary=assemble_evidence_summary_answer_product_summary(
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
                product_path=action_input.product_path,
                metadata={"input_channel": action_input.input_channel},
            ).product_response_summary,
            fetch_request_id=None,
        )
        return EvidenceSummaryAnswerAskActionResult(
            exit_code=_exit_code_from_output(output),
            output=output,
            next_state=session_state,
        )
    if session_state.follow_up_seed is None or session_state.service is None:
        blocking_reasons = ("external_readonly_ask_follow_up_state_unavailable",)
        action_input = _action_input_from_state(session_state, question=question)
        output = build_evidence_summary_answer_ask_blocked_output(
            action_input,
            blocking_reasons=blocking_reasons,
            warnings=(),
            product_response_summary=assemble_evidence_summary_answer_product_summary(
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
                product_path=action_input.product_path,
                metadata={"input_channel": action_input.input_channel},
            ).product_response_summary,
            fetch_request_id=None,
        )
        return EvidenceSummaryAnswerAskActionResult(
            exit_code=_exit_code_from_output(output),
            output=output,
            next_state=session_state,
        )

    follow_up_index = session_state.follow_up_turn_index + 1
    action_input = _action_input_from_state(session_state, question=question)
    output, next_seed = _run_follow_up_turn(
        action_input,
        follow_up_index=follow_up_index,
        evidence_bridge=session_state.evidence_bridge,
        service=session_state.service,
        seed=session_state.follow_up_seed,
    )
    next_state = replace(
        session_state,
        follow_up_seed=next_seed,
        follow_up_turn_index=follow_up_index,
    )
    return EvidenceSummaryAnswerAskActionResult(
        exit_code=_exit_code_from_output(output),
        output=output,
        next_state=next_state,
    )


def _run_follow_up_turn(
    action_input: EvidenceSummaryAnswerAskActionInput,
    *,
    follow_up_index: int,
    evidence_bridge: Mapping[str, Any],
    service: Any,
    seed: Any,
) -> tuple[dict[str, Any], Any | None]:
    context = build_evidence_summary_answer_follow_up_context(
        seed,
        request_id=f"{action_input.request_id}/follow-up-{follow_up_index}/context",
        follow_up_question=action_input.question,
        digests=evidence_bridge["context"].digests,
        metadata={"product_path": action_input.product_path},
    )
    generation_policy_facts = _generation_policy_facts(action_input, context)
    preflight_result_model = build_evidence_summary_answer_answerability_preflight_result(
        context,
        metadata={"source": action_input.source, "product_path": action_input.product_path},
    )
    follow_up_bridge = dict(evidence_bridge)
    follow_up_bridge["context"] = context
    if preflight_result_model is not None:
        answer_result = evidence_summary_answer_result_status_dict(
            preflight_result_model
        )
        next_seed = build_evidence_summary_answer_follow_up_seed(
            preflight_result_model,
            metadata={"product_path": action_input.product_path},
        )
        output = _output_from_answer_result(
            action_input,
            request_id=f"{action_input.request_id}/follow-up-{follow_up_index}",
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
        route_facts=action_input.route_facts,
        governance_precondition=action_input.governance_precondition,
        request_id=f"{action_input.request_id}/follow-up-{follow_up_index}/llm",
        generation_policy_facts=generation_policy_facts,
        metadata={"product_path": action_input.product_path},
    )
    llm_invoker = _llm_invoker(service)
    if not callable(llm_invoker):
        output = build_evidence_summary_answer_ask_blocked_output(
            action_input,
            blocking_reasons=(ASK_ACTION_PROVIDER_NOT_INJECTED,),
            warnings=(),
            product_response_summary=assemble_evidence_summary_answer_product_summary(
                request_id=f"{action_input.request_id}/follow-up-{follow_up_index}",
                answer_status="blocked",
                evidence_refs=tuple(_allowed_refs(evidence_bridge.get("evidence_refs"))),
                additional_refs=tuple(
                    _allowed_refs(evidence_bridge.get("additional_refs"))
                ),
                blocking_reasons=(ASK_ACTION_PROVIDER_NOT_INJECTED,),
                warnings=(),
                readonly_refs_status=str(evidence_bridge.get("readonly_refs_status")),
                source_url_present=bool(action_input.source_url),
                evidence_path_count=len(action_input.evidence_paths),
                model_name=None,
                llm_call_allowed=False,
                llm_call_attempted=False,
                llm_runtime_call_performed=False,
                external_readonly_fetch_performed=bool(
                    evidence_bridge.get("external_readonly_fetch_performed")
                ),
                external_readonly_network_call_performed=bool(
                    evidence_bridge.get("external_readonly_network_call_performed")
                ),
                external_network_call_performed=bool(
                    evidence_bridge.get("external_network_call_performed")
                ),
                product_path=action_input.product_path,
                metadata={"input_channel": action_input.input_channel},
            ).product_response_summary,
            fetch_request_id=_optional_string(evidence_bridge.get("fetch_request_id")),
        )
        return output, seed
    llm_result = llm_invoker(llm_request)
    answer_result_model = build_evidence_summary_answer_result_from_llm_invocation_result(
        context,
        llm_result,
        generation_policy_facts=generation_policy_facts,
        metadata={"product_path": action_input.product_path},
    )
    answer_result = evidence_summary_answer_result_status_dict(answer_result_model)
    next_seed = (
        build_evidence_summary_answer_follow_up_seed(
            answer_result_model,
            metadata={"product_path": action_input.product_path},
        )
        if answer_result_model.status == "success"
        else None
    )
    output = _output_from_answer_result(
        action_input,
        request_id=f"{action_input.request_id}/follow-up-{follow_up_index}",
        answer_result=answer_result,
        llm_request=llm_request,
        evidence_bridge=follow_up_bridge,
        resolution_warnings=(),
        follow_up_seed=next_seed,
        follow_up_turn_index=follow_up_index,
        source_follow_up_seed_ref=seed.seed_ref,
    )
    return output, next_seed


def _output_from_answer_result(
    action_input: EvidenceSummaryAnswerAskActionInput,
    *,
    answer_result: Mapping[str, Any],
    llm_request: LlmInvocationRequest | None,
    evidence_bridge: Mapping[str, Any],
    resolution_warnings: tuple[str, ...],
    request_id: str | None = None,
    follow_up_seed: Any | None = None,
    follow_up_turn_index: int | None = None,
    source_follow_up_seed_ref: str | None = None,
) -> dict[str, Any]:
    context = evidence_bridge["context"]
    output_request_id = request_id or action_input.request_id
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
    blocking_reasons = _string_tuple(answer_result.get("blocking_reasons"))
    citation_failures = _string_tuple(answer_result.get("citation_failures"))
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
    product_output = assemble_evidence_summary_answer_product_output(
        context,
        answer_result,
        request_id=output_request_id,
        readonly_refs_status=str(evidence_bridge.get("readonly_refs_status") or status),
        blocking_reasons=blocking_reasons,
        warnings=tuple(warnings),
        recovery_hints=tuple(recovery_hints),
        source_url_present=bool(action_input.source_url),
        evidence_path_count=len(action_input.evidence_paths),
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
        answer_trace_follow_up_seed_ref=trace_seed_ref,
        llm_trace_metadata=_llm_request_trace_metadata(llm_request),
        product_path=action_input.product_path,
        metadata={"input_channel": action_input.input_channel},
    )
    evidence_refs = _public_ref_details(product_output.evidence_refs)
    additional_refs = _public_ref_details(product_output.additional_refs)
    return {
        "product": action_input.product_name,
        "command": action_input.command,
        "interaction_mode": (
            EVIDENCE_SUMMARY_ANSWER_FOLLOW_UP_INTERACTION_MODE
            if follow_up_turn_index is not None
            else EVIDENCE_SUMMARY_ANSWER_GENERATION_INTERACTION_MODE
        ),
        "product_path": action_input.product_path,
        "status": status,
        "success": status == "success",
        "failure_type": None if status == "success" else ASK_ACTION_FAILURE,
        "request_id": output_request_id,
        "fetch_request_id": evidence_bridge.get("fetch_request_id"),
        "llm_request_id": llm_request.request_id if llm_request is not None else None,
        "model_name": _answer_result_model_name(answer_result, llm_request),
        "source_url_present": bool(action_input.source_url),
        "source_url": action_input.source_url,
        "evidence_path_count": len(action_input.evidence_paths),
        "evidence_ref_count": len(product_output.evidence_refs),
        "additional_ref_count": len(product_output.additional_refs),
        "evidence_refs": evidence_refs,
        "additional_refs": additional_refs,
        "readonly_refs_status": evidence_bridge.get("readonly_refs_status"),
        "answer_trace_ref": product_output.answer_trace["trace_ref"],
        "answer_trace_status": product_output.answer_trace["answer_status"],
        "answer_trace_summary": product_output.answer_trace_summary,
        "answer_artifact_ref": product_output.answer_artifact["artifact_ref"],
        "answer_artifact_status": product_output.answer_artifact["artifact_status"],
        "answer_artifact_summary": product_output.answer_artifact_summary,
        "observability_summary_ref": product_output.observability_summary[
            "summary_ref"
        ],
        "observability_summary_status": product_output.observability_summary[
            "status"
        ],
        "safe_observability_summary": product_output.safe_observability_summary,
        "trace_inspect_ref": product_output.trace_inspect["trace_inspect_ref"],
        "trace_inspect_status": product_output.trace_inspect["inspect_status"],
        "trace_inspect_summary": product_output.trace_inspect_summary,
        "answer_run_ref": product_output.answer_run["answer_run_ref"],
        "answer_run_status": product_output.answer_run["answer_run_status"],
        "answer_run_summary": product_output.answer_run_summary,
        "answer_run_unavailable_reason": product_output.answer_run.get(
            "unavailable_reason"
        ),
        "evidence_lineage_summary": product_output.evidence_lineage_summary,
        "evidence_summary_answer_trace": product_output.answer_trace,
        "evidence_summary_answer_artifact": product_output.answer_artifact,
        "evidence_summary_answer_observability_summary": (
            product_output.observability_summary
        ),
        "evidence_summary_answer_trace_inspect": product_output.trace_inspect,
        "evidence_summary_answer_run": product_output.answer_run,
        "product_response_summary": product_output.product_response_summary,
        "question_preview": _preview(action_input.question, limit=120),
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


def _state_from_action(
    action_input: EvidenceSummaryAnswerAskActionInput,
    *,
    evidence_bridge: Mapping[str, Any],
    follow_up_seed: Any | None,
    service: Any | None,
) -> EvidenceSummaryAnswerAskInteractionState:
    return EvidenceSummaryAnswerAskInteractionState(
        request_id=action_input.request_id,
        source_url=action_input.source_url,
        evidence_paths=action_input.evidence_paths,
        evidence_bridge=evidence_bridge,
        follow_up_seed=follow_up_seed,
        service=service,
        route_facts_factory=lambda action_input=action_input: action_input.route_facts,
        governance_precondition_factory=(
            lambda action_input=action_input: action_input.governance_precondition
        ),
        metadata={
            "input_channel": action_input.input_channel,
            "model_name": action_input.model_name,
            "product_path": action_input.product_path,
        },
    )


def _action_input_from_state(
    state: EvidenceSummaryAnswerAskInteractionState,
    *,
    question: str,
) -> EvidenceSummaryAnswerAskActionInput:
    metadata = dict(state.metadata or {})
    return EvidenceSummaryAnswerAskActionInput(
        request_id=state.request_id,
        source_url=state.source_url,
        evidence_paths=state.evidence_paths,
        question=question,
        route_facts=state.route_facts(),
        governance_precondition=state.governance_precondition(),
        model_name=_optional_string(metadata.get("model_name")),
        input_channel=_optional_string(metadata.get("input_channel")) or "unknown",
        product_path=_optional_string(metadata.get("product_path"))
        or EVIDENCE_SUMMARY_ANSWER_ASK_PRODUCT_PATH,
    )


def _generation_policy_facts(
    action_input: EvidenceSummaryAnswerAskActionInput,
    context: Any,
) -> dict[str, Any]:
    return {
        "profile": "controlled_live_answer_generation",
        "allow_answer_generation_success": True,
        "answer_generation_service_ref": action_input.answer_generation_service_ref,
        "answer_policy_ref": context.answer_policy_ref,
        "citation_policy_ref": context.citation_policy_ref,
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


def _answer_result_model_name(
    answer_result: Mapping[str, Any],
    llm_request: LlmInvocationRequest | None,
) -> str | None:
    metadata = _mapping(answer_result.get("metadata"))
    routed_model = metadata.get("llm_route_model")
    if isinstance(routed_model, str) and routed_model:
        return routed_model
    return llm_request.route_facts.model_name if llm_request is not None else None


def _failure_explanation(
    *,
    status: str,
    blocking_reasons: tuple[str, ...],
    citation_failures: tuple[str, ...],
) -> str | None:
    if status == "success":
        return None
    if ASK_ACTION_QUALITY_CONTRACT_VIOLATION in blocking_reasons:
        return "模型输出未通过回答质量检查，因此没有作为成功答案返回。"
    if "model_alias_conflicts_with_explicit_model_options" in blocking_reasons:
        return "模型别名参数未通过预检，尚未进入模型回答。"
    if any(reason.startswith("model_alias_unknown") for reason in blocking_reasons):
        return "模型别名参数未通过预检，尚未进入模型回答。"
    if "external_readonly_ask_guided_external_fetch_declined" in blocking_reasons:
        return "用户未授权本次外部只读抓取，已停止在模型回答之前。"
    if "external_readonly_ask_guided_live_llm_declined" in blocking_reasons:
        return "用户未授权本次受控大模型回答，已停止进入模型调用。"
    if "external_readonly_ask_guided_external_provider_declined" in blocking_reasons:
        return "用户未授权本次外部模型 provider 调用，已停止进入模型调用。"
    if "external_readonly_ask_guided_question_required" in blocking_reasons:
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
    if ASK_ACTION_PROVIDER_NOT_INJECTED in blocking_reasons:
        return "当前产品入口没有可用的模型调用服务。"
    if ASK_ACTION_PROVIDER_RESOLUTION_FAILED in blocking_reasons:
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
    if ASK_ACTION_QUALITY_CONTRACT_VIOLATION in blocking_reasons:
        return [
            "请重试一次，或换用更稳定的本地模型。",
            "请缩短问题，并明确要求只基于证据给出最终答案。",
            "若持续失败，请保留 request_id 供后续 prompt/profile 修补。",
        ]
    if "external_readonly_ask_guided_external_fetch_declined" in blocking_reasons:
        return [
            "如需让系统读取该 URL，请重新运行 --guided 并在外部只读抓取确认处输入 yes。",
            "若不希望联网，请先使用受控 fetch 生成 evidence archive，再用 evidence path 提问。",
        ]
    if "external_readonly_ask_guided_live_llm_declined" in blocking_reasons:
        return [
            "如需形成模型答案，请重新运行 --guided 并在受控大模型回答确认处输入 yes。",
            "若只想检查证据抓取，请使用 external-readonly refs/fetch 路径，不进入 ask 模型回答。",
        ]
    if "external_readonly_ask_guided_external_provider_declined" in blocking_reasons:
        return [
            "如需使用 DeepSeek，请重新运行 --guided 并在外部 provider 调用确认处输入 yes。",
            "若不希望调用外部 provider，请选择 gemma4 本地模型。",
        ]
    if "external_readonly_ask_guided_question_required" in blocking_reasons:
        return [
            "请重新运行 --guided，并在“请输入问题”处输入要基于证据回答的问题。",
            "问题可以很短，例如：这份资料主要说明了什么？",
        ]
    if _has_provider_key_reason(blocking_reasons):
        return [
            "请在交互式终端中选择输入 DeepSeek key，或使用已保存 key。",
            "如不想使用外部 provider，请改用本地 gemma4 路径。",
        ]
    if _has_missing_gate_reason(blocking_reasons):
        return [
            "请补齐 source URL 或 evidence path。",
            "请显式提供 live LLM 与 Ollama 的请求、允许和 approval ref。",
        ]
    if _has_output_schema_validation_failure_reason(blocking_reasons):
        return [
            "请缩短追问或降低摘要字数，并明确要求只基于证据给出最终答案。",
            "可重试一次，或切换到 deepseek 路径验证是否为本地结构化输出约束导致。",
            "若持续失败，请保留 request_id 供后续 output governance profile 修补。",
        ]
    if citation_failures:
        return ["请缩短问题，并明确要求只基于证据给出最终答案。"]
    return ["请查看 blocking_reasons，并按缺失的受控条件补齐后重试。"]


def _has_guided_reason(reasons: tuple[str, ...]) -> bool:
    return any(reason.startswith("external_readonly_ask_guided_") for reason in reasons)


def _has_provider_key_reason(reasons: tuple[str, ...]) -> bool:
    return any("provider_key" in reason or "deepseek_provider_key" in reason for reason in reasons)


def _has_missing_gate_reason(reasons: tuple[str, ...]) -> bool:
    missing = {
        "source_url_or_evidence_output_path_required",
        "question_required",
        "request_live_llm_required",
        "request_ollama_required",
        "allow_live_llm_required",
        "allow_ollama_required",
        "live_llm_approval_ref_required",
        "external_readonly_natural_language_confirmation_required",
    }
    return any(reason in missing for reason in reasons)


def _has_output_schema_validation_failure_reason(reasons: tuple[str, ...]) -> bool:
    return any("output_schema_validation_failure" in reason for reason in reasons)


def _exit_code_from_output(output: Mapping[str, Any]) -> int:
    return _exit_code_from_status(output.get("status"))


def _exit_code_from_status(status: Any) -> int:
    if status == "success":
        return ASK_ACTION_EXIT_OK
    if status in {"blocked", "insufficient_evidence"}:
        return ASK_ACTION_EXIT_BLOCKING
    return ASK_ACTION_EXIT_RUNTIME_FAILURE


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _llm_invoker(service: Any) -> Any | None:
    invoker = getattr(service, "invoke", None)
    return invoker if callable(invoker) else None


def _list_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _string_tuple(value: Any) -> tuple[str, ...]:
    return tuple(str(item) for item in _list_value(value))


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


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


def _preview(value: str | None, *, limit: int) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return text[:limit].rstrip()


__all__ = (
    "ASK_ACTION_CONTEXT_BRIDGE_FAILED",
    "ASK_ACTION_PROVIDER_NOT_INJECTED",
    "EVIDENCE_SUMMARY_ANSWER_ASK_ACTION_SERVICE_REF",
    "EVIDENCE_SUMMARY_ANSWER_ASK_PRODUCT_PATH",
    "EvidenceSummaryAnswerAskActionInput",
    "EvidenceSummaryAnswerAskActionResult",
    "EvidenceSummaryAnswerEvidenceBridgeBuilder",
    "EvidenceSummaryAnswerLlmServiceResolver",
    "PRODUCT_APPLICATION_EVIDENCE_SUMMARY_ANSWER_ASK_ACTION_SOURCE",
    "build_evidence_summary_answer_ask_blocked_output",
    "build_evidence_summary_answer_ask_evidence_bridge_from_facts",
    "build_evidence_summary_answer_empty_ask_evidence_bridge",
    "run_evidence_summary_answer_ask_follow_up_action",
    "run_evidence_summary_answer_ask_initial_action",
)
