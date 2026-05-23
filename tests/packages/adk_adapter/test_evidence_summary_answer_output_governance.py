from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import adk_adapter.evidence_summary_answer_output_governance as output_governance_module
from adk_adapter import (
    ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_NO_OUTPUT_SCHEMA,
    ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_OUTPUT_SCHEMA,
    ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_KEY,
    AdkEvidenceSummaryAnswerDraft,
    AdkEvidenceSummaryAnswerOutputGovernanceOptions,
    AdkEvidenceSummaryAnswerOutputGovernanceProbe,
    build_evidence_summary_answer_output_governance_agent,
)
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from product_application_assembly import (
    build_evidence_summary_answer_context,
    build_evidence_summary_answer_result_from_llm_invocation_result,
)
from schemas.llm_invocation import (
    LlmGovernancePrecondition,
    LlmInvocationFailureType,
    LlmInvocationRequest,
    LlmInvocationResult,
)
from schemas.model_routing import ModelRouteFacts


def test_output_governance_agent_declares_schema_callback_and_output_key() -> None:
    agent = build_evidence_summary_answer_output_governance_agent(
        model=_QueuedNoLiveLlm(
            model="adk-no-live/evidence-summary-answer",
            responses=("unused",),
        )
    )

    assert type(agent).__name__ == "LlmAgent"
    assert agent.output_schema is AdkEvidenceSummaryAnswerDraft
    assert agent.output_key == ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_KEY
    assert agent.after_model_callback is not None


def test_output_governance_probe_success_draft_returns_sanitized_result() -> None:
    model = _QueuedNoLiveLlm(
        model="adk-no-live/evidence-summary-answer",
        responses=(
            (
                '{"answer":"该网页说明 Example Domain 用于文档示例，'
                '证据见 evidence://external-readonly/item/cli-fetch。",'
                '"evidence_refs":["evidence://external-readonly/item/cli-fetch"],'
                '"status":"success"}'
            ),
        ),
    )
    probe = AdkEvidenceSummaryAnswerOutputGovernanceProbe(
        options=AdkEvidenceSummaryAnswerOutputGovernanceOptions(
            model=model,
            response_preview_limit=300,
        )
    )

    result = probe.invoke(_request())

    assert isinstance(result, LlmInvocationResult)
    assert result.failure_type is None
    assert result.success is True
    assert result.call_attempted is True
    assert result.runtime_call_performed is True
    assert result.sanitized_response_preview is not None
    assert result.sanitized_response_preview.startswith("该网页说明")
    assert result.metadata["adk_native_output_governance_probe"] is True
    assert result.metadata["adk_runner_used"] is True
    assert result.metadata["output_governance_mode"] == (
        ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_OUTPUT_SCHEMA
    )
    assert result.metadata["output_schema_name"] == "AdkEvidenceSummaryAnswerDraft"
    assert result.metadata["output_key"] == ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_KEY
    assert result.metadata["after_model_callback_invoked"] is True
    assert result.metadata["answer_quality_passed"] is True
    assert result.metadata["draft_schema_parsed"] is True
    assert result.metadata["repair_retry_attempted"] is False
    assert result.metadata["options"]["custom_model_injected"] is True
    assert "sanitized_response_display" in result.metadata
    assert _metadata_has_no_raw_payload_markers(result.metadata)
    assert model.calls == 1


def test_output_governance_probe_contains_output_schema_validation_hard_fail() -> None:
    model = _QueuedNoLiveLlm(
        model="adk-no-live/evidence-summary-answer",
        responses=("not valid json",),
    )
    probe = AdkEvidenceSummaryAnswerOutputGovernanceProbe(
        options=AdkEvidenceSummaryAnswerOutputGovernanceOptions(
            model=model,
            response_preview_limit=300,
        )
    )

    invocation_result = probe.invoke(_request())
    answer_result = build_evidence_summary_answer_result_from_llm_invocation_result(
        _answer_context(),
        invocation_result,
        generation_policy_facts={"allow_answer_generation_success": True},
    )

    assert invocation_result.success is False
    assert invocation_result.failure_type == (
        LlmInvocationFailureType.OUTPUT_SCHEMA_VALIDATION_FAILURE
    )
    assert invocation_result.call_attempted is True
    assert invocation_result.call_allowed is True
    assert invocation_result.runtime_call_performed is True
    assert invocation_result.error_message_sanitized == (
        "output_schema_validation_failure"
    )
    assert invocation_result.metadata["exception_classification"] == (
        "adk_output_schema_validation_exception"
    )
    assert invocation_result.metadata["raw_boundary_preserved"] is True
    assert invocation_result.metadata["draft_schema_parsed"] is False
    assert answer_result.status == "failed"
    assert answer_result.blocking_reasons == [
        "llm_invocation_failure:output_schema_validation_failure"
    ]
    assert _metadata_has_no_raw_payload_markers(invocation_result.metadata)
    assert model.calls == 1


def test_output_governance_probe_repairs_visible_reasoning_once() -> None:
    model = _QueuedNoLiveLlm(
        model="adk-no-live/evidence-summary-answer",
        responses=(
            '{"thought":"I should explain the answer first."}',
            (
                '{"answer":"这个网页说明 Example Domain 只用于文档示例，'
                '证据见 evidence://external-readonly/item/cli-fetch。",'
                '"evidence_refs":["evidence://external-readonly/item/cli-fetch"],'
                '"status":"success"}'
            ),
            '{"answer":"should not be called"}',
        ),
    )
    probe = AdkEvidenceSummaryAnswerOutputGovernanceProbe(
        options=AdkEvidenceSummaryAnswerOutputGovernanceOptions(
            model=model,
            response_preview_limit=300,
        )
    )

    result = probe.invoke(_request())

    assert result.failure_type is None
    assert result.success is True
    assert result.metadata["repair_retry_attempted"] is True
    assert result.metadata["repair_retry_performed"] is True
    assert result.metadata["repair_retry_failed"] is False
    assert result.metadata["repair_retry_max_once"] is True
    assert result.metadata["repair_retry_reason"] == (
        "evidence_summary_answer_quality_contract_violation"
    )
    assert result.metadata["answer_quality_passed"] is True
    assert result.metadata["draft_schema_parsed"] is True
    assert "Example Domain" in result.metadata["sanitized_response_display"]
    assert model.calls == 2


def test_output_governance_probe_repair_failed_stays_quality_violation_in_result_mapper() -> None:
    model = _QueuedNoLiveLlm(
        model="adk-no-live/evidence-summary-answer",
        responses=(
            '{"thought":"I should explain the answer first."}',
            '{"thought":"I still explain the hidden reasoning."}',
            '{"answer":"should not be called"}',
        ),
    )
    probe = AdkEvidenceSummaryAnswerOutputGovernanceProbe(
        options=AdkEvidenceSummaryAnswerOutputGovernanceOptions(
            model=model,
            response_preview_limit=300,
        )
    )

    invocation_result = probe.invoke(_request())
    answer_result = build_evidence_summary_answer_result_from_llm_invocation_result(
        _answer_context(),
        invocation_result,
        generation_policy_facts={"allow_answer_generation_success": True},
    )

    assert invocation_result.success is True
    assert invocation_result.metadata["repair_retry_attempted"] is True
    assert invocation_result.metadata["repair_retry_performed"] is True
    assert invocation_result.metadata["repair_retry_failed"] is True
    assert invocation_result.metadata["answer_quality_passed"] is False
    assert model.calls == 2
    assert answer_result.status == "failed"
    assert answer_result.blocking_reasons == ["llm_answer_quality_contract_violation"]


def test_no_output_schema_probe_success_returns_sanitized_result() -> None:
    model = _QueuedNoLiveLlm(
        model="adk-no-live/evidence-summary-answer",
        responses=(
            (
                "该网页说明 Example Domain 用于文档示例，证据见 "
                "evidence://external-readonly/item/cli-fetch。"
            ),
        ),
    )
    probe = AdkEvidenceSummaryAnswerOutputGovernanceProbe(
        options=AdkEvidenceSummaryAnswerOutputGovernanceOptions(
            model=model,
            output_governance_mode=(
                ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_NO_OUTPUT_SCHEMA
            ),
            response_preview_limit=300,
        )
    )

    invocation_result = probe.invoke(_request())
    answer_result = build_evidence_summary_answer_result_from_llm_invocation_result(
        _answer_context(),
        invocation_result,
        generation_policy_facts={"allow_answer_generation_success": True},
    )

    assert invocation_result.success is True
    assert invocation_result.metadata["output_governance_mode"] == (
        ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_NO_OUTPUT_SCHEMA
    )
    assert invocation_result.metadata["output_schema_name"] is None
    assert invocation_result.metadata["output_key"] is None
    assert invocation_result.metadata["after_model_callback_invoked"] is True
    assert invocation_result.metadata["draft_schema_parsed"] is False
    assert invocation_result.metadata["answer_quality_passed"] is True
    assert answer_result.status == "success"
    assert answer_result.answer is not None
    assert answer_result.evidence_refs_used
    assert _metadata_has_no_raw_payload_markers(invocation_result.metadata)
    assert model.calls == 1


def test_no_output_schema_probe_accepts_answer_scoped_transformation() -> None:
    model = _QueuedNoLiveLlm(
        model="adk-no-live/evidence-summary-answer",
        responses=(
            (
                "This summary says Example Domain is for documentation examples "
                "and should not be used in operations."
            ),
        ),
    )
    probe = AdkEvidenceSummaryAnswerOutputGovernanceProbe(
        options=AdkEvidenceSummaryAnswerOutputGovernanceOptions(
            model=model,
            output_governance_mode=(
                ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_NO_OUTPUT_SCHEMA
            ),
            response_preview_limit=300,
        )
    )

    invocation_result = probe.invoke(
        _request(metadata=_answer_scoped_transformation_metadata())
    )

    assert invocation_result.success is True
    assert invocation_result.metadata["answer_quality_passed"] is True
    assert "This summary says Example Domain" in invocation_result.metadata[
        "sanitized_response_display"
    ]
    assert _metadata_has_no_raw_payload_markers(invocation_result.metadata)
    assert model.calls == 1


def test_no_output_schema_probe_rejects_jsonish_answer_in_result_mapper() -> None:
    model = _QueuedNoLiveLlm(
        model="adk-no-live/evidence-summary-answer",
        responses=(
            (
                '{"answer":"该网页说明 Example Domain 用于文档示例，'
                '证据见 evidence://external-readonly/item/cli-fetch。"}'
            ),
        ),
    )
    probe = AdkEvidenceSummaryAnswerOutputGovernanceProbe(
        options=AdkEvidenceSummaryAnswerOutputGovernanceOptions(
            model=model,
            output_governance_mode=(
                ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_NO_OUTPUT_SCHEMA
            ),
            max_repair_attempts=0,
            response_preview_limit=300,
        )
    )

    invocation_result = probe.invoke(_request())
    answer_result = build_evidence_summary_answer_result_from_llm_invocation_result(
        _answer_context(),
        invocation_result,
        generation_policy_facts={"allow_answer_generation_success": True},
    )

    assert invocation_result.success is True
    assert invocation_result.metadata["output_governance_mode"] == (
        ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_NO_OUTPUT_SCHEMA
    )
    assert invocation_result.metadata["answer_quality_passed"] is False
    assert invocation_result.metadata["draft_schema_parsed"] is False
    assert invocation_result.metadata["repair_retry_attempted"] is False
    assert answer_result.status == "failed"
    assert answer_result.blocking_reasons == ["llm_answer_quality_contract_violation"]
    assert model.calls == 1


def test_no_output_schema_output_mapper_ignores_yielded_user_message() -> None:
    run_result = SimpleNamespace(
        runtime_events=[
            _runtime_event(
                author="evidence_summary_answer_output_governance_probe",
                role="model",
                text="这个网页主要说明 Example Domain 用于文档示例。",
            ),
            _runtime_event(
                author="user",
                role="user",
                text="Answer the governed evidence question. User question: ...",
            ),
        ]
    )

    output_text = output_governance_module._attempt_output_text(
        run_result,
        draft=None,
    )

    assert output_text == "这个网页主要说明 Example Domain 用于文档示例。"


def test_output_governance_probe_sanitizes_provider_exception() -> None:
    model = _FailingNoLiveLlm(model="adk-no-live/evidence-summary-answer")
    probe = AdkEvidenceSummaryAnswerOutputGovernanceProbe(
        options=AdkEvidenceSummaryAnswerOutputGovernanceOptions(
            model=model,
            output_governance_mode=(
                ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_NO_OUTPUT_SCHEMA
            ),
        )
    )

    invocation_result = probe.invoke(_request())
    answer_result = build_evidence_summary_answer_result_from_llm_invocation_result(
        _answer_context(),
        invocation_result,
        generation_policy_facts={"allow_answer_generation_success": True},
    )

    assert invocation_result.success is False
    assert invocation_result.failure_type == LlmInvocationFailureType.LIVE_CALL_FAILURE
    assert invocation_result.error_message_sanitized == "provider_invocation_failed"
    assert invocation_result.call_attempted is True
    assert invocation_result.runtime_call_performed is True
    assert invocation_result.metadata["exception_classification"] == (
        "adk_provider_invocation_exception"
    )
    assert invocation_result.metadata["raw_boundary_preserved"] is True
    assert "sk-test" not in str(invocation_result.model_dump(mode="json"))
    assert "[masked-tail]" not in str(invocation_result.model_dump(mode="json"))
    assert answer_result.status == "failed"
    assert answer_result.blocking_reasons == [
        "llm_invocation_failure:live_call_failure"
    ]


def test_output_governance_probe_rejects_unsupported_interaction_without_model_call() -> None:
    model = _QueuedNoLiveLlm(
        model="adk-no-live/evidence-summary-answer",
        responses=("unused",),
    )
    probe = AdkEvidenceSummaryAnswerOutputGovernanceProbe(
        options=AdkEvidenceSummaryAnswerOutputGovernanceOptions(model=model)
    )

    result = probe.invoke(
        _request(metadata={"interaction_mode": "cli_chat"})
    )

    assert result.failure_type == LlmInvocationFailureType.UNSUPPORTED_API_FAILURE
    assert result.call_attempted is False
    assert result.runtime_call_performed is False
    assert model.calls == 0


class _QueuedNoLiveLlm(BaseLlm):
    responses: tuple[str, ...]
    calls: int = 0

    @classmethod
    def supported_models(cls) -> list[str]:
        return [r"adk-no-live/.+"]

    async def generate_content_async(self, llm_request: Any, stream: bool = False):
        del llm_request, stream
        index = min(self.calls, len(self.responses) - 1)
        self.calls += 1
        yield LlmResponse(
            model_version=self.model,
            content=types.Content(
                role="model",
                parts=[types.Part(text=self.responses[index])],
            ),
            partial=False,
            turn_complete=True,
            custom_metadata={
                "no_live_execution": True,
                "source": "adk_adapter.test.evidence_summary_answer_output_governance",
            },
        )


class _FailingNoLiveLlm(BaseLlm):
    @classmethod
    def supported_models(cls) -> list[str]:
        return [r"adk-no-live/.+"]

    async def generate_content_async(self, llm_request: Any, stream: bool = False):
        del llm_request, stream
        raise RuntimeError("provider error for api key sk-test and [masked-tail]")
        yield  # pragma: no cover


def _request(
    metadata: dict[str, object] | None = None,
) -> LlmInvocationRequest:
    return LlmInvocationRequest(
        request_id="external-readonly-ask-request://unit/llm",
        route_facts=_route_facts(),
        governance_precondition=LlmGovernancePrecondition(
            allowed=True,
            reason="unit_test_allowed",
            decision="allow",
            governance_decision_ref="approval://unit/evidence-summary-answer",
        ),
        prompt_ref="prompt://unit/evidence-summary-answer",
        prompt_preview_sanitized="这个网页主要说明了什么？",
        metadata=metadata or _request_metadata(),
    )


def _request_metadata() -> dict[str, object]:
    return {
        "interaction_mode": "evidence_summary_answer_generation",
        "evidence_summary_answer_context": {
            "user_question": "这个网页主要说明了什么？",
            "summary_facts": [
                (
                    "Example Domain is for use in documentation examples "
                    "without needing permission."
                )
            ],
            "evidence_refs": [
                {
                    "ref": "evidence://external-readonly/item/cli-fetch",
                    "kind": "external_readonly_evidence",
                    "purpose": "answer_context",
                }
            ],
            "answer_constraints": [
                "Write only the final user-facing natural language answer."
            ],
        },
    }


def _answer_scoped_transformation_metadata() -> dict[str, object]:
    return {
        "interaction_mode": "evidence_summary_answer_generation",
        "answer_scoped_transformation": True,
        "temporary_only": True,
        "durable_session": False,
        "memory_enabled": False,
        "evidence_summary_answer_context": {
            "user_question": "将该摘要翻译成英文",
            "summary_facts": [
                "这个页面说明 Example Domain 用于文档示例，不应在实际运营中使用。"
            ],
            "evidence_refs": [
                {
                    "ref": "answer-snapshot://chat/turn-003",
                    "kind": "chat_last_answer_snapshot",
                    "purpose": "answer_scoped_transformation",
                }
            ],
        },
    }


def _route_facts() -> ModelRouteFacts:
    return ModelRouteFacts(
        model_name="ollama/gemma4-pro:latest",
        provider="litellm",
        source="adk_adapter.test",
        metadata={
            "backend_provider": "ollama",
            "route_target": "ollama/gemma4-pro:latest",
            "route_kind": "adk_litellm",
        },
    )


def _runtime_event(*, author: str, role: str, text: str) -> SimpleNamespace:
    return SimpleNamespace(
        metadata={"author": author},
        payload={
            "content": {
                "role": role,
                "parts": [{"text": text}],
            }
        },
    )


def _answer_context():
    return build_evidence_summary_answer_context(
        request_id="external-readonly-ask-request://unit/context",
        user_question="这个网页主要说明了什么？",
        digests=[
            {
                "product": "evidence_summary_answer",
                "payload_type": "governed_evidence_digest",
                "payload_version": "governed_evidence_digest_v1",
                "digest_id": "digest-unit",
                "digest_ref": "governed-evidence-digest://unit",
                "evidence_ref": "evidence://external-readonly/item/cli-fetch",
                "evidence_output_ref": "outputs/external-readonly/unit.json",
                "source_url_host": "example.com",
                "source_url_scheme": "https",
                "runtime_status": "governed_summary_facts_ready",
                "status": "ready",
                "reference_review_ready": True,
                "allowed_for_model_context": True,
                "evidence_written": True,
                "content_hash": "a" * 64,
                "total_excerpt_chars": 90,
                "raw_boundary_flags": {},
                "blocking_reasons": [],
                "warnings": [],
                "summary_facts": [
                    (
                        "Example Domain is for use in documentation examples "
                        "without needing permission."
                    )
                ],
                "topic_labels": ["example"],
                "risk_labels": [],
                "answerability": "answerable",
                "digest_generation_policy_ref": (
                    "policy://evidence-summary-answer/digest-generation-v1"
                ),
                "digest_budget": 4000,
                "metadata": {"source": "adk_adapter.test"},
            }
        ],
    )


def _metadata_has_no_raw_payload_markers(value: Any) -> bool:
    text = str(value)
    forbidden = (
        "raw_provider_response",
        "raw_response",
        "provider_response",
        "messages",
        "system_prompt",
        "secret",
        "token",
    )
    return not any(marker in text for marker in forbidden)
