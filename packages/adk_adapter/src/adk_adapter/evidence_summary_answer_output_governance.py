"""ADK-native output governance probe for evidence-summary-answer."""

from __future__ import annotations

import asyncio
import contextlib
import io
import json
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from behavior_contracts.evidence_summary_answer import (
    validate_evidence_summary_answer_answer_quality,
)
from behavior_contracts.llm_invocation import GovernedLlmInvocationService
from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticValidationError
from pydantic_core import ValidationError as PydanticCoreValidationError
from schemas.llm_invocation import (
    LlmInvocationFailureType,
    LlmInvocationRequest,
    LlmInvocationResult,
)
from schemas.model_routing import ModelRouteFacts

from adk_adapter.agent_service import (
    AdkAgentServiceAdapter,
    AdkAgentShellOptions,
    AdkNoLiveLlm,
)


ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_BOUNDARY = (
    "adk_adapter.evidence_summary_answer_output_governance"
)
ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_KEY = "evidence_summary_answer_draft"
ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_OUTPUT_SCHEMA = (
    "output_schema"
)
ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_NO_OUTPUT_SCHEMA = (
    "no_output_schema"
)
ADK_EVIDENCE_SUMMARY_ANSWER_REPAIR_REASON = (
    "evidence_summary_answer_quality_contract_violation"
)
DEFAULT_RESPONSE_PREVIEW_LIMIT = 120
_ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODES = frozenset(
    {
        ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_OUTPUT_SCHEMA,
        ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_NO_OUTPUT_SCHEMA,
    }
)
_OUTPUT_SCHEMA_VALIDATION_EXCEPTIONS = (
    PydanticValidationError,
    PydanticCoreValidationError,
)


class AdkEvidenceSummaryAnswerDraft(BaseModel):
    """Adapter-local internal draft schema for ADK-native answer generation."""

    answer: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    insufficient_evidence_reason: str | None = None
    status: str | None = None


@dataclass(frozen=True)
class AdkEvidenceSummaryAnswerOutputGovernanceOptions:
    """Options for the ADK-native evidence-summary-answer probe."""

    model: Any | None = None
    model_name: str = "adk-no-live/evidence-summary-answer-output-governance"
    app_name: str = "cognition_engine_evidence_summary_answer_output_governance"
    user_id: str = "cognition-engine-adk-user"
    output_key: str = ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_KEY
    output_governance_mode: str = (
        ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_OUTPUT_SCHEMA
    )
    route_facts: ModelRouteFacts | None = None
    max_repair_attempts: int = 1
    response_preview_limit: int = DEFAULT_RESPONSE_PREVIEW_LIMIT
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class _AttemptResult:
    output_text: str
    answer_text: str | None
    quality_passed: bool
    quality_violation_count: int
    callback_invoked: bool
    callback_quality_passed: bool | None
    draft_schema_parsed: bool
    event_count: int
    error_count: int


class AdkEvidenceSummaryAnswerOutputGovernanceProbe(GovernedLlmInvocationService):
    """Run evidence-summary-answer generation through an ADK-native probe."""

    def __init__(
        self,
        *,
        options: AdkEvidenceSummaryAnswerOutputGovernanceOptions | None = None,
    ) -> None:
        self._options = options or AdkEvidenceSummaryAnswerOutputGovernanceOptions()

    def invoke(self, request: LlmInvocationRequest) -> LlmInvocationResult:
        """Return sanitized LLM invocation facts from the ADK-native probe."""

        started_at = time.monotonic()
        if not request.governance_precondition.allowed:
            return self._failed_result(
                request,
                failure_type=(
                    LlmInvocationFailureType.GOVERNANCE_NEEDS_EVIDENCE
                    if request.governance_precondition.decision == "need_evidence"
                    else LlmInvocationFailureType.GOVERNANCE_BLOCKED
                ),
                error_message_sanitized="governance precondition denied",
                latency_ms=_elapsed_ms(started_at),
                metadata={
                    "blocked_before_adapter_call": True,
                    "adk_native_output_governance_probe": True,
                },
            )

        if not _is_evidence_summary_answer_request(request):
            return self._failed_result(
                request,
                failure_type=LlmInvocationFailureType.UNSUPPORTED_API_FAILURE,
                error_message_sanitized="evidence_summary_answer_context is required",
                call_allowed=True,
                latency_ms=_elapsed_ms(started_at),
                metadata={
                    "unsupported_interaction_mode": True,
                    "adk_native_output_governance_probe": True,
                },
            )

        output_governance_mode = _normalize_output_governance_mode(
            self._options.output_governance_mode
        )
        if output_governance_mode is None:
            return self._failed_result(
                request,
                failure_type=LlmInvocationFailureType.UNSUPPORTED_API_FAILURE,
                error_message_sanitized="unsupported output governance mode",
                call_allowed=True,
                latency_ms=_elapsed_ms(started_at),
                metadata={
                    "unsupported_output_governance_mode": True,
                    "adk_native_output_governance_probe": True,
                },
            )

        try:
            first_attempt = self._run_attempt(
                request,
                repair_reason=None,
                previous_output_text=None,
                output_governance_mode=output_governance_mode,
            )
        except _OUTPUT_SCHEMA_VALIDATION_EXCEPTIONS as exc:
            if output_governance_mode == (
                ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_OUTPUT_SCHEMA
            ):
                return self._output_schema_validation_failed_result(
                    request,
                    latency_ms=_elapsed_ms(started_at),
                    exc=exc,
                    output_governance_mode=output_governance_mode,
                    repair_retry_attempted=False,
                )
            raise
        except Exception as exc:  # noqa: BLE001 - provider/ADK exceptions are external.
            return self._provider_invocation_failed_result(
                request,
                latency_ms=_elapsed_ms(started_at),
                exc=exc,
                output_governance_mode=output_governance_mode,
                repair_retry_attempted=False,
            )
        repair_attempted = False
        repair_performed = False
        repair_failed = False
        final_attempt = first_attempt

        if (
            not first_attempt.quality_passed
            and self._options.max_repair_attempts > 0
        ):
            repair_attempted = True
            try:
                repaired = self._run_attempt(
                    request,
                    repair_reason=ADK_EVIDENCE_SUMMARY_ANSWER_REPAIR_REASON,
                    previous_output_text=first_attempt.output_text,
                    output_governance_mode=output_governance_mode,
                )
            except _OUTPUT_SCHEMA_VALIDATION_EXCEPTIONS as exc:
                if output_governance_mode == (
                    ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_OUTPUT_SCHEMA
                ):
                    return self._output_schema_validation_failed_result(
                        request,
                        latency_ms=_elapsed_ms(started_at),
                        exc=exc,
                        output_governance_mode=output_governance_mode,
                        repair_retry_attempted=True,
                    )
                raise
            except Exception as exc:  # noqa: BLE001 - provider/ADK exceptions are external.
                return self._provider_invocation_failed_result(
                    request,
                    latency_ms=_elapsed_ms(started_at),
                    exc=exc,
                    output_governance_mode=output_governance_mode,
                    repair_retry_attempted=True,
                )
            repair_performed = True
            repair_failed = not repaired.quality_passed
            final_attempt = repaired

        output_text = final_attempt.answer_text or final_attempt.output_text
        metadata = {
            **self._safe_options_metadata(),
            "adapter_boundary": ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_BOUNDARY,
            "adk_native_output_governance_probe": True,
            "adk_runner_used": True,
            "output_governance_mode": output_governance_mode,
            "output_schema_name": (
                "AdkEvidenceSummaryAnswerDraft"
                if output_governance_mode
                == ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_OUTPUT_SCHEMA
                else None
            ),
            "output_key": (
                self._options.output_key
                if output_governance_mode
                == ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_OUTPUT_SCHEMA
                else None
            ),
            "after_model_callback_invoked": final_attempt.callback_invoked,
            "callback_quality_passed": final_attempt.callback_quality_passed,
            "answer_quality_passed": final_attempt.quality_passed,
            "answer_quality_violation_count": final_attempt.quality_violation_count,
            "draft_schema_parsed": final_attempt.draft_schema_parsed,
            "event_count": final_attempt.event_count,
            "error_count": final_attempt.error_count,
            "repair_retry_attempted": repair_attempted,
            "repair_retry_performed": repair_performed,
            "repair_retry_failed": repair_failed,
            "repair_retry_max_once": self._options.max_repair_attempts == 1,
        }
        if repair_attempted:
            metadata["repair_retry_reason"] = (
                ADK_EVIDENCE_SUMMARY_ANSWER_REPAIR_REASON
            )

        return self._success_result(
            request,
            output_text=output_text,
            latency_ms=_elapsed_ms(started_at),
            metadata=metadata,
        )

    def _run_attempt(
        self,
        request: LlmInvocationRequest,
        *,
        repair_reason: str | None,
        previous_output_text: str | None,
        output_governance_mode: str,
    ) -> _AttemptResult:
        callback_records: list[dict[str, Any]] = []
        agent = self._build_agent(
            callback_records,
            output_governance_mode=output_governance_mode,
        )
        adapter = AdkAgentServiceAdapter(
            agent=agent,
            app_name=self._options.app_name,
            user_id=self._options.user_id,
        )
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
            io.StringIO()
        ):
            run_result = asyncio.run(
                adapter.run_text_async(
                    text=_prompt_text(
                        request,
                        repair_reason=repair_reason,
                        previous_output_text=previous_output_text,
                        output_governance_mode=output_governance_mode,
                    ),
                    invocation_id=f"{request.request_id}/adk-native-output-governance",
                    yield_user_message=True,
                )
            )
        session = adapter.service_bundle.session_service.get_session_sync(
            session_id=run_result.session_id
        )
        draft = _attempt_draft(
            getattr(session, "state", {}),
            output_key=self._options.output_key,
            output_governance_mode=output_governance_mode,
        )
        output_text = _attempt_output_text(run_result, draft)
        answer_text = _answer_from_draft(draft) or output_text
        quality = validate_evidence_summary_answer_answer_quality(answer_text)
        callback_record = callback_records[-1] if callback_records else {}
        return _AttemptResult(
            output_text=output_text,
            answer_text=answer_text,
            quality_passed=quality.passed,
            quality_violation_count=len(quality.violations),
            callback_invoked=bool(callback_records),
            callback_quality_passed=callback_record.get("quality_passed"),
            draft_schema_parsed=draft is not None,
            event_count=len(run_result.events),
            error_count=len(run_result.errors),
        )

    def _build_agent(
        self,
        callback_records: list[dict[str, Any]],
        *,
        output_governance_mode: str,
    ) -> Any:
        from google.adk.agents import Agent

        kwargs: dict[str, Any] = {}
        if (
            output_governance_mode
            == ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_OUTPUT_SCHEMA
        ):
            kwargs["output_schema"] = AdkEvidenceSummaryAnswerDraft
            kwargs["output_key"] = self._options.output_key

        return Agent(
            name="evidence_summary_answer_output_governance_probe",
            model=self._model(),
            instruction=_agent_instruction(output_governance_mode),
            after_model_callback=_after_model_callback(
                callback_records,
                output_governance_mode=output_governance_mode,
            ),
            mode="chat",
            **kwargs,
        )

    def _model(self) -> Any:
        if self._options.model is not None:
            return self._options.model
        return AdkNoLiveLlm(
            model=self._options.model_name,
            response_text=(
                '{"answer":"No-live evidence summary answer completed.",'
                '"evidence_refs":[],"status":"success"}'
            ),
        )

    def _success_result(
        self,
        request: LlmInvocationRequest,
        *,
        output_text: str,
        latency_ms: int,
        metadata: dict[str, Any],
    ) -> LlmInvocationResult:
        sanitized_output = _normalize_output_text(output_text)
        return LlmInvocationResult(
            request_id=request.request_id,
            route_facts=self._result_route_facts(request),
            governance_precondition=request.governance_precondition,
            call_attempted=True,
            call_allowed=True,
            runtime_call_performed=True,
            success=True,
            response_non_empty=bool(sanitized_output),
            sanitized_response_length=len(sanitized_output),
            sanitized_response_preview=_preview(
                sanitized_output,
                limit=DEFAULT_RESPONSE_PREVIEW_LIMIT,
            ),
            latency_ms=latency_ms,
            failure_type=None,
            metadata={
                **metadata,
                **_display_response_metadata(
                    sanitized_output,
                    limit=self._options.response_preview_limit,
                ),
            },
        )

    def _failed_result(
        self,
        request: LlmInvocationRequest,
        *,
        failure_type: LlmInvocationFailureType,
        error_message_sanitized: str,
        call_attempted: bool = False,
        call_allowed: bool = False,
        runtime_call_performed: bool = False,
        latency_ms: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> LlmInvocationResult:
        return LlmInvocationResult(
            request_id=request.request_id,
            route_facts=self._result_route_facts(request),
            governance_precondition=request.governance_precondition,
            call_attempted=call_attempted,
            call_allowed=call_allowed,
            runtime_call_performed=runtime_call_performed,
            success=False,
            response_non_empty=False,
            latency_ms=latency_ms,
            failure_type=failure_type,
            error_message_sanitized=_sanitize_error(error_message_sanitized),
            metadata={
                **self._safe_options_metadata(),
                "adapter_boundary": ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_BOUNDARY,
                **(metadata or {}),
            },
        )

    def _output_schema_validation_failed_result(
        self,
        request: LlmInvocationRequest,
        *,
        latency_ms: int,
        exc: Exception,
        output_governance_mode: str,
        repair_retry_attempted: bool,
    ) -> LlmInvocationResult:
        return self._failed_result(
            request,
            failure_type=LlmInvocationFailureType.OUTPUT_SCHEMA_VALIDATION_FAILURE,
            error_message_sanitized="output_schema_validation_failure",
            call_attempted=True,
            call_allowed=True,
            runtime_call_performed=True,
            latency_ms=latency_ms,
            metadata={
                "adapter_boundary": ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_BOUNDARY,
                "adk_native_output_governance_probe": True,
                "adk_runner_used": True,
                "output_governance_mode": output_governance_mode,
                "output_schema_name": "AdkEvidenceSummaryAnswerDraft",
                "output_key": self._options.output_key,
                "exception_type": type(exc).__name__,
                "exception_classification": (
                    "adk_output_schema_validation_exception"
                ),
                "after_model_callback_invoked": None,
                "callback_quality_passed": None,
                "answer_quality_passed": False,
                "draft_schema_parsed": False,
                "repair_retry_attempted": repair_retry_attempted,
                "repair_retry_performed": False,
                "repair_retry_failed": repair_retry_attempted,
                "repair_retry_max_once": self._options.max_repair_attempts == 1,
                "raw_boundary_preserved": True,
            },
        )

    def _provider_invocation_failed_result(
        self,
        request: LlmInvocationRequest,
        *,
        latency_ms: int,
        exc: Exception,
        output_governance_mode: str,
        repair_retry_attempted: bool,
    ) -> LlmInvocationResult:
        return self._failed_result(
            request,
            failure_type=LlmInvocationFailureType.LIVE_CALL_FAILURE,
            error_message_sanitized="provider_invocation_failed",
            call_attempted=True,
            call_allowed=True,
            runtime_call_performed=True,
            latency_ms=latency_ms,
            metadata={
                "adapter_boundary": ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_BOUNDARY,
                "adk_native_output_governance_probe": True,
                "adk_runner_used": True,
                "output_governance_mode": output_governance_mode,
                "exception_type": type(exc).__name__,
                "exception_classification": "adk_provider_invocation_exception",
                "after_model_callback_invoked": None,
                "callback_quality_passed": None,
                "answer_quality_passed": False,
                "draft_schema_parsed": False,
                "repair_retry_attempted": repair_retry_attempted,
                "repair_retry_performed": False,
                "repair_retry_failed": repair_retry_attempted,
                "repair_retry_max_once": self._options.max_repair_attempts == 1,
                "raw_boundary_preserved": True,
            },
        )

    def _safe_options_metadata(self) -> dict[str, Any]:
        return {
            "options": {
                "options_type": (
                    "adk_adapter.evidence_summary_answer_output_governance."
                    "AdkEvidenceSummaryAnswerOutputGovernanceOptions"
                ),
                "model_name": self._options.model_name,
                "app_name": self._options.app_name,
                "output_governance_mode": self._options.output_governance_mode,
                "route_facts_override_present": self._options.route_facts is not None,
                "route_model_name": (
                    self._options.route_facts.model_name
                    if self._options.route_facts is not None
                    else self._options.model_name
                ),
                "max_repair_attempts": self._options.max_repair_attempts,
                "response_preview_limit": self._options.response_preview_limit,
                "custom_model_injected": self._options.model is not None,
                "metadata_keys": sorted(self._options.metadata),
            }
        }

    def _result_route_facts(self, request: LlmInvocationRequest) -> ModelRouteFacts:
        return self._options.route_facts or request.route_facts


def build_evidence_summary_answer_output_governance_agent(
    *,
    model: Any,
    output_key: str = ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_KEY,
) -> Any:
    """Build the ADK LlmAgent used by the output governance probe."""

    from google.adk.agents import Agent

    callback_records: list[dict[str, Any]] = []
    return Agent(
        name="evidence_summary_answer_output_governance_probe",
        model=model,
        instruction=(
            "Return an evidence-summary-answer internal draft. "
            "The draft answer must be final user-facing natural language."
        ),
        output_schema=AdkEvidenceSummaryAnswerDraft,
        output_key=output_key,
        after_model_callback=_after_model_callback(
            callback_records,
            output_governance_mode=(
                ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_OUTPUT_SCHEMA
            ),
        ),
        mode="chat",
    )


def _after_model_callback(
    callback_records: list[dict[str, Any]],
    *,
    output_governance_mode: str,
) -> Any:
    def callback(*, callback_context: Any, llm_response: Any) -> None:
        del callback_context
        output_text = _llm_response_text(llm_response)
        draft = (
            _draft_from_text(output_text)
            if output_governance_mode
            == ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_OUTPUT_SCHEMA
            else None
        )
        answer_text = _answer_from_draft(draft) or output_text
        quality = validate_evidence_summary_answer_answer_quality(answer_text)
        callback_records.append(
            {
                "quality_passed": quality.passed,
                "quality_violation_count": len(quality.violations),
                "draft_schema_parsed": draft is not None,
                "candidate_non_empty": bool(answer_text),
            }
        )
        return None

    return callback


def _is_evidence_summary_answer_request(request: LlmInvocationRequest) -> bool:
    return (
        request.metadata.get("interaction_mode")
        == "evidence_summary_answer_generation"
        and isinstance(request.metadata.get("evidence_summary_answer_context"), Mapping)
    )


def _prompt_text(
    request: LlmInvocationRequest,
    *,
    repair_reason: str | None,
    previous_output_text: str | None,
    output_governance_mode: str,
) -> str:
    context = request.metadata.get("evidence_summary_answer_context")
    if not isinstance(context, Mapping):
        return request.prompt_preview_sanitized or "Answer the governed evidence question."

    if (
        output_governance_mode
        == ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_OUTPUT_SCHEMA
    ):
        lines = [
            "Build an internal evidence-summary-answer draft.",
            "Return JSON that matches the configured output schema.",
            "The answer field must be final user-facing natural language.",
            "Do not put thought, analysis, reasoning, scratchpad, or debug fields in the answer.",
            "Use only governed summary facts and listed refs.",
            "User question:",
            _safe_fragment(context.get("user_question"))
            or request.prompt_preview_sanitized
            or "",
            "Summary facts:",
        ]
    else:
        lines = [
            "Answer the governed evidence question.",
            "Return only final user-facing natural language.",
            "Answer in the same language as the user question.",
            "If the user question is Chinese, answer in Chinese.",
            "Start directly with the answer content.",
            "Do not mention the user, question, prompt, instruction, request, or what you were asked to do.",
            "Do not start with phrases like '我们被问到', '我被要求', 'We are given', 'I was asked', or 'The prompt'.",
            "Do not output JSON, YAML, code fences, keys, wrappers, protocol fields, or debug fields.",
            "Do not output thought, analysis, reasoning, scratchpad, or internal notes.",
            "Use only governed summary facts and listed refs.",
            "For the current Chinese question, start with: 这个网页主要说明",
            "User question:",
            _safe_fragment(context.get("user_question"))
            or request.prompt_preview_sanitized
            or "",
            "Summary facts:",
        ]
    for index, fact in enumerate(_string_list(context.get("summary_facts")), start=1):
        lines.append(f"{index}. {fact}")
    refs = _ref_list(context.get("evidence_refs"))
    if refs:
        lines.append("Evidence refs:")
        lines.extend(refs)
    if repair_reason is not None:
        lines.extend(
            [
                "Repair required:",
                repair_reason,
                "Previous candidate preview:",
                _preview(_normalize_output_text(previous_output_text or ""), limit=240),
                "Repair instruction:",
                (
                    "Return only a valid draft whose answer is final natural language."
                    if output_governance_mode
                    == ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_OUTPUT_SCHEMA
                    else (
                        "Return only a direct final answer without JSON, visible "
                        "reasoning, prompt mentions, or meta framing."
                    )
                ),
            ]
        )
    return "\n".join(item for item in lines if item is not None)


def _agent_instruction(output_governance_mode: str) -> str:
    if (
        output_governance_mode
        == ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_OUTPUT_SCHEMA
    ):
        return (
            "Return an evidence-summary-answer internal draft. "
            "The draft answer must be final user-facing natural language."
        )
    return (
        "Return only the final evidence-summary-answer as user-facing natural "
        "language. Start directly with the answer content. Do not mention the "
        "user, question, prompt, instruction, request, or what you were asked "
        "to do. Answer in the same language as the user question. Do not use "
        "JSON, protocol fields, or visible reasoning."
    )


def _attempt_draft(
    state: Any,
    *,
    output_key: str,
    output_governance_mode: str,
) -> AdkEvidenceSummaryAnswerDraft | None:
    if (
        output_governance_mode
        != ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_OUTPUT_SCHEMA
    ):
        return None
    return _draft_from_session_state(state, output_key=output_key)


def _draft_from_session_state(
    state: Any,
    *,
    output_key: str,
) -> AdkEvidenceSummaryAnswerDraft | None:
    if not isinstance(state, Mapping):
        return None
    value = state.get(output_key)
    if value is None:
        return None
    try:
        return AdkEvidenceSummaryAnswerDraft.model_validate(value)
    except Exception:  # noqa: BLE001 - state is ADK-managed.
        return None


def _draft_from_text(value: str) -> AdkEvidenceSummaryAnswerDraft | None:
    normalized = _normalize_output_text(value)
    if not normalized.startswith(("{", "[")):
        return None
    try:
        data = json.loads(normalized)
    except json.JSONDecodeError:
        return None
    try:
        return AdkEvidenceSummaryAnswerDraft.model_validate(data)
    except Exception:  # noqa: BLE001 - model output is provider-controlled.
        return None


def _attempt_output_text(
    run_result: Any,
    draft: AdkEvidenceSummaryAnswerDraft | None,
) -> str:
    answer = _answer_from_draft(draft)
    if answer:
        return answer
    for event in reversed(getattr(run_result, "runtime_events", ())):
        content = event.payload.get("content") if isinstance(event.payload, dict) else None
        text = _content_text(content)
        if text:
            return text
    return ""


def _llm_response_text(llm_response: Any) -> str:
    return _content_text(getattr(llm_response, "content", None))


def _content_text(content: Any) -> str:
    parts = getattr(content, "parts", None)
    if parts is None and isinstance(content, Mapping):
        parts = content.get("parts")
    if not isinstance(parts, list | tuple):
        return ""
    texts: list[str] = []
    for part in parts:
        text = getattr(part, "text", None)
        if text is None and isinstance(part, Mapping):
            text = part.get("text")
        if isinstance(text, str) and text.strip():
            texts.append(text.strip())
    return _normalize_output_text(" ".join(texts))


def _answer_from_draft(draft: AdkEvidenceSummaryAnswerDraft | None) -> str | None:
    if draft is None or not isinstance(draft.answer, str):
        return None
    answer = _normalize_output_text(draft.answer)
    return answer or None


def _ref_list(value: Any) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    refs: list[str] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        ref = _safe_fragment(item.get("ref"))
        kind = _safe_fragment(item.get("kind")) or "unknown"
        if ref:
            refs.append(f"- {kind}: {ref}")
    return refs


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    return [item for raw in value if (item := _safe_fragment(raw))]


def _safe_fragment(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _normalize_output_text(value)


def _normalize_output_text(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def _preview(value: str, *, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[:limit].rstrip()


def _display_response_metadata(
    sanitized_output: str,
    *,
    limit: int,
) -> dict[str, str]:
    if limit <= DEFAULT_RESPONSE_PREVIEW_LIMIT or not sanitized_output:
        return {}
    return {"sanitized_response_display": _preview(sanitized_output, limit=limit)}


def _sanitize_error(value: str) -> str:
    sanitized = _normalize_output_text(value)
    for marker in (
        "raw_response",
        "raw_provider_response",
        "provider_response",
        "prompt",
        "messages",
        "secret",
        "token",
    ):
        sanitized = sanitized.replace(marker, "[redacted]")
    return _preview(sanitized, limit=240)


def _elapsed_ms(started_at: float) -> int:
    return max(0, int((time.monotonic() - started_at) * 1000))


def _normalize_output_governance_mode(value: str) -> str | None:
    normalized = str(value or "").strip()
    if normalized in _ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODES:
        return normalized
    return None


__all__ = [
    "ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_BOUNDARY",
    "ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_NO_OUTPUT_SCHEMA",
    "ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_GOVERNANCE_MODE_OUTPUT_SCHEMA",
    "ADK_EVIDENCE_SUMMARY_ANSWER_OUTPUT_KEY",
    "AdkEvidenceSummaryAnswerDraft",
    "AdkEvidenceSummaryAnswerOutputGovernanceOptions",
    "AdkEvidenceSummaryAnswerOutputGovernanceProbe",
    "build_evidence_summary_answer_output_governance_agent",
]
