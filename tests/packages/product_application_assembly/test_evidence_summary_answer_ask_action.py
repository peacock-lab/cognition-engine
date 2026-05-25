from __future__ import annotations

import hashlib

from product_application_assembly.evidence_summary_answer_ask_action import (
    EvidenceSummaryAnswerAskActionInput,
    build_evidence_summary_answer_ask_evidence_bridge_from_facts,
    run_evidence_summary_answer_ask_follow_up_action,
    run_evidence_summary_answer_ask_initial_action,
)
from product_application_assembly.evidence_summary_answer_ask_entry import (
    EvidenceSummaryAnswerAskEntryRequest,
    normalize_evidence_summary_answer_ask_entry_request,
)
from product_application_assembly.evidence_summary_answer_ask_policy import (
    EvidenceSummaryAnswerAskRoutePolicyInput,
    build_evidence_summary_answer_ask_governance_precondition,
    build_evidence_summary_answer_ask_route_facts,
    evidence_summary_answer_ask_external_provider_selected,
)
from schemas.llm_invocation import (
    LlmInvocationRequest,
    LlmInvocationResult,
)


def test_ask_action_runs_initial_answer_and_returns_same_process_state() -> None:
    service = _FakeService(
        "The source describes public governed facts; see "
        "evidence://external-readonly/item/599."
    )
    action_input = _action_input("What does the source say?")
    bridge = build_evidence_summary_answer_ask_evidence_bridge_from_facts(
        (_ready_facts(),),
        request_id=action_input.request_id,
        question=action_input.question,
        fetch_request_id=None,
        readonly_refs_status="ready",
        external_readonly_fetch_performed=False,
        external_readonly_network_call_performed=False,
        external_network_call_performed=False,
    )

    result = run_evidence_summary_answer_ask_initial_action(
        action_input,
        evidence_bridge_builder=lambda _: bridge,
        llm_service_resolver=lambda _: {
            "service": service,
            "blocking_reasons": (),
            "warnings": (),
        },
    )

    assert result.exit_code == 0
    assert result.output["status"] == "success"
    assert result.output["answer_run_ref"].startswith(
        "evidence-summary-answer-run://"
    )
    assert result.output["answer_trace_ref"].startswith(
        "evidence-summary-answer-trace://"
    )
    assert service.requests[0].metadata["service_ref"] == (
        "service://product-application-assembly/external-readonly-ask/action"
    )
    assert result.next_state is not None
    assert result.next_state.service is service
    assert result.next_state.follow_up_seed is not None


def test_ask_action_runs_follow_up_from_same_process_state() -> None:
    service = _FakeService(
        "The source describes public governed facts; see "
        "evidence://external-readonly/item/599.",
        "The same evidence remains the basis for the follow-up answer; see "
        "evidence://external-readonly/item/599.",
    )
    action_input = _action_input("What does the source say?")
    bridge = build_evidence_summary_answer_ask_evidence_bridge_from_facts(
        (_ready_facts(),),
        request_id=action_input.request_id,
        question=action_input.question,
        fetch_request_id=None,
        readonly_refs_status="ready",
        external_readonly_fetch_performed=False,
        external_readonly_network_call_performed=False,
        external_network_call_performed=False,
    )
    initial = run_evidence_summary_answer_ask_initial_action(
        action_input,
        evidence_bridge_builder=lambda _: bridge,
        llm_service_resolver=lambda _: {
            "service": service,
            "blocking_reasons": (),
            "warnings": (),
        },
    )

    assert initial.next_state is not None
    follow_up = run_evidence_summary_answer_ask_follow_up_action(
        initial.next_state,
        "Can it support a follow-up?",
    )

    assert follow_up.exit_code == 0
    assert follow_up.output["status"] == "success"
    assert follow_up.output["follow_up"] is True
    assert follow_up.output["follow_up_turn_index"] == 1
    assert follow_up.next_state is not None
    assert follow_up.next_state.follow_up_turn_index == 1
    assert len(service.requests) == 2


def test_ask_policy_builds_route_and_governance_facts_outside_cli() -> None:
    route_facts = build_evidence_summary_answer_ask_route_facts(
        EvidenceSummaryAnswerAskRoutePolicyInput(
            model_name="deepseek/deepseek-chat",
            provider_profile_ref="deepseek_gated",
            model_profile_ref="deepseek_v4_flash",
            output_governance_profile_ref="evidence_summary_answer",
            source="test",
            product_path="external_readonly_ask_product_path",
        )
    )
    governance = build_evidence_summary_answer_ask_governance_precondition(
        approval_ref="approval://test/ask",
        command="cognition external-readonly ask",
        product_path="external_readonly_ask_product_path",
        source="test",
    )

    assert route_facts.metadata["backend_provider"] == "deepseek"
    assert route_facts.metadata["route_kind"] == "adk_litellm_openai_compatible"
    assert governance.allowed is True
    assert governance.governance_decision_ref == "approval://test/ask"
    assert evidence_summary_answer_ask_external_provider_selected(
        model_name=route_facts.model_name,
        provider_profile_ref="deepseek_gated",
        model_profile_ref="deepseek_v4_flash",
        output_governance_profile_ref="evidence_summary_answer",
    )


def test_ask_entry_request_normalizer_supplies_shared_refs_outside_channels() -> None:
    cli_request = normalize_evidence_summary_answer_ask_entry_request(
        EvidenceSummaryAnswerAskEntryRequest(
            request_id="external-readonly-ask-request://cli/ask",
            source_url="https://example.com",
            evidence_paths=(),
            question="这份资料主要说明什么？",
            input_channel="cli",
        )
    )
    console_request = normalize_evidence_summary_answer_ask_entry_request(
        EvidenceSummaryAnswerAskEntryRequest(
            request_id="external-readonly-ask-request://product-console/ask",
            source_url="https://example.com",
            evidence_paths=(),
            question="这份资料主要说明什么？",
            input_channel="product_console",
        )
    )

    assert cli_request.envelope_ref == "evidence://external-readonly/envelope/cli-ask"
    assert cli_request.evidence_ref == "evidence://external-readonly/item/cli-ask"
    assert cli_request.controlled_output_ref == "outputs/external-readonly/cli-ask.json"
    assert cli_request.sanitized_evidence_ref == "evidence://external-readonly/cli-ask"
    assert cli_request.governance_summary_ref == "summary://external-readonly/cli-ask"
    assert console_request.envelope_ref == (
        "evidence://external-readonly/envelope/product-console-ask"
    )
    assert console_request.evidence_ref == (
        "evidence://external-readonly/item/product-console-ask"
    )
    assert console_request.controlled_output_ref == (
        "outputs/external-readonly/product-console-ask.json"
    )
    assert console_request.sanitized_evidence_ref == (
        "evidence://external-readonly/product-console-ask"
    )
    assert console_request.governance_summary_ref == (
        "summary://external-readonly/product-console-ask"
    )


class _FakeService:
    def __init__(self, *answers: str) -> None:
        self.answers = answers
        self.requests: list[LlmInvocationRequest] = []

    def invoke(self, request: LlmInvocationRequest) -> LlmInvocationResult:
        answer = self.answers[min(len(self.requests), len(self.answers) - 1)]
        self.requests.append(request)
        return LlmInvocationResult(
            request_id=request.request_id,
            route_facts=request.route_facts,
            governance_precondition=request.governance_precondition,
            call_attempted=True,
            call_allowed=True,
            runtime_call_performed=True,
            success=True,
            response_non_empty=True,
            sanitized_response_length=len(answer),
            sanitized_response_preview=answer[:120],
            failure_type=None,
            metadata={"sanitized_response_display": answer},
        )


def _action_input(question: str) -> EvidenceSummaryAnswerAskActionInput:
    return EvidenceSummaryAnswerAskActionInput(
        request_id="external-readonly-ask-request://test/ask",
        source_url="https://example.com",
        evidence_paths=(),
        question=question,
        route_facts=build_evidence_summary_answer_ask_route_facts(
            EvidenceSummaryAnswerAskRoutePolicyInput(
                model_name="ollama/gemma4-pro:latest",
                provider_profile_ref="local_ollama",
                source="test",
                product_path="external_readonly_ask_product_path",
            )
        ),
        governance_precondition=build_evidence_summary_answer_ask_governance_precondition(
            approval_ref="approval://test/ask",
            command="cognition external-readonly ask",
            product_path="external_readonly_ask_product_path",
            source="test",
        ),
        model_name="ollama/gemma4-pro:latest",
        input_channel="test",
    )


def _ready_facts() -> dict[str, object]:
    fact = "The source describes public governed facts."
    content_hash = hashlib.sha256(fact.encode()).hexdigest()
    return {
        "payload_type": "external_readonly_governed_summary_facts",
        "payload_version": "external_readonly_governed_summary_facts_v1",
        "status": "ready",
        "evidence_ref": "evidence://external-readonly/item/599",
        "evidence_output_path": "outputs/external-readonly/599.json",
        "source_url_host": "example.com",
        "source_url_scheme": "https",
        "reference_review_ready": True,
        "allowed_for_model_context": True,
        "evidence_written": True,
        "content_hash": content_hash,
        "facts": [
            {
                "fact_ref": "external-readonly-governed-summary-fact://599-1",
                "fact_text": fact,
                "fact_index": 1,
                "evidence_ref": "evidence://external-readonly/item/599",
                "source_url_host": "example.com",
                "content_hash": content_hash,
            }
        ],
        "fact_count": 1,
        "total_fact_chars": len(fact),
        "blocking_reasons": [],
        "warnings": [],
        "generation_policy_ref": (
            "policy://external-readonly/governed-summary-facts/minimal-v1"
        ),
        "metadata": {"source_package": "external_readonly"},
    }
