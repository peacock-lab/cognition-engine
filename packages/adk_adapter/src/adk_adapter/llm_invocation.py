"""ADK adapter-local governed LLM invocation boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import json
import os
import re
import time
from typing import Any
from urllib.parse import urlparse

from behavior_contracts.llm_invocation import GovernedLlmInvocationService
from schemas.llm_invocation import (
    LlmInvocationFailureType,
    LlmInvocationRequest,
    LlmInvocationResult,
)


CLI_CHAT_PROMPT_PREFIX = (
    "你是认知系统的中文终端聊天助手。请根据以下上下文直接回应当前用户，"
    "语气自然、简洁、支持性强。必须只输出普通中文自然语言。"
    "当用户要求“直接输出方案”“继续”“展开”“全面展开”或类似指令时，"
    "不要反问用户要从哪里开始，必须承接上下文直接给出结构化回答；"
    "只有用户意图确实不清楚时才提出一个简短澄清问题。"
    "严禁输出 JSON、YAML、键值对、代码块、系统状态、环境信息或协议说明；"
    "不要出现 system_context、response_strategy、protocol_support 等内部字段。\n\n"
)
CLI_REFERENCE_REVIEW_PROMPT_PREFIX = (
    "你是认知系统的中文资料审查助手。请只依据下方受控参考资料进行审查，"
    "直接输出普通中文自然语言，不要输出 JSON、YAML、代码块、系统状态或协议说明。"
    "必须使用固定审查骨架：主要结论、判断依据、发现的问题、风险边界、建议动作。"
    "主要结论必须明确写出符合、部分符合、不符合或信息不足。"
    "发现的问题即使为空，也要说明剩余人工复核风险。"
    "风险边界必须保留资料中的暂不接入、关闭、禁止、边界类信号。"
    "建议动作必须能直接转成下一任务动作，并在需要时引用 evidence ref。"
    "如果资料说明 Agent runtime、Skills runtime 或 ADK SkillRegistry 未打开、"
    "关闭、暂不接入、禁止或阻止，必须把它们视为风险边界，"
    "不得建议打开、接入、集成、启用或开始实施这些 runtime。"
    "如果资料 excerpt 已提供，不要要求用户再次上传或粘贴文档。\n\n"
)
DEFAULT_RESPONSE_PREVIEW_LIMIT = 120
CLI_CHAT_JSON_FALLBACK_MESSAGE = (
    "我刚才的回复格式跑偏了。我们回到对话本身，我会用自然中文继续回答。"
)


@dataclass(frozen=True)
class AdkGovernedLlmInvocationOptions:
    """Local options for the ADK governed invocation candidate."""

    live_enabled: bool = False
    ollama_api_base: str = "http://127.0.0.1:11434"
    timeout_seconds: int = 45
    temperature: float = 0
    max_tokens: int = 64
    live_client: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AdkGovernedLlmInvocationService(GovernedLlmInvocationService):
    """No-live-first ADK-side candidate for governed LLM invocation.

    The candidate validates governance and route facts. It does not call a
    model by default. Explicit live mode stays adapter-local and returns only
    sanitized result facts.
    """

    def __init__(
        self,
        *,
        options: AdkGovernedLlmInvocationOptions | None = None,
    ) -> None:
        self._options = options or AdkGovernedLlmInvocationOptions()
        self._local_no_proxy_applied = False

    def invoke(self, request: LlmInvocationRequest) -> LlmInvocationResult:
        """Return a governed invocation result without default model execution."""

        self._local_no_proxy_applied = False
        if not request.governance_precondition.allowed:
            return self._blocked_result(request)

        route_error = self._route_error(request)
        if route_error is not None:
            return self._failed_result(
                request,
                failure_type=LlmInvocationFailureType.ROUTE_FACTS_INVALID,
                error_message_sanitized=route_error,
                metadata={"adapter_boundary": "adk_adapter.llm_invocation"},
            )

        if not self._options.live_enabled:
            return self._failed_result(
                request,
                failure_type=LlmInvocationFailureType.LIVE_DISABLED,
                error_message_sanitized="live invocation is disabled by default",
                call_allowed=True,
                metadata={
                    "adapter_boundary": "adk_adapter.llm_invocation",
                    "live_enabled": False,
                    "future_route": "ADK LiteLlm / LiteLLM provider route",
                },
            )

        return self._run_controlled_live_litellm_ollama(request)

    def _blocked_result(self, request: LlmInvocationRequest) -> LlmInvocationResult:
        failure_type = (
            LlmInvocationFailureType.GOVERNANCE_NEEDS_EVIDENCE
            if request.governance_precondition.decision == "need_evidence"
            else LlmInvocationFailureType.GOVERNANCE_BLOCKED
        )
        return self._failed_result(
            request,
            failure_type=failure_type,
            error_message_sanitized=f"governance precondition denied: "
            f"{request.governance_precondition.reason}",
            metadata={
                "adapter_boundary": "adk_adapter.llm_invocation",
                "blocked_before_adapter_call": True,
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
            route_facts=request.route_facts,
            governance_precondition=request.governance_precondition,
            call_attempted=call_attempted,
            call_allowed=call_allowed,
            runtime_call_performed=runtime_call_performed,
            success=False,
            response_non_empty=False,
            latency_ms=latency_ms,
            failure_type=failure_type,
            error_message_sanitized=_sanitize_message(error_message_sanitized),
            metadata={
                **self._safe_options_metadata(),
                **(metadata or {}),
            },
        )

    def _success_result(
        self,
        request: LlmInvocationRequest,
        *,
        output_text: str,
        latency_ms: int,
        metadata: dict[str, Any] | None = None,
    ) -> LlmInvocationResult:
        sanitized_output = _normalize_provider_output_text(
            output_text,
            request_metadata=request.metadata,
        )
        response_preview_limit = self._response_preview_limit()
        return LlmInvocationResult(
            request_id=request.request_id,
            route_facts=request.route_facts,
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
                **self._safe_options_metadata(),
                **_display_response_metadata(
                    sanitized_output,
                    limit=response_preview_limit,
                ),
                **(metadata or {}),
            },
        )

    def _run_controlled_live_litellm_ollama(
        self,
        request: LlmInvocationRequest,
    ) -> LlmInvocationResult:
        started_at = time.monotonic()
        prompt = (request.prompt_preview_sanitized or "").strip()
        if not prompt:
            return self._failed_result(
                request,
                failure_type=LlmInvocationFailureType.LIVE_CALL_FAILURE,
                error_message_sanitized="prompt_preview_sanitized is required for controlled live invocation",
                call_allowed=True,
                metadata={
                    "adapter_boundary": "adk_adapter.llm_invocation",
                    "controlled_live_path": "adk_litellm_ollama",
                    "live_enabled": True,
                    "adapter_call_started": False,
                },
            )

        try:
            self._construct_validated_route(request.route_facts.model_name)
        except ModuleNotFoundError as exc:
            return self._failed_result(
                request,
                failure_type=LlmInvocationFailureType.DEPENDENCY_FAILURE,
                error_message_sanitized=str(exc),
                call_allowed=True,
                latency_ms=_elapsed_ms(started_at),
                metadata=_live_failure_metadata(adapter_call_started=False),
            )
        except Exception as exc:  # noqa: BLE001 - classify route construction failures.
            return self._failed_result(
                request,
                failure_type=LlmInvocationFailureType.ROUTE_CONSTRUCTION_FAILURE,
                error_message_sanitized=str(exc),
                call_allowed=True,
                latency_ms=_elapsed_ms(started_at),
                metadata=_live_failure_metadata(adapter_call_started=False),
            )

        try:
            output_text = self._invoke_litellm_client(request, prompt)
        except ModuleNotFoundError as exc:
            return self._failed_result(
                request,
                failure_type=LlmInvocationFailureType.DEPENDENCY_FAILURE,
                error_message_sanitized=str(exc),
                call_allowed=True,
                latency_ms=_elapsed_ms(started_at),
                metadata=_live_failure_metadata(adapter_call_started=False),
            )
        except TimeoutError as exc:
            return self._failed_result(
                request,
                failure_type=LlmInvocationFailureType.TIMEOUT_FAILURE,
                error_message_sanitized=str(exc),
                call_attempted=True,
                call_allowed=True,
                runtime_call_performed=True,
                latency_ms=_elapsed_ms(started_at),
                metadata=_live_failure_metadata(adapter_call_started=True),
            )
        except _LiveCallError as exc:
            return self._failed_result(
                request,
                failure_type=LlmInvocationFailureType.LIVE_CALL_FAILURE,
                error_message_sanitized=str(exc),
                call_attempted=True,
                call_allowed=True,
                runtime_call_performed=True,
                latency_ms=_elapsed_ms(started_at),
                metadata=_live_failure_metadata(adapter_call_started=True),
            )

        repair_reason = _chat_repair_reason(request, output_text)
        repair_retry_attempted = repair_reason is not None
        repair_retry_performed = False
        repair_retry_failed = False
        repair_retry_fallback_used = False
        if repair_reason is not None:
            try:
                repaired_output_text = self._invoke_litellm_client(
                    request,
                    prompt,
                    repair_reason=repair_reason,
                    previous_output_text=output_text,
                )
            except (TimeoutError, _LiveCallError):
                repair_retry_failed = True
            else:
                if repaired_output_text.strip():
                    output_text = repaired_output_text
                    repair_retry_performed = True
                    if _chat_repair_reason(request, output_text) is not None:
                        output_text = _cli_chat_repair_fallback(
                            request.metadata,
                            repair_reason=repair_reason,
                        )
                        repair_retry_fallback_used = True

        return self._success_result(
            request,
            output_text=output_text,
            latency_ms=_elapsed_ms(started_at),
            metadata={
                "adapter_boundary": "adk_adapter.llm_invocation",
                "controlled_live_path": "adk_litellm_ollama",
                "adk_litellm_route_constructed": True,
                "adapter_call_started": True,
                "client_kind": "ADK LiteLLMClient",
                "output_non_empty": bool(output_text.strip()),
                "repair_retry_attempted": repair_retry_attempted,
                "repair_retry_performed": repair_retry_performed,
                "repair_retry_failed": repair_retry_failed,
                "repair_retry_fallback_used": repair_retry_fallback_used,
                "repair_retry_max_once": True,
                **_repair_reason_metadata(repair_reason),
            },
        )

    def _construct_validated_route(self, model_name: str) -> None:
        from adk_adapter.models import build_litellm_ollama_model_route

        _, route_facts = build_litellm_ollama_model_route(model_name=model_name)
        public_facts = route_facts.to_public_model_route_facts()
        if public_facts.provider != "litellm":
            raise ValueError("route provider must be litellm")
        if public_facts.metadata.get("backend_provider") != "ollama":
            raise ValueError("route backend_provider must be ollama")
        if public_facts.metadata.get("route_kind") != "adk_litellm":
            raise ValueError("route_kind must be adk_litellm")
        if public_facts.metadata.get("route_target") != model_name:
            raise ValueError("route_target must match model_name")

    def _invoke_litellm_client(
        self,
        request: LlmInvocationRequest,
        prompt: str,
        *,
        repair_reason: str | None = None,
        previous_output_text: str | None = None,
    ) -> str:
        self._local_no_proxy_applied = _ensure_local_no_proxy(
            self._options.ollama_api_base
        )
        client = self._options.live_client
        if client is None:
            from google.adk.models.lite_llm import LiteLLMClient

            client = LiteLLMClient()

        try:
            result = client.completion(
                model=request.route_facts.model_name,
                messages=_provider_messages(
                    request,
                    prompt,
                    repair_reason=repair_reason,
                    previous_output_text=previous_output_text,
                ),
                tools=[],
                api_base=self._options.ollama_api_base,
                temperature=self._options.temperature,
                max_tokens=self._options.max_tokens,
                timeout=self._options.timeout_seconds,
            )
        except TimeoutError:
            raise
        except Exception as exc:  # noqa: BLE001 - keep provider errors sanitized.
            raise _LiveCallError(_sanitize_message(str(exc))) from exc

        try:
            return _extract_output_text(result)
        except Exception as exc:  # noqa: BLE001 - response shape is provider-controlled.
            raise _LiveCallError(f"could not extract sanitized provider output: {exc}") from exc

    def _route_error(self, request: LlmInvocationRequest) -> str | None:
        route_facts = request.route_facts
        route_metadata = route_facts.metadata
        if route_facts.provider != "litellm":
            return "route provider must be litellm"
        if route_metadata.get("backend_provider") != "ollama":
            return "route backend_provider must be ollama"
        if route_metadata.get("route_kind") != "adk_litellm":
            return "route_kind must be adk_litellm"
        if route_metadata.get("route_target") != route_facts.model_name:
            return "route_target must match model_name"
        return None

    def _safe_options_metadata(self) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "options": {
                **dict(self._options.metadata),
                "ollama_api_base": self._options.ollama_api_base,
                "timeout_seconds": self._options.timeout_seconds,
                "temperature": self._options.temperature,
                "max_tokens": self._options.max_tokens,
                "local_no_proxy_applied": self._local_no_proxy_applied,
            },
            "live_enabled": self._options.live_enabled,
        }
        live_profile = self._live_profile_metadata()
        if live_profile is not None:
            metadata["llm_live_profile"] = live_profile
        return metadata

    def _live_profile_metadata(self) -> dict[str, Any] | None:
        options_metadata = dict(self._options.metadata)
        controlled_live = options_metadata.get(
            "controlled_live",
            self._options.live_enabled,
        )
        if not self._options.live_enabled and controlled_live is not True:
            return None

        profile = {
            "controlled_live": bool(controlled_live),
            "timeout_seconds": self._options.timeout_seconds,
            "temperature": self._options.temperature,
            "max_tokens": self._options.max_tokens,
            "local_no_proxy_applied": self._local_no_proxy_applied,
        }
        for key in (
            "live_options_source",
            "live_service_profile",
            "configured_model_name",
        ):
            value = options_metadata.get(key)
            if isinstance(value, str) and value:
                profile[key] = value
        return profile

    def _response_preview_limit(self) -> int:
        limit = self._options.metadata.get(
            "response_preview_limit",
            DEFAULT_RESPONSE_PREVIEW_LIMIT,
        )
        if isinstance(limit, int) and limit > 0:
            return limit
        return DEFAULT_RESPONSE_PREVIEW_LIMIT


def _provider_messages(
    request: LlmInvocationRequest,
    prompt: str,
    *,
    repair_reason: str | None = None,
    previous_output_text: str | None = None,
) -> list[dict[str, str]]:
    if request.metadata.get("interaction_mode") == "cli_chat":
        if repair_reason is not None:
            content = (
                f"{CLI_CHAT_PROMPT_PREFIX}"
                f"{_cli_chat_repair_prompt_text(request, prompt, repair_reason, previous_output_text)}"
            )
            return [{"role": "user", "content": content}]
        return [
            {
                "role": "user",
                "content": (
                    f"{CLI_CHAT_PROMPT_PREFIX}"
                    f"{_cli_chat_prompt_text(request, prompt)}"
                ),
            }
        ]
    if request.metadata.get("interaction_mode") == "cli_reference_review_workflow":
        return [
            {
                "role": "user",
                "content": (
                    f"{CLI_REFERENCE_REVIEW_PROMPT_PREFIX}"
                    f"{_cli_reference_review_prompt_text(request, prompt)}"
                ),
            }
        ]
    return [{"role": "user", "content": prompt}]


def _cli_reference_review_prompt_text(
    request: LlmInvocationRequest,
    prompt: str,
) -> str:
    context = request.metadata.get("reference_review_context")
    if not isinstance(context, Mapping):
        return prompt

    lines = []
    current_user_input = _normalize_provider_prompt_fragment(
        context.get("current_user_input")
    )
    lines.append("用户审查请求：")
    lines.append(current_user_input or prompt)
    labels = context.get("reference_labels")
    evidence_refs = context.get("evidence_refs")
    if isinstance(labels, list | tuple) and labels:
        lines.append("受控资料：")
        for index, label in enumerate(labels):
            ref = (
                evidence_refs[index]
                if isinstance(evidence_refs, list | tuple)
                and index < len(evidence_refs)
                else "evidence_ref未生成"
            )
            label_text = _normalize_provider_prompt_fragment(label)
            ref_text = _normalize_provider_prompt_fragment(ref)
            lines.append(f"- {label_text or f'reference-{index + 1}'}：{ref_text}")

    excerpts = context.get("reference_excerpts")
    if isinstance(excerpts, list | tuple) and excerpts:
        lines.append("受控资料 excerpt：")
        for index, excerpt in enumerate(excerpts, start=1):
            excerpt_text = _normalize_provider_prompt_fragment(excerpt)[:1800]
            lines.append(f"[excerpt {index}] {excerpt_text}")

    lines.append("输出要求：")
    lines.append("1. 必须按以下中文小标题和顺序输出：")
    lines.append("   主要结论")
    lines.append("   判断依据")
    lines.append("   发现的问题")
    lines.append("   风险边界")
    lines.append("   建议动作")
    lines.append("2. 主要结论必须明确判断：符合、部分符合、不符合或信息不足；")
    lines.append("3. 判断依据必须来自上方受控资料 excerpt 或 evidence ref；")
    lines.append("4. 发现的问题不能只写“无”，至少说明剩余人工复核风险；")
    lines.append("5. 风险边界必须保留暂不接入、关闭、禁止、边界等信号；")
    lines.append("6. 建议动作必须给出下一步可执行动作；")
    lines.append(
        "7. 如果资料中出现 Agent runtime、Skills runtime、ADK SkillRegistry "
        "与未打开、关闭、暂不接入、禁止、阻止等信号，建议动作只能写保持关闭、"
        "另开评议任务或补充审批证据；"
    )
    lines.append(
        "8. 严禁把未打开、关闭、暂不接入类边界改写成打开、接入、集成、启用或开始实施；"
    )
    lines.append("9. 不要要求用户再次提供资料；")
    lines.append("10. 不要输出 JSON。")
    return "\n".join(lines)


def _cli_chat_prompt_text(
    request: LlmInvocationRequest,
    prompt: str,
) -> str:
    context = request.metadata.get("cli_chat_context")
    if not isinstance(context, Mapping):
        return prompt

    lines = []
    history = context.get("history")
    if isinstance(history, list | tuple) and history:
        lines.append("最近对话：")
        for item in history:
            if not isinstance(item, Mapping):
                continue
            user_text = _normalize_provider_prompt_fragment(item.get("user"))
            assistant_text = _normalize_provider_prompt_fragment(item.get("assistant"))
            if user_text:
                lines.append(f"用户：{user_text}")
            if assistant_text:
                lines.append(f"助手：{assistant_text}")

    current_user_input = _normalize_provider_prompt_fragment(
        context.get("current_user_input")
    )
    lines.append("当前用户输入：")
    lines.append(current_user_input or prompt)
    direct_answer_instruction = _cli_chat_direct_answer_instruction(
        current_user_input
    )
    if direct_answer_instruction:
        lines.append("本轮执行要求：")
        lines.append(direct_answer_instruction)
    return "\n".join(lines)


def _cli_chat_repair_prompt_text(
    request: LlmInvocationRequest,
    prompt: str,
    repair_reason: str,
    previous_output_text: str | None,
) -> str:
    lines = [
        "你刚才的回复没有满足用户请求。请根据最近对话重新回答当前用户。",
        "失败原因：",
        _repair_reason_display(repair_reason),
        "",
        _cli_chat_prompt_text(request, prompt),
        "",
        "上一版 assistant 回复摘要：",
        _normalize_provider_prompt_fragment(previous_output_text)[:600]
        or "上一版回复为空。",
        "",
        "本次必须：",
        "1. 直接输出自然中文答案；",
        "2. 使用清晰标题、编号和分段；",
        "3. 承接用户给出的业务实体、规模、约束和上一轮内容；",
        "4. 如果用户要求重新排版，请直接重排已有内容；",
        "5. 不输出 JSON；",
        "6. 不反问；",
        "7. 不说请稍等。",
    ]
    return "\n".join(lines)


def _normalize_provider_prompt_fragment(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.strip().split())


def _cli_chat_direct_answer_instruction(current_user_input: str) -> str:
    if not current_user_input:
        return ""
    if _requests_full_expansion(current_user_input):
        return (
            "用户要求全面展开。请直接输出完整结构化方案，覆盖目标、模块、"
            "技术原理、应用场景、实施步骤、风险与下一步建议；不要反问，"
            "不要说请稍等，不要只写开场白。"
        )
    if _requests_continuation(current_user_input):
        return (
            "用户要求继续。请承接上一轮主题继续输出具体内容；不要反问从哪里开始，"
            "不要重复开场白，不要说请稍等。"
        )
    if _requests_direct_plan(current_user_input):
        return (
            "用户要求直接输出方案。请立即给出可读的方案框架，至少包含目标、"
            "三到五个核心模块、技术路径、落地步骤和风险边界；不要反问，"
            "不要说请稍等，不要只写准备性句子。"
        )
    return ""


def _requests_direct_plan(value: str) -> bool:
    return "方案" in value and any(
        keyword in value
        for keyword in (
            "直接",
            "输出",
            "设计",
            "给出",
            "做个",
        )
    )


def _requests_continuation(value: str) -> bool:
    normalized = value.strip()
    return normalized in {"继续", "接着说", "展开", "继续展开"}


def _requests_full_expansion(value: str) -> bool:
    return any(
        keyword in value
        for keyword in (
            "全面展开",
            "完整展开",
            "详细展开",
            "全部展开",
        )
    )


def _display_response_metadata(
    sanitized_output: str,
    *,
    limit: int,
) -> dict[str, str]:
    if limit <= DEFAULT_RESPONSE_PREVIEW_LIMIT or not sanitized_output:
        return {}
    return {"sanitized_response_display": _preview(sanitized_output, limit=limit)}


def _chat_repair_reason(
    request: LlmInvocationRequest,
    output_text: str,
) -> str | None:
    if not _is_cli_chat_metadata(request.metadata):
        return None
    normalized_output = _normalize_provider_output_text(
        output_text,
        request_metadata=request.metadata,
    )
    current_input = _cli_chat_current_input(request.metadata)
    context_text = _cli_chat_context_text(request.metadata)

    if _raw_output_is_structured_json_without_display(output_text):
        return "structured_json_without_display"
    if _assistant_defers_or_asks(normalized_output) and (
        _requests_direct_answer(current_input)
        or _requests_format_rewrite(current_input)
        or _requests_plan_output(current_input)
    ):
        return "direct_request_deflected"
    if _requests_plan_output(current_input) and _plan_output_is_too_generic(
        current_input,
        normalized_output,
    ):
        return "plan_request_not_answered"
    if _requests_format_rewrite(current_input) and _format_rewrite_is_not_done(
        normalized_output,
        context_text,
    ):
        return "format_rewrite_not_performed"
    return None


def _raw_output_is_structured_json_without_display(output_text: str) -> bool:
    sanitized_output = " ".join(output_text.strip().split())
    if not sanitized_output:
        return False
    try:
        decoded = json.loads(sanitized_output)
    except json.JSONDecodeError:
        return _looks_like_json_text(sanitized_output) and not (
            _extract_jsonish_response_text(sanitized_output)
        )
    if not isinstance(decoded, dict):
        return False
    return not any(
        isinstance(decoded.get(key), str) and decoded.get(key, "").strip()
        for key in ("response", "answer", "content", "response_to_user")
    )


def _requests_direct_answer(value: str) -> bool:
    return (
        _requests_direct_plan(value)
        or _requests_continuation(value)
        or _requests_full_expansion(value)
    )


def _requests_plan_output(value: str) -> bool:
    return any(
        keyword in value
        for keyword in (
            "方案",
            "计划",
            "规划",
            "设计",
            "怎么做",
            "如何做",
        )
    )


def _requests_format_rewrite(value: str) -> bool:
    return any(
        keyword in value
        for keyword in (
            "排版",
            "重新做",
            "重新整理",
            "重排",
            "格式",
            "所有的",
        )
    )


def _assistant_defers_or_asks(value: str) -> bool:
    return any(
        marker in value
        for marker in (
            "请稍等",
            "马上为您",
            "请告诉我",
            "你希望",
            "您希望",
            "哪个部分",
            "哪个模块",
            "从哪里开始",
            "是否需要",
            "可以吗？",
            "可以吗",
            "你觉得这个方向可以吗",
        )
    )


def _plan_output_is_too_generic(
    current_input: str,
    normalized_output: str,
) -> bool:
    if not normalized_output:
        return True
    if _assistant_defers_or_asks(normalized_output):
        return True
    generic_markers = (
        "通用方案框架",
        "目标先定义清楚",
        "感知、分析、决策、执行",
        "最小可验证能力",
        "跑通真实用户场景",
        "我将把方案拆解",
        "我马上为您呈现",
        "马上为您呈现",
    )
    if any(marker in normalized_output for marker in generic_markers):
        return True
    if len(normalized_output) < 180 and not _has_structured_response(
        normalized_output
    ):
        return True
    key_terms = _chat_key_terms(current_input)
    if key_terms and not any(term in normalized_output for term in key_terms):
        return True
    return False


def _format_rewrite_is_not_done(
    normalized_output: str,
    context_text: str,
) -> bool:
    if not normalized_output:
        return True
    if _assistant_defers_or_asks(normalized_output):
        return True
    if not _has_structured_response(normalized_output):
        return True
    key_terms = _chat_key_terms(context_text)
    if key_terms and not any(term in normalized_output for term in key_terms):
        return True
    return False


def _has_structured_response(value: str) -> bool:
    markers = (
        "##",
        "###",
        "一、",
        "二、",
        "三、",
        "四、",
        "五、",
        "1.",
        "2.",
        "3.",
        "1．",
        "2．",
        "3．",
        "* ",
        "- ",
    )
    return sum(value.count(marker) for marker in markers) >= 2


def _chat_key_terms(value: str) -> list[str]:
    terms: list[str] = []
    normalized = _normalize_provider_prompt_fragment(value)
    for number_term in re.findall(r"\d+\s*[\u4e00-\u9fff]{1,4}", normalized):
        terms.append(number_term.replace(" ", ""))

    for chunk in re.split(r"[\s，。；、,.!?！？:：]+", normalized):
        cleaned = chunk.strip()
        if not cleaned:
            continue
        for marker in (
            "我要",
            "我想",
            "开个",
            "请你",
            "请",
            "帮我",
            "给我",
            "做个",
            "设计个",
            "设计一个",
            "设计",
            "方案",
            "规模",
            "重新",
            "排版",
            "当前",
            "有点",
            "所有的",
        ):
            cleaned = cleaned.replace(marker, "")
        cleaned = cleaned.strip()
        if 2 <= len(cleaned) <= 12 and not _is_generic_chat_term(cleaned):
            terms.append(cleaned)

    deduped: list[str] = []
    for term in terms:
        if term and term not in deduped:
            deduped.append(term)
    return deduped[:6]


def _is_generic_chat_term(value: str) -> bool:
    if any(
        marker in value
        for marker in (
            "你能",
            "好些",
            "有点乱",
            "先按",
            "当前",
            "排版",
            "重新",
            "吗",
            "吧",
        )
    ):
        return True
    return value in {
        "同意",
        "继续",
        "展开",
        "直接输出",
        "你先吧",
        "的乱",
        "可以",
        "好的",
        "所有",
    }


def _repair_reason_display(reason: str) -> str:
    return {
        "structured_json_without_display": "模型返回了结构化 JSON，但没有可展示的自然语言字段。",
        "direct_request_deflected": "用户要求直接输出或重排，但回复仍在反问或推迟。",
        "plan_request_not_answered": "用户要求方案，但回复过泛，没有承接业务实体或规模。",
        "format_rewrite_not_performed": "用户要求重新排版，但回复没有直接重排上一轮内容。",
    }.get(reason, reason)


def _repair_reason_metadata(reason: str | None) -> dict[str, str]:
    if reason is None:
        return {}
    return {
        "repair_retry_reason": reason,
        "repair_retry_reason_display": _repair_reason_display(reason),
    }


def _normalize_provider_output_text(
    output_text: str,
    *,
    request_metadata: Mapping[str, Any] | None = None,
) -> str:
    sanitized_output = " ".join(output_text.strip().split())
    if not sanitized_output:
        return sanitized_output
    try:
        decoded = json.loads(sanitized_output)
    except json.JSONDecodeError:
        extracted = _extract_jsonish_response_text(sanitized_output)
        if extracted:
            return extracted
        if _is_cli_chat_metadata(request_metadata) and _looks_like_json_text(
            sanitized_output
        ):
            return _cli_chat_json_fallback(request_metadata)
        return sanitized_output
    if isinstance(decoded, dict):
        for key in ("response", "answer", "content", "response_to_user"):
            value = decoded.get(key)
            if isinstance(value, str) and value.strip():
                return " ".join(value.strip().split())
        if _is_cli_chat_metadata(request_metadata):
            return _cli_chat_json_fallback(request_metadata)
    return sanitized_output


def _extract_jsonish_response_text(value: str) -> str | None:
    for key in ("response", "answer", "content", "response_to_user"):
        extracted = _extract_jsonish_string_field(value, key)
        if extracted:
            return " ".join(extracted.strip().split())
    return None


def _is_cli_chat_metadata(value: Mapping[str, Any] | None) -> bool:
    return isinstance(value, Mapping) and value.get("interaction_mode") == "cli_chat"


def _looks_like_json_text(value: str) -> bool:
    stripped = value.lstrip()
    return stripped.startswith("{") or stripped.startswith("[")


def _cli_chat_json_fallback(metadata: Mapping[str, Any] | None) -> str:
    current_input = _cli_chat_current_input(metadata)
    context_text = _cli_chat_user_context_text(metadata)
    if _requests_format_rewrite(current_input):
        return _cli_chat_full_expansion_fallback(context_text)
    if _requests_full_expansion(current_input):
        return _cli_chat_full_expansion_fallback(context_text)
    if _requests_continuation(current_input):
        return _cli_chat_continuation_fallback(context_text)
    if _requests_direct_plan(current_input):
        return _cli_chat_direct_plan_fallback(context_text)
    if _looks_like_greeting(current_input):
        return "你好！我在这里。你想聊什么都可以，我们慢慢来。"
    if _looks_like_low_mood(current_input):
        return "听起来你现在有点不好受。我在这里，可以陪你慢慢聊。"
    if current_input in {"?", "？"} or "怎么了" in current_input:
        return "刚才回复格式跑偏了，抱歉。我们回到对话本身，我会用自然中文继续回答。"
    if current_input:
        return f"关于“{current_input}”，我先给你一个直接回应：我们可以继续往下拆。"
    return CLI_CHAT_JSON_FALLBACK_MESSAGE


def _cli_chat_repair_fallback(
    metadata: Mapping[str, Any] | None,
    *,
    repair_reason: str,
) -> str:
    current_input = _cli_chat_current_input(metadata)
    context_text = _cli_chat_user_context_text(metadata)
    if _requests_format_rewrite(current_input) or _requests_full_expansion(
        current_input
    ):
        return _cli_chat_full_expansion_fallback(context_text)
    if _requests_continuation(current_input):
        return _cli_chat_continuation_fallback(context_text)
    if _requests_plan_output(current_input) or _requests_direct_plan(current_input):
        return _cli_chat_direct_plan_fallback(context_text)
    if repair_reason == "structured_json_without_display":
        return _cli_chat_json_fallback(metadata)
    return CLI_CHAT_JSON_FALLBACK_MESSAGE


def _cli_chat_direct_plan_fallback(context_text: str) -> str:
    key_terms = "、".join(_chat_key_terms(context_text)[:3]) or "当前主题"
    return (
        f"可以，先按“{key_terms}”给出一版可执行方案：\n"
        "1. 目标：明确服务对象、规模、预算和验收指标。\n"
        "2. 模块：拆成基础条件、运营流程、资源配置、风险控制和复盘优化。\n"
        "3. 路径：先做一个最小可运行版本，再根据真实反馈逐步扩展。\n"
        "4. 风险：优先识别成本、合规、安全、供应和维护风险。\n"
        "5. 下一步：把关键数字、场地条件和预算约束补齐后细化执行清单。"
    )


def _cli_chat_continuation_fallback(context_text: str) -> str:
    key_terms = "、".join(_chat_key_terms(context_text)[:3]) or "上一轮方案"
    return (
        f"继续展开“{key_terms}”：\n"
        "1. 先明确第一阶段最小闭环，保证可以真实运行和验收。\n"
        "2. 再列出每日/每周的执行动作，避免方案停留在概念层。\n"
        "3. 接着补充成本、人员、物料、工具和时间安排。\n"
        "4. 最后设置风险预警和复盘指标，便于持续调整。"
    )


def _cli_chat_full_expansion_fallback(context_text: str) -> str:
    key_terms = "、".join(_chat_key_terms(context_text)[:3]) or "当前方案"
    return (
        f"全面展开“{key_terms}”如下：\n"
        "一、目标：定义要解决的问题、目标规模、关键收益和验收标准。\n"
        "二、资源：列出场地、设备、人员、资金、供应链和工具条件。\n"
        "三、流程：拆成准备、启动、日常运行、异常处理和复盘优化。\n"
        "四、成本：区分一次性投入、持续运营成本和应急预留。\n"
        "五、风险：覆盖合规、安全、质量、现金流、供应和人员风险。\n"
        "六、下一步：先做一版最小执行清单，再根据真实约束细化预算和时间表。"
    )


def _cli_chat_current_input(metadata: Mapping[str, Any] | None) -> str:
    if not isinstance(metadata, Mapping):
        return ""
    context = metadata.get("cli_chat_context")
    if not isinstance(context, Mapping):
        return ""
    return _normalize_provider_prompt_fragment(context.get("current_user_input"))


def _cli_chat_context_text(metadata: Mapping[str, Any] | None) -> str:
    if not isinstance(metadata, Mapping):
        return ""
    context = metadata.get("cli_chat_context")
    if not isinstance(context, Mapping):
        return ""
    fragments = [_normalize_provider_prompt_fragment(context.get("current_user_input"))]
    history = context.get("history")
    if isinstance(history, list | tuple):
        for item in history:
            if not isinstance(item, Mapping):
                continue
            fragments.append(_normalize_provider_prompt_fragment(item.get("user")))
            fragments.append(_normalize_provider_prompt_fragment(item.get("assistant")))
    return " ".join(fragment for fragment in fragments if fragment)


def _cli_chat_user_context_text(metadata: Mapping[str, Any] | None) -> str:
    if not isinstance(metadata, Mapping):
        return ""
    context = metadata.get("cli_chat_context")
    if not isinstance(context, Mapping):
        return ""
    fragments = [_normalize_provider_prompt_fragment(context.get("current_user_input"))]
    history = context.get("history")
    if isinstance(history, list | tuple):
        for item in history:
            if not isinstance(item, Mapping):
                continue
            fragments.append(_normalize_provider_prompt_fragment(item.get("user")))
    return " ".join(fragment for fragment in fragments if fragment)



def _looks_like_greeting(value: str) -> bool:
    normalized = value.strip()
    return normalized in {"你好", "您好", "hi", "Hi", "hello", "Hello"}


def _looks_like_low_mood(value: str) -> bool:
    return any(
        keyword in value
        for keyword in (
            "心情不好",
            "心情有点不好",
            "心情有些不好",
            "有些心情不好",
            "有点闷",
            "焦虑",
            "难受",
        )
    )


def _extract_jsonish_string_field(value: str, key: str) -> str | None:
    marker = f'"{key}"'
    key_index = value.find(marker)
    if key_index < 0:
        return None
    colon_index = value.find(":", key_index + len(marker))
    if colon_index < 0:
        return None
    quote_index = value.find('"', colon_index + 1)
    if quote_index < 0:
        return None

    chars: list[str] = []
    escaped = False
    for char in value[quote_index + 1 :]:
        if escaped:
            chars.append(_json_escape_char(char))
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            break
        chars.append(char)
    extracted = "".join(chars).strip()
    return extracted or None


def _json_escape_char(char: str) -> str:
    return {
        "n": "\n",
        "r": "\r",
        "t": "\t",
        '"': '"',
        "\\": "\\",
    }.get(char, char)


class _LiveCallError(RuntimeError):
    """Raised when the adapter-local live call fails."""


def _extract_output_text(result: Any) -> str:
    if isinstance(result, dict):
        choices = result.get("choices") or []
        first_choice = choices[0] if choices else {}
        message = first_choice.get("message", {})
        content = message.get("content")
        return "" if content is None else str(content)

    choices = getattr(result, "choices", None) or []
    first_choice = choices[0] if choices else None
    message = getattr(first_choice, "message", None)
    content = getattr(message, "content", None)
    return "" if content is None else str(content)


def _live_failure_metadata(*, adapter_call_started: bool) -> dict[str, Any]:
    return {
        "adapter_boundary": "adk_adapter.llm_invocation",
        "controlled_live_path": "adk_litellm_ollama",
        "live_enabled": True,
        "adapter_call_started": adapter_call_started,
    }


def _elapsed_ms(started_at: float) -> int:
    return int((time.monotonic() - started_at) * 1000)


def _preview(value: str, limit: int = 120) -> str:
    if len(value) <= limit:
        return value
    return value[:limit]


def _sanitize_message(value: str, limit: int = 240) -> str:
    sanitized = " ".join(str(value).split())
    forbidden_markers = (
        "api_key",
        "completion",
        "message",
        "messages",
        "prompt",
        "raw_provider_response",
        "raw_response",
        "response_text",
        "system_prompt",
        "token",
        "secret",
    )
    for marker in forbidden_markers:
        sanitized = sanitized.replace(marker, "[redacted]")
    if len(sanitized) <= limit:
        return sanitized
    return sanitized[:limit]


def _ensure_local_no_proxy(api_base: str) -> bool:
    host = urlparse(api_base).hostname
    if host not in {"127.0.0.1", "localhost"}:
        return False
    for key in ("NO_PROXY", "no_proxy"):
        existing = [
            item.strip()
            for item in os.environ.get(key, "").split(",")
            if item.strip()
        ]
        merged = existing + [
            item for item in ("127.0.0.1", "localhost") if item not in existing
        ]
        os.environ[key] = ",".join(merged)
    return True
